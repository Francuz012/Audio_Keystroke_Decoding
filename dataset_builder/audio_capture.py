"""Audio capture using PyAudio."""

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
