import asyncio
import click

from nx_ai.turso_service.turso_api import (
    inspect_news_schema,
    insert_news_in_db,
    migration_status,
    run_pending_migrations,
    list_news_from_db,
    get_news_from_db,
    update_news_in_db,
    delete_news_from_db,
    insert_now_note_in_db,
    insert_recap_link_in_db,
    list_recap_links_from_db,
    get_recap_link_from_db
)
from nx_ai.utils.slugify import slugify_title
from nx_ai.utils.url_checker import is_url_valid


@click.group()
def turso_group():
    """Set of commands related to Turso DB"""
    pass


@turso_group.command()
@click.option("--title", prompt="Title",
              help="The News' Title")
@click.option("--context", prompt="Context",
              help="The News' Context, e.g. the factual summary of the source")
@click.option("--lecture", default=None,
              help="The News' Lecture, e.g. your own commentary. Omit for an "
                   "old-format entry")
@click.option("--url", prompt="URL", help="The News's URL, e.g. where it comes from")
@click.option("--simulate", is_flag=True,
              help="Display the content of the news without creating it on DB")
def create_news(title: str, context: str, lecture: str, url: str, simulate: bool):
    """Insert a News in NewsFeed table"""
    if not is_url_valid(url):
        raise RuntimeError("Please insert a valid URL")
    
    if simulate:
        # The slug shown here is the unsuffixed one: the collision check needs
        # the database, which a simulation deliberately does not touch.
        print(f"""Here is the format of the news you're trying to create:
              - News title: {title}
              - News context: {context}
              - News lecture: {lecture}
              - News url: {url}
              - News slug: {slugify_title(title)}
              """)
        return
    
    asyncio.run(insert_news_in_db(
        title=title,
        context=context,
        url=url,
        lecture=lecture
    ))


@turso_group.command()
@click.option("--limit", default=50, show_default=True,
              help="Maximum number of news to list")
@click.option("--offset", default=0, show_default=True,
              help="Number of news to skip")
def list_news(limit: int, offset: int):
    """List news from the NewsFeed table, most recent first"""
    news = asyncio.run(list_news_from_db(limit=limit, offset=offset))

    if not news:
        print("No news found")
        return

    for item in news:
        print(f"[{item['id']}] {item['title']} ({item['slug']}) - {item['published']}")


@turso_group.command()
@click.option("--news-id", type=int, prompt="News id",
              help="The id of the news to display")
def get_news(news_id: int):
    """Display a single news from the NewsFeed table by its id"""
    news = asyncio.run(get_news_from_db(news_id))

    if news is None:
        print(f"No news found with id: {news_id}")
        return

    for key, value in news.items():
        print(f"- {key}: {value}")


@turso_group.command()
@click.option("--news-id", type=int, prompt="News id",
              help="The id of the news to update")
@click.option("--title", default=None, help="The new title (also refreshes the slug)")
@click.option("--context", default=None, help="The new context")
@click.option("--lecture", default=None, help="The new lecture")
@click.option("--url", default=None, help="The new URL")
def update_news(news_id: int, title: str, context: str, lecture: str, url: str):
    """Update an existing news in the NewsFeed table"""
    if title is None and context is None and lecture is None and url is None:
        raise RuntimeError(
            "Provide at least one of --title, --context, --lecture or --url"
        )

    if url is not None and not is_url_valid(url):
        raise RuntimeError("Please insert a valid URL")

    rows_affected = asyncio.run(update_news_in_db(
        news_id=news_id,
        title=title,
        context=context,
        url=url,
        lecture=lecture
    ))

    if rows_affected == 0:
        print(f"No news found with id: {news_id}")


@turso_group.command()
@click.option("--news-id", type=int, prompt="News id",
              help="The id of the news to delete")
@click.confirmation_option(prompt="Are you sure you want to delete this news?")
def delete_news(news_id: int):
    """Delete a news from the NewsFeed table"""
    rows_affected = asyncio.run(delete_news_from_db(news_id))

    if rows_affected == 0:
        print(f"No news found with id: {news_id}")


