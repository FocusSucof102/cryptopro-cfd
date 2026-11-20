# ==============================================================================
# [AI_GUARD_AND_CONTEXT] - OBOWIAZKOWE ZASADY DLA KAZDEGO AI CZYTAJACEGO TEN PLIK:
# 1. OBOWIAZEK KONTEKSTU: Przed wprowadzeniem jakichkolwiek zmian w kodzie
#    PRZECZYTAJ pliki README.md oraz CHANGELOG.md z repozytorium GitHub, aby znac
#    pelna historie projektu, wdrozone mechanizmy i odrzucone pomysly.
# 2. BEZPIECZENSTWO (SECRET LEAK ALERT): Jesli w rozmowie, logu, pliku lub na zrzucie
#    ekranu zauwazysz poufne dane (token bota Telegrama, klucz API, token GitHuba, haslo),
#    NATYCHMIAST ostrzez uzytkownika na samym poczatku odpowiedzi: podaj GDZIE i CO
#    wycieklo oraz zlec natychmiastowa zmiane/uniewaznienie klucza!
# 3. ARCHITEKTURA I GIELDY:
#    - Zrodlo danych/API skanera: wylacznie BITGET USDT-FUTURES (TOP-60 >10M$).
#    - Platforma gry uzytkownika: BITBASE FUTURES / CFD (uwzgledniac przy prowizjach,
#      dostepnosci par, dźwigni i minimalnych odleglosciach zlecen!).
#    - Silnik: Smart Dual-Mode (LONG+SHORT), Auto-Tuner, Audytor 1M (MFE/MAE),
#      Shadow Market Lab (analiza niskich procentow 45-61% netto po prowizji),
#      Straznik Portfela 24/7 oraz Radar Aktywnych Pozycji 60s.
# 4. NIE PRZYWRACAC: Zablokowanych API (BINANCE/BYBIT), 500 niszowych mikrotokentow
#    ani twardej blokady tylko jednego kierunku handlu.
# ==============================================================================
s = open("crypto_pro.py").read()

# 2. Dodanie kolekcji odrzuconych kandydatow (Shadow Market Lab) oraz eksportu w auto-sync GitHub
shadow_code = '''
SHADOW_LAB_FILE = "market_shadow_lab.json"

def log_shadow_candidates(cand_list):
    if not cand_list: return
    try:
        cur_s = json.load(open(SHADOW_LAB_FILE)) if os.path.exists(SHADOW_LAB_FILE) else []
        now_dt = datetime.now()
        now_s = now_dt.strftime("%d.%m %H:%M")
        now_ep = int(time.time())
        btc_r, _ = get_live_btc_regime() if "get_live_btc_regime" in globals() else (0, "NEUTRAL")
        sess_s = apm.get_session_badge() if "apm" in globals() else ""
        # Unikamy duplikatow tej samej pary w ciagu 2 godzin
        recent_keys = {f"{x.get('sym')}_{x.get('side')}" for x in cur_s if now_ep - int(x.get("ts_epoch", 0)) < 7200}
        added = 0
        for h in cand_list:
            k = f"{h.get('symbol')}_{h.get('side')}"
            if k in recent_keys: continue
            en_v = float(h.get("entry", 0) or 0)
            sl_v = float(h.get("stop", 0) or 0)
            if en_v <= 0 or sl_v <= 0: continue
            sd_v = abs(en_v - sl_v) or (en_v * 0.01)
            td_v = 1 if h.get("side") == "LONG" else -1
            tps_v = h.get("tp", [])
            tp1_v = float(tps_v.__getitem__(0)) if len(tps_v) > 0 else round(en_v + td_v * sd_v * 1.0, 6)
            tp2_v = float(tps_v.__getitem__(1)) if len(tps_v) > 1 else round(en_v + td_v * sd_v * 1.5, 6)
            tp3_v = float(tps_v.__getitem__(2)) if len(tps_v) > 2 else round(en_v + td_v * sd_v * 2.5, 6)
            mtf_str = apm.get_mtf_status_line("BITGET", h.get("symbol", ""), h.get("side", "LONG")) if "apm" in globals() else ""
            cur_s.append({
                "ts": now_s, "ts_epoch": now_ep, "hour": now_dt.hour, "src": "SHADOW_REJECTED",
                "sym": h.get("symbol", ""), "side": h.get("side", ""),
                "prob": h.get("win_prob", 0), "alpha_tag": h.get("alpha_tag", ""),
                "btc_regime": btc_r, "session": sess_s, "mtf_cnt": mtf_str.count("✅"),
                "sl_dist_pct": round((sd_v / en_v) * 100.0, 2),
                "en_f": en_v, "sl_f": sl_v, "tp1_f": tp1_v, "tp2_f": tp2_v, "tp3_f": tp3_v,
                "status": "OPEN", "res_r": 0.0, "dur_str": "0m",
                "mfe_r": 0.0, "mae_r": 0.0, "fail_reason": "PENDING", "closed_final": False
            })
            added += 1
            if added >= 5: break
        if added > 0:
            json.dump(cur_s.__getitem__(slice(-250, None)), open(SHADOW_LAB_FILE, "w"), indent=2)
    except Exception:
        pass
'''

