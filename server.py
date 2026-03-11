import os
import httpx
import asyncio
from mcp.server.fastmcp import FastMCP

from nx_ai.turso_service.turso_api import insert_news_in_db
from nx_ai.github_service.github_api import trigger_gh_rebuild
from nx_ai.utils.slugify import slugify_title


mcp = FastMCP("nx-mcp", host="0.0.0.0")


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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
