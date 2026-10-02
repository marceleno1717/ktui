"""Shared / reusable Kubernetes object models.

These are defined once and composed into multiple resource models.
No resource should re-implement ObjectMeta, Container, etc. from scratch.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class ObjectMeta(BaseModel):
    """Standard Kubernetes ObjectMeta.

    Only the most commonly used fields are exposed here.
    Obscure fields (ownerReferences, finalizers, managedFields) are omitted
    intentionally — they can be added when needed without breaking anything.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(
        default="",
        description="Name must be unique within a namespace.",
    )
    namespace: str = Field(
        default="",
        description="Namespace this resource lives in. Empty = cluster-scoped or default.",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Key/value pairs for organizing and selecting resources.",
    )
    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary non-identifying metadata.",
    )


# ---------------------------------------------------------------------------
# Container sub-objects
# ---------------------------------------------------------------------------


class ContainerPort(BaseModel):
    """A single port exposed by a container."""

    model_config = ConfigDict(populate_by_name=True)

    containerPort: int = Field(  # noqa: N815
        description="Port number to expose.",
    )
    name: str = Field(
        default="",
        description="Optional name for the port.",
    )
    protocol: Literal["TCP", "UDP", "SCTP"] = Field(
        default="TCP",
        description="Protocol for this port.",
    )
    hostPort: int | None = Field(  # noqa: N815
        default=None,
        description="Host port to bind. Rarely needed.",
    )


class EnvVar(BaseModel):
    """A single environment variable as a name/value pair."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(description="Environment variable name.")
    value: str = Field(default="", description="Literal string value.")


class ResourceRequirements(BaseModel):
    """CPU and memory requests and limits for a container."""

    model_config = ConfigDict(populate_by_name=True)

    requests: dict[str, str] = Field(
        default_factory=dict,
        description='Minimum required resources. E.g. {"cpu": "250m", "memory": "64Mi"}.',
    )
    limits: dict[str, str] = Field(
        default_factory=dict,
        description='Maximum allowed resources. E.g. {"cpu": "500m", "memory": "128Mi"}.',
    )


class Container(BaseModel):
    """A single container definition within a Pod spec."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(description="Unique name for this container within the Pod.")
    image: str = Field(description="Container image, e.g. nginx:1.27.")
    imagePullPolicy: Literal["Always", "IfNotPresent", "Never"] | None = Field(  # noqa: N815
        default=None,
        description="When to pull the image.",
    )
    command: list[str] = Field(
        default_factory=list,
        description="Entrypoint command (overrides Docker ENTRYPOINT).",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Arguments to the entrypoint command.",
    )
    ports: list[ContainerPort] = Field(
        default_factory=list,
        description="Ports exposed by this container.",
    )
    env: list[EnvVar] = Field(
        default_factory=list,
        description="Environment variables.",
    )
    resources: ResourceRequirements = Field(
        default_factory=ResourceRequirements,
        description="Compute resource requests and limits.",
    )
    workingDir: str = Field(  # noqa: N815
        default="",
        description="Container's working directory.",
    )


# ---------------------------------------------------------------------------
# Pod-level sub-objects
# ---------------------------------------------------------------------------


class PodSpec(BaseModel):
    """Core Pod spec fields.

    Reused by Pod directly and embedded inside PodTemplateSpec for
    Deployment, DaemonSet, Job, etc.
    """

    model_config = ConfigDict(populate_by_name=True)

    containers: list[Container] = Field(
        default_factory=list,
        description="List of containers belonging to the Pod. At least one required.",
    )
    initContainers: list[Container] = Field(  # noqa: N815
        default_factory=list,
        description="Initialization containers run before app containers.",
    )
    restartPolicy: Literal["Always", "OnFailure", "Never"] = Field(  # noqa: N815
        default="Always",
        description="Restart policy for all containers in the Pod.",
    )
    serviceAccountName: str = Field(  # noqa: N815
        default="",
        description="ServiceAccount to run the Pod as.",
    )
    nodeName: str = Field(  # noqa: N815
        default="",
        description="Request scheduling to a specific node.",
    )
    hostNetwork: bool = Field(  # noqa: N815
        default=False,
        description="Use the host's network namespace.",
    )
    dnsPolicy: Literal["ClusterFirst", "ClusterFirstWithHostNet", "Default", "None"] = Field(  # noqa: N815
        default="ClusterFirst",
        description="DNS policy for the Pod.",
    )


# ---------------------------------------------------------------------------
# Selector and Pod template — shared by Deployment, DaemonSet, StatefulSet …
# ---------------------------------------------------------------------------


class LabelSelector(BaseModel):
    """Label selector used by controllers to identify owned Pods."""

    model_config = ConfigDict(populate_by_name=True)

    matchLabels: dict[str, str] = Field(  # noqa: N815
        default_factory=dict,
        description='Map of key/value pairs. E.g. {"app": "nginx"}.',
    )


class PodTemplateSpec(BaseModel):
    """Template for Pods created by a controller (Deployment, DaemonSet, …)."""

    model_config = ConfigDict(populate_by_name=True)

    metadata: ObjectMeta = Field(
        default_factory=ObjectMeta,
        description="Metadata applied to each Pod created from this template.",
    )
    spec: PodSpec = Field(
        default_factory=PodSpec,
        description="Spec for the Pods created from this template.",
    )
