import numpy as np
import pyaudio

from src.utils.logger import custom_logger as logger


class AshaVoiceRecorder:
    """
    Microphone audio streamer with RMS-based visual noise indicator.

    Key Design Decision:
      ALL audio is sent to Deepgram (not filtered at source).
      Deepgram's built-in VAD handles silence detection.
      Filtering at source caused Deepgram 1011 timeout errors
      because it received no audio and dropped the connection.

      The noise gate here is DISPLAY-ONLY (shows when user is speaking).
    """

    def __init__(self, rate: int = 16000, chunk: int = 1024):
        self.rate = rate
        self.chunk = chunk
        self.format = pyaudio.paInt16
        self.channels = 1
        self.p = pyaudio.PyAudio()
        self.stream = None
        self._display_threshold = 300  # RMS above this → show [SPEAKING] indicator
        logger.info("Voice Recorder initialized (16kHz, system default mic).")

    def _get_rms(self, data_chunk: bytes) -> float:
        """Safe RMS calculation — handles empty/silent chunks."""
        if not data_chunk:
            return 0.0
        audio = np.frombuffer(data_chunk, dtype=np.int16)
        if len(audio) == 0:
            return 0.0
        mean_sq = np.mean(audio.astype(np.float32) ** 2)
        return float(np.sqrt(mean_sq)) if mean_sq > 0 else 0.0

    def start_recording(self, callback):
        """
        Start streaming mic audio.
        All audio goes to callback (Deepgram STT).
        RMS used only for terminal visual indicator.
        """
        logger.info("Microphone active — all audio streaming to Deepgram.")

        def internal_callback(in_data, frame_count, time_info, status):
            # Visual indicator (doesn't block audio)
            rms = self._get_rms(in_data)
            if rms > self._display_threshold:
                import sys
                sys.stdout.write(f"\r[MIC] Speaking... (RMS={rms:.0f})   ")
                sys.stdout.flush()

            # ALWAYS pass audio to STT — let Deepgram VAD handle silence
            return callback(in_data, frame_count, time_info, status)

        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=internal_callback
        )
        self.stream.start_stream()

    def stop_recording(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
            logger.info("Recording stopped.")


if __name__ == "__main__":
    """Quick test: prints RMS values to confirm mic is receiving audio."""
    import time

    def test_callback(in_data, frame_count, time_info, status):
        return (None, pyaudio.paContinue)

    r = AshaVoiceRecorder()
    r.start_recording(test_callback)
    print("Speak into your mic for 5 seconds...")
    try:
        time.sleep(5)
    finally:
        r.stop_recording()
        print("Done.")
