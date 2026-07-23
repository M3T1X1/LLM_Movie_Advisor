CANONICAL_GENRE_NAMES = {
    12: "Przygodowy",
    14: "Fantasy",
    16: "Animacja",
    18: "Dramat",
    27: "Horror",
    28: "Akcja",
    35: "Komedia",
    36: "Historyczny",
    37: "Western",
    53: "Thriller",
    80: "Kryminał",
    99: "Dokumentalny",
    878: "Science Fiction",
    9648: "Tajemnica",
    10402: "Muzyczny",
    10749: "Romans",
    10751: "Familijny",
    10752: "Wojenny",
    10762: "Dla dzieci",
    10763: "Wiadomości",
    10764: "Reality show",
    10766: "Opera mydlana",
    10767: "Talk-show",
    10768: "Polityczny",
    10770: "Film telewizyjny",
}

# TMDB uses combined categories for TV shows while movies use separate genres.
# The application exposes one media-independent taxonomy.
COMPOSITE_GENRE_EXPANSIONS = {
    10759: (28, 12),  # Action & Adventure
    10765: (878, 14),  # Sci-Fi & Fantasy
    10768: (10752, 10768),  # War & Politics
}


def canonical_genres(genres: dict[int, str]) -> dict[int, str]:
    normalized: dict[int, str] = {}
    for source_id, source_name in genres.items():
        target_ids = COMPOSITE_GENRE_EXPANSIONS.get(source_id, (source_id,))
        for target_id in target_ids:
            normalized[target_id] = CANONICAL_GENRE_NAMES.get(
                target_id,
                source_name,
            )
    return normalized


def canonical_genre_ids(genre_ids) -> tuple[int, ...]:
    normalized: list[int] = []
    seen: set[int] = set()
    for source_id in genre_ids:
        for target_id in COMPOSITE_GENRE_EXPANSIONS.get(source_id, (source_id,)):
            if target_id not in seen:
                normalized.append(target_id)
                seen.add(target_id)
    return tuple(normalized)
