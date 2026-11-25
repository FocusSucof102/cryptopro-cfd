# 🧭 PROJECT_MASTER.md — SINGLE SOURCE OF TRUTH (CRYPTO PRO CFD)
*Ostatnia pełna aktualizacja: 2026-11-26 | Architektura: 2.0 PRO+ Enterprise*

---

## 🎯 1. CEL GŁÓWNY I PROFIL BIZNESOWY
- **Cel:** W pełni autonomiczny, wysoce precyzyjny system analityczno-egzekucyjny pod handel kontraktami **BitBase Futures / CFD** oparty na płynnych danych z **Bitget USDT-Futures** (pary z obrotem 24h co najmniej 15M USDT).
- **Optymalizacja zysku:** Maksymalizacja stopy zwrotu netto w `R` po bezwzględnym odliczeniu realnego kosztu transakcyjnego: **`-0.07R` na każdą transakcję** (prowizja giełdowa + poślizg cenowy / spread).
- **Zarządzanie kapitałem:** Ogólne moduły ryzyka zachowują bazowe `1.0%` na transakcję; osobny plan BitBase w `planner_mod.py` liczy `1.5%` skonfigurowanego kapitału, bezpieczną dźwignię i margin. Żaden plan nie wysyła zleceń na giełdę. Bezpiecznik **Safe-Lock** odcina sygnały poniżej PLATINUM (>= 68%) przy obsuwie kapitału `>= 6%`.
- **Nadrzędna zasada inżynieryjna:** `PROJECT_MASTER.md` stanowi jedyne i wyłączne źródło prawdy (Single Source of Truth) o stanie projektu, badaniach, architekturze i zadaniach.

---

## 🏛️ 2. ARCHITEKTURA SYSTEMU I AKTYWNE MODUŁY
System zbudowany jest z wyspecjalizowanych modułów współpracujących pod nadzorem skryptu-dyrygenta:

| Moduł | Rola i odpowiedzialność w systemie |
| :--- | :--- |
| **`orchestrator.py`** | Nadrzędny dyrygent cyklu pracy: auto-naprawa, QA smart_verify, risk guard, audyt 1m, testy walk-forward/time-decay, sync. |
| **`crypto_pro.py`** | Główny silnik skanera, pętle w tle (Live CFD, Fast Guardian 60s, Sync 5m, Healthcheck), obsługa Telegrama. |
| **`alpha_pro_mod.py`** | Skaner par TOP-60/100, twarda czarna lista stablecoinów (`STABLECOIN_BLACKLIST`), filtry anomalii wolumenu i świec. |
| **`planner_mod.py`** | Ogólny planner oraz osobny kalkulator BitBase z SL ATR, TP 0.75R/1.5R/2.5R, ryzykiem 1.5%, dźwignią i marginem. |
| **`risk_guard_mod.py`** | Kalkulator depozytu (kapitał 200 USDT, ryzyko 1%, max DD 6%), Safe-Lock (blokada przy DD > 6%), ochrona marginu. |
| **`time_decay_mod.py`** | Krzywa przeżywalności pozycji (Survival Curve), wykrywanie degradacji zysku po czasie i reguła `TIME_DECAY_EXIT`. |
| **`smart_verify.py`** | Bramka jakości QA 5.0 PRO+: AST Scope-Guard, Docstring-Guard, Call-Guard, DevSecOps (ochrona tokenów), autotesty. |
| **`auto_repair_mod.py`** | Pętla samoleczenia: autokorekta wcięć, brakujących importów, naprawa uszkodzonych plików JSON i blokad Git. |
| **`ai_evolution_agent.py`** | Autonomiczny agent ewolucyjny: fallback modeli Gemini (`gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash`), retry 404/503. |
| **`smart_sl_mod.py`** | Dynamiczny Stop Loss: Break-Even `+0.35R` po osiągnięciu `+1.1R` zysku, trailing ATR, ochrona zysku. |
| **`meta_brain_mod.py`** | Adaptacyjne wagi neuronowe dla sygnałów (Orderflow, KNN, Lead-Lag, Regime, Red-Team, Quantum, Nash, Entropy). |
| **`nzt_cortex_mod.py`** | NZT-48 Cortex: uczenie kontrfaktyczne z odrzuconych hipotez i optymalizacja bramki decyzyjnej. |
| **`future_quantum_mod.py`**| Entropia Shannona (miękka waga punktowa) oraz twardy filtr manipulacji Whale Iceberg & Red-Team AI. |
| **`quantum_nash_mod.py`** | Teoria gier mikrostruktury: detektor polowań na zlecenia (Nash Predator Trap) i interferencja poziomów. |
| **`sniper_doctor_mod.py`** | Filtr Sniper BTC (zgodność z reżimem EMA200 1H) oraz odrzucanie knotów manipulacyjnych > 45%. |
| **`inst_orderflow_mod.py`** | Detekcja ścian zleceń przed TP1 (Orderbook Imbalance) oraz kalendarz publikacji makroekonomicznych USA. |
| **`contract_audit_mod.py`**| Audyt smart-kontraktów przez DexScreener i GoPlus Security (zabezpieczenie przed pustą odpowiedzią API). |
| **`walk_forward_mod.py`** | Rygorystyczny sędzia statystyczny: Purged Walk-Forward (70/30) oraz Monte Carlo Stress Test (100 permutacji, próg >= 85%). |
| **`web_ui_mod.py`** | Nowoczesny pulpit operatorski w przeglądarce (`/`, `/api/web_full_state`, `/api/save_risk`, audytor, skanery). |
| **`watchdog_mod.py`** | Monitor procesów 24/7 z rejestracją heartbeatów i automatycznym restartem zawieszonych pętli. |

