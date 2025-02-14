"""
Ollama Engine Implementation
============================

Example using the DeepSeek R1 70B quantized model with Ollama.
Actual inference may be via subprocess calls or HTTP requests.
"""

import logging
import subprocess
from typing import Any

from .base import BaseLLMEngine

logger = logging.getLogger(__name__)


class OllamaEngine(BaseLLMEngine):
    """
    Class to perform LLM inference using Ollama.
    """

    def generate_review(self, prompt_str: str) -> Any:
        """
        Perform inference using the Ollama CLI or API.

        Parameters
        ----------
        prompt_str : str
            Prompt text for the LLM.

        Returns
        -------
        Any
            The inference result from Ollama.

        Raises
        ------
        RuntimeError
            If Ollama inference fails.
        """
        try:
            # Example: synchronous CLI call
            # In production, you might prefer an HTTP API approach.
            command_list = ["ollama", "run", "--model", "deapseek-r1-70b-q4", prompt_str]
            completed_process = subprocess.run(command_list, capture_output=True, text=True, check=False)

            if completed_process.returncode != 0:
                logger.error(f"Failed to run Ollama inference: {completed_process.stderr}")
                raise RuntimeError("Ollama inference failed.")

            result_str = completed_process.stdout.strip()
            return result_str
        except Exception:
            logger.exception("Error while running Ollama engine.")
            raise
