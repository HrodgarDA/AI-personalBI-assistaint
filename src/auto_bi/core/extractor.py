import os
import json
import logging
from typing import Any, Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pydantic import BaseModel

from auto_bi.utils.config import (
    MODEL_ID, OLLAMA_BASE_URL, SEARCH_TIMEOUT, SEARCH_BACKENDS, 
    MERCHANT_CATALOGUE, EXTRACTION_CACHE, BRONZE_RAW, 
    BANK_CATEGORY_MAP
)
from auto_bi.utils.utils import is_valid_search_query, normalize_merchant_name
from auto_bi.utils.bank_profile import load_bank_profile
from auto_bi.utils.prompts import (
    BATCH_CLASSIFICATION_TEMPLATE, BANK_HINT_MAPPING_TEMPLATE
)

# New Component Imports
from auto_bi.core.components.cache import CacheManager
from auto_bi.core.components.search import SearchEngine
from auto_bi.core.components.classifier import Classifier

load_dotenv()
logger = logging.getLogger(__name__)

class MerchantExtraction(BaseModel):
    merchant: str

class TransactionParser:
    """Orchestrates transaction parsing using cache, search, and LLM classifiers."""
    
    def __init__(self):
        self.profile = load_bank_profile()
        self.model = self.profile.classification_model
        
        # Initialize internal components
        self.cache = CacheManager(
            merchant_path=MERCHANT_CATALOGUE,
            extraction_path=EXTRACTION_CACHE,
            bank_map_path=BANK_CATEGORY_MAP
        )
        self.search = SearchEngine(
            backends=SEARCH_BACKENDS,
            timeout=SEARCH_TIMEOUT
        )
        self.classifier = Classifier(
            base_url=OLLAMA_BASE_URL,
            model_id=self.model,
            profile=self.profile
        )
        
        # Legacy attributes for backward compatibility (if any external code hits them)
        self.merchant_cache = self.cache.merchant_cache
        self.extraction_cache = self.cache.extraction_cache
        self.bank_map_cache = self.cache.bank_map_cache
        
        self._raw_data_cache: Optional[Dict[str, str]] = None

    def save_caches(self, force: bool = False):
        """Saves all caches via CacheManager."""
        self.cache.save_all()

    def _get_raw_data_map(self) -> Dict[str, str]:
        """Loads and caches the raw data map (ID -> details) for faster feedback context building."""
        if self._raw_data_cache is not None:
            return self._raw_data_cache
        
        self._raw_data_cache = {}
        if not os.path.exists(BRONZE_RAW):
            return self._raw_data_cache
            
        try:
            with open(BRONZE_RAW, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        mid = str(record.get("id"))
                        details = record.get("details", record.get("operation", ""))
                        self._raw_data_cache[mid] = details
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Error indexing raw data: {e}")
            
        return self._raw_data_cache

    def _build_feedback_context(self, limit: int = 20) -> str:
        feedback_path = "data/user_feedback.json"
        if not os.path.exists(feedback_path):
            return ""
            
        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
            
            if not feedbacks:
                return ""
            
            feedbacks = feedbacks[-limit:] if limit > 0 else []
            data_map = self._get_raw_data_map()
            
            examples = []
            for fb in feedbacks:
                mid = str(fb["msg_id"])
                if mid in data_map:
                    detail = data_map[mid].strip()
                    if len(detail) > 250:
                        detail = detail[:250] + "..."
                    ex = f"- Transaction text: '{detail}'\n  -> Correct Category: {fb.get('corrected_category')} (Correct Merchant: {fb.get('corrected_merchant')})"
                    examples.append(ex)
                    
            if examples:
                return "\nHere are some examples of past corrections to guide you (RAG Memory):\n" + "\n".join(examples)
        except Exception as e:
            logger.warning(f"Error building feedback context: {e}")
            
        return ""

    def _prepare_tx(self, tx: Dict) -> Dict:
        """Internal helper: Resolve cached/catalogued data before LLM."""
        text = tx['text']
        cache_key = text.lower().strip()
        
        # 1. Resolve merchant if missing
        merchant = tx.get('merchant')
        if not merchant:
            merchant = self.cache.extraction_cache.get(cache_key) or self.cache.fuzzy_extract_lookup(text)
            if merchant:
                logger.info(f"💾 [CACHE] Resolved merchant '{merchant}' from extraction memory.")
        
        tx['merchant'] = merchant or "Unknown"
        tx['historical_category'] = None
        tx['category_source'] = "llm_inference"
        
        if tx['merchant'] != "Unknown":
            logger.info(f"🔍 [EXTRACT] Identifying category for merchant: '{tx['merchant']}'")
            
        # 2. Lookup in catalogue (Standard)
        if tx['merchant'] != "Unknown":
            tx['historical_category'] = self.cache.semantic_lookup(tx['merchant'], direction=tx['direction'])
            if tx['historical_category']:
                tx['category_source'] = "from_catalogue"
                return tx
        
        # 3. Deep Research Fallback (Raw Text Scan)
        # If the extracted merchant failed, we scan the RAW text for ANY known catalogue entry
        logger.info(f"🔎 [CATALOG] No direct match for '{tx['merchant']}'. Starting deep raw scan...")
        deep_res = self.cache.semantic_lookup_raw(text, direction=tx['direction'])
        if deep_res:
            cat, m_name = deep_res
            tx['historical_category'] = cat
            tx['merchant'] = m_name
            tx['category_source'] = "from_catalogue_deep"
            
        return tx

    def classify_batch(self, transactions: List[Dict], system_template: str = None) -> List[Dict]:
        """Main batch processing entry point for high performance with parallel execution."""
        # 1. Pre-resolve against caches
        prepared = [self._prepare_tx(tx.copy()) for tx in transactions]
        results = [None] * len(transactions)
        
        # 2. Parallel Web Search for unknown merchants
        to_search = [tx for tx in prepared if not tx['historical_category'] and tx['merchant'] != "Unknown" and not tx.get('hint')]
        if to_search:
            merchants = list(set(tx['merchant'] for tx in to_search))
            logger.info(f"   🔎 [WEB] Searching info for {len(merchants)} merchants in parallel...")
            
            with ThreadPoolExecutor(max_workers=min(len(merchants), 5)) as executor:
                results_list = list(executor.map(self.search.search_merchant_info, merchants))
                m_hints = dict(zip(merchants, results_list))
            
            for tx in to_search:
                tx['hint'] = m_hints.get(tx['merchant'])
                if tx.get('hint'): tx['category_source'] = "web_search"
            logger.info(f"   ✅ [WEB] Search hints retrieved.")

        # 3. Separate Bypass vs LLM
        to_llm_indices = [] # Indices in 'prepared' that need LLM
        for i, tx in enumerate(prepared):
            if tx['historical_category'] and tx.get('amount') is not None:
                results[i] = {
                    "category": tx['historical_category'],
                    "merchant": tx['merchant'],
                    "amount": tx['amount'],
                    "confidence": 1.0,
                    "reasoning": "Determined from merchant catalogue (Bypass).",
                    "category_source": tx.get('category_source', 'from_catalogue')
                }
            else:
                to_llm_indices.append(i)

        if not to_llm_indices: return results

        # 4. Execute LLM Calls in Parallel (Incoming vs Outgoing)
        def _process_direction(direction: str):
            dir_tx_indices = [idx for idx in to_llm_indices if prepared[idx]['direction'] == direction]
            if not dir_tx_indices: return []
            
            tx_data = [prepared[idx] for idx in dir_tx_indices]
            feedback = self._build_feedback_context(limit=5)
            system_prompt = self.classifier.get_system_prompt(direction, feedback)
            
            tx_strings = []
            for tx in tx_data:
                s = f"Text: {tx['text']}"
                if tx.get('amount') is not None:
                    s += f" | Amount: {abs(tx['amount']):.2f}"
                if tx.get('bank_category'):
                    s += f" | Bank Suggestion: {tx['bank_category']}"
                if tx['merchant'] != "Unknown": 
                    s += f" | Merchant Hint: {tx['merchant']}"
                if tx.get('hint'): 
                    s += f" | Web Context: {tx['hint']}"
                tx_strings.append(s)
            
            user_prompt = BATCH_CLASSIFICATION_TEMPLATE.format(
                categories_block="[SEE SYSTEM MESSAGE]",
                user_feedback_examples="[SEE SYSTEM MESSAGE]",
                custom_user_rules="[SEE SYSTEM MESSAGE]",
                transactions_block="\n".join([f"{idx+1}. {txt}" for idx, txt in enumerate(tx_strings)])
            )
            
            use_fast = any(tx.get('hint') for tx in tx_data)
            try:
                logger.info(f"   🤖 [IA]  Processing block ({direction})...")
                batch_res = self.classifier.execute_batch(system_prompt, user_prompt, direction, use_fast=use_fast)
                
                res_list = []
                for idx_in_batch, res in enumerate(batch_res.results):
                    tx = tx_data[idx_in_batch]
                    # Cache updates
                    self.cache.extraction_cache[tx['text'].lower().strip()] = res.merchant
                    if res.merchant and res.merchant.lower() != "unknown" and is_valid_search_query(res.merchant):
                        m_key = res.merchant.strip().lower()
                        if tx['category_source'] != "from_catalogue":
                            # Store in directional format
                            if m_key not in self.cache.merchant_cache or not isinstance(self.cache.merchant_cache[m_key], dict):
                                self.cache.merchant_cache[m_key] = {}
                            self.cache.merchant_cache[m_key][tx['direction']] = res.category.value
                    
                    res_list.append({
                        "original_index": dir_tx_indices[idx_in_batch],
                        "result": {
                            "category": res.category.value,
                            "merchant": res.merchant,
                            "amount": getattr(res, 'amount', tx.get('amount')),
                            "confidence": float(res.confidence if res.confidence is not None else 0.0),
                            "reasoning": res.reasoning,
                            "category_source": tx['category_source']
                        }
                    })
                return res_list
            except Exception as e:
                logger.error(f"   ❌ [IA] Batch processing error ({direction}): {e}")
                return []

        # Concurrent execution of directions
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(_process_direction, d) for d in ["Outgoing", "Incoming"]]
            for future in futures:
                for item in future.result():
                    results[item["original_index"]] = item["result"]

        # Final Fallback
        for i in range(len(results)):
            if results[i] is None:
                prepared_tx = prepared[i]
                results[i] = {
                    "category": "Uncategorized", 
                    "merchant": "Error", 
                    "amount": prepared_tx.get('amount', 0.0), 
                    "confidence": 0, 
                    "category_source": "error",
                    "reasoning": "Extraction failed due to system error."
                }
        return results

        # Final Fallback
        for i in range(len(results)):
            if results[i] is None:
                prepared_tx = prepared[i]
                results[i] = {
                    "category": "Uncategorized", 
                    "merchant": "Error", 
                    "amount": prepared_tx.get('amount', 0.0), 
                    "confidence": 0, 
                    "category_source": "error",
                    "reasoning": "Extraction failed due to system error."
                }
        return results

    def classify_transaction(self, text: str, direction: str, merchant: str = None, amount: float = None, system_template: str = None) -> dict:
        """Proxy for backward compatibility."""
        res = self.classify_batch([{"text": text, "direction": direction, "merchant": merchant, "amount": amount}], system_template=system_template)
        return res[0]

    def map_bank_category(self, bank_hint: str, direction: str) -> Optional[Dict[str, Any]]:
        """Maps bank hints using specialized LLM logic."""
        if not bank_hint: return None
        
        cache_key = f"{direction}:{bank_hint}"
        if cache_key in self.cache.bank_map_cache:
            return {
                "category": self.cache.bank_map_cache[cache_key]["category"],
                "merchant": "Bank Hint Mapping",
                "confidence": -1.0,
                "reasoning": self.cache.bank_map_cache[cache_key]["reasoning"],
                "category_source": "bank_hint_mapping"
            }
            
        try:
            cats = self.profile.outgoing_categories if direction == "Outgoing" else self.profile.incoming_categories
            cats_block = "\n".join([f"- {c}" for c in cats])
            prompt = BANK_HINT_MAPPING_TEMPLATE.format(
                categories_block=cats_block,
                direction=direction,
                bank_hint=bank_hint
            )
            
            # Simple direct reuse of classifier client for mapping
            res = self.classifier.client.chat.completions.create(
                model=self.model,
                response_model=self.classifier.outgoing_model if direction == "Outgoing" else self.classifier.incoming_model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            self.cache.bank_map_cache[cache_key] = {
                "category": res.category.value,
                "reasoning": f"(Bank: {bank_hint}) -> {res.reasoning}"
            }
            self.cache.save_all()
            
            return {
                "category": res.category.value,
                "merchant": "Bank Hint Mapping",
                "confidence": -1.0,
                "reasoning": self.cache.bank_map_cache[cache_key]["reasoning"],
                "category_source": "bank_hint_mapping"
            }
        except Exception as e:
            logger.warning(f"Error mapping bank category '{bank_hint}': {e}")
            return None