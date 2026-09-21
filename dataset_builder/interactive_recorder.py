# interactive_recorder.py
"""
Interactive keyboard‑audio recording tool.

Press F8 (global) to start a recording session.
Press F8 again to stop the recording and save the session.
All other keystrokes during recording are captured as labels.

Sessions are saved in dataset_root/session_xxx/ with auto‑incrementing IDs.
"""

import os
import json
import time
import threading
from pynput import keyboard

from config import SAMPLE_RATE, OUTPUT_ROOT
from audio_capture import AudioRecorder
from keystroke_capture import KeystrokeLogger
from utils import next_session_id

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
TOGGLE_KEY = keyboard.Key.f8          # start/stop recording
IGNORED_KEYS = {TOGGLE_KEY}           # keys that will not be logged as labels

# ----------------------------------------------------------------------
class InteractiveRecorder:
    def __init__(self):
        self.recording = False
        self.lock = threading.Lock()
        self.audio_recorder = None
        self.keystroke_logger = None
        self.listener = None

    def toggle_recording(self):
        """Start or stop a recording session."""
        with self.lock:
            if not self.recording:
                self._start_recording()
            else:
                self._stop_recording()

    def _start_recording(self):
        print("\n🔴 Recording started... Press F8 to stop.")
        self.recording = True

        # Initialize audio recorder and start stream
        self.audio_recorder = AudioRecorder()
        self.audio_recorder.start()

        # Prepare keystroke logger with the exact audio start time
        self.keystroke_logger = KeystrokeLogger(
            audio_start_time=self.audio_recorder.start_time,
            ignored_keys={k.vk if hasattr(k, 'vk') else k.value.vk for k in IGNORED_KEYS}
        )

    def _stop_recording(self):
        print("\n⏹️ Recording stopped. Saving session...")
        self.recording = False

        # Stop audio and get raw data
        raw_audio = self.audio_recorder.stop()
        events = self.keystroke_logger.events  # collected while recording

        # Determine session id and create output directory
        session_id = next_session_id()
        session_dir = os.path.join(OUTPUT_ROOT, session_id)
        os.makedirs(session_dir, exist_ok=True)

        # Save audio file
        wav_path = os.path.join(session_dir, "audio_stream.wav")
        self.audio_recorder.save_wav(wav_path, raw_audio)

        # Calculate final metrics
        total_samples = len(raw_audio) // 2      # 16-bit = 2 bytes per sample
        duration = total_samples / SAMPLE_RATE

        final_events = []
        for idx, ev in enumerate(events):
            frame_start = int(round((ev["relative_time_ms"] / 1000.0) * SAMPLE_RATE))
            final_events.append({
                "index": idx,
                "character": ev["character"],
                "vk_code": ev["vk_code"],
                "relative_time_ms": ev["relative_time_ms"],
                "audio_frame_start": frame_start
            })

        label_data = {
            "session_id": session_id,
            "audio_duration_seconds": round(duration, 3),
            "total_keystrokes": len(final_events),
            "events": final_events
        }

        json_path = os.path.join(session_dir, "keystroke_labels.json")
        with open(json_path, "w") as f:
            json.dump(label_data, f, indent=2)

        print(f"✅ Session saved to {session_dir}")
        print("Press F8 to start a new recording, or Ctrl+C to quit.\n")

        # Clean up references
        self.audio_recorder = None
        self.keystroke_logger = None

    def on_press(self, key):
        """Global keyboard callback from pynput."""
        # Toggle key always toggles recording
        if key == TOGGLE_KEY:
            self.toggle_recording()
            return

        # If we are currently recording, log the key (unless it's ignored)
        with self.lock:
            if self.recording:
                self.keystroke_logger.record_event(key)

    def run(self):
        print("=== Interactive Audio‑Keystroke Recorder ===")
        print(f"Press {TOGGLE_KEY.name.upper()} to start/stop a session.")
        print("Press Ctrl+C to exit completely.\n")

        # Start the global keyboard listener
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

        try:
            # Keep the main thread alive
            while self.listener.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            if self.recording:
                self._stop_recording()   # graceful shutdown
            if self.listener:
                self.listener.stop()

if __name__ == "__main__":
    app = InteractiveRecorder()
    app.run()