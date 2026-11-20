# ==============================================================================
# [AI_GUARD_AND_CONTEXT] - OBOWIAZKOWE ZASADY DLA KAZDEGO AI CZYTAJACEGO TEN PLIK:
# 1. OBOWIAZEK KONTEKSTU: Przed wprowadzeniem jakichkolwiek zmian w kodzie
#    PRZECZYTAJ pliki README.md oraz CHANGELOG.md z repozytorium GitHub, aby znac
#    pelna historie projektu, wdrozone mechanizmy i odrzucone pomysly.
# 2. BEZPIECZENSTWO (SECRET LEAK ALERT): Jesli w rozmowie, logu, pliku lub na zrzucie
#    ekranu zauwazysz poufne dane (token bota Telegrama, klucz API, token GitHuba, haslo),
#    NATYCHMIAST ostrzez uzytkownika na samym poczatku odpowiedzi: podaj GDZIE i CO
#    wycieklo oraz zlec natychmiastowa zmiane/uniewaznienie klucza!
# 3. ARCHITEKTURA I GIELDY:
#    - Zrodlo danych/API skanera: wylacznie BITGET USDT-FUTURES (TOP-60 >10M$).
#    - Platforma gry uzytkownika: BITBASE FUTURES / CFD (uwzgledniac przy prowizjach,
#      dostepnosci par, dźwigni i minimalnych odleglosciach zlecen!).
#    - Silnik: Smart Dual-Mode (LONG+SHORT), Auto-Tuner, Audytor 1M (MFE/MAE),
#      Shadow Market Lab (analiza niskich procentow 45-61% netto po prowizji),
#      Straznik Portfela 24/7 oraz Radar Aktywnych Pozycji 60s.
# 4. NIE PRZYWRACAC: Zablokowanych API (BINANCE/BYBIT), 500 niszowych mikrotokentow
#    ani twardej blokady tylko jednego kierunku handlu.
# ==============================================================================
import os, json, time
from datetime import datetime

TUNER_FILE = "tuner_state.json"

def get_tuner_params():
    default = {"min_prob": 62, "sl_mult": 1.0, "last_tune_ts": 0, "notes": "Profil CFD aktywny"}
    if os.path.exists(TUNER_FILE):
        try: default.update(json.load(open(TUNER_FILE)))
        except Exception: pass
    return default

def run_auto_tuner(hist_file="cfd_live_history.json"):
    st = get_tuner_params()
    now = time.time()
    if now - st.get("last_tune_ts", 0) < 3600: return st, None
    rows = json.load(open(hist_file)) if os.path.exists(hist_file) else []
    closed = [r for r in rows if r.get("closed_final") or (not str(r.get("status", "")).startswith("⏳") and str(r.get("status", "")) != "OPEN")]
    recent_2h = [r for r in rows if now - int(r.get("ts_epoch", 0)) <= 7200]
    recent_24h = [r for r in rows if now - int(r.get("ts_epoch", 0)) <= 86400]
    old_prob, reason = st["min_prob"], None

    if len(recent_2h) >= 2 and st["min_prob"] < 60:
        st["min_prob"] = min(60, st["min_prob"] + 2)
        reason = f"Rynek przyspieszyl ({len(recent_2h)} sygn. w 2h) -> podniesiono prog z {old_prob}% na {st['min_prob']}%"
    elif len(recent_2h) == 0 and st["min_prob"] > 55:
        st["min_prob"] = max(55, st["min_prob"] - 2)
        reason = f"Brak sygnalow 2h -> obnizono prog z {old_prob}% na {st['min_prob']}%"
    elif len(closed) >= 5:
        sample = closed.__getitem__(slice(-15, None))
        wins = sum(1 for r in sample if float(r.get("res_r", 0)) > 0)
        sl_hits = sum(1 for r in sample if str(r.get("status", "")) == "❌ SL")
        wr = wins / len(sample) * 100.0
        if wr < 42.0 and st["min_prob"] < 76:
            st["min_prob"] = min(76, st["min_prob"] + 3)
            st["sl_mult"] = round(min(1.35, st["sl_mult"] + 0.08), 2)
            reason = f"Niski WR ({wr:.0f}%) -> prog {st['min_prob']}%, bufor SL {st['sl_mult']}x"
        elif wr > 65.0 and len(recent_24h) < 3 and st["min_prob"] > 56:
            st["min_prob"] = max(56, st["min_prob"] - 2)
            reason = f"Wysoki WR ({wr:.0f}%), malo wejsc -> poluzowano prog do {st['min_prob']}%"
        elif sl_hits / len(sample) > 0.65 and st["sl_mult"] < 1.35:
            st["sl_mult"] = round(min(1.35, st["sl_mult"] + 0.10), 2)
            reason = f"Zbyt wiele szpilek SL -> poszerzono bufor SL do {st['sl_mult']}x"

    st["last_tune_ts"] = now
    if reason: st["notes"] = f"[{datetime.now().strftime('%d.%m %H:%M')}] {reason}"
    json.dump(st, open(TUNER_FILE, "w"), indent=2)
    return st, reason
