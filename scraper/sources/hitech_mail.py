"""Parser for Hi-Tech Mail article.

The article structures app lists as bullet lists under category headings.
"""

from . import extract_list_items, clean_app_name


def parse(html: str) -> list[str]:
    items = extract_list_items(html)
    return [clean_app_name(item) for item in items if item]
