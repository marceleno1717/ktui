"""Form builder engine — converts Pydantic models into Textual widget trees.

The engine is the bridge between the model layer and the UI layer.
It knows nothing about YAML generation and nothing about specific resources.
It only knows how to map Pydantic field types to the right Textual widget.

Widget ID encoding
------------------
Every interactive widget gets an ID that encodes its full field path:

    ``f--<segment>--<segment>--...``

Example: ``f--metadata--name`` → field at path ["metadata", "name"]
         ``f--spec--containers--0--image`` → containers[0].image

These IDs are parsed by ``MainScreen`` to update ``_form_data`` on every
widget change event.  ``MapEditor`` and ``ListEditor`` stop bubbling and
post their own ``Changed`` messages instead.
"""

from __future__ import annotations

import types
import typing
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from textual.widgets import (
    Collapsible,
    Input,
    Label,
    Select,
    Static,
    Switch,
)
from textual.containers import Vertical

FIELD_ID_PREFIX = "f"
FIELD_ID_SEP = "--"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def make_field_id(path: list[str]) -> str:
    """Encode a field path as a Textual widget ID."""
    return FIELD_ID_PREFIX + FIELD_ID_SEP + FIELD_ID_SEP.join(path)


def parse_field_id(widget_id: str) -> list[str] | None:
    """Decode a widget ID back to a field path.  Returns ``None`` if not a form ID."""
    prefix = FIELD_ID_PREFIX + FIELD_ID_SEP
    if not widget_id.startswith(prefix):
        return None
    return widget_id[len(prefix):].split(FIELD_ID_SEP)


def initialize_form_data(model_class: type[BaseModel]) -> dict:
    """Pre-populate form data with locked Literal defaults (apiVersion, kind, etc.)."""
    data: dict = {}
    for field_name, field_info in model_class.model_fields.items():
        annotation = field_info.annotation
        inner, _ = _unwrap_optional(annotation)
        literals = _get_literal_values(inner)
        if literals and len(literals) == 1:
            data[field_name] = literals[0]
    return data


def build_form_widgets(
    model_class: type[BaseModel],
    path: list[str] | None = None,
) -> list:
    """Return a list of Textual widgets representing all fields of ``model_class``.

    ``path`` is the current path prefix used to generate widget IDs.
    Callers at the top level omit it (defaults to ``[]``).
    """
    if path is None:
        path = []

    widgets = []
    for field_name, field_info in model_class.model_fields.items():
        annotation = field_info.annotation
        inner_type, is_optional = _unwrap_optional(annotation)
        field_path = path + [field_name]
        widget = _build_field_widget(
            field_name=field_name,
            field_type=inner_type,
            field_info=field_info,
            field_path=field_path,
            is_optional=is_optional,
        )
        if widget is not None:
            widgets.append(widget)
    return widgets


# ---------------------------------------------------------------------------
# Type inspection helpers
# ---------------------------------------------------------------------------


def _unwrap_optional(tp: Any) -> tuple[Any, bool]:
    """Unwrap ``Optional[X]`` (``X | None``) → ``(X, True)``.

    Returns ``(tp, False)`` if not optional.
    """
    origin = typing.get_origin(tp)
    if origin is types.UnionType or origin is typing.Union:
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0], True
    return tp, False


def _get_literal_values(tp: Any) -> list[Any] | None:
    """Return ``[v1, v2, ...]`` if ``tp`` is ``Literal[v1, v2, ...]``, else ``None``."""
    if typing.get_origin(tp) is typing.Literal:
        return list(typing.get_args(tp))
    return None


def _is_basemodel(tp: Any) -> bool:
    try:
        return isinstance(tp, type) and issubclass(tp, BaseModel)
    except TypeError:
        return False


def _get_default(field_info: FieldInfo) -> Any:
    if field_info.default is not PydanticUndefined:
        return field_info.default
    if field_info.default_factory is not None:
        return field_info.default_factory()
    return None


# ---------------------------------------------------------------------------
# Widget builders
# ---------------------------------------------------------------------------


