import json
from src.models import ExpenseCategory, ExpenseExtraction, IncomeCategory, IncomeExtraction

EMAIL_PROMPT_TEMPLATE = "Data: {date}\nOrario: {time}\nTesto: {body}"

SYSTEM_EXPENSE_EXTRACTION_PROMPT = (
    "Sei un assistente che estrae transazioni bancarie in uscita da una email. Estrai solo le spese reali, "
    "ignorando saldi, messaggi promozionali e descrizioni non legate a spese.\n"
    "Rispondi con un JSON valido che rispetti esattamente la struttura del modello Pydantic sottostante.\n"
    "Schema modello: \n"
    f"{json.dumps(ExpenseExtraction.model_json_schema(), indent=2, ensure_ascii=False)}\n"
    "Usa esclusivamente le seguenti categorie: \n"
    + "\n".join(f"- {category.value}" for category in ExpenseCategory)
    + "\n"
    "Usa 'Altro' solo quando la spesa non rientra chiaramente in nessuna delle categorie sopra. "
    "Se una transazione è chiaramente un abbonamento, bolletta, cibo, trasporto o sport, "
    "classificala nella categoria più corretta anziché in 'Altro'."
)

SYSTEM_INCOME_EXTRACTION_PROMPT = (
    "Sei un assistente che estrae transazioni bancarie in entrata da una email. Estrai solo i bonifici ricevuti, "
    "ignorando messaggi promozionali, notifiche di saldo e dettagli non legati a entrate effettive.\n"
    "Rispondi con un JSON valido che rispetti esattamente la struttura del modello Pydantic sottostante.\n"
    "Schema modello: \n"
    f"{json.dumps(IncomeExtraction.model_json_schema(), indent=2, ensure_ascii=False)}\n"
    "Usa esclusivamente le seguenti categorie: \n"
    + "\n".join(f"- {category.value}" for category in IncomeCategory)
    + "\n"
    "Usa 'Altro' solo quando l'entrata non rientra chiaramente in nessuna delle categorie sopra. "
    "Se si tratta di stipendio, regalo, rimborso o saldo con amici, "
    "classificala nella categoria più corretta anziché in 'Altro'."
)
