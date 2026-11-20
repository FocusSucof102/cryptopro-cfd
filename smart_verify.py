import os, re, sys, json, glob, traceback, py_compile

def run_smart_audit():
    # Etap 1: Kontrola pustych plikow (0B / uszkodzony rozmiar) oraz skladni .py
    req = ["crypto_pro.py", "alpha_pro_mod.py", "auto_tuner_mod.py", "portfolio_mod.py",
           "planner_mod.py", "chart_mod.py", "demo_sim_mod.py", "web_pump_radar_mod.py",
           "contract_audit_mod.py", "web_ui_mod.py", "self_test.py", "README.md", "CHANGELOG.md"]
    for fn in req:
        if not os.path.exists(fn):
            raise FileNotFoundError(f"Brak wymaganego pliku: {fn}")
        if os.path.getsize(fn) < 50:
            raise RuntimeError(f"Cichy defekt: plik '{fn}' jest pusty lub uciety ({os.path.getsize(fn)} B)!")
        if fn.endswith(".py"):
            py_compile.compile(fn, doraise=True)

    # Etap 2: Kontrola spojnosci wszystkich plikow .json (brak pustych lub uszkodzonych baz)
    for jf in ["tg_config.json", "tuner_state.json", "market_shadow_lab.json", "wild_market_lab.json", "micro_market_lab.json"]:
        if not os.path.exists(jf) or os.path.getsize(jf) < 2:
            raise RuntimeError(f"Cichy defekt: brak lub pusty plik danych '{jf}'!")
        try:
            data_j = json.load(open(jf, encoding="utf-8"))
        except Exception as je:
            raise RuntimeError(f"Uszkodzony format JSON w '{jf}': {je}")
        if jf == "tg_config.json" and (not data_j.get("token") or not data_j.get("chat_id")):
            raise RuntimeError("Cichy defekt: puste pole token lub chat_id w tg_config.json!")

    # Etap 3: Audyt martwych przyciskow Telegrama (callback_data)
    cp_txt = open("crypto_pro.py", encoding="utf-8").read()
    defined_cbs = set(re.findall(r'["\']callback_data["\']\s*:\s*["\']([^"\'{]+)["\']', cp_txt))
    handled_eq = set(re.findall(r'cb\s*==\s*["\']([^"\']+)["\']', cp_txt))
    handled_sw = set(re.findall(r'cb\.startswith\(\s*["\']([^"\']+)["\']', cp_txt))
    dead = [b for b in sorted(defined_cbs) if not ((b in handled_eq) or any(b.startswith(p) for p in handled_sw))]
    if dead:
        raise RuntimeError(f"Cichy defekt: nieobsluzone przyciski w Telegramie: {dead}")

    # Etap 4: Pelny 8-etapowy test API Bitget, MTF, Pump&Dump + symulacja tras Chrome Flask
    import self_test, crypto_pro as cp, alpha_pro_mod as apm, auto_tuner_mod as atm, contract_audit_mod as cam, web_pump_radar_mod as wpr, web_ui_mod
    res_8 = self_test.run_full_self_test()

    web_ui_mod.register_web_ui(cp.app, cp, apm, atm, cam, wpr)
    with cp.app.test_client() as client:
        for route in ["/", "/api/web_full_state"]:
            resp = client.get(route)
            if resp.status_code != 200 or len(resp.data) < 50:
                raise RuntimeError(f"Cichy defekt Pulpitu Chrome na trasie '{route}': HTTP {resp.status_code}")

    # Etap 5: Kontrola praw skryptu startowego oraz porzadku w katalogu
    sh_path = os.path.expanduser("~/.shortcuts/CryptoPro_Start.sh")
    if not os.path.exists(sh_path) or not os.access(sh_path, os.X_OK):
        raise RuntimeError("Cichy defekt: skrypt CryptoPro_Start.sh nie ma uprawnien wykonywania (+x)!")

    return res_8

if __name__ == "__main__":
    G, R, X = "\033[1;92m", "\033[1;91m", "\033[0m"
    try:
        res = run_smart_audit()
        print(f"\n{G}+--------------------------------------------------+")
        print(f"|  ✅ AUTO-WERYFIKACJA 2.0: ZERO DEFEKTÓW (100%)   |")
        print(f"+--------------------------------------------------+")
        print(f"| {res[:48].ljust(48)} |")
        print(f"+--------------------------------------------------+{X}\n")
        sys.exit(0)
    except Exception as exc:
        tb_str = traceback.format_exc()
        m = re.findall(r'File "([^"]+)", line (\d+)', tb_str)
        ctx_lines = []
        if m:
            err_file, err_line = m[-1][0], int(m[-1][1])
            if os.path.exists(err_file):
                all_l = open(err_file, encoding="utf-8", errors="ignore").readlines()
                s_i, e_i = max(0, err_line - 4), min(len(all_l), err_line + 3)
                for idx_l in range(s_i, e_i):
                    mark = ">>" if (idx_l + 1) == err_line else "  "
                    ctx_lines.append(f"{mark} {idx_l+1}: {all_l[idx_l].rstrip()}")
        log_tail = "".join(open("bot_bg.log", encoding="utf-8", errors="ignore").readlines()[-10:]) if os.path.exists("bot_bg.log") else ""
        print(f"\n{R}================ [RAPORT BLEDU DO WKLEJENIA] ================")
        print(f"BLAD: {type(exc).__name__}: {exc}")
        if ctx_lines:
            print("KOD WOKOL BLEDU:\n" + "\n".join(ctx_lines))
        print("TRACEBACK:\n" + tb_str.strip())
        if log_tail.strip():
            print("OSTATNIE LOGI:\n" + log_tail.strip())
        print(f"============================================================={X}\n")
        sys.exit(1)
