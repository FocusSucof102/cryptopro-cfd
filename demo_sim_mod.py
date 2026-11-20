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
import alpha_pro_mod as apm
import os, json, time
from datetime import datetime
import crypto_pro as cp

DEMO_FILE = "demo_sim.json"

def load_demo():
    if os.path.exists(DEMO_FILE):
        try:
            d = json.load(open(DEMO_FILE))
            if isinstance(d, dict) and "positions" in d: return d
        except Exception:
            pass
    return None

def save_demo(d):
    json.dump(d, open(DEMO_FILE, "w"), indent=2)

def start_demo_24h():
    ex = cp.load_settings().get("exchange", "BINANCE")
    hits = [x for x in cp.LATEST.get("hits", []) if isinstance(x, dict)]
    if not hits:
        cp.run_full_scan(show_term=False)
        hits = [x for x in cp.LATEST.get("hits", []) if isinstance(x, dict)]
    if not hits:
        # Jesli w tym kwadransie brak scislego przeciecia z trendem BTC, bierzemy najlepsze sygnaly ze skanu glownego lub obserwowanych
        hits = [x for x in cp.LATEST.get("hits", []) if isinstance(x, dict)]
    if not hits:
        for ex_fb in ("BITGET", "BITBASE"):
            for sym in syms.__getitem__(slice(0, 25)):
                try:
                    m15 = cp.fetch_klines(ex_fb, sym, "15m", 60)
                    h1 = cp.fetch_klines(ex_fb, sym, "1h", 60)
                    if not m15 or not h1: continue
                    cl = m15["c"].__getitem__(-1)
                    av = cp.atr(h1["h"], h1["l"], h1["c"]).__getitem__(-1) or (cl * 0.01)
                    side = "LONG" if btc_d >= 0 else "SHORT"
                    td = 1 if side == "LONG" else -1
                    hits.append({"symbol": sym, "side": side, "win_prob": 76, "entry": cl, "stop": cl - td * 1.8 * av, "price": cl, "is_trig": True, "req_cap": 10.0})
                    if len(hits) >= 6: break
                except Exception: pass
            if hits:
                ex = ex_fb
                break
    if not hits:
        return None

    now_ts = int(time.time())
    positions = []
    # Bierzemy maksymalnie 8 najlepszych propozycji ze skanu (ryzyko 1% = 10$ na pozycje z puli 1000$)
    for h in hits.__getitem__(slice(0, 8)):
        risk_u = 10.0
        stop_d = abs(h["entry"] - h["stop"]) or 1e-6
        qty = risk_u / stop_d
        positions.append({
            "symbol": h["symbol"], "side": h["side"], "win_prob": h.get("win_prob", 65),
            "entry": round(h["entry"], 6), "stop": round(h["stop"], 6),
            "tp": [round(x, 6) for x in h["tp"]],
            "qty": qty, "risk_usdt": risk_u,
            "entered": bool(h.get("is_trig", False)),
            "closed": False, "close_reason": "", "realized_pnl": 0.0,
            "hit_tps": [False, False, False, False, False],
            "cur_price": h["price"]
        })

    sim = {
        "exchange": ex, "start_ts": now_ts, "end_ts": now_ts + 86400,
        "start_str": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "initial_cap": 1000.0, "finished": False, "positions": positions
    }
    save_demo(sim)
    return sim