---

## 🗄️ 3. MAPA KATALOGU ARCHIWUM (`archive/`)
Wszystkie starsze skrypty oraz rozproszone pliki dokumentacji zostały bezpiecznie przeniesione do katalogu `archive/` bez utraty danych historycznych:

### 📦 `archive/legacy_code/`
- **`collector.py`** — Pierwotny jednoplatformowy skrypt zbierający świece z Binance Futures i kalkulujący proste pozycje symulowane.
- **`scanner.py`** — Konsolowy skaner terminalowy z renderowaniem tabel tekstowych ANSI i pierwszymi alertami Telegrama.
- **`system.py`** — Zintegrowany prototyp łączący dawny backtest 30k świec z pierwszym monitorem Live i prostym fundingiem.
- **`dashboard.py`** — Pierwsza wersja interfejsu Flask i prosty bot Telegrama z wykresami QuickChart.
- **`backtest.py`** — Wczesny silnik symulacji historycznej na świecach 1H z pierwszym modelem prowizji i poślizgów.

### 📄 `archive/legacy_docs/`
- **`MASTER_HANDOFF_AI.txt`** — Notatki przekazania stanu sesji z 21.11.2026 (wyniki badań chmurowych, obostrzenia środowiska).
- **`AI_SESSION_STATE.md`** — Pierwotny rejestr badań Walk-Forward i Monte Carlo (warianty TP/SL, Pakt Obostrzeń).
- **`EVOLUTION_JOURNAL.md`** — Wczesny dziennik wywołań API Gemini zawierający kody błędów 404/503 wymagające fallbacku modeli.

---

## 🧪 4. SYNTEZA BADAŃ NAUKOWYCH I WYNIKÓW EMPIRYCZNYCH

### A. Egzaminy Walk-Forward & Monte Carlo (Próbka 6200 świec 15m, 31 par):
1. **Badanie A (Ślepy trend EMA20 > EMA50 bez AI):**
   - Wynik OOS: **`-24.75R`** | WR: `21.8%` | Monte Carlo: `0.0% pass` -> **KRYTYCZNIE OBLANY**.
2. **Badanie B (Trend + Sniper BTC + Moduły AI + stary BE +0.12R):**
   - Wynik OOS: **`-3.23R`** | WR: `52.4%` | Monte Carlo: `1.0% pass` -> **OBLANY** (BE +0.12R po prowizji -0.07R daje zaledwie +0.05R i nie kryje strat -1.07R).
3. **Badanie C (Zwycięzca Produkcyjny: Poziom 48H + Sniper BTC + Moduły AI + BE +0.35R po +1.1R):**
   - Wynik OOS: **`+4.47R` NETTO po prowizji** | WR: `66.7%` | Monte Carlo: **`96.0% pass`** | Max DD: `3.55R` -> **ZALICZONY**.
