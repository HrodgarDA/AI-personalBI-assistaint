import json
import os
import logging
import argparse
from datetime import datetime, timedelta
from src.scraper.gmail_client import GmailScraper
from src.parser.extractor import ExpenseParser

# Configurazione Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

BRONZE_FILE = "data/bronze_raw_emails.jsonl"
SILVER_FILE = "data/silver_expenses.json"

# --- UTILS ---
def get_already_processed_ids(filepath: str, id_key: str = "id") -> set:
    if not os.path.exists(filepath): return set()
    found_ids = set()
    with open(filepath, "r", encoding="utf-8") as f:
        if filepath.endswith(".jsonl"):
            for line in f:
                try: found_ids.add(json.loads(line)[id_key])
                except: continue
        else:
            try:
                data = json.load(f)
                for item in data: found_ids.add(item.get("original_msg_id"))
            except: pass
    return found_ids

def save_to_silver(new_records):
    data = []
    if os.path.exists(SILVER_FILE):
        with open(SILVER_FILE, 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except: data = []
    data.extend([r.model_dump() if hasattr(r, 'model_dump') else r for r in new_records])
    with open(SILVER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- FASI ---
def run_ingestion():
    logger.info("="*30)
    logger.info("📥 FASE: GMAIL INGESTION")
    logger.info("="*30)
    os.makedirs("data", exist_ok=True)
    
    force_full = os.getenv("FORCE_FULL_LOAD", "false").lower() == "true"
    start_date = "2023/01/01" if force_full else (datetime.now() - timedelta(days=3)).strftime('%Y/%m/%d')
    
    scraper = GmailScraper()
    existing_ids = get_already_processed_ids(BRONZE_FILE)
    
    raw_emails = scraper.fetch_expense_emails(max_results=100, query_addon=f"after:{start_date}")
    new_emails = [e for e in raw_emails if e["id"] not in existing_ids]

    if new_emails:
        with open(BRONZE_FILE, "a", encoding="utf-8") as b_f:
            for m in new_emails:
                b_f.write(json.dumps(m, ensure_ascii=False) + "\n")
        logger.info(f"✅ Salvate {len(new_emails)} nuove mail nel Bronze Layer.")
    else:
        logger.info("✅ Nessun nuovo dato da scaricare.")

def run_processing(batch_size: int = 5):
    logger.info("="*30)
    logger.info("🧠 FASE: LLM PROCESSING")
    logger.info("="*30)
    
    if not os.path.exists(BRONZE_FILE):
        logger.error("❌ File Bronze non trovato. Esegui prima --ingest.")
        return

    # Troviamo cosa processare: leggiamo Bronze e sottraiamo ciò che è già in Silver
    all_raw = []
    with open(BRONZE_FILE, "r", encoding="utf-8") as f:
        for line in f: all_raw.append(json.loads(line))
    
    processed_silver_ids = get_already_processed_ids(SILVER_FILE)
    to_process = [m for m in all_raw if m["id"] not in processed_silver_ids]

    if not to_process:
        logger.info("✅ Silver Layer già aggiornato. Nulla da processare.")
        return

    logger.info(f"🚀 Trovate {len(to_process)} mail da processare.")
    parser = ExpenseParser()
    all_extracted = []

    for i in range(0, len(to_process), batch_size):
        batch = to_process[i:i + batch_size]
        logger.info(f"Batch { (i//batch_size)+1 } / { (len(to_process)//batch_size)+1 }")
        
        for email in batch:
            try:
                prompt = f"Data: {email['email_date']}\nOrario: {email['email_time']}\nTesto: {email['body']}"
                res = parser.parse(prompt)
                for exp in res.expenses:
                    if not exp.time:
                        exp.time = email['email_time']
                    if not exp.date and email.get('email_date'):
                        exp.date = email['email_date']
                    record = exp.model_dump()
                    record["original_msg_id"] = email["id"]
                    all_extracted.append(record)
                    logger.info(f"   ✨ {exp.amount}€ @ {exp.merchant} ({exp.date} {exp.time})")
            except Exception as e:
                logger.error(f"   ❌ Errore ID {email['id']}: {e}")

    if all_extracted:
        save_to_silver(all_extracted)
        logger.info(f"✅ Silver Layer aggiornato con {len(all_extracted)} record.")

# --- ENTRY POINT ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BI Expense Tracker CLI")
    parser.add_argument("--ingest", action="store_true", help="Scarica le mail e salva nel Bronze Layer")
    parser.add_argument("--process", action="store_true", help="Processa le mail del Bronze Layer con LLM")
    parser.add_argument("--batch", type=int, default=5, help="Dimensione del batch per il processing")
    
    args = parser.parse_args()

    # Se non viene passato nessun argomento, mostra l'aiuto
    if not args.ingest and not args.process:
        parser.print_help()
    else:
        if args.ingest:
            run_ingestion()
        if args.process:
            run_processing(batch_size=args.batch)