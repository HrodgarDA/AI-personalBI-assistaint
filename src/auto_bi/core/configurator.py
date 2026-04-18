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
    invert_signs: bool = Field(False, description="Set to true if expenses are positive and income is negative (uncommon)")

class GhostModelManager:
    """Manages downloading and removing heavy models for configuration."""
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.pull_successful = False
        self.was_already_present = False

    def __enter__(self):
        logger.info(f"👻 Ghost Model Strategy: analyzing {self.model_id}...")
        try:
            # Check if already exists
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if self.model_id in res.stdout:
                logger.info(f"Model {self.model_id} already available. Skipping pull and will PRESERVE it after use.")
                self.was_already_present = True
                self.pull_successful = True # Mark as successful to allow execution
                return self
            
            # Pull model (only if ghost)
            logger.info(f"Model {self.model_id} not found. Pulling temporary ghost...")
            t0 = time.time()
            subprocess.run(["ollama", "pull", self.model_id], check=True)
            self.pull_successful = True
            logger.info(f"Model {self.model_id} pulled successfully in {time.time() - t0:.2f}s.")
        except Exception as e:
            logger.error(f"Failed to manage ghost model {self.model_id}: {e}")
            self.pull_successful = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We NEVER delete llama3:8b as it is now our primary persistent model
        if self.model_id == "llama3:8b":
            logger.info(f"✨ Ghost Model Strategy: preserving {self.model_id} as the primary application model.")
            return

        if self.pull_successful and not self.was_already_present:
            logger.info(f"🗑️ Ghost Model Strategy: removing {self.model_id} to save space...")
            try:
                subprocess.run(["ollama", "rm", self.model_id], check=True)
            except Exception as e:
                logger.warning(f"Failed to remove model {self.model_id}: {e}")
        elif self.was_already_present:
            logger.info(f"✨ Ghost Model Strategy: preserving {self.model_id} as it was already on system.")


def detect_file_params(file_path: str) -> dict:
    """Detect encoding and delimiter for CSV files."""
    params = {"encoding": "utf-8", "delimiter": ","}
    if not file_path.endswith('.csv'):
        return params
        
    encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
    delimiters = [",", ";", "\t", "|"]
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read(4096)
                # Success if we can read 4k bytes
                params["encoding"] = enc
                
                # Check for delimiter in the first few lines
                lines = content.split('\n')[:5]
                counts = {d: 0 for d in delimiters}
                for line in lines:
                    for d in delimiters:
                        counts[d] += line.count(d)
                
                best_d = max(counts, key=counts.get)
                if counts[best_d] > 0:
                    params["delimiter"] = best_d
                return params
        except Exception:
            continue
    return params

def detect_skip_rows(file_path: str, encoding: str = "utf-8", delimiter: str = ",") -> int:
    """Detect how many rows to skip to reach the header."""
    try:
        lines = []
        if file_path.endswith('.csv'):
            with open(file_path, 'r', encoding=encoding) as f:
                for _ in range(50):
                    line = f.readline()
                    if not line: break
                    lines.append([c.strip() for c in line.split(delimiter)])
        else:
            # For Excel we still use pandas as it's more complex to read raw
            df_raw = pd.read_excel(file_path, header=None, nrows=50)
            lines = df_raw.fillna("").values.tolist()
        
        for idx, row in enumerate(lines):
            # Criterion: A row is likely a header if it contains >=3 strings that have letters
            valid_cells = [str(c).strip() for c in row if c and str(c).strip()]
            if len(valid_cells) >= 3:
                words_count = sum(1 for c in valid_cells if any(char.isalpha() for char in c))
                if words_count >= 3:
                    logger.info(f"Detected likely header at row {idx}")
                    return int(idx)
    except Exception as e:
        logger.error(f"Error detecting skip rows: {e}")
    
    return 0

def auto_configure_bank_profile(file_path: str, model_id: str = "llama3:8b") -> Optional[BankProfile]:
    """Analyze a bank file and generate a suggested BankProfile."""
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
    
    start_time = time.time()
    params = detect_file_params(file_path)
    encoding = params["encoding"]
    delimiter = params["delimiter"]
    
    skip_rows = detect_skip_rows(file_path, encoding=encoding, delimiter=delimiter)
    
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, skiprows=skip_rows, nrows=5, encoding=encoding, sep=delimiter)
        else:
            df = pd.read_excel(file_path, skiprows=skip_rows, nrows=5)
            
        # Force all column names to strings 
        headers = [str(h) for h in df.columns]
        
        # Convert all values to string to ensure JSON serializability
        sample_rows = df.head(3).astype(str).to_dict(orient='records')
        
        with GhostModelManager(model_id) as gmm:
            client = instructor.from_openai(
                OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"),
                mode=instructor.Mode.JSON,
            )
            
            logger.info(f"🚀 AI Discovery started using {model_id}...")
            t_ai_start = time.time()
            prompt = (
                "You are an expert financial data analyst.\n"
                "I am providing you with the column headers and 3 sample rows from a bank statement file.\n"
                "Your task is to identify which column corresponds to our internal schema requirements.\n\n"
                f"HEADERS: {headers}\n"
                f"SAMPLE DATA: {json.dumps(sample_rows, ensure_ascii=False)}\n\n"
                "Map them to: date, operation, details, amount, and category_hint (if available).\n"
                "Guess the date format string (e.g., %d/%m/%Y).\n"
                "Also check if the signs are inverted (expenses are positive, income is negative). "
                "Look at row descriptions: if 'AMAZON' is positive, invert_signs is likely True."
            )
            
            mapping = client.chat.completions.create(
                model=model_id,
                response_model=ColumnMappingResult,
                messages=[{"role": "user", "content": prompt}]
            )
            logger.info(f"✨ AI Model Response received in {time.time() - t_ai_start:.2f}s.")
            
            # --- Smart Validation Step ---
            # Try to parse the dates from sample_rows with the guessed format
            date_col = mapping.date_col
            date_format = mapping.date_format_hint
            validation_success = True
            
            for row in sample_rows:
                raw_val = row.get(date_col)
                if raw_val:
                    try:
                        pd.to_datetime(raw_val, format=date_format)
                    except Exception:
                        validation_success = False
                        break
            
            if not validation_success:
                logger.warning(f"AI guessed format {date_format} failed validation. Retrying with loose parsing...")
                mapping.date_format_hint = "" # Let pandas infer later
            
            # Create the profile
            profile = BankProfile(
                profile_name=f"Auto-configured ({os.path.basename(file_path)})",
                skip_rows=skip_rows,
                encoding=encoding,
                delimiter=delimiter,
                invert_signs=mapping.invert_signs,
                column_mapping=ColumnMapping(
                    date=mapping.date_col,
                    operation=mapping.operation_col,
                    details=mapping.details_col,
                    amount=mapping.amount_col,
                    category_hint=mapping.category_hint_col or "Categoria"
                ),
                date_format=mapping.date_format_hint
            )
            logger.info(f"✅ Auto-configuration completed in {time.time() - start_time:.2f}s.")
            return profile
            
    except Exception as e:
        logger.error(f"Auto-configuration failed: {e}")
        return None
