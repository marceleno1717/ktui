"""OpenShift Route resource model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ktui.models.core import K8sResource
from ktui.models.shared import ObjectMeta
from ktui.registry import register_resource


class RouteTargetReference(BaseModel):
    """Reference to the service this route points to."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["Service"] = Field(
        default="Service",
        description="The kind of target. Usually 'Service'.",
    )
    name: str = Field(
        default="",
        description="Name of the service/target.",
    )
    weight: int = Field(
        default=100,
        description="Weight for this target.",
    )


class RoutePort(BaseModel):
    """Specific port to use on the target service."""

    model_config = ConfigDict(populate_by_name=True)

    targetPort: str = Field(
        default="",
        description="The target port on pods selected by the service.",
    )


class TLSConfig(BaseModel):
    """TLS configuration for a Route."""

    model_config = ConfigDict(populate_by_name=True)

    termination: Literal["edge", "passthrough", "reencrypt"] | None = Field(
        default=None,
        description="TLS termination type.",
    )
    insecureEdgeTerminationPolicy: Literal["Allow", "Redirect", "None"] | None = Field(
        default=None,
        description="Policy for insecure connections.",
    )


class RouteSpec(BaseModel):
    """Spec describing the desired behavior of the Route."""

    model_config = ConfigDict(populate_by_name=True)

    host: str = Field(
        default="",
        description="Hostname for the route. If empty, OpenShift generates one.",
    )
    path: str = Field(
        default="",
        description="Path that the router watches for.",
    )
    to: RouteTargetReference = Field(
        default_factory=RouteTargetReference,
        description="The target this route points to (usually a Service).",
    )
    port: RoutePort | None = Field(
        default=None,
        description="Specific port to use on the target service.",
    )
    tls: TLSConfig | None = Field(
        default=None,
        description="TLS configuration for the route.",
    )


@register_resource(platform="openshift", group="route.openshift.io")
class Route(K8sResource):
    """OpenShift Route — expose a service at a host name."""

    apiVersion: Literal["route.openshift.io/v1"] = Field(
        default="route.openshift.io/v1",
        description="API version for Route resources.",
    )
    kind: Literal["Route"] = Field(
        default="Route",
        description="Resource kind.",
    )
    metadata: ObjectMeta = Field(
        default_factory=ObjectMeta,
        description="Standard object metadata.",
    )
    spec: RouteSpec = Field(
        default_factory=RouteSpec,
        description="Spec defines the desired state of the Route.",
    )
