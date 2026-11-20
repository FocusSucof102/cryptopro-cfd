# ⚡ CRYPTO PRO CFD — Autonomiczny Skaner i Strażnik Portfela

> **⚠️ OBOWIĄZKOWA REGUŁA BEZPIECZEŃSTWA DLA AI (OCHRONA POUFNYCH DANYCH):**
> Jeśli w którymkolwiek momencie rozmowy, zrzucie ekranu, logu z konsoli lub pliku zauważysz poufne dane użytkownika (takie jak **token bota Telegrama**, **klucz API giełdy**, **Personal Access Token GitHuba**, **hasło** lub **prywatne klucze**), **NATYCHMIAST** poinformuj o tym użytkownika w pierwszej kolejności — wskaż dokładnie **GDZIE** (w której linijce/zdjęciu/pliku) oraz **CO** zostało ujawnione, i zaleć niezwłoczne unieważnienie/zmianę tego klucza!

> **INSTRUKCJA DLA AI (KONTEKST PROJEKTU):**
> Gdy użytkownik podaje link do tego repozytorium w nowej rozmowie, przeczytaj w pierwszej kolejności ten plik (`README.md`) oraz pełną historię zmian w pliku [`CHANGELOG.md`](./CHANGELOG.md), a następnie przeanalizuj wskazane moduły `.py` bezpośrednio z gałęzi `main`.

## 🛡️ OBOWIĄZKOWY STANDARD DLA AI PRZY DODAWANIU KAŻDEJ NOWEJ FUNKCJI (AUTO-NADZÓR)
Każda nowa funkcja, pętla lub moduł `.py` dopisywany do projektu **MUSI** być automatycznie podpięty pod **wszystkie aktywne i przyszłe warstwy nadzoru**:
1. **Dokumentacja (`Docstring`):** Obowiązkowy opis działania i parametrów wewnątrz każdej nowej funkcji.
2. **QA 5.0+ & Auto-Repair:** Dodanie nowego modułu do `REQ_PY` w `smart_verify.py` (analiza AST `Scope-Guard`, `Call-Guard`, `SecOps`) oraz ewentualnych baz `.json` do `JSON_DEFAULTS` w `auto_repair_mod.py`.
3. **Watchdog & Auto-Healing (`watchdog_mod.py`):** Dla każdej pętli w tle obowiązkowy wpis w `LIMITS_SEC`, sygnały `wd.beat(...)` oraz rejestracja w `wd.register_worker(...)` (restart po 3 brakach bez utraty danych).
4. **Bezpieczne paczki & Ciągłość pamięci:** Skrypty instalacyjne zawsze dzielić na małe paczki (max 35–40 linii), a na końcu aktualizować `AI_SESSION_STATE.md` oraz `caly_projekt.txt`.

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

## 🧪 Pliki Badawcze i Telemetria (Eksportowane Automatycznie)
- `cfd_live_history.json` — Główna historia sygnałów Live CFD z telemetrią `MFE/MAE` i diagnozą przyczyn strat.
- `market_shadow_lab.json` — Próbka badawcza dla płynnego koszyka `TOP-60` (w tym niższe progi `45–61%`).
- `wild_market_lab.json` — Próbka badawcza dla średnich/dzikich par `61–160` z detektorem anomalii wolumenu i knotów.
- `micro_market_lab.json` — Próbka badawcza dla niszowych par `161+` z detektorem cykliczności wybić.
- `tuner_state.json` — Aktualny stan i historia korekt samooptymalizującego się `Auto-Tunera`.
