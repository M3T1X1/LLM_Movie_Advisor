import {
  Activity,
  BarChart3,
  Clock3,
  Eye,
  Film,
  LayoutDashboard,
  Radar,
  Star,
  Tv,
} from 'lucide-react';
import { useMemo, useState, type ReactNode } from 'react';
import type { Content, Interaction, UserPreference } from '../types';

type AnalyticsMode = 'overview' | 'taste-map';

interface AnalyticsViewProps {
  content: Content[];
  interactions: Interaction[];
  preferences: UserPreference[];
}

interface GenreMetric {
  name: string;
  count: number;
  titles: string[];
}

interface MonthlyMetric {
  key: string;
  label: string;
  count: number;
}

const barColors = [
  'fill-violet-500/80',
  'fill-indigo-500/80',
  'fill-blue-500/80',
  'fill-sky-500/80',
  'fill-cyan-500/80',
  'fill-teal-500/80',
];

const pointColors = [
  'fill-violet-300',
  'fill-indigo-300',
  'fill-blue-300',
  'fill-sky-300',
  'fill-cyan-300',
  'fill-teal-300',
];

export function AnalyticsView({ content, interactions, preferences }: AnalyticsViewProps) {
  const [mode, setMode] = useState<AnalyticsMode>('overview');
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);

  const analytics = useMemo(() => {
    const contentById = new Map(content.map((item) => [item.id, item]));
    const watchedInteractions = interactions.filter((interaction) => interaction.interactionType === 'watched');
    const watchedContent = watchedInteractions
      .map((interaction) => contentById.get(interaction.contentId))
      .filter((item): item is Content => Boolean(item));

    const genreMap = new Map<string, GenreMetric>();
    watchedContent.forEach((item) => {
      item.genres.forEach((genre) => {
        const current = genreMap.get(genre.name) ?? { name: genre.name, count: 0, titles: [] };
        current.count += 1;
        if (!current.titles.includes(item.title)) current.titles.push(item.title);
        genreMap.set(genre.name, current);
      });
    });

    const genres = Array.from(genreMap.values()).sort(
      (first, second) => second.count - first.count || first.name.localeCompare(second.name, 'pl'),
    );
    const movies = watchedContent.filter((item) => item.mediaType === 'movie').length;
    const series = watchedContent.filter((item) => item.mediaType === 'tv').length;
    const ratings = watchedContent
      .map((item) => item.voteAverage)
      .filter((rating): rating is number => rating !== null);
    const averageRating = ratings.length
      ? ratings.reduce((sum, rating) => sum + rating, 0) / ratings.length
      : 0;
    const runtimeMinutes = watchedContent.reduce(
      (sum, item) => sum + (item.metadata.runtimeMinutes ?? 0),
      0,
    );

    const today = new Date();
    const months: MonthlyMetric[] = Array.from({ length: 6 }, (_, index) => {
      const date = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() - 5 + index, 1));
      return {
        key: `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`,
        label: new Intl.DateTimeFormat('pl-PL', { month: 'short' }).format(date).replace('.', ''),
        count: 0,
      };
    });
    watchedInteractions.forEach((interaction) => {
      const date = new Date(interaction.createdAt);
      const key = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
      const month = months.find((item) => item.key === key);
      if (month) month.count += 1;
    });

    return {
      watchedCount: watchedContent.length,
      watchlistedCount: new Set(
        interactions
          .filter((interaction) => interaction.interactionType === 'watchlisted')
          .map((interaction) => interaction.contentId),
      ).size,
      genres,
      movies,
      series,
      averageRating,
      runtimeMinutes,
      months,
      positivePreferenceCount: preferences.filter((preference) => preference.polarity === 1).length,
    };
  }, [content, interactions, preferences]);

  const activeGenre =
    analytics.genres.find((genre) => genre.name === selectedGenre) ?? analytics.genres[0] ?? null;

  return (
    <div>
      <header className="mb-7 flex flex-col justify-between gap-5 border-b border-white/[0.07] pb-7 lg:flex-row lg:items-end">
        <div>
          <p className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-600">
            <BarChart3 className="h-4 w-4" />
            Twoja aktywność
          </p>
          <h1 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">Analiza oglądania</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
            Podsumowanie powstaje z zapisanych interakcji i metadanych obejrzanych treści.
          </p>
        </div>

        <div className="grid grid-cols-2 rounded-md border border-white/[0.08] bg-[#0d0f15] p-1">
          <ModeButton
            active={mode === 'overview'}
            onClick={() => setMode('overview')}
            icon={<LayoutDashboard className="h-3.5 w-3.5" />}
            label="Przegląd"
          />
          <ModeButton
            active={mode === 'taste-map'}
            onClick={() => setMode('taste-map')}
            icon={<Radar className="h-3.5 w-3.5" />}
            label="Mapa gustu"
          />
        </div>
      </header>

      {analytics.watchedCount === 0 ? (
        <div className="flex min-h-96 flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] text-center">
          <Activity className="mb-4 h-6 w-6 text-slate-700" />
          <h2 className="text-sm font-semibold text-slate-300">Brak danych do analizy</h2>
          <p className="mt-2 max-w-sm text-xs leading-5 text-slate-600">
            Oznacz kilka tytułów jako obejrzane, aby zobaczyć swój profil oglądania.
          </p>
        </div>
      ) : mode === 'overview' ? (
        <OverviewDashboard analytics={analytics} />
      ) : (
        <TasteMap
          genres={analytics.genres.slice(0, 6)}
          activeGenre={activeGenre}
          watchedCount={analytics.watchedCount}
          positivePreferenceCount={analytics.positivePreferenceCount}
          onSelectGenre={setSelectedGenre}
        />
      )}
    </div>
  );
}

