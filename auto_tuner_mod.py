import os, json, time
from datetime import datetime

TUNER_FILE = "tuner_state.json"

def get_tier_label(prob):
    """Przypisuje etykiete poziomu jakosci (PLATINUM, GOLD, SILVER, BRONZE). Parametry: prob."""
    p = int(prob or 0)
    if p >= 68: return "💎 PLATINUM (68%+)"
    if p >= 60: return "🥇 GOLD (60-67%)"
    if p >= 52: return "🥈 SILVER (52-59%)"
    return "🥉 BRONZE (45-51%)"

def get_tuner_params():
    """Wczytuje aktualne nastawy wielopoziomowego Auto-Tunera z tuner_state.json."""
    default = {
        "min_prob": 58,
        "scan_floor": 45,
        "sl_mult": 1.0,
        "active_tiers": ["PLATINUM", "GOLD"],
        "last_tune_ts": 0,
        "notes": "Skan 45-100% (4 poziomy) | Alerty od 58%"
    }
    if os.path.exists(TUNER_FILE):
        try: default.update(json.load(open(TUNER_FILE, encoding="utf-8")))
        except Exception: pass
    return default

def get_all_tiers_summary():
    """Zwraca krotki raport liczby probek i wyniku netto (-0.07R) dla wszystkich 4 poziomow."""
    samples = []
    for fn in ("cfd_live_history.json", "market_shadow_lab.json"):
        if os.path.exists(fn):
            try:
                for r in json.load(open(fn, encoding="utf-8")):
                    if r.get("closed_final"): samples.append(r)
            except Exception: pass
    tiers = [("💎PLAT", 68, 100), ("🥇GOLD", 60, 67), ("🥈SILV", 52, 59), ("🥉BRON", 45, 51)]
    parts = []
    for lbl, lo, hi in tiers:
        sub = [r for r in samples if lo <= int(r.get("prob", 0)) <= hi]
        net = round(sum(float(r.get("res_r", 0)) - 0.07 for r in sub), 1)
        parts.append(f"{lbl}:{len(sub)}({net:+.1f}R)")
    return " | ".join(parts)

def run_auto_tuner(hist_file="cfd_live_history.json"):
    """Kalibruje prog alertow i bufor SL na podstawie wynikow LIVE ze wszystkich 4 poziomow. Parametry: hist_file."""
    st = get_tuner_params()
    st["scan_floor"] = 45
    now = time.time()
    if now - st.get("last_tune_ts", 0) < 1800:
        return st, None

    samples = []
    for fn in (hist_file, "market_shadow_lab.json"):
        if os.path.exists(fn):
            try:
                for r in json.load(open(fn, encoding="utf-8")):
                    if r.get("closed_final") and r.get("data_type", "LIVE_FORWARD") == "LIVE_FORWARD":
                        samples.append(r)
            except Exception: pass

    bronze_live = [r for r in samples if 45 <= int(r.get("prob", 0)) <= 51]
    silver_live = [r for r in samples if 52 <= int(r.get("prob", 0)) <= 59]
    gold_live = [r for r in samples if int(r.get("prob", 0)) >= 60]
    reason = None

    if len(bronze_live) >= 10 and sum(float(r.get("res_r", 0)) - 0.07 for r in bronze_live[-20:]) > 1.0:
        st["min_prob"] = 45
        st["active_tiers"] = ["PLATINUM", "GOLD", "SILVER", "BRONZE"]
        reason = "Poziom BRONZE (45-51%) zarabia netto -> odblokowano alerty na wszystkich 4 poziomach!"
    elif len(silver_live) >= 8:
        net_silver = sum(float(r.get("res_r", 0)) - 0.07 for r in silver_live[-20:])
        if net_silver > 0.5 and st["min_prob"] > 52:
            st["min_prob"] = 52
            st["active_tiers"] = ["PLATINUM", "GOLD", "SILVER"]
            reason = f"Poziom SILVER (52-59%) zarabia netto ({net_silver:+.2f}R) -> wlaczono alerty od 52%!"
        elif net_silver < -1.0 and st["min_prob"] < 58:
            st["min_prob"] = 58
            st["active_tiers"] = ["PLATINUM", "GOLD"]
            reason = f"Poziom SILVER na minusie ({net_silver:+.2f}R) -> alerty tylko PLATINUM/GOLD (58%+)"

    if len(gold_live) >= 6:
        sample = gold_live[-15:]
        sl_hits = sum(1 for r in sample if str(r.get("status", "")) == "❌ SL")
        if sl_hits / len(sample) > 0.65 and st["sl_mult"] < 1.35:
            st["sl_mult"] = round(min(1.35, st["sl_mult"] + 0.08), 2)
            reason = f"Wysoki odsetek SL ({sl_hits}/{len(sample)}) -> bufor SL {st['sl_mult']}x"

    st["last_tune_ts"] = now
    if reason:
        st["notes"] = f"[{datetime.now().strftime('%d.%m %H:%M')}] {reason}"
    json.dump(st, open(TUNER_FILE, "w", encoding="utf-8"), indent=2)
    return st, reason
