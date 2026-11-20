import os, json, math, time
from datetime import datetime

CHAMP_FILE = "evolution_champion.json"

def detect_volatility_regime(kl_15m):
    """Wykrywa rezim zmiennosci (Ekspansja Trendowa, Kompresja Sprezyny lub Losowy Szum Chop)."""
    if not kl_15m or len(kl_15m.get("c", [])) < 32:
        return "NORMAL", 0, "⚖️ Rezim standardowy"
    h, l, c = [float(x) for x in kl_15m["h"]], [float(x) for x in kl_15m["l"]], [float(x) for x in kl_15m["c"]]
    trs = [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])) for i in range(1, len(c))]
    atr5 = sum(trs[-5:]) / 5.0
    atr30 = sum(trs[-30:]) / 30.0
    ratio = atr5 / max(1e-9, atr30)
    net_move = abs(c[-1] - c[-15]) / max(1e-9, sum(trs[-15:]))
    if ratio < 0.62:
        return "SQUEEZE", 5, f"🌀 Kompresja Sprezyny ({ratio:.2f}x)"
    if ratio > 1.15 and net_move > 0.28:
        return "TREND", 4, f"🚀 Ekspansja Trendowa ({ratio:.2f}x)"
    if net_move < 0.14:
        return "CHOP", -8, f"🛡️ CHOP SHIELD (Szum {net_move:.2f})"
    return "NORMAL", 0, f"⚖️ Rezim stabilny ({ratio:.2f}x)"

def check_portfolio_correlation(cp_mod, new_sym, active_positions):
    """Liczy korelacje Pearsona (48 swiec 15m) miedzy nowa para a otwartymi pozycjami w portfelu."""
    if not active_positions:
        return 0.0, ""
    kl_new = cp_mod.fetch_klines("BITGET", new_sym, "15m", 50)
    if not kl_new or len(kl_new.get("c", [])) < 48:
        return 0.0, ""
    c_a = [float(x) for x in kl_new["c"][-48:]]
    r_a = [(c_a[i] - c_a[i-1]) / max(1e-9, c_a[i-1]) for i in range(1, len(c_a))]
    max_corr, max_pair = 0.0, ""
    for pos in active_positions:
        psym = pos.get("symbol", "")
        if not psym or psym == new_sym: continue
        kl_p = cp_mod.fetch_klines("BITGET", psym, "15m", 50)
        if not kl_p or len(kl_p.get("c", [])) < 48: continue
        c_b = [float(x) for x in kl_p["c"][-48:]]
        r_b = [(c_b[i] - c_b[i-1]) / max(1e-9, c_b[i-1]) for i in range(1, len(c_b))]
        ma, mb = sum(r_a)/len(r_a), sum(r_b)/len(r_b)
        cov = sum((r_a[i]-ma)*(r_b[i]-mb) for i in range(len(r_a)))
        den = math.sqrt(sum((x-ma)**2 for x in r_a) * sum((y-mb)**2 for y in r_b))
        corr = round(cov / max(1e-12, den), 2)
        if abs(corr) > abs(max_corr):
            max_corr, max_pair = corr, psym
    if max_corr >= 0.78:
        return max_corr, f"⚠️ KRYTYCZNA KORELACJA {max_corr:.2f} z {max_pair} — dublujesz ryzyko!"
    return max_corr, ""

def run_evolution_tournament():
    """Ewolucyjny turniej parametrow na zamknietych danych z laboratoriow (wybiera najlepszy profil)."""
    rows = []
    for fn in ("cfd_live_history.json", "market_shadow_lab.json", "wild_market_lab.json"):
        if os.path.exists(fn):
            try: rows.extend(json.load(open(fn, encoding="utf-8")))
            except Exception: pass
    closed = [r for r in rows if r.get("closed_final")]
    best = {"min_prob": 55, "side_bias": "BOTH", "net_r": 0.0, "samples": len(closed), "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}
    for mp in (50, 53, 55, 58, 62):
        for sb in ("BOTH", "LONG", "SHORT"):
            sub = [r for r in closed if int(r.get("prob", 0)) >= mp and (sb == "BOTH" or r.get("side") == sb)]
            if len(sub) >= 5:
                nr = round(sum(float(r.get("res_r", 0)) - 0.07 for r in sub), 2)
                if nr > best["net_r"]:
                    best.update({"min_prob": mp, "side_bias": sb, "net_r": nr, "samples": len(sub)})
    json.dump(best, open(CHAMP_FILE, "w", encoding="utf-8"), indent=2)
    return best
