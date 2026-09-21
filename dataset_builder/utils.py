"""Helper functions (e.g., listing existing sessions)."""

import os
from config import OUTPUT_ROOT

def next_session_id():
    """Return the next available session ID like 'session_001'."""
    if not os.path.exists(OUTPUT_ROOT):
        return "session_001"
    existing = [d for d in os.listdir(OUTPUT_ROOT) if d.startswith("session_")]
    if not existing:
        return "session_001"
    nums = []
    for name in existing:
        try:
            nums.append(int(name.split("_")[1]))
        except (IndexError, ValueError):
            pass
    next_num = max(nums, default=0) + 1
    return f"session_{next_num:03d}"
