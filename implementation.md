# ASHA 2.0 - Implementation Roadmap 🚀

This document tracks the current status of the ASHA AI-Hospital-Agent project and outlines a comprehensive 20-phase implementation plan to build a robust, scalable, and automated hospital workflow assistant.

## Current Project Status 🔍

**Analyzed Directories:** `d:\AI-Hospital-Agent`
*   **Structure:** The foundational structure is present with `src/` (agent, api, llm, rag, utils, voice), `data/`, `config/`, `frontend/`, `tests/`, and `scripts/`.
*   **Infrastructure:** Dockerized setup (`docker-compose.yml`, `Dockerfile`), environment configuration (`.env.example`), and dependencies (`requirements.txt`) are initiated.
*   **Current Focus:** Active development is happening across LLM providers, agent schemas, and voice (TTS/STT) modules.

---

## The 20-Phase Implementation Plan 🗺️

### PART 1: V1 - MVP Voice & Booking Foundation (The Core Value)
*Focus: Get the booking flow working via voice/chat without RAG.*

*   [ ] **Phase 1: Project Skeleton & API Core**
    *   Initialize FastAPI backend.
    *   Set up CORS, logging, and basic health endpoints.
*   [ ] **Phase 2: Database Schema & Booking Logic**
    *   Design SQLite/PostgreSQL schema for `Patients`, `Appointments`, and `Doctors`.
    *   Create CRUD endpoints for booking appointments.
*   [ ] **Phase 3: State Management & Conversation Flow**
    *   Implement `AshaState` (Pydantic models) to track conversation steps (Problem -> Doctor -> Time -> Confirm).
    *   Build the non-blocking state machine.
*   [ ] **Phase 4: LLM Brain Integration**
    *   Integrate base LLM (Gemini/OpenAI).
    *   Design strict system prompts for the Receptionist persona (Hindi/Hinglish).
*   [ ] **Phase 5: Speech-to-Text (STT) Pipeline**
    *   Integrate Whisper/Deepgram for real-time Hindi/Hinglish audio transcription.
*   [ ] **Phase 6: Text-to-Speech (TTS) Pipeline**
    *   Integrate Edge-TTS/ElevenLabs.
    *   Optimize for human-like prosody and minimal latency.
*   [ ] **Phase 7: V1 End-to-End Local Assembly**
    *   Connect STT -> LLM -> DB -> TTS locally.
    *   Validate a complete mock voice booking flow.

### PART 2: V2 - RAG Brain (Context & Intelligence)
*Focus: Adding hospital knowledge (FAQs, Doctor Timings) safely.*

*   [ ] **Phase 8: Vector Database Setup**
    *   Initialize ChromaDB/FAISS.
    *   Set up embedding models (e.g., OpenAI embeddings).
*   [ ] **Phase 9: Knowledge Ingestion Pipeline**
    *   Parse text/PDFs from `data/City_Care_Hospital_Knowledge_Base.pdf`.
    *   Chunk and store doctor schedules, FAQs, and pricing in Vector DB.
*   [ ] **Phase 10: RAG Retriever Integration**
    *   Build retriever logic to fetch context based on user queries.
*   [ ] **Phase 11: LLM + RAG Guardrails**
    *   Update LLM prompts to strictly use RAG context.
    *   Implement safety guardrails: **NO MEDICAL ADVICE, NO DIAGNOSIS.**
*   [ ] **Phase 12: V2 End-to-End Testing**
    *   Test FAQ queries + Booking flow combined (e.g., "MRI cost kya hai? Kal doctor Sharma available hain?").

### PART 3: Omnichannel Integration (Twilio & WhatsApp)
*Focus: Connecting the brain to the real world.*

*   [ ] **Phase 13: Twilio Telephony Setup**
    *   Configure Twilio Voice webhooks.
    *   Set up Ngrok for local webhook testing.
*   [ ] **Phase 14: Real-time Voice Streaming**
    *   Implement WebSocket connections for bi-directional audio streaming (User Audio <-> Twilio <-> FastAPI).
*   [ ] **Phase 15: WhatsApp Chatbot Integration**
    *   Integrate Twilio WhatsApp API.
    *   Route text inputs to the same ASHA brain.
*   [ ] **Phase 16: Omnichannel Sync**
    *   Ensure state memory persists across voice calls and WhatsApp messages for the same user phone number.

### PART 4: V3 - Multimodal & Production Scale
*Focus: Vision capabilities, Admin Dashboard, and Deployment.*

*   [ ] **Phase 17: Multimodal Vision API Setup**
    *   Integrate OpenAI Vision / Gemini Vision for image inputs.
*   [ ] **Phase 18: Prescription/Report Understanding**
    *   Implement logic to extract text from user-uploaded images (via WhatsApp).
    *   Strict guardrails for explaining reports without providing medical treatment advice.
*   [ ] **Phase 19: Admin Dashboard MVP**
    *   Build a simple frontend/dashboard (Streamlit/React) to view appointments, call logs, and recordings.
*   [ ] **Phase 20: Production Deployment & Analytics**
    *   Dockerize the complete application.
    *   Deploy to a cloud provider (AWS/Render).
    *   Setup basic conversion analytics tracking (Calls vs. Bookings).

### PART 5: V4 - The "1 Crore" Enterprise Architecture (Flagship Level) 🏆
*Focus: True scalability, concurrency, and industry-standard Multi-Agent design.*

*   [ ] **Phase 21: Race-Condition Safe Database Schema**
    *   Implement Row-Locking / Redis transactions in MySQL to prevent double-booking.
    *   Separate Live DB (SQL) from Static DB (Vector).
*   [ ] **Phase 22: True Multi-Agent Swarm (OOMAS)**
    *   Refactor `AshaAgent` into isolated Agent Classes (`SupervisorAgent`, `BookingAgent`, `EmergencyAgent`, `KnowledgeAgent`).
    *   Implement strict tool separation to eliminate prompt injection / hallucination risks.
*   [ ] **Phase 23: Nightly RAG Auto-Sync Pipeline**
    *   Create `scripts/nightly_sync.py` to automatically embed new hospital policy PDFs at 1 AM via CRON jobs.
*   [ ] **Phase 24: Telephony Concurrency & WebSocket Server**
    *   Upgrade FastAPI to handle 50+ simultaneous Twilio voice streams.
    *   Migrate entirely away from `pyaudio` local microphone dependence.
*   [ ] **Phase 25: MLOps & Observability Dashboard**
    *   Track LLM Latency (ms), Agent Drop-off Rates, and Context-Window limits using Prometheus/Grafana or a custom admin panel.
