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

Polecenie `npm run dev` najpierw wykonuje cały zestaw testów, a następnie uruchamia serwer Vite
tylko wtedy, gdy wszystkie testy przejdą poprawnie. Jeśli którykolwiek test zakończy się błędem,
serwer nie zostanie uruchomiony. Sam serwer bez wstępnych testów można uruchomić poleceniem
`npm run dev:app`.

## Integracja z Django

Po wdrożeniu backendu ustaw w `.env`:

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCK_API=false
```

Frontend jest przygotowany pod kontrakt odpowiadający encjom z diagramu ERD:

- `POST /api/recommendation-requests/` — tworzy wiadomość, żądanie rekomendacji, przebieg oraz
  kandydatów; odpowiedź jest zgodna z `RecommendationResponse` w `src/types/index.ts`.
- `POST /api/interactions/` — zapisuje zdarzenie zgodne z `interaction_type_enum`, np.
  `details_opened`, `watchlisted` albo `watched`.
- `DELETE /api/interactions/:id/` — usuwa zapisanie lub oznaczenie tytułu jako obejrzany.
- `GET /api/contents/` — zwraca katalog filmów i seriali z gatunkami oraz metadanymi TMDB.

Wywołania wysyłają cookie sesyjne i nagłówek `X-CSRFToken`, więc są przygotowane do autoryzacji
sesyjnej Django.

## Najważniejsze moduły

- `src/context/SessionContext.tsx` — użytkownik, profil semantyczny, preferencje, rozmowy, wiadomości
  i interakcje,
- `src/services/api.ts` — izolowana warstwa komunikacji z Django,
- `src/components/ChatInterface.tsx` — rozmowa i status pracy agentów,
- `src/components/RecommendationCard.tsx` — rekomendacja z wyjaśnieniem AI,
- `src/components/CatalogView.tsx` — katalog treści, wyszukiwanie, filtry i sortowanie,
- `src/components/AnalyticsView.tsx` — statystyki użytkownika, dashboard wykresów i interaktywna
  mapa gustu,
- `src/components/MovieDetailModal.tsx` — metadane treści i akcje użytkownika,
- `src/components/ProfileView.tsx` — konto, profil semantyczny i znormalizowane preferencje.

## Zgodność z ERD

- Identyfikatory `BIGINT` są reprezentowane w TypeScript jako `string`.
- `content.id` i `content.tmdb_id` są osobnymi polami (`id` i `tmdbId`).
- Typ treści przyjmuje wyłącznie wartości `movie` i `tv`.
- Wynik, pozycja i wyjaśnienie rekomendacji należą do `RunCandidate`, a nie do `Content`.
- Zapisanie i obejrzenie tworzą rekordy `Interaction`. Cofnięcie oznaczenia usuwa odpowiedni
  rekord zamiast dodawać typ zdarzenia spoza `interaction_type_enum`.
- Dane demonstracyjne zachowują strukturę relacji z diagramu, mimo że nie są jeszcze pobierane z
  PostgreSQL.
