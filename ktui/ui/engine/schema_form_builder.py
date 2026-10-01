"""Schema-driven form builder.

Builds Textual widgets from a k8s schema field path list.
Common fields are shown immediately; advanced fields are added
via the FieldPickerScreen popup.

Each widget stores its dotted path as widget ID in the format:
  f__metadata.name   (prefix f__ then dotted path, dots replaced by ·)

The host screen reads values back via on_input_changed etc.
"""

from __future__ import annotations

import re
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static, Switch

from ktui.schema.loader import get_common_fields, get_resource, resolve_field_path

# Widget ID prefix / separator
_PREFIX = "sf"    # schema field
_DOT_ENC = "__"   # encode "."  as "__"
_ARR_ENC = ""     # strip "[]"


def encode_path(dotted: str) -> str:
    """Encode a dotted field path to a safe Textual widget ID.

    Rules:
      - replace [] with -ARR
      - replace . with __
      - prefix with sf_
    """
    clean = re.sub(r"\[(\d*)\]", r"-ARR\1", dotted)
    return "sf_" + clean.replace(".", "__")


def decode_path(widget_id: str) -> list[str] | None:
    """Decode widget ID back to path segments.  Returns None if not a schema field."""
    if not widget_id.startswith("sf_"):
        return None
    dotted = widget_id[3:].replace("__", ".")
    dotted = re.sub(r"-ARR(\d*)", r"[\1]", dotted)
    return dotted.split(".")


# ---------------------------------------------------------------------------
# Field type → widget
# ---------------------------------------------------------------------------

_INTEGER_KEYWORDS = {"integer", "int"}
_BOOL_KEYWORDS = {"boolean", "bool"}
_MAP_KEYWORDS = {"map[string]string", "object"}

# Known enum values for specific field paths
_KNOWN_ENUMS: dict[str, list[str]] = {
    "spec.type": ["ClusterIP", "NodePort", "LoadBalancer", "ExternalName"],
    "spec.restartPolicy": ["Always", "OnFailure", "Never"],
    "spec.accessModes": ["ReadWriteOnce", "ReadOnlyMany", "ReadWriteMany", "ReadWriteOncePod"],
    "spec.volumeMode": ["Filesystem", "Block"],
    "spec.persistentVolumeReclaimPolicy": ["Retain", "Recycle", "Delete"],
    "spec.updateStrategy.type": ["RollingUpdate", "OnDelete"],
    "spec.rules[].http.paths[].pathType": ["Prefix", "Exact", "ImplementationSpecific"],
    "spec.metrics[].type": ["Resource", "Pods", "Object", "External", "ContainerResource"],
    "spec.metrics[].resource.target.type": ["Utilization", "Value", "AverageValue"],
    "spec.policyTypes": ["Ingress", "Egress"],
}


def _widget_for_field(
    path: str,
    ftype: str,
    required: bool,
    namespaces: list[str] | None = None,
) -> Widget:
    """Build one form row for a field path."""
    widget_id = encode_path(path)
    # Leaf label: last component of path
    label = path.split(".")[-1]
    req_marker = " *" if required else ""
    label_text = f"{label}{req_marker}"

    clean_path = re.sub(r"\[\]", "", path)

    # Namespace dropdown check
    if namespaces is not None and clean_path in {"metadata.namespace", "spec.template.metadata.namespace"}:
        options = [(n, n) for n in namespaces]
        return Vertical(
            Label(label_text, classes="field-label"),
            Select(options, id=widget_id, classes="form-input", allow_blank=True, prompt="Select namespace..."),
            classes="form-field",
        )

    # Check known enum overrides first
    enum_vals = _KNOWN_ENUMS.get(clean_path) or _KNOWN_ENUMS.get(path)

    if enum_vals:
        options = [(v, v) for v in enum_vals]
        return Vertical(
            Label(label_text, classes="field-label"),
            Select(options, id=widget_id, classes="form-input", allow_blank=True, prompt=f"Select {label}"),
            classes="form-field",
        )

    if ftype in _BOOL_KEYWORDS:
        return Vertical(
            Label(label_text, classes="field-label"),
            Switch(id=widget_id, classes="form-input"),
            classes="form-field",
        )

    if ftype in _INTEGER_KEYWORDS:
        return Vertical(
            Label(label_text, classes="field-label"),
            Input(id=widget_id, type="integer", placeholder=label, classes="form-input"),
            classes="form-field",
        )

    if ftype in _MAP_KEYWORDS or "map[" in ftype:
        from ktui.ui.widgets.map_editor import MapEditor
        return Vertical(
            Label(label_text, classes="field-label"),
            MapEditor(id=widget_id, classes="form-input", name=label),
            classes="form-field",
        )

    if ftype.startswith("[]") or ftype == "array":
        # Render as comma-separated input for now
        return Vertical(
            Label(f"{label_text}  (comma-separated)", classes="field-label"),
            Input(id=widget_id, placeholder=f"{label} (e.g. val1, val2)", classes="form-input"),
            classes="form-field",
        )

    # Default: text input
    return Vertical(
        Label(label_text, classes="field-label"),
        Input(id=widget_id, placeholder=label, classes="form-input"),
        classes="form-field",
    )


