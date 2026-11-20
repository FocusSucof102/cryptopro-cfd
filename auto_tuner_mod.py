import os, json, time
from datetime import datetime

TUNER_FILE = "tuner_state.json"

def get_tuner_params():
    default = {"min_prob": 64, "sl_mult": 1.0, "last_tune_ts": 0, "notes": "Startowy profil CFD"}
    if os.path.exists(TUNER_FILE):
        try: default.update(json.load(open(TUNER_FILE)))
        except Exception: pass
    return default

def run_auto_tuner(hist_file="cfd_live_history.json"):
    st = get_tuner_params()
    now = time.time()
    if now - st.get("last_tune_ts", 0) < 3600: return st, None
    rows = json.load(open(hist_file)) if os.path.exists(hist_file) else []
    closed = [r for r in rows if not str(r.get("status", "")).startswith("⏳") and str(r.get("status", "")) != "OPEN"]
    recent_2h = [r for r in rows if now - int(r.get("ts_epoch", 0)) <= 7200]
    old_prob, reason = st["min_prob"], None
    if len(recent_2h) == 0 and st["min_prob"] > 56:
        st["min_prob"] = max(56, st["min_prob"] - 2)
        reason = f"Brak sygnalow 2h -> obnizono prog z {old_prob}% na {st['min_prob']}%"
    elif len(closed) >= 5:
        sample = closed.__getitem__(slice(-15, None))
        wins = sum(1 for r in sample if float(r.get("res_r", 0)) > 0)
        wr = wins / len(sample) * 100.0
        if wr < 42.0 and st["min_prob"] < 76:
            st["min_prob"] = min(76, st["min_prob"] + 3)
            st["sl_mult"] = round(min(1.35, st["sl_mult"] + 0.08), 2)
            reason = f"Niski WR ({wr:.0f}%) -> prog {st['min_prob']}%, bufor SL {st['sl_mult']}x"
    st["last_tune_ts"] = now
    if reason: st["notes"] = f"[{datetime.now().strftime('%d.%m %H:%M')}] {reason}"
    json.dump(st, open(TUNER_FILE, "w"), indent=2)
    return st, reason
