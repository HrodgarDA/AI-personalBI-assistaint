import json
from auto_bi.utils.models import (
    OutgoingCategory, IncomingCategory,
    OutgoingClassification, IncomingClassification,
)

EMAIL_PROMPT_TEMPLATE = "Date: {date}\nTime: {time}\nOperation: {operation}\nDetails: {details}"

OUTGOING_CLASSIFICATION_PROMPT = (
    "Analyze the bank transaction and categorize it accurately.\n"
    "Step 1: Identify the merchant and determine its primary business.\n"
    "Step 2: Assign the most fitting category from the list below.\n\n"
    "CATEGORIES & GUIDELINES:\n"
    "- Dining: Restaurants, Bars, Cafes, Fast food (KFC, McDonald's), Food delivery.\n"
    "- Groceries: Supermarkets (Ipercoop, Conad, Lidl, Esselunga), Bakeries.\n"
    "- Shopping: Clothing (Zara, H&M), Electronics (Amazon, MediaWorld), Online retail.\n"
    "- Subscriptions: Digital services (Netflix, ChatGPT, Spotify, iCloud subscription), Gym memberships.\n"
    "- Utilities: Essential services (Electricity, Gas, Water, Phone/Mobile, Internet bills).\n"
    "- Home: Rent, Mortgage, DIY/Furniture (IKEA, Leroy Merlin), Home maintenance, cleaning products.\n"
    "- Transport: Fuel, Public transport, Parking (EasyPark), Car repair, Train tickets.\n"
    "- Health: Pharmacy, Medical visits, Dentist, Health insurance.\n"
    "- Savings: Investments, Transfers to personal savings accounts.\n"
    "- Financial: Bank fees, Taxes (F24), Debt payments, official settlements.\n"
    "- Gifts: Donations, money sent to friends/family as presents.\n"
    "- Other: Use only if no other category matches.\n\n"
    "STRICT RULES:\n"
    "1. KFC/McDonald's -> Dining. Zara/Amazon -> Shopping. Supermarkets -> Groceries.\n"
    "2. If the merchant is 'PayPal', look at the other text to find the actual store.\n"
    "3. Explain your reasoning in the 'reasoning' field before picking the category.\n"
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
    "You are classifying a bank transaction where money ENTERED the account (Incoming).\n\n"
    "CATEGORIES:\n"
    "- Salary: Monthly wage, pension, or career-related income.\n"
    "- Refund: Returns from stores (Amazon refund), tax refunds, or insurance payouts.\n"
    "- Transfer: Money received from friends, family, or other personal accounts.\n"
    "- Gift: Birthday money, donations received.\n"
    "- Other: Miscellaneous income.\n\n"
    "KEY ITALIAN PATTERNS:\n"
    "- 'Stipendio O Pensione' -> Salary\n"
    "- 'Storno Pagamento' (reversal/refund) -> Refund\n"
    "- 'Bonifico A Vostro Favore' (transfer received) -> Transfer\n\n"
    "Return ONLY a valid JSON object with: 'category', 'amount' (POSITIVE number), 'confidence', and 'reasoning'.\n"
    "{user_feedback_examples}\n"
    "{custom_user_rules}"
)
