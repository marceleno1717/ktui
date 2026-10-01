"""Main screen — schema-driven resource picker + dynamic form."""

from __future__ import annotations

import re
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    Switch,
    Tab,
    Tabs,
)

from ktui.schema.emitter import emit_yaml_from_dict
from ktui.schema.loader import get_all_resources, get_resource
from ktui.ui.engine.schema_form_builder import (
    merge_paths_into_form,
    build_schema_form,
    decode_path,
)
from ktui.ui.screens.field_picker import FieldPickerScreen
from ktui.ui.screens.yaml_preview import YAMLPreviewScreen
from ktui.ui.widgets.map_editor import MapEditor


import re

def _set_nested(data: dict, path: list[str], value: Any) -> None:
    """Write a value into a nested dict/list, parsing [N] for arrays."""
    d = data
    for k in path[:-1]:
        m = re.search(r"\[(\d*)\]$", k)
        if m:
            clean_k = k[:m.start()]
            idx_str = m.group(1)
            idx = int(idx_str) if idx_str else 0
            if clean_k not in d or not isinstance(d[clean_k], list):
                d[clean_k] = []
            while len(d[clean_k]) <= idx:
                d[clean_k].append({})
            d = d[clean_k][idx]
        else:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]

    last_k = path[-1]
    m = re.search(r"\[(\d*)\]$", last_k)
    if m:
        clean_k = last_k[:m.start()]
        idx_str = m.group(1)
        idx = int(idx_str) if idx_str else 0
        if clean_k not in d or not isinstance(d[clean_k], list):
            d[clean_k] = []
        while len(d[clean_k]) <= idx:
            d[clean_k].append(None)
        d[clean_k][idx] = value
    else:
        if value is None or value == "":
            d.pop(last_k, None)
        else:
            d[last_k] = value


def _get_nested(data: dict, path: list[str], default: Any = None) -> Any:
    for key in path:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


