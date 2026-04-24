from src.llm.providers.groq_client import GroqProvider
from config.prompt import ASHA_SYSTEM_PROMPT
from src.utils.logger import custom_logger as logger

class LLMBrain:
    """
    The Orchestrator: Connects Asha's personality (Prompts) with the AI engine (Groq).
    """
    def __init__(self):
        self.provider = GroqProvider()
        self.system_prompt = ASHA_SYSTEM_PROMPT

    def get_asha_response(self, user_text: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_text}
        ]
        logger.info(f"Processing request for: {user_text[:30]}...")
        return self.provider.generate_response(messages)

    def stream_asha_response(self, user_text: str):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_text}
        ]
        logger.info(f"Starting stream for: {user_text[:30]}...")
        return self.provider.stream_response(messages)
