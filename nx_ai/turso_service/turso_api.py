import os
from datetime import datetime

from libsql_client import create_client, Client, ResultSet

from nx_ai.utils.slugify import slugify_title


def _create_db_client() -> Client:
    turso_url = os.environ.get("TURSO_URL")
    turso_token = os.environ.get("TURSO_TOKEN")

    if turso_url is None or turso_token is None:
        raise ValueError("Please enter a valid turso url and/or a valid turso app token")

    return create_client(url=turso_url, auth_token=turso_token)


def _rows_to_dicts(result: ResultSet) -> list[dict]:
    """Convert a libsql ResultSet into a list of JSON-serializable dicts"""
    return [
        {column: row[index] for index, column in enumerate(result.columns)}
        for row in result.rows
    ]


async def insert_news_in_db(title: str, content: str, url: str, slug: str):
    client = _create_db_client()
    
    try:
        now = datetime.utcnow().isoformat()
        query = """
        INSERT INTO NewsFeed (title, content, slug, url, published)
        VALUES (?, ?, ?, ?, ?)
        """
        
        await client.execute(query, [
            title,
            content,
            slug,
            url,
            now
        ])
        print("✅ News added in NewsFeed Table")
    finally:
        await client.close()


async def list_news_from_db(limit: int = 50, offset: int = 0) -> list[dict]:
    client = _create_db_client()

    try:
        query = """
        SELECT id, title, content, slug, url, published
        FROM NewsFeed
        ORDER BY published DESC
        LIMIT ? OFFSET ?
        """

        result = await client.execute(query, [limit, offset])
        return _rows_to_dicts(result)
    finally:
        await client.close()


async def get_news_from_db(news_id: int) -> dict | None:
    client = _create_db_client()

    try:
        query = """
        SELECT id, title, content, slug, url, published
        FROM NewsFeed
        WHERE id = ?
        """

        result = await client.execute(query, [news_id])
        rows = _rows_to_dicts(result)
        return rows[0] if rows else None
    finally:
        await client.close()


async def update_news_in_db(
    news_id: int,
    title: str | None = None,
    content: str | None = None,
    url: str | None = None,
) -> int:
    client = _create_db_client()

    try:
        fields = []
        values = []

        if title is not None:
            fields.append("title = ?")
            values.append(title)
            # Keep the slug in sync with the title
            fields.append("slug = ?")
            values.append(slugify_title(title))
        if content is not None:
            fields.append("content = ?")
            values.append(content)
        if url is not None:
            fields.append("url = ?")
            values.append(url)

        if not fields:
            raise ValueError("Nothing to update: provide at least a title, content or url")

        values.append(news_id)
        query = f"UPDATE NewsFeed SET {', '.join(fields)} WHERE id = ?"

        result = await client.execute(query, values)
        print(f"✅ {result.rows_affected} News updated in NewsFeed Table")
        return result.rows_affected
    finally:
        await client.close()


async def delete_news_from_db(news_id: int) -> int:
    client = _create_db_client()

    try:
        query = "DELETE FROM NewsFeed WHERE id = ?"

        result = await client.execute(query, [news_id])
        print(f"✅ {result.rows_affected} News deleted from NewsFeed Table")
        return result.rows_affected
    finally:
        await client.close()


async def insert_now_note_in_db(content: str):
    client = _create_db_client()

    try:
        now = datetime.utcnow().isoformat()
        query = """
        INSERT INTO NowNoteFeed (content, published)
        VALUES (?, ?)
        """

        await client.execute(query, [
            content,
            now
        ])
        print("✅ Now Note added in NowNoteFeed Table")
    finally:
        await client.close()