"""Resource registry — catalog of all available K8s/OC resource models.

Usage
-----
Decorate a resource model class with ``@register_resource``:

    from ktui.registry import register_resource

    @register_resource(platform="kubernetes", group="core")
    class Pod(K8sResource):
        ...

The app then queries the catalog at startup:

    from ktui.registry import CATALOG

    k8s_resources = CATALOG.list_resources(platform="kubernetes")

Design decisions
----------------
- Decorator pattern: each resource self-registers; no central list to maintain.
- ``CATALOG`` is a module-level singleton; importing it anywhere returns the
  same instance.
- ``platform`` is a plain string so future platforms (e.g. "argo", "flux")
  need no enum change.
- ``group`` loosely mirrors the Kubernetes API group (core, apps,
  route.openshift.io, etc.) and is used only for sidebar grouping in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True)
class ResourceEntry:
    """Metadata stored alongside each registered resource model."""

    platform: str
    group: str
    model: type  # the Pydantic BaseModel subclass


class ResourceCatalog:
    """Singleton catalog that holds every registered resource."""

    def __init__(self) -> None:
        self._entries: list[ResourceEntry] = []

    def register(self, *, platform: str, group: str, model: type) -> None:
        """Add a resource model to the catalog."""
        self._entries.append(ResourceEntry(platform=platform, group=group, model=model))

    def list_resources(self, platform: str) -> list[ResourceEntry]:
        """Return all entries for a given platform, preserving insertion order."""
        return [e for e in self._entries if e.platform == platform]

    def list_groups(self, platform: str) -> list[str]:
        """Return unique API groups for a platform, in insertion order."""
        seen: dict[str, None] = {}
        for e in self._entries:
            if e.platform == platform:
                seen[e.group] = None
        return list(seen)

    def __iter__(self) -> Iterator[ResourceEntry]:
        return iter(self._entries)


# Module-level singleton — import this everywhere.
CATALOG: ResourceCatalog = ResourceCatalog()


def register_resource(*, platform: str, group: str = "core"):
    """Class decorator that registers a resource model in the global CATALOG.

    Parameters
    ----------
    platform:
        ``"kubernetes"`` or ``"openshift"`` (or any future platform string).
    group:
        Kubernetes API group, e.g. ``"core"``, ``"apps"``,
        ``"route.openshift.io"``.  Defaults to ``"core"``.

    Example
    -------
    ::

        @register_resource(platform="kubernetes", group="core")
        class Pod(K8sResource):
            ...
    """

    def decorator(cls: type) -> type:
        CATALOG.register(platform=platform, group=group, model=cls)
        return cls

    return decorator


# ---------------------------------------------------------------------------
# Auto-registration: import all resource modules so decorators fire.
# ---------------------------------------------------------------------------
# Each import causes the module-level decorator to run, populating CATALOG.
# Add new modules here as resources are implemented.

def _load_resources() -> None:
    # Kubernetes
    from ktui.models.kubernetes import pod as _pod_module  # noqa: F401
    from ktui.models.kubernetes import deployment as _deployment_module  # noqa: F401
    from ktui.models.kubernetes import service as _service_module  # noqa: F401
    from ktui.models.kubernetes import configmap as _configmap_module  # noqa: F401

    # OpenShift
    from ktui.models.openshift import route as _route_module  # noqa: F401


_load_resources()
