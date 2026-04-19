from datetime import date
from typing import List, Dict, Any, Set, Tuple
from auto_bi.utils.bank_profile import BankProfile

def get_available_categories(data: List[Dict], profile: BankProfile, selected_tipology: str) -> List[str]:
    """Computes the list of available categories for filtering, prioritizing profile categories."""
    profile_cats = set(profile.outgoing_categories + profile.incoming_categories)
    
    if selected_tipology == "All":
        data_cats = {str(row.get("category", "")) for row in data if row.get("category", "")}
    else:
        data_cats = {
            str(row.get("category", "")) for row in data 
            if row.get("tipology", row.get("direction", "")) == selected_tipology and row.get("category", "")
        }
    
    # Intersection: categories that are in both profile and data
    official_present = sorted(list(profile_cats.intersection(data_cats)))
    # Extras: categories in data but NOT in profile
    extras = sorted(list(data_cats - profile_cats))
    
    available_categories = ["All"] + official_present
    if extras:
        available_categories += extras
    
    return available_categories

def filter_dataset(
    data: List[Dict], 
    selected_tipology: str, 
    selected_categories: List[str], 
    start_date: date, 
    end_date: date, 
    needs_review: bool
) -> List[Dict]:
    """Applies multiple filters to the transaction dataset."""
    filtered = data
    
    # 1. Tipology Filter
    if selected_tipology != "All":
        filtered = [row for row in filtered if row.get("tipology", row.get("direction")) == selected_tipology]
        
    # 2. Category Filter
    if selected_categories and "All" not in selected_categories:
        filtered = [row for row in filtered if row.get("category") in selected_categories]

    # 3. Date Filter
    filtered = [
        row for row in filtered 
        if row.get("parsed_date") is not None and start_date <= row["parsed_date"] <= end_date
    ]

    # 4. Review Filter
    if needs_review:
        filtered = [row for row in filtered if row.get("confidence", 1.0) < 0.7]

    # 5. Sorting (Descending by date and time)
    filtered.sort(key=lambda x: (x.get("parsed_date") or date.min, x.get("time", "00:00")), reverse=True)
    
    return filtered
