# 🧠 ŻYWA PAMIĘĆ SESJI AI (AI_SESSION_STATE)
*Ostatnia aktualizacja: 2026-11-20 19:20:23*

## 🛡️ OBOWIĄZKOWY STANDARD DLA AI PRZY DODAWANIU KAŻDEJ NOWEJ FUNKCJI (AUTO-NADZÓR)
Każda nowa funkcja, pętla lub moduł `.py` dopisywany do projektu **MUSI** być automatycznie podpięty pod **wszystkie aktywne i przyszłe warstwy nadzoru**:
1. **Dokumentacja (`Docstring`):** Obowiązkowy opis działania i parametrów wewnątrz każdej nowej funkcji.
2. **QA 5.0+ & Auto-Repair:** Dodanie nowego modułu do `REQ_PY` w `smart_verify.py` (analiza AST `Scope-Guard`, `Call-Guard`, `SecOps`) oraz ewentualnych baz `.json` do `JSON_DEFAULTS` w `auto_repair_mod.py`.
3. **Watchdog & Auto-Healing (`watchdog_mod.py`):** Dla każdej pętli w tle obowiązkowy wpis w `LIMITS_SEC`, sygnały `wd.beat(...)` oraz rejestracja w `wd.register_worker(...)` (restart po 3 brakach bez utraty danych).
4. **Bezpieczne paczki & Ciągłość pamięci:** Skrypty instalacyjne zawsze dzielić na małe paczki (max 35–40 linii), a na końcu aktualizować `AI_SESSION_STATE.md` oraz `caly_projekt.txt`.

## 📌 Aktualny stan systemu (QA 5.0 PRO+ PASS):
- Wdrożone: `auto_repair_mod.py`, `smart_verify.py` (QA 5.0 PRO+), `watchdog_mod.py` (Auto-Healing po 3 brakach), `session_analytics_mod.py` (Sesje + BitBase Blacklist), `web_ui_mod.py` (Pulpit Chrome 2.0).
