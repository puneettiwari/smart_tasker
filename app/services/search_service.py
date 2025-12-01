import os
import httpx
from typing import List, Dict, Any

class SearchService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform Google search and return results"""
        if not self.api_key or not self.search_engine_id:
            # Return mock results if Google API not configured
            return {
                "query": query,
                "results": [
                    {
                        "title": f"Result 1 for: {query}",
                        "link": "https://example.com/result1",
                        "snippet": "This is a mock search result. Configure Google API for real results."
                    }
                ],
                "has_relevant_results": True,
                "note": "Google Search API not configured. Using mock results."
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "key": self.api_key,
                        "cx": self.search_engine_id,
                        "q": query,
                        "num": num_results
                    },
                    timeout=10.0
                )
                
                response.raise_for_status()
                data = response.json()
                
                results = []
                if "items" in data:
                    results = [
                        {
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", "")
                        }
                        for item in data["items"]
                    ]
                
                return {
                    "query": query,
                    "results": results,
                    "has_relevant_results": len(results) > 0
                }
                
        except Exception as e:
            return {
                "query": query,
                "results": [],
                "has_relevant_results": False,
                "error": str(e)
            }

