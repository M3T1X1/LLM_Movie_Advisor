import { beforeEach, describe, expect, it, vi } from 'vitest';
import { demoCatalogContent } from '../data/mockData';

describe('mock API service', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv('VITE_USE_MOCK_API', 'true');
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
});
