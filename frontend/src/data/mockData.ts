import type {
  AgentExecution,
  AgentStep,
  AppUser,
  ChatMessage,
  Content,
  Conversation,
  Interaction,
  RecommendationTrends,
  RecommendationRequestRecord,
  RecommendationRun,
  RunCandidate,
  UserPreference,
  UserSemanticProfile,
  TrendPeriod,
} from '../types';

const now = new Date().toISOString();
const yesterday = new Date(Date.now() - 86_400_000).toISOString();
const fourDaysAgo = new Date(Date.now() - 4 * 86_400_000).toISOString();

export const demoUser: AppUser = {
  id: '1',
  email: 'kacper@example.com',
  username: 'kacper',
  dateJoined: '2026-07-01T10:00:00.000Z',
  isActive: true,
};

export const demoProfile: UserSemanticProfile = {
  userId: '1',
  semanticSummary:
    'Preferuje kino o mrocznym klimacie, z powolnie budowanym napięciem i niejednoznacznym finałem.',
  version: 1,
  lastRebuiltAt: yesterday,
  updatedAt: yesterday,
};

export const demoPreferences: UserPreference[] = [
  createPreference('1', 'genre', 'Thriller', 1, 0.95),
  createPreference('2', 'genre', 'Science Fiction', 1, 0.87),
  createPreference('3', 'genre', 'Drama', 1, 0.82),
  createPreference('4', 'narrative', 'Niejednoznaczne zakończenia', 1, 0.9),
  createPreference('5', 'pacing', 'Powolne budowanie napięcia', 1, 0.84),
  createPreference('6', 'mood', 'Mroczny klimat', 1, 0.92),
  createPreference('7', 'humor', 'Slapstick', -1, 0.88),
  createPreference('8', 'violence', 'Nadmierny gore', -1, 0.8),
];

export const demoConversations: Conversation[] = [
  {
    id: '1',
    userId: '1',
    title: 'Mroczny thriller z twistem',
    createdAt: now,
    updatedAt: now,
  },
  {
    id: '2',
    userId: '1',
    title: 'Inteligentne sci-fi na spokojny wieczór',
    createdAt: yesterday,
    updatedAt: yesterday,
  },
  {
    id: '3',
    userId: '1',
    title: 'Krótki serial kryminalny',
    createdAt: fourDaysAgo,
    updatedAt: fourDaysAgo,
  },
];

export const initialMessages: ChatMessage[] = [
  {
    id: '1',
    conversationId: '1',
    role: 'assistant',
    content:
      'Cześć. Opowiedz mi, jaki masz dziś nastrój albo jakiego doświadczenia szukasz — resztą zajmie się mój zespół agentów.',
    sequenceNo: 1,
    createdAt: now,
  },
];

export const initialAgentSteps: AgentStep[] = [
  {
    key: 'profiling',
    name: 'Agent Profilowania',
    activity: 'Analizuje nastrój i intencję',
    status: 'pending',
  },
  {
    key: 'retrieval',
    name: 'Agent Danych',
    activity: 'Przeszukuje katalog TMDB',
    status: 'pending',
  },
  {
    key: 'ranking',
    name: 'Agent Rankingu',
    activity: 'Porównuje tytuły z Twoim gustem',
    status: 'pending',
  },
  {
    key: 'explanation',
    name: 'Agent Wyjaśnień',
    activity: 'Uzasadnia najlepsze wybory',
    status: 'pending',
  },
];

export const demoRequest: RecommendationRequestRecord = {
  id: '1',
  conversationId: '1',
  triggerMessageId: '2',
  mood: 'mroczny',
  extractedContext: {
    themes: ['twist fabularny'],
    desired_tone: 'mroczny',
  },
  constraintsData: {
    ending: 'bez happy endu',
  },
  createdAt: now,
};

export const demoRun: RecommendationRun = {
  id: '1',
  requestId: '1',
  status: 'completed',
  graphVersion: '1.0',
  modelName: 'mock-model',
  startedAt: now,
  finishedAt: now,
};