4. **Badanie D (Izolacja Modułów Mikrostruktury):**
   - **Whale Iceberg & Red-Team AI:** Przepuszcza 100% dobrych wejść (`OOS +1.93R`, `MC 100% pass`) -> **TWARDY FILTR WETO**.
   - **Nash Predator Trap:** Przepuszcza 100% dobrych wejść (`OOS +1.93R`, `MC 100% pass`) -> **TWARDY FILTR WETO**.
   - **Shannon Entropy:** Jako twardy bloker odrzucał aż 87.5% wejść -> **ZMIENIONY NA MIĘKKĄ WAGĘ W META-BRAIN (+4 / -5 pkt)**.

### B. Wnioski ze Sprintu 24H i Wdrożone Usprawnienia:
- **Fallback modeli AI:** Gemini API wymaga elastycznej ścieżki `gemini-2.5-flash` -> `gemini-2.5-flash-lite` -> `gemini-2.0-flash` z 3 próbami backoff przy błędach 404/503.
- **Twardy filtr Stablecoinów:** Wyeliminowanie par syntetycznych/stable (`BFUSD`, `USDC`, `USD1`, `RLUSD`, `FDUSD`, `DAI`, `TUSD`, `USDE`, `USDD`, `PYUSD`, `EURC`), które zanieczyszczały skany brakiem zmienności.
- **Sesja Londyńska (08:00–13:00):** Okres wysokiej manipulacji i polowań na płynność -> zaostrzenie progu o `+10 pkt` oraz wymóg zgodności z `EMA200 1H`.
- **Zabezpieczenie JSON API:** Pełna ochrona przed pustymi odpowiedziami API DexScreener/GoPlus zapobiega awariom `Expecting value: line 1 column 1`.
- **Risk Guard & Safe-Lock:** Wymuszenie dyscypliny depozytowej (kapitał 200 USDT, max ryzyko 1%, obcięcie sygnałów poniżej PLATINUM przy DD >= 6%).
- **Time Decay:** Statystyczna analiza degradacji pozycji w czasie zamyka przetrzymywane pozycje bez dynamiki, chroniąc przed kosztami funding rate.

### C. Pakiet BitBase (25.11.2026)
- **Skaner i plan:** SL skanera wynosi `1.4x ATR`, akceptowany zakres to `1.2x–1.6x ATR`, a odległość jest ograniczona do `2.2%`; zarówno skaner, jak i samodzielny kalkulator odrzucają poziomy poza tymi granicami (planner pomija kontrolę ATR, gdy ATR nie został podany). Oddzielny plan liczy ryzyko `1.5%` skonfigurowanego kapitału, `max_safe_lev = max(1, int(50 / sl_pct))`, margin oraz cele TP `0.75R / 1.5R / 2.5R` z udziałami `50% / 30% / 20%`.
- **Prezentacja i Telegram:** ANSI i statusy Telegrama używają mapowania A/GOTOWY na zielono, B/TRIGG. na żółto, C/odrzucone na czerwono. Automatyczny alert Live wymaga nowego sygnału Grupy A (`>=75%`) w limicie ceny; zawiera Entry/SL/TP1–3/LEV/MARG/ryzyko i wynik Pattern Matchera. Ręczne skanowanie z menu nadal pokazuje wyniki na żądanie.
- **Pozycje i edycje:** Powiadomienia zarządzania dotyczą tylko pozycji `OBSTAWIONE`. TP1 przesuwa monitorowany SL na Break-Even. Ostrzeżenie `PROFIT_DECAY_WARN` wymaga pozycji obstawionej i cofnięcia co najmniej `0.65R` od MFE `>=1.1R`. Komenda `/edytuj SYMBOL entry=... sl=... tp1=... tp2=... tp3=...` waliduje R:R i odległość od ATR; zapis edycji oraz wyników oryginału i edycji trafia wyłącznie do `user_overrides.json`.
- **Pattern Matcher:** Win-rate porównuje wyłącznie zamknięte próbki `BITBASE_3TP_V1` z `cfd_live_history.json` i `market_shadow_lab.json`, dopasowane po ATR%, odległości od EMA200 1H, godzinie sesji, kierunku BTC i stronie transakcji. Wynik pokazuje się dopiero od 5 podobnych próbek; porównanie wyniku bota i edycji jest przewidziane dwa razy dziennie.
- **Walidacja:** Nowe reguły mają testy deterministyczne, ale nie stanowią dowodu przewagi ani wyników walk-forward. Nie uruchamiają zleceń i nie zmieniają ogólnego ryzyka `risk_guard_mod.py`.

