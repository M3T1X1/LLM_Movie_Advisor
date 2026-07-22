import { Bookmark, ChevronRight, MessageSquareText, Plus, Sparkles } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { AnalyticsView } from './components/AnalyticsView';
import { CatalogCard, CatalogView } from './components/CatalogView';
import { ChatInterface } from './components/ChatInterface';
import { ConversationManager } from './components/ConversationManager';
import { EmptyState } from './components/EmptyState';
import { ForgotPasswordView } from './components/ForgotPasswordView';
import { LoginView } from './components/LoginView';
import { MovieDetailModal } from './components/MovieDetailModal';
import { Navbar } from './components/Navbar';
import { ProfileView } from './components/ProfileView';
import { RecommendationCard } from './components/RecommendationCard';
import { RegisterView } from './components/RegisterView';
import { TrendsView } from './components/TrendsView';
import { UpcomingReleasesView } from './components/UpcomingReleasesView';
import { useSession } from './context/SessionContext';
import { demoCatalogContent, initialAgentSteps } from './data/mockData';
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

const viewPaths: Record<AppView, string> = {
  login: '/login',
  register: '/register',
  'forgot-password': '/forgot-password',
  recommendations: '/recommendations',
  catalog: '/catalog',
  trends: '/trends',
  upcoming: '/upcoming',
  saved: '/watchlist',
  analytics: '/analytics',
  profile: '/profile',
};

