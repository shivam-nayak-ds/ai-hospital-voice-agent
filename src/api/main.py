from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.agent.orchestrator import AshaOrchestrator
from src.utils.logger import custom_logger as logger

# 1. FastAPI App Initialization
app = FastAPI(
    title="Asha AI Hospital Agent API",
    description="The logic engine for City Care Hospital.",
    version="1.0.0"
)

# 2. Load Orchestrator (SQL + RAG + Guardrails)
orchestrator = AshaOrchestrator()

# 3. Pydantic Models for Validation
class ChatRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = "default_user"

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

# --- Endpoints ---

@app.get("/")
async def root():
    """Health Check"""
    return {"status": "online", "message": "Asha AI Backend is running."}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main Chat API: Receives text and returns Asha's intelligent response.
    """
    try:
        logger.info(f"Received Request: {request.user_input}")
        
        # Collecting tokens from orchestrator stream
        full_text = ""
        for token in orchestrator.handle_request(request.user_input):
            full_text += token
            
        return ChatResponse(response=full_text.strip())

    except Exception as e:
        logger.error(f"API Exception: {e}")
        raise HTTPException(status_code=500, detail="Asha is facing technical issues.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
