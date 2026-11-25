# 🎯 AGENTS.md — INSTRUKCJA I ZASADY SYSTEMOWE DLA AGENTÓW AI
1. **Single Source of Truth:** Jedynym źródłem wiedzy jest `PROJECT_MASTER.md`. Przed zmianą przeczytaj `PROJECT_MASTER.md`, `README.md`, `CHANGELOG.md`.
2. **Cel:** Autonomiczny system CFD/Futures (BitBase Futures, dane Bitget USDT-Futures, płynność co najmniej 15M USDT/24h), maksymalizujący zysk netto po prowizji `-0.07R` na transakcję.
3. **Pakt Obostrzeń & DevSecOps:** Nigdy nie ujawniaj tokenów/kluczy (`tg_config.json`, `active_positions.json` chronione). Nie przywracaj giełd spotowych ani zablokowanych API (Binance/Bybit).
4. **Zasada Podwójnej Naprawy:** Po zmianie uruchom `smart_verify.py` (QA 5.0 PRO+ AST/Scope-Guard). Błąd = napraw kod + dopisz regułę do `auto_repair_mod.py`.
5. **Standard Specyfikacji Inżynieryjnej:**
   - Każda funkcja: docstring + AST Scope-Guard + Call-Guard + brak NameError.
   - Wdrożenie: test `walk_forward_mod.py` (OOS > baza, Monte Carlo >= 85%).
   - Filtry: `STABLECOIN_BLACKLIST`, sesja londyńska (+10 pkt, EMA200 1H), Safe-Lock (DD >= 6% -> PLATINUM >= 68%), BE +0.35R po +1.1R.
6. **Mapa Archiwum (`archive/`):**
   - `legacy_code/`: `collector.py`, `scanner.py`, `system.py`, `dashboard.py`, `backtest.py` (referencja/badania).
   - `legacy_docs/`: `MASTER_HANDOFF_AI.txt`, `AI_SESSION_STATE.md`, `EVOLUTION_JOURNAL.md` (scalone w PROJECT_MASTER).
7. **Synchronizacja Git:** `git pull --rebase origin main` przed zadaniem; po PASS `smart_verify.py` → `git add`, `commit`, `push origin main`.
n## 7. POLITYKA LIMITOW AI (OD 01.12.2026)n- Uzywaj lekkich modeli (Gemini Flash standard) i pracuj przyrostowo (1 modul na sesje).n- Tryby High/Sonnet uruchamiaj max 1x w tygodniu do przegladu calibration_summary.json.

