import os
import json
import logging
import csv
import time
import concurrent.futures
from auto_bi.core.extractor import TransactionParser
from auto_bi.core.ingestion import get_already_processed_ids
from auto_bi.utils.config import BRONZE_RAW, SILVER_FILE, GOLD_FILE
from auto_bi.utils.utils import extract_merchant_from_excel
from auto_bi.utils.bank_profile import load_bank_profile

logger = logging.getLogger(__name__)


def _determine_direction(text: str, amount: float = None) -> str:
    """
    Classify transaction direction from amount sign.
    Keywords are technically secondary for Tabular data.
    """
    if amount is not None:
        return "Incoming" if amount >= 0 else "Outgoing"
    
    # Fallback to keywords if amount is missing
    text_lower = text.lower()
    profile = load_bank_profile()
    for pattern in profile.incoming_keywords:
        if pattern.lower() in text_lower:
            return "Incoming"
    return "Outgoing"


def _get_mode_string(source: str) -> str:
    """Map category source to a standardized log prefix."""
    mapping = {
        "fast_path_mapping": "[BYPASS]",
        "from_catalogue":    "[BYPASS]",
        "web_search":        "[ WEB  ]",
        "llm_inference":     "[  IA  ]"
    }
    return mapping.get(source, "[  IA  ]")


def _print_recap(total_time: float, records: list, failed_count: int = 0):
    """Prints a detailed recap report of the processing run."""
    logger.info("\n" + "═"*50)
    logger.info("📊 PROCESSING RECAP REPORT")
    logger.info("═"*50)
    
    total_records = len(records)
    avg_time = (sum(r['duration'] for r in records) / total_records) if total_records > 0 else 0
    
    logger.info("\n📈 GENERAL STATISTICS:")
    logger.info(f"   - Total Successfully Processed: {total_records}")
    if failed_count > 0:
        logger.info(f"   - Failed/Timed Out:             {failed_count} ⚠️")
    logger.info(f"   - Total Execution Time:         {total_time:.2f}s")
    if total_records > 0:
        logger.info(f"   - Average Speed:                {avg_time:.2f}s / record")
    
    if records:
        slowest = max(records, key=lambda x: x['duration'])
        logger.info("\n🐢 SLOWEST TRANSACTION (Bottleneck):")
        logger.info(f"   - Merchant:     {slowest['merchant']}")
        logger.info(f"   - Mode:         {slowest['mode']}")
        logger.info(f"   - Time:         {slowest['duration']:.2f}s")
        
    logger.info("\n" + "═"*50 + "\n")


