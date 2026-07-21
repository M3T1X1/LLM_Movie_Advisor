# Kontekst projektu — LLM Movie Advisor / Scene AI

Ten dokument przechowuje najważniejsze ustalenia projektowe, aby można było kontynuować pracę
w nowej rozmowie Codexa lub na innym komputerze bez odtwarzania całej historii projektu.

## 1. Cel projektu

Tematem pracy inżynierskiej jest:

> Platforma rekomendująca filmy i seriale z wykorzystaniem agentów opartych na dużych modelach
> językowych.

Aplikacja ma ograniczać przeciążenie informacyjne i paraliż decyzyjny. Użytkownik nie wybiera
wyłącznie prostych filtrów gatunkowych, lecz rozmawia z systemem i opisuje między innymi:

- aktualny nastrój,
- oczekiwany klimat,
- motywy i typ historii,
- ograniczenia, np. brak happy endu,
- preferencje i rzeczy, których chce unikać.

System wieloagentowy analizuje rozmowę, wyszukuje treści, szereguje kandydatów i przedstawia
rekomendacje wraz z naturalnym wyjaśnieniem.

Pełny opis tematu znajduje się w `praca_temat_poprawiony.pdf`.

## 2. Źródła prawdy

Najważniejsze materiały projektowe:

- `praca_temat_poprawiony.pdf` — zakres i docelowa architektura pracy,
- `przydatne/PostgreSQL_ERD.png` — relacje i encje bazy danych,
- `przydatne/postgresql_recommendation_platform_schema.sql` — dokładny fizyczny schemat
  PostgreSQL,
- `przydatne/reddis_streszczenie.png` — plan użycia Redis.

Diagram ERD oraz skrypt SQL są traktowane jako niezmienne źródła prawdy. Nie należy zmieniać ich
bez jednoznacznej decyzji użytkownika.

Skrypt SQL jest dokładnym kontraktem implementacyjnym nazw tabel, kolumn, enumów, ograniczeń i
indeksów. Diagram służy przede wszystkim do kontroli relacji i krotności.

Znane różnice pomiędzy diagramem a skryptem:

- diagram używa nazwy `USER`, a skrypt `app_user`,
- diagram nie pokazuje `password_hash`, który występuje w skrypcie,
- diagram pokazuje `constraints`, a skrypt używa `constraints_data`.

Przy implementacji fizycznej bazy należy stosować nazwy ze skryptu SQL.

## 3. Docelowy stos technologiczny

Zgodnie z tematem pracy docelowo mają zostać użyte:

- frontend: React, TypeScript, Tailwind CSS i Vite,
- backend: Python i Django,
- trwała baza danych: PostgreSQL,
- cache i krótkotrwały stan: Redis,
- orkiestracja agentów: LangGraph i LangChain,
- lokalny silnik LLM: Ollama,
- model wskazany w dokumencie pracy: Llama 4 8B,
- źródło metadanych filmowych i grafik: TMDB API.

Aktualnie zaimplementowany jest przede wszystkim frontend. Integracja z PostgreSQL, Redis, TMDB
API oraz systemem LLM jest zaplanowana na później.

## 4. Czterech agentów systemu

System ma składać się z czterech logicznych ról:

1. Agent Profilowania i Kontekstu
   - analizuje aktualne zapytanie, historię rozmów i profil użytkownika,
   - wykrywa nastrój, motywy, ograniczenia i preferencje.
2. Agent Pozyskiwania Danych
   - konstruuje zapytania do TMDB,
   - pobiera kandydatów oraz ich metadane.
3. Agent Rankingu i Krytyki
   - porównuje kandydatów z profilem użytkownika,
   - odrzuca niedopasowane tytuły i ustala ranking.
4. Agent Wyjaśnień i Interakcji
   - tworzy naturalną odpowiedź,
   - wyjaśnia, dlaczego konkretne tytuły pasują do prośby użytkownika.

