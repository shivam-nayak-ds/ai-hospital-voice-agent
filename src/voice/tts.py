import os
import asyncio
import re
import io
import base64
import requests
import pygame
from src.utils.logger import custom_logger as logger
from dotenv import load_dotenv

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not installed. Run: pip install edge-tts")

try:
    from google.cloud import texttospeech
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

load_dotenv()


class AshaTTS:
    """
    Production-Grade Hybrid TTS Engine.
    Priority: Edge-TTS (Free, Reliable) > Azure > Google > Sarvam
    Edge-TTS uses Microsoft's neural voices - zero cost, zero 400 errors.
    """

    def __init__(self):
        self.sarvam_key = os.getenv("SARVAM_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.azure_key = os.getenv("AZURE_SPEECH_KEY")
        self.azure_region = os.getenv("AZURE_REGION", "centralindia")

        self.is_playing = False
        self.should_stop = False

        # Voice for each backend
        # Edge-TTS: Professional Indian English Female
        self.edge_voice = "en-IN-NeerjaNeural"  # Top-quality, Indian English, Female

        # Priority: Edge-TTS -> Azure -> Google -> Sarvam -> Silent
        if EDGE_TTS_AVAILABLE:
            self.backend = "edge"
            logger.success(f"ASHA TTS: Edge-TTS Active (Voice: {self.edge_voice})")
        elif AZURE_AVAILABLE and self.azure_key:
            self.backend = "azure"
            self.engine = AzureTTS(self.azure_key, self.azure_region)
            logger.success("ASHA TTS: Azure Neural Engine Active")
        elif self.google_api_key or (GOOGLE_AVAILABLE and self.google_creds):
            self.backend = "google"
            self.engine = GoogleTTS(api_key=self.google_api_key)
            logger.success("ASHA TTS: Google Wavenet Engine Active")
        elif self.sarvam_key:
            self.backend = "sarvam"
            self.sarvam_voice = "meera"
            logger.success("ASHA TTS: Sarvam AI Engine Active (Fallback)")
        else:
            self.backend = "silent"
            logger.error("No TTS Engine found! Check your dependencies.")

        # Pronunciation fixes for medical terms
        self.word_fixes = {
            'city care hospital': 'City Care Hospital',
            'doctor': 'doctor',
            'appointment': 'appointment',
            'emergency': 'emergency',
            'ambulance': 'ambulance',
        }

    async def speak(self, text: str):
        """Main speak method - routes to correct backend."""
        self.should_stop = False
        if not text or not text.strip():
            return

        text = self._clean_text(text)

        if self.backend == "edge":
            await self._play_edge_tts(text)
        elif self.backend == "google":
            audio = await asyncio.to_thread(self.engine.generate, text)
            if audio:
                await self._play_bytes(audio)
        elif self.backend == "azure":
            audio = await asyncio.to_thread(self.engine.generate, text)
            if audio:
                await self._play_bytes(audio)
        elif self.backend == "sarvam":
            await self._play_sarvam(text)

    async def generate_audio(self, text: str) -> bytes:
        """Returns raw audio bytes (for sending over Twilio WebSocket)."""
        if not text or not text.strip():
            return None
        text = self._clean_text(text)

        if self.backend == "edge":
            return await self._generate_edge_bytes(text)
        elif self.backend in ("google", "azure"):
            return await asyncio.to_thread(self.engine.generate, text)
        elif self.backend == "sarvam":
            return await self._get_sarvam_bytes(text)
        return None

    # ─── Edge-TTS (Microsoft, Free, Best Quality) ──────────────────────────

    async def _play_edge_tts(self, text: str):
        """Generate and play audio using Microsoft Edge-TTS."""
        try:
            audio_bytes = await self._generate_edge_bytes(text)
            if audio_bytes and not self.should_stop:
                await self._play_bytes(audio_bytes)
        except Exception as e:
            logger.error(f"Edge-TTS Error: {e}")

    async def _generate_edge_bytes(self, text: str) -> bytes:
        """Generate audio bytes from Edge-TTS."""
        try:
            communicate = edge_tts.Communicate(text, self.edge_voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data if audio_data else None
        except Exception as e:
            logger.error(f"Edge-TTS Generation Error: {e}")
            return None

    # ─── Sarvam (Fallback) ──────────────────────────────────────────────────

    async def _play_sarvam(self, text: str):
        audio = await self._get_sarvam_bytes(text)
        if audio:
            await self._play_bytes(audio)

    async def _get_sarvam_bytes(self, text: str) -> bytes:
        try:
            url = "https://api.sarvam.ai/text-to-speech"
            headers = {
                "api-subscription-key": self.sarvam_key,
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": [text],
                "target_language_code": "en-IN",
                "speaker": self.sarvam_voice,
                "pace": 1.0,
                "speech_sample_rate": 8000,
                "enable_preprocessing": False,
                "model": "bulbul:v3"
            }
            response = await asyncio.to_thread(
                requests.post, url, json=payload, headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                audio_b64 = data.get("audios", [None])[0]
                if audio_b64:
                    return base64.b64decode(audio_b64)
            else:
                logger.error(f"Sarvam TTS Failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Sarvam Error: {e}")
        return None

    # ─── Audio Playback (pygame) ────────────────────────────────────────────

    def _ensure_mixer(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)

    async def _play_bytes(self, audio_data: bytes):
        if self.should_stop:
            return
        
        # If streaming over WebSocket, bypass pygame entirely
        if hasattr(self, "output_callback") and self.output_callback:
            self.output_callback(audio_data)
            return

        try:
            self._ensure_mixer()
            audio_io = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_io)
            pygame.mixer.music.play()
            self.is_playing = True
            while pygame.mixer.music.get_busy():
                if self.should_stop:
                    pygame.mixer.music.stop()
                    break
                await asyncio.sleep(0.05)
            self.is_playing = False
        except Exception as e:
            logger.error(f"Playback Error: {e}")
            self.is_playing = False

    def stop(self):
        """Instantly stop TTS (for barge-in)."""
        self.should_stop = True
        if self.is_playing and pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.is_playing = False

    def _clean_text(self, text: str) -> str:
        """Remove markdown artifacts and clean text for TTS."""
        text = re.sub(r'[*#_`]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text


# ─── Google TTS ──────────────────────────────────────────────────────────────

class GoogleTTS:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.client = None
        if GOOGLE_AVAILABLE:
            try:
                self.client = texttospeech.TextToSpeechClient()
            except Exception as e:
                logger.warning(f"Google TTS SDK failed: {e}")
        self.url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"

    def generate(self, text: str) -> bytes:
        if self.client:
            try:
                synthesis_input = texttospeech.SynthesisInput(text=text)
                voice = texttospeech.VoiceSelectionParams(
                    language_code="en-IN",
                    name="en-IN-Neural2-A"
                )
                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz=24000
                )
                response = self.client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
                return response.audio_content
            except Exception as e:
                logger.error(f"Google SDK Error: {e}")
        return None


# ─── Azure TTS ───────────────────────────────────────────────────────────────

class AzureTTS:
    def __init__(self, key, region):
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
        )
        self.synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=None
        )

    def generate(self, text: str) -> bytes:
        result = self.synthesizer.speak_text_async(text).get()
        return result.audio_data
