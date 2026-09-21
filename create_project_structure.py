# create_project_structure.py
"""
Generates the dataset_builder project skeleton.
Run this script once to create all directories and empty module files.
"""

import os

PROJECT_ROOT = "dataset_builder"

MODULES = {
    "config.py": '''"""Global configuration constants for the dataset builder."""

SAMPLE_RATE = 44100  # Hz
CHUNK_SIZE = 1024    # frames per buffer
CHANNELS = 1
SAMPLE_WIDTH = 2     # 16-bit = 2 bytes
OUTPUT_ROOT = "dataset_root"
''',
    "sync_clock.py": '''"""Shared monotonic clock used by audio and keystroke capture."""

import time

def now() -> float:
    """Return current time in seconds from a monotonic source."""
    return time.perf_counter()
''',
    "audio_capture.py": '''"""Audio capture using PyAudio."""

import pyaudio
import wave
from config import SAMPLE_RATE, CHUNK_SIZE, CHANNELS, SAMPLE_WIDTH
from sync_clock import now

class AudioRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.start_time = None

    def start(self):
        """Open non-blocking stream and record start timestamp."""
        self.stream = self.p.open(
            format=self.p.get_format_from_width(SAMPLE_WIDTH),
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self._callback
        )
        self.start_time = now()

    def _callback(self, in_data, frame_count, time_info, status):
        self.frames.append(in_data)
        return (None, pyaudio.paContinue)

    def stop(self):
        """Close the stream and return all captured frames."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.p.terminate()
        return b"".join(self.frames)

    def save_wav(self, filepath, raw_data):
        """Write raw PCM data to a WAV file."""
        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(raw_data)
''',
    "keystroke_capture.py": '''"""Keyboard event capture with high‑resolution timestamps."""

from pynput import keyboard
from sync_clock import now

class KeystrokeLogger:
    def __init__(self, audio_start_time: float):
        self.audio_start_time = audio_start_time
        self.events = []  # list of dicts with keys: character, vk_code, relative_time_ms
        self.listener = None

    def _on_press(self, key):
        """Callback when a key is pressed."""
        timestamp = now()
        relative_ms = (timestamp - self.audio_start_time) * 1000.0
        try:
            vk = key.vk if hasattr(key, "vk") else ord(key.char)
            char = key.char
        except AttributeError:
            # special keys: we record their name as character
            vk = key.value.vk
            char = str(key).replace("Key.", "")
        self.events.append({
            "character": char,
            "vk_code": vk,
            "relative_time_ms": round(relative_ms, 3)
        })

    def start(self):
        """Begin listening for keyboard events."""
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()

    def stop(self):
        """Stop listening and return list of events."""
        if self.listener:
            self.listener.stop()
            self.listener = None
        return self.events
''',
    "session_manager.py": '''"""Orchestrates audio and keystroke capture for one session."""

import os
import json
import time
from config import OUTPUT_ROOT
from audio_capture import AudioRecorder
from keystroke_capture import KeystrokeLogger

class SessionManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_dir = os.path.join(OUTPUT_ROOT, session_id)
        os.makedirs(self.session_dir, exist_ok=True)

    def run(self):
        """Run a single recording session. Press ESC to stop."""
        recorder = AudioRecorder()
        print("Starting audio stream...")
        recorder.start()
        logger = KeystrokeLogger(recorder.start_time)
        print("Listening for keystrokes. Press 'ESC' to finish session.")
        logger.start()

        # Wait for user to press ESC (pynput listener handles it)
        while logger.listener and logger.listener.running:
            time.sleep(0.1)

        print("Stopping keystroke capture...")
        events = logger.stop()
        print("Stopping audio capture...")
        raw_audio = recorder.stop()

        # Write audio file
        wav_path = os.path.join(self.session_dir, "audio_stream.wav")
        recorder.save_wav(wav_path, raw_audio)

        # Compute final durations and frame starts
        sample_rate = 44100  # must match config.SAMPLE_RATE
        total_samples = len(raw_audio) // 2  # 2 bytes per sample
        duration = total_samples / sample_rate

        final_events = []
        for idx, ev in enumerate(events):
            frame_start = int(round((ev["relative_time_ms"] / 1000.0) * sample_rate))
            final_events.append({
                "index": idx,
                "character": ev["character"],
                "vk_code": ev["vk_code"],
                "relative_time_ms": ev["relative_time_ms"],
                "audio_frame_start": frame_start
            })

        label_data = {
            "session_id": self.session_id,
            "audio_duration_seconds": round(duration, 3),
            "total_keystrokes": len(final_events),
            "events": final_events
        }

        json_path = os.path.join(self.session_dir, "keystroke_labels.json")
        with open(json_path, "w") as f:
            json.dump(label_data, f, indent=2)

        print(f"Session saved in {self.session_dir}")
''',
    "record_session.py": '''"""CLI entry point for recording a single session."""

import argparse
from session_manager import SessionManager

def main():
    parser = argparse.ArgumentParser(description="Record a keystroke‑audio session.")
    parser.add_argument("session_id", help="Unique ID for the session (e.g., session_001)")
    args = parser.parse_args()

    session = SessionManager(args.session_id)
    session.run()

if __name__ == "__main__":
    main()
''',
    "utils.py": '''"""Helper functions (e.g., listing existing sessions)."""

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
'''}

def create_project():
    os.makedirs(PROJECT_ROOT, exist_ok=True)
    for filename, content in MODULES.items():
        path = os.path.join(PROJECT_ROOT, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    # Create empty __init__.py to make it a package
    open(os.path.join(PROJECT_ROOT, "__init__.py"), "w").close()
    print(f"Project skeleton created in ./{PROJECT_ROOT}")

if __name__ == "__main__":
    create_project()