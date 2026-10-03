"""Sidebar widget for Kubernetes connection status."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Select

from ktui.kubernetes.cache import K8S_CACHE
from ktui.kubernetes.client import (
    ClusterStatus,
    check_connection,
    get_all_contexts,
    get_all_namespaces,
    set_namespace,
    use_context,
)


class ConnectionPanel(Widget):
    """Panel showing K8s connection and namespace selector."""

    DEFAULT_CSS = """
    ConnectionPanel {
        height: auto;
        padding: 1 1;
        border-bottom: solid $border;
    }
    
    #conn-status-label {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #conn-status-label.connected {
        color: $success;
    }

    #conn-status-label.disconnected {
        color: $error;
    }
    
    #conn-context-select, #conn-namespace-select {
        width: 100%;
        margin-bottom: 1;
        display: none;
    }
    
    #conn-reconnect-btn {
        width: 100%;
        margin-top: 1;
        display: none;
    }
    """

    class ContextChanged(Message):
        def __init__(self, context_name: str) -> None:
            self.context_name = context_name
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self._last_context: str | None = None
        self._last_namespace: str | None = None

    def compose(self) -> ComposeResult:
        yield Label("Checking connection...", id="conn-status-label")
        yield Select([], id="conn-context-select", prompt="Context")
        yield Select([], id="conn-namespace-select", prompt="Namespace")
        yield Button("Reconnect", id="conn-reconnect-btn", variant="primary")

    def on_mount(self) -> None:
        self.refresh_connection()

    def refresh_connection(self) -> None:
        lbl = self.query_one("#conn-status-label", Label)
        lbl.update("Checking connection...")
        lbl.remove_class("connected", "disconnected")
        self._check_connection_task()

    @work(thread=True)
    def _check_connection_task(self) -> None:
        status = check_connection()
        self.app.call_from_thread(self._update_ui, status)

    def _update_ui(self, status: ClusterStatus) -> None:
        lbl = self.query_one("#conn-status-label", Label)
        sel_ctx = self.query_one("#conn-context-select", Select)
        sel_ns = self.query_one("#conn-namespace-select", Select)
        btn = self.query_one("#conn-reconnect-btn", Button)

        contexts = get_all_contexts()
        sel_ctx.set_options([(c, c) for c in contexts])
        self._last_context = status.context_name
        if status.context_name and status.context_name in contexts:
            sel_ctx.value = status.context_name
        else:
            sel_ctx.clear()
        sel_ctx.display = True

        if status.connected:
            lbl.update("● Connected")
            lbl.remove_class("disconnected")
            lbl.add_class("connected")

            namespaces = get_all_namespaces()
            # Store in shared cache (replaces app._cached_namespaces hack)
            K8S_CACHE.set("all_namespaces", namespaces)
            self._last_namespace = status.namespace

            sel_ns.set_options([(n, n) for n in namespaces])
            if status.namespace and status.namespace in namespaces:
                sel_ns.value = status.namespace
            else:
                sel_ns.clear()
            sel_ns.display = True
            btn.display = False
        else:
            lbl.update("○ Disconnected")
            lbl.remove_class("connected")
            lbl.add_class("disconnected")
            sel_ns.display = False
            btn.display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "conn-reconnect-btn":
            self.refresh_connection()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK:
            return

        if event.select.id == "conn-context-select":
            context_name = str(event.value)
            if context_name == self._last_context:
                return

            success = use_context(context_name)
            if success:
                self._last_context = context_name
                self.post_message(self.ContextChanged(context_name))
                self.refresh_connection()
            else:
                self.app.notify("Failed to change context", severity="error")

        elif event.select.id == "conn-namespace-select":
            namespace = str(event.value)
            if getattr(self, "_last_namespace", None) == namespace:
                return

            success = set_namespace(namespace)
            if success:
                self._last_namespace = namespace
            else:
                self.app.notify("Failed to change namespace", severity="error")

