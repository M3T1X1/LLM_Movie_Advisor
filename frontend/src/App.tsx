import { Bookmark, ChevronRight, MessageSquareText, Plus, Sparkles } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { AnalyticsView } from './components/AnalyticsView';
import { CatalogCard, CatalogView } from './components/CatalogView';
import { ChatInterface } from './components/ChatInterface';
import { ConversationManager } from './components/ConversationManager';
import { EmptyState } from './components/EmptyState';
import { LoginView } from './components/LoginView';
import { MovieDetailModal } from './components/MovieDetailModal';
import { Navbar } from './components/Navbar';
import { ProfileView } from './components/ProfileView';
import { RegisterView } from './components/RegisterView';
import { TrendsView } from './components/TrendsView';
import { UpcomingReleasesView } from './components/UpcomingReleasesView';
import { useSession } from './context/SessionContext';
import { getCatalogContent, getContentByIds } from './services/api';
import type { AgentStep, AppView, CatalogPage, CatalogQuery, Content } from './types';

const inactiveAgentSteps: AgentStep[] = [
  { key: 'profiling', name: 'Agent Profilowania', activity: 'Integracja oczekuje na uruchomienie systemu rekomendacji', status: 'pending' },
  { key: 'retrieval', name: 'Agent Danych', activity: 'Integracja oczekuje na uruchomienie systemu rekomendacji', status: 'pending' },
  { key: 'ranking', name: 'Agent Rankingu', activity: 'Integracja oczekuje na uruchomienie systemu rekomendacji', status: 'pending' },
  { key: 'explanation', name: 'Agent Wyjaśnień', activity: 'Integracja oczekuje na uruchomienie systemu rekomendacji', status: 'pending' },
];

const initialCatalogQuery: CatalogQuery = {
  page: 1,
  pageSize: 20,
  search: '',
  mediaType: 'all',
  genre: 'all',
  minimumRating: 0,
  yearFrom: null,
  sortBy: 'popularity',
};

const emptyCatalogPage: CatalogPage = {
  items: [],
  pagination: {
    page: 1,
    pageSize: 20,
    totalItems: 0,
    totalPages: 0,
    hasPrevious: false,
    hasNext: false,
  },
  filters: { genres: [] },
};

