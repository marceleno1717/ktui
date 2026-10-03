"""Kubectl wrapper for cluster interactions.

P1-9 update:
- ``run_kubectl_async`` wraps subprocess in ``asyncio.to_thread`` — no UI freeze.
- ``run_kubectl`` remains as the sync shim for callers that need it.
- Frequently called getters (contexts, namespaces, connection check) are
  backed by ``K8S_CACHE`` (30-second TTL).
- Retries: 1 retry with 0.5 s backoff for transient errors.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass

from ktui.kubernetes.cache import K8S_CACHE


@dataclass
class ClusterStatus:
    connected: bool
    context_name: str | None
    namespace: str = "default"
    error: str | None = None


# ---------------------------------------------------------------------------
# Core subprocess runner
# ---------------------------------------------------------------------------

def run_kubectl(args: list[str], timeout: int = 5) -> tuple[int, str, str]:
    """Run a kubectl command synchronously and return (returncode, stdout, stderr)."""
    return _run_sync(args, timeout)


def _run_sync(args: list[str], timeout: int) -> tuple[int, str, str]:
    for attempt in range(2):
        try:
            result = subprocess.run(
                ["kubectl"] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError:
            return 127, "", "kubectl not found in PATH"
        except subprocess.TimeoutExpired:
            return 124, "", "kubectl command timed out"
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            return 1, "", str(e)
    return 1, "", "Unknown error"


async def run_kubectl_async(args: list[str], timeout: int = 5) -> tuple[int, str, str]:
    """Run kubectl in a thread pool — non-blocking for Textual's event loop."""
    return await asyncio.to_thread(_run_sync, args, timeout)


# ---------------------------------------------------------------------------
# High-level getters (sync, cached)
# ---------------------------------------------------------------------------

def get_current_context() -> str:
    cached = K8S_CACHE.get("current_context")
    if cached is not None:
        return cached
    code, out, _ = run_kubectl(["config", "current-context"])
    result = out if code == 0 else ""
    K8S_CACHE.set("current_context", result, ttl=10.0)
    return result


def get_all_contexts() -> list[str]:
    cached = K8S_CACHE.get("all_contexts")
    if cached is not None:
        return cached
    code, out, _ = run_kubectl(["config", "get-contexts", "-o", "name"])
    result = [c for c in out.splitlines() if c.strip()] if code == 0 else []
    K8S_CACHE.set("all_contexts", result)
    return result


def use_context(context_name: str) -> bool:
    code, _, _ = run_kubectl(["config", "use-context", context_name])
    if code == 0:
        # Invalidate context-related cache entries
        K8S_CACHE.invalidate("current_context")
        K8S_CACHE.invalidate("all_namespaces")
        K8S_CACHE.invalidate("connection_status")
    return code == 0


def get_current_namespace() -> str:
    cached = K8S_CACHE.get("current_namespace")
    if cached is not None:
        return cached
    code, out, _ = run_kubectl(
        ["config", "view", "--minify", "-o", "jsonpath={..namespace}"]
    )
    result = out if (code == 0 and out) else "default"
    K8S_CACHE.set("current_namespace", result, ttl=10.0)
    return result


def get_all_namespaces() -> list[str]:
    cached = K8S_CACHE.get("all_namespaces")
    if cached is not None:
        return cached
    code, out, _ = run_kubectl(
        ["get", "namespaces", "-o", "jsonpath={.items[*].metadata.name}"]
    )
    result = [n for n in out.split() if n.strip()] if code == 0 else ["default"]
    K8S_CACHE.set("all_namespaces", result)
    return result


def set_namespace(namespace: str) -> bool:
    code, _, _ = run_kubectl(
        ["config", "set-context", "--current", f"--namespace={namespace}"]
    )
    if code == 0:
        K8S_CACHE.invalidate("current_namespace")
    return code == 0


def check_connection() -> ClusterStatus:
    """Check if connected to a valid cluster (cached for 30 s)."""
    cached = K8S_CACHE.get("connection_status")
    if cached is not None:
        return cached

    ctx = get_current_context()
    if not ctx:
        status = ClusterStatus(connected=False, context_name=None, error="No current context")
        K8S_CACHE.set("connection_status", status, ttl=10.0)
        return status

    code, _, err = run_kubectl(["get", "namespace", "default"], timeout=3)
    ns = get_current_namespace()
    if code == 0:
        status = ClusterStatus(connected=True, context_name=ctx, namespace=ns)
    else:
        status = ClusterStatus(connected=False, context_name=ctx, namespace=ns, error=err)

    K8S_CACHE.set("connection_status", status)
    return status


def get_cluster_resources(kind: str, namespace: str = "") -> list[dict]:
    """Fetch resources of a specific kind from the cluster as JSON."""
    cache_key = f"resources:{kind}:{namespace}"
    cached = K8S_CACHE.get(cache_key)
    if cached is not None:
        return cached

    args = ["get", kind, "-o", "json"]
    if namespace:
        args.extend(["-n", namespace])

    code, out, _ = run_kubectl(args, timeout=10)
    result: list[dict] = []
    if code == 0 and out:
        try:
            data = json.loads(out)
            result = data.get("items", [])
        except json.JSONDecodeError:
            pass

    K8S_CACHE.set(cache_key, result, ttl=15.0)
    return result
