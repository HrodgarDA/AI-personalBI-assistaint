import streamlit as st
import sys
import os
from pathlib import Path

# Ensure local 'src' directory is prioritized in sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from datetime import date, timedelta
from common import apply_theme, load_data, DATA_PATH, restore_state_from_url, sync_url_from_state, parse_date
from dashboard import render_dashboard
from data_editor import render_table
from settings import render_settings
from services import filter_dataset, get_available_categories
from auto_bi.core.ingestion import ingest_tabular_data, analyze_file_for_ui
from auto_bi.core.process import run_processing, run_certify
from auto_bi.utils.config import BRONZE_RAW
from auto_bi.utils.bank_profile import load_bank_profile, get_active_profile_name

@st.cache_data(show_spinner="Analyzing file...")
def cached_analyze_file(uploaded_file):
    """Cached wrapper for file analysis to prevent UI freezes."""
    return analyze_file_for_ui(uploaded_file)


def main():
    st.set_page_config(page_title="Personal BI Assistant", page_icon="📈", layout="wide")
    
    # Restore state from URL on first load
    restore_state_from_url()
    
    # Persistent State
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Dashboard"

    # Theme
    apply_theme()

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    
    # Navigation
    if st.sidebar.button("📊 Dashboard", width="stretch"):
        st.session_state["current_page"] = "Dashboard"
        sync_url_from_state()
    if st.sidebar.button("🔍 Data Explorer", width="stretch"):
        st.session_state["current_page"] = "Table"
        sync_url_from_state()
    if st.sidebar.button("⚙️ Settings", width="stretch"):
        st.session_state["current_page"] = "Settings"
        sync_url_from_state()

    st.sidebar.markdown("---")

    # ETL Controls
    st.sidebar.subheader("📥 Data Ingestion")
    
    uploaded_file = st.sidebar.file_uploader("Upload CSV/XLSX", type=["csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        stats = cached_analyze_file(uploaded_file)
        if "error" in stats:
            st.sidebar.error(stats["error"])
        else:
            with st.sidebar.container(border=True):
                st.markdown("##### 📊 File Analysis")
                c1, c2 = st.columns(2)
                c1.metric("Total Rows", stats["total_rows"])
                c2.metric("New Rows", stats["new_rows"])
                
                # Format time
                seconds = stats["estimated_seconds"]
                if seconds >= 60:
                    time_str = f"{int(seconds // 60)}m {int(seconds % 60)}s"
                else:
                    time_str = f"{int(seconds)}s"
                
                st.write(f"⏱️ **Estimated processing time:** {time_str}")
                if stats["new_rows"] > 0:
                    st.caption(f"Based on your recent speed: {stats['avg_speed']:.2f}s/tx")
    
    col_ing, col_proc = st.sidebar.columns(2)
    
    if col_ing.button("Archive", width="stretch", help="Securely save uploaded file to the data archive"):
        if uploaded_file is not None:
            progress_bar = st.progress(0)
            status_text = st.empty()
            def update_progress_archive(current, total):
                p = min(current / total, 1.0) if total > 0 else 1.0
                progress_bar.progress(p)
                status_text.write(f"**Progress:** {current}/{total} rows")
            with st.spinner("Archiving..."):
                rows_added = ingest_tabular_data(uploaded_file, progress_callback=update_progress_archive)
                if rows_added > 0:
                    st.success(f"Archived {rows_added} rows.")
                else:
                    st.info("No new rows found.")
        else:
            st.error("Upload file first!")

    if col_proc.button("Process", width="stretch", type="primary", help="Categorize transactions using AI"):
        if not Path(BRONZE_RAW).exists():
            st.warning("No data found. Archive a file first.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            def update_p(current, total):
                p = min(current / total, 1.0) if total > 0 else 1.0
                progress_bar.progress(p)
                status_text.write(f"**Progress:** {current}/{total} transactions")
            with st.spinner("Processing..."):
                run_processing(progress_callback=update_p)
                run_certify()
            st.success("Complete!")
            st.info("💡 **Mac Tip:** If you have many transactions, run `caffeinate` in your terminal to prevent the Mac from sleeping during processing.")
            st.cache_data.clear() # IMPORTANT: Clear cache to see new data
            st.rerun()

    st.sidebar.markdown("---")
    # Global Filters & Dev Tools
    st.sidebar.checkbox("🔧 Show Advanced Settings", key="show_adv_global", on_change=sync_url_from_state)
    needs_review = st.sidebar.checkbox("⚠️ Needs Review", key="needs_review", help="Show only transactions with confidence < 0.7", on_change=sync_url_from_state)

    # Page Dispatcher
    if st.session_state["current_page"] == "Settings":
        render_settings()
    else:
        # Load Data
        data = load_data()
        
        if not DATA_PATH.exists():
            st.info("Welcome to your personal BI assistaint! Start by uploading your bank statement in the sidebar.")
            st.stop()
        elif not data:
            st.warning("Il file dati è vuoto.")
            st.stop()
            
        st.markdown("<h1 style='text-align: center;'>Personal BI Assistant</h1>", unsafe_allow_html=True)
        
        # 1. Filter Logic & State Orchestration
        with st.container(border=True):
            tipologies = sorted({str(row.get("tipology", row.get("direction", ""))) for row in data if row.get("tipology", row.get("direction", ""))})
            tipologies.insert(0, "All")
            
            dates = [row.get("parsed_date") for row in data if row.get("parsed_date") is not None]
            min_date = min(dates) if dates else date.today()
            max_date = max(dates) if dates else date.today()
            
            # Setup defaults
            today = date.today()
            default_start = max(min_date, min(max_date, date(today.year, 1, 1)))
            default_end = max(min_date, min(max_date, today))
            if default_start > default_end: default_start, default_end = min_date, max_date

            col1, col2, col3 = st.columns([2, 2, 4])
            
            # Tipology Select
            t_index = tipologies.index(st.session_state.get("selected_tipology", "All")) if st.session_state.get("selected_tipology") in tipologies else 0
            selected_tipology = col2.selectbox("Tipology", tipologies, index=t_index, key="selected_tipology", on_change=sync_url_from_state)
            
            # Categories (Dynamic list via Service)
            profile = load_bank_profile(get_active_profile_name())
            available_categories = get_available_categories(data, profile, selected_tipology)
            
            # Mutual Exclusive "All" Logic
            if "prev_cats" not in st.session_state: st.session_state.prev_cats = ["All"]
            if not st.session_state.get("cat_ms"): st.session_state.cat_ms = ["All"]
            
            def handle_cat_change():
                new = st.session_state.cat_ms
                if not new: st.session_state.cat_ms = ["All"]
                elif "All" in new and len(new) > 1:
                    st.session_state.cat_ms = [c for c in new if c != "All"] if "All" in st.session_state.prev_cats else ["All"]
                st.session_state.prev_cats = st.session_state.cat_ms
                sync_url_from_state()

            col1.multiselect("Category", available_categories, key="cat_ms", on_change=handle_cat_change)
            
            # Date Range Slider
            if min_date < max_date:
                s_date = parse_date(st.session_state.get("selected_start_date")) if isinstance(st.session_state.get("selected_start_date"), str) else st.session_state.get("selected_start_date", default_start)
                e_date = parse_date(st.session_state.get("selected_end_date")) if isinstance(st.session_state.get("selected_end_date"), str) else st.session_state.get("selected_end_date", default_end)
                
                selected_dates = col3.slider("Date Range", min_value=min_date, max_value=max_date, value=(s_date, e_date), format="DD/MM/YYYY", key="date_range_slider")
                st.session_state.selected_start_date, st.session_state.selected_end_date = selected_dates
                sync_url_from_state()
            else:
                col3.slider("Date Range", min_value=min_date, max_value=max_date + timedelta(days=1), value=(min_date, min_date), disabled=True)
                selected_dates = (min_date, min_date)

        start_date, end_date = selected_dates
        
        # 2. Dataset Processing via Service
        filtered = filter_dataset(
            data=data,
            selected_tipology=selected_tipology,
            selected_categories=st.session_state.cat_ms,
            start_date=start_date,
            end_date=end_date,
            needs_review=needs_review
        )

        st.markdown("---")

        if st.session_state["current_page"] == "Dashboard":
            render_dashboard(filtered)
        elif st.session_state["current_page"] == "Table":
            render_table(filtered, len(data))

if __name__ == "__main__":
    main()
