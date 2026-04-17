import logging
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from auto_bi.utils.config import MODEL_ID, OLLAMA_BASE_URL

logger = logging.getLogger(__name__)

class CompiledRule(BaseModel):
    """Result of Rule Interpretation."""
    formal_rule: str = Field(..., description="The rule translated into a precise instruction for the classification agent.")
    reasoning: str = Field(..., description="Explain why you formulated the rule this way.")

def interpret_user_rule(natural_language: str, model_id: str = MODEL_ID) -> str:
    """
    Translates a user's natural language request into a formal classification rule.
    """
    try:
        client = instructor.from_openai(
            OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"),
            mode=instructor.Mode.JSON,
        )
        
        prompt = (
            "You are a meta-prompt engineer for a financial AI assistant.\n"
            "The user will provide a specific spending rule in natural language.\n"
            "Your task is to translate it into a concise, formal bullet point for a classification agent.\n\n"
            "EXAMPLES:\n"
            "- 'Wellhub should be Sport' -> '* Transactions mentioning WELLHUB must be categorized as Subscriptions/Sport membership.'\n"
            "- 'Payments to Da Mimmo are restaurants' -> '* Transactions with merchant 'Da Mimmo' are for Dining category.'\n\n"
            f"USER REQUEST: '{natural_language}'"
        )
        
        result = client.chat.completions.create(
            model=model_id,
            response_model=CompiledRule,
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
        
        logger.info(f"Rule interpreted: {result.formal_rule}")
        return result.formal_rule
    except Exception as e:
        logger.error(f"Rule interpretation failed: {e}")
        return f"* {natural_language} (Fallback: classification rule)"
