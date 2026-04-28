import os
import json
import logging
from functools import lru_cache
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from backend.core.config import settings

logger = logging.getLogger(__name__)

class ColumnMapping(BaseModel):
    date: str = "Date"
    operation: str = "Operation"
    details: str = "Details"
    amount: str = "Amount"
    category_hint: str = "Category"

class BankProfile(BaseModel):
    """Configuration model for bank-specific extraction rules and metadata."""
    profile_name: str = "Default"
    skip_rows: int = 0
    column_mapping: ColumnMapping = ColumnMapping()
    date_format: str = "%d/%m/%Y"
    invert_signs: bool = False
    encoding: str = "utf-8"
    delimiter: str = ","
    custom_prompt: str = ""
    incoming_keywords: List[str] = [
        "credit", "incoming", "salary", "refund", "deposit", "transfer"
    ]
    cleaning_patterns: List[str] = [
        r"CODE\.?\s*\d+",
        r"DONE ON \d{2}/\d{2}/\d{4}",
        r"AT \d{2}:\d{2}",
        r"CARD PAYMENT",
        r"PURCHASE"
    ]
    rules_memory: List[str] = []
    outgoing_categories: List[str] = [
        "Subscriptions", "Utilities", "Home", "Dining & Entertainment", "Shopping", 
        "Health & Sport", "Transport", "Groceries", "Savings & Investments", "Gifts", "Other"
    ]
    incoming_categories: List[str] = ["Salary", "Refund", "Transfer", "Gift", "Other"]

def get_profiles_dir() -> str:
    path = os.path.join(settings.DATA_DIR, "profiles")
    os.makedirs(path, exist_ok=True)
    return path

def get_active_profile_path() -> str:
    return os.path.join(settings.DATA_DIR, "active_profile.txt")

def set_active_profile_name(name: str):
    if not name: return
    path = get_active_profile_path()
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(name))
    load_bank_profile.cache_clear()

def get_active_profile_name() -> str:
    path = get_active_profile_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            name = f.read().strip()
            if name: return name
    return "Default"

def list_profiles() -> List[str]:
    d = get_profiles_dir()
    profiles = [f.replace(".json", "") for f in os.listdir(d) if f.endswith(".json")]
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
    
    return BankProfile(profile_name=name)

def save_bank_profile(profile: BankProfile, old_name: str = None):
    new_name = profile.profile_name or get_active_profile_name()
    
    if old_name and old_name != new_name:
        old_path = os.path.join(get_profiles_dir(), f"{old_name}.json")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
                if get_active_profile_name() == old_name:
                    set_active_profile_name(new_name)
            except Exception as e:
                logger.error(f"Error removing old profile during rename: {e}")

    path = os.path.join(get_profiles_dir(), f"{new_name}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=4, ensure_ascii=False)
            load_bank_profile.cache_clear()
    except Exception as e:
        logger.error(f"Error saving bank profile '{new_name}': {e}")
