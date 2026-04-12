import json
from src.models import TransactionCategory, TransactionExtraction

EMAIL_PROMPT_TEMPLATE = "Date: {date}\nTime: {time}\nSubject: {subject}\nText: {body}"

SYSTEM_TRANSACTION_EXTRACTION_PROMPT = (
    "You are an assistant extracting bank transactions from emails. Extract ALL transactions, "
    "both expenses (costs) and incomes (salaries, refunds, reversals).\n"
    "Carefully read the Subject and the Text to understand if it is a cost, a refund, or a salary.\n"
    "Respond with a valid JSON strictly following the Pydantic schema below.\n"
    "Model Schema: \n"
    f"{json.dumps(TransactionExtraction.model_json_schema(), indent=2, ensure_ascii=False)}\n"
    "Use exclusively the following categories: \n"
    + "\n".join(f"- {category.value}" for category in TransactionCategory)
    + "\n"
    "IMPORTANT: If the transaction is an Expense, the amount MUST be a negative number. "
    "If it is a Refund or a Salary, the amount MUST be a positive number.\n"
    "{user_feedback_examples}"
)
