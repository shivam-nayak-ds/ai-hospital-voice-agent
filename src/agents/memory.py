"""
memory.py
---------
Manages state persistence, conversation history pruning, and session-based context.
Prevents context window overflow while maintaining relevant context across multi-turn sessions.

Includes RedisSessionStore for cross-worker session sharing (Gunicorn multi-worker safe).
"""

import json
from typing import List, Dict, Any, Optional
from src.utils.logger import custom_logger as logger

from src.utils.message_helper import get_message_role

class SessionMemoryManager:
    """
    Manages short-term conversational history pruning and session context cache.
    """
    def __init__(self, max_history_turns: int = 10):
        self.max_history_turns = max_history_turns
        logger.info(f"SessionMemoryManager initialized with max_history_turns={max_history_turns}")

    def prune_messages(self, messages: List[Any]) -> List[Any]:
        """
        Prunes the list of messages to ensure we only keep the system prompt 
        and the last N active conversation turns (user/assistant exchanges).
        """
        if not messages:
            return []
            
        system_messages = [msg for msg in messages if get_message_role(msg) == "system"]
        chat_messages = [msg for msg in messages if get_message_role(msg) in ["user", "assistant"]]
        
        # Max turns * 2 (user + assistant per turn)
        cutoff = self.max_history_turns * 2
        if len(chat_messages) > cutoff:
            logger.info(f"Pruning chat history from {len(chat_messages)} to {cutoff} messages.")
            chat_messages = chat_messages[-cutoff:]
            
        return system_messages + chat_messages

    def extract_patient_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts stable patient context parameters for persistence or logging.
        """
        return {
            "patient_name": state.get("patient_name"),
            "patient_phone": state.get("patient_phone"),
            "is_otp_verified": state.get("is_otp_verified")
        }


# ─── Redis Session Store ──────────────────────────────────────────────────────
# Stores AgentState in Redis so all Gunicorn workers share the same session data.
# Each worker creates a fresh AshaSwarm but loads state from Redis.

class RedisSessionStore:
    """
    Redis-backed session state storage for multi-worker Gunicorn compatibility.
    Stores the full AgentState dict as JSON with configurable TTL.
    """
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Lazy-initialize Redis connection."""
        if self._redis is None:
            import redis.asyncio as aioredis
            from config.settings import settings
            self._redis = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2
            )
        return self._redis
    
    def _key(self, session_id: str) -> str:
        """Redis key format for session state."""
        return f"asha:session:{session_id}"
    
    async def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session state from Redis.
        Returns the state dict if found, None if session doesn't exist or expired.
        """
        try:
            r = await self._get_redis()
            raw = await r.get(self._key(session_id))
            if raw:
                logger.info(f"Redis session HIT for {session_id}")
                return json.loads(raw)
            logger.info(f"Redis session MISS for {session_id} (new session)")
            return None
        except Exception as e:
            logger.warning(f"Redis session load failed, creating fresh session: {e}")
            return None
    
    async def save(self, session_id: str, state: Dict[str, Any], ttl_hours: int = 2):
        """
        Save session state to Redis with TTL.
        Serializes the AgentState dict to JSON and stores it.
        """
        try:
            r = await self._get_redis()
            # Convert state to JSON-serializable format
            serializable = {}
            for k, v in state.items():
                if v is None:
                    serializable[k] = None
                elif isinstance(v, (str, int, float, bool)):
                    serializable[k] = v
                elif isinstance(v, list):
                    serializable[k] = v
                elif isinstance(v, dict):
                    serializable[k] = v
                else:
                    serializable[k] = str(v)
            
            await r.set(
                self._key(session_id),
                json.dumps(serializable, default=str),
                ex=ttl_hours * 3600  # TTL in seconds
            )
            logger.info(f"Redis session SAVED for {session_id} (TTL: {ttl_hours}h)")
        except Exception as e:
            logger.error(f"Redis session save failed: {e}")
    
    async def delete(self, session_id: str):
        """Delete a session from Redis."""
        try:
            r = await self._get_redis()
            await r.delete(self._key(session_id))
            logger.info(f"Redis session DELETED for {session_id}")
        except Exception as e:
            logger.error(f"Redis session delete failed: {e}")


# Singleton instance shared across all workers
_session_store = RedisSessionStore()

def get_session_store() -> RedisSessionStore:
    """Get the shared Redis session store singleton."""
    return _session_store
