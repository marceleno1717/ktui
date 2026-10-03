#!/usr/bin/env python3
"""
Build k8s_schema.json from `kubectl explain <resource> --recursive`.

For each resource, parses the recursive field tree and annotates fields
as 'common' (shown by default in TUI) or 'advanced' (popup/optional).
"""

import json
import subprocess
import sys
from typing import Any

# Resources to include, with their apiGroup info
RESOURCES = [
    {"kind": "Deployment",              "resource": "deployment",             "apiVersion": "apps/v1"},
    {"kind": "Service",                 "resource": "service",                "apiVersion": "v1"},
    {"kind": "ConfigMap",               "resource": "configmap",              "apiVersion": "v1"},
    {"kind": "Pod",                     "resource": "pod",                    "apiVersion": "v1"},
    {"kind": "StatefulSet",             "resource": "statefulset",            "apiVersion": "apps/v1"},
    {"kind": "DaemonSet",               "resource": "daemonset",              "apiVersion": "apps/v1"},
    {"kind": "Job",                     "resource": "job",                    "apiVersion": "batch/v1"},
    {"kind": "CronJob",                 "resource": "cronjob",                "apiVersion": "batch/v1"},
    {"kind": "Ingress",                 "resource": "ingress",                "apiVersion": "networking.k8s.io/v1"},
    {"kind": "PersistentVolumeClaim",   "resource": "persistentvolumeclaim",  "apiVersion": "v1"},
    {"kind": "PersistentVolume",        "resource": "persistentvolume",       "apiVersion": "v1"},
    {"kind": "HorizontalPodAutoscaler", "resource": "horizontalpodautoscaler","apiVersion": "autoscaling/v2"},
    {"kind": "ServiceAccount",          "resource": "serviceaccount",         "apiVersion": "v1"},
    {"kind": "Role",                    "resource": "role",                   "apiVersion": "rbac.authorization.k8s.io/v1"},
    {"kind": "RoleBinding",             "resource": "rolebinding",            "apiVersion": "rbac.authorization.k8s.io/v1"},
    {"kind": "ClusterRole",             "resource": "clusterrole",            "apiVersion": "rbac.authorization.k8s.io/v1"},
    {"kind": "ClusterRoleBinding",      "resource": "clusterrolebinding",     "apiVersion": "rbac.authorization.k8s.io/v1"},
    {"kind": "NetworkPolicy",           "resource": "networkpolicy",          "apiVersion": "networking.k8s.io/v1"},
    {"kind": "Namespace",               "resource": "namespace",              "apiVersion": "v1"},
    {"kind": "Secret",                  "resource": "secret",                 "apiVersion": "v1"},
    {"kind": "LimitRange",              "resource": "limitrange",             "apiVersion": "v1"},
    {"kind": "ResourceQuota",           "resource": "resourcequota",          "apiVersion": "v1"},
]

