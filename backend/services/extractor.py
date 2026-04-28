import hashlib
import logging
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import pdfplumber

from backend.database.session import async_session
from backend.database.models import Transaction, Category, Merchant
from sqlalchemy import select
from backend.services.components.classifier import classifier
from backend.services.components.search import search_merchant_info
from backend.services.components.matcher import matcher
from backend.services.components.embedder import embedder
from backend.core.config import settings

logger = logging.getLogger(__name__)

class TransactionExtractor:
    """Service for extracting and classifying bank transactions from PDFs."""

    async def extract(self, file_path: str) -> List[List[str]]:
        """
        Extracts raw text from PDF using pdfplumber for better reliability.
        """
        try:
            raw_rows = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    for line in lines:
                        # Simple heuristic: transactions usually contain dates and amounts
                        if len(line) > 10 and any(char.isdigit() for char in line):
                            raw_rows.append([line])
            
            logger.info(f"Extracted {len(raw_rows)} potential transaction lines from PDF.")
            return raw_rows
        except Exception as e:
            logger.error(f"Failed to extract PDF with pdfplumber: {e}")
            return []

    async def classify_batch(self, raw_rows: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Processes transactions in optimized batches using a multi-tier classification strategy.
        """
        async with async_session() as session:
            # Pre-fetch metadata to avoid N+1 queries
            stmt_cat = select(Category.id)
            res_cat = await session.execute(stmt_cat)
            categories = [r[0] for r in res_cat.all()]
            
            stmt_merch = select(Merchant).where(Merchant.embedding != None)
            res_merch = await session.execute(stmt_merch)
            merchants_with_vectors = res_merch.scalars().all()
            
            stmt_merch_all = select(Merchant)
            res_merch_all = await session.execute(stmt_merch_all)
            known_merchants = {m.name.lower(): m for m in res_merch_all.scalars().all()}

            # Refresh regex rules in the global matcher once per batch
            await matcher.refresh_rules()

        classified_txs = []
        to_ai_queue = []
        to_ai_indices = []

        async with async_session() as session:
            for idx, row in enumerate(raw_rows):
                raw_text = " | ".join(row)
                amount = self._extract_amount(raw_text)
                
                # Deduplication using MD5 hash of (text + amount)
                raw_str = f"{raw_text}_{amount}"
                tx_id = hashlib.md5(raw_str.encode()).hexdigest()
                
                if await session.get(Transaction, tx_id):
                    logger.info(f"Skipping duplicate transaction: {tx_id}")
                    continue

                # TIER 1: REGEX MATCH (Instant, using cached rules)
                regex_res = await matcher.match(raw_text)
                if regex_res:
                    m_name, c_id, t_type = regex_res
                    classified_txs.append(self._build_tx_dict(tx_id, idx, amount, t_type, c_id, m_name, raw_text, "Matched regex pattern.", 1.0))
                    continue

                # TIER 2: DATABASE LOOKUP
                found_merch = None
                # a) Exact name match in known merchants
                for m_name, m_obj in known_merchants.items():
                    if m_name in raw_text.lower():
                        found_merch = m_obj
                        break
                
                if found_merch:
                    classified_txs.append(self._build_tx_dict(tx_id, idx, amount, "Outgoing", found_merch.default_outgoing_category_id or "General", found_merch.name, raw_text, "Matched known merchant in database.", 1.0))
                    continue

                # b) Semantic Search Fallback
                if merchants_with_vectors:
                    tx_vector = await embedder.embed(raw_text)
                    if tx_vector:
                        # Find closest merchant using L2 distance (Vector similarity)
                        stmt = select(Merchant).order_by(Merchant.embedding.l2_distance(tx_vector)).limit(1)
                        res = await session.execute(stmt)
                        best_match = res.scalar_one_or_none()
                        
                        # Use a stricter threshold for automatic semantic matching
                        if best_match:
                            classified_txs.append(self._build_tx_dict(tx_id, idx, amount, "Outgoing", best_match.default_outgoing_category_id or "General", best_match.name, raw_text, f"Semantic match with {best_match.name}.", 0.8))
                            continue

                # TIER 3: AI CLASSIFICATION (Enqueued for batch processing)
                to_ai_queue.append({"id": tx_id, "text": raw_text, "amount": amount})
                to_ai_indices.append(idx)

        # Process AI Batch
        if to_ai_queue:
            ai_results = await self._process_ai_batch(to_ai_queue, categories)
            for orig_idx, (tx_info, ai_res) in zip(to_ai_indices, zip(to_ai_queue, ai_results)):
                classified_txs.append(self._build_tx_dict(
                    tx_info["id"], orig_idx, tx_info["amount"],
                    ai_res.transaction_type, ai_res.category, ai_res.merchant,
                    tx_info["text"], ai_res.reasoning, ai_res.confidence
                ))

        # Restore original order and clean up temporary sorting index
        classified_txs.sort(key=lambda x: x["idx"])
        for tx in classified_txs:
            del tx["idx"]
        
        return classified_txs

    async def _process_ai_batch(self, queue: List[Dict], categories: List[str]):
        """Helper to process AI calls in chunks with parallelized web searches."""
        results = []
        CHUNK_SIZE = settings.LLM_BATCH_SIZE
        
        for i in range(0, len(queue), CHUNK_SIZE):
            chunk = queue[i : i + CHUNK_SIZE]
            chunk_texts = [tx["text"] for tx in chunk]
            
            # Parallelize web searches for the chunk
            search_tasks = [search_merchant_info(tx["text"][:40]) for tx in chunk]
            chunk_contexts = await asyncio.gather(*search_tasks)
            
            # AI Classification call
            chunk_res = await classifier.classify_batch(chunk_texts, categories, chunk_contexts)
            results.extend(chunk_res)
            
        return results

    def _build_tx_dict(self, tx_id, idx, amount, tx_type, cat_id, merch_id, raw_text, reasoning, confidence):
        """Helper to build a standardized transaction dictionary."""
        return {
            "id": tx_id,
            "idx": idx,
            "date": datetime.now().date(),
            "amount": amount,
            "transaction_type": tx_type,
            "category_id": cat_id,
            "merchant_id": merch_id,
            "original_operation": raw_text,
            "ai_reasoning": reasoning,
            "confidence": confidence
        }

    def _extract_amount(self, text: str) -> float:
        """Robust amount extraction from transaction strings."""
        matches = re.findall(r"-?\d+(?:[.,]\d+)+", text)
        if matches:
            val = matches[-1].replace(".", "").replace(",", ".")
            try:
                return float(val)
            except ValueError:
                return 0.0
        return 0.0

    async def save_to_db(self, transactions: List[Dict[str, Any]]):
        """Saves classified transactions to the database, ensuring categories and merchants exist."""
        async with async_session() as session:
            for tx_data in transactions:
                # Ensure category exists
                cat_id = tx_data["category_id"]
                if not await session.get(Category, cat_id):
                    session.add(Category(id=cat_id, name=cat_id))
                
                # Ensure merchant exists
                merch_id = tx_data["merchant_id"]
                if not await session.get(Merchant, merch_id):
                    session.add(Merchant(id=merch_id, name=merch_id))
                
                # Add transaction
                session.add(Transaction(**tx_data))
            
            await session.commit()
            logger.info(f"Successfully saved {len(transactions)} transactions to database.")
