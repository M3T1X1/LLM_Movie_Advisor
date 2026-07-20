import { Bookmark, ChevronRight, SlidersHorizontal } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { EmptyState } from './components/EmptyState';
import { MovieDetailModal } from './components/MovieDetailModal';
import { Navbar } from './components/Navbar';
import { ProfileView } from './components/ProfileView';
import { RecommendationCard } from './components/RecommendationCard';
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
    updateUser,
    addDetectedPreferences,
    recordInteraction,
  } = useSession();
  const [activeView, setActiveView] = useState<AppView>('recommendations');
  const [recommendations, setRecommendations] = useState<Movie[]>(demoMovies);
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
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

  const renderCard = (movie: Movie, index: number) => (
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
  );

  return (
    <div className="min-h-screen bg-ink-950 text-slate-100 selection:bg-violet-500/30">
      <Navbar
        user={user}
        activeView={activeView}
        onViewChange={setActiveView}
      />

      <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8">
        <main className="min-w-0">
          {activeView === 'profile' ? (
            <ProfileView
              user={user}
              history={history}
              savedCount={savedMovieIds.length}
              watchedCount={watchedMovieIds.length}
              onUpdateUser={updateUser}
            />
          ) : activeView === 'saved' ? (
            <div className="mx-auto max-w-4xl">
              <div className="mb-7 flex items-end justify-between gap-4">
                <PageHeading
                  eyebrow="Twoja kolekcja"
                  title="Zapisane na później"
                  description="Tytuły, do których chcesz wrócić."
                  icon={<Bookmark className="h-4 w-4" />}
                />
                <button
                  type="button"
                  onClick={() => setActiveView('recommendations')}
                  className="mb-1 hidden items-center gap-1 text-xs text-slate-500 transition hover:text-white sm:flex"
                >
                  Odkrywaj dalej
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
              {savedMovies.length ? (
                <div className="space-y-4">{savedMovies.map(renderCard)}</div>
              ) : (
                <EmptyState onDiscover={() => setActiveView('recommendations')} />
              )}
            </div>
          ) : (
            <>
              <div className="mb-7 border-b border-white/[0.07] pb-7">
                <p className="mb-2 text-xs text-slate-500">Dobry wieczór, {user.name.split(' ')[0]}.</p>
                <h1 className="max-w-3xl text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
                  Co masz ochotę dziś obejrzeć?
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
                  Opisz nastrój lub rodzaj historii. Nie musisz wybierać gatunku.
                </p>
              </div>

              <div className="grid items-start gap-7 xl:grid-cols-[minmax(560px,1.18fr)_minmax(460px,0.82fr)]">
                <ChatInterface
                  messages={messages}
                  agentSteps={agentSteps}
                  isProcessing={isProcessing}
                  onSubmit={handlePrompt}
                />

                <section aria-labelledby="recommendations-title">
                  <div className="mb-4 flex items-end justify-between border-b border-white/[0.07] pb-3">
                    <div>
                      <h2 id="recommendations-title" className="text-sm font-semibold text-white">
                        Propozycje na dziś
                      </h2>
                      <p className="mt-1 text-[11px] text-slate-600">
                        Posortowane według zgodności z Twoim profilem
                      </p>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-600">
                      <SlidersHorizontal className="h-3.5 w-3.5" />
                      {recommendations.length} wyniki
                    </div>
                  </div>

                  <div
                    className={`space-y-4 transition-opacity duration-300 ${
                      isProcessing ? 'opacity-50' : 'opacity-100'
                    }`}
                    aria-live="polite"
                  >
                    {recommendations.map(renderCard)}
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

interface PageHeadingProps {
  eyebrow: string;
  title: string;
  description: string;
  icon: ReactNode;
}

function PageHeading({ eyebrow, title, description, icon }: PageHeadingProps) {
  return (
    <div className="mb-7">
      <p className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-600">
        {icon}
        {eyebrow}
      </p>
      <h1 className="text-3xl font-semibold tracking-tight text-white">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
    </div>
  );
}
