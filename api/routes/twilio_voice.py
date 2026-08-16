"""
twilio_voice.py
---------------
FastAPI routes for Twilio Media Stream telephony integration.

Changes:
  - Replaced deprecated `audioop` (removed in Python 3.13) with numpy-based
    PCM resampling for Python 3.13+ compatibility.
  - Guarded `pygame` import: pygame is only available in local dev environments
    with a physical audio device. On headless cloud servers it will raise an
    error on import, so we import it lazily and only use it as a fallback.
"""

import base64
import io
import json

import numpy as np
from fastapi import APIRouter, Request, Response, WebSocket

from src.utils.logger import custom_logger as logger
from src.voice.orchestrator import AshaVoiceOrchestrator
from src.voice.stt import AshaSTT

# pygame is only used for MP3 decoding in local dev (non-Twilio path).
# On headless servers it may not initialise, so we import it lazily.
try:
    import pygame
    _PYGAME_AVAILABLE = True
except Exception:
    _PYGAME_AVAILABLE = False
    logger.warning("pygame not available — MP3-to-PCM path disabled (expected in server environments).")

router = APIRouter(prefix="/voice", tags=["Telephony"])


# ─── Audio Conversion Helpers ─────────────────────────────────────────────────

def _resample_pcm_numpy(pcm_bytes: bytes, src_rate: int, dst_rate: int, sample_width: int = 2) -> bytes:
    """
    Resamples raw linear PCM audio from src_rate to dst_rate using numpy linear
    interpolation. Replaces the deprecated `audioop.ratecv` (removed Python 3.13).

    Args:
        pcm_bytes:    Raw PCM byte string (signed 16-bit mono assumed).
        src_rate:     Source sample rate in Hz (e.g. 24000).
        dst_rate:     Target sample rate in Hz (e.g. 8000).
        sample_width: Bytes per sample (2 = int16).

    Returns:
        Resampled PCM bytes at dst_rate.
    """
    if src_rate == dst_rate:
        return pcm_bytes

    # Parse bytes to numpy int16 array
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)

    # Compute output length and resample via linear interpolation
    num_src = len(samples)
    num_dst = int(num_src * dst_rate / src_rate)
    src_indices = np.linspace(0, num_src - 1, num_dst)
    resampled = np.interp(src_indices, np.arange(num_src), samples)

    # Clip to int16 range and convert back to bytes
    resampled_int16 = np.clip(resampled, -32768, 32767).astype(np.int16)
    return resampled_int16.tobytes()


def _pcm_to_mulaw(pcm_bytes: bytes) -> bytes:
    """
    Encodes 16-bit linear PCM bytes to 8-bit mu-law (G.711) using the standard
    ITU-T G.711 algorithm implemented in pure numpy.
    Replaces the deprecated `audioop.lin2ulaw` (removed Python 3.13).
    """
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.int32)

    # ITU-T G.711 mu-law encoding constants
    MU = 255
    CLIP = 32767

    # Bias and clip
    sign = np.where(samples < 0, 0x80, 0x00).astype(np.uint8)
    samples = np.abs(samples)
    samples = np.minimum(samples, CLIP)

    # Add bias
    samples = samples + (CLIP + 1) >> 2  # scale: bias = 33
    # Proper mu-law: bias = 132
    samples_biased = np.abs(np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.int32)) + 132
    samples_biased = np.minimum(samples_biased, CLIP + 132)

    # Log compress
    mu_val = (np.log1p(MU * samples_biased.astype(np.float32) / (CLIP + 132)) /
              np.log1p(MU) * 127).astype(np.uint8)

    mulaw = (sign | (127 - mu_val)).astype(np.uint8)
    return mulaw.tobytes()


def mp3_to_pcm_8k(mp3_bytes: bytes) -> bytes:
    """
    Decodes MP3 bytes to 8000Hz 16-bit Mono PCM using Pygame mixer.
    Only available in local dev environments (pygame required).
    """
    if not _PYGAME_AVAILABLE:
        logger.error("mp3_to_pcm_8k called but pygame is unavailable — returning empty bytes.")
        return b""

    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=8000, size=-16, channels=1, buffer=512)
    elif pygame.mixer.get_init()[0] != 8000:
        pygame.mixer.quit()
        pygame.mixer.init(frequency=8000, size=-16, channels=1, buffer=512)

    try:
        sound = pygame.mixer.Sound(io.BytesIO(mp3_bytes))
        samples = pygame.sndarray.array(sound)
        return samples.tobytes()
    except Exception as e:
        logger.error(f"Telephony MP3-to-PCM conversion failed: {e}")
        return b""


