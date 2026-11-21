import os, json, urllib.request, py_compile

API_KEY = os.environ.get("GEMINI_API_KEY", "")

def ask_gemini_strategist(context_txt):
    """Wysyla stan systemu i wyniki Walk-Forward do Gemini API i odbiera propozycje optymalizacji."""
    if not API_KEY:
        return {"error": "Brak GEMINI_API_KEY w srodowisku"}
    url = f"https://googleapis.com{API_KEY}"
    prompt = (
        "Jestes autonomicznym inzynierem quant (cel: maksymalizacja zysku netto R po prowizji -0.07R, "
        "zdawalnosc Walk-Forward OOS > 0 oraz Monte Carlo >= 85%). Przeanalizuj ponizszy stan systemu "
        "i zwroc WYLACZNIE czysty JSON z kluczami: 'hypothesis', 'target_file', 'param_changes', 'expected_gain_r'.\n\n"
        + context_txt[:12000]
    )
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    return res["candidates"][0]["content"]["parts"][0]["text"]

def run_evolution_cycle():
    """Zbiera logi, generuje hipoteze AI i zapisuje propozycje do przegladu/piaskownicy."""
    state = ""
    for fn in ("AGENTS.md", "AI_SESSION_STATE.md", "tuner_state.json", "raport_24h_dla_ai.txt"):
        if os.path.exists(fn):
            state += f"\n--- {fn} ---\n" + open(fn, encoding="utf-8", errors="ignore").read()[-3000:]
    proposal = ask_gemini_strategist(state)
    open("ai_evolution_proposals.log", "a", encoding="utf-8").write("\n=== CYKL EWOLUCJI ===\n" + str(proposal) + "\n")
    print(proposal)

if __name__ == "__main__":
    run_evolution_cycle()