# ---------------------------------------------------------------------------
# Section widget: groups fields under a collapsible header
# ---------------------------------------------------------------------------

class FieldSection(Widget):
    """Groups a set of form fields under a labelled section."""

    DEFAULT_CSS = """
    FieldSection {
        height: auto;
        border-top: solid $border;
        margin-bottom: 2;
        padding-top: 1;
    }

    .section-title {
        color: $accent;
        text-style: bold;
        padding-bottom: 1;
    }

    .section-body {
        height: auto;
        padding-left: 2;
    }

    .tree-group-title {
        color: $text-muted;
        text-style: bold;
        margin-top: 1;
    }

    .tree-group {
        height: auto;
    }

    .tree-group-body {
        height: auto;
        padding-left: 2;
    }
    """

    def __init__(self, title: str, fields: list[Widget], **kw) -> None:
        super().__init__(**kw)
        self._title = title
        self._field_widgets = fields

    def compose(self) -> ComposeResult:
        yield Label(self._title, classes="section-title")
        with Vertical(classes="section-body"):
            yield from self._field_widgets


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def group_common_fields_by_section(common_paths: list[str]) -> dict[str, list[str]]:
    """Group dotted paths by their top-level key (metadata, spec, etc.)."""
    sections: dict[str, list[str]] = {}
    for path in common_paths:
        top = path.split(".")[0]
        sections.setdefault(top, []).append(path)
    return sections

def _build_path_tree(paths: list[str]) -> dict:
    tree: dict = {}
    for p in paths:
        parts = p.split('.')
        curr = tree
        if len(parts) > 1:
            for part in parts[1:-1]:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
            curr[parts[-1]] = p
        else:
            curr[parts[0]] = p
    return tree

class ArrayGroup(Widget):
    """Dynamically adds instances of an array item."""
    
    DEFAULT_CSS = """
    ArrayGroup {
        height: auto;
        margin-top: 1;
        margin-bottom: 2;
    }
    .array-header {
        height: auto;
        layout: horizontal;
    }
    .array-title {
        color: $text-muted;
        text-style: bold;
        width: 1fr;
    }
    .array-add-btn {
        margin-right: 1;
    }
    .array-items {
        height: auto;
        padding-left: 2;
    }
    .array-item-box {
        height: auto;
        border-bottom: solid $border;
        margin-bottom: 2;
        padding-bottom: 1;
    }
    """

    def __init__(self, key: str, tree_node: dict, schema_fields: dict, namespaces: list[str] | None, path_replacements: dict[str, str]):
        super().__init__()
        self._key = key
        self._clean_key = key.replace("[]", "").replace("-ARR", "")
        self._tree_node = tree_node
        self._schema_fields = schema_fields
        self._namespaces = namespaces
        self._path_replacements = dict(path_replacements)
        self._count = 0

    def compose(self) -> ComposeResult:
        with Horizontal(classes="array-header"):
            yield Label(f"{self._clean_key}:", classes="array-title")
            yield Button("＋ Add item", id="array-add", classes="array-add-btn")
        yield Vertical(id="array-items-container", classes="array-items")

    def on_mount(self) -> None:
        self.action_add_item()

    def action_add_item(self) -> None:
        idx = self._count
        self._count += 1
        
        # Determine the segment name that will be replaced
        # e.g., if key is "containers[]", we replace it with "containers[0]"
        # Since path in leaves has "[]" or "-ARR"? Wait, get_leaf_field_paths appends "[]".
        # We replace the exact key name in the path string.
        # But wait, paths have "[]".
        replacements = dict(self._path_replacements)
        replacements[self._key] = f"{self._key[:-2]}[{idx}]"
        
        widgets = _render_path_tree(self._tree_node, self._schema_fields, self._namespaces, replacements)
        
        container = self.query_one("#array-items-container", Vertical)
        item_box = Vertical(*widgets, classes="array-item-box")
        container.mount(item_box)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "array-add":
            event.stop()
            self.action_add_item()


