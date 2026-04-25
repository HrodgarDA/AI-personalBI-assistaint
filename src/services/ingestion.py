import os
import logging
import pandas as pd
import re
import pdfplumber
import warnings
from datetime import datetime

# Silence openpyxl warnings regarding print areas (non-critical)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

logger = logging.getLogger(__name__)

def extract_transactions_from_pdf(uploaded_file):
    """
    Specifically parses Intesa Sanpaolo PDF bank statements using a line-based approach.
    Returns a list of dicts: [date, operation, details, amount, category_hint]
    """
    transactions = []
    
    # Regex patterns for ISP
    row_pattern = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}\.\d{2}\.\d{4})\s+(.*?)\s+([\d\.\s]+,\s*\d{2})$")
    
    with pdfplumber.open(uploaded_file) as pdf:
        current_tx = None
        
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            logger.info(f"   📄 [PDF] Processing page {i+1}/{page_count}...")
            text = page.extract_text()
            if not text: 
                continue
            
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if not line: continue
                
                match = row_pattern.match(line)
                if match:
                    if current_tx:
                        transactions.append(current_tx)
                    
                    date_str = match.group(1)
                    desc = match.group(3).strip()
                    amount_str = match.group(4).strip()
                    
                    def clean_amt(s):
                        s = s.replace(" ", "").replace(".", "").replace(",", ".")
                        try: return float(s)
                        except: return 0.0
                    
                    amount = clean_amt(amount_str)
                    
                    # Heuristic for sign (ISP specific)
                    is_credit = any(k in desc.lower() for k in ["favore", "accredito", "stipendio", "storno"])
                    if not is_credit:
                        amount = -abs(amount)
                    
                    current_tx = {
                        "date": datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d"),
                        "operation": desc,
                        "details": desc,
                        "amount": amount,
                        "category_hint": ""
                    }
                elif current_tx:
                    if any(k in line for k in ["Pagina", "ESTRATTO CONTO", "Saldo"]):
                        transactions.append(current_tx)
                        current_tx = None
                        continue
                    
                    current_tx["details"] += " " + line
                    if len(current_tx["operation"]) < 10:
                        current_tx["operation"] += " " + line

        if current_tx:
            transactions.append(current_tx)
            
    logger.info(f"   ✅ [PDF] Extraction finished: found {len(transactions)} potential transactions.")
    return transactions

def load_uploaded_file(uploaded_file, profile) -> pd.DataFrame:
    """
    Unified loader for PDF, CSV, and Excel files with buffer reset.
    """
    filename = getattr(uploaded_file, 'name', '').lower()
    mapping = profile.column_mapping
    
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
        
    try:
        if filename.endswith('.pdf'):
            data = extract_transactions_from_pdf(uploaded_file)
            df = pd.DataFrame(data)
            df = df.rename(columns={
                "date": mapping.date,
                "operation": mapping.operation,
                "details": mapping.details,
                "amount": mapping.amount,
                "category_hint": mapping.category_hint
            })
        elif filename.endswith('.csv'):
            df = pd.read_csv(
                uploaded_file, 
                skiprows=profile.skip_rows, 
                encoding=getattr(profile, 'encoding', 'utf-8'), 
                sep=getattr(profile, 'delimiter', ',')
            )
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, skiprows=profile.skip_rows, engine='openpyxl')
        elif filename.endswith('.xls'):
            df = pd.read_excel(uploaded_file, skiprows=profile.skip_rows)
        else:
            df = pd.read_excel(uploaded_file, skiprows=profile.skip_rows)
            
        return df
    except Exception as e:
        logger.error(f"❌ Error loading {filename}: {e}")
        raise ValueError(f"Could not read file {filename}. Error: {e}")