# Which fields are 'common' (shown at top / always visible) for each resource.
# These are hand-curated: the 80% use-case fields.
COMMON_FIELDS: dict[str, list[str]] = {
    "Deployment": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.replicas",
        "spec.selector.matchLabels",
        "spec.template.metadata.labels",
        "spec.template.spec.containers[].name",
        "spec.template.spec.containers[].image",
        "spec.template.spec.containers[].ports[].containerPort",
        "spec.template.spec.containers[].env[].name",
        "spec.template.spec.containers[].env[].value",
        "spec.template.spec.containers[].resources.requests.cpu",
        "spec.template.spec.containers[].resources.requests.memory",
        "spec.template.spec.containers[].resources.limits.cpu",
        "spec.template.spec.containers[].resources.limits.memory",
    ],
    "Service": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.selector",
        "spec.type",
        "spec.ports[].port",
        "spec.ports[].targetPort",
        "spec.ports[].protocol",
        "spec.ports[].name",
    ],
    "ConfigMap": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "data",
        "binaryData",
    ],
    "Pod": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.containers[].name",
        "spec.containers[].image",
        "spec.containers[].ports[].containerPort",
        "spec.containers[].env[].name",
        "spec.containers[].env[].value",
        "spec.containers[].resources.requests.cpu",
        "spec.containers[].resources.requests.memory",
        "spec.restartPolicy",
        "spec.serviceAccountName",
    ],
    "StatefulSet": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.replicas",
        "spec.serviceName",
        "spec.selector.matchLabels",
        "spec.template.metadata.labels",
        "spec.template.spec.containers[].name",
        "spec.template.spec.containers[].image",
        "spec.template.spec.containers[].ports[].containerPort",
        "spec.volumeClaimTemplates[].metadata.name",
        "spec.volumeClaimTemplates[].spec.accessModes",
        "spec.volumeClaimTemplates[].spec.resources.requests.storage",
    ],
    "DaemonSet": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.selector.matchLabels",
        "spec.template.metadata.labels",
        "spec.template.spec.containers[].name",
        "spec.template.spec.containers[].image",
        "spec.template.spec.containers[].ports[].containerPort",
        "spec.updateStrategy.type",
    ],
    "Job": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.completions",
        "spec.parallelism",
        "spec.backoffLimit",
        "spec.template.spec.containers[].name",
        "spec.template.spec.containers[].image",
        "spec.template.spec.restartPolicy",
    ],
    "CronJob": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.schedule",
        "spec.suspend",
        "spec.jobTemplate.spec.template.spec.containers[].name",
        "spec.jobTemplate.spec.template.spec.containers[].image",
        "spec.jobTemplate.spec.template.spec.restartPolicy",
        "spec.successfulJobsHistoryLimit",
        "spec.failedJobsHistoryLimit",
    ],
    "Ingress": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "metadata.annotations",
        "spec.ingressClassName",
        "spec.rules[].host",
        "spec.rules[].http.paths[].path",
        "spec.rules[].http.paths[].pathType",
        "spec.rules[].http.paths[].backend.service.name",
        "spec.rules[].http.paths[].backend.service.port.number",
        "spec.tls[].hosts",
        "spec.tls[].secretName",
    ],
    "PersistentVolumeClaim": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "spec.accessModes",
        "spec.storageClassName",
        "spec.resources.requests.storage",
        "spec.volumeMode",
    ],
    "PersistentVolume": [
        "metadata.name",
        "metadata.labels",
        "spec.capacity.storage",
        "spec.accessModes",
        "spec.persistentVolumeReclaimPolicy",
        "spec.storageClassName",
        "spec.volumeMode",
        "spec.hostPath.path",
        "spec.nfs.server",
        "spec.nfs.path",
    ],
    "HorizontalPodAutoscaler": [
        "metadata.name",
        "metadata.namespace",
        "spec.scaleTargetRef.apiVersion",
        "spec.scaleTargetRef.kind",
        "spec.scaleTargetRef.name",
        "spec.minReplicas",
        "spec.maxReplicas",
        "spec.metrics[].type",
        "spec.metrics[].resource.name",
        "spec.metrics[].resource.target.type",
        "spec.metrics[].resource.target.averageUtilization",
    ],
    "ServiceAccount": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "automountServiceAccountToken",
        "imagePullSecrets[].name",
    ],
    "Role": [
        "metadata.name",
        "metadata.namespace",
        "rules[].apiGroups",
        "rules[].resources",
        "rules[].verbs",
        "rules[].resourceNames",
    ],
    "RoleBinding": [
        "metadata.name",
        "metadata.namespace",
        "roleRef.apiGroup",
        "roleRef.kind",
        "roleRef.name",
        "subjects[].kind",
        "subjects[].name",
        "subjects[].namespace",
    ],
    "ClusterRole": [
        "metadata.name",
        "metadata.labels",
        "rules[].apiGroups",
        "rules[].resources",
        "rules[].verbs",
        "rules[].resourceNames",
        "aggregationRule.clusterRoleSelectors[].matchLabels",
    ],
    "ClusterRoleBinding": [
        "metadata.name",
        "metadata.labels",
        "roleRef.apiGroup",
        "roleRef.kind",
        "roleRef.name",
        "subjects[].kind",
        "subjects[].name",
        "subjects[].namespace",
    ],
    "NetworkPolicy": [
        "metadata.name",
        "metadata.namespace",
        "spec.podSelector.matchLabels",
        "spec.policyTypes",
        "spec.ingress[].from[].podSelector.matchLabels",
        "spec.ingress[].from[].namespaceSelector.matchLabels",
        "spec.ingress[].ports[].port",
        "spec.ingress[].ports[].protocol",
        "spec.egress[].to[].podSelector.matchLabels",
        "spec.egress[].ports[].port",
    ],
    "Namespace": [
        "metadata.name",
        "metadata.labels",
        "metadata.annotations",
    ],
    "Secret": [
        "metadata.name",
        "metadata.namespace",
        "metadata.labels",
        "type",
        "data",
        "stringData",
    ],
    "LimitRange": [
        "metadata.name",
        "metadata.namespace",
        "spec.limits[].type",
        "spec.limits[].default.cpu",
        "spec.limits[].default.memory",
        "spec.limits[].defaultRequest.cpu",
        "spec.limits[].defaultRequest.memory",
        "spec.limits[].max.cpu",
        "spec.limits[].max.memory",
    ],
    "ResourceQuota": [
        "metadata.name",
        "metadata.namespace",
        "spec.hard",
        "spec.scopes",
    ],
}


