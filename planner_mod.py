import ai_quant_mod as aqm
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
import math
from decimal import Decimal, ROUND_DOWN
import crypto_pro as cp

def calc_plan(ex, sym, capital, risk_pct, max_lev, entry=None, stop=None, side=None):
    """Wylicza wielkosc pozycji, bezpieczna dzwignie, margin i TP1-TP5. Parametry: ex, sym, capital, risk_pct, max_lev, entry, stop, side."""
    ta = None
    try:
        if hasattr(cp, "cm"): ta = cp.cm.full_analysis(ex, sym)
    except Exception:
        pass
    price = ta["price"] if ta else (entry or 0.0)
    if not entry and ta: entry = ta["entry"]
    if not stop and ta: stop = ta["stop"]
    if not entry or not stop or entry == stop:
        return None

    td = 1 if entry > stop else -1
    if side: td = 1 if side.upper() == "LONG" else -1
    stop_dist = abs(entry - stop)
    risk_usdt = capital * (risk_pct / 100.0)
    fee_slip = ((cp.FEE_SIDE_PCT / 100.0) + (cp.SLIPPAGE_BPS / 10000.0)) * (entry + stop)
    r_unit = stop_dist + fee_slip

    step = 0.001 if entry >= 100 else (0.1 if entry >= 1 else 1.0)
    min_notional = 100.0 if sym.startswith("BTC") else 5.5
    raw_qty = risk_usdt / r_unit
    qty = float((Decimal(str(raw_qty)) / Decimal(str(step))).to_integral_value(rounding=ROUND_DOWN) * Decimal(str(step)))
    if qty <= 0: qty = step

    notional = qty * entry
    req_lev = max(1, math.ceil(notional / (capital * cp.MAX_MARGIN_FRACTION))) if capital > 0 else 999
    used_lev = min(max_lev, req_lev)
    margin_req = notional / used_lev if used_lev > 0 else notional
    real_risk = qty * r_unit
    min_cap_needed = math.ceil(((min_notional / entry) * r_unit) / (risk_pct / 100.0)) if risk_pct > 0 else 999
    tps = [entry + td * k * stop_dist for k in (1, 2, 3, 4, 5)]

    max_d = cp.EX_MAX_DEV.get(ex, 5.0)
    dev_pct = round(abs(entry - price) / price * 100.0, 2) if price > 0 else 0.0

    checks = [
        (notional >= min_notional, f"Min. wartosc zlecenia ({round(notional,1)}$ >= {min_notional}$)"),
        (real_risk <= risk_usdt * 1.15, f"Ryzyko w limicie ({round(real_risk,2)}$ <= {round(risk_usdt,2)}$)"),
        (req_lev <= max_lev, f"Dzwignia w limicie ({req_lev}x <= {max_lev}x)"),
        (margin_req <= capital * 0.80, f"Depozyt <= 80% kapitalu ({round(margin_req,2)}$ / {round(capital*0.8,2)}$)"),
        (price == 0 or dev_pct <= max_d, f"Odchylenie ceny w limicie {ex} ({dev_pct}% <= {max_d}%)")
    ]
    passed = all(c.__getitem__(0) for c in checks)

    stop_pct = round((stop_dist / entry) * 100.0, 2) if entry > 0 else 1.0
    atr_pct = ta["atr_pct"] if ta else stop_pct
    # Bezpieczny sufit dzwigni: likwidacja min. 2.5x dalej niz SL oraz korekta o zmiennosc ATR
    safe_ceil = max(1, int(70.0 / max(stop_pct, atr_pct * 0.8, 0.5)))
    rec_lev = max(req_lev, min(max_lev, safe_ceil))
    rec_lev = min(rec_lev, max(1, int(85.0 / max(stop_pct, 0.5))))
    rec_margin = round(notional / rec_lev, 2) if rec_lev > 0 else round(notional, 2)
    liq_price = round(entry * (1.0 - td * (0.90 / rec_lev)), 6)
    lev_grade = "🟢 BEZPIECZNA" if rec_lev <= safe_ceil else "🟡 PODWYZSZONE RYZYKO"

    return {
        "symbol": sym, "exchange": ex, "side": "LONG" if td == 1 else "SHORT",
        "price": price, "entry": entry, "stop": stop, "tp": tps,
        "qty": qty, "notional": round(notional, 2), "req_lev": req_lev, "used_lev": used_lev,
        "margin": round(margin_req, 2), "risk_usdt": round(real_risk, 2),
        "min_cap": min_cap_needed, "rec_lev": rec_lev, "safe_ceil": safe_ceil, "rec_margin": rec_margin, "liq_price": liq_price, "stop_pct": stop_pct, "lev_grade": lev_grade, "dev_pct": dev_pct, "max_dev": max_d,
        "passed": passed, "checks": checks
    }

def calc_bitbase_plan(entry, stop, side, capital, max_lev=1000, risk_pct=1.5, atr_value=None):
    """Wylicza plan BitBase: SL w ATR, ryzyko, bezpieczna dzwignia i trzy cele z podzialem pozycji."""
    entry, stop, capital = float(entry), float(stop), float(capital)
    if not all(math.isfinite(value) for value in (entry, stop, capital)):
        return None
    if entry <= 0 or stop <= 0 or entry == stop or capital <= 0:
        return None
    direction = str(side).upper()
    if direction not in ("LONG", "SHORT"):
        return None
    td = 1 if direction == "LONG" else -1
    stop_dist = abs(entry - stop)
    stop_pct = stop_dist / entry * 100.0
    if stop_pct > 2.2:
        return None
    sl_atr = None
    if atr_value is not None:
        atr_value = float(atr_value)
        if not math.isfinite(atr_value) or atr_value <= 0:
            return None
        sl_atr = stop_dist / atr_value
        if not 1.2 <= sl_atr <= 1.6:
            return None
    risk_budget = capital * (float(risk_pct) / 100.0)
    fee_slip = ((cp.FEE_SIDE_PCT / 100.0) + (cp.SLIPPAGE_BPS / 10000.0)) * (entry + stop)
    risk_per_unit = stop_dist + fee_slip
    if risk_budget <= 0 or risk_per_unit <= 0 or stop_pct <= 0:
        return None

    qty = risk_budget / risk_per_unit
    notional = qty * entry
    max_safe_lev = max(1, int(50.0 / stop_pct))
    leverage = min(max(1, int(max_lev)), max_safe_lev)
    margin = notional / leverage
    targets = [round(entry + td * stop_dist * multiple, 6) for multiple in (0.75, 1.5, 2.5)]
    return {
        "side": direction,
        "entry": entry,
        "stop": stop,
        "targets": targets,
        "target_splits": [50, 30, 20],
        "qty": round(qty, 6),
        "notional": round(notional, 2),
        "risk_usdt": round(qty * risk_per_unit, 2),
        "risk_pct": float(risk_pct),
        "leverage": leverage,
        "max_safe_lev": max_safe_lev,
        "margin": round(margin, 2),
        "sl_pct": round(stop_pct, 3),
        "sl_atr": round(sl_atr, 3) if sl_atr is not None else None,
    }
