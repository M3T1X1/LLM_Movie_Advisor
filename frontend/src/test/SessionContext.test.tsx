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