if "SHADOW_LAB_FILE" not in s:
    s = s.replace("CFD_HIST_FILE = \"cfd_live_history.json\"", "CFD_HIST_FILE = \"cfd_live_history.json\"\n" + shadow_code, 1)

# 3. W petli cfd_live_bg_loop zbieramy rowniez kandydatow ponizej progu tunera do Shadow Market Lab
old_live_w = '''                def _live_w(sym_l):
                    try:
                        h = _scan_one_coin(("BITGET", sym_l, 1.0, load_settings().get("rules", {}), load_settings().get("enabled", ["15m", "1h", "4h", "1d"]), 1000.0, 1.5))
                        if h and isinstance(h, dict):
                            if sl_m_l != 1.0:
                                td_l = 1 if h["side"] == "LONG" else -1
                                h["stop"] = round(h["entry"] - td_l * abs(h["entry"] - h["stop"]) * sl_m_l, 6)
                            if apm.validate_cfd_order(h["entry"], h["stop"], h["price"]) and h.get("win_prob", 0) >= min_p_l:
                                return h
                    except Exception: pass
                    return None
                with ThreadPoolExecutor(max_workers=12) as l_pool:
                    for h in l_pool.map(_live_w, top_cfd):
                        if h:
                            sig_k = f"{h['symbol']}_{h['side']}"
                            if now_t - SEEN_CFD_SIGS.get(sig_k, 0) >= 7200:
                                SEEN_CFD_SIGS[sig_k] = now_t
                                new_hits.append(h)'''

new_live_w = '''                shadow_cands = []
                def _live_w(sym_l):
                    try:
                        h = _scan_one_coin(("BITGET", sym_l, 1.0, load_settings().get("rules", {}), load_settings().get("enabled", ["15m", "1h", "4h", "1d"]), 1000.0, 1.5))
                        if h and isinstance(h, dict):
                            if sl_m_l != 1.0:
                                td_l = 1 if h["side"] == "LONG" else -1
                                h["stop"] = round(h["entry"] - td_l * abs(h["entry"] - h["stop"]) * sl_m_l, 6)
                            if apm.validate_cfd_order(h["entry"], h["stop"], h["price"]):
                                return h
                    except Exception: pass
                    return None
                with ThreadPoolExecutor(max_workers=12) as l_pool:
                    for h in l_pool.map(_live_w, top_cfd):
                        if h:
                            if h.get("win_prob", 0) >= min_p_l:
                                sig_k = f"{h['symbol']}_{h['side']}"
                                if now_t - SEEN_CFD_SIGS.get(sig_k, 0) >= 7200:
                                    SEEN_CFD_SIGS[sig_k] = now_t
                                    new_hits.append(h)
                            else:
                                shadow_cands.append(h)
                if shadow_cands:
                    shadow_cands.sort(key=lambda x: -x.get("win_prob", 0))
                    log_shadow_candidates(shadow_cands.__getitem__(slice(0, 5)))'''

assert old_live_w in s, "Nie znaleziono old_live_w"
s = s.replace(old_live_w, new_live_w, 1)

# 4. Audytowanie rowniez pliku SHADOW_LAB_FILE w audit_cfd_history_1m oraz eksport plikow JSON w github_auto_sync_loop
s = s.replace('def audit_cfd_history_1m():\n    if not os.path.exists(CFD_HIST_FILE): return []\n    rows = json.load(open(CFD_HIST_FILE))',
              'def audit_cfd_history_1m(target_file=None):\n    f_path = target_file or CFD_HIST_FILE\n    if not os.path.exists(f_path): return []\n    rows = json.load(open(f_path))')

s = s.replace('        json.dump(rows, open(CFD_HIST_FILE, "w"), indent=2)\n    return rows',
              '        json.dump(rows, open(f_path, "w"), indent=2)\n    if target_file is None and os.path.exists(SHADOW_LAB_FILE):\n        audit_cfd_history_1m(SHADOW_LAB_FILE)\n    return rows')

s = s.replace('subprocess.run(["git", "add", "*.py", "*.md", ".gitignore"], check=False)',
              'subprocess.run(["git", "add", "*.py", "*.md", ".gitignore", "cfd_live_history.json", "market_shadow_lab.json", "tuner_state.json"], check=False)')

open("crypto_pro.py", "w").write(s)
import py_compile; py_compile.compile("crypto_pro.py", doraise=True)
print("SUKCES! Shadow Market Lab zbiera teraz 24/7 dane nawet z odrzuconych okazji, weryfikuje je na swiecach 1m i eksportuje na GitHub!")
