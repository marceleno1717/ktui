"""Kubernetes ConfigMap resource model."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ktui.models.core import K8sResource
from ktui.models.shared import ObjectMeta
from ktui.registry import register_resource


@register_resource(platform="kubernetes", group="core")
class ConfigMap(K8sResource):
    """Kubernetes ConfigMap — key-value store for configuration data."""

    apiVersion: Literal["v1"] = Field(
        default="v1",
        description="API version for ConfigMap resources.",
    )
    kind: Literal["ConfigMap"] = Field(
        default="ConfigMap",
        description="Resource kind.",
    )
    metadata: ObjectMeta = Field(
        default_factory=ObjectMeta,
        description="Standard object metadata.",
    )
    data: dict[str, str] = Field(
        default_factory=dict,
        description="Data contains the configuration data. Each key must consist of alphanumeric characters, '-', '_' or '.'.",
    )
    binaryData: dict[str, str] = Field(  # noqa: N815
        default_factory=dict,
        description="BinaryData contains the binary data. Each key must consist of alphanumeric characters, '-', '_' or '.'. Values must be base64-encoded strings.",
    )
    immutable: bool = Field(
        default=False,
        description="If set to true, ensures that data stored in the ConfigMap cannot be updated.",
    )
