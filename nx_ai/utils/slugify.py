import re
import unicodedata


SLUG_RE = re.compile(r"[^a-z0-9\-]")
FALLBACK_SLUG = "news"


def _remove_accents(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def slugify_title(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"['’]", "-", s)
    s = _remove_accents(s)
    s = re.sub(r"\s+", "-", s)
    s = SLUG_RE.sub("", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s[:80].strip("-")

    # A title made only of punctuation slugifies to an empty string, which the
    # unique index on NewsFeed.slug would reject on its second occurrence.
    return s or FALLBACK_SLUG
