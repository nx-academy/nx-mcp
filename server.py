import os
import httpx
import asyncio

from typing import Optional

from mcp.server.fastmcp import FastMCP

from nx_ai.turso_service.turso_api import (
    insert_news_in_db,
    list_news_from_db,
    get_news_from_db,
    update_news_in_db,
    delete_news_from_db,
    insert_now_note_in_db,
    insert_recap_link_in_db,
    list_recap_links_from_db,
    get_recap_link_from_db
)
from nx_ai.github_service.github_api import trigger_gh_rebuild
from nx_ai.utils.slugify import slugify_title
from nx_ai.utils.url_checker import is_url_valid


mcp = FastMCP("nx-mcp", host="0.0.0.0", port=8000)


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def get_weather(latitude: float, longitude: float) -> dict:
    """Return the weather for a current GPS location"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,wind_speed_10m"
    }

    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


@mcp.tool()
def fetch_news_by_topic(topic: str) -> dict:
    """Retrieve latest news about a specific topic via NewsAPI"""
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        raise ValueError("NEWS_API_KEY is not set")

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": topic,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": api_key
    }

    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    articles = data.get("articles", [])
    if not articles:
        return {"message": f"No news found for subject: {topic}"}

    return [
        {
            "title": a["title"],
            "url": a["url"],
            "description": a["description"],
            "publishedAt": a["publishedAt"]
        }
        for a in articles
    ]


@mcp.tool()
def fetch_news_by_source(source: str) -> dict:
    """Retrieve latest news from a specific media (e.g. Le monde) via NewsAPI"""
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        raise ValueError("NEWS_API_KEY is not set")

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "sources": source,
        "apiKey": api_key
    }

    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    articles = data.get("articles", [])
    if not articles:
        return {"message": "Not news found for source: {source}"}

    return [
        {
            "title": a["title"],
            "url": a["url"],
            "description": a["description"],
            "publishedAt": a["publishedAt"]
        }
        for a in articles
    ]


@mcp.tool()
async def publish_news(title: str, content: str, url: str) -> dict:
    """Insert new in the Turso Database and trigger a new build"""
    slug = slugify_title(title)

    await insert_news_in_db(
        title,
        content,
        url,
        slug
    )

    trigger_gh_rebuild()

    return {
        "success": True,
        "message": f"✅  News published: {title}",
        "slug": slug
    }


@mcp.tool()
async def list_news(limit: int = 50, offset: int = 0) -> dict:
    """List news from the NewsFeed table, most recent first"""
    news = await list_news_from_db(limit, offset)

    return {
        "success": True,
        "count": len(news),
        "news": news
    }


@mcp.tool()
async def get_news(news_id: int) -> dict:
    """Retrieve a single news from the NewsFeed table by its id"""
    news = await get_news_from_db(news_id)

    if news is None:
        return {
            "success": False,
            "message": f"No news found with id: {news_id}"
        }

    return {
        "success": True,
        "news": news
    }


@mcp.tool()
async def update_news(
    news_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    url: Optional[str] = None
) -> dict:
    """Update an existing news in the NewsFeed table and trigger a new build.

    Only the provided fields are updated. Updating the title also refreshes
    the slug accordingly.
    """
    rows_affected = await update_news_in_db(news_id, title, content, url)

    if rows_affected == 0:
        return {
            "success": False,
            "message": f"No news found with id: {news_id}"
        }

    trigger_gh_rebuild()

    return {
        "success": True,
        "message": f"✅  News updated: {news_id}"
    }


@mcp.tool()
async def delete_news(news_id: int) -> dict:
    """Delete a news from the NewsFeed table and trigger a new build"""
    rows_affected = await delete_news_from_db(news_id)

    if rows_affected == 0:
        return {
            "success": False,
            "message": f"No news found with id: {news_id}"
        }

    trigger_gh_rebuild()

    return {
        "success": True,
        "message": f"✅  News deleted: {news_id}"
    }


@mcp.tool()
async def publish_now_note(content: str) -> dict:
    """Insert a new note for En Ce Moment in the Turso Database and trigger a new build"""
    await insert_now_note_in_db(content)

    trigger_gh_rebuild()

    return {
        "success": True,
        "message": f"✅  Now Note published: {content}",
    }


@mcp.tool()
async def publish_recap_link(description: str, url: str) -> dict:
    """Insert a new link in the RecapLink table of the Turso Database"""
    if not is_url_valid(url):
        return {
            "success": False,
            "message": f"Invalid URL: {url}"
        }

    await insert_recap_link_in_db(description, url)

    return {
        "success": True,
        "message": f"✅  Recap link published: {url}"
    }


@mcp.tool()
async def list_recap_links(limit: int = 50, offset: int = 0) -> dict:
    """List links from the RecapLink table, most recently added first"""
    recap_links = await list_recap_links_from_db(limit, offset)

    return {
        "success": True,
        "count": len(recap_links),
        "recap_links": recap_links
    }


@mcp.tool()
async def get_recap_link(recap_link_id: int) -> dict:
    """Retrieve a single link from the RecapLink table by its id"""
    recap_link = await get_recap_link_from_db(recap_link_id)

    if recap_link is None:
        return {
            "success": False,
            "message": f"No recap link found with id: {recap_link_id}"
        }

    return {
        "success": True,
        "recap_link": recap_link
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
