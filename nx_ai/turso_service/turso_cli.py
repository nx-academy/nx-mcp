import asyncio
import click

from nx_ai.turso_service.turso_api import (
    insert_news_in_db,
    insert_now_note_in_db
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
