"""
livekit_worker.py
-----------------
LiveKit Agent Worker for browser-based voice calls.
Replaces Twilio WebSocket with WebRTC via LiveKit Cloud (free tier).

Flow:
  Browser mic → LiveKit → Deepgram STT → AshaSwarm → Edge TTS → LiveKit → Browser speaker

Usage:
    python -m src.voice.livekit_worker

Requires env vars:
    LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, DEEPGRAM_API_KEY
"""

import asyncio
import os
import sys

sys.path.insert(0, ".")

from dotenv import load_dotenv

load_dotenv()

from livekit import agents
from livekit.agents import AutoSubscribe
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram as dg_plugin

from src.utils.logger import custom_logger as logger

# ─── LiveKit Cloud Config ────────────────────────────────────────────────────

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

# ─── Agent Entry Point ───────────────────────────────────────────────────────

async def entrypoint(ctx: agents.JobContext):
    """
    Called when a new room is created or a participant triggers the agent.
    Sets up STT → LLM pipeline → TTS for the voice session.
    """
    participant = ctx.room.remote_participants
    user_id = list(participant.keys())[0] if participant else "livekit_user"

    logger.info(f"LiveKit agent joining room: {ctx.room.name} (user: {user_id})")

    # Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.success(f"LiveKit agent connected to room: {ctx.room.name}")

    # ── STT: Deepgram Nova-2 ──
    stt = dg_plugin.STT(
        model="nova-2",
        language="en-IN",
    )

    # ── LLM: AshaSwarm wrapper ──
    # We wrap AshaSwarm as an LLM-like interface for the pipeline
    from src.agents.ananya_agent import AshaSwarm
    swarm = AshaSwarm(user_id=user_id)

    class AshaLLM:
        """Adapter: wraps AshaSwarm.run() as a streaming LLM for VoicePipelineAgent."""

        async def chat(self, *, chat_ctx, **kwargs):
            """Called by VoicePipelineAgent when user speaks."""
            # Get the last user message from the chat context
            user_text = ""
            if hasattr(chat_ctx, 'messages') and chat_ctx.messages:
                for msg in reversed(chat_ctx.messages):
                    if hasattr(msg, 'content') and msg.content:
                        user_text = msg.content
                        break
                    elif isinstance(msg, dict) and msg.get("content"):
                        user_text = msg["content"]
                        break

            if not user_text:
                user_text = "hello"

            logger.info(f"[LiveKit LLM] User said: '{user_text}'")

            # Stream response from AshaSwarm
            async def stream():
                full_text = ""
                async for chunk in swarm.run(user_text):
                    full_text += chunk
                    yield chunk
                logger.info(f"[LiveKit LLM] Response: '{full_text[:100]}...'")

            return stream()

    # ── TTS: Edge TTS (free, no API key needed) ──
    # We use a custom TTS wrapper since VoicePipelineAgent expects a TTS plugin
    from src.voice.tts import AshaTTS as _AshaTTS

    class EdgeTTSSynth:
        """Adapter: wraps our AshaTTS (Edge-TTS backend) for VoicePipelineAgent."""

        def __init__(self):
            self._tts = _AshaTTS()

        async def synthesize(self, *, text: str, **kwargs):
            """Called by VoicePipelineAgent to generate audio for each sentence."""
            import re
            clean = re.sub(r'[*#_`]', '', text).strip()
            if not clean:
                return b""

            try:
                audio_data = await self._tts.generate_audio(clean)
                return audio_data or b""
            except Exception as e:
                logger.error(f"[LiveKit TTS] Synthesis error: {e}")
                return b""

    # ── Build Voice Pipeline ──
    agent = VoicePipelineAgent(
        stt=stt,
        llm=AshaLLM(),
        tts=EdgeTTSSynth(),
        # Voice Activity Detection settings
        allow_interruptions=True,
        min_endpointing_delay=0.5,
    )

    # Start the agent — it will listen for user speech and respond
    agent.start(ctx.room)

    # Greet the user
    await agent.say("Welcome to Lifeline Hospital. I am Ananya, your virtual assistant. How can I help you today?")


# ─── Worker Startup ──────────────────────────────────────────────────────────

def main():
    """Start the LiveKit agent worker."""
    if not LIVEKIT_URL:
        logger.error("LIVEKIT_URL not set. Add it to .env: LIVEKIT_URL=wss://your-project.livekit.cloud")
        sys.exit(1)

    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        logger.error("LIVEKIT_API_KEY / LIVEKIT_API_SECRET not set in .env")
        sys.exit(1)

    logger.info(f"Starting LiveKit agent worker → {LIVEKIT_URL}")

    worker = agents.Worker(
        entrypoint_fnc=entrypoint,
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    )

    # Run the worker (blocks forever, handles room assignments)
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
