import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { SessionProvider, useSession } from '../context/SessionContext';

const wrapper = ({ children }: { children: ReactNode }) => <SessionProvider>{children}</SessionProvider>;

describe('SessionContext', () => {
  it('updates user and persists session', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    act(() => result.current.updateUser({ username: 'nowa-nazwa' }));
    expect(result.current.user.username).toBe('nowa-nazwa');
    expect(window.localStorage.getItem('scene-ai-session-erd-v2')).toContain('nowa-nazwa');
  });

  it('adds messages with increasing sequence numbers', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    act(() => { result.current.addMessage('user', 'Pierwsza wiadomość'); });
    act(() => { result.current.addMessage('assistant', 'Druga wiadomość'); });
    const messages = result.current.messages.filter((message) => message.conversationId === '1');
    expect(messages[messages.length - 2]?.sequenceNo).toBe(2);
    expect(messages[messages.length - 1]?.sequenceNo).toBe(3);
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

  it('supports an empty conversation history', () => {
    const { result } = renderHook(() => useSession(), { wrapper });
    const conversationIds = result.current.conversations.map((conversation) => conversation.id);

    conversationIds.forEach((conversationId) => {
      act(() => result.current.deleteConversation(conversationId));
    });

    expect(result.current.conversations).toHaveLength(0);
    expect(result.current.currentConversationId).toBeNull();
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
    act(() => result.current.recordInteraction('999', null, 'rated', 11));
    expect(result.current.interactions).toHaveLength(initialCount);
  });
});