class MainScreen(Screen):
    """Root screen: sidebar resource picker + schema-driven form."""

    BINDINGS = [
        Binding("p", "preview_yaml", "Preview YAML", show=True),
        Binding("ctrl+s", "save_yaml", "Save", show=True),
        Binding("q", "app.quit", "Quit", show=True),
        Binding("ctrl+q", "app.quit", "Quit", show=False),
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

    #resource-header {
        height: 3;
        background: $surface-lighten-1;
        padding: 1 2;
        text-style: bold;
    }

    #form-scroll {
        height: 1fr;
        padding: 1 2;
    }

    .form-field {
        height: auto;
        margin-bottom: 1;
    }

    .field-label {
        color: $text-muted;
        margin-bottom: 0;
    }

    .readonly-value {
        color: $warning;
        padding: 0 1;
    }

    .form-input {
        height: auto;
    }

    #action-bar {
        height: 5;
        align: right middle;
        padding: 0 2;
        border-top: solid $surface-lighten-2;
    }

    #action-bar Button {
        margin-left: 1;
    }

    .schema-add-fields-btn {
        margin: 1 0;
    }

    .schema-advanced-fields {
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_kind: str | None = None
        self._form_data: dict[str, Any] = {}
        self._shown_paths: set[str] = set()
        self._advanced_container = None

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
                with Horizontal(id="toolbar"):
                    yield Static("← Select a resource to begin", id="resource-header")
                    yield Button("Preview YAML  \\[p]", id="btn-preview", variant="primary")
                    yield Button("Save  \\[ctrl+s]", id="btn-save", variant="success")
                with VerticalScroll(id="form-scroll"):
                    yield Static(
                        "Select a resource from the sidebar.",
                        id="form-placeholder",
                        classes="placeholder-text",
                    )
        yield Footer()

    def on_mount(self) -> None:
        self._populate_sidebar()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _populate_sidebar(self) -> None:
        lv = self.query_one("#resource-list", ListView)
        lv.clear()
        for r in get_all_resources():
            item = ListItem(Label(r["kind"]), name=r["kind"])
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        kind = event.item.name
        if kind:
            self._load_resource(kind)

    # ------------------------------------------------------------------
    # Form loading
    # ------------------------------------------------------------------

    def _load_resource(self, kind: str) -> None:
        resource = get_resource(kind)
        if resource is None:
            return

        self._current_kind = kind
        self._form_data = {
            "apiVersion": resource["apiVersion"],
            "kind": kind,
        }

        self.query_one("#resource-header", Static).update(
            f"{kind}  ({resource['apiVersion']})"
        )

        namespaces = getattr(self.app, "_cached_namespaces", None)
        widgets, shown = build_schema_form(kind, namespaces)
        self._shown_paths = shown

        form_scroll = self.query_one("#form-scroll", VerticalScroll)

        # Await removal then mount — prevents DuplicateIds from same-name
        # field widgets (e.g. sf_metadata__name) appearing on multiple resources.
        async def _reload() -> None:
            await form_scroll.remove_children()
            form_scroll.mount(*widgets)
            # Store reference to the advanced container after it's mounted
            containers = list(form_scroll.query(".schema-advanced-fields"))
            self._advanced_container = containers[-1] if containers else None

        self.app.call_after_refresh(_reload)

    def _reset_form(self) -> None:
        self._current_kind = None
        self._form_data = {}
        self._shown_paths = set()
        self.query_one("#resource-header", Static).update("← Select a resource to begin")
        form_scroll = self.query_one("#form-scroll", VerticalScroll)
        form_scroll.remove_children()
        form_scroll.mount(
            Static("Select a resource from the sidebar.", classes="placeholder-text")
        )

    # ------------------------------------------------------------------
    # Field picker — "Add more fields" button
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class("schema-add-fields-btn"):
            event.stop()
            self._open_field_picker()
        elif event.button.id == "btn-preview":
            self.action_preview_yaml()
        elif event.button.id == "btn-save":
            self.action_save_yaml()

    def _open_field_picker(self) -> None:
        if not self._current_kind:
            return
        resource = get_resource(self._current_kind)
        if resource is None:
            return

        def _on_picked(paths: list[str]) -> None:
            if not paths or self._advanced_container is None:
                return
            new_paths = [p for p in paths if p not in self._shown_paths]
            if not new_paths:
                return
                
            namespaces = getattr(self.app, "_cached_namespaces", None)
            try:
                merge_paths_into_form(
                    new_paths,
                    self,
                    resource["fields"],
                    namespaces,
                    self._advanced_container
                )
                self._shown_paths.update(new_paths)
            except Exception as e:
                self.app.notify(f"Failed to merge fields: {e}", severity="error")

        self.app.push_screen(
            FieldPickerScreen(
                kind=self._current_kind,
                fields=resource["fields"],
                already_added=self._shown_paths,
            ),
            _on_picked,
        )

    # ------------------------------------------------------------------
    # Form state: read widget values into _form_data
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        wid = event.input.id or ""
        path = decode_path(wid)
        if path:
            _set_nested(self._form_data, path, event.value)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        wid = event.switch.id or ""
        path = decode_path(wid)
        if path:
            _set_nested(self._form_data, path, event.value)

    def on_select_changed(self, event: Select.Changed) -> None:
        wid = event.select.id or ""
        path = decode_path(wid)
        if path:
            val = event.value if event.value is not Select.BLANK else None
            _set_nested(self._form_data, path, val)

    def on_map_editor_changed(self, event: MapEditor.Changed) -> None:
        wid = event.map_editor.id or ""
        path = decode_path(wid)
        if path:
            _set_nested(self._form_data, path, event.data)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_preview_yaml(self) -> None:
        if not self._current_kind:
            self.app.notify("No resource selected.", severity="warning")
            return
        yaml_str = self._generate_yaml()
        name = _get_nested(self._form_data, ["metadata", "name"]) or "app"
        filename = f"{name}-{self._current_kind.lower()}.yaml"
        self.app.push_screen(YAMLPreviewScreen(yaml_str, filename))

    def action_save_yaml(self) -> None:
        if not self._current_kind:
            self.app.notify("No resource selected.", severity="warning")
            return
        yaml_str = self._generate_yaml()
        name = _get_nested(self._form_data, ["metadata", "name"]) or "app"
        filename = f"{name}-{self._current_kind.lower()}.yaml"
        self.app.push_screen(YAMLPreviewScreen(yaml_str, filename))

    def _generate_yaml(self) -> str:
        try:
            return emit_yaml_from_dict(self._form_data)
        except Exception as exc:
            return f"# Error generating YAML:\n# {exc}"
