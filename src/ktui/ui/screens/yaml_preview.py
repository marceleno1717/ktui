"""YAML preview modal screen."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class YAMLPreviewScreen(ModalScreen[bool]):
    """Modal overlay showing the generated YAML with Save / Close buttons."""
    
    BINDINGS = [
        ("escape", "dismiss(False)", "Close"),
    ]

    DEFAULT_CSS = """
    YAMLPreviewScreen {
        align: center middle;
    }

    #preview-dialog {
        width: 80%;
        height: 80%;
        max-width: 120;
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    #preview-title {
        background: $primary;
        color: $text;
        text-align: center;
        padding: 1 2;
        text-style: bold;
    }

    #yaml-scroll {
        height: 1fr;
        padding: 1 2;
    }

    #yaml-content {
        color: $text;
    }

    #preview-actions {
        height: auto;
        align: right middle;
        padding: 1 2;
        border-top: solid $surface-lighten-2;
        layout: horizontal;
    }
    
    #file-path-input {
        width: 1fr;
        margin-right: 1;
    }

    #preview-actions Button {
        margin-left: 1;
    }
    """

    def __init__(self, yaml_str: str, default_filename: str = "output.yaml") -> None:
        super().__init__()
        self._yaml_str = yaml_str
        self._default_path = str(Path.cwd() / default_filename)

    def compose(self) -> ComposeResult:
        with Vertical(id="preview-dialog"):
            yield Label("YAML Preview", id="preview-title")
            with VerticalScroll(id="yaml-scroll"):
                yield Static(self._yaml_str, id="yaml-content")
            with Horizontal(id="preview-actions"):
                from textual.widgets import Input
                yield Input(value=self._default_path, id="file-path-input", placeholder="Path to save...")
                yield Button("Browse", id="btn-browse", variant="primary")
                yield Button("Save", id="btn-save-file", variant="success")
                yield Button("Close", id="btn-close", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(False)
        elif event.button.id == "btn-save-file":
            self._save()
        elif event.button.id == "btn-browse":
            self._browse()

    def _browse(self) -> None:
        from textual.widgets import Input

        from ktui.ui.screens.directory_picker import DirectoryPickerScreen
        
        input_widget = self.query_one("#file-path-input", Input)
        current_path = Path(input_widget.value.strip() or ".")
        start_dir = current_path.parent if current_path.is_file() or current_path.suffix else current_path
        if not start_dir.exists():
            start_dir = Path.cwd()

        def _on_dir_picked(path: Path | None) -> None:
            if path:
                filename = current_path.name if current_path.name else "output.yaml"
                new_path = path / filename
                input_widget.value = str(new_path)
                
        self.app.push_screen(DirectoryPickerScreen(str(start_dir)), _on_dir_picked)

    def _save(self) -> None:
        from textual.widgets import Input
        output_path_str = self.query_one("#file-path-input", Input).value.strip()
        if not output_path_str:
            self.app.notify("File path cannot be empty", severity="error")
            return
            
        output_path = Path(output_path_str).absolute()
        try:
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(self._yaml_str, encoding="utf-8")
            self.app.notify(f"Saved → {output_path}", severity="information")
            self.dismiss(True)
        except OSError as exc:
            self.app.notify(f"Save failed: {exc}", severity="error")

