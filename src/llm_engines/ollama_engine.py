"""
Ollama Engine Implementation
============================

We instruct the LLM to return a JSON list of categories with fields:
- category
- message
Possible categories: [Memory Management, Performance, Null Check, Security, Coding Standard].
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
        Perform inference using the Ollama CLI.

        Parameters
        ----------
        prompt_str : str
            A string instructing the LLM to produce JSON with multiple categories.

        Returns
        -------
        str
            The raw inference result from Ollama (JSON or fallback text).

        Raises
        ------
        RuntimeError
            If Ollama inference fails.
        """
        try:
            command_list = ["ollama", "run", "deepseek-r1:70b", prompt_str]
            completed_process = subprocess.run(command_list, capture_output=True, text=True, check=False)

            if completed_process.returncode != 0:
                logger.error(f"Failed to run Ollama inference: {completed_process.stderr}")
                raise RuntimeError("Ollama inference failed.")

            return completed_process.stdout.strip()

        except Exception:
            logger.exception("Error while running Ollama engine.")
            raise
