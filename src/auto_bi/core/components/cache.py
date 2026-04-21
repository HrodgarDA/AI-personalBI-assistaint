import os
import json
import re
import logging
from typing import Dict, Optional
from auto_bi.utils.utils import normalize_merchant_name, levenshtein_ratio

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages transaction-related caches (merchants, extractions, bank hints)."""
    
    def __init__(self, merchant_path: str, extraction_path: str, bank_map_path: str):
        self.merchant_path = merchant_path
        self.extraction_path = extraction_path
        self.bank_map_path = bank_map_path
        
        self.merchant_cache = self._load_cache(self.merchant_path)
        self.extraction_cache = self._load_cache(self.extraction_path)
        self.bank_map_cache = self._load_cache(self.bank_map_path)
        
        # Optimized lookup map for normalized names
        self.normalized_cache = {
            normalize_merchant_name(k): v 
            for k, v in self.merchant_cache.items() 
            if normalize_merchant_name(k)
        }

    def _load_cache(self, path: str) -> dict:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache at {path}: {e}")
                return {}
        return {}

    def save_all(self):
        """Saves all caches to disk atomically."""
        self._save_atomic(self.merchant_path, self.merchant_cache)
        self._save_atomic(self.extraction_path, self.extraction_cache)
        self._save_atomic(self.bank_map_path, self.bank_map_cache)
        
        # Refresh normalized cache after save
        self.normalized_cache = {
            normalize_merchant_name(k): v 
            for k, v in self.merchant_cache.items() 
            if normalize_merchant_name(k)
        }
        logger.info("💾 Caches saved successfully.")

    def _save_atomic(self, path: str, data: dict):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            temp_path = path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, path)
        except Exception as e:
            logger.error(f"Failed to save cache at {path}: {e}")

    def semantic_lookup(self, merchant_name: str, direction: str = "Outgoing") -> Optional[str]:
        """Finds a category for a merchant using fuzzy matching against the catalogue."""
        if not merchant_name or merchant_name.lower() == "unknown":
            return None
            
        target = normalize_merchant_name(merchant_name)
        if not target: return None
        
        # 1. Direct hit in normalized cache (fast)
        if target in self.normalized_cache:
            entry = self.normalized_cache[target]
            if isinstance(entry, dict):
                return entry.get(direction)
            return entry # Fallback for legacy string format
            
        # 2. Fuzzy hit (slow but smart)
        best_match_entry = None
        best_score = 0.0
        
        for cat_merchant, entry in self.merchant_cache.items():
            norm_cat = normalize_merchant_name(cat_merchant)
            if not norm_cat: continue
            
            score = levenshtein_ratio(target, norm_cat)
            if score > 0.85 and score > best_score:
                best_score = score
                best_match_entry = entry
                
        if best_match_entry:
            logger.info(f"🧠 [SEMANTIC] Fuzzy matched '{merchant_name}' to catalogue entry (score: {best_score:.2f})")
            if isinstance(best_match_entry, dict):
                return best_match_entry.get(direction)
            return best_match_entry
            
        return None

    def semantic_lookup_raw(self, full_text: str, direction: str = "Outgoing") -> Optional[tuple]:
        """
        Deep Research: Tries to find ANY merchant from the catalogue as a fuzzy 
        substring or match within the raw text. Returns (category, merchant_name).
        """
        target = normalize_merchant_name(full_text)
        if not target: return None
        
        best_match_entry = None
        best_merchant = None
        best_score = 0.0
        
        # We check every merchant in the catalogue to see if they appear in the text
        for cat_merchant, entry in self.merchant_cache.items():
            norm_cat = normalize_merchant_name(cat_merchant)
            if not norm_cat or len(norm_cat) < 3: continue
            
            # 1. Direct contains check
            if norm_cat in target:
                logger.debug(f"🧠 [DEEP SCAN] Found '{cat_merchant}' specifically in transaction text.")
                category = entry.get(direction) if isinstance(entry, dict) else entry
                if category:
                    return category, cat_merchant
                
            # 2. Fuzzy similarity (slightly more relaxed for deep scan)
            score = levenshtein_ratio(target, norm_cat)
            if score > 0.80 and score > best_score:
                best_score = score
                best_match_entry = entry
                best_merchant = cat_merchant
                
        if best_match_entry:
            category = best_match_entry.get(direction) if isinstance(best_match_entry, dict) else best_match_entry
            if category:
                logger.info(f"🧠 [DEEP SCAN] Fuzzy matched raw text to catalogue entry '{best_merchant}' (score: {best_score:.2f})")
                return category, best_merchant
            
        return None

    def fuzzy_extract_lookup(self, text: str) -> Optional[str]:
        """Attempt to find a similar transaction in the extraction cache by ignoring IDs/dates."""
        norm_text = re.sub(r'[\d\-\/]+', '', text.lower()).strip()
        if not norm_text: return None
        
        for key, merchant in self.extraction_cache.items():
            norm_key = re.sub(r'[\d\-\/]+', '', key.lower()).strip()
            if norm_text == norm_key:
                return merchant
        return None
