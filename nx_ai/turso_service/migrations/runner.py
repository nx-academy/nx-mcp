"""Schema migrations for the Turso database.

nx-mcp owns the schema: it is the only repository that writes to the database
(INSERT/UPDATE/DELETE). nx-academy.github.io is a client, and its
`src/lib/db/schema.ts` is a hand-written, read-only Drizzle mirror that must be
updated after every migration applied here.

Each file in `sql/` is applied once, ordered by filename, and its name is
recorded in `schema_migrations`. Files are written to be safely replayable:
`UPDATE ... WHERE` clauses that no longer match anything, `CREATE INDEX IF NOT
EXISTS`, and `ADD COLUMN` statements that the runner itself skips when the
column already exists — SQLite has no `IF NOT EXISTS` for those. A migration
interrupted halfway can therefore simply be run again.
"""
import re
from datetime import datetime
from pathlib import Path

from libsql_client import Client


SQL_DIR = Path(__file__).parent / "sql"

# Matches `ALTER TABLE <table> ADD COLUMN <column> ...`, the only statement we
# write that SQLite cannot express idempotently.
ADD_COLUMN_RE = re.compile(
    r"^\s*ALTER\s+TABLE\s+(?P<table>\w+)\s+ADD\s+(?:COLUMN\s+)?(?P<column>\w+)",
    re.IGNORECASE,
)


def split_statements(sql: str) -> list[str]:
    """Split a migration file into individual statements.

    Comment lines are dropped first, so a `;` inside a comment cannot end a
    statement. Our migrations are plain DDL and UPDATEs: no triggers, and no
    string literal ever contains a semicolon.
    """
    lines = [
        line for line in sql.splitlines()
        if not line.strip().startswith("--")
    ]
    statements = ("\n".join(lines)).split(";")
    return [statement.strip() for statement in statements if statement.strip()]


def list_migrations() -> list[tuple[str, str]]:
    """Return (version, sql) for every migration file, ordered by version"""
    return [
        (path.stem, path.read_text(encoding="utf-8"))
        for path in sorted(SQL_DIR.glob("*.sql"))
    ]


async def _ensure_migrations_table(client: Client):
    await client.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TEXT NOT NULL
    )
    """)


async def applied_versions(client: Client) -> set[str]:
    await _ensure_migrations_table(client)

    result = await client.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in result.rows}


async def pending_migrations(client: Client) -> list[tuple[str, str]]:
    """Return the migrations not yet recorded in schema_migrations"""
    applied = await applied_versions(client)

    return [
        (version, sql)
        for version, sql in list_migrations()
        if version not in applied
    ]


async def _column_exists(client: Client, table: str, column: str) -> bool:
    result = await client.execute(f"PRAGMA table_info({table})")

    # PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
    return any(row[1] == column for row in result.rows)


async def _should_skip(client: Client, statement: str) -> bool:
    """True when re-running an ADD COLUMN that has already been applied"""
    match = ADD_COLUMN_RE.match(statement)
    if match is None:
        return False

    return await _column_exists(client, match["table"], match["column"])


def _summarize(statement: str) -> str:
    """One-line, truncated form of a statement, for progress output"""
    collapsed = " ".join(statement.split())

    return collapsed if len(collapsed) <= 70 else f"{collapsed[:67]}..."


async def apply_migration(client: Client, version: str, sql: str):
    """Run one migration's statements, then record it as applied.

    Safe to call on a migration that is already applied: every statement is
    either replayable or skipped, and the bookkeeping row is left alone.
    """
    for statement in split_statements(sql):
        if await _should_skip(client, statement):
            print(f"  ↷ skipped (already applied): {_summarize(statement)}")
            continue

        await client.execute(statement)
        print(f"  ✔ {_summarize(statement)}")

    await client.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, applied_at)"
        " VALUES (?, ?)",
        [version, datetime.utcnow().isoformat()],
    )
    print(f"✅ Migration applied: {version}")
