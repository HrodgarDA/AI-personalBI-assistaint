from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Tipology(str, Enum):
    """Transaction direction: money going out or coming in."""
    Outgoing = "Outgoing"
    Incoming = "Incoming"


class OutgoingCategory(str, Enum):
    """Categories for outgoing transactions (money leaving the account)."""
    Subscriptions = "Utilities & Subscriptions"
    Bills = "Bills for the house"
    Entertainment = "Dining & Entertainment"
    Shopping = "Shopping"
    Health = "Health & Fitness"
    Transport = "Transport & Fuel"
    Supermarket = "Supermarket"
    Savings = "Savings & Investments"
    Gifts = "Gifts"
    Transfers = "Transfers & Settlements"
    Other = "Other"


class IncomingCategory(str, Enum):
    """Categories for incoming transactions (money entering the account)."""
    Salary = "Salary"
    Refund = "Refund"
    Transfer = "Transfer"
    Gift = "Gift"
    Other = "Other"


class OutgoingClassification(BaseModel):
    """LLM classification result for outgoing transactions."""
    category: OutgoingCategory = Field(..., description="Expense category")
    amount: Optional[float] = Field(None, description="Transaction amount (negative). Extract from text if visible.")
    confidence: float = Field(..., description="Classification confidence 0-1")
    reasoning: Optional[str] = Field(None, description="Brief reasoning for the classification")


class IncomingClassification(BaseModel):
    """LLM classification result for incoming transactions."""
    category: IncomingCategory = Field(..., description="Income category")
    amount: Optional[float] = Field(None, description="Transaction amount (positive). Extract from text if visible.")
    confidence: float = Field(..., description="Classification confidence 0-1")
    reasoning: Optional[str] = Field(None, description="Brief reasoning for the classification")