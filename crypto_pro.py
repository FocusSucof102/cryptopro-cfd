import report_24h_mod as r24
import quant_edge_pro_mod as qep
import nzt_cortex_mod as nzt
import meta_brain_mod as mbm
import quantum_nash_mod as qnm
import future_quantum_mod as fqm
import evolution_lab_mod as elm
import ai_quant_mod as aqm
import inst_orderflow_mod as iom
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
#    - Zrodlo danych/API skanera: wylacznie BITGET USDT-FUTURES (TOP-100 >10M$).
#    - Platforma gry uzytkownika: BITBASE FUTURES / CFD (uwzgledniac przy prowizjach,
#      dostepnosci par, dźwigni i minimalnych odleglosciach zlecen!).
#    - Silnik: Smart Dual-Mode (LONG+SHORT), Auto-Tuner, Audytor 1M (MFE/MAE),
#      Shadow Market Lab (analiza niskich procentow 45-61% netto po prowizji),
#      Straznik Portfela 24/7 oraz Radar Aktywnych Pozycji 60s.
# 4. NIE PRZYWRACAC: Zablokowanych API (BINANCE/BYBIT), 500 niszowych mikrotokentow
#    ani twardej blokady tylko jednego kierunku handlu.
# ==============================================================================
import auto_tuner_mod as atm
import watchdog_mod as wd
import session_analytics_mod as sam
import sniper_doctor_mod as sdm
from concurrent.futures import ThreadPoolExecutor, as_completed
CFD_SNOOZE_UNTIL = 0
CFD_LIVE_ACTIVE = True
SEEN_CFD_SIGS = {}
SCAN_STOP = False
import alpha_pro_mod as apm
import web_pump_radar_mod as wpr
import contract_audit_mod as cam
import backtest_2020 as bt20
import demo_sim_mod as ds24
import portfolio_mod as pf
import planner_mod as pm
from concurrent.futures import ThreadPoolExecutor, as_completed
import chart_mod as cm
#!/usr/bin/env python3
import os, sys, io, csv, json, time, math, shutil, select, threading, requests
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from statistics import mean
from flask import Flask, render_template_string, jsonify, redirect, url_for

CONFIG_FILE, TG_CONFIG_FILE, SETTINGS_FILE, CSV_FILE = "config_live.json", "tg_config.json", "scanner_settings.json", "signals_history.csv"
EXCHANGES = ["BINANCE", "BYBIT", "BITGET", "WEEX", "BITBASE"]
EX_MAX_DEV = {"BINANCE": 5.0, "BYBIT": 5.0, "BITGET": 5.0, "WEEX": 3.0, "BITBASE": 4.0}
MAX_LEV, MAX_MARGIN_FRACTION, FEE_SIDE_PCT, SLIPPAGE_BPS = 100, 0.80, 0.05, 2.0
LEVEL_CANDLES, STOP_ATR, NEAR_ATR, ATR_N, ADX_MIN, VOL_MULT = 48, 1.8, 1.8, 14, 20, 1.5
WATCH_EVERY, TIMEOUT = 300, 15

G, R, Y, C, B, W = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"
sent_cooldown, watched_far = {}, {}
LATEST = {"hits": [], "near": [], "time": "Brak skanu", "exchange": "BINANCE", "liq_only": True}
LIVE_ACTIVE = False
PROG = {"running": False, "pct": 0, "eta": 0, "sym": "", "done": 0, "total": 30}
last_term_view = None

def load_settings():
    """Realizuje logike: load settings."""
    d = {"capital": 200.0, "risk_pct": 1.0, "top_n": 30, "exchange": "BINANCE", "liq_only": True}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f: d.update(json.load(f))
    return d

def save_settings(cfg):
    """Realizuje logike: save settings. Parametry: cfg."""
    with open(SETTINGS_FILE, "w") as f: json.dump(cfg, f)

def fmt_p(v):
    """Realizuje logike: fmt p. Parametry: v."""
    if v >= 10000: return f"{v:8.1f}"
    if v >= 1000:  return f"{v:8.2f}"
    if v >= 10:    return f"{v:8.3f}"
    return f"{v:8.4f}"

def round_qty_down(qty, step):
    """Realizuje logike: round qty down. Parametry: qty, step."""
    q, s = Decimal(str(qty)), Decimal(str(step))
    return float((q / s).to_integral_value(rounding=ROUND_DOWN) * s) if s > 0 else 0.0

def tg_url(tok, m): return "https://" + chr(97) + "pi.telegram.org" + "/bot" + tok + "/" + m

def send_telegram(msg, kb=None):
    """Realizuje logike: send telegram. Parametry: msg, kb."""
    if not os.path.exists(TG_CONFIG_FILE): return
    cfg = json.load(open(TG_CONFIG_FILE))
    tok, cid = cfg.get("token","").strip(), cfg.get("chat_id","").strip()
    if not tok or not cid: return
    payload = {"chat_id": cid, "text": msg, "parse_mode": "HTML"}
    if kb: payload["reply_markup"] = kb
    try: requests.post(tg_url(tok, "sendMessage"), json=payload, timeout=4)
    except Exception: pass

def log_to_csv(row):
    """Realizuje logike: log to csv. Parametry: row."""
    ex = os.path.exists(CSV_FILE)
    fields = ["timestamp","exchange","symbol","side","price","entry","stop_loss","tp_1R","tp_2R","tp_3R","tp_4R","tp_5R","qty","notional_usdt","leverage","req_cap","eta_str"]
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not ex: w.writeheader()
        w.writerow(row)

HTTP_SESS = requests.Session()
HTTP_SESS.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"})

def get_json(url, **params):
    """Realizuje logike: get json. Parametry: url."""
    for att in range(2):
        try:
            r = HTTP_SESS.get(url, params=params, timeout=4)
            if r.status_code == 429:
                time.sleep(min(5, int(r.headers.get("Retry-After", 3))))
                continue
            if r.status_code != 200:
                return None
            return r.json()
        except Exception:
            if att == 0: time.sleep(0.3)
    return None

def u_join(*parts):
    """Realizuje logike: u join."""
    clean = [p.replace("://", chr(97) + "pi.") for p in parts]
    return chr(47).join(clean)

def get_market_meta(exchange, top_n):
    """Realizuje logike: get market meta. Parametry: exchange, top_n."""
    min_vol = 5000000.0 if load_settings().get("liq_only", True) else 250000.0
    rules, prices = {}, {}
    if exchange == "BYBIT":
        info = get_json(u_join("https:", "", "://bybit.com", "v5", "market", "instruments-info"), category="linear", limit=1000)
        tick = get_json(u_join("https:", "", "://bybit.com", "v5", "market", "tickers"), category="linear")
        if not isinstance(info, dict) or not isinstance(tick, dict): raise RuntimeError("Blad API Bybit")
        for x in info["result"]["list"]:
            sym = x["symbol"]
            if x.get("status") == "Trading" and sym.endswith("USDT"):
                lot = x["lotSizeFilter"]
                rules[sym] = {"step": float(lot["qtyStep"]), "min_qty": float(lot["minOrderQty"]), "min_notional": float(lot.get("minNotionalValue", 5.0)), "max_dev": EX_MAX_DEV.get(exchange, 5.0)}
        valid = [t for t in tick["result"]["list"] if isinstance(t, dict) and t.get("symbol") in rules and float(t.get("turnover24h", 0)) >= min_vol]
        valid.sort(key=lambda x: float(x.get("turnover24h", 0)), reverse=True)
        for t in valid[:top_n]: prices[t["symbol"]] = float(t["lastPrice"])
        return [t["symbol"] for t in valid[:top_n]], rules, prices
    elif exchange == "BITGET":
        info = get_json(u_join("https:", "", "://bitget.com", "api", "v2", "mix", "market", "contracts"), productType="USDT-FUTURES")
        tick = get_json(u_join("https:", "", "://bitget.com", "api", "v2", "mix", "market", "tickers"), productType="USDT-FUTURES")
        if not isinstance(info, dict) or not isinstance(tick, dict): raise RuntimeError("Blad API Bitget")
        for x in info["data"]:
            sym = x["symbol"]
            if x.get("symbolStatus") == "normal" and sym.endswith("USDT"):
                step = float(x.get("sizeMultiplier", 0.001))
                rules[sym] = {"step": step, "min_qty": float(x.get("minTradeNum", step)), "min_notional": float(x.get("minTradeUSDT", 5.0)), "max_dev": EX_MAX_DEV.get(exchange, 5.0)}
        valid = [t for t in tick["data"] if isinstance(t, dict) and t.get("symbol") in rules and float(t.get("turnover24h", 0)) >= min_vol]
        valid.sort(key=lambda x: float(x.get("usdtVolume", 0)), reverse=True)
        for t in valid[:top_n]: prices[t["symbol"]] = float(t["lastPr"])
        return [t["symbol"] for t in valid[:top_n]], rules, prices
    else:
        info = get_json(u_join("https:", "", "://binance.com", "fapi", "v1", "exchangeInfo"))
        tick = get_json(u_join("https:", "", "://binance.com", "fapi", "v1", "ticker", "24hr"))
        if isinstance(info, dict) and isinstance(tick, list):
            for x in info["symbols"]:
                sym = x["symbol"]
                if x.get("status") == "TRADING" and sym.endswith("USDT") and x.get("contractType") == "PERPETUAL":
                    flts = {flt["filterType"]: flt for flt in x["filters"]}
                    lot = flts.get("MARKET_LOT_SIZE") or flts["LOT_SIZE"]
                    nf = flts.get("MIN_NOTIONAL") or flts.get("NOTIONAL")
                    pf = flts.get("PERCENT_PRICE")
                    m_dev = min(10.0, (float(pf.get("multiplierUp", 1.05)) - 1.0)*100.0) if pf else 5.0
                    rules[sym] = {"step": float(lot["stepSize"]), "min_qty": float(lot["minQty"]), "min_notional": float(nf.get("notional", nf.get("minNotional", 5.0))) if nf else 5.0, "max_dev": min(m_dev, EX_MAX_DEV.get(exchange, 5.0))}
            valid = [t for t in tick if isinstance(t, dict) and t.get("symbol") in rules and float(t.get("turnover24h", 0)) >= min_vol]
            valid.sort(key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
            for t in valid[:top_n]: prices[t["symbol"]] = float(t["lastPrice"])
            return [t["symbol"] for t in valid[:top_n]], rules, prices
        st = get_json(u_join("https:", "", "://binance.com", "api", "v3", "ticker", "24hr"))
        if isinstance(st, list):
            valid = [t for t in st if isinstance(t, dict) and t.get("symbol","").endswith("USDT") and float(t.get("quoteVolume", 0)) >= min_vol]
            valid.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)
            for t in valid[:top_n]:
                sym = t["symbol"]
                prices[sym] = float(t["lastPrice"])
                rules[sym] = {"step": 0.001 if prices[sym] > 10 else 1.0, "min_qty": 0.001 if prices[sym] > 10 else 1.0, "min_notional": 5.0, "max_dev": EX_MAX_DEV.get(exchange, 5.0)}
            return [t["symbol"] for t in valid[:top_n]], rules, prices
        raise RuntimeError("Brak polaczenia z API.")

def _parse_rows(rows, idx_o, idx_h, idx_l, idx_c, idx_v):
    """Realizuje logike: parse rows. Parametry: rows, idx_o, idx_h, idx_l, idx_c, idx_v."""
    return {
        "o": [float(r.__getitem__(idx_o)) for r in rows],
        "h": [float(r.__getitem__(idx_h)) for r in rows],
        "l": [float(r.__getitem__(idx_l)) for r in rows],
        "c": [float(r.__getitem__(idx_c)) for r in rows],
        "v": [float(r.__getitem__(idx_v)) for r in rows],
    }

def fetch_klines(exchange, sym, interval, limit):
    """Realizuje logike: fetch klines. Parametry: exchange, sym, interval, limit."""
    now_ms = int(time.time() * 1000)
    if exchange == "BYBIT":
        imap = {"1d": "D", "4h": "240", "1h": "60", "15m": "15"}
        raw = get_json(u_join("https:", "", "://bybit.com", "v5", "market", "kline"), category="linear", symbol=sym, interval=imap.get(interval, "60"), limit=limit)
        if not isinstance(raw, dict) or not raw.get("result", {}).get("list"): return None
        lst = list(reversed(raw.get("result").get("list")))
        if len(lst) < 55: return None
        return _parse_rows(lst, 1, 2, 3, 4, 5)
    elif exchange == "BITGET":
        imap = {"1d": "1D", "4h": "4H", "1h": "1H", "15m": "15m"}
        raw = get_json(u_join("https:", "", "://bitget.com", "api", "v2", "mix", "market", "candles"), productType="USDT-FUTURES", symbol=sym, granularity=imap.get(interval, "1H"), limit=min(limit, 200))
        if not isinstance(raw, dict) or not raw.get("data"): return None
        lst = raw.get("data")
        if len(lst) < 55: return None
        return _parse_rows(lst, 1, 2, 3, 4, 5)
    else:
        raw = get_json(u_join("https:", "", "://binance.com", "fapi", "v1", "klines"), symbol=sym, interval=interval, limit=limit)
        if not isinstance(raw, list):
            raw = get_json(u_join("https:", "", "://binance.com", "api", "v3", "klines"), symbol=sym, interval=interval, limit=limit)
        if not isinstance(raw, list): return None
        raw = [k for k in raw if int(k.__getitem__(6)) < now_ms]
        if len(raw) < 55: return None
        return _parse_rows(raw, 1, 2, 3, 4, 5)

def ema(v, p):
    """Realizuje logike: ema. Parametry: v, p."""
    a = 2.0 / (p + 1.0); res, cur = [], v.__getitem__(0)
    for x in v: cur = x * a + cur * (1.0 - a); res.append(cur)
    return res

def atr(h, l, c, p=ATR_N):
    """Realizuje logike: atr. Parametry: h, l, c, p."""
    n = len(c); res = [0.0]*n
    tr = [h[0]-l[0]] + [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])) for i in range(1, n)]
    cur = sum(tr[1:p+1])/p; res[p] = cur
    for i in range(p+1, n): cur = (cur*(p-1)+tr[i])/p; res[i] = cur
    return res

def adx(h, l, c, p=14):
    """Realizuje logike: adx. Parametry: h, l, c, p."""
    n = len(c); res = [0.0]*n; tr, pdm, mdm = [0.0]*n, [0.0]*n, [0.0]*n
    for i in range(1, n):
        up, dn = h[i]-h[i-1], l[i-1]-l[i]
        pdm[i] = up if up>dn and up>0 else 0.0; mdm[i] = dn if dn>up and dn>0 else 0.0
        tr[i] = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
    st, sp, sm = sum(tr[1:p+1]), sum(pdm[1:p+1]), sum(mdm[1:p+1]); dx = [0.0]*n
    for i in range(p, n):
        if i > p: st = st - st/p + tr[i]; sp = sp - sp/p + pdm[i]; sm = sm - sm/p + mdm[i]
        pdi = 100.0*sp/st if st else 0.0; mdi = 100.0*sm/st if st else 0.0
        dx[i] = 100.0*abs(pdi-mdi)/(pdi+mdi) if (pdi+mdi) else 0.0
    cur = mean(dx[p:2*p]); res[2*p-1] = cur
    for i in range(2*p, n): cur = (cur*(p-1)+dx[i])/p; res[i] = cur
    return res

def get_trend(c):
    """Realizuje logike: get trend. Parametry: c."""
    e20, e50 = ema(c, 20), ema(c, 50)
    return 1 if c[-1] > e20[-1] > e50[-1] else (-1 if c[-1] < e20[-1] < e50[-1] else 0)

def analyze_trajectory(c, level, td, atr_val):
    """Realizuje logike: analyze trajectory. Parametry: c, level, td, atr_val."""
    dist = max(0.0, (level - c[-1]) if td == 1 else (c[-1] - level))
    if dist == 0: return "TERAZ", "Wybija poziom"
    # Analiza przebiegu ostatnich 6h (dynamika + zmiennosc ATR)
    slope = ((c[-1] - c[-7]) if td == 1 else (c[-7] - c[-1])) / 6.0 if len(c) >= 8 else 0.0
    momentum = "Przyspiesza" if slope > atr_val * 0.25 else ("Konsolidacja" if slope >= 0 else "Korekta")
    speed = max(slope, atr_val * 0.35)
    hrs = dist / speed if speed > 0 else 99.0
    eta = f"~{max(5, int(hrs*60))}m" if hrs < 1.0 else (f"~{hrs:.1f}h" if hrs <= 24.0 else ">24h")
    return eta, momentum

def make_chart_png(exchange, symbol, entry=None, stop=None, tp_list=None):
    """Realizuje logike: make chart png. Parametry: exchange, symbol, entry, stop, tp_list."""
    h1 = fetch_klines(exchange, symbol, "1h", 80)
    if not h1: return None
    closes = [round(x, 4) for x in h1["c"][-45:]]
    labels = [str(i) for i in range(len(closes))]
    ds = [{"label": f"{symbol} ({exchange} 1H)", "data": closes, "borderColor": "#58a6ff", "backgroundColor": "rgba(88,166,255,0.12)", "borderWidth": 2, "pointRadius": 0, "fill": True}]
    if entry: ds.append({"label": f"Wejscie: {fmt_p(entry).strip()}", "data": [entry]*len(closes), "borderColor": "#f0883e", "borderWidth": 1.5, "pointRadius": 0, "fill": False})
    if stop: ds.append({"label": f"SL: {fmt_p(stop).strip()}", "data": [stop]*len(closes), "borderColor": "#f85149", "borderWidth": 1.5, "pointRadius": 0, "fill": False})
    if tp_list:
        for k, idx in [(1,0), (3,2), (5,4)]:
            ds.append({"label": f"TP {k}R: {fmt_p(tp_list[idx]).strip()}", "data": [tp_list[idx]]*len(closes), "borderColor": "#3fb950", "borderWidth": 1.2, "pointRadius": 0, "fill": False})
    cfg = {"type": "line", "data": {"labels": labels, "datasets": ds}, "options": {"title": {"display": True, "text": f"{symbol} ({exchange})", "fontColor": "#fff"}, "legend": {"labels": {"fontColor": "#c9d1d9"}}, "scales": {"xAxes": [{"display": False}], "yAxes": [{"ticks": {"fontColor": "#8b949e"}, "gridLines": {"color": "#30363d"}}]}}}
    r = requests.post("https://quickchart.io", json={"backgroundColor": "#0d1117", "width": 700, "height": 380, "chart": cfg}, timeout=15)
    return io.BytesIO(r.content) if r.status_code == 200 else None

def get_exchange_url(ex, sym):
    """Realizuje logike: get exchange url. Parametry: ex, sym."""
    base = sym.replace("USDT", "")
    sl = chr(47)
    if ex == "BINANCE": return "https:" + sl*2 + "://binance.com" + sl + "en" + sl + "futures" + sl + sym
    elif ex == "BYBIT": return "https:" + sl*2 + "://bybit.com" + sl + "trade" + sl + "usdt" + sl + sym
    elif ex == "BITGET": return "https:" + sl*2 + "://bitget.com" + sl + "futures" + sl + "usdt" + sl + sym
    elif ex == "WEEX": return "https:" + sl*2 + "://weex.com" + sl + "futures" + sl + f"{base}-USDT"
    else: return "https:" + sl*2 + "www.bitbase.com"

def format_tg_card(h, ex, tag=""):
    """Realizuje logike: format tg card. Parametry: h, ex, tag."""
    tp1, tp2, tp3, tp4, tp5 = h["tp"]
    ico = "🟢" if h["side"] == "LONG" else "🔴"
    st = "TRIGGER" if h["is_trig"] else ("DALEKO" if not h["price_ok"] else "GOTOWY")
    return (
        f"🚨 <b>{st}{tag} | {h['symbol']} ({ex})</b>\n"
        f"{ico} Kierunek: <b>{h['side']}</b> | 💰 Min. Kap: <b>{h['req_cap']}$</b>\n"
        f"📏 Dystans: <b>{h['dist_pct']:.2f}% ({h['dist_atr']:.2f} ATR)</b>" + (f" ⚠️ <b>Brakuje {h['gap_pct']}% do limitu {ex}!</b>" if not h.get("price_ok", True) else " ✅ <b>W limicie gieldy</b>") + "\n"
        f"⏱ Przebieg: <b>{h['mom']}</b> | Czas: <b>{h['eta_str']}</b>\n\n"
        f"📊 Cena teraz: <code>{fmt_p(h['price']).strip()}</code>\n"
        f"🎯 Wejście: <code>{fmt_p(h['entry']).strip()}</code>\n"
        f"🛑 Stop Loss: <code>{fmt_p(h['stop']).strip()}</code>\n"
        f"───────────────\n"
        f"✅ 1R: <code>{fmt_p(tp1).strip()}</code>  |  2R: <code>{fmt_p(tp2).strip()}</code>\n"
        f"✅ 3R: <code>{fmt_p(tp3).strip()}</code>  |  4R: <code>{fmt_p(tp4).strip()}</code>\n"
        f"🏆 5R: <code>{fmt_p(tp5).strip()}</code>"
    )

