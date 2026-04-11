import json
import os
import logging
import argparse
from datetime import datetime, timedelta
from src.gmail_client import GmailScraper
from src.extractor import ExpenseParser
from src.prompts import EMAIL_PROMPT_TEMPLATE

# Logging Setup
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
                for item in data:
                    if "original_msg_id" in item:
                        found_ids.add(item["original_msg_id"])
            except: pass
    return found_ids

def save_to_silver(new_records):
    data = []
    if os.path.exists(SILVER_FILE):
        with open(SILVER_FILE, 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except: data = []
    
    # Supporto sia per oggetti Pydantic che per dizionari
    data.extend([r.model_dump() if hasattr(r, 'model_dump') else r for r in new_records])
    
    with open(SILVER_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- CORE FASES ---
def run_ingestion():
    logger.info("="*40)
    logger.info("📥 FASE: GMAIL INGESTION")
    logger.info("="*40)
    os.makedirs("data", exist_ok=True)
    
    # Logica Data: Full Load 2025 vs Incremental 3gg
    force_full = os.getenv("FORCE_FULL_LOAD", "false").lower() == "true"
    start_date = (datetime.now() - timedelta(days=3)).strftime('%Y/%m/%d')
    max_limit = 50
    logger.info(f"📈 MODALITÀ INCREMENTALE: Check dal {start_date}")
    
    scraper = GmailScraper()
    existing_bronze_ids = get_already_processed_ids(BRONZE_FILE)
    
    raw_emails = scraper.fetch_expense_emails(max_results=max_limit, query_addon=f"after:{start_date}")
    new_emails = [e for e in raw_emails if e["id"] not in existing_bronze_ids]

    if new_emails:
        logger.info(f"💾 Scrittura di {len(new_emails)} nuovi messaggi in Bronze...")
        with open(BRONZE_FILE, "a", encoding="utf-8") as b_f:
            for m in new_emails:
                b_f.write(json.dumps(m, ensure_ascii=False) + "\n")
        logger.info("✅ Ingestion completata con successo.")
    else:
        logger.info("✅ Nessun dato nuovo trovato rispetto al Bronze locale.")

def run_processing(batch_size: int = 5):
    logger.info("="*40)
    logger.info("🧠 FASE: LLM PROCESSING")
    logger.info("="*40)
    
    if not os.path.exists(BRONZE_FILE):
        logger.error("❌ File Bronze mancante. Esegui prima --ingest.")
        return

    # Leggi tutti i dati grezzi
    all_raw = []
    with open(BRONZE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try: all_raw.append(json.loads(line))
            except: continue
    
    # Filtra ciò che è già finito nel Silver
    processed_silver_ids = get_already_processed_ids(SILVER_FILE)
    to_process = [m for m in all_raw if m["id"] not in processed_silver_ids]

    if not to_process:
        logger.info("✅ Silver Layer già sincronizzato. Nulla da processare.")
        return

    logger.info(f"🚀 Inizio parsing di {len(to_process)} email.")
    parser = ExpenseParser()
    total_extracted = 0

    for i in range(0, len(to_process), batch_size):
        batch = to_process[i:i + batch_size]
        logger.info(f"📦 Batch {(i // batch_size) + 1} / {(len(to_process) // batch_size) + 1}")
        batch_extracted = []

        for email in batch:
            try:
                # Prompt arricchito con data e orario della mail
                prompt = EMAIL_PROMPT_TEMPLATE.format(
                    date=email.get('email_date', ''),
                    time=email.get('email_time', ''),
                    body=email.get('body', ''),
                )
                res = parser.parse(prompt)

                for exp in res.expenses:
                    if not exp.time:
                        exp.time = email['email_time']
                    if not getattr(exp, 'date', None) and email.get('email_date'):
                        exp.date = email['email_date']
                    record = exp.model_dump()
                    record["original_msg_id"] = email['id']
                    batch_extracted.append(record)
                    logger.info(f"   ✨ {exp.amount}€ ({exp.date if getattr(exp, 'date', None) else email.get('email_date', 'n/d')} {exp.time})")
            except Exception as e:
                logger.error(f"   ❌ Errore parsing ID {email['id']}: {e}")

        if batch_extracted:
            save_to_silver(batch_extracted)
            total_extracted += len(batch_extracted)
            logger.info(f"💾 Salvataggio batch completato: {len(batch_extracted)} transazioni aggiunte.")

    if total_extracted:
        logger.info(f"💾 Salvataggio totale completato: {total_extracted} transazioni aggiunte.")

# --- CLI ENTRY POINT ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BI Expense ETL CLI")
    parser.add_argument("--ingest", action="store_true", help="Esegue lo scaricamento da Gmail")
    parser.add_argument("--process", action="store_true", help="Esegue il parsing LLM")
    parser.add_argument("--batch", type=int, default=5, help="Dimensione batch processing")
    
    args = parser.parse_args()

    if not args.ingest and not args.process:
        parser.print_help()
    else:
        if args.ingest:
            run_ingestion()
        if args.process:
            run_processing(batch_size=args.batch)