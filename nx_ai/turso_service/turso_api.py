import os
from datetime import datetime

from libsql_client import create_client, Client, ResultSet

from nx_ai.turso_service.migrations.runner import (
    applied_versions,
    apply_migration,
    list_migrations,
    pending_migrations,
)
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


NEWS_COLUMNS = "id, title, content, context, lecture, slug, url, published"


async def _slug_exists(client: Client, slug: str, exclude_id: int | None = None) -> bool:
    query = "SELECT 1 FROM NewsFeed WHERE slug = ?"
    values: list = [slug]

    if exclude_id is not None:
        query += " AND id != ?"
        values.append(exclude_id)

    result = await client.execute(query, values)
    return bool(result.rows)


async def unique_slug(client: Client, title: str, exclude_id: int | None = None) -> str:
    """Slugify a title, suffixing it until it stops colliding.

    NewsFeed.slug carries a unique index, and two news items may legitimately
    share a title, so an unchecked slug would eventually be rejected on INSERT.
    """
    base = slugify_title(title)
    candidate = base
    suffix = 2

    while await _slug_exists(client, candidate, exclude_id):
        candidate = f"{base}-{suffix}"
        suffix += 1

    return candidate


async def insert_news_in_db(
    title: str,
    context: str,
    url: str,
    lecture: str | None = None,
) -> str:
    """Insert a news item and return the slug it was given"""
    client = _create_db_client()

    try:
        now = datetime.utcnow().isoformat()
        slug = await unique_slug(client, title)

        # `context` is also written to `content`: that column is still NOT NULL
        # and is still what nx-academy.github.io reads until it switches over.
        # Both halves of this go away with the migration that drops `content`.
        query = """
        INSERT INTO NewsFeed (title, content, context, lecture, slug, url, published)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        await client.execute(query, [
            title,
            context,
            context,
            lecture,
            slug,
            url,
            now
        ])
        print("✅ News added in NewsFeed Table")
        return slug
    finally:
        await client.close()


async def list_news_from_db(limit: int = 50, offset: int = 0) -> list[dict]:
    client = _create_db_client()

    try:
        query = f"""
        SELECT {NEWS_COLUMNS}
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
        query = f"""
        SELECT {NEWS_COLUMNS}
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
    context: str | None = None,
    url: str | None = None,
    lecture: str | None = None,
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
            values.append(await unique_slug(client, title, exclude_id=news_id))
        if context is not None:
            fields.append("context = ?")
            values.append(context)
            # Mirrored into `content` for as long as that column exists
            fields.append("content = ?")
            values.append(context)
        if lecture is not None:
            fields.append("lecture = ?")
            values.append(lecture)
        if url is not None:
            fields.append("url = ?")
            values.append(url)

        if not fields:
            raise ValueError(
                "Nothing to update: provide at least a title, context, lecture or url"
            )

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


async def insert_recap_link_in_db(description: str, url: str):
    client = _create_db_client()

    try:
        now = datetime.utcnow().isoformat()
        query = """
        INSERT INTO RecapLink (description, url, addedAt)
        VALUES (?, ?, ?)
        """

        await client.execute(query, [
            description,
            url,
            now
        ])
        print("✅ Recap Link added in RecapLink Table")
    finally:
        await client.close()


async def list_recap_links_from_db(limit: int = 50, offset: int = 0) -> list[dict]:
    client = _create_db_client()

    try:
        query = """
        SELECT id, description, url, addedAt
        FROM RecapLink
        ORDER BY addedAt DESC
        LIMIT ? OFFSET ?
        """

        result = await client.execute(query, [limit, offset])
        return _rows_to_dicts(result)
    finally:
        await client.close()


async def get_recap_link_from_db(recap_link_id: int) -> dict | None:
    client = _create_db_client()

    try:
        query = """
        SELECT id, description, url, addedAt
        FROM RecapLink
        WHERE id = ?
        """

        result = await client.execute(query, [recap_link_id])
        rows = _rows_to_dicts(result)
        return rows[0] if rows else None
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

async def run_pending_migrations(dry_run: bool = False) -> list[str]:
    """Apply every migration not yet recorded, and return their versions"""
    client = _create_db_client()

    try:
        pending = await pending_migrations(client)

        if not dry_run:
            for version, sql in pending:
                await apply_migration(client, version, sql)

        return [version for version, _ in pending]
    finally:
        await client.close()


async def migration_status() -> list[tuple[str, bool]]:
    """Return (version, applied) for every known migration, in order"""
    client = _create_db_client()

    try:
        applied = await applied_versions(client)
        return [(version, version in applied) for version, _ in list_migrations()]
    finally:
        await client.close()


async def inspect_news_schema() -> dict:
    """Report the live shape of NewsFeed: columns, indexes and slug health.

    This is what to run before a migration to confirm the schema on record, and
    after it to confirm the outcome.
    """
    client = _create_db_client()

    try:
        columns = await client.execute("PRAGMA table_info(NewsFeed)")
        indexes = await client.execute("PRAGMA index_list(NewsFeed)")
        total = await client.execute("SELECT COUNT(*) FROM NewsFeed")
        duplicates = await client.execute(
            "SELECT slug, COUNT(*) AS total FROM NewsFeed GROUP BY slug HAVING total > 1"
        )
        empty = await client.execute(
            "SELECT COUNT(*) FROM NewsFeed WHERE slug IS NULL OR trim(slug) = ''"
        )

        return {
            # PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
            "columns": [
                {"name": row[1], "type": row[2], "notnull": bool(row[3])}
                for row in columns.rows
            ],
            # PRAGMA index_list returns (seq, name, unique, origin, partial)
            "indexes": [
                {"name": row[1], "unique": bool(row[2])} for row in indexes.rows
            ],
            "count": total.rows[0][0],
            "duplicate_slugs": _rows_to_dicts(duplicates),
            "empty_slugs": empty.rows[0][0],
        }
    finally:
        await client.close()
