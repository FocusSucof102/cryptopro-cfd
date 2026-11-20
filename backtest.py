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
backtest.py
Historyczny test BTCUSDT USD-M Futures na publicznych danych Binance.
Nie sklada zlecen. Wyniki sa symulacja, nie prognoza.
"""

import os
import json
import time
import math
import bisect
import random
import requests
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

# Kolory ANSI dla Termuxa
G = "\033[92m"   # Zielony
R = "\033[91m"   # Czerwony
Y = "\033[93m"   # Żółty
C = "\033[96m"   # Cyjan
B = "\033[1m"    # Pogrubienie
W = "\033[0m"    # Reset

os.makedirs(CACHE_DIR, exist_ok=True)


def get_json(url, **params):
    last_error = None
    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            if response.status_code == 429:
                wait_sec = int(response.headers.get("Retry-After", 15))
                print(f"  {Y}Limit zapytań Binance (429). Czekam {wait_sec}s...{W}")
                time.sleep(wait_sec)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < 4:
                time.sleep(3)
    raise RuntimeError(f"Blad API: {last_error}")


def fetch_history(interval, wanted):
    cache_path = os.path.join(CACHE_DIR, f"{SYMBOL}_{interval}_{wanted}.json")
    if os.path.exists(cache_path):
        print(f"Wczytuję {interval} z pamięci lokalnej...")
        with open(cache_path, "r") as f:
            return json.load(f)

    print(f"Pobieram {interval}: cel {wanted} świec ...")
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
        time.sleep(0.3)

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


def fetch_funding(start_ms, end_ms):
    cache_path = os.path.join(CACHE_DIR, f"{SYMBOL}_funding.json")
    if os.path.exists(cache_path):
        print("Wczytuję historyczny funding z pamięci lokalnej...")
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
        time.sleep(0.3)

    pairs = sorted(set(zip(times, rates)))
    t_out = [p[0] for p in pairs]
    r_out = [p[1] for p in pairs]
    with open(cache_path, "w") as f:
        json.dump({"times": t_out, "rates": r_out}, f)
    return t_out, r_out


def ema(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = []
    current = values[0][0]
    for value in values:
        current = value * alpha + current * (1.0 - alpha)
        result.append(current)
    return result


def atr(high, low, close, period=ATR_N):
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


def load_data():
    d1 = fetch_history("1d", D1_CANDLES)
    h4 = fetch_history("4h", H4_CANDLES)
    h1 = fetch_history("1h", H1_CANDLES)

    if len(h1["c"]) < 500 or len(d1["c"]) < 210 or len(h4["c"]) < 60:
        raise RuntimeError(
            "Za malo danych. Sprawdz polaczenie i dostepnosc danych Binance."
        )

    funding_times, funding_rates = fetch_funding(
        h1["open_time"][0],
        h1["close_time"][-1]
    )

    daily_map = [
        bisect.bisect_right(d1["close_time"], t) - 1
        for t in h1["close_time"]
    ]
    h4_map = [
        bisect.bisect_right(h4["close_time"], t) - 1
        for t in h1["close_time"]
    ]

    return {
        "D1": d1,
        "H4": h4,
        "H1": h1,
        "TD": trend(d1["c"]),
        "T4": trend(h4["c"]),
        "T1": trend(h1["c"]),
        "E200": ema(d1["c"], 200),
        "A": atr(h1["h"], h1["l"], h1["c"]),
        "ADX": adx(h1["h"], h1["l"], h1["c"]),
        "daily_map": daily_map,
        "h4_map": h4_map,
        "funding_times": funding_times,
        "funding_rates": funding_rates,
    }


def aligned(data, i, direction):
    jd = data["daily_map"][i]
    j4 = data["h4_map"][i]
    if jd < 0 or j4 < 0:
        return False
    return (
        data["TD"][jd] == direction
        and data["T4"][j4] == direction
        and data["T1"][i] == direction
    )


def breakout(data, i, direction):
    h1 = data["H1"]
    if i < LEVEL_CANDLES:
        return False
    if direction == 1:
        return h1["c"][i] > max(h1["h"][i - LEVEL_CANDLES:i])
    return h1["c"][i] < min(h1["l"][i - LEVEL_CANDLES:i])


def filter_values(data, i, direction):
    h1 = data["H1"]
    jd = data["daily_map"][i]
    a = data["A"]

    vol_ok = (
        i >= 20
        and h1["v"][i] >= VOL_MULT * mean(h1["v"][i - 20:i])
    )
    macro_ok = (
        (data["D1"]["c"][jd] > data["E200"][jd])
        == (direction == 1)
    )
    recent = sorted(a[max(0, i - 720):i])
    hivol_ok = bool(recent) and a[i] >= recent[len(recent) // 2]
    conf2_ok = breakout(data, i - 1, direction) if i > 0 else False

    return {
        "adx": data["ADX"][i] >= ADX_MIN,
        "vol": vol_ok,
        "macro": macro_ok,
        "hivol": hivol_ok,
        "conf2": conf2_ok,
    }


def simulate(data, i, direction):
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
    fee = FEE_SIDE_PCT / 100.0

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

