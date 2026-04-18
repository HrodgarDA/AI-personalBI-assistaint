import json

# Placeholder template for transaction details
EMAIL_PROMPT_TEMPLATE = "Date: {date}\nTime: {time}\nOperation: {operation}\nDetails: {details}"

OUTGOING_CLASSIFICATION_PROMPT = (
    "You are an expert financial assistant. Analyze the bank transaction and perform TWO tasks:\n"
    "1. MERCHANT EXTRACTION: Extract the clean name of the store or person (e.g., 'Spotify', 'Amazon', 'Zara'). Remove technical codes and dates.\n"
    "2. CATEGORIZATION: Assign the most fitting category from the list below.\n\n"
    "CATEGORIES & GUIDELINES:\n"
    "{categories_block}\n\n"
    "STRICT RULES:\n"
    "- Pick the closest match from the provided list. Do not invent new categories.\n"
    "- If the merchant is 'PayPal', look at the text to find the actual store (e.g., 'PayPal *Zara' -> Merchant: 'Zara').\n"
    "- Return BOTH the 'merchant' and the 'category' in the same JSON object.\n"
    "- Use the 'reasoning' field to explain your choice.\n\n"
    "{user_feedback_examples}\n"
    "{custom_user_rules}"
)

MERCHANT_EXTRACTION_PROMPT = (
    "Extract ONLY the merchant name (the store or person name) from this bank transaction text.\n"
    "Rules:\n"
    "- Remove all technical codes and noise patterns.\n"
    "- Remove dates and times.\n"
    "- Remove generic banking prefixes (e.g., 'PAGAMENTO', 'ACQUISTO').\n"
    "- If it's a PayPal transaction (e.g., 'PAYPAL *ZARA'), extract BOTH: 'PayPal *Zara'.\n"
    "- If unknown, output 'Unknown'.\n"
    "Output ONLY the name, nothing else."
)

INCOMING_CLASSIFICATION_PROMPT = (
    "Analyze this incoming bank transaction (money received) and perform TWO tasks:\n"
    "1. MERCHANT/SENDER EXTRACTION: Extract the clean name of the person or entity who sent the money.\n"
    "2. CATEGORIZATION: Assign the most fitting category from the list below.\n\n"
    "CATEGORIES:\n"
    "{categories_block}\n\n"
    "KEY ITALIAN PATTERNS:\n"
    "- 'Stipendio O Pensione' -> Category: Salary/Income\n"
    "- 'Storno Pagamento' (reversal/refund) -> Category: Refund\n"
    "- 'Bonifico A Vostro Favore' -> Category: Transfer\n\n"
    "Return BOTH the 'merchant' (sender) and the 'category' in the same JSON object.\n"
    "{user_feedback_examples}\n"
    "{custom_user_rules}"
)

BATCH_CLASSIFICATION_TEMPLATE = (
    "You are a financial expert. Analyze the following list of bank transactions and categorize each one.\n\n"
    "AVAILABLE CATEGORIES:\n"
    "{categories_block}\n\n"
    "TASK:\n"
    "For each transaction in the provided list:\n"
    "1. Extract the clean Merchant name.\n"
    "2. Assign the best Category from the list.\n"
    "3. Provide brief reasoning.\n\n"
    "SYSTEM RULES:\n"
    "- Output ONLY a JSON object with a 'results' field containing the list of result objects.\n"
    "- Maintain the exact order of the input list.\n"
    "{user_feedback_examples}\n"
    "{custom_user_rules}\n\n"
    "TRANSACTIONS TO PROCESS:\n"
    "{transactions_block}"
)

RECOVERY_CLASSIFICATION_TEMPLATE = (
    "You are a senior financial analyst. The following transactions previously failed to be categorized. "
    "Your goal is to perform a DEEP ANALYSIS and force a match with the existing categories. "
    "DO NOT USE 'Uncategorized' if there is ANY reasonable match.\n\n"
    "AVAILABLE CATEGORIES:\n"
    "{categories_block}\n\n"
    "TASK:\n"
    "For each transaction in the provided list:\n"
    "1. Extract the clean Merchant name (e.g., 'Amazon', 'Lidl').\n"
    "2. Assign the best Category from the list.\n"
    "3. Provide brief reasoning explaining why this is the best match despite previous failure.\n\n"
    "STRICT USER PREFERENCES:\n"
    "{user_feedback_examples}\n"
    "{custom_user_rules}\n\n"
    "SYSTEM RULES:\n"
    "- Output ONLY a JSON object with a 'results' field containing the list of result objects.\n"
    "- Maintain the exact order of the input list.\n"
    "FAILED TRANSACTIONS TO RE-PROCESS:\n"
    "{transactions_block}"
)

# --- BANK HINT MAPPING ---
BANK_HINT_MAPPING_TEMPLATE = (
    "You are a classification assistant. Your goal is to map a 'Bank Category' string "
    "from a bank statement to one of the user's defined Global Categories.\n\n"
    "AVAILABLE SYSTEM CATEGORIES:\n"
    "{categories_block}\n\n"
    "CONTEXT:\n"
    "Transaction Direction: {direction}\n"
    "Bank Category to Map: '{bank_hint}'\n\n"
    "SYSTEM RULES:\n"
    "1. Pick the best match from the list.\n"
    "2. If no match is possible, use 'Uncategorized'.\n"
    "3. Provide a brief reasoning for the translation.\n\n"
    "Return JSON with 'category' and 'reasoning' fields."
)