const viewPaths: Record<AppView, string> = {
  login: '/login',
  register: '/register',
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
    isLoading,
    login,
    register,
    logout,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation: deleteStoredConversation,
    addMessage,
    updateUser,
    recordInteraction: storeInteraction,
    removeInteraction: removeStoredInteraction,
  } = useSession();
  const [activeView, setActiveView] = useState<AppView>(getViewFromPath);
  const [catalogQuery, setCatalogQuery] = useState<CatalogQuery>(initialCatalogQuery);
  const [catalogPage, setCatalogPage] = useState<CatalogPage>(emptyCatalogPage);
  const [knownCatalogContent, setKnownCatalogContent] = useState<Content[]>([]);
  const [isCatalogLoading, setIsCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [upcomingContent, setUpcomingContent] = useState<Content[]>([]);
  const [selectedCatalogContent, setSelectedCatalogContent] = useState<Content | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (!user) {
      setCatalogPage(emptyCatalogPage);
      setKnownCatalogContent([]);
      setCatalogError(null);
      return;
    }
    let isCurrentRequest = true;
    setIsCatalogLoading(true);
    setCatalogError(null);
    void getCatalogContent(catalogQuery)
      .then((response) => {
        if (!isCurrentRequest) return;
        setCatalogPage(response);
        setKnownCatalogContent((current) => {
          const byId = new Map(current.map((item) => [item.id, item]));
          response.items.forEach((item) => byId.set(item.id, item));
          return Array.from(byId.values());
        });
      })
      .catch(() => {
        if (!isCurrentRequest) return;
        setCatalogPage((current) => ({ ...current, items: [] }));
        setCatalogError('Nie udało się pobrać katalogu. Spróbuj ponownie.');
      })
      .finally(() => {
        if (isCurrentRequest) setIsCatalogLoading(false);
      });
    return () => {
      isCurrentRequest = false;
    };
  }, [catalogQuery, user]);

  useEffect(() => {
    if (!user) return;
    const interactedContentIds = interactions.map(
      (interaction) => interaction.contentId,
    );
    if (!interactedContentIds.length) return;
    let isCurrentRequest = true;
    void getContentByIds(interactedContentIds)
      .then((items) => {
        if (!isCurrentRequest) return;
        setKnownCatalogContent((current) => {
          const byId = new Map(current.map((item) => [item.id, item]));
          items.forEach((item) => byId.set(item.id, item));
          return Array.from(byId.values());
        });
      })
      .catch(() => undefined);
    return () => {
      isCurrentRequest = false;
    };
  }, [interactions, user]);

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

  useEffect(() => {
    if (isLoading) return;
    const isPublicView = ['login', 'register'].includes(activeView);
    if (!user && !isPublicView) navigateTo('login', true);
  }, [activeView, isLoading, user]);

  const completeLogin = async (email: string, password: string) => {
    await login(email, password);
    navigateTo('recommendations', true);
  };

  const completeRegistration = async (
    username: string,
    email: string,
    password: string,
  ) => {
    await register(username, email, password);
    navigateTo('recommendations', true);
  };

  const handleLogout = async () => {
    await logout();
    navigateTo('login', true);
  };

  const handlePrompt = async (query: string) => {
    if (isProcessing || !currentConversationId) return;

    navigateTo('recommendations');
    setIsProcessing(true);
    try {
      await addMessage('user', query);
    } catch {
      // The chat keeps the typed value in the component when persistence fails.
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCreateConversation = async () => {
    await createConversation();
    setSelectedCatalogContent(null);
  };

  const handleSelectConversation = (conversationId: string) => {
    selectConversation(conversationId);
    setSelectedCatalogContent(null);
  };

  const handleDeleteConversation = async (conversationId: string) => {
    await deleteStoredConversation(conversationId);
  };

  const handleOpenCatalogContent = (content: Content) => {
    setSelectedCatalogContent(content);
    void storeInteraction(content.id, null, 'details_opened').catch(() => undefined);
  };

  const handleCatalogWatchlist = (content: Content) => {
    if (watchlistedContentIds.includes(content.id)) {
      void removeStoredInteraction(content.id, 'watchlisted').catch(() => undefined);
      return;
    }
    void storeInteraction(content.id, null, 'watchlisted').catch(() => undefined);
  };

  const handleCatalogWatched = (content: Content) => {
    if (watchedContentIds.includes(content.id)) {
      void removeStoredInteraction(content.id, 'watched').catch(() => undefined);
      return;
    }
    void storeInteraction(content.id, null, 'watched').catch(() => undefined);
  };

  const availableContent = [
    ...knownCatalogContent,
    ...upcomingContent.filter(
      (upcomingItem) => !knownCatalogContent.some((catalogItem) => catalogItem.id === upcomingItem.id),
    ),
  ];
  const savedContent = availableContent.filter((content) =>
    watchlistedContentIds.includes(content.id),
  );
  const selectedContent = selectedCatalogContent;

  const handleCloseDetails = () => {
    setSelectedCatalogContent(null);
  };

  const handleModalWatchlist = () => {
    if (selectedCatalogContent) handleCatalogWatchlist(selectedCatalogContent);
  };

  const handleModalWatched = () => {
    if (selectedCatalogContent) handleCatalogWatched(selectedCatalogContent);
  };

  if (isLoading) {
    return <div className="min-h-screen bg-ink-950" aria-label="Ładowanie aplikacji" />;
  }

  const isPublicView = ['login', 'register'].includes(activeView);
  const effectiveView = !user && !isPublicView ? 'login' : activeView;
  const profile = semanticProfile ?? {
    userId: user?.id ?? '',
    semanticSummary: null,
    version: 1,
    lastRebuiltAt: null,
    updatedAt: new Date().toISOString(),
  };

  return (
    <div className="min-h-screen bg-ink-950 text-slate-100 selection:bg-violet-500/30">
      {user && !['login', 'register'].includes(effectiveView) && (
        <Navbar
          user={user}
          activeView={effectiveView}
          onViewChange={navigateTo}
          onLogout={() => void handleLogout()}
        />
      )}

      <div className={['login', 'register'].includes(effectiveView) ? '' : 'mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8'}>
        <main className="min-w-0">
          {effectiveView === 'login' ? (
            <LoginView
              onLogin={completeLogin}
              onRegister={() => navigateTo('register')}
            />
          ) : effectiveView === 'register' ? (
            <RegisterView
              onBack={() => navigateTo('login')}
              onRegistered={completeRegistration}
            />
          ) : effectiveView === 'profile' && user ? (
            <ProfileView
              user={user}
              semanticProfile={profile}
              preferences={preferences}
              conversations={conversations}
              savedCount={watchlistedContentIds.length}
              watchedCount={watchedContentIds.length}
              onUpdateUser={updateUser}
            />
          ) : effectiveView === 'analytics' ? (
            <AnalyticsView
              content={knownCatalogContent}
              interactions={interactions}
              preferences={preferences}
            />
          ) : effectiveView === 'catalog' ? (
            <CatalogView
              content={catalogPage.items}
              genres={catalogPage.filters.genres}
              pagination={catalogPage.pagination}
              query={catalogQuery}
              isLoading={isCatalogLoading}
              error={catalogError}
              onQueryChange={setCatalogQuery}
              watchlistedContentIds={watchlistedContentIds}
              watchedContentIds={watchedContentIds}
              onOpen={handleOpenCatalogContent}
              onWatchlist={handleCatalogWatchlist}
              onMarkWatched={handleCatalogWatched}
            />
          ) : effectiveView === 'trends' ? (
            <TrendsView onOpen={handleOpenCatalogContent} />
          ) : effectiveView === 'upcoming' ? (
            <UpcomingReleasesView
              watchlistedContentIds={watchlistedContentIds}
              onOpen={handleOpenCatalogContent}
              onWatchlist={handleCatalogWatchlist}
              onLoaded={setUpcomingContent}
            />
          ) : effectiveView === 'saved' ? (
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
                  Dzień dobry, <span className="text-violet-400">{user?.username}</span>
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
                      agentSteps={inactiveAgentSteps}
                      isProcessing={isProcessing}
                      onSubmit={handlePrompt}
                    />
                  ) : (
                    <ConversationWorkspaceEmpty onCreate={handleCreateConversation} />
                  )}

                  <section
                    aria-labelledby="recommendations-title"
                    className="flex min-h-[680px] flex-col 2xl:h-[calc(100vh-6rem)] 2xl:min-h-[700px]"
                  >
                    <div
                      className={`min-h-0 flex-1 transition-opacity duration-300 ${
                        isProcessing ? 'opacity-50' : 'opacity-100'
                      }`}
                      aria-live="polite"
                    >
                      <RecommendationEmptyState isProcessing={false} />
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
        recommendation={null}
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
        Wiadomości zostaną zapisane. Moduł rekomendacji zostanie podłączony w kolejnym etapie.
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
        {isProcessing ? 'Zapisuję wiadomość…' : 'System rekomendacji nie jest jeszcze aktywny'}
      </p>
      <p className="mt-2 max-w-xs text-[10px] leading-5 text-slate-600">
        {isProcessing
          ? 'Wiadomość jest zapisywana w PostgreSQL.'
          : 'Rozmowy są już zapisywane w bazie. Agenci i LLM zostaną podłączeni w kolejnym etapie.'}
      </p>
    </div>
  );
}
