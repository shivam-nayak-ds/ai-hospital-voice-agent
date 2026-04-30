from openai import OpenAI
from config.settings import settings
from src.llm.providers.base import BaseLLMProvider
from src.utils.logger import custom_logger as logger 
from typing import List, Dict, Generator

class GeminiProvider(BaseLLMProvider):
    """
    Gemini 1.5 Pro Provider Implementation using OpenAI Compatibility API.
    """

    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in .env")
        
        self.client = OpenAI(
            api_key=settings.GOOGLE_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model_name = settings.GEMINI_MODEL
        logger.info(f"GeminiProvider initialized with model: {self.model_name}")
    
    def generate(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        return self.generate_response(messages)

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
            logger.error(f"Gemini generate_response error: {str(e)}")
            return "Error: I am unable to think right now. Please check Gemini API."

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
            logger.error(f"Gemini stream_response error: {str(e)}")
            yield " [Error: Connection Lost] "