function OverviewDashboard({
  analytics,
}: {
  analytics: {
    watchedCount: number;
    watchlistedCount: number;
    genres: GenreMetric[];
    movies: number;
    series: number;
    averageRating: number;
    runtimeMinutes: number;
    months: MonthlyMetric[];
  };
}) {
  const hours = Math.round(analytics.runtimeMinutes / 60);

  return (
    <>
      <div className="mb-5 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.06] lg:grid-cols-4">
        <StatCard
          icon={<Eye className="h-4 w-4" />}
          iconColor="text-violet-400"
          value={analytics.watchedCount}
          label="Obejrzane tytuły"
        />
        <StatCard
          icon={<Clock3 className="h-4 w-4" />}
          iconColor="text-blue-400"
          value={`${hours} h`}
          label="Łączny czas"
        />
        <StatCard
          icon={<Star className="h-4 w-4" />}
          iconColor="text-amber-300"
          value={analytics.averageRating.toFixed(1)}
          label="Średnia ocena TMDB"
        />
        <StatCard
          icon={<Activity className="h-4 w-4" />}
          iconColor="text-teal-400"
          value={analytics.watchlistedCount}
          label="Na liście"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <ChartPanel title="Najczęściej oglądane gatunki" description="Liczba obejrzanych tytułów">
          <GenreBarChart genres={analytics.genres.slice(0, 6)} />
        </ChartPanel>

        <ChartPanel title="Filmy a seriale" description="Udział w obejrzanych tytułach">
          <MediaDonut movies={analytics.movies} series={analytics.series} />
        </ChartPanel>

        <div className="xl:col-span-2">
          <ChartPanel title="Aktywność w ostatnich miesiącach" description="Obejrzane tytuły w czasie">
            <ActivityLineChart months={analytics.months} />
          </ChartPanel>
        </div>
      </div>
    </>
  );
}

