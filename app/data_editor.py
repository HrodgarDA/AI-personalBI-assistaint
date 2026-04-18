import streamlit as st
import time
import pandas as pd
from auto_bi.utils.feedback import log_feedback_and_update_silver
from auto_bi.utils.bank_profile import load_bank_profile, get_active_profile_name

def render_table(filtered, total_len):
    profile_name = get_active_profile_name()
    profile = load_bank_profile(profile_name)
    profile_cats = set(profile.outgoing_categories + profile.incoming_categories + ["Uncategorized"])
    
    # Also include categories that are actually in the data to prevent blank cells in SelectboxColumn
    present_cats = {r.get("category") for r in filtered if r.get("category")}
    valid_categories = sorted(list(profile_cats.union(present_cats)))

    # Shared session state for deleted rows during this session
    if "pending_deletions" not in st.session_state:
        st.session_state.pending_deletions = set()

    st.markdown("<h2 style='text-align: center;'>📋 Data Explorer</h2>", unsafe_allow_html=True)
    
    # Header Layout: Maximum alignment to the right with enough space for text
    col_info, col_spacer, col_del, col_toggle = st.columns([0.5, 0.2, 0.18, 0.12])
    with col_info:
        st.write(f"**Showing {len(filtered)} of {total_len} transactions**")
    
    # Delete Button logic (Minimal column)
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
        # Add 'Select' column to display_data
        for r in display_data:
            if "Select" not in r: r["Select"] = False

        st.warning("⚠️ You are in Edit Mode. Select rows to delete or modify values. Press 'Save Changes' to commit.")
        
        # Data Editor with key for reactivity
        edited_data = st.data_editor(
            display_data,
            width="stretch",
            hide_index=True,
            height=600,
            num_rows="fixed", # We handle deletions ourselves
            key="table_editor",
            column_order=column_order,
            column_config=col_config,
            disabled=["parsed_date", "tipology", "original_operation", "original_details", "reasoning"]
        )

        # Reactive Delete Button logic (Only visible if edit_mode is ON)
        any_selected = any(row.get("Select") for row in edited_data)
        if edit_mode and col_del.button("🗑️ Delete Selected", type="secondary", disabled=not any_selected, width="stretch", help="Delete Selected Records"):
            selected_ids = [str(row["original_msg_id"]) for row in edited_data if row.get("Select")]
            st.session_state.pending_deletions.update(selected_ids)
            st.rerun()

        if st.button("💾 Save Changes", type="primary", width="stretch"):
            changes = []
            
            # 1. Permanent Deletions (Buffer)
            final_deleted_ids = list(st.session_state.pending_deletions)
            
            # 2. Modifications (only for those NOT in blacklist)
            original_map = {str(r.get("original_msg_id")): r for r in filtered}
            for new_row in edited_data:
                msg_id = str(new_row.get("original_msg_id"))
                if msg_id in original_map:
                    old_row = original_map[msg_id]
                    
                    cat_changed = str(old_row.get("category")) != str(new_row.get("category"))
                    amt_changed = old_row.get("amount") != new_row.get("amount")
                    merch_changed = str(old_row.get("merchant")) != str(new_row.get("merchant"))
                    
                    if cat_changed or amt_changed or merch_changed:
                        changes.append({
                            "msg_id": msg_id,
                            "original_category": old_row.get("category"),
                            "corrected_category": new_row.get("category"),
                            "original_amount": old_row.get("amount"),
                            "corrected_amount": new_row.get("amount"),
                            "original_merchant": old_row.get("merchant"),
                            "corrected_merchant": new_row.get("merchant"),
                        })
            
            if changes or final_deleted_ids:
                log_feedback_and_update_silver(changes, deleted_ids=final_deleted_ids)
                st.session_state.pending_deletions = set() # Clear buffer
                st.toast(f"✅ Saved modifications and deleted {len(final_deleted_ids)} records!", icon="💾")
                time.sleep(0.5) 
                st.rerun()
            else:
                st.info("No modifications detected.")
