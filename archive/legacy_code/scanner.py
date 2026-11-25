#!/usr/bin/env python3
# ==============================================================================
# [ARCHIVE/LEGACY_CODE] scanner.py
# Przeniesiono do archiwum zgodnie z restrukturyzacją projektu.
# Zachowano w repozytorium do wglądu i badań historycznych.
# ==============================================================================
import select
import signal
import shutil
import os, sys, csv, json, time, math, requests
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from statistics import mean

BASE = "https://binance.com"
CONFIG_FILE, TG_CONFIG_FILE, SETTINGS_FILE, CSV_FILE = "config_live.json", "tg_config.json", "scanner_settings.json", "signals_history.csv"
MAX_LEV, MAX_MARGIN_FRACTION, FEE_SIDE_PCT, SLIPPAGE_BPS = 100, 0.80, 0.05, 2.0
LEVEL_CANDLES, STOP_ATR, TRAIL_ATR, NEAR_ATR, ATR_N, ADX_MIN, VOL_MULT = 48, 1.5, 3.0, 1.0, 14, 20, 1.5
WATCH_EVERY, TIMEOUT = 300, 15
G, R, Y, C, B, W = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"
sent_cooldown = {}
watched_far = {}
last_view_fn = None

def on_resize(signum, frame):
    """Realizuje logike: on resize. Parametry: signum, frame."""
    if last_view_fn:
        print("\033[2J\033[H", end="")
        last_view_fn()

try:
    signal.signal(signal.SIGWINCH, on_resize)
except Exception:
    pass


