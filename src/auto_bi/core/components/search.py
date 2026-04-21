import logging
import concurrent.futures
import os
import json
import urllib.request
import urllib.parse
import time
from typing import Optional, List
from auto_bi.utils.utils import clean_search_query, is_valid_search_query
from auto_bi.utils.usage_manager import SearchUsageManager
from auto_bi.utils.config import SEARCH_USAGE_FILE

logger = logging.getLogger(__name__)

class SearchEngine:
    """Handles web search for merchant information with multi-provider support."""
    
    def __init__(self, backends: List[str], timeout: int):
        self.backends = backends
        self.timeout = timeout
        self.usage_manager = SearchUsageManager(SEARCH_USAGE_FILE)
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    def _search_tavily(self, query: str) -> Optional[str]:
        """Direct API call to Tavily Search."""
        if not self.tavily_api_key:
            return None
            
        if not self.usage_manager.can_search():
            logger.info("⚠️ Tavily limit reached for this month. Falling back to DuckDuckGo.")
            return None
            
        url = "https://api.tavily.com/search"
        data = {
            "api_key": self.tavily_api_key,
            "query": f"What is {query} store/service category and business type?",
            "search_depth": "basic",
            "max_results": 1
        }
        
        try:
            req = urllib.request.Request(url, method="POST")
            req.add_header("Content-Type", "json")
            
            # Simple urllib post
            js_data = json.dumps(data).encode('utf-8')
            req.data = js_data
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                self.usage_manager.increment()
                
                results = res_data.get('results', [])
                if results:
                    snippet = results[0].get('content', '')
                    logger.info(f"🚀 [TAVILY] Search success ({self.usage_manager.get_status_str()})")
                    return snippet
        except Exception as e:
            logger.debug(f"Tavily search failed: {e}")
            
        return None

    def _search_ddgs(self, query: str) -> Optional[str]:
        """Fallback search via DuckDuckGo."""
        from ddgs import DDGS
        # We try only the first backend from the list to reduce pressure
        backend = self.backends[0] if self.backends else "google"
        
        try:
            start_t = time.time()
            logger.info(f"🔎 [DDGS] Searching '{query}' (timeout: {self.timeout}s)...")
            with DDGS(timeout=self.timeout) as ddgs:
                results = list(ddgs.text(f"What is {query} store service category", backend=backend, max_results=1))
                if results:
                    elapsed = time.time() - start_t
                    logger.info(f"✅ [DDGS] Found info in {elapsed:.2f}s")
                    return results[0].get('body', '')
        except Exception as e:
            logger.warning(f"❌ [DDGS] Search failed or timed out: {e}")
            
        return None

    def search_merchant_info(self, merchant_name: str) -> str:
        """Main search entry point with intelligent fallback."""
        if not merchant_name or merchant_name.lower() in ["unknown", "altro", "", "n.d"]:
            return ""
        
        query = clean_search_query(merchant_name)
        if not is_valid_search_query(query):
            return ""
            
        # 1. Try Tavily first (Professional)
        if self.tavily_api_key:
            res = self._search_tavily(query)
            if res:
                return res[:300]
                
        # 2. Fallback to DuckDuckGo (Free)
        res = self._search_ddgs(query)
        if res:
            return res[:300]
            
        return ""
