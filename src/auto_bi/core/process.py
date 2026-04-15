import os
import json
import logging
import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor
from auto_bi.core.extractor import TransactionParser
from auto_bi.utils.prompts import EMAIL_PROMPT_TEMPLATE
from auto_bi.core.ingestion import get_already_processed_ids
from auto_bi.utils.config import BRONZE_FILE, BRONZE_EXCEL, SILVER_FILE, GOLD_FILE
from auto_bi.utils.utils import extract_merchant_from_excel

logger = logging.getLogger(__name__)



def _extract_merchant_from_excel_legacy(operation: str, details: str) -> str:
    """DEPRECATED: Use src.utils.extract_merchant_from_excel instead."""
    return extract_merchant_from_excel(operation, details)



def _determine_direction(text: str, amount: float = None) -> str:
    """
    Pre-classify transaction direction from Italian banking keywords or amount sign.
    For Excel: amount sign is the source of truth.
    For Email: keyword matching on subject/body.
    """
    if amount is not None:
        return "Incoming" if amount >= 0 else "Outgoing"
    
    text_lower = text.lower()
    incoming_patterns = [
        "a vostro favore",       # "Bonifico A Vostro Favore Disposto Da"
        "accredito",             # Account credit
        "stipendio",             # Salary
        "storno pagamento",      # Payment reversal / refund
        "storno",                # Generic reversal
        "rimborso",              # Refund
    ]
    for pattern in incoming_patterns:
        if pattern in text_lower:
            return "Incoming"
    return "Outgoing"


