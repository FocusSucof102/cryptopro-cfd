import os, json, shutil, subprocess, py_compile
from datetime import datetime

JSON_DEFAULTS = {
    "tuner_state.json": {"min_prob": 58, "sl_mult": 1.0, "active_tiers": ["PLATINUM", "GOLD"], "last_tune_ts": 0, "notes": "Auto-repaired"},
    "active_positions.json": [],
    "module_heartbeats.json": {},
    "bitbase_blacklist.json": [],
    "market_shadow_lab.json": [],
    "wild_market_lab.json": [],
    "micro_market_lab.json": [],
    "qa_health_history.json": [],
    "evolution_champion.json": {},
    "meta_brain_weights.json": {},
    "nzt_synapses.json": {}
}

def run_self_healing_repair():
    """Automatycznie leczy uszkodzone pliki JSON, blokady Git oraz cofa bledy skladni .py."""
    repairs = []
    if os.path.exists(".git/index.lock"):
        try:
            os.remove(".git/index.lock")
            repairs.append("Usunieto zablokowany plik .git/index.lock")
        except Exception: pass

    for jf, default_val in JSON_DEFAULTS.items():
        if not os.path.exists(jf):
            json.dump(default_val, open(jf, "w", encoding="utf-8"), indent=2)
            repairs.append(f"Odtworzono brakujacy plik {jf}")
        else:
            try:
                json.load(open(jf, encoding="utf-8"))
            except Exception:
                shutil.copy2(jf, jf + ".corrupt.bak")
                json.dump(default_val, open(jf, "w", encoding="utf-8"), indent=2)
                repairs.append(f"Naprawiono uszkodzony JSON: {jf} (kopia w .bak)")

    for fn in sorted(os.listdir(".")):
        if fn.endswith(".py"):
            try:
                py_compile.compile(fn, doraise=True)
            except Exception as exc:
                r = subprocess.run(["git", "checkout", "--", fn], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if r.returncode == 0:
                    repairs.append(f"Cofnieto uszkodzony plik {fn} do ostatniej sprawnej wersji Git ({type(exc).__name__})")
    return repairs
