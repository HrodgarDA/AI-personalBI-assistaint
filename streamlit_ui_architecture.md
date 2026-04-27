# Streamlit Frontend Architecture Documentation

This document provides a highly detailed, LLM-optimized technical breakdown of the legacy Streamlit frontend for the Personal BI Assistant. It is designed to allow any AI agent to replicate the exact structure, logic, and aesthetic of the interface in alternative web frameworks (e.g., React, Vue, Next.js).

## 1. Global Application State & Layout

### 1.1 State Management (`st.session_state`)
The application relies on persistent state variables to maintain user context across reruns. In a modern SPA framework, these map directly to global state (e.g., React Context, Redux, or Zustand).

- `current_page`: String ("Dashboard", "Table", "Settings"). Defaults to "Dashboard".
- `show_adv_global`: Boolean. Toggles advanced settings globally.
- `needs_review`: Boolean. Filters transactions where `confidence < 0.7`.
- `selected_tipology`: String. ("All", "Incoming", "Outgoing").
- `cat_ms`: Array of Strings. Multi-select for categories. Includes mutually exclusive "All" logic.
- `selected_start_date` / `selected_end_date`: Date objects defining the global timeframe.
- `pending_profile`: Object. Temporarily holds AI discovery results before saving.

**URL Synchronization**: The app bidirectionally syncs these state variables with URL query parameters (`st.query_params`) on every change (`sync_url_from_state` and `restore_state_from_url`).

### 1.2 Theming & Aesthetics (`apply_theme()`)
The visual identity is defined by aggressive CSS injection targeting specific DOM elements.
- **Backgrounds**: 
  - Main App: `#111827` (Tailwind `gray-900`)
  - Sidebar / Cards: `#1F2937` (Tailwind `gray-800`)
  - Header: `rgba(17, 24, 39, 0.8)`
- **Text & Borders**:
  - Text: `#F9FAFB` (Tailwind `gray-50`)
  - Borders: `#374151` (Tailwind `gray-700`)
- **Containers**: Cards (`stVerticalBlockBorderWrapper`) have a `border-radius: 12px` and solid borders.
- **Sidebar Buttons**: Styled as block elements, 100% width, centered text, margin-bottom 5px. Hover effect lightens the background.

---

## 2. Global UI Structure (`webapp.py`)

The screen is divided into two primary areas: a persistent Sidebar and a dynamic Main Content Area.

### 2.1 Sidebar (Persistent)
1. **Navigation Buttons**: Three prominent buttons ("📊 Dashboard", "🔍 Data Explorer", "⚙️ Settings") that mutate `current_page`.
2. **ETL Controls - Ingestion**:
   - `st.sidebar.file_uploader`: Accepts CSV/XLSX.
   - Triggers `cached_analyze_file()`.
   - Displays a metric card: Total Rows, New Rows, Estimated Processing Time (seconds/minutes), and Speed (s/tx).
3. **ETL Controls - Action Buttons**:
   - `Archive` Button: Triggers `ingest_tabular_data()`. Shows progress bar.
   - `Process` Button: Triggers `run_processing()` and `run_certify()`. Shows progress bar. Clears cache upon completion.
4. **Global Filters & Toggles**:
   - "🔧 Show Advanced Settings" Checkbox (`show_adv_global`).
   - "⚠️ Needs Review" Checkbox (`needs_review`).

### 2.2 Main Header & Global Filters
*Rendered only if `current_page` != "Settings".*

- **Title**: `<h1>Personal BI Assistant</h1>` (Centered).
- **Filter Container** (Bordered Card):
  - **Col 1 (Width 2)**: Category Multiselect. Options dynamically fetched via `get_available_categories(data, profile, selected_tipology)`. "All" logic is mutually exclusive.
  - **Col 2 (Width 2)**: Tipology Selectbox. Evaluates `row.get("tipology", row.get("direction"))`.
  - **Col 3 (Width 4)**: Date Range Slider. Formatted as `DD/MM/YYYY`. Bounded by the absolute min/max dates in the dataset.

*Post-Filter Action*: The dataset is passed through `filter_dataset()` which applies Tipology, Category, Date, and Review filters, and sorts descending by date/time.

---

## 3. Page Views

### 3.1 Dashboard (`dashboard.py`)
Renders analytical charts and KPIs using the filtered dataset.

**Financial Configuration Constants:**
- `SAVINGS_CAT` = "Savings & Investments"
- `REFUND_CAT` = "Refund"

**KPI Logic (CRITICAL for replication):**
1. **Net Savings**: `(Deposits to SAVINGS_CAT) - (Withdrawals from SAVINGS_CAT)`
2. **Real Income**: Sum of all `Incoming` amounts, EXCLUDING `SAVINGS_CAT` and `REFUND_CAT`.
3. **Real Expenses**: `(Sum of all Outgoing EXCLUDING SAVINGS_CAT) - (Sum of all Incoming REFUND_CAT)`.
4. **Net Balance**: Absolute sum of all transactions (positive + negative).
5. **Top Category**: The category (excluding Savings/Refunds) with the highest absolute sum.

