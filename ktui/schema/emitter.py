"""YAML emitter for schema-driven form data.

Takes a plain dict (form state) and emits clean YAML.
No Pydantic validation — data is emitted as-is, omitting empty values.
"""

from __future__ import annotations

from typing import Any

import yaml


def _clean(value: Any) -> Any:
    """Recursively remove empty strings, None, and empty dicts/lists."""
    if isinstance(value, dict):
        cleaned = {k: _clean(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        cleaned = [_clean(i) for i in value]
        return [i for i in cleaned if i not in (None, "", [], {})]
    return value


def emit_yaml_from_dict(data: dict[str, Any]) -> str:
    """Emit YAML from a nested dict, removing empty values."""
    cleaned = _clean(data)
    return yaml.dump(cleaned, default_flow_style=False, allow_unicode=True, sort_keys=False)
