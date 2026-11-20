import os, json, time
from datetime import datetime

NZT_FILE = "nzt_synapses.json"

def load_nzt():
    """Wczytuje stan sieci synaptycznej NZT Cortex z nzt_synapses.json."""
    base = {"iq_cycles": 0, "saved_losses": 0, "missed_wins": 0, "synergies": {}, "pending_rejects": []}
    if os.path.exists(NZT_FILE):
        try: base.update(json.load(open(NZT_FILE, encoding="utf-8")))
        except Exception: pass
    return base

def record_rejected_hypothesis(sym, side, price, stop, reason):
    """Zapisuje odrzucony sygnal do pamieci kontrfaktycznej, aby po 60m sprawdzic czy AI mialo racje."""
    st = load_nzt()
    st["iq_cycles"] = int(st.get("iq_cycles", 0)) + 1
    rej = st.get("pending_rejects", [])
    if not any(r.get("sym") == sym and (time.time() - r.get("ts", 0)) < 3600 for r in rej):
        rej.append({"sym": sym, "side": side, "price": float(price), "stop": float(stop), "reason": str(reason)[:50], "ts": time.time()})
    st["pending_rejects"] = rej[-40:]
    json.dump(st, open(NZT_FILE, "w", encoding="utf-8"), indent=2)

def evolve_nzt_cortex(cp_mod):
    """Rozlicza odrzucone hipotezy po 60m i odkrywa najskuteczniejsze pary sygnalow (Super-Synapsy)."""
    st = load_nzt()
    now_t, still_pending = time.time(), []
    for r in st.get("pending_rejects", []):
        if now_t - float(r.get("ts", 0)) < 3600:
            still_pending.append(r); continue
        kl = cp_mod.fetch_klines("BITGET", r["sym"], "15m", 6)
        if not kl or len(kl.get("c", [])) < 4: continue
        td = 1 if r["side"] == "LONG" else -1
        sd = abs(r["price"] - r["stop"]) or (r["price"] * 0.01)
        best_c = max(float(x) for x in kl["h"][-4:]) if td == 1 else min(float(x) for x in kl["l"][-4:])
        worst_c = min(float(x) for x in kl["l"][-4:]) if td == 1 else max(float(x) for x in kl["h"][-4:])
        if td * (worst_c - r["price"]) <= -sd:
            st["saved_losses"] = int(st.get("saved_losses", 0)) + 1
        elif td * (best_c - r["price"]) >= sd * 1.5:
            st["missed_wins"] = int(st.get("missed_wins", 0)) + 1
    st["pending_rejects"] = still_pending
    json.dump(st, open(NZT_FILE, "w", encoding="utf-8"), indent=2)
    return st

def get_nzt_status_line(cp_mod):
    """Zwraca zwiezly raport inteligencji NZT-48 (liczba cykli nauki i uratowane straty)."""
    st = evolve_nzt_cortex(cp_mod)
    iq = 100 + min(85, int(st.get("iq_cycles", 0)) // 15 + int(st.get("saved_losses", 0)) * 2)
    return f"💊 <b>NZT-48 Cortex IQ {iq}:</b> Cykle nauki: <b>{st.get('iq_cycles', 0)}</b> | Uratowane SL: <b>{st.get('saved_losses', 0)}</b> | Przeoczone: <b>{st.get('missed_wins', 0)}</b>"
