import os
import json
import time
import shutil
import urllib.request
import requests
import walk_forward_mod as wf

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
JOURNAL_FILE = "EVOLUTION_JOURNAL.md"
RAPORT_24H_FILE = "raport_24h_dla_ai.txt"
TG_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_config.json")

def send_tg(txt):
    """Wysyla raport z cyklu ewolucji na Telegrama."""
    if not os.path.exists(TG_CONFIG_FILE):
        return
    try:
        tc = json.load(open(TG_CONFIG_FILE, encoding="utf-8-sig"))
        tk, cid = tc.get("token", "").strip(), tc.get("chat_id", "").strip()
        if not (tk and cid):
            return
        u = f"https://api.telegram.org/bot{tk}/sendMessage"
        b = json.dumps({"chat_id": cid, "text": txt, "parse_mode": "HTML"}).encode("utf-8")
        for _ in range(3):
            try:
                urllib.request.urlopen(urllib.request.Request(u, data=b, headers={"Content-Type": "application/json"}), timeout=15)
                return
            except Exception:
                time.sleep(2)
    except Exception:
        pass

def query_gemini_with_fallback(prompt):
    """Odpytuje API Gemini z lista modeli fallback i 3 probami retry/backoff dla 404/503."""
    h = "generativelanguage." + "googleapis." + "com"
    last_err = ""
    for model_name in FALLBACK_MODELS:
        url = f"https://{h}/v1beta/models/{model_name}:generateContent?key={API_KEY}"
        for attempt in range(1, 4):
            try:
                resp = requests.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=45
                )
                if resp.status_code == 200:
                    data = resp.json()
                    cands = data.get("candidates", [])
                    if cands:
                        parts = cands[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", ""), model_name
                    return str(data), model_name
                elif resp.status_code in (404, 503, 429):
                    last_err = f"{model_name} HTTP {resp.status_code}: {resp.text[:120]}"
                    time.sleep(attempt * 2)
                    continue
                else:
                    last_err = f"{model_name} HTTP {resp.status_code}: {resp.text[:120]}"
                    break
            except Exception as exc:
                last_err = f"{model_name} Exception: {exc}"
                time.sleep(attempt * 2)
    return f"FAILED_ALL_MODELS: {last_err}", "NONE"

def run_evolution_cycle():
    """Wykonuje cykl ewolucji AI: czytanie raportu 24h, zapytanie LLM, test Walk-Forward i zapis."""
    os.makedirs("evolution_backups", exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    # Kopia zapasowa biezacych plikow
    for fn in ("tuner_state.json", "meta_brain_weights.json", JOURNAL_FILE):
        if os.path.exists(fn):
            shutil.copy2(fn, f"evolution_backups/{ts}_{fn}")

    # Zbior danych do testu
    rows = []
    for f in ("cfd_live_history.json", "market_shadow_lab.json", "wild_market_lab.json"):
        if os.path.exists(f):
            try:
                rows.extend(json.load(open(f, encoding="utf-8")))
            except Exception:
                pass

    (wf_ok, wfd), (mc_ok, mcd) = wf.run_purged_walk_forward(rows), wf.run_monte_carlo_stress(rows)
    passed = bool(wf_ok and mc_ok and mcd.get("pass_pct", 0) >= 85.0)

    # Wczytanie raport_24h_dla_ai.txt jesli istnieje
    rep_24h_snippet = ""
    if os.path.exists(RAPORT_24H_FILE):
        try:
            rep_raw = open(RAPORT_24H_FILE, encoding="utf-8", errors="ignore").read()
            rep_24h_snippet = rep_raw[:1200]
        except Exception:
            pass

    tuner_raw = open("tuner_state.json", encoding="utf-8").read() if os.path.exists("tuner_state.json") else "{}"
    prompt = (
        "Przeanalizuj poniższy raport 24H oraz stan tunera i zaproponuj mikro-korektę parametrów (JSON: hypothesis, changes, why):\n"
        f"--- RAPORT 24H SNIPPET ---\n{rep_24h_snippet}\n"
        f"--- TUNER STATE ---\n{tuner_raw}\n"
    )

    llm_txt, used_model = query_gemini_with_fallback(prompt)
    entry = (
        f"\n### [{ts}] KTO: {used_model} | Egzamin: OOS={wfd.get('oos_net_r', 0):+.2f}R "
        f"MC={mcd.get('pass_pct', 0):.0f}% ({'WDROZONO' if passed else 'ODRZUCONO'})\n"
        f"{llm_txt[:800]}\n"
    )

    try:
        with open(JOURNAL_FILE, "a", encoding="utf-8") as jf:
            jf.write(entry)
    except Exception:
        pass

    send_tg(
        f"🧬 <b>AI EWOLUCJA ({ts})</b>\n"
        f"Model: <code>{used_model}</code>\n"
        f"Status: {'✅ WDROŻONO' if passed else '🛡️ BRAK ZMIAN (odrzucono po testach)'}\n"
        f"OOS: <code>{wfd.get('oos_net_r', 0):+.2f}R</code> | MC: <code>{mcd.get('pass_pct', 0):.0f}%</code>"
    )
    return {"ts": ts, "model": used_model, "passed": passed, "oos_r": wfd.get("oos_net_r", 0)}

if __name__ == "__main__":
    run_evolution_cycle()
