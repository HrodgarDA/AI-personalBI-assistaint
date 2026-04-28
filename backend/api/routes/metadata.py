from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database.session import get_db
from backend.database.models import Category, Merchant, BankProfile

router = APIRouter()

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    return result.scalars().all()

@router.get("/merchants")
async def get_merchants(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Merchant))
    return result.scalars().all()

@router.get("/profiles")
async def get_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankProfile))
    return result.scalars().all()

@router.post("/profiles")
async def create_profile(profile_data: dict, db: AsyncSession = Depends(get_db)):
    # Simple dict-based creation for now
    profile = BankProfile(
        id=profile_data["name"],
        name=profile_data["name"],
        config=profile_data.get("config", {})
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.delete("/profiles/{profile_name}")
async def delete_profile(profile_name: str, db: AsyncSession = Depends(get_db)):
    profile = await db.get(BankProfile, profile_name)
    if profile:
        await db.delete(profile)
        await db.commit()
    return {"status": "deleted"}
