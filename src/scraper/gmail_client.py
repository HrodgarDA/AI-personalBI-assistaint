import os
import base64
import logging
from datetime import datetime
from typing import List, Optional, Dict
from bs4 import BeautifulSoup

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailScraper:
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return build('gmail', 'v1', credentials=creds)

    def fetch_expense_emails(self, max_results: int = 10, query_addon: str = "") -> List[Dict[str, str]]:
        target_email = os.getenv('BANK_SENDER_EMAIL')
        query = f"from:{target_email} {query_addon}".strip()
        
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            extracted_data = []

            for msg in messages:
                m_id = msg['id']
                m_data = self.service.users().messages().get(userId='me', id=m_id, format='full').execute()
                
                # Estrazione data/ora originale della mail (internalDate è in ms)
                internal_date_ms = int(m_data.get('internalDate', 0))
                email_datetime = datetime.fromtimestamp(internal_date_ms / 1000.0)
                email_date = email_datetime.strftime('%Y-%m-%d')
                email_time = email_datetime.strftime('%H:%M')
                
                payload = m_data.get('payload', {})
                raw_body = self._extract_text(payload)
                
                if raw_body:
                    # Pulizia HTML: isoliamo solo il contenuto utile
                    clean_body = self._clean_html(raw_body)
                    
                    extracted_data.append({
                        "id": m_id,
                        "body": clean_body,
                        "email_date": email_date,
                        "email_time": email_time
                    })
            return extracted_data
        except Exception as e:
            logger.error(f"Errore Gmail: {e}")
            return []

    def _clean_html(self, html_content: str) -> str:
        """Estrae il testo dal div main-text eliminando il rumore dei disclaimer."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            main_div = soup.find('div', id='main-text')
            if main_div:
                # separator=' ' evita che le parole si attacchino dove c'erano i <br>
                return main_div.get_text(separator=' ', strip=True)
            # Fallback se la struttura cambia: prendi tutto ma limita i caratteri
            return soup.get_text(separator=' ', strip=True)[:500]
        except Exception:
            return html_content[:500]

    def _extract_text(self, payload):
        """Navigazione ricorsiva del payload MIME."""
        parts = payload.get('parts', [])
        data = payload.get('body', {}).get('data')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        for part in parts:
            text = self._extract_text(part)
            if text: return text
        return None