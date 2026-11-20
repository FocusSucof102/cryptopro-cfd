#!/usr/bin/env python3
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
"""
system.py
Zintegrowany system: Backtest (30k swiec + Funding + Poslizg) + Monitor Live (Collector).
Nie sklada zlecen. Wyniki sa symulacja, nie prognoza.
"""

import os
import sys
import json
import time
import math
import bisect
import random
import requests
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from statistics import mean

# ---------- KONFIGURACJA WSPOLNA ----------
BASE = "https://fapi.binance.com"
SYMBOL = "BTCUSDT"
CACHE_DIR = "bt_cache"
CONFIG_FILE = "config_live.json"

INITIAL_CAPITAL = 200.0
RISK_PCT = 1.0
MAX_LEV = 100
MAX_MARGIN_FRACTION = 0.80

FEE_SIDE_PCT = 0.05      # 0.05% Taker na strone
SLIPPAGE_BPS = 2.0       # 2 punkty bazowe (0.02%) poslizgu

LEVEL_CANDLES = 48
STOP_ATR = 1.5
TRAIL_ATR = 3.0
NEAR_ATR = 1.0
ATR_N = 14
ADX_MIN = 20
VOL_MULT = 1.5
HORIZON = 168

# Ustawienia Backtestu
H1_CANDLES = 30000
D1_CANDLES = 1800
H4_CANDLES = 9000
BLOCKS = 4
RANDOM_TRADES_PER_BLOCK = 1000
SEED = 7
TIMEOUT = 20
WATCH_EVERY = 300

# Kolory ANSI dla Termuxa
G = "\033[92m"   # Zielony
R = "\033[91m"   # Czerwony
Y = "\033[93m"   # Zolty
C = "\033[96m"   # Cyjan
B = "\033[1m"    # Pogrubienie
W = "\033[0m"    # Reset

os.makedirs(CACHE_DIR, exist_ok=True)


# =====================================================================
# MODUL 1: KOMUNIKACJA Z API BINANCE I WSKAZNIKI TECHNICZNE
# =====================================================================

def get_json(url, **params):
    """Realizuje logike: get json. Parametry: url."""
    last_error = None
    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            if response.status_code == 429:
                wait_sec = int(response.headers.get("Retry-After", 15))
                print(f"  {Y}Limit zapytan Binance (429). Czekam {wait_sec}s...{W}")
                time.sleep(wait_sec)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < 4:
                time.sleep(3)
    raise RuntimeError(f"Blad API: {last_error}")


def fetch_history_cached(interval, wanted):
    """Realizuje logike: fetch history cached. Parametry: interval, wanted."""
    cache_path = os.path.join(CACHE_DIR, f"{SYMBOL}_{interval}_{wanted}.json")
    if os.path.exists(cache_path):
        print(f"Wczytuje {interval} z pamieci lokalnej ({cache_path})...")
        with open(cache_path, "r") as f:
            return json.load(f)

    print(f"Pobieram historie {interval}: cel {wanted} swiec ...")
    result = []
    end_time = int(time.time() * 1000)

    while len(result) < wanted:
        batch = get_json(
            BASE + "/fapi/v1/klines",
            symbol=SYMBOL,
            interval=interval,
            limit=min(1500, wanted - len(result)),
            endTime=end_time
        )
        if not batch:
            break
        result = batch + result
        end_time = int(batch[0][0]) - 1
        if len(batch) < 2:
            break
        time.sleep(0.25)

    now_ms = int(time.time() * 1000)
    by_open = {}
    for candle in result:
        if int(candle[6]) < now_ms:
            by_open[int(candle[0])] = candle
    raw = [by_open[key] for key in sorted(by_open)]
    raw = raw[-wanted:]

    parsed = {
        "open_time": [int(k[0]) for k in raw],
        "close_time": [int(k[6]) for k in raw],
        "o": [float(k[1]) for k in raw],
        "h": [float(k[2]) for k in raw],
        "l": [float(k[3]) for k in raw],
        "c": [float(k[4]) for k in raw],
        "v": [float(k[5]) for k in raw],
    }
    with open(cache_path, "w") as f:
        json.dump(parsed, f)
    return parsed


