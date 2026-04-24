from groq import Groq
from config.settings import settings
from src.llm.providers.base import BaseLLMProvider
from src.utils.logger import custom_logger as logger 
from typing import List, Dict, Generator

class GroqProvider(BaseLLMProvider):
    """
    Groq LLM Provider Implementation.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = settings.GROQ_MODEL
        logger.info(f"GroqProvider initialized with model: {self.model_name}")

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            chat_completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", 0.2),
                top_p=kwargs.get("top_p", 0.9),
                stream=False
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq generate_response error: {str(e)}")
            return "Error: I am unable to think right now. Please check Groq API."

    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", 0.2),
                top_p=kwargs.get("top_p", 0.9),
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Groq stream_response error: {str(e)}")
            yield " [Error: Connection Lost] "
