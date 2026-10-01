"""Main Textual application entry point."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.theme import Theme

from ktui.ui.screens.main_screen import MainScreen


class YAMLGeneratorApp(App):
    """ktui — Kubernetes TUI manifest builder."""

    TITLE = "ktui"
    SUB_TITLE = "Kubernetes manifest builder"
    CSS_PATH = "ui/styles/app.tcss"
    
    BINDINGS = [
        ("t", "cycle_theme", "Cycle Theme"),
    ]

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
    """Entry point used by the ``yamlgen`` console script."""
    YAMLGeneratorApp().run()


if __name__ == "__main__":
    main()
