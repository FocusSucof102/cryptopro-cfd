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
import os, json, time
import crypto_pro as cp

POS_FILE = "active_positions.json"

def load_positions():
    if os.path.exists(POS_FILE):
        try:
            d = json.load(open(POS_FILE))
            if isinstance(d, list): return d
        except Exception:
            pass
    return []

def save_positions(lst):
    json.dump(lst, open(POS_FILE, "w"), indent=2)

def add_position(ex, sym, side, entry, stop, tp_list, qty, margin, risk_usdt, lev):
    lst = load_positions()
    pid = f"{sym}_{int(time.time())}"
    lst.append({
        "id": pid, "exchange": ex, "symbol": sym, "side": side,
        "entry": round(float(entry), 6), "stop": round(float(stop), 6),
        "tp": [round(float(x), 6) for x in tp_list],
        "qty": float(qty), "margin": round(float(margin), 2),
        "risk": round(float(risk_usdt), 2), "lev": int(lev),
        "hit_tps": [False, False, False, False, False]
    })
    save_positions(lst)
    return pid

def toggle_tp_hit(pid, tp_idx):
    lst = load_positions()
    cfg = cp.load_settings()
    for p in lst:
        if p["id"] == pid and 0 <= tp_idx < 5:
            was_hit = p["hit_tps"][tp_idx]
            p["hit_tps"][tp_idx] = not was_hit
            # Kazdy cel R to 1/5 pozycji z zyskiem (tp_idx + 1) * (risk / 5)
            pnl_part = round((p["risk"] / 5.0) * (tp_idx + 1), 2)
            if not was_hit:
                cfg["capital"] = round(cfg["capital"] + pnl_part, 2)
            else:
                cfg["capital"] = round(cfg["capital"] - pnl_part, 2)
            cp.save_settings(cfg)
            break
    save_positions(lst)

def close_position(pid):
    lst = [p for p in load_positions() if p["id"] != pid]
    save_positions(lst)

def get_portfolio_summary():
    cfg = cp.load_settings()
    cap = float(cfg.get("capital", 200.0))
    lst = load_positions()
    used_margin = round(sum(p["margin"] for p in lst), 2)
    # Jesli 1R juz trafione, zakladamy SL na Break-Even (ryzyko = 0)
    active_risk = round(sum(0.0 if any(p["hit_tps"]) else p["risk"] for p in lst), 2)
    max_safe_margin = round(cap * 0.80, 2)
    free_margin = round(max(0.0, max_safe_margin - used_margin), 2)
    margin_pct = round((used_margin / cap * 100.0), 1) if cap > 0 else 0.0
    risk_pct = round((active_risk / cap * 100.0), 1) if cap > 0 else 0.0

    if margin_pct >= 75 or risk_pct >= 6.0:
        status = "🔴 WYSOKIE OBCIAZENIE — Nie otwieraj kolejnych pozycji!"
    elif margin_pct >= 45 or risk_pct >= 3.5:
        status = "🟡 SREDNIE OBCIAZENIE — Ostroznie z kolejnym kontraktem"
    else:
        status = "🟢 BEZPIECZNIE — Masz wolny margin na kolejne pozycje"

    return {
        "capital": cap, "count": len(lst), "used_margin": used_margin,
        "free_margin": free_margin, "max_safe_margin": max_safe_margin,
        "margin_pct": margin_pct, "active_risk": active_risk, "risk_pct": risk_pct,
        "status": status, "positions": lst
    }

GUARD_COOLDOWN = {}

