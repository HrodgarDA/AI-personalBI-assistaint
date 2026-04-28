import os
from pydantic_settings import BaseSettings
from typing import List, Dict

class Settings(BaseSettings):
    # --- APP SETTINGS ---
    APP_TITLE: str = "AI Personal BI Assistant"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # --- DATABASE ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_bi")
    
    # --- AI / OLLAMA ---
    OLLAMA_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL: str = os.getenv("OPENAI_MODEL", "qwen3:8b")
    LLM_TIMEOUT: int = 120
    LLM_BATCH_SIZE: int = 5
    
    # --- SEARCH ---
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SEARCH_TIMEOUT: int = 10
    SEARCH_BACKENDS: List[str] = ["google", "brave"]
    
    # --- DATA PATHS ---
    DATA_DIR: str = "data"
    UPLOAD_DIR: str = os.path.join(DATA_DIR, "uploads")
    
    # --- CACHE PATHS (Migrated from auto_bi) ---
    MERCHANT_CATALOGUE: str = os.path.join(DATA_DIR, "merchant_catalogue.json")
    EXTRACTION_CACHE: str = os.path.join(DATA_DIR, "extraction_cache.json")
    BANK_CATEGORY_MAP: str = os.path.join(DATA_DIR, "bank_category_map.json")
    
    # --- NORMALIZATION ---
    CATEGORY_NORMALIZATION_MAP: Dict[str, str] = {
        "Dining": "Dining & Entertainment",
        "Health": "Health & Sport",
        "Savings": "Savings & Investments",
        "Home & Utilities": "Utilities",
        "Refunds": "Refund"
    }

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
