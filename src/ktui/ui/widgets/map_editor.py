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
        height: 3;
        margin-bottom: 1;
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

        def __init__(self, map_editor: MapEditor, data: dict[str, str]) -> None:
            self.map_editor = map_editor
            self.data = data
            super().__init__()

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._next_id: int = 0
        # Store references to widgets (idx -> (key_input, val_input, row_container))
        # This completely avoids DOM queries and race conditions during mount.
        self._row_refs: dict[int, tuple[Input, Input, Horizontal]] = {}

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
        elif "-remove-" in btn_id:
            try:
                idx = int(btn_id.rsplit("-", 1)[-1])
                self._remove_row(idx)
                self._emit_changed()
            except (ValueError, IndexError):
                pass

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
        if getattr(self, "_debounce_timer", None) is not None:
            self._debounce_timer.stop()
        self._debounce_timer = self.set_timer(0.15, self._emit_changed)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_row(self, initial_key: str = "", initial_val: str = "") -> None:
        idx = self._next_id
        self._next_id += 1
        
        prefix = self.id or f"map_{id(self)}"

        key_input = Input(value=initial_key, placeholder="key", id=f"{prefix}-key-{idx}", classes="map-key")
        val_input = Input(value=initial_val, placeholder="value", id=f"{prefix}-val-{idx}", classes="map-value")
        row = Horizontal(
            key_input,
            val_input,
            Button("✕", id=f"{prefix}-remove-{idx}", classes="map-remove-btn"),
            classes="map-row",
            id=f"{prefix}-row-{idx}",
        )
        
        # Save refs directly
        self._row_refs[idx] = (key_input, val_input, row)

        try:
            self.query_one("#map-empty-hint").display = False
        except Exception:
            pass

        try:
            rows = self.query_one("#map-rows")
            rows.mount(row)
        except Exception:
            pass

    def _remove_row(self, idx: int) -> None:
        if idx in self._row_refs:
            _, _, row = self._row_refs.pop(idx)
            try:
                row.remove()
            except Exception:
                pass
                
        if not self._row_refs:
            try:
                self.query_one("#map-empty-hint").display = True
            except Exception:
                pass

    def _emit_changed(self) -> None:
        data = self.data
        self.post_message(self.Changed(self, data))

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def data(self) -> dict[str, str]:
        """Return current map data (snapshot)."""
        data: dict[str, str] = {}
        for key_in, val_in, _ in self._row_refs.values():
            k = key_in.value.strip()
            if k:
                data[k] = val_in.value
        return data

    @data.setter
    def data(self, new_data: dict[str, str]) -> None:
        """Clear existing and set new data."""
        for idx in list(self._row_refs.keys()):
            self._remove_row(idx)
            
        for k, v in new_data.items():
            self._add_row(str(k), str(v))
        
        # Do not emit changed here: avoid infinite loops and 
        # race conditions when the form is initially loading.
