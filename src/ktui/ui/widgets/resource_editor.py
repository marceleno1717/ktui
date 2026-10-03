"""ResourceEditor — one self-contained resource form (toolbar + fields + state).

Each open tab in ``MainScreen`` hosts exactly one ``ResourceEditor``. All form
state (``_form_data``, shown paths, validation highlights) lives here, and every
DOM lookup is scoped to ``self`` so identical field IDs in other tabs never
collide.
"""

from __future__ import annotations

import re
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Select, Static, Switch

from ktui.schema.emitter import emit_yaml_from_dict
from ktui.schema.loader import get_resource
from ktui.ui.engine.schema_form_builder import (
    build_schema_form,
    decode_path,
    merge_paths_into_form,
)
from ktui.ui.engine.state import get_nested as _get_nested
from ktui.ui.engine.state import set_nested as _set_nested_raw
from ktui.ui.screens.field_picker import FieldPickerScreen
from ktui.ui.screens.yaml_preview import YAMLPreviewScreen
from ktui.ui.widgets.map_editor import MapEditor


def _set_nested(data: dict, path: list[str], value: Any) -> None:
    """Thin wrapper: delegates to state.set_nested (handles [N] bracket paths)."""
    _set_nested_raw(data, path, value)


def _normalize(value: Any) -> Any:
    """Canonical form used for unsaved-change detection.

    Drops empty values (like the YAML emitter does) and stringifies scalars, so
    ``replicas: 2`` loaded from a file equals ``"2"`` read back from an Input.
    """
    if isinstance(value, dict):
        out = {k: _normalize(v) for k, v in value.items()}
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        out_list = [_normalize(v) for v in value]
        return [v for v in out_list if v not in (None, "", [], {})]
    if value is None:
        return None
    return str(value)


