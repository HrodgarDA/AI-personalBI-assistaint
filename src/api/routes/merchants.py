from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from sqlalchemy.orm import selectinload

from src.database.session import get_db
from src.database.models import Merchant as DBMerchant, Transaction as DBTransaction
from src.api import schemas

router = APIRouter(
    prefix="/merchants",
    tags=["merchants"]
)

@router.get("/", response_model=List[schemas.Merchant])
async def get_merchants(db: AsyncSession = Depends(get_db)):
    # Fetch all merchants
    result = await db.execute(
        select(DBMerchant).options(
            selectinload(DBMerchant.default_outgoing_category),
            selectinload(DBMerchant.default_incoming_category)
        )
    )
    merchants = result.scalars().all()

    # Compute transaction_count and raw_names for each merchant
    tx_result = await db.execute(
        select(
            DBTransaction.merchant_id,
            func.count(DBTransaction.id).label("count"),
        ).group_by(DBTransaction.merchant_id)
    )
    count_map = {row.merchant_id: row.count for row in tx_result}

    # Get distinct operation strings per merchant (acts as raw names)
    raw_result = await db.execute(
        select(DBTransaction.merchant_id, DBTransaction.operation)
        .distinct()
        .filter(DBTransaction.merchant_id.is_not(None))
    )
    raw_map: dict[int, list] = {}
    for row in raw_result:
        raw_map.setdefault(row.merchant_id, [])
        if row.operation and row.operation not in raw_map[row.merchant_id]:
            raw_map[row.merchant_id].append(row.operation)

    # Build response dicts
    out = []
    for m in merchants:
        d = {
            "id": m.id,
            "name": m.name,
            "default_outgoing_category_id": m.default_outgoing_category_id,
            "default_incoming_category_id": m.default_incoming_category_id,
            "transaction_count": count_map.get(m.id, 0),
            "raw_names": raw_map.get(m.id, []),
        }
        out.append(d)

    return out


@router.patch("/{merchant_id}", response_model=schemas.Merchant)
async def update_merchant(
    merchant_id: int,
    merchant_update: schemas.MerchantUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DBMerchant).filter(DBMerchant.id == merchant_id))
    db_merchant = result.scalar_one_or_none()
    if not db_merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    update_data = merchant_update.dict(exclude_unset=True)

    # Handle alias add/remove — skip if no aliases column on model
    update_data.pop("add_alias", None)
    update_data.pop("remove_alias", None)

    for key, value in update_data.items():
        if hasattr(db_merchant, key):
            setattr(db_merchant, key, value)

    await db.commit()
    await db.refresh(db_merchant)

    # Return enriched response
    tx_result = await db.execute(
        select(func.count(DBTransaction.id)).filter(DBTransaction.merchant_id == merchant_id)
    )
    count = tx_result.scalar() or 0

    raw_result = await db.execute(
        select(DBTransaction.operation).distinct().filter(DBTransaction.merchant_id == merchant_id)
    )
    raw_names = [r.operation for r in raw_result if r.operation]

    return {
        "id": db_merchant.id,
        "name": db_merchant.name,
        "default_outgoing_category_id": db_merchant.default_outgoing_category_id,
        "default_incoming_category_id": db_merchant.default_incoming_category_id,
        "transaction_count": count,
        "raw_names": raw_names,
    }
