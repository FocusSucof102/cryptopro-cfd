import os, json, time
from datetime import datetime

TUNER_FILE = "tuner_state.json"

def get_tier_label(prob):
    """Realizuje logike: get tier label. Parametry: prob."""
    p = int(prob or 0)
    if p >= 68: return "💎 PLATINUM (68%+)"
    if p >= 60: return "🥇 GOLD (60-67%)"
    if p >= 52: return "🥈 SILVER (52-59%)"
    return "🥉 BRONZE (45-51%)"

def get_tuner_params():
    """Realizuje logike: get tuner params."""
    default = {
        "min_prob": 60,
        "sl_mult": 1.0,
        "active_tiers": ["PLATINUM", "GOLD"],
        "last_tune_ts": 0,
        "notes": "Tryb Wielopoziomowy: skan 45-100% aktywny"
    }
    if os.path.exists(TUNER_FILE):
        try: default.update(json.load(open(TUNER_FILE)))
        except Exception: pass
    return default

def run_auto_tuner(hist_file="cfd_live_history.json"):
    """Kalibruje prog min_prob i bufor SL na bazie wynikow 1m. Parametry: hist_file."""
    st = get_tuner_params()
    now = time.time()
    if now - st.get("last_tune_ts", 0) < 1800:
        return st, None

    # Sprawdzamy wyniki LIVE ze wszystkich poziomow (cfd_live_history + market_shadow_lab)
    samples = []
    for fn in (hist_file, "market_shadow_lab.json"):
        if os.path.exists(fn):
            try:
                for r in json.load(open(fn)):
                    if r.get("closed_final") and r.get("data_type", "LIVE_FORWARD") == "LIVE_FORWARD":
                        samples.append(r)
            except Exception: pass

    silver_live = [r for r in samples if 52 <= int(r.get("prob", 0)) <= 59]
    gold_live = [r for r in samples if int(r.get("prob", 0)) >= 60]
    reason = None

    # Automatyczne odblokowanie poziomu SILVER (52-59%), jesli na zywo zarabia netto po prowizji (-0.07R)
    if len(silver_live) >= 8:
        net_silver = sum(float(r.get("res_r", 0)) - 0.07 for r in silver_live[-20:])
        if net_silver > 0.5 and st["min_prob"] > 52:
            st["min_prob"] = 52
            st["active_tiers"] = ["PLATINUM", "GOLD", "SILVER"]
            reason = f"Poziom SILVER (52-59%) zarabia netto ({net_silver:+.2f}R) -> wlaczono alerty od 52%!"
        elif net_silver < -1.0 and st["min_prob"] < 60:
            st["min_prob"] = 60
            st["active_tiers"] = ["PLATINUM", "GOLD"]
            reason = f"Poziom SILVER na minusie ({net_silver:+.2f}R) -> powrot alertow do GOLD (60%+)"

    # Kalibracja bufora SL na podstawie szpilek w zamknietych pozycjach
    if len(gold_live) >= 6:
        sample = gold_live[-15:]
        sl_hits = sum(1 for r in sample if str(r.get("status", "")) == "❌ SL")
        if sl_hits / len(sample) > 0.65 and st["sl_mult"] < 1.35:
            st["sl_mult"] = round(min(1.35, st["sl_mult"] + 0.08), 2)
            reason = f"Wysoki odsetek SL ({sl_hits}/{len(sample)}) -> bufor SL {st['sl_mult']}x"

    st["last_tune_ts"] = now
    if reason:
        st["notes"] = f"[{datetime.now().strftime('%d.%m %H:%M')}] {reason}"
    json.dump(st, open(TUNER_FILE, "w"), indent=2)
    return st, reason
