"""Resource registry — catalog of all available K8s/OC resource models.

P1-7 update: CATALOG is now populated from two sources:
1. Schema index (``data/schemas/index.json``) — all 22 known kinds.
   These get a lightweight ``SchemaEntry`` with no Pydantic model.
2. ``@register_resource`` decorator on Pydantic model classes — overrides the
   schema-only entry with a richer one that includes the model for validation.

This means the sidebar always shows all 22 kinds, and Pydantic validation
kicks in only for the 5 kinds that have a model.

Usage
-----
Decorate a resource model class with ``@register_resource``::

    from ktui.registry import register_resource

    @register_resource(platform="kubernetes", group="apps")
    class Deployment(K8sResource):
        ...

Query::

    from ktui.registry import CATALOG

    k8s_resources = CATALOG.list_resources(platform="kubernetes")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Map apiVersion prefix -> group name used for sidebar grouping
_API_GROUP_LABELS: dict[str, str] = {
    "apps/v1": "apps",
    "v1": "core",
    "batch/v1": "batch",
    "networking.k8s.io/v1": "networking",
    "autoscaling/v2": "autoscaling",
    "rbac.authorization.k8s.io/v1": "rbac",
    "route.openshift.io/v1": "route.openshift.io",
}


def _api_to_group(api_version: str) -> str:
    return _API_GROUP_LABELS.get(api_version, api_version.split("/")[0] if "/" in api_version else "core")


@dataclass(frozen=True)
class ResourceEntry:
    """Metadata stored alongside each registered resource."""

    platform: str
    group: str
    kind: str
    model: type | None = None  # None for schema-only (no Pydantic model yet)


class ResourceCatalog:
    """Singleton catalog that holds every registered resource."""

    def __init__(self) -> None:
        self._entries: dict[str, ResourceEntry] = {}  # keyed by kind

    def register(self, *, platform: str, group: str, model: type) -> None:
        """Add/override a resource model in the catalog (called by decorator)."""
        kind = model.__name__
        self._entries[kind] = ResourceEntry(
            platform=platform,
            group=group,
            kind=kind,
            model=model,
        )

    def register_schema(self, *, platform: str, kind: str, api_version: str) -> None:
        """Register a schema-only entry (no Pydantic model)."""
        # Don't override an already-registered model entry
        if kind not in self._entries:
            self._entries[kind] = ResourceEntry(
                platform=platform,
                group=_api_to_group(api_version),
                kind=kind,
                model=None,
            )

    def list_resources(self, platform: str) -> list[ResourceEntry]:
        """Return all entries for a given platform, sorted by kind."""
        return sorted(
            [e for e in self._entries.values() if e.platform == platform],
            key=lambda e: e.kind,
        )

    def list_groups(self, platform: str) -> list[str]:
        """Return unique API groups for a platform, in alpha order."""
        groups: set[str] = set()
        for e in self._entries.values():
            if e.platform == platform:
                groups.add(e.group)
        return sorted(groups)

    def get_model(self, kind: str) -> type | None:
        """Return the Pydantic model for *kind*, or None if schema-only."""
        entry = self._entries.get(kind)
        return entry.model if entry else None

    def __iter__(self) -> Iterator[ResourceEntry]:
        return iter(self._entries.values())

    def __len__(self) -> int:
        return len(self._entries)


# Module-level singleton — import this everywhere.
CATALOG: ResourceCatalog = ResourceCatalog()


def register_resource(*, platform: str, group: str = "core"):
    """Class decorator that registers a resource model in the global CATALOG.

    Parameters
    ----------
    platform:
        ``"kubernetes"`` or ``"openshift"`` (or any future platform string).
    group:
        Kubernetes API group, e.g. ``"core"``, ``"apps"``.  Defaults to
        ``"core"``.
    """

    def decorator(cls: type) -> type:
        CATALOG.register(platform=platform, group=group, model=cls)
        return cls

    return decorator


# ---------------------------------------------------------------------------
# P1-7: Bootstrap — register all schema kinds from index.json
# ---------------------------------------------------------------------------

def _bootstrap_from_schema() -> None:
    """Populate CATALOG with all 22 kinds from schema index (fast, index only)."""
    try:
        from ktui.schema.loader import _load_index
        index = _load_index()
        for entry in index.get("resources", []):
            CATALOG.register_schema(
                platform="kubernetes",
                kind=entry["kind"],
                api_version=entry.get("apiVersion", ""),
            )
    except Exception:
        pass  # Silently skip if schema not available (tests, bundled builds)


def _load_pydantic_models() -> None:
    """Import Pydantic model modules so @register_resource decorators fire.

    These *override* the schema-only entries with richer Pydantic entries.
    Auto-discovery via pkgutil is possible but risky; explicit list is safer.
    """
    try:
        from ktui.models.kubernetes import configmap as _  # noqa: F401, F811
        from ktui.models.kubernetes import deployment as _  # noqa: F401, F811
        from ktui.models.kubernetes import pod as _  # noqa: F401, F811
        from ktui.models.kubernetes import service as _  # noqa: F401, F811
        from ktui.models.openshift import route as _  # noqa: F401, F811  # noqa: F401
    except Exception:
        pass


# Order matters: bootstrap schema first, then override with Pydantic models.
_bootstrap_from_schema()
_load_pydantic_models()
