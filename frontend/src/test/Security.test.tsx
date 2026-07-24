import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ChatInterface } from '../components/ChatInterface';
import { CatalogView } from '../components/CatalogView';
import { ConversationManager } from '../components/ConversationManager';
import { LoginView } from '../components/LoginView';
import { MovieDetailModal } from '../components/MovieDetailModal';
import { ProfileView } from '../components/ProfileView';
import { RecommendationCard } from '../components/RecommendationCard';
import {
  demoCandidates,
  demoCatalogContent,
  demoConversations,
  demoPreferences,
  demoProfile,
  demoUser,
  initialAgentSteps,
} from './fixtures/mockData';

const xssPayload = '<img src=x onerror="window.__xssTriggered=true"><script>window.__xssTriggered=true</script>';

function expectPayloadToRemainText(container: HTMLElement) {
  expect(container.textContent).toContain(xssPayload);
  expect(container.querySelector('script')).toBeNull();
  expect(container.querySelector('img[src="x"]')).toBeNull();
  expect(container.querySelector('[onerror]')).toBeNull();
  expect((window as typeof window & { __xssTriggered?: boolean }).__xssTriggered).toBeUndefined();
}

describe('XSS protections', () => {
  it('renders untrusted chat messages as text instead of HTML', () => {
    const { container } = render(
      <ChatInterface
        messages={[{
          id: 'xss-message',
          conversationId: '1',
          role: 'assistant',
          content: xssPayload,
          sequenceNo: 1,
          createdAt: new Date().toISOString(),
        }]}
        agentSteps={initialAgentSteps}
        isProcessing={false}
        onSubmit={vi.fn()}
      />,
    );
    expectPayloadToRemainText(container);
  });

  it('does not execute stored XSS from profile fields or preferences', () => {
    const maliciousPreference = { ...demoPreferences[0], id: 'xss', preferenceValue: xssPayload };
    const { container } = render(
      <ProfileView
        user={{ ...demoUser, username: xssPayload }}
        semanticProfile={{ ...demoProfile, semanticSummary: xssPayload }}
        preferences={[maliciousPreference]}
        conversations={demoConversations}
        savedCount={0}
        watchedCount={0}
        onUpdateUser={vi.fn()}
      />,
    );
    expectPayloadToRemainText(container);
    expect(container.querySelectorAll('script')).toHaveLength(0);
  });

  it('escapes XSS payloads in TMDB content metadata', () => {
    const content = {
      ...demoCandidates[0].content,
      title: xssPayload,
      originalTitle: xssPayload,
      overview: xssPayload,
      posterPath: null,
      metadata: { ...demoCandidates[0].content.metadata, backdropPath: undefined },
    };
    const { container } = render(
      <MovieDetailModal
        content={content}
        recommendation={null}
        isWatchlisted={false}
        isWatched={false}
        onClose={vi.fn()}
        onWatchlist={vi.fn()}
        onMarkWatched={vi.fn()}
      />,
    );
    expectPayloadToRemainText(container);
  });

  it('escapes an AI-generated explanation instead of interpreting it as markup', () => {
    const candidate = {
      ...demoCandidates[0],
      explanation: xssPayload,
      content: { ...demoCandidates[0].content, posterPath: null },
    };
    const { container } = render(
      <RecommendationCard
        candidate={candidate}
        index={0}
        isWatchlisted={false}
        isWatched={false}
        onOpen={vi.fn()}
        onWatchlist={vi.fn()}
        onMarkWatched={vi.fn()}
      />,
    );
    expectPayloadToRemainText(container);
  });

  it('keeps malicious-looking authentication input inside the input value', async () => {
    const user = userEvent.setup();
    const { container } = render(
      <LoginView onLogin={vi.fn()} onRegister={vi.fn()} />,
    );
    const email = screen.getByLabelText('Adres e-mail');
    await user.type(email, xssPayload);
    expect(email).toHaveValue(xssPayload);
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('[onerror]')).toBeNull();
  });

  it('keeps poster paths under the trusted TMDB image origin', () => {
    const candidate = {
      ...demoCandidates[0],
      content: { ...demoCandidates[0].content, posterPath: 'javascript:alert(1)' },
    };
    render(
      <RecommendationCard
        candidate={candidate}
        index={0}
        isWatchlisted={false}
        isWatched={false}
        onOpen={vi.fn()}
        onWatchlist={vi.fn()}
        onMarkWatched={vi.fn()}
      />,
    );
    expect(screen.getByRole('img', { name: /Plakat:/ }).getAttribute('src')).toMatch(
      /^https:\/\/image\.tmdb\.org\/t\/p\/w780/,
    );
  });

  it('escapes stored XSS in conversation titles and accessible labels', () => {
    const { container } = render(
      <ConversationManager
        conversations={[{
          ...demoConversations[0],
          title: xssPayload,
        }]}
        currentConversationId={demoConversations[0].id}
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expectPayloadToRemainText(container);
  });

  it('escapes catalog titles, genres and backend error messages', () => {
    const maliciousContent = {
      ...demoCatalogContent[0],
      title: xssPayload,
      posterPath: null,
    };
    const { container } = render(
      <CatalogView
        content={[maliciousContent]}
        genres={[xssPayload]}
        pagination={{
          page: 1,
          pageSize: 20,
          totalItems: 1,
          totalPages: 1,
          hasPrevious: false,
          hasNext: false,
        }}
        query={{
          page: 1,
          pageSize: 20,
          search: '',
          mediaType: 'all',
          genre: 'all',
          minimumRating: 0,
          yearFrom: null,
          sortBy: 'popularity',
        }}
        isLoading={false}
        error={xssPayload}
        onQueryChange={vi.fn()}
        watchlistedContentIds={[]}
        watchedContentIds={[]}
        onOpen={vi.fn()}
        onWatchlist={vi.fn()}
        onMarkWatched={vi.fn()}
      />,
    );

    expect(container.textContent).toContain(xssPayload);
    expect(container.querySelectorAll('script')).toHaveLength(0);
    expect(container.querySelector('[onerror]')).toBeNull();
    expect((window as typeof window & { __xssTriggered?: boolean }).__xssTriggered).toBeUndefined();
  });
});
