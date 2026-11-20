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
import time, requests
from datetime import datetime, timezone

SESS = requests.Session()
CACHE_DERIV = {}
BTC_24H_RET = {"ts": 0, "ret": 0.0}

def get_btc_24h_return(cp):
    if time.time() - BTC_24H_RET["ts"] < 180:
        return BTC_24H_RET["ret"]
    kl = cp.fetch_klines("BITGET", "BTCUSDT", "1h", 26) or cp.fetch_klines("BITBASE", "BTCUSDT", "1h", 26)
    if kl and len(kl["c"]) >= 25:
        r = ((kl["c"].__getitem__(-1) - kl["c"].__getitem__(-25)) / (kl["c"].__getitem__(-25) or 1.0)) * 100.0
        BTC_24H_RET.update({"ts": time.time(), "ret": round(r, 2)})
        return BTC_24H_RET["ret"]
    return 0.0

def get_derivatives_metrics(sym):
    now = time.time()
    if sym in CACHE_DERIV and now - CACHE_DERIV[sym]["ts"] < 300:
        return CACHE_DERIV[sym]["data"]
    sl = chr(47)
    u_fr = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "current-fund-rate"])
    u_oi = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "open-interest"])
    fr, oi = 0.0, 0.0
    try:
        r1 = SESS.get(u_fr, params={"symbol": sym, "productType": "USDT-FUTURES"}, timeout=4).json()
        d1 = r1.get("data", [])
        if d1: fr = float(d1.__getitem__(0).get("fundingRate", 0.0)) * 100.0
    except Exception:
        pass
    try:
        r2 = SESS.get(u_oi, params={"symbol": sym, "productType": "USDT-FUTURES"}, timeout=4).json()
        d2 = r2.get("data", {}).get("openInterestList", [])
        if d2: oi = float(d2.__getitem__(0).get("size", 0.0))
    except Exception:
        pass
    out = {"funding_pct": round(fr, 4), "oi": oi}
    CACHE_DERIV[sym] = {"ts": now, "data": out}
    return out

def detect_sweep_reclaim(kl):
    if not kl or len(kl["c"]) < 25: return 0
    h, l, c, v = kl["h"], kl["l"], kl["c"], kl["v"]
    lo20 = min(l.__getitem__(slice(-22, -2)))
    hi20 = max(h.__getitem__(slice(-22, -2)))
    vol_avg = sum(v.__getitem__(slice(-22, -2))) / 20.0 or 1.0
    # Bullish Sweep & Reclaim: poprzednia/obecna swieca wybila dolek 20-swiecowy, ale zamknela sie powyzej z wolumenem
    if (l.__getitem__(-1) < lo20 or l.__getitem__(-2) < lo20) and c.__getitem__(-1) > lo20 and c.__getitem__(-1) > c.__getitem__(-2) and v.__getitem__(-1) >= vol_avg * 1.1:
        return 1
    # Bearish Sweep & Reclaim: wybila szczyt 20-swiecowy, ale wrocila ponizej
    if (h.__getitem__(-1) > hi20 or h.__getitem__(-2) > hi20) and c.__getitem__(-1) < hi20 and c.__getitem__(-1) < c.__getitem__(-2) and v.__getitem__(-1) >= vol_avg * 1.1:
        return -1
    return 0

def get_session_badge():
    hr = datetime.now().hour
    if 9 <= hr <= 12: return "🔥 SESJA LONDYN (Wysoka plynnosc)"
    if 14 <= hr <= 18: return "🔥 SESJA NOWY JORK (Szczyt wolumenu)"
    if datetime.now().weekday() >= 5: return "⚠️ WEEKEND (Niska plynnosc)"
    return "🕒 SESJA STANDARDOWA"

def get_equity_risk_multiplier(pf_list):
    # Ochrona krzywej kapitalu: po 3 zamknietych stratach z rzedu tnie ryzyko o 50%
    closed = [p for p in pf_list if p.get("status") == "CLOSED"]
    if len(closed) >= 3 and all(p.get("pnl", 0) < 0 for p in closed.__getitem__(slice(-3, None))):
        return 0.5
    return 1.0

def evaluate_alpha(cp, sym, side, kl_1h):
    deriv = get_derivatives_metrics(sym)
    fr = deriv["funding_pct"]
    # Odrzucamy skrajnie przegrzane pozycje (Funding > +0.045% dla LONG lub < -0.045% dla SHORT)
    if side == "LONG" and fr > 0.045:
        return False, -15, f"🚫 Overheated Funding ({fr:+.3f}%)"
    if side == "SHORT" and fr < -0.045:
        return False, -15, f"🚫 Overheated Funding ({fr:+.3f}%)"

    btc_r = get_btc_24h_return(cp)
    coin_r = 0.0
    if kl_1h and len(kl_1h["c"]) >= 25:
        coin_r = ((kl_1h["c"].__getitem__(-1) - kl_1h["c"].__getitem__(-25)) / (kl_1h["c"].__getitem__(-25) or 1.0)) * 100.0
    rs_diff = round(coin_r - btc_r, 2)
    sweep = detect_sweep_reclaim(kl_1h)
    sqz = detect_ttm_squeeze(kl_1h)

    bonus = 0
    tags = []
    if (side == "LONG" and rs_diff >= 1.5) or (side == "SHORT" and rs_diff <= -1.5):
        bonus += 6
        tags.append(f"💪 RS vs BTC {rs_diff:+.1f}%")
    if (side == "LONG" and sweep == 1) or (side == "SHORT" and sweep == -1):
        bonus += 8
        tags.append("🧲 Sweep & Reclaim")
    if (side == "LONG" and sqz == 1) or (side == "SHORT" and sqz == -1):
        bonus += 9
        tags.append("💥 SQUEEZE CFD")
    if abs(fr) <= 0.02:
        bonus += 3
        tags.append(f"FR {fr:+.3f}%")

    return True, bonus, " | ".join(tags) if tags else f"FR {fr:+.3f}% | RS {rs_diff:+.1f}%"