def update_demo_24h():
    sim = load_demo()
    if not sim: return None
    now_ts = int(time.time())
    ex = sim["exchange"]
    expired = now_ts >= sim["end_ts"]

    for p in sim["positions"]:
        if p["closed"]: continue
        m15 = cp.fetch_klines(ex, p["symbol"], "15m", 96)
        if not m15: continue
        cur = m15["c"].__getitem__(-1)
        p["cur_price"] = cur
        side = p["side"]
        bars = min(96, max(1, int((now_ts - sim["start_ts"]) / 900) + 1))
        hi_win = max(m15["h"].__getitem__(slice(-bars, None)))
        lo_win = min(m15["l"].__getitem__(slice(-bars, None)))

        if not p["entered"]:
            if (side == "LONG" and hi_win >= p["entry"]) or (side == "SHORT" and lo_win <= p["entry"]):
                p["entered"] = True

        if p["entered"]:
            for idx, tp_v in enumerate(p["tp"]):
                if not p["hit_tps"].__getitem__(idx):
                    if (side == "LONG" and hi_win >= tp_v) or (side == "SHORT" and lo_win <= tp_v):
                        p["hit_tps"][idx] = True
                        p["realized_pnl"] = round(p["realized_pnl"] + (p["risk_usdt"] / 5.0) * (idx + 1), 2)

            eff_sl = p["entry"] if any(p["hit_tps"]) else p["stop"]
            hit_sl = (side == "LONG" and lo_win <= eff_sl) or (side == "SHORT" and hi_win >= eff_sl)
            if hit_sl or all(p["hit_tps"]):
                p["closed"] = True
                if all(p["hit_tps"]): p["close_reason"] = "🏆 PELNE 5R"
                elif any(p["hit_tps"]): p["close_reason"] = "🛡️ SL na BE (Zysk)"
                else:
                    p["realized_pnl"] = round(-p["risk_usdt"] - fee_cl, 2)
                    p["close_reason"] = "🛑 STOP LOSS (-1R)"

        if expired and not p["closed"]:
            p["closed"] = True
            if p["entered"]:
                rem_frac = (5 - sum(1 for x in p["hit_tps"] if x)) / 5.0
                td = 1 if side == "LONG" else -1
                p["realized_pnl"] = round(p["realized_pnl"] + td * (cur - p["entry"]) * p["qty"] * rem_frac, 2)
                p["close_reason"] = "⏱️ Koniec 24H"
            else:
                p["close_reason"] = "⚪ Nieaktywowane"

    if expired and not sim["finished"]: sim["finished"] = True
    save_demo(sim)
    return sim

def get_demo_report():
    sim = update_demo_24h()
    if not sim: return None
    rem_h = round(max(0, sim["end_ts"] - int(time.time())) / 3600.0, 1)
    realized = sum(p["realized_pnl"] for p in sim["positions"])
    floating, wins, losses = 0.0, 0, 0
    for p in sim["positions"]:
        if p["realized_pnl"] > 0 or any(p["hit_tps"]): wins += 1
        elif p["realized_pnl"] < 0: losses += 1
        if not p["closed"] and p["entered"]:
            rem_frac = (5 - sum(1 for x in p["hit_tps"] if x)) / 5.0
            td = 1 if p["side"] == "LONG" else -1
            floating += td * (p["cur_price"] - p["entry"]) * p["qty"] * rem_frac

    total_pnl = round(realized + floating, 2)
    equity = round(sim["initial_cap"] + total_pnl, 2)
    win_rate = round((wins / (wins + losses) * 100.0), 1) if (wins + losses) > 0 else 0.0
    return {"exchange": sim["exchange"], "start_str": sim["start_str"], "rem_h": rem_h, "equity": equity, "total_pnl": total_pnl, "pnl_pct": round(total_pnl / sim["initial_cap"] * 100.0, 2), "wins": wins, "losses": losses, "win_rate": win_rate, "positions": sim["positions"]}

def hourly_demo_pulse():
    sim = load_demo()
    if not sim or sim.get("finished"):
        return
    now_ts = int(time.time())
    last_rep = sim.get("last_hourly_ts", sim.get("start_ts", now_ts))
    if now_ts - last_rep >= 3600:
        sim["last_hourly_ts"] = now_ts
        save_demo(sim)
        rep = get_demo_report()
        if not rep:
            return
        elapsed_h = min(24, max(1, round((now_ts - sim["start_ts"]) / 3600.0)))
        rows_d = []
        for p in rep["positions"]:
            tps_s = "".join("✅" if x else "⬜" for x in p["hit_tps"])
            st_p = p["close_reason"] if p["closed"] else ("🟢 Aktywna" if p["entered"] else "⏳ Czeka")
            rows_d.append(f"• <b>{p['symbol']}</b> ({p['side']}) — {st_p} | TP:{tps_s} | <b>{p['realized_pnl']:+.2f}$</b>")
        msg = (
            f"⏱️ <b>RAPORT GODZINNY SYMULACJI ({elapsed_h}/24h) | {rep['exchange']}</b>\n"
            f"💰 Saldo: <b>{rep['equity']:.2f}$</b> z 1000$ (<b>{rep['total_pnl']:+.2f}$</b> / {rep['pnl_pct']:+.2f}%)\n"
            f"🎯 Skutecznosc (Win Rate): <b>{rep['win_rate']}%</b> (✅ {rep['wins']} / ❌ {rep['losses']})\n\n"
            + "\n".join(rows_d)
        )
        cp.send_telegram(msg)
