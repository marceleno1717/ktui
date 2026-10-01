"""MapEditor — widget for editing dict[str, str] fields.

Renders as a list of key/value Input rows with Add/Remove buttons.
Stops all child widget events from bubbling and instead posts
``MapEditor.Changed`` with the complete current dict.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label


class MapEditor(Widget):
    """Editable key-value map widget.

    Posts ``MapEditor.Changed`` whenever any row key or value changes.
    """

    DEFAULT_CSS = """
    MapEditor {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin-bottom: 2;
    }
    MapEditor #map-rows {
        height: auto;
    }
    MapEditor .map-row {
        height: auto;
        margin-bottom: 0;
    }
    MapEditor .map-key {
        width: 1fr;
    }
    MapEditor .map-value {
        width: 1fr;
    }
    MapEditor .map-remove-btn {
        width: 5;
        min-width: 5;
    }
    MapEditor #map-add-btn {
        margin: 0 0 1 0;
        width: auto;
    }
    MapEditor #map-empty-hint {
        color: $text-muted;
        margin: 1 0;
    }
    """

    class Changed(Message):
        """Posted whenever the map data changes."""

        def __init__(self, map_editor: "MapEditor", data: dict[str, str]) -> None:
            self.map_editor = map_editor
            self.data = data
            super().__init__()

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._next_id: int = 0
        self._active_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        yield Label(self.name or "Map", classes="text-bold")
        yield Label("(no entries)", id="map-empty-hint")
        with Vertical(id="map-rows"):
            pass
        with Horizontal(id="map-controls", classes="map-row"):
            yield Button("+ Add Entry", id="map-add-btn", variant="default")
            yield Button("Import from cluster", id="map-import-btn", variant="success")

    # ------------------------------------------------------------------
    # Event handlers — stop all bubbling so MainScreen isn't triggered
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        btn_id = event.button.id or ""
        if btn_id == "map-add-btn":
            self._add_row()
        elif btn_id == "map-import-btn":
            self._open_import_modal()
        elif btn_id.startswith("map-remove-"):
            idx = int(btn_id.split("-")[-1])
            self._remove_row(idx)

    def _open_import_modal(self) -> None:
        from ktui.ui.screens.cluster_import import ClusterImportScreen

        # Infer context from MapEditor's parent/field
        target = "labels"
        if "selector" in (self.id or "").lower():
            target = "selector"

        def _on_import(data: dict[str, str]) -> None:
            if not data:
                return
            for key, val in data.items():
                self._add_row(key, val)
            self._emit_changed()
            
        self.app.push_screen(ClusterImportScreen(target_property=target), _on_import)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self._emit_changed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_row(self, initial_key: str = "", initial_val: str = "") -> None:
        idx = self._next_id
        self._next_id += 1
        self._active_ids.add(idx)

        row = Horizontal(
            Input(value=initial_key, placeholder="key", id=f"map-key-{idx}", classes="map-key"),
            Input(value=initial_val, placeholder="value", id=f"map-val-{idx}", classes="map-value"),
            Button("✕", id=f"map-remove-{idx}", classes="map-remove-btn"),
            classes="map-row",
            id=f"map-row-{idx}",
        )
        # Hide the empty hint
        try:
            self.query_one("#map-empty-hint").display = False
        except Exception:
            pass

        rows = self.query_one("#map-rows")
        rows.mount(row)

    def _remove_row(self, idx: int) -> None:
        self._active_ids.discard(idx)
        try:
            self.query_one(f"#map-row-{idx}").remove()
        except Exception:
            pass
        if not self._active_ids:
            try:
                self.query_one("#map-empty-hint").display = True
            except Exception:
                pass
        self._emit_changed()

    def _emit_changed(self) -> None:
        data: dict[str, str] = {}
        for idx in self._active_ids:
            try:
                key = self.query_one(f"#map-key-{idx}", Input).value.strip()
                val = self.query_one(f"#map-val-{idx}", Input).value
                if key:
                    data[key] = val
            except Exception:
                pass
        self.post_message(self.Changed(self, data))

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_data(self) -> dict[str, str]:
        """Return current map data (snapshot)."""
        data: dict[str, str] = {}
        for idx in self._active_ids:
            try:
                key = self.query_one(f"#map-key-{idx}", Input).value.strip()
                val = self.query_one(f"#map-val-{idx}", Input).value
                if key:
                    data[key] = val
            except Exception:
                pass
        return data
