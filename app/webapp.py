import streamlit as st
from datetime import date
from pathlib import Path
from common import apply_theme, load_data, DATA_PATH
from dashboard import render_dashboard
from data_editor import render_table
from settings import render_settings
from auto_bi.core.ingestion import run_ingestion, ingest_excel
from auto_bi.core.process import run_processing, run_excel_processing, run_certify
from auto_bi.utils.config import BRONZE_EXCEL

def main():
    st.set_page_config(page_title="Personal BI Assistant", page_icon="📈", layout="wide")
    
    # Persistent State
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Dashboard"

    # Theme
    apply_theme()

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    
    # Navigation Buttons
    if st.sidebar.button("📊 Dashboard", width="stretch"):
        st.session_state["current_page"] = "Dashboard"
    if st.sidebar.button("🔍 Data Explorer", width="stretch"):
        st.session_state["current_page"] = "Table"
    if st.sidebar.button("⚙️ Settings", width="stretch"):
        st.session_state["current_page"] = "Settings"

    st.sidebar.markdown("---")

    # ETL Controls in Dropdowns (Expanders)
    st.sidebar.subheader("⚙️ ETL Controls")
    
    with st.sidebar.expander("📥 Email"):
        if st.button("Download", width="stretch", key="btn_dl_email"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            def update_progress_ingestion(current, total):
                p = min(current / total, 1.0) if total > 0 else 1.0
                progress_bar.progress(p)
                status_text.write(f"**Progress:** {current}/{total} emails")
            with st.spinner("Downloading..."):
                run_ingestion(progress_callback=update_progress_ingestion)
            st.success("Done!")

        if st.button("Process", width="stretch", type="primary", key="btn_proc_email"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            def update_progress_processing(current, total):
                p = min(current / total, 1.0) if total > 0 else 1.0
                progress_bar.progress(p)
                status_text.write(f"**Progress:** {current}/{total} emails")
            with st.spinner("Processing..."):
                run_processing(progress_callback=update_progress_processing)
                run_certify()
            st.success("Complete!")
            st.rerun()

    with st.sidebar.expander("📋 Tabular Data"):
        uploaded_excel = st.file_uploader("Upload CSV/XLSX", type=["csv", "xlsx", "xls"])
        
        if st.button("Archive", width="stretch", key="btn_arch_excel"):
            if uploaded_excel is not None:
                progress_bar = st.progress(0)
                status_text = st.empty()
                def update_progress_archive(current, total):
                    p = min(current / total, 1.0) if total > 0 else 1.0
                    progress_bar.progress(p)
                    status_text.write(f"**Progress:** {current}/{total} rows")
                with st.spinner("Archiving..."):
                    rows_added = ingest_excel(uploaded_excel, progress_callback=update_progress_archive)
                    if rows_added > 0:
                        st.success(f"Archived {rows_added} rows.")
                    else:
                        st.info("No new rows.")
            else:
                st.error("Upload file first!")

        if st.button("Process", width="stretch", type="primary", key="btn_proc_excel"):
            if not Path(BRONZE_EXCEL).exists():
                st.warning("No data found.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                def update_progress_excel(current, total):
                    p = min(current / total, 1.0) if total > 0 else 1.0
                    progress_bar.progress(p)
                    status_text.write(f"**Progress:** {current}/{total} tx")
                with st.spinner("Processing..."):
                    run_excel_processing(progress_callback=update_progress_excel)
                    run_certify()
                st.success("Complete!")
                st.rerun()

    st.sidebar.markdown("---")
    # Global Filter at the bottom
    needs_review = st.sidebar.checkbox("⚠️ Needs Review", value=False, help="Show only transactions with confidence < 0.7")


    # Load Data
    data = load_data()
    
    if not DATA_PATH.exists():
        st.sidebar.error(f"File not found: {DATA_PATH.name}")
    elif not data:
        st.sidebar.warning("The data file is empty.")

    st.markdown("<h1 style='text-align: center;'>Personal BI Assistant</h1>", unsafe_allow_html=True)

    # Page Dispatcher
    if st.session_state["current_page"] == "Settings":
        render_settings()
    else:
        # Filter Logic (Shared between Dashboard and Table)
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
            
            # Ensure defaults are within the actual data range
            default_start = max(min_date, min(max_date, start_of_year))
            default_end = max(min_date, min(max_date, today))
            
            if default_start > default_end:
                default_start, default_end = min_date, max_date

            col1, col2, col3 = st.columns([2, 2, 4])
            selected_categories = col1.multiselect("Category", categories, default=["All"])
            selected_tipologies = col2.multiselect("Tipology", tipologies, default=["All"])
            
            if min_date < max_date:
                selected_dates = col3.slider("Date Range", min_value=min_date, max_value=max_date, value=(default_start, default_end), format="DD/MM/YYYY")
            else:
                from datetime import timedelta
                fake_max = min_date + timedelta(days=1)
                col3.slider("Date Range", min_value=min_date, max_value=fake_max, value=(min_date, min_date), format="DD/MM/YYYY", disabled=True, help="Only one day of data available")
                selected_dates = (min_date, min_date)

        start_date, end_date = selected_dates if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2 else (selected_dates, selected_dates)
        
        # Filtering
        filtered = data
        if selected_categories and "All" not in selected_categories:
            filtered = [row for row in filtered if row.get("category") in selected_categories]
        if selected_tipologies and "All" not in selected_tipologies:
            filtered = [row for row in filtered if row.get("tipology", row.get("direction")) in selected_tipologies]

        filtered = [row for row in filtered if row.get("parsed_date") is not None and start_date <= row["parsed_date"] <= end_date]

        if needs_review:
            filtered = [row for row in filtered if row.get("confidence", 1.0) < 0.7]

        st.markdown("---")

        if st.session_state["current_page"] == "Dashboard":
            render_dashboard(filtered)
        elif st.session_state["current_page"] == "Table":
            render_table(filtered, len(data))

if __name__ == "__main__":
    main()
