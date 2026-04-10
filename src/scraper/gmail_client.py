import os
import base64
import logging
from typing import List, Optional, Dict

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Load environment variables (BANK_SENDER_EMAIL)
load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [os.getenv('PROJECT_SCOPE')]
class GmailScraper:
    """
    Interface for Gmail API to search, fetch, and decode bank notification emails.
    """

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        """Handles OAuth2 flow and returns the Gmail service object."""
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Google token...")
                creds.refresh(Request())
            else:
                logger.info("Initiating new OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
                
        return build('gmail', 'v1', credentials=creds)

    def fetch_expense_emails(self, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Searches for emails from the configured sender and extracts ID and text.
        
        Returns:
            List[Dict]: A list of dictionaries like {"id": "msg_id", "body": "text_content"}
        """
        target_email = os.getenv('BANK_SENDER_EMAIL')
        if not target_email:
            logger.error("BANK_SENDER_EMAIL is not set in the .env file.")
            return []

        query = f"from:{target_email}"
        logger.info(f"Searching emails with query: '{query}'")
        
        try:
            results = self.service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            extracted_data = []

            for msg in messages:
                msg_id = msg['id']
                # Fetch full message content
                msg_data = self.service.users().messages().get(
                    userId='me', 
                    id=msg_id, 
                    format='full'
                ).execute()
                
                payload = msg_data.get('payload', {})
                body_text = self._extract_text_from_payload(payload)
                
                if body_text:
                    extracted_data.append({
                        "id": msg_id,
                        "body": body_text
                    })
                    
            return extracted_data
            
        except Exception as e:
            logger.error(f"An error occurred while fetching emails: {e}")
            return []

    def _extract_text_from_payload(self, payload: dict) -> Optional[str]:
        """
        Recursively traverses the MIME tree to extract plain text or HTML content.
        Decodes from base64url and handles UTF-8 conversion.
        """
        mime_type = payload.get('mimeType')
        body = payload.get('body', {})
        data = body.get('data')

        # Base case: we found a text part
        if data and mime_type in ['text/plain', 'text/html']:
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode('utf-8', errors='replace')

        # Recursive case: check nested parts (multipart emails)
        parts = payload.get('parts', [])
        extracted_text = ""
        for part in parts:
            part_text = self._extract_text_from_payload(part)
            if part_text:
                extracted_text += part_text + "\n"
                
        return extracted_text.strip() if extracted_text else None