Frontend posiada już wizualizację statusu tych czterech etapów.

## 5. Model danych wynikający z ERD

Główne encje:

- `app_user`,
- `user_profile`,
- `user_preference`,
- `conversation`,
- `message`,
- `recommendation_request`,
- `recommendation_run`,
- `content`,
- `genre`,
- `content_genre`,
- `run_candidate`,
- `interaction`,
- `agent_execution`.

Ważne zasady odwzorowania we frontendzie:

- identyfikatory PostgreSQL `BIGINT` są reprezentowane w TypeScript jako `string`,
- `content.id` jest lokalnym ID rekordu, a `content.tmdb_id` jest identyfikatorem TMDB,
- typ treści przyjmuje tylko `movie` lub `tv`,
- wynik, ranking, uzasadnienie i wyjaśnienie należą do `RunCandidate`, nie do `Content`,
- `source_candidate_id` w interakcji jest opcjonalny, ponieważ akcja może pochodzić z katalogu,
- wartość `rating` może wystąpić tylko dla interakcji typu `rated`,
- gatunki są oddzielnymi encjami połączonymi z treścią relacją wiele-do-wielu,
- profil semantyczny jest oddzielony od znormalizowanych preferencji użytkownika.

Enum `interaction_type_enum` zawiera wyłącznie:

- `details_opened`,
- `liked`,
- `disliked`,
- `watchlisted`,
- `watched`,
- `rated`.

Nie należy dodawać we frontendzie lub backendzie typów interakcji spoza tego enuma bez zmiany
uzgodnionego schematu.

## 6. Ustalenia dotyczące preferencji użytkownika

Preferencje mają być analizowane po każdej rozmowie, ale pojedyncza zachcianka nie może
nadpisywać długoterminowego profilu.

Należy rozdzielić:

- bieżący kontekst, np. „dzisiaj chcę komedię”,
- trwały gust, np. wielokrotnie wybierane horrory.

Przykład: jeżeli użytkownik 50 razy wybierał horror, a raz poprosił o komedię, komedia może być
ważna dla bieżącej rekomendacji, ale nie może automatycznie stać się jego dominującym gatunkiem.

Docelowa logika:

- każda rozmowa dostarcza kolejnego sygnału,
- powtarzające się sygnały stopniowo zwiększają `weight` i `confidence`,
- pojedynczy sygnał ma niewielki wpływ na długoterminowy profil,
- jawna deklaracja użytkownika ma większą wagę niż niejawna obserwacja,
- aktualny nastrój jest przede wszystkim kontekstem `recommendation_request`,
- starsze preferencje mogą stopniowo tracić znaczenie,
- Agent Profilowania analizuje historię, a nie tylko ostatnią wiadomość,
- `user_profile.version` powinien rosnąć po przebudowie profilu,
- `last_rebuilt_at` powinno wskazywać ostatnią przebudowę.

Obliczanie wag należy do backendu i Agenta Profilowania. Frontend ma jedynie wyświetlać
preferencje otrzymane z backendu.

## 7. Aktualny stan frontendu

Frontend znajduje się w katalogu `frontend/` i używa komponentów funkcyjnych, hooków oraz
`SessionContext`.

Najważniejsze moduły:

- `frontend/src/App.tsx` — główna nawigacja i przepływ aplikacji,
- `frontend/src/types/index.ts` — typy odwzorowujące ERD,
- `frontend/src/context/SessionContext.tsx` — tymczasowy stan użytkownika i sesji,
- `frontend/src/services/api.ts` — przygotowana warstwa komunikacji z Django,
- `frontend/src/data/mockData.ts` — dane demonstracyjne,
- `frontend/src/components/ChatInterface.tsx` — rozmowa,
- `frontend/src/components/RecommendationCard.tsx` — rekomendacje,
- `frontend/src/components/MovieDetailModal.tsx` — szczegóły filmu lub serialu,
- `frontend/src/components/CatalogView.tsx` — katalog i filtry,
- `frontend/src/components/AnalyticsView.tsx` — analityka użytkownika,
- `frontend/src/components/ProfileView.tsx` — profil i preferencje,
- `frontend/src/components/Navbar.tsx` — nawigacja.