def run_explain(resource: str) -> str:
    result = subprocess.run(
        ["kubectl", "explain", resource, "--recursive"],
        capture_output=True, text=True, timeout=15
    )
    return result.stdout


def parse_explain(output: str) -> dict[str, Any]:
    """
    Parse kubectl explain --recursive output into a structured dict.
    Returns a tree of fields like:
      { "apiVersion": {"type": "string", "required": False, "children": {}} ... }
    """
    lines = output.splitlines()
    fields_start = False
    field_lines = []
    description = []

    for line in lines:
        if line.startswith("FIELDS:"):
            fields_start = True
            continue
        if fields_start:
            field_lines.append(line)
        elif line.startswith("DESCRIPTION:"):
            pass
        elif not fields_start and line.strip() and not any(line.startswith(x) for x in ["KIND:", "VERSION:", "GROUP:", "RESOURCE:"]):
            description.append(line.strip())

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict]] = [(-1, root)]

    for line in field_lines:
        if not line.strip():
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        # indent is in multiples of 2
        level = indent // 2

        # Parse: "fieldName  <type> [-required-]" or "fieldName  <type>"
        parts = stripped.split()
        if not parts:
            continue
        name = parts[0]
        field_type = ""
        required = False
        enum_vals: list[str] = []

        for i, p in enumerate(parts):
            if p.startswith("<") and p.endswith(">"):
                field_type = p[1:-1]
            if p == "-required-":
                required = True
            if p == "enum:":
                # remaining are the enum values
                raw = " ".join(parts[i+1:])
                enum_vals = [v.strip().rstrip(",") for v in raw.split(",") if v.strip() and v.strip() != "...."]

        # Pop stack back to parent level
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()

        parent = stack[-1][1]
        node: dict[str, Any] = {
            "type": field_type,
            "required": required,
        }
        if enum_vals:
            node["enum"] = enum_vals
        node["fields"] = {}
        parent[name] = node
        stack.append((level, node["fields"]))

    return root


def build_schema() -> dict[str, Any]:
    schema: dict[str, Any] = {"resources": []}

    for resource_def in RESOURCES:
        kind = resource_def["kind"]
        resource = resource_def["resource"]
        api_version = resource_def["apiVersion"]

        print(f"Processing {kind}...", file=sys.stderr)
        output = run_explain(resource)
        if not output:
            print("  SKIPPED (no output)", file=sys.stderr)
            continue

        fields = parse_explain(output)
        common = COMMON_FIELDS.get(kind, [])

        schema["resources"].append({
            "kind": kind,
            "apiVersion": api_version,
            "resource": resource,
            "common_fields": common,
            "fields": fields,
        })
        print(f"  OK - {len(fields)} top-level fields", file=sys.stderr)

    return schema


if __name__ == "__main__":
    schema = build_schema()

    # P1-6: Write per-kind shards + index
    import os
    shards_dir = "src/ktui/data/schemas"
    os.makedirs(shards_dir, exist_ok=True)

    index_entries = []
    for r in schema["resources"]:
        kind = r["kind"]
        shard_path = os.path.join(shards_dir, f"{kind.lower()}.json")
        with open(shard_path, "w") as f:
            json.dump(r, f, indent=2)
        print(f"  shard: {shard_path}", file=sys.stderr)
        index_entries.append({
            "kind": r["kind"],
            "apiVersion": r.get("apiVersion", ""),
            "resource": r.get("resource", kind.lower() + "s"),
            "common_fields": r.get("common_fields", []),
        })

    index_path = os.path.join(shards_dir, "index.json")
    with open(index_path, "w") as f:
        json.dump({"resources": index_entries}, f, indent=2)
    print(f"  index: {index_path}", file=sys.stderr)