export const demoCandidates: RunCandidate[] = [
  {
    id: '1',
    runId: '1',
    contentId: '101',
    sourceRank: 2,
    relevanceScore: 0.95,
    criticScore: 0.92,
    finalScore: 0.96,
    status: 'selected',
    finalRank: 1,
    decisionReason: 'Najwyższa zgodność z nastrojem i preferowanym typem zakończenia.',
    explanation:
      'Trafia w Twoją potrzebę mrocznej historii z mocnym twistem i bez komfortowego domknięcia. Film stale podważa ocenę bohaterów, a napięcie wynika bardziej z psychologicznej gry niż z przemocy.',
    metadataSnapshot: {},
    createdAt: now,
    content: {
      id: '101',
      tmdbId: 210577,
      mediaType: 'movie',
      title: 'Zaginiona dziewczyna',
      originalTitle: 'Gone Girl',
      overview:
        'W dniu piątej rocznicy ślubu Nick Dunne odkrywa, że jego żona Amy zniknęła. Presja policji i mediów odsłania pęknięcia w ich pozornie idealnym małżeństwie.',
      releaseDate: '2014-10-01',
      originalLanguage: 'en',
      posterPath: '/ts996lKsxvjkO2yiYG0ht4qAicO.jpg',
      voteAverage: 8.1,
      popularity: 78.4,
      metadata: {
        runtimeMinutes: 149,
        voteCount: 19100,
        certification: '16+',
        backdropPath: '/7LZ0K4FsALrt7OeNIGOVLNuKQRU.jpg',
        director: 'David Fincher',
        providers: ['Netflix', 'Apple TV'],
      },
      tmdbRefreshedAt: now,
      genres: [
        { id: '1', tmdbGenreId: 53, name: 'Thriller' },
        { id: '2', tmdbGenreId: 9648, name: 'Tajemnica' },
        { id: '3', tmdbGenreId: 18, name: 'Dramat' },
      ],
    },
  },
  {
    id: '2',
    runId: '1',
    contentId: '102',
    sourceRank: 1,
    relevanceScore: 0.94,
    criticScore: 0.91,
    finalScore: 0.93,
    status: 'selected',
    finalRank: 2,
    decisionReason: 'Bardzo wysoka zgodność z preferowanym tempem i moralną niejednoznacznością.',
    explanation:
      'To najcięższa emocjonalnie propozycja w zestawie. Powolne budowanie napięcia, moralnie niejednoznaczne decyzje i finał pozostawiający przestrzeń do interpretacji dobrze odpowiadają Twojemu profilowi.',
    metadataSnapshot: {},
    createdAt: now,
    content: {
      id: '102',
      tmdbId: 146233,
      mediaType: 'movie',
      title: 'Labirynt',
      originalTitle: 'Prisoners',
      overview:
        'Gdy znikają dwie dziewczynki, zdesperowany ojciec bierze sprawy w swoje ręce, podczas gdy prowadzący śledztwo detektyw podąża za kolejnymi niepokojącymi tropami.',
      releaseDate: '2013-09-19',
      originalLanguage: 'en',
      posterPath: '/tuZhZ6biFMr5n9YSVuHOJnNL1uU.jpg',
      voteAverage: 8.2,
      popularity: 66.7,
      metadata: {
        runtimeMinutes: 153,
        voteCount: 11800,
        certification: '16+',
        backdropPath: '/cCvp5Sni75agCtyJkNOMapORUQV.jpg',
        director: 'Denis Villeneuve',
        providers: ['Max', 'Canal+'],
      },
      tmdbRefreshedAt: now,
      genres: [
        { id: '1', tmdbGenreId: 53, name: 'Thriller' },
        { id: '4', tmdbGenreId: 80, name: 'Kryminał' },
        { id: '3', tmdbGenreId: 18, name: 'Dramat' },
      ],
    },
  },
  {
    id: '3',
    runId: '1',
    contentId: '103',
    sourceRank: 4,
    relevanceScore: 0.9,
    criticScore: 0.94,
    finalScore: 0.89,
    status: 'selected',
    finalRank: 3,
    decisionReason: 'Mocne dopasowanie do oczekiwanego tonu i braku klasycznego happy endu.',
    explanation:
      'Brak klasycznego happy endu jest tu czymś więcej niż zabiegiem fabularnym — wzmacnia fatalistyczny ton całej historii. Oszczędna narracja i niepokojący antagonista tworzą dokładnie ten rodzaj mroku, którego szukasz.',
    metadataSnapshot: {},
    createdAt: now,
    content: {
      id: '103',
      tmdbId: 6977,
      mediaType: 'movie',
      title: 'To nie jest kraj dla starych ludzi',
      originalTitle: 'No Country for Old Men',
      overview:
        'Przypadkowe znalezienie walizki pełnej pieniędzy uruchamia bezlitosny pościg przez zachodni Teksas, w którym los i przemoc splatają się ze sobą.',
      releaseDate: '2007-11-08',
      originalLanguage: 'en',
      posterPath: '/bj1v6YKF8yHqA489VFfnQvOJpnc.jpg',
      voteAverage: 7.9,
      popularity: 57.1,
      metadata: {
        runtimeMinutes: 122,
        voteCount: 12100,
        certification: '16+',
        backdropPath: '/kK9v1wclQxug6ZUJucD4DTaHgVF.jpg',
        director: 'Joel i Ethan Coen',
        providers: ['SkyShowtime', 'Prime Video'],
      },
      tmdbRefreshedAt: now,
      genres: [
        { id: '4', tmdbGenreId: 80, name: 'Kryminał' },
        { id: '1', tmdbGenreId: 53, name: 'Thriller' },
        { id: '5', tmdbGenreId: 37, name: 'Western' },
      ],
    },
  },
];

