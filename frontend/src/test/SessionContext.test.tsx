import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { SessionProvider, useSession } from '../context/SessionContext';

const wrapper = ({ children }: { children: ReactNode }) => (
  <SessionProvider>{children}</SessionProvider>
);

async function renderAuthenticatedSession() {
  const rendered = renderHook(() => useSession(), { wrapper });
  await waitFor(() => expect(rendered.result.current.isLoading).toBe(false));
  return rendered;
}

describe('SessionContext backend integration', () => {
  it('loads user and persistent data from bootstrap API', async () => {
    const { result } = await renderAuthenticatedSession();

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.username).toBe('kacper');
    expect(result.current.currentConversationId).toBe('1');
    expect(result.current.preferences.length).toBeGreaterThan(0);
  });

  it('updates profile through backend', async () => {
    const { result } = await renderAuthenticatedSession();

    await act(() => result.current.updateUser({ username: 'nowa-nazwa' }));

    expect(result.current.user?.username).toBe('nowa-nazwa');
  });

  it('creates, renames, selects and deletes persistent conversations', async () => {
    const { result } = await renderAuthenticatedSession();
    const originalId = result.current.currentConversationId;

    await act(() => result.current.createConversation());
    const createdId = result.current.currentConversationId;
    expect(createdId).not.toBe(originalId);

    await act(() => result.current.renameConversation(createdId!, 'Wieczorne sci-fi'));
    expect(
      result.current.conversations.find((item) => item.id === createdId)?.title,
    ).toBe('Wieczorne sci-fi');

    act(() => result.current.selectConversation(originalId!));
    expect(result.current.currentConversationId).toBe(originalId);

    await act(() => result.current.deleteConversation(createdId!));
    expect(result.current.conversations.some((item) => item.id === createdId)).toBe(false);
  });

  it('persists a user message and derives the conversation title', async () => {
    const { result } = await renderAuthenticatedSession();

    await act(() => result.current.createConversation());
    const conversationId = result.current.currentConversationId!;
    await act(() => result.current.addMessage('user', 'Ambitne science fiction'));

    expect(
      result.current.messages.some(
        (message) =>
          message.conversationId === conversationId &&
          message.content === 'Ambitne science fiction',
      ),
    ).toBe(true);
    expect(
      result.current.conversations.find((item) => item.id === conversationId)?.title,
    ).toBe('Ambitne science fiction');
  });

  it('does not accept fabricated assistant messages before LLM integration', async () => {
    const { result } = await renderAuthenticatedSession();

    await expect(
      result.current.addMessage('assistant', 'Sztuczna odpowiedź'),
    ).rejects.toThrow('wyłącznie wiadomości użytkownika');
  });

  it('records and removes a watchlist interaction through backend', async () => {
    const { result } = await renderAuthenticatedSession();

    await act(() => result.current.recordInteraction('999', null, 'watchlisted'));
    expect(result.current.watchlistedContentIds).toContain('999');

    await act(() => result.current.removeInteraction('999', 'watchlisted'));
    expect(result.current.watchlistedContentIds).not.toContain('999');
  });

  it('clears all server state after logout', async () => {
    const { result } = await renderAuthenticatedSession();

    await act(() => result.current.logout());

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.conversations).toHaveLength(0);
    expect(result.current.interactions).toHaveLength(0);
  });
});
