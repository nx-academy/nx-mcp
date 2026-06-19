import os
from datetime import datetime

from libsql_client import create_client, Client


def _create_db_client() -> Client:
    turso_url = os.environ.get("TURSO_URL")
    turso_token = os.environ.get("TURSO_TOKEN")
    
    if turso_url is None or turso_token is None:
        raise ValueError("Please enter a valid turso url and/or a valid turso app token")
    
    return create_client(url=turso_url, auth_token=turso_token)


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