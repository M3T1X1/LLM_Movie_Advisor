# Weryfikacja poprawek uzasadnień

6/6 scenariuszy live przeszło automatyczne kryteria (q23, q27, q46–q49). Pełne odpowiedzi: results.jsonl.

- q47: zamiast pierwszego zdania o Hill Valley odpowiedź wskazuje motyw podróży w czasie i cytuje zdanie o wehikule oraz cofnięciu się o 30 lat.
- q46: Planeta Małp przestała spełniać filtr samotności. Przyczyną było dopasowanie `alone` wewnątrz `oddalonej`. Wspólne wzorce motywów mają teraz granice słów.
- q46: jedynym kandydatem retrievalu był Avengers: Koniec gry; opis wprost mówi o samotnym dryfowaniu Iron Mana po kosmosie. To dowód obecności motywu, nie jego dominującej roli ani refleksyjności filmu. Nie uznajemy tego za rozwiązanie całej jakości semantycznej.
- Zmieniono wybór fragmentów opisu: zdania potwierdzające rozpoznane motywy mają pierwszeństwo przed początkiem opisu. Fakty pochodzą z katalogu, a modelowe parafrazy nadal przechodzą istniejącą weryfikację.
- Po tym przebiegu dodano komunikat o częściowym dopasowaniu przy zadanym nastroju; osobny test jednostkowy potwierdza jego obecność. Nie jest to klasyfikator nastroju.

Testy: 237 jednostkowych przeszło; po dodaniu dodatkowego testu komunikatu przeszło 21 testów uzasadnień. Dalsze ograniczenia: słownik motywów, kompletność opisów, znaczenie motywu dla całej fabuły i subiektywny ton filmu. Nie wykonano ponownie pełnych 50 scenariuszy.
