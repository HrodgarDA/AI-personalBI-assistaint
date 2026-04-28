# 🧠 Gemma-Optimized Prompts for Personal BI

# 1. Classification Prompt (Batch)
BATCH_CLASSIFICATION_PROMPT = """
### ROLE
You are an expert financial assistant. Your task is to analyze bank transactions and provide structured metadata.

### INPUT DATA
AVAILABLE CATEGORIES:
{categories_block}

TRANSACTIONS TO PROCESS:
{formatted_txs}

### INSTRUCTIONS
1. For each transaction, identify the cleaned Merchant name.
2. Assign the most appropriate Category from the provided list.
3. Determine Tipology: 'Incoming' (credits/salary) or 'Outgoing' (expenses).
4. Provide a very brief reasoning.
5. Return a valid JSON list of objects.

### OUTPUT FORMAT (STRICT JSON)
[
  {{
    "merchant": "Amazon",
    "category": "Shopping",
    "tipology": "Outgoing",
    "reasoning": "Standard online purchase.",
    "confidence": 0.95
  }},
  ...
]

### RULES
- Return ONLY the JSON list. No conversation.
- Maintain the same order as the input.
- If unsure of the merchant, use 'Unknown'.
- If unsure of the category, use 'General'.
"""

# 2. Dynamic Regex Suggestion Prompt
# (Used when a user corrects a transaction)
REGEX_SUGGESTION_PROMPT = """
### TASK
Given a raw transaction description and the correct merchant name, suggest a robust Python Regex pattern to identify this merchant in the future.

### DATA
RAW DESCRIPTION: {raw_text}
CORRECT MERCHANT: {merchant_name}

### RULES
- The regex should be simple but specific (avoid matching generic terms).
- Use case-insensitive patterns if possible.
- Return ONLY the regex string.

### EXAMPLE
Input: "POS N. 12345 AMZN MKTPLACE AMSTERDAM" -> Merchant: "Amazon"
Output: "AMZN|AMAZON"
"""
