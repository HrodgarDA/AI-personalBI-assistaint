from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from src.database.session import get_db
from src.database.models import Transaction
from src.services.learning import learning_service
from pydantic import BaseModel
from datetime import date

router = APIRouter()

class TransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    merchant_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None

@router.get("/")
async def get_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Transaction)
    if start_date:
        query = query.where(Transaction.date >= start_date)
    if end_date:
        query = query.where(Transaction.date <= end_date)
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if status:
        query = query.where(Transaction.status == status)
    
    result = await db.execute(query.order_by(Transaction.date.desc()))
    return result.scalars().all()

@router.patch("/{transaction_id}")
async def update_transaction(
    transaction_id: str, 
    update: TransactionUpdate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if merchant/category changed for learning
    old_merch = transaction.merchant_id
    old_cat = transaction.category_id

    for key, value in update.dict(exclude_unset=True).items():
        setattr(transaction, key, value)
    
    await db.commit()
    await db.refresh(transaction)

    # Learning Loop: If changed, suggest a new rule
    if (update.merchant_id and update.merchant_id != old_merch) or \
       (update.category_id and update.category_id != old_cat):
        background_tasks.add_task(
            learning_service.learn_from_edit, 
            transaction_id, 
            transaction.merchant_id, 
            transaction.category_id
        )

    return transaction

@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    await db.delete(transaction)
    await db.commit()
    return {"message": "Transaction deleted"}
