import time
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status
from api.schemas.request import ChatRequest
from api.schemas.response import ChatResponse
from src.agents.ananya_agent import AshaSwarm
from src.utils.logger import custom_logger as logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# In-memory session store: session_id -> (AshaSwarm, last_active_timestamp)
_active_sessions: dict = {}
_session_timestamps: dict = {}
SESSION_TTL_HOURS = 2

@router.post("", response_model=ChatResponse, summary="Process chat message through AI agents")
async def chat_endpoint(payload: ChatRequest):
    """
    POST /api/chat
    ------------
    Receives message and session_id from user, loads or creates the conversational session,
    triggers LangGraph multi-agent execution, and returns the response.
    """
    session_id = payload.session_id
    user_message = payload.message
    
    log = logger.bind(session_id=session_id)
    log.info(f"REST API Chat request received: '{user_message}'")
    
    start_time = time.time()
    
    try:
        # Load or initialize the session swarm
        if session_id not in _active_sessions:
            log.info(f"Initializing new conversation session swarm for ID: {session_id}")
            _active_sessions[session_id] = AshaSwarm(user_id=session_id)
        
        # Update last-active timestamp
        _session_timestamps[session_id] = datetime.now()
        swarm = _active_sessions[session_id]
        
        # Periodic cleanup: remove sessions older than SESSION_TTL_HOURS
        now = datetime.now()
        expired = [sid for sid, ts in _session_timestamps.items()
                   if now - ts > timedelta(hours=SESSION_TTL_HOURS)]
        for sid in expired:
            _active_sessions.pop(sid, None)
            _session_timestamps.pop(sid, None)
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired chat sessions")
        
        # Execute conversation turn and assemble streamed words
        response_text = ""
        async for chunk in swarm.run(user_message):
            response_text += chunk
            
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
