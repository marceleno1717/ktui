"""YAML emission for the schema-driven form — ruamel.yaml only.

This replaces the old PyYAML-based emitter.  All code that previously
did ``from ktui.schema.emitter import emit_yaml_from_dict`` continues to
work unchanged; we just produce cleaner 2-space-indented output now.

The ``_clean`` function is exported because the validation layer imports it.
"""

from __future__ import annotations

import io
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean(value: Any) -> Any:
    """Recursively remove empty strings, None, and empty dicts/lists."""
    if isinstance(value, dict):
        cleaned = {k: _clean(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        cleaned = [_clean(i) for i in value]
        return [i for i in cleaned if i not in (None, "", [], {})]
    return value


def _to_commented_map(data: Any) -> Any:
    """Recursively convert plain dicts to CommentedMap (preserves insertion order)."""
    if isinstance(data, dict):
        cm = CommentedMap()
        for k, v in data.items():
            cm[k] = _to_commented_map(v)
        return cm
    if isinstance(data, list):
        return [_to_commented_map(item) for item in data]
    return data


def _build_yaml() -> YAML:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 120
    return yaml


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_yaml_from_dict(data: dict[str, Any]) -> str:
    """Emit YAML from a nested dict, stripping empty values.

    Uses ruamel.yaml so output is consistent with the generator module
    (2-space mapping indent, 4-space sequence indent, 2-space offset).
    """
    cleaned = _clean(data)
    commented = _to_commented_map(cleaned)
    stream = io.StringIO()
    _build_yaml().dump(commented, stream)
    return stream.getvalue()
