"""Main screen — sidebar resource picker + multi-tab resource editors."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.content import Content
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Label,
    ListItem,
    ListView,
    Static,
    Tab,
    TabbedContent,
    TabPane,
    Tabs,
)
from textual.widgets._tabbed_content import ContentTab

from ktui.schema.loader import get_all_resources
from ktui.ui.screens.confirm_dialog import ConfirmScreen
from ktui.ui.widgets.resource_editor import ResourceEditor

CLOSE_GLYPH = "✕"


class MainScreen(Screen):
    """Root screen: sidebar resource picker + one tab per open resource."""

    BINDINGS = [
        Binding("ctrl+v", "validate_form", "Validate", show=True),
        Binding("p", "preview_yaml", "Preview YAML", show=True),
        Binding("ctrl+s", "save_yaml", "Save", show=True),
        Binding("ctrl+w", "close_tab", "Close Tab", show=True),
        Binding("q", "request_quit", "Quit", show=True),
        Binding("ctrl+q", "request_quit", "Quit", show=False),
    ]

    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }

    #main-layout {
        height: 1fr;
    }

    #sidebar {
        width: 28;
        border-right: solid $primary-darken-2;
    }

    #platform-tabs {
        height: 3;
        min-height: 3;
        max-height: 3;
    }

    #resource-list {
        height: 1fr;
    }

    #content-area {
        width: 1fr;
        height: 1fr;
    }

    #editor-tabs {
        height: 1fr;
    }

    #editor-tabs > ContentSwitcher {
        height: 1fr;
    }

    #editor-tabs TabPane {
        height: 1fr;
        padding: 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._tab_seq = 0                      # global, for unique pane IDs
        self._kind_seq: dict[str, int] = {}    # per-kind, for "Deployment 2" labels
        self._active_before_click: str | None = None

    def compose(self) -> ComposeResult:
        from textual.widgets import Header
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                from ktui.ui.widgets.connection_panel import ConnectionPanel
                yield ConnectionPanel()
                yield Tabs(
                    Tab("Kubernetes", id="kubernetes"),
                    id="platform-tabs",
                )
                yield ListView(id="resource-list")
            with Vertical(id="content-area"):
                yield Static(
                    "← Select a resource from the sidebar to open it in a new tab.",
                    id="editor-placeholder",
                    classes="placeholder-text",
                )
                yield TabbedContent(id="editor-tabs")
        yield Footer()

    async def on_mount(self) -> None:
        self._populate_sidebar()
        self._sync_placeholder()
        initial_data = getattr(self.app, "initial_data", None)
        if initial_data and "kind" in initial_data:
            kind = initial_data["kind"]
            # Select it in the list view visually
            lv = self.query_one("#resource-list", ListView)
            for item in lv.children:
                if isinstance(item, ListItem) and item.name == kind:
                    lv.index = lv.children.index(item)
                    break
            await self.open_editor(kind, initial_data)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _populate_sidebar(self) -> None:
        lv = self.query_one("#resource-list", ListView)
        lv.clear()
        for r in get_all_resources():
            item = ListItem(Label(r["kind"]), name=r["kind"])
            lv.append(item)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "resource-list":
            return
        kind = event.item.name
        if kind:
            await self.open_editor(kind)

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    @property
    def _tabs(self) -> TabbedContent:
        return self.query_one("#editor-tabs", TabbedContent)

    def _sync_placeholder(self) -> None:
        has_tabs = self._tabs.tab_count > 0
        self._tabs.display = has_tabs
        self.query_one("#editor-placeholder", Static).display = not has_tabs

    @staticmethod
    def _tab_label(title: str, dirty: bool = False) -> Content:
        """Tab label: ``title [●] ✕`` — the trailing ✕ is the close hit-target."""
        text = Text(title)
        if dirty:
            text.append(" ●", style="bold yellow")
        text.append(" " + CLOSE_GLYPH, style="bold red")
        return Content.from_rich_text(text)

    async def open_editor(self, kind: str, initial_data: dict[str, Any] | None = None) -> None:
        """Open ``kind`` in a brand-new tab and focus it."""
        self._tab_seq += 1
        self._kind_seq[kind] = self._kind_seq.get(kind, 0) + 1
        pane_id = f"editor-tab-{self._tab_seq}"
        
        name = initial_data.get("metadata", {}).get("name") if initial_data else None
        label = f"{kind}: {name}" if name else f"{kind} {self._kind_seq[kind]}"

        editor = ResourceEditor(kind, initial_data=initial_data, default_title=label)
        tabs = self._tabs
        await tabs.add_pane(TabPane(self._tab_label(label), editor, id=pane_id))
        tabs.active = pane_id
        self._sync_placeholder()

    def _editor_for(self, pane_id: str) -> ResourceEditor | None:
        try:
            pane = self._tabs.get_pane(pane_id)
        except Exception:
            return None
        editors = pane.query(ResourceEditor)
        return editors.first() if editors else None

    def active_editor(self) -> ResourceEditor | None:
        """Return the editor in the currently visible tab, if any."""
        active = self._tabs.active
        return self._editor_for(active) if active else None

    async def action_close_tab(self) -> None:
        active = self._tabs.active
        if active:
            await self.request_close(active)

    async def request_close(self, pane_id: str, restore_active: str | None = None) -> None:
        """Close a tab, asking first if it has unsaved changes."""
        editor = self._editor_for(pane_id)
        if editor is None:
            return

        async def _close(confirmed: bool | None = True) -> None:
            if not confirmed:
                if restore_active:
                    self._tabs.active = restore_active
                return
            tabs = self._tabs
            await tabs.remove_pane(pane_id)
            # Closing a background tab shouldn't steal focus from the one you were on.
            if restore_active and restore_active != pane_id:
                try:
                    tabs.get_pane(restore_active)
                    tabs.active = restore_active
                except Exception:
                    pass
            self._sync_placeholder()

        if editor.is_dirty:
            self.app.push_screen(
                ConfirmScreen(
                    f"'{editor.tab_title}' has unsaved changes.\nClose it and discard them?",
                    title="Unsaved changes",
                    confirm_label="Discard & Close",
                ),
                _close,
            )
        else:
            await _close()

    # --- ✕ click / middle-click handling --------------------------------

    def _content_tab_at(self, widget: Any) -> ContentTab | None:
        if isinstance(widget, ContentTab) and self._tabs in widget.ancestors:
            return widget
        return None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        # Remember the active tab *before* Tabs reacts to the click, so closing a
        # background tab via ✕ can restore it.
        if self._content_tab_at(event.widget):
            self._active_before_click = self._tabs.active

    async def on_click(self, event: events.Click) -> None:
        tab = self._content_tab_at(event.widget)
        if tab is None or not tab.id:
            return
        pane_id = ContentTab.sans_prefix(tab.id)
        restore = self._active_before_click
        self._active_before_click = None

        if event.button == 2:  # middle-click closes, like browsers / VS Code
            event.stop()
            await self.request_close(pane_id, restore_active=restore)
            return

        # Hit zone = last 3 cells of the tab: the space, the ✕ glyph, and the
        # right padding cell — forgiving for mouse users.
        if event.screen_x >= tab.region.right - 3:
            event.stop()
            await self.request_close(pane_id, restore_active=restore)

    def on_resource_editor_title_changed(self, event: ResourceEditor.TitleChanged) -> None:
        for anc in event.editor.ancestors:
            if isinstance(anc, TabPane) and anc.id:
                try:
                    self._tabs.get_tab(anc.id).label = self._tab_label(
                        event.title, dirty=event.editor.is_dirty
                    )
                except Exception:
                    pass
                break

    # ------------------------------------------------------------------
    # Quit — confirm if any tab has unsaved changes
    # ------------------------------------------------------------------

    def action_request_quit(self) -> None:
        dirty = [e for e in self.query(ResourceEditor) if e.is_dirty]
        if not dirty:
            self.app.exit()
            return
        names = ", ".join(e.tab_title for e in dirty[:3]) + ("…" if len(dirty) > 3 else "")

        def _quit(confirmed: bool | None) -> None:
            if confirmed:
                self.app.exit()

        self.app.push_screen(
            ConfirmScreen(
                f"{len(dirty)} tab(s) have unsaved changes: {names}\nQuit anyway?",
                title="Unsaved changes",
                confirm_label="Quit without saving",
            ),
            _quit,
        )

    # ------------------------------------------------------------------
    # Actions — delegated to the active tab's editor so the hotkeys work
    # even when focus is in the sidebar.
    # ------------------------------------------------------------------

    def action_validate_form(self) -> None:
        editor = self.active_editor()
        if editor:
            editor.action_validate_form()

    def action_preview_yaml(self) -> None:
        editor = self.active_editor()
        if editor is None:
            self.app.notify("No resource open.", severity="warning")
            return
        editor.action_preview_yaml()

    def action_save_yaml(self) -> None:
        editor = self.active_editor()
        if editor is None:
            self.app.notify("No resource open.", severity="warning")
            return
        editor.action_save_yaml()
