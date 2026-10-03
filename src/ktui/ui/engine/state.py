"""Nested dict/list mutation helper for form state tracking.

This is the single source of truth for reading and writing into the
``_form_data`` dict that the main screen maintains.  Both the schema-driven
form builder and the main screen import from here — no duplicate helpers.

Path formats accepted
---------------------
- Dot-separated string keys:      ``["spec", "replicas"]``
- Numeric string keys (list idx): ``["spec", "containers", "0", "name"]``
- Bracketed indices ([N] suffix):  ``["spec", "containers[0]", "name"]``

The bracketed form is produced by ``decode_path`` in schema_form_builder when
the widget ID encodes an array element (``-ARR0`` → ``[0]``).
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def set_nested(root: dict[str, Any] | list, path: list[str], value: Any) -> None:
    """Set ``value`` at ``path`` inside a nested dict/list structure.

    Supports both plain digit keys and bracketed-index keys like
    ``"containers[0]"``.  Intermediate containers are created automatically.

    Examples::

        data = {}
        set_nested(data, ["spec", "containers", "0", "name"], "nginx")
        # data == {"spec": {"containers": [{"name": "nginx"}]}}

        set_nested(data, ["spec", "containers[0]", "name"], "nginx")
        # same result
    """
    if not path:
        return

    # Normalise: expand "foo[N]" into ("foo", N) pairs so the recursive
    # logic below only ever sees plain string keys or plain int indices.
    expanded = _expand_path(path)
    _set(root, expanded, value)


def get_nested(root: dict[str, Any] | list, path: list[str], default: Any = None) -> Any:
    """Return the value at ``path``, or ``default`` if not found."""
    expanded = _expand_path(path)
    node: Any = root
    for key in expanded:
        try:
            node = node[key]
        except (KeyError, IndexError, TypeError):
            return default
    return node


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

_BRACKET_RE = re.compile(r"^(.*?)\[(\d+)\]$")


def _expand_path(path: list[str]) -> list[str | int]:
    """Convert path segments that contain ``[N]`` suffixes to (key, int) pairs.

    ``"containers[0]"`` → ``["containers", 0]``
    ``"containers"``    → ``["containers"]``
    ``"0"``             → ``[0]``   (plain digit key → int)
    """
    result: list[str | int] = []
    for seg in path:
        m = _BRACKET_RE.match(seg)
        if m:
            name, idx_str = m.group(1), m.group(2)
            if name:
                result.append(name)
            result.append(int(idx_str))
        elif seg.isdigit():
            result.append(int(seg))
        else:
            result.append(seg)
    return result


def _set(root: Any, path: list[str | int], value: Any) -> None:
    """Recursive worker that only ever sees plain str/int keys."""
    if not path:
        return

    key = path[0]
    rest = path[1:]

    if isinstance(root, list):
        assert isinstance(key, int), f"Expected int index for list, got {key!r}"
        while len(root) <= key:
            root.append({})
        if not rest:
            root[key] = value
        else:
            _ensure_container(root, key, rest[0])
            _set(root[key], rest, value)
    else:  # dict
        if not rest:
            # Remove key if value is empty (keeps _form_data clean)
            if value is None or value == "":
                root.pop(key, None)
            else:
                root[key] = value
        else:
            _ensure_container(root, key, rest[0])
            _set(root[key], rest, value)


def _ensure_container(parent: dict[str, Any] | list, key: str | int, next_key: str | int) -> None:
    """Ensure ``parent[key]`` is the right container type for ``next_key``."""
    need_list = isinstance(next_key, int)
    if isinstance(parent, list):
        idx = int(key)
        if need_list and not isinstance(parent[idx], list):
            parent[idx] = []
        elif not need_list and not isinstance(parent[idx], dict):
            parent[idx] = {}
    else:
        if need_list and not isinstance(parent.get(key), list):  # type: ignore[arg-type]
            parent[key] = []  # type: ignore[index]
        elif not need_list and not isinstance(parent.get(key), dict):  # type: ignore[arg-type]
            parent[key] = {}  # type: ignore[index]
