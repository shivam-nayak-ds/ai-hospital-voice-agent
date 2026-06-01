import audioop
import base64
import json
from src.utils.logger import custom_logger as logger

class TwilioAudioBridge:
    """
    Handles conversion between Twilio's mulaw audio and PCM for STT/TTS.
    """
    @staticmethod
    def decode_mulaw(payload_base64: str) -> bytes:
        """Convert Twilio base64 mulaw to raw PCM."""
        try:
            mulaw_data = base64.b64decode(payload_base64)
            # Convert mulaw to linear16 (PCM)
            return audioop.ulaw2lin(mulaw_data, 2)
        except Exception as e:
            logger.error(f"Mulaw Decode Error: {e}")
            return b""

    @staticmethod
    def encode_mulaw(pcm_data: bytes) -> str:
        """Convert raw PCM to Twilio base64 mulaw."""
        try:
            # Twilio expects 8000Hz mulaw. 
            # If our input is different, we might need resampling, 
            # but usually TTS output can be configured to 8000Hz.
            mulaw_data = audioop.lin2ulaw(pcm_data, 2)
            return base64.b64encode(mulaw_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Mulaw Encode Error: {e}")
            return ""

    @staticmethod
    def create_twilio_media_message(payload_base64: str, stream_sid: str) -> str:
        """Wrap audio payload in Twilio's JSON format."""
        return json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": payload_base64
            }
        })
