import logging
import uuid
from backend.database.session import async_session
from backend.database.models import RegexRule, Transaction
from backend.services.components.classifier import classifier
from backend.services.components.prompts import REGEX_SUGGESTION_PROMPT
from sqlalchemy import select

logger = logging.getLogger(__name__)

class LearningService:
    async def learn_from_edit(self, tx_id: str, new_merchant: str, new_category: str):
        """
        Triggered when a user edits a transaction.
        Suggests and saves a regex rule to automate this in the future.
        """
        async with async_session() as session:
            tx = await session.get(Transaction, tx_id)
            if not tx:
                return

            # Check if we already have a rule for this pattern/merchant
            # (Simplified check: if merchant name already has a rule, maybe skip)
            
            prompt = REGEX_SUGGESTION_PROMPT.format(
                raw_text=tx.original_operation,
                merchant_name=new_merchant
            )
            
            try:
                # Ask Gemma for a regex
                response = classifier.client.chat.completions.create(
                    model=classifier.model,
                    messages=[
                        {"role": "system", "content": "You are a regex expert."},
                        {"role": "user", "content": prompt}
                    ]
                )
                suggested_regex = response.choices[0].message.content.strip().replace('"', '')
                
                # Save the new rule
                new_rule = RegexRule(
                    id=str(uuid.uuid4())[:8],
                    pattern=suggested_regex,
                    merchant_name=new_merchant,
                    category_id=new_category,
                    transaction_type=tx.transaction_type
                )
                session.add(new_rule)
                await session.commit()
                logger.info(f"Learned new rule: {suggested_regex} -> {new_merchant}")
                return suggested_regex
            except Exception as e:
                logger.error(f"Failed to learn from edit: {e}")
                return None

learning_service = LearningService()
