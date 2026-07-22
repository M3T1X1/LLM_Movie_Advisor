# Plany rozwoju frontendu — FilmiQ AI

Dokument obejmuje wyłącznie rozwój interfejsu użytkownika w React, TypeScript i Tailwind CSS.
Nie opisuje implementacji modeli Django, bazy danych, agentów, integracji TMDB ani logiki LLM.

## Nienaruszalna zasada generowania rekomendacji

Filmy i seriale mogą zostać zarekomendowane wyłącznie po wysłaniu przez użytkownika własnego
inputu tekstowego z czatu do systemu LLM.

Frontend nie może automatycznie rozpoczynać generowania rekomendacji po:

- wejściu na stronę,
- zmianie zakładki lub filtrów,
- otwarciu szczegółów tytułu,
- zapisaniu albo oznaczeniu tytułu jako obejrzany,
- polubieniu, odrzuceniu lub ocenieniu tytułu,
- wybraniu wcześniejszej rozmowy,
- kliknięciu elementu katalogu.

Przyciski z przykładowymi promptami mogą jedynie uzupełniać pole tekstowe. Użytkownik musi
świadomie wysłać wiadomość. Dopiero wysłanie formularza czatu może wywołać żądanie
rekomendacji. Frontend wyświetla wyniki otrzymane z backendu i nie tworzy własnego rankingu.

## 1. Ulepszenie interfejsu czatu

Warto rozbudować główny element aplikacji o:

- czytelny licznik znaków,
- automatyczne dopasowanie wysokości pola tekstowego,
- lepsze stany wysyłania, oczekiwania i błędu,
- widoczny podział wiadomości użytkownika i odpowiedzi systemu,
- przewijanie do najnowszej wiadomości,
- dostępne z klawiatury wysyłanie i obsługę fokusu,
- propozycje promptów, które wyłącznie uzupełniają pole tekstowe.

## 2. Doprecyzowywanie rekomendacji przez input użytkownika

Użytkownik może poprawić otrzymane wyniki, wysyłając kolejną wiadomość, na przykład:

- „coś krótszego”,
- „mniej brutalne”,
- „tylko seriale”,
- „podobne do drugiej propozycji”.

Każde doprecyzowanie pozostaje zwykłym inputem tekstowym wysłanym przez formularz czatu.
Frontend przekazuje wiadomość do API i zastępuje aktualne rekomendacje dopiero po otrzymaniu
nowej odpowiedzi.

## 3. Zarządzanie rozmowami w interfejsie

Frontend może udostępnić:

- przycisk rozpoczęcia nowej rozmowy,
- listę poprzednich rozmów,
- przełączanie aktywnej rozmowy,
- zmianę nazwy rozmowy,
- potwierdzenie usunięcia rozmowy,
- pusty stan dla użytkownika bez historii.

Otwarcie lub utworzenie rozmowy nie generuje rekomendacji. Pierwsze wyniki pojawiają się dopiero
po wysłaniu wiadomości przez użytkownika.

## 4. Karty rekomendacji i szczegóły tytułu

Karty powinny czytelnie prezentować dane otrzymane w odpowiedzi API:

- tytuł, plakat i podstawowe metadane,
- procent dopasowania,
- pozycję w rankingu,
- wyjaśnienie „Dlaczego ten tytuł?”,
- stan zapisania i obejrzenia,
- bezpieczny fallback dla brakującego plakatu albo opisu.

Procent dopasowania i wyjaśnienie AI są widoczne wyłącznie dla tytułu pochodzącego z konkretnej
rekomendacji. Widok otwarty z katalogu nie pokazuje tych informacji.

## 5. Sugerowane doprecyzowania bez automatycznego wysyłania

Pod rekomendacją mogą znajdować się akcje opisane na przykład jako:

- „więcej podobnych”,
- „podobny klimat, inny gatunek”,
- „coś krótszego”,
- „łagodniejszy ton”.

Kliknięcie takiej akcji nie może pobierać kolejnych filmów. Powinno jedynie wpisać odpowiedni
tekst do pola czatu. Użytkownik może go zmienić i samodzielnie wysłać do LLM.

## 6. Interakcje użytkownika

Interfejs może obsługiwać istniejące typy interakcji:

- `details_opened`,
- `liked`,
- `disliked`,
- `watchlisted`,
- `watched`,
- `rated`.

Frontend odpowiada za przyciski, aktywne stany, walidację oceny od 0 do 10 oraz komunikaty
powodzenia lub błędu. Zapisanie interakcji nie może samodzielnie odświeżać rekomendacji.

## 7. Rozbudowa strony „Moja lista”

Widok można podzielić na:

- zapisane,
- obejrzane,
- polubione,
- ocenione,
- ostatnio otwierane.

Przydatne będą wyszukiwanie, sortowanie, filtrowanie, szybkie wystawienie oceny oraz czytelne
puste stany. Operacje na liście nie uruchamiają LLM.

## 8. Katalog filmów i seriali

Katalog pozostaje niezależnym widokiem do przeglądania treści i powinien oferować:

- wyszukiwanie po tytule,
- filtrowanie po typie, gatunku, roku i ocenie,
- sortowanie,
- responsywną siatkę kart,
- otwieranie szczegółów,
- zapisywanie i oznaczanie jako obejrzany.

Filtrowanie katalogu odbywa się lokalnie lub przez zwykłe API katalogowe. Nie jest rekomendacją
LLM i nie może pokazywać procentu dopasowania ani wyjaśnienia AI.

## 9. Profil i analiza aktywności

Frontend może rozwijać prezentację:

- danych konta,
- zapisanych preferencji,
- podsumowania semantycznego,
- ostatnich rozmów,
- liczby zapisanych i obejrzanych tytułów,
- wykresów aktywności i mapy gustu.

Są to widoki informacyjne. Samo ich otwarcie ani zmiana danych konta nie może generować nowych
rekomendacji.

## 10. Dostępność i responsywność

Każdy widok powinien uwzględniać:

- pełną obsługę klawiatury,
- widoczny fokus,
- poprawne etykiety i role ARIA,
- komunikaty błędów czytelne dla czytników ekranu,
- odpowiedni kontrast,
- układ mobilny, tabletowy i desktopowy,
- ograniczenie animacji zgodnie z preferencją `prefers-reduced-motion`.

## Sugerowana kolejność realizacji frontendu

1. Uporządkować stany czatu i jedno miejsce wysyłania inputu do LLM.
2. Dodać wiele rozmów i przełączanie historii bez automatycznego generowania wyników.
3. Rozbudować karty rekomendacji oraz stany ładowania, błędu i braku wyników.
4. Dodać `liked`, `disliked` i `rated` bez automatycznego odświeżania rekomendacji.
5. Rozbudować stronę „Moja lista” i katalog.
6. Udoskonalić profil, analitykę, dostępność i widoki mobilne.

Najważniejszym elementem aplikacji pozostaje rozmowa. Frontend inicjuje proces rekomendacji
wyłącznie wtedy, gdy użytkownik świadomie wysyła tekstowy input do LLM.
