# 🧠 ŻYWA PAMIĘĆ SESJI AI (AI_SESSION_STATE)
*Ostatnia aktualizacja: 2026-11-20 19:50:22*

## 🛡️ OBOWIĄZKOWY STANDARD DLA AI PRZY DODAWANIU KAŻDEJ NOWEJ FUNKCJI (AUTO-NADZÓR)
1. **Docstring** wewnątrz każdej nowej funkcji (`Docstring-Guard` w QA 5.0 PRO+).
2. **QA 5.0+ & Auto-Repair:** Dodanie pliku `.py` do `REQ_PY` w `smart_verify.py` oraz `.json` do `JSON_DEFAULTS` w `auto_repair_mod.py`.
3. **Watchdog & Auto-Healing (`watchdog_mod.py`):** `LIMITS_SEC`, `wd.beat(...)` i `wd.register_worker(...)` dla pętli w tle.
4. **Małe paczki (<=35 linii)** + odświeżenie `AI_SESSION_STATE.md` oraz `caly_projekt.txt`.

## 📌 Aktualny stan systemu (Etap 10.1 — Wizualne Banery Czerwone/Zielone + Smart SL):
- Dodano wyraźne bloki 🟩🟩🟩 (`SĄ AKTYWNE OKAZJE`) oraz 🟥🟥🟥 (`BRAK AKTYWNYCH SYGNAŁÓW`) do wszystkich wyników w Telegramie (Skan CFD, Auto-Alert 15m, Puls 30m, Pump & Dump 7 wzorców) oraz neonowe ramki w Pulpicie Chrome 2.0.
