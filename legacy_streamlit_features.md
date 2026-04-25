# Legacy Frontend Features: Streamlit Version

This document lists the structure and features of the original Streamlit-based interface to ensure full feature parity in the new React microservices architecture.

## 📂 Page Structure

### 1. 🏠 Main Dashboard
The entry point for financial overview and high-level analytics.
- **KPI Cards**:
    - Total Balance (Sum of all transactions).
    - Monthly Income (Dynamic based on selected month).
    - Monthly Spending (Dynamic based on selected month).
    - Monthly Savings (Income - Spending).
- **Visualizations (Plotly)**:
    - **Sankey Diagram**: Visualization of income distribution into categories.
    - **Area Chart**: Historical spending trends over time.
    - **Pie Chart**: Spending breakdown by category.
- **Global Filters**:
    - Sidebar date range selector (Month/Year).
    - Category multi-select filter.

### 2. 🔍 Data Explorer
The central hub for auditing and manually refining transaction data.
- **Interactive Dataframe**:
    - Sorting and filtering by all columns.
    - **Inline Editing**: Ability to change categories via dropdowns directly in the table.
- **Audit Tools**:
    - Search bar for merchant names/details.
    - "Verified" flag toggle for each transaction.
    - Visualization of the "AI Reasoning" (the logic the LLM used for classification).

### 3. 📥 Import & Ingestion
The interface for uploading and processing bank statements.
- **File Uploader**: Drag-and-drop support for PDF, XLSX, and CSV.
- **Pre-Ingestion Analysis**:
    - Row count validation.
    - **Duplicate Detection**: Identifies how many rows are already in the system.
    - **Processing Estimator**: Calculates how many seconds the AI will take based on historical average speed.
- **Ingestion Loop**:
    - Sequential progress tracking for each transaction.
    - Real-time logging of search queries and LLM responses.

### 4. ⚙️ Settings (Bank Profiles)
Configuration management for the ETL pipeline.
- **Profile Editor**:
    - Column mapping management (Date, Amount, Description).
    - AI Model selection (Gemma vs Qwen).
    - Prompt customization.
- **Taxonomy Management**:
    - Define custom income and expense categories.
    - Set monthly savings targets.

### 5. 📖 Merchant Catalogue
Management of the system's classification memory.
- **Catalogue View**: List of all learned merchant-to-category mappings.
- **Alias Management**: Unification of multiple raw names (e.g., "Amazon IT", "Amazon.it") under a single normalized merchant.
- **Manual Overrides**: Forcing a specific category for a merchant regardless of AI prediction.

---

## 🛠️ Logic & Features
- **Deterministic ID Generation**: MD5 hashing based on `date_operation_amount_occurrence` to prevent duplicates.
- **Directional Awareness**: Intelligent detection of incoming vs. outgoing flows.
- **Fuzzy Matching**: Levenshtein-based search for merchant name normalization.
- **RAG Integration**: Injection of manual correction examples into the LLM context.