class ResourceEditor(Vertical):
    """Schema-driven form for a single Kubernetes resource."""

    DEFAULT_CSS = """
    ResourceEditor {
        height: 1fr;
    }

    ResourceEditor #resource-header {
        height: 3;
        background: $surface-lighten-1;
        padding: 1 2;
        text-style: bold;
    }

    ResourceEditor #form-scroll {
        height: 1fr;
        padding: 1 2;
    }

    ResourceEditor .field-label {
        color: $text-muted;
        margin-bottom: 0;
    }

    ResourceEditor .readonly-value {
        color: $warning;
        padding: 0 1;
    }

    ResourceEditor .form-input {
        height: auto;
    }

    ResourceEditor .schema-add-fields-btn {
        margin: 1 0;
    }

    ResourceEditor .schema-advanced-fields {
        height: auto;
    }
    """

    class TitleChanged(Message):
        """Posted when the tab label should change (name edited or dirty state flipped)."""

        def __init__(self, editor: ResourceEditor, title: str) -> None:
            self.editor = editor
            self.title = title
            super().__init__()

    def __init__(
        self,
        kind: str,
        initial_data: dict[str, Any] | None = None,
        default_title: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.kind = kind
        self.default_title = default_title or kind
        self._initial_data = initial_data
        self._current_kind: str | None = None
        self._form_data: dict[str, Any] = {}
        self._shown_paths: set[str] = set()
        self._advanced_container = None
        self._baseline: Any = {}
        self._last_dirty = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="toolbar"):
            yield Static("Loading…", id="resource-header")
            yield Button("Validate  \\[ctrl+v]", id="btn-validate")
            yield Button("Preview YAML  \\[p]", id="btn-preview", variant="primary")
            yield Button("Save  \\[ctrl+s]", id="btn-save", variant="success")
        yield VerticalScroll(id="form-scroll")

    def on_mount(self) -> None:
        self._load_resource(self.kind, self._initial_data)
        self._initial_data = None

    @property
    def tab_title(self) -> str:
        """Display title for the hosting tab."""
        name = _get_nested(self._form_data, ["metadata", "name"])
        return f"{self.kind}: {name}" if name else self.default_title

    # ------------------------------------------------------------------
    # Unsaved-change tracking
    # ------------------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        """True if the form differs from what was loaded / last saved."""
        return _normalize(self._form_data) != self._baseline

    def mark_clean(self) -> None:
        """Treat the current form contents as saved."""
        self._baseline = _normalize(self._form_data)
        self._refresh_dirty(force=True)

    def _refresh_dirty(self, force: bool = False) -> None:
        """Notify the tab only when the dirty state actually flips (cheap per keystroke)."""
        dirty = self.is_dirty
        if force or dirty != self._last_dirty:
            self._last_dirty = dirty
            self.post_message(self.TitleChanged(self, self.tab_title))

    # ------------------------------------------------------------------
    # Form loading
    # ------------------------------------------------------------------

    def _load_resource(self, kind: str, initial_data: dict[str, Any] | None = None) -> None:
        resource = get_resource(kind)
        if resource is None:
            self.query_one("#resource-header", Static).update(f"Unknown resource: {kind}")
            return

        self._current_kind = kind
        self._form_data = {
            "apiVersion": resource["apiVersion"],
            "kind": kind,
        }
        # Baseline = what the user sees right after loading. Computed from the
        # source data (not from widgets) so async widget population can't race it.
        self._baseline = _normalize({**self._form_data, **(initial_data or {})})

        self.query_one("#resource-header", Static).update(
            f"{kind}  ({resource['apiVersion']})"
        )

        namespaces = getattr(self.app, "_cached_namespaces", None)

        extra_paths = None
        raw_paths = None
        if initial_data:
            from ktui.schema.loader import resolve_field_path

            def extract_paths_schema(d: dict, current_schema_path: str = "", current_raw_path: str = "") -> list[str]:
                paths = []
                for k, v in d.items():
                    if not current_raw_path and k in ("apiVersion", "kind"):
                        continue

                    next_raw_path = f"{current_raw_path}.{k}" if current_raw_path else k
                    next_schema_path = f"{current_schema_path}.{k}" if current_schema_path else k

                    lookup_path = next_schema_path.replace("[]", "")
                    schema_node = resolve_field_path(resource["fields"], lookup_path)

                    if schema_node is None:
                        continue

                    ftype = schema_node.get("type", "")
                    if schema_node.get("fields") and isinstance(v, dict):
                        paths.extend(extract_paths_schema(v, next_schema_path, next_raw_path))
                    elif (ftype.startswith("[]") or ftype == "array") and isinstance(v, list):
                        item_schema_path = next_schema_path + "[]"
                        for i, item in enumerate(v):
                            item_raw_path = f"{next_raw_path}[{i}]"

                            item_node = resolve_field_path(resource["fields"], item_schema_path.replace("[]", ""))
                            if item_node and item_node.get("fields") and isinstance(item, dict):
                                paths.extend(extract_paths_schema(item, item_schema_path, item_raw_path))
                            else:
                                paths.append(item_raw_path)
                    else:
                        paths.append(next_raw_path)
                return paths

            raw_paths = extract_paths_schema(initial_data)
            extra_paths = [re.sub(r"\[\d+\]", "[]", p) for p in raw_paths]

        widgets, shown = build_schema_form(kind, namespaces, extra_paths)
        self._shown_paths = shown

        form_scroll = self.query_one("#form-scroll", VerticalScroll)

        # Await removal then mount — prevents DuplicateIds from same-name
        # field widgets (e.g. sf_metadata__name) appearing on multiple resources.
        async def _reload() -> None:
            await form_scroll.remove_children()
            await form_scroll.mount(*widgets)
            # Store reference to the advanced container after it's mounted
            containers = list(form_scroll.query(".schema-advanced-fields"))
            self._advanced_container = containers[-1] if containers else None

            if initial_data and raw_paths:
                self._populate_initial_data(initial_data, raw_paths)

        self.app.call_after_refresh(_reload)

    def _populate_initial_data(self, data: dict[str, Any], raw_paths: list[str]) -> None:
        def populate() -> None:
            from ktui.ui.engine.schema_form_builder import ArrayGroup, encode_path

            # Ensure array groups have correct number of items
            for p in raw_paths:
                for match in re.finditer(r"\[(\d+)\]", p):
                    idx = int(match.group(1))
                    arr_path_str = p[:match.end()]
                    base_arr_path = re.sub(r"\[\d+\]", "[]", arr_path_str)

                    # Find ArrayGroup with matching full path
                    for ag in self.query(ArrayGroup):
                        if getattr(ag, "_full_path", "") == base_arr_path:
                            while ag._count <= idx:
                                ag.action_add_item()

            # Wait one more refresh for array items to mount
            def set_values() -> None:
                for p in raw_paths:
                    wid = encode_path(p)
                    val = data
                    for part in re.split(r"\.|\[|\]", p):
                        if not part:
                            continue
                        if isinstance(val, list):
                            val = val[int(part)]
                        elif isinstance(val, dict):
                            val = val.get(part)
                        if val is None:
                            break

                    if val is not None:
                        try:
                            widget = self.query_one(f"#{wid}")
                            if isinstance(widget, Input):
                                widget.value = str(val)
                            elif isinstance(widget, Switch):
                                widget.value = bool(val)
                            elif hasattr(widget, "data") and isinstance(val, dict):
                                widget.data = val
                        except Exception:
                            pass
                # Update underlying form data
                self._form_data.update(data)
                self._refresh_dirty(force=True)

            self.app.call_after_refresh(set_values)

        self.app.call_after_refresh(populate)

    # ------------------------------------------------------------------
    # Field picker — "Add more fields" button
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class("schema-add-fields-btn"):
            event.stop()
            self._open_field_picker()
        elif event.button.id == "btn-validate":
            event.stop()
            self.action_validate_form()
        elif event.button.id == "btn-preview":
            event.stop()
            self.action_preview_yaml()
        elif event.button.id == "btn-save":
            event.stop()
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
            self._refresh_dirty(force=list(path) == ["metadata", "name"])

    def on_switch_changed(self, event: Switch.Changed) -> None:
        wid = event.switch.id or ""
        path = decode_path(wid)
        if path:
            _set_nested(self._form_data, path, event.value)
            self._refresh_dirty()

    def on_select_changed(self, event: Select.Changed) -> None:
        wid = event.select.id or ""
        path = decode_path(wid)
        if path:
            val = event.value if event.value is not Select.BLANK else None
            _set_nested(self._form_data, path, val)
            self._refresh_dirty()

    def on_map_editor_changed(self, event: MapEditor.Changed) -> None:
        wid = event.map_editor.id or ""
        path = decode_path(wid)
        if path:
            _set_nested(self._form_data, path, event.data)
            self._refresh_dirty()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_validate_form(self) -> None:
        if not self._current_kind:
            return
        errors = self._validate_form()
        if errors:
            self.app.notify(f"Validation failed ({len(errors)} errors). Check highlighted fields.", title="Validation", severity="error", timeout=4.0)
        else:
            self.app.notify("All fields are valid!", title="Validation", severity="information", timeout=3.0)

    def _validate_form(self) -> list[str]:
        errors: list[str] = []
        invalid_widget_ids: list[str] = []

        # Clear existing highlights in one batch pass
        for w in self.query(".invalid-field"):
            w.remove_class("invalid-field")

        # --- Pydantic validation (for kinds with models) ---
        from ktui.registry import CATALOG
        from ktui.ui.engine.schema_form_builder import encode_path
        model_cls = CATALOG.get_model(self._current_kind)

        if model_cls:
            try:
                from ktui.schema.emitter import _clean
                model_cls(**_clean(self._form_data))
            except Exception as e:
                from pydantic import ValidationError
                if isinstance(e, ValidationError):
                    for err in e.errors():
                        path_parts = err["loc"]
                        path_str = ""
                        for p in path_parts:
                            if isinstance(p, int):
                                path_str += f"[{p}]"
                            else:
                                path_str = f"{path_str}.{p}" if path_str else str(p)
                        errors.append(f"{path_str}: {err['msg']}")
                        invalid_widget_ids.append(encode_path(path_str))
                else:
                    errors.append(str(e))

        # --- Schema required-field check ---
        res = get_resource(self._current_kind)
        if res:
            def check_required(
                data: dict, schema_fields: dict, current_path: str = ""
            ) -> list[str]:
                req_errors = []
                for k, v in schema_fields.items():
                    node_path = f"{current_path}.{k}" if current_path else k
                    val = data.get(k)
                    is_empty = val is None or val == "" or val == [] or val == {}
                    if v.get("required") and is_empty:
                        req_errors.append(node_path)
                    elif val is not None and not is_empty:
                        if v.get("fields") and isinstance(val, dict):
                            req_errors.extend(check_required(val, v["fields"], node_path))
                        elif (
                            v.get("type", "").startswith("[]") or v.get("type", "") == "array"
                        ) and isinstance(val, list):
                            item_schema = v.get("fields", {})
                            if item_schema:
                                for i, item in enumerate(val):
                                    if isinstance(item, dict):
                                        req_errors.extend(
                                            check_required(item, item_schema, f"{node_path}[{i}]")
                                        )
                return req_errors

            for rp in check_required(self._form_data, res.get("fields", {})):
                errors.append(f"{rp}: Field is required.")
                invalid_widget_ids.append(encode_path(rp))

        # --- Batch highlight ---
        for wid in invalid_widget_ids:
            try:
                widget = self.query_one(f"#{wid}")
                target = widget.parent if (widget.parent and widget.parent.has_class("form-field")) else widget
                target.add_class("invalid-field")
            except Exception:
                pass

        return errors

    def action_preview_yaml(self) -> None:
        if not self._current_kind:
            self.app.notify("No resource selected.", severity="warning")
            return
        errors = self._validate_form()
        if errors:
            self.app.notify("Cannot preview: Validation failed. Check highlighted fields.", severity="error", timeout=4.0)
            return
        yaml_str = self._generate_yaml()
        name = _get_nested(self._form_data, ["metadata", "name"]) or "app"
        filename = f"{name}-{self._current_kind.lower()}.yaml"
        self.app.push_screen(YAMLPreviewScreen(yaml_str, filename), self._on_preview_closed)

    def action_save_yaml(self) -> None:
        if not self._current_kind:
            self.app.notify("No resource selected.", severity="warning")
            return
        errors = self._validate_form()
        if errors:
            self.app.notify("Cannot save: Validation failed. Check highlighted fields.", severity="error", timeout=4.0)
            return
        yaml_str = self._generate_yaml()
        name = _get_nested(self._form_data, ["metadata", "name"]) or "app"
        filename = f"{name}-{self._current_kind.lower()}.yaml"
        self.app.push_screen(YAMLPreviewScreen(yaml_str, filename), self._on_preview_closed)

    def _generate_yaml(self) -> str:
        try:
            return emit_yaml_from_dict(self._form_data)
        except Exception as exc:
            return f"# Error generating YAML:\n# {exc}"

    def _on_preview_closed(self, saved: bool | None) -> None:
        """YAMLPreviewScreen dismisses with True after writing the file."""
        if saved:
            self.mark_clean()
