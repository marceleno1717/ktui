"""Kubernetes Pod resource model."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ktui.models.core import K8sResource
from ktui.models.shared import ObjectMeta, PodSpec
from ktui.registry import register_resource


@register_resource(platform="kubernetes", group="core")
class Pod(K8sResource):
    """Kubernetes Pod — the smallest deployable unit.

    A Pod wraps one or more containers sharing network and storage.
    Pods are rarely created directly; use Deployment or DaemonSet in
    production. However, Pod is a fundamental resource for understanding
    K8s and for one-off debugging/testing tasks.
    """

    apiVersion: Literal["v1"] = Field(
        default="v1",
        description="API version for Pod resources.",
    )
    kind: Literal["Pod"] = Field(
        default="Pod",
        description="Resource kind.",
    )
    metadata: ObjectMeta = Field(
        default_factory=ObjectMeta,
        description="Standard object metadata.",
    )
    spec: PodSpec = Field(
        default_factory=PodSpec,
        description="Spec defines the desired state of the Pod.",
    )
