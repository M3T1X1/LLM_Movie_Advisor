import {
  Bookmark,
  CalendarDays,
  Clock3,
  Film,
  RefreshCw,
  Search,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getUpcomingReleases } from '../services/api';
import type { Content, DatabaseId } from '../types';
import { getPosterUrl } from '../utils/content';

type DateRange = 'all' | '30' | '90' | '365';

interface UpcomingReleasesViewProps {
  watchlistedContentIds: DatabaseId[];
  onOpen: (content: Content) => void;
  onWatchlist: (content: Content) => void;
  onLoaded: (content: Content[]) => void;
}

const DAY_IN_MS = 86_400_000;
const dateFormatter = new Intl.DateTimeFormat('pl-PL', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});
const monthFormatter = new Intl.DateTimeFormat('pl-PL', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});

function parseReleaseDate(value: string) {
  return new Date(`${value}T00:00:00Z`);
}

function getTodayTimestamp() {
  const today = new Date();
  return Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
}

function getDaysUntilRelease(releaseDate: string) {
  return Math.ceil((parseReleaseDate(releaseDate).getTime() - getTodayTimestamp()) / DAY_IN_MS);
}

function getCountdownLabel(days: number) {
  if (days === 0) return 'Premiera dzisiaj';
  if (days === 1) return 'Premiera jutro';
  return `Za ${days} dni`;
}

function getReleaseCountLabel(count: number) {
  if (count === 1) return '1 premiera';
  const lastTwoDigits = count % 100;
  const lastDigit = count % 10;
  if (lastTwoDigits < 12 || lastTwoDigits > 14) {
    if (lastDigit >= 2 && lastDigit <= 4) return `${count} premiery`;
  }
  return `${count} premier`;
}

