import evolution_lab_mod as elm
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
import os, json, math, time, threading
from datetime import datetime, date, time as datetime_time, timedelta, timezone
import crypto_pro as cp
import smart_sl_mod as ssl

POS_FILE = "active_positions.json"
DAILY_GUARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_guard.json")
DAILY_GUARD_LOCK = threading.RLock()
DAILY_NOTICE_IN_PROGRESS = False

def warsaw_now():
    """Returns the current Europe/Warsaw wall time using EU daylight-saving rules."""
    utc_now = datetime.now(timezone.utc)
    march_end = date(utc_now.year, 3, 31)
    october_end = date(utc_now.year, 10, 31)
    dst_start_day = march_end - timedelta(days=(march_end.weekday() + 1) % 7)
    dst_end_day = october_end - timedelta(days=(october_end.weekday() + 1) % 7)
    dst_start = datetime.combine(dst_start_day, datetime_time(1), timezone.utc)
    dst_end = datetime.combine(dst_end_day, datetime_time(1), timezone.utc)
    utc_offset = 2 if dst_start <= utc_now < dst_end else 1
    return utc_now.astimezone(timezone(timedelta(hours=utc_offset), "Europe/Warsaw"))

def _new_daily_guard_state(today=None):
    """Builds a fresh daily guard state using the configured opening capital."""
    current_day = today or warsaw_now().date().isoformat()
    capital = float(cp.load_settings().get("capital", 200.0))
    if not math.isfinite(capital) or capital <= 0:
        capital = 200.0
    return {
        "date": current_day,
        "base_capital": round(capital, 2),
        "realized_pnl_usdt": 0.0,
        "consecutive_sl": 0,
        "locked": False,
        "lock_until_date": None,
        "lock_reason": "",
        "lock_notified": False,
        "closed_trades": [],
    }

def _load_daily_guard_unlocked():
    """Loads or rolls over the Warsaw-day guard state; caller holds its lock."""
    today = warsaw_now().date().isoformat()
    if os.path.exists(DAILY_GUARD_FILE):
        with open(DAILY_GUARD_FILE, "r", encoding="utf-8") as state_file:
            state = json.load(state_file)
        if not isinstance(state, dict):
            raise ValueError("daily_guard.json must contain a JSON object")
    else:
        state = _new_daily_guard_state(today)
    if state.get("date") != today:
        state = _new_daily_guard_state(today)
        save_daily_guard(state)
    else:
        defaults = _new_daily_guard_state(today)
        for key, value in defaults.items():
            state.setdefault(key, value)
    if not isinstance(state.get("closed_trades"), list):
        raise ValueError("daily_guard.json closed_trades must be a JSON array")
    return state

def save_daily_guard(state):
    """Persists the daily guard atomically to the ignored local state file."""
    temp_path = DAILY_GUARD_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2)
    os.replace(temp_path, DAILY_GUARD_FILE)

def get_daily_guard_status():
    """Returns the Warsaw-day PnL, stop-loss streak, and current lock status."""
    with DAILY_GUARD_LOCK:
        state = _load_daily_guard_unlocked()
        save_daily_guard(state)
    base_capital = float(state.get("base_capital", 200.0) or 200.0)
    realized_pnl = float(state.get("realized_pnl_usdt", 0.0) or 0.0)
    locked = bool(state.get("locked"))
    lock_until = state.get("lock_until_date")
    status_text = (
        f"🔴 DAILY_LOCK AKTYWNY do {lock_until} 00:00 (Europe/Warsaw)"
        if locked else "🟢 DAILY_LOCK: OFF"
    )
    return {
        "locked": locked,
        "date": state.get("date", ""),
        "lock_until_date": lock_until,
        "lock_reason": state.get("lock_reason", ""),
        "base_capital": base_capital,
        "realized_pnl_usdt": round(realized_pnl, 2),
        "loss_pct": round(max(0.0, -realized_pnl) / base_capital * 100.0, 2) if base_capital > 0 else 0.0,
        "consecutive_sl": int(state.get("consecutive_sl", 0)),
        "status_text": status_text,
    }

def unlock_daily_guard():
    """Manually clears DAILY_LOCK after the Telegram confirmation action."""
    with DAILY_GUARD_LOCK:
        state = _load_daily_guard_unlocked()
        if not state.get("locked"):
            return False
        state.update({
            "locked": False,
            "lock_until_date": None,
            "lock_reason": "manual_unlock",
            "lock_notified": True,
            "manually_unlocked_at": warsaw_now().isoformat(),
        })
        save_daily_guard(state)
    return True

