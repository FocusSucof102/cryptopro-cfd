import os, json, math, random

def run_purged_walk_forward(samples, split_ratio=0.70, purge_gap=4):
    """Dzieli probki na okno treningowe (70%), bufor purge_gap oraz egzamin Out-of-Sample (30%)."""
    closed = [r for r in samples if r.get("closed_final")]
    if len(closed) < 12:
        return False, {"reason": f"Za malo probek ({len(closed)} < 12)", "oos_net_r": 0.0}
    cut = int(len(closed) * split_ratio)
    train = closed.__getitem__(slice(0, max(1, cut - purge_gap)))
    oos = closed.__getitem__(slice(min(len(closed), cut + purge_gap), None))
    if not oos:
        return False, {"reason": "Brak probek w oknie Out-of-Sample", "oos_net_r": 0.0}
    train_r = round(sum(float(x.get("res_r", 0)) - 0.07 for x in train), 2)
    oos_r = round(sum(float(x.get("res_r", 0)) - 0.07 for x in oos), 2)
    oos_wr = round(sum(1 for x in oos if float(x.get("res_r", 0)) > 0.07) / len(oos) * 100.0, 1)
    ok = (oos_r > 0.0 and oos_wr >= 42.0)
    return ok, {"train_n": len(train), "train_r": train_r, "oos_n": len(oos), "oos_net_r": oos_r, "oos_wr": oos_wr}

def run_monte_carlo_stress(samples, runs=100, extra_slip_r=0.04):
    """Symuluje 100 losowych przebiegow z dodatkowym poslizgiem i 10% pominietych wejsc."""
    closed = [float(r.get("res_r", 0)) - 0.07 for r in samples if r.get("closed_final")]
    if len(closed) < 10:
        return False, {"pass_pct": 0.0, "worst_dd_r": 0.0}
    rng = random.Random(42)
    prof_runs, max_dds = 0, []
    for _ in range(runs):
        seq = [x - rng.uniform(0.0, extra_slip_r) for x in closed if rng.random() > 0.10]
        rng.shuffle(seq)
        eq, pk, mdd = 0.0, 0.0, 0.0
        for v in seq:
            eq += v
            if eq > pk: pk = eq
            if pk - eq > mdd: mdd = pk - eq
        if eq > 0: prof_runs += 1
        max_dds.append(mdd)
    pass_pct = round((prof_runs / runs) * 100.0, 1)
    worst_dd = round(max(max_dds) if max_dds else 0.0, 2)
    return pass_pct >= 80.0, {"pass_pct": pass_pct, "worst_dd_r": worst_dd}
