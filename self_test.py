import os, json, re, sys, py_compile

def run_full_self_test():
    # 1. Skladnia wszystkich plikow .py
    for fn in ["crypto_pro.py", "alpha_pro_mod.py", "auto_tuner_mod.py", "portfolio_mod.py", "planner_mod.py", "chart_mod.py", "demo_sim_mod.py"]:
        if not os.path.exists(fn):
            raise RuntimeError(f"Brak wymaganego pliku: {fn}")
        py_compile.compile(fn, doraise=True)

    # 2. Importy i integracja modulow
    import alpha_pro_mod as apm, auto_tuner_mod as atm, portfolio_mod as pf, planner_mod as plm, crypto_pro as cp

    # 3. Test API Bitget (pobieranie wszystkich 3 pul par oraz swiec)
    t60 = apm.get_cfd_top60_symbols()
    w80 = apm.get_wild_61_160_symbols()
    m60 = apm.get_micro_161_plus_symbols()
    kl = cp.fetch_klines("BITGET", "BTCUSDT", "15m", 100)
    if len(t60) < 40 or len(w80) < 30 or len(m60) < 20 or not kl or len(kl.get("c", [])) < 20:
        raise RuntimeError(f"Blad danych API Bitget: TOP60={len(t60)}, Wild={len(w80)}, Micro={len(m60)}")

    # 4. Test silnika analizy, MTF (X/4) oraz detektora Pump & Dump
    mtf_btc = re.sub(r"<[^>]+>", "", apm.get_mtf_status_line("BITGET", "BTCUSDT", "LONG"))
    if "➖" in mtf_btc or "MTF (" not in mtf_btc:
        raise RuntimeError(f"Blad paska MTF: {mtf_btc}")
    apm.scan_macro_pump_dump_coin("BTCUSDT")

    # 5. Test Auto-Tunera i Straznika Portfela
    st = atm.get_tuner_params()
    g_msg = pf.check_new_opportunity_margin("LONG")
    if "min_prob" not in st or not isinstance(g_msg, str):
        raise RuntimeError("Blad Auto-Tunera lub Straznika Portfela")

    # 6. Kontrola integralnosci plikow laboratoriow badawczych (.json)
    live_tot, hist_tot = 0, 0
    for jf in ["market_shadow_lab.json", "wild_market_lab.json", "micro_market_lab.json"]:
        if os.path.exists(jf):
            arr = json.load(open(jf, encoding="utf-8"))
            hist_tot += sum(1 for x in arr if x.get("data_type") == "HIST_BACKFILL")
            live_tot += sum(1 for x in arr if x.get("data_type") == "LIVE_FORWARD")

    return f"6/6 ETAPOW OK | Pule: {len(t60)}/{len(w80)}/{len(m60)} | Tuner: {st['min_prob']}% | Baza: {hist_tot} HIST + {live_tot} LIVE"

if __name__ == "__main__":
    try:
        summary = run_full_self_test()
        print(f"✅ [SELF-TEST] {summary}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ [SELF-TEST BLAD KRYTYCZNY] {e}")
        sys.exit(1)
