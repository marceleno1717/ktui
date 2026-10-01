"""Kubectl wrapper for cluster interactions."""

import json
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClusterStatus:
    connected: bool
    context_name: Optional[str]
    namespace: str = "default"
    error: Optional[str] = None


def run_kubectl(args: list[str], timeout: int = 5) -> tuple[int, str, str]:
    """Run a kubectl command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["kubectl"] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", "kubectl not found in PATH"
    except subprocess.TimeoutExpired:
        return 124, "", "kubectl command timed out"
    except Exception as e:
        return 1, "", str(e)


def get_current_context() -> str:
    code, out, _ = run_kubectl(["config", "current-context"])
    if code == 0:
        return out
    return ""


def get_all_contexts() -> list[str]:
    code, out, _ = run_kubectl(["config", "get-contexts", "-o", "name"])
    if code == 0:
        return [c for c in out.splitlines() if c.strip()]
    return []


def use_context(context_name: str) -> bool:
    code, _, _ = run_kubectl(["config", "use-context", context_name])
    return code == 0


def get_current_namespace() -> str:
    code, out, _ = run_kubectl(["config", "view", "--minify", "-o", "jsonpath={..namespace}"])
    if code == 0 and out:
        return out
    return "default"


def get_all_namespaces() -> list[str]:
    code, out, _ = run_kubectl(["get", "namespaces", "-o", "jsonpath={.items[*].metadata.name}"])
    if code == 0:
        return [n for n in out.split() if n.strip()]
    return ["default"]


def set_namespace(namespace: str) -> bool:
    code, _, _ = run_kubectl(["config", "set-context", "--current", f"--namespace={namespace}"])
    return code == 0


def check_connection() -> ClusterStatus:
    """Check if connected to a valid cluster."""
    ctx = get_current_context()
    if not ctx:
        return ClusterStatus(connected=False, context_name=None, error="No current context")

    # Fast check: get namespaces or version
    code, _, err = run_kubectl(["get", "namespace", "default"], timeout=3)
    ns = get_current_namespace()
    if code == 0:
        return ClusterStatus(connected=True, context_name=ctx, namespace=ns)
    return ClusterStatus(connected=False, context_name=ctx, namespace=ns, error=err)


def get_cluster_resources(kind: str, namespace: str = "") -> list[dict]:
    """Fetch resources of a specific kind from the cluster as JSON."""
    args = ["get", kind, "-o", "json"]
    if namespace:
        args.extend(["-n", namespace])
    
    code, out, _ = run_kubectl(args, timeout=10)
    if code == 0 and out:
        try:
            data = json.loads(out)
            return data.get("items", [])
        except json.JSONDecodeError:
            pass
    return []
