import os
import json
import logging
import time
from auto_bi.core.extractor import TransactionParser
from auto_bi.utils.config import BRONZE_RAW, SILVER_FILE

logger = logging.getLogger(__name__)

def run_error_recovery(progress_callback=None):
    """
    Identifies 'Uncategorized' or 'error' records in Silver and re-processes them
    using the specialized Recovery Prompt. 
    Also 'repairs' older records by fetching missing original data from Bronze.
    """
    try:
        from auto_bi.utils.prompts import RECOVERY_CLASSIFICATION_TEMPLATE
    except ImportError:
        # Fallback to local copy if streamlit reloading fails to see the new constant
        RECOVERY_CLASSIFICATION_TEMPLATE = (
            "You are a senior financial analyst. The following transactions previously failed to be categorized. "
            "Your goal is to perform a DEEP ANALYSIS and force a match with the existing categories. "
            "DO NOT USE 'Uncategorized' if there is ANY reasonable match.\n\n"
            "AVAILABLE CATEGORIES:\n"
            "{categories_block}\n\n"
            "TASK:\n"
            "For each transaction in the provided list:\n"
            "1. Extract the clean Merchant name (e.g., 'Amazon', 'Lidl').\n"
            "2. Assign the best Category from the list.\n"
            "3. Provide brief reasoning explaining why this is the best match despite previous failure.\n\n"
            "SYSTEM RULES:\n"
            "- Output ONLY a JSON object with a 'results' field containing the list of result objects.\n"
            "- Maintain the exact order of the input list.\n"
            "{custom_user_rules}\n\n"
            "FAILED TRANSACTIONS TO RE-PROCESS:\n"
            "{transactions_block}"
        )
    
    if not os.path.exists(SILVER_FILE):
        return 0, 0
        
    start_time = time.time()
    logger.info("=" * 40)
    logger.info("🚑 PHASE: ERROR RECOVERY & REPAIR")
    logger.info("=" * 40)
    
    with open(SILVER_FILE, 'r', encoding='utf-8') as f:
        silver_data = json.load(f)
    
    # Load Bronze data for retroactive repair
    bronze_map = {}
    if os.path.exists(BRONZE_RAW):
        with open(BRONZE_RAW, 'r', encoding='utf-8') as bf:
            for line in bf:
                try: 
                    item = json.loads(line)
                    bronze_map[str(item.get('id'))] = item
                except Exception: continue

    # Indices of records to retry or repair
    to_retry_indices = []
    repair_count = 0
    for i, r in enumerate(silver_data):
        is_uncat = r.get("category") == "Uncategorized"
        is_error = r.get("category_source") == "error"
        
        if is_uncat or is_error:
            # RETROACTIVE REPAIR: Fill missing original data from Bronze
            if not r.get("original_operation") or not r.get("reasoning"):
                b_item = bronze_map.get(str(r.get("id")))
                if b_item:
                    op = b_item.get("operation", "")
                    det = b_item.get("details", "")
                    r["original_operation"] = op
                    r["original_details"] = det
                    # If reasoning was empty, fill with raw info for visibility
                    if not r.get("reasoning"):
                        r["reasoning"] = f"{op} | {det}"
                    repair_count += 1
            
            to_retry_indices.append(i)
            
    if repair_count > 0:
        logger.info(f"🔧 Repaired {repair_count} older records with missing original context.")

    if not to_retry_indices:
        if repair_count > 0:
            with open(SILVER_FILE, 'w', encoding='utf-8') as f:
                json.dump(silver_data, f, indent=4, ensure_ascii=False)
        logger.info("✅ No errors found to recover.")
        return 0, 0
        
    logger.info(f"🧐 Found {len(to_retry_indices)} records to re-process.")
    
    # FORCE RELOAD of extractor and prompts to bypass Streamlit stale cache
    import importlib
    import auto_bi.core.extractor
    import auto_bi.utils.prompts
    try:
        importlib.reload(auto_bi.utils.prompts)
        importlib.reload(auto_bi.core.extractor)
        from auto_bi.core.extractor import TransactionParser
        logger.info("🔄 Modules reloaded successfully to ensure latest signatures.")
    except Exception as e:
        logger.warning(f"Could not reload modules: {e}")
        from auto_bi.core.extractor import TransactionParser

    batch_input = []
    for idx in to_retry_indices:
        r = silver_data[idx]
        batch_input.append({
            "text": f"{r.get('original_operation', '')} {r.get('original_details', '')}",
            "direction": r.get("tipology", "Outgoing"),
            "merchant": None, # Force re-extraction
            "amount": abs(r.get("amount", 0.0)),
            "original_operation": r.get("original_operation", ""),
            "original_details": r.get("original_details", ""),
            "id": r.get("id")
        })
        
    parser = TransactionParser()
    
    # Logic check: if system_template is still missing despite reload, fallback to standard call
    import inspect
    sig = inspect.signature(parser.classify_batch)
    if 'system_template' in sig.parameters:
        results = parser.classify_batch(batch_input, system_template=RECOVERY_CLASSIFICATION_TEMPLATE)
    else:
        logger.warning("⚠️ system_template parameter still missing in classify_batch signature. Calling without it.")
        results = parser.classify_batch(batch_input)
    
    recovered_count = 0
    for i, res in enumerate(results):
        if res.get("category") != "Uncategorized":
            idx = to_retry_indices[i]
            silver_data[idx].update({
                "merchant": res['merchant'],
                "category": res['category'],
                "confidence": res.get('confidence', 0.5),
                "reasoning": res.get('reasoning', ''),
                "category_source": "recovery_inference"
            })
            recovered_count += 1
            
    with open(SILVER_FILE, 'w', encoding='utf-8') as f:
        json.dump(silver_data, f, indent=4, ensure_ascii=False)
        
    duration = time.time() - start_time
    logger.info(f"✨ Recovery complete: {recovered_count}/{len(to_retry_indices)} records fixed in {duration:.2f}s")
    
    return recovered_count, len(to_retry_indices)
