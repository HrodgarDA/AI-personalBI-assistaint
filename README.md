# AI-personal BI-assistaint
Personal expenses tracker powered by AI

## 🚀 What it does now
This project supports a complete, end-to-end Medallion ETL flow (Bronze ➔ Silver ➔ Gold) with an interactive Web Dashboard:
- 📩 **Ingestion**: Downloading bank notification emails from Gmail via API, actively capturing subject and body contexts.
- 🧱 **Bronze Layer**: Saving raw messages to `data/bronze_raw_emails.jsonl`
- 🤖 **Intelligent Extraction**: Using LLMs to read the full context to classify explicitly into Typologies (Expenses, Salaries, Refunds) and allocate proper negative/positive signs. Optionally performs a Web Search (DuckDuckGo) to understand unknown merchants.
- 💾 **Silver Layer**: Saving normalized transactions to `data/silver_expenses.json`
- 🏅 **Gold Layer**: Curating certified tabular data into `data/gold_certified_data.csv`
- 📊 **Web Application**: An advanced Streamlit Personal BI Dashboard to visualize dual Salary vs. Expenses trends, filter granularities, and edit raw records!

## 🧩 Architecture
- `src/gmail_client.py`: Gmail authentication + scraping emails from the configured sender
- `src/main.py`: Main CLI tool to trigger `--ingest`, `--process`, and `--certify` phases
- `src/extractor.py`: AI parsing with `instructor` and local OpenAI, injected with DuckDuckGo web search
- `src/models.py`: Unified Pydantic schemas for parsing transactional records (`Tipology` mapping to Expense/Salary/Refund)
- `src/prompts.py`: Extraction prompts and LLM templates
- `src/feedback.py`: Manages the user feedback loop from the UI back to the Silver Data
- `webapp.py`: Premium Streamlit application managing both Data Visualization and ETL execution

## 📁 Output files
- `data/bronze_raw_emails.jsonl`: Bronze layer with raw emails and metadata
- `data/silver_expenses.json`: Silver layer with extracted and normalized transactions
- `data/gold_certified_data.csv`: Analytical layer ready to be visualized
- `data/user_feedback.json`: Internal ledger recording all user overrides for AI few-shot prompting

## ⚙️ Environment variables
Set these variables in your `.env` file or environment:
- `BANK_SENDER_EMAIL`: bank notification sender email to filter
- `MODEL_ID`: local LLM model ID
- `FORCE_FULL_LOAD`: `true` to force a full data load
- `MAX_EMAILS`: maximum number of emails to download

## 🏃‍♂️ How to run

### 1. Run the Web Dashboard
You can run the full UI which allows triggering the ETL phases directly via interface:
```bash
poetry run streamlit run webapp.py
```

### 2. Manual CLI ETL Commands
1. Run ingestion:
   ```bash
   poetry run python -m src.main --ingest
   ```
2. Run Two-Pass LLM processing:
   ```bash
   poetry run python -m src.main --process
   ```
3. Generate Gold CSV:
   ```bash
   poetry run python -m src.main --certify
   ```

## ✅ What was done recently
- **Unified Modeling & Typology**: Upgraded the AI logic to output single-schema Extractions where costs are negative values and incomes are positive values (Expense, Salary, Refund).
- **Subject-Aware Prompts**: Bronze and Parsing layers now read and context-match Email subjects to ensure precision.
- **Premium UI**: Enforced a responsive dark-mode Dashboard with split Line-Charts to distinctively plot inputs vs. outputs over time, and custom colored filters.
- **Two-Pass Merchant Search**: The LLM queries DuckDuckGo for previously unknown merchants to enhance categorization accuracy.
- **Few-Shot Feedback Loop**: Your corrections in the UI Table are fed back directly to the LLM system prompts.
- **Global Dashboards filters**: Full analytics granularity selection (Day/Week/Month) with active states.

## 💡 Note
The pipeline is built to scale following the Medallion Data Architecture (Bronze -> Silver -> Gold). The interactive Streamlit WebApp allows easy monitoring and self-correcting mechanisms!
