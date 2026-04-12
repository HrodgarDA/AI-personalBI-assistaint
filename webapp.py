import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from src.graph import plot_amount_over_time, plot_category_pie, plot_category_totals
from src.main import run_ingestion, run_processing, run_certify
from src.feedback import log_feedback_and_update_silver

DATA_PATH = Path(__file__).resolve().parent / "data" / "gold_certified_data.csv"
DATE_FORMAT = "%Y-%m-%d"


def apply_theme():
    css = """
    <style>
        [data-testid="stAppViewContainer"] { background-color: #111827 !important; }
        [data-testid="stHeader"] { background-color: rgba(17, 24, 39, 0.8) !important; }
        [data-testid="stSidebar"] { background-color: #1F2937 !important; }
        h1, h2, h3, h4, p, label, .stMarkdown, .stText { color: #F9FAFB !important; }
        div[data-testid="stMetricValue"] { color: #F9FAFB !important; display: flex; justify-content: center; }
        div[data-testid="stMetricLabel"] { color: #F9FAFB !important; display: flex; justify-content: center; }
        div[data-testid="stVerticalBlockBorderWrapper"] { border-color: #374151 !important; border-radius: 12px; background-color: #1F2937 !important; }
        button[kind="secondary"] { background-color: #1F2937 !important; color: #F9FAFB !important; border-color: #374151 !important; }
        button[kind="secondary"]:hover { border-color: #F9FAFB !important; color: #F9FAFB !important; background-color: #374151 !important; }
        button[kind="primary"], button[kind="primary"] * { color: #111827 !important; }
        span[data-baseweb="tag"] { color: #111827 !important; }
        span[data-baseweb="tag"] svg { color: #111827 !important; }
        /* Partial Canvas Wrapper Styling */
        [data-testid="stDataFrameResizable"] { background-color: #1F2937 !important; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def parse_date(value: str):
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except (TypeError, ValueError):
        return None


def load_data(path: Path):
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


def render_dashboard(data):
    st.markdown("<h1 style='text-align: center;'>💸 Personal BI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Monitor and analyze your spending trends with advanced analytics.</p><br>", unsafe_allow_html=True)

    valid_amounts = [row.get("amount", 0) for row in data if isinstance(row.get("amount"), (int, float))]
    total_amount = sum(valid_amounts)
    num_tx = len(data)
    
    cat_totals = defaultdict(float)
    for row in data:
        amount = row.get("amount")
        cat = row.get("category")
        if cat and isinstance(amount, (int, float)):
             cat_totals[cat] += amount
    top_cat = max(cat_totals.items(), key=lambda x: x[1])[0] if cat_totals else "N/A"

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Transactions", num_tx)
        col2.metric("Total Spending", f"€ {total_amount:,.2f}")
        avg_tx = total_amount / num_tx if num_tx else 0.0
        col3.metric("Avg Transaction", f"€ {avg_tx:,.2f}")
        col4.metric("Top Category", top_cat)

    st.markdown("<br>", unsafe_allow_html=True)

    g_col1, g_col2, g_col3 = st.columns([1,1,1])
    if "time_freq" not in st.session_state:
        st.session_state["time_freq"] = "M"
        
    freq = st.session_state["time_freq"]
    with g_col1:
        if st.button("Daily", width='stretch', type="primary" if freq=="D" else "secondary"):
            st.session_state["time_freq"] = "D"
            st.rerun()
    with g_col2:
        if st.button("Weekly", width='stretch', type="primary" if freq=="W" else "secondary"):
            st.session_state["time_freq"] = "W"
            st.rerun()
    with g_col3:
        if st.button("Monthly", width='stretch', type="primary" if freq=="M" else "secondary"):
            st.session_state["time_freq"] = "M"
            st.rerun()

    st.markdown("<h3 style='text-align: center;'>Total Expenses Over Time</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(plot_amount_over_time(data, freq=st.session_state["time_freq"]), width='stretch')

    st.markdown("<h3 style='text-align: center;'>Distribution by Category</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(plot_category_pie(data), width='stretch')

    st.markdown("<h3 style='text-align: center;'>Total Amount by Category</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(plot_category_totals(data), width='stretch')

    st.caption("Insights generated by Auto-BI Assistant.")


def render_table(filtered, total_len):
    st.markdown("<h1 style='text-align: center;'>🗂️ Data Explorer</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Filter and view your raw certified data.</p><br>", unsafe_allow_html=True)

    st.write(f"**Showing {len(filtered)} of {total_len} transactions**")
    
    col_config = {
        "parsed_date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "category": st.column_config.TextColumn("Category"),
        "merchant": st.column_config.TextColumn("Merchant"),
        "amount": st.column_config.NumberColumn("Amount", format="€ %.2f"),
        "tipology": st.column_config.TextColumn("Tipology"),
        "reasoning": st.column_config.TextColumn("Reasoning"),
        "confidence": None,
        "original_msg_id": None,
        "date": None,
        "time": None,
        "direction": None, # Ignore the old direction field if present
    }

    edited_data = st.data_editor(
        filtered,
        width='stretch',
        hide_index=True,
        height=700,
        column_order=["parsed_date", "category", "merchant", "amount", "tipology", "reasoning"],
        column_config=col_config,
        disabled=["parsed_date", "confidence", "reasoning", "tipology", "merchant"]
    )

    if st.button("💾 Save Changes", type="primary"):
        changes = []
        for old_row, new_row in zip(filtered, edited_data):
            cat_changed = old_row.get("category") != new_row.get("category")
            amt_changed = old_row.get("amount") != new_row.get("amount")
            
            if cat_changed or amt_changed:
                changes.append({
                    "msg_id": old_row.get("original_msg_id"),
                    "original_category": old_row.get("category"),
                    "corrected_category": new_row.get("category"),
                    "original_amount": old_row.get("amount"),
                    "corrected_amount": new_row.get("amount"),
                })
        
        if changes:
            log_feedback_and_update_silver(changes)
            st.success(f"Successfully applied {len(changes)} modifications.")
            st.rerun()
        else:
            st.info("No modifications detected.")


def main():
    st.set_page_config(page_title="Personal BI Assistant", page_icon="📈", layout="wide")

    # Stato persistente
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Dashboard"

    # Sidebar settings
    st.sidebar.title("Navigation")
    
    if st.sidebar.button("📊 Dashboard", width='stretch'):
        st.session_state["current_page"] = "Dashboard"
    if st.sidebar.button("📋 Table", width='stretch'):
        st.session_state["current_page"] = "Table"
    
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("⚙️ ETL Controls")
    if st.sidebar.button("📥 Download Emails", width='stretch'):
        with st.spinner("Downloading emails..."):
            run_ingestion()
        st.sidebar.success("Emails downloaded!")
        
    if st.sidebar.button("🧠 Process Transactions", width='stretch'):
        with st.spinner("LLM Processing in progress..."):
            run_processing()
            run_certify()
        st.sidebar.success("Processing complete!")
        st.rerun()

    st.sidebar.markdown("---")
    
    # App is forced to Dark Mode as per user request
    apply_theme()

    if not DATA_PATH.exists():
        st.sidebar.error(f"File not found: {DATA_PATH}")
        return

    data = load_data(DATA_PATH)
    if not data:
        st.sidebar.warning("The file exists but does not contain rows to display.")
        return

    st.markdown("<h2 style='text-align: center;'>Global Filters</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        categories = sorted({str(row.get("category", "")) for row in data if row.get("category", "")})
        categories.insert(0, "All")
        tipologies = sorted({str(row.get("tipology", row.get("direction", ""))) for row in data if row.get("tipology", row.get("direction", ""))})
        tipologies.insert(0, "All")
        
        dates = [row.get("parsed_date") for row in data if row.get("parsed_date") is not None]
        min_date = min(dates) if dates else date.today()
        max_date = max(dates) if dates else date.today()
        today = date.today()
        start_of_year = date(today.year, 1, 1)
        default_start = max(start_of_year, min_date)
        default_end = min(today, max_date)

        col1, col2, col3 = st.columns([1,1,2])
        selected_categories = col1.multiselect("Category", categories, default=["All"])
        selected_tipologies = col2.multiselect("Tipology", tipologies, default=["All"])
        selected_dates = col3.slider("Date Range", min_value=min_date, max_value=max_date, value=(default_start, default_end), format="DD/MM/YYYY")

    start_date, end_date = selected_dates if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2 else (selected_dates, selected_dates)

    filtered = data
    if selected_categories and "All" not in selected_categories:
        filtered = [row for row in filtered if row.get("category") in selected_categories]
    if selected_tipologies and "All" not in selected_tipologies:
        filtered = [row for row in filtered if row.get("tipology", row.get("direction")) in selected_tipologies]

    filtered = [row for row in filtered if row.get("parsed_date") is not None and start_date <= row["parsed_date"] <= end_date]

    st.markdown("---")

    if st.session_state["current_page"] == "Dashboard":
        render_dashboard(filtered)
    else:
        render_table(filtered, len(data))


if __name__ == "__main__":
    main()
