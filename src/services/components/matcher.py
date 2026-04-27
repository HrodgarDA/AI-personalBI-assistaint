import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

from src.database.session import async_session
from src.database.models import RegexRule
from sqlalchemy import select

logger = logging.getLogger(__name__)

class RegexMatcher:
    async def match(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Quickly matches a raw transaction string against dynamic regex rules from DB.
        """
        async with async_session() as session:
            stmt = select(RegexRule)
            res = await session.execute(stmt)
            rules = res.scalars().all()

        for rule in rules:
            try:
                if re.search(rule.pattern, text, re.IGNORECASE):
                    return rule.merchant_name, rule.category_id
            except Exception as e:
                logger.error(f"Invalid regex pattern '{rule.pattern}': {e}")
        return None

matcher = RegexMatcher()
