from openai import OpenAI
import os
from config.settings import settings
from src.llm.providers.base import BaseLLMProvider
from src.utils.logger import custom_logger as logger 
from typing import List, Dict, Generator

class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI Provider Implementation (For GPT models).
    """

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        
        self.client = OpenAI(api_key=self.api_key)
        # Using the model name they prefer, defaulting to gpt-4o if not set
        self.model_name = os.environ.get("OPENAI_MODEL", "gpt-4o") 
        logger.info(f"OpenAIProvider initialized with model: {self.model_name}")
    
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
            logger.error(f"OpenAI generate_response error: {str(e)}")
            return "Error: I am unable to think right now. Please check OpenAI API."

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
            logger.error(f"OpenAI stream_response error: {str(e)}")
            yield " [Error: Connection Lost] "
