# AI-BI-assistaint
Personal expenses tracker powered by AI

## 🚀 Cosa fa ora
Questo progetto supporta un flusso ETL end-to-end per:
- 📩 scaricare email bancarie da Gmail via API
- 🧱 salvare i messaggi grezzi in `data/bronze_raw_emails.jsonl`
- 🤖 utilizzare un LLM locale per estrarre e classificare le spese
- 💾 salvare le transazioni normalizzate in `data/silver_expenses.json`

## 🧩 Architettura
- `src/gmail_client.py`: autenticazione Gmail + scraping email dal mittente configurato
- `src/main.py`: CLI con le fasi `--ingest` e `--process`
- `src/extractor.py`: parsing AI con `instructor` e OpenAI locale
- `src/models.py`: schemi Pydantic per spese e entrate
- `src/prompts.py`: prompt di estrazione e template per l’LLM

## 📁 File di output
- `data/bronze_raw_emails.jsonl`: Bronze layer con email grezze e metadata
- `data/silver_expenses.json`: Silver layer con transazioni estratte e normalizzate

## ⚙️ Ambiente e variabili
Imposta queste variabili nel file `.env` o nell’ambiente:
- `BANK_SENDER_EMAIL`: indirizzo email del mittente bancario da filtrare
- `MODEL_ID`: ID del modello LLM locale
- `FORCE_FULL_LOAD`: `true` per forzare il caricamento completo
- `MAX_EMAILS`: numero massimo di email da scaricare

## 🏃‍♂️ Come eseguire
1. Ingestione delle email:
   ```bash
   poetry run python -m src.main --ingest
   ```

2. Processing LLM delle email grezze:
   ```bash
   poetry run python -m src.main --process
   ```

## ✅ Cosa è stato fatto ora
- Implementata la fase di ingestione Gmail con query sul mittente e paginazione
- Aggiunto supporto incrementale per non riscaricare email già elaborate
- Creata la fase di processamento LLM per estrarre le spese dalle email grezze
- Salvata la trasformazione nel Silver layer con oggetti Pydantic

## 💡 Nota
La pipeline è progettata per crescere: il Bronze layer conserva i dati originali, mentre il Silver layer contiene output strutturati pronti per analisi e reportistica.
