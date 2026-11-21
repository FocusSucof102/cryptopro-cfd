# 📜 PEŁNA HISTORIA ZMIAN (CHANGELOG) — CRYPTO PRO CFD

## Etap 1: Fundament i Stabilizacja Środowiska Termux + Web + Telegram
- Przeniesienie skanera wyłącznie na płynne kontrakty Futures/CFD (**BITGET USDT-FUTURES**), odcięcie zablokowanych lub mało płynnych giełd spotowych.
- Rozwiązanie problemu `EOFError` przy uruchamianiu w tle (`nohup`) oraz eliminacja podwójnych procesów w `CryptoPro_Start.sh`.
- Zwiększenie limitu czasu (`timeout=15s`) dla zapytań Telegram API w sieci komórkowej 5G oraz bezpieczne kodowanie znaków HTML (`<`, `>`).
- Automatyczne odświeżanie pulpitu lokalnego w przeglądarce (`http://127.0.0.1:5000`) co 30 sekund bez otwierania nowych zakładek.

## Etap 2: Przebudowa Menu Telegrama pod Handel CFD
- Uproszczenie klawiatury Telegrama do kompaktowego **Panelu CFD PRO**:
  - `⚡ Skanuj CFD (Long/Short)` | `🟢 Live CFD: ON (15m)`
  - `💼 Portfel CFD` | `🧮 Planner` | `📈 Wykresy`
  - `⚙️ Warstwy` | `🏆 Symulacja CFD PRO`
  - `📜 Backtest 2020-2026` | `📊 Historia CSV`
  - `🎭 Demo Okazji (Podgląd Pulpitu)`

## Etap 3: Silnik Typowania TOP-60, Smart Dual-Mode oraz Karty Sygnałów
- Dynamiczne pobieranie **TOP-60 najpłynniejszych kontraktów Futures** z API Bitget (`obrót dobowy > 10 000 000$`) w `alpha_pro_mod.py`.
- Walidacja wymogów giełdowych/CFD (`validate_cfd_order`): min. dystans `Entry <-> SL >= 0.35%`, max SL `<= 6.5%`, min. dystans zlecenia oczekującego `>= 0.12%`.
- **Smart Dual-Mode (`LONG + SHORT`):** Gra zgodnie z reżimem makro Bitcoina (`EMA 200 1H`), ale przepuszcza również silne sygnały w kierunku przeciwnym, gdy altcoin wykazuje przewagę siły relatywnej (`RS vs BTC`) lub wybicie `TTM Squeeze`.
- **Pasek MTF (`X/4: 15M | 1H | 4H | 1D`)** oraz procentowa **Szansa kontynuacji (%)** na każdej karcie sygnału wraz z przyciskami `🧮 Plan`, `➕ Obstawiam`, `📈 Wykres`.
- Przyspieszenie skanowania **12-krotnie** dzięki wielowątkowości (`ThreadPoolExecutor(max_workers=12)`).

## Etap 4: Planner, Kopiowanie Wartości i Strażnik Portfela 24/7
- **Planner (`🧮 Plan`):** Wylicza wielkość pozycji, dźwignię, margin, cenę likwidacji oraz **5 poziomów Take Profit (`TP1: 1.0R`, `TP2: 1.5R`, `TP3: 2.5R`, `TP4: 3.5R`, `TP5: 5.0R`)** z osobnymi przyciskami kopiowania do schowka telefonu (`cpv_`).
- **Pre-Check Strażnika przy każdej okazji:** Ostrzega przed przekroczeniem marginu (`>50%`), nadmierną korelacją kierunku (`>=2` pozycje w tę samą stronę) oraz skumulowanym ryzykiem SL (`>6%`).
- **Szybki Radar Aktywnych Pozycji (`60s`):** Monitoruje co minutę pozycje dodane przez `➕ Obstawiam`, powiadamia o osiągnięciu `TP1..TP5` (chroniąc przed błędem zera po przecinku na giełdzie) oraz ostrzega przy zbliżeniu się na 20% do SL.
- **Wyłącznik Dziennej Straty (`Daily Drawdown Circuit Breaker`):** Przy dziennej stracie `>= 8%` konta proponuje wyciszenie alertów na `15 / 30 / 60 min` przeciw *revenge tradingowi*.