const additionalCatalogContent: Content[] = [
  {
    id: '104',
    tmdbId: 70523,
    mediaType: 'tv',
    title: 'Dark',
    originalTitle: 'Dark',
    overview:
      'Zaginięcie dziecka odsłania tajemnice czterech rodzin i rozpoczyna skomplikowaną podróż przez trzy pokolenia mieszkańców niemieckiego miasteczka.',
    releaseDate: '2017-12-01',
    originalLanguage: 'de',
    posterPath: '/apbrbWs8M9lyOpJYU5WXrpFbk1Z.jpg',
    voteAverage: 8.4,
    popularity: 92.3,
    metadata: {
      runtimeMinutes: 60,
      voteCount: 6900,
      certification: '16+',
      providers: ['Netflix'],
    },
    tmdbRefreshedAt: now,
    genres: [
      { id: '6', tmdbGenreId: 10765, name: 'Sci-Fi i Fantasy' },
      { id: '2', tmdbGenreId: 9648, name: 'Tajemnica' },
      { id: '3', tmdbGenreId: 18, name: 'Dramat' },
    ],
  },
  {
    id: '105',
    tmdbId: 136315,
    mediaType: 'tv',
    title: 'The Bear',
    originalTitle: 'The Bear',
    overview:
      'Młody szef kuchni wraca do Chicago, aby prowadzić rodzinny bar kanapkowy i zmierzyć się z chaosem kuchni oraz własną przeszłością.',
    releaseDate: '2022-06-23',
    originalLanguage: 'en',
    posterPath: '/sHFlbKS3WLqMnp9t2ghADIJFnuQ.jpg',
    voteAverage: 8.2,
    popularity: 84.6,
    metadata: {
      runtimeMinutes: 30,
      voteCount: 1200,
      certification: '16+',
      providers: ['Disney+'],
    },
    tmdbRefreshedAt: now,
    genres: [
      { id: '3', tmdbGenreId: 18, name: 'Dramat' },
      { id: '7', tmdbGenreId: 35, name: 'Komedia' },
    ],
  },
  {
    id: '106',
    tmdbId: 693134,
    mediaType: 'movie',
    title: 'Diuna: Część druga',
    originalTitle: 'Dune: Part Two',
    overview:
      'Paul Atryda jednoczy się z Chani i Fremenami, przygotowując zemstę na spiskowcach odpowiedzialnych za upadek jego rodu.',
    releaseDate: '2024-02-27',
    originalLanguage: 'en',
    posterPath: '/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg',
    voteAverage: 8.1,
    popularity: 118.2,
    metadata: {
      runtimeMinutes: 166,
      voteCount: 6200,
      certification: '13+',
      backdropPath: '/xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg',
      director: 'Denis Villeneuve',
      providers: ['Max'],
    },
    tmdbRefreshedAt: now,
    genres: [
      { id: '9', tmdbGenreId: 878, name: 'Science Fiction' },
      { id: '8', tmdbGenreId: 12, name: 'Przygodowy' },
      { id: '3', tmdbGenreId: 18, name: 'Dramat' },
    ],
  },
];

export const demoCatalogContent: Content[] = [
  ...demoCandidates.map((candidate) => candidate.content),
  ...additionalCatalogContent,
];

