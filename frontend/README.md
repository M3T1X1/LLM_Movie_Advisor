# Scene AI — frontend

Responsywny interfejs platformy rekomendacji filmów i seriali. Frontend korzysta z React,
TypeScript, Vite i Tailwind CSS. Domyślnie działa na danych demonstracyjnych, dzięki czemu można
uruchomić cały przepływ UI przed ukończeniem endpointów Django.

## Uruchomienie

Wymagany jest Node.js 20.19 lub nowszy.

```bash
cp .env.example .env
npm install
npm run dev
```

Aplikacja będzie dostępna pod adresem `http://localhost:5173`. Vite przekazuje zapytania z `/api`
do Django działającego na `http://localhost:8000`.

## Integracja z Django

Po wdrożeniu backendu ustaw w `.env`:

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCK_API=false
```

Frontend oczekuje dwóch endpointów:

- `POST /api/agents/recommendations/` — body: `{ "query": "..." }`; odpowiedź zgodna z typem
  `RecommendationResponse` w `src/types/index.ts`.
- `PATCH /api/profile/movies/:tmdbId/` — body: `{ "saved": true }` albo `{ "watched": true }`.

Wywołania wysyłają cookie sesyjne i nagłówek `X-CSRFToken`, więc są przygotowane do autoryzacji
sesyjnej Django.

## Najważniejsze moduły

- `src/context/SessionContext.tsx` — użytkownik, sesja, preferencje, zapisane i obejrzane tytuły,
- `src/services/api.ts` — izolowana warstwa komunikacji z Django,
- `src/components/ChatInterface.tsx` — rozmowa i status pracy agentów,
- `src/components/RecommendationCard.tsx` — rekomendacja z wyjaśnieniem AI,
- `src/components/MovieDetailModal.tsx` — metadane, obsada i akcje użytkownika,
- `src/components/UserProfileSidebar.tsx` — profil gustu i historia interakcji.
