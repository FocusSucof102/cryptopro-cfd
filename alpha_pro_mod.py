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
#    - Zrodlo danych/API skanera: wylacznie BITGET USDT-FUTURES (co najmniej 15M USDT/24h).
#    - Platforma gry uzytkownika: BITBASE FUTURES / CFD (uwzgledniac przy prowizjach,
#      dostepnosci par, dźwigni i minimalnych odleglosciach zlecen!).
#    - Silnik: Smart Dual-Mode (LONG+SHORT), Auto-Tuner, Audytor 1M (MFE/MAE),
#      Shadow Market Lab (analiza niskich procentow 45-61% netto po prowizji),
#      Straznik Portfela 24/7 oraz Radar Aktywnych Pozycji 60s.
# 4. NIE PRZYWRACAC: Zablokowanych API (BINANCE/BYBIT), 500 niszowych mikrotokentow
#    ani twardej blokady tylko jednego kierunku handlu.
# ==============================================================================
import time, requests, math
from datetime import datetime, timezone

SESS = requests.Session()
CACHE_DERIV = {}
BTC_24H_RET = {"ts": 0, "ret": 0.0}
STABLECOIN_BLACKLIST = {"BFUSD", "USDC", "USD1", "RLUSD", "FDUSD", "DAI", "TUSD", "USDE", "USDD", "PYUSD", "EURC"}

def get_btc_24h_return(cp):
    """Oblicza zwrot BTC (24h) z cache 3 min. Parametry: cp."""
    if time.time() - BTC_24H_RET["ts"] < 180:
        return BTC_24H_RET["ret"]
    kl = cp.fetch_klines("BITGET", "BTCUSDT", "1h", 26) or cp.fetch_klines("BITBASE", "BTCUSDT", "1h", 26)
    if kl and len(kl["c"]) >= 25:
        r = ((kl["c"].__getitem__(-1) - kl["c"].__getitem__(-25)) / (kl["c"].__getitem__(-25) or 1.0)) * 100.0
        BTC_24H_RET.update({"ts": time.time(), "ret": round(r, 2)})
        return BTC_24H_RET["ret"]
    return 0.0

def get_derivatives_metrics(sym):
    """Pobiera Funding Rate (%) i Open Interest (OI) z Bitget. Parametry: sym."""
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
    """Wykrywa formacje Liquidity Sweep & Reclaim na 20 swiecach. Parametry: kl."""
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
    """Zwraca etykiete aktywnej sesji (Londyn, NY, Weekend)."""
    hr = datetime.now().hour
    if 9 <= hr <= 12: return "🔥 SESJA LONDYN (Wysoka plynnosc)"
    if 14 <= hr <= 18: return "🔥 SESJA NOWY JORK (Szczyt wolumenu)"
    if datetime.now().weekday() >= 5: return "⚠️ WEEKEND (Niska plynnosc)"
    return "🕒 SESJA STANDARDOWA"

def get_equity_risk_multiplier(pf_list):
    # Ochrona krzywej kapitalu: po 3 zamknietych stratach z rzedu tnie ryzyko o 50%
    """Tnie ryzyko o 50% po serii 3 zamknietych strat z rzedu. Parametry: pf_list."""
    closed = [p for p in pf_list if p.get("status") == "CLOSED"]
    if len(closed) >= 3 and all(p.get("pnl", 0) < 0 for p in closed.__getitem__(slice(-3, None))):
        return 0.5
    return 1.0

def evaluate_alpha(cp, sym, side, kl_1h):
    """Ocenia jakosc sygnalu (Funding, RS vs BTC, Sweep, Squeeze). Parametry: cp, sym, side, kl_1h."""
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
    """Wykrywa scisniecie BB wewnatrz Keltnera (TTM Squeeze). Parametry: kl."""
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
MIN_LIQUIDITY_24H_USDT = 15000000.0

def is_liquid_24h_volume(volume_usdt):
    """Returns whether a futures pair meets the fixed 15M USDT 24h turnover floor."""
    try:
        volume = float(volume_usdt)
    except (TypeError, ValueError):
        return False
    return math.isfinite(volume) and volume >= MIN_LIQUIDITY_24H_USDT

