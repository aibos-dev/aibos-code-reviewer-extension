"""
Base Class for LLM Engines
==========================

Defines an abstract base class for LLM engines, allowing easy swapping of implementations.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMEngine(ABC):
    """
    Abstract base class for LLM engines.

    All LLM engines should inherit this interface and implement
    'generate_review' method.
    """

    @abstractmethod
    def generate_review(self, prompt_str: str) -> Any:
        """
        Accepts a text prompt for the LLM and returns the inference result.

        Parameters
        ----------
        prompt_str : str
            The text prompt given to the LLM.

        Returns
        -------
        Any
            The raw inference (usually text) from the LLM.
        """
