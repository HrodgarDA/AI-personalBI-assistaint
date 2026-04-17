import os
import json
import re
import logging
import instructor
import subprocess
import time
from openai import OpenAI
from dotenv import load_dotenv
from typing import Any, Optional, Dict, List
import concurrent.futures
from pydantic import BaseModel
from auto_bi.utils.models import create_dynamic_classification_model, create_batch_model
from auto_bi.utils.prompts import (
    OUTGOING_CLASSIFICATION_PROMPT, INCOMING_CLASSIFICATION_PROMPT, 
    MERCHANT_EXTRACTION_PROMPT, BATCH_CLASSIFICATION_TEMPLATE
)
from auto_bi.utils.config import (
    MODEL_ID, OLLAMA_BASE_URL, SEARCH_TIMEOUT, SEARCH_BACKENDS, 
    MERCHANT_CATALOGUE, EXTRACTION_CACHE, BRONZE_RAW, LLM_TIMEOUT, MAX_RETRIES,
    LLM_BATCH_SIZE
)
from auto_bi.utils.utils import clean_search_query, is_valid_search_query, normalize_merchant_name
from auto_bi.utils.bank_profile import load_bank_profile

load_dotenv()
logger = logging.getLogger(__name__)

class MerchantExtraction(BaseModel):
    merchant: str

