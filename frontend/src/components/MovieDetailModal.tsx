import {
  Bookmark,
  Check,
  Clock3,
  Eye,
  Film,
  Play,
  Star,
  X,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Movie } from '../types';

interface MovieDetailModalProps {
  movie: Movie | null;
  isSaved: boolean;
  isWatched: boolean;
  onClose: () => void;
  onToggleSaved: (movieId: number) => void;
  onToggleWatched: (movieId: number) => void;
}

export function MovieDetailModal({
  movie,
  isSaved,
  isWatched,
  onClose,
  onToggleSaved,
  onToggleWatched,
}: MovieDetailModalProps) {
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    if (!movie) return;

    document.body.classList.add('overflow-hidden');
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);

    return () => {
      document.body.classList.remove('overflow-hidden');
      window.removeEventListener('keydown', handleEscape);
    };
  }, [movie, onClose]);

  useEffect(() => setImageFailed(false), [movie?.id]);

  if (!movie) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 p-0 backdrop-blur-md sm:items-center sm:p-5"
      role="dialog"
      aria-modal="true"
      aria-labelledby="movie-modal-title"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="max-h-[96vh] w-full max-w-5xl overflow-y-auto rounded-t-xl border border-white/10 bg-[#0d0f15] shadow-2xl [scrollbar-color:rgba(148,163,184,0.2)_transparent] sm:rounded-xl">
        <div className="relative min-h-[340px] overflow-hidden sm:min-h-[420px]">
          {!imageFailed ? (
            <img
              src={movie.backdropUrl}
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
              <span className="bg-emerald-400/15 px-2 py-1 font-semibold text-emerald-200">
                {movie.matchScore}% dopasowania
              </span>
              <span>{movie.year}</span>
              <span>•</span>
              <span>{movie.runtime}</span>
              <span className="rounded border border-white/20 px-1.5 py-0.5 text-[10px]">{movie.certification}</span>
            </div>
            <h2 id="movie-modal-title" className="max-w-3xl text-3xl font-bold tracking-tight text-white sm:text-5xl">
              {movie.title}
            </h2>
            <p className="mt-2 text-sm text-slate-400">{movie.originalTitle}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                className="flex h-10 items-center gap-2 rounded-md bg-white px-4 text-xs font-semibold text-ink-950 transition hover:bg-slate-200"
              >
                <Play className="h-4 w-4 fill-current" />
                Zobacz zwiastun
              </button>
              <button
                type="button"
                onClick={() => onToggleSaved(movie.id)}
                className={`flex h-10 items-center gap-2 rounded-md px-4 text-xs font-semibold transition ${
                  isSaved
                    ? 'bg-violet-500/20 text-violet-100 ring-1 ring-violet-400/30'
                    : 'bg-black/40 text-white ring-1 ring-white/15 hover:bg-black/60'
                }`}
              >
                <Bookmark className={`h-4 w-4 ${isSaved ? 'fill-current' : ''}`} />
                {isSaved ? 'Na Twojej liście' : 'Zapisz'}
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
              <div className="mb-2 text-slate-300">
                <h3 className="text-xs font-semibold uppercase tracking-[0.1em]">Dlaczego ten tytuł?</h3>
              </div>
              <p className="text-sm leading-7 text-slate-300">{movie.explanation}</p>
            </div>

            <h3 className="text-sm font-semibold text-white">Opis</h3>
            <p className="mt-3 text-sm leading-7 text-slate-400">{movie.overview}</p>

            <h3 className="mt-8 text-sm font-semibold text-white">Główna obsada</h3>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {movie.cast.map((person) => (
                <div key={person.id} className="rounded-md border border-white/[0.06] bg-white/[0.025] p-3">
                  <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-[10px] font-semibold text-slate-400">
                    {person.name
                      .split(' ')
                      .map((part) => part[0])
                      .join('')}
                  </div>
                  <p className="text-xs font-medium text-slate-200">{person.name}</p>
                  <p className="mt-1 text-[10px] text-slate-600">{person.character}</p>
                </div>
              ))}
            </div>
          </div>

          <aside>
            <div className="rounded-lg border border-white/[0.07] bg-white/[0.025] p-5">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-4">
                <span className="text-xs text-slate-500">Ocena widzów</span>
                <span className="flex items-center gap-1.5 text-sm font-bold text-white">
                  <Star className="h-4 w-4 fill-amber-300 text-amber-300" />
                  {movie.rating.toFixed(1)}
                </span>
              </div>
              <dl className="space-y-4 py-4 text-xs">
                <div>
                  <dt className="text-slate-600">Reżyseria</dt>
                  <dd className="mt-1 text-slate-300">{movie.director}</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Gatunki</dt>
                  <dd className="mt-1 text-slate-300">{movie.genres.join(', ')}</dd>
                </div>
                <div>
                  <dt className="text-slate-600">Dostępność</dt>
                  <dd className="mt-2 flex flex-wrap gap-1.5">
                    {movie.providers.map((provider) => (
                      <span key={provider} className="rounded-md bg-white/[0.06] px-2 py-1 text-slate-300">
                        {provider}
                      </span>
                    ))}
                  </dd>
                </div>
              </dl>
              <button
                type="button"
                onClick={() => onToggleWatched(movie.id)}
                className={`mt-1 flex h-10 w-full items-center justify-center gap-2 rounded-md border text-xs font-medium transition ${
                  isWatched
                    ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200'
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
