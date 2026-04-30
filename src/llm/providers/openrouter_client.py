from openai import OpenAI
import os
from config.settings import settings
from src.llm.providers.base import BaseLLMProvider
from src.utils.logger import custom_logger as logger 
from typing import List, Dict, Generator

class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter Provider Implementation (Compatible with all OpenRouter models).
    """

    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GPT_5.5_PRO")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY or GPT_5.5_PRO is not set in .env")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        # Set to the model you chose on OpenRouter
        self.model_name = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o") 
        logger.info(f"OpenRouterProvider initialized with model: {self.model_name}")
    
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
            logger.error(f"OpenRouter generate_response error: {str(e)}")
            return "Error: I am unable to think right now. Please check OpenRouter API."

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
            logger.error(f"OpenRouter stream_response error: {str(e)}")
            yield " [Error: Connection Lost] "
