import quantum_nash_mod as qnm
import os, json, math, time

_LEAD_CACHE = {"ts": 0, "dir": 0, "pct": 0.0}

def evaluate_knn_pattern(side, prob, adx_v, sl_pct, hour):
    """Algorytm KNN: porownuje setup z 8 najbardziej podobnymi zagraniami z laboratoriow."""
    rows = []
    for fn in ("cfd_live_history.json", "market_shadow_lab.json", "wild_market_lab.json"):
        if os.path.exists(fn):
            try: rows.extend(json.load(open(fn, encoding="utf-8")))
            except Exception: pass
    closed = [r for r in rows if r.get("closed_final") and r.get("side") == side]
    if len(closed) < 8: return True, 0, "🤖 KNN: Zbieranie bazy"
    scored = []
    for r in closed:
        dp = (float(prob) - float(r.get("prob", 55))) / 15.0
        ds = (float(sl_pct) - float(r.get("sl_dist_pct", 1.5))) / 1.5
        dh = min(abs(int(hour) - int(r.get("hour", 12))), 24 - abs(int(hour) - int(r.get("hour", 12)))) / 6.0
        scored.append((math.sqrt(dp*dp + ds*ds + dh*dh), (float(r.get("res_r", 0)) - 0.07) * qnm.liquid_decay_weight(r.get("ts", 0))))
    scored.sort(key=lambda x: x.__getitem__(0))
    top8 = scored.__getitem__(slice(0, 8))
    wins = sum(1 for _, net in top8 if net > 0)
    avg_n = sum(net for _, net in top8) / 8.0
    if wins <= 2 and avg_n < -0.35: return False, -10, f"🤖 KNN Blokada ({wins}/8)"
    if wins >= 6 and avg_n > 0.25: return True, 6, f"🤖 KNN Match {wins}/8 (+{avg_n:.2f}R)"
    return True, 0, f"🤖 KNN {wins}/8"

def get_lead_lag_impulse(cp_mod, sym):
    """Wykrywa efekt domina Lead-Lag (zgodny impuls BTC+ETH+SOL na 5m wyprzedzajacy alty)."""
    if sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"): return 0, ""
    now_t = time.time()
    if now_t - _LEAD_CACHE["ts"] > 120:
        mv = []
        for ld in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            kl = cp_mod.fetch_klines("BITGET", ld, "5m", 4)
            if kl and len(kl.get("c", [])) >= 4:
                c0, c1 = float(kl["c"][-4]), float(kl["c"][-1])
                mv.append(((c1 - c0) / max(1e-9, c0)) * 100.0)
        if len(mv) == 3 and all(m > 0.35 for m in mv): _LEAD_CACHE.update({"ts": now_t, "dir": 1, "pct": round(sum(mv)/3.0, 2)})
        elif len(mv) == 3 and all(m < -0.35 for m in mv): _LEAD_CACHE.update({"ts": now_t, "dir": -1, "pct": round(sum(mv)/3.0, 2)})
        else: _LEAD_CACHE.update({"ts": now_t, "dir": 0, "pct": 0.0})
    return (_LEAD_CACHE["dir"], f"⚡ AI LEAD-LAG ({_LEAD_CACHE['pct']:+.2f}%)") if _LEAD_CACHE["dir"] != 0 else (0, "")

def calc_kelly_risk_pct(base_risk_pct=1.0):
    """Oblicza bezpieczny ulamkowy rozmiar ryzyka (0.25x Kelly) z ostatnich 30 zamknietych zagran."""
    rows = []
    for fn in ("cfd_live_history.json", "market_shadow_lab.json"):
        if os.path.exists(fn):
            try: rows.extend(json.load(open(fn, encoding="utf-8")))
            except Exception: pass
    closed = [r for r in rows if r.get("closed_final")][-30:]
    if len(closed) < 10: return round(float(base_risk_pct), 2), "Standard (zbieranie probki)"
    wins = [(float(r.get("res_r", 0)) - 0.07) * qnm.liquid_decay_weight(r.get("ts", 0)) for r in closed if float(r.get("res_r", 0)) > 0.07]
    losses = [abs((float(r.get("res_r", 0)) - 0.07) * qnm.liquid_decay_weight(r.get("ts", 0))) for r in closed if float(r.get("res_r", 0)) <= 0.07]
    if not wins or not losses: return round(max(0.4, float(base_risk_pct) * 0.5), 2), "Ochronny 0.5x"
    wp = len(wins) / len(closed)
    po = (sum(wins) / len(wins)) / max(0.1, (sum(losses) / len(losses)))
    kf = wp - ((1.0 - wp) / po)
    return round(max(0.35, min(1.5, kf * 25.0)), 2), f"Kelly 0.25x (WR {int(wp*100)}%)"
