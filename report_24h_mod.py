import os, json, time, subprocess
from datetime import datetime

STATE_24H = "sprint_24h_state.json"
DECISIONS_LOG = "ai_decisions_log.json"
TG_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_config.json")

def log_ai_decision(module_name, action, reason, details=""):
    """Zapisuje kazda autonomiczna decyzje AI (co zmienil i dlaczego) do dziennika 24H."""
    try:
        arr = json.load(open(DECISIONS_LOG, encoding="utf-8")) if os.path.exists(DECISIONS_LOG) else []
        arr.append({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "module": module_name, "action": action, "reason": reason, "details": str(details)[:200]})
        json.dump(arr[-250:], open(DECISIONS_LOG, "w", encoding="utf-8"), indent=2)
    except Exception: pass

def check_and_build_24h_report(cp_mod, force=False):
    """Sprawdza czy minelo 24h; po 24h tworzy pelna czarna skrzynke raport_24h_dla_ai.txt i wysyla alert TG."""
    now_t = time.time()
    st = json.load(open(STATE_24H, encoding="utf-8")) if os.path.exists(STATE_24H) else {}
    if not st.get("start_ts"):
        st = {"start_ts": now_t, "start_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "reported": False}
        json.dump(st, open(STATE_24H, "w", encoding="utf-8"), indent=2)
        return False
    if not force and (st.get("reported") or (now_t - float(st["start_ts"])) < 86400):
        return False
    st.update({"reported": True, "end_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    json.dump(st, open(STATE_24H, "w", encoding="utf-8"), indent=2)
    cp_mod.build_ai_context_bundle()

    import session_analytics_mod as sam
    files = ["funnel_stats.json", "ai_decisions_log.json", "meta_brain_weights.json", "nzt_synapses.json", "evolution_champion.json", "tuner_state.json", "cfd_live_history.json", "market_shadow_lab.json", "wild_market_lab.json", "micro_market_lab.json", "module_heartbeats.json", "qa_health_history.json", "bitbase_blacklist.json", "scanner_settings.json"]
    blocks = [f"# 🧠 PEŁNA CZARNA SKRZYNKA 24H DO DOGŁĘBNEJ ANALIZY AI\nOkres: {st['start_str']} -> {st['end_str']}\n\n=== ANALITYKA SESJI DOBOWYCH ===\n{json.dumps(sam.compute_session_edge(), indent=2, ensure_ascii=False)}"]
    live_cnt = 0
    for fn in files:
        if os.path.exists(fn):
            raw = open(fn, encoding="utf-8", errors="ignore").read()
            live_cnt += raw.count('"LIVE_FORWARD"')
            blocks.append(f"=== {fn} ===\n{raw}")
    rep_txt = "\n\n".join(blocks)
    for out_p in ("raport_24h_dla_ai.txt", "/storage/emulated/0/Download/raport_24h_dla_ai.txt"):
        try: open(out_p, "w", encoding="utf-8").write(rep_txt)
        except Exception: pass
    subprocess.run(["termux-media-scan", "/storage/emulated/0/Download/raport_24h_dla_ai.txt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        tc = json.load(open(TG_CONFIG_FILE, encoding="utf-8-sig"))
        tok, cid = tc.get("token", "").strip(), tc.get("chat_id", "").strip()
        if tok and cid and os.path.exists("raport_24h_dla_ai.txt"):
            import requests
            requests.post(cp_mod.tg_url(tok, "sendDocument"), data={"chat_id": cid, "caption": "📁 Pełna czarna skrzynka 24H gotowa do analizy AI!"}, files={"document": open("raport_24h_dla_ai.txt", "rb")}, timeout=20)
    except Exception: pass
    cp_mod.send_telegram(f"⏰ <b>UPŁYNĘŁO 24 GODZINY ANALIZ!</b>\n📊 Zebrano <b>{live_cnt}</b> nowych próbek <code>LIVE_FORWARD</code> + pełny dziennik decyzji AI.\n📁 W folderze <b>Download</b> czeka gotowa czarna skrzynka:\n• <code>raport_24h_dla_ai.txt</code>\n• <code>caly_projekt.txt</code>\n\n<i>Wrzuć raport_24h_dla_ai.txt do rozmowy z AI!</i>")
    return True

def get_24h_countdown_line():
    """Zwraca czytelny pasek postepu odliczania 24H i ostrzega jesli zegar ulegl opozniemu."""
    if not os.path.exists(STATE_24H):
        return "⏳ <b>Sprint 24H:</b> Oczekiwanie na inicjalizacje zegara..."
    try:
        st = json.load(open(STATE_24H, encoding="utf-8"))
        el_h = (time.time() - float(st.get("start_ts", time.time()))) / 3600.0
        rem_h = max(0.0, 24.0 - el_h)
        pct = min(100, int((el_h / 24.0) * 100))
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        if el_h > 24.5 and not st.get("reported"):
            return f"🚨 <b>ALARM ZEGARA 24H:</b> Minęło {el_h:.1f}h bez raportu — sprawdź Watchdog!"
        if st.get("reported"):
            return f"✅ <b>Sprint 24H ZAKOŃCZONY!</b> Raport <code>raport_24h_dla_ai.txt</code> gotowy w Download."
        return f"⏳ <b>Sprint 24H:</b> <code>[{bar}] {pct}%</code> ({el_h:.1f}h / 24h | Zostało: <b>{rem_h:.1f}h</b>)"
    except Exception:
        return "⚠️ Błąd odczytu zegara 24H"

FUNNEL_FILE = "funnel_stats.json"

def record_funnel_drop(reason_key):
    """Zlicza ile razy dany modul zablokowal sygnal lub napotkal brak danych w ciagu 24H."""
    try:
        d = json.load(open(FUNNEL_FILE, encoding="utf-8")) if os.path.exists(FUNNEL_FILE) else {}
        d[reason_key] = int(d.get(reason_key, 0)) + 1
        json.dump(d, open(FUNNEL_FILE, "w", encoding="utf-8"), indent=2)
    except Exception: pass