def check_positions_guardian():
    lst = load_positions()
    if not lst: return
    changed = False
    for p in lst:
        ex, sym, side = p["exchange"], p["symbol"], p["side"]
        ta = cp.cm.full_analysis(ex, sym) if hasattr(cp, "cm") else None
        if not ta: continue
        cur = ta["price"]
        entry, stop = p["entry"], p["stop"]
        td = 1 if side == "LONG" else -1
        pnl_pct = round(td * (cur - entry) / entry * 100.0, 2) if entry > 0 else 0.0
        lev_pnl = round(pnl_pct * p["lev"], 1)

        # Analiza zagrozen i przeciwdzialan
        threats, actions = [], []
        sl_dist_total = abs(entry - stop) or 1e-9
        age_h = (time.time() - p.get("opened_ts", time.time())) / 3600.0
        if age_h >= 36.0 and ((td * (cur - entry)) / sl_dist_total) < 1.0:
            threats.append(f"⏱️ TIME-STOP CFD ({round(age_h,1)}h < +1R) — uniknij oplaty swap!")
            actions.append("Zamknij pozycje CFD po czasie i zwolnij margin pod szybszy impuls.")
        cur_r = (td * (cur - entry)) / sl_dist_total
        atr_1h = ta.get("atr", sl_dist_total * 0.6)
        if cur_r >= 1.5:
            new_sl = round(cur - td * 2.5 * atr_1h, 6)
            if (td == 1 and new_sl > stop) or (td == -1 and new_sl < stop):
                p["stop"] = stop = new_sl
                threats.append(f"📈 TRAILING STOP NA {cp.fmt_p(stop).strip()} (+{round(cur_r,1)}R)")
                actions.append("Zaktualizuj SL na gieldzie do poziomu kroczacego.")
        elif cur_r >= 1.5 and not p.get("half_tp_15", False):
            p["half_tp_15"] = True
            p["stop"] = stop = round(entry + td * 0.1 * sl_dist_total, 6)
            threats.append(f"⚡ CFD +1.5R! SL na BE+ ({cp.fmt_p(stop).strip()}) — mozesz dolozyc piramide +1.0R z zysku!")
            actions.append("Zamknij polowe pozycji z zyskiem i przesun SL na +0.1R (transakcja bez ryzyka).")
        elif cur_r >= 1.0 and ((td == 1 and stop < entry) or (td == -1 and stop > entry)):
            p["stop"] = stop = entry
            threats.append("🛡️ BREAK-EVEN AKTYWNY (SL na wejsciu)")
            actions.append("Przesun SL na cene wejscia — zero ryzyka.")
        sl_dist_left = td * (cur - stop)
        sl_rem_pct = round((sl_dist_left / sl_dist_total) * 100.0, 0)

        if sl_dist_left <= 0:
            threats.append("🚨 PRZEBITO POZIOM STOP LOSS!")
            actions.append("Sprawdz, czy zlecenie SL na gieldzie zamknelo pozycje; jesli nie — zamknij natychmiast z reki.")
        elif sl_rem_pct <= 25:
            threats.append(f"🚨 KRYTYCZNIE BLISKO SL (zostalo {int(sl_rem_pct)}% dystansu)")
            actions.append("Nie usredniaj straty! Przygotuj sie na zamkniecie lub utnij 50% pozycji.")

        struct = ta["smc"]["struct"]
        if (side == "LONG" and "BEARISH" in struct) or (side == "SHORT" and "BULLISH" in struct):
            threats.append(f"⚠️ ODWROCENIE STRUKTURY ({struct})")
            actions.append("Zamknij 50% pozycji lub przesun SL blizej ceny rynkowej.")

        if ta["chop"] > 65.0:
            threats.append(f"⏳ SILNA KONSOLIDACJA (CHOP {ta['chop']})")
            actions.append("Brak impetu — rozwaz zamkniecie z reki przy minimalnym zysku/stracie.")

        if (side == "LONG" and ta["rsi"] > 76) or (side == "SHORT" and ta["rsi"] < 24):
            threats.append(f"🔥 EKSTREMALNE RSI ({ta['rsi']})")
            actions.append("Zrealizuj czesc zysku i przestaw SL na Break-Even.")

        # Sprawdzanie czy cena osiagnela kolejny cel TP 1R-5R
        for idx, tp_v in enumerate(p["tp"]):
            if not p["hit_tps"][idx] and ((side == "LONG" and cur >= tp_v) or (side == "SHORT" and cur <= tp_v)):
                threats.append(f"🎯 OSIAGNIETO CEL TP {idx+1}R ({cp.fmt_p(tp_v).strip()})!")
                actions.append(f"Zrealizuj 1/5 pozycji na gieldzie, przesun SL na Break-Even i odznacz TP{idx+1} w Portfelu.")

        status_line = " | ".join(threats) if threats else f"🟢 Pozycja stabilna ({struct}, RSI {ta['rsi']})"
        hp = cp.ds24.analyze_hold_potential(ex, sym, side, cur, p["tp"]) if hasattr(cp, "ds24") else {"verdict": "Brak danych", "eta_tp": "?"}
        base_act = " ".join(actions) if actions else "Trzymaj plan — brak zagrozen."
        action_line = f"{base_act} | ⏱️ Do TP 3R: {hp['eta_tp']} | 🔮 {hp['verdict']}"
        p["live_price"] = cur
        p["live_pnl"] = f"{pnl_pct:+.2f}% ({lev_pnl:+.1f}% z lev)"
        p["live_status"] = status_line
        p["live_action"] = action_line
        changed = True

        # Wysylka natychmiastowego alertu na Telegrama (z zabezpieczeniem przed spamem co 15 min)
        if threats:
            ckey = f"{p['id']}_{threats.__getitem__(0)[:18]}"
            if time.time() - GUARD_COOLDOWN.get(ckey, 0) > 900:
                GUARD_COOLDOWN[ckey] = time.time()
                msg = (
                    f"🛡️ <b>STRAZNIK PORTFELA | {sym} ({ex})</b>\n"
                    f"Pozycja: <b>{side} {p['lev']}x</b> | Wynik: <b>{p['live_pnl']}</b>\n"
                    f"Cena: <code>{cp.fmt_p(cur).strip()}</code> (Wej: <code>{cp.fmt_p(entry).strip()}</code> | SL: <code>{cp.fmt_p(stop).strip()}</code>)\n\n"
                    f"<b>Wykryte zagrozenie / cel:</b>\n{status_line}\n\n"
                    f"<b>💡 Zalecane przeciwdzialanie:</b>\n{action_line}"
                )
                cp.send_telegram(msg)
    if changed:
        save_positions(lst)

