import {Film, Flame, RefreshCw, Sparkles } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getRecommendationTrends } from '../services/api';
import type {
  Content,
  ContentRecommendationTrend,
  RecommendationTrends,
  TrendPeriod,
} from '../types';
import { getPosterUrl, getReleaseYear } from '../utils/content';

interface TrendsViewProps {
  onOpen: (content: Content) => void;
}

const periodOptions: { value: TrendPeriod; label: string; description: string }[] = [
  { value: 'day', label: 'Dzisiaj', description: 'ostatnie 24 godziny' },
  { value: 'week', label: 'Tydzień', description: 'ostatnie 7 dni' },
  { value: 'month', label: 'Miesiąc', description: 'ostatnie 30 dni' },
];

const numberFormatter = new Intl.NumberFormat('pl-PL');

export function TrendsView({ onOpen }: TrendsViewProps) {
  const [period, setPeriod] = useState<TrendPeriod>('day');
  const [report, setReport] = useState<RecommendationTrends | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let isCurrent = true;
    setIsLoading(true);
    setHasError(false);

    void getRecommendationTrends(period).then(
      (response) => {
        if (!isCurrent) return;
        setReport(response);
        setIsLoading(false);
      },
      () => {
        if (!isCurrent) return;
        setReport(null);
        setHasError(true);
        setIsLoading(false);
      },
    );

    return () => {
      isCurrent = false;
    };
  }, [period, reloadKey]);

  const genreTrends = useMemo(
    () =>
      [...(report?.genreTrends ?? [])].sort(
        (first, second) => second.recommendationCount - first.recommendationCount,
      ),
    [report],
  );
  const contentTrends = useMemo(
    () =>
      [...(report?.contentTrends ?? [])]
        .sort((first, second) => second.recommendationCount - first.recommendationCount)
        .slice(0, 3),
    [report],
  );

  return (
    <div>
      <header className="mb-7 border-b border-white/[0.07] pb-7">
        <p className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-violet-300/70">
          <Flame className="h-4 w-4" />
          Popularne w rekomendacjach
        </p>
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <h1 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
              Trendy
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              Zobacz, jakie gatunki LLM poleca najczęściej i które filmy i seriale najczęściej pojawiają
              się w rekomendacjach całej społeczności.
            </p>
          </div>

          <div
            className="grid grid-cols-3 rounded-lg border border-white/[0.08] bg-[#0d0f15] p-1"
            aria-label="Zakres czasu trendów"
          >
            {periodOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setPeriod(option.value)}
                aria-pressed={period === option.value}
                className={`h-9 rounded-md px-3 text-[11px] font-medium transition sm:px-5 ${
                  period === option.value
                    ? 'bg-violet-500/15 text-violet-200 ring-1 ring-violet-400/20'
                    : 'text-slate-600 hover:text-slate-300'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {isLoading ? (
        <TrendsLoadingState />
      ) : hasError || !report ? (
        <TrendsErrorState onRetry={() => setReloadKey((current) => current + 1)} />
      ) : (
        <>
          <div className="grid gap-6 xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.32fr)] xl:items-stretch">
            <section
              aria-labelledby="trending-genres-title"
              className="rounded-xl border border-white/[0.08] bg-[#0d0f15] p-5 sm:p-6">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="text-[9px] font-medium uppercase tracking-[0.12em] text-slate-600">
                    {numberFormatter.format(report.totalRecommendations)}  wyświetleń rekomendacji
                  </p>
                  <h2 id="trending-genres-title" className="mt-1.5 text-lg font-semibold text-white">
                    Najczęściej polecane gatunki
                  </h2>
                </div>
                <Sparkles className={"text-violet-500"}></Sparkles>
              </div>

              <div className="space-y-5">
                {genreTrends.map((genre, index) => {
                  const maximum = genreTrends[0]?.recommendationCount ?? 1;
                  const width = Math.max(8, (genre.recommendationCount / maximum) * 100);

                  return (
                    <div key={genre.genreName}>
                      <div className="mb-2 flex items-center justify-between gap-3 text-xs">
                        <span className="flex min-w-0 items-center gap-2 text-slate-300">
                          <span className="w-5 text-[10px] font-semibold text-slate-700">
                            {String(index + 1).padStart(2, '0')}
                          </span>
                          <span className="truncate">{genre.genreName}</span>
                        </span>
                        <span className="shrink-0 text-[10px] text-slate-600">
                          {numberFormatter.format(genre.recommendationCount)} poleceń
                        </span>
                      </div>
                      <div className="ml-7 h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-violet-500/75 to-blue-500/65"
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <section aria-labelledby="trending-content-title">
              <div className="mb-4 flex items-end justify-between border-b border-white/[0.07] pb-3">
                <div>
                  <p className="text-[9px] font-medium uppercase tracking-[0.12em] text-slate-600">
                    Top 3
                  </p>
                  <h2 id="trending-content-title" className="mt-1.5 text-lg font-semibold text-white">
                    Najczęściej wyświetlane filmy
                  </h2>
                </div>
                <p className="hidden text-[10px] text-slate-600 sm:block">
                  Wyświetlenia w odpowiedziach LLM
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {contentTrends.map((item, index) => (
                  <TrendingContentCard
                    key={item.content.id}
                    item={item}
                    position={index + 1}
                    onOpen={onOpen}
                  />
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}

function TrendingContentCard({
  item,
  position,
  onOpen,
}: {
  item: ContentRecommendationTrend;
  position: number;
  onOpen: (content: Content) => void;
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const posterUrl = getPosterUrl(item.content);
  const releaseYear = getReleaseYear(item.content);

  return (
    <article className="group overflow-hidden rounded-xl border border-white/[0.08] bg-[#0d0f15] transition hover:-translate-y-0.5 hover:border-violet-300/20">
      <button
        type="button"
        onClick={() => onOpen(item.content)}
        aria-label={`Pokaż szczegóły: ${item.content.title}`}
        className="block w-full text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-300/60"
      >
        <div className="relative aspect-[2/3] overflow-hidden bg-slate-900">
          {posterUrl && !imageFailed ? (
            <img
              src={posterUrl}
              alt={`Plakat: ${item.content.title}`}
              onError={() => setImageFailed(true)}
              className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
            />
          ) : (
            <span className="flex h-full w-full items-center justify-center">
              <Film className="h-9 w-9 text-slate-700" />
            </span>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/15" />
          <span
            aria-label={`Pozycja: ${position}`}
            className={`absolute left-3 top-3 flex h-10 min-w-10 items-center justify-center rounded-lg border px-2 text-base font-bold shadow-xl backdrop-blur-md ${
              position === 1
                ? 'border-violet-300/40 bg-violet-500/90 text-white'
                : 'border-white/10 bg-black/65 text-white'
            }`}
          >
            #{position}
          </span>
          <span className="absolute inset-x-3 bottom-3 text-[10px] font-medium text-violet-100">
            {numberFormatter.format(item.recommendationCount)} wyświetleń
          </span>
        </div>

        <div className="p-4">
          <h3 className="truncate text-sm font-semibold text-white transition group-hover:text-violet-100">
            {item.content.title}
          </h3>
          <p className="mt-1.5 truncate text-[10px] text-slate-600">
            {[releaseYear, ...item.content.genres.slice(0, 2).map((genre) => genre.name)]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
      </button>
    </article>
  );
}

function TrendsLoadingState() {
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.32fr)]" aria-label="Ładowanie trendów">
      <div className="h-[420px] animate-pulse rounded-xl border border-white/[0.06] bg-white/[0.025]" />
      <div className="grid gap-4 md:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="aspect-[2/3] animate-pulse rounded-xl border border-white/[0.06] bg-white/[0.025]" />
        ))}
      </div>
    </div>
  );
}

function TrendsErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div role="alert" className="flex min-h-72 flex-col items-center justify-center rounded-xl border border-red-400/10 bg-red-500/[0.025] px-6 text-center">
      <Flame className="mb-4 h-6 w-6 text-red-300/60" />
      <h2 className="text-sm font-semibold text-white">Nie udało się pobrać trendów</h2>
      <p className="mt-2 max-w-sm text-xs leading-5 text-slate-600">
        Statystyki rekomendacji są chwilowo niedostępne. Spróbuj ponownie za moment.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 flex h-9 items-center gap-2 rounded-md bg-white/[0.06] px-3 text-xs text-slate-300 transition hover:bg-white/[0.1] hover:text-white"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        Spróbuj ponownie
      </button>
    </div>
  );
}
