import os
import json
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from typing import Any
from pydantic import BaseModel
from src.models import TransactionExtraction
from src.prompts import SYSTEM_TRANSACTION_EXTRACTION_PROMPT

load_dotenv()

class MerchantExtraction(BaseModel):
    merchant: str

class TransactionParser:
    def __init__(self):
        self.model = os.getenv("MODEL_ID")
        self.client = instructor.patch(
            OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
            mode=instructor.Mode.JSON,
        )

    def _build_feedback_context(self) -> str:
        feedback_path = "data/user_feedback.json"
        bronze_path = "data/bronze_raw_emails.jsonl"
        
        if not os.path.exists(feedback_path) or not os.path.exists(bronze_path):
            return ""
            
        try:
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedbacks = json.load(f)
            
            if not feedbacks:
                return ""
            
            # Use up to the last 5 edits to keep the prompt concise
            feedbacks = feedbacks[-5:]
            
            msg_ids_to_find = {str(fb["msg_id"]) for fb in feedbacks}
            bodies_map = {}
            with open(bronze_path, "r", encoding="utf-8") as bf:
                for line in bf:
                    try:
                        record = json.loads(line)
                        mid = str(record.get("id"))
                        if mid in msg_ids_to_find:
                            bodies_map[mid] = record.get("body", "")
                    except Exception:
                        pass
                        
            examples = []
            for fb in feedbacks:
                mid = str(fb["msg_id"])
                if mid in bodies_map:
                    body = bodies_map[mid].strip()
                    if len(body) > 250:
                        body = body[:250] + "..."
                    ex = f"- Email text: '{body}'\n  -> Correct Category: {fb.get('corrected_category')} (Correct Amount: {fb.get('corrected_amount')})"
                    examples.append(ex)
                    
            if examples:
                return "\nHere are some examples of past categorizations. Use them as a reference:\n" + "\n".join(examples)
                
        except Exception as e:
            print(f"Error loading feedback: {e}")
            
        return ""

    def _search_merchant_info(self, merchant_name: str) -> str:
        if not merchant_name or merchant_name.lower() in ["unknown", "altro", ""]:
            return ""
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(f"What is {merchant_name} store service business", max_results=2))
                if results:
                    snippet = " ".join([r.get('body', '') for r in results])
                    return f"\nGoogle snippet for '{merchant_name}': {snippet}"
        except Exception as e:
            print(f"Web search skipped for {merchant_name}: {e}")
        return ""

    def parse(self, text: str) -> TransactionExtraction:
        merchant_name = "Unknown"
        merchant_hint = ""
        
        # Pass 1: Extract Merchant
        try:
            merchant_res = self.client.chat.completions.create(
                model=self.model,
                response_model=MerchantExtraction,
                messages=[
                    {"role": "system", "content": "Extract the merchant name from this bank transaction email. If unknown, output 'Unknown'."},
                    {"role": "user", "content": text},
                ],
            )
            merchant_name = merchant_res.merchant
            merchant_hint = self._search_merchant_info(merchant_name)
        except Exception:
            pass

        # Pass 2: Main Classification
        feedback_str = self._build_feedback_context()
        system_prompt = SYSTEM_TRANSACTION_EXTRACTION_PROMPT.replace("{user_feedback_examples}", feedback_str)
        if merchant_hint: system_prompt += merchant_hint
        response_model = TransactionExtraction

        result = self.client.chat.completions.create(
            model=self.model,
            response_model=response_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        
        # Inject merchant into result records
        for tr in result.transactions:
            if not getattr(tr, 'merchant', None): tr.merchant = merchant_name
                
        return result