def record_closed_position(position, close_price=None, close_reason=None):
    """Records the net close result for an OBSTAWIONE position and may activate DAILY_LOCK."""
    if not isinstance(position, dict) or position.get("tracked_as") != "OBSTAWIONE":
        return {"recorded": False, "lock_activated": False, "pnl_usdt": None}

    entry = float(position.get("entry", 0.0) or 0.0)
    qty = float(position.get("qty", 0.0) or 0.0)
    risk = float(position.get("risk", 0.0) or 0.0)
    side = str(position.get("side", "")).upper()
    if (
        side not in ("LONG", "SHORT")
        or entry <= 0
        or qty < 0
        or risk < 0
        or not all(math.isfinite(value) for value in (entry, qty, risk))
    ):
        raise ValueError("Cannot record closed position with invalid side, entry, quantity, or risk")

    resolved_price = None
    if close_price is not None:
        candidate_price = float(close_price)
        if math.isfinite(candidate_price) and candidate_price > 0:
            resolved_price = candidate_price
    if resolved_price is None:
        saved_price = position.get("live_price")
        if saved_price is not None:
            candidate_price = float(saved_price)
            if math.isfinite(candidate_price) and candidate_price > 0:
                resolved_price = candidate_price

    hit_tps = position.get("hit_tps", [])
    tp_weights = position.get("tp_weights", [])
    tp_r = position.get("tp_r", [])
    realized_tp_pnl = position.get("realized_pnl_usdt")
    if realized_tp_pnl is None:
        realized_tp_pnl = sum(
            risk * float(tp_weights[index]) * float(tp_r[index])
            for index, was_hit in enumerate(hit_tps)
            if was_hit and index < len(tp_weights) and index < len(tp_r)
        )
    realized_tp_pnl = float(realized_tp_pnl or 0.0)
    remaining_weight = max(
        0.0,
        1.0 - sum(float(tp_weights[index]) for index, was_hit in enumerate(hit_tps)
                  if was_hit and index < len(tp_weights)),
    )
    remaining_pnl = None
    net_pnl = None
    resolved_reason = str(close_reason or "").upper()
    if resolved_price is not None:
        direction = 1 if side == "LONG" else -1
        remaining_pnl = (resolved_price - entry) * direction * qty * remaining_weight
        net_pnl = round(realized_tp_pnl + remaining_pnl - risk * 0.07, 4)
        stop = float(position.get("stop", entry) or entry)
        hit_stop = resolved_price <= stop if side == "LONG" else resolved_price >= stop
        if not resolved_reason:
            resolved_reason = "SL" if hit_stop else "MANUAL"
    else:
        resolved_reason = resolved_reason or "UNKNOWN"
        print(f"DAILY_GUARD_CLOSE_UNPRICED: {position.get('id', position.get('symbol', 'unknown'))}", flush=True)

    lock_activated = False
    with DAILY_GUARD_LOCK:
        state = _load_daily_guard_unlocked()
        trade_id = str(position.get("id", ""))
        if trade_id and any(
            isinstance(item, dict) and item.get("id") == trade_id
            for item in state.get("closed_trades", [])
        ):
            return {"recorded": False, "lock_activated": False, "pnl_usdt": None, "duplicate": True}
        if net_pnl is not None:
            state["realized_pnl_usdt"] = round(float(state.get("realized_pnl_usdt", 0.0)) + net_pnl, 4)
        if resolved_reason == "SL":
            state["consecutive_sl"] = int(state.get("consecutive_sl", 0)) + 1
        else:
            state["consecutive_sl"] = 0
        state.setdefault("closed_trades", []).append({
            "id": trade_id,
            "symbol": str(position.get("symbol", "")),
            "side": side,
            "closed_at": warsaw_now().isoformat(),
            "close_reason": resolved_reason,
            "close_price": resolved_price,
            "pnl_usdt": net_pnl,
        })
        state["closed_trades"] = state["closed_trades"][-200:]
        base_capital = float(state.get("base_capital", 200.0) or 200.0)
        daily_loss = max(0.0, -float(state.get("realized_pnl_usdt", 0.0)))
        threshold_reached = base_capital > 0 and daily_loss >= base_capital * 0.035
        streak_reached = int(state["consecutive_sl"]) >= 2
        if not state.get("locked") and (threshold_reached or streak_reached):
            tomorrow = warsaw_now().date() + timedelta(days=1)
            state.update({
                "locked": True,
                "lock_until_date": tomorrow.isoformat(),
                "lock_reason": "consecutive_sl" if streak_reached else "daily_loss",
                "lock_notified": False,
            })
            lock_activated = True
        save_daily_guard(state)

    return {
        "recorded": True,
        "lock_activated": lock_activated,
        "pnl_usdt": net_pnl,
        "capital_adjustment": None if remaining_pnl is None else round(remaining_pnl - risk * 0.07, 4),
        "close_reason": resolved_reason,
    }

