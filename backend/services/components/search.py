import os
import logging
import httpx
from duckduckgo_search import DDGS
from typing import Optional

logger = logging.getLogger(__name__)

from backend.core.config import settings

async def search_merchant_info(query: str) -> Optional[str]:
    """
    Performs an asynchronous web search to identify a merchant.
    Tries Tavily first, falls back to DDGS.
    """
    api_key = settings.TAVILY_API_KEY
    
    if api_key and api_key != "tvly-placeholder":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": f"{query} merchant store business description",
                        "search_depth": "basic",
                        "max_results": 3
                    },
                    timeout=settings.SEARCH_TIMEOUT
                )
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    if results:
                        context = "\n".join([f"- {r['content']}" for r in results])
                        logger.info(f"Tavily search success for: {query}")
                        return context
        except Exception as e:
            logger.warning(f"Tavily search failed, falling back to DDGS: {e}")

    # Fallback to DDGS (Synchronous library, called in a thread if needed, but here simple)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{query} merchant store company", max_results=3))
            if results:
                context = "\n".join([f"- {r['body']}" for r in results])
                logger.info(f"DDGS fallback search success for: {query}")
                return context
    except Exception as e:
        logger.error(f"Error during DDGS search for '{query}': {e}")
        
    return None
