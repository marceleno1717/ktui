"""Main Textual application entry point."""

from __future__ import annotations

from typing import Any

from textual.app import App

from ktui import __version__
from ktui.ui.screens.main_screen import MainScreen


class YAMLGeneratorApp(App):
    """ktui — Kubernetes TUI manifest builder."""

    TITLE = "ktui"
    SUB_TITLE = f"Kubernetes manifest builder (v{__version__})"
    CSS_PATH = "ui/styles/app.tcss"
    
    BINDINGS = [
        ("t", "cycle_theme", "Cycle Theme"),
    ]

    def __init__(self, initial_data: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.initial_data = initial_data

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self._available_themes = [
            "textual-dark",
            "catppuccin-mocha",
            "tokyo-night",
            "dracula",
            "nord",
        ]
        self.push_screen(MainScreen())

    def action_cycle_theme(self) -> None:
        try:
            idx = self._available_themes.index(self.theme)
        except ValueError:
            idx = 0
        next_theme = self._available_themes[(idx + 1) % len(self._available_themes)]
        self.theme = next_theme
        self.notify(f"Theme: {next_theme}", timeout=2.0)


def main() -> None:
    """Entry point used by the ``ktui`` console script."""
    import argparse

    from ruamel.yaml import YAML
    
    parser = argparse.ArgumentParser(description="ktui — Kubernetes TUI manifest builder.")
    parser.add_argument(
        "file", 
        nargs="?", 
        help="Path to an existing Kubernetes YAML file to edit."
    )
    args = parser.parse_args()
    
    initial_data = None
    file_load_error = None
    if args.file:
        try:
            from pathlib import Path
            path = Path(args.file)
            if not path.exists() and path.parts and path.parts[0] != "~":
                # Try relative to home dir as a fallback
                home_path = Path("~").expanduser() / args.file
                if home_path.exists():
                    path = home_path
            
            yaml = YAML(typ='safe')
            with open(path, "r") as f:
                initial_data = yaml.load(f)
        except Exception as e:
            file_load_error = f"Error loading YAML file '{args.file}': {e}"
            
    app = YAMLGeneratorApp(initial_data=initial_data)
    if file_load_error:
        app.call_after_refresh(app.notify, file_load_error, severity="error", timeout=5.0)
    app.run()


if __name__ == "__main__":
    main()