### Aktualne zakładki

Po lewej stronie navbara:

- `System rekomendacji`,
- `Baza filmów i seriali`.

Obok danych użytkownika:

- `Moja lista`,
- `Analiza`,
- `Profil`.

Zakładka `Historia` została usunięta. Ostatnie rozmowy są prezentowane w profilu użytkownika.

### System rekomendacji

- Czat jest główną częścią strony.
- Po prawej stronie znajdują się trzy rekomendacje.
- Po każdej udanej rozmowie rekomendacje muszą zostać zastąpione tytułami zwróconymi przez
  backend i system LLM.
- Aktualnie mock API zwraca zawsze te same trzy pozycje, dlatego wizualnie się nie zmieniają.
- Frontend jest już przygotowany do aktualizacji przez
  `setRecommendations(result.response.candidates)`.
- Każda rekomendacja może zawierać procent dopasowania i sekcję „Dlaczego ten tytuł?”.

### Baza filmów i seriali

- Zawiera filmy i seriale oraz wyszukiwanie, filtrowanie i sortowanie.
- Kliknięcie plakatu lub informacji o tytule otwiera szczegóły treści.
- Widok szczegółów otwarty z katalogu nie pokazuje procentu dopasowania ani wyjaśnienia AI,
  ponieważ treść nie pochodzi z konkretnej rekomendacji.
- Widok szczegółów otwarty z rekomendacji nadal pokazuje dopasowanie i wyjaśnienie.

### Szczegóły filmu lub serialu

Widok zawiera:

- tytuł i tytuł oryginalny,
- rok, czas trwania i kategorię wiekową,
- opis,
- ocenę TMDB,
- reżysera, gatunki i dostępność,
- możliwość zapisania i oznaczenia jako obejrzany.

Zgodnie z wcześniejszą decyzją widok nie zawiera:

- przycisku „Zobacz zwiastun”,
- obsady.

### Zapisano i obejrzano

- Ponowne kliknięcie aktywnego oznaczenia cofa je.
- Zaznaczenie tworzy rekord `interaction` typu `watchlisted` albo `watched`.
- Odznaczenie usuwa odpowiedni rekord zamiast tworzyć nowy typ zdarzenia spoza ERD.
- Akcje są dostępne w rekomendacjach, katalogu, szczegółach i na stronie „Moja lista”.

### Profil

Profil prezentuje:

- nazwę użytkownika i e-mail,
- zapisane i obejrzane tytuły,
- liczbę rozmów,
- ulubione gatunki,
- pozytywne i negatywne preferencje,
- podsumowanie semantyczne,
- ostatnią aktywność.

### Analiza

Zakładka posiada dwa tryby:

- dashboard z kilkoma wykresami,
- dużą interaktywną mapę gustu.

Wykresy wykorzystują dane z interakcji `watched`, treści i gatunków. Kolory są zróżnicowane,
ale zachowują spójną chłodną paletę pasującą do ciemnego interfejsu.

## 8. Aktualne dane i integracja API

