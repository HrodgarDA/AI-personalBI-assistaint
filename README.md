# Personal Business Intelligence: AI-Powered Financial Control 🚀
> Transform your raw bank statements into a clear, actionable financial narrative with local AI and interactive analytics.

---

**Personal Business Intelligence (PBI)** is a professional-grade, privacy-first platform designed to give you total control over your financial life. By combining the power of local LLMs (Ollama) with a modern microservices architecture, PBI automates the painful process of categorizing expenses and uncovering spending trends—all without your data ever leaving your machine.

### ✨ Key Features
- **📊 Dynamic Visual Analytics**: Explore your finances through high-fidelity interactive charts, including Sankey diagrams for income flow, trend line analysis, and granular category breakdowns.
- **🤖 Intelligent AI Classification**: Leveraging a dual-tier model strategy (Gemma & Qwen), the system extracts, cleans, and categorizes every transaction with expert-level precision.
- **📁 Multi-Format Ingestion**: Native support for PDF bank statements (Intesa Sanpaolo), Excel, and CSV files from any bank.
- **🛠️ Bank Profile Manager**: Easily map columns and customize AI behavior for any new bank format through a dedicated management interface.
- **✍️ Interactive Correction Loop**: Review and edit AI classifications directly in the dashboard. Your corrections instantly feed the system's "Merchant Memory," making the AI smarter with every use.
- **🔒 Privacy-First by Design**: 100% local processing. No cloud APIs, no data sharing. Your finances, your privacy.

---

## 🏗️ Modern Microservices Architecture

The system has evolved from a monolithic script into a scalable, asynchronous platform:

*   **💻 React Frontend**: A premium, state-of-the-art interface built with Vite, Tailwind, and Framer Motion for a "WOW" user experience.
*   **📡 FastAPI Backend**: A high-performance REST API orchestrating data flow and AI tasks.
*   **🐘 PostgreSQL Persistence**: Centralized relational database for reliable storage of transactions, merchants, and configurations.
*   **⚙️ Celery & Redis**: Background worker architecture to handle long-running AI extraction tasks without blocking the UI.
*   **🧠 Local AI Engine**: Powered by Ollama, running models like Gemma 2 for speed and Qwen 3 for complex reasoning.

---

## 🏗️ Data Strategy: The Medallion Paradigm (Conceptual)

Even in our new database-centric architecture, we maintain the integrity of the Medallion paradigm:
- **📩 Bronze Layer**: Raw ingestion of uploaded files into the database, preserving the original source message and metadata.
- **🤖 Silver Layer**: AI-enriched transactions. Every record is classified, merchant names are normalized, and directional flow (In/Out) is established.
- **🏅 Gold Layer**: Curated, analytical views and aggregations used by the React dashboard for real-time reporting.

---

## 🚀 Getting Started

The project is managed via a `Makefile` for simplicity.

### 1. Requirements
*   Python 3.11+
*   [Poetry](https://python-poetry.org/)
*   [Ollama](https://ollama.ai/)
*   [Docker](https://www.docker.com/) (for Postgres & Redis)

### 2. Start Everything
This command starts Docker containers, initializes the database, and launches the API, Worker, and Frontend.
```bash
make start
```

### 3. Restart Everything
```bash
make restart
```

### 4. Stop Everything
```bash
make stop
```

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.
