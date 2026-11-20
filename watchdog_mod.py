import os, json, time, threading
from datetime import datetime

HB_FILE = "module_heartbeats.json"
WORKERS = {}

LIMITS_SEC = {
    "cfd_live_scanner": (2100, "Skaner CFD TOP-60 (cykl 15m)"),
    "fast_guardian_60s": (300, "Radar Pozycji 60s (cykl 1m)"),
    "market_labs_30m": (3900, "Laboratoria Rynkowe 24/7 (cykl 30m)"),
    "macro_pump_dump_30m": (3900, "Radar Pump & Dump 7 Wzorcow (cykl 30m)"),
    "github_sync_5m": (900, "GitHub Auto-Sync & Paczka AI (cykl 5m)")
}

def register_worker(module_name, target_fn):
    """Rejestruje funkcje robocza modulu na potrzeby bezpiecznego restartu (Auto-Healing)."""
    WORKERS[module_name] = target_fn

def beat(module_name, note="OK"):
    """Zapisuje sygnal zycia (heartbeat) i zeruje licznik brakow wpisu."""
    try:
        data = json.load(open(HB_FILE, encoding="utf-8")) if os.path.exists(HB_FILE) else {}
        prev = data.get(module_name, {})
        data[module_name] = {
            "ts": time.time(),
            "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "note": str(note)[:120],
            "misses": 0,
            "restarts": int(prev.get("restarts", 0))
        }
        json.dump(data, open(HB_FILE, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass

def check_and_heal_modules():
    """Sprawdza aktywnosc modulow; po 3 brakach restartuje watek bez utraty danych."""
    if not os.path.exists(HB_FILE): return [], []
    try: data = json.load(open(HB_FILE, encoding="utf-8"))
    except Exception: return [], []
    now_t, healed, critical = time.time(), [], []
    for mod_key, (max_sec, label) in LIMITS_SEC.items():
        info = data.get(mod_key)
        if not info: continue
        if int(now_t - float(info.get("ts", now_t))) > max_sec:
            misses = int(info.get("misses", 0)) + 1
            restarts = int(info.get("restarts", 0))
            info["misses"] = misses
            if misses >= 3 and mod_key in WORKERS and restarts < 3:
                threading.Thread(target=WORKERS[mod_key], daemon=True).start()
                info.update({"ts": now_t, "misses": 0, "restarts": restarts + 1, "note": f"Auto-restart #{restarts + 1}"})
                healed.append(f"🔄 <b>{label}</b> — zrestartowano po 3 brakach (restart #{restarts + 1}, dane zachowane)")
            elif restarts >= 3:
                critical.append(f"🚨 <b>{label}</b> — nie odpowiada mimo 3 restartow!")
    json.dump(data, open(HB_FILE, "w", encoding="utf-8"), indent=2)
    return healed, critical

def check_stalled_modules():
    """Zwraca liste krytycznie zawieszonych modulow dla audytora QA 5.0."""
    _, crit = check_and_heal_modules()
    return crit
