# Phase 2: LLM Brain Integration (10 Steps)

Is phase mein hum apne Hospital Agent ko "Dimaag" denge. Hum Groq (Super-fast LLM) ko connect karenge taaki hamara agent patient ki baatein samajh sake.

### Steps Breakdown:

1.  **Step 1: LLM Client Initialization**
    - `groq` SDK install karna aur client setup karna.
2.  **Step 2: Base LLM Wrapper**
    - `src/llm/base.py` mein ek abstract class banana taaki aage OpenAI/Gemini easily add ho sakein.
3.  **Step 3: Groq Provider Implementation**
    - `src/llm/providers/groq.py` mein chat completion ka core logic likhna.
4.  **Step 4: Prompt Template Manager**
    - `config/prompts.py` mein "Hospital Persona" ke system prompts define karna.
5.  **Step 5: Chat Engine Service**
    - `src/llm/engine.py` banana jo agent ke intentions aur replies ko handle karega.
6.  **Step 6: Streaming Logic Integration**
    - `yield` generator use karke LLM se real-time chunks receive karna (Voice ke liye bohot zaruri hai).
7.  **Step 7: Context & Memory Injection**
    - `AgentState` se pichle 5-10 messages ko prompt mein automatically add karna.
8.  **Step 8: Token & Latency Tracking**
    - Har response ke saath ye track karna ki "Time-to-First-Byte" (TTFB) kitna hai.
9.  **Step 9: Error Handling & Retries**
    - `tenacity` library ya simple try-except se Rate Limits aur Connection errors handle karna.
10. **Step 10: Phase 2 Verification**
    - `src/main.py` ko update karna aur AI se actual "Medical" conversation karke test karna.

---

> [!IMPORTANT]
> **Learning Goal:** Is phase se aap seekhenge ki kaise AI model ko ek "Professional Personality" di jati hai aur kaise low-latency (Fast) responses handle kiye jate hain.
