import os

# --- MODEL SETTINGS ---
MODEL_ID = "qwen3:8b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
LLM_TIMEOUT = 120  # Increased for stability on M1 Pro
MAX_RETRIES = 1

# --- SEARCH SETTINGS ---
SEARCH_TIMEOUT = 4
SEARCH_BACKENDS = ["google", "brave"]
LLM_BATCH_SIZE = 5 # Number of transactions to process in a single LLM pass

# --- FILE PATHS ---
DATA_DIR = "data"
BRONZE_RAW = os.path.join(DATA_DIR, "bronze_raw_data.jsonl") # Consolidated raw data
SILVER_FILE = os.path.join(DATA_DIR, "silver_expenses.jsonl")
LEGACY_SILVER = os.path.join(DATA_DIR, "silver_expenses.json")
GOLD_FILE = os.path.join(DATA_DIR, "gold_certified_data.csv")
DELETED_IDS_FILE = os.path.join(DATA_DIR, "deleted_ids.json")
MERCHANT_CATALOGUE = os.path.join(DATA_DIR, "merchant_catalogue.json")
EXTRACTION_CACHE = os.path.join(DATA_DIR, "extraction_cache.json")
BANK_CATEGORY_MAP = os.path.join(DATA_DIR, "bank_category_map.json")
PERF_STATS = os.path.join(DATA_DIR, "perf_stats.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- NORMALIZATION ---
CATEGORY_NORMALIZATION_MAP = {
    "Dining": "Dining & Entertainment",
    "Health": "Health & Sport",
    "Savings": "Savings & Investments",
    "Home & Utilities": "Utilities",
    "Refunds": "Refund"
}
