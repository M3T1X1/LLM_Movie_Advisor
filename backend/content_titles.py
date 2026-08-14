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
