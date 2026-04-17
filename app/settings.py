import streamlit as st
import os
import tempfile
import logging
from auto_bi.utils.bank_profile import (
    load_bank_profile, save_bank_profile, ColumnMapping, BankProfile,
    get_active_profile_name, set_active_profile_name, list_profiles
)
from auto_bi.core.configurator import auto_configure_bank_profile
from auto_bi.core.rule_assistant import interpret_user_rule
from auto_bi.core.noise_assistant import suggest_cleaning_patterns
import re
import json
import time
from auto_bi.utils.config import EXTRACTION_CACHE, MERCHANT_CATALOGUE

logger = logging.getLogger(__name__)
def render_settings():
    # --- CORE INITIALIZATION ---
    active_name = get_active_profile_name()
    profile = load_bank_profile(active_name)
    all_profiles = list_profiles()
    
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
                set_active_profile_name(new_active)
                st.rerun()
            
        if st.button("➕ Create New Profile", use_container_width=True):
            st.session_state["show_new_profile_dialog"] = True
            
        if st.session_state.get("show_new_profile_dialog"):
            with st.form("new_profile_form"):
                new_name = st.text_input("Profile Name (e.g. My Bank)")
                if st.form_submit_button("Create"):
                    if new_name:
                        set_active_profile_name(new_name)
                        save_bank_profile(BankProfile(profile_name=new_name))
                        del st.session_state["show_new_profile_dialog"]
                        st.rerun()

    # --- MAIN UI ---
    show_advanced = st.session_state.get("show_adv_global", False)
    
    # 4 TABS: Get Started, Auto-Configure, General Settings, AI & Memory
    tab0, tab1, tab2, tab3 = st.tabs(["🏠 Get Started", "🚀 Auto-Configure", "⚙️ General Settings", "🧠 AI & Memory"])
    
    with tab0:
        st.subheader("Welcome to your personal BI assistaint!")
        st.write("Extract insights from your bank statements using AI. No manual data entry required.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 1. 🚀 Discovery")
            st.write("Upload a sample PDF/Excel/CSV. Our AI will automatically detect the columns and format.")
        with c2:
            st.markdown("### 2. 🧠 Training")
            st.write("Fine-tune the classification rules or teach the system about specific regular merchants.")
            
        st.divider()
        # Stats section
        if active_name:
            st.markdown("### 📊 System Health")
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

        st.divider()
        st.subheader("💾 Backup & Global Maintenance")
        if active_name:
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.download_button(
                    label="📥 Export Profile (JSON)",
                    data=json.dumps(profile.model_dump(), indent=4, ensure_ascii=False),
                    file_name=f"bank_profile_{profile.profile_name}.json",
                    mime="application/json",
                    use_container_width=True
                )
            with col_res2:
                if st.button("⚠️ Reset Active Profile", type="secondary", use_container_width=True):
                    new_p = BankProfile(profile_name=active_name)
                    save_bank_profile(new_p)
                    st.toast("Profile reset!")
                    st.rerun()

    with tab1:
        st.subheader("🚀 Smart Ingestion Discovery")
        st.write("Upload a sample file to automatically detect column mapping and data structure.")
        
        uploaded_file = st.file_uploader("Sample File (CSV/XLSX)", type=["xlsx", "xls", "csv"])
        if uploaded_file:
            if st.button("🔍 Run Auto-Discovery", type="primary", use_container_width=True):
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
            st.markdown("### 📋 Findings")
            st.info("Verify these suggestions before applying.")
            st.code(f"Date: {pending.column_mapping.date} | Desc: {pending.column_mapping.operation} | Amount: {pending.column_mapping.amount}\nFormat: {pending.date_format} | Skip: {pending.skip_rows}")
            
            if st.button("✅ Apply This Configuration", type="primary", use_container_width=True):
                save_bank_profile(pending)
                set_active_profile_name(pending.profile_name)
                del st.session_state["pending_profile"]
                st.success("Config saved and active!")
                st.rerun()

    with tab2:
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
                    edf_out = st.data_editor([{"Category": c} for c in display_profile.outgoing_categories], num_rows="dynamic", use_container_width=True, key=f"edout_{key_suffix}")
                    display_profile.outgoing_categories = [r["Category"] for r in edf_out if r.get("Category")]
                with c_inc:
                    st.markdown("**Incoming**")
                    edf_inc = st.data_editor([{"Category": c} for c in display_profile.incoming_categories], num_rows="dynamic", use_container_width=True, key=f"edinc_{key_suffix}")
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

            if st.button("💾 Save Settings", type="primary", use_container_width=True):
                if not display_profile.profile_name:
                    st.error("Profile name is required!")
                else:
                    save_bank_profile(display_profile)
                    if is_discovery_mode:
                        set_active_profile_name(display_profile.profile_name)
                        del st.session_state["pending_profile"]
                    st.toast("Settings Saved!")
                    time.sleep(0.5)
                    st.rerun()

    with tab3:
        if not active_name:
            st.warning("Select a profile to access AI tools.")
        else:
            st.subheader("🧠 Intelligence & Memory")
            new_rule = st.text_input("New Business Rule (Natural Language)")
            if st.button("✨ Train System", use_container_width=True):
                if new_rule:
                    with st.spinner("Compiling..."):
                        compiled = interpret_user_rule(new_rule)
                        profile.rules_memory.append(compiled)
                        save_bank_profile(profile)
                        st.toast("Logic updated!")
                        st.rerun()
            
            st.divider()
            st.subheader("📋 Active Rules")
            for i, rule in enumerate(profile.rules_memory):
                r1, r2 = st.columns([0.9, 0.1])
                r1.code(rule)
                if r2.button("🗑️", key=f"delr_{i}"):
                    profile.rules_memory.pop(i)
                    save_bank_profile(profile)
                    st.rerun()

            st.divider()
            st.subheader("🛠️ Deployment")
            if show_advanced:
                profile.config_model = st.text_input("Config Model", profile.config_model)
                profile.classification_model = st.text_input("Classification Model", profile.classification_model)
                if st.button("Sync Models", use_container_width=True):
                    save_bank_profile(profile)
                    st.toast("Syncing...")
            else:
                st.info("Enable Advanced Settings in the sidebar to modify models.")
