export type DatabaseId = string;
export type MediaType = 'movie' | 'tv';
export type MessageRole = 'user' | 'assistant' | 'system';
export type RecommendationRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type CandidateStatus = 'pending' | 'selected' | 'rejected';
export type AgentExecutionStatus = 'pending' | 'running' | 'success' | 'failed';
export type InteractionType =
  | 'details_opened'
  | 'liked'
  | 'disliked'
  | 'watchlisted'
  | 'watched'
  | 'rated';

export interface AppUser {
  id: DatabaseId;
  email: string;
  username: string;
  dateJoined: string;
  isActive: boolean;
}

export interface UserSemanticProfile {
  userId: DatabaseId;
  semanticSummary: string | null;
  version: number;
  lastRebuiltAt: string | null;
  updatedAt: string;
}

export interface UserPreference {
  id: DatabaseId;
  userId: DatabaseId;
  preferenceType: string;
  preferenceValue: string;
  polarity: -1 | 0 | 1;
  weight: number;
  confidence: number;
  createdAt: string;
  updatedAt: string;
}

export interface Conversation {
  id: DatabaseId;
  userId: DatabaseId;
  title: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ChatMessage {
  id: DatabaseId;
  conversationId: DatabaseId;
  role: MessageRole;
  content: string;
  sequenceNo: number;
  createdAt: string;
}

export interface RecommendationRequestRecord {
  id: DatabaseId;
  conversationId: DatabaseId;
  triggerMessageId: DatabaseId | null;
  mood: string | null;
  extractedContext: Record<string, unknown>;
  constraintsData: Record<string, unknown>;
  createdAt: string;
}

export interface RecommendationRun {
  id: DatabaseId;
  requestId: DatabaseId;
  status: RecommendationRunStatus;
  graphVersion: string | null;
  modelName: string | null;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface Genre {
  id: DatabaseId;
  tmdbGenreId: number;
  name: string;
}

export interface ContentMetadata {
  runtimeMinutes?: number;
  voteCount?: number;
  certification?: string;
  backdropPath?: string;
  director?: string;
  providers?: string[];
}

export interface Content {
  id: DatabaseId;
  tmdbId: number;
  mediaType: MediaType;
  title: string;
  originalTitle: string | null;
  overview: string | null;
  releaseDate: string | null;
  originalLanguage: string | null;
  posterPath: string | null;
  voteAverage: number | null;
  popularity: number | null;
  metadata: ContentMetadata;
  tmdbRefreshedAt: string | null;
  genres: Genre[];
}

export type CatalogMediaFilter = 'all' | MediaType;
export type CatalogSort = 'popularity' | 'rating' | 'newest' | 'title';

export interface CatalogQuery {
  page: number;
  pageSize: number;
  search: string;
  mediaType: CatalogMediaFilter;
  genre: string;
  minimumRating: number;
  yearFrom: number | null;
  sortBy: CatalogSort;
}

export interface CatalogPage {
  items: Content[];
  pagination: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
    hasPrevious: boolean;
    hasNext: boolean;
  };
  filters: {
    genres: string[];
  };
}

export interface RunCandidate {
  id: DatabaseId;
  runId: DatabaseId;
  contentId: DatabaseId;
  sourceRank: number | null;
  relevanceScore: number | null;
  criticScore: number | null;
  finalScore: number | null;
  status: CandidateStatus;
  finalRank: number | null;
  decisionReason: string | null;
  explanation: string | null;
  metadataSnapshot: Record<string, unknown>;
  createdAt: string;
  content: Content;
}

export type AgentKey = 'profiling' | 'retrieval' | 'ranking' | 'explanation';

export interface AgentStep {
  key: AgentKey;
  name: string;
  activity: string;
  status: AgentExecutionStatus;
}

export interface AgentExecution {
  id: DatabaseId;
  runId: DatabaseId;
  agentType: string;
  sequenceNo: number;
  status: AgentExecutionStatus;
  inputSnapshot: Record<string, unknown>;
  outputSnapshot: Record<string, unknown>;
  durationMs: number | null;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface Interaction {
  id: DatabaseId;
  userId: DatabaseId;
  contentId: DatabaseId;
  sourceCandidateId: DatabaseId | null;
  interactionType: InteractionType;
  rating: number | null;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface RecommendationResponse {
  conversationId: DatabaseId;
  request: RecommendationRequestRecord;
  run: RecommendationRun;
  assistantMessage: ChatMessage;
  candidates: RunCandidate[];
  detectedPreferences: UserPreference[];
  agentExecutions: AgentExecution[];
}

export type TrendPeriod = 'day' | 'week' | 'month';

export interface GenreRecommendationTrend {
  genreName: string;
  recommendationCount: number;
}

export interface ContentRecommendationTrend {
  content: Content;
  recommendationCount: number;
}

export interface RecommendationTrends {
  period: TrendPeriod;
  totalRecommendations: number;
  genreTrends: GenreRecommendationTrend[];
  contentTrends: ContentRecommendationTrend[];
  generatedAt: string;
}

export interface AppBootstrap {
  user: AppUser;
  semanticProfile: UserSemanticProfile;
  preferences: UserPreference[];
  conversations: Conversation[];
  messages: ChatMessage[];
  interactions: Interaction[];
}

export type AppView =
  | 'login'
  | 'register'
  | 'recommendations'
  | 'catalog'
  | 'trends'
  | 'upcoming'
  | 'saved'
  | 'analytics'
  | 'profile';
