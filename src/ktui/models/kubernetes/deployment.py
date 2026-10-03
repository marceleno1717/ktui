"""Kubernetes Deployment resource model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ktui.models.core import K8sResource
from ktui.models.shared import LabelSelector, ObjectMeta, PodTemplateSpec
from ktui.registry import register_resource

# ---------------------------------------------------------------------------
# Deployment-specific sub-objects
# ---------------------------------------------------------------------------


class RollingUpdateDeployment(BaseModel):
    """Parameters for the RollingUpdate deployment strategy."""

    model_config = ConfigDict(populate_by_name=True)

    maxUnavailable: str = Field(
        default="25%",
        description="Max Pods that can be unavailable during the update (number or %).",
    )
    maxSurge: str = Field(
        default="25%",
        description="Max Pods that can be scheduled above the desired count (number or %).",
    )


class DeploymentStrategy(BaseModel):
    """Strategy used to replace old Pods with new ones."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["RollingUpdate", "Recreate"] = Field(
        default="RollingUpdate",
        description="RollingUpdate replaces Pods gradually. Recreate kills all before creating new.",
    )
    rollingUpdate: RollingUpdateDeployment = Field(
        default_factory=RollingUpdateDeployment,
        description="Rolling update configuration. Only used when type=RollingUpdate.",
    )


class DeploymentSpec(BaseModel):
    """Spec describing the desired behaviour of the Deployment."""

    model_config = ConfigDict(populate_by_name=True)

    replicas: int = Field(
        default=1,
        description="Number of desired Pods.",
    )
    selector: LabelSelector = Field(
        default_factory=LabelSelector,
        description="Label selector that identifies the Pods managed by this Deployment.",
    )
    template: PodTemplateSpec = Field(
        default_factory=PodTemplateSpec,
        description="Template used to create new Pods.",
    )
    strategy: DeploymentStrategy = Field(
        default_factory=DeploymentStrategy,
        description="Update strategy for the Deployment.",
    )
    minReadySeconds: int = Field(
        default=0,
        description="Seconds a Pod must be ready before being considered available.",
    )
    revisionHistoryLimit: int = Field(
        default=10,
        description="Number of old ReplicaSets to retain for rollback.",
    )
    paused: bool = Field(
        default=False,
        description="Pause the Deployment. No new rollouts while paused.",
    )


# ---------------------------------------------------------------------------
# Deployment resource
# ---------------------------------------------------------------------------


@register_resource(platform="kubernetes", group="apps")
class Deployment(K8sResource):
    """Kubernetes Deployment — declarative Pod lifecycle management.

    Deployments are the standard way to run stateless workloads.
    They own a ReplicaSet which in turn owns Pods, enabling zero-downtime
    rolling updates and easy rollbacks.
    """

    apiVersion: Literal["apps/v1"] = Field(
        default="apps/v1",
        description="API version for Deployment resources.",
    )
    kind: Literal["Deployment"] = Field(
        default="Deployment",
        description="Resource kind.",
    )
    metadata: ObjectMeta = Field(
        default_factory=ObjectMeta,
        description="Standard object metadata.",
    )
    spec: DeploymentSpec = Field(
        default_factory=DeploymentSpec,
        description="Spec defines the desired state of the Deployment.",
    )
