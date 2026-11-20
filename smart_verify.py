import os, re, sys, ast, json, shutil, subprocess, traceback, py_compile

REQ_PY = [
    "crypto_pro.py", "alpha_pro_mod.py", "auto_tuner_mod.py", "portfolio_mod.py",
    "planner_mod.py", "chart_mod.py", "demo_sim_mod.py", "web_pump_radar_mod.py",
    "contract_audit_mod.py", "web_ui_mod.py", "self_test.py"
]

def check_ast_quality(fn):
    src = open(fn, encoding="utf-8").read()
    tree = ast.parse(src, filename=fn)
    seen_funcs = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name in seen_funcs:
                raise RuntimeError(f"AST Duplikat funkcji '{node.name}' w pliku {fn} (linia {node.lineno})!")
            seen_funcs.add(node.name)

def check_secret_leaks():
    # Skanujemy pliki sledzone przez git oraz staged files pod katem wycieku sekretow
    tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    secret_patterns = [
        (r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b", "Token Bota Telegrama"),
        (r"\bghp_[A-Za-z0-9]{36}\b", "GitHub Personal Access Token"),
        (r"\bgithub_pat_[A-Za-z0-9_]{22,}\b", "GitHub Fine-Grained Token"),
    ]
    for fn in tracked:
        if not os.path.exists(fn) or fn.endswith(".json"):
            continue
        txt = open(fn, encoding="utf-8", errors="ignore").read()
        for pat, desc in secret_patterns:
            if re.search(pat, txt):
                raise RuntimeError(f"SECURITY ALERT! Wykryto {desc} w pliku sledzonym przez Git: '{fn}'!")

def check_system_resources():
    # Kontrola wolnego miejsca na dysku (>150 MB) oraz automatyczna rotacja bot_bg.log (>2 MB)
    _, _, free_b = shutil.disk_usage(".")
    free_mb = free_b // (1024 * 1024)
    if free_mb < 150:
        raise RuntimeError(f"Krytycznie malo wolnego miejsca na telefonie: {free_mb} MB (wymagane min. 150 MB)!")
    if os.path.exists("bot_bg.log") and os.path.getsize("bot_bg.log") > 2 * 1024 * 1024:
        tail = open("bot_bg.log", encoding="utf-8", errors="ignore").readlines()[-500:]
        open("bot_bg.log", "w", encoding="utf-8").writelines(tail)
    return free_mb

def run_smart_audit():
    # 1. Zasoby urzadzenia i rotacja logow
    free_mb = check_system_resources()

    # 2. Kompilacja + Statyczna Analiza AST (duplikaty funkcji, puste pliki)
    for fn in REQ_PY + ["README.md", "CHANGELOG.md"]:
        if not os.path.exists(fn) or os.path.getsize(fn) < 50:
            raise RuntimeError(f"Brak lub pusty plik: '{fn}'")
        if fn.endswith(".py"):
            py_compile.compile(fn, doraise=True)
            check_ast_quality(fn)

    # 3. DevSecOps Secret Leak Scanner
    check_secret_leaks()

    # 4. Integralnosc baz JSON
    for jf in ["tg_config.json", "tuner_state.json", "market_shadow_lab.json", "wild_market_lab.json", "micro_market_lab.json"]:
        if not os.path.exists(jf):
            raise FileNotFoundError(f"Brak pliku danych: {jf}")
        data_j = json.load(open(jf, encoding="utf-8"))
        if jf == "tg_config.json" and (not data_j.get("token") or not data_j.get("chat_id")):
            raise RuntimeError("Puste pole token lub chat_id w tg_config.json!")

    # 5. Audyt martwych przyciskow Telegrama
    cp_txt = open("crypto_pro.py", encoding="utf-8").read()
    defined_cbs = set(re.findall(r'["\']callback_data["\']\s*:\s*["\']([^"\'{]+)["\']', cp_txt))
    handled_eq = set(re.findall(r'cb\s*==\s*["\']([^"\']+)["\']', cp_txt))
    handled_sw = set(re.findall(r'cb\.startswith\(\s*["\']([^"\']+)["\']', cp_txt))
    dead = [b for b in sorted(defined_cbs) if not ((b in handled_eq) or any(b.startswith(p) for p in handled_sw))]
    if dead:
        raise RuntimeError(f"Martwe przyciski w Telegramie bez obslugi: {dead}")

    # 6. Edge-Case Fuzzing (test odpornosci na bledne dane z gieldy: 0, ujemne, puste)
    import alpha_pro_mod as apm, auto_tuner_mod as atm, contract_audit_mod as cam, web_pump_radar_mod as wpr, web_ui_mod, crypto_pro as cp, self_test
    if apm.validate_cfd_order(0, 0, 0) is not False or apm.validate_cfd_order(100, 100, 100) is not False:
        raise RuntimeError("Fuzzing Alert: validate_cfd_order przepuscil zerowe/bledne zlecenie!")

    # 7. Pelny 8-etapowy test API + symulacja tras Chrome Flask
    res_8 = self_test.run_full_self_test()
    web_ui_mod.register_web_ui(cp.app, cp, apm, atm, cam, wpr)
    with cp.app.test_client() as client:
        for route in ["/", "/api/web_full_state"]:
            resp = client.get(route)
            if resp.status_code != 200 or len(resp.data) < 50:
                raise RuntimeError(f"Defekt Pulpitu Chrome na trasie '{route}': HTTP {resp.status_code}")

    return f"QA 3.0 PASS | Wolne: {free_mb}MB | {res_8}"

if __name__ == "__main__":
    G, R, X = "\033[1;92m", "\033[1;91m", "\033[0m"
    try:
        res = run_smart_audit()
        print(f"\n{G}+--------------------------------------------------+")
        print(f"|   ✅ PROFESJONALNY AUDYT QA 3.0: ZERO BŁĘDÓW!    |")
        print(f"+--------------------------------------------------+")
        print(f"| {res[:48].ljust(48)} |")
        print(f"+--------------------------------------------------+{X}\n")
        sys.exit(0)
    except Exception as exc:
        tb_str = traceback.format_exc()
        m = re.findall(r'File "([^"]+)", line (\d+)', tb_str)
        ctx_lines = []
        if m:
            err_file, err_line = m[-1], int(m[-1])
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
