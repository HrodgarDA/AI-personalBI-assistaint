import streamlit as st
import sys
import os
from pathlib import Path

# Ensure local 'src' directory is prioritized in sys.path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from datetime import date
from common import apply_theme, load_data, DATA_PATH, restore_state_from_url, sync_url_from_state, parse_date
from dashboard import render_dashboard
from data_editor import render_table
from settings import render_settings
from auto_bi.core.ingestion import ingest_tabular_data, analyze_file_for_ui
from auto_bi.core.process import run_processing, run_certify
from auto_bi.utils.config import BRONZE_RAW

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
        
        # Filter Logic (Shared between Dashboard and Table)
        with st.container(border=True):
            tipologies = sorted({str(row.get("tipology", row.get("direction", ""))) for row in data if row.get("tipology", row.get("direction", ""))})
            tipologies.insert(0, "All")
            
            dates = [row.get("parsed_date") for row in data if row.get("parsed_date") is not None]
            min_date = min(dates) if dates else date.today()
            max_date = max(dates) if dates else date.today()
            today = date.today()
            start_of_year = date(today.year, 1, 1)
            
            # Ensure defaults are within the actual data range
            default_start = max(min_date, min(max_date, start_of_year))
            default_end = max(min_date, min(max_date, today))
            
            if default_start > default_end:
                default_start, default_end = min_date, max_date

            col1, col2, col3 = st.columns([2, 2, 4])
            
            # Tipology (Single Select)
            if "selected_tipology" not in st.session_state:
                st.session_state.selected_tipology = "All"
            
            try:
                t_index = tipologies.index(st.session_state.selected_tipology)
            except ValueError:
                t_index = 0

            selected_tipology = col2.selectbox(
                "Tipology", 
                tipologies, 
                index=t_index, 
                key="selected_tipology", 
                on_change=sync_url_from_state
            )
            
            # Dynamic Categories (Smart Filter + Profile Prioritization)
            from auto_bi.utils.bank_profile import load_bank_profile, get_active_profile_name
            p_name = get_active_profile_name()
            profile = load_bank_profile(p_name)
            
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
            # Extras: categories in data but NOT in profile (the "duplicates" or old names)
            extras = sorted(list(data_cats - profile_cats))
            
            available_categories = ["All"] + official_present
            if extras:
                available_categories += extras # Keep them at the end
            
            # Logic to make "All" mutually exclusive
            if "prev_cats" not in st.session_state:
                st.session_state.prev_cats = ["All"]
            if "cat_ms" not in st.session_state or not st.session_state.cat_ms:
                st.session_state.cat_ms = ["All"]
            
            def handle_cat_change():
                new_selection = st.session_state.cat_ms
                if not new_selection:
                    st.session_state.cat_ms = ["All"]
                elif "All" in new_selection and len(new_selection) > 1:
                    all_was_there = "All" in st.session_state.get("prev_cats", [])
                    if all_was_there:
                        st.session_state.cat_ms = [c for c in new_selection if c != "All"]
                    else:
                        st.session_state.cat_ms = ["All"]
                st.session_state.prev_cats = st.session_state.cat_ms
                sync_url_from_state()

            # Sanitize against available categories
            sanitized = [c for c in st.session_state.cat_ms if c in available_categories]
            if not sanitized:
                sanitized = ["All"]
            st.session_state.cat_ms = sanitized

            selected_categories = col1.multiselect(
                "Category", 
                available_categories, 
                key="cat_ms",
                on_change=handle_cat_change,
            )
            
            if min_date < max_date:
                # Restore dates from URL strings if present
                if "selected_start_date" in st.session_state and isinstance(st.session_state.selected_start_date, str):
                    st.session_state.selected_start_date = parse_date(st.session_state.selected_start_date) or default_start
                if "selected_end_date" in st.session_state and isinstance(st.session_state.selected_end_date, str):
                    st.session_state.selected_end_date = parse_date(st.session_state.selected_end_date) or default_end
                
                # Double check bounds
                s_date = st.session_state.get("selected_start_date", default_start)
                e_date = st.session_state.get("selected_end_date", default_end)
                
                selected_dates = col3.slider(
                    "Date Range", 
                    min_value=min_date, 
                    max_value=max_date, 
                    value=(s_date, e_date), 
                    format="DD/MM/YYYY",
                    key="date_range_slider"
                )
                # Update individual keys for sync
                st.session_state.selected_start_date = selected_dates[0]
                st.session_state.selected_end_date = selected_dates[1]
                sync_url_from_state()
            else:
                from datetime import timedelta
                fake_max = min_date + timedelta(days=1)
                col3.slider("Date Range", min_value=min_date, max_value=fake_max, value=(min_date, min_date), format="DD/MM/YYYY", disabled=True, help="Only one day of data available")
                selected_dates = (min_date, min_date)

        start_date, end_date = selected_dates if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2 else (selected_dates, selected_dates)
        
        # Filtering
        filtered = data
        if selected_tipology != "All":
            filtered = [row for row in filtered if row.get("tipology", row.get("direction")) == selected_tipology]
            
        if selected_categories and "All" not in selected_categories:
            filtered = [row for row in filtered if row.get("category") in selected_categories]

        filtered = [row for row in filtered if row.get("parsed_date") is not None and start_date <= row["parsed_date"] <= end_date]

        if needs_review:
            filtered = [row for row in filtered if row.get("confidence", 1.0) < 0.7]

        # Sorting: Default to descending by date (most recent first)
        filtered.sort(key=lambda x: (x.get("parsed_date") or date.min, x.get("time", "00:00")), reverse=True)

        st.markdown("---")

        if st.session_state["current_page"] == "Dashboard":
            render_dashboard(filtered)
        elif st.session_state["current_page"] == "Table":
            render_table(filtered, len(data))

if __name__ == "__main__":
    main()
