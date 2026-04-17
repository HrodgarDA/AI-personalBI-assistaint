import json
import os
import logging
from auto_bi.core.process import run_certify
from auto_bi.utils.config import SILVER_FILE

USER_FEEDBACK_FILE = "data/user_feedback.json"



logger = logging.getLogger(__name__)

def log_feedback_and_update_silver(changes: list[dict]):
    """
    Applies a list of modifications:
    1. Saves locally to user_feedback.json for AI tuning
    2. Modifies the specific record in the Silver layer
    3. Regenerates the Gold layer automatically
    """
    os.makedirs("data", exist_ok=True)
    
    # --- 1. Log Feedback ---
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
        
    try:
        with open(SILVER_FILE, "r", encoding="utf-8") as f:
            silver_records = json.load(f)
    except Exception as e:
        logger.error(f"Cannot read silver file: {e}")
        return
        
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
                    
    with open(SILVER_FILE, "w", encoding="utf-8") as f:
        json.dump(silver_records, f, indent=4, ensure_ascii=False)
        
    if catalogue_updated:
        with open(MERCHANT_CATALOGUE, "w", encoding="utf-8") as f:
            json.dump(catalogue, f, indent=2, ensure_ascii=False)
        
    # --- 3. Regenerate Gold CSV ---
    run_certify()