def get_btc_1h_change_pct():
    """Returns BTC's latest one-hour close change from Bitget, or None if unavailable."""
    candles = cp.fetch_klines("BITGET", "BTCUSDT", "1h", 2)
    if not candles or len(candles.get("c", [])) < 2:
        return None
    previous_close = float(candles["c"][-2])
    latest_close = float(candles["c"][-1])
    if previous_close <= 0 or not math.isfinite(previous_close) or not math.isfinite(latest_close):
        return None
    return round((latest_close - previous_close) / previous_close * 100.0, 4)

def check_directional_correlation(new_side, btc_1h_change_pct=None, positions=None):
    """Checks the OBSTAWIONE same-direction cap, tightened during BTC 1h moves above 1.5%."""
    side = str(new_side).upper()
    if side not in ("LONG", "SHORT"):
        raise ValueError("Direction must be LONG or SHORT")
    open_positions = load_positions() if positions is None else positions
    btc_change = None if btc_1h_change_pct is None else float(btc_1h_change_pct)
    if btc_change is not None and not math.isfinite(btc_change):
        btc_change = None
    limit = 1 if btc_change is None or abs(btc_change) > 1.5 else 2
    same_direction = sum(
        1 for position in open_positions
        if isinstance(position, dict)
        and position.get("tracked_as") == "OBSTAWIONE"
        and str(position.get("side", "")).upper() == side
    )
    return {
        "blocked": same_direction >= limit,
        "reason": "CORRELATION_GUARD" if same_direction >= limit else "",
        "same_direction": same_direction,
        "limit": limit,
        "btc_1h_change_pct": btc_change,
    }

def _send_daily_lock_notice():
    """Sends the single DAILY_LOCK alert with a callback that requests confirmation."""
    global DAILY_NOTICE_IN_PROGRESS
    with DAILY_GUARD_LOCK:
        state = _load_daily_guard_unlocked()
        if not state.get("locked") or state.get("lock_notified") or DAILY_NOTICE_IN_PROGRESS:
            return False
        DAILY_NOTICE_IN_PROGRESS = True
        notice_date = state.get("date")
    keyboard = {"inline_keyboard": [[
        {"text": "🔓 Odblokuj (potwierdź)", "callback_data": "unlock_request"}
    ]]}
    sent = False
    try:
        sent = bool(cp.send_telegram("🔴 DAILY DRAWDOWN LOCK AKTYWNY", keyboard))
    except Exception as err:
        print(f"DAILY_GUARD_NOTIFY_ERR: {err}", flush=True)
    with DAILY_GUARD_LOCK:
        DAILY_NOTICE_IN_PROGRESS = False
        state = _load_daily_guard_unlocked()
        if sent and state.get("date") == notice_date and state.get("locked"):
            state["lock_notified"] = True
        save_daily_guard(state)
    if not sent:
        print("DAILY_GUARD_NOTIFY_PENDING: Telegram send was not confirmed", flush=True)
    return sent

def send_pending_daily_lock_notice():
    """Retries the one-time DAILY_LOCK notice when a prior Telegram send failed."""
    status = get_daily_guard_status()
    if not status["locked"]:
        return False
    return _send_daily_lock_notice()

def load_positions():
    """Realizuje logike: load positions."""
    if os.path.exists(POS_FILE):
        try:
            d = json.load(open(POS_FILE))
            if isinstance(d, list): return d
        except Exception:
            pass
    return []

def save_positions(lst):
    """Realizuje logike: save positions. Parametry: lst."""
    json.dump(lst, open(POS_FILE, "w"), indent=2)

