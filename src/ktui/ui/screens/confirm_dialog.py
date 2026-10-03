"""Generic yes/no confirmation modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmScreen(ModalScreen[bool]):
    """Ask the user to confirm a destructive action. Dismisses with True/False."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("n", "cancel", "No", show=False),
        Binding("y", "confirm", "Yes", show=False),
    ]

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    ConfirmScreen > #confirm-box {
        width: 60;
        height: auto;
        padding: 1 2;
        border: thick $warning;
        background: $surface;
    }

    ConfirmScreen #confirm-title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }

    ConfirmScreen #confirm-message {
        margin-bottom: 1;
    }

    ConfirmScreen #confirm-buttons {
        height: auto;
        align: right middle;
    }

    ConfirmScreen #confirm-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(
        self,
        message: str,
        title: str = "Are you sure?",
        confirm_label: str = "Yes",
        cancel_label: str = "Cancel",
    ) -> None:
        super().__init__()
        self._message = message
        self._title = title
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(self._title, id="confirm-title")
            yield Label(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button(self._cancel_label, id="confirm-cancel")
                yield Button(self._confirm_label, id="confirm-ok", variant="error")

    def on_mount(self) -> None:
        # Default focus on the safe choice.
        self.query_one("#confirm-cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "confirm-ok")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
