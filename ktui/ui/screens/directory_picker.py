"""Modal screen to pick a directory."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label, Tree


class DirectoryPickerScreen(ModalScreen[Path]):
    """Modal to select a directory."""

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]

    DEFAULT_CSS = """
    DirectoryPickerScreen {
        align: center middle;
        background: $background 80%;
    }

    #dir-picker-dialog {
        width: 60;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #dir-header {
        height: 3;
        margin-bottom: 1;
        layout: horizontal;
    }
    
    #dir-current-path {
        width: 1fr;
        padding: 0 1;
        content-align: left middle;
        border: solid $surface-lighten-2;
    }

    #dir-tree {
        height: 1fr;
        border: solid $surface-lighten-2;
        margin-bottom: 1;
    }

    .dir-buttons {
        height: auto;
        align: right middle;
    }
    
    .dir-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, initial_path: str = ".") -> None:
        super().__init__()
        self.initial_path = str(Path(initial_path).absolute())
        self.selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="dir-picker-dialog"):
            yield Label("Select Directory", classes="text-bold")
            with Horizontal(id="dir-header"):
                yield Button("⬆ Up", id="btn-dir-up", variant="primary")
                yield Label(self.initial_path, id="dir-current-path")
                
            yield DirectoryTree(self.initial_path, id="dir-tree")
            with Horizontal(classes="dir-buttons"):
                yield Button("Select", id="btn-dir-select", variant="success")
                yield Button("Cancel", id="btn-dir-cancel", variant="error")

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        event.stop()
        if event.node.data:
            path = event.node.data.path
            # If it's a file, get parent dir
            if path.is_file():
                self.selected_path = path.parent
            else:
                self.selected_path = path
                
            self.query_one("#dir-current-path", Label).update(str(self.selected_path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "btn-dir-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-dir-select":
            tree = self.query_one("#dir-tree", DirectoryTree)
            path = Path(tree.path)  # fallback to root
            if tree.cursor_node and tree.cursor_node.data:
                node_path = tree.cursor_node.data.path
                if node_path.is_file():
                    path = node_path.parent
                else:
                    path = node_path
            self.dismiss(path)
        elif event.button.id == "btn-dir-up":
            tree = self.query_one("#dir-tree", DirectoryTree)
            current = Path(tree.path)
            parent = current.parent
            if parent != current:
                tree.path = str(parent)
                self.query_one("#dir-current-path", Label).update(str(parent))
