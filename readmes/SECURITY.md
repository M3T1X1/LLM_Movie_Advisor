# Bezpieczeństwo projektu — LLM Movie Advisor / Scene AI

Dokument opisuje najważniejsze zagrożenia, o których należy pamiętać podczas implementacji
backendu Django, integracji PostgreSQL i Redis oraz systemu wieloagentowego opartego na LLM.

## 1. Kontrola dostępu — IDOR/BOLA

Każdy endpoint musi sprawdzać, czy pobierany albo modyfikowany rekord należy do zalogowanego
użytkownika. Nie wolno ufać identyfikatorom przekazanym przez frontend.

Szczególnie chronione muszą być:

- profile użytkowników,
- rozmowy i wiadomości,
- interakcje oraz listy zapisanych i obejrzanych treści,
- żądania rekomendacji i przebiegi agentów.

Przykładowo interakcję należy pobierać razem z właścicielem:

```python
Interaction.objects.get(id=interaction_id, user=request.user)
```

Backend powinien ignorować `user_id` przesłane przez klienta i zawsze przypisywać
`request.user`.

## 2. Logowanie i hasła

Hasła muszą być obsługiwane przez mechanizmy Django, między innymi `set_password()` i
`check_password()`. Nie należy samodzielnie tworzyć ani porównywać hashy.

Należy zapewnić:

- ograniczenie liczby prób logowania,
- ochronę rejestracji przed automatycznym tworzeniem kont,
- jednorazowe i wygasające tokeny resetowania hasła,
- neutralne odpowiedzi, które nie ujawniają, czy adres e-mail istnieje,
- ponowne uwierzytelnienie przed operacjami wrażliwymi.

Więcej informacji: [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).

## 3. Bezpieczeństwo sesji

