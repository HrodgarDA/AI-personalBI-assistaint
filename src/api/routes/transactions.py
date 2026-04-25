from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func
from typing import List, Optional
from src.database.session import get_db
from src.database.models import Transaction as DBTransaction, Category as DBCategory
from src.api import schemas

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"]
)

@router.get("/", response_model=List[schemas.Transaction])
async def get_transactions(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(DBTransaction)
    if category_id:
        query = query.filter(
            (DBTransaction.ai_category_id == category_id) | 
            (DBTransaction.manual_category_id == category_id)
        )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{transaction_id}", response_model=schemas.Transaction)
async def get_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBTransaction).filter(DBTransaction.id == transaction_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.patch("/{transaction_id}", response_model=schemas.Transaction)
async def update_transaction(
    transaction_id: str,
    update_data: schemas.TransactionUpdate,
    db: AsyncSession = Depends(get_db)
):
    # Verify category exists if provided
    if update_data.manual_category_id:
        cat_result = await db.execute(select(DBCategory).filter(DBCategory.id == update_data.manual_category_id))
        if not cat_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category not found")

    query = update(DBTransaction).where(DBTransaction.id == transaction_id).values(
        **update_data.dict(exclude_unset=True)
    ).execution_options(synchronize_session="fetch")
    
    await db.execute(query)
    await db.commit()
    
    # Return updated transaction
    result = await db.execute(select(DBTransaction).filter(DBTransaction.id == transaction_id))
    return result.scalar_one()

@router.get("/stats/summary")
async def get_transaction_stats(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    import calendar

    # Base filters for current period
    filters = []
    if year:
        filters.append(func.extract('year', DBTransaction.date) == year)
    if month:
        filters.append(func.extract('month', DBTransaction.date) == month)

    # Total balance (unfiltered)
    total_res = await db.execute(
        select(func.sum(DBTransaction.amount).label("total"), func.count(DBTransaction.id).label("count"))
    )
    total_row = total_res.one()

    # Current period income/expense
    income_q = select(func.sum(DBTransaction.amount)).filter(DBTransaction.amount > 0)
    expense_q = select(func.sum(DBTransaction.amount)).filter(DBTransaction.amount < 0)
    if filters:
        income_q = income_q.filter(*filters)
        expense_q = expense_q.filter(*filters)

    monthly_income = (await db.execute(income_q)).scalar() or 0
    monthly_expense = abs((await db.execute(expense_q)).scalar() or 0)

    # Previous period for delta calculation
    prev_filters = []
    if year and month:
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_filters = [
            func.extract('year', DBTransaction.date) == prev_year,
            func.extract('month', DBTransaction.date) == prev_month,
        ]

    def pct_delta(curr, prev):
        if prev and prev != 0:
            return round(((curr - prev) / abs(prev)) * 100, 1)
        return None

    income_delta = None
    expense_delta = None
    savings_delta = None

    if prev_filters:
        prev_income = (await db.execute(
            select(func.sum(DBTransaction.amount)).filter(DBTransaction.amount > 0).filter(*prev_filters)
        )).scalar() or 0
        prev_expense = abs((await db.execute(
            select(func.sum(DBTransaction.amount)).filter(DBTransaction.amount < 0).filter(*prev_filters)
        )).scalar() or 0)
        prev_savings = prev_income - prev_expense
        income_delta = pct_delta(monthly_income, prev_income)
        expense_delta = pct_delta(monthly_expense, prev_expense)
        savings_delta = pct_delta(monthly_income - monthly_expense, prev_savings)

    return {
        "total_amount": total_row.total or 0,
        "transaction_count": total_row.count,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "monthly_savings": monthly_income - monthly_expense,
        "income_delta": income_delta,
        "expense_delta": expense_delta,
        "savings_delta": savings_delta,
    }

@router.get("/stats/daily")
async def get_daily_stats(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(
        DBTransaction.date,
        func.sum(DBTransaction.amount).label("value")
    ).group_by(DBTransaction.date).order_by(DBTransaction.date)
    
    if year:
        query = query.filter(func.extract('year', DBTransaction.date) == year)
    if month:
        query = query.filter(func.extract('month', DBTransaction.date) == month)
        
    result = await db.execute(query)
    return [{"name": str(row.date), "value": row.value} for row in result.all()]

@router.get("/stats/categories")
async def get_category_stats(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(
        func.coalesce(DBCategory.name, "Uncategorized").label("name"),
        func.sum(func.abs(DBTransaction.amount)).label("value")
    ).outerjoin(DBCategory, DBCategory.id == func.coalesce(DBTransaction.manual_category_id, DBTransaction.ai_category_id)).filter(DBTransaction.amount < 0).group_by(DBCategory.name)
    
    if year:
        query = query.filter(func.extract('year', DBTransaction.date) == year)
    if month:
        query = query.filter(func.extract('month', DBTransaction.date) == month)
        
    result = await db.execute(query)
    return [{"name": row.name, "value": round(row.value, 2)} for row in result.all()]

@router.get("/stats/flow")
async def get_flow_stats(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    # 1. Total Income
    income_query = select(func.sum(DBTransaction.amount)).filter(DBTransaction.amount > 0)
    expense_query = select(
        func.coalesce(DBCategory.name, "Other").label("name"),
        func.sum(func.abs(DBTransaction.amount)).label("value")
    ).outerjoin(DBCategory, DBCategory.id == func.coalesce(DBTransaction.manual_category_id, DBTransaction.ai_category_id)).filter(DBTransaction.amount < 0).group_by(DBCategory.name)
    
    if year:
        income_query = income_query.filter(func.extract('year', DBTransaction.date) == year)
        expense_query = expense_query.filter(func.extract('year', DBTransaction.date) == year)
    if month:
        income_query = income_query.filter(func.extract('month', DBTransaction.date) == month)
        expense_query = expense_query.filter(func.extract('month', DBTransaction.date) == month)

    income_res = await db.execute(income_query)
    total_income = income_res.scalar() or 0
    
    expense_res = await db.execute(expense_query)
    expenses = expense_res.all()
    
    nodes = [{"id": "Total Income"}]
    links = []
    
    for exp in expenses:
        nodes.append({"id": exp.name})
        links.append({
            "source": "Total Income",
            "target": exp.name,
            "value": float(exp.value)
        })
        
    return {"nodes": nodes, "links": links}