def _scan_one_coin(args):
    """Realizuje logike: scan one coin. Parametry: args."""
    ex, sym, price, rules, enabled, cap, rpct = args
    d1 = fetch_klines(ex, sym, "1d", 220)
    h4 = fetch_klines(ex, sym, "4h", 80)
    if not d1 or not h4: return None
    td = get_trend(h4["c"])
    h1 = fetch_klines(ex, sym, "1h", 120)
    if not h1 or get_trend(h1["c"]) == 0: return None
    td = get_trend(h1["c"])
    m15 = fetch_klines(ex, sym, "15m", 70)
    if not m15: return None

    i = len(h1["c"]) - 1
    a_vals = atr(h1["h"], h1["l"], h1["c"]); atr_val = a_vals[i]
    if price < 0.001 or atr_val <= 0 or atr_val > price * 0.25: return None
    level = max(h1["h"][i - LEVEL_CANDLES:i]) if td == 1 else min(h1["l"][i - LEVEL_CANDLES:i])
    dist_atr = (level - price)/atr_val if td == 1 else (price - level)/atr_val
    dist_pct = abs(level - price)/price * 100.0 if price > 0 else 0.0
    eta_str, mom = analyze_trajectory(h1["c"], level, td, atr_val)
    beyond_15m = m15["c"][-1] > level if td == 1 else m15["c"][-1] < level
    beyond_now = td * (price - level) > 0
    ext_atr = td * (price - level) / atr_val
    e200, adx_v = ema(d1["c"], 200), adx(h1["h"], h1["l"], h1["c"])
    f_vals = {"adx": adx_v[i] >= ADX_MIN, "vol": h1["v"][i] >= VOL_MULT * mean(h1["v"][i - 20:i]), "macro": (d1["c"][-1] > e200[-1]) == (td == 1)}
    missing = []

    if beyond_now and beyond_15m and ext_atr <= NEAR_ATR and not missing: is_trig = True
    elif not beyond_now and dist_atr <= NEAR_ATR and not missing: is_trig = False
    else:
        if not beyond_now and dist_atr <= 1.5:
            side_n = "LONG" if td == 1 else "SHORT"
            ok_a, bonus_a, alpha_tag = apm.evaluate_alpha(sys.modules[__name__], sym, side_n, h1)
            win_prob = 55
            if not ok_a: return None
            win_prob = min(96, max(45, win_prob + bonus_a))
            return ("near", {"symbol": sym, "side": "LONG" if td == 1 else "SHORT", "price": price, "dist_atr": round(dist_atr, 2), "dist_pct": round(dist_pct, 2), "eta_str": eta_str, "mom": mom, "missing": ",".join(missing) or "Blisko wybicia"})
        return None

    entry, stop_dist = (price if is_trig else level), STOP_ATR * atr_val
    stop = entry - td * stop_dist
    tp = [entry + td * k * stop_dist for k in (1, 2, 3, 4, 5)]
    r_unit = stop_dist + ((FEE_SIDE_PCT/100.0) + (SLIPPAGE_BPS/10000.0)) * (entry + stop)
    raw_min = max(rules["min_qty"], max(rules["min_notional"], 5.5) / entry)
    min_q = float(Decimal(str(math.ceil(raw_min / rules["step"]))) * Decimal(str(rules["step"])))
    req_cap = math.ceil((min_q * r_unit) / (rpct / 100.0))
    u_cap = max(cap, float(req_cap))
    qty = max(min_q, round_qty_down((u_cap * rpct / 100.0) / r_unit, rules["step"]))
    notional = qty * entry
    lev = max(1, math.ceil(notional / (u_cap * MAX_MARGIN_FRACTION)))
    max_d = rules.get("max_dev", EX_MAX_DEV.get(ex, 5.0))
    dev_pct = abs(entry - price)/price * 100.0 if price > 0 else 999.0
    price_ok = dev_pct <= max_d
    gap_pct = round(max(0.0, dev_pct - max_d), 2)
    adx_val = round(adx_v[i], 1)
    vol_mult_val = round(h1["v"][i] / (mean(h1["v"][i - 20:i]) or 1.0), 2)
    prob = 52
    if adx_val >= 25: prob += 12
    elif adx_val >= 20: prob += 6
    if vol_mult_val >= 1.5: prob += 10
    elif vol_mult_val >= 1.1: prob += 5
    if mom in ("Wybija poziom", "Przyspiesza"): prob += 10
    elif mom == "Stabilny": prob += 5
    if is_trig: prob += 6
    if not price_ok: prob -= 8
    win_prob = max(42, min(92, prob))
    prob_tier = "🔥 WYSOKA (>=75%)" if win_prob >= 75 else ("✅ SOLIDNA (60-74%)" if win_prob >= 60 else "⚠️ RYZYKOWNA (<60%)")

    return ("hit", {"win_prob": win_prob, "prob_tier": prob_tier, "adx": adx_val, "vol_r": vol_mult_val, "symbol": sym, "side": "LONG" if td == 1 else "SHORT", "is_trig": is_trig, "price_ok": price_ok, "gap_pct": gap_pct, "max_dev": max_d, "price": price, "entry": entry, "stop": stop, "tp": tp, "dist_atr": round(dist_atr, 2), "dist_pct": round(dist_pct, 2), "eta_str": eta_str, "mom": mom, "qty": qty, "notional": round(notional, 1), "lev": lev, "req_cap": req_cap, "dev_pct": dev_pct})

EX_COUNTS = {}

def get_dynamic_top_tiers(ex):
    """Realizuje logike: get dynamic top tiers. Parametry: ex."""
    liq = load_settings().get("liq_only", True)
    ckey = f"{ex}_{liq}"
    try:
        syms, _, _ = get_market_meta(ex, 2000)
        if syms: EX_COUNTS[ckey] = len(syms)
    except Exception:
        pass
    mx = EX_COUNTS.get(ckey, 65 if liq else 350)
    tiers = [x for x in (30, 100, 200) if x < mx]
    if mx not in tiers: tiers.append(mx)
    return tiers, mx

BTC_LIVE_REGIME = {"ts": 0, "dir": 0, "label": "NEUTRALNY"}

def get_live_btc_regime():
    """Realizuje logike: get live btc regime."""
    if time.time() - BTC_LIVE_REGIME["ts"] < 180 and BTC_LIVE_REGIME["dir"] != 0:
        return BTC_LIVE_REGIME["dir"], BTC_LIVE_REGIME["label"]
    kl = fetch_klines("BYBIT", "BTCUSDT", "1h", 220) or fetch_klines("BITGET", "BTCUSDT", "1h", 220)
    if kl and len(kl["c"]) >= 200:
        c_b = kl["c"]
        e200 = ema(c_b, 200).__getitem__(-1)
        cur = c_b.__getitem__(-1)
        d = 1 if cur > e200 else -1
        lbl = f"🟢 HOSSA BTC ({round(cur,1)} > EMA200) — Priorytet LONG + Silne SHORT" if d == 1 else f"🔴 BESSA BTC ({round(cur,1)} < EMA200) — Priorytet SHORT + Silne LONG"
        BTC_LIVE_REGIME.update({"ts": time.time(), "dir": d, "label": lbl})
        return d, lbl
    return 0, "⚪ BRAK DANYCH BTC"

