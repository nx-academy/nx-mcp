import re
import unicodedata
from urllib.parse import urlparse


SLUG_RE = re.compile(r"[^a-z0-9\-]")


def _remove_accents(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def slugify_title(title: str) -> str:
    s = title.strip().lower().replace("’", "-")
    s = _remove_accents(s)
    s = re.sub(r"\s+", "-", s)
    s = SLUG_RE.sub("", s)
    s = re.sub(r"-{2,}", "-", s)
    return s[:80].strip("-")


def slug_from_url(url: str) -> str:
    """Derive a slug from the last non-empty path segment of a URL.

    e.g. https://nx.academy/drafts/artefact-github-actions/ -> artefact-github-actions
    """
    path = urlparse(url).path
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        raise ValueError(f"Cannot derive a slug from URL: {url}")
    return slugify_title(segments[-1])
