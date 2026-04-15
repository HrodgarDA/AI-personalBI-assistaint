import os
import json
import logging
from pydantic import BaseModel, Field
from typing import List, Optional

logger = logging.getLogger(__name__)

class ColumnMapping(BaseModel):
    date: str = "Data"
    operation: str = "Operazione"
    details: str = "Dettagli"
    amount: str = "Importo"
    category_hint: str = "Categoria"

class BankProfile(BaseModel):
    profile_name: str = "Intesa Sanpaolo (Default)"
    skip_rows: int = 18
    column_mapping: ColumnMapping = ColumnMapping()
    date_format: str = "%d/%m/%Y"
    bank_sender_email: str = "notifiche@intesasanpaolo.com"
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
    config_model: str = "llama3:8b"

def get_profile_path() -> str:
    from auto_bi.utils.config import DATA_DIR
    return os.path.join(DATA_DIR, "bank_profile.json")

def load_bank_profile() -> BankProfile:
    path = get_profile_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return BankProfile(**data)
        except Exception as e:
            logger.error(f"Error loading bank profile: {e}. Using defaults.")
    
    # If not exists or error, return default and save it
    profile = BankProfile()
    save_bank_profile(profile)
    return profile

def save_bank_profile(profile: BankProfile):
    path = get_profile_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=4, ensure_ascii=False)
            logger.info(f"Bank profile saved to {path}")
    except Exception as e:
        logger.error(f"Error saving bank profile: {e}")