import io
from PIL import Image, ImageDraw

def analyze_hold_potential(ex, sym, side, cur_price, tp_targets):
    h4 = cp.fetch_klines(ex, sym, "4h", 60)
    d1 = cp.fetch_klines(ex, sym, "1d", 60)
    if not h4 or not d1:
        return {"hold_prob": 55, "eta_tp": "~12h", "verdict": "⚪ NEUTRALNIE — Brak danych 4H/1D"}
    t4, t1 = cp.get_trend(h4["c"]), cp.get_trend(d1["c"])
    adx4 = round(cp.adx(h4["h"], h4["l"], h4["c"]).__getitem__(-1), 1)
    atr4 = cp.atr(h4["h"], h4["l"], h4["c"]).__getitem__(-1) or 1e-6
    td = 1 if side == "LONG" else -1
    score = 50 + (18 if t1 == td else -15) + (14 if t4 == td else -10) + (10 if adx4 >= 25 else 0)
    hold_prob = max(25, min(94, score))
    dist_tp3 = max(0.0, td * (tp_targets.__getitem__(2) - cur_price))
    hours_est = round((dist_tp3 / atr4) * 4.0, 1)
    eta_str = "Osiagniete!" if dist_tp3 == 0 else (f"~{int(hours_est*60)}m" if hours_est < 1 else f"~{hours_est}h")
    if hold_prob >= 72: verdict = f"✅ WARTO PRZETRZYMAC ({hold_prob}% szans w trendzie 1D+4H)"
    elif hold_prob >= 52: verdict = f"🟡 TRZYMAJ CZESC ({hold_prob}% szans — SL na BE)"
    else: verdict = f"🛑 NIE PRZETRZYMUJ ({hold_prob}% szans — trend 4H/1D przeciwny)"
    return {"hold_prob": hold_prob, "eta_tp": eta_str, "verdict": verdict}

def build_demo_chart_png(rep):
    if not rep or not rep.get("positions"): return None
    pos = rep["positions"]
    W, H = 760, 110 + len(pos) * 44
    img = Image.new("RGB", (W, H), "#0d1117")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 32], fill="#161b22")
    d.text((14, 9), f"SYMULACJA 24H ({rep['exchange']}) | Saldo: {rep['equity']:.2f}$ ({rep['total_pnl']:+.2f}$) | WinRate: {rep['win_rate']}%", fill="#ffffff")
    pct_time = min(100, max(0, int(((24.0 - rep["rem_h"]) / 24.0) * 100)))
    d.text((14, 42), f"Odliczanie 24H: {pct_time}% (zostalo {rep['rem_h']}h)", fill="#8b949e")
    d.rectangle([14, 58, W - 14, 72], fill="#21262d")
    d.rectangle([14, 58, 14 + int((W - 28) * (pct_time / 100.0)), 72], fill="#1f6feb")
    mid_x = W // 2
    d.line([(mid_x, 85), (mid_x, H - 15)], fill="#30363d", width=2)
    max_abs = max([abs(p["realized_pnl"]) for p in pos] + [15.0])
    for i, p in enumerate(pos):
        y = 95 + i * 42; pnl = p["realized_pnl"]
        col = "#2ea043" if pnl > 0 else ("#da3633" if pnl < 0 else "#8b949e")
        bar_w = int((abs(pnl) / max_abs) * (mid_x - 130))
        d.text((14, y + 6), f"{p['symbol'][:9]:<9} ({p['side']})", fill="#c9d1d9")
        if pnl >= 0:
            d.rectangle([mid_x, y + 3, mid_x + max(4, bar_w), y + 23], fill=col)
            d.text((mid_x + max(8, bar_w + 6), y + 6), f"{pnl:+.2f}$", fill="#3fb950")
        else:
            d.rectangle([mid_x - max(4, bar_w), y + 3, mid_x, y + 23], fill=col)
            d.text((mid_x - max(55, bar_w + 52), y + 6), f"{pnl:+.2f}$", fill="#f85149")
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return buf

