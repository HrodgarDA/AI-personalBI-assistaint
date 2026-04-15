import os
import json
import logging
import time
from datetime import datetime
import pandas as pd
from auto_bi.utils.gmail_client import GmailScraper
from auto_bi.utils.config import BRONZE_FILE, BRONZE_EXCEL

logger = logging.getLogger(__name__)


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

def get_latest_saved_date(filepath: str) -> datetime | None:
    if not os.path.exists(filepath):
        return None

    latest_dt = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                date_val = item.get("date", item.get("email_date"))
                if not date_val:
                    continue
                current_dt = datetime.strptime(date_val, "%Y-%m-%d")
                if latest_dt is None or current_dt > latest_dt:
                    latest_dt = current_dt
            except Exception:
                continue
    return latest_dt

def run_ingestion(progress_callback=None):
    start_time = time.time()
    logger.info("="*40)
    logger.info("📥 PHASE: GMAIL INGESTION")
    logger.info("="*40)
    os.makedirs("data", exist_ok=True)
    
    force_full = os.getenv("FORCE_FULL_LOAD", "false").lower() == "true"
    max_limit = int(os.getenv("MAX_EMAILS", "1000000")) if force_full else int(os.getenv("MAX_EMAILS", "50"))
    last_saved_dt = None if force_full else get_latest_saved_date(BRONZE_FILE)

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
    total_raw = len(raw_emails)
    for i, email in enumerate(raw_emails):
        if progress_callback:
            progress_callback(i + 1, total_raw)
            
        if email["id"] in existing_bronze_ids:
            continue

        if last_saved_dt:
            try:
                email_dt = datetime.strptime(email.get('email_date', ''), "%Y-%m-%d")
                if email_dt <= last_saved_dt:
                    continue
            except Exception:
                pass

        new_emails.append(email)

    new_emails.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))

    elapsed = time.time() - start_time
    if new_emails:
        logger.info(f"Writing {len(new_emails)} new messages to Bronze layer...")
        with open(BRONZE_FILE, "a", encoding="utf-8") as b_f:
            for m in new_emails:
                b_f.write(json.dumps(m, ensure_ascii=False) + "\n")
        logger.info(f"✅ Ingestion completed successfully - Time taken: {elapsed:.2f}s")
    else:
        logger.info(f"✅ No new emails found compared to local Bronze - Time taken: {elapsed:.2f}s")


def ingest_excel(uploaded_file, progress_callback=None):
    start_time = time.time()
    logger.info("="*40)
    logger.info("📥 PHASE: EXCEL INGESTION")
    logger.info("="*40)
    os.makedirs("data", exist_ok=True)
    
    try:
        # Load excel skipping first 18 rows. Row 19 becomes header (index 0).
        df = pd.read_excel(uploaded_file, skiprows=18)
    except Exception as e:
        logger.error(f"Failed to read excel file: {e}")
        return 0
        
    expected_cols = ["Data", "Operazione", "Dettagli", "Importo"]
    for col in expected_cols:
        if col not in df.columns:
            logger.error(f"Missing expected column '{col}' in the uploaded excel.")
            return 0
            
    # Remove empty rows based on necessary columns
    df = df.dropna(subset=["Data", "Operazione", "Importo"])
    
    # Check if 'Categoria' column exists for bank_category_hint
    has_bank_category = "Categoria" in df.columns
    
    new_records = []
    
    # Check already processed excel rows? We might need an ID.
    # We can create a pseudo-ID based on Data + Operazione + Importo, or just ingest everything
    # and then in `process` deduplicate, but standard behavior usually assigns the hash as ID if no ID exists.
    import hashlib
    
    existing_bronze_ids = get_already_processed_ids(BRONZE_EXCEL)
    
    total_df = len(df)
    for idx, row in df.iterrows():
        if progress_callback:
            progress_callback(int(idx) + 1, total_df)
            
        date_str = str(row["Data"]).split(" ")[0] # ensure YYYY-MM-DD formatting loosely if it's a datetime
        # More robust date handling:
        try:
            if pd.api.types.is_datetime64_any_dtype(df['Data']):
                parsed_dt = row["Data"]
            else:
                parsed_dt = pd.to_datetime(row["Data"], format="%d/%m/%Y", errors="coerce")
            
            if pd.notna(parsed_dt):
                date_str = parsed_dt.strftime("%Y-%m-%d")
            else:
                date_str = str(row["Data"])
        except:
            date_str = str(row["Data"])
            
        operation = str(row["Operazione"])
        details = str(row["Dettagli"]) if pd.notna(row["Dettagli"]) else ""
        amount = float(row["Importo"]) if pd.notna(row["Importo"]) else 0.0
        
        # Create an ID hash including the index to distinguish consecutive identical transactions
        hash_string = f"{date_str}_{operation}_{amount}_{idx}".encode('utf-8')
        pseudo_id = hashlib.md5(hash_string).hexdigest()
        
        if pseudo_id in existing_bronze_ids:
            continue
            
        # Find the category hint (handle case-insensitive or extra spaces)
        bank_category = ""
        for col in df.columns:
            if str(col).strip().lower() == "categoria":
                val = row[col]
                if pd.notna(val) and str(val).strip().lower() not in ["", "nan", "n.d."]:
                    bank_category = str(val).strip()
                break
        
        record = {
            "id": pseudo_id,
            "date": date_str,
            "time": "00:00",
            "operation": operation,
            "details": details,
            "amount": amount,
            "bank_category_hint": bank_category,
        }
        new_records.append(record)
        existing_bronze_ids.add(pseudo_id)
        
    elapsed = time.time() - start_time
    if new_records:
        with open(BRONZE_EXCEL, "a", encoding="utf-8") as b_f:
            for m in new_records:
                b_f.write(json.dumps(m, ensure_ascii=False) + "\n")
        logger.info(f"✅ Excel Ingestion completed successfully: {len(new_records)} new rows saved - Time taken: {elapsed:.2f}s")
    else:
        logger.info(f"✅ Excel Ingestion completed: no new rows to add - Time taken: {elapsed:.2f}s")
        
    return len(new_records)
