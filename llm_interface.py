import abc
from typing import List, Union, AsyncGenerator, Dict, Any, Optional
from dataclasses import dataclass
from open_sourced.llm import LLMModel

@dataclass
class LLMContext:
    image: Optional[bytes] = None
    text: Optional[str] = None

class LLMProcessorInterface(abc.ABC):
    """
    Abstract Base Class defining the interface for interacting with Large Language Models.
    Extensions can use this interface to process text or multimodal context
    without depending on the specific LLM provider implementation.
    """

    @abc.abstractmethod
    async def process(
        self,
        system_prompt: Optional[str],
        message: str,
        contexts: List[LLMContext],
        model: LLMModel,
        stream: bool = False,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        # Add other common parameters if needed
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Processes the given message and context using the specified LLM.

        Args:
            system_prompt: The system prompt or instructions for the LLM.
            message: The main user message or query.
            contexts: A list of LLMContext objects providing text or image context.
            model: The specific LLM model to use.
            stream: Whether to return the response as a stream (async generator).
            max_output_tokens: Maximum number of tokens to generate.
            temperature: Controls randomness (sampling temperature).
            top_p: Nucleus sampling parameter.
            top_k: Top-k sampling parameter.

        Returns:
            If stream is False, returns the complete response string.
            If stream is True, returns an async generator yielding response chunks.
        """
        pass

    # Potentially add other methods if extensions need more specific LLM interactions,
    # e.g., get_embeddings, specific tool usage, etc. 