def get_upcoming_funding_warning(side, funding_pct, now_utc=None):
    """Warns when adverse funding above 0.05% settles in under 30 minutes."""
    direction = str(side).upper()
    if direction not in ("LONG", "SHORT"):
        raise ValueError("Direction must be LONG or SHORT")
    rate = float(funding_pct)
    if direction == "LONG" and rate <= 0.05:
        return ""
    if direction == "SHORT" and rate >= -0.05:
        return ""
    current_time = now_utc or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    current_time = current_time.astimezone(timezone.utc)
    seconds_today = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
    seconds_to_funding = 8 * 3600 - (seconds_today % (8 * 3600))
    if seconds_to_funding >= 30 * 60:
        return ""
    minutes = max(1, int(seconds_to_funding // 60))
    next_seconds = seconds_today + seconds_to_funding
    funding_hour = (next_seconds // 3600) % 24
    return (
        f"⚠️ WYSOKI FUNDING: {rate:+.3f}% — naliczenie za {minutes} min "
        f"({funding_hour:02d}:00 UTC), niekorzystne dla {direction}."
    )

def get_cfd_top60_symbols():
    """Fetches Bitget USDT futures pairs with at least 15M USDT of 24h turnover."""
    now = time.time()
    if CACHE_TOP60["syms"] and now - CACHE_TOP60["ts"] < 300:
        return CACHE_TOP60["syms"]
    try:
        sl = chr(47)
        u = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "tickers"])
        r = SESS.get(u, params={"productType": "USDT-FUTURES"}, timeout=6).json()
        rows = []
        for it in r.get("data", []):
            sym = it.get("symbol", "")
            base = sym.replace("USDT", "")
            if base in STABLECOIN_BLACKLIST or any(sb == base for sb in STABLECOIN_BLACKLIST):
                continue
            vol_u = float(it.get("usdtVolume", 0) or 0)
            if sym.endswith("USDT") and is_liquid_24h_volume(vol_u):
                rows.append((sym, vol_u))
        rows.sort(key=lambda x: -x.__getitem__(1))
        if len(rows) < 25:
            print(f"BITGET_LIQUIDITY_FILTER: only {len(rows)} pairs meet 15M USDT/24h", flush=True)
            return []
        syms = [x.__getitem__(0) for x in rows.__getitem__(slice(0, 100)) if not any(x.__getitem__(0).startswith(sb) for sb in STABLECOIN_BLACKLIST)]
        CACHE_TOP60.update({"ts": now, "syms": syms})
        return syms
    except Exception as err:
        print(f"BITGET_LIQUIDITY_FILTER_ERR: {err}", flush=True)
        return []

def validate_cfd_order(entry, stop, cur_price):
    """Waliduje dystans zlecenia i SL (0.35%-6.5%) pod wymogi CFD. Parametry: entry, stop, cur_price."""
    if entry <= 0 or stop <= 0 or cur_price <= 0: return False
    sl_pct = abs(entry - stop) / entry * 100.0
    cur_diff_pct = abs(entry - cur_price) / cur_price * 100.0
    # Gielda/CFD wymaga min. 0.35% dystansu do SL (poza spreadem) i max 6.5% SL, oraz min. 0.12% dla zlecenia oczekujacego
    if sl_pct < 0.35 or sl_pct > 6.5: return False
    if cur_diff_pct > 0 and cur_diff_pct < 0.12: return False
    return True

def get_mtf_status_line(ex, sym, side):
    """Buduje pasek zgodnosci trendu MTF (15M|1H|4H|1D). Parametry: ex, sym, side."""
    import crypto_pro as cp
    td = 1 if side == "LONG" else -1
    res, ok_cnt = [], 0
    for tf in ("15m", "1h", "4h", "1d"):
        try:
            kl = _apm_klines(ex, sym, tf, 60)
            if kl and len(kl["c"]) >= 50:
                c_now = kl["c"].__getitem__(-1)
                e21 = cp.ema(kl["c"], 21).__getitem__(-1)
                e50 = cp.ema(kl["c"], 50).__getitem__(-1)
                ok = (c_now > e21 and e21 > e50) if td == 1 else (c_now < e21 and e21 < e50)
                if ok: ok_cnt += 1
                res.append(f"{tf.upper()} {'✅' if ok else '⚠️'}")
            else:
                res.append(f"{tf.upper()} ➖")
        except Exception:
            res.append(f"{tf.upper()} ➖")
    return f"📊 <b>MTF ({ok_cnt}/4):</b> " + " | ".join(res)

def get_wild_61_160_symbols():
    """Realizuje logike: get wild 61 160 symbols."""
    try:
        sl = chr(47)
        u = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "tickers"])
        r = SESS.get(u, params={"productType": "USDT-FUTURES"}, timeout=6).json()
        rows = []
        for it in r.get("data", []):
            sym = it.get("symbol", "")
            vol_u = float(it.get("usdtVolume", 0) or 0)
            if sym.endswith("USDT") and 1000000 <= vol_u < 10000000:
                rows.append((sym, vol_u))
        rows.sort(key=lambda x: -x.__getitem__(1))
        return [x.__getitem__(0) for x in rows.__getitem__(slice(0, 80))]
    except Exception:
        return []

