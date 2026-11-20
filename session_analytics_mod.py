import os, json

BL_FILE = "bitbase_blacklist.json"

def get_bitbase_blacklist():
    """Wczytuje liste par wykluczonych z alertow (niedostepnych na BitBase Futures)."""
    if os.path.exists(BL_FILE):
        try: return set(json.load(open(BL_FILE, encoding="utf-8")))
        except Exception: pass
    return set()

def add_to_bitbase_blacklist(sym):
    """Dodaje pare do czarnej listy BitBase (nadal badana w laboratoriach, bez alertow)."""
    clean = str(sym).upper().strip()
    if not clean.endswith("USDT"): clean += "USDT"
    bl = get_bitbase_blacklist()
    bl.add(clean)
    json.dump(sorted(bl), open(BL_FILE, "w", encoding="utf-8"), indent=2)
    return clean

def compute_session_edge():
    """Analizuje oplacalnosc sygnalow netto (-0.07R) w podziale na 4 sesje dobowe."""
    buckets = {
        "Azja (00-07)": set(range(0, 8)),
        "Londyn (08-13)": set(range(8, 14)),
        "Nowy Jork (14-19)": set(range(14, 20)),
        "Noc US (20-23)": set(range(20, 24))
    }
    samples = []
    for fn in ("cfd_live_history.json", "market_shadow_lab.json", "wild_market_lab.json"):
        if os.path.exists(fn):
            try: samples.extend(json.load(open(fn, encoding="utf-8")))
            except Exception: pass
    closed = [x for x in samples if x.get("closed_final")]
    out = {}
    for name, hrs in buckets.items():
        sub = [x for x in closed if int(x.get("hour", -1)) in hrs]
        cnt = len(sub)
        wins = sum(1 for x in sub if float(x.get("res_r", 0)) > 0)
        net_r = round(sum(float(x.get("res_r", 0)) - 0.07 for x in sub), 2)
        wr = round((wins / cnt) * 100.0, 1) if cnt > 0 else 0.0
        out[name] = {"count": cnt, "wr": wr, "net_r": net_r}
    return out
