import streamlit as st
import time
import pandas as pd
from auto_bi.utils.feedback import log_feedback_and_update_silver
from auto_bi.utils.bank_profile import load_bank_profile, get_active_profile_name

def render_table(filtered, total_len):
    # Fetch valid categories for the dropdown from active profile
    profile_name = get_active_profile_name()
    profile = load_bank_profile(profile_name)
    valid_categories = sorted(list(set(profile.outgoing_categories + profile.incoming_categories + ["Uncategorized"])))

    st.markdown("<h2 style='text-align: center;'>📋 Data Explorer</h2>", unsafe_allow_html=True)
    
    col_ctrl1, col_ctrl2 = st.columns([0.8, 0.2])
    with col_ctrl1:
        st.write(f"**Showing {len(filtered)} of {total_len} transactions**")
    with col_ctrl2:
        edit_mode = st.toggle("🖊️ Edit Mode", value=False, help="Toggle to enable data corrections")

    col_config = {
        "parsed_date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "category": st.column_config.SelectboxColumn("Category", options=valid_categories, width="medium"),
        "merchant": st.column_config.TextColumn("Merchant", width="medium"),
        "amount": st.column_config.NumberColumn("Amount", format="€ %.2f"),
        "tipology": st.column_config.TextColumn("Tipology"),
        "original_operation": st.column_config.TextColumn("🏦 Bank Operation", width="large"),
        "original_details": st.column_config.TextColumn("📝 Bank Details", width="large"),
        "reasoning": st.column_config.TextColumn("🧠 AI Reasoning / Context", width="large"),
    }
    
    column_order = ["parsed_date", "category", "merchant", "amount", "tipology"]
    if edit_mode:
        column_order += ["original_operation", "original_details", "reasoning"]

    if not edit_mode:
        # --- VIEW MODE (with colors) ---
        if not filtered:
            st.info("No data to display with current filters.")
            return

        df = pd.DataFrame(filtered)
        
        # Color function
        def color_amount(val):
            color = '#10B981' if val >= 0 else '#EF4444'
            return f'color: {color}; font-weight: bold;'

        styled_df = df.style.map(color_amount, subset=['amount'])

        st.dataframe(
            styled_df,
            width="stretch",
            hide_index=True,
            height=700,
            column_order=column_order,
            column_config=col_config
        )
    else:
        # --- EDIT MODE (Plain but interactive) ---
        st.warning("⚠️ You are in Edit Mode. Changes made here will be saved to your transaction history.")
        edited_data = st.data_editor(
            filtered,
            width="stretch",
            hide_index=True,
            height=600,
            column_order=column_order,
            column_config=col_config,
            disabled=["parsed_date", "tipology", "original_operation", "original_details", "reasoning"]
        )

        if st.button("💾 Save Changes", type="primary", width="stretch"):
            changes = []
            for old_row, new_row in zip(filtered, edited_data):
                cat_changed = str(old_row.get("category")) != str(new_row.get("category"))
                amt_changed = old_row.get("amount") != new_row.get("amount")
                merch_changed = str(old_row.get("merchant")) != str(new_row.get("merchant"))
                
                if cat_changed or amt_changed or merch_changed:
                    changes.append({
                        "msg_id": old_row.get("original_msg_id"),
                        "original_category": old_row.get("category"),
                        "corrected_category": new_row.get("category"),
                        "original_amount": old_row.get("amount"),
                        "corrected_amount": new_row.get("amount"),
                        "original_merchant": old_row.get("merchant"),
                        "corrected_merchant": new_row.get("merchant"),
                    })
            
            if changes:
                log_feedback_and_update_silver(changes)
                st.toast(f"✅ Applied {len(changes)} modifications!", icon="💾")
                time.sleep(0.5) # Brief pause to let the user see the toast
                st.rerun()
            else:
                st.info("No modifications detected.")
