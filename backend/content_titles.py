import re
from typing import Any


LATIN_CHARACTER = re.compile(r"[A-Za-zÀ-žĄĆĘŁŃÓŚŹŻąćęłńóśźż]")


def display_content_title(
    title: str,
    original_title: str | None,
    metadata: dict[str, Any] | None,
) -> str:
    normalized = title.strip()
    values = metadata or {}
    polish_title = values.get("polishTitle")
    if (
        isinstance(polish_title, str)
        and polish_title.strip()
        and LATIN_CHARACTER.search(polish_title)
    ):
        return polish_title.strip()[:500]
    if LATIN_CHARACTER.search(normalized):
        return normalized
    for alternative in (
        values.get("englishTitle"),
        original_title,
    ):
        if (
            isinstance(alternative, str)
            and alternative.strip()
            and LATIN_CHARACTER.search(alternative)
        ):
            return alternative.strip()[:500]
    return normalized


def parse_recommendation_list(text: str) -> tuple[tuple[str, str], ...]:
    """Parse our numbered answers without splitting hyphens inside titles."""
    items = []
    for line in text.splitlines():
        match = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if not match:
            continue
        body = match.group(1)
        separator = " — " if " — " in body else " - "
        title, found, description = body.partition(separator)
        if found and title.strip() and description.strip():
            items.append((title.strip(), description.strip()))
    return tuple(items)
