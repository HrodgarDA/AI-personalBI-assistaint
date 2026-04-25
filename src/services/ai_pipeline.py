import logging
import time
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database.models import Transaction as DBTransaction, Category, Merchant, BankProfile
from src.services.data_service import DataService
from src.services.extractor import TransactionParser
from src.utils.utils import extract_merchant_from_excel

logger = logging.getLogger(__name__)

class AIPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_service = DataService(db)
        self.parser = None

    async def run_full_extraction(self, bank_profile_id: int):
        """Processes all pending transactions for a given bank profile."""
        logger.info(f"🚀 Starting AI Pipeline for Bank Profile ID: {bank_profile_id}")
        
        # 1. Fetch pending transactions
        result = await self.db.execute(
            select(DBTransaction).filter(
                DBTransaction.bank_profile_id == bank_profile_id,
                DBTransaction.status == "pending"
            )
        )
        to_process = result.scalars().all()
        
        if not to_process:
            logger.info("✅ No pending transactions found.")
            return
        
        # 1b. Initialize Parser with DB data
        result = await self.db.execute(select(BankProfile).filter(BankProfile.id == bank_profile_id))
        db_p = result.scalar_one_or_none()
        if not db_p:
            logger.error(f"Bank Profile {bank_profile_id} not found.")
            return
            
        from src.utils.bank_profile import BankProfile as DomainProfile
        profile = DomainProfile.from_config(db_p.name, db_p.config)
        catalogue = await self.data_service.get_merchant_catalogue()
        
        self.parser = TransactionParser(
            profile=profile,
            merchant_catalogue=catalogue
        )
        
        logger.info(f"Found {len(to_process)} transactions to process.")
        
        # 2. Extract unique signatures (to avoid redundant LLM calls)
        groups = {}
        for tx in to_process:
            sig = (tx.operation, tx.details, tx.bank_category_hint, tx.amount)
            groups.setdefault(sig, []).append(tx)
            
        unique_sigs = list(groups.keys())
        logger.info(f"Grouped into {len(unique_sigs)} unique signatures.")
        
        # 3. Process each signature
        for sig in unique_sigs:
            op, det, bank_hint, amt = sig
            instances = groups[sig]
            
            # Use the existing parser logic (we can refactor this further later)
            # For now, let's use classify_batch for performance
            batch_inputs = [{
                "text": f"Operation: {op}\nDetails: {det}",
                "direction": "Incoming" if amt >= 0 else "Outgoing",
                "merchant": None,
                "amount": amt,
                "bank_category": bank_hint
            }]
            
            batch_results = self.parser.classify_batch(batch_inputs)
            res = batch_results[0]
            
            # 4. Persistence
            # Get or create Category and Merchant
            db_category = await self.data_service.get_or_create_category(
                res['category'], 
                is_income=(amt >= 0)
            )
            db_merchant = await self.data_service.get_or_create_merchant(res['merchant'])
            
            # Update all instances
            for tx in instances:
                tx.ai_category_id = db_category.id
                tx.merchant_id = db_merchant.id
                tx.ai_reasoning = res['reasoning']
                tx.status = "classified"
                
        await self.db.commit()
        logger.info("✅ AI Pipeline completed.")
