from __future__ import annotations

import time
from collections import defaultdict

from app.settings import settings

# In-memory sliding window storage: client_ip -> list of call timestamps
_client_calls: dict[str, list[float]] = defaultdict(list)


def get_client_ip(headers: dict[str, str], client_host: str | None = None) -> str:
    """Extract client IP respecting X-Forwarded-For if present behind proxy / CDN."""
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        # Use first proxy client IP
        return forwarded.split(",")[0].strip()
    return client_host or "127.0.0.1"


def check_rate_limit(
    client_ip: str,
    max_calls: int | None = None,
    window_seconds: int | None = None,
) -> tuple[bool, int, int]:
    """
    Check sliding-window rate limit for live AI model invocations.
    Returns:
        (is_allowed: bool, remaining_calls: int, retry_after_seconds: int)
    """
    max_c = max_calls if max_calls is not None else settings.live_rate_limit_max_calls
    win_s = (
        window_seconds
        if window_seconds is not None
        else settings.live_rate_limit_window_seconds
    )

    now = time.time()
    cutoff = now - win_s

    # Clean expired timestamps
    history = [t for t in _client_calls[client_ip] if t > cutoff]
    _client_calls[client_ip] = history

    if len(history) >= max_c:
        # Earliest call will expire at history[0] + win_s
        retry_after = max(1, int((history[0] + win_s) - now))
        return False, 0, retry_after

    remaining = max_c - len(history)
    return True, remaining, 0


def record_live_call(client_ip: str) -> None:
    """Record a timestamp for a live AI model call."""
    _client_calls[client_ip].append(time.time())


def reset_rate_limits() -> None:
    """Clear all rate limit histories (for testing)."""
    _client_calls.clear()