def detect_ttm_squeeze(kl):
    if not kl or len(kl["c"]) < 25: return 0
    h, l, c, v = kl["h"], kl["l"], kl["c"], kl["v"]
    win = c.__getitem__(slice(-21, -1))
    mid = sum(win) / 20.0
    std = (sum((x - mid) ** 2 for x in win) / 20.0) ** 0.5
    bb_w = 4.0 * std
    trs = [max(h.__getitem__(k) - l.__getitem__(k), abs(h.__getitem__(k) - c.__getitem__(k - 1)), abs(l.__getitem__(k) - c.__getitem__(k - 1))) for k in range(-20, 0)]
    atr20 = sum(trs) / 20.0 or 1e-9
    kc_w = 3.0 * atr20
    # Scisniecie BB wewnatrz Keltnera + wybicie obecnej swiecy z wolumenem
    vol_avg = sum(v.__getitem__(slice(-21, -1))) / 20.0 or 1.0
    if bb_w < kc_w and v.__getitem__(-1) >= vol_avg * 1.25:
        if c.__getitem__(-1) > mid + 1.8 * std: return 1
        if c.__getitem__(-1) < mid - 1.8 * std: return -1
    return 0

CACHE_TOP60 = {"ts": 0, "syms": []}

def get_cfd_top60_symbols():
    now = time.time()
    if CACHE_TOP60["syms"] and now - CACHE_TOP60["ts"] < 1800:
        return CACHE_TOP60["syms"]
    fallback = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","TRXUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","LTCUSDT","BCHUSDT","NEARUSDT","INJUSDT","APTUSDT","UNIUSDT","ATOMUSDT","FILUSDT","SUIUSDT","TONUSDT","OPUSDT","ARBUSDT","SEIUSDT","TIAUSDT","RENDERUSDT","FETUSDT","AAVEUSDT","RUNEUSDT","LDOUSDT","GRTUSDT","IMXUSDT","STXUSDT","ICPUSDT","ALGOUSDT","PEPEUSDT","WIFUSDT","ENAUSDT","ONDOUSDT","TAOUSDT","WLDUSDT","JUPUSDT","PYTHUSDT","PENDLEUSDT","STRKUSDT","EIGENUSDT","ZKUSDT","NOTUSDT","GALAUSDT","SANDUSDT","MANAUSDT","CRVUSDT","MKRUSDT","SNXUSDT","COMPUSDT","DYDXUSDT","ENSUSDT","CHZUSDT","AXSUSDT","EGLDUSDT"]
    try:
        sl = chr(47)
        u = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "tickers"])
        r = SESS.get(u, params={"productType": "USDT-FUTURES"}, timeout=6).json()
        rows = []
        for it in r.get("data", []):
            sym = it.get("symbol", "")
            vol_u = float(it.get("usdtVolume", 0) or 0)
            if sym.endswith("USDT") and vol_u >= 10000000:
                rows.append((sym, vol_u))
        rows.sort(key=lambda x: -x.__getitem__(1))
        if len(rows) >= 25:
            syms = [x.__getitem__(0) for x in rows.__getitem__(slice(0, 60))]
            CACHE_TOP60.update({"ts": now, "syms": syms})
            return syms
    except Exception:
        pass
    return fallback

def validate_cfd_order(entry, stop, cur_price):
    if entry <= 0 or stop <= 0 or cur_price <= 0: return False
    sl_pct = abs(entry - stop) / entry * 100.0
    cur_diff_pct = abs(entry - cur_price) / cur_price * 100.0
    # Gielda/CFD wymaga min. 0.35% dystansu do SL (poza spreadem) i max 6.5% SL, oraz min. 0.12% dla zlecenia oczekujacego
    if sl_pct < 0.35 or sl_pct > 6.5: return False
    if cur_diff_pct > 0 and cur_diff_pct < 0.12: return False
    return True

def get_mtf_status_line(ex, sym, side):
    td = 1 if side == "LONG" else -1
    res, ok_cnt = [], 0
    for tf in ("15m", "1h", "4h", "1d"):
        try:
            kl = fetch_klines(ex, sym, tf, 60)
            if kl and len(kl["c"]) >= 50:
                c_now = kl["c"].__getitem__(-1)
                e21 = ema(kl["c"], 21).__getitem__(-1)
                e50 = ema(kl["c"], 50).__getitem__(-1)
                ok = (c_now > e21 and e21 > e50) if td == 1 else (c_now < e21 and e21 < e50)
                if ok: ok_cnt += 1
                res.append(f"{tf.upper()} {'✅' if ok else '⚠️'}")
            else:
                res.append(f"{tf.upper()} ➖")
        except Exception:
            res.append(f"{tf.upper()} ➖")
    return f"📊 <b>MTF ({ok_cnt}/4):</b> " + " | ".join(res)
