from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert, update
from src.database.models import Transaction, Category, Merchant, BankProfile
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_category(self, name: str, is_income: bool = False) -> Category:
        result = await self.db.execute(select(Category).filter(Category.name == name))
        category = result.scalar_one_or_none()
        if not category:
            category = Category(name=name, is_income=is_income)
            self.db.add(category)
            await self.db.flush()
        return category

    async def get_or_create_merchant(self, name: str) -> Merchant:
        result = await self.db.execute(select(Merchant).filter(Merchant.name == name))
        merchant = result.scalar_one_or_none()
        if not merchant:
            merchant = Merchant(name=name)
            self.db.add(merchant)
            await self.db.flush()
        return merchant

    async def get_or_create_bank_profile(self, name: str, config: str = None) -> BankProfile:
        result = await self.db.execute(select(BankProfile).filter(BankProfile.name == name))
        profile = result.scalar_one_or_none()
        if not profile:
            profile = BankProfile(name=name, config=config)
            self.db.add(profile)
            await self.db.flush()
        elif config:
            profile.config = config
            await self.db.flush()
        return profile

    async def get_merchant_catalogue(self) -> Dict[str, Dict[str, str]]:
        """Returns a dict mapping merchant names to their directional categories."""
        from sqlalchemy.orm import joinedload
        result = await self.db.execute(
            select(Merchant).options(
                joinedload(Merchant.default_outgoing_category),
                joinedload(Merchant.default_incoming_category)
            )
        )
        merchants = result.scalars().all()
        
        catalogue = {}
        for m in merchants:
            catalogue[m.name] = {
                "Outgoing": m.default_outgoing_category.name if m.default_outgoing_category else "Other",
                "Incoming": m.default_incoming_category.name if m.default_incoming_category else "Other"
            }
        return catalogue

    async def get_category_map(self) -> Dict[str, int]:
        """Returns a map of category names to their IDs."""
        result = await self.db.execute(select(Category))
        categories = result.scalars().all()
        return {c.name: c.id for c in categories}

    async def set_active_bank_profile(self, name: str):
        # 1. Deactivate all
        await self.db.execute(update(BankProfile).values(is_active=False))
        # 2. Activate one
        await self.db.execute(update(BankProfile).filter(BankProfile.name == name).values(is_active=True))
        await self.db.commit()

    async def get_active_bank_profile(self) -> Optional[BankProfile]:
        result = await self.db.execute(select(BankProfile).filter(BankProfile.is_active == True))
        return result.scalar_one_or_none()

    async def upsert_transactions(self, transactions_data: List[Dict]):
        """Bulk upsert transactions."""
        for data in transactions_data:
            # We use transaction ID (hash) as primary key
            tx_id = data.get("id")
            result = await self.db.execute(select(Transaction).filter(Transaction.id == tx_id))
            tx = result.scalar_one_or_none()
            
            if not tx:
                tx = Transaction(**data)
                self.db.add(tx)
            else:
                # Update existing if needed (e.g., status changed or re-classified)
                for key, value in data.items():
                    setattr(tx, key, value)
        
        await self.db.commit()
        logger.info(f"Upserted {len(transactions_data)} transactions.")