def add_position(ex, sym, side, entry, stop, tp_list, qty, margin, risk_usdt, lev, tracked_as="OBSTAWIONE", btc_1h_change_pct=None):
    """Adds a tracked position with optional OBSTAWIONE state and target weights."""
    lst = load_positions()
    if tracked_as == "OBSTAWIONE":
        daily_status = get_daily_guard_status()
        if daily_status["locked"]:
            raise ValueError("DAILY_LOCK: nowe pozycje są zablokowane do północy Europe/Warsaw")
        btc_change = btc_1h_change_pct
        if btc_change is None:
            try:
                btc_change = get_btc_1h_change_pct()
            except Exception as err:
                print(f"CORRELATION_GUARD_BTC_ERR: {err}", flush=True)
        correlation = check_directional_correlation(side, btc_change, lst)
        if correlation["blocked"]:
            raise ValueError(
                f"CORRELATION_GUARD: {correlation['same_direction']}/{correlation['limit']} "
                f"otwarte pozycje {str(side).upper()}"
            )
    pid = f"{sym}_{int(time.time())}"
    tp_count = len(tp_list)
    if tp_count == 3:
        tp_r, tp_weights = [0.75, 1.5, 2.5], [0.50, 0.30, 0.20]
    else:
        tp_r = [float(index + 1) for index in range(tp_count)]
        tp_weights = [1.0 / max(1, tp_count)] * tp_count
    lst.append({
        "id": pid, "exchange": ex, "symbol": sym, "side": side,
        "entry": round(float(entry), 6), "stop": round(float(stop), 6),
        "tp": [round(float(x), 6) for x in tp_list],
        "tp_r": tp_r, "tp_weights": tp_weights, "tracked_as": tracked_as,
        "realized_pnl_usdt": 0.0,
        "qty": float(qty), "margin": round(float(margin), 2),
        "risk": round(float(risk_usdt), 2), "lev": int(lev),
        "hit_tps": [False] * tp_count
    })
    save_positions(lst)
    return pid

def toggle_tp_hit(pid, tp_idx):
    """Realizuje logike: toggle tp hit. Parametry: pid, tp_idx."""
    lst = load_positions()
    cfg = cp.load_settings()
    for p in lst:
        if p["id"] == pid and 0 <= tp_idx < len(p.get("hit_tps", [])):
            was_hit = p["hit_tps"][tp_idx]
            p["hit_tps"][tp_idx] = not was_hit
            weights = p.get("tp_weights", [1.0 / max(1, len(p["hit_tps"]))] * len(p["hit_tps"]))
            multiples = p.get("tp_r", [float(index + 1) for index in range(len(p["hit_tps"]))])
            pnl_part = round(p["risk"] * weights[tp_idx] * multiples[tp_idx], 2)
            if not was_hit:
                cfg["capital"] = round(cfg["capital"] + pnl_part, 2)
                p["realized_pnl_usdt"] = round(float(p.get("realized_pnl_usdt", 0.0)) + pnl_part, 4)
            else:
                cfg["capital"] = round(cfg["capital"] - pnl_part, 2)
                p["realized_pnl_usdt"] = round(float(p.get("realized_pnl_usdt", 0.0)) - pnl_part, 4)
            cp.save_settings(cfg)
            break
    save_positions(lst)

def close_position(pid, close_price=None, close_reason=None):
    """Closes a tracked position, books its net result, and activates DAILY_LOCK when required."""
    positions = load_positions()
    position = next((item for item in positions if str(item.get("id")) == str(pid)), None)
    if position is None:
        return None

    if close_price is None and position.get("live_price") is None:
        try:
            candles = cp.fetch_klines("BITGET", position.get("symbol", ""), "15m", 2)
            if candles and candles.get("c"):
                close_price = float(candles["c"][-1])
        except Exception as err:
            print(f"DAILY_GUARD_PRICE_ERR: {position.get('symbol', '')}: {err}", flush=True)

    close_info = record_closed_position(position, close_price, close_reason)
    if close_info.get("capital_adjustment") is not None:
        settings = cp.load_settings()
        settings["capital"] = round(
            max(0.0, float(settings.get("capital", 200.0)) + close_info["capital_adjustment"]),
            2,
        )
        cp.save_settings(settings)

    save_positions([item for item in positions if str(item.get("id")) != str(pid)])
    if close_info.get("lock_activated"):
        _send_daily_lock_notice()
    return close_info

