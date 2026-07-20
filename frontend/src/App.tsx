import { Bookmark, BrainCircuit, ChevronRight, Sparkles, WandSparkles } from 'lucide-react';
import { useState } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { EmptyState } from './components/EmptyState';
import { HistoryView } from './components/HistoryView';
import { MovieDetailModal } from './components/MovieDetailModal';
import { Navbar } from './components/Navbar';
import { RecommendationCard } from './components/RecommendationCard';
import { UserProfileSidebar } from './components/UserProfileSidebar';
import { useSession } from './context/SessionContext';
import { demoMovies, initialAgentSteps } from './data/mockData';
import { requestRecommendations, updateMovieState } from './services/api';
import type { AgentStep, AppView, Movie } from './types';

function wait(duration: number) {
  return new Promise((resolve) => window.setTimeout(resolve, duration));
}

export default function App() {
  const {
    user,
    messages,
    history,
    savedMovieIds,
    watchedMovieIds,
    addMessage,
    toggleSaved,
    toggleWatched,
    addDetectedPreferences,
    recordInteraction,
  } = useSession();
  const [activeView, setActiveView] = useState<AppView>('recommendations');
  const [recommendations, setRecommendations] = useState<Movie[]>(demoMovies);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>(initialAgentSteps);

  const handlePrompt = async (query: string) => {
    if (isProcessing) return;

    setActiveView('recommendations');
    setIsProcessing(true);
    addMessage('user', query);
    setAgentSteps(initialAgentSteps.map((step) => ({ ...step, status: 'idle' })));

    const responsePromise = requestRecommendations(query).then(
      (response) => ({ response, error: null }),
      (error: unknown) => ({ response: null, error }),
    );

    try {
      for (let index = 0; index < initialAgentSteps.length; index += 1) {
        setAgentSteps((steps) =>
          steps.map((step, stepIndex) => ({
            ...step,
            status: stepIndex < index ? 'completed' : stepIndex === index ? 'working' : 'idle',
          })),
        );
        await wait(index === 0 ? 650 : 520);
      }

      const result = await responsePromise;
      if (result.error || !result.response) throw result.error;

      setAgentSteps((steps) => steps.map((step) => ({ ...step, status: 'completed' })));
      setRecommendations(result.response.recommendations);
      addDetectedPreferences(result.response.detectedPreferences);
      recordInteraction(query, result.response.recommendations.length);
      addMessage('assistant', result.response.message);
      await wait(350);
    } catch {
      addMessage(
        'assistant',
        'Nie udało mi się teraz pobrać rekomendacji. Sprawdź połączenie z backendem i spróbuj ponownie za chwilę.',
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleToggleSaved = (movieId: number) => {
    const enabled = !savedMovieIds.includes(movieId);
    toggleSaved(movieId);
    void updateMovieState(movieId, 'saved', enabled).catch(() => undefined);
  };

  const handleToggleWatched = (movieId: number) => {
    const enabled = !watchedMovieIds.includes(movieId);
    toggleWatched(movieId);
    void updateMovieState(movieId, 'watched', enabled).catch(() => undefined);
  };

  const savedMovies = recommendations.filter((movie) => savedMovieIds.includes(movie.id));
  const visibleMovies = activeView === 'saved' ? savedMovies : recommendations;

  return (
    <div className="min-h-screen overflow-x-hidden bg-ink-950 text-slate-100 selection:bg-violet-500/30">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-64 h-[540px] w-[540px] rounded-full bg-violet-600/[0.07] blur-[120px]" />
        <div className="absolute -right-60 top-1/3 h-[520px] w-[520px] rounded-full bg-blue-600/[0.06] blur-[130px]" />
      </div>

      <Navbar
        user={user}
        activeView={activeView}
        onViewChange={setActiveView}
        onOpenProfile={() => setIsProfileOpen(true)}
      />

      <div className="relative mx-auto flex max-w-[1600px] gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <UserProfileSidebar
          user={user}
          history={history}
          savedCount={savedMovieIds.length}
          watchedCount={watchedMovieIds.length}
          isOpen={isProfileOpen}
          onClose={() => setIsProfileOpen(false)}
        />

        <main className="min-w-0 flex-1">
          {activeView === 'history' ? (
            <div className="mx-auto max-w-4xl">
              <div className="mb-8">
                <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-blue-400">
                  <BrainCircuit className="h-4 w-4" />
                  Pamięć Twoich rozmów
                </p>
                <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Historia odkrywania</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
                  Każda rozmowa wzbogaca profil gustu i pomaga agentom trafniej rozumieć kolejne
                  prośby.
                </p>
              </div>
              <HistoryView history={history} onRepeat={(query) => void handlePrompt(query)} />
            </div>
          ) : activeView === 'saved' ? (
            <div>
              <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
                <div>
                  <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-violet-400">
                    <Bookmark className="h-4 w-4" />
                    Twoja kolekcja
                  </p>
                  <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Zapisane na później</h1>
                  <p className="mt-3 text-sm text-slate-500">Tytuły, które zwróciły Twoją uwagę.</p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveView('recommendations')}
                  className="flex items-center gap-1.5 text-xs font-semibold text-violet-300 hover:text-violet-200"
                >
                  Wróć do odkrywania
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
              {savedMovies.length ? (
                <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
                  {visibleMovies.map((movie, index) => (
                    <RecommendationCard
                      key={movie.id}
                      movie={movie}
                      index={index}
                      isSaved={savedMovieIds.includes(movie.id)}
                      isWatched={watchedMovieIds.includes(movie.id)}
                      onOpen={setSelectedMovie}
                      onToggleSaved={handleToggleSaved}
                      onToggleWatched={handleToggleWatched}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState onDiscover={() => setActiveView('recommendations')} />
              )}
            </div>
          ) : (
            <>
              <div className="mb-8 overflow-hidden rounded-3xl border border-white/[0.06] bg-gradient-to-r from-violet-500/[0.07] via-transparent to-blue-500/[0.06] px-5 py-6 sm:px-7 sm:py-8">
                <div className="flex flex-col justify-between gap-6 2xl:flex-row 2xl:items-end">
                  <div>
                    <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-violet-400">
                      <WandSparkles className="h-4 w-4" />
                      Rekomendacje, które rozumieją kontekst
                    </p>
                    <h1 className="max-w-3xl text-3xl font-bold leading-tight tracking-[-0.03em] text-white sm:text-5xl">
                      Mniej scrollowania.{' '}
                      <span className="bg-gradient-to-r from-violet-300 to-blue-300 bg-clip-text text-transparent">
                        Więcej dobrych seansów.
                      </span>
                    </h1>
                    <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-500 sm:text-base">
                      Opisz, czego dziś potrzebujesz. Czterech agentów przeanalizuje Twój nastrój,
                      przeszuka katalog i wyjaśni każdy wybór.
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3 rounded-2xl border border-white/[0.06] bg-black/10 px-4 py-3">
                    <div className="flex -space-x-2">
                      {['P', 'D', 'R', 'W'].map((letter, index) => (
                        <span
                          key={letter}
                          className={`flex h-8 w-8 items-center justify-center rounded-full border-2 border-ink-900 text-[10px] font-bold text-white ${
                            index % 2 === 0 ? 'bg-violet-600' : 'bg-blue-600'
                          }`}
                        >
                          {letter}
                        </span>
                      ))}
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-200">Zespół agentów gotowy</p>
                      <p className="mt-0.5 text-[10px] text-slate-600">Profil · Dane · Ranking · Wyjaśnienia</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid items-start gap-6 lg:grid-cols-[minmax(340px,0.76fr)_minmax(0,1.24fr)] 2xl:grid-cols-[minmax(390px,0.72fr)_minmax(0,1.28fr)]">
                <ChatInterface
                  messages={messages}
                  agentSteps={agentSteps}
                  isProcessing={isProcessing}
                  onSubmit={handlePrompt}
                />

                <section aria-labelledby="recommendations-title">
                  <div className="mb-4 flex items-end justify-between px-1">
                    <div>
                      <div className="mb-1.5 flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-violet-400" />
                        <h2 id="recommendations-title" className="text-lg font-bold text-white sm:text-xl">
                          Wybrane dla Ciebie
                        </h2>
                      </div>
                      <p className="text-xs text-slate-600">
                        Ranking uwzględnia nastrój, preferencje i historię rozmów.
                      </p>
                    </div>
                    <span className="hidden rounded-full border border-white/[0.06] bg-white/[0.025] px-3 py-1.5 text-[10px] text-slate-500 sm:block">
                      {recommendations.length} trafne propozycje
                    </span>
                  </div>

                  <div
                    className={`grid gap-5 transition duration-500 2xl:grid-cols-2 ${
                      isProcessing ? 'opacity-55' : 'opacity-100'
                    }`}
                    aria-live="polite"
                  >
                    {recommendations.map((movie, index) => (
                      <RecommendationCard
                        key={movie.id}
                        movie={movie}
                        index={index}
                        isSaved={savedMovieIds.includes(movie.id)}
                        isWatched={watchedMovieIds.includes(movie.id)}
                        onOpen={setSelectedMovie}
                        onToggleSaved={handleToggleSaved}
                        onToggleWatched={handleToggleWatched}
                      />
                    ))}
                  </div>
                </section>
              </div>
            </>
          )}
        </main>
      </div>

      <MovieDetailModal
        movie={selectedMovie}
        isSaved={selectedMovie ? savedMovieIds.includes(selectedMovie.id) : false}
        isWatched={selectedMovie ? watchedMovieIds.includes(selectedMovie.id) : false}
        onClose={() => setSelectedMovie(null)}
        onToggleSaved={handleToggleSaved}
        onToggleWatched={handleToggleWatched}
      />
    </div>
  );
}