def _get_mode_string(source: str) -> str:
    """Map category source to a user-friendly mode string with emoji."""
    mapping = {
        "from_catalogue": "⚡ BYPASS MODEL",
        "web_search": "🔍 WEB SEARCH",
        "llm_inference": "🧠 LLM MODEL"
    }
    return mapping.get(source, "🧠 LLM MODEL")


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

    # Migration/Normalization: ensure source, time, and new tipology values
    OLD_TO_NEW_TIPOLOGY = {
        "Expense": "Outgoing", "expense": "Outgoing",
        "Refund": "Outgoing",  # Old refund was outgoing-negative; now we use amount sign
        "Salary": "Incoming",
    }
    for r in records:
        if "source" not in r:
            r["source"] = "excel" if len(str(r.get("original_msg_id", ""))) == 32 else "email"
        if "time" not in r or not r["time"]:
            r["time"] = "00:00"
        # Migrate old tipology values
        old_tip = r.get("tipology", "")
        if old_tip in OLD_TO_NEW_TIPOLOGY:
            r["tipology"] = OLD_TO_NEW_TIPOLOGY[old_tip]
        # Migrate old category "Refunds" -> "Refund"
        if r.get("category") == "Refunds":
            r["category"] = "Refund"

    # Identify "Excel Coverage": Dates that have at least one Excel record
    excel_dates = {r["date"] for r in records if r["source"] == "excel"}
    
    final_records = []
    
    # Group by Date to handle culling
    from collections import defaultdict
    date_groups = defaultdict(list)
    for r in records:
        date_groups[r["date"]].append(r)
        
    for dt, group in date_groups.items():
        if dt not in excel_dates:
            # Case A: No Excel for this date. Keep all email records.
            final_records.extend(group)
        else:
            # Case B: Excel exists for this date. EXCEL COMMANDS.
            excel_rows = [r for r in group if r["source"] == "excel"]
            email_rows = [r for r in group if r["source"] == "email"]
            
            # Sort emails by time to pair them predictably
            email_rows.sort(key=lambda x: x.get("time", "00:00"))
            
            # Group by amount and merchant to match specific identical transactions
            excel_subgroups = defaultdict(list)
            for r in excel_rows:
                key = (r["amount"], r["merchant"].lower()[:5])
                excel_subgroups[key].append(r)
                
            email_subgroups = defaultdict(list)
            for r in email_rows:
                key = (r["amount"], r["merchant"].lower()[:5])
                email_subgroups[key].append(r)
                
            # For each Excel record, try to take a time from a matching email
            for (amt, merch_prefix), sub_excel in excel_subgroups.items():
                sub_email = email_subgroups.get((amt, merch_prefix), [])
                
                for ex_rec in sub_excel:
                    if sub_email:
                        matching_mail = sub_email.pop(0)
                        ex_rec["time"] = matching_mail["time"]
                    final_records.append(ex_rec)
            
            # Note: Any leftover email_rows are DISCARDED (Culling)
            
    records = final_records
    records.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    os.makedirs("data", exist_ok=True)
    fieldnames = sorted({key for record in records for key in record.keys()})

    with open(GOLD_FILE, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({k: record.get(k, "") for k in fieldnames})

    elapsed = time.time() - start_time
    logger.info(f"✅ CSV Generated: {GOLD_FILE} ({len(records)} rows) - Time taken: {elapsed:.2f}s")


def run_processing(batch_size: int = 5, progress_callback=None):
    start_time = time.time()
    logger.info("="*40)
    logger.info("🧠 PHASE: LLM PROCESSING (EMAILS)")
    logger.info("="*40)
    
    if not os.path.exists(BRONZE_FILE):
        logger.error("Bronze file missing. Run --ingest first.")
        return

    all_raw = []
    with open(BRONZE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try: all_raw.append(json.loads(line))
            except: continue
    
    processed_silver_ids = get_already_processed_ids(SILVER_FILE, id_key="original_msg_id")
    to_process = [m for m in all_raw if m["id"] not in processed_silver_ids]

    if not to_process:
        elapsed = time.time() - start_time
        logger.info(f"✅ Silver Layer already synced. Nothing to process. - Time taken: {elapsed:.2f}s")
        return

    logger.info(f"Starting to parse {len(to_process)} emails.")
    parser = TransactionParser()
    total_extracted = 0
    total_emails = len(to_process)

    for i in range(0, len(to_process), batch_size):
        batch_start = time.time()
        batch = to_process[i:i + batch_size]
        logger.info(f"📦 Batch {(i // batch_size) + 1} / {(len(to_process) // batch_size) + 1}")
        
        def process_email(email):
            try:
                text = EMAIL_PROMPT_TEMPLATE.format(
                    date=email.get('date', ''),
                    time=email.get('time', ''),
                    operation=email.get('operation', ''),
                    details=email.get('details', ''),
                )
                canonical_date = email.get('date', '')
                direction = _determine_direction(
                    email.get('operation', '') + ' ' + email.get('details', '')
                )

                # Unified classification
                result = parser.classify_transaction(text, direction)

                return {
                    "original_msg_id": email['id'],
                    "tipology": direction,
                    "merchant": result.get('merchant', 'Unknown'),
                    "category": result['category'],
                    "amount": result.get('amount') or 0.0,
                    "date": canonical_date,
                    "time": email.get('time', '00:00'),
                    "source": "email",
                    "category_source": result.get('category_source', 'llm_inference'),
                    "confidence": result.get('confidence', 0.0),
                    "reasoning": result.get('reasoning', ''),
                }
            except Exception as e:
                logger.error(f"   Parsing Error ID {email['id']}: {e}")
                return None

        results = []
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            results = list(executor.map(process_email, batch))
        
        batch_extracted = []
        for res in results:
            if res:
                total_extracted += 1
                mode_str = _get_mode_string(res.get('category_source'))
                logger.info(f"Processing transaction {total_extracted} ({res['merchant']}, {res['amount']}€, {res['date']}) Selected Mode: {mode_str}")
                batch_extracted.append(res)

        if batch_extracted:
            save_to_silver(batch_extracted)
            total_extracted += len(batch_extracted)
            if progress_callback:
                progress_callback(total_extracted, total_emails)
            
        batch_elapsed = time.time() - batch_start
        logger.info(f"   Batch completed - {len(batch_extracted)} extractions - {batch_elapsed:.2f}s")

    elapsed = time.time() - start_time
    logger.info("="*40)
    logger.info("🏁 EMAIL PROCESSING SUMMARY")
    logger.info(f"   - Total Emails Handled: {total_emails}")
    logger.info(f"   - Total Extractions:    {total_extracted}")
    logger.info(f"   - Total Time Elapsed:   {elapsed:.2f}s")
    if total_extracted > 0:
        logger.info(f"   - Speed (avg):         {elapsed/total_extracted:.2f}s / extraction")
    logger.info("="*40)

def run_excel_processing(batch_size: int = 5, progress_callback=None):
    start_time = time.time()
    logger.info("="*40)
    logger.info("🧠 PHASE: LLM PROCESSING (EXCEL)")
    logger.info("="*40)
    
    if not os.path.exists(BRONZE_EXCEL):
        logger.info("Nessun file data/bronze_raw_excel.jsonl trovato. Niente da processare o caricamento mancante.")
        return

    all_raw = []
    with open(BRONZE_EXCEL, "r", encoding="utf-8") as f:
        for line in f:
            try: all_raw.append(json.loads(line))
            except: continue
            
    processed_silver_ids = get_already_processed_ids(SILVER_FILE, id_key="original_msg_id")
    to_process = [m for m in all_raw if m["id"] not in processed_silver_ids]
    
    if not to_process:
        elapsed = time.time() - start_time
        logger.info(f"✅ Excel Silver Layer already synced. Nothing to process. - Time taken: {elapsed:.2f}s")
        return
        
    logger.info(f"Starting to parse {len(to_process)} excel occurrences.")
    parser = TransactionParser()
    total_extracted = 0
    total_rows = len(to_process)
    
    for i in range(0, len(to_process), batch_size):
        batch_start = time.time()
        batch = to_process[i:i + batch_size]
        logger.info(f"📦 Excel Batch {(i // batch_size) + 1} / {(len(to_process) // batch_size) + 1}")
        
        def process_record(record):
            try:
                operation = record.get("operation", "")
                details = record.get("details", "")
                amount = float(record.get("amount", 0.0))
                rec_date = record.get("date", "")
                rec_time = record.get("time", "00:00")
                bank_cat = record.get("bank_category_hint", "")
                
                direction = _determine_direction(f"{operation} {details}", amount=amount)
                merchant = extract_merchant_from_excel(operation, details)

                text_parts = [f"Operation: {operation}", f"Merchant: {merchant}", f"Details: {details}"]
                if bank_cat:
                    text_parts.append(f"Bank category hint: {bank_cat}")
                text = "\n".join(text_parts)
                
                # Pass amount to allow LLM bypass if already in catalogue
                result = parser.classify_transaction(text, direction, merchant=merchant, amount=amount)
                
                final_amount = -abs(amount) if direction == "Outgoing" else abs(amount)
                
                return {
                    "original_msg_id": record["id"],
                    "tipology": direction,
                    "merchant": merchant,
                    "category": result['category'],
                    "amount": final_amount,
                    "date": rec_date,
                    "time": rec_time,
                    "source": "excel",
                    "category_source": result.get('category_source', 'llm_inference'),
                    "confidence": result.get('confidence', 0.0),
                    "reasoning": result.get('reasoning', ''),
                }
            except Exception as e:
                logger.error(f"   Excel Parsing Error ID {record.get('id')}: {e}")
                return None

        results = []
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            results = list(executor.map(process_record, batch))
        
        batch_extracted = []
        for res in results:
            if res:
                total_extracted += 1
                mode_str = _get_mode_string(res.get('category_source'))
                logger.info(f"Processing transaction {total_extracted} ({res['merchant']}, {res['amount']}€, {res['date']}) Selected Mode: {mode_str}")
                batch_extracted.append(res)

        if batch_extracted:
            save_to_silver(batch_extracted)
            if progress_callback:
                progress_callback(total_extracted, total_rows)
            
        batch_elapsed = time.time() - batch_start
        logger.info(f"   Batch completed - {len(batch_extracted)} extractions - {batch_elapsed:.2f}s")

    elapsed = time.time() - start_time
    logger.info("="*40)
    logger.info("🏁 EXCEL PROCESSING SUMMARY")
    logger.info(f"   - Total Excel Rows Handled: {total_rows}")
    logger.info(f"   - Total Classifications:    {total_extracted}")
    logger.info(f"   - Total Time Elapsed:       {elapsed:.2f}s")
    if total_extracted > 0:
        logger.info(f"   - Speed (avg):             {elapsed/total_extracted:.2f}s / row")
    logger.info("="*40)