export const demoRecommendationTrends: Record<TrendPeriod, RecommendationTrends> = {
  day: {
    period: 'day',
    totalRecommendations: 486,
    generatedAt: now,
    genreTrends: [
      { genreName: 'Thriller', recommendationCount: 148 },
      { genreName: 'Dramat', recommendationCount: 121 },
      { genreName: 'Tajemnica', recommendationCount: 96 },
      { genreName: 'Kryminał', recommendationCount: 81 },
      { genreName: 'Science Fiction', recommendationCount: 69 },
    ],
    contentTrends: [
      { content: demoCatalogContent[0], recommendationCount: 84 },
      { content: demoCatalogContent[1], recommendationCount: 72 },
      { content: demoCatalogContent[2], recommendationCount: 63 },
    ],
  },
  week: {
    period: 'week',
    totalRecommendations: 3154,
    generatedAt: now,
    genreTrends: [
      { genreName: 'Dramat', recommendationCount: 892 },
      { genreName: 'Thriller', recommendationCount: 814 },
      { genreName: 'Science Fiction', recommendationCount: 607 },
      { genreName: 'Tajemnica', recommendationCount: 536 },
      { genreName: 'Kryminał', recommendationCount: 471 },
    ],
    contentTrends: [
      { content: demoCatalogContent[1], recommendationCount: 486 },
      { content: demoCatalogContent[5], recommendationCount: 459 },
      { content: demoCatalogContent[0], recommendationCount: 421 },
    ],
  },
  month: {
    period: 'month',
    totalRecommendations: 12849,
    generatedAt: now,
    genreTrends: [
      { genreName: 'Dramat', recommendationCount: 3842 },
      { genreName: 'Science Fiction', recommendationCount: 3106 },
      { genreName: 'Thriller', recommendationCount: 2984 },
      { genreName: 'Tajemnica', recommendationCount: 2135 },
      { genreName: 'Kryminał', recommendationCount: 1987 },
    ],
    contentTrends: [
      { content: demoCatalogContent[5], recommendationCount: 1842 },
      { content: demoCatalogContent[0], recommendationCount: 1693 },
      { content: demoCatalogContent[2], recommendationCount: 1511 },
    ],
  },
};

export const demoAgentExecutions: AgentExecution[] = initialAgentSteps.map((step, index) => ({
  id: String(index + 1),
  runId: '1',
  agentType: step.key,
  sequenceNo: index + 1,
  status: 'success',
  inputSnapshot: {},
  outputSnapshot: {},
  durationMs: 500 + index * 120,
  startedAt: now,
  finishedAt: now,
}));

export const demoInteractions: Interaction[] = [
  {
    id: '1',
    userId: '1',
    contentId: '101',
    sourceCandidateId: '1',
    interactionType: 'watchlisted',
    rating: null,
    metadata: {},
    createdAt: yesterday,
  },
  {
    id: '2',
    userId: '1',
    contentId: '102',
    sourceCandidateId: '2',
    interactionType: 'watched',
    rating: null,
    metadata: {},
    createdAt: '2026-02-12T19:30:00.000Z',
  },
  {
    id: '3',
    userId: '1',
    contentId: '103',
    sourceCandidateId: '3',
    interactionType: 'watched',
    rating: null,
    metadata: {},
    createdAt: '2026-03-08T21:10:00.000Z',
  },
  {
    id: '4',
    userId: '1',
    contentId: '104',
    sourceCandidateId: null,
    interactionType: 'watched',
    rating: null,
    metadata: {},
    createdAt: '2026-04-17T20:00:00.000Z',
  },
  {
    id: '5',
    userId: '1',
    contentId: '105',
    sourceCandidateId: null,
    interactionType: 'watched',
    rating: null,
    metadata: {},
    createdAt: '2026-05-22T18:45:00.000Z',
  },
  {
    id: '6',
    userId: '1',
    contentId: '106',
    sourceCandidateId: null,
    interactionType: 'watched',
    rating: null,
    metadata: {},
    createdAt: '2026-06-28T20:20:00.000Z',
  },
];

export const promptSuggestions = [
  'Coś mrocznego z twistem, bez happy endu',
  'Lekki serial na dwa wieczory',
  'Ambitne sci-fi, które daje do myślenia',
];

function createPreference(
  id: string,
  preferenceType: string,
  preferenceValue: string,
  polarity: -1 | 0 | 1,
  confidence: number,
): UserPreference {
  return {
    id,
    userId: '1',
    preferenceType,
    preferenceValue,
    polarity,
    weight: 1,
    confidence,
    createdAt: yesterday,
    updatedAt: yesterday,
  };
}
