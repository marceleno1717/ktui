"""Nested dict/list mutation helper for form state tracking."""

from __future__ import annotations

from typing import Any


def set_nested(root: dict | list, path: list[str], value: Any) -> None:
    """Set ``value`` at ``path`` inside a nested dict/list structure.

    Digits in the path are treated as list indices.  Intermediate containers
    are created automatically (dict for string keys, list for digit keys).

    Example::

        data = {}
        set_nested(data, ["spec", "containers", "0", "name"], "nginx")
        # data == {"spec": {"containers": [{"name": "nginx"}]}}
    """
    if not path:
        return

    key = path[0]
    rest = path[1:]

    if isinstance(root, list):
        idx = int(key)
        while len(root) <= idx:
            root.append({})
        if not rest:
            root[idx] = value
        else:
            _ensure_container(root, idx, rest[0])
            set_nested(root[idx], rest, value)
    else:  # dict
        if not rest:
            root[key] = value
        else:
            _ensure_container(root, key, rest[0])
            set_nested(root[key], rest, value)


def _ensure_container(parent: dict | list, key: str | int, next_key: str) -> None:
    """Ensure parent[key] exists as the correct container type for next_key."""
    need_list = isinstance(next_key, str) and next_key.isdigit()
    if isinstance(parent, list):
        idx = int(key)
        if need_list and not isinstance(parent[idx], list):
            parent[idx] = []
        elif not need_list and not isinstance(parent[idx], dict):
            parent[idx] = {}
    else:
        if need_list and not isinstance(parent.get(key), list):
            parent[key] = []
        elif not need_list and not isinstance(parent.get(key), dict):
            parent[key] = {}