function getViewFromPath(): AppView {
  const pathname = window.location.pathname.replace(/\/+$/, '') || '/';
  if (pathname === '/') return 'login';
  return (
    (Object.entries(viewPaths).find(([, path]) => path === pathname)?.[0] as AppView | undefined) ??
    'login'
  );
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
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation: deleteStoredConversation,
    addMessage,
    appendMessage,
    updateUser,
    addDetectedPreferences,
    updateConversationFromQuery,
    recordInteraction: storeInteraction,
    removeInteraction: removeStoredInteraction,
  } = useSession();
  const [activeView, setActiveView] = useState<AppView>(getViewFromPath);
  const [recommendationsByConversation, setRecommendationsByConversation] = useState<
    Record<string, RunCandidate[]>
  >({});
  const [catalogContent, setCatalogContent] = useState<Content[]>(demoCatalogContent);
  const [upcomingContent, setUpcomingContent] = useState<Content[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<RunCandidate | null>(null);
  const [selectedCatalogContent, setSelectedCatalogContent] = useState<Content | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>(initialAgentSteps);
  const recommendations = currentConversationId
    ? (recommendationsByConversation[currentConversationId] ?? [])
    : [];

  useEffect(() => {
    void getCatalogContent().then(setCatalogContent).catch(() => undefined);
  }, []);

  useEffect(() => {
    const handlePopState = () => setActiveView(getViewFromPath());
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = (view: AppView, replace = false) => {
    const path = viewPaths[view];
    if (window.location.pathname !== path) {
      window.history[replace ? 'replaceState' : 'pushState']({}, '', path);
    }
    setActiveView(view);
  };

  const completeLogin = () => {
    navigateTo('recommendations', true);
  };

  const handlePrompt = async (query: string) => {
    if (isProcessing || !currentConversationId) return;

    const conversationId = currentConversationId;
    navigateTo('recommendations');
    setIsProcessing(true);
    const userMessage = addMessage('user', query);
    setAgentSteps(initialAgentSteps.map((step) => ({ ...step, status: 'pending' })));

    const responsePromise = requestRecommendations(conversationId, userMessage).then(
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
      setRecommendationsByConversation((current) => ({
        ...current,
        [conversationId]: result.response.candidates,
      }));
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

  const handleCreateConversation = () => {
    createConversation();
    setSelectedCandidate(null);
    setSelectedCatalogContent(null);
    setAgentSteps(initialAgentSteps.map((step) => ({ ...step, status: 'pending' })));
  };

  const handleSelectConversation = (conversationId: string) => {
    selectConversation(conversationId);
    setSelectedCandidate(null);
    setSelectedCatalogContent(null);
    setAgentSteps(initialAgentSteps.map((step) => ({ ...step, status: 'pending' })));
  };

  const handleDeleteConversation = (conversationId: string) => {
    deleteStoredConversation(conversationId);
    setRecommendationsByConversation((current) => {
      const next = { ...current };
      delete next[conversationId];
      return next;
    });
    setSelectedCandidate(null);
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

  const availableContent = [
    ...catalogContent,
    ...upcomingContent.filter(
      (upcomingItem) => !catalogContent.some((catalogItem) => catalogItem.id === upcomingItem.id),
    ),
  ];
  const savedContent = availableContent.filter((content) =>
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
      {!['login', 'register', 'forgot-password'].includes(activeView) && (
        <Navbar
          user={user}
          activeView={activeView}
          onViewChange={navigateTo}
          onLogout={() => navigateTo('login', true)}
        />
      )}

      <div className={['login', 'register', 'forgot-password'].includes(activeView) ? '' : 'mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8'}>
        <main className="min-w-0">
          {activeView === 'login' ? (
            <LoginView
              onLogin={completeLogin}
              onRegister={() => navigateTo('register')}
              onForgotPassword={() => navigateTo('forgot-password')}
            />
          ) : activeView === 'register' ? (
            <RegisterView
              onBack={() => navigateTo('login')}
              onRegistered={() => navigateTo('login')}
            />
          ) : activeView === 'forgot-password' ? (
            <ForgotPasswordView onBack={() => navigateTo('login')} />
          ) : activeView === 'profile' ? (
            <ProfileView
              user={user}
              semanticProfile={semanticProfile}
              preferences={preferences}
              conversations={conversations}
              savedCount={watchlistedContentIds.length}
              watchedCount={watchedContentIds.length}
              onUpdateUser={updateUser}
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
          ) : activeView === 'trends' ? (
            <TrendsView onOpen={handleOpenCatalogContent} />
          ) : activeView === 'upcoming' ? (
            <UpcomingReleasesView
              watchlistedContentIds={watchlistedContentIds}
              onOpen={handleOpenCatalogContent}
              onWatchlist={handleCatalogWatchlist}
              onLoaded={setUpcomingContent}
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
                  onClick={() => navigateTo('recommendations')}
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
                <EmptyState onDiscover={() => navigateTo('recommendations')} />
              )}
            </div>
          ) : (
            <>
              <div className="mb-7 border-b border-white/[0.07] pb-7">
                <h1 className="text-center text-4xl font-semibold tracking-[-0.045em] text-white sm:text-5xl lg:text-6xl">
                  Dzień dobry, <span className="text-violet-400">{user.username}</span>
                </h1>
              </div>

              <div className="grid items-start gap-7 xl:grid-cols-[220px_minmax(0,1fr)]">
                <ConversationManager
                  conversations={conversations}
                  currentConversationId={currentConversationId}
                  disabled={isProcessing}
                  onCreate={handleCreateConversation}
                  onSelect={handleSelectConversation}
                  onRename={renameConversation}
                  onDelete={handleDeleteConversation}
                />

                <div className="grid min-w-0 items-start gap-7 2xl:grid-cols-[minmax(500px,1.08fr)_minmax(420px,0.92fr)]">
                  {currentConversationId ? (
                    <ChatInterface
                      messages={messages.filter(
                        (message) => message.conversationId === currentConversationId,
                      )}
                      agentSteps={agentSteps}
                      isProcessing={isProcessing}
                      onSubmit={handlePrompt}
                    />
                  ) : (
                    <ConversationWorkspaceEmpty onCreate={handleCreateConversation} />
                  )}

                  <section
                    aria-labelledby="recommendations-title"
                    className={
                      recommendations.length
                        ? undefined
                        : 'flex min-h-[680px] flex-col 2xl:h-[calc(100vh-6rem)] 2xl:min-h-[700px]'
                    }
                  >
                    <div
                      className={`transition-opacity duration-300 ${
                        recommendations.length ? 'space-y-4' : 'min-h-0 flex-1'
                      } ${
                        isProcessing ? 'opacity-50' : 'opacity-100'
                      }`}
                      aria-live="polite"
                    >
                      {recommendations.length ? (
                        recommendations.map(renderCard)
                      ) : (
                        <RecommendationEmptyState isProcessing={isProcessing} />
                      )}
                    </div>
                  </section>
                </div>
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

function ConversationWorkspaceEmpty({ onCreate }: { onCreate: () => void }) {
  return (
    <section className="flex min-h-[680px] flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.1] bg-[#0d0f15] px-6 text-center xl:sticky xl:top-[76px] xl:h-[calc(100vh-6rem)] xl:min-h-[700px]">
      <span className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-white/[0.04] text-slate-500">
        <MessageSquareText className="h-5 w-5" />
      </span>
      <h2 className="text-sm font-semibold text-white">Wybierz lub rozpocznij rozmowę</h2>
      <p className="mt-2 max-w-sm text-xs leading-5 text-slate-600">
        Rekomendacje pojawią się dopiero wtedy, gdy wyślesz własną wiadomość do LLM.
      </p>
      <button
        type="button"
        onClick={onCreate}
        className="mt-5 flex h-9 items-center gap-2 rounded-md bg-violet-600 px-3 text-xs font-medium text-white transition hover:bg-violet-500"
      >
        <Plus className="h-3.5 w-3.5" />
        Nowa rozmowa
      </button>
    </section>
  );
}

function RecommendationEmptyState({ isProcessing }: { isProcessing: boolean }) {
  return (
    <div className="flex h-full min-h-56 flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] bg-[#0d0f15]/60 px-6 text-center">
      <Sparkles className={`mb-3 h-5 w-5 ${isProcessing ? 'animate-pulse text-violet-400' : 'text-slate-700'}`} />
      <p className="text-xs font-medium text-slate-400">
        {isProcessing ? 'Analizuję Twój prompt…' : 'Brak rekomendacji w tej rozmowie'}
      </p>
      <p className="mt-2 max-w-xs text-[10px] leading-5 text-slate-600">
        {isProcessing
          ? 'Wyniki pojawią się po zakończeniu pracy agentów.'
          : 'Wyślij wiadomość w czacie, aby poprosić LLM o dopasowane filmy lub seriale.'}
      </p>
    </div>
  );
}