def detect_weird_move(ex, sym):
    """Realizuje logike: detect weird move. Parametry: ex, sym."""
    try:
        kl = _apm_klines(ex, sym, "15m", 25)
        if not kl or len(kl["c"]) < 20: return ""
        o, h, l, c, v = kl["o"].__getitem__(-1), kl["h"].__getitem__(-1), kl["l"].__getitem__(-1), kl["c"].__getitem__(-1), kl["v"].__getitem__(-1)
        avg_v = sum(kl["v"].__getitem__(slice(-20, -1))) / 19.0
        rng = max(1e-9, h - l)
        body = abs(c - o)
        wick_ratio = (rng - body) / rng
        vol_spike = v / max(1e-9, avg_v)
        tags = []
        if vol_spike >= 4.0: tags.append(f"VOL_SPIKE_{vol_spike:.1f}x")
        if wick_ratio >= 0.65 and (rng / max(1e-9, c)) >= 0.015: tags.append("LONG_WICK_HUNT")
        return "+".join(tags)
    except Exception:
        return ""

def get_micro_161_plus_symbols():
    """Realizuje logike: get micro 161 plus symbols."""
    try:
        sl = chr(47)
        u = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "tickers"])
        r = SESS.get(u, params={"productType": "USDT-FUTURES"}, timeout=6).json()
        rows = []
        for it in r.get("data", []):
            sym = it.get("symbol", "")
            vol_u = float(it.get("usdtVolume", 0) or 0)
            if sym.endswith("USDT") and 50000 <= vol_u < 1000000:
                rows.append((sym, vol_u))
        rows.sort(key=lambda x: -x.__getitem__(1))
        return [x.__getitem__(0) for x in rows.__getitem__(slice(0, 100))]
    except Exception:
        return []

def _apm_klines(ex, sym, tf, lim):
    """Realizuje logike: apm klines. Parametry: ex, sym, tf, lim."""
    import crypto_pro as cp
    return cp.fetch_klines(ex, sym, tf, lim)

