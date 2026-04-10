from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ExpenseCategory(str, Enum):
    """Possibili categorie di spesa per classificare le transazioni bancarie."""
    Abbonamenti = "Utenze e Abbonamenti mensili"
    Casa = "Utenze e spese per la casa"
    Svago = "Svago, Sport, Ristoranti e Tempo Libero"
    Trasporti = "Trasporti e Carburante"
    Risparmi = "Risparmi e Investimenti"
    Altro = "Altro"

class ExpenseRecord(BaseModel):
    """Schema per una singola transazione bancaria."""
    category: ExpenseCategory = Field(..., description="Categoria della spesa")
    amount: float = Field(..., description="Importo speso (valore numerico)")
    date: str = Field(..., description="Data della transazione trovata nell'email")
    time: str = Field(..., description="Orario della transazione trovata nell'email")
    description: Optional[str] = Field(None, description="Descrizione o dettagli aggiuntivi dellaq transazione")
    confidence: float = Field(..., description="Livello di confidenza dell'estrazione (0-1)")

class ExpenseExtraction(BaseModel):
    """Contenitore per i risultati estratti dall'LLM."""
    expenses: List[ExpenseRecord]