import logging
import hashlib
import pandas as pd
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Transaction, BankProfile
from src.database.session import get_db
from src.services.data_service import DataService
from src.services.ingestion import load_uploaded_file
from src.utils.bank_profile import load_bank_profile

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_service = DataService(db)

    async def ingest_file(self, file_path: str, bank_profile_id: int):
        """Parses a file and saves transactions to the database."""
        # Fetch profile from DB
        result = await self.db.execute(select(BankProfile).filter(BankProfile.id == bank_profile_id))
        db_p = result.scalar_one_or_none()
        if not db_p:
            logger.error(f"Bank Profile {bank_profile_id} not found.")
            return 0
            
        from src.utils.bank_profile import BankProfile as DomainProfile
        profile = DomainProfile.from_config(db_p.name, db_p.config)
        mapping = profile.column_mapping
        
        # Load file using the existing logic (handling PDF, XLSX, CSV)
        with open(file_path, "rb") as f:
            # We mock a 'name' attribute for load_uploaded_file
            f.name = file_path
            df = load_uploaded_file(f, profile)
            
        # Deduplication and processing logic
        new_transactions = []
        local_occ_tracker = {}
        
        for idx, row in df.iterrows():
            # Robust date parsing (simplified for now, using the same logic as ingestion.py)
            raw_date = row[mapping.date]
            try:
                parsed_dt = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
                date_str = parsed_dt.strftime("%Y-%m-%d") if pd.notna(parsed_dt) else str(raw_date)
                date_val = parsed_dt.date() if pd.notna(parsed_dt) else None
            except Exception:
                date_str = str(raw_date)
                date_val = None
                
            operation = str(row[mapping.operation])
            details = str(row[mapping.details]) if mapping.details in df.columns and pd.notna(row[mapping.details]) else ""
            
            try:
                amount = float(row[mapping.amount])
                if getattr(profile, 'invert_signs', False):
                    amount = -amount
            except (ValueError, TypeError):
                amount = 0.0
                
            # Stable ID logic
            signature = f"{date_str}_{operation}_{amount}_{details}"
            occ_count = local_occ_tracker.get(signature, 0)
            local_occ_tracker[signature] = occ_count + 1
            
            hash_string = f"{signature}_{occ_count}".encode('utf-8')
            pseudo_id = hashlib.md5(hash_string).hexdigest()
            
            # Category hint
            bank_category = ""
            if mapping.category_hint in df.columns:
                val = row[mapping.category_hint]
                if pd.notna(val) and str(val).strip().lower() not in ["", "nan", "n.d."]:
                    bank_category = str(val).strip()
            
            new_transactions.append({
                "id": pseudo_id,
                "date": date_val,
                "time": None, # or extract if possible
                "operation": operation,
                "details": details,
                "amount": amount,
                "bank_category_hint": bank_category,
                "bank_profile_id": bank_profile_id,
                "status": "pending"
            })
            
        await self.data_service.upsert_transactions(new_transactions)
        return len(new_transactions)

    async def analyze_file(self, file_path: str, bank_profile_id: int):
        """Analyzes a file and returns metrics (total, new, estimated time)."""
        result = await self.db.execute(select(BankProfile).filter(BankProfile.id == bank_profile_id))
        db_p = result.scalar_one_or_none()
        if not db_p:
            return {"error": "Profile not found"}
            
        from src.utils.bank_profile import BankProfile as DomainProfile
        profile = DomainProfile.from_config(db_p.name, db_p.config)
        mapping = profile.column_mapping
        
        with open(file_path, "rb") as f:
            f.name = file_path
            df = load_uploaded_file(f, profile)
            
        total_rows = len(df)
        new_count = 0
        local_occ_tracker = {}
        
        for idx, row in df.iterrows():
            # ID generation logic (must match ingest_file exactly)
            raw_date = row[mapping.date]
            try:
                parsed_dt = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
                date_str = parsed_dt.strftime("%Y-%m-%d") if pd.notna(parsed_dt) else str(raw_date)
            except Exception:
                date_str = str(raw_date)
            
            operation = str(row[mapping.operation])
            details = str(row[mapping.details]) if mapping.details in df.columns and pd.notna(row[mapping.details]) else ""
            
            try:
                amount = float(row[mapping.amount])
                if getattr(profile, 'invert_signs', False):
                    amount = -amount
            except (ValueError, TypeError):
                amount = 0.0
                
            signature = f"{date_str}_{operation}_{amount}_{details}"
            occ_count = local_occ_tracker.get(signature, 0)
            local_occ_tracker[signature] = occ_count + 1
            
            hash_string = f"{signature}_{occ_count}".encode('utf-8')
            pseudo_id = hashlib.md5(hash_string).hexdigest()
            
            # Check if exists in DB
            from src.database.models import Transaction as DBTransaction
            res = await self.db.execute(select(DBTransaction).filter(DBTransaction.id == pseudo_id))
            if not res.scalar_one_or_none():
                new_count += 1
                
        avg_speed = 1.5 # Default seconds per transaction
        return {
            "total_rows": total_rows,
            "new_rows": new_count,
            "estimated_seconds": new_count * avg_speed,
            "avg_speed": avg_speed
        }
