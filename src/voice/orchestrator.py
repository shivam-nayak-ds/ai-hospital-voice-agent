import time
import sys
import os
import threading
import pyaudio
import asyncio
import queue
from src.voice.recorder import AshaVoiceRecorder
from src.voice.stt import AshaSTT
from src.voice.tts import AshaTTS
from src.agent.orchestrator import AshaOrchestrator
from src.utils.logger import custom_logger as logger
import enum

class VoiceState(enum.Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"

CURRENT_STATE = VoiceState.IDLE
LAST_CALL_TIME = 0

def start_voice_mode():
    global CURRENT_STATE
    try:
        brain = AshaOrchestrator()
        tts = AshaTTS()
        recorder = AshaVoiceRecorder()
        
        # ==========================================
        # 🧠 CORE LOGIC: Handling User's Sentence
        # ==========================================
        def handle_user_speech(text):
            global CURRENT_STATE, LAST_CALL_TIME
            
            # 🔥 DEBOUNCE: Prevent multiple rapid LLM calls
            if time.time() - LAST_CALL_TIME < 1.5:
                return
            LAST_CALL_TIME = time.time()
            
            if not text or len(text.strip()) < 2:
                return
                
            sys.stdout.write(f"\r[HEARD]: \"{text}\"\n")
            CURRENT_STATE = VoiceState.PROCESSING
            tts.should_stop = False
            
            def llm_to_tts_streamer():
                global CURRENT_STATE
                CURRENT_STATE = VoiceState.SPEAKING
                print("[ASHA]: ", end="", flush=True)
                
                full_response = ""
                
                # Stream LLM tokens (Groq is very fast, so this takes <1 second)
                try:
                    for token in brain.handle_request(text):
                        if tts.should_stop:
                            break # User interrupted! Stop generating.
                            
                        print(token, end="", flush=True)
                        clean_token = token.replace("😊", "").replace("🙏", "").replace("🏥", "").replace("🚑", "")
                        full_response += clean_token
                        
                except Exception as e:
                    logger.error(f"LLM Crash: {e}")
                    full_response = "माफ़ कीजिये, सिस्टम अभी व्यस्त है, कृपया थोड़ी देर बाद प्रयास करें।"
                        
                print("\n")
                if full_response.strip() and not tts.should_stop:
                    # Send entire response to Sarvam API at once (No pauses between sentences!)
                    asyncio.run(tts.speak(full_response.strip()))
                    
                if brain.state.intent == "exit":
                    logger.info("Call ended by user. Exiting.")
                    import os
                    os._exit(0)
                    
                CURRENT_STATE = VoiceState.IDLE

            # Start LLM processing in a background thread
            threading.Thread(target=llm_to_tts_streamer, daemon=True).start()

        # ==========================================
        # 🎙️ EVENT LISTENER: Deepgram STT Callback
        # ==========================================
        def on_transcript(text, is_final):
            global CURRENT_STATE
            
            # 🔥 BARGE-IN (Interruption Detection)
            if CURRENT_STATE == VoiceState.SPEAKING:
                if len(text.split()) > 2: # Strict Min words condition to avoid noise
                    logger.warning("\n[BARGE-IN DETECTED] You interrupted Asha. Stopping audio!")
                    tts.stop() # Instantly stop TTS
                    CURRENT_STATE = VoiceState.LISTENING

            if is_final:
                # Deepgram detected a pause. Execute the Brain!
                handle_user_speech(text)

        # Initialize Deepgram
        stt = AshaSTT(on_transcript_callback=on_transcript)
        if not stt.start():
            return

        # Mic Callback -> Directly pipe raw audio bytes to Deepgram!
        frame_counter = 0
        def mic_callback(in_data, frame_count, time_info, status):
            nonlocal frame_counter
            # 🔥 Echo Cancellation Hack: Mute mic while Asha is talking
            if CURRENT_STATE != VoiceState.SPEAKING:
                stt.send_audio(in_data)
            else:
                frame_counter += 1
                if frame_counter % 20 == 0: # Every ~500ms
                    stt.send_keepalive()
            return (in_data, pyaudio.paContinue)

        recorder.start_recording(mic_callback)
        logger.success("Asha Pro-Voice (Real-time Streaming) Active! Call connected.")
        
        # Initial Greeting
        CURRENT_STATE = VoiceState.SPEAKING
        print("[ASHA]: नमस्ते! मैं आशा हूँ, सिटी केयर हॉस्पिटल से।", flush=True)
        asyncio.run(tts.speak("नमस्ते! मैं आशा हूँ, सिटी केयर हॉस्पिटल से। मैं आपकी क्या सहायता कर सकती हूँ?"))
        CURRENT_STATE = VoiceState.IDLE

        # Keep alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Voice Agent stopped cleanly.")
    except Exception as e:
        logger.error(f"Orchestrator Error: {e}")
    finally:
        if 'recorder' in locals(): recorder.stop_recording()
        if 'stt' in locals(): 
            try:
                # Fire and forget disconnect
                threading.Thread(target=stt.disconnect, daemon=True).start()
            except Exception:
                pass
        
        os._exit(0)

if __name__ == "__main__":
    start_voice_mode()
