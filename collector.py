#!/usr/bin/env python3
# collector.py
# Publiczne dane Binance USD-M Futures. Bez klucza API i bez skladania zlecen.

import math
import time
import requests
from decimal import Decimal, ROUND_DOWN
from statistics import mean

BASE = "https://fapi.binance.com"
SYMBOL = "BTCUSDT"

# Kapital jest symulowany. Skrypt nie odczytuje salda konta.
SIM_CAPITAL = 200.0
RISK_PCT = 1.0
MAX_LEV = 100
MAX_MARGIN_FRACTION = 0.80

FEE_SIDE_PCT = 0.05       # zalozenie: 0.05% od kazdej strony
SLIPPAGE_BPS = 2.0        # zalozenie: 2 punkty bazowe od kazdej strony

LEVEL_CANDLES = 48
STOP_ATR = 1.5
TRAIL_ATR = 3.0
NEAR_ATR = 1.0
ATR_N = 14
ADX_MIN = 20
VOL_MULT = 1.5

# Filtry wymagane do sygnalu. Na poczatku puste, do czasu oceny backtestu.
ENABLED = []

TIMEOUT = 20
WATCH_EVERY = 300


def get_json(url, **params):
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2)
    raise RuntimeError(f"Blad API: {last_error}")


def fetch_klines(interval, limit):
    now_ms = int(time.time() * 1000)
    raw = get_json(
        BASE + "/fapi/v1/klines",
        symbol=SYMBOL,
        interval=interval,
        limit=limit
    )
    # Binance zwraca rowniez swiece aktualnie tworzone.
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


def ema(values, period):
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
    result = []
    for i, price in enumerate(close):
        if i < 50:
            result.append(0)
        elif price > e20[i] > e50[i]:
            result.append(1)
        elif price < e20[i] < e50[i]:
            result.append(-1)
        else:
            result.append(0)
    return result


def get_symbol_rules():
    info = get_json(BASE + "/fapi/v1/exchangeInfo")
    symbol_info = next(
        item for item in info["symbols"]
        if item["symbol"] == SYMBOL
    )
    filters = {item["filterType"]: item for item in symbol_info["filters"]}

    lot_filter = filters.get("MARKET_LOT_SIZE")
    if not lot_filter or float(lot_filter.get("stepSize", 0)) == 0:
        lot_filter = filters["LOT_SIZE"]

    notional_filter = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL")
    min_notional = 0.0
    if notional_filter:
        min_notional = float(
            notional_filter.get(
                "notional",
                notional_filter.get("minNotional", 0)
            )
        )

    return {
        "step": float(lot_filter["stepSize"]),
        "min_qty": float(lot_filter["minQty"]),
        "min_notional": min_notional,
    }


def round_qty_down(quantity, step):
    q = Decimal(str(quantity))
    s = Decimal(str(step))
    if s <= 0:
        return 0.0
    return float((q / s).to_integral_value(rounding=ROUND_DOWN) * s)


def load_data():
    print("Pobieram zamkniete swiece Binance ...")
    d1 = fetch_klines("1d", 400)
    h4 = fetch_klines("4h", 300)
    h1 = fetch_klines("1h", 1000)
    m15 = fetch_klines("15m", 100)
    price = float(get_json(
        BASE + "/fapi/v1/ticker/price",
        symbol=SYMBOL
    )["price"])
    rules = get_symbol_rules()

    if min(len(d1["c"]), len(h4["c"]), len(h1["c"]), len(m15["c"])) == 0:
        raise RuntimeError("API nie zwrocilo wystarczajacej liczby swiec.")

    return {
        "D1": d1,
        "H4": h4,
        "H1": h1,
        "M15": m15,
        "price": price,
        "rules": rules,
        "TD": trend(d1["c"]),
        "T4": trend(h4["c"]),
        "T1": trend(h1["c"]),
        "E200": ema(d1["c"], 200),
        "A": atr(h1["h"], h1["l"], h1["c"]),
        "ADX": adx(h1["h"], h1["l"], h1["c"]),
    }


def breakout(data, i, direction):
    h1 = data["H1"]
    if i < LEVEL_CANDLES:
        return False
    if direction == 1:
        return h1["c"][i] > max(h1["h"][i - LEVEL_CANDLES:i])
    return h1["c"][i] < min(h1["l"][i - LEVEL_CANDLES:i])


