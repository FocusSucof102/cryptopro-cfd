import os, re, sys
import auto_repair_mod as arm, ast, json, shutil, subprocess, traceback, py_compile, builtins

REQ_PY = [
    "crypto_pro.py", "alpha_pro_mod.py", "auto_tuner_mod.py", "portfolio_mod.py",
    "planner_mod.py", "chart_mod.py", "demo_sim_mod.py", "web_pump_radar_mod.py",
    "contract_audit_mod.py", "web_ui_mod.py", "self_test.py", "watchdog_mod.py", "session_analytics_mod.py", "auto_repair_mod.py", "sniper_doctor_mod.py", "smart_sl_mod.py", "inst_orderflow_mod.py", "ai_quant_mod.py", "evolution_lab_mod.py", "future_quantum_mod.py", "quantum_nash_mod.py", "meta_brain_mod.py", "nzt_cortex_mod.py"
]

def check_ast_and_scope(fn):
    """Analiza AST: duplikaty, niezdefiniowane zmienne (NameError), liczba argumentow i URL-e."""
    src = open(fn, encoding="utf-8").read()
    tree = ast.parse(src, filename=fn)
    seen_funcs, func_arities = set(), {}
    mod_globals = set(dir(builtins))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and next(iter(node.body)).lineno > node.lineno and ast.get_docstring(node) is None:
                raise RuntimeError(f"QA 5.0 Docstring-Guard: Brak opisu funkcji '{node.name}' w {fn}:{node.lineno}!")
            if node.name in seen_funcs:
                raise RuntimeError(f"QA 5.0 AST: Duplikat '{node.name}' w {fn}:{node.lineno}!")
            seen_funcs.add(node.name)
            mod_globals.add(node.name)
            tot_a = len(node.args.args)
            func_arities[node.name] = (tot_a - len(node.args.defaults), tot_a, bool(node.args.vararg or node.args.kwarg))
        elif isinstance(node, ast.ClassDef):
            mod_globals.add(node.name)
        elif isinstance(node, ast.Import):
            for al in node.names: mod_globals.add(al.asname or al.name.partition(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for al in node.names: mod_globals.add(al.asname or al.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name): mod_globals.add(n.id)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            local_defs = {a.arg for a in node.args.args + node.args.kwonlyargs}
            if node.args.vararg: local_defs.add(node.args.vararg.arg)
            if node.args.kwarg: local_defs.add(node.args.kwarg.arg)
            used_loads = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name):
                    if isinstance(sub.ctx, (ast.Store, ast.Param, ast.Del)): local_defs.add(sub.id)
                    elif isinstance(sub.ctx, ast.Load): used_loads.append((sub.id, getattr(sub, "lineno", node.lineno)))
                elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for al in sub.names: local_defs.add(al.asname or al.name.partition(".")[0])
                elif isinstance(sub, ast.ExceptHandler) and sub.name: local_defs.add(sub.name)
                elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    local_defs.add(sub.name)
                    for a in sub.args.args + sub.args.kwonlyargs: local_defs.add(a.arg)
                elif isinstance(sub, ast.Lambda):
                    for a in sub.args.args + sub.args.kwonlyargs: local_defs.add(a.arg)
                elif isinstance(sub, (ast.For, ast.AsyncFor, ast.comprehension)):
                    tgt = sub.target
                    for t in ast.walk(tgt):
                        if isinstance(t, ast.Name): local_defs.add(t.id)
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    fn_c = sub.func.id
                    if fn_c in func_arities and not sub.keywords and not any(isinstance(a, ast.Starred) for a in sub.args):
                        r_min, r_max, has_v = func_arities[fn_c]
                        if len(sub.args) < r_min or (not has_v and len(sub.args) > r_max):
                            raise RuntimeError(f"QA 5.0 Call-Guard: Zla liczba arg. '{fn_c}' w {fn}:{getattr(sub, 'lineno', 0)}")
            for nid, ln in used_loads:
                if nid not in local_defs and nid not in mod_globals:
                    raise RuntimeError(f"QA 5.0 Scope-Guard: Niezdefiniowana zmienna '{nid}' w {fn}:{ln} ({node.name})!")

def check_secret_leaks():
    """DevSecOps: skanuje pliki Git pod katem wycieku kluczy i tokenow."""
    tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    pats = [(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b", "Token TG"), (r"\bghp_[A-Za-z0-9]{36}\b", "GitHub Token")]
    for fn in tracked:
        if os.path.exists(fn) and not fn.endswith(".json"):
            txt = open(fn, encoding="utf-8", errors="ignore").read()
            for pat, desc in pats:
                if re.search(pat, txt): raise RuntimeError(f"SECURITY ALERT: {desc} w '{fn}'!")
def run_smart_audit():
    """Pelny audyt QA 5.0 PRO+."""
    _, _, free_b = shutil.disk_usage(".")
    free_mb = free_b // (1024 * 1024)
    if free_mb < 150: raise RuntimeError(f"Malo miejsca: {free_mb} MB!")
    if os.path.exists("bot_bg.log") and os.path.getsize("bot_bg.log") > 2 * 1024 * 1024:
        open("bot_bg.log", "w", encoding="utf-8").writelines(open("bot_bg.log", encoding="utf-8", errors="ignore").readlines()[-500:])
    doc_cnt = 0
    all_mods = sorted(set(REQ_PY + [f for f in os.listdir(".") if f.endswith("_mod.py")])) # Auto-Discovery
    for fn in all_mods + ["README.md", "CHANGELOG.md"]:
        if not os.path.exists(fn) or os.path.getsize(fn) < 50: raise RuntimeError(f"Brak/pusty: '{fn}'")
        if fn.endswith(".py"):
            py_compile.compile(fn, doraise=True)
            check_ast_and_scope(fn)
            doc_cnt += sum(1 for n in ast.parse(open(fn, encoding="utf-8").read()).body if isinstance(n, ast.FunctionDef) and ast.get_docstring(n))
    check_secret_leaks()
    for jf in ["tg_config.json", "tuner_state.json", "market_shadow_lab.json", "wild_market_lab.json", "micro_market_lab.json"]:
        if not os.path.exists(jf): raise FileNotFoundError(f"Brak: {jf}")
        json.load(open(jf, encoding="utf-8"))
    import alpha_pro_mod as apm, auto_tuner_mod as atm, contract_audit_mod as cam, web_pump_radar_mod as wpr, web_ui_mod, crypto_pro as cp, self_test
    if apm.validate_cfd_order(0, 0, 0) is not False: raise RuntimeError("Fuzzing Alert!")
    import watchdog_mod as wd
    stalled_qa = wd.check_stalled_modules()
    if stalled_qa: raise RuntimeError('Watchdog Alert: ' + ' | '.join(stalled_qa))
    res_8 = self_test.run_full_self_test()
    web_ui_mod.register_web_ui(cp.app, cp, apm, atm, cam, wpr)
    with cp.app.test_client() as cl:
        for rt in ["/", "/api/web_full_state"]:
            if cl.get(rt).status_code != 200: raise RuntimeError(f"Defekt Web UI: {rt}")
    return f"QA 5.0 PRO+ | Docs:{doc_cnt} | {free_mb}MB | {res_8}"

if __name__ == "__main__":
    from datetime import datetime
    QA_FILE = "qa_health_history.json"
    G, R, X = "\033[1;92m", "\033[1;91m", "\033[0m"
    hist = json.load(open(QA_FILE, encoding="utf-8")) if os.path.exists(QA_FILE) else []
    now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        res = run_smart_audit()
        hist.append({"ts": now_s, "status": "PASS", "summary": res})
        json.dump(hist[-100:], open(QA_FILE, "w", encoding="utf-8"), indent=2)
        import crypto_pro as cp; cp.build_ai_context_bundle()
        print(f"\n{G}+--------------------------------------------------+\n|   ✅ AUDYT QA 5.0 PRO+ (AST/SCOPE): ZERO BLEDOW! |\n+--------------------------------------------------+\n| {res[:48].ljust(48)} |\n+--------------------------------------------------+{X}\n")
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        hist.append({"ts": now_s, "status": "UNRESOLVED", "error": err_msg})
        json.dump(hist[-100:], open(QA_FILE, "w", encoding="utf-8"), indent=2)
        print(f"\n{R}================ [RAPORT BLEDU DO WKLEJENIA] ================\nBLAD: {err_msg}\n============================================================={X}\n")
        sys.exit(1)
