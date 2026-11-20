# 🧠 ŻYWA PAMIĘĆ SESJI AI (AI_SESSION_STATE)
*Ostatnia aktualizacja: 2026-11-20 19:34:16*

## 🛡️ OBOWIĄZKOWY STANDARD DLA AI PRZY DODAWANIU KAŻDEJ NOWEJ FUNKCJI (AUTO-NADZÓR)
Każda nowa funkcja, pętla lub moduł `.py` dopisywany do projektu **MUSI** być automatycznie podpięty pod **wszystkie aktywne i przyszłe warstwy nadzoru**:
1. **Dokumentacja (`Docstring`):** Obowiązkowy opis działania i parametrów wewnątrz każdej nowej funkcji (egzekwowane przez Docstring-Guard w QA 5.0 PRO+).
2. **QA 5.0+ & Auto-Repair:** Dodanie nowego modułu do `REQ_PY` w `smart_verify.py` oraz baz `.json` do `JSON_DEFAULTS` w `auto_repair_mod.py`.
3. **Watchdog & Auto-Healing (`watchdog_mod.py`):** Wpis w `LIMITS_SEC`, `wd.beat(...)` oraz `wd.register_worker(...)` dla pętli w tle.
4. **Bezpieczne paczki & Ciągłość pamięci:** Skrypty instalacyjne dzielić na małe paczki (max 35–40 linii), a na końcu aktualizować `AI_SESSION_STATE.md` oraz `caly_projekt.txt`.

## 📌 Aktualny stan systemu (Etap 9 — Sniper Mode & Lekarz Konta):
- Wdrożono `sniper_doctor_mod.py`: twarda zgodność z reżimem BTC, odrzucanie świec z długim przeciwnym knotem (>45%), poszerzony SL `1.8x ATR`, limit max 2 najlepsze okazje na skan, jednoznaczna instrukcja **👉 CO TERAZ ZROBIĆ** na kartach oraz przycisk `🩺 Diagnoza` w Telegramie.
