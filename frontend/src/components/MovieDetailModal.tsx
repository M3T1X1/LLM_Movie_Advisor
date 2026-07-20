import { Bookmark, Check, Clock3, Eye, Film, Star, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { RunCandidate } from '../types';
import {
  formatRuntime,
  getBackdropUrl,
  getMatchPercent,
  getReleaseYear,
} from '../utils/content';

interface MovieDetailModalProps {
  candidate: RunCandidate | null;
  isWatchlisted: boolean;
  isWatched: boolean;
  onClose: () => void;
  onWatchlist: (candidate: RunCandidate) => void;
  onMarkWatched: (candidate: RunCandidate) => void;
}

export function MovieDetailModal({
  candidate,
  isWatchlisted,
  isWatched,
  onClose,
  onWatchlist,
  onMarkWatched,
}: MovieDetailModalProps) {
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    if (!candidate) return;
    document.body.classList.add('overflow-hidden');
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => {
      document.body.classList.remove('overflow-hidden');
      window.removeEventListener('keydown', handleEscape);
    };
  }, [candidate, onClose]);

  useEffect(() => setImageFailed(false), [candidate?.id]);

  if (!candidate) return null;

  const { content } = candidate;
  const backdropUrl = getBackdropUrl(content);
  const releaseYear = getReleaseYear(content);
  const runtime = formatRuntime(content.metadata.runtimeMinutes);
  const matchPercent = getMatchPercent(candidate);
  const providers = content.metadata.providers ?? [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 p-0 backdrop-blur-md sm:items-center sm:p-5"
      role="dialog"
      aria-modal="true"
      aria-labelledby="content-modal-title"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="max-h-[96vh] w-full max-w-5xl overflow-y-auto rounded-t-xl border border-white/10 bg-[#0d0f15] shadow-2xl [scrollbar-color:rgba(148,163,184,0.2)_transparent] sm:rounded-xl">
        <div className="relative min-h-[340px] overflow-hidden sm:min-h-[420px]">
          {backdropUrl && !imageFailed ? (
            <img
              src={backdropUrl}
              alt=""
              onError={() => setImageFailed(true)}
              className="absolute inset-0 h-full w-full object-cover"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-violet-950 via-slate-900 to-blue-950">
              <Film className="h-16 w-16 text-white/10" />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/45 to-black/20" />
          <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8 lg:p-10">
            <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-slate-300">
              {matchPercent !== null && (
                <span className="bg-emerald-400/15 px-2 py-1 font-semibold text-emerald-200">
                  {matchPercent}% dopasowania
                </span>
              )}
              {releaseYear && <span>{releaseYear}</span>}
              {runtime && <span>•</span>}
              {runtime && <span>{runtime}</span>}
              {content.metadata.certification && (
                <span className="rounded border border-white/20 px-1.5 py-0.5 text-[10px]">
                  {content.metadata.certification}
                </span>
              )}
            </div>
            <h2 id="content-modal-title" className="max-w-3xl text-3xl font-bold tracking-tight text-white sm:text-5xl">
              {content.title}
            </h2>
            {content.originalTitle && <p className="mt-2 text-sm text-slate-400">{content.originalTitle}</p>}
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => onWatchlist(candidate)}
                title={isWatchlisted ? 'Usuń z listy' : 'Zapisz na później'}
                className={`flex h-10 items-center gap-2 rounded-md px-4 text-xs font-semibold transition ${
                  isWatchlisted
                    ? 'bg-violet-500/20 text-violet-100 ring-1 ring-violet-400/30 hover:bg-red-500/15 hover:text-red-200 hover:ring-red-400/20'
                    : 'bg-black/40 text-white ring-1 ring-white/15 hover:bg-black/60'
                }`}
              >
                <Bookmark className={`h-4 w-4 ${isWatchlisted ? 'fill-current' : ''}`} />
                {isWatchlisted ? 'Na Twojej liście' : 'Zapisz'}
              </button>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-black/50 text-white backdrop-blur-md transition hover:bg-black/80"
            aria-label="Zamknij szczegóły"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid gap-8 p-5 sm:p-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(250px,0.6fr)] lg:p-10">
          <div>
            <div className="mb-8 border-l-2 border-violet-500/60 pl-5">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.1em] text-slate-300">
                Dlaczego ten tytuł?
              </h3>
              <p className="text-sm leading-7 text-slate-300">
                {candidate.explanation ?? 'Brak wyjaśnienia dla tej rekomendacji.'}
              </p>
            </div>

            <h3 className="text-sm font-semibold text-white">Opis</h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">
              {content.overview ?? 'Brak opisu.'}
            </p>
          </div>

          <aside>
            <div className="rounded-lg border border-white/[0.07] bg-white/[0.025] p-5">
              {content.voteAverage !== null && (
                <div className="flex items-center justify-between border-b border-white/[0.06] pb-4">
                  <span className="text-xs text-slate-500">Ocena widzów</span>
                  <span className="flex items-center gap-1.5 text-sm font-bold text-white">
                    <Star className="h-4 w-4 fill-amber-300 text-amber-300" />
                    {content.voteAverage.toFixed(1)}
                  </span>
                </div>
              )}
              <dl className="space-y-4 py-4 text-xs">
                {content.metadata.director && (
                  <div>
                    <dt className="text-slate-600">Reżyseria</dt>
                    <dd className="mt-1 text-slate-300">{content.metadata.director}</dd>
                  </div>
                )}
                <div>
                  <dt className="text-slate-600">Gatunki</dt>
                  <dd className="mt-1 text-slate-300">
                    {content.genres.map((genre) => genre.name).join(', ')}
                  </dd>
                </div>
                {providers.length > 0 && (
                  <div>
                    <dt className="text-slate-600">Dostępność</dt>
                    <dd className="mt-2 flex flex-wrap gap-1.5">
                      {providers.map((provider) => (
                        <span key={provider} className="rounded-md bg-white/[0.06] px-2 py-1 text-slate-300">
                          {provider}
                        </span>
                      ))}
                    </dd>
                  </div>
                )}
              </dl>
              <button
                type="button"
                onClick={() => onMarkWatched(candidate)}
                title={isWatched ? 'Cofnij oznaczenie jako obejrzany' : 'Oznacz jako obejrzany'}
                className={`mt-1 flex h-10 w-full items-center justify-center gap-2 rounded-md border text-xs font-medium transition ${
                  isWatched
                    ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200 hover:border-red-400/20 hover:bg-red-500/10 hover:text-red-300'
                    : 'border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.07]'
                }`}
              >
                {isWatched ? <Check className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {isWatched ? 'Oznaczono jako obejrzany' : 'Oznacz jako obejrzany'}
              </button>
            </div>
            <div className="mt-3 flex items-center justify-center gap-2 text-[10px] text-slate-700">
              <Clock3 className="h-3 w-3" />
              Metadane zsynchronizowane z TMDB
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
