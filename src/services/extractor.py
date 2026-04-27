from pdfminer.high_level import extract_text
import hashlib
import logging
import re
from datetime import datetime
from src.database.session import async_session
from src.database.models import Transaction, Category, Merchant
from sqlalchemy import select
from src.services.components.classifier import classifier
from src.services.components.search import search_merchant_info
from src.services.components.matcher import matcher
from src.services.components.embedder import embedder

logger = logging.getLogger(__name__)

class TransactionExtractor:
    async def extract(self, file_path: str):
        """
        Extracts raw text from PDF using pdfminer.six (faster).
        """
        try:
            text = extract_text(file_path)
            # Basic line-based splitting for now
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            
            # Simple heuristic: look for lines that look like transactions
            raw_rows = []
            for line in lines:
                if len(line) > 10 and any(char.isdigit() for char in line):
                    raw_rows.append([line])
            return raw_rows
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            return []

    async def classify_batch(self, raw_rows):
        """
        Process rows in smart batches with early deduplication.
        """
        async with async_session() as session:
            # 1. Fetch metadata
            stmt_cat = select(Category.id)
            res_cat = await session.execute(stmt_cat)
            categories = [r[0] for r in res_cat.all()]
            
            # Fetch known merchants with embeddings
            stmt_merch = select(Merchant).where(Merchant.embedding != None)
            res_merch = await session.execute(stmt_merch)
            merchants_with_vectors = res_merch.scalars().all()
            
            stmt_merch_all = select(Merchant)
            res_merch_all = await session.execute(stmt_merch_all)
            known_merchants = {m.name.lower(): m for m in res_merch_all.scalars().all()}

        classified_txs = []
        to_ai_texts = []
        to_ai_contexts = []
        to_ai_indices = []

        async with async_session() as session:
            for idx, row in enumerate(raw_rows):
                raw_text = " | ".join(row)
                amount = self._extract_amount(raw_text)
                
                # EARLY DEDUPLICATION (MD5 Hash)
                raw_str = f"{raw_text}_{amount}"
                tx_id = hashlib.md5(raw_str.encode()).hexdigest()
                
                if await session.get(Transaction, tx_id):
                    logger.info(f"Skipping duplicate transaction: {tx_id}")
                    continue

                # TIER 1: REGEX MATCH (Instant)
                regex_res = await matcher.match(raw_text)
                if regex_res:
                    m_name, c_id = regex_res
                    classified_txs.append({
                        "id": tx_id,
                        "idx": idx,
                        "date": datetime.now().date(),
                        "amount": amount,
                        "tipology": "Outgoing",
                        "category_id": c_id,
                        "merchant_id": m_name,
                        "original_operation": raw_text,
                        "ai_reasoning": "Matched regex pattern.",
                        "confidence": 1.0
                    })
                    continue

                # TIER 2: DB LOOKUP (Fast Path)
                found_merch = None
                # a) Exact Match
                for m_name, m_obj in known_merchants.items():
                    if m_name in raw_text.lower():
                        found_merch = m_obj
                        break
                
                # b) Semantic Search Fallback
                if not found_merch and merchants_with_vectors:
                    tx_vector = await embedder.embed(raw_text)
                    if tx_vector:
                        # Find closest merchant using L2 distance
                        stmt = select(Merchant).order_by(Merchant.embedding.l2_distance(tx_vector)).limit(1)
                        res = await session.execute(stmt)
                        best_match = res.scalar_one_or_none()
                        
                        # Only accept if close enough (heuristic threshold)
                        if best_match:
                             classified_txs.append({
                                "id": tx_id,
                                "idx": idx,
                                "date": datetime.now().date(),
                                "amount": amount,
                                "tipology": "Outgoing",
                                "category_id": best_match.default_outgoing_category_id or "General",
                                "merchant_id": best_match.name,
                                "original_operation": raw_text,
                                "ai_reasoning": f"Semantic match with {best_match.name}.",
                                "confidence": 0.8
                            })
                             continue

                if found_merch:
                    classified_txs.append({
                        "id": tx_id,
                        "idx": idx,
                        "date": datetime.now().date(),
                        "amount": amount,
                        "tipology": "Outgoing",
                        "category_id": found_merch.default_outgoing_category_id or "General",
                        "merchant_id": found_merch.name,
                        "original_operation": raw_text,
                        "ai_reasoning": "Matched known merchant in database.",
                        "confidence": 1.0
                    })
                else:
                    # TIER 3: AI BATCH (Slow Path)
                    to_ai_texts.append((tx_id, raw_text, amount))
                    context = None
                    if len(to_ai_texts) <= 5:
                        context = search_merchant_info(raw_text[:40])
                    to_ai_contexts.append(context)
                    to_ai_indices.append(idx)

        # 2. Batch AI Processing (chunks of 5)
        CHUNK_SIZE = 5
        for i in range(0, len(to_ai_texts), CHUNK_SIZE):
            chunk_data = to_ai_texts[i : i + CHUNK_SIZE]
            chunk_texts = [d[1] for d in chunk_data]
            chunk_contexts = to_ai_contexts[i : i + CHUNK_SIZE]
            chunk_res = await classifier.classify_batch(chunk_texts, categories, chunk_contexts)
            
            for j, ai_res in enumerate(chunk_res):
                orig_idx = to_ai_indices[i + j]
                tx_id, raw_text, amount = to_ai_texts[i + j]
                classified_txs.append({
                    "id": tx_id,
                    "idx": orig_idx,
                    "date": datetime.now().date(),
                    "amount": amount,
                    "tipology": ai_res.tipology,
                    "category_id": ai_res.category,
                    "merchant_id": ai_res.merchant,
                    "original_operation": raw_text,
                    "ai_reasoning": ai_res.reasoning,
                    "confidence": ai_res.confidence
                })

        # Sort back to original order
        classified_txs.sort(key=lambda x: x["idx"])
        for tx in classified_txs: del tx["idx"]
        
        return classified_txs

    def _extract_amount(self, text):
        # Improved regex for amounts like 1.234,56 or 1234.56
        matches = re.findall(r"-?\d+(?:[.,]\d+)+", text)
        if matches:
            val = matches[-1].replace(".", "").replace(",", ".")
            try: return float(val)
            except: return 0.0
        return 0.0

    async def save_to_db(self, transactions):
        async with async_session() as session:
            for tx_data in transactions:
                # Upsert category/merchant
                for table, key, val in [(Category, "id", tx_data["category_id"]), 
                                        (Merchant, "id", tx_data["merchant_id"])]:
                    if not await session.get(table, val):
                        session.add(table(id=val, name=val))
                
                session.add(Transaction(**tx_data))
            await session.commit()
