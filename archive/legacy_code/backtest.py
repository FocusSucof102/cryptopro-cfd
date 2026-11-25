#!/usr/bin/env python3
# ==============================================================================
# [ARCHIVE/LEGACY_CODE] backtest.py
# Przeniesiono do archiwum zgodnie z restrukturyzacją projektu.
# Zachowano w repozytorium do wglądu i badań historycznych.
# ==============================================================================
"""
backtest.py
Historyczny test BTCUSDT USD-M Futures na publicznych danych Binance.
Nie sklada zlecen. Wyniki sa symulacja, nie prognoza.
"""
import os, json, time, math, bisect, random, requests
from datetime import datetime, timezone
from statistics import mean

BASE = "https://binance.com"
SYMBOL = "BTCUSDT"
CACHE_DIR = "bt_cache"
INITIAL_CAPITAL = 200.0
RISK_PCT = 1.0
FEE_SIDE_PCT = 0.05
SLIPPAGE_BPS = 2.0
H1_CANDLES = 30000
D1_CANDLES = 1800
H4_CANDLES = 9000
LEVEL_CANDLES = 48
STOP_ATR = 1.5
TRAIL_ATR = 3.0
ATR_N = 14
ADX_MIN = 20
VOL_MULT = 1.5
HORIZON = 168
BLOCKS = 4
RANDOM_TRADES_PER_BLOCK = 1000
SEED = 7
TIMEOUT = 20

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

def fetch_history(interval, wanted):
    """Realizuje logike: fetch history. Parametry: interval, wanted."""
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
        time.sleep(0.3)
    now_ms = int(time.time() * 1000)
    by_open = {int(candle[0]): candle for candle in result if int(candle[6]) < now_ms}
    raw = [by_open[key] for key in sorted(by_open)][-wanted:]
    parsed = {"open_time": [int(k[0]) for k in raw], "close_time": [int(k[6]) for k in raw], "o": [float(k[1]) for k in raw], "h": [float(k[2]) for k in raw], "l": [float(k[3]) for k in raw], "c": [float(k[4]) for k in raw], "v": [float(k[5]) for k in raw]}
    with open(cache_path, "w") as f: json.dump(parsed, f)
    return parsed

def fetch_funding(start_ms, end_ms):
    """Realizuje logike: fetch funding. Parametry: start_ms, end_ms."""
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
        time.sleep(0.3)
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

def simulate(data, i, direction):
    """Realizuje logike: simulate. Parametry: data, i, direction."""
    h1 = data["H1"]
    entry_index = i + 1
    end_index = min(i + HORIZON, len(h1["c"]) - 1)
    if entry_index > end_index: return None
    atr_value = data["A"][i]
    if atr_value <= 0: return None
    stop_distance = STOP_ATR * atr_value
    slip = SLIPPAGE_BPS / 10000.0
    fee = FEE_SIDE_PCT / 100.0
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
            new_stop = extreme - direction * TRAIL_ATR * atr_value
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

if __name__ == "__main__":
    print("Skrypt archiwalny backtest.py")
