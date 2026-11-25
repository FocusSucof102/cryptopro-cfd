import os
import json
import math
import requests

RISK_CONFIG_FILE = "risk_config.json"
TG_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_config.json")

DEFAULT_RISK_CONFIG = {
    "capital_usdt": 200.0,
    "risk_pct": 1.0,
    "max_drawdown_pct": 6.0,
    "current_drawdown_pct": 0.0,
    "peak_equity": 200.0,
    "safe_lock_active": False,
    "min_platinum_prob": 68
}

def load_risk_config():
    """Wczytuje konfiguracje zarzadzania ryzykiem i bezpiecznika Safe-Lock."""
    if os.path.exists(RISK_CONFIG_FILE):
        try:
            with open(RISK_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                out = dict(DEFAULT_RISK_CONFIG)
                out.update(cfg)
                return out
        except Exception:
            pass
    return dict(DEFAULT_RISK_CONFIG)

def save_risk_config(cfg):
    """Zapisuje parametry zarzadzania ryzykiem do pliku konfiguracyjnego."""
    try:
        cur = load_risk_config()
        cur.update(cfg)
        with open(RISK_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cur, f, indent=2)
        return True
    except Exception:
        return False

def send_tg_risk_alert(msg):
    """Wysyla powiadomienie alarmowe dot. ryzyka i Safe-Lock na Telegram."""
    if not os.path.exists(TG_CONFIG_FILE):
        return
    try:
        with open(TG_CONFIG_FILE, "r", encoding="utf-8") as f:
            tc = json.load(f)
        tok = tc.get("token", "").strip()
        cid = tc.get("chat_id", "").strip()
        if tok and cid:
            url = f"https://api.telegram.org/bot{tok}/sendMessage"
            requests.post(url, json={"chat_id": cid, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass

def update_equity_and_drawdown(current_equity):
    """Aktualizuje szczyt kapitalu oraz biezaca obsuwe (drawdown) w procentach."""
    cfg = load_risk_config()
    peak = max(float(cfg.get("peak_equity", 200.0)), float(current_equity))
    cur_eq = float(current_equity)
    dd_pct = ((peak - cur_eq) / peak * 100.0) if peak > 0 else 0.0
    dd_pct = round(max(0.0, dd_pct), 2)
    max_dd = float(cfg.get("max_drawdown_pct", 6.0))
    was_active = bool(cfg.get("safe_lock_active", False))
    safe_lock = dd_pct >= max_dd

    cfg["peak_equity"] = round(peak, 2)
    cfg["current_drawdown_pct"] = dd_pct
    cfg["safe_lock_active"] = safe_lock
    save_risk_config(cfg)

    if safe_lock and not was_active:
        send_tg_risk_alert(
            f"🚨 <b>BEZPIECZNIK SAFE-LOCK AKTYWOWANY!</b>\n"
            f"Obsuwa kapitału: <b>-{dd_pct}%</b> (próg: {max_dd}%).\n"
            f"Od teraz system przepuszcza <b>WYŁĄCZNIE sygnały PLATINUM (≥{cfg.get('min_platinum_prob', 68)}%)</b> "
            f"ze stawką ochronną kapitału!"
        )
    return cfg

def calculate_position_size(entry_price, stop_loss, capital=None, risk_pct=None):
    """Wylicza wielkosc pozycji, bezpieczna dzwignie Isolated (3x-10x) i margin <= 20%."""
    cfg = load_risk_config()
    cap = float(capital if capital is not None else cfg.get("capital_usdt", 200.0))
    rpct = float(risk_pct if risk_pct is not None else cfg.get("risk_pct", 1.0))
    entry = float(entry_price)
    sl = float(stop_loss)

    if entry <= 0 or sl <= 0 or entry == sl or cap <= 0:
        return {
            "qty": 0.0, "notional_usdt": 0.0, "risk_usdt": 0.0,
            "sl_dist_pct": 0.0, "rec_leverage": 1, "margin_usdt": 0.0,
            "margin_pct": 0.0, "safe": False
        }

    sl_dist = abs(entry - sl)
    sl_dist_pct = (sl_dist / entry) * 100.0
    risk_budget = cap * (rpct / 100.0)

    # Koszt transakcyjny szacowany na -0.07R
    risk_per_unit = sl_dist + 0.0007 * (entry + sl)
    raw_qty = (risk_budget / risk_per_unit) if risk_per_unit > 0 else 0.0
    notional = raw_qty * entry

    # Bezpieczna dzwignia Isolated (3x-10x) aby margin nie przekraczal 20% kapitalu
    max_margin_budget = cap * 0.20
    calc_lev = math.ceil(notional / max_margin_budget) if max_margin_budget > 0 else 3
    rec_lev = max(3, min(10, calc_lev))
    margin_usdt = notional / rec_lev if rec_lev > 0 else notional
    margin_pct = (margin_usdt / cap * 100.0) if cap > 0 else 0.0

    safe = margin_usdt <= (cap * 0.25) and sl_dist_pct >= 0.35 and sl_dist_pct <= 6.5
    return {
        "qty": round(raw_qty, 6),
        "notional_usdt": round(notional, 2),
        "risk_usdt": round(risk_budget, 2),
        "sl_dist_pct": round(sl_dist_pct, 2),
        "rec_leverage": rec_lev,
        "margin_usdt": round(margin_usdt, 2),
        "margin_pct": round(margin_pct, 1),
        "safe": safe
    }

def check_safe_lock_filter(win_prob):
    """Sprawdza czy sygnał kwalifikuje sie w biezacym stanie Safe-Lock."""
    cfg = load_risk_config()
    prob = int(win_prob or 0)
    if cfg.get("safe_lock_active", False):
        min_plat = int(cfg.get("min_platinum_prob", 68))
        if prob < min_plat:
            return False, f"SAFE-LOCK AKTYWNY (DD -{cfg.get('current_drawdown_pct', 0)}%): Wymagane PLATINUM >= {min_plat}%, otrzymano {prob}%"
        return True, "SAFE-LOCK PLATINUM OK"
    return True, "STANDBY NORMAL"