def evaluate_filters(data, i, direction):
    h1 = data["H1"]
    d1 = data["D1"]
    a = data["A"]
    adx_values = data["ADX"]

    vol_ok = (
        i >= 20
        and h1["v"][i] >= VOL_MULT * mean(h1["v"][i - 20:i])
    )
    daily_index = len(d1["c"]) - 1
    macro_ok = (
        (d1["c"][daily_index] > data["E200"][daily_index])
        == (direction == 1)
    )

    recent_atr = sorted(a[max(0, i - 720):i])
    hivol_ok = bool(recent_atr) and a[i] >= recent_atr[len(recent_atr) // 2]

    # Funding jest informacyjny. Nie pobieramy go w tym prostym monitorze.
    funding_ok = True

    filters = {
        "adx": adx_values[i] >= ADX_MIN,
        "vol": vol_ok,
        "macro": macro_ok,
        "hivol": hivol_ok,
        "fund": funding_ok,
        "conf2": breakout(data, i - 1, direction) if i > 0 else False,
    }
    return filters


def analyze(data):
    h1 = data["H1"]
    d1 = data["D1"]
    h4 = data["H4"]
    price = data["price"]
    rules = data["rules"]

    i = len(h1["c"]) - 1
    if i < LEVEL_CANDLES + 2 or data["A"][i] <= 0:
        return "WAIT", ["Za malo danych do analizy."]

    td, t4, t1 = data["TD"][-1], data["T4"][-1], data["T1"][-1]
    names = {1: "up", -1: "down", 0: "flat"}
    lines = [
        f"{SYMBOL} cena {price:.2f}",
        f"Trendy: 1D {names[td]} | 4H {names[t4]} | 1H {names[t1]}"
    ]

    if not (td == t4 == t1 and td != 0):
        lines.append("Brak zgodnego kierunku 1D/4H/1H: WAIT.")
        return "WAIT", lines

    direction = td
    atr_value = data["A"][i]
    if direction == 1:
        level = max(h1["h"][i - LEVEL_CANDLES:i])
    else:
        level = min(h1["l"][i - LEVEL_CANDLES:i])

    distance_atr = (
        (level - price) / atr_value
        if direction == 1
        else (price - level) / atr_value
    )

    last_15m_close = data["M15"]["c"][-1]
    beyond_15m = (
        last_15m_close > level
        if direction == 1
        else last_15m_close < level
    )
    beyond_now = direction * (price - level) > 0
    extension_atr = direction * (price - level) / atr_value

    filters = evaluate_filters(data, i, direction)
    failed = [key for key in ENABLED if not filters.get(key, False)]

    if beyond_now and beyond_15m and extension_atr <= NEAR_ATR:
        status = "TRIGGER"
    elif beyond_now and beyond_15m:
        status = "WAIT (wybicie spoznione)"
    elif beyond_now:
        status = "WAIT (brak potwierdzenia 15M)"
    elif distance_atr <= NEAR_ATR:
        status = "WAIT (blisko poziomu)"
    else:
        status = "WAIT (za daleko od poziomu)"

    if status == "TRIGGER" and failed:
        status = "WAIT (filtry: " + ",".join(failed) + ")"

    entry = price if status == "TRIGGER" else level
    stop_distance = STOP_ATR * atr_value
    stop = entry - direction * stop_distance

    equity = SIM_CAPITAL
    risk_budget = equity * RISK_PCT / 100.0
    fee_rate = FEE_SIDE_PCT / 100.0
    slippage_rate = SLIPPAGE_BPS / 10000.0
    cost_rate = fee_rate + slippage_rate

    # Ryzyko na 1 BTC obejmuje ruch do stopa oraz szacowane koszty obu stron.
    risk_per_btc = stop_distance + cost_rate * (entry + stop)
    raw_qty = risk_budget / risk_per_btc if risk_per_btc > 0 else 0.0
    qty = round_qty_down(raw_qty, rules["step"])
    notional = qty * entry
    actual_risk = qty * risk_per_btc

    estimated_leverage = max(
        1,
        math.ceil(notional / (equity * MAX_MARGIN_FRACTION))
    )
    estimated_margin = notional / estimated_leverage

    block_reasons = []
    if qty < rules["min_qty"]:
        block_reasons.append("minQty")
    if notional < rules["min_notional"]:
        block_reasons.append("minNotional")
    if actual_risk > risk_budget * 1.001:
        block_reasons.append("limit ryzyka")
    if estimated_leverage > MAX_LEV:
        block_reasons.append("limit dzwigni")
    if estimated_margin > equity * MAX_MARGIN_FRACTION:
        block_reasons.append("depozyt")

    if status == "TRIGGER" and block_reasons:
        status = "BLOCKED (" + ",".join(block_reasons) + ")"

    side = "LONG" if direction == 1 else "SHORT"
    lines.extend([
        "",
        f"{side} | status: {status}",
        f"Poziom wybicia: {level:.2f} | odleglosc: {distance_atr:+.2f} ATR",
        f"ATR 1H: {atr_value:.2f}",
        f"Wejscie orientacyjne: {entry:.2f} | SL: {stop:.2f}",
        "Cele: " + " | ".join(
            f"{multiple}R {entry + direction * multiple * stop_distance:.2f}"
            for multiple in (1, 2, 3, 5)
        ),
        f"Kapital symulowany: {equity:.2f} USDT",
        f"Budzet ryzyka: {risk_budget:.3f} USDT",
        f"Ryzyko wyliczone: {actual_risk:.3f} USDT",
        f"Ilosc: {qty} BTC | wartosc: {notional:.2f} USDT",
        f"Dzwignia orientacyjna: {estimated_leverage}x",
        f"Depozyt orientacyjny: {estimated_margin:.2f} USDT",
        f"Filtry: " + " | ".join(
            f"{key} {'OK' if value else 'NIE'}"
            for key, value in filters.items()
        ),
        "Filtry wymagane: " + (", ".join(ENABLED) if ENABLED else "brak"),
        "Uwaga: wielkosc zlecenia i depozyt sa szacunkiem, nie zleceniem Binance."
    ])

    if block_reasons:
        lines.append("Kontrola ograniczen: " + ", ".join(block_reasons))
    if notional == 0:
        lines.append("Nie mozna wyliczyc pozycji o dodatniej wielkosci.")

    return status, lines


def main():
    import sys

    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "live"

    if mode == "watch":
        previous_status = None
        while True:
            try:
                data = load_data()
                status, lines = analyze(data)
                print("\n" + time.strftime("%Y-%m-%d %H:%M:%S"))
                print("\n".join(lines))
                if status != previous_status:
                    print(f"Zmiana statusu: {previous_status} -> {status}")
                previous_status = status
            except KeyboardInterrupt:
                print("\nZatrzymano monitoring.")
                break
            except Exception as exc:
                print("Blad:", exc)
            time.sleep(WATCH_EVERY)
    else:
        data = load_data()
        status, lines = analyze(data)
        print("\n".join(lines))


if __name__ == "__main__":
    main()