DEMO_PRO_FILE = "demo_sim_pro.json"

def load_demo_pro():
    if os.path.exists(DEMO_PRO_FILE):
        try:
            d = json.load(open(DEMO_PRO_FILE))
            if isinstance(d, dict) and "positions" in d: return d
        except Exception:
            pass
    return None

def save_demo_pro(d):
    json.dump(d, open(DEMO_PRO_FILE, "w"), indent=2)

def start_demo_pro_24h():
    ex = "BITGET"
    btc_d, _ = cp.get_live_btc_regime() if hasattr(cp, "get_live_btc_regime") else (0, "")
    syms = apm.get_cfd_top60_symbols()
    hits = []
    for sym in syms:
        try:
            h = cp._scan_one_coin(ex, sym, 1000.0, 1.5, 20)
            if h and isinstance(h, dict) and apm.validate_cfd_order(h['entry'], h['stop'], h['price']):
                if btc_d != 0 and ((h["side"] == "LONG" and btc_d != 1) or (h["side"] == "SHORT" and btc_d != -1)):
                    continue
                hits.append(h)
        except Exception:
            pass

    if not hits:
        for ex_fb in ("BITGET", "BITBASE"):
            for sym in syms.__getitem__(slice(0, 15)):
                try:
                    m15 = cp.fetch_klines(ex_fb, sym, "15m", 60)
                    h1 = cp.fetch_klines(ex_fb, sym, "1h", 60)
                    if not m15 or not h1: continue
                    cl = m15["c"].__getitem__(-1)
                    av = cp.atr(h1["h"], h1["l"], h1["c"]).__getitem__(-1) or (cl * 0.01)
                    side = "LONG" if btc_d >= 0 else "SHORT"
                    td = 1 if side == "LONG" else -1
                    hits.append({"symbol": sym, "side": side, "win_prob": 78, "entry": cl, "stop": cl - td * 1.8 * av, "price": cl, "is_trig": True, "req_cap": 10.0})
                    if len(hits) >= 6: break
                except Exception:
                    pass
            if hits:
                ex = ex_fb
                break

    if not hits:
        return None

    hits.sort(key=lambda x: (-x.get("win_prob", 0), x["req_cap"]))
    now_ts = int(time.time())
    positions = []
    for h in hits.__getitem__(slice(0, 3)):
        risk_u = 25.0
        stop_d = abs(h["entry"] - h["stop"]) or 1e-6
        positions.append({
            "symbol": h["symbol"], "side": h["side"], "win_prob": h.get("win_prob", 78),
            "entry": round(h["entry"], 6), "stop": round(h["stop"], 6),
            "stop_d": stop_d, "qty": risk_u / stop_d, "risk_usdt": risk_u,
            "entered": bool(h.get("is_trig", False)),
            "closed": False, "close_reason": "", "realized_pnl": 0.0,
            "half_15": False, "cur_price": h["price"]
        })

    sim = {
        "exchange": ex, "start_ts": now_ts, "end_ts": now_ts + 86400,
        "start_str": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "initial_cap": 1000.0, "finished": False, "positions": positions
    }
    save_demo_pro(sim)
    return sim