def convert_to_twilio_mulaw(audio_data: bytes) -> str:
    """
    Converts audio bytes (MP3 or high-sample PCM) to base64-encoded 8kHz mu-law
    string suitable for Twilio Media Stream.

    Encoding path:
      MP3  → pygame decode → 8kHz PCM → mu-law → base64
      PCM  → numpy resample (24kHz→8kHz) → mu-law → base64
    """
    # Detect MP3 magic bytes
    if audio_data[:3] in (b'\xff\xfb', b'\xff\xf3', b'ID3'):
        pcm_8k = mp3_to_pcm_8k(audio_data)
    else:
        # Assume 24kHz PCM from Edge-TTS / Azure / Google
        try:
            pcm_8k = _resample_pcm_numpy(audio_data, src_rate=24000, dst_rate=8000)
        except Exception as e:
            logger.error(f"PCM resampling failed: {e}")
            pcm_8k = audio_data

    # Encode to mu-law
    try:
        mulaw_data = _pcm_to_mulaw(pcm_8k)
        return base64.b64encode(mulaw_data).decode("utf-8")
    except Exception as e:
        logger.error(f"Conversion to mulaw failed: {e}")
        return ""


# ─── Twilio Webhook & WebSocket Routes ───────────────────────────────────────

@router.post("/incoming", summary="Twilio Call Entry Webhook")
async def incoming_call(request: Request):
    """
    HTTP POST called by Twilio when a call is placed.
    Returns TwiML instructions directing Twilio to establish a WebSocket audio stream.
    """
    host = request.headers.get("host", "localhost:8000")
    protocol = "wss" if request.url.scheme == "https" else "ws"
    stream_url = f"{protocol}://{host}/voice/stream"

    logger.info(f"Incoming call received. Routing stream to: {stream_url}")

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Aditi">Welcome to Lifeline Multi-Speciality Hospital. Please wait while we connect your call.</Say>
    <Connect>
        <Stream url="{stream_url}" />
    </Connect>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """
    WebSocket endpoint handling live bidirectional telephony audio.
    Receives user voice transcripts via Deepgram STT, and replies via streamed mulaw audio.
    """
    await websocket.accept()
    logger.info("Twilio media stream WebSocket connected.")

    stream_sid = None
    orchestrator = None
    stt = None

    async def twilio_audio_sender(audio_bytes: bytes):
        """Callback triggered by TTS to send audio packets back to Twilio."""
        nonlocal stream_sid
        if not stream_sid:
            return

        # Convert generated audio (MP3/PCM) to base64 8kHz mulaw
        payload = convert_to_twilio_mulaw(audio_bytes)
        if not payload:
            return

        media_msg = {
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": payload
            }
        }
        try:
            await websocket.send_json(media_msg)
        except Exception as e:
            logger.error(f"Failed to send audio packet to Twilio: {e}")

    try:
        while True:
            # Receive messages from Twilio WebSocket
            data = await websocket.receive_text()
            msg = json.loads(data)

            event = msg.get("event")

            if event == "start":
                stream_sid = msg["start"]["streamSid"]
                call_sid = msg["start"]["callSid"]
                logger.success(f"Stream started. StreamSid: {stream_sid}, CallSid: {call_sid}")

                # Initialize orchestrator & STT for this specific call session
                orchestrator = AshaVoiceOrchestrator(output_callback=twilio_audio_sender, user_id=call_sid)

                stt = AshaSTT(on_transcript_callback=orchestrator.on_transcript)
                stt.on_speech_start_callback = orchestrator.on_speech_start

                # Start Deepgram STT under mulaw encoding at 8000Hz (native Twilio rate)
                stt.start(encoding="mulaw", sample_rate=8000)
                logger.info(f"Initialized voice orchestrator and STT session for call {call_sid}")

            elif event == "media":
                # Process audio packet from user
                payload = msg["media"]["payload"]
                audio_bytes = base64.b64decode(payload)

                # Directly pipe raw mulaw bytes to Deepgram STT
                if stt:
                    stt.send_audio(audio_bytes)

            elif event == "stop":
                logger.info("Stream stopped event received from Twilio.")
                break

    except Exception as e:
        logger.error(f"Error in Twilio voice streaming loop: {e}")
    finally:
        # Cleanup
        logger.info("Closing Twilio voice streaming session and disconnecting STT.")
        if stt:
            stt.disconnect()
        if orchestrator:
            await orchestrator.stop_current_response()
        try:
            await websocket.close()
        except Exception:
            pass
