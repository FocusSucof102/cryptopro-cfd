import os, json, time
from datetime import datetime

NZT_FILE = "nzt_synapses.json"

def load_nzt():
    """Wczytuje stan sieci synaptycznej NZT Cortex wraz z pelna historia rozliczonych odrzucen."""
    base = {"iq_cycles": 0, "saved_losses": 0, "missed_wins": 0, "pending_rejects": [], "resolved_rejects": []}
    if os.path.exists(NZT_FILE):
        try: base.update(json.load(open(NZT_FILE, encoding="utf-8")))
        except Exception: pass
    return base

def record_rejected_hypothesis(sym, side, price, stop, reason):
    """Zapisuje odrzucony sygnal wraz z przyczyna blokady do weryfikacji czy bylby zyskowny."""
    st = load_nzt()
    st["iq_cycles"] = int(st.get("iq_cycles", 0)) + 1
    rej = st.get("pending_rejects", [])
    if not any(r.get("sym") == sym and (time.time() - r.get("ts", 0)) < 3600 for r in rej):
        rej.append({"sym": sym, "side": side, "price": float(price), "stop": float(stop), "blocked_by": str(reason)[:90], "ts": time.time(), "time_str": datetime.now().strftime("%d.%m %H:%M")})
    st["pending_rejects"] = rej[-80:]
    json.dump(st, open(NZT_FILE, "w", encoding="utf-8"), indent=2)

def evolve_nzt_cortex(cp_mod):
    """Rozlicza odrzucone propozycje na swiecach 15m (MFE/MAE) i zapisuje czy blokada byla sluszna."""
    st = load_nzt()
    now_t, still_pending = time.time(), []
    res_list = st.get("resolved_rejects", [])
    for r in st.get("pending_rejects", []):
        if now_t - float(r.get("ts", 0)) < 5400:
            still_pending.append(r); continue
        kl = cp_mod.fetch_klines("BITGET", r["sym"], "15m", 12)
        if not kl or len(kl.get("c", [])) < 6: continue
        td = 1 if r["side"] == "LONG" else -1
        sd = abs(r["price"] - r["stop"]) or (r["price"] * 0.01)
        mfe_r = round(max((td * (float(x) - r["price"])) / sd for x in (kl["h"][-6:] if td == 1 else kl["l"][-6:])), 2)
        mae_r = round(min((td * (float(x) - r["price"])) / sd for x in (kl["l"][-6:] if td == 1 else kl["h"][-6:])), 2)
        if mae_r <= -1.0 and mfe_r < 1.0:
            st["saved_losses"] = int(st.get("saved_losses", 0)) + 1
            verdict, would_r = "✅ SŁUSZNA BLOKADA (Uratowano SL)", -1.07
        elif mfe_r >= 1.5:
            st["missed_wins"] = int(st.get("missed_wins", 0)) + 1
            verdict, would_r = f"❌ STRACONA OKAZJA (Poszło +{mfe_r:.1f}R)", round(min(2.0, mfe_r) - 0.07, 2)
        else:
            verdict, would_r = "⚪ NEUTRALNA (Brak wybicia)", 0.0
        res_list.append({"time": r.get("time_str", "-"), "sym": r["sym"], "side": r["side"], "blocked_by": r.get("blocked_by", r.get("reason", "")), "mfe_r": mfe_r, "mae_r": mae_r, "would_be_r": would_r, "verdict": verdict})
    st["pending_rejects"] = still_pending
    st["resolved_rejects"] = res_list[-150:]
    json.dump(st, open(NZT_FILE, "w", encoding="utf-8"), indent=2)
    return st

def get_nzt_status_line(cp_mod):
    """Zwraca zwiezly raport inteligencji NZT-48 (liczba cykli nauki i uratowane straty)."""
    st = evolve_nzt_cortex(cp_mod)
    iq = 100 + min(85, int(st.get("iq_cycles", 0)) // 15 + int(st.get("saved_losses", 0)) * 2)
    return f"💊 <b>NZT-48 Cortex IQ {iq}:</b> Cykle nauki: <b>{st.get('iq_cycles', 0)}</b> | Uratowane SL: <b>{st.get('saved_losses', 0)}</b> | Stracone okazje: <b>{st.get('missed_wins', 0)}</b>"
