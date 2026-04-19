import os
import json
import logging
import csv
import time
from typing import List, Dict, Set, Tuple, Optional

from auto_bi.core.extractor import TransactionParser
from auto_bi.utils.config import (
    BRONZE_RAW, SILVER_FILE, GOLD_FILE, DELETED_IDS_FILE, 
    PERF_STATS, LEGACY_SILVER, CATEGORY_NORMALIZATION_MAP
)
from auto_bi.utils.utils import extract_merchant_from_excel
from auto_bi.utils.bank_profile import load_bank_profile

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _determine_direction(text: str, amount: float = None) -> str:
    """Classify transaction direction from amount sign or keywords."""
    if amount is not None:
        return "Incoming" if amount >= 0 else "Outgoing"
    
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
    
    if avg_time > 0:
        try:
            with open(PERF_STATS, "w", encoding="utf-8") as f:
                json.dump({"avg_speed_seconds": avg_time, "last_updated": time.time()}, f)
            logger.info(f"💾 Performance stats saved (Avg speed: {avg_time:.2f}s/tx)")
        except Exception as e:
            logger.warning(f"Could not save perf stats: {e}")
        
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


def migrate_silver_to_jsonl():
    """Converts legacy .json silver file to .jsonl format."""
    if os.path.exists(LEGACY_SILVER) and not os.path.exists(SILVER_FILE):
        logger.info(f"🚚 Migrating legacy silver file: {LEGACY_SILVER} -> {SILVER_FILE}")
        try:
            with open(LEGACY_SILVER, "r", encoding="utf-8") as f:
                records = json.load(f)
            with open(SILVER_FILE, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.rename(LEGACY_SILVER, LEGACY_SILVER + ".bak")
            logger.info("✅ Migration completed.")
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")


def save_to_silver(new_records):
    """Appends new records to the silver JSONL file."""
    os.makedirs(os.path.dirname(SILVER_FILE), exist_ok=True)
    try:
        with open(SILVER_FILE, 'a', encoding='utf-8') as f:
            for r in new_records:
                data = r.model_dump() if hasattr(r, 'model_dump') else r
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to append to silver: {e}")


# --- Core Pipeline Steps ---

def _load_data_state() -> Tuple[List[Dict], Set[str], Set[str]]:
    """Loads raw data, existing IDs, and deleted IDs."""
    all_raw = []
    if os.path.exists(BRONZE_RAW):
        with open(BRONZE_RAW, "r", encoding="utf-8") as f:
            for line in f:
                try: all_raw.append(json.loads(line))
                except Exception: continue
    
    processed_ids = set()
    if os.path.exists(SILVER_FILE):
        with open(SILVER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try: processed_ids.add(str(json.loads(line).get("id")))
                except Exception: continue
                
    deleted_ids = set()
    if os.path.exists(DELETED_IDS_FILE):
        try:
            with open(DELETED_IDS_FILE, "r", encoding="utf-8") as f:
                deleted_ids = {str(did) for did in json.load(f)}
        except Exception: pass
        
    return all_raw, processed_ids, deleted_ids


def _group_by_signature(to_process: List[Dict]) -> Dict[Tuple, List[Dict]]:
    """Groups transactions by their unique semantic signature."""
    groups = {}
    for record in to_process:
        sig = (
            record.get("operation", "").strip(),
            record.get("details", "").strip(),
            record.get("bank_category_hint", "").strip(),
            float(record.get("amount", 0.0))
        )
        groups.setdefault(sig, []).append(record)
    return groups


def _resolve_signature_result(sig: Tuple, instances: List[Dict], parser: TransactionParser) -> Optional[Dict]:
    """Attempts to resolve a signature via fast-path or prepares it for LLM."""
    operation, details, bank_cat, amount = sig
    direction = _determine_direction(f"{operation} {details}", amount=amount)
    
    # 1. Fast Path Mapping from Bank Profile
    mapping = getattr(parser.profile, 'category_mapping', {})
    lookup = {k.lower().strip(): v for k, v in mapping.items()}
    mapped_cat = lookup.get(bank_cat.lower().strip()) if bank_cat else None
    
    if mapped_cat:
        return {
            "is_fast": True,
            "result": {
                "category": mapped_cat,
                "merchant": "Mapped",
                "confidence": 1.0,
                "category_source": "fast_path_mapping",
                "reasoning": "Mapped via bank profile.",
                "duration": 0.01
            }
        }
    
    # 2. Prepare for LLM
    custom_p = getattr(parser.profile, 'cleaning_patterns', [])
    aliases = getattr(parser.profile, 'merchant_aliases', {})
    merchant = extract_merchant_from_excel(operation, details, custom_patterns=custom_p, aliases=aliases)
    
    text = f"Operation: {operation}\nDetails: {details}"
    if bank_cat: text += f"\nBank category: {bank_cat}"
    
    return {
        "is_fast": False,
        "llm_input": {
            "sig": sig,
            "text": text,
            "direction": direction,
            "merchant": merchant,
            "amount": amount
        }
    }


def run_certify():
    """Converts Silver JSONL to Gold CSV with normalization."""
    start_time = time.time()
    logger.info("🏅 PHASE: DATA CERTIFICATION")
    
    if not os.path.exists(SILVER_FILE):
        return

    records = []
    with open(SILVER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try: records.append(json.loads(line))
            except Exception: continue

    if not records:
        return

    for r in records:
        if not r.get("time"): r["time"] = "00:00"
        
        # Tipology Normalization
        tip = r.get("tipology", "").lower()
        if tip in ["expense", "refund"]: r["tipology"] = "Outgoing"
        elif tip == "salary": r["tipology"] = "Incoming"
            
        # Category Normalization
        cat = r.get("category")
        if cat in CATEGORY_NORMALIZATION_MAP:
            r["category"] = CATEGORY_NORMALIZATION_MAP[cat]

    records.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

    fieldnames = sorted({key for record in records for key in record.keys()})
    with open(GOLD_FILE, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({k: record.get(k, "") for k in fieldnames})

    logger.info(f"✅ CSV Generated: {GOLD_FILE} ({len(records)} rows)")


def run_processing(batch_size: int = 10, progress_callback=None):
    """Refactored main processing loop."""
    start_time = time.time()
    logger.info("🧠 PHASE: AI CATEGORIZATION (DECOMPOSED)")
    
    # 0. Pre-flight
    migrate_silver_to_jsonl()
    if not _check_llm_health():
        logger.error("❌ Ollama unreachable.")
        if progress_callback: progress_callback(0, 1, status="❌ Ollama Unreachable")
        return

    # 1. Load & Filter
    all_raw, processed_ids, deleted_ids = _load_data_state()
    to_process = [m for m in all_raw if str(m["id"]) not in processed_ids and str(m["id"]) not in deleted_ids]
    
    if not to_process:
        logger.info("✅ Everything already processed.")
        return
        
    parser = TransactionParser()
    groups = _group_by_signature(to_process)
    unique_sigs = list(groups.keys())
    total_tx = len(to_process)
    
    logger.info(f"Found {len(unique_sigs)} unique signatures in {total_tx} records.")
    
    total_processed = 0
    total_failed = 0
    all_stats = []

    # 2. Block Processing
    for i in range(0, len(unique_sigs), batch_size):
        sig_batch = unique_sigs[i:i + batch_size]
        results_map = {}
        to_llm = []
        
        # Prepare Block
        for sig in sig_batch:
            res = _resolve_signature_result(sig, groups[sig], parser)
            if res["is_fast"]:
                results_map[sig] = res["result"]
            else:
                to_llm.append(res["llm_input"])

        # Execute LLM Batch
        if to_llm:
            t0 = time.time()
            batch_results = parser.classify_batch([{"text": x["text"], "direction": x["direction"], "merchant": x["merchant"], "amount": x["amount"]} for x in to_llm])
            duration = (time.time() - t0) / len(to_llm)
            for idx, res in enumerate(batch_results):
                res["duration"] = duration
                results_map[to_llm[idx]["sig"]] = res

        # Persistence & Mapping
        new_entries = []
        for sig in sig_batch:
            res = results_map.get(sig)
            if not res:
                total_failed += 1
                continue
            
            instances = groups[sig]
            mode = _get_mode_string(res.get('category_source'))
            logger.info(f"   {mode} {res['merchant']:<20} | {res['category']:<20} (x{len(instances)})")
            
            op, det, bank_cat, amt = sig
            direction = _determine_direction(f"{op} {det}", amount=amt)
            final_amt = -abs(amt) if direction == "Outgoing" else abs(amt)

            for inst in instances:
                entry = {
                    "id": inst["id"], "date": inst.get("date", ""), "time": inst.get("time", "00:00"),
                    "tipology": direction, "merchant": res['merchant'], "category": res['category'],
                    "amount": final_amt, "original_operation": op, "original_details": det,
                    "source": "tabular", "category_source": res.get('category_source', 'llm_inference'),
                    "confidence": res.get('confidence', 0.0), "reasoning": res.get('reasoning', ''),
                }
                new_entries.append(entry)
                all_stats.append({"id": inst["id"], "merchant": res["merchant"], "duration": res.get("duration", 0), "mode": mode})

        if new_entries:
            save_to_silver(new_entries)
            parser.save_caches()
            total_processed += len(new_entries)
            if progress_callback: progress_callback(total_processed, total_tx)

    _print_recap(time.time() - start_time, all_stats, total_failed)


# --- Aliases ---
run_excel_processing = run_processing
