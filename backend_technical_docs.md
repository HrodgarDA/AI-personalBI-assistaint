# AI Personal BI Assistant - Backend Technical Documentation

This document provides a comprehensive technical overview of the backend infrastructure for the AI Personal BI Assistant. It is designed to be used as a reference for LLMs to replicate or extend the system.

## 🏗️ Architecture Overview

The system follows a modern asynchronous microservices-inspired architecture:

- **API Layer**: FastAPI handles HTTP requests, file uploads, and provides a RESTful interface for the frontend.
- **Task Queue**: Celery with Redis as a broker manages long-running processes (ingestion and AI classification).
- **Database**: PostgreSQL (via SQLAlchemy/Asyncpg) stores transaction data, bank profiles, merchants, and categories.
- **AI Engine**: A multi-stage pipeline using DuckDuckGo search and OpenAI (via Instructor) for transaction classification.

### Data Flow
1. **Upload**: PDF bank statement -> FastAPI -> Celery Worker.
2. **Ingestion**: Worker -> PDF Extractor -> Postgres (Pending Transactions).
3. **AI Pipeline**: Worker -> DDG Search -> LLM Classifier -> Postgres (Classified Transactions).

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI (Async)
- **Database**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.0 (Async)
- **Migrations**: Alembic
- **Task Queue**: Celery 5.6
- **Cache/Broker**: Redis 7
- **AI/LLM**: OpenAI GPT-4o, Instructor, Pydantic
- **Extraction**: PDFPlumber
- **Package Manager**: Poetry

---

## 🗄️ Database Schema (SQLAlchemy)

### Core Models (`src/database/models.py`)

| Model | Table Name | Key Fields |
| :--- | :--- | :--- |
| `BankProfile` | `bank_profiles` | `name`, `config` (JSON extraction rules), `is_active` |
| `Category` | `categories` | `name`, `is_income` |
| `Merchant` | `merchants` | `name`, `default_outgoing_category_id` |
| `Transaction` | `transactions` | `id` (MD5 hash), `amount`, `date`, `status` (pending/classified/verified), `ai_reasoning` |

**Key Constraints:**
- Transactions use a unique MD5 hash of their content as ID to prevent duplicates.
- Relationships are established between Transactions, Merchants, Categories, and BankProfiles.

---

## 🖥️ Streamlit Frontend Integration

Il backend è stato progettato per supportare front-end disaccoppiati (come React o Streamlit).

**Modalità di integrazione consigliata**:
Streamlit può effettuare chiamate REST agli endpoint FastAPI (es. `GET /api/transactions/`, `POST /api/upload/`) utilizzando la libreria `requests` o `httpx`.
Questo garantisce che la logica di business rimanga centralizzata nel backend e che Streamlit si occupi solo della visualizzazione, evitando di duplicare la gestione dello stato asincrono o le dipendenze del database all'interno del processo Streamlit.

---

## 🔌 API Reference (FastAPI)

### Endpoints (`src/api/routes/`)

#### 📤 Upload & Ingestion
- `POST /api/upload/`: Uploads a PDF file and triggers a `process_file_ingestion` Celery task.
- `GET /api/upload/task/{task_id}`: Polls the status and live logs of an ingestion task.

#### 💸 Transactions
- `GET /api/transactions/`: List transactions with filtering (date, category, status).
- `PATCH /api/transactions/{id}`: Manual override of category or status.
- `DELETE /api/transactions/{id}`: Remove a transaction.

#### 🏢 Merchants & Categories
- `GET /api/merchants/`: List all identified merchants.
- `GET /api/categories/`: List all available categories.

---

## 🤖 AI Classification Pipeline

The pipeline is orchestrated by `TransactionParser` (`src/services/extractor.py`) and utilizes several specialized components:

### 1. 🗂️ Resolution Strategy (Hierarchical)
To maximize performance and minimize LLM costs, the system follows this order:
1.  **Exact Cache Match**: Checks if the exact raw text has been seen and classified before.
2.  **Semantic Catalogue Lookup**: Uses a fuzzy/semantic match against a known merchant catalogue.
3.  **Deep Raw Scan**: Scans the transaction details for keywords present in the catalogue.
4.  **Web-Enhanced LLM Inference**: If above fail, it performs a web search and then calls the LLM.

