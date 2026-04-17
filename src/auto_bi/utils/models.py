from pydantic import BaseModel, Field, create_model
from typing import Optional, List, Type
from enum import Enum


class Tipology(str, Enum):
    """Transaction direction: money going out or coming in."""
    Outgoing = "Outgoing"
    Incoming = "Incoming"


# --- Common Model Base ---

class ClassificationBase(BaseModel):
    """Base fields for all transaction classifications."""
    reasoning: Optional[str] = Field(None, description="Step-by-step reasoning")
    amount: Optional[float] = Field(None, description="Transaction amount")
    confidence: Optional[float] = Field(0.0, description="Classification confidence 0-1")


# --- Dynamic Model Factory ---

def create_dynamic_classification_model(categories: List[str], tipology: str) -> Type[BaseModel]:
    """Generates a dynamic Pydantic mode with an Enum constrained by the provided categories."""
    enum_name = f"{tipology}Category"
    # Create the Enum dynamically from the provided list
    DynamicEnum = Enum(enum_name, {cat.replace(" ", "_"): cat for cat in categories})
    
    return create_model(
        f"{tipology}Classification",
        merchant=(str, Field(..., description="The cleaned name of the merchant (e.g. ZARA, Amazon, Spotify)")),
        category=(DynamicEnum, Field(..., description=f"The {tipology} category for this transaction")),
        __base__=ClassificationBase
    )


def create_batch_model(base_model: Type[BaseModel]) -> Type[BaseModel]:
    """Wraps a classification model into a list-based response for batch processing."""
    return create_model(
        "BatchResponse",
        results=(List[base_model], Field(..., description="List of classification results matching the input order"))
    )