from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class Tipology(str, Enum):
    """Transaction typology: Expense, Refund, or Salary."""
    Expense = "Expense"
    Refund = "Refund"
    Salary = "Salary"

class TransactionCategory(str, Enum):
    """Possible categories for classifying transactions."""
    Subscriptions = "Utilities & Subscriptions"
    Bills = "Bills for the house"
    Entertainment = "Dining & Entertainment"
    Shopping = "Shopping"
    Health = "Health & Fitness"
    Transport = "Transport & Fuel"
    Supermarket = "Supermarket"
    Savings = "Savings & Investments"
    Refunds = "Refunds"
    Salary = "Salary"
    Gifts = "Gifts"
    Transfers = "Transfers & Settlements"
    Other = "Other"

class TransactionRecord(BaseModel):
    """Schema for a single bank transaction (expense, refund, or salary)."""
    tipology: Tipology = Field(..., description="Transaction type: Expense (negative), Refund (positive), or Salary (positive)")
    merchant: str = Field(..., description="Merchant name")
    category: TransactionCategory = Field(..., description="Transaction category")
    amount: float = Field(..., description="Transaction amount. MUST be negative for Expense, and positive for Salary or Refund.")
    date: str = Field(..., description="Transaction date found in the email")
    time: str = Field(..., description="Transaction time found in the email")
    confidence: float = Field(..., description="Extraction confidence level (0-1)")
    reasoning: str = Field(None, description="Extraction reasoning, specifying the rationale behind the selected sign and category")

class TransactionExtraction(BaseModel):
    """Container for LLM extracted results."""
    transactions: List[TransactionRecord]