def load_settings():
    """Realizuje logike: load settings."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f: return json.load(f)
    return {"capital": 200.0, "risk_pct": 1.0, "top_n": 30}

def change_settings():
    """Realizuje logike: change settings."""
    cfg = load_settings()
    print(f"\n{C}{B}--- USTAWIENIA SKANERA ---{W}")
    c_in = input(f"Kapital w USDT [{cfg['capital']}]: ").strip()
    r_in = input(f"Ryzyko na transakcje % [{cfg['risk_pct']}]: ").strip()
    t_in = input(f"Ile najplynniejszych monet skanowac (10-100) [{cfg['top_n']}]: ").strip()
    if c_in: cfg["capital"] = float(c_in)
    if r_in: cfg["risk_pct"] = float(r_in)
    if t_in: cfg["top_n"] = max(5, min(100, int(t_in)))
    with open(SETTINGS_FILE, "w") as f: json.dump(cfg, f)
    print(f"{G}Zapisano nowe ustawienia!{W}")

def get_json(url, **params):
    """Realizuje logike: get json. Parametry: url."""
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 429:
                wait_s = int(r.headers.get("Retry-After", 10))
                print(f"\n  {Y}Limit API (429). Czekam {wait_s}s...{W}")
                time.sleep(wait_s)
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt < 3: time.sleep(2)
    return None

def send_telegram(msg):
    """Realizuje logike: send telegram. Parametry: msg."""
    if not os.path.exists(TG_CONFIG_FILE): return
    with open(TG_CONFIG_FILE, "r") as f: cfg = json.load(f)
    token, chat_id = cfg.get("token", "").strip(), cfg.get("chat_id", "").strip()
    if not token or not chat_id: return
    try:
        host = "https://" + "api.telegram.org" + "/bot" + token + "/sendMessage"
        requests.post(host, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception: pass

def setup_telegram():
    """Realizuje logike: setup telegram."""
    if os.path.exists(TG_CONFIG_FILE): return
    print(f"\n{C}{B}--- KONFIGURACJA TELEGRAMA ---{W}")
    token = input("Podaj Bot Token (lub ENTER aby pominac): ").strip()
    if not token:
        with open(TG_CONFIG_FILE, "w") as f: json.dump({"token": "", "chat_id": ""}, f)
        return
    chat_id = input("Podaj swoje Chat ID: ").strip()
    with open(TG_CONFIG_FILE, "w") as f: json.dump({"token": token, "chat_id": chat_id}, f)
    send_telegram("<b>Multi-Scanner</b>: Polaczenie aktywne!")

def log_to_csv(row_dict):
    """Realizuje logike: log to csv. Parametry: row_dict."""
    file_exists = os.path.exists(CSV_FILE)
    fields = ["timestamp","symbol","side","price","entry","stop_loss","tp_1R","tp_2R","tp_3R","tp_4R","tp_5R","qty","notional_usdt","leverage","filters"]
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not file_exists: w.writeheader()
        w.writerow(row_dict)

def fmt_p(val):
    """Realizuje logike: fmt p. Parametry: val."""
    if val >= 10000: return f"{val:8.1f}"
    if val >= 1000:  return f"{val:8.2f}"
    if val >= 10:    return f"{val:8.3f}"
    return f"{val:8.4f}"

def round_qty_down(qty, step):
    """Realizuje logike: round qty down. Parametry: qty, step."""
    q, s = Decimal(str(qty)), Decimal(str(step))
    return float((q / s).to_integral_value(rounding=ROUND_DOWN) * s) if s > 0 else 0.0

def get_market_meta(top_n):
    """Realizuje logike: get market meta. Parametry: top_n."""
    info = get_json(BASE + "/fapi/v1/exchangeInfo")
    tickers = get_json(BASE + "/fapi/v1/ticker/24hr")
    if not info or not tickers: raise RuntimeError("Blad API Binance.")
    rules_map, active_usdt = {}, set()
    for s in info["symbols"]:
        sym = s["symbol"]
        if s.get("status") == "TRADING" and sym.endswith("USDT") and s.get("contractType") == "PERPETUAL":
            active_usdt.add(sym)
            flts = {flt["filterType"]: flt for flt in s["filters"]}
            lot = flts.get("MARKET_LOT_SIZE")
            if not lot or float(lot.get("stepSize", 0)) == 0: lot = flts["LOT_SIZE"]
            nf = flts.get("MIN_NOTIONAL") or flts.get("NOTIONAL")
            min_not = float(nf.get("notional", nf.get("minNotional", 0))) if nf else 5.0
            pf = flts.get("PERCENT_PRICE")
            max_dev = (float(pf.get("multiplierUp", 1.05)) - 1.0) * 100.0 if pf else 5.0
            max_dev = min(max_dev, 10.0)
            rules_map[sym] = {"step": float(lot["stepSize"]), "min_qty": float(lot["minQty"]), "min_notional": min_not, "max_dev": max_dev}
    valid = [t for t in tickers if t["symbol"] in active_usdt]
    valid.sort(key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
    return [t["symbol"] for t in valid[:top_n]], rules_map, {t["symbol"]: float(t["lastPrice"]) for t in valid[:top_n]}

def fetch_klines(symbol, interval, limit):
    """Realizuje logike: fetch klines. Parametry: symbol, interval, limit."""
    now_ms = int(time.time() * 1000)
    raw = get_json(BASE + "/fapi/v1/klines", symbol=symbol, interval=interval, limit=limit)
    if not raw: return None
    raw = [k for k in raw if int(k[6]) < now_ms]
    if len(raw) < 55: return None
    return {"o": [float(k[1]) for k in raw], "h": [float(k[2]) for k in raw], "l": [float(k[3]) for k in raw], "c": [float(k[4]) for k in raw], "v": [float(k[5]) for k in raw]}

def ema(v, p):
    """Realizuje logike: ema. Parametry: v, p."""
    a = 2.0 / (p + 1.0)
    res, cur = [], v[0]
    for x in v:
        cur = x * a + cur * (1.0 - a)
        res.append(cur)
    return res

def atr(h, l, c, p=ATR_N):
    """Realizuje logike: atr. Parametry: h, l, c, p."""
    n = len(c)
    res = [0.0] * n
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1])) for i in range(1, n)]
    cur = sum(tr[1:p+1]) / p
    res[p] = cur
    for i in range(p + 1, n):
        cur = (cur * (p - 1) + tr[i]) / p
        res[i] = cur
    return res

def adx(h, l, c, p=14):
    """Realizuje logike: adx. Parametry: h, l, c, p."""
    n = len(c)
    res = [0.0] * n
    tr, pdm, mdm = [0.0]*n, [0.0]*n, [0.0]*n
    for i in range(1, n):
        up, dn = h[i] - h[i-1], l[i-1] - l[i]
        pdm[i] = up if up > dn and up > 0 else 0.0
        mdm[i] = dn if dn > up and dn > 0 else 0.0
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
    st, sp, sm = sum(tr[1:p+1]), sum(pdm[1:p+1]), sum(mdm[1:p+1])
    dx = [0.0] * n
    for i in range(p, n):
        if i > p:
            st = st - st / p + tr[i]
            sp = sp - sp / p + pdm[i]
            sm = sm - sm / p + mdm[i]
        pdi = 100.0 * sp / st if st else 0.0
        mdi = 100.0 * sm / st if st else 0.0
        dx[i] = 100.0 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) else 0.0
    cur = mean(dx[p:2*p])
    res[2*p - 1] = cur
    for i in range(2*p, n):
        cur = (cur * (p - 1) + dx[i]) / p
        res[i] = cur
    return res

def get_trend(c):
    """Realizuje logike: get trend. Parametry: c."""
    e20, e50 = ema(c, 20), ema(c, 50)
    return 1 if c[-1] > e20[-1] > e50[-1] else (-1 if c[-1] < e20[-1] < e50[-1] else 0)

def get_cols():
    """Realizuje logike: get cols."""
    return max(46, shutil.get_terminal_size((52, 24)).columns)

def draw_box_table(title, col, rows):
    """Realizuje logike: draw box table. Parametry: title, col, rows."""
    cols = get_cols()
    if cols >= 96:
        fixed = 5 + 6 + 7*8 + 4 + 13
        w_sym = max(5, cols - 1 - fixed)
        inner = w_sym + 5 + 6 + 56 + 4 + 11
        hdr = f"─ {title} ({len(rows)}) "
        print(f"\n{col}{B}┌{hdr}{'─'*max(1, inner-len(hdr))}┐{W}")
        print(f"{col}│{W}{'MONETA':<{w_sym}}{col}│{W}{'KIER':<5}{col}│{W}{'STATUS':<6}{col}│{W}{'CENA':>7}{col}│{W}{'WEJSCIE':>7}{col}│{W}{'SL':>7}{col}│{W}{'TP 1R':>7}{col}│{W}{'TP 2R':>7}{col}│{W}{'TP 3R':>7}{col}│{W}{'TP 4R':>7}{col}│{W}{'TP 5R':>7}{col}│{W}{'KAP':>4}{col}│{W}")
        print(f"{col}├{'─'*w_sym}┼─────┼──────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼────┤{W}")
        for h in rows:
            sym_s = h["symbol"].replace("USDT", "")[:w_sym]
            k_col = G if h["side"] == "LONG" else R
            st_col = f"{G}{B}" if h["is_trigger"] else (R if not h.get("price_ok", True) else C)
            st_txt = "TRIGG." if h["is_trigger"] else ("DALEKO" if not h.get("price_ok", True) else "GOTOWY")
            t1, t2, t3, t4, t5 = [fmt_p(x).strip()[:7] for x in h["tp"]]
            print(f"{col}│{W}{B}{sym_s:<{w_sym}}{W}{col}│{W}{k_col}{h['side']:<5}{W}{col}│{W}{st_col}{st_txt:<6}{W}{col}│{W}{fmt_p(h['price']).strip()[:7]:>7}{col}│{W}{fmt_p(h['entry']).strip()[:7]:>7}{col}│{W}{fmt_p(h['stop']).strip()[:7]:>7}{col}│{W}{t1:>7}{col}│{W}{t2:>7}{col}│{W}{t3:>7}{col}│{W}{t4:>7}{col}│{W}{t5:>7}{col}│{W}{col}{h['req_cap']:>3}${W}{col}│{W}")
        print(f"{col}└{'─'*w_sym}┴─────┴──────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴────┘{W}")
    else:
        fixed = 5 + 6 + 4 + 8
        avail = max(27, cols - 1 - fixed)
        w_sym = 6 + max(0, (avail - 27) // 4)
        rem = avail - w_sym
        w_p = rem // 3
        w_e = rem // 3
        w_sl = rem - w_p - w_e
        inner = w_sym + 5 + 6 + w_p + w_e + w_sl + 4 + 6
        hdr = f"─ {title} ({len(rows)}) "
        print(f"\n{col}{B}┌{hdr}{'─'*max(1, inner-len(hdr))}┐{W}")
        print(f"{col}│{W}{'MONETA':<{w_sym}}{col}│{W}{'KIER':<5}{col}│{W}{'STATUS':<6}{col}│{W}{'CENA':>{w_p}}{col}│{W}{'WEJSCIE':>{w_e}}{col}│{W}{'SL':>{w_sl}}{col}│{W}{'KAP':>4}{col}│{W}")
        print(f"{col}├{'─'*w_sym}┼─────┼──────┼{'─'*w_p}┼{'─'*w_e}┼{'─'*w_sl}┼────┤{W}")
        for idx_r, h in enumerate(rows):
            sym_s = h["symbol"].replace("USDT", "")[:w_sym]
            k_col = G if h["side"] == "LONG" else R
            st_col = f"{G}{B}" if h["is_trigger"] else (R if not h.get("price_ok", True) else C)
            st_txt = "TRIGG." if h["is_trigger"] else ("DALEKO" if not h.get("price_ok", True) else "GOTOWY")
            print(f"{col}│{W}{B}{sym_s:<{w_sym}}{W}{col}│{W}{k_col}{h['side']:<5}{W}{col}│{W}{st_col}{st_txt:<6}{W}{col}│{W}{fmt_p(h['price']).strip()[:w_p]:>{w_p}}{col}│{W}{fmt_p(h['entry']).strip()[:w_e]:>{w_e}}{col}│{W}{fmt_p(h['stop']).strip()[:w_sl]:>{w_sl}}{col}│{W}{col}{h['req_cap']:>3}${W}{col}│{W}")
            tps = [fmt_p(v).strip() for v in h["tp"]]
            bw, rw = (inner - 4) // 5, (inner - 4) % 5
            cw = [bw + (1 if j < rw else 0) for j in range(5)]
            print(f"{col}├" + "┼".join(f"{'─'*((cw[j]-2)//2)}{C}{j+1}R{col}{'─'*(cw[j]-2-(cw[j]-2)//2)}" for j in range(5)) + f"┤{W}")
            print(f"{col}│" + f"{col}│".join(f"{W}{C}{tps[j][:cw[j]]:^{cw[j]}}{W}" for j in range(5)) + f"{col}│{W}")
            if idx_r < len(rows) - 1:
                print(f"{col}├{'─'*w_sym}┼─────┼──────┼{'─'*w_p}┼{'─'*w_e}┼{'─'*w_sl}┼────┤{W}")
        print(f"{col}└{'─'*w_sym}┴─────┴──────┴{'─'*w_p}┴{'─'*w_e}┴{'─'*w_sl}┴────┘{W}")

def draw_near_table(items):
    """Realizuje logike: draw near table. Parametry: items."""
    cols = get_cols()
    fixed = 5 + 6 + 6
    avail = max(30, cols - 1 - fixed)
    w_sym = 6 + max(0, (avail - 30) // 4)
    w_p = 8 + max(0, (avail - 30) // 4)
    w_miss = avail - w_sym - w_p
    inner = w_sym + 5 + w_p + 6 + w_miss + 4
    hdr = f"─ OBSERWOWANE / W POBLIZU ({len(items)}) "
    print(f"\n{C}{B}┌{hdr}{'─'*max(1, inner-len(hdr))}┐{W}")
    print(f"{C}│{W}{'MONETA':<{w_sym}}{C}│{W}{'KIER':<5}{C}│{W}{'CENA':>{w_p}}{C}│{W}{'DYST':>6}{C}│{W}{'BRAKUJACY WARUNEK':<{w_miss}}{C}│{W}")
    print(f"{C}├{'─'*w_sym}┼─────┼{'─'*w_p}┼──────┼{'─'*w_miss}┤{W}")
    for it in items:
        sym_s = it["symbol"].replace("USDT", "")[:w_sym]
        k_col = G if it["side"] == "LONG" else R
        print(f"{C}│{W}{B}{sym_s:<{w_sym}}{W}{C}│{W}{k_col}{it['side']:<5}{W}{C}│{W}{fmt_p(it['price']).strip()[:w_p]:>{w_p}}{C}│{W}{it['dist_atr']:+5.2f}A{C}│{W}{Y}{it['missing'][:w_miss-1]:<{w_miss}}{W}{C}│{W}")
    print(f"{C}└{'─'*w_sym}┴─────┴{'─'*w_p}┴──────┴{'─'*w_miss}┘{W}")

def send_tg_card(h, is_demo=False):
    """Realizuje logike: send tg card. Parametry: h, is_demo."""
    tp1, tp2, tp3, tp4, tp5 = h["tp"][0], h["tp"][1], h["tp"][2], h["tp"][3], h["tp"][4]
    ico = "🟢" if h["side"] == "LONG" else "🔴"
    tag = " [TEST WIZUALNY]" if is_demo else ""
    dev_pct = abs(h["entry"] - h["price"]) / h["price"] * 100.0 if h["price"] > 0 else 0.0
    send_telegram(
        f"🚨 <b>TRIGGER{tag} | {h['symbol']}</b>\n"
        f"{ico} Kierunek: <b>{h['side']}</b> | 💰 Min. Kap: <b>{h['req_cap']}$</b>\n"
        f"<pre>POZYCJA  : {h['qty']} ({h['notional']:.1f}$ | {h['lev']}x)\n"
        f"CENA TERAZ: {fmt_p(h['price']).strip()}\n"
        f"WEJSCIE  : {fmt_p(h['entry']).strip()} ({dev_pct:.2f}%)\n"
        f"STOP LOSS: {fmt_p(h['stop']).strip()}\n"
        f"-------------------------\n"
        f"CEL 1R   : {fmt_p(tp1).strip()}\n"
        f"CEL 2R   : {fmt_p(tp2).strip()}\n"
        f"CEL 3R   : {fmt_p(tp3).strip()}\n"
        f"CEL 4R   : {fmt_p(tp4).strip()}\n"
        f"CEL 5R   : {fmt_p(tp5).strip()}</pre>"
    )

def demo_visual(send_tg=True):
    """Realizuje logike: demo visual. Parametry: send_tg."""
    global last_view_fn
    last_view_fn = lambda: demo_visual(send_tg=False)
    print(f"\n{C}{B}=== PODGLAD INTERFEJSU (EKRAN: {get_cols()} ZNAKOW) ==={W}")
    doge = {"symbol": "DOGEUSDT", "side": "LONG", "is_trigger": True, "price_ok": True, "price": 0.1455, "entry": 0.1452, "stop": 0.1380, "req_cap": 18, "qty": "120 DOGE", "notional": 17.4, "lev": 1, "tp": [0.1524, 0.1596, 0.1668, 0.1740, 0.1812]}
    sol  = {"symbol": "SOLUSDT", "side": "LONG", "is_trigger": True, "price_ok": True, "price": 142.850, "entry": 142.500, "stop": 138.200, "req_cap": 65, "qty": "0.45 SOL", "notional": 64.1, "lev": 1, "tp": [146.800, 151.100, 155.400, 159.700, 164.000]}
    xrp  = {"symbol": "XRPUSDT", "side": "SHORT", "is_trigger": False, "price_ok": False, "price": 0.5510, "entry": 0.5120, "stop": 0.5310, "req_cap": 82, "qty": "150 XRP", "notional": 76.8, "lev": 1, "tp": [0.4930, 0.4740, 0.4550, 0.4360, 0.4170]}
    draw_box_table("GRUPA 2: 11$ - 20$", G, [doge])
    draw_box_table("GRUPA 4: 51$ - 100$", C, [sol, xrp])
    draw_near_table([{"symbol": "BTC", "side": "SHORT", "price": 62747.7, "dist_atr": 0.45, "missing": "adx,vol"}, {"symbol": "ETH", "side": "LONG", "price": 2450.20, "dist_atr": 1.12, "missing": "Czeka na wybicie"}])
    if send_tg:
        setup_telegram()
        send_tg_card(sol, is_demo=True)
        print(f"\n{G}{B}Wyslano 1 testowa karte na Telegram (obrot nie wysle ponownie)!{W}")

def scan_market():
    """Realizuje logike: scan market."""
    cfg_s = load_settings()
    cap, rpct, top_n = cfg_s["capital"], cfg_s["risk_pct"], cfg_s["top_n"]
    enabled = json.load(open(CONFIG_FILE)).get("enabled_filters", ["adx","macro","vol"]) if os.path.exists(CONFIG_FILE) else ["adx","macro","vol"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{C}{B}=== SKAN TOP {top_n} ({now_str}) | {cap}$ | {rpct}% ==={W}")
    top_symbols, rules_map, prices_map = get_market_meta(top_n)
    hits, near_list = [], []
    for idx, sym in enumerate(top_symbols, 1):
        sys.stdout.write(f"\rSkanuje [{idx:2d}/{top_n}]: {sym:<12}"); sys.stdout.flush()
        d1 = fetch_klines(sym, "1d", 250); time.sleep(0.22)
        if not d1: continue
        td = get_trend(d1["c"])
        if td == 0: continue
        h4 = fetch_klines(sym, "4h", 100); time.sleep(0.22)
        if not h4 or get_trend(h4["c"]) != td: continue
        h1 = fetch_klines(sym, "1h", 750); time.sleep(0.22)
        if not h1 or get_trend(h1["c"]) != td: continue
        m15 = fetch_klines(sym, "15m", 20); time.sleep(0.22)
        if not m15: continue
        price, i = prices_map[sym], len(h1["c"]) - 1
        a_vals = atr(h1["h"], h1["l"], h1["c"]); atr_val = a_vals[i]
        if atr_val <= 0: continue
        level = max(h1["h"][i - LEVEL_CANDLES:i]) if td == 1 else min(h1["l"][i - LEVEL_CANDLES:i])
        dist_atr = (level - price) / atr_val if td == 1 else (price - level) / atr_val
        beyond_15m = m15["c"][-1] > level if td == 1 else m15["c"][-1] < level
        beyond_now = td * (price - level) > 0
        ext_atr = td * (price - level) / atr_val
        e200, adx_v = ema(d1["c"], 200), adx(h1["h"], h1["l"], h1["c"])
        rec_a = sorted(a_vals[max(0, i - 720):i])
        f_vals = {"adx": adx_v[i] >= ADX_MIN, "vol": h1["v"][i] >= VOL_MULT * mean(h1["v"][i - 20:i]), "macro": (d1["c"][-1] > e200[-1]) == (td == 1), "hivol": bool(rec_a) and atr_val >= rec_a[len(rec_a)//2]}
        missing = [k for k in enabled if not f_vals.get(k, False)]
        if beyond_now and beyond_15m and ext_atr <= NEAR_ATR and not missing: is_trig = True
        elif not beyond_now and dist_atr <= NEAR_ATR and not missing: is_trig = False
        else:
            if not beyond_now and dist_atr <= 1.5:
                near_list.append({"symbol": sym, "side": "LONG" if td == 1 else "SHORT", "price": price, "dist_atr": dist_atr, "missing": ",".join(missing) if missing else "Czeka na wybicie"})
            continue
        rules, entry, stop_dist = rules_map[sym], (price if is_trig else level), STOP_ATR * atr_val
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
        dev_pct = (abs(entry - price) / price * 100.0) if price > 0 else 999.0
        price_ok = dev_pct <= rules.get("max_dev", 5.0)
        hits.append({"symbol": sym, "side": "LONG" if td == 1 else "SHORT", "is_trigger": is_trig, "price_ok": price_ok, "price": price, "entry": entry, "stop": stop, "tp": tp, "dist_atr": dist_atr, "qty": qty, "notional": notional, "lev": lev, "req_cap": req_cap, "filters": ",".join(enabled)})
    print("\r" + " " * 40 + "\r", end="")

    def render_scan_results():
        tiers = [("GRUPA 1: DO 10$", G, [x for x in hits if x["req_cap"] <= 10]), ("GRUPA 2: 11$ - 20$", G, [x for x in hits if 10 < x["req_cap"] <= 20]), ("GRUPA 3: 21$ - 50$", C, [x for x in hits if 20 < x["req_cap"] <= 50]), ("GRUPA 4: 51$ - 100$", C, [x for x in hits if 50 < x["req_cap"] <= 100]), ("GRUPA 5: 101$ - 200$", B, [x for x in hits if 100 < x["req_cap"] <= 200]), ("GRUPA 6: TEST > 200$", Y, [x for x in hits if x["req_cap"] > 200])]
        any_h = False
        for t, col, grp in tiers:
            if grp:
                any_h = True
                draw_box_table(t, col, sorted(grp, key=lambda x: (x["req_cap"], x["dist_atr"])))
        if not any_h:
            print(f"\n{Y}Brak aktywnych sygnalow w TOP {top_n}.{W}")
        if near_list:
            draw_near_table(sorted(near_list, key=lambda x: x["dist_atr"]))

    for h in hits:
        sym = h["symbol"]
        dev_pct = (abs(h["entry"] - h["price"]) / h["price"] * 100.0) if h["price"] > 0 else 0.0
        if not h.get("price_ok", True):
            watched_far[sym] = {"entry": h["entry"], "max_dev": rules_map[sym].get("max_dev", 5.0), "side": h["side"], "already_new": sym not in watched_far}
            if watched_far[sym]["already_new"]:
                print(f"{Y}[OBSERWACJA DALEKO] {sym}: odchylenie {dev_pct:.2f}% poza limitem gieldy. Monitoruje co 30s.{W}")
                send_telegram(f"⏳ <b>OBSERWACJA (DALEKO) | {sym}</b>\nCena: <code>{fmt_p(h['price']).strip()}</code> | Wejscie: <code>{fmt_p(h['entry']).strip()}</code> ({dev_pct:.2f}%)\n<i>Monitoruje cene co 30 sek...</i>")
        elif sym in watched_far:
            del watched_far[sym]
            print(f"{G}{B}[W CELU GIELDY!] {sym}: cena w limicie ({dev_pct:.2f}%)!{W}")
            send_telegram(f"✅ <b>W ZASIEGU GIELDY! | {sym} ({h['side']})</b>\nCena: <code>{fmt_p(h['price']).strip()}</code> | Wejscie: <code>{fmt_p(h['entry']).strip()}</code> ({dev_pct:.2f}%)")

        if h["is_trigger"] and h.get("price_ok", True) and time.time() - sent_cooldown.get(sym, 0) > 3600:
            sent_cooldown[sym] = time.time()
            tp1, tp2, tp3, tp4, tp5 = h["tp"]
            log_to_csv({"timestamp": now_str, "symbol": sym, "side": h["side"], "price": h["price"], "entry": round(h["entry"],6), "stop_loss": round(h["stop"],6), "tp_1R": round(tp1,6), "tp_2R": round(tp2,6), "tp_3R": round(tp3,6), "tp_4R": round(tp4,6), "tp_5R": round(tp5,6), "qty": h["qty"], "notional_usdt": round(h["notional"],2), "leverage": h["lev"], "filters": f"{h['filters']}|req:{h['req_cap']}"})
            send_tg_card(h)

    global last_view_fn
    last_view_fn = render_scan_results
    render_scan_results()

def smart_input(prompt):
    """Realizuje logike: smart input. Parametry: prompt."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    prev_cols = get_cols()
    while True:
        r, _, _ = select.select([sys.stdin], [], [], 0.25)
        cur_cols = get_cols()
        if cur_cols != prev_cols:
            prev_cols = cur_cols
            if last_view_fn:
                print("\033[2J\033[H", end="")
                last_view_fn()
            sys.stdout.write("\n" + prompt)
            sys.stdout.flush()
        if r:
            return sys.stdin.readline().strip()

