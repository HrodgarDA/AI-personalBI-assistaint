import os
import json
import logging
from scraper.gmail_client import GmailScraper

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAW_DATA_DIR = "data/raw"
RAW_FILE_PATH = os.path.join(RAW_DATA_DIR, "raw_emails.json")

def save_raw_data(data: list, filepath: str):
    """Salva i dati grezzi estratti in formato JSON per l'audit e lo staging."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f"Dati grezzi salvati con successo in {filepath}")

def main():
    logger.info("Inizio pipeline ETL...")
    
    # 1. EXTRACT: Inizializzazione scraper ed estrazione dati
    scraper = GmailScraper()
    # Recupera le ultime 5 mail per test
    raw_emails = scraper.fetch_expense_emails(max_results=5) 
    
    if not raw_emails:
        logger.warning("Nessuna email trovata o errore nell'estrazione. Uscita.")
        return

    # 2. STAGING: Salvataggio del testo grezzo (Bronze Layer)
    save_raw_data(raw_emails, RAW_FILE_PATH)
    
    # 3. TRANSFORM: (Da implementare) 
    # Qui leggeremo da raw_emails.json o passeremo raw_emails direttamente al parser
    # parser = ExpenseParser()
    # structured_data = parser.extract_entities(raw_emails)
    
    # 4. LOAD: (Da implementare)
    # json_writer.save(structured_data)

if __name__ == "__main__":
    main()