**Visual Layout:**
1. **Net Balance Widget**: A custom HTML/CSS banner. Dark background, flexbox `space-around`. Shows "Net Balance" (Green if >=0, Red if <0) and "Monthly Net Savings" (Blue).
2. **Secondary Metrics Row** (4 Columns):
   - Transactions (Count)
   - Real Income
   - Real Expenses (Net) -> `delta_color="inverse"`
   - Top Category (Text)
3. **Review Warning**: Shows a yellow `st.warning` if any transaction has `confidence < 0.7`.
4. **Time Series Chart**:
   - Toggles: "Daily", "Weekly", "Monthly" buttons (update `st.session_state["time_freq"]`).
   - Toggles: "Cumulative", "Periodical" buttons (update `st.session_state["chart_is_cumulative"]`).
   - Renders `plot_amount_over_time()` via Plotly.
5. **Category Distribution**:
   - Renders `plot_category_pie()`. Data explicitly filters OUT `SAVINGS_CAT` and `REFUND_CAT`.
6. **Category Totals Bar Chart**:
   - Renders `plot_category_totals()`.

### 3.2 Data Explorer / Table (`data_editor.py`)
A highly interactive data grid with inline editing and bulk deletion.

**Layout & Toggles:**
- Top row: Row count text ("Showing X of Y transactions").
- Edit Toggle switch (`edit_mode`).

**Column Configuration:**
- Always visible: Date, Category (Selectbox), Merchant, Amount, Tipology.
- Visible only in Edit Mode: Select (Checkbox), Bank Operation, Bank Details, AI Reasoning.

**Interaction Modes:**
1. **View Mode (`st.dataframe`)**:
   - Read-only.
   - Amounts are color-coded (Green for >=0, Red for <0) using Pandas styling.
2. **Edit Mode (`st.data_editor`)**:
   - `disabled` fields: Date, Tipology, Operation, Details, Reasoning.
   - **Delete Logic**: A "🗑️ Delete Selected" button appears if any row is checked. Deletions are pushed to `st.session_state.pending_deletions` (buffer) and the UI reruns to hide them.
   - **Save Logic**: "💾 Save Changes" compares the edited data against the original data. Changes in `category`, `amount`, or `merchant` are packaged into a list of dicts. Deletions and changes are passed to `log_feedback_and_update_silver()`.

### 3.3 Settings (`settings.py`)
Complex multi-tab interface for configuration and ML model management.

**Sidebar Extension (Profile Management):**
- Selectbox to switch Active Profile (`get_active_profile_name()`).
- "➕ Create New Profile" form.

**Tabs Layout:**
1. **🏠 Get Started**:
   - Quick Start Guide (Expander).
   - **Smart Auto-Discovery**: File uploader + "Run Auto-Discovery" button. Triggers `auto_configure_bank_profile()`. If successful, populates `pending_profile`.
   - **AI Discovery Results**: Renders if `pending_profile` exists. Shows a text input for the profile name and the detected schema. "✅ Save & Apply" commits it.
   - **System Status**: 4 metrics showing size of Rules Memory, Aliases, Catalogue, and Extraction Cache.
   - **Maintenance**: Export Profile (JSON) button, Reset Profile button, and a "🚑 Deep Recovery (Retry Errors)" button that triggers `run_error_recovery()`.

2. **⚙️ General Settings**:
   - Editable core schema: Profile Name, Skip Rows, Date Format.
   - Column Mapping: Date, Operation, Amount, Details, Hint.
   - *Advanced Mode Only*:
     - Dynamic data editors for Incoming and Outgoing Categories.
     - Text areas for Income Keywords and Cleanup Regex Patterns.
   - "💾 Save Settings" button.

3. **🧠 AI & Memory**:
   - "New Business Rule" natural language input. Triggers `interpret_user_rule()`.
   - List of Active Rules (`profile.rules_memory`) with "🗑️" delete buttons per rule.
   - *Advanced Mode Only*: Text inputs to override AI models (`config_model`, `classification_model`, `fast_model_id`).

---

## 4. API & Backend Boundaries
When rebuilding in a decoupled architecture, the following Python backend function calls represent the API boundaries required by the frontend:

**ETL / Ingestion**
- `analyze_file_for_ui(file)` -> Returns dict with stats.
- `ingest_tabular_data(file, progress_cb)` -> Inserts data to Bronze.
- `run_processing(progress_cb)` -> AI Classification pipeline.
- `run_certify()` -> Gold tier promotion.

**Data & Profile Retrieval**
- `load_data()` -> Returns array of flat transaction dicts.
- `load_bank_profile(name)` -> Returns `BankProfile` Pydantic object.
- `list_profiles()` -> Returns array of strings.

**Data Mutation**
- `log_feedback_and_update_silver(changes, deleted_ids)` -> Applies user edits/deletions.
- `save_bank_profile(profile_obj)` -> Saves settings.
- `interpret_user_rule(rule_text)` -> Compiles NLP to system rule.
- `run_error_recovery()` -> Re-runs failed classifications.
