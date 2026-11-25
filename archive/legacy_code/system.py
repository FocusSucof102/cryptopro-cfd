#!/usr/bin/env python3
# ==============================================================================
# [ARCHIVE/LEGACY_CODE] system.py
# Przeniesiono do archiwum zgodnie z restrukturyzacją projektu.
# Zachowano w repozytorium do wglądu i badań historycznych.
# ==============================================================================
import os, sys, json, time, math, bisect, random, requests
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from statistics import mean

BASE = "https://fapi.binance.com"
SYMBOL = "BTCUSDT"
CACHE_DIR = "bt_cache"
CONFIG_FILE = "config_live.json"
INITIAL_CAPITAL = 200.0
RISK_PCT = 1.0
MAX_LEV = 100
MAX_MARGIN_FRACTION = 0.80
FEE_SIDE_PCT = 0.05
SLIPPAGE_BPS = 2.0
LEVEL_CANDLES = 48
STOP_ATR = 1.5
TRAIL_ATR = 3.0
NEAR_ATR = 1.0
ATR_N = 14
ADX_MIN = 20
VOL_MULT = 1.5
HORIZON = 168
H1_CANDLES = 30000
D1_CANDLES = 1800
H4_CANDLES = 9000
BLOCKS = 4
RANDOM_TRADES_PER_BLOCK = 1000
SEED = 7
TIMEOUT = 20
WATCH_EVERY = 300

G, R, Y, C, B, W = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_json(url, **params):
    """Realizuje logike: get json. Parametry: url."""
    last_error = None
    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            if response.status_code == 429:
                wait_sec = int(response.headers.get("Retry-After", 15))
                time.sleep(wait_sec)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < 4: time.sleep(3)
    raise RuntimeError(f"Blad API: {last_error}")

def fetch_history_cached(interval, wanted):
    """Realizuje logike: fetch history cached. Parametry: interval, wanted."""
    cache_path = os.path.join(CACHE_DIR, f"{SYMBOL}_{interval}_{wanted}.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f: return json.load(f)
    result = []
    end_time = int(time.time() * 1000)
    while len(result) < wanted:
        batch = get_json(BASE + "/fapi/v1/klines", symbol=SYMBOL, interval=interval, limit=min(1500, wanted - len(result)), endTime=end_time)
        if not batch: break
        result = batch + result
        end_time = int(batch[0][0]) - 1
        if len(batch) < 2: break
        time.sleep(0.25)
    now_ms = int(time.time() * 1000)
    by_open = {int(candle[0]): candle for candle in result if int(candle[6]) < now_ms}
    raw = [by_open[key] for key in sorted(by_open)][-wanted:]
    parsed = {"open_time": [int(k[0]) for k in raw], "close_time": [int(k[6]) for k in raw], "o": [float(k[1]) for k in raw], "h": [float(k[2]) for k in raw], "l": [float(k[3]) for k in raw], "c": [float(k[4]) for k in raw], "v": [float(k[5]) for k in raw]}
    with open(cache_path, "w") as f: json.dump(parsed, f)
    return parsed

def fetch_live_klines(interval, limit):
    """Realizuje logike: fetch live klines. Parametry: interval, limit."""
    now_ms = int(time.time() * 1000)
    raw = get_json(BASE + "/fapi/v1/klines", symbol=SYMBOL, interval=interval, limit=limit)
    raw = [k for k in raw if int(k[6]) < now_ms]
    return {"open_time": [int(k[0]) for k in raw], "close_time": [int(k[6]) for k in raw], "o": [float(k[1]) for k in raw], "h": [float(k[2]) for k in raw], "l": [float(k[3]) for k in raw], "c": [float(k[4]) for k in raw], "v": [float(k[5]) for k in raw]}

def fetch_funding_cached(start_ms, end_ms):
    """Realizuje logike: fetch funding cached. Parametry: start_ms, end_ms."""
    cache_path = os.path.join(CACHE_DIR, f"{SYMBOL}_funding.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f: data = json.load(f); return data["times"], data["rates"]
    times, rates = [], []
    cursor = start_ms
    while cursor < end_ms:
        batch = get_json(BASE + "/fapi/v1/fundingRate", symbol=SYMBOL, startTime=cursor, endTime=end_ms, limit=1000)
        if not batch: break
        for item in batch:
            times.append(int(item["fundingTime"]))
            rates.append(float(item["fundingRate"]))
        next_cursor = int(batch[-1]["fundingTime"]) + 1
        if next_cursor <= cursor or len(batch) < 1000: break
        cursor = next_cursor
        time.sleep(0.25)
    pairs = sorted(set(zip(times, rates)))
    t_out, r_out = [p[0] for p in pairs], [p[1] for p in pairs]
    with open(cache_path, "w") as f: json.dump({"times": t_out, "rates": r_out}, f)
    return t_out, r_out

def ema(values, period):
    """Realizuje logike: ema. Parametry: values, period."""
    if not values: return []
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
    if n <= period: return result
    tr = [high[0] - low[0]] + [max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])) for i in range(1, n)]
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
    if n < 2 * period + 1: return result
    tr, plus_dm, minus_dm = [0.0] * n, [0.0] * n, [0.0] * n
    for i in range(1, n):
        up, down = high[i] - high[i - 1], low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    sm_tr, sm_plus, sm_minus = sum(tr[1:period + 1]), sum(plus_dm[1:period + 1]), sum(minus_dm[1:period + 1])
    dx = [0.0] * n
    for i in range(period, n):
        if i > period:
            sm_tr = sm_tr - sm_tr / period + tr[i]
            sm_plus = sm_plus - sm_plus / period + plus_dm[i]
            sm_minus = sm_minus - sm_minus / period + minus_dm[i]
        pdi = 100.0 * sm_plus / sm_tr if sm_tr else 0.0
        mdi = 100.0 * sm_minus / sm_tr if sm_tr else 0.0
        dx[i] = 100.0 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0.0
    current = mean(dx[period:2 * period])
    result[2 * period - 1] = current
    for i in range(2 * period, n):
        current = (current * (period - 1) + dx[i]) / period
        result[i] = current
    return result

