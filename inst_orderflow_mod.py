import json, urllib.request
from datetime import datetime, timezone

def check_macro_volatility_shield():
    """Sprawdza okna publikacji danych makro USA (14:30 CET CPI/NFP oraz 20:00 CET FOMC)."""
    now_local = datetime.now()
    wd = now_local.weekday()
    mins = now_local.hour * 60 + now_local.minute
    if wd < 5:
        if 840 <= mins <= 900:
            return True, "⚠️ OKNO DANYCH USA (14:00-15:00 CET — możliwe szpilki CPI/NFP)"
        if wd == 2 and 1170 <= mins <= 1245:
            return True, "⚠️ OKNO FED / FOMC (19:30-20:45 CET — ekstremalna zmienność)"
    return False, "🟢 Makro stabilne"

def get_orderflow_and_walls(sym, side, entry, tp1):
    """Analizuje arkusz zlecen Bitget (Imbalance % + sciany plynnosci) oraz delte Taker Buy/Sell."""
    try:
        u_ob = "".join(["https://bitget.com", "/api/v2/mix/market/merge-depth?productType=USDT-FUTURES&symbol=", sym, "&limit=20"])
        ob = json.loads(urllib.request.urlopen(u_ob, timeout=6).read().decode()).get("data", {})
        bids = [(float(x.__getitem__(0)), float(x.__getitem__(1))) for x in ob.get("bids", [])]
        asks = [(float(x.__getitem__(0)), float(x.__getitem__(1))) for x in ob.get("asks", [])]
        if not bids or not asks:
            return True, 0, "Orderbook brak danych"
        b_vol = sum(p * q for p, q in bids)
        a_vol = sum(p * q for p, q in asks)
        imb_pct = round(((b_vol - a_vol) / max(1.0, b_vol + a_vol)) * 100.0, 1)
        avg_wall = (b_vol + a_vol) / max(1, len(bids) + len(asks))
        if side == "LONG":
            wall_hit = any(p <= tp1 and (p * q) > avg_wall * 4.5 for p, q in asks)
            if wall_hit: return False, -10, f"🧱 Sell Wall przed TP1 (Imb {imb_pct:+.0f}%)"
            bonus = 5 if imb_pct >= 18 else (0 if imb_pct >= -20 else -5)
            return True, bonus, f"📚 OB Imb {imb_pct:+.0f}%"
        else:
            wall_hit = any(p >= tp1 and (p * q) > avg_wall * 4.5 for p, q in bids)
            if wall_hit: return False, -10, f"🧱 Buy Wall przed TP1 (Imb {imb_pct:+.0f}%)"
            bonus = 5 if imb_pct <= -18 else (0 if imb_pct <= 20 else -5)
            return True, bonus, f"📚 OB Imb {imb_pct:+.0f}%"
    except Exception:
        return True, 0, "OB neutralny"
