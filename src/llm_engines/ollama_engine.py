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
import requests
import time
from typing import Any

from .base import BaseLLMEngine

logger = logging.getLogger(__name__)

# Load debug mode from environment
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Default Ollama host
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:70b")

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

    def __init__(self):
        """Initialize the Ollama engine and check availability."""
        self.ollama_available = self.check_ollama_available()
        self.model_available = self.check_model_available() if self.ollama_available else False
        
        if self.ollama_available:
            logger.info(f"Connected to Ollama at {OLLAMA_HOST}")
            if self.model_available:
                logger.info(f"Model {OLLAMA_MODEL} is available")
            else:
                logger.warning(f"Model {OLLAMA_MODEL} is not available at Ollama endpoint")
        else:
            logger.warning(f"Ollama service not available at {OLLAMA_HOST}")

    def check_ollama_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{OLLAMA_HOST}", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Error connecting to Ollama: {e}")
            return False
            
    def check_model_available(self) -> bool:
        """Check if the required model is available in Ollama."""
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models:
                    if model.get("name") == OLLAMA_MODEL:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking model availability: {e}")
            return False

    def generate_review(self, prompt_str: str) -> Any:
        """
        Perform inference using the Ollama API.

        Parameters
        ----------
        prompt_str : str
            A string instructing the LLM to produce JSON with multiple categories.

        Returns
        -------
        str
            The raw inference result from Ollama API.

        Raises
        ------
        RuntimeError
            If Ollama API call fails.
        """
        try:
            if DEBUG_MODE:
                logger.debug(f"[OllamaEngine] Sending Prompt to API:\n{prompt_str}")

            import requests
            
            # Get model name from environment or use default
            model_name = os.getenv("OLLAMA_MODEL", "deepseek-r1:70b")
            host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
            
            logger.info(f"Sending request to Ollama API for model {model_name}")
            
            # Make API request
            response = requests.post(
                f"{host}/api/generate",
                json={"model": model_name, "prompt": prompt_str},
                timeout=600  # 10 minute timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Failed API call with status code {response.status_code}: {response.text}")
                raise RuntimeError(f"Ollama API call failed with status {response.status_code}")
            
            # Process streaming response
            output = ""
            for line in response.text.strip().split('\n'):
                try:
                    data = json.loads(line)
                    if "response" in data:
                        output += data["response"]
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse JSON line: {line}")
            
            if DEBUG_MODE:
                logger.debug(f"[OllamaEngine] Raw Output Length: {len(output)} characters")
                logger.debug(f"[OllamaEngine] Full Response:\n{output}")

            return output

        except Exception as e:
            logger.exception(f"Error while running Ollama: {e}")
            Raises