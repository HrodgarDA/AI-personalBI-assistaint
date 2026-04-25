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

DATA_DIR = "data"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- NORMALIZATION ---
CATEGORY_NORMALIZATION_MAP = {
    "Dining": "Dining & Entertainment",
    "Health": "Health & Sport",
    "Savings": "Savings & Investments",
    "Home & Utilities": "Home",
    "Refunds": "Refund"
}
