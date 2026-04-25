from pydantic import BaseModel, Field
from datetime import date, time as time_type
from typing import Optional, List, Dict, Any

class CategoryBase(BaseModel):
    name: str
    is_income: bool = False
    type: Optional[str] = "expense"  # "income" | "expense"

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class MerchantBase(BaseModel):
    name: str
    default_outgoing_category_id: Optional[int] = None
    default_incoming_category_id: Optional[int] = None

class MerchantCreate(MerchantBase):
    pass

class Merchant(MerchantBase):
    id: int
    raw_names: List[str] = []
    transaction_count: int = 0

    class Config:
        from_attributes = True

class MerchantUpdate(BaseModel):
    default_outgoing_category_id: Optional[int] = None
    default_incoming_category_id: Optional[int] = None
    add_alias: Optional[str] = None
    remove_alias: Optional[str] = None

class TransactionBase(BaseModel):
    id: str
    date: date
    time: Optional[time_type] = None
    operation: str
    details: str
    amount: float
    bank_category_hint: Optional[str] = None
    status: str = "pending"
    ai_reasoning: Optional[str] = None

class TransactionCreate(TransactionBase):
    ai_category_id: Optional[int] = None
    manual_category_id: Optional[int] = None
    merchant_id: Optional[int] = None
    bank_profile_id: Optional[int] = None

class Transaction(TransactionBase):
    ai_category: Optional[Category] = None
    manual_category: Optional[Category] = None
    merchant: Optional[Merchant] = None

    class Config:
        from_attributes = True

class TransactionUpdate(BaseModel):
    manual_category_id: Optional[int] = None
    status: Optional[str] = None

class BankProfileBase(BaseModel):
    name: str
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: bool = False

class BankProfileCreate(BankProfileBase):
    pass

class BankProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None

class BankProfile(BankProfileBase):
    id: int

    class Config:
        from_attributes = True

class AnalysisResult(BaseModel):
    total_rows: int
    new_rows: int
    duplicate_rows: int = 0
    estimated_seconds: float
    avg_speed: float
    preview_rows: List[Dict[str, Any]] = []
    error: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    logs: List[str] = []
    result: Optional[dict] = None
