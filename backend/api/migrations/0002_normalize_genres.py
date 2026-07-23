from django.db import migrations


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

COMPOSITE_GENRE_EXPANSIONS = {
    10759: (28, 12),
    10765: (878, 14),
    10768: (10752, 10768),
}


def normalize_existing_genres(apps, schema_editor):
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())
    if not {"genre", "content_genre"}.issubset(tables):
        return

    Genre = apps.get_model("api", "Genre")
    ContentGenre = apps.get_model("api", "ContentGenre")

    for tmdb_genre_id, name in CANONICAL_GENRE_NAMES.items():
        Genre.objects.filter(tmdb_genre_id=tmdb_genre_id).update(name=name)

    for source_tmdb_id, target_tmdb_ids in COMPOSITE_GENRE_EXPANSIONS.items():
        source = Genre.objects.filter(tmdb_genre_id=source_tmdb_id).first()
        if source is None:
            continue

        content_ids = list(
            ContentGenre.objects.filter(genre_id=source.pk).values_list(
                "content_id",
                flat=True,
            )
        )
        for target_tmdb_id in target_tmdb_ids:
            target, _ = Genre.objects.update_or_create(
                tmdb_genre_id=target_tmdb_id,
                defaults={"name": CANONICAL_GENRE_NAMES[target_tmdb_id]},
            )
            ContentGenre.objects.bulk_create(
                [
                    ContentGenre(content_id=content_id, genre_id=target.pk)
                    for content_id in content_ids
                ],
                ignore_conflicts=True,
            )

        if source_tmdb_id not in target_tmdb_ids:
            source.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            normalize_existing_genres,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