def get_portfolio_summary():
    """Realizuje logike: get portfolio summary."""
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
    """Straznik 24/7: pilnuje Time-Stop, BE, Trailing SL i SMC."""
    lst = load_positions()
    if not lst: return
    changed = False
    for p in lst:
        if p.get("tracked_as") != "OBSTAWIONE":
            continue
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
        cur_r = (td * (cur - entry)) / sl_dist_total
        p["mfe_r"] = max(float(p.get("mfe_r", 0.0)), cur_r)
        if p["mfe_r"] >= 1.1 and p["mfe_r"] - cur_r >= 0.65:
            threats.append(f"⚠️ PROFIT_DECAY_WARN: cofnięcie {p['mfe_r'] - cur_r:.2f}R od MFE {p['mfe_r']:.2f}R")
            actions.append("Rozważ realizację części zysku i ochronę pozostałej pozycji.")
        age_h = (time.time() - p.get("opened_ts", time.time())) / 3600.0
        if age_h >= 36.0 and ((td * (cur - entry)) / sl_dist_total) < 1.0:
            threats.append(f"⏱️ TIME-STOP CFD ({round(age_h,1)}h < +1R) — uniknij oplaty swap!")
            actions.append("Zamknij pozycje CFD po czasie i zwolnij margin pod szybszy impuls.")
        atr_1h = ta.get("atr", sl_dist_total * 0.6)
        be_035_stop = round(entry + td * 0.35 * sl_dist_total, 6)
        if cur_r >= 1.1 and not p.get("be_035_active", False) and td * (be_035_stop - stop) > 0:
            p["stop"] = stop = be_035_stop
            p["be_035_active"] = True
            threats.append(f"🛡️ SL przesunięty na +0.35R ({cp.fmt_p(stop).strip()})")
            actions.append("Zabezpiecz pozycję; pierwsza połowa realizacji po TP1.")
        elif cur_r >= 1.5:
            new_sl = round(cur - td * 2.5 * atr_1h, 6)
            if (td == 1 and new_sl > stop) or (td == -1 and new_sl < stop):
                p["stop"] = stop = new_sl
                threats.append(f"📈 TRAILING STOP NA {cp.fmt_p(stop).strip()} (+{round(cur_r,1)}R)")
                actions.append("Zaktualizuj SL na gieldzie do poziomu kroczacego.")
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
                target_label = p.get("tp_r", [float(index + 1) for index in range(len(p["tp"]))])[idx]
                target_weight = p.get("tp_weights", [1.0 / max(1, len(p["tp"]))] * len(p["tp"]))[idx]
                threats.append(f"🎯 OSIAGNIETO CEL TP{idx+1} ({target_label}R, {target_weight:.0%}) ({cp.fmt_p(tp_v).strip()})!")
                actions.append(f"Zrealizuj {target_weight:.0%} pozycji na gieldzie i odznacz TP{idx+1} w Portfelu.")
                if idx == 0 and ((td == 1 and stop < entry) or (td == -1 and stop > entry)):
                    p["stop"] = stop = entry
                    p["be_entry_active"] = True
                    actions.append("Przesuń SL na Break-Even po TP1.")

        status_line = " | ".join(threats) if threats else f"🟢 Pozycja stabilna ({struct}, RSI {ta['rsi']})"
        hp = cp.ds24.analyze_hold_potential(ex, sym, side, cur, p["tp"]) if hasattr(cp, "ds24") else {"verdict": "Brak danych", "eta_tp": "?"}
        base_act = " ".join(actions) if actions else "Trzymaj plan — brak zagrozen."
        rec_sl, sl_why = ssl.compute_smart_sl(side, entry, cur, stop, atr_1h, ta["smc"]["bos_hi"], ta["smc"]["bos_lo"], p.get("lev", 10))
        action_line = f"{base_act} | 🛡️ Proponowany SL: <code>{cp.fmt_p(rec_sl).strip()}</code> ({sl_why}) | ⏱️ Do TP 3R: {hp['eta_tp']}"
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
    """Realizuje logike: check new opportunity margin. Parametry: new_side, est_margin, est_risk."""
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
    """Realizuje logike: record closed trade pnl. Parametry: pnl_usdt."""
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