export function UpcomingReleasesView({
  watchlistedContentIds,
  onOpen,
  onWatchlist,
  onLoaded,
}: UpcomingReleasesViewProps) {
  const [content, setContent] = useState<Content[]>([]);
  const [query, setQuery] = useState('');
  const [genre, setGenre] = useState('all');
  const [month, setMonth] = useState('all');
  const [dateRange, setDateRange] = useState<DateRange>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isCurrent = true;
    setIsLoading(true);
    setHasError(false);

    void getUpcomingReleases().then(
      (response) => {
        if (!isCurrent) return;
        setContent(response);
        onLoaded(response);
        setIsLoading(false);
      },
      () => {
        if (!isCurrent) return;
        setHasError(true);
        setIsLoading(false);
      },
    );

    return () => {
      isCurrent = false;
    };
  }, [onLoaded, reloadKey]);

  const genres = useMemo(
    () =>
      Array.from(new Set(content.flatMap((item) => item.genres.map((itemGenre) => itemGenre.name)))).sort(
        (first, second) => first.localeCompare(second, 'pl'),
      ),
    [content],
  );

  const months = useMemo(() => {
    const uniqueMonths = new Map<string, string>();
    content.forEach((item) => {
      if (!item.releaseDate) return;
      const value = item.releaseDate.slice(0, 7);
      uniqueMonths.set(value, monthFormatter.format(parseReleaseDate(item.releaseDate)));
    });
    return [...uniqueMonths.entries()].sort(([first], [second]) => first.localeCompare(second));
  }, [content]);

  const filteredContent = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('pl-PL');
    const maximumDays = dateRange === 'all' ? Number.POSITIVE_INFINITY : Number(dateRange);

    return content
      .filter((item) => {
        if (!item.releaseDate) return false;
        const daysUntilRelease = getDaysUntilRelease(item.releaseDate);
        const matchesQuery =
          !normalizedQuery ||
          item.title.toLocaleLowerCase('pl-PL').includes(normalizedQuery) ||
          item.originalTitle?.toLocaleLowerCase('pl-PL').includes(normalizedQuery);
        const matchesGenre =
          genre === 'all' || item.genres.some((itemGenre) => itemGenre.name === genre);
        const matchesMonth = month === 'all' || item.releaseDate.startsWith(month);
        const matchesRange = daysUntilRelease >= 0 && daysUntilRelease <= maximumDays;
        return matchesQuery && matchesGenre && matchesMonth && matchesRange;
      })
      .sort(
        (first, second) =>
          parseReleaseDate(first.releaseDate!).getTime() -
          parseReleaseDate(second.releaseDate!).getTime(),
      );
  }, [content, dateRange, genre, month, query]);

  const hasActiveFilters =
    Boolean(query) || genre !== 'all' || month !== 'all' || dateRange !== 'all';

  const clearFilters = () => {
    setQuery('');
    setGenre('all');
    setMonth('all');
    setDateRange('all');
  };

  return (
    <div>
      <header className="mb-7 border-b border-white/[0.07] pb-7">
        <p className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-violet-300/70">
          <CalendarDays className="h-4 w-4" />
          Kalendarz TMDB
        </p>
        <h1 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
          Przyszłe premiery
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
          Sprawdź, jakie filmy wkrótce pojawią się w kinach, i zapisz najbardziej wyczekiwane
          tytuły na swoją listę.
        </p>
      </header>

      <section aria-label="Filtry przyszłych premier" className="mb-6 rounded-xl border border-white/[0.08] bg-[#0d0f15] p-4 sm:p-5">
        <div className="mb-4 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.12em] text-slate-600">
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filtry
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(260px,1.35fr)_1fr_1fr_1fr_auto]">
          <label className="relative block">
            <span className="sr-only">Szukaj premiery</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-700" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Szukaj po tytule..."
              className="h-10 w-full rounded-lg border border-white/[0.08] bg-black/20 pl-9 pr-3 text-xs text-white outline-none transition placeholder:text-slate-700 focus:border-violet-400/40"
            />
          </label>

          <FilterSelect label="Gatunek" value={genre} onChange={setGenre}>
            <option value="all">Wszystkie gatunki</option>
            {genres.map((itemGenre) => <option key={itemGenre} value={itemGenre}>{itemGenre}</option>)}
          </FilterSelect>

          <FilterSelect label="Miesiąc premiery" value={month} onChange={setMonth}>
            <option value="all">Każdy miesiąc</option>
            {months.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </FilterSelect>

          <FilterSelect label="Zakres czasu" value={dateRange} onChange={(value) => setDateRange(value as DateRange)}>
            <option value="all">Wszystkie terminy</option>
            <option value="30">Najbliższe 30 dni</option>
            <option value="90">Najbliższe 90 dni</option>
            <option value="365">Najbliższy rok</option>
          </FilterSelect>

          <button
            type="button"
            onClick={clearFilters}
            disabled={!hasActiveFilters}
            className="flex h-10 items-center justify-center gap-2 rounded-lg border border-white/[0.08] px-3 text-[10px] text-slate-500 transition hover:border-white/15 hover:text-white disabled:cursor-not-allowed disabled:opacity-35 md:col-span-2 xl:col-span-1"
          >
            <X className="h-3.5 w-3.5" />
            Wyczyść
          </button>
        </div>
      </section>

      {isLoading ? (
        <UpcomingLoadingState />
      ) : hasError ? (
        <UpcomingErrorState onRetry={() => setReloadKey((current) => current + 1)} />
      ) : (
        <section aria-labelledby="upcoming-list-title">
          <div className="mb-4 flex items-end justify-between border-b border-white/[0.07] pb-3">
            <div>
              <p className="text-[9px] font-medium uppercase tracking-[0.12em] text-slate-600">Polska dystrybucja</p>
              <h2 id="upcoming-list-title" className="mt-1.5 text-lg font-semibold text-white">Nadchodzące filmy</h2>
            </div>
            <p className="text-[10px] text-slate-600">{getReleaseCountLabel(filteredContent.length)}</p>
          </div>

          {filteredContent.length ? (
            <div className="space-y-3">
              {filteredContent.map((item) => (
                <UpcomingReleaseCard
                  key={item.id}
                  content={item}
                  isWatchlisted={watchlistedContentIds.includes(item.id)}
                  onOpen={onOpen}
                  onWatchlist={onWatchlist}
                />
              ))}
            </div>
          ) : (
            <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] bg-[#0d0f15]/60 px-6 text-center">
              <CalendarDays className="mb-3 h-6 w-6 text-slate-700" />
              <h2 className="text-sm font-semibold text-white">Brak premier dla tych filtrów</h2>
              <p className="mt-2 text-xs text-slate-600">Zmień zakres czasu, miesiąc albo wybrany gatunek.</p>
              {hasActiveFilters && <button type="button" onClick={clearFilters} className="mt-4 text-xs font-medium text-violet-300 transition hover:text-violet-200">Wyczyść filtry</button>}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function FilterSelect({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="sr-only">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} aria-label={label} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#10131a] px-3 text-xs text-slate-400 outline-none transition focus:border-violet-400/40">
        {children}
      </select>
    </label>
  );
}

function UpcomingReleaseCard({ content, isWatchlisted, onOpen, onWatchlist }: { content: Content; isWatchlisted: boolean; onOpen: (content: Content) => void; onWatchlist: (content: Content) => void }) {
  const [imageFailed, setImageFailed] = useState(false);
  const posterUrl = getPosterUrl(content);
  const releaseDate = content.releaseDate!;
  const daysUntilRelease = getDaysUntilRelease(releaseDate);

  return (
    <article className="grid overflow-hidden rounded-xl border border-white/[0.08] bg-[#0d0f15] transition hover:border-violet-300/20 sm:grid-cols-[128px_minmax(0,1fr)_180px]">
      <div className="aspect-[16/8] overflow-hidden bg-gradient-to-br from-violet-950/50 via-slate-900 to-blue-950/40 sm:aspect-[2/3]">
        {posterUrl && !imageFailed ? <img src={posterUrl} alt={`Plakat: ${content.title}`} onError={() => setImageFailed(true)} className="h-full w-full object-cover" /> : <span className="flex h-full w-full items-center justify-center"><Film className="h-8 w-8 text-slate-700" /></span>}
      </div>

      <div className="min-w-0 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2 text-[9px] font-medium uppercase tracking-[0.1em] text-violet-300/70">
          {content.genres.slice(0, 3).map((itemGenre) => <span key={itemGenre.tmdbGenreId}>{itemGenre.name}</span>)}
        </div>
        <h2 className="mt-2 text-lg font-semibold text-white">{content.title}</h2>
        {content.originalTitle && content.originalTitle !== content.title && <p className="mt-1 text-[10px] text-slate-600">{content.originalTitle}</p>}
        <p className="mt-3 line-clamp-3 max-w-3xl text-xs leading-5 text-slate-500">{content.overview || 'Opis nie jest jeszcze dostępny w języku polskim.'}</p>
        <button type="button" onClick={() => onOpen(content)} className="mt-3 text-[10px] font-medium text-violet-300 transition hover:text-violet-200" aria-label={`Pokaż szczegóły: ${content.title}`}>Zobacz szczegóły</button>
      </div>

      <div className="flex items-center justify-between gap-4 border-t border-white/[0.06] p-4 sm:flex-col sm:items-stretch sm:justify-center sm:border-l sm:border-t-0 sm:p-5">
        <div>
          <p className="flex items-center gap-2 text-[10px] text-slate-600"><CalendarDays className="h-3.5 w-3.5 text-violet-400" />Data premiery</p>
          <time dateTime={releaseDate} className="mt-2 block text-sm font-semibold text-white">{dateFormatter.format(parseReleaseDate(releaseDate))}</time>
          <p className="mt-1 flex items-center gap-1.5 text-[10px] font-medium text-violet-300"><Clock3 className="h-3 w-3" />{getCountdownLabel(daysUntilRelease)}</p>
        </div>
        <button type="button" onClick={() => onWatchlist(content)} className={`flex h-9 shrink-0 items-center justify-center gap-2 rounded-lg px-3 text-[10px] font-medium transition ${isWatchlisted ? 'bg-violet-500/15 text-violet-200 hover:bg-red-500/10 hover:text-red-300' : 'bg-white/[0.05] text-slate-400 hover:bg-white/[0.09] hover:text-white'}`}>
          <Bookmark className={`h-3.5 w-3.5 ${isWatchlisted ? 'fill-current' : ''}`} />
          {isWatchlisted ? 'Zapisano' : 'Zapisz na listę'}
        </button>
      </div>
    </article>
  );
}

function UpcomingLoadingState() {
  return <div aria-label="Ładowanie przyszłych premier" className="space-y-3">{[0, 1, 2].map((item) => <div key={item} className="h-48 animate-pulse rounded-xl border border-white/[0.06] bg-white/[0.025]" />)}</div>;
}

function UpcomingErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" className="flex min-h-72 flex-col items-center justify-center rounded-xl border border-red-400/10 bg-red-500/[0.025] px-6 text-center">
      <CalendarDays className="mb-4 h-6 w-6 text-red-300/60" />
      <h2 className="text-sm font-semibold text-white">Nie udało się pobrać premier</h2>
      <p className="mt-2 max-w-sm text-xs leading-5 text-slate-600">Kalendarz TMDB jest chwilowo niedostępny. Spróbuj ponownie za moment.</p>
      <button type="button" onClick={onRetry} className="mt-4 flex h-9 items-center gap-2 rounded-md bg-white/[0.06] px-3 text-xs text-slate-300 transition hover:bg-white/[0.1] hover:text-white"><RefreshCw className="h-3.5 w-3.5" />Spróbuj ponownie</button>
    </div>
  );
}
