import math, time

def quantum_wave_interference(side, entry, tp1, stop, kl_15m):
    """Symuluje interferencje fali prawdopodobienstwa ceny (Quantum Walk) wzgledem barier wolumenowych."""
    if not kl_15m or len(kl_15m.get("c", [])) < 30:
        return 0, "⚛️ Q-Wave neutral"
    c = [float(x) for x in kl_15m["c"][-30:]]
    v = [float(x) for x in kl_15m.get("v", [1.0]*len(c))[-30:]]
    avg_v = max(1e-9, sum(v) / len(v))
    td = 1 if side == "LONG" else -1
    phase_tp, phase_sl = 0.0, 0.0
    for i in range(len(c)):
        w = v[i] / avg_v
        d_tp = abs(c[i] - tp1) / max(1e-9, abs(tp1 - entry))
        d_sl = abs(c[i] - stop) / max(1e-9, abs(entry - stop))
        if d_tp < 0.35: phase_tp += w * math.cos(d_tp * math.pi)
        if d_sl < 0.35: phase_sl += w * math.cos(d_sl * math.pi)
    net_wave = round(phase_tp - phase_sl, 2)
    if net_wave >= 2.2:
        return 5, f"🌊 Q-Wave Konstruktywna (+{net_wave})"
    if net_wave <= -2.5:
        return -6, f"🌀 Q-Wave Bariera ({net_wave})"
    return 0, f"🌊 Q-Wave ({net_wave:+.1f})"

def detect_nash_predator_trap(side, kl_15m):
    """Teoria gier Nasha: wykrywa ksiazkowe pulapki zastawiane przez algorytmy na tlum detaliczny."""
    if not kl_15m or len(kl_15m.get("c", [])) < 15:
        return True, 0, "♟️ Nash OK"
    o, h, l, c = [float(x) for x in kl_15m["o"]], [float(x) for x in kl_15m["h"]], [float(x) for x in kl_15m["l"]], [float(x) for x in kl_15m["c"]]
    v = [float(x) for x in kl_15m.get("v", [1.0]*len(c))]
    avg_v = max(1e-9, sum(v[-15:-2]) / 13.0)
    rng = max(1e-9, h[-1] - l[-1])
    up_w = h[-1] - max(o[-1], c[-1])
    lo_w = min(o[-1], c[-1]) - l[-1]
    both_wicks = (up_w / rng > 0.32) and (lo_w / rng > 0.32)
    if v[-1] > avg_v * 2.8 and both_wicks:
        return False, -10, "🕸️ NASH PREDATOR TRAP (Czyszczenie SL obu stron)"
    return True, 2, "♟️ Nash Clean"

def liquid_decay_weight(sample_ts, half_life_hours=36.0):
    """Neuropamiec z zanikiem wykladniczym (Liquid Time-Constant): swieze wyniki maja 5x wieksza wage."""
    if not sample_ts:
        return 0.35
    age_h = max(0.0, (time.time() - float(sample_ts)) / 3600.0)
    return round(max(0.15, math.pow(0.5, age_h / max(1.0, half_life_hours))), 3)
