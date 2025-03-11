"""
llm_engines.ollama_engine
========================
Ollama Engine Implementation
============================

We instruct the LLM to return a JSON list of categories with fields:
- category
- message
Possible categories: [General Feedback, Memory Management, Performance, Null Check, Security, Coding Standard, etc.].
"""

import logging
import os
import subprocess
from typing import Any

from .base import BaseLLMEngine

logger = logging.getLogger(__name__)

# Load debug mode from environment
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Automatically detect and set all available GPUs
try:
    gpu_count = int(subprocess.getoutput("nvidia-smi -L | wc -l").strip())  # Get GPU count
    if gpu_count > 1:
        gpu_ids = ",".join(str(i) for i in range(gpu_count))
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu_ids  # Set all GPUs for usage
        logger.info(f"Using all available GPUs: {gpu_ids}")
    else:
        logger.info("Single GPU detected, using default settings.")
except Exception as e:
    logger.warning(f"Could not auto-detect GPUs: {e}")


class OllamaEngine(BaseLLMEngine):
    """
    Class to perform LLM inference using Ollama with multi-GPU support.
    """

    def generate_review(self, prompt_str: str) -> Any:
        """
        Perform inference using the Ollama CLI with multi-GPU support.

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
            if DEBUG_MODE:
                logger.debug(f"[OllamaEngine] Using GPUs: {os.environ.get('CUDA_VISIBLE_DEVICES', 'default')}")
                logger.debug(f"[OllamaEngine] Sending Prompt:\n{prompt_str}")

            # Construct the command to use all GPUs
            command_list = ["ollama", "run", "deepseek-r1:70b", prompt_str]

            # Ensure Ollama inherits the multi-GPU environment
            completed_process = subprocess.run(
                command_list,
                capture_output=True,
                text=True,
                check=False,
                env=os.environ,  # Pass modified environment variables (CUDA_VISIBLE_DEVICES)
            )

            if completed_process.returncode != 0:
                logger.error(f"Failed to run Ollama inference: {completed_process.stderr}")
                raise RuntimeError("Ollama inference failed.")

            output = completed_process.stdout.strip()

            if DEBUG_MODE:
                logger.debug(f"[OllamaEngine] Raw Output Length: {len(output)} characters")
                logger.debug(f"[OllamaEngine] Full Response:\n{output}")

            return output

        except Exception as e:
            logger.exception(f"Error while running Ollama: {e}")
            raise
