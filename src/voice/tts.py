import os
import pygame
import asyncio
import re
import io
import base64
import requests
from src.utils.logger import custom_logger as logger
from dotenv import load_dotenv

load_dotenv()

class AshaTTS:
    """
    Ultra-Fast In-Memory Indian Receptionist Voice TTS.
    Powered by Sarvam AI for Human-like Indian accent.
    """
    
    def __init__(self, voice_style: str = "friendly"):
        # Initialize mixer only if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=24000) # Sarvam provides high-quality audio
            
        self.api_key = os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            logger.error("SARVAM_API_KEY not found in .env! Asha will be silent.")
            
        # 'kavya' provides a great young receptionist feel for bulbul:v3
        self.voice = "kavya" 
        self.is_playing = False
        self.should_stop = False
        
        if self.api_key:
            logger.success(f"Asha Pro-Voice Engine initialized! (Sarvam AI Active)")

    async def speak(self, text: str):
        """Speak text using in-memory byte streams."""
        if not text or not text.strip() or self.should_stop:
            return

        # Clean markdown artifacts
        text = re.sub(r'[*#_`]', '', text)
        
        await self.play_chunk(text)

    async def play_chunk(self, chunk: str):
        if not self.api_key:
            return
            
        try:
            url = "https://api.sarvam.ai/text-to-speech"
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": [chunk],
                "target_language_code": "hi-IN",
                "speaker": self.voice,
                "model": "bulbul:v3"
            }
            
            # Using to_thread to prevent blocking the async voice loop
            response = await asyncio.to_thread(
                requests.post, url, json=payload, headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Sarvam API Rejected! {response.status_code} - {response.text}")
                return
                
            response.raise_for_status()
            
            data = response.json()
            audio_base64 = None
            
            # Extract base64 based on Sarvam's API structure
            if "audios" in data and len(data["audios"]) > 0:
                audio_base64 = data["audios"][0]
            elif "audio_content" in data: 
                audio_base64 = data["audio_content"]
                
            if not audio_base64 or self.should_stop:
                return
                
            # Play directly from RAM (0 Disk I/O = Instant Voice)
            audio_data = base64.b64decode(audio_base64)
            audio_io = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_io)
            pygame.mixer.music.play()
            
            self.is_playing = True
            while pygame.mixer.music.get_busy():
                if self.should_stop:
                    pygame.mixer.music.stop()
                    break
                await asyncio.sleep(0.01) # Check quickly for barge-in
            
            self.is_playing = False
                
        except Exception as e:
            logger.error(f"Sarvam TTS Error: {e}")
            self.is_playing = False

    def stop(self):
        """Instantly stops the audio playback (For Barge-in)"""
        self.should_stop = True
        if self.is_playing:
            pygame.mixer.music.stop()
            self.is_playing = False
