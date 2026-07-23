import { describe, expect, it, vi } from 'vitest';
import {
  createConversation,
  createInteraction,
  createMessage,
  deleteConversation,
  getBootstrap,
  getCatalogContent,
  getContentByIds,
  getRecommendationTrends,
  getUpcomingReleases,
  login,
  register,
  renameConversation,
  updateProfile,
} from '../services/api';
import { demoCatalogContent, demoUpcomingReleases } from './fixtures/mockData';

describe('backend API service', () => {
  it('loads the authenticated application snapshot', async () => {
    const snapshot = await getBootstrap();

    expect(snapshot.user.username).toBe('kacper');
    expect(snapshot.conversations.length).toBeGreaterThan(0);
    expect(snapshot.preferences.length).toBeGreaterThan(0);
  });

  it('loads catalog, upcoming releases and trend periods from backend', async () => {
    await expect(getCatalogContent()).resolves.toMatchObject({
      items: demoCatalogContent,
      pagination: {
        page: 1,
        pageSize: 20,
        totalItems: demoCatalogContent.length,
      },
    });
    await expect(getUpcomingReleases()).resolves.toHaveLength(demoUpcomingReleases.length);
    await expect(getRecommendationTrends('week')).resolves.toMatchObject({ period: 'week' });
  });

  it('initializes CSRF before login and registration', async () => {
    const fetchMock = vi.mocked(fetch);

    await login('user@example.com', 'StrongPassword123!');
    await register('new-user', 'new@example.com', 'StrongPassword123!');

    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      '/api/auth/csrf/',
      '/api/auth/login/',
      '/api/auth/csrf/',
      '/api/auth/register/',
    ]);
  });

  it('maps profile and conversation operations to persistent endpoints', async () => {
    const updatedUser = await updateProfile({
      username: 'nowa-nazwa',
      email: 'new@example.com',
    });
    const conversation = await createConversation();
    const renamed = await renameConversation(conversation.id, 'Nowy tytuł');
    const message = await createMessage(conversation.id, 'Trwała wiadomość');
    await deleteConversation(conversation.id);

    expect(updatedUser.username).toBe('nowa-nazwa');
    expect(renamed.title).toBe('Nowy tytuł');
    expect(message.content).toBe('Trwała wiadomość');
  });

  it('validates ratings before sending a request', async () => {
    await expect(createInteraction('101', null, 'rated')).rejects.toThrow(
      'oceny od 0 do 10',
    );
    await expect(createInteraction('101', null, 'rated', 11)).rejects.toThrow(
      'oceny od 0 do 10',
    );
    await expect(createInteraction('101', null, 'rated', 8)).resolves.toMatchObject({
      rating: 8,
    });
  });

  it('sends snake_case interaction DTO expected by Django', async () => {
    const fetchMock = vi.mocked(fetch);

    await createInteraction('101', '7', 'watchlisted');

    const [, options] = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(JSON.parse(String(options?.body))).toEqual({
      content_id: '101',
      source_candidate_id: '7',
      interaction_type: 'watchlisted',
      rating: null,
      metadata: {},
    });
  });

  it('surfaces backend detail and status through ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Authentication required.' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    await expect(getBootstrap()).rejects.toMatchObject({
      message: 'Authentication required.',
      status: 401,
    });
  });

  it('uses Polish upcoming release query parameters', async () => {
    const fetchMock = vi.mocked(fetch);

    await getUpcomingReleases();

    expect(String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1]?.[0])).toBe(
      '/api/contents/upcoming/?language=pl-PL&region=PL',
    );
  });

  it('maps catalog pagination, filters and sorting to query parameters', async () => {
    const fetchMock = vi.mocked(fetch);

    await getCatalogContent({
      page: 3,
      pageSize: 20,
      search: 'diuna',
      mediaType: 'movie',
      genre: 'Science Fiction',
      minimumRating: 8,
      yearFrom: 2020,
      sortBy: 'rating',
    });

    const requestedUrl = new URL(
      String(fetchMock.mock.calls[fetchMock.mock.calls.length - 1]?.[0]),
      'http://localhost',
    );
    expect(requestedUrl.pathname).toBe('/api/contents/');
    expect(Object.fromEntries(requestedUrl.searchParams)).toEqual({
      page: '3',
      page_size: '20',
      sort: 'rating',
      q: 'diuna',
      media_type: 'movie',
      genre: 'Science Fiction',
      min_rating: '8',
      year_from: '2020',
    });
  });

  it('loads only selected content records for saved and analytics views', async () => {
    const selected = await getContentByIds([
      demoCatalogContent[0].id,
      demoCatalogContent[2].id,
      demoCatalogContent[0].id,
    ]);

    expect(selected.map((item) => item.id)).toEqual([
      demoCatalogContent[0].id,
      demoCatalogContent[2].id,
    ]);
  });
});
