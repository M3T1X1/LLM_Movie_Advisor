import type {
  AgentStep,
  ChatMessage,
  Movie,
  RecommendationHistoryItem,
  UserProfile,
} from '../types';

export const initialAgentSteps: AgentStep[] = [
  {
    key: 'profiling',
    name: 'Agent Profilowania',
    activity: 'Analizuje nastrój i intencję',
    status: 'idle',
  },
  {
    key: 'retrieval',
    name: 'Agent Danych',
    activity: 'Przeszukuje katalog TMDB',
    status: 'idle',
  },
  {
    key: 'ranking',
    name: 'Agent Rankingu',
    activity: 'Porównuje tytuły z Twoim gustem',
    status: 'idle',
  },
  {
    key: 'explanation',
    name: 'Agent Wyjaśnień',
    activity: 'Uzasadnia najlepsze wybory',
    status: 'idle',
  },
];

export const initialMessages: ChatMessage[] = [
  {
    id: 'welcome-message',
    role: 'assistant',
    content:
      'Cześć, Kacper. Opowiedz mi, jaki masz dziś nastrój albo jakiego doświadczenia szukasz — resztą zajmie się mój zespół agentów.',
    createdAt: new Date().toISOString(),
  },
];

export const demoUser: UserProfile = {
  id: 'user-1',
  name: 'Kacper Dusza',
  email: 'kacper@example.com',
  initials: 'KD',
  favoriteGenres: ['Thriller', 'Sci-Fi', 'Dramat'],
  preferences: ['Niejednoznaczne zakończenia', 'Powolne budowanie napięcia', 'Mroczny klimat'],
  avoidedThemes: ['Slapstick', 'Nadmierny gore'],
};

export const demoHistory: RecommendationHistoryItem[] = [
  {
    id: 'history-1',
    query: 'Inteligentne sci-fi na spokojny wieczór',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
    resultCount: 6,
  },
  {
    id: 'history-2',
    query: 'Krótki serial kryminalny bez zbędnych wątków',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
    resultCount: 5,
  },
];

export const demoMovies: Movie[] = [
  {
    id: 210577,
    mediaType: 'movie',
    title: 'Zaginiona dziewczyna',
    originalTitle: 'Gone Girl',
    year: 2014,
    runtime: '2 godz. 29 min',
    rating: 8.1,
    voteCount: 19100,
    matchScore: 96,
    certification: '16+',
    genres: ['Thriller', 'Tajemnica', 'Dramat'],
    posterUrl: 'https://image.tmdb.org/t/p/w780/ts996lKsxvjkO2yiYG0ht4qAicO.jpg',
    backdropUrl: 'https://image.tmdb.org/t/p/original/7LZ0K4FsALrt7OeNIGOVLNuKQRU.jpg',
    overview:
      'W dniu piątej rocznicy ślubu Nick Dunne odkrywa, że jego żona Amy zniknęła. Presja policji i mediów odsłania pęknięcia w ich pozornie idealnym małżeństwie.',
    explanation:
      'Trafia w Twoją potrzebę mrocznej historii z mocnym twistem i bez komfortowego domknięcia. Film stale podważa ocenę bohaterów, a napięcie wynika bardziej z psychologicznej gry niż z przemocy.',
    director: 'David Fincher',
    cast: [
      { id: 1, name: 'Ben Affleck', character: 'Nick Dunne' },
      { id: 2, name: 'Rosamund Pike', character: 'Amy Dunne' },
      { id: 3, name: 'Carrie Coon', character: 'Margo Dunne' },
      { id: 4, name: 'Neil Patrick Harris', character: 'Desi Collings' },
    ],
    providers: ['Netflix', 'Apple TV'],
  },
  {
    id: 146233,
    mediaType: 'movie',
    title: 'Labirynt',
    originalTitle: 'Prisoners',
    year: 2013,
    runtime: '2 godz. 33 min',
    rating: 8.2,
    voteCount: 11800,
    matchScore: 93,
    certification: '16+',
    genres: ['Thriller', 'Kryminał', 'Dramat'],
    posterUrl: 'https://image.tmdb.org/t/p/w780/tuZhZ6biFMr5n9YSVuHOJnNL1uU.jpg',
    backdropUrl: 'https://image.tmdb.org/t/p/original/cCvp5Sni75agCtyJkNOMapORUQV.jpg',
    overview:
      'Gdy znikają dwie dziewczynki, zdesperowany ojciec bierze sprawy w swoje ręce, podczas gdy prowadzący śledztwo detektyw podąża za kolejnymi niepokojącymi tropami.',
    explanation:
      'To najcięższa emocjonalnie propozycja w zestawie. Powolne budowanie napięcia, moralnie niejednoznaczne decyzje i finał pozostawiający przestrzeń do interpretacji dobrze odpowiadają Twojemu profilowi.',
    director: 'Denis Villeneuve',
    cast: [
      { id: 5, name: 'Hugh Jackman', character: 'Keller Dover' },
      { id: 6, name: 'Jake Gyllenhaal', character: 'Detektyw Loki' },
      { id: 7, name: 'Viola Davis', character: 'Nancy Birch' },
      { id: 8, name: 'Paul Dano', character: 'Alex Jones' },
    ],
    providers: ['Max', 'Canal+'],
  },
  {
    id: 6977,
    mediaType: 'movie',
    title: 'To nie jest kraj dla starych ludzi',
    originalTitle: 'No Country for Old Men',
    year: 2007,
    runtime: '2 godz. 2 min',
    rating: 7.9,
    voteCount: 12100,
    matchScore: 89,
    certification: '16+',
    genres: ['Kryminał', 'Thriller', 'Western'],
    posterUrl: 'https://image.tmdb.org/t/p/w780/bj1v6YKF8yHqA489VFfnQvOJpnc.jpg',
    backdropUrl: 'https://image.tmdb.org/t/p/original/kK9v1wclQxug6ZUJucD4DTaHgVF.jpg',
    overview:
      'Przypadkowe znalezienie walizki pełnej pieniędzy uruchamia bezlitosny pościg przez zachodni Teksas, w którym los i przemoc splatają się ze sobą.',
    explanation:
      'Brak klasycznego happy endu jest tu czymś więcej niż zabiegiem fabularnym — wzmacnia fatalistyczny ton całej historii. Oszczędna narracja i niepokojący antagonista tworzą dokładnie ten rodzaj mroku, którego szukasz.',
    director: 'Joel i Ethan Coen',
    cast: [
      { id: 9, name: 'Javier Bardem', character: 'Anton Chigurh' },
      { id: 10, name: 'Josh Brolin', character: 'Llewelyn Moss' },
      { id: 11, name: 'Tommy Lee Jones', character: 'Ed Tom Bell' },
      { id: 12, name: 'Kelly Macdonald', character: 'Carla Jean Moss' },
    ],
    providers: ['SkyShowtime', 'Prime Video'],
  },
];

export const promptSuggestions = [
  'Coś mrocznego z twistem, bez happy endu',
  'Lekki serial na dwa wieczory',
  'Ambitne sci-fi, które daje do myślenia',
];
