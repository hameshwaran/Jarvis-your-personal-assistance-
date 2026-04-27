"""
===========================================================
J.A.R.V.I.S. — Web Search Tool
===========================================================
DuckDuckGo search (free, no API key) + trafilatura scraping.
Results cached in SQLite for 24 hours.
===========================================================
"""

import logging
from typing import Optional

logger = logging.getLogger("jarvis.tools.web_search")


class WebSearchTool:
    """Search the web using DuckDuckGo and extract clean text from results."""

    def __init__(self, memory=None):
        self.memory = memory

    def execute(self, params: dict) -> str:
        """
        Execute a web search.
        
        Params:
            query (str): Search query
            max_results (int): Number of results (default 3)
        """
        query = params.get("query", "")
        max_results = params.get("max_results", 3)

        if not query:
            return "No search query provided, Sir."

        # Check cache first
        if self.memory:
            cached = self.memory.get_cached_search(query)
            if cached:
                return cached

        try:
            results = self._search_duckduckgo(query, max_results)
            if not results:
                return f"I couldn't find any results for '{query}', Sir."

            # Format results
            formatted = self._format_results(results, query)

            # Cache results
            if self.memory:
                self.memory.cache_search(query, formatted)

            return formatted

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return f"Web search encountered an error, Sir: {str(e)}"

    def _search_duckduckgo(self, query: str, max_results: int) -> list:
        """Search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", r.get("link", "")),
                        "snippet": r.get("body", r.get("snippet", "")),
                    })
            return results

        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

    def _format_results(self, results: list, query: str) -> str:
        """Format search results into a readable string."""
        lines = [f"Search results for '{query}':\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   {r['snippet']}")
            lines.append(f"   URL: {r['url']}\n")
        return "\n".join(lines)

    def scrape_url(self, url: str) -> Optional[str]:
        """Extract clean text from a URL using trafilatura."""
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                return text
        except Exception as e:
            logger.error(f"URL scraping failed: {e}")
        return None
