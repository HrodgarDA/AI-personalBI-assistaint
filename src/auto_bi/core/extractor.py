import os
import json
import re
import logging
import instructor
import subprocess
import time
from openai import OpenAI
from dotenv import load_dotenv
from typing import Any, Optional
from pydantic import BaseModel
from auto_bi.utils.models import OutgoingClassification, IncomingClassification
from auto_bi.utils.prompts import OUTGOING_CLASSIFICATION_PROMPT, INCOMING_CLASSIFICATION_PROMPT, MERCHANT_EXTRACTION_PROMPT
from auto_bi.utils.config import (
    MODEL_ID, OLLAMA_BASE_URL, SEARCH_TIMEOUT, SEARCH_BACKENDS, 
    MERCHANT_CATALOGUE, BRONZE_FILE, LLM_TIMEOUT, MAX_RETRIES
)
from auto_bi.utils.utils import clean_search_query, is_valid_search_query, normalize_merchant_name
from auto_bi.utils.bank_profile import load_bank_profile

load_dotenv()
logger = logging.getLogger(__name__)

# Patterns that indicate the merchant name is NOT a real searchable merchant
UNIVERSAL_INVALID_PATTERNS = [
    r'^\d{10,}',                       # Long numeric codes
    r'^N\.?D\.?$',                     # "N.D" (not available)
    r'^\d{2}/\d{2}/\d{4}',            # Dates 
]



class MerchantExtraction(BaseModel):
    merchant: str


