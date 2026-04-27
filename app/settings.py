import streamlit as st
import os
import tempfile
import logging
from api_client import api_client
from auto_bi.core.configurator import auto_configure_bank_profile
from auto_bi.core.rule_assistant import interpret_user_rule
from auto_bi.core.noise_assistant import suggest_cleaning_patterns
import re
import json
import time
from auto_bi.core.recovery import run_error_recovery
# Keep some constants if needed, but profiles should come from API
from auto_bi.utils.config import EXTRACTION_CACHE, MERCHANT_CATALOGUE

logger = logging.getLogger(__name__)
def render_settings():
    # --- CORE INITIALIZATION ---
    profiles_raw = api_client.get_profiles()
    all_profiles = [p["name"] for p in profiles_raw]
    active_name = st.session_state.get("active_profile_name")
    
    # Simple profile object for UI (using first one if none selected)
    profile_data = next((p for p in profiles_raw if p["name"] == active_name), None)
    if not profile_data and profiles_raw:
        profile_data = profiles_raw[0]
        active_name = profile_data["name"]
    
    # Mocking a BankProfile-like object for compatibility with the rest of the script
    class ProfileProxy:
        def __init__(self, data):
            self.profile_name = data.get("name", "Default")
            self.config = data.get("config", {})
            self.skip_rows = self.config.get("skip_rows", 0)
            self.date_format = self.config.get("date_format", "%d/%m/%Y")
            self.column_mapping = type('CM', (), self.config.get("column_mapping", {
                "date": "Data", "operation": "Descrizione", "amount": "Importo", "details": "Dettagli", "category_hint": ""
            }))
            self.outgoing_categories = self.config.get("outgoing_categories", [])
            self.incoming_categories = self.config.get("incoming_categories", [])
            self.incoming_keywords = self.config.get("incoming_keywords", [])
            self.cleaning_patterns = self.config.get("cleaning_patterns", [])
            self.rules_memory = self.config.get("rules_memory", [])
            self.config_model = self.config.get("config_model", "gemma4:e4b")
            self.classification_model = self.config.get("classification_model", "gemma4:e4b")
            self.fast_model_id = self.config.get("fast_model_id", "gemma4:e4b")
        
        def model_dump(self):
            return {"name": self.profile_name, "config": self.config}

    profile = ProfileProxy(profile_data if profile_data else {})
    
    # AI Discovery state override
    is_discovery_mode = "pending_profile" in st.session_state
    display_profile = st.session_state.get("pending_profile", profile)
    
    # Use a dynamic suffix for keys to force UI reset
    discovery_id = st.session_state.get("discovery_id", "")
    key_suffix = f"discovery_{discovery_id}" if is_discovery_mode else (active_name or "initial")
    
    if is_discovery_mode:
        st.warning("✨ **AI Discovery Results Loaded**: Review suggestions and click **Save** in General Settings.")
        if st.button("Discard AI Suggestions", type="secondary"):
            del st.session_state["pending_profile"]
            st.rerun()    # --- PROFILE MANAGEMENT (SIDEBAR) ---
    with st.sidebar:
        st.divider()
        st.subheader("🏦 Bank Profiles")
        if not all_profiles:
            st.info("No profiles found. Create one to start.")
        else:
            try:
                p_idx = all_profiles.index(active_name) if active_name in all_profiles else 0
            except ValueError:
                p_idx = 0
            new_active = st.selectbox("Switch Active Profile", 
                                     options=all_profiles, 
                                     index=p_idx)
            if new_active and new_active != active_name:
                st.session_state["active_profile_name"] = new_active
                st.rerun()
            
        if st.button("➕ Create New Profile", width='stretch'):
            st.session_state["show_new_profile_dialog"] = True
            
        if st.session_state.get("show_new_profile_dialog"):
            with st.form("new_profile_form"):
                new_name = st.text_input("Profile Name (e.g. My Bank)")
                if st.form_submit_button("Create"):
                    if new_name:
                        api_client.create_profile(new_name)
                        st.session_state["active_profile_name"] = new_name
                        del st.session_state["show_new_profile_dialog"]
                        st.rerun()

    # --- MAIN UI ---
    show_advanced = st.session_state.get("show_adv_global", False)
    
    # 3 TABS: Get Started, General Settings, AI & Memory
    tab0, tab1, tab2 = st.tabs(["🏠 Get Started", "⚙️ General Settings", "🧠 AI & Memory"])
    
    with tab0:
        st.subheader("Welcome to your personal Business Intelligence assistaint!")
        st.write("Extract insights from your bank statements using AI. No manual data entry required.")
        
        # --- SECTION: QUICK START ---
        with st.expander("📖 **Quick Start Guide**", expanded=True):
            st.markdown("""
            Follow these steps to set up your assistant:
            1. **Setup**: Create a **Bank Profile** in the sidebar or use the **Auto-Discovery** below.
            2. **Ingest**: Upload your bank statement in the sidebar and click **Archive**.
            3. **Analyze**: Click **Process** in the sidebar to let the AI categorize your transactions.
            4. **Explore**: Visit the **Dashboard** and **Data Explorer** to see your financial insights!
            """)
        
        # --- SECTION: DISCOVERY ---
        st.divider()
        st.subheader("🚀 Smart Auto-Discovery")
        st.write("Upload a sample file to automatically detect column mapping and data structure.")
        
        uploaded_file = st.file_uploader("Sample File (CSV/XLSX)", type=["xlsx", "xls", "csv"])
        if uploaded_file:
            if st.button("🔍 Run Auto-Discovery", type="primary", width='stretch'):
                with st.status("Analyzing file schema...", expanded=True) as status:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    try:
                        detected = auto_configure_bank_profile(tmp_path, model_id=profile.config_model)
                        if detected:
                            st.session_state["pending_profile"] = detected
                            st.session_state["discovery_id"] = str(int(time.time()))
                            status.update(label="Discovery Complete! Please review in 'General Settings'", state="complete", expanded=False)
                        else:
                            st.error("Discovery failed.")
                    finally:
                        if os.path.exists(tmp_path): os.remove(tmp_path)

        if "pending_profile" in st.session_state:
            pending = st.session_state["pending_profile"]
            st.divider()
            st.markdown("### 📋 AI Discovery Results")
            st.info("AI has detected the following schema. Review and name your profile below.")
            
            # Make the profile name extremely evident
            new_name = st.text_input("💎 **Give this Bank Profile a name**", value=pending.profile_name, help="E.g. My Main Bank, Revolut Business, etc.")
            pending.profile_name = new_name
            
            st.code(f"Columns: {pending.column_mapping.date}, {pending.column_mapping.operation}, {pending.column_mapping.amount}\nFormat: {pending.date_format} | Skip rows: {pending.skip_rows}")
            
            if st.button("✅ Save & Apply This Configuration", type="primary", width='stretch'):
                api_client.create_profile(pending.profile_name, pending.model_dump().get("config"))
                st.session_state["active_profile_name"] = pending.profile_name
                del st.session_state["pending_profile"]
                st.success("Config saved and active!")
                st.rerun()

        # --- SECTION: STATUS ---
        st.divider()
        if active_name:
            st.subheader("📊 System Status")
            s1, s2, s3, s4 = st.columns(4)
            cat_size = 0
            if os.path.exists(MERCHANT_CATALOGUE):
                try:
                    with open(MERCHANT_CATALOGUE, "r") as f: cat_size = len(json.load(f))
                except: pass
            ext_size = 0
            if os.path.exists(EXTRACTION_CACHE):
                try:
                    with open(EXTRACTION_CACHE, "r") as f: ext_size = len(json.load(f))
                except: pass
                
            s1.metric("Memory Rules", len(getattr(profile, 'rules_memory', [])))
            s2.metric("Aliases", len(getattr(profile, 'merchant_aliases', {})))
            s3.metric("Catalogue", cat_size)
            s4.metric("Extr. Cache", ext_size)
        else:
            st.info("Profiles help you manage multiple banks. Create your first one to see stats here.")

        # --- SECTION: MAINTENANCE ---
        if active_name:
            st.divider()
            st.subheader("💾 Maintenance")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.download_button(
                    label="📥 Export Profile (JSON)",
                    data=json.dumps(profile.model_dump(), indent=4, ensure_ascii=False),
                    file_name=f"bank_profile_{profile.profile_name}.json",
                    mime="application/json",
                    width='stretch'
                )
            with col_res2:
                if st.button("⚠️ Reset Active Profile", type="secondary", use_container_width=True):
                    api_client.create_profile(active_name, {})
                    st.toast("Profile reset!")
                    st.rerun()
            
            # --- NEW: RECOVERY BUTTON ---
            if st.button("🚑 Deep Recovery (Retry Errors)", use_container_width=True, help="Retry processing all 'Uncategorized' transactions using the latest rules."):
                with st.spinner("Analyzing and fixing errors..."):
                    res = api_client.run_recovery()
                    if res and res.get("status") == "success":
                        fixed = res.get("fixed", 0)
                        total = res.get("total", 0)
                        if fixed > 0:
                            st.success(f"✨ Success! Recovered {fixed} / {total} transactions.")
                            st.cache_data.clear()
                            st.rerun()
                        elif total > 0:
                            st.warning(f"Analyzed {total} errors but could not improve classification. Try adding a manual rule first!")
                        else:
                            st.info("No 'Uncategorized' transactions found to recover.")
                    else:
                        st.error("Failed to run recovery service. Check logs.")
        else:
            st.divider()
            st.info("💡 Tip: Once you create a bank profile, maintenance and export tools will appear here.")

    with tab1:
        if not active_name and not is_discovery_mode:
            st.warning("Please create or select a profile to view general settings.")
        else:
            st.subheader("⚙️ Core Configuration")
            display_profile.profile_name = st.text_input("Name", display_profile.profile_name, key=f"pname_{key_suffix}")
            c_m1, c_m2 = st.columns(2)
            display_profile.skip_rows = c_m1.number_input("Skip Header Rows", min_value=0, value=display_profile.skip_rows, key=f"skip_{key_suffix}")
            display_profile.date_format = c_m2.text_input("Date Format", display_profile.date_format, key=f"dfmt_{key_suffix}")
            
            st.divider()
            st.subheader("📊 Column Mapping")
            cm1, cm2 = st.columns(2)
            display_profile.column_mapping.date = cm1.text_input("Date Column", display_profile.column_mapping.date, key=f"cdate_{key_suffix}")
            display_profile.column_mapping.operation = cm1.text_input("Operation Column", display_profile.column_mapping.operation, key=f"cop_{key_suffix}")
            display_profile.column_mapping.amount = cm2.text_input("Amount Column", display_profile.column_mapping.amount, key=f"camt_{key_suffix}")
            display_profile.column_mapping.details = cm2.text_input("Details Column", display_profile.column_mapping.details, key=f"cdet_{key_suffix}")
            display_profile.column_mapping.category_hint = cm2.text_input("Hint Column (Opt)", display_profile.column_mapping.category_hint, key=f"chint_{key_suffix}")

            if show_advanced:
                st.divider()
                st.subheader("🏷️ Categories")
                c_out, c_inc = st.columns(2)
                with c_out:
                    st.markdown("**Outgoing**")
                    edf_out = st.data_editor([{"Category": c} for c in display_profile.outgoing_categories], num_rows="dynamic", width='stretch', key=f"edout_{key_suffix}")
                    display_profile.outgoing_categories = [r["Category"] for r in edf_out if r.get("Category")]
                with c_inc:
                    st.markdown("**Incoming**")
                    edf_inc = st.data_editor([{"Category": c} for c in display_profile.incoming_categories], num_rows="dynamic", width='stretch', key=f"edinc_{key_suffix}")
                    display_profile.incoming_categories = [r["Category"] for r in edf_inc if r.get("Category")]

                st.divider()
                st.subheader("🔍 Logic & Noise")
                l1, l2 = st.columns(2)
                with l1:
                    ikw = st.text_area("Income Keywords", value="\n".join(display_profile.incoming_keywords), height=150)
                    display_profile.incoming_keywords = [k.strip() for k in ikw.split("\n") if k.strip()]
                with l2:
                    pats = st.text_area("Cleanup Regex Patterns", value="\n".join(display_profile.cleaning_patterns), height=150)
                    display_profile.cleaning_patterns = [p.strip() for p in pats.split("\n") if p.strip()]

            if st.button("💾 Save Settings", type="primary", width='stretch'):
                if not display_profile.profile_name:
                    st.error("Profile name is required!")
                else:
                    api_client.create_profile(display_profile.profile_name, display_profile.config)
                    if is_discovery_mode:
                        st.session_state["active_profile_name"] = display_profile.profile_name
                        del st.session_state["pending_profile"]
                    st.toast("Settings Saved!")
                    time.sleep(0.5)
                    st.rerun()

    with tab2:
        if not active_name:
            st.warning("Select a profile to access AI tools.")
        else:
            st.subheader("🧠 Intelligence & Memory")
            new_rule = st.text_input("New Business Rule (Natural Language)")
            if st.button("✨ Train System", width='stretch'):
                if new_rule:
                    with st.spinner("Compiling..."):
                        compiled = interpret_user_rule(new_rule)
                        profile.rules_memory.append(compiled)
                        api_client.create_profile(profile.profile_name, profile.config)
                        st.toast("Logic updated!")
                        st.rerun()
            
            st.divider()
            st.subheader("📋 Active Rules")
            for i, rule in enumerate(profile.rules_memory):
                r1, r2 = st.columns([0.9, 0.1])
                r1.code(rule)
                if r2.button("🗑️", key=f"delr_{i}"):
                    profile.rules_memory.pop(i)
                    api_client.create_profile(profile.profile_name, profile.config)
                    st.rerun()

            st.divider()
            st.subheader("🛠️ Deployment")
            if show_advanced:
                profile.config_model = st.text_input("Config Model", profile.config_model)
                profile.classification_model = st.text_input("Classification Model", profile.classification_model)
                profile.fast_model_id = st.text_input("Fast Model (Multi-Model)", profile.fast_model_id)
                if st.button("Sync Models", width='stretch'):
                    api_client.create_profile(profile.profile_name, profile.config)
                    st.toast("Syncing...")
            else:
                st.info("Enable Advanced Settings in the sidebar to modify models.")