## Etap 5: Audytor na Świecach 1m, Auto-Tuner oraz GitHub CI/CD
- **Audytor Wyników Live (`📊 Historia CSV`):** Odtwarza minuta po minucie los każdego trafienia na świecach **1-minutowych (`1m`)**, uwzględniając przypadkowe szpilki (`High/Low`), podaje dokładny czas do zysku/SL oraz wylicza skuteczność `WR%` i wynik w `R`.
- **Auto-Tuner (`auto_tuner_mod.py`):** Automatycznie obniża próg czułości po `2h` ciszy (min. `56%`) lub zaostrza próg i poszerza bufor SL, gdy skuteczność z audytu `1m` spada poniżej `42%`.
- **Puls Życia (`30 min`):** Cichy raport kontrolny z liczbą przeskanowanych par oraz aktualnymi nastawami Auto-Tunera.
- **Integracja z GitHub + `self_test.py`:** Ochrona kluczy prywatnych przez `.gitignore` (`*.json`, `*.csv`, `*.log`) oraz automatyczna weryfikacja składni i połączenia z API.

## Etap 6: Pełny Rejestr Decyzji i Przerobionych Opcji (Pamięć Projektu)
### ✅ Opcje zatwierdzone i działające w systemie:
1. **Giełda i koszyk par:** Dane API: `BITGET USDT-FUTURES` | Realna gra użytkownika: **`BitBase Futures / CFD`** (`TOP-60` par o obrocie dobowym `> 10M$`), walidacja odległości `Entry <-> SL >= 0.35%`.
2. **Kierunek handlu (`Smart Dual-Mode`):** Gra `LONG` oraz `SHORT` jednocześnie, z priorytetem dla makro-reżimu Bitcoina (`EMA 200 1H`) oraz warunkowym dopuszczeniem kontr-trendowych odbić przy silnym `RS vs BTC` lub `TTM Squeeze`.
3. **Szybkość i kalibracja:** Skaner wielowątkowy (`12 wątków`), automatyczny `Auto-Tuner` (obniża próg po 2h ciszy do min. `55%`, zaostrza przy `WR < 42%` i poszerza bufor SL przy serii szpilek), cichy `Puls CFD Live` co 30 minut z bieżącym statusem tunera.
4. **Karty okazji i Planner:** Pasek zgodności wielointerwałowej `MTF (X/4: 15M | 1H | 4H | 1D)`, procentowa szansa kontynuacji, przyciski `🧮 Plan`, `➕ Obstawiam`, `📈 Wykres`, osobne kopiowanie każdej z 7 wartości (`Wejście`, `SL`, `TP1..TP5`) przez `termux-clipboard-set`.
5. **Strażnik Portfela 24/7:** Pre-check marginu (`>50%`), korelacji kierunku (`>=2` pozycje) i łącznego ryzyka SL (`>6%`) na kartach okazji; Szybki Radar Aktywnych Pozycji (`co 60s`) chroniący przed błędem zera po przecinku na giełdzie; Dzienny Wyłącznik Straty (`>= 8%`) z przyciskami wyciszenia `15 / 30 / 60 min`.
6. **Audytor Wyników (`📊 Historia CSV`):** Weryfikacja minuta po minucie na świecach `1m` (oraz `5m` powyżej 16,5h) z uwzględnieniem przypadkowych szpilek `High/Low`, czasem do wyniku oraz blokadą zamkniętych pozycji (`closed_final`).
7. **Automatyzacja GitHub:** Ochrona prywatnych kluczy (`*.json`, `*.csv`, `*.log` w `.gitignore`), `self_test.py` oraz ciągła auto-synchronizacja z repozytorium `FocusSucof102/cryptopro-cfd` co 5 minut i przy starcie.

### ❌ Opcje odrzucone / wycięte (nie przywracać):
- Giełdy spotowe (`BITBASE`) oraz zablokowane API (`BINANCE`, `BYBIT`).
- Skanowanie wszystkich ~500 niszowych mikrotokentów z małą płynnością (zbyt duże spready i stop-hunty).
- Twarda blokada tylko jednego kierunku (`Tylko SHORT` lub `Tylko LONG`).
- Stare przyciski z pierwszej wersji menu (nieużywane w handlu CFD).

