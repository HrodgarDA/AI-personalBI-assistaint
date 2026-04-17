import json
import os
import random
import logging
import instructor
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from auto_bi.utils.config import BRONZE_RAW, OLLAMA_BASE_URL, MODEL_ID
from auto_bi.utils.bank_profile import load_bank_profile

logger = logging.getLogger(__name__)

class NoisePattern(BaseModel):
    regex: str = Field(..., description="The regex pattern to remove this noise.")
    explanation: str = Field(..., description="Plain-English explanation of what this pattern removes.")
    example_match: str = Field(..., description="Example string from the provided data that matches this pattern.")

class NoiseAnalysis(BaseModel):
    patterns: List[NoisePattern] = Field(..., description="List of identified noise patterns.")

def get_raw_sample(limit: int = 50) -> List[str]:
    """Retrieves a sample of raw transaction descriptions."""
    if not os.path.exists(BRONZE_RAW):
        return []
    
    samples = []
    try:
        with open(BRONZE_RAW, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Pick a random sample if many lines
            if len(lines) > limit:
                lines = random.sample(lines, limit)
            
            for line in lines:
                try:
                    record = json.loads(line)
                    # Use both operation and details to get full context
                    text = f"{record.get('operation', '')} {record.get('details', '')}".strip()
                    if text and len(text) > 10:
                        samples.append(text)
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Error sampling raw data: {e}")
    
    return list(set(samples)) # Deduplicate

def suggest_cleaning_patterns(model_id: str = MODEL_ID) -> List[NoisePattern]:
    """Analyzes raw data and suggests cleaning patterns via LLM."""
    samples = get_raw_sample()
    if not samples:
        return []

    client = instructor.from_openai(
        OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"),
        mode=instructor.Mode.JSON,
    )
    
    profile = load_bank_profile()
    existing_patterns = "\n".join(profile.cleaning_patterns)

    # Building the prompt
    samples_text = "\n".join([f"- {s}" for s in samples[:30]])
    
    system_msg = (
        "You are an expert Data Engineer. Your task is to identify repetitive 'noise' patterns "
        "in bank transaction descriptions that hide the actual merchant name.\n\n"
        "EXAMPLES OF NOISE:\n"
        "- Technical transaction codes (e.g., 'COD. DISP. 12345678')\n"
        "- Date/Time markers (e.g., 'ALLE ORE 14:30', 'DEL 12/03/24')\n"
        "- Generic prefixes (e.g., 'PAGAMENTO CARTA NIW', 'ACQUISTO TV')\n"
        "- Card numbers (e.g., 'CARTA N. 1234')\n\n"
        "Your goal is to suggest Python Regex patterns to STRIP this noise.\n"
        "STRICT RULE: Do NOT suggest patterns that might remove actual merchant names like 'Amazon' or 'Netflix'."
    )
    
    user_msg = (
        f"Here are 30 sample transactions from the bank:\n{samples_text}\n\n"
        f"Existing patterns (DO NOT REPEAT THESE):\n{existing_patterns}\n\n"
        "Suggest up to 5 NEW regex patterns to clean these descriptions. "
        "Return a JSON object with a list of patterns, each including the regex, an explanation, and an example match."
    )

    try:
        analysis = client.chat.completions.create(
            model=model_id,
            response_model=NoiseAnalysis,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            timeout=120
        )
        return analysis.patterns
    except Exception as e:
        logger.error(f"Error suggesting patterns: {e}")
        return []