class TransactionParser:
    def __init__(self):
        self.model = MODEL_ID
        self._ensure_model_available()
        self.profile = load_bank_profile()
        self.client = instructor.from_openai(
            OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"),
            mode=instructor.Mode.JSON,
        )
        self.cache_path = MERCHANT_CATALOGUE
        self.merchant_cache = self._load_cache()
        # Build optimized lookup map for normalized names
        self.normalized_cache = {normalize_merchant_name(k): v for k, v in self.merchant_cache.items() if normalize_merchant_name(k)}

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.merchant_cache, f, indent=2, ensure_ascii=False)
            # Rebuild normalized cache
            self.normalized_cache = {normalize_merchant_name(k): v for k, v in self.merchant_cache.items() if normalize_merchant_name(k)}
        except Exception as e:
            logger.warning(f"Error saving merchant cache: {e}")

    def _ensure_model_available(self):
        """Verifica se il modello Ollama esiste localmente, altrimenti lo crea dal Modelfile."""
        # Common paths for ollama CLI on macOS/Linux
        ollama_bin = "ollama"
        possible_paths = ["ollama", "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/bin/ollama"]
        
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
                modelfile_path = "Modelfile"
                if os.path.exists(modelfile_path):
                    logger.info(f"Modello '{self.model}' non trovato. Creazione in corso dal Modelfile utilizzando '{ollama_bin}'...")
                    subprocess.run([ollama_bin, "create", self.model, "-f", modelfile_path], check=True)
                else:
                    logger.warning(f"Attenzione: Modelfile non trovato. Impossibile creare '{self.model}'.")
        except (subprocess.SubprocessError, FileNotFoundError):
             logger.debug("Ollama CLI not found or unreachable. Skipping pre-check.")
        except Exception as e:
            logger.warning(f"Errore durante il controllo del modello Ollama: {e}")


    def _build_feedback_context(self) -> str:
        feedback_path = "data/user_feedback.json"
        bronze_path = BRONZE_FILE

        
        if not os.path.exists(feedback_path) or not os.path.exists(bronze_path):
            return ""
            
        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
            
            if not feedbacks:
                return ""
            
            feedbacks = feedbacks[-5:]
            
            msg_ids_to_find = {str(fb["msg_id"]) for fb in feedbacks}
            details_map = {}
            with open(bronze_path, "r", encoding="utf-8") as bf:
                for line in bf:
                    try:
                        record = json.loads(line)
                        mid = str(record.get("id"))
                        if mid in msg_ids_to_find:
                            details_map[mid] = record.get("details", record.get("body", ""))
                    except Exception:
                        pass
                        
            examples = []
            for fb in feedbacks:
                mid = str(fb["msg_id"])
                if mid in details_map:
                    detail = details_map[mid].strip()
                    if len(detail) > 250:
                        detail = detail[:250] + "..."
                    ex = f"- Transaction text: '{detail}'\n  -> Correct Category: {fb.get('corrected_category')} (Correct Amount: {fb.get('corrected_amount')})"
                    examples.append(ex)
                    
            if examples:
                return "\nHere are some examples of past categorizations. Use them as a reference:\n" + "\n".join(examples)
                
        except Exception as e:
            logger.warning(f"Error loading feedback: {e}")
            
        return ""

    def _clean_search_query(self, merchant_name: str) -> str:
        """DEPRECATED: Use src.utils.clean_search_query instead."""
        return clean_search_query(merchant_name)

    def _is_valid_search_query(self, query: str) -> bool:
        """DEPRECATED: Use src.utils.is_valid_search_query instead."""
        return is_valid_search_query(query)


    def _search_merchant_info(self, merchant_name: str) -> str:
        """
        Search for merchant info using web search. 
        Returns a web snippet (hint) but DOES NOT save it to the permanent catalogue.
        """
        if not merchant_name or merchant_name.lower() in ["unknown", "altro", "", "n.d"]:
            return ""
        
        # Clean up the query
        clean_query = self._clean_search_query(merchant_name)
        
        if not self._is_valid_search_query(clean_query):
            return ""
        
        # Search using only fast, reliable backends
        try:
            from ddgs import DDGS
            for backend in SEARCH_BACKENDS:
                try:
                    with DDGS(timeout=SEARCH_TIMEOUT) as ddgs:
                        results = list(ddgs.text(
                            f"What is {clean_query} store service category",
                            backend=backend,
                            max_results=1
                        ))
                        if results:
                            snippet = results[0].get('body', '')
                            logger.debug(f"   🔍 Web search OK ({backend}): '{clean_query}' -> hint retrieved")
                            return snippet[:200]
                except Exception as e:
                    logger.debug(f"   Web search failed on {backend}: {e}")
                    continue
        except ImportError:
            logger.warning("ddgs library not installed, skipping web search")
        
        return ""

    def classify_transaction(self, text: str, direction: str, merchant: str = None, amount: float = None) -> dict:
        """
        Unified transaction classification with catalogue-first logic and source tracking.
        """
        category_source = "llm_inference"
        historical_category = None

        # 1. Merchant extraction (only if not provided)
        if not merchant:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    merchant_res = self.client.chat.completions.create(
                        model=self.model,
                        temperature=0.0,
                        response_model=MerchantExtraction,
                        messages=[
                            {"role": "system", "content": MERCHANT_EXTRACTION_PROMPT},
                            {"role": "user", "content": text},
                        ],
                        timeout=LLM_TIMEOUT
                    )
                    merchant = merchant_res.merchant
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        logger.warning(f"   ⚠️ Merchant extraction failed (Attempt {attempt+1}/{MAX_RETRIES+1}). Retrying in 2s...")
                        time.sleep(2)
                    else:
                        logger.error(f"   ❌ Merchant extraction failed after {MAX_RETRIES+1} attempts: {e}")
                        merchant = "Unknown"

        if merchant and merchant.lower() != "unknown":
            m_key = merchant.strip().lower()
            m_normalized = normalize_merchant_name(m_key)
            
            # Fast Exact Match
            if m_key in self.merchant_cache:
                historical_category = self.merchant_cache[m_key]
                category_source = "from_catalogue"
                logger.debug(f"   📂 Catalogue MATCH: '{merchant}' -> '{historical_category}'")
            # Fast Normalized Match (O(1) instead of O(M))
            elif m_normalized in self.normalized_cache:
                historical_category = self.normalized_cache[m_normalized]
                category_source = "from_catalogue"
                logger.debug(f"   📂 Catalogue SMART MATCH: '{merchant}' -> '{historical_category}'")

        # 2c. LLM BYPASS: If we already have the category and the amount, skip the AI
        if historical_category and amount is not None:
             logger.debug(f"   ⚡ BYPASS AI: Using cached category '{historical_category}' for '{merchant}'")
             return {
                "category": historical_category,
                "merchant": merchant,
                "amount": amount,
                "confidence": 1.0,
                "reasoning": "Determined from merchant catalogue (LLM bypass).",
                "category_source": "from_catalogue"
            }

        # 3. Web search hint (only if NOT in catalogue)
        merchant_hint = ""
        if not historical_category and merchant and merchant.lower() != "unknown":
            merchant_hint = self._search_merchant_info(merchant)
            if merchant_hint:
                category_source = "web_search"

        # 4. Direction-specific classification
        if direction == "Outgoing":
            model_class = OutgoingClassification
            system_prompt = OUTGOING_CLASSIFICATION_PROMPT
        else:
            model_class = IncomingClassification
            system_prompt = INCOMING_CLASSIFICATION_PROMPT

        feedback = self._build_feedback_context()
        system_prompt = system_prompt.replace("{user_feedback_examples}", feedback)
        
        # Inject custom user prompt from profile
        custom_rules = f"\nUSER CUSTOM RULES:\n{self.profile.custom_prompt}" if self.profile.custom_prompt else ""
        system_prompt = system_prompt.replace("{custom_user_rules}", custom_rules)
        
        if historical_category:
            system_prompt += f"\nVERIFIED HISTORICAL CATEGORY for '{merchant}': {historical_category}. Favor this category unless the text strongly indicates otherwise."
        elif merchant_hint:
            system_prompt += f"\nWeb hint for merchant '{merchant}': {merchant_hint}"

        # Call LLM with retries and timeout
        result = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                result = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    response_model=model_class,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    timeout=LLM_TIMEOUT
                )
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    logger.warning(f"   ⚠️ LLM classification failed (Attempt {attempt+1}/{MAX_RETRIES+1}). Retrying in 2s...")
                    time.sleep(2)
                else:
                    logger.error(f"   ❌ LLM classification FAILED after {MAX_RETRIES+1} attempts: {e}")
                    raise e # Re-raise to be caught by the process caller

        classified_category = result.category.value

        # 5. Update catalogue with the final result (Skip likely person names)
        if merchant and merchant.lower() != "unknown" and is_valid_search_query(merchant):
            m_key = merchant.strip().lower()
            m_normalized = normalize_merchant_name(m_key)
            
            # Check if we already have a normalized match to avoid redundant entries
            already_has_normalized = False
            if category_source == "from_catalogue":
                already_has_normalized = True
            else:
                if m_normalized:
                    for cat_key in self.merchant_cache:
                        if normalize_merchant_name(cat_key) == m_normalized:
                            already_has_normalized = True
                            break
            
            if not already_has_normalized:
                self.merchant_cache[m_key] = classified_category
                self._save_cache()


        return {
            "category": classified_category,
            "merchant": merchant,
            "amount": getattr(result, 'amount', None),
            "confidence": result.confidence,
            "reasoning": getattr(result, 'reasoning', None),
            "category_source": category_source
        }