import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { SessionProvider, useSession } from '../context/SessionContext';

const wrapper = ({ children }: { children: ReactNode }) => <SessionProvider>{children}</SessionProvider>;

describe('SessionContext', () => {
  it('falls back to demo data when persisted JSON is corrupted', () => {
    window.localStorage.setItem('scene-ai-session-erd-v2', '{niepoprawny-json');
    const { result } = renderHook(() => useSession(), { wrapper });

    expect(result.current.user.username).toBe('kacper');
    expect(result.current.currentConversationId).toBe('1');
    expect(result.current.conversations.length).toBeGreaterThan(0);
  });

  it('updates user and persists session', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    act(() => result.current.updateUser({ username: 'nowa-nazwa' }));
    expect(result.current.user.username).toBe('nowa-nazwa');
    expect(window.localStorage.getItem('scene-ai-session-erd-v2')).toContain('nowa-nazwa');
  });

  it('restores persisted session after remounting the provider', () => {
    const firstRender = renderHook(() => useSession(), { wrapper });
    act(() => firstRender.result.current.updateUser({ email: 'persisted@example.com' }));
    firstRender.unmount();

    const secondRender = renderHook(() => useSession(), { wrapper });
    expect(secondRender.result.current.user.email).toBe('persisted@example.com');
  });

  it('adds messages with increasing sequence numbers', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    act(() => { result.current.addMessage('user', 'Pierwsza wiadomość'); });
    act(() => { result.current.addMessage('assistant', 'Druga wiadomość'); });
    const messages = result.current.messages.filter((message) => message.conversationId === '1');
    expect(messages[messages.length - 2]?.sequenceNo).toBe(2);
    expect(messages[messages.length - 1]?.sequenceNo).toBe(3);
  });

  it('does not append the same server message twice', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    const message = {
      id: 'server-message',
      conversationId: '1',
      role: 'assistant' as const,
      content: 'Gotowa odpowiedź',
      sequenceNo: 2,
      createdAt: new Date().toISOString(),
    };

    act(() => result.current.appendMessage(message));
    act(() => result.current.appendMessage(message));
    expect(result.current.messages.filter((item) => item.id === message.id)).toHaveLength(1);
  });

  it('creates, selects, renames and deletes conversations', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    const originalConversationId = result.current.currentConversationId;

    act(() => { result.current.createConversation(); });
    const createdConversationId = result.current.currentConversationId;
    expect(createdConversationId).not.toBe(originalConversationId);
    expect(result.current.conversations.find((item) => item.id === createdConversationId)?.title).toBeNull();

    act(() => result.current.renameConversation(createdConversationId!, 'Wieczorne science fiction'));
    expect(result.current.conversations.find((item) => item.id === createdConversationId)?.title).toBe(
      'Wieczorne science fiction',
    );

    act(() => { result.current.addMessage('user', 'Pokaż ambitne science fiction'); });
    expect(result.current.messages.some((message) => message.conversationId === createdConversationId)).toBe(true);

    act(() => result.current.selectConversation(originalConversationId!));
    expect(result.current.currentConversationId).toBe(originalConversationId);

    act(() => result.current.deleteConversation(createdConversationId!));
    expect(result.current.conversations.some((item) => item.id === createdConversationId)).toBe(false);
    expect(result.current.messages.some((message) => message.conversationId === createdConversationId)).toBe(false);
  });

  it('ignores an unknown conversation and derives a new title only once', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    const originalConversationId = result.current.currentConversationId;
    act(() => result.current.selectConversation('missing-conversation'));
    expect(result.current.currentConversationId).toBe(originalConversationId);

    act(() => { result.current.createConversation(); });
    const createdId = result.current.currentConversationId;
    act(() => result.current.updateConversationFromQuery('Pierwszy prompt ustala tytuł'));
    act(() => result.current.updateConversationFromQuery('Drugi prompt nie nadpisuje tytułu'));
    expect(result.current.conversations.find((item) => item.id === createdId)?.title).toBe(
      'Pierwszy prompt ustala tytuł',
    );
  });

  it('supports an empty conversation history', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    const conversationIds = result.current.conversations.map((conversation) => conversation.id);

    conversationIds.forEach((conversationId) => {
      act(() => result.current.deleteConversation(conversationId));
    });

    expect(result.current.conversations).toHaveLength(0);
    expect(result.current.currentConversationId).toBeNull();
    expect(() => result.current.addMessage('user', 'Nie można wysłać')).toThrow(
      'Nie wybrano aktywnej rozmowy.',
    );
  });

  it('records a single watchlist state and can remove it', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    act(() => result.current.recordInteraction('999', null, 'watchlisted'));
    act(() => result.current.recordInteraction('999', null, 'watchlisted'));
    expect(result.current.interactions.filter((item) => item.contentId === '999')).toHaveLength(1);
    act(() => { result.current.removeInteraction('999', 'watchlisted'); });
    expect(result.current.watchlistedContentIds).not.toContain('999');
  });

  it('rejects rated interactions without a valid rating', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    const initialCount = result.current.interactions.length;
    act(() => result.current.recordInteraction('999', null, 'rated'));
    act(() => result.current.recordInteraction('999', null, 'rated', -1));
    act(() => result.current.recordInteraction('999', null, 'rated', 11));
    expect(result.current.interactions).toHaveLength(initialCount);

    act(() => result.current.recordInteraction('999', null, 'rated', 10));
    const rating = result.current.interactions.find(
      (item) => item.contentId === '999' && item.interactionType === 'rated',
    );
    expect(rating?.rating).toBe(10);
  });

  it('deduplicates preference groups and prevents a value from being positive and avoided', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    act(() =>
      result.current.replacePreferenceGroups({
        favoriteGenres: ['Thriller', 'Thriller'],
        positivePreferences: ['Mroczny klimat', 'Mroczny klimat'],
        avoidedPreferences: ['Mroczny klimat', 'Gore', 'Gore'],
      }),
    );

    expect(
      result.current.preferences.map((preference) => [
        preference.preferenceValue,
        preference.polarity,
      ]),
    ).toEqual([
      ['Thriller', 1],
      ['Mroczny klimat', 1],
      ['Gore', -1],
    ]);
  });
});
