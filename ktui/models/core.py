"""Base classes for all resource models.

Every Kubernetes/OpenShift resource inherits from K8sResource.
It enforces the top-level structure (apiVersion, kind, metadata)
and provides helpers used by the YAML emitter and form engine.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class K8sResource(BaseModel):
    """Root base for every K8s / OC resource model.

    Subclasses must supply:
        apiVersion  – locked via ``Literal[...]`` default
        kind        – locked via ``Literal[...]`` default
        metadata    – instance of ObjectMeta
        spec        – resource-specific spec model (if applicable)
    """

    model_config = ConfigDict(
        # Allow both alias and Python name when constructing models.
        populate_by_name=True,
        # Exclude fields that were never set so YAML stays clean.
        # Callers use model_dump(exclude_unset=True) to exploit this.
    )
