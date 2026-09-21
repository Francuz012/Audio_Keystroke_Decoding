# keystroke_capture.py
"""Keyboard event capture with high‑resolution timestamps, ignoring specified keys."""

from pynput import keyboard
from sync_clock import now

class KeystrokeLogger:
    def __init__(self, audio_start_time: float, ignored_keys: set = None):
        """
        audio_start_time: monotonic time when audio stream started.
        ignored_keys: set of pynput Key or vk codes to exclude from events.
        """
        self.audio_start_time = audio_start_time
        self.events = []          # list of dicts: character, vk_code, relative_time_ms
        self.ignored_keys = ignored_keys or set()
        self.listener = None

    def record_event(self, key):
        """Process a key press and append to events if not ignored."""
        # Determine if key should be ignored
        if hasattr(key, 'vk') and key.vk in self.ignored_keys:
            return
        if key in self.ignored_keys:
            return

        timestamp = now()
        relative_ms = (timestamp - self.audio_start_time) * 1000.0
        try:
            vk = key.vk if hasattr(key, "vk") else ord(key.char)
            char = key.char
        except AttributeError:
            # Special keys: use their name
            vk = key.value.vk
            char = str(key).replace("Key.", "")
        self.events.append({
            "character": char,
            "vk_code": vk,
            "relative_time_ms": round(relative_ms, 3)
        })

    def clear(self):
        """Reset the event list (useful when starting a new session)."""
        self.events = []

    def start(self):
        """No longer needed – events are fed externally."""
        pass

    def stop(self):
        """Stop (no-op) – kept for API compatibility."""
        pass