import streamlit as st
import time
import pandas as pd
from api_client import api_client

def render_table(filtered, total_len):
    # Fetch categories from API
    categories = api_client.get_categories()
    valid_categories = sorted([c["id"] for c in categories] + ["Uncategorized"])
    
    # Shared session state for deleted rows during this session
    if "pending_deletions" not in st.session_state:
        st.session_state.pending_deletions = set()

    st.markdown("<h2 style='text-align: center;'>📋 Data Explorer</h2>", unsafe_allow_html=True)
    
    # Header Layout
    col_info, col_spacer, col_del, col_toggle = st.columns([0.5, 0.2, 0.18, 0.12])
    with col_info:
        st.write(f"**Showing {len(filtered)} of {total_len} transactions**")
    
    # Delete Button logic
    display_data = [r for r in filtered if str(r.get("original_msg_id")) not in st.session_state.pending_deletions]
    
    edit_mode = col_toggle.toggle("🖊️ Edit", value=False, help="Enable Edit Mode")

    col_config = {
        "Select": st.column_config.CheckboxColumn("Select", default=False, width="small"),
        "parsed_date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "category": st.column_config.SelectboxColumn("Category", options=valid_categories, width="medium"),
        "merchant": st.column_config.TextColumn("Merchant", width="medium"),
        "amount": st.column_config.NumberColumn("Amount", format="€ %.2f"),
        "tipology": st.column_config.TextColumn("Tipology"),
        "original_operation": st.column_config.TextColumn("🏦 Bank Operation", width="large"),
        "original_details": st.column_config.TextColumn("📝 Bank Details", width="large"),
        "reasoning": st.column_config.TextColumn("🧠 AI Reasoning / Context", width="large"),
    }
    
    column_order = (["Select"] if edit_mode else []) + ["parsed_date", "category", "merchant", "amount", "tipology"]
    if edit_mode:
        column_order += ["original_operation", "original_details", "reasoning"]

    if not edit_mode:
        # --- VIEW MODE ---
        if not display_data:
            st.info("No data to display with current filters.")
            return

        df = pd.DataFrame(display_data)
        def color_amount(val):
            color = '#10B981' if val >= 0 else '#EF4444'
            return f'color: {color}; font-weight: bold;'
        styled_df = df.style.map(color_amount, subset=['amount'])

        st.dataframe(styled_df, width="stretch", hide_index=True, height=700, column_order=column_order, column_config=col_config)
    else:
        # --- EDIT MODE ---
        for r in display_data:
            if "Select" not in r: r["Select"] = False

        st.warning("⚠️ You are in Edit Mode. Select rows to delete or modify values. Press 'Save Changes' to commit.")
        
        edited_data = st.data_editor(
            display_data,
            width="stretch",
            hide_index=True,
            height=600,
            num_rows="fixed",
            key="table_editor",
            column_order=column_order,
            column_config=col_config,
            disabled=["original_operation", "original_details", "reasoning"]
        )

        any_selected = any(row.get("Select") for row in edited_data)
        if edit_mode and col_del.button("🗑️ Delete Selected", type="secondary", disabled=not any_selected, width="stretch", help="Delete Selected Records"):
            selected_ids = [str(row["original_msg_id"]) for row in edited_data if row.get("Select")]
            st.session_state.pending_deletions.update(selected_ids)
            st.rerun()

        if st.button("💾 Save Changes", type="primary", width="stretch"):
            # 1. Modifications
            original_map = {str(r.get("original_msg_id")): r for r in filtered}
            mod_count = 0
            for new_row in edited_data:
                msg_id = str(new_row.get("original_msg_id"))
                if msg_id in original_map:
                    old_row = original_map[msg_id]
                    
                    changes = {}
                    if str(old_row.get("category")) != str(new_row.get("category")):
                        changes["category_id"] = new_row.get("category")
                    if old_row.get("amount") != new_row.get("amount"):
                        changes["amount"] = new_row.get("amount")
                    if str(old_row.get("merchant")) != str(new_row.get("merchant")):
                        changes["merchant_id"] = new_row.get("merchant")
                    
                    if changes:
                        api_client.update_transaction(msg_id, changes)
                        mod_count += 1
            
            # 2. Deletions
            del_count = 0
            for del_id in st.session_state.pending_deletions:
                api_client.delete_transaction(del_id)
                del_count += 1
            
            if mod_count > 0 or del_count > 0:
                st.session_state.pending_deletions = set()
                st.toast(f"✅ Saved {mod_count} modifications and deleted {del_count} records!", icon="💾")
                st.cache_data.clear()
                time.sleep(0.5) 
                st.rerun()
            else:
                st.info("No modifications detected.")
