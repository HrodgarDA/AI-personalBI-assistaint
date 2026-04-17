import os

# --- MODEL SETTINGS ---
MODEL_ID = "gemma4-e4b-4bit"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
LLM_TIMEOUT = 30  # Seconds to wait for AI response
MAX_RETRIES = 1   # Number of times to retry a failed LLM call

# --- SEARCH SETTINGS ---
SEARCH_TIMEOUT = 4
SEARCH_BACKENDS = ["google", "brave"]
LLM_BATCH_SIZE = 5 # Number of transactions to process in a single LLM pass

# --- FILE PATHS ---
DATA_DIR = "data"
BRONZE_RAW = os.path.join(DATA_DIR, "bronze_raw_data.jsonl") # Consolidated raw data
SILVER_FILE = os.path.join(DATA_DIR, "silver_expenses.json")
GOLD_FILE = os.path.join(DATA_DIR, "gold_certified_data.csv")
MERCHANT_CATALOGUE = os.path.join(DATA_DIR, "merchant_catalogue.json")
EXTRACTION_CACHE = os.path.join(DATA_DIR, "extraction_cache.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
