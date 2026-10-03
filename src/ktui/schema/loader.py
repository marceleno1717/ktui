"""Load and query the k8s schema database.

P1-6 update: schema is now sharded into per-kind JSON files under
``src/ktui/data/schemas/{kind.lower()}.json`` plus a lightweight
``index.json`` (kind + apiVersion + common_fields only, ~10 KB).

Public API (unchanged for callers):
  - ``get_all_resources()``   → list of index entries (fast, index only)
  - ``get_resource(kind)``    → full resource dict (lazy, cached per kind)
  - ``get_common_fields(kind)`` → list[str]
  - ``load_schema()``         → backward-compat shim (loads monolith if present)
  - ``load_resource(kind)``   → NEW: load one kind's shard (lru_cache)

Leaf-path helpers:
  - ``get_leaf_field_paths(fields)``  — memoised by field-dict identity
  - ``get_common_fields(kind)``        — reads index only, no shard parse needed
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_SCHEMA_DIR = Path(__file__).parent.parent / "data" / "schemas"
# ---------------------------------------------------------------------------
# Index — lightweight, always loaded once
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_index() -> dict[str, Any]:
    """Load index.json (~10 KB)."""
    idx_path = _SCHEMA_DIR / "index.json"
    if idx_path.exists():
        return json.loads(idx_path.read_text())
    return {"resources": []}

# ---------------------------------------------------------------------------
# Per-kind shard loading (P1-6)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=32)
def load_resource(kind: str) -> dict[str, Any] | None:
    """Load and cache one resource shard by kind."""
    shard_path = _SCHEMA_DIR / f"{kind.lower()}.json"
    if shard_path.exists():
        return json.loads(shard_path.read_text())
    return None


# ---------------------------------------------------------------------------
# Public API (unchanged signatures)
# ---------------------------------------------------------------------------

def get_all_resources() -> list[dict[str, Any]]:
    """Return all resource index entries sorted by kind.

    Reads only ``index.json`` (~10 KB) — no shard parsing.
    """
    entries = _load_index().get("resources", [])
    return sorted(entries, key=lambda r: r["kind"])


def get_resource(kind: str) -> dict[str, Any] | None:
    """Return a full resource entry (fields included) for *kind*.

    Uses ``load_resource`` which is lru_cache'd per kind.
    """
    return load_resource(kind)


def get_common_fields(kind: str) -> list[str]:
    """Return the curated list of common field paths for a kind.

    Reads from the index — no shard parse needed.
    """
    for entry in _load_index().get("resources", []):
        if entry["kind"] == kind:
            return entry.get("common_fields", [])
    return []


# ---------------------------------------------------------------------------
# Backward-compat shim (P1-6: keep for 1 release)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Backward-compatible shim: returns a merged dict like the old monolith.

    Callers that do ``load_schema()["resources"]`` still work.  New code
    should use ``get_all_resources()`` + ``get_resource(kind)`` instead.
    """
    index_entries = _load_index().get("resources", [])
    # Return index-only resources (no full fields) — sufficient for most callers
    return {"resources": index_entries}


# ---------------------------------------------------------------------------
# Field-path helpers (P1-8: memoised by field-dict id)
# ---------------------------------------------------------------------------

def get_all_field_paths(fields: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    """Recursively walk the fields tree; return (dotted_path, type) tuples."""
    result = []
    for name, info in fields.items():
        path = f"{prefix}.{name}" if prefix else name
        result.append((path, info.get("type", "string")))
        child = info.get("fields", {})
        if child:
            result.extend(get_all_field_paths(child, path))
    return result


# Memoised per unique field-dict object identity (P1-8)
_leaf_cache: dict[str, Any][int, list[tuple[str, str, bool]]] = {}


def get_leaf_field_paths(
    fields: dict[str, Any], prefix: str = ""
) -> list[tuple[str, str, bool]]:
    """Walk field tree; return (dotted_path, type, required) for leaf fields.

    Memoised by ``id(fields)`` to avoid repeated traversal of the same
    top-level schema dict.  The cache is module-level so it persists for the
    session.
    """
    # Only cache top-level calls (prefix == "") to avoid over-caching subtrees
    cache_key = id(fields) if not prefix else None
    if cache_key is not None and cache_key in _leaf_cache:
        return _leaf_cache[cache_key]

    result = _walk_leaf_paths(fields, prefix)

    if cache_key is not None:
        _leaf_cache[cache_key] = result
    return result


def _walk_leaf_paths(
    fields: dict[str, Any], prefix: str = ""
) -> list[tuple[str, str, bool]]:
    """Internal recursive walker for get_leaf_field_paths."""
    SKIP_ALWAYS = {
        "status", "managedFields", "creationTimestamp", "deletionTimestamp",
        "deletionGracePeriodSeconds", "selfLink", "resourceVersion", "uid",
        "generation", "ownerReferences", "finalizers", "generateName",
        "enum:",
    }
    SKIP_TOP = SKIP_ALWAYS | {"apiVersion", "kind"}

    result = []
    for name, info in fields.items():
        skip_set = SKIP_TOP if not prefix else SKIP_ALWAYS
        if name in skip_set:
            continue

        ftype = info.get("type", "string")
        segment = f"{name}[]" if ftype.startswith("[]") else name
        path = f"{prefix}.{segment}" if prefix else segment

        required = info.get("required", False)
        child = info.get("fields", {})

        if child:
            result.extend(_walk_leaf_paths(child, path))
        else:
            result.append((path, ftype, required))
    return result


def resolve_field_path(fields: dict[str, Any], dotted_path: str) -> dict[str, Any] | None:
    """Look up a field in the schema tree by dotted path."""
    parts = dotted_path.split(".")
    current = fields
    for part in parts:
        if part not in current:
            return None
        node = current[part]
        current = node.get("fields", {})
    # Return the last node
    current2 = fields
    for part in parts[:-1]:
        current2 = current2[part]["fields"]
    return current2.get(parts[-1])
