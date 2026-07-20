export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

export type AgentKey = 'profiling' | 'retrieval' | 'ranking' | 'explanation';
export type AgentStepStatus = 'idle' | 'working' | 'completed';

export interface AgentStep {
  key: AgentKey;
  name: string;
  activity: string;
  status: AgentStepStatus;
}

export interface CastMember {
  id: number;
  name: string;
  character: string;
  photoUrl?: string;
}

export interface Movie {
  id: number;
  mediaType: 'movie' | 'series';
  title: string;
  originalTitle: string;
  year: number;
  runtime: string;
  rating: number;
  voteCount: number;
  matchScore: number;
  certification: string;
  genres: string[];
  posterUrl: string;
  backdropUrl: string;
  overview: string;
  explanation: string;
  director: string;
  cast: CastMember[];
  providers: string[];
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  initials: string;
  favoriteGenres: string[];
  preferences: string[];
  avoidedThemes: string[];
}

export interface RecommendationHistoryItem {
  id: string;
  query: string;
  createdAt: string;
  resultCount: number;
}

export interface RecommendationResponse {
  message: string;
  recommendations: Movie[];
  detectedPreferences: string[];
}

export type AppView = 'recommendations' | 'saved' | 'profile';
