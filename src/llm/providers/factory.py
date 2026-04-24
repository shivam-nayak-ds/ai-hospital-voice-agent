from src.llm.providers.groq_client import GroqProvider

class LLMFactory:
    @staticmethod
    def get_provider(provider_type: str = "groq"):
        if provider_type == "groq":
            return GroqProvider()
        else:
            raise ValueError(f"Provider {provider_type} not supported.")
