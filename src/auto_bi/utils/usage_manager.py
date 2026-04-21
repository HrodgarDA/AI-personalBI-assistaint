import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SearchUsageManager:
    """Manages monthly search quotas for professional APIs."""
    
    def __init__(self, storage_path: str, monthly_limit: int = 1000):
        self.storage_path = storage_path
        self.monthly_limit = monthly_limit
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    current_month = datetime.now().strftime("%Y-%m")
                    if data.get("month") != current_month:
                        logger.info(f"🆕 Resetting search usage for new month: {current_month}")
                        return {"month": current_month, "count": 0}
                    return data
            except Exception as e:
                logger.warning(f"Failed to load usage data: {e}")
        
        return {"month": datetime.now().strftime("%Y-%m"), "count": 0}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage data: {e}")

    def can_search(self) -> bool:
        """Returns True if we are within the monthly limit."""
        return self.data["count"] < self.monthly_limit

    def increment(self):
        """Increments the search counter."""
        self.data["count"] += 1
        self._save()

    def get_status_str(self) -> str:
        """Returns a formatted status string for logging."""
        return f"{self.data['count']}/{self.monthly_limit}"
