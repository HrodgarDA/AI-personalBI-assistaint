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

    def fetch_expense_emails(self, max_results: int = 100, query_addon: str = "") -> List[Dict[str, str]]:
        """
        Scarica le email con supporto alla paginazione per superare il limite dei 100 risultati.
        """
        target_email = os.getenv('BANK_SENDER_EMAIL')
        query = f"from:{target_email} {query_addon}".strip()
        
        extracted_data = []
        next_page_token = None
        
        logger.info(f"🔍 Ricerca in corso: '{query}' (Target: {max_results} mail)")

        try:
            while len(extracted_data) < max_results:
                # Determina quanti risultati chiedere in questa pagina
                remaining = max_results - len(extracted_data)
                page_size = min(100, remaining)

                results = self.service.users().messages().list(
                    userId='me', 
                    q=query, 
                    maxResults=page_size,
                    pageToken=next_page_token
                ).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break

                for msg in messages:
                    m_id = msg['id']
                    m_data = self.service.users().messages().get(userId='me', id=m_id, format='full').execute()
                    
                    # Estrazione data/ora originale dalla mail (internalDate è in ms)
                    internal_date_ms = int(m_data.get('internalDate', 0))
                    email_datetime = datetime.fromtimestamp(internal_date_ms / 1000.0)
                    email_date = email_datetime.strftime('%Y-%m-%d')
                    email_time = email_datetime.strftime('%H:%M')
                    
                    payload = m_data.get('payload', {})
                    raw_body = self._extract_text(payload)
                    
                    if raw_body:
                        clean_body = self._clean_html(raw_body)
                        extracted_data.append({
                            "id": m_id,
                            "body": clean_body,
                            "email_date": email_date,
                            "email_time": email_time
                        })
                
                # Check per pagina successiva
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    break
                
                logger.info(f"📦 Caricamento pagina successiva... (Totale parziale: {len(extracted_data)})")
                    
            return sorted(
                extracted_data,
                key=lambda e: (e.get("email_date", ""), e.get("email_time", ""))
            )
        except Exception as e:
            logger.error(f"❌ Errore durante il fetching: {e}")
            return []

    def _clean_html(self, html_content: str) -> str:
        """Isola il testo utile eliminando il template HTML e i disclaimer."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            main_div = soup.find('div', id='main-text')
            if main_div:
                return main_div.get_text(separator=' ', strip=True)
            return soup.get_text(separator=' ', strip=True)[:500]
        except:
            return html_content[:500]

    def _extract_text(self, payload):
        parts = payload.get('parts', [])
        data = payload.get('body', {}).get('data')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        for part in parts:
            text = self._extract_text(part)
            if text: return text
        return None