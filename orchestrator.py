#!/usr/bin/env python3
import os
import json
import time
import subprocess
from datetime import datetime

import auto_repair_mod as arm
import risk_guard_mod as rgm
import time_decay_mod as tdm
import walk_forward_mod as wf
import smart_verify

PROJECT_MASTER = "PROJECT_MASTER.md"

def update_project_master_heartbeat(status_dict):
    """Zapisuje najswiezszy puls cyklu orchestratora do PROJECT_MASTER.md."""
    if not os.path.exists(PROJECT_MASTER):
        return
    try:
        content = open(PROJECT_MASTER, "r", encoding="utf-8").read()
        ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        marker = "## 💓 OSTATNI CYKL ORCHESTRATORA (LIVE):"
        summary_block = (
            f"\n{marker}\n"
            f"- **Timestamp:** `{ts_now}`\n"
            f"- **QA Status:** `{status_dict.get('qa_status', 'OK')}`\n"
            f"- **Kapitał & Safe-Lock:** `{status_dict.get('capital_usdt', 200.0)}$` | Safe-Lock: `{'AKTYWNY' if status_dict.get('safe_lock') else 'STANDBY'}`\n"
            f"- **Obsuwa (DD):** `-{status_dict.get('current_dd', 0.0)}%` (Limit: `{status_dict.get('max_dd', 6.0)}%`)\n"
            f"- **Time-Decay Exit:** `{status_dict.get('time_decay_verdict', 'KEPT_AS_RESEARCH')}` (Cutoff: `{status_dict.get('time_decay_cutoff', 360)}m`)\n"
            f"- **Auto-Repairs:** `{len(status_dict.get('repairs', []))} wykonanych napraw`\n"
        )
        if marker in content:
            parts = content.split(marker)
            # Podmieniamy blok az do nastepnego naglowka
            after = parts[1].split("\n---", 1)
            content = parts[0].rstrip() + summary_block + ("\n---" + after[1] if len(after) > 1 else "")
        else:
            content = content.rstrip() + "\n\n" + summary_block + "\n"
        with open(PROJECT_MASTER, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

def run_git_research_sync():
    """Wysyla zaktualizowane pliki badawcze do repozytorium GitHub."""
    tracked_files = [
        "PROJECT_MASTER.md", "AGENTS.md", "CHANGELOG.md", "README.md",
        "market_shadow_lab.json", "wild_market_lab.json", "micro_market_lab.json",
        "cfd_live_history.json", "qa_health_history.json", "tuner_state.json",
        "meta_brain_weights.json", "nzt_synapses.json", "evolution_champion.json",
        "risk_config.json", "time_decay_state.json", "raport_24h_dla_ai.txt"
    ]
    try:
        to_add = [f for f in tracked_files if os.path.exists(f)]
        if to_add:
            subprocess.run(["git", "add", "-f"] + to_add, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "commit", "-m", f"Orchestrator Research Sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "push", "origin", "main"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        pass
    return False

def run_master_cycle():
    """Nadrzedny cykl dyrygenta zarzadzajacy auto-naprawa, QA, ryzykiem, audytem i syncem."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cycle_report = {"ts": now_str, "status": "IN_PROGRESS"}

    # 1. Autonomiczna naprawa oraz pelna walidacja smart_verify
    repairs = arm.run_self_healing_repair()
    cycle_report["repairs"] = repairs
    try:
        qa_result = smart_verify.run_smart_audit()
        cycle_report["qa_status"] = qa_result
    except Exception as exc:
        cycle_report["qa_status"] = f"QA_ERROR: {exc}"

    # 2. Status modulu zarzadzania ryzykiem (Risk Guard & Safe-Lock)
    risk_cfg = rgm.load_risk_config()
    cycle_report["capital_usdt"] = risk_cfg.get("capital_usdt", 200.0)
    cycle_report["safe_lock"] = risk_cfg.get("safe_lock_active", False)
    cycle_report["current_dd"] = risk_cfg.get("current_drawdown_pct", 0.0)
    cycle_report["max_dd"] = risk_cfg.get("max_drawdown_pct", 6.0)

    # 3. Audyt wynikow 1m oraz badania walk_forward i time_decay
    try:
        import crypto_pro as cp
        if hasattr(cp, "audit_cfd_history_1m"):
            cp.audit_cfd_history_1m()
    except Exception:
        pass

    td_res = tdm.test_time_decay_walk_forward()
    cycle_report["time_decay_verdict"] = td_res.get("verdict", "KEPT_AS_RESEARCH")
    cycle_report["time_decay_cutoff"] = td_res.get("cutoff_minutes", 360)

    # 4. Aktualizacja statusu w PROJECT_MASTER.md oraz synchronizacja Git
    update_project_master_heartbeat(cycle_report)
    sync_ok = run_git_research_sync()
    cycle_report["git_sync"] = sync_ok
    cycle_report["status"] = "SUCCESS"

    return cycle_report

if __name__ == "__main__":
    print("🚀 Uruchamiam Nadrzędny Cykl Dyrygenta (Orchestrator)...")
    res = run_master_cycle()
    print(json.dumps(res, indent=2, ensure_ascii=False))
