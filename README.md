# AI Personal BI Assistant
> An advanced, privacy-first financial intelligence system for automated transaction classification and analytics.

---

## 🔒 Privacy-First Architecture
**100% Private & Local**: This system is designed with a "Privacy-First" mindset. All AI processing happens locally via **Ollama**, and all financial data is stored securely in your local **PostgreSQL** instance. **No cloud API calls, no data leaks, no third-party tracking.** Your financial life remains entirely your own.

---

## 🏗️ Modern Tech Stack
The repository has been modernized into a robust **FastAPI + Streamlit** architecture, ensuring scalability and high performance.

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | FastAPI | High-performance asynchronous API for processing and services. |
| **Frontend** | Streamlit | Interactive dashboard and explorer for data visualization. |
| **Database** | PostgreSQL + pgvector | Relational storage with vector support for semantic search. |
| **ORM & Migrations** | SQLAlchemy + Alembic | Type-safe database interaction and version-controlled schema evolution. |
| **AI Engine** | Ollama + Instructor | Local LLM orchestration (Gemma/Qwen) with structured JSON output. |
| **Dependency Mgmt** | Poetry | Deterministic package management and environment isolation. |
| **Containerization** | Docker | Standardized deployment and environment consistency. |
| **PDF Extraction** | pdfplumber | Reliable and precise text extraction from bank statements. |

---

## 🧠 The AI Intelligence Layer
The system implements a multi-tier classification strategy for maximum precision and efficiency:

1.  **Tier 1: Regex Automation**: Instant matching for known merchants using dynamic, user-defined regex rules.
2.  **Tier 2: Semantic Database Search**: Uses **pgvector** and embeddings to find similar historical transactions or known merchants.
3.  **Tier 3: AI Batch Classification**: Deep reasoning via local LLMs (Gemma 4 / Qwen) with parallelized web searches (Tavily/DuckDuckGo) for real-time merchant identification.

---

## 📊 Features & UI
*   **📊 Dynamic Dashboard**: High-level financial metrics, spending trends, and category distribution.
*   **🔍 Data Explorer**: Granular view of all transactions with advanced filtering by type and date.
*   **⚙️ Smart Settings**: Configure bank profiles, regex rules, and AI parameters.
*   **📥 Intelligent Ingestion**: Upload PDF bank statements and let the AI handle the heavy lifting.
*   **⚠️ Audit & Review**: Specialized view for transactions with low AI confidence for manual verification.

---

## 🛠️ Setup & Installation

### 1. Prerequisites
*   Docker & Docker Compose
*   Ollama (running locally)
*   Poetry (for local development)

### 2. Environment Setup
Clone the repository and create your `.env` file from the provided example:
```bash
git clone https://github.com/HrodgarDA/AI-personalBI-assistaint.git
cd AI-personalBI-assistaint
cp .env.example .env
```

### 3. Deploy with Docker
The easiest way to start the entire stack is via Docker Compose:
```bash
docker-compose up -d
```
This will spin up:
- **Database**: PostgreSQL with pgvector.
- **Backend**: FastAPI server.
- **Frontend**: Streamlit dashboard.

### 4. Local Development (Optional)
If you prefer running without Docker:
```bash
# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start Backend
poetry run python -m backend.api.main

# Start Frontend
poetry run streamlit run frontend/webapp.py
```

### 5. AI Model Setup
Ensure Ollama is running and download the optimized models:
```bash
ollama pull gemma4:e4b
```

---

## 🚀 Roadmap
1.  **🔍 Advanced Anomaly Detection**: Unsupervised ML to identify unusual spending spikes.
2.  **💰 Smart Budgeting**: Predictive financial planning based on historical cash flow.
3.  **💬 Natural Language Query**: RAG-based chat interface to query your financial data.
4.  **🎯 Autonomous Goals**: Automated saving suggestions and monthly allocation plans.

---
*Developed with a focus on data integrity, privacy, and automated intelligence.*
