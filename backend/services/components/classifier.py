import os
import logging
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional

from backend.services.components.prompts import BATCH_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)

from backend.core.config import settings

# Schema for AI Response
class TransactionClassification(BaseModel):
    category: str = Field(..., description="The most appropriate category for this transaction.")
    merchant: str = Field(..., description="The identified merchant name (cleaned).")
    transaction_type: str = Field(..., description="Incoming or Outgoing.")
    reasoning: str = Field(..., description="Short explanation of why this category/merchant was chosen.")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0.")

class AIClassifier:
    """Handles interaction with the LLM for transaction classification."""
    
    def __init__(self):
        # Configuration from unified settings
        self.api_key = "ollama"  # Default for local Ollama
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        
        self.client = instructor.patch(
            OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        )

    async def classify(
        self, 
        raw_text: str, 
        categories: List[str], 
        context: Optional[str] = None
    ) -> TransactionClassification:
        res = await self.classify_batch([raw_text], categories, [context] if context else [None])
        return res[0]

    async def classify_batch(
        self, 
        texts: List[str], 
        categories: List[str], 
        contexts: List[Optional[str]]
    ) -> List[TransactionClassification]:
        """
        Classifies multiple transactions in a single LLM call.
        """
        if not texts:
            return []

        formatted_txs = ""
        for i, (txt, ctx) in enumerate(zip(texts, contexts)):
            formatted_txs += f"TX {i}: {txt}\nContext {i}: {ctx or 'N/A'}\n\n"

        prompt = BATCH_CLASSIFICATION_PROMPT.format(
            categories_block=", ".join(categories),
            formatted_txs=formatted_txs
        )
        
        try:
            # Using instructor's support for List[BaseModel]
            response = self.client.chat.completions.create(
                model=self.model,
                response_model=List[TransactionClassification],
                messages=[
                    {"role": "system", "content": "You are an expert financial assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response
        except Exception as e:
            logger.error(f"Error during batch classification: {e}")
            return [
                TransactionClassification(
                    category="Uncategorized", merchant="Unknown", transaction_type="Outgoing",
                    reasoning=f"Error: {str(e)}", confidence=0.0
                ) for _ in texts
            ]

classifier = AIClassifier()
