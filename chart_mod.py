import io, math, json, requests
from statistics import mean
from PIL import Image, ImageDraw
import crypto_pro as cp

DEFAULT_OPTS = {"ema": True, "smc": True, "levels": True, "vol": True, "hurst": True, "rsi": True, "macd": True, "chop": True}

def get_chart_opts():
    opts = dict(DEFAULT_OPTS)
    saved = cp.load_settings().get("chart_opts", {})
    for k in DEFAULT_OPTS:
        if k in saved: opts[k] = saved[k]
    return opts

def toggle_chart_opt(key):
    c = cp.load_settings()
    opts = get_chart_opts()
    if key == "all":
        target = not all(opts.values())
        for k in opts: opts[k] = target
    elif key in opts:
        opts[key] = not opts[key]
    c["chart_opts"] = opts
    cp.save_settings(c)
    return opts

def calc_rsi_series(c, p=14):
    res = [50.0] * len(c)
    for i in range(p + 1, len(c)):
        sub = c[i-p:i+1]
        g = [max(0.0, sub[j] - sub[j-1]) for j in range(1, len(sub))]
        l = [max(0.0, sub[j-1] - sub[j]) for j in range(1, len(sub))]
        al = mean(l)
        res[i] = 100.0 if al == 0 else round(100.0 - (100.0 / (1.0 + mean(g) / al)), 1)
    return res

def calc_macd_series(c):
    e12, e26 = cp.ema(c, 12), cp.ema(c, 26)
    macd = [round(a - b, 5) for a, b in zip(e12, e26)]
    sig = [round(x, 5) for x in cp.ema(macd, 9)]
    hist = [round(m - s, 5) for m, s in zip(macd, sig)]
    return macd, sig, hist

def calc_chop_series(h, l, c, p=14):
    res = [50.0] * len(c)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1])) for i in range(1, len(c))]
    for i in range(p, len(c)):
        atr_sum = sum(tr[i-p+1:i+1])
        hh, ll = max(h[i-p+1:i+1]), min(l[i-p+1:i+1])
        rng = (hh - ll) or 1e-9
        val = 100.0 * math.log10(atr_sum / rng) / math.log10(p)
        res[i] = round(max(0.0, min(100.0, val)), 1)
    return res

def calc_hurst_osc(c, p=20):
    # Oscylator pozycji ceny w kanale zmiennosci (-250% do +250% jak na zrzucie)
    res = [0.0] * len(c)
    for i in range(p, len(c)):
        hi, lo = max(c[i-p:i+1]), min(c[i-p:i+1])
        mid = (hi + lo) / 2.0
        half = (hi - lo) / 2.0 or 1e-9
        res[i] = round(((c[i] - mid) / half) * 120.0, 1)
    return res

def analyze_smc(h, l, c):
    sh, sl = [], []
    for i in range(2, len(c) - 2):
        if h[i] > h[i-1] and h[i] > h[i-2] and h[i] >= h[i+1] and h[i] >= h[i+2]: sh.append(h[i])
        if l[i] < l[i-1] and l[i] < l[i-2] and l[i] <= l[i+1] and l[i] <= l[i+2]: sl.append(l[i])
    last_sh = sh[-1] if sh else max(h[-30:-5])
    prev_sh = sh[-2] if len(sh) >= 2 else last_sh
    last_sl = sl[-1] if sl else min(l[-30:-5])
    prev_sl = sl[-2] if len(sl) >= 2 else last_sl

    struct = "KONSOLIDACJA"
    if c[-1] > last_sh and last_sh > prev_sh: struct = "BULLISH BOS"
    elif c[-1] > last_sh and last_sh < prev_sh: struct = "BULLISH CHoCH"
    elif c[-1] < last_sl and last_sl < prev_sl: struct = "BEARISH BOS"
    elif c[-1] < last_sl and last_sl > prev_sl: struct = "BEARISH CHoCH"

    fvg = "Brak FVG"
    for i in range(len(c) - 1, max(3, len(c) - 15), -1):
        if l[i] > h[i-2]: fvg = f"Bull FVG ({cp.fmt_p(h[i-2]).strip()}-{cp.fmt_p(l[i]).strip()})"; break
        if h[i] < l[i-2]: fvg = f"Bear FVG ({cp.fmt_p(h[i]).strip()}-{cp.fmt_p(l[i-2]).strip()})"; break
    return {"struct": struct, "fvg": fvg, "bos_hi": last_sh, "bos_lo": last_sl}

