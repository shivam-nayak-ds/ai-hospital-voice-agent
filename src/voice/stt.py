"""
stt.py
------
Deepgram Live Streaming Speech-to-Text (SDK v3+).

Migration notes:
  - Upgraded from the legacy `Deepgram` (v1) client to `DeepgramClient` (v3+).
  - The v3 SDK changed the live transcription API:
      Old: deepgram.transcription.live(options)
      New: deepgram.listen.websocket.v("1")
  - Event listeners now use the LiveTranscriptionEvents enum.
  - `send_audio()` uses the new `.send()` method on the live connection object.
"""

import os
import asyncio
import threading
from typing import Callable, Optional
from dotenv import load_dotenv
from loguru import logger

try:
    from deepgram import (
        DeepgramClient,
        DeepgramClientOptions,
        LiveTranscriptionEvents,
        LiveOptions,
    )
    _DEEPGRAM_AVAILABLE = True
except ImportError:
    _DEEPGRAM_AVAILABLE = False
    logger.error(
        "deepgram-sdk not installed or wrong version. "
        "Run: pip install 'deepgram-sdk>=3.11.0'"
    )

load_dotenv()


class AshaSTT:
    """
    Deepgram Live Streaming STT (SDK v3+).

    Usage:
        stt = AshaSTT(on_transcript_callback=my_callback)
        stt.start(encoding="mulaw", sample_rate=8000)
        stt.send_audio(raw_bytes)
        stt.disconnect()

    The `on_transcript_callback` signature:
        callback(text: str, is_final: bool, confidence: float) -> None
    """

    def __init__(
        self,
        on_transcript_callback: Callable[[str, bool, float], None],
        on_speech_start_callback: Optional[Callable[[], None]] = None,
    ):
        self.api_key: Optional[str] = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            logger.error("DEEPGRAM_API_KEY is not set — STT will not function.")

        self.on_transcript_callback = on_transcript_callback
        self.on_speech_start_callback = on_speech_start_callback

        self.is_connected: bool = False
        self._encoding: str = "mulaw"
        self._sample_rate: int = 8000
        self._lock = threading.Lock()

        # Deepgram v3 client
        self._client: Optional[DeepgramClient] = None
        self.dg_connection = None

        if _DEEPGRAM_AVAILABLE and self.api_key:
            config = DeepgramClientOptions(verbose=False)
            self._client = DeepgramClient(self.api_key, config)

    # ─── Public API ───────────────────────────────────────────────────────────

    def start(self, encoding: str = "mulaw", sample_rate: int = 8000) -> bool:
        """Opens a live Deepgram WebSocket connection with the given audio format."""
        self._encoding = encoding
        self._sample_rate = sample_rate
        return self._connect()

    def send_audio(self, audio_data: bytes) -> None:
        """Thread-safe method to stream raw audio bytes to Deepgram."""
        if not audio_data or not self.is_connected or self.dg_connection is None:
            return
        with self._lock:
            try:
                self.dg_connection.send(audio_data)
            except Exception as e:
                logger.warning(f"[STT] send_audio failed: {e}")
                self.is_connected = False

    def disconnect(self) -> None:
        """Closes the Deepgram WebSocket connection cleanly."""
        self.is_connected = False
        if self.dg_connection is not None:
            try:
                self.dg_connection.finish()
            except Exception:
                pass
            self.dg_connection = None

    # ─── Internal Connection ──────────────────────────────────────────────────

    def _connect(self) -> bool:
        if not _DEEPGRAM_AVAILABLE or self._client is None:
            logger.error("[STT] Deepgram client unavailable — check installation and API key.")
            return False

        try:
            # v3 SDK: create a live WebSocket connection
            self.dg_connection = self._client.listen.websocket.v("1")

            # ── Event Handlers ──

            def on_message(self_conn, result, **kwargs):
                """Fired on every transcript result (interim or final)."""
                try:
                    transcript = result.channel.alternatives[0].transcript
                    is_final = result.is_final
                    confidence = result.channel.alternatives[0].confidence
                    if transcript.strip() and self.on_transcript_callback:
                        self.on_transcript_callback(transcript, is_final, confidence)
                except Exception:
                    pass  # Malformed result — silently discard

            def on_speech_started(self_conn, event, **kwargs):
                """
                Barge-in hook: fired as soon as Deepgram detects voice activity,
                before the first word is fully transcribed.
                """
                logger.debug("[STT] Speech Started Detected")
                if self.on_speech_start_callback:
                    self.on_speech_start_callback()

            def on_error(self_conn, error, **kwargs):
                logger.error(f"[STT] Deepgram error: {error}")

            def on_close(self_conn, close, **kwargs):
                logger.warning("[STT] Deepgram connection closed.")
                self.is_connected = False

            # Register listeners using the v3 enum API
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)

            # Connection options — tuned for low-latency telephony
            options = LiveOptions(
                model="nova-2",
                language="en-IN",
                smart_format=True,
                encoding=self._encoding,
                sample_rate=self._sample_rate,
                interim_results=True,
                vad_events=True,
                endpointing=300,   # 300ms silence before endpoint detection
            )

            if self.dg_connection.start(options) is False:
                logger.error("[STT] Deepgram connection.start() returned False.")
                return False

            self.is_connected = True
            logger.success(f"[STT] Connected (encoding={self._encoding}, rate={self._sample_rate}Hz)")
            return True

        except Exception as e:
            logger.error(f"[STT] Connection failed: {e}")
            return False