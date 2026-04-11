import os
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from typing import Any
from src.models import ExpenseExtraction, IncomeExtraction
from src.prompts import SYSTEM_EXPENSE_EXTRACTION_PROMPT, SYSTEM_INCOME_EXTRACTION_PROMPT

load_dotenv()

class ExpenseParser:
    def __init__(self):
        self.model = os.getenv("MODEL_ID")
        self.client = instructor.patch(
            OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
            mode=instructor.Mode.JSON,
        )

    def parse(self, text: str, kind: str = "expense") -> Any:
        if kind == "income":
            system_prompt = SYSTEM_INCOME_EXTRACTION_PROMPT
            response_model = IncomeExtraction
        else:
            system_prompt = SYSTEM_EXPENSE_EXTRACTION_PROMPT
            response_model = ExpenseExtraction

        return self.client.chat.completions.create(
            model=self.model,
            response_model=response_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )

    def parse_expense(self, text: str) -> ExpenseExtraction:
        return self.parse(text, kind="expense")

    def parse_income(self, text: str) -> IncomeExtraction:
        return self.parse(text, kind="income")