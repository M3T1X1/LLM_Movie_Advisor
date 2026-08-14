from django.test import SimpleTestCase

from backend.content_titles import display_content_title


class ContentTitleTests(SimpleTestCase):
    def test_keeps_localized_latin_title(self):
        self.assertEqual(
            display_content_title("Podniebna poczta Kiki", "魔女の宅急便", {}),
            "Podniebna poczta Kiki",
        )

    def test_uses_english_fallback_for_non_latin_title(self):
        self.assertEqual(
            display_content_title(
                "ようこそ実力至上主義の教室へ",
                "ようこそ実力至上主義の教室へ",
                {"englishTitle": "Classroom of the Elite"},
            ),
            "Classroom of the Elite",
        )

    def test_prefers_polish_metadata_over_latin_english_title(self):
        self.assertEqual(
            display_content_title(
                "Avatar Aang: The Last Airbender",
                "Aang: The Last Airbender",
                {"polishTitle": "Awatar Aang: Ostatni władca wiatru"},
            ),
            "Awatar Aang: Ostatni władca wiatru",
        )
