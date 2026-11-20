import os, json

def check_sniper_quality(side, btc_dir, kl_15m):
    """Filtr Sniper Mode: wymaga zgodnosci z reżimem BTC i odrzuca swiece z dlugim knotem (>45%)."""
    if btc_dir != 0:
        if side == "LONG" and btc_dir != 1:
            return False, "Pod prad bessy BTC"
        if side == "SHORT" and btc_dir != -1:
            return False, "Pod prad hossy BTC"
    if kl_15m and len(kl_15m.get("c", [])) >= 2:
        o, h, l, c = float(kl_15m["o"][-1]), float(kl_15m["h"][-1]), float(kl_15m["l"][-1]), float(kl_15m["c"][-1])
        rng = max(1e-9, h - l)
        opp_wick = (h - max(o, c)) if side == "LONG" else (min(o, c) - l)
        if (opp_wick / rng) > 0.45:
            return False, "Zbyt dlugi przeciwny knot (>45%)"
    return True, "SNIPER OK"

def build_action_instruction(sym, side, entry, stop, tp1, is_trig):
    """Generuje jednoznaczna instrukcje 'CO TERAZ ZROBIC' bez zbednego szumu."""
    order_t = "RYNKOWYM (MARKET)" if is_trig else f"OCZEKUJACYM (LIMIT na {entry})"
    return (
        f"👉 <b>CO TERAZ ZROBIC:</b>\n"
        f"1️⃣ Otworz <b>{sym}</b> na BitBase ({side}) zleceniem <b>{order_t}</b>.\n"
        f"2️⃣ Wpisz SL: <code>{stop}</code> (ryzyko max <b>0.5%-1.0%</b> konta).\n"
        f"3️⃣ Po dojsciu do TP1 (<code>{tp1}</code>) zamknij 50% i przesun SL na wejscie (zero ryzyka)."
    )

def run_account_doctor():
    """Analizuje historie zamknietych pozycji (Live + Shadow Lab) i wskazuje przyczyny strat."""
    rows = []
    for fn in ("cfd_live_history.json", "market_shadow_lab.json"):
        if os.path.exists(fn):
            try: rows.extend(json.load(open(fn, encoding="utf-8")))
            except Exception: pass
    closed = [r for r in rows if r.get("closed_final")]
    if not closed:
        return "🩺 <b>LEKARZ KONTA:</b> Brak zamknietych transakcji do analizy. Zbieramy pierwsze probki w Sniper Mode."
    longs = [r for r in closed if r.get("side") == "LONG"]
    shorts = [r for r in closed if r.get("side") == "SHORT"]
    net_l = round(sum(float(r.get("res_r", 0)) - 0.07 for r in longs), 2)
    net_s = round(sum(float(r.get("res_r", 0)) - 0.07 for r in shorts), 2)
    wicks = sum(1 for r in closed if r.get("fail_reason") == "SL_WICK_REVERSAL")
    c_btc = sum(1 for r in closed if r.get("fail_reason") == "COUNTER_BTC_FAIL")
    advice = "Utrzymaj Sniper Mode (zgodnosc z BTC + SL 1.8x ATR)."
    if wicks >= 3: advice = "Zbyt wiele wycinan na szpilce — trzymaj szerszy SL 1.8x ATR i mniejsza dzwignie!"
    elif c_btc >= 2: advice = "Straty pochodzily z gry pod prad BTC — blokada Sniper Mode juz to odcina."
    return (
        f"🩺 <b>DIAGNOZA WYNIKOW ({len(closed)} zamknietych):</b>\n"
        f"• 🟢 LONG ({len(longs)}): <b>{net_l:+.2f}R</b> | 🔴 SHORT ({len(shorts)}): <b>{net_s:+.2f}R</b>\n"
        f"• Wyciete szpilka SL: <b>{wicks}</b> | Pod prad BTC: <b>{c_btc}</b>\n"
        f"💡 <b>Zalecenie:</b> {advice}"
    )
