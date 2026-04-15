import streamlit as st
from auto_bi.utils.feedback import log_feedback_and_update_silver

def render_table(filtered, total_len):
    st.markdown("<h2 style='text-align: center;'>📋 Data Explorer</h2>", unsafe_allow_html=True)
    st.write(f"**Showing {len(filtered)} of {total_len} transactions**")
    
    col_config = {
        "parsed_date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "category": st.column_config.TextColumn("Category"),
        "merchant": st.column_config.TextColumn("Merchant"),
        "amount": st.column_config.NumberColumn("Amount", format="€ %.2f"),
        "confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.2f"),
        "tipology": st.column_config.TextColumn("Tipology"),
        "reasoning": st.column_config.TextColumn("Reasoning"),
        "time": st.column_config.TextColumn("Time"),
    }

    edited_data = st.data_editor(
        filtered,
        width="stretch",
        hide_index=True,
        height=700,
        column_order=["parsed_date", "time", "category", "merchant", "amount", "confidence", "tipology", "reasoning"],
        column_config=col_config,
        disabled=["parsed_date", "time", "confidence", "reasoning", "tipology", "merchant"]
    )

    if st.button("💾 Save Changes", type="primary"):
        changes = []
        for old_row, new_row in zip(filtered, edited_data):
            cat_changed = str(old_row.get("category")) != str(new_row.get("category"))
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
