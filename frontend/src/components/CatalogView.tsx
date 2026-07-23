import {
  ArrowUpDown,
  Bookmark,
  Check,
  ChevronLeft,
  ChevronRight,
  Eye,
  Film,
  Library,
  Search,
  SlidersHorizontal,
  Star,
  Tv,
  X,
} from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import type {
  CatalogPage,
  CatalogQuery,
  Content,
  DatabaseId,
} from '../types';
import { getPosterUrl, getReleaseYear } from '../utils/content';

interface CatalogViewProps {
  content: Content[];
  genres: string[];
  pagination: CatalogPage['pagination'];
  query: CatalogQuery;
  isLoading: boolean;
  error: string | null;
  onQueryChange: (query: CatalogQuery) => void;
  watchlistedContentIds: DatabaseId[];
  watchedContentIds: DatabaseId[];
  onOpen: (content: Content) => void;
  onWatchlist: (content: Content) => void;
  onMarkWatched: (content: Content) => void;
}

export function CatalogView({
  content,
  genres,
  pagination,
  query,
  isLoading,
  error,
  onQueryChange,
  watchlistedContentIds,
  watchedContentIds,
  onOpen,
  onWatchlist,
  onMarkWatched,
}: CatalogViewProps) {
  const [searchInput, setSearchInput] = useState(query.search);
  const [yearInput, setYearInput] = useState(
    query.yearFrom === null ? '' : String(query.yearFrom),
  );

  useEffect(() => {
    setSearchInput(query.search);
  }, [query.search]);

  useEffect(() => {
    setYearInput(query.yearFrom === null ? '' : String(query.yearFrom));
  }, [query.yearFrom]);

  useEffect(() => {
    if (searchInput === query.search) return undefined;
    const timeout = window.setTimeout(() => {
      onQueryChange({ ...query, page: 1, search: searchInput });
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [onQueryChange, query, searchInput]);

  const hasActiveFilters =
    Boolean(query.search) ||
    query.mediaType !== 'all' ||
    query.genre !== 'all' ||
    query.minimumRating !== 0 ||
    query.yearFrom !== null;

  const clearFilters = () => {
    setSearchInput('');
    setYearInput('');
    onQueryChange({
      ...query,
      page: 1,
      search: '',
      mediaType: 'all',
      genre: 'all',
      minimumRating: 0,
      yearFrom: null,
    });
  };

  const updateQuery = (changes: Partial<CatalogQuery>) => {
    onQueryChange({ ...query, ...changes, page: changes.page ?? 1 });
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
              value={searchInput}
              maxLength={200}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Szukaj po tytule..."
              className="h-10 w-full rounded-md border border-white/[0.08] bg-white/[0.025] pl-10 pr-3 text-xs text-white outline-none transition placeholder:text-slate-700 focus:border-violet-500/60"
            />
          </label>

          <div className="grid grid-cols-3 rounded-md border border-white/[0.08] p-1">
            <MediaTypeButton active={query.mediaType === 'all'} onClick={() => updateQuery({ mediaType: 'all' })} label="Wszystko" />
            <MediaTypeButton
              active={query.mediaType === 'movie'}
              onClick={() => updateQuery({ mediaType: 'movie' })}
              label="Filmy"
              icon={<Film className="h-3.5 w-3.5" />}
            />
            <MediaTypeButton
              active={query.mediaType === 'tv'}
              onClick={() => updateQuery({ mediaType: 'tv' })}
              label="Seriale"
              icon={<Tv className="h-3.5 w-3.5" />}
            />
          </div>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <FilterSelect label="Gatunek" value={query.genre} onChange={(genre) => updateQuery({ genre })}>
            <option value="all">Wszystkie gatunki</option>
            {genres.map((itemGenre) => (
              <option key={itemGenre} value={itemGenre}>{itemGenre}</option>
            ))}
          </FilterSelect>

          <FilterSelect label="Minimalna ocena" value={String(query.minimumRating)} onChange={(value) => updateQuery({ minimumRating: Number(value) })}>
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
              max={new Date().getFullYear() + 10}
              value={yearInput}
              onChange={(event) => {
                const value = event.target.value;
                setYearInput(value);
                if (!value) {
                  updateQuery({ yearFrom: null });
                  return;
                }
                const year = Number(value);
                if (
                  Number.isInteger(year) &&
                  year >= 1888 &&
                  year <= new Date().getFullYear() + 10
                ) {
                  updateQuery({ yearFrom: year });
                }
              }}
              placeholder="np. 2015"
              className="h-9 w-full rounded-md border border-white/[0.08] bg-white/[0.025] px-3 text-xs text-white outline-none transition placeholder:text-slate-700 focus:border-violet-500/60"
            />
          </label>

          <FilterSelect label="Sortowanie" value={query.sortBy} onChange={(value) => updateQuery({ sortBy: value as CatalogQuery['sortBy'] })}>
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
          <span>
            {pagination.totalItems}{' '}
            {pagination.totalItems === 1 ? 'wynik' : 'wyników'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-1.5 text-[10px] text-slate-700 sm:flex">
            <ArrowUpDown className="h-3 w-3" />
            {query.sortBy === 'popularity' ? 'Popularność' : query.sortBy === 'rating' ? 'Ocena' : query.sortBy === 'newest' ? 'Data premiery' : 'Tytuł'}
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

      {error ? (
        <div role="alert" className="mb-5 rounded-lg border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      {content.length ? (
        <div
          className={`grid gap-4 transition-opacity sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 ${
            isLoading ? 'opacity-50' : ''
          }`}
          aria-busy={isLoading}
        >
          {content.map((item) => (
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
      ) : !isLoading && !error ? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] text-center">
          <Search className="mb-3 h-5 w-5 text-slate-700" />
          <p className="text-sm font-medium text-slate-400">Brak pasujących tytułów</p>
          <button type="button" onClick={clearFilters} className="mt-2 text-xs text-violet-400 hover:text-violet-300">
            Wyczyść filtry
          </button>
        </div>
      ) : isLoading ? (
        <div className="flex min-h-64 items-center justify-center text-sm text-slate-500" role="status">
          Ładowanie katalogu…
        </div>
      ) : null}

      {pagination.totalPages > 1 && (
        <CatalogPagination
          page={pagination.page}
          totalPages={pagination.totalPages}
          hasPrevious={pagination.hasPrevious}
          hasNext={pagination.hasNext}
          disabled={isLoading}
          onPageChange={(page) => {
            updateQuery({ page });
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        />
      )}
    </div>
  );
}

function CatalogPagination({
  page,
  totalPages,
  hasPrevious,
  hasNext,
  disabled,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  hasPrevious: boolean;
  hasNext: boolean;
  disabled: boolean;
  onPageChange: (page: number) => void;
}) {
  const firstPage = Math.max(1, Math.min(page - 2, totalPages - 4));
  const visiblePages = Array.from(
    { length: Math.min(5, totalPages) },
    (_, index) => firstPage + index,
  );

  return (
    <nav className="mt-8 flex flex-wrap items-center justify-center gap-2 border-t border-white/[0.07] pt-6" aria-label="Paginacja katalogu">
      <button
        type="button"
        disabled={disabled || !hasPrevious}
        onClick={() => onPageChange(page - 1)}
        className="flex h-9 items-center gap-1 rounded-md border border-white/[0.08] px-3 text-xs text-slate-400 transition hover:border-white/[0.16] hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        Poprzednia
      </button>
      {visiblePages.map((pageNumber) => (
        <button
          key={pageNumber}
          type="button"
          disabled={disabled}
          aria-current={pageNumber === page ? 'page' : undefined}
          aria-label={`Strona ${pageNumber}`}
          onClick={() => onPageChange(pageNumber)}
          className={`h-9 min-w-9 rounded-md border px-2 text-xs transition ${
            pageNumber === page
              ? 'border-violet-400/50 bg-violet-500/15 text-violet-200'
              : 'border-white/[0.08] text-slate-500 hover:border-white/[0.16] hover:text-white'
          } disabled:cursor-not-allowed disabled:opacity-50`}
        >
          {pageNumber}
        </button>
      ))}
      <button
        type="button"
        disabled={disabled || !hasNext}
        onClick={() => onPageChange(page + 1)}
        className="flex h-9 items-center gap-1 rounded-md border border-white/[0.08] px-3 text-xs text-slate-400 transition hover:border-white/[0.16] hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
      >
        Następna
        <ChevronRight className="h-3.5 w-3.5" />
      </button>
      <span className="ml-1 text-[10px] text-slate-600">
        Strona {page} z {totalPages}
      </span>
    </nav>
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
