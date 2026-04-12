import csv
import json
import os
import logging
import argparse
import time
from datetime import datetime, timedelta
from src.gmail_client import GmailScraper
from src.extractor import TransactionParser
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
    start_time = time.time()
    logger.info("="*40)
    logger.info("🏅 PHASE: CERTIFY SILVER -> GOLD CSV")
    logger.info("="*40)
    if not os.path.exists(SILVER_FILE):
        logger.error("Silver file missing. Run --process first.")
        return

    with open(SILVER_FILE, 'r', encoding='utf-8') as f:
        try:
            records = json.load(f)
        except Exception as e:
            logger.error(f"Cannot read {SILVER_FILE}: {e}")
            return

    if not records:
        elapsed = time.time() - start_time
        logger.info(f"✅ No records in Silver table. No CSV generated. - Time taken: {elapsed:.2f}s")
        return

    os.makedirs("data", exist_ok=True)
    fieldnames = sorted({key for record in records for key in record.keys()})

    with open(GOLD_FILE, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({k: record.get(k, "") for k in fieldnames})

    elapsed = time.time() - start_time
    logger.info(f"✅ CSV Generated: {GOLD_FILE} ({len(records)} rows) - Time taken: {elapsed:.2f}s")

# --- CORE FASES ---
def run_ingestion():
    start_time = time.time()
    logger.info("="*40)
    logger.info("📥 PHASE: GMAIL INGESTION")
    logger.info("="*40)
    os.makedirs("data", exist_ok=True)
    
    force_full = os.getenv("FORCE_FULL_LOAD", "false").lower() == "true"
    max_limit = int(os.getenv("MAX_EMAILS", "1000000")) if force_full else int(os.getenv("MAX_EMAILS", "50"))
    last_saved_dt = None if force_full else get_latest_saved_datetime(BRONZE_FILE)

    if force_full:
        logger.info("FORCE_FULL_LOAD=true: downloading all available emails.")
        query_addon = ""
    elif last_saved_dt:
        logger.info(f"Incremental logic: fetching emails after {last_saved_dt.isoformat()}")
        query_addon = f"after:{last_saved_dt.strftime('%Y/%m/%d')}"
    else:
        logger.info("No Bronze file found: downloading all available emails.")
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

    elapsed = time.time() - start_time
    if new_emails:
        logger.info(f"Writing {len(new_emails)} new messages to Bronze layer...")
        with open(BRONZE_FILE, "a", encoding="utf-8") as b_f:
            for m in new_emails:
                b_f.write(json.dumps(m, ensure_ascii=False) + "\n")
        logger.info(f"✅ Ingestion completed successfully - Time taken: {elapsed:.2f}s")
    else:
        logger.info(f"✅ No new emails found compared to local Bronze - Time taken: {elapsed:.2f}s")

def run_processing(batch_size: int = 5):
    start_time = time.time()
    logger.info("="*40)
    logger.info("🧠 PHASE: LLM PROCESSING")
    logger.info("="*40)
    
    if not os.path.exists(BRONZE_FILE):
        logger.error("Bronze file missing. Run --ingest first.")
        return

    all_raw = []
    with open(BRONZE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try: all_raw.append(json.loads(line))
            except: continue
    
    processed_silver_ids = get_already_processed_ids(SILVER_FILE)
    to_process = [m for m in all_raw if m["id"] not in processed_silver_ids]

    if not to_process:
        elapsed = time.time() - start_time
        logger.info(f"✅ Silver Layer already synced. Nothing to process. - Time taken: {elapsed:.2f}s")
        return

    logger.info(f"Starting to parse {len(to_process)} emails.")
    parser = TransactionParser()
    total_extracted = 0

    for i in range(0, len(to_process), batch_size):
        batch_start = time.time()
        batch = to_process[i:i + batch_size]
        logger.info(f"📦 Batch {(i // batch_size) + 1} / {(len(to_process) // batch_size) + 1}")
        batch_extracted = []

        for email in batch:
            try:
                prompt = EMAIL_PROMPT_TEMPLATE.format(
                    date=email.get('email_date', ''),
                    time=email.get('email_time', ''),
                    subject=email.get('subject', ''),
                    body=email.get('body', ''),
                )
                res = parser.parse(prompt)

                for exp in res.transactions:
                    if not exp.time:
                        exp.time = email['email_time']
                    if not getattr(exp, 'date', None) and email.get('email_date'):
                        exp.date = email['email_date']
                    record = exp.model_dump()
                    record["original_msg_id"] = email['id']
                    batch_extracted.append(record)
                    logger.info(f"   {exp.amount}€ ({exp.date if getattr(exp, 'date', None) else email.get('email_date', 'n/d')} {exp.time})")
            except Exception as e:
                logger.error(f"   Parsing Error ID {email['id']}: {e}")

        if batch_extracted:
            save_to_silver(batch_extracted)
            total_extracted += len(batch_extracted)
            
        batch_elapsed = time.time() - batch_start
        logger.info(f"Batch saved: {len(batch_extracted)} extractions added - Time taken: {batch_elapsed:.2f}s")

    elapsed = time.time() - start_time
    if total_extracted:
        logger.info(f"✅ Total saving completed: {total_extracted} extractions added - Total time: {elapsed:.2f}s")
    else:
        logger.info(f"✅ Processing completed with 0 new extractions - Total time: {elapsed:.2f}s")

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