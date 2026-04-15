import streamlit as st
import os
import tempfile
import logging
from auto_bi.utils.bank_profile import load_bank_profile, save_bank_profile, ColumnMapping, BankProfile
from auto_bi.core.configurator import auto_configure_bank_profile

logger = logging.getLogger(__name__)

def render_settings():
    st.markdown("<h1 style='text-align: center;'>⚙️ System Settings</h1>", unsafe_allow_html=True)
    
    profile = load_bank_profile()
    
    # Use tabs to organize the settings
    tab1, tab2, tab3 = st.tabs(["🏦 Bank Profile", "🤖 AI Behavior", "🔧 Auto-Configure"])
    
    with tab1:
        st.subheader("General Profile Settings")
        profile.profile_name = st.text_input("Bank Profile Name", profile.profile_name)
        profile.bank_sender_email = st.text_input("Bank Sender Email (for Gmail)", profile.bank_sender_email, help="E.g. notifiche@intesasanpaolo.com")
        
        col1, col2 = st.columns(2)
        with col1:
            profile.skip_rows = st.number_input("Rows to skip (Excel/CSV Header)", min_value=0, value=profile.skip_rows)
        with col2:
            profile.date_format = st.text_input("Date Format (strftime)", profile.date_format, help="Default: %d/%m/%Y")
            
        st.divider()
        st.subheader("Column Mapping")
        st.caption("Map the file column names to internal fields")
        
        c1, c2 = st.columns(2)
        with c1:
            profile.column_mapping.date = st.text_input("Date Column", profile.column_mapping.date)
            profile.column_mapping.operation = st.text_input("Operation Column", profile.column_mapping.operation)
            profile.column_mapping.amount = st.text_input("Amount Column", profile.column_mapping.amount)
        with c2:
            profile.column_mapping.details = st.text_input("Details Column", profile.column_mapping.details)
            profile.column_mapping.category_hint = st.text_input("Bank Category Column", profile.column_mapping.category_hint)

        st.divider()
        st.subheader("Logic Keywords")
        
        inc_kw_str = st.text_area("Incoming Patterns (one per line)", value="\n".join(profile.incoming_keywords), help="Keywords that identify a transaction as Incoming (Income/Refund/Transfer)")
        profile.incoming_keywords = [k.strip() for k in inc_kw_str.split("\n") if k.strip()]
        
        clean_pat_str = st.text_area("Cleaning Patterns (Regex, one per line)", value="\n".join(profile.cleaning_patterns), help="Regex patterns to remove noise from transaction descriptions")
        profile.cleaning_patterns = [p.strip() for p in clean_pat_str.split("\n") if p.strip()]

        if st.button("💾 Save Profile Settings", type="primary", use_container_width=True):
            save_bank_profile(profile)
            st.success("Profile saved successfully!")
            
    with tab2:
        st.subheader("AI System Prompt Injection")
        st.info("The text below will be injected into the LLM system prompt for every classification.")
        profile.custom_prompt = st.text_area("Custom System Rules", value=profile.custom_prompt, height=300, 
                                            placeholder="E.g.: 'The merchant WELLHUB is ALWAYS Sport category.'")
        
        st.divider()
        st.subheader("Configuration Model")
        profile.config_model = st.text_input("Ghost Model ID", value=profile.config_model, help="Heavy model used for auto-configuration (e.g., llama3:8b)")
        
        if st.button("💾 Save AI Settings", type="primary", use_container_width=True):
            save_bank_profile(profile)
            st.success("AI settings saved!")

    with tab3:
        st.subheader("🔍 Smart Auto-Configure")
        st.write("Upload a sample transaction file (Excel or CSV) and I will try to detect the configuration automatically using a heavy LLM.")
        
        uploaded_file = st.file_uploader("Upload sample file", type=["xlsx", "xls", "csv"])
        
        if uploaded_file:
            if st.button("🚀 Start Auto-Config Analysis", use_container_width=True):
                with st.status("Analyzing file structure...", expanded=True) as status:
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        st.write("Step 1: Detecting headers and skip_rows...")
                        # We use the existing function but inside the UI
                        new_profile = auto_configure_bank_profile(tmp_path, model_id=profile.config_model)
                        
                        if new_profile:
                            st.write("Step 2: Analysis complete!")
                            st.session_state["pending_profile"] = new_profile
                            status.update(label="Analysis Finished!", state="complete", expanded=False)
                        else:
                            st.error("Could not determine configuration. Try adjusting manually.")
                            status.update(label="Analysis Failed", state="error")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

        if "pending_profile" in st.session_state:
            pending = st.session_state["pending_profile"]
            st.success("Analysis successful! Review the detected settings below:")
            
            st.json(pending.model_dump())
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Apply & Save This Profile", type="primary", use_container_width=True):
                    save_bank_profile(pending)
                    st.success("New profile applied and saved!")
                    del st.session_state["pending_profile"]
                    st.rerun()
            with col_b:
                if st.button("❌ Discard", use_container_width=True):
                    del st.session_state["pending_profile"]
                    st.rerun()
