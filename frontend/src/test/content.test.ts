import { describe, expect, it } from 'vitest';
import { demoCandidates } from '../data/mockData';
import { formatRuntime, getBackdropUrl, getMatchPercent, getPosterUrl, getReleaseYear } from '../utils/content';

describe('content utilities', () => {
  const candidate = demoCandidates[0];

  it('builds TMDB image URLs', () => {
    expect(getPosterUrl(candidate.content)).toContain('/w780');
    expect(getBackdropUrl(candidate.content)).toContain('/original');
  });

  it('formats year, runtime and match score', () => {
    expect(getReleaseYear(candidate.content)).toBe(2014);
    expect(formatRuntime(149)).toBe('2 godz. 29 min');
    expect(formatRuntime(45)).toBe('45 min');
    expect(getMatchPercent(candidate)).toBe(96);
  });

  it('returns null for unavailable optional data', () => {
    const content = { ...candidate.content, posterPath: null, releaseDate: null, metadata: {} };
    expect(getPosterUrl(content)).toBeNull();
    expect(getBackdropUrl(content)).toBeNull();
    expect(getReleaseYear(content)).toBeNull();
    expect(formatRuntime()).toBeNull();
    expect(getMatchPercent({ ...candidate, finalScore: null })).toBeNull();
  });
});
