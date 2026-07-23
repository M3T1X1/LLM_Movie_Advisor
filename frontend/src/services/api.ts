import type {
  AppBootstrap,
  AppUser,
  ChatMessage,
  Content,
  Conversation,
  DatabaseId,
  Interaction,
  InteractionType,
  RecommendationTrends,
  TrendPeriod,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function getCookie(name: string) {
  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Backend zwrócił kod ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // The status code still provides a useful fallback error.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method?.toUpperCase() ?? 'GET';
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers.set('X-CSRFToken', getCookie('csrftoken'));
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });
  return parseResponse<T>(response);
}

function jsonRequest(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export async function ensureCsrf(): Promise<void> {
  await request<{ detail: string }>('/auth/csrf/');
}

export async function getAuthSession(): Promise<{
  authenticated: boolean;
  user: AppUser | null;
}> {
  return request('/auth/session/');
}

export async function login(email: string, password: string): Promise<AppUser> {
  await ensureCsrf();
  const response = await request<{ user: AppUser }>(
    '/auth/login/',
    jsonRequest('POST', { email, password }),
  );
  return response.user;
}

export async function register(
  username: string,
  email: string,
  password: string,
): Promise<AppUser> {
  await ensureCsrf();
  const response = await request<{ user: AppUser }>(
    '/auth/register/',
    jsonRequest('POST', { username, email, password }),
  );
  return response.user;
}

export async function logout(): Promise<void> {
  await ensureCsrf();
  await request('/auth/logout/', { method: 'POST' });
}

export async function getBootstrap(): Promise<AppBootstrap> {
  return request('/bootstrap/');
}

export async function getCatalogContent(): Promise<Content[]> {
  return request('/contents/');
}

export async function getUpcomingReleases(): Promise<Content[]> {
  const params = new URLSearchParams({ language: 'pl-PL', region: 'PL' });
  return request(`/contents/upcoming/?${params}`);
}

export async function getRecommendationTrends(
  period: TrendPeriod,
): Promise<RecommendationTrends> {
  return request(`/recommendation-trends/?${new URLSearchParams({ period })}`);
}

export async function updateProfile(
  changes: Pick<AppUser, 'username' | 'email'>,
): Promise<AppUser> {
  const response = await request<{ user: AppUser }>(
    '/profile/',
    jsonRequest('PATCH', changes),
  );
  return response.user;
}

export async function createConversation(): Promise<Conversation> {
  return request('/conversations/', jsonRequest('POST', {}));
}

export async function renameConversation(
  conversationId: DatabaseId,
  title: string,
): Promise<Conversation> {
  return request(
    `/conversations/${conversationId}/`,
    jsonRequest('PATCH', { title }),
  );
}

export async function deleteConversation(conversationId: DatabaseId): Promise<void> {
  await request(`/conversations/${conversationId}/`, { method: 'DELETE' });
}

export async function createMessage(
  conversationId: DatabaseId,
  content: string,
): Promise<ChatMessage> {
  return request(
    `/conversations/${conversationId}/messages/`,
    jsonRequest('POST', { content }),
  );
}

export async function createInteraction(
  contentId: DatabaseId,
  sourceCandidateId: DatabaseId | null,
  interactionType: InteractionType,
  rating: number | null = null,
): Promise<Interaction> {
  if (interactionType === 'rated' && (rating === null || rating < 0 || rating > 10)) {
    throw new Error('Interakcja rated wymaga oceny od 0 do 10.');
  }
  return request(
    '/interactions/',
    jsonRequest('POST', {
      content_id: contentId,
      source_candidate_id: sourceCandidateId,
      interaction_type: interactionType,
      rating: interactionType === 'rated' ? rating : null,
      metadata: {},
    }),
  );
}

export async function deleteInteraction(interactionId: DatabaseId): Promise<void> {
  await request(`/interactions/${interactionId}/`, { method: 'DELETE' });
}
