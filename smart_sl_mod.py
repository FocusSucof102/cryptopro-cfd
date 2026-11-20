def compute_smart_sl(side, entry, cur_price, cur_sl, atr_1h, bos_hi, bos_lo, lev):
    """Wylicza optymalny SL laczacy: strukture SMC, 1.8x ATR, Break-Even +0.12R, Trailing 2.2x ATR i bezpieczenstwo likwidacji."""
    td = 1 if side == "LONG" else -1
    sd_init = abs(entry - cur_sl) or max(entry * 0.01, atr_1h * 1.5)
    cur_r = (td * (cur_price - entry)) / sd_init

    # 1. Poziom strukturalny SMC (za ostatnim dolkiem/szczytem + bufor 0.35 ATR)
    smc_sl = (bos_lo - 0.35 * atr_1h) if td == 1 else (bos_hi + 0.35 * atr_1h)
    # 2. Poziom zmiennosciowy (1.8x ATR od wejscia)
    atr_sl = entry - td * 1.8 * atr_1h
    # 3. Bezpiecznik przed cena likwidacji (max 65% dystansu do likwidacji)
    safe_liq_dist = entry * (0.65 / max(1, int(lev)))
    liq_guard_sl = entry - td * safe_liq_dist

    if cur_r >= 2.0:
        prop_sl = cur_price - td * 2.2 * atr_1h
        reason = f"Trailing Stop 2.2x ATR (zysk +{cur_r:.1f}R)"
    elif cur_r >= 1.0:
        prop_sl = entry + td * 0.12 * sd_init
        reason = f"Break-Even+ (+0.12R na pokrycie prowizji BitBase)"
    else:
        raw_sl = min(smc_sl, atr_sl) if td == 1 else max(smc_sl, atr_sl)
        prop_sl = max(raw_sl, liq_guard_sl) if td == 1 else min(raw_sl, liq_guard_sl)
        reason = "Struktura SMC + 1.8x ATR (zabezpieczony przed likwidacja)"

    # SL przesuwamy wylacznie w strone zysku (nigdy nie oddalamy ryzyka)
    if td == 1:
        final_sl = max(cur_sl, prop_sl) if cur_r >= 1.0 else prop_sl
    else:
        final_sl = min(cur_sl, prop_sl) if cur_r >= 1.0 else prop_sl
    return round(final_sl, 6), reason
