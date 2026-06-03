import click

from nx_ai.workflows.generate_quiz import generate_quiz_beta
from nx_ai.workflows.generate_recap import generate_recap_beta
from nx_ai.utils.slugify import slugify_title, slug_from_url


@click.group()
def workflows_group():
    """Commands related to NX automation workflows."""
    pass


@workflows_group.command()
@click.option("--simulate", is_flag=True,
              help="Simulate the API Call to GPT / Costs no money")
def generate_quiz(simulate):
    """
    Generate a quiz from an article and open a PR on nx-academy.github.io
    """
    
    # For now, I keep the url of the article here. I'll see later to maybe save them in a local db.
    url = "https://nx.academy/drafts/artefact-github-actions/"
    filename = slug_from_url(url)

    generate_quiz_beta(url, filename, simulate)


@workflows_group.command()
@click.option("--simulate", is_flag=True,
              help="Simulate the API Call to GPT / Costs no money")
def generate_recap(simulate):
    """
    Generate an article recap as Markdown and open a PR on nx-academy.github.io
    """
    
    # Same that above -> For now, I keep the urls of the article and its title here.
    urls = ["https://www.courrierinternational.com/video/video-foot-athletisme-ou-menage-les-images-des-premiers-jeux-mondiaux-d-humanoides_234026"]
    title = "Le récap - Août 2025"
    filename = slugify_title(title)

    generate_recap_beta(urls=urls, filename=filename, title=title, simulate=simulate)
