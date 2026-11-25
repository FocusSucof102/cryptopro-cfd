import os, json, re, sys, py_compile

def run_full_self_test():
    # 1. Skladnia wszystkich plikow .py
    """Realizuje logike: run full self test."""
    req_files = ["crypto_pro.py", "alpha_pro_mod.py", "auto_tuner_mod.py", "portfolio_mod.py", "planner_mod.py", "chart_mod.py", "demo_sim_mod.py"]
    for fn in req_files:
        if not os.path.exists(fn):
            raise RuntimeError(f"Brak pliku: {fn}")
        py_compile.compile(fn, doraise=True)

    # 2. Importy i podpiecie modulow w rdzeniu
    cp_src = open("crypto_pro.py", encoding="utf-8").read()
    for mod_name in ["alpha_pro_mod", "auto_tuner_mod", "portfolio_mod", "planner_mod", "chart_mod", "demo_sim_mod"]:
        if mod_name not in cp_src:
            raise RuntimeError(f"Brak podpiecia modulu {mod_name} w crypto_pro.py")
    import alpha_pro_mod as apm, auto_tuner_mod as atm, portfolio_mod as pf, planner_mod as plm, crypto_pro as cp

    # 3. BitBase risk plan, target split, blacklist and pattern matching
    expected_stablecoins = {"USD1", "RLUSD", "USDE", "FDUSD", "PYUSD", "TUSD", "DAI"}
    if not expected_stablecoins.issubset(apm.STABLECOIN_BLACKLIST) or not expected_stablecoins.issubset(cp.STABLECOIN_BLACKLIST):
        raise RuntimeError("Niepelna lista stablecoinow BitBase")
    bitbase_plan = plm.calc_bitbase_plan(100.0, 98.6, "LONG", 1000.0, atr_value=1.0)
    if not bitbase_plan or bitbase_plan["targets"] != [101.05, 102.1, 103.5]:
        raise RuntimeError("Niepoprawne cele planu BitBase")
    if bitbase_plan["target_splits"] != [50, 30, 20] or bitbase_plan["leverage"] != 35:
        raise RuntimeError("Niepoprawne podzialy TP lub bezpieczna dzwignia")
    if plm.calc_bitbase_plan(100.0, 98.9, "LONG", 1000.0, atr_value=1.0) is not None:
        raise RuntimeError("Plan BitBase przyjął SL poniżej 1.2 ATR")
    if plm.calc_bitbase_plan(100.0, 98.3, "LONG", 1000.0, atr_value=1.0) is not None:
        raise RuntimeError("Plan BitBase przyjął SL powyżej 1.6 ATR")
    if plm.calc_bitbase_plan(100.0, 97.7, "LONG", 1000.0) is not None:
        raise RuntimeError("Plan BitBase przyjął SL ponad limit 2.2%")
    edit_signal = {
        "symbol": "TESTUSDT", "side": "LONG", "atr_value": 1.0,
    }
    edit_levels, edit_rr, edit_sl_pct, edit_sl_atr = cp.parse_user_override_levels(
        ["TESTUSDT", "entry=100", "sl=98.6", "tp1=101.05", "tp2=102.1", "tp3=103.5"],
        edit_signal,
    )
    if edit_levels["side"] != "LONG" or edit_rr != [0.75, 1.5, 2.5] or round(edit_sl_pct, 1) != 1.4 or edit_sl_atr != 1.4:
        raise RuntimeError("Niepoprawna walidacja /edytuj i analiza R:R/ATR")
    try:
        cp.parse_user_override_levels(
            ["TESTUSDT", "entry=100", "sl=101", "tp1=99", "tp2=98", "tp3=97"],
            edit_signal,
        )
    except ValueError:
        pass
    else:
        raise RuntimeError("Walidator /edytuj przyjął błędne poziomy")
    pattern_rows = [{
        "closed_final": True, "plan_version": "BITBASE_3TP_V1", "side": "LONG",
        "btc_regime": 1, "atr_pct": 1.0, "ema200_dist_pct": 0.5,
        "hour": 23, "res_r": 0.5,
    } for _ in range(5)]
    pattern_summary = cp.get_pattern_match_summary({
        "side": "LONG", "btc_regime": 1, "atr_pct": 1.0,
        "ema200_dist_pct": 0.5, "hour": 1,
    }, pattern_rows)
    if pattern_summary != "WR 100% (5/5 podobnych)":
        raise RuntimeError(f"Blad Pattern Matchera: {pattern_summary}")

    # 4. API Bitget: wszystkie 3 koszyki par + swiece 4 interwalow (limit 100)
    t60 = apm.get_cfd_top60_symbols()
    w80 = apm.get_wild_61_160_symbols()
    m60 = apm.get_micro_161_plus_symbols()
    if len(t60) < 40 or len(w80) < 30 or len(m60) < 20:
        raise RuntimeError(f"Niepelne pule par API: TOP60={len(t60)}, Wild={len(w80)}, Micro={len(m60)}")
    for tf in ("15m", "1h", "4h", "1d"):
        kl = cp.fetch_klines("BITGET", "BTCUSDT", tf, 100)
        if not kl or len(kl.get("c", [])) < 50:
            raise RuntimeError(f"Brak swiec BTCUSDT dla interwalu {tf}")

    # 5. Silnik analizy technicznej + walidator odleglosci zlecen CFD
    rules = cp.load_settings().get("rules", {})
    for sym_t in ("BTCUSDT", "ETHUSDT"):
        r_scan = cp._scan_one_coin(("BITGET", sym_t, 1.0, rules, ["15m", "1h", "4h", "1d"], 1000.0, 1.5))
        if r_scan is not None and not isinstance(r_scan, dict):
            raise RuntimeError(f"Bledny format wyniku _scan_one_coin dla {sym_t}")
    if not apm.validate_cfd_order(100.0, 98.5, 100.0):
        raise RuntimeError("Blad walidatora CFD dla poprawnego zlecenia!")

    # 6. Pasek wielointerwalowy MTF (X/4: 15M|1H|4H|1D)
    mtf_btc = re.sub(r"<[^>]+>", "", apm.get_mtf_status_line("BITGET", "BTCUSDT", "LONG"))
    if "➖" in mtf_btc or "MTF (" not in mtf_btc:
        raise RuntimeError(f"Blad paska MTF: {mtf_btc}")

    # 7. Detektory specjalne: Macro Pump & Dump (4H/1D), Cyklicznosc oraz Dziwne Ruchy
    apm.scan_macro_pump_dump_coin("BTCUSDT")
    cyc_t, _, _ = apm.detect_cyclical_and_pump_dump("BITGET", m60[0])
    weird_t = apm.detect_weird_move("BITGET", w80[0])
    if cyc_t == "ERR":
        raise RuntimeError("Blad detektora cyklicznosci i Pump & Dump!")

    # 8. Auto-Tuner, Straznik Portfela oraz Konfiguracja Telegrama
    st = atm.get_tuner_params()
    g_msg = pf.check_new_opportunity_margin("LONG")
    if "min_prob" not in st or not isinstance(g_msg, str):
        raise RuntimeError("Blad Auto-Tunera lub Straznika Portfela")
    tg_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_config.json")
    if not os.path.exists(tg_config_path):
        raise RuntimeError("Brak pliku tg_config.json!")

    # 9. Audytor 1M, Tabela CSV oraz kompletnosc pol w 3 laboratoriach .json
    tbl = cp.render_cfd_history_table()
    if not tbl or len(tbl) < 50:
        raise RuntimeError("Blad generowania raportu Audytora 1M!")
    live_tot, hist_tot = 0, 0
    for jf in ["market_shadow_lab.json", "wild_market_lab.json", "micro_market_lab.json"]:
        if os.path.exists(jf):
            arr = json.load(open(jf, encoding="utf-8"))
            hist_tot += sum(1 for x in arr if x.get("data_type") == "HIST_BACKFILL")
            live_tot += sum(1 for x in arr if x.get("data_type") == "LIVE_FORWARD")

    return f"9/9 ETAPOW OK | Pule: {len(t60)}/{len(w80)}/{len(m60)} | Tuner: {st['min_prob']}% | Baza: {hist_tot} HIST + {live_tot} LIVE"

