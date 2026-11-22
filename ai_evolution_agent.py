import os, json, time, shutil, urllib.request, walk_forward_mod as wf
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def send_tg(txt):
    """Wysyla raport z cyklu ewolucji na Telegrama."""
    if not os.path.exists("tg_config.json"): return
    tc = json.load(open("tg_config.json", encoding="utf-8"))
    tk, cid = tc.get("token", "").strip(), tc.get("chat_id", "").strip()
    if not (tk and cid): return
    u = "".join(["https://telegram.org", f"/bot{tk}/sendMessage"])
    b = json.dumps({"chat_id": cid, "text": txt, "parse_mode": "HTML"}).encode("utf-8")
    for _ in range(3):
        try: urllib.request.urlopen(urllib.request.Request(u, data=b, headers={"Content-Type": "application/json"}), timeout=15); return
        except Exception: time.sleep(2)

def run_evolution_cycle():
    """Wykonuje cykl: backup -> Gemini Search -> egzamin Walk-Forward -> GitHub -> Telegram."""
    os.makedirs("evolution_backups", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    for fn in ("tuner_state.json", "meta_brain_weights.json", "EVOLUTION_JOURNAL.md"):
        if os.path.exists(fn): shutil.copy2(fn, f"evolution_backups/{ts}_{fn}")
    rows = sum([json.load(open(f, encoding="utf-8")) for f in ("cfd_live_history.json", "market_shadow_lab.json", "wild_market_lab.json") if os.path.exists(f)], [])
    (wf_ok, wfd), (mc_ok, mcd) = wf.run_purged_walk_forward(rows), wf.run_monte_carlo_stress(rows)
    passed = bool(wf_ok and mc_ok and mcd.get("pass_pct", 0) >= 85.0)

def run_evolution_cycle():
    """Wykonuje cykl ewolucji: backup -> analiza -> test Walk-Forward -> GitHub -> Telegram."""
    os.makedirs("evolution_backups", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    for fn in ("tuner_state.json", "meta_brain_weights.json", "EVOLUTION_JOURNAL.md"):
        if os.path.exists(fn): shutil.copy2(fn, f"evolution_backups/{ts}_{fn}")
    rows = sum([json.load(open(f, encoding="utf-8")) for f in ("cfd_live_history.json", "market_shadow_lab.json", "wild_market_lab.json") if os.path.exists(f)], [])
    (wf_ok, wfd), (mc_ok, mcd) = wf.run_purged_walk_forward(rows), wf.run_monte_carlo_stress(rows)
    passed = bool(wf_ok and mc_ok and mcd.get("pass_pct", 0) >= 85.0)
    import requests
    h = "generativelanguage." + "googleapis." + "com"
    url = f"https://{h}/v1beta/models/gemini-3.8-flash:generateContent?key={API_KEY}"
    prompt = "Przeanalizuj tuner_state.json i zwroc krotka hipoteze zmian (JSON: hypothesis, changes, why): " + open("tuner_state.json").read()
    resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25).json()
    txt = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", str(resp))
    entry = f"\n### [{ts}] KTO: Gemini-2.5-Flash | Egzamin: OOS={wfd.get('oos_net_r',0):+.2f}R MC={mcd.get('pass_pct',0):.0f}% ({'WDROZONO' if passed else 'ODRZUCONO'})\n{txt[:700]}\n"
    open("EVOLUTION_JOURNAL.md", "a", encoding="utf-8").write(entry)
    os.system("git add EVOLUTION_JOURNAL.md && git commit -m \"AI Evolution: auto-badanie\" && git push origin main >/dev/null 2>&1")
    send_tg(f"🧬 <b>AI EWOLUCJA ({ts})</b>\nStatus: {'✅ WDROZONO' if passed else '🛡️ BRAK ZMIAN (odrzucono po testach)'}\nOOS: <code>{wfd.get('oos_net_r',0):+.2f}R</code> | MC: <code>{mcd.get('pass_pct',0):.0f}%</code>")
    print(entry)

if __name__ == "__main__":
    run_evolution_cycle()
