import time
from fastapi import APIRouter, HTTPException, status
from api.schemas.request import ChatRequest
from api.schemas.response import ChatResponse
from src.agents.ananya_agent import AshaSwarm
from src.agents.memory import get_session_store
from src.utils.logger import custom_logger as logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# ─── Redis Session Store ──────────────────────────────────────────────────────
# All Gunicorn workers share session state via Redis.
# No in-memory session dicts — fully stateless request handling.
_session_store = get_session_store()

@router.post("", response_model=ChatResponse, summary="Process chat message through AI agents")
async def chat_endpoint(payload: ChatRequest):
    """
    POST /api/chat
    ------------
    Receives message and session_id from user, loads state from Redis (or creates new),
    triggers LangGraph multi-agent execution, saves state back to Redis, and returns response.
    Fully stateless — any Gunicorn worker can handle any session.
    """
    session_id = payload.session_id
    user_message = payload.message
    
    log = logger.bind(session_id=session_id)
    log.info(f"REST API Chat request received: '{user_message}'")
    
    start_time = time.time()
    
    try:
        # 1. Load session state from Redis (shared across all workers)
        saved_state = await _session_store.load(session_id)
        
        # 2. Create fresh swarm with loaded state (or new if no state exists)
        swarm = AshaSwarm(user_id=session_id, initial_state=saved_state)
        
        # 3. Execute conversation turn and assemble streamed words
        response_text = ""
        async for chunk in swarm.run(user_message):
            response_text += chunk
            
        # 4. Save updated state back to Redis (2-hour TTL auto-expires inactive sessions)
        await _session_store.save(session_id, swarm.state, ttl_hours=2)
            
        latency_ms = round((time.time() - start_time) * 1000, 2)
        log.info(f"Response compiled in {latency_ms} ms: '{response_text}'")
        
        # Extract intent and potential actions from session state
        intent = swarm.state.get("current_intent", "chitchat")
        suggested_actions = []
        if intent == "book_appointment":
            suggested_actions = ["Confirm Date", "Cancel Booking"]
        elif intent == "emergency":
            suggested_actions = ["Call Emergency Desk"]
            
        return ChatResponse(
            session_id=session_id,
            response_text=response_text.strip(),
            intent_detected=intent,
            suggested_actions=suggested_actions,
            status="success",
            latency_ms=latency_ms
        )
        
    except Exception as e:
        log.exception(f"Exception raised in API Chat Handler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat query: {str(e)}"
        )