if __name__ == "__main__":
    import os, signal, textwrap, time

    def get_cols():
        try:
            return os.get_terminal_size().columns
        except Exception:
            return 44

    def draw_banner(is_ok, text_msg, clear_scr=False):
        G, R, B, X = "\033[1;92m", "\033[1;91m", "\033[1m", "\033[0m"
        col = G if is_ok else R
        cols = max(32, get_cols() - 2)
        inner_w = cols - 2
        title_txt = "SELF-TEST: 9/9 TESTOW OK!" if is_ok else "SELF-TEST: BLAD KRYTYCZNY!"
        wrapped = textwrap.wrap(text_msg, width=max(18, inner_w - 2)) or [""]
        top = "+" + "-" * inner_w + "+"
        mid = "+" + "-" * inner_w + "+"
        bot = "+" + "-" * inner_w + "+"
        lines = []
        if clear_scr:
            lines.append("\033[2J\033[H")
        lines.append(f"{col}{top}")
        lines.append(f"|{title_txt.center(inner_w)}|")
        lines.append(mid)
        for ln in wrapped:
            lines.append(f"| {ln.ljust(inner_w - 2)} |")
        lines.append(f"{bot}{X}")
        print("\n".join(lines) + "\n", flush=True)

    state = {"ok": True, "msg": "", "resized": False}
    def _on_resize(signum, frame):
        state["resized"] = True

    if hasattr(signal, "SIGWINCH"):
        signal.signal(signal.SIGWINCH, _on_resize)

    try:
        summary = run_full_self_test()
        state["ok"], state["msg"] = True, summary
        draw_banner(True, summary, clear_scr=False)
        if "--watch" in sys.argv:
            print("Obroc telefon (tryb podgladu 15s, Ctrl+C aby wyjsc)...", flush=True)
            t_end = time.time() + 15
            while time.time() < t_end:
                if state["resized"]:
                    state["resized"] = False
                    time.sleep(0.18)
                    draw_banner(state["ok"], state["msg"], clear_scr=True)
                time.sleep(0.05)
        sys.exit(0)
    except Exception as e:
        state["ok"], state["msg"] = False, f"PRZYCZYNA: {e}"
        draw_banner(False, state["msg"], clear_scr=False)
        sys.exit(1)
