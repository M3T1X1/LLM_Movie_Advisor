import type { Content, RunCandidate } from '../types';

const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p';

export function getPosterUrl(content: Content) {
  return content.posterPath ? `${TMDB_IMAGE_BASE_URL}/w780${content.posterPath}` : null;
}

export function getBackdropUrl(content: Content) {
  const path = content.metadata.backdropPath;
  return path ? `${TMDB_IMAGE_BASE_URL}/original${path}` : null;
}

export function getReleaseYear(content: Content) {
  return content.releaseDate ? new Date(content.releaseDate).getUTCFullYear() : null;
}

export function formatRuntime(minutes?: number) {
  if (!minutes) return null;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return hours ? `${hours} godz. ${remainingMinutes} min` : `${remainingMinutes} min`;
}

export function getMatchPercent(candidate: RunCandidate) {
  return candidate.finalScore === null ? null : Math.round(candidate.finalScore * 100);
}
