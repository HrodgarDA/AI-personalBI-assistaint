from sqlalchemy import Column, Integer, String, Float, Date, Time, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.database.session import Base

class BankProfile(Base):
    __tablename__ = "bank_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    config = Column(String, nullable=True) # Stores the JSON configuration
    is_active = Column(Boolean, default=False)
    
    transactions = relationship("Transaction", back_populates="bank_profile")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_income = Column(Boolean, default=False)
    
    merchants_outgoing = relationship("Merchant", foreign_keys="[Merchant.default_outgoing_category_id]", back_populates="default_outgoing_category")
    merchants_incoming = relationship("Merchant", foreign_keys="[Merchant.default_incoming_category_id]", back_populates="default_incoming_category")

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    default_outgoing_category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    default_incoming_category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    default_outgoing_category = relationship("Category", foreign_keys=[default_outgoing_category_id], back_populates="merchants_outgoing")
    default_incoming_category = relationship("Category", foreign_keys=[default_incoming_category_id], back_populates="merchants_incoming")
    
    transactions = relationship("Transaction", back_populates="merchant")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True) # Using the MD5 hash from the data
    date = Column(Date, index=True)
    time = Column(Time, nullable=True)
    operation = Column(String)
    details = Column(String)
    amount = Column(Float)
    bank_category_hint = Column(String, nullable=True)
    
    # Classification fields
    ai_category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    manual_category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=True)
    bank_profile_id = Column(Integer, ForeignKey("bank_profiles.id"), nullable=True)
    
    status = Column(String, default="pending") # pending, classified, verified
    ai_reasoning = Column(String, nullable=True) # Logic/thoughts from the LLM
    
    bank_profile = relationship("BankProfile", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    ai_category = relationship("Category", foreign_keys=[ai_category_id])
    manual_category = relationship("Category", foreign_keys=[manual_category_id])