def detect_cyclical_and_pump_dump(ex, sym):
    """Realizuje logike: detect cyclical and pump dump. Parametry: ex, sym."""
    try:
        kl = _apm_klines(ex, sym, "15m", 120)
        if not kl or len(kl["c"]) < 60: return "NO_DATA", 0.0, ""
        vols, highs, lows, opens, closes = kl["v"], kl["h"], kl["l"], kl["o"], kl["c"]
        avg_v = sum(vols) / len(vols)
        spike_idxs = [i for i in range(len(vols)) if vols.__getitem__(i) >= avg_v * 3.5]
        cyc_tag, gap_h = "SINGLE_IMPULSE", 0.0
        if len(spike_idxs) >= 2:
            gap_h = round((spike_idxs.__getitem__(-1) - spike_idxs.__getitem__(-2)) * 0.25, 2)
            cyc_tag = f"CYCLIC_{gap_h}H"
        # Detekcja Pump & Dump na ostatnich 4 swiecach 15m
        p_idx = -3
        base_p = float(opens.__getitem__(p_idx))
        peak_p = max(float(highs.__getitem__(j)) for j in range(-3, 0))
        cur_p = float(closes.__getitem__(-1))
        pump_pct = ((peak_p - base_p) / max(1e-9, base_p)) * 100.0
        retrace = ((peak_p - cur_p) / max(1e-9, peak_p - base_p)) if peak_p > base_p else 0.0
        max_v_spike = max(float(vols.__getitem__(j)) for j in range(-3, 0)) / max(1e-9, avg_v)
        pd_tag = ""
        if pump_pct >= 3.5 and max_v_spike >= 4.0:
            pd_tag = f"PUMP_DUMP_{pump_pct:.1f}%" if retrace >= 0.45 else f"ACTIVE_PUMP_{pump_pct:.1f}%"
        return cyc_tag, gap_h, pd_tag
    except Exception:
        return "ERR", 0.0, ""


def get_all_futures_symbols():
    """Realizuje logike: get all futures symbols."""
    try:
        sl = chr(47)
        u = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "tickers"])
        r = SESS.get(u, params={"productType": "USDT-FUTURES"}, timeout=8).json()
        rows = []
        for it in r.get("data", []):
            sym = it.get("symbol", "")
            vol_u = float(it.get("usdtVolume", 0) or 0)
            if sym.endswith("USDT") and vol_u >= 25000:
                rows.append((sym, vol_u))
        rows.sort(key=lambda x: -x[1])
        return [x[0] for x in rows]
    except Exception:
        return get_cfd_top60_symbols()

