import time
import sys
import asyncio
import enum
import re
from typing import Optional, Callable

from src.voice.stt import AshaSTT
from src.voice.tts import AshaTTS
from src.agents.ananya_agent import AshaSwarm, AshaIntentClassifier
from src.utils.logger import custom_logger as logger
from src.voice.voice_quality import filter_transcript, TranscriptDeduplicator, smart_split_sentences, speak_with_intent

class VoiceState(enum.Enum):
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"

class AshaVoiceOrchestrator:
    """
    Enterprise Orchestrator: Fully Asynchronous.
    Coordinates STT -> Intent -> LLM -> TTS using asyncio for concurrency.
    Supports:
      - Real-time Barge-in (Interruption)
      - Non-blocking Sentence Streaming
      - Async Task Management
    """

    def __init__(self, output_callback: Optional[Callable] = None, user_id: str = "default_user"):
        logger.info(f"Initializing Async ASHA Voice Orchestrator for {user_id}...")
        self.brain = AshaSwarm(user_id=user_id)
        # Classifier is kept only for TTS prosody (SSML rate/pitch selection).
        # Full intent routing is done inside LangGraph via the Planner NLU node.
        self.classifier = AshaIntentClassifier()
        self.tts = AshaTTS()

        self.output_callback = output_callback
        self.tts.output_callback = output_callback

        self.state = VoiceState.LISTENING
        self._current_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Dedup guard
        self._dedup = TranscriptDeduplicator(window_seconds=3.0)

        logger.success("Async Orchestrator Ready! [AsyncIO | Non-Blocking | Sub-500ms]")

    # ─── Main Entry Point ───────────────────────────────────────────────────

    def on_transcript(self, text: str, is_final: bool, confidence: float = 1.0):
        """
        Called by STT. We use asyncio.create_task to ensure 
        we don't block the audio processing loop.
        """
        if not text.strip():
            return

        if not is_final:
            sys.stdout.write(f"\r[HEARING]: {text}   ")
            sys.stdout.flush()
            return

        # Handle final transcript in an async context
        asyncio.create_task(self._handle_final_transcript(text, confidence))

    def on_speech_start(self):
        """
        BARGE-IN: User started talking.
        Stop AI immediately for instant responsiveness.
        """
        if self.state == VoiceState.SPEAKING or self.state == VoiceState.THINKING:
            logger.warning("[VAD] Speech started - interrupting AI.")
            asyncio.create_task(self.stop_current_response())

    async def _handle_final_transcript(self, text: str, confidence: float):
        """Async handler for final transcripts."""
        clean_text = filter_transcript(text, confidence)
        if not clean_text or self._dedup.is_duplicate(clean_text):
            return

        logger.info(f"\n[USER]: {clean_text}")

        # ── BARGE-IN: Interrupt current speaking task ──
        if self.state == VoiceState.SPEAKING or self.state == VoiceState.THINKING:
            logger.warning("[BARGE-IN] User interrupted AI!")
            await self.stop_current_response()

        # Start new processing task
        self._current_task = asyncio.create_task(self._process_and_respond(clean_text))

    async def stop_current_response(self):
        """Forcefully stops any ongoing thinking or speaking."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError:
                pass
        
        self._stop_event.set()
        self.tts.stop()
        self.state = VoiceState.LISTENING
        self._stop_event.clear()

    # ─── Processing Pipeline ────────────────────────────────────────────────

    async def _process_and_respond(self, text: str):
        """Async Pipeline: Brain (LangGraph) -> TTS.
        
        Intent classification is handled inside LangGraph by the Planner NLU node.
        Here we run a lightweight local rule-check ONLY to determine TTS prosody (SSML),
        which must happen before the first audio byte is sent.
        """
        try:
            self.state = VoiceState.THINKING

            # Lightweight local intent check — used ONLY for TTS prosody (SSML rate/pitch).
            # The full LLM-based classification happens inside graph.ainvoke via the Planner node.
            intent, _ = await self.classifier.classify(text)
            logger.info(f"[PROSODY INTENT]: {intent} (local rule-check for SSML only)")

            # Generate & Stream Response via LangGraph
            self.state = VoiceState.SPEAKING
            await self._stream_response(text, intent)
            
        except asyncio.CancelledError:
            logger.info("[Orchestrator] Task cancelled.")
        except Exception as e:
            logger.error(f"Response generation error: {e}")
        finally:
            self.state = VoiceState.LISTENING

    async def _stream_response(self, text: str, intent: str):
        """
        Concurrent LLM Streaming + TTS Pre-fetching.
        We fetch audio for sentence N+1 while sentence N is still playing.
        This removes the robotic gaps between sentences.
        """
        sentence_buffer = ""
        full_response = ""
        audio_queue = asyncio.Queue()
        
        # Background task to play audio from the queue
        playback_task = asyncio.create_task(self._playback_worker(audio_queue))

        try:
            async for token in self.brain.run(text):
                if self._stop_event.is_set():
                    break

                sentence_buffer += token
                full_response += token

                # Check if we have a complete sentence
                sentences = smart_split_sentences(sentence_buffer)
                if len(sentences) > 1:
                    for sentence in sentences[:-1]:
                        if sentence and not self._stop_event.is_set():
                            logger.success(f"[AI STREAMING]: {sentence}")
                            # Trigger TTS generation in background and put in queue
                            asyncio.create_task(self._enqueue_audio(sentence, intent, audio_queue))
                    sentence_buffer = sentences[-1]
                
                await asyncio.sleep(0)

            # Enqueue remaining text
            if sentence_buffer.strip() and not self._stop_event.is_set():
                logger.success(f"[AI STREAMING]: {sentence_buffer.strip()}")
                await self._enqueue_audio(sentence_buffer.strip(), intent, audio_queue)

            # Signal end of stream
            await audio_queue.put(None)
            await playback_task

        except Exception as e:
            logger.error(f"Streaming response error: {e}")
        finally:
            logger.info(f"[AI FULL RESPONSE]: {full_response.strip()}")

    async def _enqueue_audio(self, text: str, intent: str, queue: asyncio.Queue):
        """Generates audio bytes and puts them in the playback queue."""
        try:
            # We use a wrapper to get audio bytes without playing them immediately
            from src.voice.voice_quality import wrap_ssml
            clean = re.sub(r'[*#_`]', '', text).strip()
            
            if self.tts.backend == "edge":
                import edge_tts
                ssml = wrap_ssml(clean, intent=intent, voice=self.tts.edge_voice)
                communicate = edge_tts.Communicate(ssml, self.tts.edge_voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                if audio_data:
                    await queue.put(audio_data)
            else:
                # Fallback for other backends
                audio_data = await self.tts.generate_audio(clean)
                if audio_data:
                    await queue.put(audio_data)
        except Exception as e:
            logger.error(f"Audio enqueue error: {e}")

    async def _playback_worker(self, queue: asyncio.Queue):
        """Background worker that plays audio chunks sequentially."""
        while not self._stop_event.is_set():
            audio_data = await queue.get()
            if audio_data is None: # End of stream signal
                break
            
            try:
                # Play the bytes using the TTS engine's playback logic
                await self.tts._play_bytes(audio_data)
            except Exception as e:
                logger.error(f"Playback worker error: {e}")
            finally:
                queue.task_done()

    async def _speak_async(self, text: str, intent: str = "llm_chat"):
        """Async TTS execution."""
        if not text or self._stop_event.is_set():
            return
        
        try:
            # speak_with_intent is already async
            await speak_with_intent(self.tts, text, intent)
        except Exception as e:
            logger.error(f"TTS Execution Error: {e}")


# ─── Local Mic Testing Entry Point ──────────────────────────────────────────

if __name__ == "__main__":
    import pyaudio
    from src.voice.recorder import AshaVoiceRecorder

    orch = AshaVoiceOrchestrator()

    # LOCAL MIC: Use linear16 @ 16000Hz (PyAudio default format)
    stt = AshaSTT(on_transcript_callback=orch.on_transcript)
    stt.start(encoding="linear16", sample_rate=16000)

    recorder = AshaVoiceRecorder()

    def mic_callback(in_data, frame_count, time_info, status):
        stt.send_audio(in_data)
        return (None, pyaudio.paContinue)

    print("\n" + "="*50)
    print("  ASHA LIVE VOICE TEST (Mic + English)")
    print("  Speak into your microphone...")
    print("  Press Ctrl+C to stop.")
    print("="*50 + "\n")

    try:
        recorder.start_recording(callback=mic_callback)
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recorder.stop_recording()
        stt.disconnect()
