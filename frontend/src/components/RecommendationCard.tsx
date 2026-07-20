import { Bookmark, Check, ChevronRight, Eye, Film, Star } from 'lucide-react';
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
    <article className="group grid grid-cols-[104px_minmax(0,1fr)] overflow-hidden rounded-xl border border-white/[0.08] bg-[#0d0f15] transition-colors hover:border-white/[0.14] sm:grid-cols-[148px_minmax(0,1fr)]">
      <button
        type="button"
        onClick={() => onOpen(movie)}
        className="relative min-h-[230px] overflow-hidden bg-slate-900 text-left sm:min-h-[250px]"
        aria-label={`Pokaż szczegóły: ${movie.title}`}
      >
        {!imageFailed ? (
          <img
            src={movie.posterUrl}
            alt={`Plakat filmu ${movie.title}`}
            onError={() => setImageFailed(true)}
            className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <span className="flex h-full w-full items-center justify-center bg-slate-900">
            <Film className="h-7 w-7 text-slate-700" />
          </span>
        )}
        <span className="absolute left-2 top-2 bg-black/75 px-1.5 py-1 text-[9px] font-semibold text-white backdrop-blur-sm">
          {String(index + 1).padStart(2, '0')}
        </span>
      </button>

      <div className="flex min-w-0 flex-col p-3.5 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <button type="button" onClick={() => onOpen(movie)} className="text-left">
              <h3 className="truncate text-base font-semibold tracking-tight text-white transition group-hover:text-violet-200 sm:text-xl">
                {movie.title}
              </h3>
            </button>
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-slate-500 sm:text-xs">
              <span>{movie.year}</span>
              <span className="text-slate-700">/</span>
              <span>{movie.runtime}</span>
              <span className="hidden text-slate-700 sm:inline">/</span>
              <span className="hidden sm:inline">{movie.certification}</span>
            </div>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-sm font-semibold text-emerald-400">{movie.matchScore}%</p>
            <p className="text-[9px] text-slate-600">dopasowania</p>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="mr-1 flex items-center gap-1 text-[10px] font-medium text-amber-300">
            <Star className="h-3 w-3 fill-current" />
            {movie.rating.toFixed(1)}
          </span>
          {movie.genres.slice(0, 3).map((genre, genreIndex) => (
            <span key={genre} className="text-[10px] text-slate-500">
              {genre}
              {genreIndex < Math.min(movie.genres.length, 3) - 1 ? (
                <span className="ml-1.5 text-slate-700">·</span>
              ) : null}
            </span>
          ))}
        </div>

        <div className="mt-4 border-l-2 border-violet-500/50 pl-3">
          <p className="mb-1 text-[10px] font-medium uppercase tracking-[0.1em] text-slate-600">
            Dlaczego ten tytuł
          </p>
          <p className="line-clamp-4 text-[11px] leading-5 text-slate-400 sm:text-xs">
            {movie.explanation}
          </p>
        </div>

        <div className="mt-auto flex items-center gap-1 pt-4">
          <button
            type="button"
            onClick={() => onToggleSaved(movie.id)}
            className={`flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[10px] font-medium transition sm:text-[11px] ${
              isSaved
                ? 'bg-violet-500/15 text-violet-200'
                : 'bg-white/[0.05] text-slate-400 hover:bg-white/[0.08] hover:text-white'
            }`}
          >
            <Bookmark className={`h-3.5 w-3.5 ${isSaved ? 'fill-current' : ''}`} />
            <span className="hidden sm:inline">{isSaved ? 'Zapisano' : 'Zapisz'}</span>
          </button>
          <button
            type="button"
            onClick={() => onToggleWatched(movie.id)}
            className={`flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[10px] font-medium transition sm:text-[11px] ${
              isWatched
                ? 'bg-emerald-500/10 text-emerald-300'
                : 'text-slate-500 hover:bg-white/[0.05] hover:text-slate-300'
            }`}
          >
            {isWatched ? <Check className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{isWatched ? 'Obejrzano' : 'Obejrzany'}</span>
          </button>
          <button
            type="button"
            onClick={() => onOpen(movie)}
            className="ml-auto flex h-8 items-center gap-1 text-[10px] font-medium text-slate-500 transition hover:text-white sm:text-[11px]"
          >
            Szczegóły
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </article>
  );
}
