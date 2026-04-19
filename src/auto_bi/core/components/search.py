import logging
import concurrent.futures
from typing import Optional, List
from auto_bi.utils.utils import clean_search_query, is_valid_search_query

logger = logging.getLogger(__name__)

class SearchEngine:
    """Handles web search for merchant information."""
    
    def __init__(self, backends: List[str], timeout: int):
        self.backends = backends
        self.timeout = timeout

    def _execute_single_search(self, backend: str, query: str) -> Optional[str]:
        """Wrap DDGS call for individual backend execution."""
        from ddgs import DDGS
        try:
            with DDGS(timeout=self.timeout) as ddgs:
                results = list(ddgs.text(f"What is {query} store service category", backend=backend, max_results=1))
                if results:
                    return results[0].get('body', '')
        except Exception:
            pass
        return None

    def search_merchant_info(self, merchant_name: str) -> str:
        """Search for merchant info using web search backends in parallel."""
        if not merchant_name or merchant_name.lower() in ["unknown", "altro", "", "n.d"]:
            return ""
        
        query = clean_search_query(merchant_name)
        if not is_valid_search_query(query):
            return ""
        
        try:
            # Parallelize searches across all configured backends
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.backends)) as executor:
                # Dispatch all searches
                future_to_backend = {
                    executor.submit(self._execute_single_search, backend, query): backend 
                    for backend in self.backends
                }
                
                # First success wins - process as they complete
                for future in concurrent.futures.as_completed(future_to_backend):
                    try:
                        res = future.result()
                        if res:
                            logger.debug(f"🔍 Parallel web search OK (Backend: {future_to_backend[future]}): '{query}'")
                            return res[:200]
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Error during parallel web search: {e}")
            
        return ""
