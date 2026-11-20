# ⚡ CRYPTO PRO CFD — Autonomiczny Skaner i Strażnik Portfela

> **⚠️ OBOWIĄZKOWA REGUŁA BEZPIECZEŃSTWA DLA AI (OCHRONA POUFNYCH DANYCH):**
> Jeśli w którymkolwiek momencie rozmowy, zrzucie ekranu, logu z konsoli lub pliku zauważysz poufne dane użytkownika (takie jak **token bota Telegrama**, **klucz API giełdy**, **Personal Access Token GitHuba**, **hasło** lub **prywatne klucze**), **NATYCHMIAST** poinformuj o tym użytkownika w pierwszej kolejności — wskaż dokładnie **GDZIE** (w której linijce/zdjęciu/pliku) oraz **CO** zostało ujawnione, i zaleć niezwłoczne unieważnienie/zmianę tego klucza!

> **INSTRUKCJA DLA AI (KONTEKST PROJEKTU):**
> Gdy użytkownik podaje link do tego repozytorium w nowej rozmowie, przeczytaj w pierwszej kolejności ten plik (`README.md`) oraz pełną historię zmian w pliku [`CHANGELOG.md`](./CHANGELOG.md), a następnie przeanalizuj wskazane moduły `.py` bezpośrednio z gałęzi `main`.

## 🗂️ Architektura Modułów w Repozytorium
- `crypto_pro.py` — Główny rdzeń systemu: serwer Flask (`:5000`), obsługa bota Telegram (`tg_listener`, `tg_menu`), pętla `cfd_live_bg_loop` (co 15 min + Puls co 30 min), `fast_active_positions_loop` (co 60s) oraz `audit_cfd_history_1m`.
- `alpha_pro_mod.py` — Dynamiczne pobieranie `TOP-60` kontraktów `BITGET USDT-FUTURES` (`>10M$`), walidacja odległości zleceń CFD (`validate_cfd_order`), pasek wielointerwałowy `MTF (X/4: 15M|1H|4H|1D)` oraz wskaźniki Alpha.
- `auto_tuner_mod.py` — Samooptymalizujący się regulator czułości (`min_prob`, `sl_mult`) na podstawie wyników ze świec `1m`.
- `portfolio_mod.py` — Zarządzanie otwartymi pozycjami, kontrola marginu/korelacji przed wejściem (`check_new_opportunity_margin`) oraz dzienny wyłącznik straty (`record_closed_trade_pnl`).
- `planner_mod.py` — Kalkulator wielkości pozycji, dźwigni, ceny likwidacji oraz 5 progów `TP1..TP5`.
- `demo_sim_mod.py` — 24-godzinna symulacja CFD PRO na żywo z prowizjami i Break-Even po `+1.5R`.
- `chart_mod.py` — Generowanie wykresów SMC/EMA z warstwami na żądanie.
- `self_test.py` — Automatyczny test składni, importów i połączenia z API Bitget przed restartem.

## 🔒 Bezpieczeństwo
Plik `.gitignore` blokuje wysyłanie wszelkich plików `.json`, `.csv` oraz `.log` (`tg_config.json`, stan portfela i historia trafień pozostają wyłącznie lokalnie na urządzeniu w `~/downloads`).

Pełny zapis wszystkich wdrożonych zmian od początku projektu znajduje się w pliku **[CHANGELOG.md](./CHANGELOG.md)**.
