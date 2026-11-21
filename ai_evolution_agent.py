import time, shutil, walk_forward_mod as wf
import os, json, shutil, datetime, urllib.request, subprocess, py_compile
import walk_forward_mod as wf

API_KEY = os.environ.get("GEMINI_API_KEY", "")

def send_tg(msg):
    """Wysyla raport z cyklu ewolucji na Telegrama."""
    if not os.path.exists("tg_config.json"): return
    cfg = json.load(open("tg_config.json", encoding="utf-8"))
    tok, cid = cfg.get("bot_token", ""), cfg.get("chat_id", "")
    if not tok or not cid: return
    u = f"https://telegram.org{tok}/sendMessage"
    data = json.dumps({"chat_id": cid, "text": msg}).encode("utf-8")
    urllib.request.urlopen(urllib.request.Request(u, data=data, headers={"Content-Type": "application/json"}), timeout=15)

def make_backup(tag="auto"):
    """Tworzy pelny backup plikow .py i .json w folderze backups_ai/."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join("backups_ai", f"{ts}_{tag}")
    os.makedirs(dst, exist_ok=True)
    for fn in os.listdir("."):
        if fn.endswith((".py", ".json", ".md")):
            shutil.copy2(fn, os.path.join(dst, fn))
    return dst

def run_full_evolution_cycle():
    """Pelny cykl: kopia zapasowa -> internet + Gemini -> test Walk-Forward -> GitHub -> Telegram."""
    os.makedirs("evolution_backups", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    for fn in ("tuner_state.json", "meta_brain_weights.json", "AI_SESSION_STATE.md"):
        if os.path.exists(fn):
            shutil.copy2(fn, f"evolution_backups/{ts}_{fn}")
    state = ""
    for fn in ("AGENTS.md", "AI_SESSION_STATE.md", "tuner_state.json", "raport_24h_dla_ai.txt"):
        if os.path.exists(fn):
            state += f"\n--- {fn} ---\n" + open(fn, encoding="utf-8", errors="ignore").read()[-2500:]
    raw = ask_gemini_strategist(state)
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(clean)
    rows = sum([json.load(open(f)) for f in ("market_shadow_lab.json", "wild_market_lab.json") if os.path.exists(f)], [])
    (wf_ok, wfd), (mc_ok, mcd) = wf.run_purged_walk_forward(rows), wf.run_monte_carlo_stress(rows)
    passed = bool(wf_ok and mc_ok and mcd.get("pass_pct", 0) >= 85.0)
    log_entry = f"\n### [{ts}] KTO: Gemini-2.5-Flash (Search+Quant)\n- **CO:** {data.get('changes')}\n- **DLACZEGO:** {data.get('why')}\n- **EGZAMIN:** WF={wfd.get('oos_net_r',0):+.2f}R | MC={mcd.get('pass_pct',0):.0f}% -> {'WDROZONO' if passed else 'ODRZUCONO (brak poprawy)'}\n"
    open("AI_EVOLUTION_LOG.md", "a", encoding="utf-8").write(log_entry)
    if passed and os.path.exists("tuner_state.json"):
        st = json.load(open("tuner_state.json"))
        for k, v in data.get("changes", {}).items():
            if k in st: st[k] = v
        json.dump(st, open("tuner_state.json", "w"), indent=2)
    os.system('git add AI_EVOLUTION_LOG.md && git commit -m "AI Evolution: auto-badanie i audyt" && git push origin main >/dev/null 2>&1')
    msg = f"🧬 *AI EWOLUCJA ({ts})*\n• *Status:* {'✅ ZMIANY WDROŻONE' if passed else '🛡️ BRAK ZMIAN (odrzucono po testach)'}\n• *Hipoteza:* {data.get('hypothesis','')[:140]}\n• *Egzamin:* OOS `{wfd.get('oos_net_r',0):+.2f}R` | MC `{mcd.get('pass_pct',0):.0f}%`\n• *Backup:* `evolution_backups/{ts}_*`"
    send_tg(msg)
    print(msg)

if __name__ == "__main__":
    run_full_evolution_cycle()
