import os
import hmac
import httpx
import asyncio
from urllib.parse import parse_qs

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

from nx_ai.turso_service.turso_api import (
    insert_news_in_db,
    insert_now_note_in_db
)
from nx_ai.github_service.github_api import trigger_gh_rebuild
from nx_ai.utils.slugify import slugify_title


mcp = FastMCP("nx-mcp", host="0.0.0.0", port=8000)


class TokenAuthMiddleware:
    """Pure ASGI middleware requiring a shared secret token on every HTTP request.

    The token is read from the MCP_AUTH_TOKEN environment variable and can be
    provided by the client either as an ``Authorization: Bearer <token>`` header
    (preferred, does not leak into access logs) or as a ``?token=<token>`` query
    parameter (fallback for clients that only accept a URL).

    A pure ASGI middleware is used on purpose: Starlette's BaseHTTPMiddleware
    buffers responses and breaks the SSE/streaming responses of the
    streamable-http transport.
    """

    def __init__(self, app):
        self.app = app

    def _extract_token(self, scope) -> str:
        # 1. Authorization: Bearer <token>
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                decoded = value.decode("latin-1")
                if decoded.lower().startswith("bearer "):
                    return decoded[7:].strip()
        # 2. ?token=<token> fallback
        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        return query.get("token", [""])[0]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        expected = os.environ.get("MCP_AUTH_TOKEN")
        if not expected:
            # Fail closed: refuse to serve if no secret is configured.
            response = JSONResponse(
                {"error": "server misconfigured: MCP_AUTH_TOKEN is not set"},
                status_code=500,
            )
            await response(scope, receive, send)
            return

        provided = self._extract_token(scope)
        if not hmac.compare_digest(provided, expected):
            response = JSONResponse({"error": "unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


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
async def publish_now_note(content: str) -> dict:
    """Insert a new note for En Ce Moment in the Turso Database and trigger a new build"""
    await insert_now_note_in_db(content)

    trigger_gh_rebuild()

    return {
        "success": True,
        "message": f"✅  Now Note published: {content}",
    }

if __name__ == "__main__":
    import uvicorn

    app = mcp.streamable_http_app()
    app.add_middleware(TokenAuthMiddleware)
    uvicorn.run(app, host="0.0.0.0", port=8000)