def fetch_live_klines(interval, limit):
    """Realizuje logike: fetch live klines. Parametry: interval, limit."""
    now_ms = int(time.time() * 1000)
    raw = get_json(
        BASE + "/fapi/v1/klines",
        symbol=SYMBOL,
        interval=interval,
        limit=limit
    )
    raw = [k for k in raw if int(k[6]) < now_ms]
    return {
        "open_time": [int(k[0]) for k in raw],
        "close_time": [int(k[6]) for k in raw],
        "o": [float(k[1]) for k in raw],
        "h": [float(k[2]) for k in raw],
        "l": [float(k[3]) for k in raw],
        "c": [float(k[4]) for k in raw],
        "v": [float(k[5]) for k in raw],
    }


def fetch_funding_cached(start_ms, end_ms):
    """Realizuje logike: fetch funding cached. Parametry: start_ms, end_ms."""
    cache_path = os.path.join(CACHE_DIR, f"{SYMBOL}_funding.json")
    if os.path.exists(cache_path):
        print("Wczytuje historyczny funding z pamieci lokalnej...")
        with open(cache_path, "r") as f:
            data = json.load(f)
            return data["times"], data["rates"]

    print("Pobieram historyczny funding ...")
    times, rates = [], []
    cursor = start_ms

    while cursor < end_ms:
        batch = get_json(
            BASE + "/fapi/v1/fundingRate",
            symbol=SYMBOL,
            startTime=cursor,
            endTime=end_ms,
            limit=1000
        )
        if not batch:
            break

        for item in batch:
            times.append(int(item["fundingTime"]))
            rates.append(float(item["fundingRate"]))

        next_cursor = int(batch[-1]["fundingTime"]) + 1
        if next_cursor <= cursor or len(batch) < 1000:
            break
        cursor = next_cursor
        time.sleep(0.25)

    pairs = sorted(set(zip(times, rates)))
    t_out = [p[0] for p in pairs]
    r_out = [p[1] for p in pairs]
    with open(cache_path, "w") as f:
        json.dump({"times": t_out, "rates": r_out}, f)
    return t_out, r_out


def ema(values, period):
    """Realizuje logike: ema. Parametry: values, period."""
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = []
    current = values[0]
    for value in values:
        current = value * alpha + current * (1.0 - alpha)
        result.append(current)
    return result


def atr(high, low, close, period=ATR_N):
    """Realizuje logike: atr. Parametry: high, low, close, period."""
    n = len(close)
    result = [0.0] * n
    if n <= period:
        return result

    tr = [high[0] - low[0]]
    for i in range(1, n):
        tr.append(max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        ))

    current = sum(tr[1:period + 1]) / period
    result[period] = current
    for i in range(period + 1, n):
        current = (current * (period - 1) + tr[i]) / period
        result[i] = current
    return result


def adx(high, low, close, period=14):
    """Realizuje logike: adx. Parametry: high, low, close, period."""
    n = len(close)
    result = [0.0] * n
    if n < 2 * period + 1:
        return result

    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n

    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )

    sm_tr = sum(tr[1:period + 1])
    sm_plus = sum(plus_dm[1:period + 1])
    sm_minus = sum(minus_dm[1:period + 1])
    dx = [0.0] * n

    for i in range(period, n):
        if i > period:
            sm_tr = sm_tr - sm_tr / period + tr[i]
            sm_plus = sm_plus - sm_plus / period + plus_dm[i]
            sm_minus = sm_minus - sm_minus / period + minus_dm[i]

        pdi = 100.0 * sm_plus / sm_tr if sm_tr else 0.0
        mdi = 100.0 * sm_minus / sm_tr if sm_tr else 0.0
        denom = pdi + mdi
        dx[i] = 100.0 * abs(pdi - mdi) / denom if denom else 0.0

    seed_end = 2 * period
    current = mean(dx[period:seed_end])
    result[seed_end - 1] = current
    for i in range(seed_end, n):
        current = (current * (period - 1) + dx[i]) / period
        result[i] = current
    return result


