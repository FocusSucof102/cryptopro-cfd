import json, math, urllib.request

def check_binance_futures_lead(sym, side, local_price):
    """Porownuje cene lokalna z Binance Futures (wykrywa wyprzedzajacy impuls plynnosci)."""
    try:
        u = "".join(["https://binance.com", "/fapi/v1/ticker/price?symbol=", sym])
        bn_p = float(json.loads(urllib.request.urlopen(u, timeout=4).read().decode()).get("price", 0))
        if bn_p <= 0 or local_price <= 0: return 0, ""
        diff_pct = ((bn_p - local_price) / local_price) * 100.0
        if side == "LONG" and diff_pct >= 0.14: return 4, f"⚡ Binance Lead +{diff_pct:.2f}%"
        if side == "SHORT" and diff_pct <= -0.14: return 4, f"⚡ Binance Lead {diff_pct:.2f}%"
        return 0, ""
    except Exception:
        return 0, ""

def profile_coin_fingerprint(kl_15m):
    """Adversarial Coin Fingerprinting: bada styl danej monety (szpilkarz vs czysty trend)."""
    if not kl_15m or len(kl_15m.get("c", [])) < 25:
        return 1.0, 0, "🧬 Profil standard"
    o, h, l, c = [float(x) for x in kl_15m["o"][-25:]], [float(x) for x in kl_15m["h"][-25:]], [float(x) for x in kl_15m["l"][-25:]], [float(x) for x in kl_15m["c"][-25:]]
    wick_ratios = [((h[i] - l[i]) - abs(c[i] - o[i])) / max(1e-9, h[i] - l[i]) for i in range(len(c))]
    avg_wick = sum(wick_ratios) / len(wick_ratios)
    if avg_wick > 0.68:
        return 1.25, -3, f"🧬 Szpilkarz (SL x1.25 | knoty {int(avg_wick*100)}%)"
    if avg_wick < 0.42:
        return 0.90, 4, f"🧬 Czysty Trend (knoty {int(avg_wick*100)}%)"
    return 1.0, 0, f"🧬 Profil zrównoważony"

def check_extreme_tail_and_social(sym, kl_15m, news_list):
    """Extreme Value Theory (ochrona przed krachem grubego ogona) + Social Velocity Spike w RSS."""
    if kl_15m and len(kl_15m.get("c", [])) >= 20:
        c = [float(x) for x in kl_15m["c"][-20:]]
        rets = [abs((c[i] - c[i-1]) / max(1e-9, c[i-1])) for i in range(1, len(c))]
        avg_r = sum(rets[:-1]) / max(1, len(rets) - 1)
        if rets[-1] > avg_r * 4.8 and rets[-1] > 0.035:
            return False, -12, "🦢 BLACK SWAN TAIL LOCK (Ekstremalny skok zmienności)"
    base_coin = sym.replace("USDT", "").upper()
    hits = sum(1 for n in (news_list or []) if base_coin in str(n).upper())
    if hits >= 2:
        return True, 5, f"🔥 Social Velocity Spike ({hits} wzmianek RSS)"
    return True, 0, "🦢 Tail OK"