### D. Tarcza Kapitału — Etap 1 (26.11.2026)
- **Daily Drawdown Lock:** `portfolio_mod.py` zapisuje wyłącznie lokalny, ignorowany przez Git stan `daily_guard.json`. Dla pozycji `OBSTAWIONE` śledzi dzienny wynik netto po opłacie `0.07R`; blokuje nowe pozycje i automatyczne alerty wejścia po dwóch kolejnych SL lub stracie dziennej >=3.5% kapitału bazowego. Dzień rozliczany jest według `Europe/Warsaw`, a blokada wygasa o północy następnego dnia. Telegram `/status` pokazuje stan i wynik, `/unlock` wymaga potwierdzenia przyciskiem; skaner nadal pracuje i zapisuje wyniki dla AutoTunera.
- **Limit kierunkowy:** Maksymalnie dwie obstawione pozycje w tym samym kierunku; limit spada do jednej, gdy bezwzględna zmiana BTC w ostatniej godzinie przekracza 1.5%. Brak wiarygodnej zmiany BTC używa konserwatywnego limitu jednej pozycji. Kolejne sygnały otrzymują `CORRELATION_GUARD`, pozostają widoczne w konsoli i nie generują alertu wejścia.
- **Płynność i funding:** Bitget USDT-Futures filtruje obrót dobowy poniżej 15M USDT. Karta sygnału może zawierać `WYSOKI FUNDING`, gdy niekorzystna stawka przekracza 0.05% i do najbliższego rozliczenia UTC 00:00/08:00/16:00 pozostaje mniej niż 30 minut.
- **Zakres walidacji:** Testy deterministyczne obejmują progi płynności i funding, limity korelacji, dzienny rollover, dwa SL z rzędu, próg straty oraz ręczne odblokowanie. Po wdrożeniu `smart_verify.py` zakończył się kodem 0 z banerem QA PASS, a `self_test.py` kodem 0; oba uruchomienia wykonały zestaw 9/9 etapów. Etap nie stanowi dowodu przewagi strategii.

---

## 🔒 5. TWARDE STANDARDY INŻYNIERYJNE I BEZPIECZEŃSTWA
1. **Pakt Obostrzeń Giełdowych:** Zawsze uwzględniaj specyfikę BitBase Futures (min. odległość Entry-SL >= 0.35%, max SL <= 6.5%, prowizja -0.07R). Nigdy nie przywracaj giełd spotowych ani zablokowanych API (Binance/Bybit jako bezpośrednie źródło egzekucji).
2. **Zasada Podwójnej Naprawy:** W razie wykrycia defektu należy: a) natychmiast naprawić kod źródłowy, b) dopisać permanentną regułę prewencyjną do `auto_repair_mod.py`.
3. **Nadzór AST Scope-Guard & QA 5.0:** Każda funkcja musi posiadać pełny docstring, prawidłową liczbę argumentów, zadeklarowane zmienne (brak NameError) i przejść bezbłędnie audyt `smart_verify.py`.
4. **DevSecOps (Zero Secret Leaks):** Bezwzględny zakaz commitowania tokenów Telegrama (`bot_token`), kluczy API, tokenów GitHuba czy prywatnych plików stanu (`tg_config.json`, `active_positions.json`).

---

## 📋 6. OTWARTE ZADANIA I ROADMAPA
- [x] Utworzenie ustrukturyzowanego archiwum `archive/legacy_code/` i `archive/legacy_docs/`.
- [x] Opracowanie i wdrożenie `PROJECT_MASTER.md` jako Single Source of Truth.
- [x] Odchudzenie `AGENTS.md` do zwięzłej specyfikacji inżynieryjnej (poniżej 45 linii).
- [x] Implementacja nadrzędnego dyrygenta `orchestrator.py` z cyklem `run_master_cycle()`.
- [x] Implementacja 6 ulepszeń ze Sprintu 24H (`risk_guard_mod.py`, `time_decay_mod.py`, filtry stablecoinów, fallback AI, sesja londyńska, zabezpieczenie parsera JSON).
- [x] Rozszerzenie Web UI o formularz konfiguracji ryzyka (`/api/save_risk`) i status Safe-Lock.
- [x] Aktualizacja `smart_verify.py` o nowe moduły do pełnego wyniku PASS.
- [ ] Dalsze zbieranie próbek `LIVE_FORWARD` w trybie ciągłym i cotygodniowy re-trening wag Meta-Brain.
n## ROADMAPA OD 01.12.2026: SAMOUCZACA SIE PETLA PREDYKCJI (SELF-CALIBRATING ENGINE)n- CEL: Zamknieta petla Prognoza (forecast_ledger.json) -> Audyt Rzeczywistosci (Drift = Real_WR - Predicted_WR netto -0.07R) -> Bezpieczna Korekta Wag (EMA alpha=0.15, clamp +/-5%, min N>=20) w module self_learning_loop_mod.py (0 tokenow AI 24/7).n- ROZSZERZENIE Tydzien 2 (regime_predictor_mod.py): Funding Rate Bitget, szerokosc rynku TOP-100 Altcoin Breadth, kompresja ATR.n- KRYTERIUM AKCEPTACJI: walk_forward_mod.py (OOS > baza, Monte Carlo >= 85%) + python smart_verify.py.n

