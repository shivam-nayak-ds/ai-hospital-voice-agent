import pyaudio
from src.utils.logger import custom_logger as logger

class AshaVoiceRecorder:
    def __init__(self, rate=16000, chunk=1024):
        self.rate = rate
        self.chunk = chunk
        self.format = pyaudio.paInt16
        self.channels = 1
        self.p = pyaudio.PyAudio()
        self.stream = None
        logger.info("Voice Recorder initialized (16kHz).")

    def start_recording(self, callback):
        """
        Starts streaming microphone audio to the provided callback function.
        """
        logger.info("Listening... Speak now!")
        
        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=callback
        )
        self.stream.start_stream()

    def stop_recording(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            logger.info("Recording stopped.")

if __name__ == "__main__":
    # Test: Microphone check
    def dummy_callback(in_data, frame_count, time_info, status):
        print(".", end="", flush=True) # Printing dots for each audio chunk
        return (in_data, pyaudio.paContinue)

    recorder = AshaVoiceRecorder()
    try:
        recorder.start_recording(dummy_callback)
        import time
        time.sleep(5) # Record for 5 seconds
    finally:
        recorder.stop_recording()
