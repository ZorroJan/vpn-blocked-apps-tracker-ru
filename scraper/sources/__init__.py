"""Shared utilities for source parsers.

Each parser module exports a `parse(html: str) -> list[str]` function that
returns a list of raw app names found in the article. Names are normalized
later in normalize.py.
"""

from __future__ import annotations

import re
from bs4 import BeautifulSoup


def extract_list_items(html: str) -> list[str]:
    """Extract text from all <li> elements in the article.

    Most source articles structure their app lists as bullet lists, so this
    is a reasonable default. Individual parsers can override or refine.
    """
    soup = BeautifulSoup(html, "lxml")
    items: list[str] = []
    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        if text and len(text) < 200:  # filter out long paragraphs that aren't app names
            items.append(text)
    return items


def extract_article_text(html: str) -> str:
    """Extract the main text of the article, stripped of HTML."""
    soup = BeautifulSoup(html, "lxml")
    # Remove scripts, styles, navs
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def clean_app_name(raw: str) -> str:
    """Strip common noise from a raw app name string.

    Removes leading bullets, dashes, numbering, and trailing punctuation.
    """
    # Strip leading list markers
    cleaned = re.sub(r"^[\s\-\*•·–—\d\.\)]+", "", raw).strip()
    # Strip trailing punctuation
    cleaned = re.sub(r"[\.,;:]+$", "", cleaned).strip()
    return cleaned
