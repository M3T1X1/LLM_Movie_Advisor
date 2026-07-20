import {
  ArrowUpDown,
  Bookmark,
  Check,
  Eye,
  Film,
  Library,
  Search,
  SlidersHorizontal,
  Star,
  Tv,
  X,
} from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import type { Content, DatabaseId, MediaType } from '../types';
import { getPosterUrl, getReleaseYear } from '../utils/content';

type MediaFilter = 'all' | MediaType;
type SortOption = 'popularity' | 'rating' | 'newest' | 'title';

interface CatalogViewProps {
  content: Content[];
  watchlistedContentIds: DatabaseId[];
  watchedContentIds: DatabaseId[];
  onOpen: (content: Content) => void;
  onWatchlist: (content: Content) => void;
  onMarkWatched: (content: Content) => void;
}

export function CatalogView({
  content,
  watchlistedContentIds,
  watchedContentIds,
  onOpen,
  onWatchlist,
  onMarkWatched,
}: CatalogViewProps) {
  const [query, setQuery] = useState('');
  const [mediaType, setMediaType] = useState<MediaFilter>('all');
  const [genre, setGenre] = useState('all');
  const [minimumRating, setMinimumRating] = useState('0');
  const [yearFrom, setYearFrom] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('popularity');

  const genres = useMemo(
    () => Array.from(new Set(content.flatMap((item) => item.genres.map((itemGenre) => itemGenre.name)))).sort(),
    [content],
  );

  const filteredContent = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('pl-PL');
    const minimumYear = Number(yearFrom) || 0;
    const rating = Number(minimumRating);

    return content
      .filter((item) => {
        const releaseYear = getReleaseYear(item) ?? 0;
        const matchesQuery =
          !normalizedQuery ||
          item.title.toLocaleLowerCase('pl-PL').includes(normalizedQuery) ||
          item.originalTitle?.toLocaleLowerCase('pl-PL').includes(normalizedQuery);
        const matchesType = mediaType === 'all' || item.mediaType === mediaType;
        const matchesGenre = genre === 'all' || item.genres.some((itemGenre) => itemGenre.name === genre);
        const matchesRating = (item.voteAverage ?? 0) >= rating;
        const matchesYear = releaseYear >= minimumYear;
        return matchesQuery && matchesType && matchesGenre && matchesRating && matchesYear;
      })
      .sort((first, second) => {
        if (sortBy === 'rating') return (second.voteAverage ?? 0) - (first.voteAverage ?? 0);
        if (sortBy === 'newest') return (getReleaseYear(second) ?? 0) - (getReleaseYear(first) ?? 0);
        if (sortBy === 'title') return first.title.localeCompare(second.title, 'pl');
        return (second.popularity ?? 0) - (first.popularity ?? 0);
      });
  }, [content, genre, mediaType, minimumRating, query, sortBy, yearFrom]);

  const hasActiveFilters =
    Boolean(query) || mediaType !== 'all' || genre !== 'all' || minimumRating !== '0' || Boolean(yearFrom);

  const clearFilters = () => {
    setQuery('');
    setMediaType('all');
    setGenre('all');
    setMinimumRating('0');
    setYearFrom('');
  };

  return (
    <div>
      <header className="mb-7 border-b border-white/[0.07] pb-7">
        <p className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-600">
          <Library className="h-4 w-4" />
          Katalog TMDB
        </p>
        <h1 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
          Baza filmów i seriali
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
          Przeglądaj katalog niezależnie od rekomendacji i zapisuj interesujące tytuły na swoją listę.
        </p>
      </header>

      <section className="mb-6 rounded-xl border border-white/[0.08] bg-[#0d0f15] p-4" aria-label="Filtry katalogu">
        <div className="grid gap-3 lg:grid-cols-[minmax(260px,1fr)_auto]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Szukaj po tytule..."
              className="h-10 w-full rounded-md border border-white/[0.08] bg-white/[0.025] pl-10 pr-3 text-xs text-white outline-none transition placeholder:text-slate-700 focus:border-violet-500/60"
            />
          </label>

          <div className="grid grid-cols-3 rounded-md border border-white/[0.08] p-1">
            <MediaTypeButton active={mediaType === 'all'} onClick={() => setMediaType('all')} label="Wszystko" />
            <MediaTypeButton
              active={mediaType === 'movie'}
              onClick={() => setMediaType('movie')}
              label="Filmy"
              icon={<Film className="h-3.5 w-3.5" />}
            />
            <MediaTypeButton
              active={mediaType === 'tv'}
              onClick={() => setMediaType('tv')}
              label="Seriale"
              icon={<Tv className="h-3.5 w-3.5" />}
            />
          </div>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <FilterSelect label="Gatunek" value={genre} onChange={setGenre}>
            <option value="all">Wszystkie gatunki</option>
            {genres.map((itemGenre) => (
              <option key={itemGenre} value={itemGenre}>{itemGenre}</option>
            ))}
          </FilterSelect>

          <FilterSelect label="Minimalna ocena" value={minimumRating} onChange={setMinimumRating}>
            <option value="0">Dowolna ocena</option>
            <option value="6">Od 6.0</option>
            <option value="7">Od 7.0</option>
            <option value="8">Od 8.0</option>
          </FilterSelect>

          <label className="block">
            <span className="mb-1.5 block text-[9px] font-medium uppercase tracking-[0.1em] text-slate-600">
              Rok produkcji od
            </span>
            <input
              type="number"
              min="1900"
              max={new Date().getFullYear()}
              value={yearFrom}
              onChange={(event) => setYearFrom(event.target.value)}
              placeholder="np. 2015"
              className="h-9 w-full rounded-md border border-white/[0.08] bg-white/[0.025] px-3 text-xs text-white outline-none transition placeholder:text-slate-700 focus:border-violet-500/60"
            />
          </label>

          <FilterSelect label="Sortowanie" value={sortBy} onChange={(value) => setSortBy(value as SortOption)}>
            <option value="popularity">Najpopularniejsze</option>
            <option value="rating">Najwyżej oceniane</option>
            <option value="newest">Najnowsze</option>
            <option value="title">Alfabetycznie</option>
          </FilterSelect>
        </div>
      </section>

      <div className="mb-4 flex items-center justify-between border-b border-white/[0.07] pb-3">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          <span>{filteredContent.length} {filteredContent.length === 1 ? 'wynik' : 'wyników'}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-1.5 text-[10px] text-slate-700 sm:flex">
            <ArrowUpDown className="h-3 w-3" />
            {sortBy === 'popularity' ? 'Popularność' : sortBy === 'rating' ? 'Ocena' : sortBy === 'newest' ? 'Data premiery' : 'Tytuł'}
          </span>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="flex items-center gap-1.5 text-[10px] text-slate-500 transition hover:text-white"
            >
              <X className="h-3 w-3" />
              Wyczyść filtry
            </button>
          )}
        </div>
      </div>

      {filteredContent.length ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
          {filteredContent.map((item) => (
            <CatalogCard
              key={item.id}
              content={item}
              isWatchlisted={watchlistedContentIds.includes(item.id)}
              isWatched={watchedContentIds.includes(item.id)}
              onOpen={onOpen}
              onWatchlist={onWatchlist}
              onMarkWatched={onMarkWatched}
            />
          ))}
        </div>
      ) : (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] text-center">
          <Search className="mb-3 h-5 w-5 text-slate-700" />
          <p className="text-sm font-medium text-slate-400">Brak pasujących tytułów</p>
          <button type="button" onClick={clearFilters} className="mt-2 text-xs text-violet-400 hover:text-violet-300">
            Wyczyść filtry
          </button>
        </div>
      )}
    </div>
  );
}

