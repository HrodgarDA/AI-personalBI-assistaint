import os
import json
import logging
import pandas as pd
import subprocess
import time
import instructor
from openai import OpenAI
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from auto_bi.utils.bank_profile import BankProfile, ColumnMapping
from auto_bi.utils.config import OLLAMA_BASE_URL

logger = logging.getLogger(__name__)

class ColumnMappingResult(BaseModel):
    """Result of LLM mapping column names to internal schema."""
    date_col: str = Field(..., description="Column name for transaction date")
    operation_col: str = Field(..., description="Column name for operation type/description")
    details_col: str = Field(..., description="Column name for technical details/description")
    amount_col: str = Field(..., description="Column name for transaction amount")
    category_hint_col: Optional[str] = Field(None, description="Column name for bank categories (if any)")
    date_format_hint: str = Field("%d/%m/%Y", description="Probable strftime format of the date column")

class GhostModelManager:
    """Manages downloading and removing heavy models for configuration."""
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.pull_successful = False

    def __enter__(self):
        logger.info(f"👻 Ghost Model Strategy: pulling {self.model_id}...")
        try:
            # Check if already exists
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if self.model_id in res.stdout:
                logger.info(f"Model {self.model_id} already available.")
                self.pull_successful = True
                return self
            
            # Pull model
            subprocess.run(["ollama", "pull", self.model_id], check=True)
            self.pull_successful = True
            logger.info(f"Model {self.model_id} pulled successfully.")
        except Exception as e:
            logger.error(f"Failed to manage ghost model {self.model_id}: {e}")
            self.pull_successful = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pull_successful:
            logger.info(f"🗑️ Ghost Model Strategy: removing {self.model_id} to save space...")
            try:
                subprocess.run(["ollama", "rm", self.model_id], check=True)
            except Exception as e:
                logger.warning(f"Failed to remove model {self.model_id}: {e}")


def detect_skip_rows(file_path: str) -> int:
    """Detect how many rows to skip to reach the header."""
    try:
        if file_path.endswith('.csv'):
            # For CSV we read raw lines first to see the structure
            df_raw = pd.read_csv(file_path, header=None, nrows=50)
        else:
            df_raw = pd.read_excel(file_path, header=None, nrows=50)
        
        for idx, row in df_raw.iterrows():
            # Criterion: A row is likely a header if it contains >3 strings that are not numbers
            # and it's followed by rows that look like data.
            valid_cells = [str(c).strip() for c in row if pd.notna(c) and str(c).strip()]
            if len(valid_cells) >= 3:
                # Check if it looks like headers (words, not just codes)
                words_count = sum(1 for c in valid_cells if any(char.isalpha() for char in c))
                if words_count >= 3:
                    logger.info(f"Detected likely header at row {idx}")
                    return int(idx)
    except Exception as e:
        logger.error(f"Error detecting skip rows: {e}")
    
    return 0

def auto_configure_bank_profile(file_path: str, model_id: str = "llama3:8b") -> Optional[BankProfile]:
    """Analyze a bank file and generate a suggested BankProfile."""
    skip_rows = detect_skip_rows(file_path)
    
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, skiprows=skip_rows, nrows=5)
        else:
            df = pd.read_excel(file_path, skiprows=skip_rows, nrows=5)
            
        headers = df.columns.tolist()
        sample_rows = df.head(3).to_dict(orient='records')
        
        with GhostModelManager(model_id) as gmm:
            client = instructor.from_openai(
                OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"),
                mode=instructor.Mode.JSON,
            )
            
            prompt = (
                "You are an expert financial data analyst.\n"
                "I am providing you with the column headers and 3 sample rows from a bank statement file.\n"
                "Your task is to identify which column corresponds to our internal schema requirements.\n\n"
                f"HEADERS: {headers}\n"
                f"SAMPLE DATA: {json.dumps(sample_rows, ensure_ascii=False)}\n\n"
                "Map them to: date, operation, details, amount, and category_hint (if available).\n"
                "Also, guess the date format string (e.g., %d/%m/%Y)."
            )
            
            mapping = client.chat.completions.create(
                model=model_id,
                response_model=ColumnMappingResult,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Create the profile
            profile = BankProfile(
                profile_name=f"Auto-configured ({os.path.basename(file_path)})",
                skip_rows=skip_rows,
                column_mapping=ColumnMapping(
                    date=mapping.date_col,
                    operation=mapping.operation_col,
                    details=mapping.details_col,
                    amount=mapping.amount_col,
                    category_hint=mapping.category_hint_col or "Categoria"
                ),
                date_format=mapping.date_format_hint
            )
            return profile
            
    except Exception as e:
        logger.error(f"Auto-configuration failed: {e}")
        return None
