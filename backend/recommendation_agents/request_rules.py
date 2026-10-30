"""Catalog-independent vocabulary and final checks shared by the agent stages."""
import re


COUNTRIES = (
    (r"polsk\w*|polish|poland", "PL"),
    (r"koreańsk\w*|korean|korei(?:\s+południowej)?|south korea", "KR"),
    (r"amerykańsk\w*|american|usa|us|stan\w*\s+zjednoczon\w*", "US"),
    (r"japońsk\w*|japon\w*|japanese|japan", "JP"),
    (r"francusk\w*|francj\w*|french|france", "FR"),
    (r"niemieck\w*|niemiec|niemcy|german\w*", "DE"),
    (r"brytyjsk\w*|wielkiej\s+brytanii|british|united kingdom|uk", "GB"),
    (r"hiszpańsk\w*|hiszpan\w*|spanish|spain", "ES"),
    (r"włosk\w*|włoch\w*|italian|italy", "IT"),
    (r"indyjsk\w*|indii|indie|indian|india", "IN"),
    (r"kanadyjsk\w*|kanad\w*|canadian|canada", "CA"),
    (r"chińsk\w*|chin|chiny|chinese|china", "CN"),
)
LANGUAGES = (
    (r"polsk\w*|polsku|polish", "pl"), (r"angielsk\w*|angielsku|english", "en"),
    (r"koreańsk\w*|koreańsku|korean", "ko"), (r"japońsk\w*|japońsku|japanese", "ja"),
    (r"francusk\w*|francusku|french", "fr"), (r"niemieck\w*|niemiecku|german", "de"),
    (r"hiszpańsk\w*|hiszpańsku|spanish", "es"), (r"włosk\w*|włosku|italian", "it"),
    (r"hindi", "hi"), (r"chińsk\w*|chińsku|chinese", "zh"),
)

# These patterns are evidence of a topic in a catalog description, not a claim
# that the catalog exhaustively describes every scene of a film.
TOPIC_EVIDENCE = {
    "podróż kosmiczna": r"kosmos\w*|kosmiczn\w*|galakty\w*|astronaut\w*|space\w*|orbit\w*",
    "podróże w czasie": r"podróż\w*\s+w\s+czas\w*|czas\w*\s+podróż\w*|wehikuł\w*|pętl\w*\s+czas\w*|cof\w*\s+(?:się\s+)?w\s+czas\w*|time\s+travel\w*",
    "sztuczna inteligencja": r"sztuczn\w*\s+inteligenc\w*|robot\w*|android\w*|droid\w*|artificial\s+intelligence|\bhal\b",
    "przetrwanie": r"przetrwa\w*|przeży\w*|ocal\w*|surviv\w*",
    "przyjaźń": r"przyjaź\w*|przyja[cz]\w*|przyjaci\w*|friend\w*",
    "napad na bank": r"napad\w*(?:\s+\w+){0,4}\s+bank\w*|bank\w*(?:\s+\w+){0,4}\s+napad\w*|obrab\w*\s+bank\w*|bank\s+(?:heist|robber)\w*",
    "śledztwo": r"detektyw\w*|śledztw\w*|dochodzen\w*|detective\w*|investigat\w*",
    "wojna": r"wojn\w*|wojen\w*|żołnier\w*|nazist\w*|\bwar\b|soldier\w*",
    "samotność": r"samotn\w*|osamotn\w*|izolac\w*|lonel\w*|alone|isolat\w*",
    "muzyka": r"muzy[ck]\w*|piosen\w*|wokal\w*|koncert\w*|śpiew\w*|music\w*|singer\w*",
    "hakerzy": r"haker\w*|hacker\w*|cyber\w*|właman\w*\s+(?:do\s+)?(?:system|sieci|komputer)\w*",
}
TOPIC_REQUESTS = {
    **TOPIC_EVIDENCE,
    "sztuczna inteligencja": r"sztuczn\w*\s+inteligenc\w*|artificial intelligence|\bAI\b|robot\w*|android\w*",
    "przyjaźń": r"przyjaź\w*|friendship",
    "napad na bank": r"napad\w*\s+na\s+bank\w*|bank\s+(?:heist|robber)\w*",
}


def normalize_request(text):
    text = text.casefold()
    for pattern, value in ((r"\bthriler\w*", "thriller"), (r"\bfilnu\b", "filmu"),
                           (r"\bminot\w*", "minut"), (r"\bwieczur\b", "wieczór")):
        text = re.sub(pattern, value, text)
    return text


def topic_patterns(topic):
    if topic in TOPIC_EVIDENCE:
        return (TOPIC_EVIDENCE[topic],)
    if topic.startswith('temat: '):
        terms = [word for word in re.findall(r'\w+', topic[7:]) if len(word)>3]
        patterns = []
        for word in terms[:6]:
            stem = re.sub(r'(?:ami|ach|ego|owej|ów|em|om|ie|u|a|y|i)$','',word)
            if len(stem)<3:
                stem=word
            patterns.append(r'\b'+re.escape(stem)+r'(?:a|y|i|ów|ach|ami|em|om|u|ie)?\b')
        return tuple(patterns)
    return ()


def candidate_violations(candidate, profile):
    """Check returned facts, independently of model relevance scores."""
    errors = []
    if profile.needs_clarification:
        errors.append('clarification_required')
    if profile.media_types and candidate.media_type not in profile.media_types:
        errors.append("media_type")
    if candidate.content_id in profile.excluded_content_ids:
        errors.append("excluded_title")
    genres = set(candidate.genres)
    if profile.genres:
        matches = [bool(genres & {"Dla dzieci", "Familijny"}) if g == "Dla dzieci" else g in genres
                   for g in profile.genres]
        if not (all(matches) if profile.genre_match_mode == "all" else any(matches)):
            errors.append("genres")
    if genres.intersection(profile.avoid):
        errors.append("excluded_genre")
    countries = set(candidate.origin_countries or candidate.metadata.get("originCountry", ()))
    if profile.origin_countries and not countries.intersection(profile.origin_countries):
        errors.append("origin_country")
    if profile.excluded_origin_countries and (not countries or countries.intersection(profile.excluded_origin_countries)):
        errors.append("excluded_country")
    if profile.original_languages and candidate.original_language not in profile.original_languages:
        errors.append("original_language")
    limits = profile.constraints
    year = int(candidate.release_date[:4]) if candidate.release_date else None
    if limits.release_year_from is not None and (year is None or year < limits.release_year_from):
        errors.append("release_year_from")
    if limits.release_year_to is not None and (year is None or year > limits.release_year_to):
        errors.append("release_year_to")
    if limits.min_vote_average is not None and (candidate.vote_average is None or candidate.vote_average < limits.min_vote_average):
        errors.append("min_vote_average")
    maximum = limits.max_runtime_minutes
    if "krótkie odcinki" in profile.themes:
        maximum = min(maximum, 35) if maximum is not None else 35
    if maximum is not None:
        key = "episodeRuntimeMinutes" if candidate.media_type == "tv" else "runtimeMinutes"
        runtime = candidate.metadata.get(key)
        if type(runtime) not in (int, float) or not 0 < runtime <= maximum:
            errors.append("max_runtime_minutes")
    for topic in profile.themes:
        patterns = topic_patterns(topic)
        if patterns and not all(re.search(pattern, candidate.overview, re.I) for pattern in patterns):
            errors.append("topic:" + topic)
    for topic in profile.excluded_themes:
        patterns = topic_patterns(topic)
        if patterns and all(re.search(pattern, candidate.overview, re.I) for pattern in patterns):
            errors.append("excluded_topic:" + topic)
    return tuple(errors)