## Etap 7: Laboratoria Rynkowe 24/7, Macro Pump & Dump (4H/1D) i Praca w Tle Androida
- **Rozbudowa Audytora 1M (`MFE / MAE` + Przyczyny Strat):** Automatyczna klasyfikacja każdego zamkniętego sygnału (`CLEAN_WIN`, `SL_WICK_REVERSAL`, `MISSED_TP_REVERSAL`, `COUNTER_BTC_FAIL`), obsługa pozycji powyżej 16,5h na świecach `5m` oraz tabela opłacalności niższych progów procentowych (`45-54%`, `55-61%`, `62%+`) **netto po prowizjach BitBase Futures (`-0.07R`)**.
- **Trzy Ciche Laboratoria Badawcze (z podziałem `HIST_BACKFILL` vs `LIVE_FORWARD`):**
  1. `market_shadow_lab.json` (`TOP-60`, obrót `>10M$`) — analiza odrzuconych setupów z niższą punktacją.
  2. `wild_market_lab.json` (`TOP 61–160`, obrót `1M$–10M$`) — detektor manipulacji i polowań na SL (`VOL_SPIKE`, `LONG_WICK_HUNT`).
  3. `micro_market_lab.json` (`TOP 161+`, obrót `<1M$`) — detektor cykliczności wybić godzinowych (`CYCLIC_XH`).
- **Skaner & Auto-Radar `Macro Pump & Dump (4H/1D)`:** Przycisk `🚀 Pump & Dump` w menu Telegrama oraz skan w tle co 30 min dla 140 kontraktów (wykrywanie wczesnych wybić z bazy `LONG` oraz załamań po paraboli typu `RAVEUSDT` pod `MA7 4H` dla `SHORT`).
- **Stabilizacja 24/7 w Androidzie (`termux-wake-lock`):** Utrzymywanie procesów przy zminimalizowanym oknie Termuxa oraz ciągły eksport zanonimizowanych plików badawczych na GitHub co 5 minut.

## Etap 8–12: Nadzór QA 5.0 PRO+, Auto-Repair, Watchdog, Sniper Mode i Instytucjonalny Orderflow
- **4 Warstwy Ochrony (`smart_verify.py`, `auto_repair_mod.py`, `watchdog_mod.py`):** Analiza AST (`Scope-Guard`, `Call-Guard`, `Docstring-Guard`), samoleczenie wcięć/importów/JSON/Git oraz automatyczny restart zawieszonych pętli po 3 brakach bez utraty danych.
- **Sniper Mode & Smart SL (`sniper_doctor_mod.py`, `smart_sl_mod.py`):** Zgodność z reżimem BTC, blokada długich knotów `>45%`, SL `1.8x ATR` + SMC + Break-Even `+0.12R` + Trailing `2.2x ATR` + bezpiecznik likwidacji, przycisk `🩺 Diagnoza Konta` oraz instrukcje **👉 CO TERAZ ZROBIĆ**.
- **Wielopoziomowy Auto-Tuner (`45–100%`) + Bezpiecznik Anty-Przestojowy 6h + Orderbook Imbalance & Makro Shield (`inst_orderflow_mod.py`):** Blokada ścian płynności przed TP1 oraz ochrona przed publikacjami danych USA (CPI/NFP/FOMC).

## Etap 13–20: Pakiet Kwantytatywny AI Quant, NZT-48 Cortex, Meta-Brain i Sprint 24H
- **AI Quant & Ewolucja (`ai_quant_mod.py`, `evolution_lab_mod.py`, `quant_edge_pro_mod.py`):** Algorytm `KNN Pattern Matcher` z zanikiem czasowym `Liquid Decay`, macierz `Lead-Lag` (`BTC+ETH+SOL -> Alty`), `Fractional Kelly 0.25x`, `CHOP Shield`, korelacja Pearsona w portfelu, `Binance Futures Lead`, `Coin Fingerprinting` oraz `EVT Tail Shield`.
- **Technologie Przyszłości & Samouczenie (`future_quantum_mod.py`, `quantum_nash_mod.py`, `meta_brain_mod.py`, `nzt_cortex_mod.py`):** Entropia Shannona, `Whale Iceberg Absorption`, `Red-Team AI` (5-punktowe weto), `Quantum Wave Interference`, `Nash Predator Trap`, wagi `Meta-Brain` (`0.25x–2.00x`) oraz uczenie kontrfaktyczne z odrzuceń (`NZT-48 Cortex`).
- **Bramka Aktualizacji A/B (`upgrade_gate_mod.py`) & Czarna Skrzynka 24H (`report_24h_mod.py`):** Testy piaskownicy przed wdrożeniem zmian, licznik lejka odrzuceń `funnel_stats.json`, dziennik decyzji AI oraz automatyczny eksport `raport_24h_dla_ai.txt`.
