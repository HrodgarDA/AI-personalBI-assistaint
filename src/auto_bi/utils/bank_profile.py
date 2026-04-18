import os
import json
import logging
from functools import lru_cache
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class ColumnMapping(BaseModel):
    date: str = "Data"
    operation: str = "Operazione"
    details: str = "Dettagli"
    amount: str = "Importo"
    category_hint: str = "Categoria"

class BankProfile(BaseModel):
    profile_name: str = "Default"
    skip_rows: int = 0
    column_mapping: ColumnMapping = ColumnMapping()
    date_format: str = "%d/%m/%Y"
    invert_signs: bool = False
    encoding: str = "utf-8"
    delimiter: str = ","
    custom_prompt: str = ""
    incoming_keywords: List[str] = [
        "a vostro favore", "accredito", "stipendio",
        "storno pagamento", "storno", "rimborso"
    ]
    cleaning_patterns: List[str] = [
        r"COD\.?\s*DISP\.?\s*\d+",
        r"EFFETTUATO IL \d{2}/\d{2}/\d{4}",
        r"ALLE ORE \d+",
        r"PAGAMENTO CARTA",
        r"ACQUISTO"
    ]
    rules_memory: List[str] = []
    config_model: str = "qwen3:8b"
    classification_model: str = "qwen3:8b"
    fast_model_id: str = "gemma4:e2b"
    merchant_aliases: Dict[str, str] = {}
    category_mapping: Dict[str, str] = {}
    outgoing_categories: List[str] = [
        "Subscriptions", "Utilities", "Home", "Dining & Entertainment", "Shopping", 
        "Health & Sport", "Transport", "Groceries", "Savings & Investments", "Gifts", "Financial", "Other"
    ]
    incoming_categories: List[str] = ["Salary", "Refund", "Transfer", "Gift", "Other"]

def get_profiles_dir() -> str:
    from auto_bi.utils.config import DATA_DIR
    path = os.path.join(DATA_DIR, "profiles")
    os.makedirs(path, exist_ok=True)
    return path

def get_active_profile_path() -> str:
    from auto_bi.utils.config import DATA_DIR
    return os.path.join(DATA_DIR, "active_profile.txt")

def set_active_profile_name(name: str):
    if not name: return
    path = get_active_profile_path()
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(name))
    # CRITICAL: Clear cache so next load_bank_profile() reads the new active name
    load_bank_profile.cache_clear()

def get_active_profile_name() -> str:
    path = get_active_profile_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            name = f.read().strip()
            if name: return name
    return None

def list_profiles() -> List[str]:
    d = get_profiles_dir()
    profiles = [f.replace(".json", "") for f in os.listdir(d) if f.endswith(".json")]
    if not profiles:
        return []
    return profiles

@lru_cache(maxsize=32)
def load_bank_profile(name: str = None) -> BankProfile:
    if name is None:
        name = get_active_profile_name()
    
    path = os.path.join(get_profiles_dir(), f"{name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return BankProfile(**data)
        except Exception as e:
            logger.error(f"Error loading bank profile '{name}': {e}. Using defaults.")
    
    # If not exists or error, return a fresh profile object BUT DO NOT SAVE IT YET
    profile = BankProfile(profile_name=name if name else "New Profile")
    if name: # Only cache if a name was provided
        load_bank_profile.cache_clear()
    return profile

def save_bank_profile(profile: BankProfile, old_name: str = None):
    new_name = profile.profile_name or get_active_profile_name()
    
    # Handle Rename: If an old name is provided and it differs from the new one, cleanup the old file
    if old_name and old_name != new_name:
        old_path = os.path.join(get_profiles_dir(), f"{old_name}.json")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
                logger.info(f"Renaming profile: deleted old file {old_path}")
                # If we were editing the active profile, point the system to the new name
                if get_active_profile_name() == old_name:
                    set_active_profile_name(new_name)
            except Exception as e:
                logger.error(f"Error removing old profile file during rename: {e}")

    path = os.path.join(get_profiles_dir(), f"{new_name}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=4, ensure_ascii=False)
            logger.info(f"Bank profile '{new_name}' saved to {path}")
            # Clear cache to ensure next load gets updated version
            load_bank_profile.cache_clear()
    except Exception as e:
        logger.error(f"Error saving bank profile '{new_name}': {e}")
