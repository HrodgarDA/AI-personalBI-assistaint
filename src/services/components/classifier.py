import logging
import instructor
import subprocess
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel
from src.utils.models import create_dynamic_classification_model, create_batch_model
from src.utils.prompts import (
    OUTGOING_CLASSIFICATION_PROMPT, INCOMING_CLASSIFICATION_PROMPT, 
    BATCH_CLASSIFICATION_TEMPLATE
)
from src.utils.config import LLM_TIMEOUT

logger = logging.getLogger(__name__)

class Classifier:
    """Handles LLM-based categorization of transactions."""
    
    def __init__(self, base_url: str, model_id: str, profile: Any):
        self.model_id = model_id
        self.profile = profile
        self.client = instructor.from_openai(
            OpenAI(base_url=base_url, api_key="ollama"),
            mode=instructor.Mode.JSON,
        )
        
        # Dynamic models based on profile
        self.outgoing_model = create_dynamic_classification_model(
            self.profile.outgoing_categories, "Outgoing"
        )
        self.incoming_model = create_dynamic_classification_model(
            self.profile.incoming_categories, "Incoming"
        )
        self.outgoing_batch_model = create_batch_model(self.outgoing_model)
        self.incoming_batch_model = create_batch_model(self.incoming_model)
        self._ensure_model_available()

    def _ensure_model_available(self):
        """Ensures the Ollama model is available; creates it from Modelfile if missing."""
        possible_paths = ["ollama", "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/bin/ollama"]
        ollama_bin = "ollama"
        for path in possible_paths:
            try:
                subprocess.run([path, "list"], capture_output=True, text=True, timeout=2)
                ollama_bin = path
                break
            except (subprocess.SubprocessError, FileNotFoundError):
                continue

        try:
            result = subprocess.run([ollama_bin, "list"], capture_output=True, text=True, timeout=5)
            if self.model_id not in result.stdout:
                if os.path.exists("Modelfile"):
                    logger.info(f"Model '{self.model_id}' not found. Creating from Modelfile...")
                    subprocess.run([ollama_bin, "create", self.model_id, "-f", "Modelfile"], check=True)
                else:
                    logger.warning(f"Modelfile not found. Cannot create '{self.model_id}'.")
        except Exception as e:
            logger.debug(f"Ollama check skipped or failed: {e}")

    def get_system_prompt(self, direction: str, feedback_context: str = "") -> str:
        """Builds the system prompt for classification."""
        if direction == "Outgoing":
            system_prompt = OUTGOING_CLASSIFICATION_PROMPT
            cats = self.profile.outgoing_categories
        else:
            system_prompt = INCOMING_CLASSIFICATION_PROMPT
            cats = self.profile.incoming_categories

        cats_block = "\n".join([f"- {c}" for c in cats])
        system_prompt = system_prompt.replace("{categories_block}", cats_block)
        system_prompt = system_prompt.replace("{user_feedback_examples}", feedback_context)
        
        rules_mem = getattr(self.profile, "rules_memory", [])
        custom_rules_formatted = f"\nUSER CUSTOM RULES AND MEMORY:\n{chr(10).join(rules_mem)}" if rules_mem else ""
        system_prompt = system_prompt.replace("{custom_user_rules}", custom_rules_formatted)
        
        return system_prompt

    def execute_batch(self, system_prompt: str, user_prompt: str, direction: str, use_fast: bool = False) -> Any:
        """Executes a batch classification call with separated system and user prompts."""
        model_name = self.profile.fast_model_id if use_fast else self.model_id
        batch_model = self.outgoing_batch_model if direction == "Outgoing" else self.incoming_batch_model
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            return self.client.chat.completions.create(
                model=model_name,
                temperature=0.0,
                response_model=batch_model,
                messages=messages,
                timeout=LLM_TIMEOUT * 2
            )
        except Exception as e:
            if use_fast and model_name != self.model_id:
                logger.warning(f"Fast model {model_name} failed. Retrying with {self.model_id}...")
                return self.client.chat.completions.create(
                    model=self.model_id,
                    temperature=0.0,
                    response_model=batch_model,
                    messages=messages,
                    timeout=LLM_TIMEOUT * 2
                )
            raise e
