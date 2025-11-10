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
    
    def _enhance_query_for_recency(self, query: str) -> str:
        """Enhance search query to prioritize recent results"""
        query_lower = query.lower()
        
        # Check if query already has recency indicators
        recency_keywords = [
            "latest", "recent", "current", "new", "2024", "2025", 
            "today", "this week", "this month", "now"
        ]
        
        has_recency = any(keyword in query_lower for keyword in recency_keywords)
        
        # If no recency indicator, add current year to prioritize recent content
        if not has_recency:
            from datetime import datetime
            current_year = datetime.now().year
            # Only add year if it makes sense (not for general queries)
            if len(query.split()) < 5:  # Short queries benefit from year
                return f"{query} {current_year}"
        
        return query
    
    def search(self, query: str, max_results: int = 5, prioritize_recent: bool = True) -> Dict[str, Any]:
        """
        Perform a web search
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 5)
            prioritize_recent: Whether to enhance query for recent results (default: True)
            
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
            # Enhance query for recency if requested
            enhanced_query = self._enhance_query_for_recency(query) if prioritize_recent else query
            if enhanced_query != query:
                print(f"[WebSearch] Enhanced query for recency: '{query}' -> '{enhanced_query}'")
            
            # Perform search with Tavily
            response = self.client.search(
                query=enhanced_query,
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
                        "score": result.get("score", 0.0),
                        "published_date": result.get("published_date"),  # If available from Tavily
                    })
            
            # Sort by score (higher = more relevant) - Tavily already ranks by relevance + recency
            # Results with higher scores are typically more recent and relevant
            results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            
            return {
                "success": True,
                "results": results,
                "query": query,
                "enhanced_query": enhanced_query if enhanced_query != query else None,
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

