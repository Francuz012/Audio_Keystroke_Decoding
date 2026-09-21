"""Shared monotonic clock used by audio and keystroke capture."""

import time

def now() -> float:
    """Return current time in seconds from a monotonic source."""
    return time.perf_counter()