def fast_watch_far(seconds):
    """Realizuje logike: fast watch far. Parametry: seconds."""
    end_t = time.time() + seconds
    while time.time() < end_t:
        if not watched_far:
            time.sleep(min(5, max(0.1, end_t - time.time())))
            continue
        time.sleep(min(30, max(0.1, end_t - time.time())))
        if not watched_far:
            continue
        tickers = get_json(BASE + "/fapi/v1/ticker/24hr")
        if not tickers:
            continue
        pmap = {t["symbol"]: float(t["lastPrice"]) for t in tickers}
        for sym in list(watched_far.keys()):
            if sym not in pmap:
                continue
            cur_p = pmap[sym]
            info = watched_far[sym]
            dev = abs(info["entry"] - cur_p) / cur_p * 100.0 if cur_p > 0 else 999.0
            if dev <= info["max_dev"]:
                del watched_far[sym]
                print(f"\n{G}{B}[W CELU GIELDY! - FAST] {sym}: cena {fmt_p(cur_p).strip()} w limicie ({dev:.2f}%)!{W}")
                send_telegram(f"✅ <b>W ZASIEGU GIELDY! | {sym} ({info['side']})</b>\nCena teraz: <code>{fmt_p(cur_p).strip()}</code>\nWejscie: <code>{fmt_p(info['entry']).strip()}</code> ({dev:.2f}%)\n<i>Odchylenie w normie - gielda przyjmie zlecenie!</i>")

def main():
    """Realizuje logike: main."""
    while True:
        s = load_settings()
        cols = get_cols()
        print(f"\n{C}{B}{'='*cols}\n  MULTI-SCANNER | TOP {s['top_n']} | {s['capital']}$ | {s['risk_pct']}%\n{'='*cols}{W}")
        print("1. Skanuj TERAZ  | 2. Tryb Live (TG + CSV)")
        print("3. Ustawienia    | 4. TEST WYGLADU | 0. Wyjscie")
        ch = smart_input(f"{B}Wybor (0-4): {W}")
        if ch == "1": scan_market()
        elif ch == "2":
            setup_telegram()
            try:
                while True: scan_market(); fast_watch_far(WATCH_EVERY)
            except KeyboardInterrupt: pass
        elif ch == "3": change_settings()
        elif ch == "4": demo_visual()
        elif ch == "0": sys.exit(0)

if __name__ == "__main__": main()
