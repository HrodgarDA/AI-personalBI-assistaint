import os
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from src.models import ExpenseExtraction

load_dotenv()

class ExpenseParser:
    def __init__(self):
        self.model = os.getenv("MODEL_ID")
        self.client = instructor.patch(
            OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
            mode=instructor.Mode.JSON,
        )

    def parse(self, text: str) -> ExpenseExtraction:
        return self.client.chat.completions.create(
            model=self.model,
            response_model=ExpenseExtraction,
            messages=[
                {"role": "system", "content": "Estrai spese bancarie dal testo. Sii preciso con importi e merchant."},
                {"role": "user", "content": text},
            ],
        )