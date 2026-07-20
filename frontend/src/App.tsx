import { Bookmark, ChevronRight, SlidersHorizontal } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { AnalyticsView } from './components/AnalyticsView';
import { CatalogCard, CatalogView } from './components/CatalogView';
import { ChatInterface } from './components/ChatInterface';
import { EmptyState } from './components/EmptyState';
import { MovieDetailModal } from './components/MovieDetailModal';
import { Navbar } from './components/Navbar';
import { ProfileView } from './components/ProfileView';
import { RecommendationCard } from './components/RecommendationCard';
import { useSession } from './context/SessionContext';
import { demoCandidates, demoCatalogContent, initialAgentSteps } from './data/mockData';
import {
  createInteraction,
  deleteInteraction,
  getCatalogContent,
  requestRecommendations,
} from './services/api';
import type { AgentStep, AppView, Content, RunCandidate } from './types';

function wait(duration: number) {
  return new Promise((resolve) => window.setTimeout(resolve, duration));
}

export default function App() {
  const {
    user,
    semanticProfile,
    preferences,
    interactions,
    messages,
    conversations,
    currentConversationId,
    watchlistedContentIds,
    watchedContentIds,
    addMessage,
    appendMessage,
    updateUser,
    replacePreferenceGroups,
    addDetectedPreferences,
    updateConversationFromQuery,
    recordInteraction: storeInteraction,
    removeInteraction: removeStoredInteraction,
  } = useSession();
  const [activeView, setActiveView] = useState<AppView>('recommendations');
  const [recommendations, setRecommendations] = useState<RunCandidate[]>(demoCandidates);
  const [catalogContent, setCatalogContent] = useState<Content[]>(demoCatalogContent);
  const [selectedCandidate, setSelectedCandidate] = useState<RunCandidate | null>(null);
  const [selectedCatalogContent, setSelectedCatalogContent] = useState<Content | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>(initialAgentSteps);

  const now = new Date();
  const curr_hour =  now.getHours();
  const greeting = curr_hour >= 16 ? "Dobry wieczór" : "Dzień dobry"

  useEffect(() => {
    void getCatalogContent().then(setCatalogContent).catch(() => undefined);
  }, []);

  const handlePrompt = async (query: string) => {
    if (isProcessing) return;

    setActiveView('recommendations');
    setIsProcessing(true);
    const userMessage = addMessage('user', query);
    setAgentSteps(initialAgentSteps.map((step) => ({ ...step, status: 'pending' })));

    const responsePromise = requestRecommendations(currentConversationId, userMessage).then(
      (response) => ({ response, error: null }),
      (error: unknown) => ({ response: null, error }),
    );

    try {
      for (let index = 0; index < initialAgentSteps.length; index += 1) {
        setAgentSteps((steps) =>
          steps.map((step, stepIndex) => ({
            ...step,
            status: stepIndex < index ? 'success' : stepIndex === index ? 'running' : 'pending',
          })),
        );
        await wait(index === 0 ? 650 : 520);
      }

      const result = await responsePromise;
      if (result.error || !result.response) throw result.error;

      setAgentSteps((steps) => steps.map((step) => ({ ...step, status: 'success' })));
      setRecommendations(result.response.candidates);
      addDetectedPreferences(result.response.detectedPreferences);
      updateConversationFromQuery(query);
      appendMessage(result.response.assistantMessage);
      await wait(350);
    } catch {
      setAgentSteps((steps) =>
        steps.map((step) => (step.status === 'running' ? { ...step, status: 'failed' } : step)),
      );
      addMessage(
        'assistant',
        'Nie udało mi się teraz pobrać rekomendacji. Sprawdź połączenie z backendem i spróbuj ponownie za chwilę.',
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleWatchlist = (candidate: RunCandidate) => {
    if (watchlistedContentIds.includes(candidate.contentId)) {
      const interaction = removeStoredInteraction(candidate.contentId, 'watchlisted');
      if (interaction) void deleteInteraction(interaction.id).catch(() => undefined);
      return;
    }
    storeInteraction(candidate.contentId, candidate.id, 'watchlisted');
    void createInteraction(candidate.contentId, candidate.id, 'watchlisted').catch(() => undefined);
  };

  const handleMarkWatched = (candidate: RunCandidate) => {
    if (watchedContentIds.includes(candidate.contentId)) {
      const interaction = removeStoredInteraction(candidate.contentId, 'watched');
      if (interaction) void deleteInteraction(interaction.id).catch(() => undefined);
      return;
    }
    storeInteraction(candidate.contentId, candidate.id, 'watched');
    void createInteraction(candidate.contentId, candidate.id, 'watched').catch(() => undefined);
  };

  const handleOpenCandidate = (candidate: RunCandidate) => {
    setSelectedCatalogContent(null);
    setSelectedCandidate(candidate);
    storeInteraction(candidate.contentId, candidate.id, 'details_opened');
    void createInteraction(candidate.contentId, candidate.id, 'details_opened').catch(() => undefined);
  };

  const handleOpenCatalogContent = (content: Content) => {
    setSelectedCandidate(null);
    setSelectedCatalogContent(content);
    storeInteraction(content.id, null, 'details_opened');
    void createInteraction(content.id, null, 'details_opened').catch(() => undefined);
  };

  const handleCatalogWatchlist = (content: Content) => {
    if (watchlistedContentIds.includes(content.id)) {
      const interaction = removeStoredInteraction(content.id, 'watchlisted');
      if (interaction) void deleteInteraction(interaction.id).catch(() => undefined);
      return;
    }
    storeInteraction(content.id, null, 'watchlisted');
    void createInteraction(content.id, null, 'watchlisted').catch(() => undefined);
  };

  const handleCatalogWatched = (content: Content) => {
    if (watchedContentIds.includes(content.id)) {
      const interaction = removeStoredInteraction(content.id, 'watched');
      if (interaction) void deleteInteraction(interaction.id).catch(() => undefined);
      return;
    }
    storeInteraction(content.id, null, 'watched');
    void createInteraction(content.id, null, 'watched').catch(() => undefined);
  };

  const savedContent = catalogContent.filter((content) =>
    watchlistedContentIds.includes(content.id),
  );
  const selectedContent = selectedCandidate?.content ?? selectedCatalogContent;

  const handleCloseDetails = () => {
    setSelectedCandidate(null);
    setSelectedCatalogContent(null);
  };

  const handleModalWatchlist = () => {
    if (selectedCandidate) handleWatchlist(selectedCandidate);
    else if (selectedCatalogContent) handleCatalogWatchlist(selectedCatalogContent);
  };

  const handleModalWatched = () => {
    if (selectedCandidate) handleMarkWatched(selectedCandidate);
    else if (selectedCatalogContent) handleCatalogWatched(selectedCatalogContent);
  };

  const renderCard = (candidate: RunCandidate, index: number) => (
    <RecommendationCard
      key={candidate.id}
      candidate={candidate}
      index={index}
      isWatchlisted={watchlistedContentIds.includes(candidate.contentId)}
      isWatched={watchedContentIds.includes(candidate.contentId)}
      onOpen={handleOpenCandidate}
      onWatchlist={handleWatchlist}
      onMarkWatched={handleMarkWatched}
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
              semanticProfile={semanticProfile}
              preferences={preferences}
              conversations={conversations}
              savedCount={watchlistedContentIds.length}
              watchedCount={watchedContentIds.length}
              onUpdateUser={updateUser}
              onReplacePreferenceGroups={replacePreferenceGroups}
            />
          ) : activeView === 'analytics' ? (
            <AnalyticsView
              content={catalogContent}
              interactions={interactions}
              preferences={preferences}
            />
          ) : activeView === 'catalog' ? (
            <CatalogView
              content={catalogContent}
              watchlistedContentIds={watchlistedContentIds}
              watchedContentIds={watchedContentIds}
              onOpen={handleOpenCatalogContent}
              onWatchlist={handleCatalogWatchlist}
              onMarkWatched={handleCatalogWatched}
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
              {savedContent.length ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {savedContent.map((content) => (
                    <CatalogCard
                      key={content.id}
                      content={content}
                      isWatchlisted
                      isWatched={watchedContentIds.includes(content.id)}
                      onOpen={handleOpenCatalogContent}
                      onWatchlist={handleCatalogWatchlist}
                      onMarkWatched={handleCatalogWatched}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState onDiscover={() => setActiveView('recommendations')} />
              )}
            </div>
          ) : (
            <>
              <div className="mb-7 border-b border-white/[0.07] pb-7">
                <p className="mb-2 text-xs text-slate-500">{greeting}, {user.username}.</p>
                <h1 className="max-w-3xl text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
                  Co masz ochotę dziś obejrzeć?
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
                  Opisz nastrój lub rodzaj historii. Nie musisz wybierać gatunku.
                </p>
              </div>

              <div className="grid items-start gap-7 xl:grid-cols-[minmax(560px,1.18fr)_minmax(460px,0.82fr)]">
                <ChatInterface
                  messages={messages.filter(
                    (message) => message.conversationId === currentConversationId,
                  )}
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
        content={selectedContent}
        recommendation={selectedCandidate}
        isWatchlisted={selectedContent ? watchlistedContentIds.includes(selectedContent.id) : false}
        isWatched={selectedContent ? watchedContentIds.includes(selectedContent.id) : false}
        onClose={handleCloseDetails}
        onWatchlist={handleModalWatchlist}
        onMarkWatched={handleModalWatched}
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