## 8. PROTOKOL TURBO-SPEED I ZERO-ERROR (OSZCZEDZANIE LIMITOW AI)
1. ZAKAZ WIELOLINIOWYCH SKRYPTOW W POWERSHELL/TELEGRAM: Generuj wylacznie jednoliniowe komendy lub krotkie prompty bez zagniezdzonych cudzyslowow.
2. PODZIAL ROL: Telefon (Termux) zapisuje wylacznie dane (*.json), Laptop/IDE modyfikuje wylacznie kod (*.py, *.md). Zawsze uzywaj git pull --rebase --autostash.
3. ATOMOWE ZADANIA: 1 sesja AI = 1 konkretny modul na lekkim modelu (Gemini Flash standard). Tryby High/Sonnet max 1x/tydzien.
4. AKTUALIZACJA TESTOW: Kazda zmiana logiki w rdzeniu musi od razu aktualizowac odpowiadajacy test w self_test.py przed uruchomieniem smart_verify.py.

### 5. ROZSZERZENIE KORELACJI: LEAD-LAG, DECOUPLING I CLUSTER RISK CAP (po 01.12.2026)
- 1) Lead-Lag Alpha: Wykrywanie opoznionych tokenow w klastrze (r > 0.80), gdy lider (BTC/SOL) juz ruszyl.
- 2) Decoupling Detector: Wyroznianie tokenow odpornych na spadki BTC (r < 0.30 + wysoki wolumen) jako niezaleznych okazji ALFA.
- 3) Cluster Risk Cap: Zamiast calkowitej blokady CORR!, dzielenie limitu ryzyka klastra ($3.00) po polowie ($1.50 + $1.50) miedzy 2 najsilniejsze setupy z tego samego klastra.
- KRYTERIUM AKCEPTACJI: Walidacja w walk_forward_mod.py (OOS > baza, Monte Carlo >= 85%) + python smart_verify.py.

### 6. ARSENAL QUANT 2026 — MIKROSTRUKTURA I ZARZADZANIE KAPITALEM (po 01.12.2026)
- 1) Liquidation Magnet (liquidation_map_mod.py): Szacowanie skupisk likwidacji z Open Interest i Funding Rate Bitget (unikanie wejsc przed Stop-Huntem i lapanie odbic po kaskadzie).
- 2) VPIN Toxicity Detector (vpin_flow_mod.py): Mierzenie nierownowagi wolumenowej w paczkach wolumenu (wykrywanie przeplywu poinformowanego kapitalu przed ruchem ceny).
- 3) Real-Time Orderbook Slippage Guard: Sprawdzanie glebokosci 5 poziomow Bid/Ask przed statusem GOTOWY (blokada sygnalow przy pustym arkuszu/duzym spreadzie).
- 4) Fractional Kelly Sizer: Dynamiczne skalowanie ryzyka (0.75% - 2.0% kapitalu) na podstawie skalibrowanej skutecznosci z self_learning_loop_mod.py.
- KRYTERIUM AKCEPTACJI: Kazdy modul wdrazany osobno (1 sesja = 1 modul) i zatwierdzany wylacznie po przejsciu walk_forward_mod.py (OOS > baza, Monte Carlo >= 85%) oraz python smart_verify.py.
- 4) Asymmetric Tail Correlation: Osobne liczenie korelacji i Bety dla swiec spadkowych BTC (Downside Beta - tarcza dla LONG) oraz wzrostowych BTC (Upside Beta - wybor lidera o najwyzszej dynamice).