def check_new_opportunity_margin(new_side, est_margin=35.0, est_risk=15.0):
    sm = get_portfolio_summary()
    cap = sm.get("capital", 1000.0) or 1000.0
    used_m = sm.get("used_margin", 0.0)
    act_r = sm.get("active_risk", 0.0)
    pos_list = sm.get("positions", [])
    same_dir = sum(1 for x in pos_list if x.get("side") == new_side)
    proj_m_pct = round(((used_m + est_margin) / cap) * 100.0, 1)
    proj_r_pct = round(((act_r + est_risk) / cap) * 100.0, 1)
    warns = []
    if len(pos_list) >= 3:
        warns.append(f"Masz juz {len(pos_list)} aktywne pozycje (limit 3)")
    if same_dir >= 2:
        warns.append(f"Korelacja: {same_dir} pozycje juz na {new_side}")
    if proj_m_pct > 50.0:
        warns.append(f"Margin wzrosnie do {proj_m_pct}% konta (>50%)")
    if proj_r_pct > 6.0:
        warns.append(f"Laczne ryzyko SL wyniesie {proj_r_pct}% konta")
    if warns:
        return "⚠️ <b>STRAZNIK OSTRZEGA:</b> " + " | ".join(warns)
    return f"🛡️ <b>Straznik OK:</b> Margin po wejsciu ~{proj_m_pct}% | Pozycje: {len(pos_list)}/3"

DAILY_LOSS_STATE = {"date": "", "loss_usdt": 0.0, "alerted_pct": 0}

def record_closed_trade_pnl(pnl_usdt):
    today = datetime.now().strftime("%Y-%m-%d")
    if DAILY_LOSS_STATE["date"] != today:
        DAILY_LOSS_STATE.update({"date": today, "loss_usdt": 0.0, "alerted_pct": 0})
    if pnl_usdt < 0:
        DAILY_LOSS_STATE["loss_usdt"] += abs(pnl_usdt)
    sm = get_portfolio_summary()
    cap = sm.get("capital", 1000.0) or 1000.0
    loss_pct = round((DAILY_LOSS_STATE["loss_usdt"] / cap) * 100.0, 1)
    if loss_pct >= 8.0 and DAILY_LOSS_STATE["alerted_pct"] < int(loss_pct):
        DAILY_LOSS_STATE["alerted_pct"] = int(loss_pct)
        return loss_pct, round(DAILY_LOSS_STATE["loss_usdt"], 2)
    return 0.0, 0.0
