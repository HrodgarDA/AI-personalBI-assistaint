import csv
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
GOLD_FILE = "data/gold_certified_data.csv"

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


def get_latest_saved_datetime(filepath: str) -> datetime | None:
    if not os.path.exists(filepath):
        return None

    latest_dt = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                email_date = item.get("email_date")
                email_time = item.get("email_time")
                if not email_date or not email_time:
                    continue
                current_dt = datetime.strptime(f"{email_date} {email_time}", "%Y-%m-%d %H:%M")
                if latest_dt is None or current_dt > latest_dt:
                    latest_dt = current_dt
            except Exception:
                continue
    return latest_dt


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


def run_certify():
    logger.info("="*40)
    logger.info("🏅 FASE: CERTIFY SILVER -> GOLD CSV")
    logger.info("="*40)
    if not os.path.exists(SILVER_FILE):
        logger.error("❌ File Silver mancante. Esegui prima --process.")
        return

    with open(SILVER_FILE, 'r', encoding='utf-8') as f:
        try:
            records = json.load(f)
        except Exception as e:
            logger.error(f"❌ Impossibile leggere {SILVER_FILE}: {e}")
            return

    if not records:
        logger.info("ℹ️ Nessun record presente in Silver. Nessun file CSV generato.")
        return

    os.makedirs("data", exist_ok=True)
    fieldnames = sorted({key for record in records for key in record.keys()})

    with open(GOLD_FILE, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({k: record.get(k, "") for k in fieldnames})

    logger.info(f"✅ CSV generato: {GOLD_FILE} ({len(records)} righe)")

# --- CORE FASES ---
def run_ingestion():
    logger.info("="*40)
    logger.info("📥 FASE: GMAIL INGESTION")
    logger.info("="*40)
    os.makedirs("data", exist_ok=True)
    
    force_full = os.getenv("FORCE_FULL_LOAD", "false").lower() == "true"
    max_limit = int(os.getenv("MAX_EMAILS", "1000000")) if force_full else int(os.getenv("MAX_EMAILS", "50"))
    last_saved_dt = None if force_full else get_latest_saved_datetime(BRONZE_FILE)

    if force_full:
        logger.info("📈 FORCE_FULL_LOAD=true: scarico tutte le email disponibili.")
        query_addon = ""
    elif last_saved_dt:
        logger.info(f"📈 Incrementale: scarico solo le email successive a {last_saved_dt.isoformat()}")
        query_addon = f"after:{last_saved_dt.strftime('%Y/%m/%d')}"
    else:
        logger.info("📈 Nessun Bronze esistente: scarico tutte le email disponibili.")
        query_addon = ""

    scraper = GmailScraper()
    existing_bronze_ids = get_already_processed_ids(BRONZE_FILE)

    raw_emails = scraper.fetch_expense_emails(max_results=max_limit, query_addon=query_addon)
    new_emails = []
    for email in raw_emails:
        if email["id"] in existing_bronze_ids:
            continue

        if last_saved_dt:
            try:
                email_dt = datetime.strptime(
                    f"{email.get('email_date', '')} {email.get('email_time', '')}",
                    "%Y-%m-%d %H:%M",
                )
                if email_dt <= last_saved_dt:
                    continue
            except Exception:
                pass

        new_emails.append(email)

    new_emails.sort(key=lambda e: (e.get("email_date", ""), e.get("email_time", "")))

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
    parser.add_argument("--certify", action="store_true", help="Converte il Silver JSON in gold_certified_data.csv")
    parser.add_argument("--batch", type=int, default=5, help="Dimensione batch processing")
    
    args = parser.parse_args()

    if not args.ingest and not args.process and not args.certify:
        parser.print_help()
    else:
        if args.ingest:
            run_ingestion()
        if args.process:
            run_processing(batch_size=args.batch)
        if args.certify:
            run_certify()