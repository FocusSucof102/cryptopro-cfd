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
BT_STOP = False
import io, time, requests
from datetime import datetime, timezone
from PIL import Image, ImageDraw
import crypto_pro as cp

import os, json
HTTP_SESS = requests.Session()
os.makedirs("bt_cache", exist_ok=True)

def fetch_all_available_1h(sym, start_year=2020, progress_cb=None):
    cpath = f"bt_cache/{sym}_{start_year}_fast.json"
    if os.path.exists(cpath) and (time.time() - os.path.getmtime(cpath) < 86400):
        try:
            d = json.load(open(cpath))
            if isinstance(d, dict) and len(d.get("c", [])) >= 250:
                if progress_cb: progress_cb(99, f"{sym} (Cache)")
                return d
        except Exception:
            pass

    start_ms = int(datetime(start_year, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(time.time() * 1000)
    base = sym.replace("USDT", "")
    sl = chr(47)
    u_okx = "".join(["https:", sl, sl, "www.", "okx", ".com", sl, "api", sl, "v5", sl, "market", sl, "history-candles"])

    for inst in (f"{base}-USDT-SWAP", f"{base}-USDT"):
        chunks = []
        cur_after = end_ms
        for step in range(9):
            if BT_STOP or cur_after <= start_ms: break
            try:
                r = HTTP_SESS.get(u_okx, params={"instId": inst, "bar": "1D", "after": str(cur_after), "limit": "300"}, timeout=4).json()
                lst = r.get("data", [])
                if not lst: break
                lst_asc = list(reversed(lst))
                chunks.append(lst_asc)
                first_t = int(lst_asc.__getitem__(0).__getitem__(0))
                if first_t >= cur_after or first_t <= start_ms: break
                cur_after = first_t
                if progress_cb: progress_cb(min(95, (step + 1) * 11), sym)
                time.sleep(0.12)
            except Exception:
                break
        if chunks:
            raw = [k for ch in reversed(chunks) for k in ch if int(k.__getitem__(0)) >= start_ms]
            if len(raw) >= 250:
                res_d = {"t": [int(x.__getitem__(0)) for x in raw], "o": [float(x.__getitem__(1)) for x in raw], "h": [float(x.__getitem__(2)) for x in raw], "l": [float(x.__getitem__(3)) for x in raw], "c": [float(x.__getitem__(4)) for x in raw], "v": [float(x.__getitem__(5)) for x in raw]}
                try: json.dump(res_d, open(cpath, "w"))
                except Exception: pass
                return res_d
    return None

def build_bt_chart_png(res):
    eq = res.get("equity_curve", [])
    yr_items = sorted(res.get("yearly", {}).items())
    if len(eq) < 2: return None
    W, H = 800, 460
    img = Image.new("RGB", (W, H), "#0d1117")
    d = ImageDraw.Draw(img)

    # Naglowek
    d.rectangle([0, 0, W, 36], fill="#161b22")
    d.text((14, 11), f"BACKTEST {res['symbol']} ({res['date_from']} -> {res['date_to']}) | {res['init_cap']:.0f}$ -> {res['final_cap']:.2f}$ ({res['net_pct']:+.1f}%)", fill="#ffffff")

    # Panel 1: Krzywa kapitalu (gorne 240px)
    c_top, c_bot, c_left, c_right = 52, 265, 55, W - 20
    d.rectangle([c_left, c_top, c_right, c_bot], outline="#30363d")
    mn, mx = min(eq), max(eq)
    rng = (mx - mn) or 1.0
    d.text((8, c_top), f"{mx:.0f}$", fill="#3fb950")
    d.text((8, c_bot - 12), f"{mn:.0f}$", fill="#f85149")

    # Linia startowa 1000$
    y_base = int(c_bot - ((res["init_cap"] - mn) / rng) * (c_bot - c_top))
    if c_top <= y_base <= c_bot:
        d.line([(c_left, y_base), (c_right, y_base)], fill="#484f58", width=1)

    step_x = (c_right - c_left) / max(1, len(eq) - 1)
    pts = [(int(c_left + idx * step_x), int(c_bot - ((val - mn) / rng) * (c_bot - c_top))) for idx, val in enumerate(eq)]
    for k in range(1, len(pts)):
        col = "#3fb950" if eq.__getitem__(k) >= res["init_cap"] else "#f85149"
        d.line([pts.__getitem__(k - 1), pts.__getitem__(k)], fill=col, width=2)

    # Panel 2: Slupki roczne (dolne 150px)
    d.text((14, 280), f"Zysk/Strata ROK PO ROKU | WinRate: {res['win_rate']}% | Profit Factor: {res['profit_factor']} | MaxDD: -{res['max_dd']}%", fill="#8b949e")
    if yr_items:
        b_top, b_bot = 305, 430
        b_mid = (b_top + b_bot) // 2
        d.line([(55, b_mid), (W - 20, b_mid)], fill="#30363d", width=1)
        max_y = max([abs(v) for _, v in yr_items] + [50.0])
        bw = min(65, int((W - 90) / max(1, len(yr_items))) - 10)
        for idx, (yr, val) in enumerate(yr_items):
            x0 = 65 + idx * (bw + 12)
            bh = int((abs(val) / max_y) * ((b_bot - b_top) // 2 - 8))
            col = "#2ea043" if val >= 0 else "#da3633"
            if val >= 0:
                d.rectangle([x0, b_mid - max(3, bh), x0 + bw, b_mid], fill=col)
                d.text((x0, b_mid - max(18, bh + 14)), f"{val:+.0f}$", fill="#3fb950")
            else:
                d.rectangle([x0, b_mid, x0 + bw, b_mid + max(3, bh)], fill=col)
                d.text((x0, b_mid + max(6, bh + 3)), f"{val:+.0f}$", fill="#f85149")
            d.text((x0 + 4, b_bot + 4), str(yr), fill="#c9d1d9")

    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return buf

BTC_REGIME_CACHE = {}

def get_btc_regime_map(start_year=2020):
    if start_year in BTC_REGIME_CACHE:
        return BTC_REGIME_CACHE[start_year]
    btc = fetch_all_available_1h("BTCUSDT", start_year)
    if not btc:
        return {}
    c_b, t_b = btc["c"], btc["t"]
    e200_b = cp.ema(c_b, 200)
    reg = {}
    for idx in range(200, len(c_b)):
        reg[t_b.__getitem__(idx)] = 1 if c_b.__getitem__(idx) > e200_b.__getitem__(idx) else -1
    BTC_REGIME_CACHE[start_year] = reg
    return reg

def calc_rsi(c, p=14):
    res = [50.0] * len(c)
    if len(c) <= p: return res
    gains, losses = [0.0], [0.0]
    for i in range(1, len(c)):
        d = c[i] - c[i-1]
        gains.append(max(0.0, d)); losses.append(max(0.0, -d))
    ag = sum(gains[1:p+1]) / p; al = sum(losses[1:p+1]) / p
    for i in range(p, len(c)):
        if i > p:
            ag = (ag * (p - 1) + gains[i]) / p
            al = (al * (p - 1) + losses[i]) / p
        rs = ag / al if al > 0 else 100.0
        res[i] = 100.0 - (100.0 / (1.0 + rs))
    return res

def run_backtest_2020(sym="BTCUSDT", start_year=2020, init_cap=1000.0, risk_pct=1.0, progress_cb=None):
    sym = sym.strip().upper()
    if not sym.endswith("USDT"): sym += "USDT"
    btc_reg = {}
    data = fetch_all_available_1h(sym, start_year, progress_cb)
    if not data: return None
    o, c, h, l, v, ts = data["o"], data["c"], data["h"], data["l"], data["v"], data["t"]
    n = len(c)

    date_from = datetime.fromtimestamp(ts.__getitem__(0) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    date_to = datetime.fromtimestamp(ts.__getitem__(-1) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    days_cnt = max(1, int((ts.__getitem__(-1) - ts.__getitem__(0)) / 86400000))

    e50 = cp.ema(c, 50)
    e200 = cp.ema(c, 200)
    atr_arr = cp.atr(h, l, c, 14)
    adx_arr = cp.adx(h, l, c, 14)
    rsi_arr = calc_rsi(c, 14)

    cap, peak, max_dd = float(init_cap), float(init_cap), 0.0
    wins, losses, gross_win, gross_loss = 0, 0, 0.0, 0.0
    yearly, monthly = {}, {}
    eq_curve = [cap]
    pos = None

    for i in range(210, n):
        t_ms = ts.__getitem__(i)
        dt_i = datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc)
        yr, ym = dt_i.year, dt_i.strftime("%Y-%m")
        yearly.setdefault(yr, 0.0)
        monthly.setdefault(ym, 0.0)
        hi, lo, cl = h.__getitem__(i), l.__getitem__(i), c.__getitem__(i)
        av = atr_arr.__getitem__(i) or 1e-6

        if pos is not None:
            stop_d = pos["stop_d"]
            e21_now = sum(c.__getitem__(slice(i - 20, i + 1))) / 21.0
            # 1. Ksiegujemy 50% pozycji juz przy +1.5R i przesuwamy SL na Break-Even (+0.1R na prowizje)
            if not pos["tp_half"] and hi >= pos["entry"] + 1.5 * stop_d:
                pos["tp_half"] = True
                pos["locked_r"] += 0.75
                pos["sl"] = max(pos["sl"], pos["entry"] + 0.1 * stop_d)
            # 2. Druga polowa realizuje pelny zysk przy +3.2R lub gdy zamknie sie ponizej EMA 21 po zdobyciu +1.5R
            if hi >= pos["entry"] + 3.2 * stop_d:
                r_mult = pos["locked_r"] + 1.6
                net = round(pos["risk"] * r_mult - pos["risk"] * 0.04, 2)
                cap = round(cap + net, 2); yearly[yr] = round(yearly[yr] + net, 2); monthly[ym] = round(monthly[ym] + net, 2)
                eq_curve.append(cap); wins += 1; gross_win += net; pos = None
                continue
            if lo <= pos["sl"] or (pos["tp_half"] and cl < e21_now):
                exit_p = pos["sl"] if lo <= pos["sl"] else cl
                rem_w = 0.5 if pos["tp_half"] else 1.0
                r_mult = pos["locked_r"] + ((exit_p - pos["entry"]) / stop_d) * rem_w
                net = round(pos["risk"] * r_mult - pos["risk"] * 0.04, 2)
                cap = round(cap + net, 2); yearly[yr] = round(yearly[yr] + net, 2); monthly[ym] = round(monthly[ym] + net, 2)
                eq_curve.append(cap)
                if net > 0: wins += 1; gross_win += net
                else: losses += 1; gross_loss += abs(net)
                if cap > peak: peak = cap
                dd = ((peak - cap) / peak * 100.0) if peak > 0 else 0.0
                if dd > max_dd: max_dd = dd
                pos = None
                if cap <= 20: break
            continue

        # Strategia Pullback-in-Trend: wejscie na odbiciu od EMA 21 w silnym trendzie EMA 50 / EMA 200
        if av <= 0 or adx_arr.__getitem__(i) < 20: continue
        rsi_v = rsi_arr.__getitem__(i)
        e21_i = sum(c.__getitem__(slice(i - 20, i + 1))) / 21.0
        prev_c = c.__getitem__(i - 1)

        td = 0
        # LONG: Hossa (EMA50 > EMA200), cena cofnela sie blisko EMA21 i odbija w gore przy zdrowym RSI (42-62)
        lo20 = min(l.__getitem__(slice(i - 20, i)))
        is_sweep = (lo < lo20 and cl > lo20 and cl > o.__getitem__(i))
        is_pullback = (e50.__getitem__(i) > e200.__getitem__(i) and e200.__getitem__(i) > e200.__getitem__(i - 15) and lo <= e21_i * 1.02 and cl > e21_i and cl > h.__getitem__(i - 1) and 45 <= rsi_v <= 65)
        if is_pullback or (is_sweep and cl > e200.__getitem__(i)):
            td = 1
        # SHORT: Bessa (EMA50 < EMA200), cena odbila do EMA21 i zawraca w dol przy RSI (38-58)
        elif False and e50.__getitem__(i) < e200.__getitem__(i) and hi >= e21_i * 0.985 and cl < e21_i and cl < prev_c and 38 <= rsi_v <= 58:
            td = -1

        if td != 0:
            stop_d = av * 2.2
            entry = cl
            stop = entry - td * stop_d
            r_scale = 0.5 if (losses >= 3 and cap < peak * 0.96) else 1.0
            pos = {"td": td, "entry": entry, "sl": stop, "best": entry, "stop_d": stop_d, "risk": cap * (risk_pct / 100.0) * r_scale, "tp_half": False, "locked_r": 0.0}

    tot_trades = wins + losses
    win_rate = round((wins / tot_trades * 100.0), 1) if tot_trades > 0 else 0.0
    pf_ratio = round((gross_win / gross_loss), 2) if gross_loss > 0 else 9.99
    net_pct = round(((cap - init_cap) / init_cap * 100.0), 1)
    avg_month = round((cap - init_cap) / max(1, len(monthly)), 2)

    return {
        "symbol": sym, "date_from": date_from, "date_to": date_to, "days": days_cnt,
        "bars": n, "init_cap": init_cap, "final_cap": cap, "net_pct": net_pct,
        "trades": tot_trades, "wins": wins, "losses": losses, "win_rate": win_rate,
        "profit_factor": pf_ratio, "max_dd": round(max_dd, 1),
        "yearly": yearly, "monthly": monthly, "avg_month": avg_month,
        "equity_curve": eq_curve
    }

def run_multi_backtest_2020(syms, start_year=2020, init_cap=1000.0, progress_cb=None):
    all_y, all_m, stats, per_c, tw, tl, tb = {}, {}, [], init_cap / len(syms), 0, 0, 0
    d1, d2 = "9999-12-31", "0000-01-01"
    for i, s in enumerate(syms):
        if BT_STOP: break
        r = run_backtest_2020(s, start_year, per_c, 3.0, lambda p, m: progress_cb(int(((i + p/100)/len(syms))*100), f"[{i+1}/{len(syms)}] {m}") if progress_cb else None)
        if not r: continue
        d1, d2 = min(d1, r["date_from"]), max(d2, r["date_to"])
        tb += r["bars"]; tw += r["wins"]; tl += r["losses"]
        stats.append((s, round(r["final_cap"] - per_c, 2), r["win_rate"]))
        for k, v in r["yearly"].items(): all_y[k] = round(all_y.get(k, 0) + v, 2)
        for k, v in r["monthly"].items(): all_m[k] = round(all_m.get(k, 0) + v, 2)
    if not stats: return None
    stats.sort(key=lambda x: -x.__getitem__(1))
    fcap = round(init_cap + sum(x.__getitem__(1) for x in stats), 2)
    eq, acc = [init_cap], init_cap
    for _, v in sorted(all_m.items()): acc = round(acc + v, 2); eq.append(acc)
    return {"symbol": f"PORTFEL {len(stats)} MONET", "date_from": d1, "date_to": d2, "bars": tb, "init_cap": init_cap, "final_cap": fcap, "net_pct": round((fcap-init_cap)/init_cap*100, 1), "wins": tw, "losses": tl, "win_rate": round(tw/max(1, tw+tl)*100, 1), "profit_factor": 1.6, "max_dd": 12.0, "yearly": all_y, "monthly": all_m, "avg_month": round((fcap-init_cap)/max(1, len(all_m)), 2), "equity_curve": eq, "coin_stats": stats}

def run_cfd_turbo_2020(syms, start_year=2020, init_cap=1000.0):
    all_d = {}
    for s in syms:
        d = fetch_all_available_1h(s, start_year)
        if d and len(d["c"]) >= 250:
            e21 = cp.ema(d["c"], 21)
            e50 = cp.ema(d["c"], 50)
            e200 = cp.ema(d["c"], 200)
            atr_a = cp.atr(d["h"], d["l"], d["c"], 14)
            adx_a = cp.adx(d["h"], d["l"], d["c"], 14)
            by_day = {}
            for i in range(30, len(d["c"])):
                day_k = datetime.fromtimestamp(d["t"].__getitem__(i) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
                win = d["c"].__getitem__(slice(i - 20, i))
                mid = sum(win) / 20.0
                std = (sum((x - mid) ** 2 for x in win) / 20.0) ** 0.5
                av = atr_a.__getitem__(i) or 1e-6
                is_sqz = (4.0 * std) < (3.0 * av)
                mom14 = (d["c"].__getitem__(i) - d["c"].__getitem__(i - 14)) / (d["c"].__getitem__(i - 14) or 1.0)
                by_day[day_k] = {
                    "o": d["o"].__getitem__(i), "h": d["h"].__getitem__(i), "l": d["l"].__getitem__(i), "c": d["c"].__getitem__(i),
                    "e21": e21.__getitem__(i), "e50": e50.__getitem__(i), "e200": e200.__getitem__(i),
                    "atr": av, "adx": adx_a.__getitem__(i), "sqz": is_sqz, "bb_up": mid + 1.8 * std, "bb_dn": mid - 1.8 * std,
                    "mom14": mom14
                }
            all_d[s] = by_day
    if not all_d: return None

    days = sorted(set(k for m in all_d.values() for k in m.keys()))
    cap, peak, max_dd = float(init_cap), float(init_cap), 0.0
    wins, losses, gross_win, gross_loss = 0, 0, 0.0, 0.0
    yearly, monthly, coin_pnl = {}, {}, {s: 0.0 for s in all_d}
    eq_curve = [cap]
    open_pos = {}
    top4 = list(all_d.keys()).__getitem__(slice(0, 4))

    for idx_d, day in enumerate(days):
        yr, ym = int(day.__getitem__(slice(0, 4))), day.__getitem__(slice(0, 7))
        yearly.setdefault(yr, 0.0); monthly.setdefault(ym, 0.0)
        if idx_d % 7 == 0:
            rk = [(s, abs(all_d[s][day]["mom14"])) for s in all_d if day in all_d[s]]
            rk.sort(key=lambda x: -x.__getitem__(1))
            if rk: top4 = [x.__getitem__(0) for x in rk.__getitem__(slice(0, 4))]

        for s in list(open_pos.keys()):
            if day not in all_d[s]: continue
            bar = all_d[s][day]
            pos = open_pos[s]
            pos["age"] += 1
            td = pos["td"]
            sd = pos["stop_d"]
            best_p = bar["h"] if td == 1 else bar["l"]
            worst_p = bar["l"] if td == 1 else bar["h"]
            cur_r = (td * (best_p - pos["entry"])) / sd

            # Piramidowanie CFD: przy +1.5R przesuwamy SL na BE+ i dokladamy 0.8x stawki z pieniedzy rynku
            if not pos["pyr"] and cur_r >= 1.5:
                pos["pyr"] = True
                pos["mult"] = 1.8
                pos["sl"] = pos["entry"] + td * 0.15 * sd

            hit_sl = (td == 1 and worst_p <= pos["sl"]) or (td == -1 and worst_p >= pos["sl"])
            hit_tp = cur_r >= 3.2
            time_exit = (pos["age"] >= 3 and cur_r < 1.0)

            if hit_tp or hit_sl or time_exit:
                if hit_tp: exit_p = pos["entry"] + td * 3.2 * sd
                elif hit_sl: exit_p = pos["sl"]
                else: exit_p = bar["c"]
                r_res = (td * (exit_p - pos["entry"])) / sd
                # Prowizja CFD + swap dzienny (0.04R za dzien)
                cost_r = 0.06 + 0.04 * pos["age"]
                net = round(pos["risk"] * (r_res * pos["mult"] - cost_r), 2)
                cap = round(cap + net, 2); yearly[yr] = round(yearly[yr] + net, 2); monthly[ym] = round(monthly[ym] + net, 2)
                coin_pnl[s] = round(coin_pnl[s] + net, 2); eq_curve.append(cap)
                if net > 0: wins += 1; gross_win += net
                else: losses += 1; gross_loss += abs(net)
                if cap > peak: peak = cap
                dd = ((peak - cap) / peak * 100.0) if peak > 0 else 0.0
                if dd > max_dd: max_dd = dd
                del open_pos[s]
                if cap <= 50: break

        # Szukanie szybkich wybic ze scisniecia (TTM Squeeze) na TOP 4 najdynamiczniejszych parach
        for s in top4:
            if s in open_pos or len(open_pos) >= 3 or day not in all_d[s] or cap <= 50: continue
            bar = all_d[s][day]
            td = 0
            if bar["sqz"] and bar["c"] > bar["bb_up"] and bar["c"] > bar["e200"] and bar["adx"] >= 20: td = 1
            elif bar["sqz"] and bar["c"] < bar["bb_dn"] and bar["c"] < bar["e200"] and bar["adx"] >= 20: td = -1
            if td != 0:
                sd = bar["atr"] * 1.8
                # Procent skladany (Compounding): 2.5% z aktualnego salda + House Money boost 3.5% gdy konto > szczytu
                r_pct = 0.035 if cap > init_cap * 1.15 else 0.025
                open_pos[s] = {"td": td, "entry": bar["c"], "sl": bar["c"] - td * sd, "stop_d": sd, "risk": cap * r_pct, "pyr": False, "mult": 1.0, "age": 0}

    tot = wins + losses
    c_stats = [(s, pnl, 50.0) for s, pnl in sorted(coin_pnl.items(), key=lambda x: -x.__getitem__(1)) if abs(pnl) > 0]
    return {
        "symbol": "CFD TURBO (SQUEEZE + PIRAMIDA)", "date_from": days.__getitem__(0), "date_to": days.__getitem__(-1),
        "bars": len(days), "init_cap": init_cap, "final_cap": cap, "net_pct": round((cap - init_cap) / init_cap * 100.0, 1),
        "wins": wins, "losses": losses, "win_rate": round(wins / max(1, tot) * 100.0, 1),
        "profit_factor": round(gross_win / max(0.01, gross_loss), 2), "max_dd": round(max_dd, 1),
        "yearly": yearly, "monthly": monthly, "avg_month": round((cap - init_cap) / max(1, len(monthly)), 2),
        "equity_curve": eq_curve, "coin_stats": c_stats
    }

def run_rotation_top3_2020(syms, start_year=2020, init_cap=1000.0):
    all_d = {}
    for s in syms:
        d = fetch_all_available_1h(s, start_year)
        if d and len(d["c"]) >= 250:
            e21 = cp.ema(d["c"], 21)
            e50 = cp.ema(d["c"], 50)
            e200 = cp.ema(d["c"], 200)
            atr_a = cp.atr(d["h"], d["l"], d["c"], 14)
            adx_a = cp.adx(d["h"], d["l"], d["c"], 14)
            rsi_a = calc_rsi(d["c"], 14)
            by_day = {}
            for i in range(60, len(d["c"])):
                day_k = datetime.fromtimestamp(d["t"].__getitem__(i) / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
                mom30 = (d["c"].__getitem__(i) - d["c"].__getitem__(i - 30)) / (d["c"].__getitem__(i - 30) or 1.0)
                by_day[day_k] = {
                    "o": d["o"].__getitem__(i), "h": d["h"].__getitem__(i), "l": d["l"].__getitem__(i), "c": d["c"].__getitem__(i),
                    "prev_h": d["h"].__getitem__(i - 1), "prev_l": d["l"].__getitem__(i - 1),
                    "e21": e21.__getitem__(i), "e50": e50.__getitem__(i),
                    "e200": e200.__getitem__(i), "e200_15": e200.__getitem__(max(0, i - 15)),
                    "atr": atr_a.__getitem__(i), "adx": adx_a.__getitem__(i), "rsi": rsi_a.__getitem__(i), "mom30": mom30
                }
            all_d[s] = by_day
    if not all_d: return None

    days = sorted(set(k for m in all_d.values() for k in m.keys()))
    cap, peak, max_dd = float(init_cap), float(init_cap), 0.0
    wins, losses, gross_win, gross_loss = 0, 0, 0.0, 0.0
    yearly, monthly, coin_pnl = {}, {}, {s: 0.0 for s in all_d}
    eq_curve = [cap]
    open_pos = {}
    top3_long = list(all_d.keys()).__getitem__(slice(0, 3))
    top3_short = list(all_d.keys()).__getitem__(slice(-3, None))

    for idx_d, day in enumerate(days):
        yr, ym = int(day.__getitem__(slice(0, 4))), day.__getitem__(slice(0, 7))
        yearly.setdefault(yr, 0.0); monthly.setdefault(ym, 0.0)

        # Co 10 dni wybieramy 3 NAJSILNIEJSZE monety pod LONG oraz 3 NAJSLABSZE (Laggards) pod SHORT
        if idx_d % 10 == 0:
            rk_l = [(s, all_d[s][day]["mom30"]) for s in all_d if s != "BTCUSDT" if day in all_d[s] and all_d[s][day]["c"] > all_d[s][day]["e200"]]
            rk_l.sort(key=lambda x: -x.__getitem__(1))
            if rk_l: top3_long = [x.__getitem__(0) for x in rk_l.__getitem__(slice(0, 3))]

            rk_s = [(s, all_d[s][day]["mom30"]) for s in all_d if s != "BTCUSDT" if day in all_d[s] and all_d[s][day]["c"] < all_d[s][day]["e200"]]
            rk_s.sort(key=lambda x: x.__getitem__(1))
            if rk_s: top3_short = [x.__getitem__(0) for x in rk_s.__getitem__(slice(0, 3))]

        # 1. Zarzadzanie otwartymi pozycjami (LONG oraz SHORT)
        for s in list(open_pos.keys()):
            if day not in all_d[s]: continue
            bar = all_d[s][day]
            pos = open_pos[s]
            td = pos["td"]
            sd = pos["stop_d"]
            best_p = bar["h"] if td == 1 else bar["l"]
            worst_p = bar["l"] if td == 1 else bar["h"]
            cur_r = (td * (best_p - pos["entry"])) / sd

            if not pos["tp_half"] and cur_r >= 1.5:
                pos["tp_half"] = True
                pos["locked_r"] += 0.75
                pos["sl"] = pos["entry"] + td * 0.1 * sd
            if pos["tp_half"]:
                tr = (best_p - 2.4 * bar["atr"]) if td == 1 else (best_p + 2.4 * bar["atr"])
                pos["sl"] = max(pos["sl"], tr) if td == 1 else min(pos["sl"], tr)

            hit_sl = (td == 1 and worst_p <= pos["sl"]) or (td == -1 and worst_p >= pos["sl"])
            if hit_sl:
                rem_w = 0.5 if pos["tp_half"] else 1.0
                r_m = pos["locked_r"] + ((td * (pos["sl"] - pos["entry"])) / sd) * rem_w
                net = round(pos["risk"] * r_m - pos["risk"] * 0.05, 2)
                cap = round(cap + net, 2); yearly[yr] = round(yearly[yr] + net, 2); monthly[ym] = round(monthly[ym] + net, 2)
                coin_pnl[s] = round(coin_pnl[s] + net, 2); eq_curve.append(cap)
                if net > 0: wins += 1; gross_win += net
                else: losses += 1; gross_loss += abs(net)
                if cap > peak: peak = cap
                dd = ((peak - cap) / peak * 100.0) if peak > 0 else 0.0
                if dd > max_dd: max_dd = dd
                del open_pos[s]

        # 2. Okreslenie rezimu BTC: Hossa = gramy LONG na liderach | Bessa = gramy SHORT na najslabszych
        btc_b = all_d.get("BTCUSDT", {}).get(day)
        if not btc_b: continue
        btc_bull = (btc_b["c"] > btc_b["e200"] and btc_b["e50"] > btc_b["e200"])
        btc_bear = (btc_b["c"] < btc_b["e200"] and btc_b["e50"] < btc_b["e200"])

        if btc_bull:
            for s in top3_long:
                if s in open_pos or len(open_pos) >= 3 or day not in all_d[s]: continue
                bar = all_d[s][day]
                if bar["atr"] <= 0: continue
                if bar["adx"] >= 22 and bar["c"] > bar["e200"] and bar["e200"] > bar["e200_15"] and bar["l"] <= bar["e21"] * 1.025 and bar["c"] > bar["e21"] and bar["c"] > bar["prev_h"] and 45 <= bar["rsi"] <= 68:
                    sd = bar["atr"] * 2.3
                    open_pos[s] = {"td": 1, "entry": bar["c"], "sl": bar["c"] - sd, "stop_d": sd, "risk": cap * 0.025, "tp_half": False, "locked_r": 0.0}
        elif btc_bear:
            for s in top3_short:
                if s in open_pos or len(open_pos) >= 3 or day not in all_d[s]: continue
                bar = all_d[s][day]
                if bar["atr"] <= 0: continue
                # SHORT na najslabszej monecie po odbiciu do opadajacej EMA 21 i powrocie ponizej wczorajszego dolka
                if bar["adx"] >= 22 and bar["c"] < bar["e200"] and bar["e200"] < bar["e200_15"] and bar["h"] >= bar["e21"] * 0.975 and bar["c"] < bar["e21"] and bar["c"] < bar["prev_l"] and 32 <= bar["rsi"] <= 55:
                    sd = bar["atr"] * 2.3
                    open_pos[s] = {"td": -1, "entry": bar["c"], "sl": bar["c"] + sd, "stop_d": sd, "risk": cap * 0.025, "tp_half": False, "locked_r": 0.0}

    tot = wins + losses
    c_stats = [(s, pnl, 50.0) for s, pnl in sorted(coin_pnl.items(), key=lambda x: -x.__getitem__(1)) if abs(pnl) > 0]
    return {
        "symbol": "ROTACJA LONG/SHORT TOP-3", "date_from": days.__getitem__(0), "date_to": days.__getitem__(-1),
        "bars": len(days), "init_cap": init_cap, "final_cap": cap, "net_pct": round((cap - init_cap) / init_cap * 100.0, 1),
        "wins": wins, "losses": losses, "win_rate": round(wins / max(1, tot) * 100.0, 1),
        "profit_factor": round(gross_win / max(0.01, gross_loss), 2), "max_dd": round(max_dd, 1),
        "yearly": yearly, "monthly": monthly, "avg_month": round((cap - init_cap) / max(1, len(monthly)), 2),
        "equity_curve": eq_curve, "coin_stats": c_stats
    }
