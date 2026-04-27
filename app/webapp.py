import streamlit as st
import time
import sys
from pathlib import Path
from datetime import date, timedelta

# Ensure local 'src' directory is available for legacy imports
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from api_client import api_client
from common import apply_theme, load_data, restore_state_from_url, sync_url_from_state, parse_date
from dashboard import render_dashboard
from data_editor import render_table
from settings import render_settings
from ui_services import filter_dataset, fetch_categories

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
    if st.sidebar.button("📊 Dashboard", width="stretch", key="nav_dashboard"):
        st.session_state["current_page"] = "Dashboard"
        sync_url_from_state()
    if st.sidebar.button("🔍 Data Explorer", width="stretch", key="nav_explorer"):
        st.session_state["current_page"] = "Table"
        sync_url_from_state()
    if st.sidebar.button("⚙️ Settings", width="stretch", key="nav_settings"):
        st.session_state["current_page"] = "Settings"
        sync_url_from_state()

    st.sidebar.markdown("---")

    # ETL Controls
    st.sidebar.subheader("📥 Data Ingestion")
    
    uploaded_file = st.sidebar.file_uploader("Upload PDF Bank Statement", type=["pdf"])
    
    if uploaded_file is not None:
        if st.sidebar.button("🚀 Process with AI", type="primary", width="stretch", key="btn_process_ai"):
            with st.sidebar.status("Uploading & Processing...", expanded=True) as status:
                st.write("📤 Uploading file...")
                profile_name = st.session_state.get("active_profile_name", "Default")
                result = api_client.upload_file(uploaded_file, profile_name)
                
                if result and "task_id" in result:
                    task_id = result["task_id"]
                    st.write(f"⚙️ Task started: {task_id}")
                    
                    # Polling
                    while True:
                        task_info = api_client.get_task_status(task_id)
                        if not task_info: break
                        
                        state = task_info.get("status")
                        if state == "SUCCESS":
                            status.update(label="✅ Processing Complete!", state="complete")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                            break
                        elif state == "FAILURE":
                            status.update(label="❌ Processing Failed", state="error")
                            st.error(task_info.get("info"))
                            break
                        else:
                            # Progress update
                            info = task_info.get("info") or {}
                            msg = info.get("msg", "Processing...")
                            st.write(f"🔄 {msg}")
                        
                        time.sleep(2)

    st.sidebar.markdown("---")
    # Global Filters & Dev Tools
    st.sidebar.checkbox("🔧 Show Advanced Settings", key="show_adv_global", on_change=sync_url_from_state)
    needs_review = st.sidebar.checkbox("⚠️ Needs Review", key="needs_review", help="Show only transactions with low confidence", on_change=sync_url_from_state)

    # Page Dispatcher
    if st.session_state["current_page"] == "Settings":
        render_settings()
    else:
        # Load Data
        data = load_data()
        
        if not data:
            st.info("Welcome to your personal BI assistant! Start by uploading your bank statement in the sidebar.")
            st.stop()
            
        st.markdown("<h1 style='text-align: center;'>Personal BI Assistant</h1>", unsafe_allow_html=True)
        
        # 1. Filter Logic & State Orchestration
        with st.container(border=True):
            tipologies = sorted({str(row.get("tipology", "")) for row in data if row.get("tipology")})
            tipologies.insert(0, "All")
            
            dates = [row.get("parsed_date") for row in data if row.get("parsed_date") is not None]
            min_date = min(dates) if dates else date.today()
            max_date = max(dates) if dates else date.today()
            
            # Setup defaults
            today = date.today()
            default_start = max(min_date, min(max_date, date(today.year, 1, 1)))
            default_end = max(min_date, min(max_date, today))

            col1, col2, col3 = st.columns([2, 2, 4])
            
            # Tipology Select
            t_index = tipologies.index(st.session_state.get("selected_tipology", "All")) if st.session_state.get("selected_tipology") in tipologies else 0
            selected_tipology = col2.selectbox("Tipology", tipologies, index=t_index, key="selected_tipology", on_change=sync_url_from_state)
            
            # Categories (Dynamic list via Service)
            available_categories = fetch_categories(selected_tipology)
            
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
                s_date = parse_date(st.session_state.get("selected_start_date")) or default_start
                e_date = parse_date(st.session_state.get("selected_end_date")) or default_end
                
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