### 2. 🔍 Search & Research (`search.py`)
Uses `ddgs` (DuckDuckGo Search) to find information about the merchant. Searches are performed in **parallel** (ThreadPoolExecutor) for efficiency. Context snippets are injected into the LLM prompt.

### 3. ⚡ Cache & Memory (`cache.py`)
- **Extraction Cache**: Stores raw-text to merchant-name mappings.
- **Merchant Catalogue**: Persistent store of merchant-to-category mappings (bi-directional: Incoming vs Outgoing).
- **Bank Map Cache**: Stores translations of cryptic bank category hints to the system's category schema.

### 4. 🧠 Batch Classifier (`classifier.py`)
- **Directional Batching**: Transactions are grouped by "Incoming" or "Outgoing" to use specialized prompts and Pydantic models.
- **Structured JSON Output**: Uses `instructor` to enforce Pydantic schemas, ensuring the LLM returns valid category IDs and merchant names.
- **Confidence Scoring**: The LLM provides a confidence score (0-1) and reasoning for each classification.

---

## 🐳 Infrastructure (Docker)

The system is fully containerized using `docker-compose.yml`:

- **`db`**: Postgres 16.
- **`redis`**: Redis 7 for Celery and caching.
- **`api`**: Runs Uvicorn on port 8000.
- **`worker`**: Runs Celery worker.

### Environment Variables (`.env`)
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/personal_bi
REDIS_URL=redis://redis:6379/0
OPENAI_API_KEY=sk-...
```

---

## 📋 LLM Implementation Guide (Replication Instructions)

To replicate this backend, follow these steps in order:

### Phase 1: Environment Setup
1.  **Initialize Poetry**: Use `pyproject.toml` to install dependencies including `fastapi`, `sqlalchemy` (with `asyncio` extra), `asyncpg`, `celery`, `redis`, and `instructor`.
2.  **Docker Setup**: Configure `docker-compose.yml` with Postgres and Redis. The `worker` container must start Celery tracking states.
3.  **Database Migration**: Use Alembic to initialize the schema based on `src/database/models.py`. The `Base` uses `sqlalchemy.orm.declarative_base`.

### Phase 2: Core Services & Infrastructure
1.  **Database Layer**: Setup async session handling in `src/database/session.py` using `create_async_engine` and `async_sessionmaker`. Expose a `get_db()` async generator for FastAPI dependency injection (`Depends(get_db)`).
2.  **Celery Configuration**: Set up the Celery app in `src/worker/celery_app.py` with Redis as both broker and backend. Enable `task_track_started=True` and configure JSON serializers.
3.  **FastAPI Initialization**: In `src/api/main.py`, configure `CORSMiddleware` (allowing `localhost:5173`) and include routers dynamically.
4.  **PDF Extractor**: Implement logic in `src/services/extractor.py` using `pdfplumber`. Create bank-specific regex patterns to parse transaction lines into standard schemas.

### Phase 3: AI Orchestration (Instructor + Pydantic)
1.  **Search Service**: Implement a DuckDuckGo wrapper (`ddgs`) to fetch merchant context.
2.  **Dynamic LLM Classifier**: 
    - In `src/services/components/classifier.py`, use `instructor.from_openai(OpenAI(base_url="...", api_key="ollama"), mode=instructor.Mode.JSON)`.
    - **CRITICAL**: The Pydantic models for categorization are created *dynamically* at runtime based on the `BankProfile` settings (e.g., creating an Enum of active categories on the fly using `create_dynamic_classification_model`).
    - The classifier automatically verifies and provisions the LLM locally using Ollama (`subprocess.run(["ollama", "create", ...])`) via a `Modelfile`.
    - Prompts inject both standard rules and user-defined NLP rules (`rules_memory`).

### Phase 4: API & Background Tasks
1.  **Task Logic**: Create a task that chains `IngestionService.ingest_file` -> `AIPipeline.run_full_extraction`. Expose task state updates via `self.update_state`.
2.  **FastAPI Routes**: Implement the endpoints for file upload, returning the Celery `task_id` for long polling by the frontend.

### Phase 5: Verification
1.  Run `pytest` for unit tests on the extraction logic.
2.  Verify the task flow by uploading a sample PDF and monitoring Celery logs.