@turso_group.command()
@click.option("--content", prompt="Now Note Content",
              help="The content of the note")
@click.option("--simulate", is_flag=True,
              help="Display the content of the news without creating it on DB")
def create_now_note(content: str, simulate: bool):
    """Insert an entry inside the NowNoteFeed table"""

    if simulate:
        print(f"""Here is the format of the Note you're trying to create:
              - Now Note content: {content}
              """)
        return
    
    asyncio.run(insert_now_note_in_db(
        content
    ))


@turso_group.command()
@click.option("--description", prompt="Description",
              help="The Recap Link's description")
@click.option("--url", prompt="URL", help="The Recap Link's URL")
@click.option("--simulate", is_flag=True,
              help="Display the content of the link without creating it on DB")
def create_recap_link(description: str, url: str, simulate: bool):
    """Insert a link in the RecapLink table"""
    if not is_url_valid(url):
        raise RuntimeError("Please insert a valid URL")

    if simulate:
        print(f"""Here is the format of the recap link you're trying to create:
              - Recap link description: {description}
              - Recap link url: {url}
              """)
        return

    asyncio.run(insert_recap_link_in_db(
        description=description,
        url=url
    ))


@turso_group.command()
@click.option("--limit", default=50, show_default=True,
              help="Maximum number of recap links to list")
@click.option("--offset", default=0, show_default=True,
              help="Number of recap links to skip")
def list_recap_links(limit: int, offset: int):
    """List links from the RecapLink table, most recently added first"""
    recap_links = asyncio.run(list_recap_links_from_db(limit=limit, offset=offset))

    if not recap_links:
        print("No recap link found")
        return

    for item in recap_links:
        print(f"[{item['id']}] {item['description']} - {item['url']} ({item['addedAt']})")


@turso_group.command()
@click.option("--recap-link-id", type=int, prompt="Recap link id",
              help="The id of the recap link to display")
def get_recap_link(recap_link_id: int):
    """Display a single link from the RecapLink table by its id"""
    recap_link = asyncio.run(get_recap_link_from_db(recap_link_id))

    if recap_link is None:
        print(f"No recap link found with id: {recap_link_id}")
        return

    for key, value in recap_link.items():
        print(f"- {key}: {value}")


@turso_group.command()
@click.option("--dry-run", is_flag=True,
              help="List the migrations that would run, without applying them")
def migrate(dry_run: bool):
    """Apply the pending schema migrations to the Turso database"""
    versions = asyncio.run(run_pending_migrations(dry_run=dry_run))

    if not versions:
        print("Schema is up to date, nothing to apply")
        return

    if dry_run:
        print("Migrations that would be applied:")
        for version in versions:
            print(f"- {version}")
        return

    print(f"✅ {len(versions)} migration(s) applied")


@turso_group.command()
def migrate_status():
    """Show which schema migrations have been applied"""
    for version, applied in asyncio.run(migration_status()):
        print(f"[{'x' if applied else ' '}] {version}")


@turso_group.command()
def inspect_schema():
    """Show the live shape of the NewsFeed table and the health of its slugs"""
    schema = asyncio.run(inspect_news_schema())

    print(f"NewsFeed — {schema['count']} row(s)")

    print("\nColumns:")
    for column in schema["columns"]:
        flag = " NOT NULL" if column["notnull"] else ""
        print(f"- {column['name']}: {column['type']}{flag}")

    print("\nIndexes:")
    for index in schema["indexes"] or []:
        print(f"- {index['name']}{' (unique)' if index['unique'] else ''}")
    if not schema["indexes"]:
        print("- none")

    print(f"\nEmpty slugs: {schema['empty_slugs']}")
    print(f"Duplicated slugs: {len(schema['duplicate_slugs'])}")
    for duplicate in schema["duplicate_slugs"]:
        print(f"- {duplicate['slug']} ({duplicate['total']})")
