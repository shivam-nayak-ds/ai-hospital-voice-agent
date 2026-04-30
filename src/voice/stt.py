import os
import asyncio
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions
)
from src.utils.logger import custom_logger as logger

load_dotenv()

class AshaSTT:
    def __init__(self, on_transcript_callback):
        """
        Ultra-Fast Deepgram Live Streaming STT over WebSockets.
        """
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            logger.error("DEEPGRAM_API_KEY is missing! STT will fail.")
            
        # Callback to send text back to the orchestrator as soon as it arrives
        self.on_transcript_callback = on_transcript_callback
        
        # Initialize Deepgram WebSocket Client with native KeepAlive
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.deepgram = DeepgramClient(self.api_key, config)
        self.dg_connection = self.deepgram.listen.websocket.v("1")
        self.is_connected = False
        
        self._setup_events()
        logger.success("Asha STT Ready! (Deepgram Live WebSocket Active)")

    def _setup_events(self):
        def on_message(self_param, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            
            # is_final means the user took a pause (Deepgram's built-in VAD detected silence)
            is_final = result.is_final
            self.on_transcript_callback(sentence, is_final)

        def on_error(self_param, error, **kwargs):
            logger.error(f"Deepgram WebSocket Error: {error}")
            # Auto-reconnect on timeout or 1011 error
            if "timeout" in str(error).lower() or "1011" in str(error):
                logger.warning("Attempting to reconnect Deepgram...")
                try:
                    self.disconnect()
                    self.dg_connection = self.deepgram.listen.websocket.v("1")
                    self._setup_events()
                    self.start()
                except Exception as e:
                    logger.error(f"Reconnect failed: {e}")

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    def start(self):
        """Starts the WebSocket connection with Deepgram."""
        options = LiveOptions(
            model="nova-2",
            language="hi", # 'hi' works best for Hinglish/Hindi
            smart_format=True,
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            endpointing=300 # Deepgram's internal VAD (300ms pause = sentence end)
        )
        
        if self.dg_connection.start(options) is False:
            logger.error("Failed to connect to Deepgram WebSockets.")
            return False
            
        self.is_connected = True
        logger.info("Deepgram Live WebSocket connection established.")
        return True

    def send_audio(self, audio_data: bytes):
        """Streams raw audio bytes directly to Deepgram with zero latency."""
        if self.is_connected:
            self.dg_connection.send(audio_data)

    def send_keepalive(self):
        """Sends native KeepAlive message to Deepgram to prevent timeout when mic is muted."""
        if self.is_connected:
            try:
                self.dg_connection.keep_alive()
            except AttributeError:
                # Fallback if keep_alive method isn't available
                self.dg_connection.send('{"type": "KeepAlive"}')

    def disconnect(self):
        """Closes the WebSocket connection."""
        if self.is_connected:
            self.dg_connection.finish()
            self.is_connected = False
            logger.info("Deepgram Live connection closed.")