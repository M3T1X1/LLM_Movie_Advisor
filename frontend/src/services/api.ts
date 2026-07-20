import { demoMovies } from '../data/mockData';
import type { RecommendationResponse } from '../types';

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

export async function requestRecommendations(query: string): Promise<RecommendationResponse> {
  if (USE_MOCK_API) {
    await wait(900);
    return {
      message:
        'Znalazłem trzy historie, które stawiają na psychologiczne napięcie, nieoczywiste zwroty i finały zostające w głowie. Najmocniejsze dopasowanie to „Zaginiona dziewczyna”.',
      recommendations: demoMovies,
      detectedPreferences: ['Mroczny klimat', 'Niejednoznaczne zakończenia', 'Twist fabularny'],
    };
  }

  const response = await fetch(`${API_BASE_URL}/agents/recommendations/`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(`Backend zwrócił kod ${response.status}.`);
  }

  return response.json() as Promise<RecommendationResponse>;
}

export async function updateMovieState(
  movieId: number,
  state: 'saved' | 'watched',
  enabled: boolean,
) {
  if (USE_MOCK_API) return;

  const response = await fetch(`${API_BASE_URL}/profile/movies/${movieId}/`, {
    method: 'PATCH',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ [state]: enabled }),
  });

  if (!response.ok) {
    throw new Error(`Nie udało się zaktualizować filmu (${response.status}).`);
  }
}
