from abc import ABC, abstractmethod
from typing import List, Dict, Any, Generator

class BaseLLMProvider(ABC):
    """
    Abstract Base Class defining the contract for all LLM providers (Groq, OpenAI, etc.)
    """

    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generates a complete response from the LLM for the given messages.
        """
        pass

    @abstractmethod
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """
        Streams the response from the LLM token by token.
        """
        pass