def run_full_scan(show_term=False, tg_mid=None):
    """Realizuje logike: run full scan. Parametry: show_term, tg_mid."""
    if PROG["running"]:
        if show_term: print(f"{Y}Skanowanie juz trwa w tle ({PROG['pct']}%)...{W}")
        return
    cfg = load_settings()
    ex, cap, rpct, top_n = cfg["exchange"], cfg["capital"], cfg["risk_pct"], cfg["top_n"]
    PROG.update({"running": True, "pct": 1, "eta": 6, "sym": "Start...", "done": 0, "total": top_n})
    t0 = time.time()
    tg_cfg = json.load(open(TG_CONFIG_FILE)) if os.path.exists(TG_CONFIG_FILE) else {}
    tok, cid = tg_cfg.get("token","").strip(), tg_cfg.get("chat_id","").strip()
    last_tg_t = 0

    try:
        enabled = json.load(open(CONFIG_FILE)).get("enabled_filters", ["adx","macro","vol"]) if os.path.exists(CONFIG_FILE) else ["adx","macro","vol"]
        syms, rules_map, prices_map = get_market_meta(ex, top_n)
        hits, near = [], []
        tasks = [(ex, sym, prices_map[sym], rules_map[sym], enabled, cap, rpct) for sym in syms]

        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(_scan_one_coin, t): t[1] for t in tasks}
            done_cnt = 0
            for fut in as_completed(futs):
                done_cnt += 1
                sym = futs[fut]
                el = time.time() - t0
                eta_s = max(1, int((top_n - done_cnt) * (el / done_cnt)))
                pct = int((done_cnt / top_n) * 100)
                PROG.update({"pct": pct, "eta": eta_s, "sym": sym, "done": done_cnt})
                if show_term:
                    bar = "█"*(pct//10) + "░"*(10 - pct//10)
                    sys.stdout.write(f"\r{C}[{bar}] {pct:3d}% | ETA ~{eta_s:2d}s | {sym:<10}{W}"); sys.stdout.flush()
                if tg_mid and tok and cid and (time.time() - last_tg_t >= 2.0 or done_cnt == top_n):
                    last_tg_t = time.time()
                    bar = "█"*(pct//10) + "░"*(10 - pct//10)
                    try: requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": tg_mid, "text": f"⏳ <b>Skanuje {ex} ({sym})</b>\n<code>[{bar}] {pct}%</code> | ETA: <b>~{eta_s}s</b>", "parse_mode": "HTML"}, timeout=5)
                    except Exception: pass

                res = fut.result()
                if not res: continue
                kind, obj = res
                if kind == "near": near.append(obj)
                elif kind == "hit":
                    hits.append(obj)
                    key_f = f"{ex}:{obj['symbol']}"
                    if not obj["price_ok"]:
                        if key_f not in watched_far:
                            pass
                        watched_far[key_f] = {"ex": ex, "sym": obj["symbol"], "entry": obj["entry"], "max_dev": obj["max_dev"], "side": obj["side"]}
                    elif key_f in watched_far:
                        del watched_far[key_f]
                        pass

                    if obj["is_trig"] and obj["price_ok"] and time.time() - sent_cooldown.get(key_f, 0) > 3600:
                        sent_cooldown[key_f] = time.time()
                        tp1, tp2, tp3, tp4, tp5 = obj["tp"]
                        log_to_csv({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "exchange": ex, "symbol": obj["symbol"], "side": obj["side"], "price": obj["price"], "entry": round(obj["entry"],6), "stop_loss": round(obj["stop"],6), "tp_1R": round(tp1,6), "tp_2R": round(tp2,6), "tp_3R": round(tp3,6), "tp_4R": round(tp4,6), "tp_5R": round(tp5,6), "qty": obj["qty"], "notional_usdt": round(obj["notional"],2), "leverage": obj["lev"], "req_cap": obj["req_cap"], "eta_str": obj["eta_str"]})
                        pass

        if show_term: print("\r" + " " * 55 + "\r", end="")
        LATEST.update({"hits": sorted(hits, key=lambda x: (-x.get("win_prob", 50), x["req_cap"])), "near": sorted(near, key=lambda x: x["dist_atr"]), "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "exchange": ex})
    finally:
        PROG.update({"running": False, "pct": 100, "eta": 0, "sym": "Gotowe"})

app = Flask(__name__)
HTML_TPL = """<!DOCTYPE html>\n<html lang="pl"><head><meta http-equiv="refresh" content="30"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Crypto Pro Multi-Scanner</title>\n<style>\nbody{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;margin:0;padding:12px}\n.hdr{display:flex;justify-content:space-between;align-items:center;background:#161b22;padding:12px;border-radius:10px;border:1px solid #30363d;margin-bottom:12px;flex-wrap:wrap;gap:8px}\n.btn{background:#238636;color:#fff;border:none;padding:7px 10px;border-radius:6px;font-weight:bold;text-decoration:none;font-size:12px;cursor:pointer}\n.btn-b{background:#1f6feb} .btn-g{background:#30363d}\n.pwrap{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:10px;margin-bottom:12px;display:{{'block' if prog.running else 'none'}}}\n.pbar-bg{background:#0d1117;border-radius:8px;height:18px;overflow:hidden;border:1px solid #30363d;margin-top:6px}\n.pbar-fill{background:linear-gradient(90deg,#1f6feb,#3fb950);height:100%;width:{{prog.pct}}%;transition:width 0.4s}\n.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:12px}\n.long{color:#3fb950;font-weight:bold} .short{color:#f85149;font-weight:bold}\n.badge{padding:2px 7px;border-radius:12px;font-size:11px;font-weight:bold;background:#1f6feb;color:#fff} .trig{background:#238636} .far{background:#da3633}\n.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}\n.box{background:#0d1117;padding:6px;border-radius:6px;border:1px solid #21262d;font-size:12px;text-align:center} .cp{cursor:pointer;color:#58a6ff;font-weight:bold}\n</style>\n<script>\nfunction cp(v){navigator.clipboard.writeText(v);alert('Skopiowano: '+v);}\nfunction trig(){document.getElementById('pwrap').style.display='block';fetch('/start');poll();}\nfunction poll(){let iv=setInterval(()=>{fetch('/prog').then(r=>r.json()).then(d=>{document.getElementById('pfill').style.width=d.pct+'%';document.getElementById('ptxt').innerText='Skanuje: '+d.sym+' ('+d.done+'/'+d.total+') — '+d.pct+'% | ETA: ~'+d.eta+'s';if(!d.running&&d.pct>=100){clearInterval(iv);location.reload();}});},800);}\nwindow.onload=()=>{if({{'true' if prog.running else 'false'}})poll();};\n</script></head><body>\n<div class="hdr">\n  <div><b>📊 {{cfg.exchange}} TOP {{cfg.top_n}}</b><br><small style="color:#8b949e">{{res.time}} | Kap: {{cfg.capital}}$</small></div>\n  <div style="display:flex;gap:4px;flex-wrap:wrap">\n    {% for e in ['BINANCE','BYBIT','BITGET','WEEX','BITBASE'] %}\n    <a href="/ex/{{e}}" class="btn {{'btn-b' if cfg.exchange==e else 'btn-g'}}">{{'✅ ' if cfg.exchange==e else ''}}{{e}}</a>\n    {% endfor %}\n    <a href="/portfolio" class="btn" style="background:#d29922;color:#000">💼 Portfel ({{pf.count}})</a> <a href="/planner" class="btn btn-b">🧮 Planner</a> <a href="/demo24" class="btn btn-g">🧪 Demo 24H</a> <a href="/backtest?sym=BTCUSDT" class="btn btn-g">📜 Backtest 2020-26</a>\n    <a href="/live_tgl" class="btn" style="background:{{'#da3633' if live else '#30363d'}}">{{'⏹ Stop Live' if live else '🔄 Auto Live 5m'}}</a> <button onclick="trig()" class="btn">🔍 Skanuj</button>\n  </div>\n</div>\n<div id="pwrap" class="pwrap"><div id="ptxt" style="font-size:12px;color:#58a6ff;font-weight:bold">Skanuje: {{prog.sym}} — {{prog.pct}}% | ETA: ~{{prog.eta}}s</div><div class="pbar-bg"><div id="pfill" class="pbar-fill"></div></div></div>\n<div class="card" style="padding:8px 12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;font-size:12px"><div><b>💧 Grupa:</b>
    <a href="/liq/1" class="btn {{'btn-b' if cfg.liq_only else 'btn-g'}}" style="padding:3px 7px;font-size:11px">{{'✅ ' if cfg.liq_only else ''}}💧 Plynne (&gt;5M$)</a>
    <a href="/liq/0" class="btn {{'btn-b' if not cfg.liq_only else 'btn-g'}}" style="padding:3px 7px;font-size:11px;margin-right:6px">{{'✅ ' if not cfg.liq_only else ''}}🌊 Wszystkie</a>
    <b>📊 Ilosc:</b> {% for n in tiers %}<a href="/top/{{n}}" class="btn {{'btn-b' if cfg.top_n==n else 'btn-g'}}" style="padding:3px 7px;font-size:11px;margin-right:3px">{{'✅ ' if cfg.top_n==n else ''}}{{'WSZYSTKIE (' ~ n ~ ')' if n==mx_coins else 'TOP ' ~ n}}</a>{% endfor %}</div><form action="/go_analyze" method="get" style="display:flex;gap:4px"><input name="sym" placeholder="np. BTCUSDT" style="background:#0d1117;color:#fff;border:1px solid #30363d;border-radius:5px;padding:4px 7px;width:105px;font-size:12px"><button type="submit" class="btn btn-b" style="padding:4px 8px;font-size:11px">📈 Analizuj</button></form></div>
<div class="card" style="padding:8px 12px;border-color:#d29922;font-size:12px">
  <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px">
    <span>💰 Kapital: <b>{{pf.capital}}$</b></span>
    <span>🔒 Margin: <b>{{pf.used_margin}}$</b> ({{pf.margin_pct}}%)</span>
    <span>🟢 Wolny limit: <b>{{pf.free_margin}}$</b></span>
    <span>⚠️ Ryzyko: <b>{{pf.active_risk}}$</b> ({{pf.risk_pct}}%)</span>
  </div>
  <div style="margin-top:4px;color:#8b949e">{{pf.status}}</div>
</div>
<h3>🎯 Okazje ({{res.hits|length}})</h3>\n{% for h in res.hits %}<div class="card">\n  <div style="display:flex;justify-content:space-between;align-items:center">\n    <span><b style="font-size:16px">{{h.symbol}}</b> <span class="{{'long' if h.side=='LONG' else 'short'}}">{{h.side}}</span></span>\n    <a href="/add_pos?sym={{h.symbol}}" class="btn" style="padding:2px 7px;font-size:11px;margin-right:4px;background:#238636">➕ Obstawiam</a><a href="/planner?sym={{h.symbol}}&entry={{h.entry}}&stop={{h.stop}}" class="btn" style="padding:2px 7px;font-size:11px;margin-right:4px;background:#8957e5">🧮 Plan</a><a href="/analyze/{{h.symbol}}" class="btn btn-b" style="padding:2px 7px;font-size:11px;margin-right:4px">📈 Wykres</a><a href="/open_ex/{{h.symbol}}" target="_blank" class="btn" style="padding:2px 7px;font-size:11px;margin-right:4px">🚀 {{cfg.exchange}}</a><span class="badge {{'trig' if h.is_trig else ('far' if not h.price_ok else '')}}">{{'TRIGGER' if h.is_trig else ('DALEKO' if not h.price_ok else 'GOTOWY')}} | Min. {{h.req_cap}}$</span>\n  </div>\n  <div style="font-size:12px;color:#8b949e;margin-top:4px">📏 Dystans: <b>{{h.dist_pct}}% ({{h.dist_atr}} ATR)</b> {% if not h.price_ok %}<span style="color:#f85149">(Brakuje {{h.gap_pct}}% do limitu {{cfg.exchange}})</span>{% endif %} | 📈 <b>{{h.mom}}</b> | ⏱ Czas: <b style="color:#d29922">{{h.eta_str}}</b></div>\n  <div class="grid"><div class="box">Cena<br><b>{{h.price}}</b></div><div class="box" onclick="cp('{{h.entry}}')">Wejscie 📋<br><span class="cp">{{h.entry|round(4)}}</span></div><div class="box" onclick="cp('{{h.stop}}')">SL 📋<br><span class="cp" style="color:#f85149">{{h.stop|round(4)}}</span></div></div>\n  <div class="grid" style="grid-template-columns:repeat(5,1fr)">{% for t in h.tp %}<div class="box" onclick="cp('{{t|round(4)}}')">{{loop.index}}R 📋<br><span class="cp">{{t|round(3)}}</span></div>{% endfor %}</div>\n</div>{% else %}<div class="card" style="color:#8b949e">Brak aktywnych sygnalow. Kliknij <b>Skanuj</b> lub <b>Demo</b>.</div>{% endfor %}\n<h3>👀 Obserwowane / W poblizu ({{res.near|length}})</h3>\n{% for n in res.near %}<div class="card" style="padding:9px 12px;font-size:13px">\n  <div style="display:flex;justify-content:space-between"><span><b>{{n.symbol}}</b> <span class="{{'long' if n.side=='LONG' else 'short'}}">{{n.side}}</span> ({{n.price}})</span><span><a href="/analyze/{{n.symbol}}" class="btn btn-b" style="padding:2px 6px;font-size:11px">📈 Wykres</a> <span style="color:#58a6ff">⏱ {{n.eta_str}}</span></span></div>\n  <div style="color:#d29922;font-size:12px;margin-top:3px">Dystans: {{n.dist_pct}}% ({{n.dist_atr}} ATR) | Brak: {{n.missing}}</div>\n</div>{% endfor %}\n</body></html>"""

@app.route("/toggle/<k>")
def r_tgl(k): cm.toggle_chart_opt(k); return redirect(url_for("index"))

@app.route("/img/<sym>")
def r_img(sym):
    """Realizuje logike: r img. Parametry: sym."""
    from flask import send_file
    buf, _ = cm.build_chart_buf(load_settings()["exchange"], sym)
    return send_file(buf, mimetype="image/png") if buf else ("Blad", 404)

@app.route("/analyze/<sym>")
def r_an(sym):
    """Realizuje logike: r an. Parametry: sym."""
    ex = load_settings()["exchange"]
    _, ta = cm.build_chart_buf(ex, sym)
    if not ta: return "Brak danych"
    opts = cm.get_chart_opts()
    all_on = all(opts.values())
    b_all = f'<a href="/toggle/all" style="color:#fff;background:{"#238636" if all_on else "#da3633"};padding:5px 9px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:bold;margin-right:6px">{"✅ Wylacz WSZYSTKIE" if all_on else "⚡ Wlacz WSZYSTKIE"}</a>'
    btns = b_all + " ".join(f'<a href="/toggle/{k}" style="color:#58a6ff;background:#161b22;border:1px solid #30363d;padding:4px 8px;border-radius:6px;text-decoration:none;font-size:12px;margin-right:4px">{"✅" if opts[k] else "❌"} {lbl}</a>' for k, lbl in [("ema","EMA 5/13"),("smc","BOS/CHoCH/POC"),("levels","TP/BUY/SL"),("vol","Wolumen"),("hurst","Hurst"),("rsi","RSI 14"),("macd","MACD"),("chop","CHOP 14")])
    return f'<body style="background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:12px"><a href="/" style="color:#fff;background:#1f6feb;padding:6px 10px;border-radius:6px;text-decoration:none">⬅ Powrot</a> <b style="margin-left:6px">{sym} ({ex})</b><div style="margin:10px 0;display:flex;flex-wrap:wrap;gap:4px">{btns}</div><img src="/img/{sym}" style="width:100%;border-radius:8px"><div style="background:#161b22;padding:12px;border-radius:8px;margin-top:10px;font-size:13px"><b>🏛 Struktura SMC:</b> <span style="color:#d2a8ff">{ta["smc"]["struct"]}</span> | <b>Luka:</b> {ta["smc"]["fvg"]}<br><b>🧠 Wniosek:</b> {ta["summary"]}<br><b>📊 Wskazniki:</b> 1D:{ta["t1d"]} | 1H:{ta["t1h"]} | RSI:{ta["rsi"]} | CHOP:{ta["chop"]} | MACD:{ta["macd"]} | ADX:{ta["adx"]} | ATR:{ta["atr_pct"]}% | Vol:{ta["vol_r"]}x | ETA:{ta["eta"]}</div></body>'

@app.route("/open_ex/<sym>")
def r_open_ex(sym): return redirect(get_exchange_url(load_settings()["exchange"], sym))

@app.route("/top/<int:n>")
def r_top(n):
    """Realizuje logike: r top. Parametry: n."""
    c = load_settings(); c["top_n"] = n; save_settings(c)
    return redirect(url_for("index"))

@app.route("/live_tgl")
def r_live_tgl():
    """Realizuje logike: r live tgl."""
    global LIVE_ACTIVE
    LIVE_ACTIVE = not LIVE_ACTIVE
    return redirect(url_for("index"))

@app.route("/go_analyze")
def r_go_analyze():
    """Realizuje logike: r go analyze."""
    from flask import request
    sym = request.args.get("sym", "BTCUSDT").strip().upper()
    if not sym.endswith("USDT"): sym += "USDT"
    return redirect(url_for("r_an", sym=sym))

@app.route("/planner")
def r_planner():
    """Realizuje logike: r planner."""
    from flask import request
    cfg = load_settings()
    ex = cfg["exchange"]
    sym = request.args.get("sym", "BTCUSDT").strip().upper()
    if not sym.endswith("USDT"): sym += "USDT"
    cap = float(request.args.get("cap", cfg.get("capital", 200.0)))
    rpct = float(request.args.get("rpct", cfg.get("risk_pct", 1.0)))
    mlev = int(request.args.get("mlev", 20))
    ent_s = request.args.get("entry", "").strip()
    sl_s = request.args.get("stop", "").strip()
    ent = float(ent_s) if ent_s else None
    sl = float(sl_s) if sl_s else None
    p = pm.calc_plan(ex, sym, cap, rpct, mlev, ent, sl)
    if not p: return "Brak danych dla " + sym
    tp1, tp2, tp3, tp4, tp5 = p["tp"]
    st_col = "#238636" if p["passed"] else "#da3633"
    st_txt = "✅ PASS — ZLECENIE BEZPIECZNE" if p["passed"] else f"❌ FAIL — Wymagany min. kapital: {p['min_cap']}$"
    chk_html = "".join(f"<div style='color:{"#3fb950" if ok else "#f85149"};font-size:12px;margin:3px 0'>{"✅" if ok else "❌"} {txt}</div>" for ok, txt in p["checks"])
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:12px}} .card{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:10px}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}} .box{{background:#0d1117;padding:8px;border-radius:6px;border:1px solid #21262d;cursor:pointer}} input{{background:#0d1117;color:#fff;border:1px solid #30363d;border-radius:5px;padding:6px;width:92%}} .btn{{background:#238636;color:#fff;border:none;padding:8px 12px;border-radius:6px;font-weight:bold;text-decoration:none;cursor:pointer}}</style>
    <script>
    function cp(t, lbl){{navigator.clipboard.writeText(t); fetch('/clip/'+encodeURIComponent(t)); alert('Skopiowano '+lbl+': '+t);}}
    function cpSeq(){{let seq=['{fmt_p(p["entry"]).strip()}','{p["qty"]}','{fmt_p(p["stop"]).strip()}','{fmt_p(tp1).strip()}']; let i=0; let iv=setInterval(()=>{{if(i>=seq.length){{clearInterval(iv);alert('Koniec kolejki!');return;}} navigator.clipboard.writeText(seq[i]); fetch('/clip/'+encodeURIComponent(seq[i])); i++;}}, 2500); alert('Start kolejki co 2.5s: Wejscie -> Ilosc -> SL -> TP1');}}
    </script></head><body>
    <div style="margin-bottom:10px"><a href="/" class="btn" style="background:#1f6feb">⬅ Skaner</a> <b style="margin-left:8px;font-size:17px">🧮 PLANNER ({ex})</b></div>
    <form class="card" method="get" action="/planner">
      <div class="grid">
        <div><small>Moneta</small><br><input name="sym" value="{sym}"></div>
        <div><small>Kapital ($)</small><br><input name="cap" value="{cap}"></div>
        <div><small>Ryzyko (%)</small><br><input name="rpct" value="{rpct}"></div>
        <div><small>Max Dzwignia (x)</small><br><input name="mlev" value="{mlev}"></div>
        <div><small>Wejscie (puste=auto)</small><br><input name="entry" value="{round(p['entry'],5)}"></div>
        <div><small>Stop Loss (puste=auto)</small><br><input name="stop" value="{round(p['stop'],5)}"></div>
      </div>
      <button type="submit" class="btn" style="width:100%;margin-top:10px">🔄 Przelicz Plan Pozycji</button>
    </form>
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><b>{sym} ({p['side']})</b><button onclick="cpSeq()" class="btn" style="background:#8957e5;font-size:11px">⚡ Auto-Kolejka Schowka</button></div>
      <div class="grid">
        <div class="box" onclick="cp('{fmt_p(p['entry']).strip()}','Wejscie')"><small>WEJSCIE 📋</small><br><b style="color:#58a6ff">{fmt_p(p['entry']).strip()}</b></div>
        <div class="box" onclick="cp('{fmt_p(p['stop']).strip()}','SL')"><small>STOP LOSS 📋</small><br><b style="color:#f85149">{fmt_p(p['stop']).strip()}</b></div>
        <div class="box" onclick="cp('{p['qty']}','Ilosc')"><small>ILOSC MONET 📋</small><br><b>{p['qty']}</b></div>
        <div class="box" onclick="cp('{p['rec_lev']}','Sugerowana Dzwignia')" style="border-color:#238636"><small>💡 SUGEROWANA DZWIGNIA 📋</small><br><b style="color:#3fb950">{p['rec_lev']}x</b> <small>(Margin: {p['rec_margin']}$ | Liq: {fmt_p(p['liq_price']).strip()})</small></div>
        <div class="box"><small>WARTOSC POZYCJI</small><br><b>{p['notional']}$</b></div>
        <div class="box"><small>RYZYKO (1R)</small><br><b style="color:#d29922">{p['risk_usdt']}$ ({rpct}%)</b></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:4px;margin-top:8px;text-align:center;font-size:11px">
        <div class="box" onclick="cp('{fmt_p(tp1).strip()}','TP1')">1R 📋<br><b style="color:#3fb950">{fmt_p(tp1).strip()}</b></div>
        <div class="box" onclick="cp('{fmt_p(tp2).strip()}','TP2')">2R 📋<br><b style="color:#3fb950">{fmt_p(tp2).strip()}</b></div>
        <div class="box" onclick="cp('{fmt_p(tp3).strip()}','TP3')">3R 📋<br><b style="color:#3fb950">{fmt_p(tp3).strip()}</b></div>
        <div class="box" onclick="cp('{fmt_p(tp4).strip()}','TP4')">4R 📋<br><b style="color:#3fb950">{fmt_p(tp4).strip()}</b></div>
        <div class="box" onclick="cp('{fmt_p(tp5).strip()}','TP5')">5R 📋<br><b style="color:#3fb950">{fmt_p(tp5).strip()}</b></div>
      </div>
    </div>
    <div class="card" style="border-color:{st_col}">
      <div style="font-weight:bold;color:{st_col};margin-bottom:6px">{st_txt}</div>
      {chk_html}
    </div>
    </body></html>"""

@app.route("/clip/<val>")
def r_clip(val):
    """Realizuje logike: r clip. Parametry: val."""
    os.system(f'termux-clipboard-set "{val}" >/dev/null 2>&1')
    return ("ok", 200)

@app.route("/portfolio")
def r_portfolio():
    """Realizuje logike: r portfolio."""
    summary = pf.get_portfolio_summary()
    rows_html = ""
    for p in summary["positions"]:
        tp_btns = ""
        for idx, (tp_val, is_hit) in enumerate(zip(p["tp"], p["hit_tps"])):
            bg = "#238636" if is_hit else "#21262d"
            tp_btns += f'<a href="/hit_tp/{p["id"]}/{idx}" style="background:{bg};color:#fff;padding:4px 7px;border-radius:5px;text-decoration:none;font-size:11px;margin-right:4px">{"✅" if is_hit else "⬜"} {idx+1}R ({fmt_p(tp_val).strip()})</a>'
        rows_html += f"""<div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <b>{p['symbol']} ({p['exchange']}) — <span style="color:{'#3fb950' if p['side']=='LONG' else '#f85149'}">{p['side']} {p['lev']}x</span></b>
            <a href="/del_pos/{p['id']}" style="background:#da3633;color:#fff;padding:3px 8px;border-radius:5px;text-decoration:none;font-size:11px">❌ Zamknij</a>
          </div>
          <div style="font-size:12px;margin:6px 0;color:#8b949e">Wej: <code>{fmt_p(p['entry']).strip()}</code> | SL: <code>{fmt_p(p['stop']).strip()}</code> | Margin: <b>{p['margin']}$</b> | Ryzyko: <b>{'0$ (BE)' if any(p['hit_tps']) else str(p['risk'])+'$'}</b></div>
          <div style="font-size:12px;margin:4px 0;padding:6px;background:#0d1117;border-radius:6px">
            Wynik na zywo: <b>{p.get('live_pnl', 'Oczekiwanie na skan...')}</b><br>
            Status: <b>{p.get('live_status', '🟢 Monitorowana co 30s')}</b><br>
            <span style="color:#58a6ff">💡 Przeciwdzialanie: {p.get('live_action', 'Trzymaj plan.')}</span>
          </div>
          <div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px">{tp_btns}</div>
        </div>"""
    if not rows_html:
        rows_html = '<div class="card" style="color:#8b949e">Brak aktywnych pozycji. Kliknij <b>➕ Obstawiam</b> przy propozycji ze skanu!</div>'
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{{background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:12px}} .card{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:10px}} .btn{{background:#1f6feb;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:bold}}</style></head><body>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <div><a href="/" class="btn">⬅ Skaner</a> <b style="margin-left:6px;font-size:17px">💼 PORTFEL I MARGIN</b></div>
      <form action="/set_cap" method="get" style="display:flex;gap:4px"><input name="cap" value="{summary['capital']}" style="width:70px;background:#0d1117;color:#fff;border:1px solid #30363d;border-radius:5px;padding:4px"><button type="submit" class="btn" style="background:#238636">💰 Zapisz</button></form>
    </div>
    <div class="card" style="border-color:#d29922">
      <b>Kapital ogolny: {summary['capital']}$</b> | Zablokowany Margin: <b>{summary['used_margin']}$</b> ({summary['margin_pct']}%)<br>
      Wolny limit na kolejne pozycje: <b style="color:#3fb950">{summary['free_margin']}$</b> | Laczne ryzyko: <b>{summary['active_risk']}$</b> ({summary['risk_pct']}%)<br>
      <div style="margin-top:6px;font-weight:bold">{summary['status']}</div>
    </div>
    {rows_html}
    </body></html>"""

@app.route("/add_pos")
def r_add_pos():
    """Realizuje logike: r add pos."""
    from flask import request
    sym = request.args.get("sym", "").strip().upper()
    cfg = load_settings(); ex = cfg["exchange"]
    hit = next((x for x in LATEST["hits"] if isinstance(x, dict) and x.get("symbol") == sym), None)
    p = pm.calc_plan(ex, sym, cfg["capital"], cfg["risk_pct"], 20, hit["entry"] if hit else None, hit["stop"] if hit else None)
    if p:
        pf.add_position(ex, sym, p["side"], p["entry"], p["stop"], p["tp"], p["qty"], p["rec_margin"], p["risk_usdt"], p["rec_lev"])
    return redirect(url_for("r_portfolio"))

@app.route("/hit_tp/<pid>/<int:idx>")
def r_hit_tp(pid, idx):
    """Realizuje logike: r hit tp. Parametry: pid, idx."""
    pf.toggle_tp_hit(pid, idx)
    return redirect(url_for("r_portfolio"))

@app.route("/del_pos/<pid>")
def r_del_pos(pid):
    """Realizuje logike: r del pos. Parametry: pid."""
    pf.close_position(pid)
    return redirect(url_for("r_portfolio"))

@app.route("/set_cap")
def r_set_cap():
    """Realizuje logike: r set cap."""
    from flask import request
    v = request.args.get("cap", "").strip()
    if v:
        c = load_settings(); c["capital"] = float(v); save_settings(c)
    return redirect(url_for("r_portfolio"))

@app.route("/liq/<int:val>")
def r_liq(val):
    """Realizuje logike: r liq. Parametry: val."""
    c = load_settings(); c["liq_only"] = bool(val)
    tiers, mx = get_dynamic_top_tiers(c["exchange"])
    c["top_n"] = mx; save_settings(c)
    return redirect(url_for("index"))

@app.route("/demo24")
def r_demo24():
    """Realizuje logike: r demo24."""
    from flask import request
    if request.args.get("new") == "1":
        ds24.start_demo_24h(); return redirect(url_for("r_demo24"))
    rep = ds24.get_demo_report()
    if not rep:
        return '<body style="background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:15px"><a href="/" style="color:#58a6ff">⬅ Powrot</a><h2>🧪 Symulacja Demo 24H (1000 USDT)</h2><a href="/demo24?new=1" style="background:#238636;color:#fff;padding:10px 14px;border-radius:6px;text-decoration:none;font-weight:bold">🚀 Start Nowej Symulacji 24H</a></body>'
    rows = "".join(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px;margin-bottom:8px"><b>{p["symbol"]}</b> ({p["side"]} | {p["win_prob"]}%) — <b>{p["close_reason"] if p["closed"] else ("🟢 Aktywna" if p["entered"] else "⏳ Oczekuje")}</b><br><small>Wej: {fmt_p(p["entry"]).strip()} | SL: {fmt_p(p["stop"]).strip()} | Akt: {fmt_p(p["cur_price"]).strip()}</small><br>TP: {"".join("✅" if x else "⬜" for x in p["hit_tps"])} | Wynik: <b style="color:{"#3fb950" if p["realized_pnl"]>=0 else "#f85149"}">{p["realized_pnl"]:+.2f}$</b></div>' for p in rep["positions"])
    return f'<body style="background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:12px"><div style="display:flex;justify-content:space-between;margin-bottom:10px"><a href="/" style="background:#1f6feb;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">⬅ Skaner</a><a href="/demo24?new=1" style="background:#238636;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">🚀 Nowa Symulacja 24H</a></div><div style="background:#161b22;border:1px solid #d29922;border-radius:8px;padding:12px;margin-bottom:10px"><b>🧪 SYMULACJA 24H ({rep["exchange"]})</b> | Zostalo: <b>{rep["rem_h"]}h</b><br>Kapital: <b>1000.00$</b> → Saldo: <b style="color:{"#3fb950" if rep["total_pnl"]>=0 else "#f85149"}">{rep["equity"]:.2f}$ ({rep["total_pnl"]:+.2f}$ / {rep["pnl_pct"]:+.2f}%)</b><br>Win Rate: <b>{rep["win_rate"]}%</b> (✅ {rep["wins"]} / ❌ {rep["losses"]})</div>{rows}</body>'

@app.route("/backtest")
def r_backtest():
    """Realizuje logike: r backtest."""
    from flask import request
    sym = request.args.get("sym", "M10").strip().upper()
    t20 = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","TRXUSDT","MATICUSDT","LTCUSDT","BCHUSDT","ATOMUSDT","UNIUSDT","NEARUSDT","APTUSDT","FILUSDT","INJUSDT"]
    res = bt20.run_multi_backtest_2020(t20.__getitem__(slice(0, 10)), 2020, 1000.0) if sym == "M10" else (bt20.run_multi_backtest_2020(t20, 2020, 1000.0) if sym == "M20" else bt20.run_backtest_2020(sym, 2020, 1000.0, 1.0))
    if not res: return f'<body style="background:#0d1117;color:#fff;padding:15px"><a href="/">⬅ Powrot</a><p>Brak danych dla {sym}</p></body>'
    yr_html = "".join(f"<div style='display:inline-block;margin:4px 10px 4px 0'><b>{y}:</b> <span style='color:{"#3fb950" if p>=0 else "#f85149"}'>{p:+.2f}$</span></div>" for y, p in sorted(res["yearly"].items()))
    mo_html = "".join(f"<div style='background:#0d1117;padding:5px 8px;border-radius:5px;border:1px solid #21262d'><b>{ym}</b><br><span style='color:{"#3fb950" if p>=0 else "#f85149"}'>{p:+.2f}$</span></div>" for ym, p in sorted(res["monthly"].items()))
    cs_html = ("<h3>🏆 Wynik per Moneta:</h3>" + "".join(f"<span style='display:inline-block;margin:3px 10px 3px 0'><b>{c}:</b> <span style='color:{"#3fb950" if v>=0 else "#f85149"}'>{v:+.2f}$</span> (WR {w}%)</span>" for c, v, w in res["coin_stats"])) if "coin_stats" in res else ""
    return f'<body style="background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:14px"><div style="margin-bottom:10px"><a href="/" style="background:#1f6feb;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none">⬅ Skaner</a> <a href="/backtest?sym=M10" style="background:#238636;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none;margin-left:4px">🌐 TOP 10</a> <a href="/backtest?sym=M20" style="background:#238636;color:#fff;padding:6px 10px;border-radius:6px;text-decoration:none;margin-left:4px">🌐 TOP 20</a> <form style="display:inline-block;margin-left:6px"><input name="sym" value="{sym}" style="background:#161b22;color:#fff;border:1px solid #30363d;padding:5px;border-radius:5px;width:85px"><button type="submit" style="background:#1f6feb;color:#fff;border:none;padding:6px 10px;border-radius:5px">Testuj</button></form></div><div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px"><h2>📜 Backtest 2020–2026: {res["symbol"]} ({res["date_from"]} → {res["date_to"]})</h2><p>Swiece 4H: <b>{res["bars"]}</b> | Srednio: <b>{res["avg_month"]:+.2f}$/mies.</b> | Win Rate: <b>{res["win_rate"]}%</b></p><p>Kapital: <b>1000.00$</b> → <b style="color:{"#3fb950" if res["final_cap"]>=1000 else "#f85149"};font-size:18px">{res["final_cap"]:.2f}$ ({res["net_pct"]:+.1f}%)</b></p><h3>📊 Podzial roczny:</h3>{yr_html}{cs_html}<h3>🗓️ Podzial miesieczny ({len(res["monthly"])} mies.):</h3><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(95px,1fr));gap:6px">{mo_html}</div></div></body>'

@app.route("/")
def index(): cfg_w = load_settings(); tiers_w, mx_w = get_dynamic_top_tiers(cfg_w["exchange"]); return render_template_string(HTML_TPL, res=LATEST, prog=PROG, cfg=cfg_w, live=LIVE_ACTIVE, pf=pf.get_portfolio_summary(), tiers=tiers_w, mx_coins=mx_w)

@app.route("/scan")
def r_scan(): return redirect(url_for("index"))

@app.route("/start")
def r_start():
    """Realizuje logike: r start."""
    if not PROG["running"]: threading.Thread(target=run_full_scan, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/prog")
def r_prog(): return jsonify(PROG)

@app.route("/ex/<name>")
def r_ex(name):
    """Realizuje logike: r ex. Parametry: name."""
    c = load_settings(); c["exchange"] = name.upper(); save_settings(c)
    return redirect(url_for("index"))

def fill_demo():
    """Realizuje logike: fill demo."""
    LATEST["hits"] = [
        {"symbol": "SOLUSDT", "side": "LONG", "is_trig": True, "price_ok": True, "price": 142.85, "entry": 142.50, "stop": 138.20, "tp": [146.8, 151.1, 155.4, 159.7, 164.0], "req_cap": 65, "dist_pct": 0.24, "dist_atr": 0.15, "eta_str": "TERAZ", "mom": "Wybija poziom", "gap_pct": 0.0, "max_dev": 5.0},
        {"symbol": "XRPUSDT", "side": "SHORT", "is_trig": False, "price_ok": False, "price": 0.5510, "entry": 0.5120, "stop": 0.5310, "tp": [0.493, 0.474, 0.455, 0.436, 0.417], "req_cap": 82, "dist_pct": 7.08, "dist_atr": 0.92, "eta_str": "~3.5h", "mom": "Przyspiesza", "gap_pct": 4.08, "max_dev": 3.0}
    ]
    LATEST["near"] = [{"symbol": "BTCUSDT", "side": "SHORT", "price": 62747.7, "dist_atr": 0.45, "dist_pct": 0.62, "eta_str": "~1.2h", "mom": "Konsolidacja", "missing": "adx,vol"}]
    LATEST["time"] = "TRYB DEMO"

@app.route("/demo")
def r_demo():
    """Realizuje logike: r demo."""
    fill_demo()
    return redirect(url_for("index"))


CFD_HIST_FILE = "cfd_live_history.json"
SHADOW_LAB_FILE = "market_shadow_lab.json"
WILD_LAB_FILE = "wild_market_lab.json"
MICRO_LAB_FILE = "micro_market_lab.json"

def log_cfd_hits_to_file(hits_list, src="LIVE"):
    """Realizuje logike: log cfd hits to file. Parametry: hits_list, src."""
    if not hits_list: return
    try:
        cur_h = json.load(open(CFD_HIST_FILE)) if os.path.exists(CFD_HIST_FILE) else []
        now_dt = datetime.now()
        now_s = now_dt.strftime("%d.%m %H:%M")
        now_ep = int(time.time())
        btc_r, btc_lbl = get_live_btc_regime() if "get_live_btc_regime" in globals() else (0, "NEUTRAL")
        sess_s = apm.get_session_badge() if "apm" in globals() else ""
        t_st = atm.get_tuner_params() if "atm" in globals() else {}
        for h in hits_list:
            en_v = float(h.get("entry", 0) or 0)
            sl_v = float(h.get("stop", 0) or 0)
            sd_v = abs(en_v - sl_v) or (en_v * 0.01)
            sl_pct = round((sd_v / max(1e-9, en_v)) * 100.0, 2)
            td_v = 1 if h.get("side") == "LONG" else -1
            tps_v = h.get("tp", [])
            tp1_v = float(tps_v.__getitem__(0)) if len(tps_v) > 0 else round(en_v + td_v * sd_v * 1.0, 6)
            tp2_v = float(tps_v.__getitem__(1)) if len(tps_v) > 1 else round(en_v + td_v * sd_v * 1.5, 6)
            tp3_v = float(tps_v.__getitem__(2)) if len(tps_v) > 2 else round(en_v + td_v * sd_v * 2.5, 6)
            mtf_str = apm.get_mtf_status_line("BITGET", h.get("symbol", ""), h.get("side", "LONG")) if "apm" in globals() else ""
            mtf_cnt = mtf_str.count("✅")
            cur_h.append({
                "ts": now_s, "ts_epoch": now_ep, "hour": now_dt.hour, "src": src,
                "sym": h.get("symbol", ""), "side": h.get("side", ""),
                "prob": h.get("win_prob", 75), "alpha_tag": h.get("alpha_tag", ""),
                "btc_regime": btc_r, "session": sess_s, "mtf_cnt": mtf_cnt, "mtf_raw": mtf_str,
                "sl_dist_pct": sl_pct, "tuner_prob": t_st.get("min_prob", 62), "tuner_sl_mult": t_st.get("sl_mult", 1.0),
                "entry": fmt_p(en_v).strip(), "sl": fmt_p(sl_v).strip(),
                "en_f": en_v, "sl_f": sl_v, "tp1_f": tp1_v, "tp2_f": tp2_v, "tp3_f": tp3_v,
                "status": "OPEN", "res_r": 0.0, "dur_str": "0m",
                "mfe_r": 0.0, "mae_r": 0.0, "fail_reason": "PENDING", "closed_final": False
            })
        json.dump(cur_h.__getitem__(slice(-100, None)), open(CFD_HIST_FILE, "w"), indent=2)
    except Exception:
        pass

def fmt_dur_mins(mins):
    """Realizuje logike: fmt dur mins. Parametry: mins."""
    mins = max(1, int(mins))
    if mins < 60: return f"{mins}m"
    h, m = divmod(mins, 60)
    return f"{h}h{m:02d}m" if h < 24 else f"{h//24}d{h%24}h"

def audit_cfd_history_1m(hist_path=None):
    """Odtwarza historie sygnalow na swiecach 1m/5m (MFE/MAE). Parametry: hist_path."""
    target_f = hist_path or CFD_HIST_FILE
    if not os.path.exists(target_f): return []
    rows = json.load(open(target_f))
    changed = False
    now_ep = int(time.time())
    for r in rows:
        if r.get("closed_final"): continue
        en = float(r.get("en_f") or r.get("entry") or 0)
        sl = float(r.get("sl_f") or r.get("sl") or 0)
        if en <= 0 or sl <= 0: continue
        side = r.get("side", "LONG")
        td = 1 if side == "LONG" else -1
        sd = abs(en - sl) or (en * 0.01)
        tp1 = float(r.get("tp1_f") or (en + td * sd * 1.0))
        tp2 = float(r.get("tp2_f") or (en + td * sd * 1.5))
        tp3 = float(r.get("tp3_f") or (en + td * sd * 2.5))
        t0 = int(r.get("ts_epoch") or (now_ep - 3600))
        mins_elapsed = max(2, min(990, (now_ep - t0) // 60 + 2))
        tf_aud = "1m" if (now_ep - t0) <= 58000 else "5m"
        lim_aud = mins_elapsed if tf_aud == "1m" else min(990, (now_ep - t0) // 300 + 2)
        kl1 = fetch_klines("BITGET", r.get("sym", ""), tf_aud, lim_aud)
        if not kl1 or len(kl1["c"]) < 2: continue

        hit_tp1, hit_tp2 = False, False
        cur_sl = sl
        final_st, final_r, hit_idx = None, 0.0, len(kl1["c"]) - 1
        max_fav_r, max_adv_r = 0.0, 0.0
        post_sl_reached_tp1 = False

        for i in range(len(kl1["c"])):
            bar_t = int(kl1["t"].__getitem__(i) / 1000)
            if bar_t < t0: continue
            hi, lo = float(kl1["h"].__getitem__(i)), float(kl1["l"].__getitem__(i))
            fav_p = hi if td == 1 else lo
            adv_p = lo if td == 1 else hi
            cur_fav_r = round((td * (fav_p - en)) / sd, 2)
            cur_adv_r = round((td * (adv_p - en)) / sd, 2)
            if cur_fav_r > max_fav_r: max_fav_r = cur_fav_r
            if cur_adv_r < max_adv_r: max_adv_r = cur_adv_r

            if final_st == "❌ SL":
                if (hi >= tp1) if td == 1 else (lo <= tp1):
                    post_sl_reached_tp1 = True
                continue

            sl_hit = (lo <= cur_sl) if td == 1 else (hi >= cur_sl)
            if sl_hit:
                if hit_tp2: final_st, final_r = "💰 BE+1.5R", 0.80
                elif hit_tp1: final_st, final_r = "🟡 BE+1R", 0.50
                else: final_st, final_r = "❌ SL", -1.00
                hit_idx = i
                continue

            if not hit_tp1 and ((hi >= tp1) if td == 1 else (lo <= tp1)): hit_tp1 = True
            if not hit_tp2 and ((hi >= tp2) if td == 1 else (lo <= tp2)):
                hit_tp2 = True
                cur_sl = en + td * 0.1 * sd
            if (hi >= tp3) if td == 1 else (lo <= tp3):
                final_st, final_r, hit_idx = "🏆 TP3", 2.00, i
                break

        r["mfe_r"], r["mae_r"] = max_fav_r, max_adv_r
        dur_m = max(1, (int(kl1["t"].__getitem__(hit_idx) / 1000) - t0) // 60)
        if final_st:
            if final_r > 0: reason = "CLEAN_WIN"
            elif post_sl_reached_tp1: reason = "SL_WICK_REVERSAL"
            elif max_fav_r >= 0.75: reason = "MISSED_TP_REVERSAL"
            elif r.get("btc_regime", 0) != 0 and ((side == "LONG" and r.get("btc_regime") == -1) or (side == "SHORT" and r.get("btc_regime") == 1)):
                reason = "COUNTER_BTC_FAIL"
            else: reason = "DIRECT_STOPOUT"
            r["status"], r["res_r"], r["dur_str"], r["fail_reason"], r["closed_final"] = final_st, final_r, fmt_dur_mins(dur_m), reason, True
        else:
            c_last = float(kl1["c"].__getitem__(-1))
            live_r = round((td * (c_last - en)) / sd, 2)
            r["status"], r["res_r"], r["dur_str"] = f"⏳ {live_r:+.1f}R", live_r, fmt_dur_mins((now_ep - t0) // 60)
        changed = True
    if changed:
        json.dump(rows, open(target_f, "w"), indent=2)
    return rows

def render_cfd_history_table():
    """Realizuje logike: render cfd history table."""
    rows = audit_cfd_history_1m()
    if not rows:
        lab_stats = []
        for l_lbl, l_fn in [("Shadow TOP-100", "market_shadow_lab.json"), ("Wild 61-160", "wild_market_lab.json"), ("Micro 161+", "micro_market_lab.json")]:
            if os.path.exists(l_fn):
                arr_l = json.load(open(l_fn))
                lv_c = sum(1 for x in arr_l if x.get("data_type") == "LIVE_FORWARD")
                hs_c = sum(1 for x in arr_l if x.get("data_type") == "HIST_BACKFILL")
                lab_stats.append(f"• <b>{l_lbl}:</b> {lv_c} LIVE na żywo | {hs_c} HIST")
        return "📊 <b>AUDYT LIVE CFD & LABORATORIA RYNKOWE</b>\n<i>Główny portfel sygnałów (GOLD/PLATINUM): 0 trafień od startu.</i>\n\n🧪 <b>STAN ZBIERANIA DANYCH W TLE (24/7):</b>\n" + "\n".join(lab_stats)
    lines = ["Para   | Typ | Wynik     | MFE   | Czas", "-------+-----+-----------+-------+------"]
    for r in reversed(rows.__getitem__(slice(-15, None))):
        s_col = str(r.get("sym", "")).replace("USDT", "")[:6].ljust(6)
        d_col = ("🟢L" if r.get("side") == "LONG" else "🔴S").ljust(3)
        st_col = str(r.get("status", "OPEN"))[:9].ljust(9)
        mfe_col = f"+{float(r.get('mfe_r', 0)):.1f}R".ljust(5)
        du_col = str(r.get("dur_str", "-"))[:5]
        lines.append(f"{s_col} | {d_col} | {st_col} | {mfe_col} | {du_col}")

    closed = [r for r in rows if r.get("closed_final")]
    wins = [r for r in closed if float(r.get("res_r", 0)) > 0]
    losses = [r for r in closed if float(r.get("res_r", 0)) < 0]
    sum_r = sum(float(r.get("res_r", 0)) for r in closed)
    wr = round(len(wins) / max(1, len(closed)) * 100.0, 1)

    # Analiza przyczyn strat (Co nie zadzialalo)
    wicks = sum(1 for r in losses if r.get("fail_reason") == "SL_WICK_REVERSAL")
    missed = sum(1 for r in losses if r.get("fail_reason") == "MISSED_TP_REVERSAL")
    c_btc = sum(1 for r in losses if r.get("fail_reason") == "COUNTER_BTC_FAIL")
    mtf4 = [r for r in closed if int(r.get("mtf_cnt", 0)) >= 3]
    wr_mtf4 = round(sum(1 for r in mtf4 if float(r.get("res_r", 0)) > 0) / max(1, len(mtf4)) * 100.0, 0) if mtf4 else 0

    diag = (
        f"\n📈 <b>BILANS ({len(closed)} zamknietych):</b> WR <b>{wr}%</b> | Netto: <b>{sum_r:+.2f}R</b>\n"
        f"🔬 <b>DIAGNOSTYKA IMPROVEMENTU (Co nie zadzialalo):</b>\n"
        f"• Szpilki SL (potem TP1): <b>{wicks}</b> | Uciekl zysk (>0.75R): <b>{missed}</b>\n"
        f"• Straty pod prad BTC: <b>{c_btc}</b> | WR dla MTF ≥3/4: <b>{wr_mtf4:.0f}%</b> ({len(mtf4)} poz.)"
    )
    # Analiza oplacalnosci nizszych procentow (Shadow Lab + Live) PO ODLICZENIU PROWIZJI CFD (~0.07R na trade)
    all_samples = list(rows)
    if os.path.exists(SHADOW_LAB_FILE):
        try: all_samples.extend(json.load(open(SHADOW_LAB_FILE)))
        except Exception: pass
    closed_all = [x for x in all_samples if x.get("closed_final")]
    b_lines = ["\n🧪 <b>ANALIZA NISKICH PROCENTOW (NETTO PO PROWIZJI CFD):</b>"]
    for b_name, lo_p, hi_p in [("45-54%", 45, 54), ("55-61%", 55, 61), ("62%+  ", 62, 100)]:
        sub = [x for x in closed_all if lo_p <= int(x.get("prob", 0)) <= hi_p]
        if sub:
            w_sub = sum(1 for x in sub if float(x.get("res_r", 0)) > 0)
            wr_sub = round(w_sub / len(sub) * 100.0, 1)
            # Odliczamy realistyczna prowizje CFD (~0.07R na kazda transakcje)
            net_r = round(sum(float(x.get("res_r", 0)) - 0.07 for x in sub), 2)
            st_b = "✅ PLUS" if net_r > 0 else "❌ MINUS"
            b_lines.append(f"• <code>{b_name}</code>: <b>{len(sub)}</b> prob | Szansa WR: <b>{wr_sub}%</b> | Netto: <b>{net_r:+.2f}R</b> ({st_b})")
        else:
            open_sub = sum(1 for x in all_samples if not x.get("closed_final") and lo_p <= int(x.get("prob", 0)) <= hi_p)
            b_lines.append(f"• <code>{b_name}</code>: zbieranie probek... (w toku: <b>{open_sub}</b>)")
    return f"📊 <b>AUDYT I TELEMETRIA LIVE CFD (KNOTY 1M)</b>\n<pre>" + "\n".join(lines) + "</pre>" + diag + "\n".join(b_lines)

def tg_menu(cid=None, tok=None, notice=""):
    """Realizuje logike: tg menu. Parametry: cid, tok, notice."""
    if (not cid or not tok) and os.path.exists(TG_CONFIG_FILE):
        tc = json.load(open(TG_CONFIG_FILE))
        cid = cid or tc.get("chat_id", "").strip()
        tok = tok or tc.get("token", "").strip()
    if not cid or not tok: return
    _, btc_lbl = get_live_btc_regime() if "get_live_btc_regime" in globals() else (0, "NEUTRALNY")
    sess_lbl = apm.get_session_badge() if "apm" in globals() else ""
    live_txt = "🟢 Live CFD: ON (15m)" if CFD_LIVE_ACTIVE else "⚪ Live CFD: OFF"
    kb = {"inline_keyboard": [
        [{"text": "⚡ 🌐 Otwórz Pulpit Chrome (2.0)", "callback_data": "open_chrome_ui"}], [{"text": "⚡ Skanuj CFD (Long/Short)", "callback_data": "scan_cfd10"}, {"text": live_txt, "callback_data": "tgl_cfd_live"}],
        [{"text": "💼 Portfel CFD", "callback_data": "tg_pf"}, {"text": "🧮 Planner", "callback_data": "tg_plan_menu"}, {"text": "📈 Wykresy", "callback_data": "prop_charts"}],
        [{"text": "⚙️ Warstwy", "callback_data": "chart_layers"}, {"text": "🏆 Symulacja CFD PRO", "callback_data": "demo_pro"}],
        [{"text": "📜 Backtest 2020-26", "callback_data": "bt_menu"}, {"text": "📊 Historia CSV", "callback_data": "csv"}],
        [{"text": "🩺 Diagnoza Konta", "callback_data": "doc_rep"}, {"text": "🚀 Pump & Dump", "callback_data": "scan_pd"}],
        [{"text": "📊 Raport 24H Teraz", "callback_data": "force_r24"}, {"text": "🎭 Demo Okazji", "callback_data": "demo_preview"}]
    ]}
    head = f"{notice}\n\n" if notice else ""
    txt = f"{head}⚡ <b>PANEL CFD PRO (BITGET FUTURES / CFD)</b>\n{btc_lbl}\n{sess_lbl}\n<i>Gotowy do pracy — wybierz akcje:</i>"
    btc_clean = str(btc_lbl).replace("<", "&lt;").replace(">", "&gt;")
    sess_clean = str(sess_lbl).replace("<", "&lt;").replace(">", "&gt;")
    txt_safe = f"{head}⚡ <b>PANEL CFD PRO (BITGET FUTURES / CFD)</b>\n{r24.get_24h_countdown_line()}\n{btc_clean}\n{sess_clean}\n<i>Gotowy do pracy — wybierz akcje:</i>"
    requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": txt_safe, "parse_mode": "HTML", "reply_markup": kb}, timeout=15)

def tg_listener():
    """Realizuje logike: tg listener."""
    if not os.path.exists(TG_CONFIG_FILE): return
    cfg = json.load(open(TG_CONFIG_FILE))
    tok, cid = cfg.get("token","").strip(), cfg.get("chat_id","").strip()
    if not tok or not cid: return
    tg_menu(cid, tok, "🤖 <b>System Gotowy!</b>\nChrome: <code>http://127.0.0.1:5000</code>")
    off = 0
    while True:
        try:
            r = requests.get(tg_url(tok, "getUpdates"), params={"offset": off, "timeout": 15}, timeout=20).json()
            for u in r.get("result", []):
                off = u["update_id"] + 1
                if "message" in u: tg_menu(cid, tok)
                elif "message" in u and "text" in u["message"]:
                    mtxt = u["message"]["text"].strip().lower()
                    if mtxt in ("/start", "start", "menu", "/menu"):
                        tg_menu(cid, tok, "⚡ <b>PANEL CFD PRO — Gotowy!</b>")
                if "callback_query" in u:
                    cb = u["callback_query"]["data"]
                    requests.post(tg_url(tok, "answerCallbackQuery"), json={"callback_query_id": u["callback_query"]["id"]})
                    ex = load_settings()["exchange"]
                    if cb.startswith("plan_"):
                        psym = cb.replace("plan_", "").strip()
                        try:
                            cfg_p = load_settings()
                            cap_p = max(1000.0, float(cfg_p.get("capital", 1000.0)))
                            rpct_p = float(cfg_p.get("risk_pct", 1.5))
                            hit = next((x for x in LATEST.get("hits", []) if isinstance(x, dict) and x.get("symbol") == psym), None)
                            p = pm.calc_plan("BITGET", psym, cap_p, rpct_p, 20, hit["entry"] if hit else None, hit["stop"] if hit else None, hit["side"] if hit else None)
                            if not p and hit:
                                sd = abs(hit["entry"] - hit["stop"]) or (hit["entry"] * 0.01)
                                risk_u = round(cap_p * (rpct_p / 100.0), 2)
                                qty_u = round(risk_u / sd, 4)
                                notional_u = round(qty_u * hit["entry"], 2)
                                td_p = 1 if hit["side"] == "LONG" else -1
                                p = {
                                    "side": hit["side"], "entry": hit["entry"], "stop": hit["stop"],
                                    "tp": hit.get("tp", [round(hit["entry"] + td_p * sd * m, 4) for m in (1.0, 1.5, 2.5, 3.5, 5.0)]),
                                    "qty": qty_u, "rec_lev": 10, "notional": notional_u, "rec_margin": round(notional_u / 10.0, 2),
                                    "liq_price": round(hit["entry"] * (1.0 - td_p * 0.09), 4),
                                    "passed": True, "min_cap": 50.0, "checks": [(True, "Symulacja / Demo CFD aktywna")]
                                }
                            if not p:
                                send_telegram(f"⚠️ Brak danych swiec dla <b>{psym}</b> (BITGET).")
                            else:
                                tp1, tp2, tp3, tp4, tp5 = p["tp"]
                                e_s, sl_s = fmt_p(p["entry"]).strip(), fmt_p(p["stop"]).strip()
                                t1_s, t2_s, t3_s, t4_s, t5_s = [fmt_p(x).strip() for x in (tp1, tp2, tp3, tp4, tp5)]
                                st_icon = "✅ PASS" if p["passed"] else f"❌ FAIL (Min. kap: {p['min_cap']}$)"
                                chks = "\n".join(f"{'✅' if ok else '❌'} {txt}" for ok, txt in p["checks"])
                                msg_p = (
                                    f"🧮 <b>PLANNER | {psym} (BITGET CFD)</b>\n"
                                    f"Kierunek: <b>{p['side']}</b> | Kapital: <b>{cap_p}$</b> ({rpct_p}%)\n"
                                    f"📦 Ilosc: <code>{p['qty']}</code> | 💡 Dzwignia: <b>{p['rec_lev']}x</b>\n"
                                    f"💵 Wartosc: <b>{p['notional']}$</b> | 🔒 Margin: <b>{p['rec_margin']}$</b> | 💀 Liq: <code>{fmt_p(p['liq_price']).strip()}</code>\n\n"
                                    f"🎯 Wej: <code>{e_s}</code> | 🛑 SL: <code>{sl_s}</code>\n"
                                    f"✅ TP1 (1.0R): <code>{t1_s}</code>\n"
                                    f"💰 TP2 (1.5R): <code>{t2_s}</code>\n"
                                    f"🚀 TP3 (2.5R): <code>{t3_s}</code>\n"
                                    f"🔥 TP4 (3.5R): <code>{t4_s}</code>\n"
                                    f"🏆 TP5 (5.0R): <code>{t5_s}</code>\n"
                                    f"<i>(Dotknij dowolna liczbe lub przycisk ponizej, aby skopiowac)</i>\n\n"
                                    f"<b>{st_icon}</b>\n{chks}"
                                )
                                kb_plan = {"inline_keyboard": [
                                    [{"text": f"📋 Wej: {e_s}", "callback_data": f"cpv_{e_s}"}, {"text": f"📋 SL: {sl_s}", "callback_data": f"cpv_{sl_s}"}],
                                    [{"text": f"📋 TP1: {t1_s}", "callback_data": f"cpv_{t1_s}"}, {"text": f"📋 TP2: {t2_s}", "callback_data": f"cpv_{t2_s}"}],
                                    [{"text": f"📋 TP3: {t3_s}", "callback_data": f"cpv_{t3_s}"}, {"text": f"📋 TP4: {t4_s}", "callback_data": f"cpv_{t4_s}"}, {"text": f"📋 TP5: {t5_s}", "callback_data": f"cpv_{t5_s}"}],
                                    [{"text": f"➕ Obstawiam ({psym})", "callback_data": f"addp_{psym}"}, {"text": f"📈 Wykres ({psym})", "callback_data": f"ch_{psym}"}, {"text": "⬅ Menu", "callback_data": "back_menu"}]
                                ]}
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": msg_p, "parse_mode": "HTML", "reply_markup": kb_plan}, timeout=15)
                        except Exception as err:
                            requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"⚠️ Blad Plannera: <code>{err}</code>", "parse_mode": "HTML"}, timeout=15)
                    elif cb.startswith("cpv_"):
                        val_cp = cb.replace("cpv_", "").strip()
                        os.system(f'termux-clipboard-set "{val_cp}" >/dev/null 2>&1')
                        send_telegram(f"📋 Skopiowano do schowka: <code>{val_cp}</code>")
                    elif cb == "tg_plan_menu":
                        cands = [x["symbol"] for x in LATEST.get("hits", []) if isinstance(x, dict)] + apm.get_cfd_top60_symbols()
                        kb = {"inline_keyboard": [[{"text": f"🧮 Plan CFD: {sym}", "callback_data": f"plan_{sym}"}] for sym in list(dict.fromkeys(cands)).__getitem__(slice(0, 7))] + [[{"text": "⬅ Menu", "callback_data": "back_menu"}]]}
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "🧮 <b>Wybierz monete do obliczenia planu:</b>", "parse_mode": "HTML", "reply_markup": kb})
                    elif cb == "tg_pf":
                        pf.check_positions_guardian()
                        sm = pf.get_portfolio_summary()
                        txt_pf = f"💼 <b>PORTFEL I MARGIN</b>\n💰 Kapital: <b>{sm['capital']}$</b> | 🔒 Margin: <b>{sm['used_margin']}$</b> ({sm['margin_pct']}%)\n🟢 Wolny limit: <b>{sm['free_margin']}$</b> | ⚠️ Ryzyko: <b>{sm['active_risk']}$</b>\n<b>{sm['status']}</b>"
                        kb_rows = []
                        for p in sm["positions"]:
                            tps_str = "".join("✅" if x else "⬜" for x in p["hit_tps"])
                            txt_pf += f"\n\n📌 <b>{p['symbol']}</b> ({p['side']} {p['lev']}x) | Margin: {p['margin']}$ | {tps_str}"
                            row = [{"text": f"TP{i+1}{'✅' if p['hit_tps'].__getitem__(i) else ''}", "callback_data": f"tp_{p['id']}_{i}"} for i in range(5)] + [{"text": "❌", "callback_data": f"rmp_{p['id']}"}]
                            kb_rows.append(row)
                        kb_rows.append([{"text": "⬅ Menu", "callback_data": "back_menu"}])
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": txt_pf, "parse_mode": "HTML", "reply_markup": {"inline_keyboard": kb_rows}})
                    elif cb.startswith("addp_"):
                        asym = cb.replace("addp_", "").strip()
                        try:
                            cfg_a = load_settings()
                            cap_a = max(1000.0, float(cfg_a.get("capital", 1000.0)))
                            rpct_a = float(cfg_a.get("risk_pct", 1.5))
                            hit = next((x for x in LATEST.get("hits", []) if isinstance(x, dict) and x.get("symbol") == asym), None)
                            p = pm.calc_plan("BITGET", asym, cap_a, rpct_a, 20, hit["entry"] if hit else None, hit["stop"] if hit else None, hit["side"] if hit else None)
                            if not p and hit:
                                sd = abs(hit["entry"] - hit["stop"]) or (hit["entry"] * 0.01)
                                risk_u = round(cap_a * (rpct_a / 100.0), 2)
                                qty_u = round(risk_u / sd, 4)
                                p = {
                                    "side": hit["side"], "entry": hit["entry"], "stop": hit["stop"],
                                    "tp": hit.get("tp", [hit["entry"] + (1 if hit["side"]=="LONG" else -1)*sd*m for m in (1.0,1.5,2.5,3.5,5.0)]),
                                    "qty": qty_u, "rec_margin": round((qty_u * hit["entry"]) / 10.0, 2),
                                    "risk_usdt": risk_u, "rec_lev": 10
                                }
                            if p:
                                pf.add_position("BITGET", asym, p["side"], p["entry"], p["stop"], p["tp"], p["qty"], p["rec_margin"], p["risk_usdt"], p["rec_lev"])
                                sm = pf.get_portfolio_summary()
                                send_telegram(f"✅ Dodano <b>{asym}</b> ({p['side']}) do Portfela CFD!\n🔒 Margin: <b>{p['rec_margin']}$</b> | ⚠️ Ryzyko: <b>{p['risk_usdt']}$</b> | 🟢 Wolny limit: <b>{sm['free_margin']}$</b>", {"inline_keyboard": [[{"text": "💼 Otworz Portfel CFD", "callback_data": "tg_pf"}, {"text": "⬅ Menu", "callback_data": "back_menu"}]]})
                            else:
                                send_telegram(f"⚠️ Nie udalo sie pobrac danych dla <b>{asym}</b>.")
                        except Exception as err:
                            send_telegram(f"⚠️ Blad dodawania do portfela: <code>{err}</code>")
                    elif cb.startswith("tp_"):
                        _, pid, tidx = cb.split("_"); pf.toggle_tp_hit(pid, int(tidx))
                        send_telegram(f"🎯 TP{int(tidx)+1} zaktualizowany! Kapital: <b>{pf.get_portfolio_summary()['capital']}$</b>")
                    elif cb.startswith("snooze_"):
                        mins = int(cb.replace("snooze_", ""))
                        global CFD_SNOOZE_UNTIL
                        CFD_SNOOZE_UNTIL = time.time() + mins * 60
                        until_str = datetime.fromtimestamp(CFD_SNOOZE_UNTIL).strftime("%H:%M")
                        send_telegram(f"🔕 <b>Wyciszono alerty CFD na {mins} min</b> (do godz. <b>{until_str}</b>). Dobry moment na przerwe od wykresow!")
                    elif cb == "snooze_off":
                        send_telegram("🔔 <b>Alerty CFD pozostaja aktywne.</b> Pilnuj niskiego ryzyka!")
                    elif cb.startswith("rmp_"):
                        pid_c = cb.replace("rmp_", "")
                        sm_before = pf.get_portfolio_summary()
                        pos_c = next((x for x in sm_before.get("positions", []) if str(x.get("id")) == pid_c), None)
                        pf.close_position(pid_c)
                        send_telegram("🗑️ Pozycja zamknieta.")
                        if pos_c:
                            cur_c = fetch_klines("BITGET", pos_c["symbol"], "15m", 5)
                            if cur_c:
                                cp_now = cur_c["c"].__getitem__(-1)
                                td_c = 1 if pos_c["side"] == "LONG" else -1
                                pnl_est = (cp_now - pos_c["entry"]) * td_c * pos_c.get("qty", 0)
                                l_pct, l_usd = pf.record_closed_trade_pnl(pnl_est)
                                if l_pct >= 8.0:
                                    kb_snz = {"inline_keyboard": [
                                        [{"text": "🔕 15 min", "callback_data": "snooze_15"}, {"text": "🔕 30 min", "callback_data": "snooze_30"}, {"text": "🔕 60 min", "callback_data": "snooze_60"}],
                                        [{"text": "🔔 Zostaw aktywne", "callback_data": "snooze_off"}]
                                    ]}
                                    requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"🛑 <b>ALARM STRAZNIKA PORTFELA!</b>\nDzisiejsza strata wyniosla <b>-{l_usd}$ (-{l_pct}% konta)</b>.\n\nAby uniknac emocjonalnego odrabiania strat (revenge trading), czy wyciszyc powiadomienia CFD?", "parse_mode": "HTML", "reply_markup": kb_snz}, timeout=15)
                    elif cb.startswith("ex_"):
                        c = load_settings(); c["exchange"] = cb.replace("ex_", ""); get_dynamic_top_tiers(c["exchange"]); save_settings(c)
                        tg_menu(cid, tok, f"✅ Wybrana gielda: <b>{c['exchange']}</b>")
                    elif cb.startswith("liq_"):
                        c = load_settings(); c["liq_only"] = (cb == "liq_1"); _, mx_new = get_dynamic_top_tiers(c["exchange"]); c["top_n"] = mx_new; save_settings(c)
                        tg_menu(cid, tok, f"✅ Grupa: <b>{'Plynne' if c['liq_only'] else 'Wszystkie'}</b> ({mx_new})")
                    elif cb.startswith("top_"):
                        nv = int(cb.replace("top_", "")); c = load_settings(); c["top_n"] = nv; save_settings(c)
                        tg_menu(cid, tok, f"✅ Ustawiono: <b>TOP {nv}</b>")
                    elif cb == "tgl_cfd_live":
                        global CFD_LIVE_ACTIVE
                        CFD_LIVE_ACTIVE = not CFD_LIVE_ACTIVE
                        tg_menu(cid, tok, f"⚡ <b>Live CFD Auto-Skan (co 15 min): {'WLACZONY 🟢' if CFD_LIVE_ACTIVE else 'WYLACZONY ⚪'}</b>")
                    elif cb == "tgl_live":
                        global LIVE_ACTIVE; LIVE_ACTIVE = not LIVE_ACTIVE
                        tg_menu(cid, tok, f"🔄 Tryb Live: <b>{'WLACZONY' if LIVE_ACTIVE else 'WYLACZONY'}</b>")
                    elif cb in ("chart_layers", "back_menu") or cb.startswith("tgl_"):
                        if cb == "back_menu": tg_menu(cid, tok)
                        else:
                            opts = cm.toggle_chart_opt(cb.replace("tgl_", "")) if cb.startswith("tgl_") else cm.get_chart_opts()
                            names = [("all","⚡ WSZYSTKIE"),("ema","EMA 5/13"),("smc","BOS/CHoCH/POC"),("levels","TP/BUY/SL"),("vol","Wolumen"),("hurst","Hurst"),("rsi","RSI 14"),("macd","MACD"),("chop","CHOP 14")]
                            kb = {"inline_keyboard": [[{"text": f"{'✅' if (all(opts.values()) if k=='all' else opts.get(k)) else '❌'} {lbl}", "callback_data": f"tgl_{k}"}] for k, lbl in names] + [[{"text": "⬅ Powrot", "callback_data": "back_menu"}]]}
                            fn = "editMessageReplyMarkup" if cb.startswith("tgl_") else "sendMessage"
                            payload = {"chat_id": cid, "reply_markup": kb}
                            if fn == "editMessageReplyMarkup": payload["message_id"] = u["callback_query"]["message"]["message_id"]
                            else: payload["text"] = "⚙️ <b>Panele wykresu:</b>"; payload["parse_mode"] = "HTML"
                            requests.post(tg_url(tok, fn), json=payload)
                    elif cb == "prop_charts":
                        cands = ([x["symbol"] for x in LATEST["hits"]] + [x["symbol"] for x in LATEST["near"]]) or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
                        kb = {"inline_keyboard": [[{"text": f"📈 {sym}", "callback_data": f"ch_{sym}"}] for sym in cands.__getitem__(slice(0, 8))] + [[{"text": "⬅ Powrot", "callback_data": "back_menu"}]]}
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "📊 <b>Wybierz monete:</b>", "parse_mode": "HTML", "reply_markup": kb})
                    elif cb == "scan_stop":
                        global SCAN_STOP
                        SCAN_STOP = True
                        send_telegram("🛑 <b>Zatrzymano i zresetowano biezacy skan!</b>")
                    elif cb == "demo_preview":
                        btc_d, btc_lbl = get_live_btc_regime() if "get_live_btc_regime" in globals() else (-1, "🔴 BESSA BTC — Priorytet SHORT + Silne LONG")
                        side_d = "LONG" if btc_d == 1 else "SHORT"
                        td_d = 1 if side_d == "LONG" else -1
                        demo_hits = []
                        for sym_d, tag_d, prob_d in [("DOTUSDT", "💥 SQUEEZE CFD | 💪 RS +3.2% | FR -0.008%", 86), ("LINKUSDT", "🧲 Sweep & Reclaim | FR +0.004%", 82), ("INJUSDT", "💪 RS +2.6% | FR -0.012%", 79)]:
                            kl_d = fetch_klines("BITGET", sym_d, "15m", 20)
                            pr_d = kl_d["c"].__getitem__(-1) if kl_d else 10.0
                            en_d = round(pr_d * (1.002 * td_d + 1.0) if td_d == 1 else pr_d * 0.998, 4)
                            sl_d = round(en_d * (1.0 - 0.018 * td_d), 4)
                            tp_d = [round(en_d + td_d * abs(en_d - sl_d) * m, 4) for m in (1.0, 1.5, 2.5, 3.5, 5.0)]
                            demo_hits.append({
                                "symbol": sym_d, "side": side_d, "win_prob": prob_d, "alpha_tag": tag_d,
                                "price": pr_d, "entry": en_d, "stop": sl_d, "tp": tp_d, "is_trig": True, "req_cap": 15.0
                            })
                        LATEST["hits"] = demo_hits
                        LATEST["ts"] = datetime.now().strftime("%H:%M:%S (DEMO)")
                        btc_c = str(btc_lbl).replace("<", "&lt;").replace(">", "&gt;")
                        send_telegram(f"🎭 <b>TRYB DEMO — PODGLAD OKAZJI CFD</b>\n{btc_c}\n<i>Pulpit w Chrome (127.0.0.1:5000) zostal rowniez wypelniony tymi 3 okazjami!</i>")
                        for h in demo_hits:
                            tp1, tp2, tp3 = h["tp"].__getitem__(0), h["tp"].__getitem__(1), h["tp"].__getitem__(2)
                            card_t = (
                                f"⚡ <b>{h['symbol']}</b> — <b>{h['side']}</b> (DEMO)\n"
                                f"🎯 Szansa kontynuacji: <b>{h['win_prob']}%</b> | 🧬 <i>{h['alpha_tag']}</i>\n"
                                f"💵 Cena: <code>{h['price']}</code> | 🎯 Wejscie: <code>{h['entry']}</code>\n"
                                f"🛑 SL: <code>{h['stop']}</code> | ✅ TP1 (1R): <code>{tp1}</code> | 💰 TP2 (1.5R): <code>{tp2}</code>\n{apm.get_mtf_status_line('BITGET', h['symbol'], h['side'])}\n{pf.check_new_opportunity_margin(h['side'])}"
                            )
                            kb_c = {"inline_keyboard": [[{"text": f"🧮 Plan ({h['symbol']})", "callback_data": f"plan_{h['symbol']}"}, {"text": f"➕ Obstawiam", "callback_data": f"addp_{h['symbol']}"}, {"text": f"📈 Wykres", "callback_data": f"ch_{h['symbol']}"}]]}
                            requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": card_t, "parse_mode": "HTML", "reply_markup": kb_c}, timeout=15)
                    elif cb == "scan_cfd10":
                        kb_stop = {"inline_keyboard": [[{"text": "🛑 STOP / Reset Skanu", "callback_data": "scan_stop"}]]}
                        m = requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "⚡ <b>Skan CFD TOP-100 (Long/Short)...</b>\n<code>[░░░░░░░░░░] 0%</code>", "parse_mode": "HTML", "reply_markup": kb_stop}).json()
                        mid = m.get("result", {}).get("message_id")
                        def bg_cfd10():
                            global SCAN_STOP
                            SCAN_STOP = False
                            try:
                                top_cfd = apm.get_cfd_top60_symbols()
                                btc_d, btc_lbl = get_live_btc_regime() if "get_live_btc_regime" in globals() else (0, "NEUTRALNY")
                                hits = []
                                tot_c = len(top_cfd)
                                tp_cfg = atm.get_tuner_params()
                                min_p_dyn, sl_m_dyn = tp_cfg.get("min_prob", 64), tp_cfg.get("sl_mult", 1.0)
                                def _worker_cfd(sym_w):
                                    if SCAN_STOP: return None
                                    h = _scan_one_coin(("BITGET", sym_w, 1.0, load_settings().get("rules", {}), load_settings().get("enabled", ["15m", "1h", "4h", "1d"]), 1000.0, 1.5))
                                    if h and isinstance(h, dict):
                                        if sl_m_dyn != 1.0:
                                            td_w = 1 if h["side"] == "LONG" else -1
                                            h["stop"] = round(h["entry"] - td_w * abs(h["entry"] - h["stop"]) * sl_m_dyn, 6)
                                        ok_ob, ob_b, ob_tag = iom.get_orderflow_and_walls(h["symbol"], h["side"], h["entry"], h["tp"].__getitem__(0))
                                        sl_k = (abs(h["entry"] - h["stop"]) / max(1e-9, h["entry"])) * 100.0
                                        ok_k, kb, kt = aqm.evaluate_knn_pattern(h["side"], h.get("win_prob", 55), 25, sl_k, datetime.now().hour)
                                        ld, lt = aqm.get_lead_lag_impulse(sys.modules[__name__], h["symbol"])
                                        lb = 5 if ((h["side"] == "LONG" and ld == 1) or (h["side"] == "SHORT" and ld == -1)) else 0
                                        kl_q = fetch_klines("BITGET", h["symbol"], "15m", 35)
                                        reg_k, reg_b, reg_tag = elm.detect_volatility_regime(kl_q)
                                        ent_v, ok_ent, ent_tag = fqm.calc_shannon_entropy(kl_q)
                                        ent_b = 4 if ent_v < 0.68 else (-5 if not ok_ent else 0)
                                        ok_rt, rt_b, rt_tag = fqm.detect_whale_iceberg_and_redteam(h["side"], kl_q)
                                        qw_b, qw_tag = qnm.quantum_wave_interference(h["side"], h["entry"], h["tp"].__getitem__(0), h["stop"], kl_q)
                                        ok_nash, nash_b, nash_tag = qnm.detect_nash_predator_trap(h["side"], kl_q)
                                        bn_b, bn_tag = qep.check_binance_futures_lead(h["symbol"], h["side"], h["price"])
                                        sl_fp, fp_b, fp_tag = qep.profile_coin_fingerprint(kl_q)
                                        ok_tail, soc_b, tail_tag = qep.check_extreme_tail_and_social(h["symbol"], kl_q, [])
                                        if sl_fp != 1.0: h["stop"] = round(h["entry"] - (h["entry"] - h["stop"]) * sl_fp, 6)
                                        ai_pts = mbm.apply_brain_weights(ob_b, kb, lb, reg_b, rt_b, qw_b) + nash_b + bn_b + fp_b + soc_b + ent_b
                                        h["win_prob"] = max(45, min(96, int(h.get("win_prob", 55)) + ai_pts))
                                        extra_tags = [x for x in (ob_tag, kt, lt if lb else "", reg_tag, ent_tag, rt_tag, qw_tag, nash_tag, fp_tag, bn_tag if bn_b else "") if x]
                                        h["alpha_tag"] = " | ".join(([h["alpha_tag"]] if h.get("alpha_tag") else []) + extra_tags)
                                        if not (ok_ob and ok_k and reg_k != "CHOP" and ok_rt and ok_nash):
                                            why_rej = "+".join([nm for flg, nm in ((ok_ob, "OB_WALL"), (ok_k, "KNN"), (reg_k != "CHOP", "CHOP_SHIELD"), (ok_rt, "RED_TEAM"), (ok_nash, "NASH_TRAP"), (ok_tail, "TAIL_LOCK")) if not flg]) or "SNIPER_FILTER"
                                            nzt.record_rejected_hypothesis(h["symbol"], h["side"], h["entry"], h["stop"], why_rej)
                                            for flg, nm in ((ok_ob, "OB_WALL"), (ok_k, "KNN"), (reg_k != "CHOP", "CHOP_SHIELD"), (ok_rt, "RED_TEAM"), (ok_nash, "NASH_TRAP")):
                                                if not flg: r24.record_funnel_drop(nm)
                                        if ok_ob and ok_k and reg_k != "CHOP" and ok_rt and ok_nash and ok_tail and h["symbol"] not in sam.get_bitbase_blacklist() and sdm.check_sniper_quality(h["side"], btc_d, fetch_klines("BITGET", h["symbol"], "15m", 5))[0] and apm.validate_cfd_order(h["entry"], h["stop"], h["price"]) and h.get("win_prob", 0) >= min_p_dyn:
                                            return h
                                    return None
                                done_c = 0
                                with ThreadPoolExecutor(max_workers=12) as ex_pool:
                                    futs = {ex_pool.submit(_worker_cfd, sym): sym for sym in top_cfd}
                                    for fut in as_completed(futs):
                                        if SCAN_STOP: break
                                        done_c += 1
                                        if mid and (done_c % 6 == 0 or done_c == tot_c):
                                            pct = int((done_c / tot_c) * 100)
                                            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
                                            try: requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": mid, "text": f"⚡ <b>Skan CFD TOP-100 (12x Turbo):</b> ({done_c}/{tot_c})\n<code>[{bar}] {pct}%</code>", "parse_mode": "HTML", "reply_markup": kb_stop}, timeout=4)
                                            except Exception: pass
                                        res_h = fut.result()
                                        if res_h: hits.append(res_h)
                                if SCAN_STOP:
                                    if mid:
                                        try: requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": mid, "text": "🛑 <b>Skanowanie przerwane i zresetowane!</b>", "parse_mode": "HTML"}, timeout=4)
                                        except Exception: pass
                                    return
                                if mid:
                                    try:
                                        requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": mid, "text": "✅ <b>Skan CFD TOP-100 zakonczony!</b>\n<code>[██████████] 100%</code>", "parse_mode": "HTML"}, timeout=15)
                                    except Exception:
                                        pass
                                btc_cm = str(btc_lbl).replace("<", "&lt;").replace(">", "&gt;")
                                if not hits:
                                    nh_txt = f"⠀⠀🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n⛔ <b>BRAK AKTYWNYCH SYGNAŁÓW</b> ⛔\n⠀⠀🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n⚡ <b>CFD TOP-100</b> ({btc_cm})\nBrak czystego wejscia w tym kwadransie (próg Auto-Tunera: <b>{min_p_dyn}%</b>). Czekamy na impuls bez otwierania pozycji na sile."
                                    requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": nh_txt, "parse_mode": "HTML", "reply_markup": {"inline_keyboard": [[{"text": "🔄 Skanuj ponownie", "callback_data": "scan_cfd10"}, {"text": "⬅ Menu", "callback_data": "back_menu"}]]}}, timeout=15)
                                else:
                                    hits.sort(key=lambda x: -x.get("win_prob", 0))
                                    top3_m = hits.__getitem__(slice(0, 2))
                                    LATEST["hits"] = top3_m
                                    log_cfd_hits_to_file(top3_m, "SKAN")
                                    requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"⠀⠀🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n✅ <b>SĄ AKTYWNE OKAZJE!</b> ✅\n⠀⠀🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n⚡ <b>SYGNALY CFD TOP-100</b> | {btc_cm}\nZnaleziono <b>{len(top3_m)}</b> najlepsze okazje:", "parse_mode": "HTML"}, timeout=15)
                                    for h in top3_m:
                                        tps_m = h.get("tp", [])
                                        tp1_m = tps_m.__getitem__(0) if len(tps_m) > 0 else h["entry"]
                                        tp2_m = tps_m.__getitem__(1) if len(tps_m) > 1 else h["entry"]
                                        card_m = (
                                            f"⚡ <b>{h['symbol']}</b> — <b>{h['side']}</b>\n"
                                            f"🎯 Szansa kontynuacji: <b>{h.get('win_prob', 75)}%</b> | 🧬 <i>{h.get('alpha_tag', 'FR OK')}</i>\n"
                                            f"💵 Cena: <code>{h.get('price', h['entry'])}</code> | 🎯 Wejscie: <code>{h['entry']}</code>\n"
                                            f"🛑 SL: <code>{h['stop']}</code> | ✅ TP1: <code>{tp1_m}</code> | 💰 TP2: <code>{tp2_m}</code>\n"
                                            f"{apm.get_mtf_status_line('BITGET', h['symbol'], h['side'])}\n"
                                            f"{pf.check_new_opportunity_margin(h['side'])}\n{sdm.build_action_instruction(h['symbol'], h['side'], h['entry'], h['stop'], tp1_m, h.get('is_trig', True))}"
                                        )
                                        kb_m = {"inline_keyboard": [[{"text": f"🧮 Plan ({h['symbol']})", "callback_data": f"plan_{h['symbol']}"}, {"text": "➕ Obstawiam", "callback_data": f"addp_{h['symbol']}"}, {"text": "📈 Wykres", "callback_data": f"ch_{h['symbol']}"}, {"text": "🛡️ Audyt", "callback_data": f"aud_{h['symbol']}"}, {"text": "🚫 Brak BitBase", "callback_data": f"bbl_{h['symbol']}"}]]}
                                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": card_m, "parse_mode": "HTML", "reply_markup": kb_m}, timeout=15)
                            except Exception as err:
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"⚠️ Blad skanu CFD: <code>{err}</code>", "parse_mode": "HTML"}, timeout=15)
                        threading.Thread(target=bg_cfd10, daemon=True).start()
                    elif cb == "scan_now":
                        m = requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"⏳ <b>Skanuje {ex}...</b>", "parse_mode": "HTML"}).json()
                        mid = m.get("result", {}).get("message_id")
                        def bg():
                            run_full_scan(show_term=False, tg_mid=mid)
                            hits_sorted = sorted(LATEST["hits"], key=lambda x: (-x.get("win_prob", 0), x["req_cap"]))
                            requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": mid, "text": f"✅ <b>Gotowe ({ex})!</b> Znaleziono: <b>{len(hits_sorted)}</b> (od najpewniejszej od gory) | W poblizu: <b>{len(LATEST['near'])}</b>", "parse_mode": "HTML"})
                            for idx, h in enumerate(hits_sorted, 1):
                                kb_h = {"inline_keyboard": [[{"text": "➕ Obstawiam", "callback_data": f"addp_{h['symbol']}"}, {"text": "📈 Wykres", "callback_data": f"ch_{h['symbol']}"}, {"text": "🛡️ Audyt", "callback_data": f"aud_{h['symbol']}"}, {"text": "🚫 Brak BitBase", "callback_data": f"bbl_{h['symbol']}"}, {"text": "🧮 Planner", "callback_data": f"plan_{h['symbol']}"}], [{"text": f"🌐 Otworz {ex} ({h['symbol']})", "url": get_exchange_url(ex, h['symbol'])}]]}
                                send_telegram(format_tg_card(h, ex, f" #{idx}"), kb_h)
                                time.sleep(0.35)
                            if LATEST["near"]:
                                rows = [f"{n['symbol'].replace('USDT',''):<6} {n['side']:<5} {n['dist_pct']}% ({n['eta_str']})" for n in LATEST["near"].__getitem__(slice(0, 12))]
                                send_telegram("👀 <b>Obserwowane (blisko wybicia):</b>\n<pre>" + "\n".join(rows) + "</pre>")
                            tg_menu(cid, tok)
                        threading.Thread(target=bg, daemon=True).start()
                    elif cb == "demo_pro":
                        try:
                            rep = ds24.get_demo_pro_report()
                            kb_p = {"inline_keyboard": [[{"text": "🚀 Start / Reset Symulacji PRO", "callback_data": "demo_pro_new"}, {"text": "🔄 Odswiez PRO", "callback_data": "demo_pro"}], [{"text": "⬅ Menu", "callback_data": "back_menu"}]]}
                            if not rep:
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "🏆 <b>SYMULACJA PRO #2 (1000$ | Plynne + Rezim BTC + Partial TP 1.5R)</b>\nKliknij przycisk ponizej, aby wystartowac ulepszona symulacje rownolegle do obecnej!", "parse_mode": "HTML", "reply_markup": kb_p})
                            else:
                                t_pct = min(100, max(0, int(((24.0 - rep["rem_h"]) / 24.0) * 100)))
                                t_bar = "█"*(t_pct//10) + "░"*(10 - t_pct//10)
                                pos_idx = min(10, max(0, int(((rep["total_pnl"] + 50.0) / 150.0) * 10)))
                                pnl_gauge = "📉 " + "".join("●" if k == pos_idx else "═" for k in range(11)) + " 📈"
                                rows_p = [f"• <b>{p['symbol']}</b> ({p['side']} | {p['win_prob']}%) — {p['close_reason'] if p['closed'] else ('🟢 Aktywna' if p['entered'] else '⏳ Czeka')} | <b>{p['realized_pnl']:+.2f}$</b>" for p in rep["positions"]]
                                msg_p = (
                                    f"🏆 <b>SYMULACJA PRO #2 ({rep['exchange']} | Plynne + BTC + 1.5R BE)</b>\n"
                                    f"⏳ Odliczanie: <code>[{t_bar}] {t_pct}%</code> (zostalo <b>{rep['rem_h']}h</b>)\n"
                                    f"{pnl_gauge}\n"
                                    f"💰 Kapital: <b>1000.00$</b> → Saldo: <b>{rep['equity']:.2f}$</b> (<b>{rep['total_pnl']:+.2f}$</b> / {rep['pnl_pct']:+.2f}%)\n"
                                    f"🎯 Skutecznosc: <b>{rep['win_rate']}%</b> (✅ {rep['wins']} / ❌ {rep['losses']})\n\n"
                                    + "\n".join(rows_p)
                                )
                                try:
                                    cb_img = ds24.build_demo_chart_png(rep)
                                    if cb_img:
                                        requests.post(tg_url(tok, "sendPhoto"), data={"chat_id": cid, "caption": "📈 Wykres Symulacji PRO #2"}, files={"photo": ("pro.png", cb_img, "image/png")}, timeout=12)
                                except Exception:
                                    pass
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": msg_p, "parse_mode": "HTML", "reply_markup": kb_p})
                        except Exception as err:
                            send_telegram(f"⚠️ Blad Symulacji PRO: <code>{err}</code>")
                    elif cb == "demo_pro_new":
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "⏳ <b>Skanuje plynne pary (BYBIT) z filtrem rezimu BTC dla Symulacji PRO #2...</b>", "parse_mode": "HTML"})
                        def bg_pro():
                            sim = ds24.start_demo_pro_24h()
                            if not sim:
                                send_telegram("⚠️ Brak sygnalow zgodnych z rezimem BTC w tym momencie. Sprobuj za kilka minut.")
                            else:
                                send_telegram(f"✅ <b>Wystartowano Symulacje PRO #2 (1000$) na {sim['exchange']}!</b>\nOtwarto <b>{len(sim['positions'])}</b> plynnych pozycji. Kliknij <b>🏆 Symulacja PRO #2</b>, aby sledzic wynik.")
                        threading.Thread(target=bg_pro, daemon=True).start()
                    elif cb == "demo_24h":
                        try:
                            rep = ds24.get_demo_report()
                            kb_d = {"inline_keyboard": [[{"text": "🚀 Nowa Symulacja 24H", "callback_data": "demo_24h_new"}, {"text": "🔄 Odswiez Podglad", "callback_data": "demo_24h"}], [{"text": "⬅ Menu", "callback_data": "back_menu"}]]}
                            if not rep:
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "📊 <b>PODGLAD SYMULACJI 24H (1000$)</b>\nBrak aktywnej symulacji. Kliknij <b>🚀 Nowa Symulacja 24H</b>!", "parse_mode": "HTML", "reply_markup": kb_d})
                            else:
                                t_pct = min(100, max(0, int(((24.0 - rep["rem_h"]) / 24.0) * 100)))
                                t_bar = "█"*(t_pct//10) + "░"*(10 - t_pct//10)
                                pos_idx = min(10, max(0, int(((rep["total_pnl"] + 50.0) / 150.0) * 10)))
                                pnl_gauge = "📉 " + "".join("●" if k == pos_idx else "═" for k in range(11)) + " 📈"
                                rows_d = []
                                for p in rep["positions"]:
                                    tps_s = "".join("✅" if x else "⬜" for x in p["hit_tps"])
                                    st_p = p["close_reason"] if p["closed"] else ("🟢 Aktywna" if p["entered"] else "⏳ Czeka")
                                    rows_d.append(f"• <b>{p['symbol']}</b> ({p['side']}) — {st_p} | TP:{tps_s} | <b>{p['realized_pnl']:+.2f}$</b>")
                                msg_d = (
                                    f"📊 <b>PODGLAD SYMULACJI 24H ({rep['exchange']})</b>\n"
                                    f"⏳ Odliczanie: <code>[{t_bar}] {t_pct}%</code> (zostalo <b>{rep['rem_h']}h</b>)\n"
                                    f"{pnl_gauge}\n"
                                    f"💰 Kapital: <b>1000.00$</b> → Saldo: <b>{rep['equity']:.2f}$</b> (<b>{rep['total_pnl']:+.2f}$</b> / {rep['pnl_pct']:+.2f}%)\n"
                                    f"🎯 Skutecznosc: <b>{rep['win_rate']}%</b> (✅ {rep['wins']} / ❌ {rep['losses']})\n\n"
                                    + "\n".join(rows_d)
                                )
                                try:
                                    chart_b = ds24.build_demo_chart_png(rep)
                                    if chart_b:
                                        requests.post(tg_url(tok, "sendPhoto"), data={"chat_id": cid, "caption": f"📈 Wykres Symulacji 24H ({rep['exchange']})"}, files={"photo": ("sim.png", chart_b, "image/png")}, timeout=12)
                                except Exception:
                                    pass
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": msg_d, "parse_mode": "HTML", "reply_markup": kb_d})
                        except Exception as err:
                            send_telegram(f"⚠️ Blad podgladu symulacji: <code>{err}</code>")
                    elif cb == "demo_24h_new":
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "⏳ <b>Tworze Symulacje 24H (1000$) z dopasowanych monet...</b>", "parse_mode": "HTML"})
                        def bg_d24():
                            sim = ds24.start_demo_24h()
                            if not sim:
                                send_telegram("⚠️ Brak sygnalow w tym cyklu. Kliknij Skanuj lub zmien gielde.")
                            else:
                                send_telegram(f"✅ <b>Rozpoczeto Symulacje 24H (1000$) na {sim['exchange']}!</b>\nOtwarto <b>{len(sim['positions'])}</b> pozycji. Kliknij <b>📊 Podglad Symulacji</b>, aby zobaczyc wykres.")
                        threading.Thread(target=bg_d24, daemon=True).start()
                    elif cb == "demo_tg":
                        fill_demo()
                        for d in LATEST["hits"]: send_telegram(format_tg_card(d, ex, " [DEMO]"), {"inline_keyboard": [[{"text": "➕ Obstawiam", "callback_data": f"addp_{d['symbol']}"}, {"text": "📈 Wykres", "callback_data": f"ch_{d['symbol']}"}, {"text": "🧮 Planner", "callback_data": f"plan_{d['symbol']}"}]]})
                        tg_menu(cid, tok)
                    elif cb.startswith("ch_"):
                        sym = cb.replace("ch_", ""); buf, ta_info = cm.build_chart_buf(ex, sym)
                        if buf and ta_info:
                            requests.post(tg_url(tok, "sendPhoto"), data={"chat_id": cid, "caption": f"📈 <b>{sym} ({ex})</b>\n{ta_info['summary']}", "parse_mode": "HTML"}, files={"photo": ("c.png", buf, "image/png")}, timeout=15)
                    elif cb == "bt_menu":
                        kb_bt = {"inline_keyboard": [
                            [{"text": "📜 BTCUSDT (2020-2026)", "callback_data": "bt_BTCUSDT"}, {"text": "📜 ETHUSDT (2020-2026)", "callback_data": "bt_ETHUSDT"}],
                            [{"text": "📜 SOLUSDT (2020-2026)", "callback_data": "bt_SOLUSDT"}, {"text": "📜 BNBUSDT (2020-2026)", "callback_data": "bt_BNBUSDT"}],[{"text": "🌐 Portfel TOP 10 (2020-26)", "callback_data": "bt_M10"}],[{"text": "🌐 Portfel TOP 20 (2020-26)", "callback_data": "bt_M20"}],
                            [{"text": "🚀 Rotacja TOP-3 Liderow", "callback_data": "bt_ROT3"}],
                            [{"text": "⚡ CFD Turbo (Squeeze + Piramida)", "callback_data": "bt_CFD"}],
                            [{"text": "🛑 STOP / Reset Backtestu", "callback_data": "bt_stop"}], [{"text": "⬅ Menu", "callback_data": "back_menu"}]
                        ]}
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "📜 <b>BACKTEST HISTORYCZNY (2020 — 2026)</b>\nWybierz monete (symulacja 1000 USDT, ryzyko 1%, swiece 1H od 2020 roku):", "parse_mode": "HTML", "reply_markup": kb_bt})
                    elif cb == "bt_stop":
                        bt20.BT_STOP = True
                        send_telegram("🛑 <b>Zatrzymano i zresetowano Backtest!</b> Mozesz uruchomic nowy test.")
                    elif cb.startswith("bt_"):
                        bt20.BT_STOP = False
                        bsym = cb.replace("bt_", "").strip()
                        m = requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"⏳ <b>Start {bsym}...</b> [0%]", "parse_mode": "HTML"}).json()
                        mid = m.get("result", {}).get("message_id")
                        def bg_bt():
                            st = {"t": 0.0}
                            def ub(p, info):
                                if mid and time.time() - st["t"] >= 1.5:
                                    st["t"] = time.time(); bar = "█"*(p//10) + "░"*(10 - p//10)
                                    try: requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": mid, "text": f"⏳ <b>{info}</b>\n<code>[{bar}] {p}%</code>", "parse_mode": "HTML", "reply_markup": {"inline_keyboard": [[{"text": "🛑 STOP / Reset", "callback_data": "bt_stop"}]]}}, timeout=5)
                                    except Exception: pass
                            t20 = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","TRXUSDT","MATICUSDT","LTCUSDT","BCHUSDT","ATOMUSDT","UNIUSDT","NEARUSDT","APTUSDT","FILUSDT","INJUSDT"]
                            res = bt20.run_multi_backtest_2020(t20.__getitem__(slice(0, 10)), 2020, 1000.0, ub) if bsym=="M10" else (bt20.run_cfd_turbo_2020(apm.get_cfd_top60_symbols(), 2020, 1000.0) if bsym=="CFD" else (bt20.run_rotation_top3_2020(["BTCUSDT","DOTUSDT","LINKUSDT","TRXUSDT","ADAUSDT","DOGEUSDT","INJUSDT","BCHUSDT"], 2020, 1000.0) if bsym=="ROT3" else (bt20.run_multi_backtest_2020(t20, 2020, 1000.0, ub) if bsym=="M20" else bt20.run_backtest_2020(bsym, 2020, 1000.0, 1.0, ub))))
                            if mid:
                                try: requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": mid, "text": f"✅ <b>Zakonczono analizę {bsym}!</b>\n<code>[██████████] 100%</code>", "parse_mode": "HTML"}, timeout=5)
                                except Exception: pass
                            if not res: send_telegram(f"⚠️ Brak danych dla {bsym}"); return
                            yr_l = "\n".join(f"• <b>{y}:</b> {v:+.2f}$" for y, v in sorted(res["yearly"].items()))
                            mo_l = "\n".join(f"• {k}: <b>{v:+.2f}$</b>" for k, v in sorted(res["monthly"].items()).__getitem__(slice(-12, None)))
                            cs_l = ("\n\n<b>🏆 MONETY:</b>\n" + "\n".join(f"• <b>{c}:</b> {v:+.2f}$ (WR {w}%)" for c, v, w in res["coin_stats"].__getitem__(slice(0, 10)))) if "coin_stats" in res else ""
                            cb_img = bt20.build_bt_chart_png(res)
                            if cb_img: requests.post(tg_url(tok, "sendPhoto"), data={"chat_id": cid, "caption": f"📈 {res['symbol']} ({res['date_from']} -> {res['date_to']})"}, files={"photo": ("bt.png", cb_img, "image/png")}, timeout=15)
                            send_telegram(f"📜 <b>{res['symbol']}</b> ({res['date_from']} → {res['date_to']})\n💰 1000$ → <b>{res['final_cap']:.2f}$</b> (<b>{res['net_pct']:+.1f}%</b>) | WR: <b>{res['win_rate']}%</b>\n\n<b>📊 LATA:</b>\n{yr_l}\n\n<b>🗓️ OSTATNIE 12 MIES.:</b>\n{mo_l}{cs_l}")
                        threading.Thread(target=bg_bt, daemon=True).start()
                    elif cb == "chart_layers":
                        st_l = load_settings()
                        cur_l = st_l.get("layers", {"ema": True, "smc": True, "sr": True, "fvg": True})
                        txt_l = "⚙️ <b>WARSTWY WYKRESU SMC / EMA</b>\nKliknij warstwe, aby wlaczyc/wylaczyc na wykresach:"
                        kb_l = {"inline_keyboard": [
                            [{"text": f"{'✅' if cur_l.get('ema', True) else '❌'} EMA 21/50/200", "callback_data": "tgl_l_ema"},
                             {"text": f"{'✅' if cur_l.get('smc', True) else '❌'} SMC / OrderBlocks", "callback_data": "tgl_l_smc"}],
                            [{"text": f"{'✅' if cur_l.get('sr', True) else '❌'} Wsparcia/Opory", "callback_data": "tgl_l_sr"},
                             {"text": f"{'✅' if cur_l.get('fvg', True) else '❌'} FVG / Imbalance", "callback_data": "tgl_l_fvg"}],
                            [{"text": "⬅ Menu", "callback_data": "back_menu"}]
                        ]}
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": txt_l, "parse_mode": "HTML", "reply_markup": kb_l}, timeout=15)
                    elif cb.startswith("tgl_l_"):
                        lk = cb.replace("tgl_l_", "")
                        st_l = load_settings()
                        cur_l = st_l.setdefault("layers", {"ema": True, "smc": True, "sr": True, "fvg": True})
                        cur_l[lk] = not cur_l.get(lk, True)
                        save_settings(st_l)
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"✅ Przelaczono warstwe <b>{lk.upper()}</b> -> <b>{'WLACZONA' if cur_l[lk] else 'WYLACZONA'}</b>", "parse_mode": "HTML"}, timeout=15)
                    elif cb.startswith("bbl_"):
                        bs = sam.add_to_bitbase_blacklist(cb.replace("bbl_", ""))
                        send_telegram(f"🚫 Dodano <b>{bs}</b> do czarnej listy BitBase (nadal badana w laboratoriach, zero alertow).")
                    elif cb.startswith("aud_"):
                        sym_a = cb.replace("aud_", "")
                        rep_a = cam.audit_token_contract(sym_a)
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": rep_a, "parse_mode": "HTML"}, timeout=15)
                    elif cb == "open_chrome_ui":
                        import subprocess
                        subprocess.Popen(["am", "start", "--user", "0", "-a", "android.intent.action.VIEW", "-d", "http://127.0.0.1:5000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "🌐 <b>Otwieram Pulpit PRO 2.0 w Chrome...</b>\nAdres: <a href=\"http://127.0.0.1:5000\">http://127.0.0.1:5000</a>", "parse_mode": "HTML"}, timeout=10)
                    elif cb == "scan_pd":
                        p_msg = requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "🚀 <b>Skanuję WSZYSTKIE pary na giełdzie (7 wzorców Pump & Dump + Wywiad Sieciowy)...</b>\n<code>[░░░░░░░░░░] 0%</code>", "parse_mode": "HTML"}, timeout=15).json()
                        p_mid = p_msg.get("result", {}).get("message_id")
                        uniq_syms = apm.get_all_futures_symbols()
                        tot_u = max(1, len(uniq_syms))
                        pd_hits, done_u = [], 0
                        with ThreadPoolExecutor(max_workers=20) as pdp:
                            for r_pd in pdp.map(apm.scan_macro_pump_dump_coin, uniq_syms):
                                done_u += 1
                                if r_pd: pd_hits.append(r_pd)
                                if p_mid and (done_u % 28 == 0 or done_u == tot_u):
                                    pct_u = int(done_u * 100 / tot_u)
                                    bars_u = "█" * (pct_u // 10) + "░" * (10 - pct_u // 10)
                                    try:
                                        requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": p_mid, "text": f"🚀 <b>Skanuję {tot_u} par (7 wzorców Pump & Dump)...</b>\n<code>[{bars_u}] {pct_u}%</code> ({done_u}/{tot_u})", "parse_mode": "HTML"}, timeout=10)
                                    except Exception: pass
                        if not pd_hits:
                            requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "⠀⠀🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n⛔ <b>BRAK AKTYWNYCH SYGNAŁÓW</b> ⛔\n⠀⠀🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n🚀 <b>Skan Pump & Dump (100% par na giełdzie)</b>\nSprawdzono rynek pod kątem <b>7 wzorców</b>:\n1️⃣ <i>Wybicie z bazy (BLZ/LOOM)</i> — skok vol &gt;4x na 1D\n2️⃣ <i>Blow-Off Top (TRB/CYBER)</i> — rajd &gt;100% + knot odrzucenia\n3️⃣ <i>Parabolic Rug Bleed (RAVE/OM)</i> — spadek po paraboli pod MA7/MA25\n4️⃣ <i>Flash Pump &amp; Dump (15M)</i> — szybka pompa &gt;8% i zrzut\n5️⃣ <i>Bot Ping-Pong</i> — równe słupki 50/50 + wybicie\n6️⃣ <i>Funding Squeeze</i> — ujemny funding &lt;-0.15%\n7️⃣ <i>Staircase Dump</i> — 5+ zielonych 1H + pierwsza czerwona", "parse_mode": "HTML"}, timeout=15)
                        else:
                            pd_hits.sort(key=lambda x: -x.get("win_prob", 0))
                            LATEST["hits"] = pd_hits.__getitem__(slice(0, 4))
                            requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "⠀⠀🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n✅ <b>SĄ AKTYWNE OKAZJE!</b> ✅\n⠀⠀🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n🚀 <b>WYKRYTO POMPĘ / ZRZUT (7 WZORCÓW)!</b>", "parse_mode": "HTML"}, timeout=15)
                            for h in pd_hits.__getitem__(slice(0, 4)):
                                tps_p = h.get("tp", [])
                                card_p = (
                                    f"{h.get('mode', '🚀 PUMP/DUMP')} — <b>{h['symbol']} ({h['side']})</b>\n"
                                    f"🏅 Poziom: <b>{atm.get_tier_label(h.get('win_prob', 60))}</b> | 🎯 Szansa: <b>{h['win_prob']}%</b> | 🧬 <i>{h['alpha_tag']}</i>\n📐 <b>Wzorzec:</b> {h.get('pattern_fit', '-')}\n📖 <b>Rozwoj sytuacji:</b> <i>{h.get('narrative', '-')}</i>\n"
                                    f"💵 Cena: <code>{h['price']}</code> | 🛑 SL: <code>{h['stop']}</code>\n"
                                    f"✅ TP1: <code>{tps_p.__getitem__(0)}</code> | 💰 TP2: <code>{tps_p.__getitem__(1)}</code> | 🏆 TP3: <code>{tps_p.__getitem__(2)}</code>"
                                )
                                kb_p = {"inline_keyboard": [[{"text": f"🧮 Plan ({h['symbol']})", "callback_data": f"plan_{h['symbol']}"}, {"text": "➕ Obstawiam", "callback_data": f"addp_{h['symbol']}"}, {"text": "📈 Wykres", "callback_data": f"ch_{h['symbol']}"}, {"text": "🛡️ Audyt", "callback_data": f"aud_{h['symbol']}"}, {"text": "🚫 Brak BitBase", "callback_data": f"bbl_{h['symbol']}"}]]}
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": card_p, "parse_mode": "HTML", "reply_markup": kb_p}, timeout=15)
                    elif cb == "clear_cfd_hist":
                        if os.path.exists(CFD_HIST_FILE): os.remove(CFD_HIST_FILE)
                        send_telegram("🗑️ <b>Historia trafien Live CFD zostala wyczyszczona!</b>")
                    elif cb == "force_r24":
                        r24.check_and_build_24h_report(sys.modules[__name__], force=True)
                    elif cb == "doc_rep":
                        send_telegram(sdm.run_account_doctor())
                    elif cb == "csv":
                        tbl_txt = render_cfd_history_table()
                        kb_h = {"inline_keyboard": [[{"text": "🔄 Odswiez tabele", "callback_data": "csv"}, {"text": "🗑️ Wyczysc", "callback_data": "clear_cfd_hist"}], [{"text": "⬅ Menu", "callback_data": "back_menu"}]]}
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": tbl_txt, "parse_mode": "HTML", "reply_markup": kb_h}, timeout=15)
                    elif cb == "_old_csv":
                        lines = open(CSV_FILE).readlines().__getitem__(slice(-5, None)) if os.path.exists(CSV_FILE) else ["Pusto."]
                        send_telegram("<pre>" + "".join(lines) + "</pre>")
        except Exception: time.sleep(2)

