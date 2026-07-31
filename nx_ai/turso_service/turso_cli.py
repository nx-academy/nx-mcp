import asyncio
import click

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
from nx_ai.utils.slugify import slugify_title
from nx_ai.utils.url_checker import is_url_valid


@click.group()
def turso_group():
    """Set of commands related to Turso DB"""
    pass


@turso_group.command()
@click.option("--title", prompt="Title",
              help="The News' Title")
@click.option("--content", prompt="Content",
              help="The News' Content")
@click.option("--url", prompt="URL", help="The News's URL, e.g. where it comes from")
@click.option("--simulate", is_flag=True,
              help="Display the content of the news without creating it on DB")
def create_news(title: str, content: str, url: str, simulate: bool):
    """Insert a News in NewsFeed table"""
    if not is_url_valid(url):
        raise RuntimeError("Please insert a valid URL")
    
    if simulate:
        print(f"""Here is the format of the news you're trying to create:
              - News title: {title}
              - News content: {content}
              - News url: {url}
              - News slug: {slugify_title(title)}
              """)
        return
    
    asyncio.run(insert_news_in_db(
        title=title,
        content=content,
        url=url,
        slug=slugify_title(title)
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
@click.option("--content", default=None, help="The new content")
@click.option("--url", default=None, help="The new URL")
def update_news(news_id: int, title: str, content: str, url: str):
    """Update an existing news in the NewsFeed table"""
    if title is None and content is None and url is None:
        raise RuntimeError("Provide at least one of --title, --content or --url")

    if url is not None and not is_url_valid(url):
        raise RuntimeError("Please insert a valid URL")

    rows_affected = asyncio.run(update_news_in_db(
        news_id=news_id,
        title=title,
        content=content,
        url=url
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
