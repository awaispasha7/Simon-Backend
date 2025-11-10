"""
Web Search Service using Tavily
Provides internet search capabilities for the chatbot
"""

import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

# Try to import Tavily
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None
    print("Warning: Tavily not available. Install with: pip install tavily-python")


class WebSearchService:
    """Service for performing web searches using Tavily"""
    
    def __init__(self):
        self.client = None
        self.enabled = False
        
        if not TAVILY_AVAILABLE:
            print("[WebSearch] Tavily not available - web search disabled")
            return
        
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key and api_key != "your_tavily_api_key_here":
            try:
                self.client = TavilyClient(api_key=api_key)
                self.enabled = True
                print("[WebSearch] ✅ Tavily client initialized")
            except Exception as e:
                print(f"[WebSearch] ❌ Failed to initialize Tavily client: {e}")
        else:
            print("[WebSearch] ⚠️ TAVILY_API_KEY not set - web search disabled")
    
    def is_enabled(self) -> bool:
        """Check if web search is enabled"""
        return self.enabled and self.client is not None
    
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform a web search
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 5)
            
        Returns:
            Dictionary with search results containing:
            - results: List of search results with title, url, content, score
            - query: The search query used
            - success: Whether the search was successful
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "Web search is not enabled. Set TAVILY_API_KEY to enable.",
                "results": [],
                "query": query
            }
        
        try:
            # Perform search with Tavily
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced"  # Use advanced search for better results
            )
            
            # Format results
            results = []
            if response and "results" in response:
                for result in response.get("results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0)
                    })
            
            return {
                "success": True,
                "results": results,
                "query": query,
                "total_results": len(results)
            }
            
        except Exception as e:
            print(f"[WebSearch] ❌ Error performing search: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "query": query
            }
    
    def format_search_results_for_context(self, search_results: Dict[str, Any]) -> str:
        """
        Format search results as a string to include in LLM context
        
        Args:
            search_results: Results from search() method
            
        Returns:
            Formatted string with search results
        """
        if not search_results.get("success") or not search_results.get("results"):
            return ""
        
        formatted = "\n## Web Search Results\n\n"
        formatted += f"Query: {search_results.get('query', '')}\n\n"
        
        for i, result in enumerate(search_results.get("results", []), 1):
            formatted += f"### Result {i}: {result.get('title', 'No title')}\n"
            formatted += f"URL: {result.get('url', '')}\n"
            formatted += f"Content: {result.get('content', '')}\n\n"
        
        return formatted


# Global instance
web_search_service = WebSearchService()

