from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class TransactionDirection(str, Enum):
    """Direzione della transazione: entrata o uscita."""
    Expense = "expense"
    Income = "income"

class ExpenseCategory(str, Enum):
    """Possibili categorie per classificare le transazioni bancarie."""
    Abbonamenti = "Utenze e Abbonamenti mensili"
    Casa = "Utenze e spese per la casa"
    Svago = "Ristoranti e Tempo Libero"
    Sport = "Sport, fitness e Benessere"
    Trasporti = "Trasporti e Carburante"
    Risparmi = "Risparmi e Investimenti"
    Stipendio = "Stipendio"
    Regali = "Regali"
    Rimborsi = "Rimborsi e Condivisione"
    Altro = "Altro"

class ExpenseRecord(BaseModel):
    """Schema per una singola transazione bancaria."""
    direction: TransactionDirection = Field(..., description="Tipo di transazione: income o expense")
    category: ExpenseCategory = Field(..., description="Categoria della transazione")
    amount: float = Field(..., description="Importo speso o ricevuto (valore numerico)")
    date: str = Field(..., description="Data della transazione trovata nell'email")
    time: str = Field(..., description="Orario della transazione trovata nell'email")
    confidence: float = Field(..., description="Livello di confidenza dell'estrazione (0-1)")
    reasoning: str = Field(None, description="Motivazione o spiegazione dell'estrazione")

class ExpenseExtraction(BaseModel):
    """Contenitore per i risultati estratti dall'LLM."""
    expenses: List[ExpenseRecord]

class IncomeCategory(str, Enum):
    """Possibili categorie di entrata per classificare i bonifici in entrata."""
    Stipendio = "Stipendio"
    Regali = "Regali"
    Rimborsi = "Rimborsi"
    Saldi = "Saldi con amici"
    Altro = "Altro"

class IncomeRecord(BaseModel):
    """Schema per una singola entrata bancaria."""
    category: IncomeCategory = Field(..., description="Categoria dell'entrata")
    amount: float = Field(..., description="Importo ricevuto (valore numerico)")
    date: str = Field(..., description="Data della transazione trovata nell'email")
    time: str = Field(..., description="Orario della transazione trovata nell'email")
    confidence: float = Field(..., description="Livello di confidenza dell'estrazione (0-1)")
    reasoning: str = Field(None, description="Motivazione o spiegazione dell'estrazione")

class IncomeExtraction(BaseModel):
    """Contenitore per i risultati estratti per le entrate."""
    incomes: List[IncomeRecord]
    