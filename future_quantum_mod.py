import math

def calc_shannon_entropy(kl_15m):
    """Oblicza Entropie Shannona (stopien chaosu rynku 0.0-1.0) z ostatnich 30 swiec."""
    if not kl_15m or len(kl_15m.get("c", [])) < 30:
        return 0.5, True, "⚛️ Entropia standard"
    c = [float(x) for x in kl_15m["c"][-30:]]
    rets = [(c[i] - c[i-1]) / max(1e-9, c[i-1]) for i in range(1, len(c))]
    bins = list((0, 0, 0, 0, 0))
    for r in rets:
        idx = 0 if r < -0.004 else (1 if r < -0.001 else (2 if r <= 0.001 else (3 if r <= 0.004 else 4)))
        bins[idx] += 1
    tot = len(rets)
    ent = -sum((b / tot) * math.log2(b / tot) for b in bins if b > 0) / math.log2(5)
    if ent > 0.91:
        return round(ent, 2), False, f"⚛️ ENTROPY LOCK (Chaos {ent:.2f})"
    if ent < 0.68:
        return round(ent, 2), True, f"⚛️ Niska Entropia ({ent:.2f} — wysoka struktura)"
    return round(ent, 2), True, f"⚛️ Entropia {ent:.2f}"

def detect_whale_iceberg_and_redteam(side, kl_15m, funding_pct=0.0):
    """Wykrywa cicha absorpcje wielorybow (Iceberg) oraz przeprowadza 5-punktowy audyt Red-Team AI."""
    if not kl_15m or len(kl_15m.get("c", [])) < 20:
        return True, 0, "🛡️ Red-Team OK"
    o, h, l, c = [float(x) for x in kl_15m["o"]], [float(x) for x in kl_15m["h"]], [float(x) for x in kl_15m["l"]], [float(x) for x in kl_15m["c"]]
    v = [float(x) for x in kl_15m.get("v", [1.0]*len(c))]
    avg_v = sum(v[-20:-2]) / 18.0
    avg_rng = sum(h[i]-l[i] for i in range(-20, -2)) / 18.0
    last_body = abs(c[-1] - o[-1])
    iceberg = (v[-1] > avg_v * 3.2) and (last_body < avg_rng * 0.35)

    # Red-Team AI (szuka kontrargumentow przeciw transakcji)
    flags = 0
    if side == "LONG" and funding_pct > 0.045: flags += 1
    if side == "SHORT" and funding_pct < -0.045: flags += 1
    if side == "LONG" and c[-1] < c[-6] and c[-2] < c[-7]: flags += 1
    if side == "SHORT" and c[-1] > c[-6] and c[-2] > c[-7]: flags += 1
    if (h[-1] - l[-1]) > avg_rng * 3.0: flags += 1

    if flags >= 3:
        return False, -10, f"🔴 Red-Team VETO ({flags} kontrargumenty)"
    bonus = (6 if iceberg else 0) + (3 if flags == 0 else 0)
    tag = ("🐋 WHALE ICEBERG | " if iceberg else "") + (f"🛡️ Red-Team ({flags} uwag)" if flags else "🛡️ Red-Team CLEARED")
    return True, bonus, tag
