import {
  Bookmark,
  Check,
  ChevronRight,
  Eye,
  Film,
  Info,
  Sparkles,
  Star,
} from 'lucide-react';
import { useState } from 'react';
import type { Movie } from '../types';

interface RecommendationCardProps {
  movie: Movie;
  index: number;
  isSaved: boolean;
  isWatched: boolean;
  onOpen: (movie: Movie) => void;
  onToggleSaved: (movieId: number) => void;
  onToggleWatched: (movieId: number) => void;
}

export function RecommendationCard({
  movie,
  index,
  isSaved,
  isWatched,
  onOpen,
  onToggleSaved,
  onToggleWatched,
}: RecommendationCardProps) {
  const [imageFailed, setImageFailed] = useState(false);

  return (
    <article className="group overflow-hidden rounded-3xl border border-white/[0.08] bg-ink-900/80 shadow-card transition duration-500 hover:-translate-y-1 hover:border-white/[0.14]">
      <button
        type="button"
        onClick={() => onOpen(movie)}
        className="relative block aspect-[16/10] w-full overflow-hidden text-left"
        aria-label={`Pokaż szczegóły: ${movie.title}`}
      >
        {!imageFailed ? (
          <img
            src={movie.backdropUrl}
            alt=""
            onError={() => setImageFailed(true)}
            className="h-full w-full object-cover transition duration-700 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-violet-950 via-slate-900 to-blue-950">
            <Film className="h-10 w-10 text-white/15" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-ink-900 via-ink-900/25 to-transparent" />
        <div className="absolute left-4 top-4 flex items-center gap-2">
          <span className="rounded-lg border border-white/10 bg-black/50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-white backdrop-blur-md">
            #{index + 1} wybór
          </span>
          <span className="rounded-lg border border-emerald-300/15 bg-emerald-400/15 px-2 py-1 text-[10px] font-semibold text-emerald-200 backdrop-blur-md">
            {movie.matchScore}% dopasowania
          </span>
        </div>
        <div className="absolute right-4 top-4 flex gap-2">
          {isWatched && (
            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-black/50 text-emerald-300 backdrop-blur-md">
              <Check className="h-4 w-4" />
            </span>
          )}
          <span className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-black/50 text-white opacity-0 backdrop-blur-md transition group-hover:opacity-100">
            <Info className="h-4 w-4" />
          </span>
        </div>
        <div className="absolute inset-x-4 bottom-3">
          <div className="mb-1.5 flex items-center gap-2 text-[11px] text-slate-300">
            <span className="flex items-center gap-1 font-semibold text-amber-300">
              <Star className="h-3 w-3 fill-current" />
              {movie.rating.toFixed(1)}
            </span>
            <span className="h-1 w-1 rounded-full bg-slate-500" />
            <span>{movie.year}</span>
            <span className="h-1 w-1 rounded-full bg-slate-500" />
            <span>{movie.runtime}</span>
            <span className="rounded border border-white/15 px-1 py-0.5 text-[9px]">{movie.certification}</span>
          </div>
          <h3 className="text-xl font-bold tracking-tight text-white sm:text-2xl">{movie.title}</h3>
          <p className="mt-0.5 text-xs text-slate-400">{movie.originalTitle}</p>
        </div>
      </button>

      <div className="p-4 sm:p-5">
        <div className="mb-4 flex flex-wrap gap-1.5">
          {movie.genres.map((genre) => (
            <span
              key={genre}
              className="rounded-md bg-white/[0.05] px-2 py-1 text-[10px] font-medium text-slate-400"
            >
              {genre}
            </span>
          ))}
        </div>

        <div className="rounded-2xl border border-violet-400/10 bg-gradient-to-br from-violet-500/[0.08] to-blue-500/[0.04] p-4">
          <div className="mb-2 flex items-center gap-2 text-violet-300">
            <Sparkles className="h-3.5 w-3.5" />
            <h4 className="text-xs font-semibold">Dlaczego to polecamy?</h4>
          </div>
          <p className="line-clamp-4 text-xs leading-relaxed text-slate-400">{movie.explanation}</p>
          <button
            type="button"
            onClick={() => onOpen(movie)}
            className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-violet-300 transition hover:text-violet-200"
          >
            Pełne uzasadnienie
            <ChevronRight className="h-3 w-3" />
          </button>
        </div>

        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={() => onToggleSaved(movie.id)}
            className={`flex h-10 flex-1 items-center justify-center gap-2 rounded-xl text-xs font-semibold transition ${
              isSaved
                ? 'bg-violet-500/15 text-violet-200 ring-1 ring-violet-400/20 hover:bg-violet-500/20'
                : 'bg-white text-ink-950 hover:bg-violet-100'
            }`}
          >
            <Bookmark className={`h-3.5 w-3.5 ${isSaved ? 'fill-current' : ''}`} />
            {isSaved ? 'Zapisano' : 'Zapisz'}
          </button>
          <button
            type="button"
            onClick={() => onToggleWatched(movie.id)}
            className={`flex h-10 flex-1 items-center justify-center gap-2 rounded-xl border text-xs font-semibold transition ${
              isWatched
                ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200'
                : 'border-white/10 bg-white/[0.03] text-slate-300 hover:bg-white/[0.07]'
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            {isWatched ? 'Obejrzano' : 'Oznacz jako obejrzany'}
          </button>
        </div>
      </div>
    </article>
  );
}