Frontend domyślnie korzysta z mock API:

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCK_API=true
```

Planowany kontrakt endpointów:

- `GET /api/contents/`,
- `POST /api/recommendation-requests/`,
- `POST /api/interactions/`,
- `DELETE /api/interactions/:id/`.

Żądania używają sesyjnych cookies Django i nagłówka `X-CSRFToken`.

Przed integracją należy jednoznacznie ustalić format JSON. Aktualnie żądania używają `snake_case`,
natomiast typy odpowiedzi frontendu korzystają z `camelCase`. Backend musi zwracać camelCase albo
frontend musi otrzymać warstwę mapującą DTO.

Metadane i ścieżki plakatów są obecnie demonstracyjne. Grafiki są składane z adresu CDN TMDB.
Docelowe dane powinny pochodzić z TMDB API przez backend lub warstwę agentową.

## 9. Znane ograniczenia i przyszłe poprawki

### Backend i baza

- Django jest obecnie podstawowym szkieletem projektu.
- `app/settings.py` nadal używa SQLite.
- Nie ma jeszcze modeli Django odpowiadających ERD.
- Nie ma migracji aplikacyjnych ani endpointów API.
- Nie ma jeszcze konfiguracji PostgreSQL ani własnego modelu użytkownika.
- `SECRET_KEY` jest wartością deweloperską wpisaną w pliku i przed wdrożeniem musi trafić do
  zmiennej środowiskowej.

### Integracje z PDF-a

Nie zaimplementowano jeszcze:

- Redis,
- LangGraph,
- LangChain,
- Ollama i modelu LLM,
- komunikacji z TMDB API,
- właściwego systemu ważenia preferencji.

### Interakcje

Frontend tworzy obecnie lokalny identyfikator interakcji i nie zapisuje ID zwróconego przez
przyszły backend. Po podłączeniu API trzeba:

1. odebrać utworzony rekord `Interaction` z `POST /api/interactions/`,
2. zastąpić lokalny identyfikator identyfikatorem z PostgreSQL,
3. dopiero tego ID używać przy `DELETE /api/interactions/:id/`.

Bez tej poprawki odznaczanie może działać lokalnie, ale przyszły backend może otrzymać
nieistniejące ID.

### Stan użytkownika

- Stan jest tymczasowo przechowywany w `localStorage`.
- Aktywna rozmowa ma obecnie stałe ID `1`.
- Profil, rozmowy i interakcje nie są jeszcze pobierane z backendu.
- Docelowo trwałe dane mają trafić do PostgreSQL, a stan aktywnej sesji i cache do Redis.

## 10. Zasady dalszej pracy dla Codexa

Podczas kontynuowania projektu:

1. Najpierw przeczytaj ten dokument, PDF, skrypt SQL i diagram ERD.
2. Nie zmieniaj diagramu ani skryptu SQL bez wyraźnej zgody użytkownika.
3. Zachowuj rozdzielenie `Content` i `RunCandidate`.
4. Nie dodawaj pól lub enumów sprzecznych ze schematem.
5. Frontend rozwijaj w React + TypeScript + Tailwind CSS.
6. Używaj komponentów funkcyjnych i hooków.
7. Zachowuj ciemny, responsywny interfejs VOD.
8. Czat ma pozostać głównym elementem systemu rekomendacji.
9. Wyjaśnienia AI i procent dopasowania pokazuj tylko dla rekomendacji.
10. Nie implementuj połączenia bazy lub LLM bez wyraźnego polecenia — były to dotąd zadania na
    późniejszy etap.
11. Po każdej zmianie frontendu uruchom build i lint.
12. Nie modyfikuj niezwiązanych zmian użytkownika w repozytorium.

## 11. Uruchomienie na nowym komputerze

### Backend Django

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py runserver
```

Na Windows aktywacja środowiska:

```powershell
.venv\Scripts\activate
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```

Frontend działa domyślnie pod `http://localhost:5173`, a Django pod
`http://localhost:8000`.

Wymagania środowiska:

- zalecany Python 3.13,
- Node.js 20.19 lub nowszy.

## 12. Weryfikacja zmian

Frontend:

```bash
cd frontend
npm run build
npm run lint
```

Backend:

```bash
python manage.py check
```

Kontrola zmian Git:

```bash
git diff --check
git status --short
```

W trakcie ostatniej pełnej kontroli frontend przechodził build i lint, Django przechodziło
`manage.py check`, a repozytorium było czyste przed dodaniem tego dokumentu.
