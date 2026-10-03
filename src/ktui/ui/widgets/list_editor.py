"""ListEditor — widget for editing list[BaseModel] fields.

Renders each item as a numbered Collapsible containing a generated form.
Stops child widget events from bubbling and instead posts
``ListEditor.Changed`` with the complete current list of dicts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Input, Label, Select, Switch

from ktui.ui.engine.state import set_nested


class ListEditor(Widget):
    """Editable list of ``BaseModel`` instances.

    Posts ``ListEditor.Changed`` whenever any field inside any item changes.
    All child Input / Switch / Select events are stopped here and do not
    bubble to the parent screen.
    """

    DEFAULT_CSS = """
    ListEditor {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin-bottom: 2;
    }
    ListEditor #list-add-btn {
        margin: 1 0;
        width: auto;
    }
    ListEditor #list-empty-hint {
        color: $text-muted;
        margin: 1 0;
    }
    ListEditor .item-header {
        height: auto;
    }
    ListEditor .item-remove-btn {
        width: auto;
        margin-left: 1;
    }
    """

    class Changed(Message):
        """Posted whenever the list data changes."""

        def __init__(self, list_editor: ListEditor, data: list[dict]) -> None:
            self.list_editor = list_editor
            self.data = data
            super().__init__()

    def __init__(
        self,
        item_model: type[BaseModel],
        field_path: list[str],
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._item_model = item_model
        self._field_path = field_path
        self._next_id: int = 0
        self._active_ids: list[int] = []  # ordered list of active item IDs
        # Per-item state dict: item_id → dict
        self._item_data: dict[int, dict] = {}

    def compose(self) -> ComposeResult:
        yield Label(
            f"No {self._item_model.__name__} items.",
            id="list-empty-hint",
        )
        yield Button(
            f"+ Add {self._item_model.__name__}",
            id="list-add-btn",
            variant="primary",
        )

    # ------------------------------------------------------------------
    # Event handlers — intercept and stop bubbling
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        btn_id = event.button.id or ""
        if btn_id == "list-add-btn":
            self._add_item()
        elif btn_id.startswith("list-remove-"):
            item_id = int(btn_id.split("-")[-1])
            self._remove_item(item_id)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self._sync_from_widget(event.input.id, event.value)

    def on_switch_changed(self, event: Switch.Changed) -> None:
        event.stop()
        self._sync_from_widget(event.switch.id, event.value)

    def on_select_changed(self, event: Select.Changed) -> None:
        event.stop()
        val = event.value if event.value is not Select.BLANK else None
        self._sync_from_widget(event.select.id, val)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_item(self) -> None:
        from textual.containers import Vertical as _V
        from textual.widgets import Input as _I
        from textual.widgets import Label as _L

        from ktui.ui.engine.schema_form_builder import encode_path

        item_id = self._next_id
        self._next_id += 1
        self._active_ids.append(item_id)
        self._item_data[item_id] = {}

        item_idx = len(self._active_ids) - 1
        item_path = self._field_path + [str(item_idx)]

        # Build widgets directly from the Pydantic model fields
        child_widgets = []
        for field_name, field_info in self._item_model.model_fields.items():
            path_str = ".".join(item_path + [field_name])
            wid = encode_path(path_str)
            label_text = field_name
            child_widgets.append(
                _V(
                    _L(label_text, classes="field-label"),
                    _I(id=wid, placeholder=label_text, classes="form-input"),
                    classes="form-field",
                )
            )

        collapsible = Collapsible(
            *child_widgets,
            Horizontal(
                Button(
                    "Remove",
                    id=f"list-remove-{item_id}",
                    variant="error",
                    classes="item-remove-btn",
                ),
                classes="item-header",
            ),
            title=f"{self._item_model.__name__} #{len(self._active_ids)}",
            collapsed=False,
            id=f"list-item-{item_id}",
        )

        try:
            self.query_one("#list-empty-hint").display = False
        except Exception:
            pass

        add_btn = self.query_one("#list-add-btn")
        self.mount(collapsible, before=add_btn)

    def _remove_item(self, item_id: int) -> None:
        if item_id in self._active_ids:
            self._active_ids.remove(item_id)
        self._item_data.pop(item_id, None)
        try:
            self.query_one(f"#list-item-{item_id}").remove()
        except Exception:
            pass
        if not self._active_ids:
            try:
                self.query_one("#list-empty-hint").display = True
            except Exception:
                pass
        self._emit_changed()

    def _sync_from_widget(self, widget_id: str | None, value: Any) -> None:
        """Parse widget ID to determine which item and field it belongs to,
        then update that item's data dict."""
        if not widget_id:
            return

        from ktui.ui.engine.schema_form_builder import decode_path

        path = decode_path(widget_id)
        if path is None:
            return

        # path like: ["spec", "containers", "0", "name"]
        # self._field_path like: ["spec", "containers"]
        prefix_len = len(self._field_path)
        if len(path) <= prefix_len:
            return

        # path[prefix_len] is the list index relative to the *original* item_path
        # but we track by item_id, not by position. We need to map position → item_id.
        position_str = path[prefix_len]
        if not position_str.isdigit():
            return
        position = int(position_str)
        if position >= len(self._active_ids):
            return
        item_id = self._active_ids[position]

        relative_path = path[prefix_len + 1:]  # field path within the item
        if not relative_path:
            return

        set_nested(self._item_data[item_id], relative_path, value)
        self._emit_changed()

    def _emit_changed(self) -> None:
        if getattr(self, "_debounce_timer", None) is not None:
            self._debounce_timer.stop()
        self._debounce_timer = self.set_timer(0.15, self._do_emit)

    def _do_emit(self) -> None:
        data = [self._item_data.get(iid, {}) for iid in self._active_ids]
        self.post_message(self.Changed(self, data))

    def get_data(self) -> list[dict]:
        """Return current list data (snapshot)."""
        return [self._item_data.get(iid, {}) for iid in self._active_ids]
