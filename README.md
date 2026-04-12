# AI-personal BI-assistaint
Personal expenses tracker powered by AI

## 🚀 What it does now
This project supports a complete, end-to-end Medallion ETL flow (Bronze ➔ Silver ➔ Gold) with an interactive Web Dashboard:
- 📩 **Ingestion**: Downloading bank notification emails from Gmail via API
- 🧱 **Bronze Layer**: Saving raw messages to `data/bronze_raw_emails.jsonl`
- 🤖 **Two-Pass AI Extraction**: Using LLMs to first extract the `merchant`, optionally performing a Web Search (DuckDuckGo) to understand the merchant, and then extracting and classifying expenses intelligently.
- 💾 **Silver Layer**: Saving normalized transactions to `data/silver_expenses.json`
- 🏅 **Gold Layer**: Curating certified tabular data into `data/gold_certified_data.csv`
- 📊 **Web Application**: An advanced Streamlit Personal BI Dashboard to visualize spending trends, filter granularities, and edit raw records!

## 🧩 Architecture
- `src/gmail_client.py`: Gmail authentication + scraping emails from the configured sender
- `src/main.py`: Main CLI tool to trigger `--ingest`, `--process`, and `--certify` phases
- `src/extractor.py`: AI parsing with `instructor` and local OpenAI, injected with DuckDuckGo web search
- `src/models.py`: Pydantic schemas for expenses and income categories
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
- **Premium UI**: Introduced a fully responsive, dark/light mode compatible Streamlit Data Editor and Dashboard with interactive Plotly charts.
- **Two-Pass Merchant Search**: The LLM queries DuckDuckGo for previously unknown merchants to enhance categorization accuracy.
- **Few-Shot Feedback Loop**: Your corrections in the UI Table are fed back directly to the LLM system prompts.
- **Global Dashboards filters**: Full analytics granularity selection (Day/Week/Month).

## 💡 Note
The pipeline is built to scale following the Medallion Data Architecture (Bronze -> Silver -> Gold). The interactive Streamlit WebApp allows easy monitoring and self-correcting mechanisms!
