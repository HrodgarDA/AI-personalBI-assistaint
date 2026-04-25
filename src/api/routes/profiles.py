from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import json

from src.database.session import get_db
from src.database.models import BankProfile as DBBankProfile
from src.api import schemas
from src.services.data_service import DataService

router = APIRouter(
    prefix="/profiles",
    tags=["profiles"]
)

@router.get("/", response_model=List[schemas.BankProfile])
async def get_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBBankProfile))
    return result.scalars().all()

@router.get("/{profile_id}", response_model=schemas.BankProfile)
async def get_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBBankProfile).filter(DBBankProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/", response_model=schemas.BankProfile)
async def create_profile(profile_data: schemas.BankProfileCreate, db: AsyncSession = Depends(get_db)):
    data_service = DataService(db)
    # Convert Pydantic config to JSON string
    config_json = json.dumps(profile_data.config) if profile_data.config else None
    profile = await data_service.get_or_create_bank_profile(profile_data.name, config=config_json)
    await db.commit()
    return profile

@router.patch("/{profile_id}", response_model=schemas.BankProfile)
async def update_profile(
    profile_id: int, 
    update_data: schemas.BankProfileUpdate, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DBBankProfile).filter(DBBankProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if update_data.name:
        profile.name = update_data.name
    if update_data.description:
        profile.description = update_data.description
    if update_data.config:
        profile.config = json.dumps(update_data.config)
    if update_data.is_active is not None:
        if update_data.is_active:
            data_service = DataService(db)
            await data_service.set_active_bank_profile(profile.name)
        else:
            profile.is_active = False
            
    await db.commit()
    await db.refresh(profile)
    return profile
