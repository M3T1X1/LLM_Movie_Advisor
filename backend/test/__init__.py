"""Backend test suite."""


IN_MEMORY_TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "llm-movie-advisor-tests",
    },
}