class TransactionParser:
    def __init__(self):
        self.profile = load_bank_profile()
        self.model = self.profile.classification_model
        self._ensure_model_available()
        self.client = instructor.from_openai(
            OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"),
            mode=instructor.Mode.JSON,
        )
        self.cache_path = MERCHANT_CATALOGUE
        self.merchant_cache = self._load_cache(self.cache_path)
        # Build optimized lookup map for normalized names
        self.normalized_cache = {normalize_merchant_name(k): v for k, v in self.merchant_cache.items() if normalize_merchant_name(k)}
        self._raw_data_cache: Optional[Dict[str, str]] = None
        
        # New: Extraction Cache (maps raw_text -> merchant_name)
        self.extraction_cache_path = EXTRACTION_CACHE
        self.extraction_cache = self._load_cache(self.extraction_cache_path)
        
        # --- Dynamic Models Initialization ---
        # Models are built based on the custom categories defined in the bank profile
        self.outgoing_model = create_dynamic_classification_model(
            self.profile.outgoing_categories, "Outgoing"
        )
        self.incoming_model = create_dynamic_classification_model(
            self.profile.incoming_categories, "Incoming"
        )
        self.outgoing_batch_model = create_batch_model(self.outgoing_model)
        self.incoming_batch_model = create_batch_model(self.incoming_model)

    def _load_cache(self, path: str) -> dict:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_caches(self, force: bool = False):
        """Saves both merchant and extraction caches to disk."""
        if not force:
            # We could add a 'dirty' flag here, but for now we'll just save when requested
            pass
            
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            # Save Merchant Catalogue atomically
            temp_catalogue = self.cache_path + ".tmp"
            with open(temp_catalogue, "w", encoding="utf-8") as f:
                json.dump(self.merchant_cache, f, indent=2, ensure_ascii=False)
            os.replace(temp_catalogue, self.cache_path)
            
            # Save Extraction Cache atomically
            temp_extraction = self.extraction_cache_path + ".tmp"
            with open(temp_extraction, "w", encoding="utf-8") as f:
                json.dump(self.extraction_cache, f, indent=2, ensure_ascii=False)
            os.replace(temp_extraction, self.extraction_cache_path)
                
            self.normalized_cache = {normalize_merchant_name(k): v for k, v in self.merchant_cache.items() if normalize_merchant_name(k)}
            logger.info("💾 Caches saved successfully.")
        except Exception as e:
            logger.warning(f"Error saving caches: {e}")

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
            if self.model not in result.stdout:
                if os.path.exists("Modelfile"):
                    logger.info(f"Model '{self.model}' not found. Creating from Modelfile...")
                    subprocess.run([ollama_bin, "create", self.model, "-f", "Modelfile"], check=True)
                else:
                    logger.warning(f"Modelfile not found. Cannot create '{self.model}'.")
        except Exception as e:
            logger.debug(f"Ollama check skipped or failed: {e}")

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
                        # Prefer details, fallback to operation
                        details = record.get("details", record.get("operation", ""))
                        self._raw_data_cache[mid] = details
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Error indexing raw data: {e}")
            
        return self._raw_data_cache

    def _build_feedback_context(self) -> str:
        feedback_path = "data/user_feedback.json"
        if not os.path.exists(feedback_path):
            return ""
            
        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
            
            if not feedbacks:
                return ""
            
            feedbacks = feedbacks[-5:]
            data_map = self._get_raw_data_map()
            
            examples = []
            for fb in feedbacks:
                mid = str(fb["msg_id"])
                if mid in data_map:
                    detail = data_map[mid].strip()
                    if len(detail) > 250:
                        detail = detail[:250] + "..."
                    ex = f"- Transaction text: '{detail}'\n  -> Correct Category: {fb.get('corrected_category')} (Correct Amount: {fb.get('corrected_amount')})"
                    examples.append(ex)
                    
            if examples:
                return "\nHere are some examples of past corrections to guide you:\n" + "\n".join(examples)
        except Exception as e:
            logger.warning(f"Error building feedback context: {e}")
            
        return ""

    def _execute_single_search(self, backend: str, query: str) -> Optional[str]:
        """Wrap DDGS call for individual backend execution."""
        from ddgs import DDGS
        try:
            with DDGS(timeout=SEARCH_TIMEOUT) as ddgs:
                results = list(ddgs.text(f"What is {query} store service category", backend=backend, max_results=1))
                if results:
                    return results[0].get('body', '')
        except Exception:
            pass
        return None

    def _search_merchant_info(self, merchant_name: str) -> str:
        """Search for merchant info using web search backends in parallel."""
        if not merchant_name or merchant_name.lower() in ["unknown", "altro", "", "n.d"]:
            return ""
        
        query = clean_search_query(merchant_name)
        if not is_valid_search_query(query):
            return ""
        
        try:
            # Parallelize searches across all configured backends
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(SEARCH_BACKENDS)) as executor:
                # Dispatch all searches
                future_to_backend = {
                    executor.submit(self._execute_single_search, backend, query): backend 
                    for backend in SEARCH_BACKENDS
                }
                
                # First success wins - process as they complete
                for future in concurrent.futures.as_completed(future_to_backend):
                    try:
                        res = future.result()
                        if res:
                            logger.debug(f"🔍 Parallel web search OK (Backend: {future_to_backend[future]}): '{query}'")
                            return res[:200]
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Error during parallel web search: {e}")
            
        return ""

    def _fuzzy_extract_lookup(self, text: str) -> Optional[str]:
        """Attempt to find a similar transaction in the extraction cache by ignoring IDs/dates."""
        norm_text = re.sub(r'[\d\-\/]+', '', text.lower()).strip()
        if not norm_text: return None
        
        for key, merchant in self.extraction_cache.items():
            norm_key = re.sub(r'[\d\-\/]+', '', key.lower()).strip()
            if norm_text == norm_key:
                return merchant
        return None

    def classify_transaction(self, text: str, direction: str, merchant: str = None, amount: float = None) -> dict:
        """Unified classification with catalogue-first logic and single-pass LLM fallback."""
        category_source = "llm_inference"
        historical_category = None
        cache_key = text.lower().strip()

        # 1. Merchant Resolution (Catalogue or Cache)
        if not merchant:
            # Check exact extraction cache
            if cache_key in self.extraction_cache:
                merchant = self.extraction_cache[cache_key]
                logger.info(f"⚡ Extraction Cache hit: '{merchant}'")
            else:
                # Try fuzzy lookup
                merchant = self._fuzzy_extract_lookup(text)
                if merchant:
                    logger.info(f"⚡ Fuzzy Cache hit: '{merchant}'")
                    self.extraction_cache[cache_key] = merchant # Seal the exact match for next time

        if merchant and merchant.lower() != "unknown":
            m_key = merchant.strip().lower()
            m_normalized = normalize_merchant_name(m_key)
            
            if m_key in self.merchant_cache:
                historical_category = self.merchant_cache[m_key]
                category_source = "from_catalogue"
            elif m_normalized in self.normalized_cache:
                historical_category = self.normalized_cache[m_normalized]
                category_source = "from_catalogue"

        # 2. LLM BYPASS (If we have merchant + known category)
        if historical_category and amount is not None:
             return {
                "category": historical_category,
                "merchant": merchant,
                "amount": amount,
                "confidence": 1.0,
                "reasoning": "Determined from merchant catalogue (LLM bypass).",
                "category_source": "from_catalogue"
            }

        # 3. Web search hint (Optional but fast if parallel)
        merchant_hint = ""
        # Only search if we have a merchant name but no historical category
        if merchant and merchant.lower() != "unknown" and not historical_category:
            merchant_hint = self._search_merchant_info(merchant)
            if merchant_hint:
                category_source = "web_search"

        # 4. SINGLE-PASS AI Classification
        if direction == "Outgoing":
            model_class = self.outgoing_model
            system_prompt = OUTGOING_CLASSIFICATION_PROMPT
            cats = self.profile.outgoing_categories
        else:
            model_class = self.incoming_model
            system_prompt = INCOMING_CLASSIFICATION_PROMPT
            cats = self.profile.incoming_categories

        # Inject categories block
        cats_block = "\n".join([f"- {c}" for c in cats])
        system_prompt = system_prompt.replace("{categories_block}", cats_block)

        # Inject context (Feedback, Rules, Hints)
        feedback = self._build_feedback_context()
        system_prompt = system_prompt.replace("{user_feedback_examples}", feedback)
        
        rules_mem = getattr(self.profile, "rules_memory", [])
        custom_rules_formatted = f"\nUSER CUSTOM RULES AND MEMORY:\n{chr(10).join(rules_mem)}" if rules_mem else ""
        system_prompt = system_prompt.replace("{custom_user_rules}", custom_rules_formatted)
        
    def _prepare_tx(self, tx: Dict) -> Dict:
        """Internal helper: Resolve cached/catalogued data before LLM."""
        text = tx['text']
        direction = tx['direction']
        merchant = tx.get('merchant')
        cache_key = text.lower().strip()
        
        # 1. Resolve merchant if missing
        if not merchant:
            merchant = self.extraction_cache.get(cache_key) or self._fuzzy_extract_lookup(text)
        
        tx['merchant'] = merchant or "Unknown"
        tx['historical_category'] = None
        tx['category_source'] = "llm_inference"
        
        # 2. Lookup in catalogue
        if tx['merchant'] != "Unknown":
            m_key = tx['merchant'].strip().lower()
            m_normalized = normalize_merchant_name(m_key)
            if m_key in self.merchant_cache:
                tx['historical_category'] = self.merchant_cache[m_key]
                tx['category_source'] = "from_catalogue"
            elif m_normalized in self.normalized_cache:
                tx['historical_category'] = self.normalized_cache[m_normalized]
                tx['category_source'] = "from_catalogue"
        return tx

    def classify_batch(self, transactions: List[Dict], system_template: str = None) -> List[Dict]:
        """Main batch processing entry point for high performance."""
        # 1. Pre-resolve
        prepared = [self._prepare_tx(tx.copy()) for tx in transactions]
        results = [None] * len(transactions)
        
        # 2. Parallel Web Search for unknown merchants in batch
        to_search = [tx for tx in prepared if not tx['historical_category'] and tx['merchant'] != "Unknown"]
        if to_search:
            merchants = list(set(tx['merchant'] for tx in to_search))
            logger.info(f"   🔎 [WEB] Searching info for {len(merchants)} merchants in parallel...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(merchants)) as executor:
                m_to_hint = {m: executor.submit(self._search_merchant_info, m) for m in merchants}
                m_hints = {m: f.result() for m, f in m_to_hint.items()}
                for tx in to_search:
                    tx['hint'] = m_hints.get(tx['merchant'])
                    if tx.get('hint'): tx['category_source'] = "web_search"
            logger.info(f"   ✅ [WEB] Search hints retrieved.")

        # 3. Separate Bypass vs LLM
        to_llm = [] # List of (original_index, tx)
        for i, tx in enumerate(prepared):
            # Bypass if we have a direct hit
            if tx['historical_category'] and tx.get('amount') is not None:
                results[i] = {
                    "category": tx['historical_category'],
                    "merchant": tx['merchant'],
                    "amount": tx['amount'],
                    "confidence": 1.0,
                    "reasoning": "Determined from merchant catalogue (Bypass).",
                    "category_source": "from_catalogue"
                }
            else:
                to_llm.append((i, tx))

        if not to_llm: return results

        # 4. Process Batch by Direction
        groups = {
            "Outgoing": {
                "items": [(i, tx) for i, tx in to_llm if tx['direction'] == "Outgoing"],
                "model": self.outgoing_batch_model,
                "cats": self.profile.outgoing_categories
            },
            "Incoming": {
                "items": [(i, tx) for i, tx in to_llm if tx['direction'] == "Incoming"],
                "model": self.incoming_batch_model,
                "cats": self.profile.incoming_categories
            }
        }

        for direction, config in groups.items():
            tx_group = config['items']
            if not tx_group: continue
            
            indices = [x[0] for x in tx_group]
            tx_data = [x[1] for x in tx_group]
            
            # Prepare Prompt
            cats_block = "\n".join([f"- {c}" for c in config['cats']])
            # Add merchant hints to strings
            tx_strings = []
            for tx in tx_data:
                s = f"Text: {tx['text']}"
                if tx['merchant'] != "Unknown": s += f" | Merchant Hint: {tx['merchant']}"
                if tx.get('hint'): s += f" | Web Context: {tx['hint']}"
                tx_strings.append(s)
            
            tx_block = "\n".join([f"{idx+1}. {txt}" for idx, txt in enumerate(tx_strings)])
            
            rules_mem = getattr(self.profile, "rules_memory", [])
            custom_rules = f"\nRULES:\n{chr(10).join(rules_mem)}" if rules_mem else ""
            
            template_to_use = system_template if system_template else BATCH_CLASSIFICATION_TEMPLATE
            prompt = template_to_use.format(
                categories_block=cats_block,
                custom_user_rules=custom_rules,
                transactions_block=tx_block
            )

            # LLM Call
            try:
                logger.info(f"   🤖 [IA]  Processing block of {len(tx_group)} {direction} transactions... (thinking)")
                batch_res = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    response_model=config['model'],
                    messages=[{"role": "system", "content": prompt}],
                    timeout=LLM_TIMEOUT * 2 # Double timeout for batches
                )
                
                # Assign results
                for idx_in_batch, res in enumerate(batch_res.results):
                    if idx_in_batch < len(indices):
                        orig_idx = indices[idx_in_batch]
                        tx = tx_data[idx_in_batch]
                        
                        # Cache update
                        self.extraction_cache[tx['text'].lower().strip()] = res.merchant
                        if res.merchant and res.merchant.lower() != "unknown" and is_valid_search_query(res.merchant):
                            m_key = res.merchant.strip().lower()
                            if tx['category_source'] != "from_catalogue":
                                self.merchant_cache[m_key] = res.category.value
                        
                        results[orig_idx] = {
                            "category": res.category.value,
                            "merchant": res.merchant,
                            "amount": getattr(res, 'amount', tx.get('amount')),
                            "confidence": res.confidence,
                            "reasoning": res.reasoning,
                            "category_source": tx['category_source']
                        }
            except Exception as e:
                logger.error(f"Error in batch IA processing: {e}")
                # Fallback: flag remaining as failed or mark them one by one (could be skipped for now)

        # Fill any missing results from errors
        for i in range(len(results)):
            if results[i] is None:
                prepared_tx = prepared[i]
                raw_info = f"{prepared_tx.get('original_operation', '')} | {prepared_tx.get('original_details', '')}"
                results[i] = {
                    "category": "Uncategorized", 
                    "merchant": "Error", 
                    "amount": prepared_tx.get('amount', 0.0), 
                    "confidence": 0, 
                    "category_source": "error",
                    "reasoning": f"Extraction failed. Raw data: {raw_info}"
                }

        return results

    def classify_transaction(self, text: str, direction: str, merchant: str = None, amount: float = None) -> dict:
        """Proxy to classify_batch for backward compatibility."""
        res = self.classify_batch([{"text": text, "direction": direction, "merchant": merchant, "amount": amount}])
        return res[0]