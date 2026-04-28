from sqlalchemy import Column, String, Float, Date, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.database.session import Base

from pgvector.sqlalchemy import Vector

class BankProfile(Base):
    """Configuration and rules for specific bank statement formats."""
    __tablename__ = "bank_profiles"
    name = Column(String, primary_key=True)
    config = Column(JSON)  # extraction rules
    is_active = Column(Boolean, default=True)

class Category(Base):
    """Financial categories for transaction classification."""
    __tablename__ = "categories"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True)
    is_income = Column(Boolean, default=False)

class Merchant(Base):
    """Identified merchants with their default categories and embeddings."""
    __tablename__ = "merchants"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True)
    default_outgoing_category_id = Column(String, ForeignKey("categories.id"), nullable=True)
    embedding = Column(Vector(1024))
    
    default_category = relationship("Category")

class Transaction(Base):
    """Core transaction record containing amount, date, type, and classification info."""
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)  # MD5 hash
    amount = Column(Float)
    date = Column(Date)
    transaction_type = Column(String)  # Incoming/Outgoing (previously 'tipology')
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=True)
    category_id = Column(String, ForeignKey("categories.id"), nullable=True)
    status = Column(String, default="pending")  # pending/classified/verified
    original_operation = Column(String)
    original_details = Column(String)
    ai_reasoning = Column(String)
    confidence = Column(Float, default=0.0)
    embedding = Column(Vector(1024))
    
    merchant = relationship("Merchant")
    category = relationship("Category")

class RegexRule(Base):
    """Regex-based automation rules for instant transaction classification."""
    __tablename__ = "regex_rules"
    id = Column(String, primary_key=True)
    pattern = Column(String, unique=True)
    merchant_name = Column(String)
    category_id = Column(String, ForeignKey("categories.id"))
    transaction_type = Column(String, default="Outgoing")
