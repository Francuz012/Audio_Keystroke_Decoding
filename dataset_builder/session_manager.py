"""Orchestrates audio and keystroke capture for one session."""

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
