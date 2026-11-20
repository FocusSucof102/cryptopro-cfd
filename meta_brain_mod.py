import os, json
from datetime import datetime

BRAIN_FILE = "meta_brain_weights.json"

DEFAULT_WEIGHTS = {
    "OB_IMB": {"w": 1.0, "wins": 0, "losses": 0, "label": "Orderbook Imbalance"},
    "KNN": {"w": 1.0, "wins": 0, "losses": 0, "label": "KNN Pattern Matcher"},
    "LEAD_LAG": {"w": 1.0, "wins": 0, "losses": 0, "label": "Lead-Lag BTC/ETH/SOL"},
    "ENTROPY": {"w": 1.0, "wins": 0, "losses": 0, "label": "Niska Entropia Shannona"},
    "ICEBERG": {"w": 1.0, "wins": 0, "losses": 0, "label": "Whale Iceberg Absorption"},
    "QWAVE": {"w": 1.0, "wins": 0, "losses": 0, "label": "Quantum Wave Interference"},
    "last_learn": "Inicjalizacja"
}

def load_brain():
    """Wczytuje wagi inteligencji Meta-Brain z meta_brain_weights.json."""
    st = json.loads(json.dumps(DEFAULT_WEIGHTS))
    if os.path.exists(BRAIN_FILE):
        try: st.update(json.load(open(BRAIN_FILE, encoding="utf-8")))
        except Exception: pass
    return st

def apply_brain_weights(ob_b, kb, lb, reg_b, rt_b, qw_b):
    """Mnozy punkty kazdego modulu przez jego aktualna wage skutecznosci z Meta-Brain."""
    br = load_brain()
    tot = (
        ob_b * br["OB_IMB"]["w"] +
        kb * br["KNN"]["w"] +
        lb * br["LEAD_LAG"]["w"] +
        reg_b * br["ENTROPY"]["w"] +
        rt_b * br["ICEBERG"]["w"] +
        qw_b * br["QWAVE"]["w"]
    )
    return int(round(tot))

def learn_from_closed_history():
    """Samouczenie (Reinforcement): analizuje zamkniete sygnaly i aktualizuje wagi modulow."""
    br = json.loads(json.dumps(DEFAULT_WEIGHTS))
    tag_map = {"OB Imb": "OB_IMB", "KNN Match": "KNN", "LEAD-LAG": "LEAD_LAG", "Niska Entropia": "ENTROPY", "ICEBERG": "ICEBERG", "Q-Wave Konstruktywna": "QWAVE"}
    rows = []
    for fn in ("cfd_live_history.json", "market_shadow_lab.json"):
        if os.path.exists(fn):
            try: rows.extend(json.load(open(fn, encoding="utf-8")))
            except Exception: pass
    for r in rows:
        if not r.get("closed_final"): continue
        net = float(r.get("res_r", 0)) - 0.07
        atag = str(r.get("alpha_tag", ""))
        for needle, key in tag_map.items():
            if needle in atag:
                if net > 0:
                    br[key]["wins"] += 1
                    br[key]["w"] = round(min(2.0, br[key]["w"] + 0.06), 2)
                else:
                    br[key]["losses"] += 1
                    br[key]["w"] = round(max(0.25, br[key]["w"] - 0.05), 2)
    br["last_learn"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump(br, open(BRAIN_FILE, "w", encoding="utf-8"), indent=2)
    return br

def get_brain_summary_line():
    """Zwraca zwiezly raport czego nauczyl sie Meta-Brain (top 2 najsilniejsze moduly)."""
    br = learn_from_closed_history()
    items = [(k, v) for k, v in br.items() if isinstance(v, dict)]
    items.sort(key=lambda x: -x.__getitem__(1)["w"])
    top2 = [f"{v['label']}: <b>{v['w']:.2f}x</b> ({v['wins']}W/{v['losses']}L)" for _, v in items.__getitem__(slice(0, 2))]
    return "🧠 <b>Meta-Brain AI:</b> " + " | ".join(top2)
