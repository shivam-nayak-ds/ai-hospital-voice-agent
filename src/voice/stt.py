from loguru import logger
import os
import asyncio
import threading
import time
from dotenv import load_dotenv
from deepgram import Deepgram

load_dotenv()

class AshaSTT:
    """
    Deepgram Live Streaming STT (Updated for v6 SDK).
    """

    def __init__(self, on_transcript_callback):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            logger.error("DEEPGRAM_API_KEY missing!")

        self.on_transcript_callback = on_transcript_callback
        self.is_connected = False
        self._encoding = "mulaw"
        self._sample_rate = 8000
        self._lock = threading.Lock()

        # In v6, the class is named Deepgram
        self.deepgram = Deepgram(api_key=self.api_key)
        self.dg_connection = None

    def start(self, encoding: str = "mulaw", sample_rate: int = 8000) -> bool:
        self._encoding = encoding
        self._sample_rate = sample_rate
        return self._connect()

    def _connect(self) -> bool:
        try:
            # In v6 (Fern), use listen.live.v("1")
            self.dg_connection = self.deepgram.listen.live.v("1")

            # In v6, we use string events
            def on_message(result, **kwargs):
                try:
                    # 1. Handle Transcript Results
                    if hasattr(result, "channel"):
                        transcript = result.channel.alternatives[0].transcript
                        is_final = result.is_final
                        confidence = result.channel.alternatives[0].confidence
                        if transcript.strip():
                            if self.on_transcript_callback:
                                # We pass a special flag for speech start if needed, 
                                # but usually we use the dedicated SpeechStarted event.
                                self.on_transcript_callback(transcript, is_final, confidence)
                except Exception:
                    pass

            def on_speech_started(event, **kwargs):
                """
                BARGE-IN: Triggered as soon as the user starts talking.
                This allows us to stop AI speech BEFORE the first word is even transcribed.
                """
                logger.debug("[STT] Speech Started Detected")
                if hasattr(self, "on_speech_start_callback") and self.on_speech_start_callback:
                    self.on_speech_start_callback()

            def on_error(error, **kwargs):
                logger.error(f"[STT] Error: {error}")

            def on_close(close, **kwargs):
                logger.warning("[STT] Connection Closed")
                self.is_connected = False

            # Bind events using strings
            self.dg_connection.on("Results", on_message)
            self.dg_connection.on("SpeechStarted", on_speech_started)
            self.dg_connection.on("Error", on_error)
            self.dg_connection.on("Close", on_close)

            # Start options
            options = {
                "model": "nova-2",
                "language": "en-IN",
                "smart_format": True,
                "encoding": self._encoding,
                "sample_rate": self._sample_rate,
                "interim_results": True,
                "vad_events": True,
                "endpointing": 300, # Faster endpointing (300ms of silence)
            }

            if self.dg_connection.start(options) is False:
                return False

            self.is_connected = True
            logger.success(f"[STT] Connected ({self._encoding})")
            return True

        except Exception as e:
            logger.error(f"[STT] Connection Failed: {e}")
            return False

    def send_audio(self, audio_data: bytes):
        if not audio_data or not self.is_connected:
            return
        with self._lock:
            try:
                self.dg_connection.send(audio_data)
            except Exception:
                self.is_connected = False

    def disconnect(self):
        self.is_connected = False
        if self.dg_connection:
            try:
                self.dg_connection.finish()
            except Exception:
                pass