import asyncio
import os
import sqlite3
import sys

import pytest

# Fix to make test work with import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from nx_ai.turso_service.migrations.runner import (
    apply_migration,
    list_migrations,
    pending_migrations,
    split_statements,
)


# The production schema as of the Astro DB migration, mirrored in
# nx-academy.github.io's src/lib/db/schema.ts.
NEWS_FEED_SCHEMA = """
CREATE TABLE NewsFeed (
  id INTEGER PRIMARY KEY,
  content TEXT NOT NULL,
  published TEXT NOT NULL,
  slug TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL
);
"""


class FakeResultSet:
    def __init__(self, rows, columns):
        self.rows = rows
        self.columns = columns


class FakeClient:
    """Minimal stand-in for libsql's async Client, backed by in-memory SQLite.

    The runner only ever calls `execute`, so this is enough to exercise the
    real migrations without a network round-trip — and without pulling in
    pytest-asyncio just to await them.
    """

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    async def execute(self, sql, args=None):
        cursor = self._connection.execute(sql, args or [])
        columns = [c[0] for c in cursor.description] if cursor.description else []
        return FakeResultSet(cursor.fetchall(), columns)


@pytest.fixture
def client():
    connection = sqlite3.connect(":memory:")
    connection.executescript(NEWS_FEED_SCHEMA)
    connection.executemany(
        "INSERT INTO NewsFeed (id, content, published, slug, title, url)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "c1", "2025-07-29", "docker-en-prod", "Docker en prod", "https://a"),
            (2, "c2", "2025-07-30", "docker-en-prod", "Docker en prod", "https://b"),
            (3, "c3", "2025-07-31", "docker-en-prod", "Docker en prod", "https://c"),
            (4, "c4", "2025-08-01", "", "!!!", "https://d"),
            (5, "c5", "2025-08-02", "kubernetes-1-32", "Kubernetes", "https://e"),
        ],
    )
    return FakeClient(connection)


def migrate(client: FakeClient):
    async def run():
        for version, sql in await pending_migrations(client):
            await apply_migration(client, version, sql)

    asyncio.run(run())


def query(client: FakeClient, sql: str):
    return asyncio.run(client.execute(sql)).rows


def test_split_statements_ignores_semicolons_in_comments():
    sql = "-- a comment; with a semicolon\nUPDATE T SET a = 1;\n\nUPDATE T SET b = 2;"

    assert split_statements(sql) == ["UPDATE T SET a = 1", "UPDATE T SET b = 2"]


def test_migrations_are_ordered_by_version():
    versions = [version for version, _ in list_migrations()]

    assert versions == sorted(versions)
    assert versions[0].startswith("001")


def test_migration_adds_context_and_lecture(client):
    migrate(client)

    assert query(client, "SELECT COUNT(*) FROM NewsFeed WHERE context IS NOT content") \
        == [(0,)]
    # NULL lecture means "old format entry" and must never be backfilled
    assert query(client, "SELECT COUNT(*) FROM NewsFeed WHERE lecture IS NOT NULL") \
        == [(0,)]


def test_migration_leaves_the_oldest_slug_of_a_group_untouched(client):
    migrate(client)

    slugs = [row[0] for row in query(client, "SELECT slug FROM NewsFeed ORDER BY id")]

    # Only the duplicates move, so anchors already shared as /feed#<slug> hold
    assert slugs[0] == "docker-en-prod"
    assert slugs[1:3] == ["docker-en-prod-2", "docker-en-prod-3"]
    assert slugs[3] == "news-4"
    assert slugs[4] == "kubernetes-1-32"


def test_migration_leaves_no_empty_or_duplicated_slug(client):
    migrate(client)

    assert query(
        client, "SELECT COUNT(*) FROM NewsFeed WHERE slug IS NULL OR trim(slug) = ''"
    ) == [(0,)]
    assert query(
        client,
        "SELECT COUNT(*) FROM (SELECT slug FROM NewsFeed GROUP BY slug HAVING COUNT(*) > 1)",
    ) == [(0,)]


def test_slug_index_is_unique(client):
    migrate(client)

    with pytest.raises(sqlite3.IntegrityError):
        asyncio.run(client.execute(
            "INSERT INTO NewsFeed (content, published, slug, title, url)"
            " VALUES ('x', '2026-01-01', 'kubernetes-1-32', 't', 'https://f')"
        ))


def test_migrations_are_replayable(client):
    migrate(client)
    before = query(client, "SELECT id, slug, context, lecture FROM NewsFeed ORDER BY id")

    # Nothing is pending any more, and forcing a replay changes nothing either
    assert asyncio.run(pending_migrations(client)) == []
    for version, sql in list_migrations():
        asyncio.run(apply_migration(client, version, sql))

    assert query(client, "SELECT id, slug, context, lecture FROM NewsFeed ORDER BY id") \
        == before
