import { vi } from 'vitest';
import type { Interaction } from '../types';
import {
  demoCatalogContent,
  demoConversations,
  demoInteractions,
  demoPreferences,
  demoProfile,
  demoRecommendationTrends,
  demoUpcomingReleases,
  demoUser,
  initialMessages,
} from './fixtures/mockData';

function json(data: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export function installApiMock() {
  let conversations = structuredClone(demoConversations);
  let messages = structuredClone(initialMessages);
  let interactions = structuredClone(demoInteractions);

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const path = new URL(url, 'http://localhost').pathname;
    const method = init?.method?.toUpperCase() ?? 'GET';
    const body = init?.body ? JSON.parse(String(init.body)) : {};

    if (path === '/api/auth/csrf/') return json({ detail: 'CSRF cookie set.' });
    if (path === '/api/auth/session/') {
      return json({ authenticated: true, user: demoUser });
    }
    if (path === '/api/auth/login/' || path === '/api/auth/register/') {
      return json({ user: demoUser }, path.endsWith('register/') ? 201 : 200);
    }
    if (path === '/api/auth/logout/') return json({ detail: 'Logged out.' });
    if (path === '/api/bootstrap/') {
      return json({
        user: demoUser,
        semanticProfile: demoProfile,
        preferences: demoPreferences,
        conversations,
        messages,
        interactions,
      });
    }
    if (path === '/api/contents/') {
      const params = new URL(url, 'http://localhost').searchParams;
      const page = Number(params.get('page') ?? 1);
      const pageSize = Number(params.get('page_size') ?? 20);
      const start = (page - 1) * pageSize;
      const selectedIds = new Set(
        (params.get('ids') ?? '').split(',').filter(Boolean),
      );
      const matchingContent = selectedIds.size
        ? demoCatalogContent.filter((item) => selectedIds.has(item.id))
        : demoCatalogContent;
      return json({
        items: matchingContent.slice(start, start + pageSize),
        pagination: {
          page,
          pageSize,
          totalItems: matchingContent.length,
          totalPages: Math.ceil(matchingContent.length / pageSize),
          hasPrevious: page > 1,
          hasNext: start + pageSize < matchingContent.length,
        },
        filters: {
          genres: Array.from(
            new Set(
              demoCatalogContent.flatMap((item) =>
                item.genres.map((genre) => genre.name),
              ),
            ),
          ).sort(),
        },
      });
    }
    if (path === '/api/contents/upcoming/') return json(demoUpcomingReleases);
    if (path === '/api/recommendation-trends/') {
      const period = new URL(url, 'http://localhost').searchParams.get('period') ?? 'day';
      return json(demoRecommendationTrends[period as keyof typeof demoRecommendationTrends]);
    }
    if (path === '/api/profile/' && method === 'PATCH') {
      return json({ user: { ...demoUser, ...body } });
    }
    if (path === '/api/conversations/' && method === 'POST') {
      const timestamp = new Date().toISOString();
      const conversation = {
        id: `conversation-${conversations.length + 1}`,
        userId: demoUser.id,
        title: null,
        createdAt: timestamp,
        updatedAt: timestamp,
      };
      conversations = [conversation, ...conversations];
      return json(conversation, 201);
    }
    const conversationMatch = path.match(/^\/api\/conversations\/([^/]+)\/$/);
    if (conversationMatch && method === 'PATCH') {
      const id = conversationMatch[1];
      const conversation = {
        ...conversations.find((item) => item.id === id)!,
        title: body.title,
        updatedAt: new Date().toISOString(),
      };
      conversations = conversations.map((item) => (item.id === id ? conversation : item));
      return json(conversation);
    }
    if (conversationMatch && method === 'DELETE') {
      conversations = conversations.filter((item) => item.id !== conversationMatch[1]);
      messages = messages.filter((item) => item.conversationId !== conversationMatch[1]);
      return json(null, 204);
    }
    const messageMatch = path.match(/^\/api\/conversations\/([^/]+)\/messages\/$/);
    if (messageMatch && method === 'POST') {
      const conversationId = messageMatch[1];
      const message = {
        id: `message-${messages.length + 1}`,
        conversationId,
        role: 'user' as const,
        content: body.content,
        sequenceNo:
          Math.max(
            0,
            ...messages
              .filter((item) => item.conversationId === conversationId)
              .map((item) => item.sequenceNo),
          ) + 1,
        createdAt: new Date().toISOString(),
      };
      messages = [...messages, message];
      return json(message, 201);
    }
    if (path === '/api/interactions/' && method === 'POST') {
      const interaction: Interaction = {
        id: `interaction-${interactions.length + 1}`,
        userId: demoUser.id,
        contentId: String(body.content_id),
        sourceCandidateId: body.source_candidate_id
          ? String(body.source_candidate_id)
          : null,
        interactionType: body.interaction_type,
        rating: body.rating,
        metadata: body.metadata ?? {},
        createdAt: new Date().toISOString(),
      };
      interactions = [...interactions, interaction];
      return json(interaction, 201);
    }
    const interactionMatch = path.match(/^\/api\/interactions\/([^/]+)\/$/);
    if (interactionMatch && method === 'DELETE') {
      interactions = interactions.filter((item) => item.id !== interactionMatch[1]);
      return json(null, 204);
    }
    return json({ detail: `Unhandled test endpoint: ${method} ${path}` }, 500);
  });

  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}