def _check_llm_health() -> bool:
    """Check if Ollama server is reachable."""
    from auto_bi.utils.config import OLLAMA_BASE_URL
    import requests
    try:
        response = requests.get(OLLAMA_BASE_URL.replace("/v1", "/api/tags"), timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def save_to_silver(new_records, current_state=None):
    """
    Appends new records to the silver JSON file.
    If current_state is provided, it uses it instead of re-reading from disk.
    """
    if current_state is not None:
        data = current_state
    else:
        data = []
        if os.path.exists(SILVER_FILE):
            with open(SILVER_FILE, 'r', encoding='utf-8') as f:
                try: 
                    data = json.load(f)
                except Exception: 
                    data = []
    
    # Handle both Pydantic models and dictionaries
    new_data = [r.model_dump() if hasattr(r, 'model_dump') else r for r in new_records]
    data.extend(new_data)
    
    os.makedirs(os.path.dirname(SILVER_FILE), exist_ok=True)
    
    # Atomic write-then-rename to prevent corruption
    temp_file = SILVER_FILE + ".tmp"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(temp_file, SILVER_FILE)
    
    return data


def run_certify():
    """Converts Silver JSON to Gold CSV with normalization."""
    start_time = time.time()
    logger.info("="*40)
    logger.info("🏅 PHASE: DATA CERTIFICATION")
    logger.info("="*40)
    
    if not os.path.exists(SILVER_FILE):
        logger.error("Silver file missing. Run processing first.")
        return

    with open(SILVER_FILE, 'r', encoding='utf-8') as f:
        try:
            records = json.load(f)
        except Exception as e:
            logger.error(f"Cannot read {SILVER_FILE}: {e}")
            return

    if not records:
        logger.info(f"✅ No records to certify. - Time taken: {time.time() - start_time:.2f}s")
        return

    # Normalization & Cleaning
    for r in records:
        if "time" not in r or not r["time"]:
            r["time"] = "00:00"
        
        # Migrate/Fix typography/direction labels
        tip = r.get("tipology", "").lower()
        if tip in ["expense", "refund"]:
            r["tipology"] = "Outgoing"
        elif tip == "salary":
            r["tipology"] = "Incoming"
            
        if r.get("category") == "Refunds":
            r["category"] = "Refund"

    records.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    # Export to CSV
    fieldnames = sorted({key for record in records for key in record.keys()})
    with open(GOLD_FILE, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({k: record.get(k, "") for k in fieldnames})

    logger.info(f"✅ CSV Generated: {GOLD_FILE} ({len(records)} rows) - Time taken: {time.time() - start_time:.2f}s")


def run_processing(batch_size: int = 5, progress_callback=None):
    """Main LLM processing loop for Bronze data. Optimized with grouping and buffering."""
    start_time = time.time()
    logger.info("="*40)
    logger.info("🧠 PHASE: AI CATEGORIZATION (OPTIMIZED)")
    logger.info("="*40)
    
    if not os.path.exists(BRONZE_RAW):
        logger.info(f"No raw data found at {BRONZE_RAW}. Upload data first.")
        return

    # 1. Load context once
    all_raw = []
    with open(BRONZE_RAW, "r", encoding="utf-8") as f:
        for line in f:
            try: 
                all_raw.append(json.loads(line))
            except Exception: 
                continue
            
    # Load silver state once to avoid repeated disk hits
    silver_state = []
    if os.path.exists(SILVER_FILE):
        with open(SILVER_FILE, 'r', encoding='utf-8') as f:
            try: silver_state = json.load(f)
            except Exception: silver_state = []
            
    processed_silver_ids = {str(r.get("id")) for r in silver_state}
    to_process = [m for m in all_raw if str(m["id"]) not in processed_silver_ids]
    
    if not to_process:
        logger.info(f"✅ Silver Layer already synced. Nothing to process. - Time taken: {time.time() - start_time:.2f}s")
        return
        
    logger.info(f"Starting to process {len(to_process)} transactions.")
    if not _check_llm_health():
        logger.error("❌ CRITICAL: Ollama server is unreachable. Ensure Ollama is running.")
        return

    parser = TransactionParser()
    total_rows = len(to_process)
    total_processed_instances = 0
    total_failed = 0
    all_processed_stats = []

    # 2. Semantic Grouping (Grouping identical transactions)
    groups = {}
    for record in to_process:
        sig = (
            record.get("operation", "").strip(),
            record.get("details", "").strip(),
            record.get("bank_category_hint", "").strip(),
            float(record.get("amount", 0.0))
        )
        if sig not in groups:
            groups[sig] = []
        groups[sig].append(record)

    unique_signatures = list(groups.keys())
    logger.info(f"💎 Found {len(unique_signatures)} unique transaction signatures among {total_rows} records.")

    # 3. Processing unique signatures in blocks
    process_batch_size = 10 # Process 10 unique signatures at a time
    for i in range(0, len(unique_signatures), process_batch_size):
        batch_start = time.time()
        sig_batch = unique_signatures[i:i + process_batch_size]
        logger.info(f"📦 Unique Block {(i // process_batch_size) + 1} / {(len(unique_signatures) // process_batch_size) + 1}")
        
        tx_to_classify = [] # Inputs for classify_batch
        results_map = {} # Results for each signature
        
        # Prepare the block
        for sig in sig_batch:
            record = groups[sig][0]
            operation, details, bank_cat, amount = sig
            direction = _determine_direction(f"{operation} {details}", amount=amount)
            
            # Fast Path Mapping
            mapped_cat = None
            if bank_cat:
                mapping = getattr(parser.profile, 'category_mapping', {})
                lookup = {k.lower().strip(): v for k, v in mapping.items()}
                mapped_cat = lookup.get(bank_cat.lower().strip())
            
            if mapped_cat:
                results_map[sig] = {
                    "category": mapped_cat,
                    "merchant": "Mapped", # Will be refined later
                    "confidence": 1.0,
                    "category_source": "fast_path_mapping",
                    "reasoning": f"Mapped via bank profile.",
                    "duration": 0.01
                }
            else:
                # Add to LLM batch
                custom_p = getattr(parser.profile, 'cleaning_patterns', [])
                aliases = getattr(parser.profile, 'merchant_aliases', {})
                merchant = extract_merchant_from_excel(operation, details, custom_patterns=custom_p, aliases=aliases)
                
                text = f"Operation: {operation}\nDetails: {details}"
                if bank_cat: text += f"\nBank category: {bank_cat}"
                
                tx_to_classify.append({
                    "sig": sig,
                    "text": text,
                    "direction": direction,
                    "merchant": merchant,
                    "amount": amount
                })

        # Process Batch
        if tx_to_classify:
            t0 = time.time()
            logger.info(f"   ⚙️ Preparing batch for LLM...")
            batch_results = parser.classify_batch([{"text": x['text'], "direction": x['direction'], "merchant": x['merchant'], "amount": x['amount']} for x in tx_to_classify])
            duration_per_tx = (time.time() - t0) / len(tx_to_classify)
            
            for idx, res in enumerate(batch_results):
                sig = tx_to_classify[idx]['sig']
                res['duration'] = duration_per_tx 
                results_map[sig] = res
            logger.info(f"   ✨ Batch processed in {time.time() - t0:.2f}s")

        # Distribute Results to All Instances
        new_silver_entries = []
        for sig in sig_batch:
            res = results_map.get(sig)
            if not res: 
                total_failed += 1
                continue
            
            instances = groups[sig]
            mode_prefix = _get_mode_string(res.get('category_source'))
            logger.info(f"   {mode_prefix} {res['merchant']:<20} | {res['category']:<20} (x{len(instances)}) [{res['duration']:.2f}s/avg]")
            
            operation, details, bank_cat, amount = sig
            direction = _determine_direction(f"{operation} {details}", amount=amount)
            final_amount = -abs(amount) if direction == "Outgoing" else abs(amount)

            for inst in instances:
                entry = {
                    "id": inst["id"],
                    "date": inst.get("date", ""),
                    "time": inst.get("time", "00:00"),
                    "tipology": direction,
                    "merchant": res['merchant'],
                    "category": res['category'],
                    "amount": final_amount,
                    "original_operation": operation,
                    "original_details": details,
                    "source": "tabular",
                    "category_source": res.get('category_source', 'llm_inference'),
                    "confidence": res.get('confidence', 0.0),
                    "reasoning": res.get('reasoning', ''),
                }
                new_silver_entries.append(entry)
                total_processed_instances += 1
                
                all_processed_stats.append({
                    "id": inst.get("id"),
                    "merchant": res.get("merchant"),
                    "duration": res['duration'],
                    "mode": mode_prefix
                })

        if new_silver_entries:
            silver_state = save_to_silver(new_silver_entries, current_state=silver_state)
            parser.save_caches()
            if progress_callback:
                progress_callback(total_processed_instances, total_rows)
            
        logger.info(f"   Block completed in {time.time() - batch_start:.2f}s")
            
    _print_recap(total_time=time.time() - start_time, records=all_processed_stats, failed_count=total_failed)


# --- Backward Compatibility Aliases ---
run_excel_processing = run_processing
