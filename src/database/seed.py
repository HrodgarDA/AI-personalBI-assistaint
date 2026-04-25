import json
import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import AsyncSessionLocal
from src.database.models import Category, Merchant, BankProfile
from src.services.data_service import DataService

async def seed_database():
    async with AsyncSessionLocal() as db:
        data_service = DataService(db)
        
        # 1. Seed Categories (Standard ones)
        categories = [
            "Shopping", "Dining & Entertainment", "Groceries", "Other", 
            "Salary", "Subscriptions", "Transport", "Health & Sport", 
            "Refund", "Transfer", "Home", "Income", "Expense"
        ]
        
        cat_map = {}
        for cat_name in categories:
            cat = await data_service.get_or_create_category(cat_name)
            cat_map[cat_name] = cat.id
            
        # 2. Seed Merchant Catalogue
        catalogue_path = "data/merchant_catalogue.json"
        if os.path.exists(catalogue_path):
            with open(catalogue_path, "r", encoding="utf-8") as f:
                catalogue = json.load(f)
                
            for m_name, cat_data in catalogue.items():
                merchant = await data_service.get_or_create_merchant(m_name)
                
                outgoing_cat = cat_data.get("Outgoing")
                incoming_cat = cat_data.get("Incoming")
                
                if outgoing_cat and outgoing_cat in cat_map:
                    merchant.default_outgoing_category_id = cat_map[outgoing_cat]
                if incoming_cat and incoming_cat in cat_map:
                    merchant.default_incoming_category_id = cat_map[incoming_cat]
        
        # 3. Seed Bank Profiles from legacy JSON files
        profiles_dir = "data/profiles"
        active_name = ""
        if os.path.exists("data/active_profile.txt"):
            with open("data/active_profile.txt", "r") as f:
                active_name = f.read().strip()
        
        if os.path.exists(profiles_dir):
            for filename in os.listdir(profiles_dir):
                if filename.endswith(".json"):
                    p_name = filename.replace(".json", "")
                    with open(os.path.join(profiles_dir, filename), "r") as f:
                        config_data = json.load(f)
                        await data_service.get_or_create_bank_profile(p_name, config=json.dumps(config_data))
                        if p_name == active_name:
                            await data_service.set_active_bank_profile(p_name)
        
        # Fallback if no profiles found
        if not active_name:
            await data_service.get_or_create_bank_profile("Intesa Sanpaolo")
            await data_service.set_active_bank_profile("Intesa Sanpaolo")
        
        await db.commit()
        print("✅ Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_database())
