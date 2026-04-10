# test_scraper.py
from src.scraper.gmail_client import GmailScraper
import os
from dotenv import load_dotenv

load_dotenv()

def dry_run():
    print("--- Avvio Dry Run dello Scraper ---")
    print(f"Target Email: {os.getenv('BANK_SENDER_EMAIL')}")
    
    try:
        scraper = GmailScraper()
        # Testiamo il recupero di una sola mail per verifica rapida
        emails = scraper.fetch_expense_emails(max_results=1)
        
        if not emails:
            print("Risultato: Nessuna email trovata. Controlla il mittente nel file .env o i permessi su Google Cloud.")
            return

        print(f"Risultato: {len(emails)} email recuperata/e con successo.")
        print("\n--- Anteprima contenuto grezzo ---")
        # Mostriamo solo i primi 200 caratteri per brevità
        print(emails[0][:200] + "...")
        print("----------------------------------")
        
    except Exception as e:
        print(f"Errore durante il test: {e}")

if __name__ == "__main__":
    dry_run()