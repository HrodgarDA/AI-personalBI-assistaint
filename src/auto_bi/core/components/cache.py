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

    def semantic_lookup(self, merchant_name: str) -> Optional[str]:
        """Finds a category for a merchant using fuzzy matching against the catalogue."""
        if not merchant_name or merchant_name.lower() == "unknown":
            return None
            
        target = normalize_merchant_name(merchant_name)
        if not target: return None
        
        # 1. Direct hit in normalized cache (fast)
        if target in self.normalized_cache:
            return self.normalized_cache[target]
            
        # 2. Fuzzy hit (slow but smart)
        best_match = None
        best_score = 0.0
        
        for cat_merchant, category in self.merchant_cache.items():
            norm_cat = normalize_merchant_name(cat_merchant)
            if not norm_cat: continue
            
            score = levenshtein_ratio(target, norm_cat)
            if score > 0.85 and score > best_score:
                best_score = score
                best_match = category
                
        if best_match:
            logger.info(f"🧠 [SEMANTIC] Fuzzy matched '{merchant_name}' to catalogue entry (score: {best_score:.2f})")
        return best_match

    def fuzzy_extract_lookup(self, text: str) -> Optional[str]:
        """Attempt to find a similar transaction in the extraction cache by ignoring IDs/dates."""
        norm_text = re.sub(r'[\d\-\/]+', '', text.lower()).strip()
        if not norm_text: return None
        
        for key, merchant in self.extraction_cache.items():
            norm_key = re.sub(r'[\d\-\/]+', '', key.lower()).strip()
            if norm_text == norm_key:
                return merchant
        return None
