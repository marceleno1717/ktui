"""Screen for importing values from cluster resources."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Select

from ktui.kubernetes.client import get_cluster_resources


class ClusterImportScreen(ModalScreen[dict[str, str]]):
    """Modal to select a resource and import its labels/annotations."""

    DEFAULT_CSS = """
    ClusterImportScreen {
        align: center middle;
        background: $background 80%;
    }

    #cluster-import-dialog {
        width: 60;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #import-kind-select {
        margin-bottom: 1;
    }

    #import-resource-list {
        height: 1fr;
        border: solid $surface-lighten-2;
        margin-bottom: 1;
    }
    
    #import-status {
        color: $warning;
        margin-bottom: 1;
    }

    .import-buttons {
        height: auto;
        align: right middle;
    }
    """

    def __init__(self, target_property: str = "labels") -> None:
        super().__init__()
        self.target_property = target_property  # e.g. "labels" or "annotations"
        self._resources_cache: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="cluster-import-dialog"):
            yield Label(f"Import {self.target_property} from cluster", classes="text-bold")
            yield Select(
                [("Deployment", "deployment"), ("Pod", "pod"), ("Service", "service")],
                value="deployment",
                id="import-kind-select"
            )
            yield Label("", id="import-status")
            yield ListView(id="import-resource-list")
            with Horizontal(classes="import-buttons"):
                yield Button("Cancel", id="import-cancel", variant="error")

    def on_mount(self) -> None:
        self.fetch_resources("deployment")

    @work(thread=True)
    def fetch_resources(self, kind: str) -> None:
        self.app.call_from_thread(self._set_status, f"Fetching {kind}s...")
        items = get_cluster_resources(kind)
        self.app.call_from_thread(self._populate_list, items)

    def _set_status(self, msg: str) -> None:
        self.query_one("#import-status", Label).update(msg)

    def _populate_list(self, items: list[dict]) -> None:
        self._resources_cache = items
        lv = self.query_one("#import-resource-list", ListView)
        lv.clear()
        if not items:
            self._set_status("No resources found.")
            return

        self._set_status(f"Found {len(items)} resources.")
        for idx, item in enumerate(items):
            meta = item.get("metadata", {})
            name = meta.get("name", "unknown")
            ns = meta.get("namespace", "default")
            lv.append(ListItem(Label(f"{ns}/{name}"), name=str(idx)))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "import-kind-select" and event.value != Select.BLANK:
            self.fetch_resources(str(event.value))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not event.item.name:
            return
        idx = int(event.item.name)
        item = self._resources_cache[idx]
        meta = item.get("metadata", {})
        
        # Determine what to extract based on target_property
        # If it's a selector, we usually want the pod labels. 
        # A Deployment's pod labels are in spec.template.metadata.labels
        # Otherwise, if importing labels/annotations directly, use metadata.labels
        
        data = {}
        if self.target_property == "selector" and item.get("kind") == "Deployment":
            data = item.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
        else:
            # default to metadata.labels
            data = meta.get("labels", {})
            
        self.dismiss(data)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "import-cancel":
            self.dismiss({})
