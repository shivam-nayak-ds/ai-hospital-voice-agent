"""
memory.py
---------
Manages state persistence, conversation history pruning, and session-based context.
Prevents context window overflow while maintaining relevant context across multi-turn sessions.
"""

from typing import List, Dict, Any
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
