# Plany rozwoju frontendu — Scene AI

Największą wartość dadzą funkcje, które zamykają pętlę między rekomendacją, reakcją użytkownika
i kolejnymi wynikami systemu.

## 1. Lubię, nie lubię i oceń

Schemat PostgreSQL już obsługuje interakcje `liked`, `disliked` i `rated`, ale nie są one jeszcze
dostępne w interfejsie. Użytkownik powinien móc:

- polubić tytuł,
- oznaczyć tytuł jako niedopasowany,
- wystawić ocenę od 0 do 10,
- cofnąć wcześniejszą reakcję.

Informacje te powinny być przekazywane do backendu i wpływać na profil oraz przyszłe
rekomendacje.

## 2. Doprecyzowywanie rekomendacji w rozmowie

Użytkownik powinien móc poprawiać otrzymane wyniki za pomocą kolejnych wiadomości, na przykład:

- „coś krótszego”,
- „mniej brutalne”,
- „tylko seriale”,
- „podobne do drugiej propozycji”.

System agentowy powinien zachować kontekst rozmowy i wygenerować nowy ranking zamiast
rozpoczynać cały proces od zera.

## 3. Zarządzanie rozmowami

Warto dodać:

- rozpoczynanie nowej rozmowy,
- listę poprzednich rozmów,
- kontynuowanie wybranej rozmowy,
- zmianę nazwy rozmowy,
- usuwanie rozmów.

Funkcjonalność można oprzeć na istniejących encjach `conversation` i `message`.

## 4. Więcej takich i mniej takich

Na karcie rekomendacji lub w widoku szczegółów można udostępnić szybkie akcje:

- więcej podobnych tytułów,
- mniej podobnych tytułów,
- podobny klimat, ale inny gatunek,
- podobna historia, ale krótsza,
- podobny temat, ale łagodniejszy ton.

Akcje powinny rozpoczynać kolejne żądanie rekomendacji w ramach bieżącej rozmowy.

## 5. Filtry kontekstowe podczas rozmowy

Pod czatem mogą pojawiać się dynamiczne opcje pomagające doprecyzować prośbę:

- maksymalny czas trwania,
- film lub serial,
- preferowana platforma streamingowa,
- poziom przemocy,
- tempo historii,
- rodzaj zakończenia,
- seans dla jednej osoby, pary albo rodziny.

Opcje powinny uzupełniać rozmowę, a nie zastępować naturalnego języka klasycznym formularzem.

## 6. Rozbudowa strony „Moja lista”

Listę użytkownika można podzielić na:

- zapisane,
- obejrzane,
- polubione,
- ocenione,
- ostatnio otwierane.

Przydatne będą również wyszukiwanie, sortowanie, filtrowanie oraz możliwość szybkiego
wystawienia oceny.

## 7. Wyjaśnienie wpływu profilu

Obok rekomendacji można pokazywać konkretne sygnały wykorzystane przez agentów, na przykład:

- zgodność z preferowanym klimatem,
- obecność często wybieranego gatunku,
- brak elementów, których użytkownik unika,
- podobieństwo do wcześniej polubionych tytułów,
- dopasowanie do bieżącego nastroju, a nie tylko długoterminowego profilu.

Zwiększy to przejrzystość i wyjaśnialność działania systemu.

## 8. Tryb „Niespodzianka”

System może zaproponować jeden tytuł zamiast pełnej listy. Użytkownik wybiera charakter
rekomendacji:

- bezpieczny wybór,
- coś nowego,
- wyjście poza typowy gust,
- ukryty klasyk.

## 9. Onboarding gustu

Po rejestracji użytkownik może ocenić kilka znanych filmów i seriali. Pozwoli to utworzyć
początkowy profil przed zgromadzeniem historii rozmów i interakcji.

Proces powinien być krótki, opcjonalny i umożliwiać oznaczanie tytułów jako lubianych,
nielubianych albo nieznanych.

## 10. Kontrola prywatności

Użytkownik powinien móc:

- zobaczyć, jakie informacje system zapamiętał na jego temat,
- wyczyścić historię rozmów,
- zresetować profil rekomendacyjny,
- pobrać swoje dane,
- usunąć konto i powiązane dane.

Operacje nieodwracalne powinny wymagać wyraźnego potwierdzenia i ponownego uwierzytelnienia.

## Sugerowana kolejność realizacji

1. Dodać obsługę `liked`, `disliked` i `rated`.
2. Wprowadzić wiele rozmów oraz zarządzanie historią.
3. Umożliwić doprecyzowywanie wyników w czacie.
4. Dodać akcję „Więcej takich” i jej warianty.
5. Rozbudować stronę „Moja lista”.
6. Dodać onboarding gustu.
7. Udostępnić użytkownikowi kontrolę nad historią, profilem rekomendacyjnym i prywatnością.

Najważniejszym wyróżnikiem aplikacji powinna być możliwość naturalnego poprawiania
rekomendacji. Użytkownik nie tylko otrzymuje wyniki, ale prowadzi z systemem rozmowę aż do
znalezienia odpowiedniego tytułu.
