from src.llm.providers.groq_client import GroqProvider
from src.llm.providers.gemini_client import GeminiProvider
from src.llm.providers.openai_client import OpenAIProvider
from src.llm.providers.openrouter_client import OpenRouterProvider

class LLMFactory:
    @staticmethod
    def get_provider(provider_type: str = "groq"):
        if provider_type == "groq":
            return GroqProvider()
        elif provider_type == "gemini":
            return GeminiProvider()
        elif provider_type == "openai":
            return OpenAIProvider()
        elif provider_type == "openrouter":
            return OpenRouterProvider()
        else:
            raise ValueError(f"Provider {provider_type} not supported.")
