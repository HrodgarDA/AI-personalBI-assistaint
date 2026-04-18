import json
import os
import logging
from auto_bi.core.process import run_certify
from auto_bi.utils.config import SILVER_FILE, DELETED_IDS_FILE

USER_FEEDBACK_FILE = "data/user_feedback.json"



logger = logging.getLogger(__name__)

def log_feedback_and_update_silver(changes: list[dict], deleted_ids: list[str] = None):
    """
    Applies a list of modifications:
    1. Saves locally to user_feedback.json for AI tuning
    2. Modifies OR deletes specific records in the Silver layer
    3. Regenerates the Gold layer automatically
    """
    os.makedirs("data", exist_ok=True)
    deleted_ids = deleted_ids or []
    
    # --- 1. Log Feedback (only for changes/modifications) ---
    if changes:
        feedback_data = []
        if os.path.exists(USER_FEEDBACK_FILE):
            try:
                with open(USER_FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    feedback_data = json.load(f)
            except Exception:
                pass
                
        feedback_data.extend(changes)
        with open(USER_FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=4, ensure_ascii=False)
        
    # --- 2. Update Silver Layer ---
    if not os.path.exists(SILVER_FILE):
        return
        
    silver_records = []
    try:
        with open(SILVER_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    silver_records.append(json.loads(line))
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"Cannot read silver file: {e}")
        return

    # Handle Deletions: Filter out records that are in deleted_ids
    if deleted_ids:
        initial_count = len(silver_records)
        silver_records = [r for r in silver_records if str(r.get("original_msg_id", "")) not in deleted_ids]
        logger.info(f"Deleted {initial_count - len(silver_records)} records from silver.")
        
        # PERSIST TO BLACKLIST
        existing_blacklist = []
        if os.path.exists(DELETED_IDS_FILE):
            try:
                with open(DELETED_IDS_FILE, "r", encoding="utf-8") as f:
                    existing_blacklist = json.load(f)
            except Exception: pass
        
        # Add new deleted IDs, ensuring uniqueness
        updated_blacklist = list(set(existing_blacklist + deleted_ids))
        with open(DELETED_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(updated_blacklist, f, indent=4, ensure_ascii=False)

    changes_map = {str(c["msg_id"]): c for c in changes}
    
    # We also want to update the Merchant Catalogue if a category/merchant was corrected
    from auto_bi.utils.config import MERCHANT_CATALOGUE
    catalogue = {}
    if os.path.exists(MERCHANT_CATALOGUE):
        try:
            with open(MERCHANT_CATALOGUE, "r", encoding="utf-8") as f:
                catalogue = json.load(f)
        except Exception: pass

    catalogue_updated = False
    for record in silver_records:
        msg_id = str(record.get("original_msg_id", ""))
        if msg_id in changes_map:
            modification = changes_map[msg_id]
            
            # Update Merchant first if changed
            if "corrected_merchant" in modification:
                record["merchant"] = modification["corrected_merchant"]
                
            # Update Category
            if "corrected_category" in modification:
                record["category"] = modification["corrected_category"]
            
            # Update Amount
            if "corrected_amount" in modification:
                try:
                    record["amount"] = float(modification["corrected_amount"])
                except ValueError:
                    pass
            
            # If both merchant and category are now solid, add to catalogue for future bypass
            m_name = record.get("merchant")
            m_cat = record.get("category")
            if m_name and m_cat and m_name.lower() != "unknown" and m_cat != "Uncategorized":
                catalogue[m_name.lower().strip()] = m_cat
                catalogue_updated = True
                     
    # Atomic re-write for JSONL
    temp_file = SILVER_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        for r in silver_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(temp_file, SILVER_FILE)
        
    if catalogue_updated:
        with open(MERCHANT_CATALOGUE, "w", encoding="utf-8") as f:
            json.dump(catalogue, f, indent=2, ensure_ascii=False)
        
    # --- 3. Regenerate Gold CSV ---
    run_certify()
