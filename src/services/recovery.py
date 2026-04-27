import logging
import hashlib
from datetime import datetime
from src.database.session import async_session
from src.database.models import Transaction, Category, Merchant
from sqlalchemy import select, update
from src.services.components.classifier import classifier
from src.services.components.search import search_merchant_info

logger = logging.getLogger(__name__)

class RecoveryService:
    async def recover_uncategorized(self):
        """
        Identifies 'Uncategorized' transactions and re-processes them.
        Useful after updating rules or changing models.
        """
        async with async_session() as session:
            # 1. Fetch transactions needing review
            stmt = select(Transaction).where(Transaction.category_id == "Uncategorized")
            res = await session.execute(stmt)
            to_fix = res.scalars().all()
            
            if not to_fix:
                return 0, 0

            # 2. Fetch Categories
            stmt_cat = select(Category.id)
            res_cat = await session.execute(stmt_cat)
            categories = [r[0] for r in res_cat.all()]

            fixed_count = 0
            # Process in batches of 5 (Gemma friendly)
            CHUNK_SIZE = 5
            for i in range(0, len(to_fix), CHUNK_SIZE):
                chunk = to_fix[i : i + CHUNK_SIZE]
                texts = [f"{tx.original_operation} | {tx.original_details}" for tx in chunk]
                
                # Search context for unknowns (just first few)
                contexts = []
                for tx in chunk:
                    ctx = search_merchant_info(tx.original_operation[:40])
                    contexts.append(ctx)
                
                ai_results = await classifier.classify_batch(texts, categories, contexts)
                
                for j, ai_res in enumerate(ai_results):
                    if ai_res.category != "Uncategorized":
                        tx = chunk[j]
                        tx.category_id = ai_res.category
                        tx.merchant_id = ai_res.merchant
                        tx.tipology = ai_res.tipology
                        tx.ai_reasoning = f"Recovered: {ai_res.reasoning}"
                        tx.confidence = ai_res.confidence
                        fixed_count += 1
            
            await session.commit()
            return fixed_count, len(to_fix)

recovery_service = RecoveryService()
