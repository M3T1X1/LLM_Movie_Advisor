"""Resolve catalog identity once; keep inflected names out of SQL filters."""
import re
import unicodedata
from dataclasses import replace
from difflib import SequenceMatcher

from backend.api.models import Content
from backend.content_titles import display_content_title
from backend.recommendation_agents.request_rules import TOPIC_EVIDENCE


def title_key(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    return re.findall(r'\w+', value.replace('ł', 'l'))


def title_similarity(requested, title):
    left, right = title_key(requested), title_key(title)
    if left == right:
        return 1.0
    if len(left) != len(right):
        return 0.0  # A sequel is a separate identity, even if it shares a prefix.
    if any(a.isdigit() != b.isdigit() or (a.isdigit() and a != b) for a,b in zip(left,right)):
        return 0.0
    return sum(SequenceMatcher(None,a,b).ratio() for a,b in zip(left,right)) / max(1,len(left))


def resolve_catalog_references(profile):
    if not profile.reference_titles or profile.reference_content_ids:
        return profile
    rows = list(Content.objects.values('id','title','original_title','metadata')[:20000])
    resolved, unresolved = [], []
    for reference in profile.reference_titles:
        scores = []
        for row in rows:
            aliases = (row['title'], row['original_title'] or '',
                       (row['metadata'] or {}).get('englishTitle',''),
                       (row['metadata'] or {}).get('polishTitle',''))
            score = max(title_similarity(reference, alias) for alias in aliases if isinstance(alias,str))
            if score >= .82:
                scores.append((score,row['id']))
        scores.sort(reverse=True)
        if scores and (len(scores)==1 or scores[0][0]-scores[1][0]>=.04):
            resolved.append(scores[0][1])
        else:
            unresolved.append(reference)
    if unresolved and profile.intent=='recommendation':
        return replace(profile, needs_clarification=True,
                       clarification_question='Podaj pełny lub oryginalny tytuł filmu odniesienia: ' + ', '.join(unresolved) + '.')
    if not resolved:
        return profile
    contents = list(Content.objects.filter(pk__in=resolved).prefetch_related('genres'))
    by_id = {c.pk:c for c in contents}
    titles = tuple(display_content_title(by_id[i].title,by_id[i].original_title,by_id[i].metadata) for i in resolved)
    excluded = tuple(dict.fromkeys((*profile.excluded_content_ids,*resolved))) if profile.exclude_reference_titles else profile.excluded_content_ids
    changes = dict(reference_content_ids=tuple(resolved),reference_titles=titles,excluded_content_ids=excluded)
    if profile.intent=='recommendation' and profile.exclude_reference_titles and len(contents)==1:
        source=contents[0]
        if not profile.genres:
            changes['genres']=tuple(g.name for g in source.genres.all())
            changes['genre_match_mode']='all'
        if not profile.themes and re.search(TOPIC_EVIDENCE['podróż kosmiczna'],source.overview or '',re.I):
            changes['themes']=('podróż kosmiczna',)
    return replace(profile,**changes)
