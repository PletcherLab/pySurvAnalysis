"""Reading the manual's pages — no Qt, so the tests and a search can use it.

A page is ``topics/<topic-id>.md``: Markdown in the subset Qt's text browser
renders (headings, paragraphs, lists, tables, code, emphasis, links). A link
to another page is written ``[text](help:<topic-id>)``.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from .manifest import CHAPTERS, TITLES

TOPICS_DIR = Path(__file__).with_name("topics")
HELP_SCHEME = "help"
_LINK = re.compile(r"\]\(help:([A-Za-z0-9_-]+)\)")


def page_path(topic: str) -> Path:
    return TOPICS_DIR / f"{topic}.md"


@lru_cache(maxsize=None)
def page_text(topic: str) -> str:
    """The page's Markdown, or a short stand-in when the topic has no page —
    never an exception, because a help button must always open something."""
    path = page_path(topic)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    title = TITLES.get(topic, topic)
    return (f"# {title}\n\nThis page has not been written yet. "
            f"Browse the contents on the left, or search.")


def links_in(topic: str) -> list[str]:
    """Topic ids this page links to."""
    return _LINK.findall(page_text(topic))


def ordered_topics() -> list[str]:
    return [tid for _chapter, topics in CHAPTERS for tid, _title in topics]


def search(query: str) -> list[str]:
    """Topics whose title or text contains every word of *query*, title
    matches first, each group in manual order."""
    words = [w for w in query.lower().split() if w]
    if not words:
        return ordered_topics()
    in_title, in_body = [], []
    for topic in ordered_topics():
        title = TITLES[topic].lower()
        body = page_text(topic).lower()
        if all(w in title or w in body for w in words):
            (in_title if all(w in title for w in words) else in_body).append(topic)
    return in_title + in_body
