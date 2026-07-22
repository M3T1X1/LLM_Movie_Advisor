import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { demoCatalogContent } from '../data/mockData';

describe('mock API service', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv('VITE_USE_MOCK_API', 'true');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('returns catalog content', async () => {
    const { getCatalogContent } = await import('../services/api');
    const content = await getCatalogContent();
    expect(content.map((item) => item.id)).toEqual(demoCatalogContent.map((item) => item.id));
    expect(content.map((item) => item.title)).toEqual(demoCatalogContent.map((item) => item.title));
  });

  it('returns recommendation trends for the selected period', async () => {
    const { getRecommendationTrends } = await import('../services/api');
    const daily = await getRecommendationTrends('day');
    const monthly = await getRecommendationTrends('month');

    expect(daily.period).toBe('day');
    expect(daily.genreTrends[0]?.genreName).toBe('Thriller');
    expect(daily.contentTrends[0]?.content.title).toBe('Zaginiona dziewczyna');
    expect(monthly.period).toBe('month');
    expect(monthly.contentTrends[0]?.content.title).toBe('Diuna: Część druga');
    expect(daily.contentTrends).toHaveLength(3);
    expect(
      daily.contentTrends.every(
        (item, index, items) =>
          index === 0 || items[index - 1].recommendationCount >= item.recommendationCount,
      ),
    ).toBe(true);
  });

  it('validates rated interactions', async () => {
    const { createInteraction } = await import('../services/api');
    await expect(createInteraction('101', null, 'rated')).rejects.toThrow('oceny od 0 do 10');
    await expect(createInteraction('101', null, 'rated', 11)).rejects.toThrow('oceny od 0 do 10');
    await expect(createInteraction('101', null, 'rated', 8)).resolves.toBeUndefined();
  });

  it('creates a mock recommendation response from the user message', async () => {
    vi.useFakeTimers();
    const { requestRecommendations } = await import('../services/api');
    const promise = requestRecommendations('7', {
      id: '9',
      conversationId: '7',
      role: 'user',
      content: 'Mroczny thriller',
      sequenceNo: 2,
      createdAt: new Date().toISOString(),
    });
    await vi.runAllTimersAsync();
    const response = await promise;
    expect(response.conversationId).toBe('7');
    expect(response.request.triggerMessageId).toBe('9');
    expect(response.candidates).toHaveLength(3);
  });

  it('uses the trends endpoint and exposes a backend error', async () => {
    vi.stubEnv('VITE_USE_MOCK_API', 'false');
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    vi.stubGlobal('fetch', fetchMock);
    const { getRecommendationTrends } = await import('../services/api');

    await expect(getRecommendationTrends('week')).rejects.toThrow(
      'Nie udało się pobrać trendów (503).',
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/recommendation-trends/?period=week',
      expect.objectContaining({ credentials: 'include' }),
    );
  });

  it('maps a recommendation request to the backend DTO', async () => {
    vi.stubEnv('VITE_USE_MOCK_API', 'false');
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue({}) });
    vi.stubGlobal('fetch', fetchMock);
    const { requestRecommendations } = await import('../services/api');
    const message = {
      id: 'message-9',
      conversationId: 'conversation-7',
      role: 'user' as const,
      content: 'Mroczny thriller',
      sequenceNo: 4,
      createdAt: new Date().toISOString(),
    };

    await requestRecommendations('conversation-7', message);
    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body as string)).toEqual({
      conversation_id: 'conversation-7',
      message: {
        id: 'message-9',
        role: 'user',
        content: 'Mroczny thriller',
        sequence_no: 4,
      },
    });
  });
});
