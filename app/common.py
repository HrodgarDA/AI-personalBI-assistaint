import csv
import logging
from datetime import datetime
from pathlib import Path
import streamlit as st
from auto_bi.utils.config import GOLD_FILE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DATA_PATH = Path(GOLD_FILE)
DATE_FORMAT = "%Y-%m-%d"

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
        div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #374151 !important; border-radius: 12px; background-color: #1F2937 !important; }
        
        /* Aggressive styling for all Sidebar Buttons */
        [data-testid="stSidebar"] button[data-testid^="stBaseButton"] {
            display: flex !important;
            justify-content: flex-start !important;
            text-align: left !important;
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
            text-align: left !important;
            color: white !important;
            justify-content: flex-start !important;
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
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except (TypeError, ValueError):
        return None

def load_data(path: Path = DATA_PATH):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        rows = list(reader)

    for row in rows:
        if "amount" in row:
            try:
                row["amount"] = float(row["amount"])
            except (ValueError, TypeError):
                pass
        if "confidence" in row:
            try:
                row["confidence"] = float(row["confidence"])
            except (ValueError, TypeError):
                pass
        row["parsed_date"] = parse_date(row.get("date"))
    return rows
