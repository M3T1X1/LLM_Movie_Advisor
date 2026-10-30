# FilmiQ — bazowa ocena jakości, 30.10.2026

Przeprowadzono 50 scenariuszy przez HTTP na działającej aplikacji i rzeczywistym modelu. Wszystkie 50 spełniło zdefiniowane automatyczne kryteria. To nie oznacza 100% trafności rekomendacji: ręczna ocena ujawniła słabe uzasadnienia oraz częściowe dopasowanie motywu samotności w kosmosie.

## Wyniki

- 18 przypadków gatunku/liczby filmów, 4 serialowe, 6 negacji gatunków, 5 zakresów lat, 4 językowe, 8 tur rozmów (w tym obejrzane), 4 tematyczne, 1 brak wyników.
- Mediana całej odpowiedzi: **18,05 s**. P95: **22,16 s**.
- Mediany etapów: profilowanie 2,32 s; wyszukiwanie 0,08 s; ranking 9,74 s; uzasadnienia 6,36 s. Median etapów nie należy sumować jako mediany całości.
- Źródło uzasadnienia: `catalog` 30/50, `model_catalog` 15/50, `model` 3/50, `model_retry` 2/50. Nazwy pochodzą bezpośrednio z API; sam fallback nie oznacza błędu.
- Brak rekomendacji z roku 1800 zakończył się czytelnym komunikatem o braku pozycji.
- Oznaczenie dwóch rekomendacji jako obejrzanych wykluczyło je z kolejnej odpowiedzi.

## Ręczna ocena czterech przypadków tematycznych

Ocena asystenta na podstawie odpowiedzi i zapisanych opisów katalogowych, bez niezależnej weryfikacji treści filmu. Skala 0–2: trafność tematu, oparcie uzasadnienia w danych, użyteczność uzasadnienia. Jest to mała próbka, nie oznaczony benchmark całego retrievalu.

| ID | Film | Temat | Oparcie w danych | Uzasadnienie | Obserwacja |
|---|---|---:|---:|---:|---|
| q46 | Planeta Małp | 1 | 2 | 0 | Astronauci i obca planeta pasują częściowo; samotność i refleksyjność nie zostały wyjaśnione. Odpowiedź streszcza powrót załogi. |
| q47 | Powrót do przyszłości | 2 | 2 | 0 | Opis potwierdza podróż w czasie, ale odpowiedź zawiera tylko „Połowa lat 80, miasteczko Hill Valley…”. |
| q48 | Klopsiki i inne zjawiska pogodowe | 1 | 2 | 0 | Możliwa zgodność nastroju, lecz opis katastrofy i pierwsze zdanie odpowiedzi nie uzasadniają pogodnego tonu. |
| q49 | Ma frère | 2 | 2 | 1 | Zdanie o przyjaźni od dzieciństwa wiąże się z tematem, ale nie rozwija uzasadnienia wyboru. |

## Priorytety

1. **Poprawić dobór i składanie uzasadnień.** Przy q47 odpowiednie fakty są już w opisie katalogowym, ale odpowiedź wybiera nieprzydatny początek. Wymagać konkretnego związku z motywem zapytania; przy braku potwierdzenia mówić o ograniczeniu zamiast dopowiadać fakty. Kryterium kolejnej oceny: q46–q49 zawierają konkretne, poparte metadanymi wyjaśnienie albo jawne zastrzeżenie częściowego dopasowania.
2. **Rozszerzyć ocenę trafności motywów.** Przypadek q46 pokazuje, że sama obecność astronautów nie wystarcza. Przygotować oznaczone przykłady kandydatów i ocenić retrieval oddzielnie od rankingu. Obecny zestaw nie mierzy recall@k ani nDCG.
3. **Optymalizować ranking i uzasadnienia.** To najwolniejsze etapy. Najpierw zbadać ponowienia modelu (ranking: 8 przypadków), a po zmianach powtórzyć identyczny zestaw. Samo wyszukiwanie nie jest tu głównym źródłem opóźnień.

## Odtworzenie i ograniczenia

Uruchomienie: `python3 evaluation/run_quality.py --output reports/quality-next`.
Analiza: `python3 evaluation/analyze.py reports/quality-next`.
Test mechanizmu oceniania: `python3 -m unittest evaluation.test_scoring` — 3 testy przeszły.

Zestaw i skrypty znajdują się w `evaluation/`. Pełne odpowiedzi, snapshoty metadanych, nazwa modelu, wersja grafu i czasy etapów są w `live/results.jsonl`. `live/revision.txt` zapisuje HEAD lokalnego repozytorium, nie dowodzi tożsamości obrazu kontenera. `live/environment.json` identyfikuje konto testowe. Hasła i cookies nie są zapisywane. Konto i rozmowy pozostawiono do inspekcji.

Jeden przebieg, jedno konto ze stałymi preferencjami (humor i złożona fabuła dodatnio, gore ujemnie), bez porównania modeli i bez kontroli deterministyczności generacji. Cztery rozmowy mają po dwie tury. Zmiany katalogu mogą zmienić wyniki. Nie badano obciążenia współbieżnego, runtime filmu, dostępności platform, ataków na prompt ani pełnej personalizacji między kontami. Automatycznie nie sprawdzano braku halucynowanych tytułów poza kartami.

Pierwsza próba bez preferencji zwróciła 50 razy HTTP 409 i nie wywołała modelu; została zachowana w katalogu nadrzędnym jako ślad konfiguracji i wyłączona z powyższych statystyk. Właściwy przebieg znajduje się wyłącznie w `live/`.
