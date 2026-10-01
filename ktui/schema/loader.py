"""Load and query the k8s_schema.json database."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).parent.parent / "data" / "k8s_schema.json"


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def get_all_resources() -> list[dict[str, Any]]:
    """Return all resource entries sorted by kind."""
    return sorted(load_schema()["resources"], key=lambda r: r["kind"])


def get_resource(kind: str) -> dict[str, Any] | None:
    """Return a single resource entry by kind."""
    for r in load_schema()["resources"]:
        if r["kind"] == kind:
            return r
    return None


def get_common_fields(kind: str) -> list[str]:
    """Return the curated list of common field paths for a kind."""
    r = get_resource(kind)
    return r["common_fields"] if r else []


def get_all_field_paths(fields: dict, prefix: str = "") -> list[tuple[str, str]]:
    """
    Recursively walk the fields tree and return a flat list of
    (dotted_path, type_string) tuples.
    """
    result = []
    for name, info in fields.items():
        path = f"{prefix}.{name}" if prefix else name
        result.append((path, info.get("type", "string")))
        child = info.get("fields", {})
        if child:
            result.extend(get_all_field_paths(child, path))
    return result


def get_leaf_field_paths(fields: dict, prefix: str = "") -> list[tuple[str, str, bool]]:
    """
    Walk field tree; return (dotted_path, type, required) only for leaf fields
    (those with no children, i.e., actual scalar values).
    Skip status subtrees and internal K8s metadata fields.
    """
    # Fields to skip at any level
    SKIP_ALWAYS = {
        "status", "managedFields", "creationTimestamp", "deletionTimestamp",
        "deletionGracePeriodSeconds", "selfLink", "resourceVersion", "uid",
        "generation", "ownerReferences", "finalizers", "generateName",
        "enum:",
    }
    # Fields to skip only at the top level
    SKIP_TOP = SKIP_ALWAYS | {"apiVersion", "kind"}

    result = []
    for name, info in fields.items():
        skip_set = SKIP_TOP if not prefix else SKIP_ALWAYS
        if name in skip_set:
            continue
        
        # Append [] to array types so paths correctly indicate arrays
        ftype = info.get("type", "string")
        segment = f"{name}[]" if ftype.startswith("[]") else name
        path = f"{prefix}.{segment}" if prefix else segment
        
        required = info.get("required", False)
        child = info.get("fields", {})

        if child:
            result.extend(get_leaf_field_paths(child, path))
        else:
            result.append((path, ftype, required))
    return result


def resolve_field_path(fields: dict, dotted_path: str) -> dict | None:
    """Look up a field in the schema tree by dotted path."""
    parts = dotted_path.split(".")
    current = fields
    for part in parts:
        if part not in current:
            return None
        node = current[part]
        current = node.get("fields", {})
    # Return the last node
    parts2 = dotted_path.split(".")
    current2 = fields
    for part in parts2[:-1]:
        current2 = current2[part]["fields"]
    return current2.get(parts2[-1])