def full_analysis(ex, sym):
    h1 = cp.fetch_klines(ex, sym, "1h", 120)
    d1 = cp.fetch_klines(ex, sym, "1d", 60)
    if not h1: return None
    o, c, h, l, v = h1["o"], h1["c"], h1["h"], h1["l"], h1["v"]
    price = c[-1]
    e5, e13 = cp.ema(c, 5), cp.ema(c, 13)
    e20, e50 = cp.ema(c, 20), cp.ema(c, 50)
    a_v = cp.atr(h, l, c)[-1]
    adx_v = round(cp.adx(h, l, c)[-1], 1)
    rsi_s = calc_rsi_series(c, 14)
    macd_s, sig_s, hist_s = calc_macd_series(c)
    chop_s = calc_chop_series(h, l, c, 14)
    hurst_s = calc_hurst_osc(c, 20)
    poc = c[-45:][max(range(45), key=lambda i: v[-45:][i])]
    smc = analyze_smc(h[-50:], l[-50:], c[-50:])
    res48, sup48 = max(h[-49:-1]), min(l[-49:-1])
    t1h = "WZROSTOWY" if c[-1] > e20[-1] > e50[-1] else ("SPADKOWY" if c[-1] < e20[-1] < e50[-1] else "BOCZNY")
    t1d = "WZROSTOWY" if (d1 and cp.get_trend(d1["c"]) == 1) else ("SPADKOWY" if (d1 and cp.get_trend(d1["c"]) == -1) else "NEUTRALNY")
    td = 1 if (t1h == "WZROSTOWY" or t1d == "WZROSTOWY") else -1
    lvl = res48 if td == 1 else sup48
    eta_s, mom = cp.analyze_trajectory(c, lvl, td, a_v)
    vol_r = round(v[-1] / (mean(v[-21:-1]) or 1.0), 2)
    chop_txt = "Konsolidacja (>61.8)" if chop_s[-1] > 61.8 else ("Silny trend (<38.2)" if chop_s[-1] < 38.2 else f"Przejsciowy ({chop_s[-1]})")
    summary = f"{smc['struct']} | {smc['fvg']} | CHOP: {chop_txt} | Hurst: {hurst_s[-1]}%"
    return {
        "symbol": sym, "ex": ex, "price": price, "td": td, "t1d": t1d, "t1h": t1h, "rsi": rsi_s[-1], "adx": adx_v,
        "chop": chop_s[-1], "macd": macd_s[-1], "hurst": hurst_s[-1], "poc": poc, "atr_pct": round(a_v/price*100, 2), "vol_r": vol_r,
        "smc": smc, "entry": lvl, "stop": lvl - td*cp.STOP_ATR*a_v, "tp": [lvl + td*k*cp.STOP_ATR*a_v for k in (1,2,3,4,5)],
        "eta": eta_s, "mom": mom, "summary": summary,
        "o": o[-45:], "h": h[-45:], "l": l[-45:], "c": c[-45:], "v": v[-45:],
        "e5": e5[-45:], "e13": e13[-45:], "rsi_s": rsi_s[-45:], "macd_s": macd_s[-45:], "sig_s": sig_s[-45:], "hist_s": hist_s[-45:], "chop_s": chop_s[-45:], "hurst_s": hurst_s[-45:]
    }