def trend(close):
    """Realizuje logike: trend. Parametry: close."""
    e20, e50 = ema(close, 20), ema(close, 50)
    out = []
    for i, price in enumerate(close):
        if i < 50: out.append(0)
        elif price > e20[i] > e50[i]: out.append(1)
        elif price < e20[i] < e50[i]: out.append(-1)
        else: out.append(0)
    return out

def breakout(h1, i, direction):
    """Realizuje logike: breakout. Parametry: h1, i, direction."""
    if i < LEVEL_CANDLES: return False
    return (h1["c"][i] > max(h1["h"][i - LEVEL_CANDLES:i])) if direction == 1 else (h1["c"][i] < min(h1["l"][i - LEVEL_CANDLES:i]))

def evaluate_filters(d1, h1, e200, a, adx_vals, daily_idx, i, direction):
    """Realizuje logike: evaluate filters. Parametry: d1, h1, e200, a, adx_vals, daily_idx, i, direction."""
    vol_ok = (i >= 20 and h1["v"][i] >= VOL_MULT * mean(h1["v"][i - 20:i]))
    macro_ok = ((d1["c"][daily_idx] > e200[daily_idx]) == (direction == 1))
    recent = sorted(a[max(0, i - 720):i])
    hivol_ok = bool(recent) and a[i] >= recent[len(recent) // 2]
    conf2_ok = breakout(h1, i - 1, direction) if i > 0 else False
    return {"adx": adx_vals[i] >= ADX_MIN, "vol": vol_ok, "macro": macro_ok, "hivol": hivol_ok, "conf2": conf2_ok}

def simulate_trade(data, i, direction, stop_atr=STOP_ATR, trail_atr=TRAIL_ATR, fee_side=FEE_SIDE_PCT):
    """Realizuje logike: simulate trade. Parametry: data, i, direction, stop_atr, trail_atr, fee_side."""
    h1 = data["H1"]
    entry_index = i + 1
    end_index = min(i + HORIZON, len(h1["c"]) - 1)
    if entry_index > end_index: return None
    atr_value = data["A"][i]
    if atr_value <= 0: return None
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
        stopped = (direction == 1 and h1["l"][j] <= stop) or (direction == -1 and h1["h"][j] >= stop)
        if stopped:
            exit_price = stop * (1.0 - direction * slip)
            exit_index = j
            break
        extreme = max(extreme, h1["h"][j]) if direction == 1 else min(extreme, h1["l"][j])
        if not armed and direction * (extreme - entry) >= stop_distance:
            armed = True
            stop = entry
        if armed:
            new_stop = extreme - direction * trail_atr * atr_value
            stop = max(stop, new_stop) if direction == 1 else min(stop, new_stop)
    if exit_price is None: exit_price = h1["c"][end_index] * (1.0 - direction * slip)
    gross_per_btc = direction * (exit_price - entry)
    fees_per_btc = fee * (entry + exit_price)
    entry_time, exit_time = h1["open_time"][entry_index], h1["close_time"][exit_index]
    f_times, f_rates = data["funding_times"], data["funding_rates"]
    left = bisect.bisect_left(f_times, entry_time)
    right = bisect.bisect_right(f_times, exit_time)
    funding_cash_per_btc = sum(-direction * f_rates[k] * entry for k in range(left, right))
    net_per_btc = gross_per_btc - fees_per_btc + funding_cash_per_btc
    return {"r": net_per_btc / stop_distance, "entry_index": entry_index, "exit_index": exit_index}

def calc_metrics(trades):
    """Realizuje logike: calc metrics. Parametry: trades."""
    if not trades: return {"n": 0, "wr": 0.0, "avg_r": 0.0, "pf": 0.0, "dd": 0.0, "bal": INITIAL_CAPITAL}
    r_vals = [t["r"] for t in trades]
    wins, losses = [r for r in r_vals if r > 0], [abs(r) for r in r_vals if r <= 0]
    wr = len(wins) / len(r_vals) * 100.0
    avg_r = mean(r_vals)
    pf = (sum(wins) / sum(losses)) if losses and sum(losses) > 0 else 99.9
    bal, peak, max_dd = INITIAL_CAPITAL, INITIAL_CAPITAL, 0.0
    for r in r_vals:
        bal += bal * (RISK_PCT / 100.0) * r
        if bal > peak: peak = bal
        dd = (peak - bal) / peak * 100.0
        if dd > max_dd: max_dd = dd
    return {"n": len(r_vals), "wr": wr, "avg_r": avg_r, "pf": pf, "dd": max_dd, "bal": bal}

def run_bt_strategy(data, active_filters, start_idx=60, end_idx=None):
    """Realizuje logike: run bt strategy. Parametry: data, active_filters, start_idx, end_idx."""
    h1 = data["H1"]
    if end_idx is None: end_idx = len(h1["c"]) - HORIZON - 1
    trades = []
    i, free = start_idx, 0
    while i < end_idx:
        if i >= free:
            jd, j4 = data["daily_map"][i], data["h4_map"][i]
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

def get_symbol_rules():
    """Realizuje logike: get symbol rules."""
    info = get_json(BASE + "/fapi/v1/exchangeInfo")
    symbol_info = next(item for item in info["symbols"] if item["symbol"] == SYMBOL)
    filters = {item["filterType"]: item for item in symbol_info["filters"]}
    lot = filters.get("MARKET_LOT_SIZE") or filters["LOT_SIZE"]
    nf = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL")
    min_notional = float(nf.get("notional", nf.get("minNotional", 0))) if nf else 0.0
    return {"step": float(lot["stepSize"]), "min_qty": float(lot["minQty"]), "min_notional": min_notional}

def round_qty_down(quantity, step):
    """Realizuje logike: round qty down. Parametry: quantity, step."""
    q, s = Decimal(str(quantity)), Decimal(str(step))
    return float((q / s).to_integral_value(rounding=ROUND_DOWN) * s) if s > 0 else 0.0

if __name__ == "__main__":
    print("Skrypt archiwalny system.py")
