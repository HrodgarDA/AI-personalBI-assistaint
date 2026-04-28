import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

from backend.database.session import async_session
from backend.database.models import RegexRule
from sqlalchemy import select

logger = logging.getLogger(__name__)

class RegexMatcher:
    """Matches transaction text against regex rules stored in the database."""
    
    def __init__(self):
        self._rules = None

    async def refresh_rules(self):
        """Fetches all regex rules from the database and caches them."""
        async with async_session() as session:
            stmt = select(RegexRule)
            res = await session.execute(stmt)
            self._rules = res.scalars().all()
            logger.info(f"Loaded {len(self._rules)} regex rules from database.")

    async def match(self, text: str) -> Optional[Tuple[str, str, str]]:
        """
        Quickly matches a raw transaction string against dynamic regex rules.
        Uses cached rules if available.
        Returns: (merchant_name, category_id, transaction_type) or None
        """
        if self._rules is None:
            await self.refresh_rules()

        for rule in self._rules:
            try:
                if re.search(rule.pattern, text, re.IGNORECASE):
                    return rule.merchant_name, rule.category_id, rule.transaction_type
            except Exception as e:
                logger.error(f"Invalid regex pattern '{rule.pattern}': {e}")
        return None

matcher = RegexMatcher()
