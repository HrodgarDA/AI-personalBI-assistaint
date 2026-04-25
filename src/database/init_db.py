import asyncio
import os
import sys

# Add src to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.database.session import engine, Base
from src.database.models import Category, Merchant, BankProfile, Transaction
from src.database.seed import seed_database

async def init_db():
    print("🚀 Initializing database...")
    async with engine.begin() as conn:
        # Drop all tables to start fresh (ONLY FOR DEV!)
        print("🗑️ Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        print("🏗️ Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed data
    print("🌱 Seeding database...")
    await seed_database()
    print("✨ Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(init_db())