def trend(close):
    """Realizuje logike: trend. Parametry: close."""
    e20 = ema(close, 20)
    e50 = ema(close, 50)
    out = []
    for i, price in enumerate(close):
        if i < 50:
            out.append(0)
        elif price > e20[i] > e50[i]:
            out.append(1)
        elif price < e20[i] < e50[i]:
            out.append(-1)
        else:
            out.append(0)
    return out


def breakout(h1, i, direction):
    """Realizuje logike: breakout. Parametry: h1, i, direction."""
    if i < LEVEL_CANDLES:
        return False
    if direction == 1:
        return h1["c"][i] > max(h1["h"][i - LEVEL_CANDLES:i])
    return h1["c"][i] < min(h1["l"][i - LEVEL_CANDLES:i])


def evaluate_filters(d1, h1, e200, a, adx_vals, daily_idx, i, direction):
    """Realizuje logike: evaluate filters. Parametry: d1, h1, e200, a, adx_vals, daily_idx, i, direction."""
    vol_ok = (
        i >= 20
        and h1["v"][i] >= VOL_MULT * mean(h1["v"][i - 20:i])
    )
    macro_ok = (
        (d1["c"][daily_idx] > e200[daily_idx])
        == (direction == 1)
    )
    recent = sorted(a[max(0, i - 720):i])
    hivol_ok = bool(recent) and a[i] >= recent[len(recent) // 2]
    conf2_ok = breakout(h1, i - 1, direction) if i > 0 else False

    return {
        "adx": adx_vals[i] >= ADX_MIN,
        "vol": vol_ok,
        "macro": macro_ok,
        "hivol": hivol_ok,
        "conf2": conf2_ok,
    }


# =====================================================================
# MODUL 2: BACKTESTER I KALIBRACJA FILTROW (Z DAWNEGO BACKTEST.PY)
# =====================================================================

def simulate_trade(data, i, direction, stop_atr=STOP_ATR, trail_atr=TRAIL_ATR, fee_side=FEE_SIDE_PCT):
    """Realizuje logike: simulate trade. Parametry: data, i, direction, stop_atr, trail_atr, fee_side."""
    h1 = data["H1"]
    entry_index = i + 1
    end_index = min(i + HORIZON, len(h1["c"]) - 1)
    if entry_index > end_index:
        return None

    atr_value = data["A"][i]
    if atr_value <= 0:
        return None

    stop_distance = STOP_ATR * atr_value
    slip = SLIPPAGE_BPS / 10000.0
    fee = fee_side / 100.0

    raw_entry = h1["o"][entry_index]
    entry = raw_entry * (1.0 + direction * slip)
    stop = entry - direction * stop_distance
    extreme = entry
    armed = False
    exit_price = None
    exit_index = end_index

    for j in range(entry_index, end_index + 1):
        stopped = (
            direction == 1 and h1["l"][j] <= stop
        ) or (
            direction == -1 and h1["h"][j] >= stop
        )

        if stopped:
            exit_price = stop * (1.0 - direction * slip)
            exit_index = j
            break

        if direction == 1:
            extreme = max(extreme, h1["h"][j])
        else:
            extreme = min(extreme, h1["l"][j])

        if not armed and direction * (extreme - entry) >= stop_distance:
            armed = True
            stop = entry

        if armed:
            new_stop = extreme - direction * trail_atr * atr_value
            stop = max(stop, new_stop) if direction == 1 else min(stop, new_stop)

    if exit_price is None:
        exit_price = h1["c"][end_index] * (1.0 - direction * slip)

    gross_per_btc = direction * (exit_price - entry)
    fees_per_btc = fee * (entry + exit_price)

    entry_time = h1["open_time"][entry_index]
    exit_time = h1["close_time"][exit_index]
    f_times = data["funding_times"]
    f_rates = data["funding_rates"]

    left = bisect.bisect_left(f_times, entry_time)
    right = bisect.bisect_right(f_times, exit_time)
    funding_cash_per_btc = 0.0
    for k in range(left, right):
        funding_cash_per_btc += -direction * f_rates[k] * entry

    net_per_btc = gross_per_btc - fees_per_btc + funding_cash_per_btc
    net_r = net_per_btc / stop_distance

    return {
        "r": net_r,
        "entry_index": entry_index,
        "exit_index": exit_index,
    }


def calc_metrics(trades):
    """Realizuje logike: calc metrics. Parametry: trades."""
    if not trades:
        return {"n": 0, "wr": 0.0, "avg_r": 0.0, "pf": 0.0, "dd": 0.0, "bal": INITIAL_CAPITAL}

    r_vals = [t["r"] for t in trades]
    wins = [r for r in r_vals if r > 0]
    losses = [abs(r) for r in r_vals if r <= 0]

    wr = len(wins) / len(r_vals) * 100.0
    avg_r = mean(r_vals)
    pf = (sum(wins) / sum(losses)) if losses and sum(losses) > 0 else 99.9

    bal = INITIAL_CAPITAL
    peak = INITIAL_CAPITAL
    max_dd = 0.0
    for r in r_vals:
        bal += bal * (RISK_PCT / 100.0) * r
        if bal > peak:
            peak = bal
        dd = (peak - bal) / peak * 100.0
        if dd > max_dd:
            max_dd = dd

    return {"n": len(r_vals), "wr": wr, "avg_r": avg_r, "pf": pf, "dd": max_dd, "bal": bal}


def run_bt_strategy(data, active_filters, start_idx=60, end_idx=None):
    """Realizuje logike: run bt strategy. Parametry: data, active_filters, start_idx, end_idx."""
    h1 = data["H1"]
    n = len(h1["c"])
    if end_idx is None:
        end_idx = n - HORIZON - 1

    trades = []
    i = start_idx
    free = 0
    while i < end_idx:
        if i >= free:
            jd = data["daily_map"][i]
            j4 = data["h4_map"][i]
            if jd >= 0 and j4 >= 0:
                for direction in (1, -1):
                    if (data["TD"][jd] == direction and data["T4"][j4] == direction and data["T1"][i] == direction):
                        if breakout(h1, i, direction):
                            f_vals = evaluate_filters(data["D1"], h1, data["E200"], data["A"], data["ADX"], jd, i, direction)
                            if all(f_vals[f] for f in active_filters):
                                res = simulate_trade(data, i, direction)
                                if res:
                                    trades.append(res)
                                    free = res["exit_index"] + 1
                                    break
        i += 1
    return trades


def run_full_backtest():
    """Realizuje logike: run full backtest."""
    random.seed(SEED)
    d1 = fetch_history_cached("1d", D1_CANDLES)
    h4 = fetch_history_cached("4h", H4_CANDLES)
    h1 = fetch_history_cached("1h", H1_CANDLES)

    funding_times, funding_rates = fetch_funding_cached(
        h1["open_time"][0],
        h1["close_time"][-1]
    )

    data = {
        "D1": d1, "H4": h4, "H1": h1,
        "TD": trend(d1["c"]), "T4": trend(h4["c"]), "T1": trend(h1["c"]),
        "E200": ema(d1["c"], 200),
        "A": atr(h1["h"], h1["l"], h1["c"]),
        "ADX": adx(h1["h"], h1["l"], h1["c"]),
        "daily_map": [bisect.bisect_right(d1["close_time"], t) - 1 for t in h1["close_time"]],
        "h4_map": [bisect.bisect_right(h4["close_time"], t) - 1 for t in h1["close_time"]],
        "funding_times": funding_times,
        "funding_rates": funding_rates,
    }

    n = len(h1["c"])
    t_start = datetime.fromtimestamp(h1["open_time"][0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    t_end = datetime.fromtimestamp(h1["close_time"][-1] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    print(f"\n{C}{B}=== 1. WPLYW FILTROW ({SYMBOL} | {t_start} -> {t_end} | Start: {INITIAL_CAPITAL}$) ==={W}")
    print(f"{'Wariant / Filtr':<22} | {'Tr.':>4} | {'WR%':>6} | {'Sr. R':>7} | {'PF':>4} | {'Max DD':>6} | {'Kapital koncowy'}")
    print("-" * 82)

    filter_sets = [
        ("Brak (czysta baza)", []),
        ("Tylko ADX >= 20", ["adx"]),
        ("Tylko Wolumen 1.5x", ["vol"]),
        ("Tylko Makro EMA200", ["macro"]),
        ("Tylko Wysokie ATR", ["hivol"]),
        ("Potwierdzenie 2 sw.", ["conf2"]),
        ("ADX + Wolumen", ["adx", "vol"]),
        ("ADX + Makro", ["adx", "macro"]),
        ("ADX + Makro + Vol", ["adx", "macro", "vol"]),
    ]

    best_score = -999.0
    best_filters = []
    best_name = "Brak (czysta baza)"

    for name, flt in filter_sets:
        tr = run_bt_strategy(data, flt)
        m = calc_metrics(tr)
        r_col = G if m["avg_r"] > 0.08 else (Y if m["avg_r"] > 0 else R)
        dd_col = G if m["dd"] < 20 else (Y if m["dd"] < 35 else R)
        b_col = G if m["bal"] > INITIAL_CAPITAL * 1.15 else (Y if m["bal"] > INITIAL_CAPITAL else R)
        pct = (m["bal"] / INITIAL_CAPITAL - 1.0) * 100.0
        print(f"{name:<22} | {m['n']:>4} | {m['wr']:>5.1f}% | {r_col}{m['avg_r']:>+6.3f}R{W} | {m['pf']:>4.2f} | {dd_col}-{m['dd']:>4.1f}%{W} | {b_col}{m['bal']:>7.2f}$ ({pct:>+5.1f}%){W}")

        if m["n"] >= 20 and m["avg_r"] > best_score:
            best_score = m["avg_r"]
            best_filters = flt
            best_name = name

    print("-" * 82)
    print(f"{G}{B}Zwycieski wariant zapisany dla trybu LIVE:{W} {B}{best_name}{W} -> filtry: {C}{best_filters}{W}")
    with open(CONFIG_FILE, "w") as f:
        json.dump({"enabled_filters": best_filters, "name": best_name}, f)

    print(f"\n{C}{B}=== 2. STABILNOSC W {BLOCKS} BLOKACH ({best_name} vs Losowe wejscia) ==={W}")
    print(f"{'Okres / Blok':<22} | {'Tr.':>4} | {'WR%':>6} | {'Sr. R':>7} | {'PF':>4} | {'Max DD':>6} | {'Kapital koncowy'}")
    print("-" * 82)

    usable_start = 200
    usable_end = n - HORIZON - 1
    block_size = (usable_end - usable_start) // BLOCKS

    for b in range(BLOCKS):
        b_start = usable_start + b * block_size
        b_end = usable_end if b == BLOCKS - 1 else b_start + block_size
        d_s = datetime.fromtimestamp(h1["open_time"][b_start] / 1000, tz=timezone.utc).strftime("%Y-%m")
        d_e = datetime.fromtimestamp(h1["close_time"][b_end] / 1000, tz=timezone.utc).strftime("%Y-%m")

        tr_strat = run_bt_strategy(data, best_filters, b_start, b_end)
        m = calc_metrics(tr_strat)
        r_col = G if m["avg_r"] > 0.08 else (Y if m["avg_r"] > 0 else R)
        dd_col = G if m["dd"] < 20 else (Y if m["dd"] < 35 else R)
        b_col = G if m["bal"] > INITIAL_CAPITAL else R
        pct = (m["bal"] / INITIAL_CAPITAL - 1.0) * 100.0
        print(f"B{b+1} ({d_s}..{d_e})  | {m['n']:>4} | {m['wr']:>5.1f}% | {r_col}{m['avg_r']:>+6.3f}R{W} | {m['pf']:>4.2f} | {dd_col}-{m['dd']:>4.1f}%{W} | {b_col}{m['bal']:>7.2f}$ ({pct:>+5.1f}%){W}")

        rand_trades = []
        for _ in range(RANDOM_TRADES_PER_BLOCK):
            ri = random.randint(b_start, b_end - 1)
            rd = random.choice([1, -1])
            res = simulate_trade(data, ri, rd)
            if res:
                rand_trades.append(res)
        mr = calc_metrics(rand_trades)
        rc = G if mr["avg_r"] > 0 else R
        print(f"  -> Losowe (baza)     | {mr['n']:>4} | {mr['wr']:>5.1f}% | {rc}{mr['avg_r']:>+6.3f}R{W} | {mr['pf']:>4.2f} |   ---  |   ---")
        print("-" * 82)


# =====================================================================
# MODUL 3: MONITOR LIVE I KALKULATOR RYZYKA (Z DAWNEGO COLLECTOR.PY)
# =====================================================================

def get_symbol_rules():
    """Realizuje logike: get symbol rules."""
    info = get_json(BASE + "/fapi/v1/exchangeInfo")
    symbol_info = next(item for item in info["symbols"] if item["symbol"] == SYMBOL)
    filters = {item["filterType"]: item for item in symbol_info["filters"]}

    lot_filter = filters.get("MARKET_LOT_SIZE")
    if not lot_filter or float(lot_filter.get("stepSize", 0)) == 0:
        lot_filter = filters["LOT_SIZE"]

    notional_filter = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL")
    min_notional = float(notional_filter.get("notional", notional_filter.get("minNotional", 0))) if notional_filter else 0.0

    return {
        "step": float(lot_filter["stepSize"]),
        "min_qty": float(lot_filter["minQty"]),
        "min_notional": min_notional,
    }


def round_qty_down(quantity, step):
    """Realizuje logike: round qty down. Parametry: quantity, step."""
    q = Decimal(str(quantity))
    s = Decimal(str(step))
    if s <= 0:
        return 0.0
    return float((q / s).to_integral_value(rounding=ROUND_DOWN) * s)


def run_live_check():
    """Realizuje logike: run live check."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            enabled = cfg.get("enabled_filters", [])
            cfg_name = cfg.get("name", "Wlasny")
    else:
        enabled = []
        cfg_name = "Domyslny (brak kalibracji - uruchom najpierw opcje 1)"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{C}{B}=== MONITOR LIVE ({SYMBOL} | {now_str}) ==={W}")
    print(f"Aktywny profil filtrow: {B}{cfg_name}{W} -> {enabled}")

    d1 = fetch_live_klines("1d", 400)
    h4 = fetch_live_klines("4h", 300)
    h1 = fetch_live_klines("1h", 1000)
    m15 = fetch_live_klines("15m", 100)
    price = float(get_json(BASE + "/fapi/v1/ticker/price", symbol=SYMBOL)["price"])
    rules = get_symbol_rules()

    td, t4, t1 = trend(d1["c"])[-1], trend(h4["c"])[-1], trend(h1["c"])[-1]
    e200 = ema(d1["c"], 200)
    a_vals = atr(h1["h"], h1["l"], h1["c"])
    adx_vals = adx(h1["h"], h1["l"], h1["c"])

    i = len(h1["c"]) - 1
    names = {1: f"{G}UP{W}", -1: f"{R}DOWN{W}", 0: f"{Y}FLAT{W}"}
    print(f"Cena: {B}{price:.2f} USDT{W} | Trendy: 1D {names[td]} | 4H {names[t4]} | 1H {names[t1]}")

    if not (td == t4 == t1 and td != 0):
        print(f"Status: {Y}WAIT{W} (brak zgodnego kierunku na 1D/4H/1H)")
        return

    direction = td
    side_str = f"{G}LONG{W}" if direction == 1 else f"{R}SHORT{W}"
    atr_value = a_vals[i]
    level = max(h1["h"][i - LEVEL_CANDLES:i]) if direction == 1 else min(h1["l"][i - LEVEL_CANDLES:i])

    distance_atr = (level - price) / atr_value if direction == 1 else (price - level) / atr_value
    last_15m_close = m15["c"][-1]
    beyond_15m = last_15m_close > level if direction == 1 else last_15m_close < level
    beyond_now = direction * (price - level) > 0
    extension_atr = direction * (price - level) / atr_value

    f_vals = evaluate_filters(d1, h1, e200, a_vals, adx_vals, len(d1["c"]) - 1, i, direction)
    failed = [key for key in enabled if not f_vals.get(key, False)]

    if beyond_now and beyond_15m and extension_atr <= NEAR_ATR:
        status = f"{G}{B}TRIGGER (WEJSCIE!){W}"
        is_trigger = True
    elif beyond_now and beyond_15m:
        status = f"{Y}WAIT (wybicie spoznione > {NEAR_ATR} ATR){W}"
        is_trigger = False
    elif beyond_now:
        status = f"{Y}WAIT (brak potwierdzenia zamknieciem 15M){W}"
        is_trigger = False
    elif distance_atr <= NEAR_ATR:
        status = f"{C}WAIT (blisko poziomu - gotowosc){W}"
        is_trigger = False
    else:
        status = "WAIT (za daleko od poziomu)"
        is_trigger = False

    if is_trigger and failed:
        status = f"{R}WAIT (odrzucone przez filtry: {','.join(failed)}){W}"
        is_trigger = False

    entry = price if is_trigger else level
    stop_distance = STOP_ATR * atr_value
    stop = entry - direction * stop_distance
    tp = [entry + direction * k * stop_distance for k in (1, 2, 3, 5)]

    risk_budget = INITIAL_CAPITAL * RISK_PCT / 100.0
    cost_rate = (FEE_SIDE_PCT / 100.0) + (SLIPPAGE_BPS / 10000.0)
    risk_per_btc = stop_distance + cost_rate * (entry + stop)
    raw_qty = risk_budget / risk_per_btc if risk_per_btc > 0 else 0.0
    qty = round_qty_down(raw_qty, rules["step"])
    notional = qty * entry
    lev = max(1, math.ceil(notional / (INITIAL_CAPITAL * MAX_MARGIN_FRACTION))) if notional > 0 else 1

    print("-" * 65)
    print(f"Kierunek: {side_str} | Status: {status}")
    print(f"Poziom wybicia: {level:.2f} | Dystans: {distance_atr:+.2f} ATR | ATR(1H): {atr_value:.2f}")
    print(f"Wejscie: {entry:.2f} | Stop Loss: {stop:.2f} | Trailing: {TRAIL_ATR * atr_value:.2f}")
    print("Cele (R): " + " | ".join(f"{k}R: {x:.2f}" for k, x in zip((1, 2, 3, 5), tp)))
    print("-" * 65)
    print(f"Kapital: {INITIAL_CAPITAL:.2f}$ | Ryzyko: {risk_budget:.2f}$ | Ilosc: {qty} BTC | Wartosc: {notional:.2f}$ | Dzwignia: {lev}x")

    f_status = " | ".join(f"{k}: {G}OK{W}" if v else f"{k}: {R}NO{W}" for k, v in f_vals.items())
    print(f"Stan filtrow: {f_status}")

    checks = [
        (qty >= rules["min_qty"] and qty > 0, f"Ilosc {qty} >= min_qty ({rules['min_qty']})"),
        (notional >= rules["min_notional"], f"Wartosc {notional:.2f}$ >= min_notional ({rules['min_notional']}$)"),
        (lev <= MAX_LEV, f"Dzwignia {lev}x <= max ({MAX_LEV}x)"),
    ]
    for ok, msg in checks:
        print(f"  [{G}OK{W}]   {msg}" if ok else f"  [{R}FAIL{W}] {msg}")
    if is_trigger:
        send_telegram(f"<b>🚨 TRIGGER {SYMBOL}</b>\nKierunek: {'LONG' if direction==1 else 'SHORT'}\nWejscie: {entry:.2f}\nStop Loss: {stop:.2f}\nIlosc: {qty} BTC")


# =====================================================================
# MENU GLOWNE
# =====================================================================


TG_CONFIG_FILE = "tg_config.json"

def send_telegram(msg):
    """Realizuje logike: send telegram. Parametry: msg."""
    if not os.path.exists(TG_CONFIG_FILE):
        return
    with open(TG_CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    token = cfg.get("token", "").strip()
    chat_id = cfg.get("chat_id", "").strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://telegram.org{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"  {Y}Blad wysylania Telegram: {e}{W}")

def setup_telegram():
    """Realizuje logike: setup telegram."""
    if os.path.exists(TG_CONFIG_FILE):
        return
    print(f"\n{C}{B}--- KONFIGURACJA TELEGRAMA (opcjonalnie) ---{W}")
    print("Nacisnij ENTER, aby pominac i uzywac tylko konsoli.")
    token = input("Podaj Bot Token (od @BotFather): ").strip()
    if not token:
        with open(TG_CONFIG_FILE, "w") as f:
            json.dump({"token": "", "chat_id": ""}, f)
        return
    chat_id = input("Podaj swoje Chat ID (od @userinfobot): ").strip()
    with open(TG_CONFIG_FILE, "w") as f:
        json.dump({"token": token, "chat_id": chat_id}, f)
    send_telegram("<b>BTCUSDT Monitor</b>: Polaczenie z Termuxem aktywne!")
    print(f"{G}Zapisano i wyslano wiadomosc testowa na Telegrama!{W}")

def main():
    """Realizuje logike: main."""
    while True:
        print(f"\n{C}{B}===================================================={W}")
        print(f"{C}{B}   BTCUSDT SYSTEM (BACKTEST + LIVE COLLECTOR)       {W}")
        print(f"{C}{B}===================================================={W}")
        print("1. Uruchom Backtest (30k swiec) i skalibruj filtry")
        print("2. Sprawdz rynek TERAZ (jednorazowy skan Live)")
        print(f"3. Tryb czuwania Live (skan co {WATCH_EVERY} sek.)")
        print("0. Wyjscie")
        choice = input(f"\n{B}Wybierz opcje (0-3): {W}").strip()

        if choice == "1":
            run_full_backtest()
        elif choice == "2":
            run_live_check()
        elif choice == "3":
            print(f"{Y}Uruchomiono tryb czuwania. Nacisnij CTRL+C, aby przerwac.{W}")
            try:
                setup_telegram()
                while True:
                    run_live_check()
                    time.sleep(WATCH_EVERY)
            except KeyboardInterrupt:
                print(f"\n{Y}Zatrzymano tryb czuwania.{W}")
        elif choice == "0":
            sys.exit(0)
        else:
            print(f"{R}Nieprawidlowy wybor.{W}")


if __name__ == "__main__":
    main()
