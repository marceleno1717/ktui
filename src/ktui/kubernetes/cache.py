"""Kubernetes client cache — TTL-based in-memory store.

Replaces the ``app._cached_namespaces`` hack in connection_panel.py.
Import and use ``K8S_CACHE`` everywhere that needs cached cluster data.
"""

from __future__ import annotations

import time
from typing import Any

_DEFAULT_TTL = 30.0  # seconds


class _TTLCache:
    """Simple TTL dict cache — no external dependencies."""

    def __init__(self, ttl: float = _DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expire_at)

    def get(self, key: str) -> Any:
        """Return cached value or ``None`` if missing / expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if time.monotonic() > expire_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store *value* under *key* with optional TTL override."""
        expire_at = time.monotonic() + (ttl if ttl is not None else self._ttl)
        self._store[key] = (value, expire_at)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# Module-level singleton — import this everywhere cluster data is needed.
K8S_CACHE: _TTLCache = _TTLCache(ttl=30.0)
