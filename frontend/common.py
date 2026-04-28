import streamlit as st
from datetime import datetime
from api_client import api_client

DATE_FORMAT = "%Y-%m-%d"

def restore_state_from_url():
    """Reads st.query_params and populates st.session_state on initial load."""
    params = st.query_params
    
    if "page" in params and "current_page" not in st.session_state:
        st.session_state["current_page"] = params["page"]
    
    # Global toggles - Only set if not already in session state (to avoid widget conflicts)
    if "adv" in params and "show_adv_global" not in st.session_state:
        st.session_state["show_adv_global"] = params["adv"].lower() == "true"
    if "review" in params and "needs_review" not in st.session_state:
        st.session_state["needs_review"] = params["review"].lower() == "true"
        
    # Filters
    if "tx_type" in params and "selected_tx_type" not in st.session_state:
        st.session_state["selected_tx_type"] = params["tx_type"]
    if "cats" in params and "cat_ms" not in st.session_state:
        st.session_state["cat_ms"] = params.get_all("cats")
    if "start" in params and "selected_start_date" not in st.session_state:
        st.session_state["selected_start_date"] = params["start"]
    if "end" in params and "selected_end_date" not in st.session_state:
        st.session_state["selected_end_date"] = params["end"]

def sync_url_from_state():
    """Writes relevant session_state variables to st.query_params."""
    updates = {}
    
    if "current_page" in st.session_state:
        updates["page"] = st.session_state["current_page"]
        
    if "show_adv_global" in st.session_state:
        updates["adv"] = str(st.session_state["show_adv_global"]).lower()
    if "needs_review" in st.session_state:
        updates["review"] = str(st.session_state["needs_review"]).lower()
        
    if "cat_ms" in st.session_state:
        updates["cats"] = st.session_state["cat_ms"]
        
    if "selected_tx_type" in st.session_state:
        updates["tx_type"] = st.session_state["selected_tx_type"]
        
    # Specific date handling if they are objects (from slider/picker)
    if "selected_start_date" in st.session_state:
        val = st.session_state["selected_start_date"]
        updates["start"] = val.isoformat() if hasattr(val, "isoformat") else str(val)
    if "selected_end_date" in st.session_state:
        val = st.session_state["selected_end_date"]
        updates["end"] = val.isoformat() if hasattr(val, "isoformat") else str(val)
        
    st.query_params.from_dict(updates)

def apply_theme():
    css = """
    <style>
        [data-testid="stAppViewContainer"] { background-color: #111827 !important; }
        [data-testid="stHeader"] { background-color: rgba(17, 24, 39, 0.8) !important; }
        [data-testid="stSidebar"] { background-color: #1F2937 !important; }
        h1, h2, h3, h4, p, label, .stMarkdown, .stText { color: #F9FAFB !important; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; text-align: center; }
        [data-testid="stMetricLabel"] > div { justify-content: center !important; }
        [data-testid="stMetricValue"] > div { justify-content: center !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { text-align: center !important; width: 100%; display: block; }
        div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #374151 !important; border-radius: 12px; background-color: #1F2937 !important; }
        
        /* Aggressive styling for all Sidebar Buttons */
        [data-testid="stSidebar"] button[data-testid^="stBaseButton"] {
            display: flex !important;
            justify-content: center !important;
            text-align: center !important;
            width: 100% !important;
            background-color: #111827 !important; /* Page Background Color */
            color: white !important;
            border: 1px solid #374151 !important;
            border-radius: 8px !important;
            margin-bottom: 5px !important;
        }
        
        [data-testid="stSidebar"] button[data-testid^="stBaseButton"]:hover {
            background-color: #1F2937 !important;
            border-color: #F9FAFB !important;
            color: white !important;
        }

        /* Target the internal text container for alignment */
        [data-testid="stSidebar"] button[data-testid^="stBaseButton"] * {
            text-align: center !important;
            color: white !important;
            justify-content: center !important;
        }

        [data-testid="stSidebar"] button[data-testid^="stBaseButton"] p {
            margin: 0 !important;
            width: 100% !important;
            font-weight: 500 !important;
        }

        /* Match expander/summary header to the same style */
        [data-testid="stSidebar"] [data-testid="stExpander"] summary,
        [data-testid="stSidebar"] [data-testid="stExpander"] div[role="button"] {
            background-color: #111827 !important;
            border-radius: 8px !important;
            color: white !important;
            margin-bottom: 5px !important;
            border: 1px solid #374151 !important;
        }
        
        [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
            background-color: #1F2937 !important;
        }

        /* Improve readability on widgets with light backgrounds (e.g., primary buttons, multiselect tags) */
        button[kind="primary"] p,
        span[data-baseweb="tag"],
        span[data-baseweb="tag"] svg,
        div[data-baseweb="select"] {
            color: #111827 !important;
            fill: #111827 !important;
            font-weight: 600 !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def parse_date(value: str):
    if not value: return None
    if isinstance(value, datetime): return value.date()
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except (TypeError, ValueError):
        return None

@st.cache_data
def load_data():
    transactions = api_client.get_transactions()
    
    # Map API fields to UI fields
    mapped_rows = []
    for tx in transactions:
        row = {
            "id": tx.get("id"),
            "amount": tx.get("amount"),
            "date": tx.get("date"),
            "transaction_type": tx.get("transaction_type"),
            "category_id": tx.get("category_id"),
            "merchant_id": tx.get("merchant_id"),
            "original_operation": tx.get("original_operation"),
            "original_details": tx.get("original_details"),
            "reasoning": tx.get("ai_reasoning"),
            "confidence": tx.get("confidence", 0.0),
            "parsed_date": parse_date(tx.get("date"))
        }
        mapped_rows.append(row)
    return mapped_rows
