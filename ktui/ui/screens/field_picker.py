from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Tree

from ktui.schema.loader import get_common_fields, get_leaf_field_paths

_MAX_VISIBLE = 150  # cap to avoid rendering thousands of widgets


class FieldPickerScreen(ModalScreen[list[str]]):
    """Let the user pick additional fields to add to the form."""
    
    BINDINGS = [
        ("escape", "dismiss([])", "Cancel"),
    ]

    DEFAULT_CSS = """
    FieldPickerScreen {
        align: center middle;
        background: $background 80%;
    }

    #field-picker-dialog {
        width: 70;
        height: 38;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #field-search {
        margin-bottom: 1;
    }

    #field-tree {
        height: 1fr;
        border: solid $surface-lighten-2;
        margin-bottom: 1;
    }

    #fp-count {
        color: $text-muted;
        margin-bottom: 1;
        height: 1;
    }

    .fp-buttons {
        height: auto;
        align: right middle;
    }

    .fp-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, kind: str, fields: dict, already_added: set[str]) -> None:
        super().__init__()
        self._kind = kind
        self._fields = fields
        self._already_added = already_added
        # Pre-compute once — leaf paths only, excluding common + already added
        common = set(get_common_fields(self._kind))
        # Sort paths alphabetically so prefixes group nicely
        paths = get_leaf_field_paths(self._fields)
        paths.sort(key=lambda x: x[0])
        self._all_paths: list[tuple[str, str, bool]] = [
            (p, t, req)
            for p, t, req in paths
            if p not in common and p not in self._already_added
        ]
        self._selected: set[str] = set()
        self._current_query = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="field-picker-dialog"):
            yield Label(f"Add fields — {self._kind}", classes="text-bold")
            yield Input(placeholder="Type to filter fields…", id="field-search")
            yield Label("", id="fp-count")
            tree = Tree("Fields", id="field-tree")
            tree.root.expand()
            yield tree
            with Horizontal(classes="fp-buttons"):
                yield Button("Add selected", id="fp-add", variant="success")
                yield Button("Cancel", id="fp-cancel", variant="error")

    def on_mount(self) -> None:
        self._refresh_list("")

    def _refresh_list(self, query: str) -> None:
        q = query.strip().lower()
        matches = [
            (p, t, req) for p, t, req in self._all_paths
            if not q or q in p.lower()
        ]
        total = len(matches)
        visible = matches[:_MAX_VISIBLE]

        count_label = self.query_one("#fp-count", Label)
        if total > _MAX_VISIBLE:
            count_label.update(f"{total} fields — showing {_MAX_VISIBLE}. Type to filter.")
        else:
            count_label.update(f"{total} fields")

        tree = self.query_one("#field-tree", Tree)
        tree.clear()
        
        nodes = {"": tree.root}
        
        for path, ftype, req in visible:
            parts = path.split('.')
            # Add intermediate nodes
            for i in range(1, len(parts)):
                parent_path = ".".join(parts[:i])
                if parent_path not in nodes:
                    grandparent = ".".join(parts[:i-1])
                    grandparent_node = nodes.get(grandparent, tree.root)
                    label = f"📁 {parts[i-1]}  [+]"
                    nodes[parent_path] = grandparent_node.add(
                        label,
                        data=("GROUP", parent_path),
                        expand=True
                    )
            
            # Add leaf node
            parent_path = ".".join(parts[:-1])
            parent_node = nodes.get(parent_path, tree.root)
            marker = "[✓] " if path in self._selected else "[ ] "
            req_tag = " *" if req else ""
            leaf_name = parts[-1]
            label = f"{marker}{leaf_name}{req_tag}  [{ftype}]"
            parent_node.add_leaf(label, data=(path, leaf_name, ftype, req))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "field-search":
            self._current_query = event.value
            self.set_timer(0.25, self._apply_search)

    def _apply_search(self) -> None:
        self._refresh_list(self._current_query)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            if event.node.data[0] == "GROUP":
                group_path = event.node.data[1]
                prefix = group_path + "."
                
                # Check if all matching paths are already selected
                matching_paths = [p for p, t, r in self._all_paths if p.startswith(prefix) or p == group_path]
                all_selected = all(p in self._selected for p in matching_paths)
                
                if all_selected:
                    for p in matching_paths:
                        self._selected.discard(p)
                    self.app.notify(f"Deselected all fields in {group_path}")
                else:
                    for p in matching_paths:
                        self._selected.add(p)
                    self.app.notify(f"Selected all fields in {group_path}")
                
                # Recursively update the UI labels for all children
                def _update_leaves(node):
                    if node.data and node.data[0] != "GROUP":
                        path, leaf_name, ftype, req = node.data
                        marker = "[✓] " if path in self._selected else "[ ] "
                        req_tag = " *" if req else ""
                        node.set_label(f"{marker}{leaf_name}{req_tag}  [{ftype}]")
                    for child in node.children:
                        _update_leaves(child)
                        
                _update_leaves(event.node)
                event.node.expand()
            else:
                path, leaf_name, ftype, req = event.node.data
                if path in self._selected:
                    self._selected.discard(path)
                else:
                    self._selected.add(path)
                
                marker = "[✓] " if path in self._selected else "[ ] "
                req_tag = " *" if req else ""
                new_label = f"{marker}{leaf_name}{req_tag}  [{ftype}]"
                event.node.set_label(new_label)
        else:
            # Toggle expansion for non-leaf nodes
            event.node.toggle()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "fp-cancel":
            self.dismiss([])
        elif event.button.id == "fp-add":
            self.dismiss(list(self._selected))