function GenreBarChart({ genres }: { genres: GenreMetric[] }) {
  const max = Math.max(1, ...genres.map((genre) => genre.count));
  const rowHeight = 42;
  const chartHeight = Math.max(130, genres.length * rowHeight + 16);

  return (
    <svg viewBox={`0 0 600 ${chartHeight}`} className="h-auto w-full" role="img" aria-label="Najczęściej oglądane gatunki">
      {genres.map((genre, index) => {
        const y = index * rowHeight + 8;
        const width = (genre.count / max) * 390;
        return (
          <g key={genre.name}>
            <text x="0" y={y + 17} className="fill-slate-500 text-[11px]">{genre.name}</text>
            <rect x="150" y={y} width="400" height="24" rx="4" className="fill-white/[0.035]" />
            <rect
              x="150"
              y={y}
              width={width}
              height="24"
              rx="4"
              className={barColors[index % barColors.length]}
            />
            <text x={Math.min(560, 160 + width)} y={y + 17} className="fill-slate-300 text-[10px] font-semibold">
              {genre.count}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function MediaDonut({ movies, series }: { movies: number; series: number }) {
  const total = Math.max(1, movies + series);
  const moviePercent = (movies / total) * 100;
  const seriesPercent = 100 - moviePercent;

  return (
    <div className="flex flex-col items-center justify-center gap-6 py-2 sm:flex-row xl:flex-col">
      <div className="relative h-44 w-44">
        <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90" role="img" aria-label="Podział na filmy i seriale">
          <circle cx="100" cy="100" r="70" pathLength="100" className="fill-none stroke-white/[0.05] stroke-[22]" />
          <circle
            cx="100"
            cy="100"
            r="70"
            pathLength="100"
            strokeDasharray={`${moviePercent} ${100 - moviePercent}`}
            className="fill-none stroke-violet-500 stroke-[22]"
          />
          <circle
            cx="100"
            cy="100"
            r="70"
            pathLength="100"
            strokeDasharray={`${seriesPercent} ${100 - seriesPercent}`}
            strokeDashoffset={-moviePercent}
            className="fill-none stroke-cyan-400 stroke-[22]"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-semibold text-white">{movies + series}</span>
          <span className="text-[9px] text-slate-600">łącznie</span>
        </div>
      </div>
      <div className="flex gap-5 text-xs">
        <MediaLegend color="bg-violet-500" icon={<Film className="h-3.5 w-3.5" />} label="Filmy" value={movies} />
        <MediaLegend color="bg-cyan-400" icon={<Tv className="h-3.5 w-3.5" />} label="Seriale" value={series} />
      </div>
    </div>
  );
}

function ActivityLineChart({ months }: { months: MonthlyMetric[] }) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const max = Math.max(1, ...months.map((month) => month.count));
  const points = months.map((month, index) => ({
    ...month,
    x: 45 + (index * 510) / Math.max(1, months.length - 1),
    y: 175 - (month.count / max) * 125,
  }));
  const line = points.map((point) => `${point.x},${point.y}`).join(' ');
  const area = `45,176 ${line} 555,176`;

  return (
    <svg viewBox="0 0 600 220" className="h-auto w-full" role="img" aria-label="Aktywność w ostatnich miesiącach">
      {[50, 92, 134, 176].map((y) => (
        <line key={y} x1="45" y1={y} x2="555" y2={y} className="stroke-white/[0.05]" />
      ))}
      <polygon points={area} className="fill-sky-500/[0.08]" />
      <polyline points={line} className="fill-none stroke-sky-400 stroke-[2]" />
      {points.map((point, index) => (
        <g
          key={point.key}
          role="button"
          tabIndex={0}
          onMouseEnter={() => setActiveIndex(index)}
          onMouseLeave={() => setActiveIndex(null)}
          onFocus={() => setActiveIndex(index)}
          onBlur={() => setActiveIndex(null)}
          className="cursor-pointer outline-none"
        >
          <circle cx={point.x} cy={point.y} r="14" className="fill-transparent" />
          <circle
            cx={point.x}
            cy={point.y}
            r={activeIndex === index ? 6 : 4}
            className="fill-cyan-300 stroke-[#0d0f15] stroke-[3] transition-all"
          />
          <text x={point.x} y="205" textAnchor="middle" className="fill-slate-600 text-[10px]">
            {point.label}
          </text>
          {activeIndex === index && (
            <g>
              <rect x={point.x - 34} y={point.y - 39} width="68" height="25" rx="4" className="fill-slate-800" />
              <text x={point.x} y={point.y - 22} textAnchor="middle" className="fill-white text-[10px] font-semibold">
                {point.count} tytuły
              </text>
            </g>
          )}
        </g>
      ))}
    </svg>
  );
}

function TasteMap({
  genres,
  activeGenre,
  watchedCount,
  positivePreferenceCount,
  onSelectGenre,
}: {
  genres: GenreMetric[];
  activeGenre: GenreMetric | null;
  watchedCount: number;
  positivePreferenceCount: number;
  onSelectGenre: (genre: string) => void;
}) {
  const centerX = 280;
  const centerY = 240;
  const radius = 170;
  const max = Math.max(1, ...genres.map((genre) => genre.count));
  const axisCount = Math.max(3, genres.length);
  const axes = genres.map((genre, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / axisCount;
    const outer = polarPoint(centerX, centerY, radius, angle);
    const label = polarPoint(centerX, centerY, radius + 34, angle);
    const value = polarPoint(centerX, centerY, radius * (genre.count / max), angle);
    return { genre, angle, outer, label, value };
  });
  const valuePoints = axes.map((axis) => `${axis.value.x},${axis.value.y}`).join(' ');

  return (
    <div className="grid overflow-hidden rounded-xl border border-white/[0.08] bg-[#0d0f15] lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0 border-b border-white/[0.07] p-4 sm:p-6 lg:border-b-0 lg:border-r">
        <div className="mb-2">
          <h2 className="text-sm font-semibold text-white">Mapa najczęściej oglądanych gatunków</h2>
          <p className="mt-1 text-[11px] text-slate-600">Kliknij punkt lub nazwę gatunku, aby zobaczyć szczegóły.</p>
        </div>

        <svg viewBox="0 0 560 500" className="mx-auto h-auto w-full max-w-2xl" role="img" aria-label="Interaktywna mapa gustu">
          {[0.25, 0.5, 0.75, 1].map((level) => {
            const points = Array.from({ length: axisCount }, (_, index) => {
              const angle = -Math.PI / 2 + (index * Math.PI * 2) / axisCount;
              const point = polarPoint(centerX, centerY, radius * level, angle);
              return `${point.x},${point.y}`;
            }).join(' ');
            return <polygon key={level} points={points} className="fill-none stroke-white/[0.07]" />;
          })}

          {axes.map((axis) => (
            <g key={axis.genre.name}>
              <line x1={centerX} y1={centerY} x2={axis.outer.x} y2={axis.outer.y} className="stroke-white/[0.07]" />
              <g
                role="button"
                tabIndex={0}
                onClick={() => onSelectGenre(axis.genre.name)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') onSelectGenre(axis.genre.name);
                }}
                className="cursor-pointer outline-none"
              >
                <circle cx={axis.label.x} cy={axis.label.y - 4} r="30" className="fill-transparent" />
                <text
                  x={axis.label.x}
                  y={axis.label.y}
                  textAnchor="middle"
                  className={`text-[10px] font-medium ${
                    activeGenre?.name === axis.genre.name ? 'fill-violet-300' : 'fill-slate-500'
                  }`}
                >
                  {shortenLabel(axis.genre.name)}
                </text>
              </g>
            </g>
          ))}

          <polygon points={valuePoints} className="fill-indigo-500/15 stroke-blue-400 stroke-[2]" />
          {axes.map((axis, index) => (
            <g
              key={`point-${axis.genre.name}`}
              role="button"
              tabIndex={0}
              onClick={() => onSelectGenre(axis.genre.name)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') onSelectGenre(axis.genre.name);
              }}
              className="cursor-pointer outline-none"
            >
              <circle cx={axis.value.x} cy={axis.value.y} r="11" className="fill-transparent" />
              <circle
                cx={axis.value.x}
                cy={axis.value.y}
                r={activeGenre?.name === axis.genre.name ? 6 : 4}
                className={`${pointColors[index % pointColors.length]} stroke-[#0d0f15] stroke-[3]`}
              />
            </g>
          ))}
        </svg>
      </div>

      <aside className="p-5 sm:p-6">
        <p className="text-[9px] font-medium uppercase tracking-[0.12em] text-slate-600">Wybrany gatunek</p>
        {activeGenre ? (
          <>
            <h3 className="mt-2 text-xl font-semibold text-white">{activeGenre.name}</h3>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <SmallMetric value={activeGenre.count} label="obejrzane" />
              <SmallMetric value={`${Math.round((activeGenre.count / watchedCount) * 100)}%`} label="udział" />
            </div>
            <div className="mt-6 border-t border-white/[0.06] pt-5">
              <p className="mb-3 text-[10px] text-slate-600">Tytuły z tego gatunku</p>
              <ul className="space-y-2">
                {activeGenre.titles.map((title) => (
                  <li key={title} className="flex items-start gap-2 text-xs leading-5 text-slate-400">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-violet-400" />
                    {title}
                  </li>
                ))}
              </ul>
            </div>
          </>
        ) : (
          <p className="mt-3 text-xs text-slate-600">Brak danych o gatunkach.</p>
        )}
        <div className="mt-7 border-t border-white/[0.06] pt-5">
          <p className="text-[10px] leading-5 text-slate-600">
            Mapa wykorzystuje {watchedCount} obejrzanych tytułów i {positivePreferenceCount} pozytywnych preferencji zapisanych w profilu.
          </p>
        </div>
      </aside>
    </div>
  );
}

function ModeButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex h-8 items-center justify-center gap-2 rounded px-3 text-[10px] font-medium transition ${
        active ? 'bg-white/[0.08] text-white' : 'text-slate-600 hover:text-slate-300'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function StatCard({
  icon,
  iconColor,
  value,
  label,
}: {
  icon: ReactNode;
  iconColor: string;
  value: string | number;
  label: string;
}) {
  return (
    <div className="bg-[#0d0f15] p-4 sm:p-5">
      <div className={`mb-4 ${iconColor}`}>{icon}</div>
      <p className="text-xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-[10px] text-slate-600">{label}</p>
    </div>
  );
}

function ChartPanel({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-white/[0.08] bg-[#0d0f15] p-4 sm:p-5">
      <div className="mb-5 border-b border-white/[0.06] pb-3">
        <h2 className="text-xs font-semibold text-slate-300">{title}</h2>
        <p className="mt-1 text-[10px] text-slate-600">{description}</p>
      </div>
      {children}
    </section>
  );
}

function MediaLegend({ color, icon, label, value }: { color: string; icon: ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 text-slate-500">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {icon}
      <span>{label}</span>
      <strong className="text-slate-300">{value}</strong>
    </div>
  );
}

function SmallMetric({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="rounded-md border border-white/[0.06] bg-white/[0.025] p-3">
      <p className="text-lg font-semibold text-white">{value}</p>
      <p className="mt-1 text-[9px] text-slate-600">{label}</p>
    </div>
  );
}

function polarPoint(centerX: number, centerY: number, radius: number, angle: number) {
  return {
    x: centerX + Math.cos(angle) * radius,
    y: centerY + Math.sin(angle) * radius,
  };
}

function shortenLabel(label: string) {
  return label.length > 16 ? `${label.slice(0, 14)}…` : label;
}
