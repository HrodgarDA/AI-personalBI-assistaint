from datetime import date
from typing import List, Dict, Any
import streamlit as st
from api_client import api_client

def fetch_categories(selected_tipology: str = "All") -> List[str]:
    """Fetches categories from the API and filters based on tipology if needed."""
    categories = api_client.get_categories()
    
    if not categories:
        return ["All"]
    
    # Filter by tipology if requested
    if selected_tipology == "Incoming":
        filtered_cats = [c["id"] for c in categories if c.get("is_income")]
    elif selected_tipology == "Outgoing":
        filtered_cats = [c["id"] for c in categories if not c.get("is_income")]
    else:
        filtered_cats = [c["id"] for c in categories]
    
    return ["All"] + sorted(filtered_cats)

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
        filtered = [row for row in filtered if row.get("tipology") == selected_tipology]
        
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

    # 5. Sorting (Descending by date)
    filtered.sort(key=lambda x: x.get("parsed_date") or date.min, reverse=True)
    
    return filtered