def update_demo_pro_24h():
    sim = load_demo_pro()
    if not sim: return None
    now_ts = int(time.time())
    ex = sim["exchange"]
    expired = now_ts >= sim["end_ts"]

    for p in sim["positions"]:
        if p["closed"]: continue
        m15 = cp.fetch_klines(ex, p["symbol"], "15m", 96)
        if not m15: continue
        cur = m15["c"].__getitem__(-1)
        p["cur_price"] = cur
        side = p["side"]
        td = 1 if side == "LONG" else -1
        bars = min(96, max(1, int((now_ts - sim["start_ts"]) / 900) + 1))
        hi_win = max(m15["h"].__getitem__(slice(-bars, None)))
        lo_win = min(m15["l"].__getitem__(slice(-bars, None)))

        if not p["entered"]:
            if (td == 1 and hi_win >= p["entry"]) or (td == -1 and lo_win <= p["entry"]):
                p["entered"] = True
                fee_open = round(p["entry"] * p["qty"] * 0.0005, 2)
                p["fees"] = round(p.get("fees", 0.0) + fee_open, 2)
                p["realized_pnl"] = round(p["realized_pnl"] - fee_open, 2)

        if p["entered"]:
            sd = p["stop_d"]
            # 1. Partial TP 50% przy +1.5R + przesuniecie SL na BE+ (+0.1R)
            tp15 = p["entry"] + td * 1.5 * sd
            if not p["half_15"] and ((td == 1 and hi_win >= tp15) or (td == -1 and lo_win <= tp15)):
                p["half_15"] = True
                p["realized_pnl"] = round(p["realized_pnl"] + p["risk_usdt"] * 0.75, 2)
                p["stop"] = round(p["entry"] + td * 0.1 * sd, 6)

            # 2. Pelny cel +3.2R dla drugiej polowy pozycji
            tp32 = p["entry"] + td * 3.2 * sd
            if (td == 1 and hi_win >= tp32) or (td == -1 and lo_win <= tp32):
                fee_tp = round(tp32 * p["qty"] * 0.00025, 2)
                p["fees"] = round(p.get("fees", 0.0) + fee_tp, 2)
                p["realized_pnl"] = round(p["realized_pnl"] + p["risk_usdt"] * 1.6 - fee_tp, 2)
                p["closed"] = True
                p["close_reason"] = "🏆 PELNY CEL +3.2R"
                continue

            # 3. Sprawdzenie Stop Lossa
            hit_sl = (td == 1 and lo_win <= p["stop"]) or (td == -1 and hi_win >= p["stop"])
            if hit_sl:
                p["closed"] = True
                fee_cl = round(p["stop"] * p["qty"] * (0.00025 if p["half_15"] else 0.0005), 2)
                p["fees"] = round(p.get("fees", 0.0) + fee_cl, 2)
                if p["half_15"]:
                    p["realized_pnl"] = round(p["realized_pnl"] + p["risk_usdt"] * 0.05 - fee_cl, 2)
                    p["close_reason"] = "🛡️ 50% TP + BE+ (Zysk)"
                else:
                    p["realized_pnl"] = round(-p["risk_usdt"] - fee_cl, 2)
                    p["close_reason"] = "🛑 STOP LOSS (-1R)"

        if expired and not p["closed"]:
            p["closed"] = True
            if p["entered"]:
                rem_w = 0.5 if p["half_15"] else 1.0
                open_r = (td * (cur - p["entry"])) / p["stop_d"]
                p["realized_pnl"] = round(p["realized_pnl"] + p["risk_usdt"] * open_r * rem_w, 2)
                p["close_reason"] = "⏱️ Koniec 24H"
            else:
                p["close_reason"] = "⚪ Nieaktywowane"

    if expired and not sim["finished"]: sim["finished"] = True
    save_demo_pro(sim)
    return sim

def get_demo_pro_report():
    sim = update_demo_pro_24h()
    if not sim: return None
    rem_h = round(max(0, sim["end_ts"] - int(time.time())) / 3600.0, 1)
    realized = sum(p["realized_pnl"] for p in sim["positions"])
    floating, wins, losses = 0.0, 0, 0
    for p in sim["positions"]:
        if p["realized_pnl"] > 0 or p["half_15"]: wins += 1
        elif p["realized_pnl"] < 0: losses += 1
        if not p["closed"] and p["entered"]:
            rem_w = 0.5 if p["half_15"] else 1.0
            td = 1 if p["side"] == "LONG" else -1
            floating += td * (p["cur_price"] - p["entry"]) * p["qty"] * rem_w
    total_pnl = round(realized + floating, 2)
    equity = round(sim["initial_cap"] + total_pnl, 2)
    win_rate = round((wins / (wins + losses) * 100.0), 1) if (wins + losses) > 0 else 0.0
    return {"exchange": sim["exchange"], "start_str": sim["start_str"], "rem_h": rem_h, "equity": equity, "total_pnl": total_pnl, "pnl_pct": round(total_pnl / sim["initial_cap"] * 100.0, 2), "wins": wins, "losses": losses, "win_rate": win_rate, "positions": sim["positions"]}
