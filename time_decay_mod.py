import os
import json
import re
import walk_forward_mod as wf

STATE_FILE = "time_decay_state.json"
SHADOW_LAB = "market_shadow_lab.json"

DEFAULT_CUTOFF_MINUTES = 360

def parse_duration_to_minutes(dur_str):
    """Konwertuje napis czasu trwania np. '150m' lub '12h' na liczbe minut."""
    if not dur_str:
        return 0
    s = str(dur_str).strip().lower()
    m_match = re.search(r"(\d+)\s*m", s)
    h_match = re.search(r"(\d+)\s*h", s)
    if m_match:
        return int(m_match.group(1))
    if h_match:
        return int(h_match.group(1)) * 60
    digits = re.findall(r"\d+", s)
    return int(digits[0]) if digits else 0

def compute_survival_curve(samples=None):
    """Wylicza empiryczna krzywa przezywalnosci pozycji i oczekiwany zwrot w czasie."""
    if samples is None:
        if os.path.exists(SHADOW_LAB):
            try:
                samples = json.load(open(SHADOW_LAB, encoding="utf-8"))
            except Exception:
                samples = []
        else:
            samples = []

    closed = [s for s in (samples or []) if s.get("closed_final")]
    buckets = {
        "0-90m": {"trades": 0, "wins": 0, "r_sum": 0.0},
        "91-240m": {"trades": 0, "wins": 0, "r_sum": 0.0},
        "241-480m": {"trades": 0, "wins": 0, "r_sum": 0.0},
        "481m+": {"trades": 0, "wins": 0, "r_sum": 0.0}
    }

    for t in closed:
        dur = parse_duration_to_minutes(t.get("dur_str", "0m"))
        r_val = float(t.get("res_r", 0.0)) - 0.07
        b_key = "0-90m" if dur <= 90 else ("91-240m" if dur <= 240 else ("241-480m" if dur <= 480 else "481m+"))
        buckets[b_key]["trades"] += 1
        buckets[b_key]["r_sum"] += r_val
        if r_val > 0:
            buckets[b_key]["wins"] += 1

    summary = {}
    optimal_cutoff = DEFAULT_CUTOFF_MINUTES
    for k, v in buckets.items():
        cnt = v["trades"]
        wr = round((v["wins"] / max(1, cnt)) * 100.0, 1)
        avg_r = round(v["r_sum"] / max(1, cnt), 3)
        summary[k] = {"count": cnt, "wr": wr, "avg_net_r": avg_r}

    # Jesli najdluzsze pozycje przynosza ujemna srednia, ucinamy w optymalnym punkcie
    if summary["481m+"]["avg_net_r"] < 0:
        optimal_cutoff = 360

    return {"buckets": summary, "optimal_cutoff_min": optimal_cutoff, "total_closed": len(closed)}

def apply_time_decay_to_samples(samples, cutoff_minutes=DEFAULT_CUTOFF_MINUTES):
    """Symuluje wyjscie TIME_DECAY_EXIT dla pozycji przeciagajacych sie bez dynamiki."""
    modified = []
    for t in samples:
        cp = dict(t)
        dur = parse_duration_to_minutes(cp.get("dur_str", "0m"))
        status = str(cp.get("status", ""))
        r_val = float(cp.get("res_r", 0.0))
        # Jesli transakcja trwala dluzej niz cutoff i nie osiagnela pelnego TP (TP3+)
        if dur >= cutoff_minutes and "TP3" not in status and "TP4" not in status and "TP5" not in status:
            mfe = float(cp.get("mfe_r", 0.0))
            if mfe >= 0.8:
                cp["res_r"] = 0.35 # Awaryjny Break-Even czasowy
                cp["status"] = "⏳ TIME_DECAY_BE"
            elif r_val < 0:
                cp["res_r"] = -0.50 # Wczesne ciecie przeciagnietej straty
                cp["status"] = "⏳ TIME_DECAY_CUT"
        modified.append(cp)
    return modified

def test_time_decay_walk_forward():
    """Weryfikuje hipoteze Time Decay w Walk-Forward i Monte Carlo."""
    samples = json.load(open(SHADOW_LAB, encoding="utf-8")) if os.path.exists(SHADOW_LAB) else []
    closed = [s for s in samples if s.get("closed_final")]
    if len(closed) < 12:
        return {
            "active": False,
            "reason": "Za mało próbek do egzaminu OOS",
            "base_oos_r": 0.0,
            "decay_oos_r": 0.0,
            "mc_pass_pct": 0.0
        }

    # 1. Wynik bazowy
    (base_wf_ok, base_wf), (base_mc_ok, base_mc) = wf.run_purged_walk_forward(closed), wf.run_monte_carlo_stress(closed)
    base_oos_r = float(base_wf.get("oos_net_r", 0.0))

    # 2. Wynik z regułą TIME_DECAY_EXIT
    decay_samples = apply_time_decay_to_samples(closed, DEFAULT_CUTOFF_MINUTES)
    (dec_wf_ok, dec_wf), (dec_mc_ok, dec_mc) = wf.run_purged_walk_forward(decay_samples), wf.run_monte_carlo_stress(decay_samples)
    dec_oos_r = float(dec_wf.get("oos_net_r", 0.0))
    dec_mc_pct = float(dec_mc.get("pass_pct", 0.0))

    # Wdrozyc do produkcji TYLKO jesli pobije wynik OOS bazy przy Monte Carlo >= 85%
    approved = bool(dec_oos_r >= base_oos_r and dec_mc_pct >= 85.0)

    res = {
        "active": approved,
        "cutoff_minutes": DEFAULT_CUTOFF_MINUTES,
        "base_oos_net_r": base_oos_r,
        "decay_oos_net_r": dec_oos_r,
        "decay_mc_pass_pct": dec_mc_pct,
        "beats_baseline": dec_oos_r >= base_oos_r,
        "verdict": "APPROVED_FOR_PROD" if approved else "KEPT_AS_RESEARCH"
    }

    try:
        json.dump(res, open(STATE_FILE, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass
    return res

def should_time_decay_exit(opened_ts, current_mfe_r=0.0):
    """Sprawdza w czasie rzeczywistym czy pozycja powinna zostac zamknieta czasowo."""
    import time
    st = {}
    if os.path.exists(STATE_FILE):
        try:
            st = json.load(open(STATE_FILE, encoding="utf-8"))
        except Exception:
            pass
    if not st.get("active", False):
        return False, "TIME_DECAY_INACTIVE"

    cutoff_sec = int(st.get("cutoff_minutes", DEFAULT_CUTOFF_MINUTES)) * 60
    elapsed_sec = time.time() - float(opened_ts or time.time())
    if elapsed_sec >= cutoff_sec and float(current_mfe_r) < 1.0:
        return True, f"EXIT_TIME_DECAY: {int(elapsed_sec / 60)}m >= {int(cutoff_sec / 60)}m bez TP"
    return False, "HOLD_OK"
