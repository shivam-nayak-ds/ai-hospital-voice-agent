# AI Hospital Voice Agent: 10-Phase Implementation Plan

This roadmap is designed to take you from a blank directory to a production-grade, voice-enabled AI Hospital Assistant. Each phase is a building block for both the project and your learning.

---

### Phase 1: Foundation & Project Architecture
**Goal:** Set up a scalable structure and configuration management.
- **Key Tasks:**
  - Initialize Git and Virtual Environment.
  - Configure `.env` and `settings.py` (Pydantic Settings).
  - Define Global State and Logging (Loguru).
  - Setup Docker & Docker Compose base.
- **Learning:** Project structure patterns (Modular Monolith), Environment management.

### Phase 2: LLM Brain Integration (Groq/OpenAI)
**Goal:** Establish the core reasoning engine.
- **Key Tasks:**
  - Implement a generic LLM wrapper.
  - Integrate Groq (for speed) or OpenAI.
  - Implement streaming responses.
  - Create basic prompt templates for "Hospital Persona".
- **Learning:** API integrations, Streaming, Prompt Engineering.

### Phase 3: Knowledge Retrieval (RAG Pipeline)
**Goal:** Give the agent "Hospital Data" (Doctors, Timings, Services).
- **Key Tasks:**
  - Setup ChromaDB as the Vector Store.
  - Implement Document Loader (PDF/Text) for hospital policies.
  - Create an Embedding Pipeline (Sentence-Transformers).
  - Implement a Retrieval Tool for the agent.
- **Learning:** Vector Databases, Semantic Search, Chunking strategies.

### Phase 4: Agent Core & State Management
**Goal:** Enable multi-turn conversations with memory.
- **Key Tasks:**
  - Implement `AgentState` to track user details (Name, Symptoms, History).
  - Setup Short-term and Long-term Memory.
  - Build the main Agent Loop (Reasoning -> Action -> Observation).
- **Learning:** State machines, Context window management, Memory persistence.

### Phase 5: Hospital Tools & API Integration
**Goal:** Allow the agent to "Do" things (Book appointments).
- **Key Tasks:**
  - Build a mock Appointment Booking system (SQLAlchemy/SQLite).
  - Create a Tool Router to call Python functions from LLM intents.
  - Implement "Doctor Search" and "Department Info" tools.
- **Learning:** Tool calling (Function calling), Database ORM, Mocking external APIs.

### Phase 6: STT - The "Ears" (Speech-to-Text)
**Goal:** Convert user voice input to text.
- **Key Tasks:**
  - Integrate OpenAI Whisper (Local or API).
  - Implement Real-time Audio capture (Sounddevice).
  - Add VAD (Voice Activity Detection) to stop recording when the user stops talking.
- **Learning:** Audio processing, Signal processing basics, VAD algorithms.

### Phase 7: TTS - The "Voice" (Text-to-Speech)
**Goal:** Make the agent talk back.
- **Key Tasks:**
  - Integrate `pyttsx3` (Offline) or OpenAI/ElevenLabs (Online).
  - Implement an asynchronous playback queue.
  - Optimize for low-latency (Speak while LLM is still generating).
- **Learning:** TTS Engines, Asynchronous audio playback, Latency optimization.

### Phase 8: Unified Backend API (FastAPI)
**Goal:** Create a bridge for the frontend.
- **Key Tasks:**
  - Create WebSocket endpoints for real-time voice streaming.
  - Define Pydantic schemas for requests/responses.
  - Implement Health checks and Telemetry.
- **Learning:** WebSockets, FastAPI best practices, API Security.

### Phase 9: Modern Frontend Interface
**Goal:** A "WOW" factor UI for the user.
- **Key Tasks:**
  - Build a dashboard using Streamlit or React.
  - Add a "Pulsing" microphone animation for voice input.
  - Display real-time chat history and extracted appointment details.
- **Learning:** UI/UX for AI, Real-time state syncing between Frontend and Backend.

### Phase 10: Optimization & Production Ready
**Goal:** Polish, Test, and Deploy.
- **Key Tasks:**
  - Implement unit/integration tests (Pytest).
  - Add Latency Tracking for every step (STT -> LLM -> TTS).
  - Finalize Dockerization for one-click deployment.
  - Add "Privacy Mode" (PII masking).
- **Learning:** Performance profiling, Testing AI agents, PII security.

---

> [!TIP]
> **Learning Tip:** Don't rush to Phase 6. Mastering Phase 1-5 will give you a solid "Text Agent" which is the brain. Voice is just the interface!
