"""UMA-002: account lockout after repeated failed logins.

Backed by Django's cache framework (LocMemCache by default -- swap in Redis
via CACHES for a multi-process deployment) instead of an in-process dict, so
it works the same way whether the app runs as one worker or several.
"""
from __future__ import annotations

import time

from django.core.cache import cache


def _key(username: str) -> str:
    return f"login_failures:{username}"


def record_failure(username: str, window_seconds: int) -> None:
    now = time.time()
    history = [t for t in cache.get(_key(username), []) if t >= now - window_seconds]
    history.append(now)
    cache.set(_key(username), history, timeout=window_seconds)


def record_success(username: str) -> None:
    cache.delete(_key(username))


def is_locked_out(username: str, max_attempts: int, window_seconds: int) -> bool:
    now = time.time()
    history = [t for t in cache.get(_key(username), []) if t >= now - window_seconds]
    return len(history) >= max_attempts