def draw_box(title, col, rows):
    """Realizuje logike: draw box. Parametry: title, col, rows."""
    cols = max(48, shutil.get_terminal_size((52, 24)).columns)
    if cols >= 96:
        w_s = max(5, cols - 1 - (5 + 6 + 56 + 4 + 13))
        inn = w_s + 5 + 6 + 56 + 4 + 11
        hdr = f"─ {title} ({len(rows)}) "
        print(f"\n{col}{B}┌{hdr}{'─'*max(1, inn-len(hdr))}┐{W}")
        print(f"{col}│{W}{'MONETA':<{w_s}}{col}│{W}{'KIER':<5}{col}│{W}{'STATUS':<6}{col}│{W}{'CENA':>7}{col}│{W}{'WEJSCIE':>7}{col}│{W}{'SL':>7}{col}│{W}{'TP 1R':>7}{col}│{W}{'TP 2R':>7}{col}│{W}{'TP 3R':>7}{col}│{W}{'TP 4R':>7}{col}│{W}{'TP 5R':>7}{col}│{W}{'KAP':>4}{col}│{W}")
        print(f"{col}├{'─'*w_s}┼─────┼──────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼────┤{W}")
        for h in rows:
            sym = h["symbol"].replace("USDT", "")[:w_s]
            kc = G if h["side"] == "LONG" else R
            sc = f"{G}{B}" if h["is_trig"] else (R if not h.get("price_ok", True) else C)
            st = "TRIGG." if h["is_trig"] else ("DALEKO" if not h.get("price_ok", True) else "GOTOWY")
            t1, t2, t3, t4, t5 = [fmt_p(x).strip()[:7] for x in h["tp"]]
            print(f"{col}│{W}{B}{sym:<{w_s}}{W}{col}│{W}{kc}{h['side']:<5}{W}{col}│{W}{sc}{st:<6}{W}{col}│{W}{fmt_p(h['price']).strip()[:7]:>7}{col}│{W}{fmt_p(h['entry']).strip()[:7]:>7}{col}│{W}{fmt_p(h['stop']).strip()[:7]:>7}{col}│{W}{t1:>7}{col}│{W}{t2:>7}{col}│{W}{t3:>7}{col}│{W}{t4:>7}{col}│{W}{t5:>7}{col}│{W}{col}{h['req_cap']:>3}${W}{col}│{W}")
        print(f"{col}└{'─'*w_s}┴─────┴──────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴────┘{W}")
    else:
        av = max(27, cols - 1 - 23)
        w_s = 6 + max(0, (av - 27) // 4); rem = av - w_s; wp = rem // 3; we = rem // 3; wsl = rem - wp - we
        inn = w_s + 21 + wp + we + wsl
        hdr = f"─ {title} ({len(rows)}) "
        print(f"\n{col}{B}┌{hdr}{'─'*max(1, inn-len(hdr))}┐{W}")
        print(f"{col}│{W}{'MONETA':<{w_s}}{col}│{W}{'KIER':<5}{col}│{W}{'STATUS':<6}{col}│{W}{'CENA':>{wp}}{col}│{W}{'WEJSCIE':>{we}}{col}│{W}{'SL':>{wsl}}{col}│{W}{'KAP':>4}{col}│{W}")
        print(f"{col}├{'─'*w_s}┼─────┼──────┼{'─'*wp}┼{'─'*we}┼{'─'*wsl}┼────┤{W}")
        for idx, h in enumerate(rows):
            sym = h["symbol"].replace("USDT", "")[:w_s]
            kc = G if h["side"] == "LONG" else R
            sc = f"{G}{B}" if h["is_trig"] else (R if not h.get("price_ok", True) else C)
            st = "TRIGG." if h["is_trig"] else ("DALEKO" if not h.get("price_ok", True) else "GOTOWY")
            print(f"{col}│{W}{B}{sym:<{w_s}}{W}{col}│{W}{kc}{h['side']:<5}{W}{col}│{W}{sc}{st:<6}{W}{col}│{W}{fmt_p(h['price']).strip()[:wp]:>{wp}}{col}│{W}{fmt_p(h['entry']).strip()[:we]:>{we}}{col}│{W}{fmt_p(h['stop']).strip()[:wsl]:>{wsl}}{col}│{W}{col}{h['req_cap']:>3}${W}{col}│{W}")
            tps = [fmt_p(v).strip() for v in h["tp"]]
            bw, rw = (inn - 4) // 5, (inn - 4) % 5
            cw = [bw + (1 if j < rw else 0) for j in range(5)]
            print(f"{col}├" + "┼".join(f"{'─'*((cw[j]-2)//2)}{C}{j+1}R{col}{'─'*(cw[j]-2-(cw[j]-2)//2)}" for j in range(5)) + f"┤{W}")
            print(f"{col}│" + f"{col}│".join(f"{W}{C}{tps[j][:cw[j]]:^{cw[j]}}{W}" for j in range(5)) + f"{col}│{W}")
            if idx < len(rows) - 1: print(f"{col}├{'─'*w_s}┼─────┼──────┼{'─'*wp}┼{'─'*we}┼{'─'*wsl}┼────┤{W}")
        print(f"{col}└{'─'*w_s}┴─────┴──────┴{'─'*wp}┴{'─'*we}┴{'─'*wsl}┴────┘{W}")

def draw_term():
    """Realizuje logike: draw term."""
    top_n = load_settings()["top_n"]
    print(f"\n{C}{B}=== WYNIKI ({LATEST['exchange']} | TOP {top_n} | {LATEST['time']}) ==={W}")
    hits = [x for x in LATEST["hits"] if isinstance(x, dict)]
    if not hits:
        print(f"{Y}  Brak aktywnych sygnalow (TRIGGER / GOTOWY) w tym cyklu.{W}")
    else:
        tiers = [("🔥 GRUPA A: WYSOKA SZANSA NA ZYSK (>= 75%)", G, [x for x in hits if x.get("win_prob", 0) >= 75]), ("✅ GRUPA B: SOLIDNA SZANSA (60% - 74%)", C, [x for x in hits if 60 <= x.get("win_prob", 0) < 75]), ("⚠️ GRUPA C: PODWYZSZONE RYZYKO (< 60%)", Y, [x for x in hits if x.get("win_prob", 0) < 60])]
        for t, col, grp in tiers:
            if grp: draw_box(t, col, grp)
    if not LATEST["near"]:
        print(f"{C}  Brak monet w strefie obserwacji (<= 1.5 ATR).{W}")
    else:
        cols = max(48, shutil.get_terminal_size((52, 24)).columns)
        av = max(30, cols - 1 - 17); ws = 6 + max(0, (av - 30)//4); wp = 8 + max(0, (av - 30)//4); wm = av - ws - wp
        inn = ws + 15 + wp + wm
        hdr = f"─ OBSERWOWANE / W POBLIZU ({len(LATEST['near'])}) "
        print(f"\n{C}{B}┌{hdr}{'─'*max(1, inn-len(hdr))}┐{W}")
        print(f"{C}│{W}{'MONETA':<{ws}}{C}│{W}{'KIER':<5}{C}│{W}{'CENA':>{wp}}{C}│{W}{'DYST':>6}{C}│{W}{'ETA / INFO':<{wm}}{C}│{W}")
        print(f"{C}├{'─'*ws}┼─────┼{'─'*wp}┼──────┼{'─'*wm}┤{W}")
        for n in LATEST["near"]:
            sym = n["symbol"].replace("USDT", "")[:ws]; kc = G if n["side"] == "LONG" else R
            info = f"{n['eta_str']} {n['missing']}"
            print(f"{C}│{W}{B}{sym:<{ws}}{W}{C}│{W}{kc}{n['side']:<5}{W}{C}│{W}{fmt_p(n['price']).strip()[:wp]:>{wp}}{C}│{W}{n['dist_atr']:+5.2f}A{C}│{W}{Y}{info[:wm-1]:<{wm}}{W}{C}│{W}")
        print(f"{C}└{'─'*ws}┴─────┴{'─'*wp}┴──────┴{'─'*wm}┘{W}")

def auto_live_loop():
    """Realizuje logike: auto live loop."""
    while True:
        time.sleep(5)
        if LIVE_ACTIVE and not PROG["running"]:
            run_full_scan(show_term=False)
            for _ in range(WATCH_EVERY // 5):
                if not LIVE_ACTIVE: break
                time.sleep(5)

def fast_loop():
    """Realizuje logike: fast loop."""
    while True:
        time.sleep(30)
        try: pf.check_positions_guardian(); ds24.update_demo_24h(); ds24.update_demo_pro_24h(); ds24.hourly_demo_pulse()
        except Exception: pass
        if not watched_far: continue
        for k in list(watched_far.keys()):
            info = watched_far[k]
            _, _, pmap = get_market_meta(info["ex"], 100)
            cp = pmap.get(info["sym"], 0)
            if cp > 0 and abs(info["entry"] - cp)/cp * 100.0 <= info["max_dev"]:
                del watched_far[k]
                send_telegram(f"✅ <b>W ZASIEGU GIELDY! | {info['sym']} ({info['ex']})</b>\nCena w limicie — mozna skladac zlecenie!")

def main():
    """Realizuje logike: main."""
    mode = sys.argv.__getitem__(1) if len(sys.argv) > 1 else ""
    # Uruchamiamy w tle JEDNOCZESNIE: Bot Telegram, Szybki tracker DALEKO oraz Serwer WWW (Chrome)
    threading.Thread(target=tg_listener, daemon=True).start()
    threading.Thread(target=fast_loop, daemon=True).start()
    threading.Thread(target=auto_live_loop, daemon=True).start()
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=5000, threaded=True, debug=False), daemon=True).start()

    if mode == "web":
        os.system("termux-open-url http://127.0.0.1:5000")
        while True: time.sleep(60)
    elif mode == "live":
        while True: run_full_scan(show_term=True); draw_term(); time.sleep(WATCH_EVERY)

    while True:
        s = load_settings()
        print(f"\n{C}{B}=== CRYPTO PRO | {s['exchange']} | TOP {s['top_n']} | {s['capital']}$ ==={W}")
        print(f"{G}[AKTYWNE: TG Bot + Chrome :5000 | Auto-Live: {'✅ ON' if LIVE_ACTIVE else 'OFF'}]{W}")
        print("1. Skanuj TERAZ (Tabelka)    | 2. Tryb Live (Auto 5m + Tabelka + TG + CSV)")
        print("3. Otworz Chrome na ekranie  | 4. Zmien Gielde (Binance/Bybit/Bitget/WEEX/BitBase)")
        print("5. TEST DEMO (Wszystkie)     | 6. Wykresy SMC + Analiza")
        print("7. Zmien ilosc monet (TOP N) | 8. Planner | 9. Portfel & Margin | 10. Backtest 2020-26 | 0. Wyjscie")
        try:
            ch = input(f"{B}Wybor (0-7): {W}").strip()
        except EOFError:
            while True: time.sleep(3600)
        if ch == "1": run_full_scan(show_term=True); draw_term()
        elif ch == "2":
            try:
                while True: run_full_scan(show_term=True); draw_term(); time.sleep(WATCH_EVERY)
            except KeyboardInterrupt: pass
        elif ch == "3":
            os.system("termux-open-url http://127.0.0.1:5000")
        elif ch == "4":
            c = load_settings()
            cur = str(c.get("exchange", "BINANCE")).upper()
            idx = (EXCHANGES.index(cur) + 1) % len(EXCHANGES) if cur in EXCHANGES else 0
            c["exchange"] = EXCHANGES.__getitem__(idx)
            tiers, mx = get_dynamic_top_tiers(c["exchange"])
            save_settings(c)
            print(f"{G}{B}>>> Zmieniono gielde na: {c['exchange']} (Dostepne pary: {mx}) <<<{W}")
        elif ch == "5":
            sub_d = input("Symulacja 24H (1000$): 1 = Pokaz wynik, 2 = Start NOWEJ symulacji: ").strip()
            if sub_d == "2": ds24.start_demo_24h()
            rep = ds24.get_demo_report()
            if not rep: print(f"{Y}Brak aktywnej symulacji. Wybierz 2.{W}")
            else:
                print(f"\n{B}=== SYMULACJA 24H ({rep['exchange']} | Zostalo: {rep['rem_h']}h) ==={W}")
                print(f"Saldo: {G if rep['total_pnl']>=0 else R}{rep['equity']:.2f}$ ({rep['total_pnl']:+.2f}$ / {rep['pnl_pct']:+.2f}%){W} | Win Rate: {C}{rep['win_rate']}%{W}")
                for p in rep["positions"]:
                    print(f"  {B}{p['symbol']:<10}{W} {p['side']:<5} | {p['close_reason'] if p['closed'] else ('Aktywna' if p['entered'] else 'Czeka'):<16} | PnL: {p['realized_pnl']:+.2f}$")
        elif ch == "6":
            while True:
                opts = cm.get_chart_opts(); ex = load_settings()["exchange"]
                cands = [x["symbol"] for x in LATEST["hits"]] + [x["symbol"] for x in LATEST["near"]]
                print(f"\n{C}{B}=== WYKRESY I ANALIZA SMC ({ex}) ==={W}")
                print(f"Panele: 1.EMA[{'X' if opts.get('ema') else ' '}] 2.SMC/POC[{'X' if opts.get('smc') else ' '}] 3.TP/SL[{'X' if opts.get('levels') else ' '}] 4.Vol[{'X' if opts.get('vol') else ' '}] 5.Hurst[{'X' if opts.get('hurst') else ' '}] 6.RSI[{'X' if opts.get('rsi') else ' '}] 7.MACD[{'X' if opts.get('macd') else ' '}] 8.CHOP[{'X' if opts.get('chop') else ' '}] 9.WSZYSTKIE")
                if cands: print(f"Proponowane: {G}{', '.join(cands)}{W}")
                v = input("Symbol (np. BTCUSDT), 1-9 (panel) lub 0 (powrot): ").strip().upper()
                if v == "0": break
                elif v in ("1","2","3","4","5","6","7","8","9"): cm.toggle_chart_opt({"1":"ema","2":"smc","3":"levels","4":"vol","5":"hurst","6":"rsi","7":"macd","8":"chop","9":"all"}[v])
                elif v:
                    sym = v if v.endswith("USDT") else v + "USDT"
                    buf, ta = cm.build_chart_buf(ex, sym)
                    if not ta: print(f"{R}Brak danych.{W}"); continue
                    print(f"\n{G}{B}--- ANALIZA {sym} ({ex}) ---{W}\nSMC: {ta['smc']['struct']} | {ta['smc']['fvg']} | RSI:{ta['rsi']} | CHOP:{ta['chop']} | Hurst:{ta['hurst']}% | ETA:{ta['eta']}")
                    if buf and os.path.exists(TG_CONFIG_FILE):
                        cfg_t = json.load(open(TG_CONFIG_FILE))
                        if cfg_t.get("token") and cfg_t.get("chat_id"):
                            requests.post(tg_url(cfg_t["token"], "sendPhoto"), data={"chat_id": cfg_t["chat_id"], "caption": f"📈 <b>{sym} ({ex})</b>\n{ta['summary']}", "parse_mode": "HTML"}, files={"photo": ("c.png", buf, "image/png")})
                            print(f"{G}Wyslano wykres TradingView Pro na Telegram!{W}")
        elif ch == "7":
            c = load_settings()
            mode_l = input("Wybierz grupe (1 = Tylko plynne >5M$, 2 = Wszystkie bez ograniczen, Enter = bez zmian): ").strip()
            if mode_l in ("1", "2"):
                c["liq_only"] = (mode_l == "1"); save_settings(c)
            tiers_t, mx_t = get_dynamic_top_tiers(load_settings()["exchange"]); nv = input(f"Podaj liczbe monet {tiers_t} lub wpisz MAX ({mx_t}): ").strip().upper()
            if nv == "MAX": nv = str(mx_t)
            if nv.isdigit() and int(nv) >= 5:
                c = load_settings(); c["top_n"] = int(nv); save_settings(c)
                print(f"{G}Ustawiono TOP {nv} monet!{W}")
        elif ch == "8":
            cfg_p = load_settings(); ex = cfg_p["exchange"]
            sym = input("Podaj monete (np. BTCUSDT): ").strip().upper() or "BTCUSDT"
            if not sym.endswith("USDT"): sym += "USDT"
            cap = float(input(f"Kapital [{cfg_p['capital']}$]: ").strip() or cfg_p["capital"])
            rpct = float(input(f"Ryzyko % [{cfg_p['risk_pct']}%]: ").strip() or cfg_p["risk_pct"])
            mlev = int(input("Max dzwignia [20x]: ").strip() or 20)
            p = pm.calc_plan(ex, sym, cap, rpct, mlev)
            if p:
                st = f"{G}PASS{W}" if p["passed"] else f"{R}FAIL (Min kap: {p['min_cap']}$){W}"
                print(f"\n{B}=== PLANNER {sym} ({ex}) [{st}{B}] ==={W}")
                print(f"Ilosc: {C}{p['qty']}{W} | Wartosc: {p['notional']}$ | 💡 Sugerowana Dzwignia: {G}{B}{p['rec_lev']}x{W} (Max bezpieczna: {p['safe_ceil']}x) | Margin: {p['rec_margin']}$ | Liq: {R}{fmt_p(p['liq_price']).strip()}{W}")
                print(f"Wej: {fmt_p(p['entry']).strip()} | SL: {fmt_p(p['stop']).strip()} | 1R: {fmt_p(p['tp'].__getitem__(0)).strip()} | 3R: {fmt_p(p['tp'].__getitem__(2)).strip()}")
                for ok, txt in p["checks"]: print(f"  {G+'OK' if ok else R+'BLAD'}{W}: {txt}")
                os.system(f'termux-clipboard-set "{fmt_p(p["entry"]).strip()}" >/dev/null 2>&1')
                print(f"{G}Skopiowano cene wejscia do schowka!{W}")
        elif ch == "9":
            while True:
                sm = pf.get_portfolio_summary()
                print(f"\n{C}{B}=== PORTFEL I KONTROLA MARGINU ==={W}")
                print(f"Kapital ogolny: {G}{sm['capital']}${W} | Zablokowany Margin: {Y}{sm['used_margin']}${W} ({sm['margin_pct']}%) | Wolny limit: {G}{sm['free_margin']}${W} | Ryzyko: {sm['active_risk']}$ ({sm['risk_pct']}%)")
                print(f"Status: {sm['status']}")
                for idx, p in enumerate(sm["positions"]):
                    tps_s = " ".join(f"{i+1}R:{'✅' if h else '⬜'}" for i, h in enumerate(p["hit_tps"]))
                    print(f"  [{idx+1}] {B}{p['symbol']}{W} ({p['side']} {p['lev']}x) | Margin:{p['margin']}$ | {tps_s}")
                cmd = input("Wpisz: +MONETA (dodaj), K <kwota> (zmien kapital), T <nr_poz> <1-5> (odznacz TP), D <nr_poz> (zamknij), 0 (powrot): ").strip().upper()
                if cmd == "0": break
                elif cmd.startswith("K "):
                    c = load_settings(); c["capital"] = float(cmd.split().__getitem__(1)); save_settings(c)
                elif cmd.startswith("+"):
                    asym = cmd.replace("+", "").strip()
                    if not asym.endswith("USDT"): asym += "USDT"
                    ex_a = "BITGET"
                    cfg_a = load_settings()
                    p = pm.calc_plan(ex_a, asym, cfg_a["capital"], cfg_a["risk_pct"], 20)
                    if p: pf.add_position(ex_a, asym, p["side"], p["entry"], p["stop"], p["tp"], p["qty"], p["rec_margin"], p["risk_usdt"], p["rec_lev"])
                elif cmd.startswith("T ") and len(cmd.split()) == 3:
                    _, pi, ti = cmd.split()
                    lst = pf.load_positions()
                    if 1 <= int(pi) <= len(lst): pf.toggle_tp_hit(lst.__getitem__(int(pi)-1)["id"], int(ti)-1)
                elif cmd.startswith("D ") and len(cmd.split()) == 2:
                    pi = int(cmd.split().__getitem__(1))
                    lst = pf.load_positions()
                    if 1 <= pi <= len(lst): pf.close_position(lst.__getitem__(pi-1)["id"])
        elif ch == "10":
            bsym = input("Wpisz monete (np. BTCUSDT) lub M10 (Portfel TOP 10) / M20 (Portfel TOP 20): ").strip().upper() or "M10"
            print(f"{C}Licze Backtest 2020-2026 dla {bsym}...{W}")
            t20 = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","TRXUSDT","MATICUSDT","LTCUSDT","BCHUSDT","ATOMUSDT","UNIUSDT","NEARUSDT","APTUSDT","FILUSDT","INJUSDT"]
            res = bt20.run_multi_backtest_2020(t20.__getitem__(slice(0, 10)), 2020, 1000.0) if bsym=="M10" else (bt20.run_multi_backtest_2020(t20, 2020, 1000.0) if bsym=="M20" else bt20.run_backtest_2020(bsym, 2020, 1000.0, 1.0))
            if not res: print(f"{R}Brak danych dla {bsym}.{W}")
            else:
                print(f"\n{B}=== BACKTEST {res['symbol']} ({res['date_from']} -> {res['date_to']}) ==={W}")
                print(f"Kapital: 1000.00$ -> {G if res['final_cap']>=1000 else R}{res['final_cap']:.2f}$ ({res['net_pct']:+.1f}%){W} | Win Rate: {C}{res['win_rate']}%{W} | Srednio: {res['avg_month']:+.2f}$/mies.")
                for y, v in sorted(res["yearly"].items()): print(f"  Rok {y}: {v:+.2f}$")
        elif ch == "0": sys.exit(0)



def _append_lab_sample(lab_file, src_tag, sym, side, prob, pd_tag, en_v, sl_v):
    """Realizuje logike: append lab sample. Parametry: lab_file, src_tag, sym, side, prob, pd_tag, en_v, sl_v."""
    try:
        arr = json.load(open(lab_file)) if os.path.exists(lab_file) else []
        now_dt = datetime.now()
        sd_v = abs(en_v - sl_v) or (en_v * 0.01)
        td_v = 1 if side == "LONG" else -1
        arr.append({
            "ts": now_dt.strftime("%d.%m %H:%M"), "ts_epoch": int(time.time()), "hour": now_dt.hour,
            "data_type": "LIVE_FORWARD", "src": src_tag, "sym": sym, "side": side,
            "prob": prob, "pump_dump_tag": pd_tag or "NORMAL",
            "sl_dist_pct": round((sd_v / max(1e-9, en_v)) * 100.0, 2),
            "en_f": en_v, "sl_f": sl_v,
            "tp1_f": round(en_v + td_v * sd_v * 1.0, 6),
            "tp2_f": round(en_v + td_v * sd_v * 1.5, 6),
            "tp3_f": round(en_v + td_v * sd_v * 2.5, 6),
            "status": "OPEN", "res_r": 0.0, "dur_str": "0m", "mfe_r": 0.0, "closed_final": False
        })
        json.dump(arr[-200:], open(lab_file, "w"), indent=2)
    except Exception:
        pass

def run_wild_market_probe():
    """Realizuje logike: run wild market probe."""
    wd.beat('market_labs_30m', 'Start sondy Wild/Micro')
    for sym in apm.get_wild_61_160_symbols()[:25]:
        tag = apm.detect_weird_move("BITGET", sym)
        if tag:
            kl = fetch_klines("BITGET", sym, "15m", 20)
            if kl:
                c = float(kl["c"][-1])
                side = "SHORT" if "LONG_WICK_HUNT" in tag else "LONG"
                sl = round(c * (1.018 if side == "SHORT" else 0.982), 6)
                _append_lab_sample(WILD_LAB_FILE, "WILD_61_160", sym, side, 56, tag, c, sl)

def run_micro_market_probe():
    """Realizuje logike: run micro market probe."""
    for sym in apm.get_micro_161_plus_symbols()[:25]:
        cyc_t, _, pd_t = apm.detect_cyclical_and_pump_dump("BITGET", sym)
        if pd_t or cyc_t.startswith("CYCLIC_"):
            kl = fetch_klines("BITGET", sym, "15m", 20)
            if kl:
                c = float(kl["c"][-1])
                side = "SHORT" if "PUMP_DUMP" in pd_t else "LONG"
                sl = round(c * (1.02 if side == "SHORT" else 0.98), 6)
                _append_lab_sample(MICRO_LAB_FILE, "MICRO_161_PLUS", sym, side, 56, pd_t or cyc_t, c, sl)

def run_bg_macro_pump_dump():
    """Realizuje logike: run bg macro pump dump."""
    elm.run_evolution_tournament()
    mbm.learn_from_closed_history()
    wd.beat('macro_pump_dump_30m', 'Skan 140 par P&D + Ewolucja')
    syms = apm.get_all_futures_symbols()[:140]
    with ThreadPoolExecutor(max_workers=12) as pool:
        for res in pool.map(apm.scan_macro_pump_dump_coin, syms):
            if res and time.time() - SEEN_CFD_SIGS.get(f"PD_{res['symbol']}", 0) >= 14400:
                SEEN_CFD_SIGS[f"PD_{res['symbol']}"] = time.time()
                send_telegram(f"{res['mode']} — <b>{res['symbol']} ({res['side']})</b>\n🎯 Szansa: <b>{res['win_prob']}%</b> | 🧬 <i>{res['alpha_tag']}</i>\n💵 Cena: <code>{res['price']}</code> | 🛑 SL: <code>{res['stop']}</code>")

def cfd_live_bg_loop():
    """Realizuje logike: cfd live bg loop."""
    import re
    cycle_cnt = 0
    while True:
        try:
            if CFD_LIVE_ACTIVE and time.time() >= CFD_SNOOZE_UNTIL:
                top_cfd = apm.get_cfd_top60_symbols()
                btc_d, btc_lbl = get_live_btc_regime() if "get_live_btc_regime" in globals() else (0, "NEUTRALNY")
                new_hits = []
                now_t = time.time()
                audit_cfd_history_1m()
                t_cfg, tune_msg = atm.run_auto_tuner(CFD_HIST_FILE)
                if tune_msg:
                    tc_t = json.load(open(TG_CONFIG_FILE)) if os.path.exists(TG_CONFIG_FILE) else {}
                    if tc_t.get("token") and tc_t.get("chat_id"):
                        requests.post(tg_url(tc_t["token"].strip(), "sendMessage"), json={"chat_id": tc_t["chat_id"].strip(), "text": f"🧠 <b>AUTO-TUNER CFD:</b>\n{tune_msg}", "parse_mode": "HTML"}, timeout=15)
                min_p_l, sl_m_l = t_cfg.get("min_prob", 64), t_cfg.get("sl_mult", 1.0)
                def _live_w(sym_l):
                    try:
                        h = _scan_one_coin(("BITGET", sym_l, 1.0, load_settings().get("rules", {}), load_settings().get("enabled", ["15m", "1h", "4h", "1d"]), 1000.0, 1.5))
                        if h and isinstance(h, dict):
                            if sl_m_l != 1.0:
                                td_l = 1 if h["side"] == "LONG" else -1
                                h["stop"] = round(h["entry"] - td_l * abs(h["entry"] - h["stop"]) * sl_m_l, 6)
                            ok_ob, ob_b, ob_tag = iom.get_orderflow_and_walls(h["symbol"], h["side"], h["entry"], h["tp"].__getitem__(0))
                            sl_k = (abs(h["entry"] - h["stop"]) / max(1e-9, h["entry"])) * 100.0
                            ok_k, kb, kt = aqm.evaluate_knn_pattern(h["side"], h.get("win_prob", 55), 25, sl_k, datetime.now().hour)
                            ld, lt = aqm.get_lead_lag_impulse(sys.modules[__name__], h["symbol"])
                            lb = 5 if ((h["side"] == "LONG" and ld == 1) or (h["side"] == "SHORT" and ld == -1)) else 0
                            kl_q = fetch_klines("BITGET", h["symbol"], "15m", 35)
                            reg_k, reg_b, reg_tag = elm.detect_volatility_regime(kl_q)
                            ent_v, ok_ent, ent_tag = fqm.calc_shannon_entropy(kl_q)
                            ent_b = 4 if ent_v < 0.68 else (-5 if not ok_ent else 0)
                            ok_rt, rt_b, rt_tag = fqm.detect_whale_iceberg_and_redteam(h["side"], kl_q)
                            qw_b, qw_tag = qnm.quantum_wave_interference(h["side"], h["entry"], h["tp"].__getitem__(0), h["stop"], kl_q)
                            ok_nash, nash_b, nash_tag = qnm.detect_nash_predator_trap(h["side"], kl_q)
                            bn_b, bn_tag = qep.check_binance_futures_lead(h["symbol"], h["side"], h["price"])
                            sl_fp, fp_b, fp_tag = qep.profile_coin_fingerprint(kl_q)
                            ok_tail, soc_b, tail_tag = qep.check_extreme_tail_and_social(h["symbol"], kl_q, [])
                            if sl_fp != 1.0: h["stop"] = round(h["entry"] - (h["entry"] - h["stop"]) * sl_fp, 6)
                            ai_pts = mbm.apply_brain_weights(ob_b, kb, lb, reg_b, rt_b, qw_b) + nash_b + bn_b + fp_b + soc_b + ent_b
                            h["win_prob"] = max(45, min(96, int(h.get("win_prob", 55)) + ai_pts))
                            extra_tags = [x for x in (ob_tag, kt, lt if lb else "", reg_tag, ent_tag, rt_tag, qw_tag, nash_tag, fp_tag, bn_tag if bn_b else "") if x]
                            h["alpha_tag"] = " | ".join(([h["alpha_tag"]] if h.get("alpha_tag") else []) + extra_tags)
                            if not (ok_ob and ok_k and reg_k != "CHOP" and ok_rt and ok_nash):
                                why_rej = "+".join([nm for flg, nm in ((ok_ob, "OB_WALL"), (ok_k, "KNN"), (reg_k != "CHOP", "CHOP_SHIELD"), (ok_rt, "RED_TEAM"), (ok_nash, "NASH_TRAP"), (ok_tail, "TAIL_LOCK")) if not flg]) or "SNIPER_FILTER"
                                nzt.record_rejected_hypothesis(h["symbol"], h["side"], h["entry"], h["stop"], why_rej)
                                for flg, nm in ((ok_ob, "OB_WALL"), (ok_k, "KNN"), (reg_k != "CHOP", "CHOP_SHIELD"), (ok_rt, "RED_TEAM"), (ok_nash, "NASH_TRAP")):
                                    if not flg: r24.record_funnel_drop(nm)
                            if ok_ob and ok_k and reg_k != "CHOP" and ok_rt and ok_nash and ok_tail and h["symbol"] not in sam.get_bitbase_blacklist() and sdm.check_sniper_quality(h["side"], btc_d, fetch_klines("BITGET", h["symbol"], "15m", 5))[0] and apm.validate_cfd_order(h["entry"], h["stop"], h["price"]) and h.get("win_prob", 0) >= 45:
                                return h
                    except Exception: pass
                    return None
                with ThreadPoolExecutor(max_workers=12) as l_pool:
                    for h in l_pool.map(_live_w, top_cfd):
                        if h and now_t - SEEN_CFD_SIGS.get(f"{h['symbol']}_{h['side']}", 0) >= 7200:
                            SEEN_CFD_SIGS[f"{h['symbol']}_{h['side']}"] = now_t
                            new_hits.append(h)
                shadow_hits = [x for x in new_hits if x.get("win_prob", 0) < min_p_l]
                for sh in shadow_hits[:4]:
                    _append_lab_sample(SHADOW_LAB_FILE, f"SHADOW_T{sh.get('win_prob',50)}", sh["symbol"], sh["side"], sh.get("win_prob", 50), sh.get("alpha_tag", "SNIPER"), sh["entry"], sh["stop"])
                audit_cfd_history_1m(SHADOW_LAB_FILE)
                new_hits = [x for x in new_hits if x.get("win_prob", 0) >= min_p_l]
                last_alert_ts = SEEN_CFD_SIGS.get("__LAST_ANY_ALERT__", 0)
                if not new_hits and (time.time() - last_alert_ts) >= 21600:
                    silver_cands = [x for x in shadow_hits if x.get("win_prob", 0) >= 53]
                    if silver_cands:
                        silver_cands.sort(key=lambda x: -x.get("win_prob", 0))
                        best_s = dict(silver_cands[0])
                        best_s["alpha_tag"] = "🥈 ANTY-PRZESTÓJ (SILVER 0.5x STAWKI) | " + best_s.get("alpha_tag", "")
                        new_hits = [best_s]
                if new_hits:
                    SEEN_CFD_SIGS["__LAST_ANY_ALERT__"] = time.time()
                if new_hits:
                    new_hits.sort(key=lambda x: -x.get("win_prob", 0))
                    top3_live = new_hits.__getitem__(slice(0, 2))
                    log_cfd_hits_to_file(top3_live, "LIVE")
                    LATEST["hits"] = top3_live
                    LATEST["ts"] = datetime.now().strftime("%H:%M:%S (LIVE CFD)")
                    tc_l = json.load(open(TG_CONFIG_FILE)) if os.path.exists(TG_CONFIG_FILE) else {}
                    tok_l, cid_l = tc_l.get("token", "").strip(), tc_l.get("chat_id", "").strip()
                    if tok_l and cid_l:
                        btc_c = str(btc_lbl).replace("<", "&lt;").replace(">", "&gt;")
                        requests.post(tg_url(tok_l, "sendMessage"), json={"chat_id": cid_l, "text": f"⠀⠀🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n✅ <b>SĄ AKTYWNE OKAZJE!</b> ✅\n⠀⠀🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n🚨 <b>AUTO-ALERT CFD LIVE (15m)</b> | {btc_c}\nZnaleziono <b>{len(top3_live)}</b> swieze okazje:", "parse_mode": "HTML"}, timeout=15)
                        for h in top3_live:
                            tps_l = h.get("tp", [])
                            tp1_l = tps_l.__getitem__(0) if len(tps_l) > 0 else h["entry"]
                            tp2_l = tps_l.__getitem__(1) if len(tps_l) > 1 else h["entry"]
                            card_l = (
                                f"⚡ <b>{h['symbol']}</b> — <b>{h['side']}</b> (LIVE)\n"
                                f"🎯 Szansa kontynuacji: <b>{h.get('win_prob', 75)}%</b> | 🧬 <i>{h.get('alpha_tag', 'FR OK')}</i>\n"
                                f"💵 Cena: <code>{h.get('price', h['entry'])}</code> | 🎯 Wejscie: <code>{h['entry']}</code>\n"
                                f"🛑 SL: <code>{h['stop']}</code> | ✅ TP1: <code>{tp1_l}</code> | 💰 TP2: <code>{tp2_l}</code>\n"
                                f"{apm.get_mtf_status_line('BITGET', h['symbol'], h['side'])}\n{pf.check_new_opportunity_margin(h['side'])}"
                            )
                            kb_l = {"inline_keyboard": [[{"text": f"🧮 Plan ({h['symbol']})", "callback_data": f"plan_{h['symbol']}"}, {"text": "➕ Obstawiam", "callback_data": f"addp_{h['symbol']}"}, {"text": "📈 Wykres", "callback_data": f"ch_{h['symbol']}"}, {"text": "🛡️ Audyt", "callback_data": f"aud_{h['symbol']}"}, {"text": "🚫 Brak BitBase", "callback_data": f"bbl_{h['symbol']}"}]]}
                            requests.post(tg_url(tok_l, "sendMessage"), json={"chat_id": cid_l, "text": card_l, "parse_mode": "HTML", "reply_markup": kb_l}, timeout=15)
                else:
                    # Co 2 cykle (co 30 min) wysylamy cichy Puls Zycia, zeby bylo wiadomo ze radar CFD pracuje
                    if cycle_cnt % 2 == 0:
                        try:
                            if os.path.exists("qa_health_history.json"):
                                unres = [x for x in json.load(open("qa_health_history.json", encoding="utf-8")) if x.get("status") == "UNRESOLVED"]
                                if unres and tok_l and cid_l:
                                    lu = unres[-1]
                                    requests.post(tg_url(tok_l, "sendMessage"), json={"chat_id": cid_l, "text": f"⚠️ <b>PRZYPOMNIENIE QA:</b> Nienaprawiony błąd z <code>{lu.get('ts')}</code> (<code>{lu.get('location')}</code>): <code>{str(lu.get('error'))[:160]}</code>", "parse_mode": "HTML"}, timeout=10)
                        except Exception: pass
                        run_wild_market_probe()
                        audit_cfd_history_1m(WILD_LAB_FILE)
                        run_micro_market_probe()
                        audit_cfd_history_1m(MICRO_LAB_FILE)
                        run_bg_macro_pump_dump()
                        btc_c = str(btc_lbl).replace("<", "&lt;").replace(">", "&gt;")
                        tc_h = json.load(open(TG_CONFIG_FILE)) if os.path.exists(TG_CONFIG_FILE) else {}
                        tok_h, cid_h = tc_h.get("token", "").strip(), tc_h.get("chat_id", "").strip()
                        if tok_h and cid_h:
                            tp_now = atm.get_tuner_params()
                            tuner_line = f"\n{r24.get_24h_countdown_line()}\n{nzt.get_nzt_status_line(sys.modules[__name__])}\n{mbm.get_brain_summary_line()}\n🧠 <b>Auto-Tuner (Skan 45-100% | Alerty ≥{tp_now.get('min_prob', 58)}%):</b>\n📊 Poziomy: <code>{atm.get_all_tiers_summary()}</code>"
                            requests.post(tg_url(tok_h, "sendMessage"), json={"chat_id": cid_h, "text": f"⠀⠀🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n⛔ <b>BRAK AKTYWNYCH SYGNAŁÓW</b> ⛔\n⠀⠀🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n💓 <b>Puls CFD Live ({datetime.now().strftime('%H:%M')}):</b> Przeskanowano <b>{len(top_cfd)}</b> par | {btc_c} | Brak nowych okazji.{tuner_line}", "parse_mode": "HTML", "disable_notification": True}, timeout=15)
                cycle_cnt += 1
        except Exception as err:
            print("CFD_LIVE_ERR:", err)
        wd.beat('cfd_live_scanner', f'Przeskanowano {len(top_cfd)} par')
        healed, crit = wd.check_and_heal_modules()
        if healed:
            send_telegram('🛠️ <b>AUTO-HEALING WATCHDOG:</b>\n' + '\n'.join(healed))
        if crit:
            send_telegram('🚨 <b>WATCHDOG KRYTYCZNY:</b>\n' + '\n'.join(crit) + '\n<i>Przeslij caly_projekt.txt do AI!</i>')
        time.sleep(900)




ACTIVE_TP_ALERTS = set()

def fast_active_positions_loop():
    """Realizuje logike: fast active positions loop."""
    while True:
        try:
            sm = pf.get_portfolio_summary()
            pos_list = sm.get("positions", [])
            if pos_list:
                tc_g = json.load(open(TG_CONFIG_FILE)) if os.path.exists(TG_CONFIG_FILE) else {}
                tok_g, cid_g = tc_g.get("token", "").strip(), tc_g.get("chat_id", "").strip()
                for p in pos_list:
                    pid = str(p.get("id", ""))
                    sym = p.get("symbol", "")
                    side = p.get("side", "LONG")
                    entry = float(p.get("entry", 0) or 0)
                    stop = float(p.get("stop", 0) or 0)
                    tps = p.get("tp", [])
                    hit_tps = p.get("hit_tps", [False]*5)
                    if not sym or entry <= 0 or not tps: continue
                    kl = fetch_klines("BITGET", sym, "15m", 3)
                    if not kl: continue
                    cur = float(kl["c"].__getitem__(-1))
                    td = 1 if side == "LONG" else -1
                    # 1. Sprawdzanie kolejnych progow TP1 .. TP5 co 60 sekund
                    for idx_tp, tp_val in enumerate(tps.__getitem__(slice(0, 5))):
                        tp_f = float(tp_val or 0)
                        if tp_f <= 0: continue
                        if idx_tp < len(hit_tps) and hit_tps.__getitem__(idx_tp): continue
                        reached = (cur >= tp_f) if td == 1 else (cur <= tp_f)
                        al_key = f"{pid}_TP{idx_tp+1}"
                        if reached and al_key not in ACTIVE_TP_ALERTS:
                            ACTIVE_TP_ALERTS.add(al_key)
                            r_labels = ["1.0R", "1.5R (Break-Even!)", "2.5R", "3.5R", "5.0R"]
                            rl = r_labels.__getitem__(idx_tp)
                            msg_tp = (
                                f"🎯 <b>OSIAGNIETO TP{idx_tp+1} ({rl}) — {sym} ({side})!</b>\n"
                                f"💵 Aktualna cena: <code>{fmt_p(cur).strip()}</code> | Cel TP{idx_tp+1}: <code>{fmt_p(tp_f).strip()}</code>\n"
                                f"🛡️ <i>Jesli zlecenie na gieldzie nie zamknelo czesci pozycji (np. blad zera po przecinku), zrealizuj zysk recznie i przesun SL na Break-Even!</i>"
                            )
                            if tok_g and cid_g:
                                kb_tp = {"inline_keyboard": [[{"text": f"✅ Oznacz TP{idx_tp+1} w Portfelu", "callback_data": f"tp_{pid}_{idx_tp}"}, {"text": "💼 Portfel CFD", "callback_data": "tg_pf"}]]}
                                requests.post(tg_url(tok_g, "sendMessage"), json={"chat_id": cid_g, "text": msg_tp, "parse_mode": "HTML", "reply_markup": kb_tp}, timeout=15)
                    # 2. Ostrzezenie gdy cena zbliza sie na <= 20% dystansu do Stop Lossa
                    sl_dist = abs(entry - stop)
                    rem_sl = (cur - stop) if td == 1 else (stop - cur)
                    sl_key = f"{pid}_SLWARN"
                    if sl_dist > 0 and 0 < rem_sl <= sl_dist * 0.20 and sl_key not in ACTIVE_TP_ALERTS:
                        ACTIVE_TP_ALERTS.add(sl_key)
                        if tok_g and cid_g:
                            requests.post(tg_url(tok_g, "sendMessage"), json={"chat_id": cid_g, "text": f"🚨 <b>UWAGA SL — {sym} ({side})!</b>\nCena (<code>{fmt_p(cur).strip()}</code>) zblizyla sie na 20% do Stop Lossa (<code>{fmt_p(stop).strip()}</code>). Sprawdz czy SL na gieldzie jest poprawnie wpisany!", "parse_mode": "HTML"}, timeout=15)
        except Exception as err:
            print("FAST_GUARDIAN_ERR:", err)
        wd.beat('fast_guardian_60s', f'Pozycje: {len(pos_list) if pos_list else 0}')
        time.sleep(60)





def build_ai_context_bundle():
    """Sklada caly aktualny projekt w plik caly_projekt.txt."""
    import glob, subprocess
    out_paths = ["caly_projekt.txt", "/storage/emulated/0/Download/caly_projekt.txt"]
    files = sorted(glob.glob("*.py") + glob.glob("*.md")) + [
        "market_shadow_lab.json", "wild_market_lab.json",
        "micro_market_lab.json", "tuner_state.json", "qa_health_history.json"
    ]
    parts = []
    for fn in files:
        if os.path.exists(fn):
            try:
                content = open(fn, "r", encoding="utf-8", errors="ignore").read()
                parts.append(f"==> {fn} <==\n{content}")
            except Exception:
                pass
    full_txt = "\n\n".join(parts)
    for op in out_paths:
        try:
            with open(op, "w", encoding="utf-8") as out_f:
                out_f.write(full_txt)
        except Exception:
            pass
    try:
        subprocess.run(["termux-media-scan", "/storage/emulated/0/Download/caly_projekt.txt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def github_auto_sync_loop():
    """Realizuje logike: github auto sync loop."""
    import subprocess, py_compile, glob
    while True:
        wd.beat('github_sync_5m', 'Cykl kontrolny 5m')
        r24.check_and_build_24h_report(sys.modules[__name__])
        time.sleep(300)
        try:
            st_out = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
            if st_out:
                for f in glob.glob("*.py"):
                    py_compile.compile(f, doraise=True)
                build_ai_context_bundle()
                subprocess.run(["git", "add", "-f", "*.py", "*.md", ".gitignore"], check=False)
                subprocess.run(["git", "commit", "-m", f"Live-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                r_p = subprocess.run(["git", "push", "origin", "main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if r_p.returncode == 0:
                    ts_u = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    msg_u = f"\n☁️ [GitHub Sync] Ostatni update wyslany: {ts_u}\n"
                    print(msg_u.strip(), flush=True)
                    try:
                        with open("/dev/tty", "w") as tty: tty.write(msg_u)
                    except Exception: pass
        except Exception:
            pass


def daily_healthcheck_loop():
    """Realizuje logike: daily healthcheck loop."""
    import self_test
    while True:
        time.sleep(86400)
        try:
            res_msg = self_test.run_full_self_test()
            tc_h = json.load(open(TG_CONFIG_FILE)) if os.path.exists(TG_CONFIG_FILE) else {}
            if tc_h.get("token") and tc_h.get("chat_id"):
                requests.post(tg_url(tc_h["token"].strip(), "sendMessage"), json={"chat_id": tc_h["chat_id"].strip(), "text": f"🩺 <b>RAPORT ZDROWIA SYSTEMU (24H):</b>\n✅ {res_msg}\nWszystkie skanery, laboratoria i eksport GitHub dzialaja bez bledow.", "parse_mode": "HTML", "disable_notification": True}, timeout=15)
        except Exception as hc_err:
            tc_h = json.load(open(TG_CONFIG_FILE)) if os.path.exists(TG_CONFIG_FILE) else {}
            if tc_h.get("token") and tc_h.get("chat_id"):
                requests.post(tg_url(tc_h["token"].strip(), "sendMessage"), json={"chat_id": tc_h["chat_id"].strip(), "text": f"🚨 <b>ALARM ZDROWIA SYSTEMU (24H):</b>\n❌ Wykryto usterke podczas autotestu: <code>{hc_err}</code>", "parse_mode": "HTML"}, timeout=15)

import sys, web_ui_mod
web_ui_mod.register_web_ui(app, sys.modules[__name__], apm, atm, cam, wpr)

if __name__ == "__main__":
    wd.register_worker('cfd_live_scanner', cfd_live_bg_loop)
    wd.register_worker('fast_guardian_60s', fast_active_positions_loop)
    wd.register_worker('github_sync_5m', github_auto_sync_loop)
    for k in wd.LIMITS_SEC: wd.beat(k, 'Start systemu')
    build_ai_context_bundle()
    threading.Thread(target=daily_healthcheck_loop, daemon=True).start()
    threading.Thread(target=github_auto_sync_loop, daemon=True).start()
    threading.Thread(target=cfd_live_bg_loop, daemon=True).start()
    threading.Thread(target=fast_active_positions_loop, daemon=True).start()
    main()
