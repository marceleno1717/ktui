"""YAML serialization — decoupled from Textual widgets entirely.

All YAML emission goes through ``emit_yaml``. It accepts either:
- a ``K8sResource`` Pydantic model instance, or
- a plain ``dict`` (for cases where the model has already been dumped)

Design goals
------------
- Deterministic output (field order follows model definition, not alphabet).
- No empty/unset fields — uses ``exclude_unset=True, exclude_none=True``.
- Human-readable indentation (2 spaces, block style).
- Handles nested objects, lists, and dicts correctly.
- Raises ``YAMLEmitError`` on any serialization failure — never silently
  produces garbage.
"""

from __future__ import annotations

import io
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from ktui.models.core import K8sResource


class YAMLEmitError(Exception):
    """Raised when YAML serialization fails."""


def _to_commented_map(data: Any) -> Any:
    """Recursively convert dicts to CommentedMap to preserve insertion order."""
    if isinstance(data, dict):
        cm = CommentedMap()
        for k, v in data.items():
            cm[k] = _to_commented_map(v)
        return cm
    if isinstance(data, list):
        return [_to_commented_map(item) for item in data]
    return data


def _build_yaml() -> YAML:
    """Return a configured ruamel.yaml instance."""
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 120  # avoid line-wrapping in most cases
    return yaml


# Fields that must always appear in the YAML output regardless of whether
# the user explicitly set them (they have locked Literal defaults).
_ALWAYS_INCLUDE = {"apiVersion", "kind"}


def model_to_dict(resource: K8sResource) -> dict[str, Any]:
    """Convert a resource model to a clean dictionary.

    - ``apiVersion`` and ``kind`` are always included (they are Literal
      defaults but K8s requires them unconditionally).
    - All other unset / None fields are stripped.
    - Uses field aliases so output matches K8s API field names exactly.
    """
    # Full dump (no exclusions) to capture Literal defaults for apiVersion/kind.
    full: dict[str, Any] = resource.model_dump(by_alias=True)
    # Dump without defaults to know what the user explicitly set.
    unset_stripped: dict[str, Any] = resource.model_dump(
        exclude_unset=True,
        exclude_none=True,
        by_alias=True,
    )
    # Merge: always-include keys from full dump + user-set keys.
    result: dict[str, Any] = {}
    for key in _ALWAYS_INCLUDE:
        if key in full:
            result[key] = full[key]
    result.update(unset_stripped)
    return _strip_empty(result)



def _strip_empty(obj: Any) -> Any:
    """Recursively remove empty dicts and empty lists from a nested structure."""
    if isinstance(obj, dict):
        cleaned = {k: _strip_empty(v) for k, v in obj.items()}
        return {k: v for k, v in cleaned.items() if v not in (None, {}, [])}
    if isinstance(obj, list):
        cleaned = [_strip_empty(item) for item in obj]
        return [item for item in cleaned if item not in (None, {}, [])]
    return obj


def emit_yaml(resource: K8sResource | dict[str, Any]) -> str:
    """Serialize a resource or raw dict to a YAML string.

    Parameters
    ----------
    resource:
        A ``K8sResource`` subclass instance or a plain dictionary.

    Returns
    -------
    str
        Well-formatted YAML string ending with a newline.

    Raises
    ------
    YAMLEmitError
        If serialization fails for any reason.
    """
    try:
        if isinstance(resource, K8sResource):
            data = model_to_dict(resource)
        else:
            data = _strip_empty(resource)

        commented = _to_commented_map(data)
        stream = io.StringIO()
        _build_yaml().dump(commented, stream)
        return stream.getvalue()
    except Exception as exc:
        raise YAMLEmitError(f"Failed to serialize resource: {exc}") from exc
