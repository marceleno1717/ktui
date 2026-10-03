"""Models package — re-exports core and shared abstractions."""

from ktui.models.core import K8sResource
from ktui.models.shared import (
    Container,
    ContainerPort,
    EnvVar,
    LabelSelector,
    ObjectMeta,
    PodSpec,
    PodTemplateSpec,
    ResourceRequirements,
)

__all__ = [
    "Container",
    "ContainerPort",
    "EnvVar",
    "K8sResource",
    "LabelSelector",
    "ObjectMeta",
    "PodSpec",
    "PodTemplateSpec",
    "ResourceRequirements",
]
