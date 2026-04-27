"""
===========================================================
J.A.R.V.I.S. — News Tool
===========================================================
Primary:  NewsAPI.org (free tier, 100 req/day)
Fallback: RSS feeds (BBC, Reuters, TechCrunch)
===========================================================
"""

import logging
import requests
from datetime import datetime
from typing import Optional

from jarvis.config import NEWSAPI_KEY, RSS_FEEDS

logger = logging.getLogger("jarvis.tools.news")


class NewsTool:
    """Fetch and summarize news from multiple sources."""

    def __init__(self, memory=None):
        self.memory = memory

    def execute(self, params: dict) -> str:
        """
        Get news headlines.
        
        Params:
            category (str): Optional filter — tech, world, sports, science
            count (int): Number of headlines (default 5)
        """
        category = params.get("category", "general")
        count = params.get("count", 5)

        try:
            # Try NewsAPI first
            if NEWSAPI_KEY:
                articles = self._fetch_newsapi(category, count)
                if articles:
                    return self._format_articles(articles, category)

            # Fallback to RSS
            articles = self._fetch_rss(category, count)
            if articles:
                return self._format_articles(articles, category)

            return "I couldn't fetch the latest news at the moment, Sir."

        except Exception as e:
            logger.error(f"News tool failed: {e}")
            return f"News service error, Sir: {str(e)}"

    def _fetch_newsapi(self, category: str, count: int) -> list:
        """Fetch from NewsAPI.org."""
        try:
            # Map categories
            cat_map = {
                "tech": "technology", "world": "general",
                "sports": "sports", "science": "science",
                "general": "general"
            }
            api_category = cat_map.get(category, "general")

            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "apiKey": NEWSAPI_KEY,
                    "category": api_category,
                    "language": "en",
                    "pageSize": count,
                },
                timeout=10
            )
            data = resp.json()

            if data.get("status") == "ok":
                return [
                    {
                        "title": a.get("title", ""),
                        "source": a.get("source", {}).get("name", ""),
                        "description": a.get("description", ""),
                        "url": a.get("url", ""),
                    }
                    for a in data.get("articles", [])[:count]
                ]
        except Exception as e:
            logger.warning(f"NewsAPI failed: {e}")
        return []

    def _fetch_rss(self, category: str, count: int) -> list:
        """Fetch from RSS feeds as fallback."""
        try:
            import feedparser

            # Select appropriate feed
            feed_url = RSS_FEEDS.get(category, RSS_FEEDS.get("world"))
            if not feed_url:
                feed_url = list(RSS_FEEDS.values())[0]

            feed = feedparser.parse(feed_url)
            articles = []

            for entry in feed.entries[:count]:
                articles.append({
                    "title": entry.get("title", ""),
                    "source": feed.feed.get("title", "RSS"),
                    "description": entry.get("summary", entry.get("description", "")),
                    "url": entry.get("link", ""),
                })

            return articles

        except Exception as e:
            logger.warning(f"RSS feed failed: {e}")
            return []

    def _format_articles(self, articles: list, category: str) -> str:
        """Format news articles into a readable briefing."""
        cat_label = category.title() if category != "general" else "Top"
        lines = [f"{cat_label} News Briefing:\n"]

        for i, a in enumerate(articles, 1):
            lines.append(f"{i}. {a['title']}")
            if a.get("description"):
                # Truncate long descriptions
                desc = a["description"][:200]
                lines.append(f"   {desc}")
            if a.get("source"):
                lines.append(f"   — {a['source']}")
            lines.append("")

        return "\n".join(lines)