function MediaTypeButton({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-8 items-center justify-center gap-1.5 rounded px-2 text-[10px] font-medium transition ${
        active ? 'bg-white/[0.08] text-white' : 'text-slate-600 hover:text-slate-300'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[9px] font-medium uppercase tracking-[0.1em] text-slate-600">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full rounded-md border border-white/[0.08] bg-[#11141c] px-3 text-xs text-slate-300 outline-none transition focus:border-violet-500/60"
      >
        {children}
      </select>
    </label>
  );
}

export function CatalogCard({
  content,
  isWatchlisted,
  isWatched,
  onOpen,
  onWatchlist,
  onMarkWatched,
}: {
  content: Content;
  isWatchlisted: boolean;
  isWatched: boolean;
  onOpen: (content: Content) => void;
  onWatchlist: (content: Content) => void;
  onMarkWatched: (content: Content) => void;
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const posterUrl = getPosterUrl(content);
  const releaseYear = getReleaseYear(content);

  return (
    <article className="group overflow-hidden rounded-lg border border-white/[0.08] bg-[#0d0f15] transition hover:border-white/[0.15]">
      <button
        type="button"
        onClick={() => onOpen(content)}
        className="block w-full text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-400/70"
        aria-label={`Pokaż szczegóły: ${content.title}`}
      >
        <div className="relative aspect-[2/3] overflow-hidden bg-slate-900">
          {posterUrl && !imageFailed ? (
            <img
              src={posterUrl}
              alt={`Plakat: ${content.title}`}
              onError={() => setImageFailed(true)}
              className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              {content.mediaType === 'tv' ? <Tv className="h-8 w-8 text-slate-700" /> : <Film className="h-8 w-8 text-slate-700" />}
            </div>
          )}
          <span className="absolute left-2 top-2 flex items-center gap-1 bg-black/75 px-2 py-1 text-[9px] font-medium text-slate-200 backdrop-blur-sm">
            {content.mediaType === 'tv' ? <Tv className="h-2.5 w-2.5" /> : <Film className="h-2.5 w-2.5" />}
            {content.mediaType === 'tv' ? 'Serial' : 'Film'}
          </span>
          {isWatched && (
            <span className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500 text-white">
              <Check className="h-3.5 w-3.5" />
            </span>
          )}
        </div>

        <div className="px-3.5 pt-3.5">
          <h2 className="truncate text-sm font-semibold text-white transition group-hover:text-violet-200" title={content.title}>{content.title}</h2>
          <div className="mt-1.5 flex items-center gap-2 text-[10px] text-slate-600">
            {releaseYear && <span>{releaseYear}</span>}
            {content.voteAverage !== null && (
              <span className="flex items-center gap-1 text-amber-300">
                <Star className="h-2.5 w-2.5 fill-current" />
                {content.voteAverage.toFixed(1)}
              </span>
            )}
          </div>
          <p className="mt-2 truncate text-[10px] text-slate-600">
            {content.genres.slice(0, 2).map((genre) => genre.name).join(' · ')}
          </p>
        </div>
      </button>

      <div className="px-3.5 pb-3.5">
        <div className="mt-3 grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={() => onWatchlist(content)}
            title={isWatchlisted ? 'Usuń z listy' : 'Zapisz na później'}
            className={`flex h-8 items-center justify-center gap-1.5 rounded-md text-[10px] font-medium transition ${
              isWatchlisted
                ? 'bg-violet-500/15 text-violet-200 hover:bg-red-500/10 hover:text-red-300'
                : 'bg-white/[0.05] text-slate-400 hover:bg-white/[0.09] hover:text-white'
            }`}
          >
            <Bookmark className={`h-3.5 w-3.5 ${isWatchlisted ? 'fill-current' : ''}`} />
            {isWatchlisted ? 'Zapisano' : 'Zapisz'}
          </button>
          <button
            type="button"
            onClick={() => onMarkWatched(content)}
            title={isWatched ? 'Cofnij oznaczenie jako obejrzany' : 'Oznacz jako obejrzany'}
            className={`flex h-8 items-center justify-center gap-1.5 rounded-md text-[10px] font-medium transition ${
              isWatched
                ? 'bg-emerald-500/10 text-emerald-300 hover:bg-red-500/10 hover:text-red-300'
                : 'bg-white/[0.03] text-slate-500 hover:bg-white/[0.08] hover:text-white'
            }`}
          >
            {isWatched ? <Check className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            {isWatched ? 'Obejrzano' : 'Obejrzyj'}
          </button>
        </div>
      </div>
    </article>
  );
}