def scan_macro_pump_dump_coin(sym):
    """Skanuje kontrakt pod katem 7 archetypow Pump & Dump. Parametry: sym."""
    try:
        d1 = _apm_klines("BITGET", sym, "1d", 40)
        h4 = _apm_klines("BITGET", sym, "4h", 60)
        m15 = _apm_klines("BITGET", sym, "15m", 40)
        if not d1 or not h4 or len(d1["c"]) < 25 or len(h4["c"]) < 30:
            return None

        c1, h1, l1, v1 = d1["c"], d1["h"], d1["l"], d1["v"]
        cur = float(c1[-1])
        avg_v20 = sum(float(x) for x in v1[-21:-1]) / 20.0
        vol_mult_1d = float(v1[-1]) / max(1e-9, avg_v20)

        low_14d = min(float(x) for x in l1[-15:-1])
        high_14d = max(float(x) for x in h1[-14:])
        pump_from_low = ((cur - low_14d) / max(1e-9, low_14d)) * 100.0
        max_pump_14d = ((high_14d - low_14d) / max(1e-9, low_14d)) * 100.0
        drop_from_peak = ((high_14d - cur) / max(1e-9, high_14d)) * 100.0

        c4 = [float(x) for x in h4["c"]]
        ma7_4h = sum(c4[-7:]) / 7.0
        ma25_4h = sum(c4[-25:]) / 25.0
        atr_4h = sum(abs(float(h4["h"][j]) - float(h4["l"][j])) for j in range(-14, 0)) / 14.0

        # WZORZEC 1: Cicha akumulacja + wczesne wybicie z bazy (LONG, wzor BLZ/LOOM)
        if 15.0 <= pump_from_low <= 85.0 and vol_mult_1d >= 4.0 and cur > ma7_4h and cur > ma25_4h:
            sl = round(cur - max(cur * 0.035, atr_4h * 1.8), 6)
            sd = abs(cur - sl)
            return {
                "symbol": sym, "side": "LONG", "mode": "🚀 WZORZEC 1: WYBICIE Z BAZY",
                "win_prob": min(84, int(62 + vol_mult_1d * 2)),
                "alpha_tag": f"BAZA +{pump_from_low:.0f}% | VOL {vol_mult_1d:.1f}x",
                "pattern_fit": "Archetyp BLZ / LOOM (Wczesna akumulacja + skok wolumenu na 1D)",
                "narrative": f"Kurs wybil z wielodniowej konsolidacji (+{pump_from_low:.0f}% od dolka) przy {vol_mult_1d:.1f}-krotnym wzroscie wolumenu i utrzymuje wsparcie MA7/MA25 na 4H. Oczekiwana kontynuacja fali wzrostowej przed wejsciem tlumu FOMO.",
                "price": cur, "entry": cur, "stop": sl,
                "tp": [round(cur + sd * m, 6) for m in (1.5, 2.5, 4.0, 6.0, 10.0)]
            }

        # WZORZEC 2: Short-Squeeze Blow-Off Top z dlugim knotem szczytowym (SHORT, wzor TRB/CYBER)
        peak_bar_h = max(float(x) for x in h4["h"][-6:])
        peak_bar_c = float(h4["c"][-1])
        wick_drop_4h = ((peak_bar_h - peak_bar_c) / max(1e-9, peak_bar_h)) * 100.0
        if max_pump_14d >= 100.0 and wick_drop_4h >= 8.0 and cur < ma7_4h:
            sl = round(peak_bar_h * 1.015, 6)
            sd = abs(sl - cur)
            if 0.015 <= (sd / max(1e-9, cur)) <= 0.18:
                return {
                    "symbol": sym, "side": "SHORT", "mode": "🩸 WZORZEC 2: BLOW-OFF TOP (SQUEEZE)",
                    "win_prob": min(87, int(66 + min(16, wick_drop_4h))),
                    "alpha_tag": f"RAJD +{max_pump_14d:.0f}% | KNOT -{wick_drop_4h:.1f}%",
                    "pattern_fit": "Archetyp TRB / CYBER (Wyczerpanie Short-Squeeze i dlugi gorny knot)",
                    "narrative": f"Po pionowym rajdzie +{max_pump_14d:.0f}% pojawilo sie silne odrzucenie szczytu (-{wick_drop_4h:.1f}% od knota) i zamkniecie pod MA7 (4H). Paliwo z likwidacji shortow wygaslo — mozliwa szybka korekta w strone sredniej MA25.",
                    "price": cur, "entry": cur, "stop": sl,
                    "tp": [round(cur - sd * m, 6) for m in (1.5, 2.5, 4.0, 6.0, 10.0)]
                }

        # WZORZEC 3: Wielodniowe wykrwawianie po paraboli (SHORT, wzor OM/RAVE)
        if max_pump_14d >= 120.0 and 15.0 <= drop_from_peak <= 60.0 and cur < ma7_4h and cur < ma25_4h:
            sl = round(cur + max(cur * 0.05, atr_4h * 2.2), 6)
            sd = abs(sl - cur)
            return {
                "symbol": sym, "side": "SHORT", "mode": "🩸 WZORZEC 3: PARABOLIC RUG BLEED",
                "win_prob": min(85, int(64 + min(15, max_pump_14d / 20))),
                "alpha_tag": f"SZCZYT +{max_pump_14d:.0f}% | SPADEK -{drop_from_peak:.0f}%",
                "pattern_fit": "Archetyp RAVE / OM (Wielodniowa dystrybucja i utrata MA7/MA25 4H)",
                "narrative": f"Token po wzroscie +{max_pump_14d:.0f}% stracil juz {drop_from_peak:.0f}% od szczytu i zlamal obie srednie kroczace (MA7 oraz MA25) na 4H. Rozpoczela sie faza stopniowego wykrwawiania popytu i powrotu do bazy.",
                "price": cur, "entry": cur, "stop": sl,
                "tp": [round(cur - sd * m, 6) for m in (1.5, 2.5, 4.0, 6.0, 10.0)]
            }

        # WZORZEC 4: Szybki Flash Pump & Dump wewnatrz dnia na 15m (SHORT, pompy grupowe)
        if m15 and len(m15["c"]) >= 25:
            v15 = [float(x) for x in m15["v"]]
            avg_v15 = sum(v15[-25:-4]) / 21.0
            max_v15 = max(v15[-4:]) / max(1e-9, avg_v15)
            low_2h = min(float(x) for x in m15["l"][-8:-2])
            high_2h = max(float(x) for x in m15["h"][-4:])
            flash_pct = ((high_2h - low_2h) / max(1e-9, low_2h)) * 100.0
            retrace_15m = ((high_2h - cur) / max(1e-9, high_2h - low_2h)) if high_2h > low_2h else 0.0
            if flash_pct >= 8.0 and max_v15 >= 5.5 and retrace_15m >= 0.40:
                sl = round(high_2h * 1.01, 6)
                sd = abs(sl - cur)
                if 0.01 <= (sd / max(1e-9, cur)) <= 0.12:
                    return {
                        "symbol": sym, "side": "SHORT", "mode": "⚡ WZORZEC 4: FLASH PUMP & DUMP (15M)",
                        "win_prob": min(83, int(63 + max_v15)),
                        "alpha_tag": f"IMPULS +{flash_pct:.1f}% | VOL {max_v15:.1f}x",
                        "pattern_fit": "Archetyp Szybkiej Pompy Grupowej 15M (Skok wolumenu >5.5x + natychmiastowy zrzut)",
                        "narrative": f"Gwałtowna pompa +{flash_pct:.1f}% na {max_v15:.1f}x wolumenie zostala juz w {int(retrace_15m*100)}% zniesiona przez podaz. Wysokie prawdopodobienstwo pelnego domkniecia szpilki do poziomu wyjscia.",
                        "price": cur, "entry": cur, "stop": sl,
                        "tp": [round(cur - sd * m, 6) for m in (1.5, 2.5, 4.0, 6.0, 10.0)]
                    }
        # WZORZEC 5: Bot Ping-Pong Accumulation (rowne slupki kupna/sprzedazy przez 12h + start wybicia)
        if m15 and len(m15["c"]) >= 36:
            buy_v, sell_v = 0.0, 0.0
            for j in range(-36, -2):
                o_j, c_j, v_j = float(m15["o"][j]), float(m15["c"][j]), float(m15["v"][j])
                if c_j >= o_j: buy_v += v_j
                else: sell_v += v_j
            tot_v = buy_v + sell_v
            if tot_v > 0:
                buy_ratio = buy_v / tot_v
                box_hi = max(float(x) for x in m15["h"][-36:-2])
                box_lo = min(float(x) for x in m15["l"][-36:-2])
                box_rng_pct = ((box_hi - box_lo) / max(1e-9, box_lo)) * 100.0
                # Proporcja kupna/sprzedazy niemal idealnie 50/50 (0.46 - 0.54) w waskim pudelku <= 4.5% i obecne wybicie nad box_hi
                if 0.46 <= buy_ratio <= 0.54 and 0.4 <= box_rng_pct <= 4.5 and cur > box_hi * 1.003:
                    sl = round(box_lo * 0.995, 6)
                    sd = abs(cur - sl)
                    if 0.008 <= (sd / max(1e-9, cur)) <= 0.08:
                        return {
                            "symbol": sym, "side": "LONG", "mode": "🤖 WZORZEC 5: BOT PING-PONG BREAKOUT",
                            "win_prob": 76,
                            "alpha_tag": f"BUY/SELL {int(buy_ratio*100)}/{int((1-buy_ratio)*100)} | BOX {box_rng_pct:.1f}%",
                            "pattern_fit": "Archetyp Wash-Trading / Bot Ping-Pong (Rowne slupki kupna i sprzedazy + wybicie z pudelka)",
                            "narrative": f"Przez ostatnie 9h bot utrzymywal nienaturalnie rowny bilans kupna do sprzedazy ({int(buy_ratio*100)}% / {int((1-buy_ratio)*100)}%) w waskim zakresie {box_rng_pct:.1f}%, a kurs wlasnie wybija gora. Czesty wstep do wlasciwej fazy pompy — wchodzic wylacznie zleceniem LIMIT.",
                            "price": cur, "entry": cur, "stop": sl,
                            "tp": [round(cur + sd * m, 6) for m in (1.5, 2.5, 4.0, 6.0, 10.0)]
                        }
        # WZORZEC 6: Pulapka Funding Rate / Extreme Squeeze
        try:
            sl = chr(47)
            u_fr = "".join(["https:", sl, sl, "api.", "bitget", ".com", sl, "api", sl, "v2", sl, "mix", sl, "market", sl, "current-fund-rate"])
            r_fr = SESS.get(u_fr, params={"productType": "USDT-FUTURES", "symbol": sym}, timeout=3).json()
            fr_val = float((r_fr.get("data") or [{}])[0].get("fundingRate", 0) or 0) * 100.0
            if fr_val <= -0.15 and cur > ma7_4h:
                sl_p = round(cur - max(cur * 0.025, atr_4h * 1.5), 6)
                sd_p = abs(cur - sl_p)
                return {
                    "symbol": sym, "side": "LONG", "mode": "🧲 WZORZEC 6: FUNDING SHORT-SQUEEZE",
                    "win_prob": 82,
                    "alpha_tag": f"FUNDING {fr_val:.3f}% | SQUEEZE LONG",
                    "pattern_fit": "Archetyp Ekstremalnego Funding Rate (Masowe shorty placa kary -> wyciskanie w gore)",
                    "narrative": f"Stawka finansowania spadla do {fr_val:.3f}%, co oznacza ekstremalne przeladowanie shortow. Wieloryby moga wycisnac pozycje krotkie w gore, zeby skasowac likwidacje.",
                    "price": cur, "entry": cur, "stop": sl_p,
                    "tp": [round(cur + sd_p * m, 6) for m in (1.5, 2.5, 4.0, 6.0, 10.0)]
                }
        except Exception:
            pass

        # WZORZEC 7: Schodkowa Pompa Bez Korekty (6+ zielonych swiec 1H z rzedu)
        h1 = _apm_klines("BITGET", sym, "1h", 20)
        if h1 and len(h1["c"]) >= 10:
            greens = sum(1 for j in range(-7, -1) if float(h1["c"][j]) > float(h1["o"][j]))
            ladder_pct = ((float(h1["c"][-2]) - float(h1["o"][-7])) / max(1e-9, float(h1["o"][-7]))) * 100.0
            last_red = float(h1["c"][-1]) < float(h1["o"][-1])
            if greens >= 5 and ladder_pct >= 10.0 and last_red:
                sl_p = round(max(float(x) for x in h1["h"][-3:]) * 1.008, 6)
                sd_p = abs(sl_p - cur)
                if 0.01 <= (sd_p / max(1e-9, cur)) <= 0.10:
                    return {
                        "symbol": sym, "side": "SHORT", "mode": "🪜 WZORZEC 7: STAIRCASE LADDER DUMP",
                        "win_prob": 79,
                        "alpha_tag": f"SCHODKI +{ladder_pct:.1f}% ({greens}/6 zielonych 1H)",
                        "pattern_fit": "Archetyp Schodkowej Pompy Algorytmicznej (Sztuczny marsz bez korekty + pierwsza czerwona 1H)",
                        "narrative": f"Algorytm ciagnal kurs schodkowo w gore (+{ladder_pct:.1f}% na {greens} z 6 swiec 1H) bez korekty, a teraz pojawila sie pierwsza swieca podazowa. Czesty sygnal zakonczenia dystrybucji i szybkiego zrzutu.",
                        "price": cur, "entry": cur, "stop": sl_p,
                        "tp": [round(cur - sd_p * m, 6) for m in (1.5, 2.5, 4.0, 6.0, 10.0)]
                    }

        return None
    except Exception:
        return None
