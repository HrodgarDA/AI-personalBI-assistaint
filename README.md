# Personal Business Intelligence AI powered system
> Personal expenses tracking and classification powered by an advanced AI engine.

---

## 🔒 Privacy-First Architecture
**100% Private & Local**: This system is designed with a "Privacy-First" mindset. All AI processing happens locally via **Ollama**, and all financial data is stored exclusively on your machine. **No cloud API calls, no data leaks, no third-party tracking.** Your financial life remains entirely your own.

---

## 🏗️ Architecture: The Medallion Paradigm
The system is built according to modern Data Engineering principles, ensuring data integrity and traceability at every stage:

*   **📩 Bronze Layer (Raw)**: Atomic ingestion of heterogeneous bank statement files (CSV, XLSX). Raw data is persisted in `JSONL` format to ensure the immutability of the source.
*   **🤖 Silver Layer (AI-Enriched)**: The core of the system. Data is validated, enriched, and categorized via LLMs. We implement **Atomic JSONL persistence** to ensure data integrity; every record is appended independently, preventing database corruption during hardware failures or AI stalls.
*   **🏅 Gold Layer (Certified)**: Certified final datasets optimized in analytical `CSV` format, ready for consumption by the dashboard or other OLAP tools.

---

## 🧠 The AI Engine: Advanced Intelligence Layer
Unlike systems based on simple Regex, this platform implements advanced AI logic for maximum precision:

### 1. Dual-Tier Model Strategy
Smart workload optimization via dispatching between two models:
*   **Fast Mode (Gemma 2)**: Rapid categorization for standard transactions and known patterns.
*   **Big Mode (Qwen 3)**: Complex reasoning, detailed extraction, and recovery analysis for ambiguous cases.

### 2. Expert RAG Memory (Long-term Learning)
Implementation of a **RAG (Retrieval-Augmented Generation)** memory buffer. The system injects up to 20 real examples of your past corrections into the AI context, allowing the engine to learn your personal preferences over time without the need for fine-tuning.

### 3. Fuzzy Semantic Aliaser & Entity Resolution
A proprietary normalization engine based on **Levenshtein** algorithms. It identifies and unifies similar merchants (e.g., `Amazon IT` vs. `AMZN Digital`) avoiding redundant AI queries for known patterns, drastically reducing latency and resource consumption.

### 4. Multi-Bank Federated Ingestor
Bank-agnostic architecture. Using AI **Ghost Models**, the system can automatically infer the structure of new file formats (columns, amounts, and dates) and generate a dynamic "Bank Profile" without writing a single line of code.

### 5. Layer of Last Resort (Bank Hint Mapping)
Robust fallback mechanism: if all AI analyses fail, the system performs a semantic mapping of the bank's original category hint onto your personal taxonomy, marking the record with a special confidence flag (`-1`) for easy manual review.

---

## 📊 Dashboard & UX
*   **Cross-Filter Intelligence**: Explore financial trends with global filters synchronized in real-time.
*   **Interactive Correction Loop**: Correct the AI directly from the data table; every modification instantly feeds the system's RAG memory.
*   **Data Audit**: Granular visualization of the "Reasoning" behind every AI-driven classification.

---

## 🛠️ Setup & Installation
The system is managed via **Poetry** for deterministic dependency management and is optimized for local execution on Apple Silicon (M1/M2/M3).

### 1. Requirements
*   Python 3.11+
*   [Poetry](https://python-poetry.org/)
*   [Ollama](https://ollama.ai/) (for running local LLM models)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/HrodgarDA/AI-BI-assistaint.git
cd AI-BI-assistaint

# Install dependencies
poetry install
```

### 3. AI Model Setup
Ensure Ollama is running and download the required models:
```bash
ollama pull qwen3:8b
ollama pull gemma2:2b
```

### 4. Run the Application
```bash
poetry run streamlit run app/webapp.py
```

---

## 🚀 Next Steps & Roadmap
The system is constantly evolving towards total financial autonomy:

1.  **🔍 Anomaly Detection**: Implementation of unsupervised ML algorithms (Isolation Forest) to identify suspicious transactions or unusual spending spikes.
2.  **💰 Expenses Budgeting**: Smart financial planning system with predictive alerts based on current trends.
3.  **💬 Personal Natural Language Query system**: An AI chat interface (RAG-based) allowing you to query your Gold financial data in natural language (e.g., *"How much more did I spend on dining out this month compared to last?"*).
4.  **🎯 Autonomous Smart Savings**: Predictive engine analyzing cash flow to suggest realistic savings goals and monthly allocation plans.

---
*Developed with a focus on scalability, distributed intelligence, and data integrity.*
