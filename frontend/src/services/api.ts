import {
  demoAgentExecutions,
  demoCatalogContent,
  demoCandidates,
  demoPreferences,
  demoRequest,
  demoRun,
} from '../data/mockData';
import type {
  DatabaseId,
  ChatMessage,
  Content,
  InteractionType,
  RecommendationResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== 'false';

function getCookie(name: string) {
  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
}

function wait(duration: number) {
  return new Promise((resolve) => window.setTimeout(resolve, duration));
}

export async function getCatalogContent(): Promise<Content[]> {
  if (USE_MOCK_API) return demoCatalogContent;

  const response = await fetch(`${API_BASE_URL}/contents/`, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error(`Nie udało się pobrać katalogu (${response.status}).`);
  return response.json() as Promise<Content[]>;
}

export async function requestRecommendations(
  conversationId: DatabaseId,
  userMessage: ChatMessage,
): Promise<RecommendationResponse> {
  if (USE_MOCK_API) {
    await wait(900);
    return {
      conversationId,
      request: {
        ...demoRequest,
        conversationId,
        triggerMessageId: userMessage.id,
      },
      run: demoRun,
      assistantMessage: {
        id: String(Date.now()),
        conversationId,
        role: 'assistant',
        content:
          'Znalazłem trzy historie o psychologicznym napięciu, nieoczywistych zwrotach i finałach, które zostają w głowie. Najmocniejsze dopasowanie to „Zaginiona dziewczyna”.',
        sequenceNo: userMessage.sequenceNo + 1,
        createdAt: new Date().toISOString(),
      },
      candidates: demoCandidates,
      detectedPreferences: demoPreferences.filter((preference) =>
        ['mood', 'narrative'].includes(preference.preferenceType),
      ),
      agentExecutions: demoAgentExecutions,
    };
  }

  const response = await fetch(`${API_BASE_URL}/recommendation-requests/`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message: {
        id: userMessage.id,
        role: userMessage.role,
        content: userMessage.content,
        sequence_no: userMessage.sequenceNo,
      },
    }),
  });

  if (!response.ok) throw new Error(`Backend zwrócił kod ${response.status}.`);
  return response.json() as Promise<RecommendationResponse>;
}

export async function createInteraction(
  contentId: DatabaseId,
  sourceCandidateId: DatabaseId | null,
  interactionType: InteractionType,
  rating: number | null = null,
) {
  if (interactionType === 'rated' && (rating === null || rating < 0 || rating > 10)) {
    throw new Error('Interakcja rated wymaga oceny od 0 do 10.');
  }
  if (interactionType !== 'rated') rating = null;
  if (USE_MOCK_API) return;

  const response = await fetch(`${API_BASE_URL}/interactions/`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({
      content_id: contentId,
      source_candidate_id: sourceCandidateId,
      interaction_type: interactionType,
      rating,
      metadata: {},
    }),
  });

  if (!response.ok) throw new Error(`Nie udało się zapisać interakcji (${response.status}).`);
}

export async function deleteInteraction(interactionId: DatabaseId) {
  if (USE_MOCK_API) return;

  const response = await fetch(`${API_BASE_URL}/interactions/${interactionId}/`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {
      'X-CSRFToken': getCookie('csrftoken'),
    },
  });

  if (!response.ok) throw new Error(`Nie udało się usunąć interakcji (${response.status}).`);
}