def _build_field_widget(
    field_name: str,
    field_type: Any,
    field_info: FieldInfo,
    field_path: list[str],
    is_optional: bool,
) -> Any:
    from ktui.ui.widgets.map_editor import MapEditor
    from ktui.ui.widgets.list_editor import ListEditor

    widget_id = make_field_id(field_path)
    description = field_info.description or ""
    label_suffix = " (optional)" if is_optional else ""
    label_text = f"{field_name}{label_suffix}"
    default = _get_default(field_info)

    # --- 1. Literal[single_value] → read-only Static (apiVersion / kind) ---
    literals = _get_literal_values(field_type)
    if literals and len(literals) == 1:
        return Vertical(
            Label(f"{field_name}:"),
            Static(str(literals[0]), classes="readonly-value"),
            classes="form-field",
        )

    # --- 2. Literal[v1, v2, ...] → Select ---
    if literals:
        options = [(str(v), str(v)) for v in literals]
        init_value = str(default) if default is not None else str(literals[0])
        desc_widget = Static(description, classes="field-description") if description else Static("")
        return Vertical(
            Label(f"{label_text}:"),
            Select(options=options, value=init_value, id=widget_id, classes="form-input"),
            desc_widget,
            classes="form-field",
        )

    # --- 3. bool → Switch ---
    if field_type is bool:
        init = bool(default) if default is not None else False
        desc_widget = Static(description, classes="field-description") if description else Static("")
        return Vertical(
            Label(f"{label_text}:"),
            Switch(value=init, id=widget_id, classes="form-input"),
            desc_widget,
            classes="form-field",
        )

    # --- 4. int → Input (integer type) ---
    if field_type is int:
        init = str(default) if default is not None else ""
        desc_widget = Static(description, classes="field-description") if description else Static("")
        return Vertical(
            Label(f"{label_text}:"),
            Input(value=init, id=widget_id, type="integer", classes="form-input"),
            desc_widget,
            classes="form-field",
        )

    # --- 5. str → Input ---
    if field_type is str:
        init = str(default) if default not in (None, "") else ""
        desc_widget = Static(description, classes="field-description") if description else Static("")
        return Vertical(
            Label(f"{label_text}:"),
            Input(value=init, placeholder=field_name, id=widget_id, classes="form-input"),
            desc_widget,
            classes="form-field",
        )

    # --- 6. dict[str, str] → MapEditor ---
    origin = typing.get_origin(field_type)
    if origin is dict:
        desc_widget = Static(description, classes="field-description") if description else Static("")
        return Vertical(
            Label(f"{label_text}:"),
            MapEditor(id=widget_id, classes="form-input"),
            desc_widget,
            classes="form-field",
        )

    # --- 7. list[BaseModel] → ListEditor ---
    if origin is list:
        args = typing.get_args(field_type)
        if args and _is_basemodel(args[0]):
            desc_widget = Static(description, classes="field-description") if description else Static("")
            return Vertical(
                Label(f"{label_text}:"),
                ListEditor(item_model=args[0], field_path=field_path, id=widget_id, classes="form-input"),
                desc_widget,
                classes="form-field",
            )
        # list[str] — comma-separated for now
        desc_widget = Static(description, classes="field-description") if description else Static("")
        return Vertical(
            Label(f"{label_text}: (comma-separated)"),
            Input(id=widget_id, classes="form-input"),
            desc_widget,
            classes="form-field",
        )

    # --- 8. Nested BaseModel → Collapsible section ---
    if _is_basemodel(field_type):
        child_widgets = build_form_widgets(field_type, path=field_path)
        return Collapsible(
            *child_widgets,
            title=field_name,
            collapsed=False,
            classes="form-section",
        )

    # --- Fallback: string input ---
    desc_widget = Static(description, classes="field-description") if description else Static("")
    return Vertical(
        Label(f"{label_text}:"),
        Input(id=widget_id, placeholder=field_name, classes="form-input"),
        desc_widget,
        classes="form-field",
    )
