from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Tipology(str, Enum):
    """Transaction direction: money going out or coming in."""
    Outgoing = "Outgoing"
    Incoming = "Incoming"


class OutgoingCategory(str, Enum):
    """Categories for outgoing transactions (money leaving the account)."""
    Subscriptions = "Subscriptions"
    Utilities = "Utilities"
    Home = "Home"
    Dining = "Dining"
    Shopping = "Shopping"
    Health = "Health"
    Transport = "Transport"
    Groceries = "Groceries"
    Savings = "Savings"
    Gifts = "Gifts"
    Financial = "Financial"
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
    reasoning: Optional[str] = Field(None, description="Step-by-step reasoning")
    category: OutgoingCategory = Field(..., description="Expense category")
    amount: Optional[float] = Field(None, description="Transaction amount (negative)")
    confidence: Optional[float] = Field(0.0, description="Classification confidence 0-1")


class IncomingClassification(BaseModel):
    """LLM classification result for incoming transactions."""
    reasoning: Optional[str] = Field(None, description="Step-by-step reasoning")
    category: IncomingCategory = Field(..., description="Income category")
    amount: Optional[float] = Field(None, description="Transaction amount (positive)")
    confidence: Optional[float] = Field(0.0, description="Classification confidence 0-1")