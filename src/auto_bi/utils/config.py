import os

# --- MODEL SETTINGS ---
MODEL_ID = "gemma4-e4b-4bit"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# --- SEARCH SETTINGS ---
SEARCH_TIMEOUT = 8
SEARCH_BACKENDS = ["google", "brave"]

# --- FILE PATHS ---
DATA_DIR = "data"
BRONZE_FILE = os.path.join(DATA_DIR, "bronze_raw_emails.jsonl")
BRONZE_EXCEL = os.path.join(DATA_DIR, "bronze_raw_excel.jsonl")
SILVER_FILE = os.path.join(DATA_DIR, "silver_expenses.json")
GOLD_FILE = os.path.join(DATA_DIR, "gold_certified_data.csv")
MERCHANT_CATALOGUE = os.path.join(DATA_DIR, "merchant_catalogue.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
