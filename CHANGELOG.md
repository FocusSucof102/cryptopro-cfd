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
