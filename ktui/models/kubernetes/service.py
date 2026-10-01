"""Kubernetes Service resource model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ktui.models.core import K8sResource
from ktui.models.shared import ObjectMeta
from ktui.registry import register_resource


class ServicePort(BaseModel):
    """Port configuration for a Service."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(
        default="",
        description="Name of this port within the service.",
    )
    protocol: Literal["TCP", "UDP", "SCTP"] = Field(
        default="TCP",
        description="IP protocol for this port.",
    )
    port: int = Field(
        description="The port that will be exposed by this service.",
    )
    targetPort: str = Field(  # noqa: N815
        default="",
        description="Number or name of the port to access on the pods targeted by the service. Defaults to the port field if not specified.",
    )
    nodePort: int | None = Field(  # noqa: N815
        default=None,
        description="The port on each node on which this service is exposed when type is NodePort or LoadBalancer.",
    )


class ServiceSpec(BaseModel):
    """Spec describing the desired behavior of the Service."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["ClusterIP", "NodePort", "LoadBalancer", "ExternalName"] = Field(
        default="ClusterIP",
        description="Type of Service. Defaults to ClusterIP.",
    )
    selector: dict[str, str] = Field(
        default_factory=dict,
        description="Route service traffic to pods with label keys and values matching this selector.",
    )
    ports: list[ServicePort] = Field(
        default_factory=list,
        description="List of ports that are exposed by this service.",
    )
    clusterIP: str = Field(  # noqa: N815
        default="",
        description="IP address of the service. Set to 'None' for headless services.",
    )
    externalName: str = Field(  # noqa: N815
        default="",
        description="External domain name, required when type is ExternalName.",
    )


@register_resource(platform="kubernetes", group="core")
class Service(K8sResource):
    """Kubernetes Service — network endpoint to expose Pods."""

    apiVersion: Literal["v1"] = Field(
        default="v1",
        description="API version for Service resources.",
    )
    kind: Literal["Service"] = Field(
        default="Service",
        description="Resource kind.",
    )
    metadata: ObjectMeta = Field(
        default_factory=ObjectMeta,
        description="Standard object metadata.",
    )
    spec: ServiceSpec = Field(
        default_factory=ServiceSpec,
        description="Spec defines the desired state of the Service.",
    )
