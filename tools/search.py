from typing import List, Dict, Any, Optional
from tavily import TavilyClient
from config.settings import settings

def search_tavily(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the web using Tavily Search API.
    Returns structured results containing title, URL, snippet, published date (if available), and answer.
    """
    if not settings.TAVILY_API_KEY:
        return {
            "success": False,
            "error": "TAVILY_API_KEY is not configured in .env file.",
            "results": [],
            "query": query
        }

    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True
        )

        results = []
        raw_results = response.get("results", [])
        for item in raw_results:
            published_date = item.get("published_date") or item.get("publishedDate") or None
            results.append({
                "title": item.get("title", "Untitled Source"),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "published_date": published_date
            })

        return {
            "success": True,
            "error": None,
            "answer": response.get("answer"),
            "results": results,
            "query": query
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "query": query
        }