def build_chart_buf(ex, sym):
    ta = full_analysis(ex, sym)
    if not ta: return None, None
    opts = get_chart_opts()
    W, PAD_R = 820, 125
    PW = W - PAD_R - 15
    n = len(ta["c"])

    # Obliczamy wysokosc calego obrazu w zaleznosci od wlaczonych paneli
    sub_panels = [k for k in ("vol", "hurst", "rsi", "macd", "chop") if opts.get(k, True)]
    H_MAIN = 340
    H_SUB = 95
    H_TOT = H_MAIN + len(sub_panels) * H_SUB + 20

    img = Image.new("RGB", (W, H_TOT), "#0d1117")
    d = ImageDraw.Draw(img)

    # 1. PANEL GLOWNY: Swiece japonskie + strefy popytu/podazy + POC + EMA 5/13 + BOS/CHoCH + TP/BUY/SL
    hi_all = max(max(ta["h"]), ta["tp"][2] if opts.get("levels") else max(ta["h"]))
    lo_all = min(min(ta["l"]), ta["stop"] if opts.get("levels") else min(ta["l"]))
    rng = (hi_all - lo_all) or 1e-6
    hi_all += rng * 0.06; lo_all -= rng * 0.06; rng = hi_all - lo_all

    def py(val): return int(28 + (hi_all - val) / rng * (H_MAIN - 44))
    def px(idx): return int(12 + (idx + 0.5) * (PW / n))

    # Siatka pozioma + ceny na prawej osi
    for step in range(6):
        yv = lo_all + step * (rng / 5.0)
        y = py(yv)
        d.line([(10, y), (PW + 10, y)], fill="#1c2128", width=1)
        d.text((PW + 16, y - 5), cp.fmt_p(yv).strip(), fill="#8b949e")

    # Strefy Popytu / Podazy (jak na zrzucie)
    if opts.get("smc"):
        y_hi, y_lo = py(ta["smc"]["bos_hi"]), py(ta["smc"]["bos_lo"])
        d.rectangle([10, max(25, y_hi - 8), PW + 10, y_hi + 8], fill="#3d1e24")
        d.rectangle([10, y_lo - 8, PW + 10, min(H_MAIN - 10, y_lo + 8)], fill="#163326")
        d.line([(10, py(ta["poc"])), (PW + 10, py(ta["poc"]))], fill="#d29922", width=2)
        d.text((16, py(ta["poc"]) - 12), f"POC {cp.fmt_p(ta['poc']).strip()}", fill="#d29922")
        d.text((PW // 2 - 40, max(28, y_hi - 14)), f"{ta['smc']['struct']}", fill="#d2a8ff")

    # Swiece japonskie
    cw = max(3, int((PW / n) * 0.62))
    for i in range(n):
        x = px(i)
        col = "#2ea043" if ta["c"][i] >= ta["o"][i] else "#da3633"
        d.line([(x, py(ta["h"][i])), (x, py(ta["l"][i]))], fill=col, width=1)
        y1, y2 = py(ta["o"][i]), py(ta["c"][i])
        if abs(y2 - y1) < 2: y2 = y1 + 2
        d.rectangle([x - cw//2, min(y1, y2), x + cw//2, max(y1, y2)], fill=col)

    # EMA 5 / 13
    if opts.get("ema"):
        for i in range(1, n):
            d.line([(px(i-1), py(ta["e5"][i-1])), (px(i), py(ta["e5"][i]))], fill="#58a6ff", width=2)
            d.line([(px(i-1), py(ta["e13"][i-1])), (px(i), py(ta["e13"][i]))], fill="#e3b341", width=2)

    # Kolorowe etykiety TP / BUY / SL po prawej osi (dokladnie jak na zdjeciu!)
    def draw_tag(val, label, bg_col):
        y = max(26, min(H_MAIN - 18, py(val)))
        d.line([(10, y), (PW + 10, y)], fill=bg_col, width=1)
        d.rectangle([PW + 12, y - 8, W - 4, y + 8], fill=bg_col)
        d.text((PW + 16, y - 5), f"{label} {cp.fmt_p(val).strip()}", fill="#ffffff")

    if opts.get("levels"):
        tp1, tp2, tp3 = ta["tp"][0], ta["tp"][1], ta["tp"][2]
        draw_tag(tp3, "TP ", "#238636")
        draw_tag(tp2, "TP2", "#2ea043")
        draw_tag(tp1, "TP1", "#3fb950")
        draw_tag(ta["entry"], "BUY", "#1f6feb")
        draw_tag(ta["stop"], "SL ", "#da3633")

    d.rectangle([0, 0, W, 22], fill="#161b22")
    d.text((12, 5), f"{sym} ({ex} 1H) | {ta['smc']['struct']} | {ta['smc']['fvg']} | ETA: {ta['eta']}", fill="#ffffff")

    # 2. DOLNE PANELE WSKAZNIKOW (jeden pod drugim)
    cur_y = H_MAIN
    for p_name in sub_panels:
        d.line([(0, cur_y), (W, cur_y)], fill="#30363d", width=2)
        top_p, bot_p = cur_y + 18, cur_y + H_SUB - 8
        h_p = bot_p - top_p

        if p_name == "vol":
            d.text((12, cur_y + 3), f"Wolumen ({ta['vol_r']}x sredniej)", fill="#8b949e")
            vmax = max(ta["v"]) or 1.0
            for i in range(n):
                x = px(i)
                bh = int((ta["v"][i] / vmax) * h_p)
                col = "#238636" if ta["c"][i] >= ta["o"][i] else "#da3633"
                d.rectangle([x - cw//2, bot_p - bh, x + cw//2, bot_p], fill=col)

        elif p_name == "hurst":
            d.text((12, cur_y + 3), f"Hurst / Impet ({ta['hurst']}%) | gorka >100% | dolek <0%", fill="#39c5cf")
            def hy(v): return int(top_p + (250.0 - max(-250.0, min(250.0, v))) / 500.0 * h_p)
            d.line([(10, hy(100)), (PW+10, hy(100))], fill="#8b949e", width=1)
            d.line([(10, hy(0)), (PW+10, hy(0))], fill="#8b949e", width=1)
            for i in range(1, n):
                d.line([(px(i-1), hy(ta["hurst_s"][i-1])), (px(i), hy(ta["hurst_s"][i]))], fill="#39c5cf", width=2)
            d.rectangle([PW+12, hy(ta["hurst"])-7, W-4, hy(ta["hurst"])+7], fill="#1f6feb")
            d.text((PW+16, hy(ta["hurst"])-5), f"{ta['hurst']}%", fill="#ffffff")

        elif p_name == "rsi":
            d.text((12, cur_y + 3), f"RSI 14 ({ta['rsi']}) | >70 wykupienie", fill="#58a6ff")
            def ry(v): return int(top_p + (100.0 - max(0.0, min(100.0, v))) / 100.0 * h_p)
            d.line([(10, ry(70)), (PW+10, ry(70))], fill="#da3633", width=1)
            d.line([(10, ry(30)), (PW+10, ry(30))], fill="#2ea043", width=1)
            for i in range(1, n):
                d.line([(px(i-1), ry(ta["rsi_s"][i-1])), (px(i), ry(ta["rsi_s"][i]))], fill="#58a6ff", width=2)
            d.rectangle([PW+12, ry(ta["rsi"])-7, W-4, ry(ta["rsi"])+7], fill="#1f6feb")
            d.text((PW+16, ry(ta["rsi"])-5), f"{ta['rsi']}", fill="#ffffff")

        elif p_name == "macd":
            d.text((12, cur_y + 3), f"MACD 12/26/9 ({ta['macd']})", fill="#3fb950")
            m_all = ta["macd_s"] + ta["sig_s"] + ta["hist_s"]
            m_max = max(abs(min(m_all)), abs(max(m_all))) or 1e-6
            def my(v): return int(top_p + (m_max - v) / (2 * m_max) * h_p)
            y0 = my(0)
            for i in range(n):
                x = px(i); yh = my(ta["hist_s"][i])
                col = "#2ea043" if ta["hist_s"][i] >= 0 else "#da3633"
                d.rectangle([x - cw//2, min(y0, yh), x + cw//2, max(y0, yh)], fill=col)
            for i in range(1, n):
                d.line([(px(i-1), my(ta["macd_s"][i-1])), (px(i), my(ta["macd_s"][i]))], fill="#58a6ff", width=2)
                d.line([(px(i-1), my(ta["sig_s"][i-1])), (px(i), my(ta["sig_s"][i]))], fill="#e3b341", width=1)

        elif p_name == "chop":
            d.text((12, cur_y + 3), f"CHOP 14 ({ta['chop']}) | 61.8 konsolidacja | 38.2 trend", fill="#d2a8ff")
            def cy(v): return int(top_p + (100.0 - max(0.0, min(100.0, v))) / 100.0 * h_p)
            d.line([(10, cy(61.8)), (PW+10, cy(61.8))], fill="#8b949e", width=1)
            d.line([(10, cy(38.2)), (PW+10, cy(38.2))], fill="#2ea043", width=1)
            for i in range(1, n):
                d.line([(px(i-1), cy(ta["chop_s"][i-1])), (px(i), cy(ta["chop_s"][i]))], fill="#d2a8ff", width=2)
            d.rectangle([PW+12, cy(ta["chop"])-7, W-4, cy(ta["chop"])+7], fill="#1f6feb")
            d.text((PW+16, cy(ta["chop"])-5), f"{ta['chop']}", fill="#ffffff")

        cur_y += H_SUB

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf, ta
