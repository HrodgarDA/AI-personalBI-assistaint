# AI-personal BI-assistaint
Personal expenses tracker powered by AI

## 🚀 What it does now
This project now supports an end-to-end ETL flow for:
- 📩 downloading bank notification emails from Gmail via API
- 🧱 saving raw messages to `data/bronze_raw_emails.jsonl`
- 🤖 using a local LLM to extract and classify expenses
- 💾 saving normalized transactions to `data/silver_expenses.json`

## 🧩 Architecture
- `src/gmail_client.py`: Gmail authentication + scraping emails from the configured sender
- `src/main.py`: CLI with `--ingest` and `--process` phases
- `src/extractor.py`: AI parsing with `instructor` and local OpenAI
- `src/models.py`: Pydantic schemas for expenses and income
- `src/prompts.py`: extraction prompts and LLM templates

## 📁 Output files
- `data/bronze_raw_emails.jsonl`: Bronze layer with raw emails and metadata
- `data/silver_expenses.json`: Silver layer with extracted and normalized transactions

## ⚙️ Environment variables
Set these variables in your `.env` file or environment:
- `BANK_SENDER_EMAIL`: bank notification sender email to filter
- `MODEL_ID`: local LLM model ID
- `FORCE_FULL_LOAD`: `true` to force a full data load
- `MAX_EMAILS`: maximum number of emails to download

## 🏃‍♂️ How to run
1. Run ingestion:
   ```bash
   poetry run python -m src.main --ingest
   ```

2. Run LLM processing of raw emails:
   ```bash
   poetry run python -m src.main --process
   ```

## ✅ What was done now
- Implemented Gmail ingestion with sender-based query and pagination
- Added incremental support to avoid re-downloading already processed emails
- Added LLM processing phase to extract expenses from raw emails
- Saved transformed data in the Silver layer with Pydantic-backed objects

## 💡 Note
The pipeline is built to scale: the Bronze layer keeps original raw data, while the Silver layer holds structured output ready for analysis and reporting.