Projekt przewiduje sesyjne cookies Django. W środowisku produkcyjnym powinny zostać ustawione
między innymi:

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
```

Identyfikator sesji powinien być zmieniany po logowaniu, a sesja usuwana po wylogowaniu. Tokenów
sesyjnych nie należy przechowywać w `localStorage`. Cała aplikacja produkcyjna musi korzystać z
HTTPS.

Więcej informacji: [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

## 4. CSRF

Wszystkie operacje zmieniające dane przez `POST`, `PUT`, `PATCH` i `DELETE` muszą wymagać
prawidłowego tokenu CSRF. Metody `GET` nie mogą zmieniać danych. Nie należy wyłączać ochrony za
pomocą `@csrf_exempt` tylko po to, aby uprościć integrację z frontendem.

Więcej informacji: [ochrona CSRF w Django](https://docs.djangoproject.com/en/6.0/ref/csrf/).

## 5. XSS i bezpieczne renderowanie

Dane użytkownika, treści z TMDB i odpowiedzi LLM są niezaufane. Nie wolno przekazywać ich do
`dangerouslySetInnerHTML`, `innerHTML`, `eval()` ani podobnych mechanizmów. Należy wdrożyć Content
Security Policy i ograniczyć dozwolone źródła skryptów, obrazów oraz połączeń.

Frontend posiada testy sprawdzające XSS w:

- wiadomościach czatu,
- profilu i preferencjach,
- metadanych TMDB,
- wyjaśnieniach AI,
- formularzach,
- ścieżkach plakatów.

Testy frontendu nie zastępują walidacji oraz zabezpieczeń backendu.

## 6. SQL Injection

Należy używać Django ORM. Surowe zapytania, `RawSQL` i `cursor.execute()` powinny być stosowane
tylko wtedy, gdy są niezbędne, zawsze z parametryzacją. Nie wolno składać SQL przez interpolację
wartości pochodzących od użytkownika.

Niebezpieczny przykład:

```python
cursor.execute(f"SELECT * FROM content WHERE title = '{title}'")
```

Bezpieczniejszy przykład:

```python
cursor.execute("SELECT * FROM content WHERE title = %s", [title])
```

Więcej informacji: [bezpieczeństwo Django](https://docs.djangoproject.com/en/6.0/topics/security/).

## 7. Walidacja danych i mass assignment

Frontend nie może decydować o właścicielu rekordu, wyniku rankingu, stanie przebiegu agenta ani
uprawnieniach użytkownika. Backend musi walidować:

- enumy zgodnie ze schematem PostgreSQL,
- ocenę w zakresie od 0 do 10,
- długości tekstów,
- typy i strukturę JSON,
- identyfikatory powiązanych rekordów,
- dozwolone pola sortowania i filtrowania.

## 8. SSRF i integracje zewnętrzne

Połączenia z TMDB i Ollamą powinny korzystać ze stałych, zaufanych adresów bazowych. Użytkownik
nie może przekazywać dowolnego URL-a do pobrania przez backend.

Należy stosować:

- allowlistę domen,
- timeouty,
- limit przekierowań,
- blokowanie dostępu do sieci wewnętrznej,
- przechowywanie klucza TMDB wyłącznie po stronie backendu.

## 9. Prompt injection i niezaufane odpowiedzi LLM

Użytkownik lub treść z zewnętrznego źródła może próbować zmienić instrukcje agenta. Prompt nie
jest mechanizmem bezpieczeństwa. Backend musi deterministycznie kontrolować:

- dane przekazywane do modelu,
- narzędzia dostępne dla każdego agenta,
- argumenty wywołań narzędzi,
- uprawnienia do odczytu i zapisu,
- dane zapisywane w bazie po odpowiedzi modelu.

Wyjście LLM należy zawsze traktować jako niezaufane dane i walidować przed dalszym użyciem.

Więcej informacji: [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/).

## 10. Nadmierne uprawnienia agentów

Każdy agent powinien mieć minimalny zakres możliwości:

- Agent Profilowania — dostęp tylko do danych bieżącego użytkownika,
- Agent Danych — wyłącznie odczyt wymaganych danych TMDB,
- Agent Rankingu — bez możliwości zarządzania kontami,
- Agent Wyjaśnień — bez prawa do dowolnego zapisu w bazie.

Operacje o istotnych skutkach powinny wymagać deterministycznej walidacji, a w razie potrzeby
potwierdzenia użytkownika.

Więcej informacji: [OWASP Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/).

## 11. Sekrety, prywatność i logi

W repozytorium i frontendzie nie wolno umieszczać:

- `SECRET_KEY`,
- klucza TMDB,
- haseł PostgreSQL i Redis,
- tokenów resetowania hasła,
- cookies i identyfikatorów sesji,
- prywatnych danych z promptów.

`SECRET_KEY` znajdujący się obecnie w `settings.py` musi przed wdrożeniem trafić do zmiennej
środowiskowej. `input_snapshot` i `output_snapshot` wykonania agentów nie powinny bez ograniczeń
przechowywać całych rozmów, tokenów ani danych uwierzytelniających.

## 12. Redis i izolacja danych

Klucze Redis muszą jednoznacznie uwzględniać użytkownika, sesję, żądanie albo przebieg:

```text
session:{user_id}:{session_id}
agent:profiling:{request_id}
agent:ranking:{run_id}
```

Należy zapewnić TTL, uwierzytelnienie Redisa, brak publicznego dostępu do portu, bezpieczną
serializację i usuwanie sesji po wylogowaniu. Błędne klucze cache mogą doprowadzić do pokazania
danych innego użytkownika.

## 13. Rate limiting i DoS

Ograniczenia należy zastosować szczególnie dla:

- logowania,
- rejestracji,
- resetowania hasła,
- wywołań LLM,
- zapytań do TMDB,
- generowania rekomendacji.

Potrzebne są limity per użytkownik oraz IP, maksymalne długości wiadomości, timeouty, ograniczenie
liczby kandydatów i blokada równoległego uruchamiania identycznych zadań. Należy również
ograniczyć maksymalny rozmiar requestu na poziomie serwera.

## 14. Nagłówki bezpieczeństwa i CORS

W produkcji należy skonfigurować:

- Content Security Policy,
- HTTPS i HSTS,
- `X-Content-Type-Options`,
- ochronę przed clickjackingiem,
- restrykcyjne `ALLOWED_HOSTS`,
- ograniczone `CSRF_TRUSTED_ORIGINS`,
- CORS wyłącznie dla zaufanych domen.

## 15. Zależności i aktualizacje

Zależności powinny mieć przypięte wersje i być regularnie aktualizowane. Pomocne polecenia:

```bash
npm audit
python -m pip list --outdated
```

Należy śledzić [poprawki bezpieczeństwa Django](https://docs.djangoproject.com/en/6.0/releases/security/)
i ostrożnie wybierać biblioteki związane z agentami oraz LLM.

## Priorytety dla tego projektu

Najwyższy priorytet mają:

1. kontrola dostępu do danych użytkowników,
2. bezpieczne sesje, logowanie i CSRF,
3. ochrona przed prompt injection i walidacja wyjść LLM,
4. izolacja danych w Redis,
5. rate limiting kosztownych wywołań LLM i TMDB,
6. bezpieczne zarządzanie sekretami i logami.
