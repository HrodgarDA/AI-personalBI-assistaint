import json
from auto_bi.utils.models import (
    OutgoingCategory, IncomingCategory,
    OutgoingClassification, IncomingClassification,
)

EMAIL_PROMPT_TEMPLATE = "Date: {date}\nTime: {time}\nOperation: {operation}\nDetails: {details}"

OUTGOING_CLASSIFICATION_PROMPT = (
    "You are classifying a bank transaction where money LEFT the account (Outgoing).\n"
    "Determine the most appropriate expense category from the following list:\n"
    + "\n".join(f"- {cat.value}" for cat in OutgoingCategory)
    + "\n\n"
    "CRITICAL: Return ONLY a valid JSON object matching the requested structure. "
    "DO NOT include the schema definition, '$defs', or 'properties' keys. "
    "Fill in the fields 'category', 'amount', 'confidence', and 'reasoning'.\n"
    "If you can see an amount in the text, extract it as a NEGATIVE number.\n"
    "{user_feedback_examples}"
)

INCOMING_CLASSIFICATION_PROMPT = (
    "You are classifying a bank transaction where money ENTERED the account (Incoming).\n"
    "Determine the most appropriate income category from the following list:\n"
    + "\n".join(f"- {cat.value}" for cat in IncomingCategory)
    + "\n\n"
    "KEY ITALIAN PATTERNS:\n"
    "- 'Stipendio O Pensione' → Salary\n"
    "- 'Storno Pagamento' (reversal/refund) → Refund\n"
    "- 'Bonifico A Vostro Favore Disposto Da' (transfer received) → Transfer\n\n"
    "CRITICAL: Return ONLY a valid JSON object matching the requested structure. "
    "DO NOT include the schema definition, '$defs', or 'properties' keys. "
    "Fill in the fields 'category', 'amount', 'confidence', and 'reasoning'.\n"
    "If you can see an amount in the text, extract it as a POSITIVE number.\n"
    "{user_feedback_examples}"
)