def _render_path_tree(
    tree_node: dict,
    schema_fields: dict,
    namespaces: list[str] | None,
    path_replacements: dict[str, str] | None = None,
    current_path: str = ""
) -> list[Widget]:
    if path_replacements is None:
        path_replacements = {}
        
    widgets = []
    for key, val in tree_node.items():
        node_path = f"{current_path}.{key}" if current_path else key
        
        if isinstance(val, dict):
            is_array = key.endswith("[]") or key.endswith("-ARR")
            if is_array:
                widgets.append(ArrayGroup(key, val, schema_fields, namespaces, path_replacements))
            else:
                branch_widgets = _render_path_tree(val, schema_fields, namespaces, path_replacements, node_path)
                clean_key = key.replace("[]", "").replace("-ARR", "")
                
                body_id = f"tg_body_{encode_path(node_path)}"
                widgets.append(
                    Vertical(
                        Label(f"{clean_key}:", classes="tree-group-title"),
                        Vertical(*branch_widgets, id=body_id, classes="tree-group-body"),
                        classes="tree-group"
                    )
                )
        else:
            path = val
            for k, repl in path_replacements.items():
                path = path.replace(k, repl)
            
            lookup = re.sub(r"\[\d*\]", "", path)
            lookup = re.sub(r"\[\]", "", lookup)
            
            node = resolve_field_path(schema_fields, lookup)
            ftype = node.get("type", "string") if node else "string"
            required = node.get("required", False) if node else False
            w = _widget_for_field(path, ftype, required, namespaces)
            if w:
                widgets.append(w)
    return widgets


def build_schema_form(kind: str, namespaces: list[str] | None = None) -> tuple[list[Widget], set[str]]:
    """
    Build form widgets for a resource kind using the schema.

    Returns:
        (widgets, shown_paths) — list of Textual widgets to mount,
        and the set of dotted paths already shown (for field picker).
    """
    resource = get_resource(kind)
    if resource is None:
        return [Static(f"No schema found for {kind}")], set()

    common = resource["common_fields"]
    schema_fields = resource["fields"]
    shown_paths: set[str] = set(common)

    # Header: apiVersion + kind (read-only)
    api_version = resource["apiVersion"]
    header_widgets: list[Widget] = [
        Vertical(
            Label("apiVersion:", classes="field-label"),
            Static(api_version, classes="readonly-value"),
            classes="form-field",
        ),
        Vertical(
            Label("kind:", classes="field-label"),
            Static(kind, classes="readonly-value"),
            classes="form-field",
        ),
    ]

    # Group common fields by section
    sections = group_common_fields_by_section(common)
    section_widgets: list[Widget] = []

    for section_name, paths in sections.items():
        tree_node = _build_path_tree(paths)
        field_rows = _render_path_tree(tree_node, schema_fields, namespaces, current_path=section_name)
        section_widgets.append(FieldSection(section_name, field_rows))

    # "Add more fields" button
    add_btn = Button("＋ Add more fields…", classes="schema-add-fields-btn", variant="default")

    # Container for dynamically added advanced fields
    advanced_container = Vertical(classes="schema-advanced-fields")

    all_widgets = header_widgets + section_widgets + [advanced_container, add_btn]
    return all_widgets, shown_paths


def merge_paths_into_form(
    paths: list[str],
    screen: Widget,
    schema_fields: dict,
    namespaces: list[str] | None,
    advanced_container: Widget
) -> None:
    """Intelligently merge new field paths into existing form sections, or create new ones."""
    sections = group_common_fields_by_section(paths)
    for section_name, sec_paths in sections.items():
        tree = _build_path_tree(sec_paths)
        
        target = None
        for s in screen.query(FieldSection):
            if getattr(s, "_title", None) == section_name:
                target = s
                break
                
        if target:
            # We must manually merge the tree into the existing target
            # by traversing the dict structure.
            def _merge_tree(sub_tree: dict, parent_container: Widget, current_path: str):
                for key, val in sub_tree.items():
                    node_path = f"{current_path}.{key}" if current_path else key
                    if isinstance(val, dict):
                        is_array = key.endswith("[]") or key.endswith("-ARR")
                        if is_array:
                            parent_container.mount(ArrayGroup(key, val, schema_fields, namespaces))
                        else:
                            body_id = f"tg_body_{encode_path(node_path)}"
                            # Does this container exist?
                            try:
                                existing_body = target.query_one(f"#{body_id}")
                                _merge_tree(val, existing_body, node_path)
                            except Exception:
                                # Doesn't exist, generate the rest and mount it
                                widgets = _render_path_tree({key: val}, schema_fields, namespaces, current_path=current_path)
                                parent_container.mount(*widgets)
                    else:
                        # Leaf node
                        widgets = _render_path_tree({key: val}, schema_fields, namespaces, current_path=current_path)
                        parent_container.mount(*widgets)
            
            body = target.query_one(".section-body")
            _merge_tree(tree, body, section_name)
        else:
            # Create a new top-level section in the advanced container
            widgets = _render_path_tree(tree, schema_fields, namespaces, current_path=section_name)
            new_section = FieldSection(section_name, widgets)
            advanced_container.mount(new_section)
