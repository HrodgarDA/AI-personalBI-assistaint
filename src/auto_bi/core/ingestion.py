import os
import json
import logging
import time
import pandas as pd
import hashlib
from datetime import datetime
from auto_bi.utils.config import BRONZE_RAW
from auto_bi.utils.bank_profile import load_bank_profile

logger = logging.getLogger(__name__)


def get_already_processed_ids(filepath: str, id_key: str = "id") -> set:
    """Helper to get IDs that are already present in a JSONL or JSON file."""
    if not os.path.exists(filepath): return set()
    found_ids = set()
    with open(filepath, "r", encoding="utf-8") as f:
        if filepath.endswith(".jsonl"):
            for line in f:
                try: 
                    found_ids.add(json.loads(line)[id_key])
                except Exception: 
                    continue
        else:
            try:
                data = json.load(f)
                for item in data:
                    # Compatibility with silver (which might use original_msg_id) or generic id
                    val = item.get("id", item.get("original_msg_id"))
                    if val:
                        found_ids.add(val)
            except Exception: 
                pass
    return found_ids


def ingest_tabular_data(uploaded_file, progress_callback=None):
    """
    Ingests tabular data (Excel/CSV) into the Bronze layer.
    Renamed from ingest_excel to reflect broader support.
    """
    start_time = time.time()
    logger.info("="*40)
    logger.info("📥 PHASE: TABULAR INGESTION")
    logger.info("="*40)
    os.makedirs("data", exist_ok=True)
    
    profile = load_bank_profile()
    skip_rows = profile.skip_rows
    mapping = profile.column_mapping

    encoding = getattr(profile, 'encoding', 'utf-8')
    delimiter = getattr(profile, 'delimiter', ',')
    
    try:
        # Load file. Pandas handles both Excel and CSV if we use appropriate loaders.
        filename = getattr(uploaded_file, 'name', '').lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(uploaded_file, skiprows=skip_rows, encoding=encoding, sep=delimiter)
        else:
            df = pd.read_excel(uploaded_file, skiprows=skip_rows)
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return 0
        
    expected_cols = [mapping.date, mapping.operation, mapping.amount]
    for col in expected_cols:
        if col not in df.columns:
            logger.error(f"Missing expected column '{col}' in the uploaded file. Check Settings.")
            return 0
            
    # Remove empty rows based on necessary columns
    df = df.dropna(subset=[mapping.date, mapping.operation, mapping.amount])
    
    # Check if category hint column exists
    has_bank_category = mapping.category_hint in df.columns if mapping.category_hint else False
    
    new_records = []
    existing_bronze_ids = get_already_processed_ids(BRONZE_RAW)
    
    total_df = len(df)
    for idx, row in df.iterrows():
        if progress_callback:
            progress_callback(int(idx) + 1, total_df)
            
        raw_date = row[mapping.date]
        # Robust date parsing using pandas powerful inference
        try:
            parsed_dt = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
            if pd.notna(parsed_dt):
                date_str = parsed_dt.strftime("%Y-%m-%d")
            else:
                date_str = str(raw_date)
        except Exception:
            date_str = str(raw_date)
            
        operation = str(row[mapping.operation])
        details = str(row[mapping.details]) if mapping.details in df.columns and pd.notna(row[mapping.details]) else ""
        
        try:
            amount = float(row[mapping.amount]) if pd.notna(row[mapping.amount]) else 0.0
            if getattr(profile, 'invert_signs', False):
                amount = -amount
        except (ValueError, TypeError):
            logger.warning(f"Could not parse amount '{row[mapping.amount]}' at row {idx}")
            amount = 0.0
        
        # Create an ID hash including the index to distinguish consecutive identical transactions
        hash_string = f"{date_str}_{operation}_{amount}_{idx}".encode('utf-8')
        pseudo_id = hashlib.md5(hash_string).hexdigest()
        
        if pseudo_id in existing_bronze_ids:
            continue
            
        # Find the category hint
        bank_category = ""
        if has_bank_category and mapping.category_hint:
            val = row[mapping.category_hint]
            if pd.notna(val) and str(val).strip().lower() not in ["", "nan", "n.d."]:
                bank_category = str(val).strip()
        
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
        with open(BRONZE_RAW, "a", encoding="utf-8") as b_f:
            for m in new_records:
                b_f.write(json.dumps(m, ensure_ascii=False) + "\n")
        logger.info(f"✅ Ingestion completed: {len(new_records)} new rows saved - Time taken: {elapsed:.2f}s")
    else:
        logger.info(f"✅ Ingestion completed: no new rows to add - Time taken: {elapsed:.2f}s")
        
    return len(new_records)


# --- Backward Compatibility Aliases ---
def run_ingestion(*args, **kwargs):
    """Stub for the removed Gmail ingestion logic."""
    logger.warning("run_ingestion (Gmail) has been removed. Use tabular data ingestion instead.")
    return 0

ingest_excel = ingest_tabular_data
