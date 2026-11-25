import os, re, json, shutil, subprocess, py_compile

JSON_DEFAULTS = {
    "tuner_state.json": {"min_prob": 58, "scan_floor": 45, "sl_mult": 1.0, "active_tiers": ["PLATINUM", "GOLD"], "last_tune_ts": 0, "notes": "Auto-repaired"},
    "active_positions.json": [], "module_heartbeats.json": {}, "bitbase_blacklist.json": [],
    "market_shadow_lab.json": [], "wild_market_lab.json": [], "micro_market_lab.json": [],
    "qa_health_history.json": [], "evolution_champion.json": {}, "meta_brain_weights.json": {},
    "nzt_synapses.json": {}, "ai_decisions_log.json": [], "funnel_stats.json": {},
    "risk_config.json": {"capital_usdt": 200.0, "risk_pct": 1.0, "max_drawdown_pct": 6.0, "current_drawdown_pct": 0.0, "safe_lock_active": False},
    "time_decay_state.json": {"active": False, "cutoff_minutes": 360, "verdict": "KEPT_AS_RESEARCH"}
}

ALIAS_IMPORTS = {
    "apm": "import alpha_pro_mod as apm", "atm": "import auto_tuner_mod as atm", "wd": "import watchdog_mod as wd",
    "sam": "import session_analytics_mod as sam", "sdm": "import sniper_doctor_mod as sdm", "ssl": "import smart_sl_mod as ssl",
    "iom": "import inst_orderflow_mod as iom", "aqm": "import ai_quant_mod as aqm", "elm": "import evolution_lab_mod as elm",
    "fqm": "import future_quantum_mod as fqm", "qnm": "import quantum_nash_mod as qnm", "qep": "import quant_edge_pro_mod as qep",
    "mbm": "import meta_brain_mod as mbm", "nzt": "import nzt_cortex_mod as nzt", "r24": "import report_24h_mod as r24",
    "rgm": "import risk_guard_mod as rgm", "tdm": "import time_decay_mod as tdm", "orch": "import orchestrator as orch"
}

def heal_python_file(fn):
    """Wieloprzebiegowo naprawia wciecia, brakujace importy i skladnie pliku .py."""
    fixed = []
    for _ in range(8):
        try:
            py_compile.compile(fn, doraise=True)
            break
        except Exception as exc:
            lines = open(fn, encoding="utf-8").read().splitlines()
            ln = getattr(exc, "lineno", 0) or 0
            if 1 < ln <= len(lines):
                prev_ind = len(lines[ln - 2]) - len(lines[ln - 2].lstrip())
                if lines[ln - 2].rstrip().endswith(":"): prev_ind += 4
                lines[ln - 1] = (" " * prev_ind) + lines[ln - 1].lstrip()
                open(fn, "w", encoding="utf-8").write("\n".join(lines) + "\n")
                fixed.append(f"wciecie:{fn}:{ln}")
            else:
                break
    raw = open(fn, encoding="utf-8").read()
    for alias, imp_line in ALIAS_IMPORTS.items():
        if re.search(rf"\b{alias}\.", raw) and imp_line not in raw:
            raw = imp_line + "\n" + raw
            open(fn, "w", encoding="utf-8").write(raw)
            fixed.append(f"import:{alias}->{fn}")
    return fixed

def run_self_healing_repair():
    """Autonomicznie leczy pliki JSON, blokady Git, wciecia, importy i cofa bledy krytyczne."""
    repairs = []
    if os.path.exists(".git/index.lock"):
        try: os.remove(".git/index.lock"); repairs.append("Usunieto .git/index.lock")
        except Exception: pass
    for jf, def_v in JSON_DEFAULTS.items():
        if not os.path.exists(jf):
            json.dump(def_v, open(jf, "w", encoding="utf-8"), indent=2)
        else:
            try: json.load(open(jf, encoding="utf-8"))
            except Exception:
                shutil.copy2(jf, jf + ".corrupt.bak")
                json.dump(def_v, open(jf, "w", encoding="utf-8"), indent=2)
                repairs.append(f"Naprawiono JSON: {jf}")
    for fn in sorted(os.listdir(".")):
        if fn.endswith(".py"):
            repairs.extend(heal_python_file(fn))
            try: py_compile.compile(fn, doraise=True)
            except Exception:
                if subprocess.run(["git", "checkout", "--", fn], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                    repairs.append(f"Git rollback: {fn}")
    return repairs
