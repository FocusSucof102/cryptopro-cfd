#!/usr/bin/env python3
import os, io, json, time, threading, requests
from datetime import datetime
from flask import Flask, render_template_string, jsonify, redirect, url_for
import scanner as sc

app = Flask(__name__)
LATEST_RESULTS = {"hits": [], "near": [], "time": "Oczekuje na skan..."}
PROGRESS = {"running": False, "pct": 0, "eta": 0, "sym": "", "done": 0, "total": 30}

def tg_url(token, method):
    return "https://" + "api.telegram.org" + "/bot" + token + "/" + method

def make_chart_png(symbol):
    h1 = sc.fetch_klines(symbol, "1h", 80)
    if not h1: return None
    closes = [round(x, 4) for x in h1["c"][-45:]]
    labels = [str(i) for i in range(len(closes))]
    datasets = [{"label": f"{symbol} (1H)", "data": closes, "borderColor": "#58a6ff", "backgroundColor": "rgba(88,166,255,0.12)", "borderWidth": 2, "pointRadius": 0, "fill": True}]
    chart_cfg = {"type": "line", "data": {"labels": labels, "datasets": datasets}, "options": {"title": {"display": True, "text": f"{symbol} - Wykres 1H", "fontColor": "#fff"}, "legend": {"labels": {"fontColor": "#c9d1d9"}}, "scales": {"xAxes": [{"display": False}], "yAxes": [{"ticks": {"fontColor": "#8b949e"}, "gridLines": {"color": "#30363d"}}]}}}
    r = requests.post("https://quickchart.io", json={"backgroundColor": "#0d1117", "width": 700, "height": 380, "chart": chart_cfg}, timeout=15)
    return io.BytesIO(r.content) if r.status_code == 200 else None

def run_web_scan(tg_chat=None, tg_tok=None, tg_msg_id=None):
    if PROGRESS["running"]: return
    cfg_s = sc.load_settings()
    cap, rpct, top_n = cfg_s["capital"], cfg_s["risk_pct"], cfg_s["top_n"]
    PROGRESS.update({"running": True, "pct": 1, "eta": int(top_n * 0.45), "sym": "Start...", "done": 0, "total": top_n})
    start_t = time.time()
    try:
        enabled = json.load(open(sc.CONFIG_FILE)).get("enabled_filters", ["adx","macro","vol"]) if os.path.exists(sc.CONFIG_FILE) else ["adx","macro","vol"]
        top_symbols, rules_map, prices_map = sc.get_market_meta(top_n)
        hits, near_list = [], []
        last_tg_upd = 0

        for idx, sym in enumerate(top_symbols, 1):
            elapsed = time.time() - start_t
            avg_per_item = elapsed / idx
            eta_sec = max(1, int((top_n - idx) * avg_per_item))
            pct = int((idx / top_n) * 100)
            PROGRESS.update({"pct": pct, "eta": eta_sec, "sym": sym, "done": idx})

            if tg_chat and tg_tok and tg_msg_id and (time.time() - last_tg_upd >= 2.0 or idx == top_n):
                last_tg_upd = time.time()
                filled = int(pct / 10)
                bar = "█" * filled + "░" * (10 - filled)
                txt = f"⏳ <b>Skanowanie rynku ({sym})</b>\n<code>[{bar}] {pct}%</code>\n⏱ Pozostaly czas: <b>~{eta_sec}s</b>"
                try: requests.post(tg_url(tg_tok, "editMessageText"), json={"chat_id": tg_chat, "message_id": tg_msg_id, "text": txt, "parse_mode": "HTML"}, timeout=5)
                except Exception: pass

            d1 = sc.fetch_klines(sym, "1d", 250); time.sleep(0.18)
            if not d1 or sc.get_trend(d1["c"]) == 0: continue
            td = sc.get_trend(d1["c"])
            h4 = sc.fetch_klines(sym, "4h", 100); time.sleep(0.18)
            if not h4 or sc.get_trend(h4["c"]) != td: continue
            h1 = sc.fetch_klines(sym, "1h", 750); time.sleep(0.18)
            if not h1 or sc.get_trend(h1["c"]) != td: continue
            m15 = sc.fetch_klines(sym, "15m", 20); time.sleep(0.18)
            if not m15: continue

            price, i = prices_map[sym], len(h1["c"]) - 1
            a_vals = sc.atr(h1["h"], h1["l"], h1["c"]); atr_val = a_vals[i]
            if atr_val <= 0: continue
            level = max(h1["h"][i - sc.LEVEL_CANDLES:i]) if td == 1 else min(h1["l"][i - sc.LEVEL_CANDLES:i])
            dist_atr = (level - price) / atr_val if td == 1 else (price - level) / atr_val
            beyond_15m = m15["c"][-1] > level if td == 1 else m15["c"][-1] < level
            beyond_now = td * (price - level) > 0
            ext_atr = td * (price - level) / atr_val
            e200, adx_v = sc.ema(d1["c"], 200), sc.adx(h1["h"], h1["l"], h1["c"])
            f_vals = {"adx": adx_v[i] >= sc.ADX_MIN, "vol": h1["v"][i] >= sc.VOL_MULT * sc.mean(h1["v"][i - 20:i]), "macro": (d1["c"][-1] > e200[-1]) == (td == 1)}
            missing = [k for k in enabled if not f_vals.get(k, False)]

            if beyond_now and beyond_15m and ext_atr <= sc.NEAR_ATR and not missing: is_trig = True
            elif not beyond_now and dist_atr <= sc.NEAR_ATR and not missing: is_trig = False
            else:
                if not beyond_now and dist_atr <= 1.5:
                    near_list.append({"symbol": sym, "side": "LONG" if td == 1 else "SHORT", "price": price, "dist": round(dist_atr, 2), "missing": ",".join(missing) or "Blisko wybicia"})
                continue

            rules, entry, stop_dist = rules_map[sym], (price if is_trig else level), sc.STOP_ATR * atr_val
            stop = entry - td * stop_dist
            tp = [entry + td * k * stop_dist for k in (1, 2, 3, 4, 5)]
            r_unit = stop_dist + ((sc.FEE_SIDE_PCT/100.0) + (sc.SLIPPAGE_BPS/10000.0)) * (entry + stop)
            raw_min = max(rules["min_qty"], max(rules["min_notional"], 5.5) / entry)
            min_q = float(sc.Decimal(str(sc.math.ceil(raw_min / rules["step"]))) * sc.Decimal(str(rules["step"])))
            req_cap = sc.math.ceil((min_q * r_unit) / (rpct / 100.0))
            hits.append({"symbol": sym, "side": "LONG" if td == 1 else "SHORT", "is_trig": is_trig, "price": price, "entry": entry, "stop": stop, "tp": tp, "req_cap": req_cap})

        LATEST_RESULTS["hits"] = sorted(hits, key=lambda x: x["req_cap"])
        LATEST_RESULTS["near"] = sorted(near_list, key=lambda x: x["dist"])
        LATEST_RESULTS["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finally:
        PROGRESS.update({"running": False, "pct": 100, "eta": 0, "sym": "Gotowe"})

HTML_TPL = """<!DOCTYPE html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Krypto Skaner Pro</title>
<style>
body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;margin:0;padding:12px}
.hdr{display:flex;justify-content:space-between;align-items:center;background:#161b22;padding:12px;border-radius:10px;border:1px solid #30363d;margin-bottom:12px;gap:6px}
.btn{background:#238636;color:#fff;border:none;padding:9px 12px;border-radius:6px;font-weight:bold;text-decoration:none;font-size:13px;cursor:pointer}
.btn-sec{background:#1f6feb}
.pwrap{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:10px;margin-bottom:12px;display:{{'block' if prog.running else 'none'}}}
.pbar-bg{background:#0d1117;border-radius:8px;height:18px;overflow:hidden;border:1px solid #30363d;margin-top:6px}
.pbar-fill{background:linear-gradient(90deg,#1f6feb,#3fb950);height:100%;width:{{prog.pct}}%;transition:width 0.4s ease}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-bottom:12px}
.long{color:#3fb950;font-weight:bold} .short{color:#f85149;font-weight:bold}
.badge{padding:2px 7px;border-radius:12px;font-size:11px;font-weight:bold;background:#1f6feb;color:#fff} .trig{background:#238636}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
.box{background:#0d1117;padding:6px;border-radius:6px;border:1px solid #21262d;font-size:12px;text-align:center} .cp{cursor:pointer;color:#58a6ff;font-weight:bold}
</style>
<script>
function copyVal(v){navigator.clipboard.writeText(v);alert('Skopiowano: '+v);}
function triggerScan(){
  document.getElementById('pwrap').style.display='block';
  fetch('/start_scan');
  pollProgress();
}
function pollProgress(){
  let iv = setInterval(()=>{
    fetch('/progress').then(r=>r.json()).then(d=>{
      document.getElementById('pfill').style.width = d.pct + '%';
      document.getElementById('ptxt').innerText = 'Skanuje: ' + d.sym + ' (' + d.done + '/' + d.total + ') — ' + d.pct + '% | Pozostalo: ~' + d.eta + 's';
      if(!d.running && d.pct >= 100){ clearInterval(iv); location.reload(); }
    });
  }, 800);
}
window.onload = ()=>{ if({{'true' if prog.running else 'false'}}) pollProgress(); };
</script>
</head><body>
<div class="hdr">
  <div><b>📊 SKANER TOP {{top_n}}</b><br><small style="color:#8b949e">{{res.time}}</small></div>
  <div style="display:flex;gap:6px">
    <a href="/demo" class="btn btn-sec">🧪 Demo</a>
    <button onclick="triggerScan()" class="btn">🔍 Skanuj</button>
  </div>
</div>
<div id="pwrap" class="pwrap">
  <div id="ptxt" style="font-size:12px;color:#58a6ff;font-weight:bold">Skanuje: {{prog.sym}} — {{prog.pct}}% | Pozostalo: ~{{prog.eta}}s</div>
  <div class="pbar-bg"><div id="pfill" class="pbar-fill"></div></div>
</div>
<h3>🎯 Aktywne Okazje ({{res.hits|length}})</h3>
{% for h in res.hits %}<div class="card"><div style="display:flex;justify-content:space-between"><span><b>{{h.symbol}}</b> <span class="{{'long' if h.side=='LONG' else 'short'}}">{{h.side}}</span></span><span class="badge {{'trig' if h.is_trig else ''}}">{{'TRIGGER' if h.is_trig else 'GOTOWY'}} | Min. {{h.req_cap}}$</span></div>
<div class="grid"><div class="box">Cena<br><b>{{h.price}}</b></div><div class="box" onclick="copyVal('{{h.entry}}')">Wejscie 📋<br><span class="cp">{{h.entry|round(4)}}</span></div><div class="box" onclick="copyVal('{{h.stop}}')">SL 📋<br><span class="cp" style="color:#f85149">{{h.stop|round(4)}}</span></div></div>
<div class="grid" style="grid-template-columns:repeat(5,1fr)">{% for t in h.tp %}<div class="box" onclick="copyVal('{{t|round(4)}}')">{{loop.index}}R 📋<br><span class="cp">{{t|round(3)}}</span></div>{% endfor %}</div></div>
{% else %}<div class="card" style="color:#8b949e">Brak aktywnych sygnalow. Kliknij <b>Skanuj</b> lub <b>Demo</b>.</div>{% endfor %}
<h3>👀 Obserwowane ({{res.near|length}})</h3>
{% for n in res.near %}<div class="card" style="padding:8px 12px;display:flex;justify-content:space-between;font-size:13px"><span><b>{{n.symbol}}</b> <span class="{{'long' if n.side=='LONG' else 'short'}}">{{n.side}}</span> ({{n.price}})</span><span style="color:#d29922">{{n.dist}}A | {{n.missing}}</span></div>{% endfor %}
</body></html>"""

@app.route("/scan")
def old_scan(): return redirect(url_for("index"))

@app.route("/")
def index():
    return render_template_string(HTML_TPL, res=LATEST_RESULTS, prog=PROGRESS, top_n=sc.load_settings()["top_n"])

@app.route("/start_scan")
def start_scan_bg():
    if not PROGRESS["running"]:
        threading.Thread(target=run_web_scan, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/progress")
def get_progress():
    return jsonify(PROGRESS)

@app.route("/demo")
def do_demo():
    LATEST_RESULTS["hits"] = [
        {"symbol": "SOLUSDT", "side": "LONG", "is_trig": True, "price": 142.85, "entry": 142.50, "stop": 138.20, "tp": [146.8, 151.1, 155.4, 159.7, 164.0], "req_cap": 65},
        {"symbol": "DOGEUSDT", "side": "LONG", "is_trig": False, "price": 0.1455, "entry": 0.1452, "stop": 0.1380, "tp": [0.1524, 0.1596, 0.1668, 0.1740, 0.1812], "req_cap": 18}
    ]
    LATEST_RESULTS["near"] = [{"symbol": "BTCUSDT", "side": "SHORT", "price": 62747.7, "dist": 0.45, "missing": "adx,vol"}]
    LATEST_RESULTS["time"] = "TRYB DEMO (Podglad wizualny)"
    return redirect(url_for("index"))

def send_tg_menu(cid, tok, text="<b>Panel Sterowania Skanerem</b>"):
    kb = {"inline_keyboard": [
        [{"text": "🔍 Skanuj Rynek Teraz", "callback_data": "scan_now"}],
        [{"text": "📈 Wykres BTCUSDT", "callback_data": "chart_BTCUSDT"}, {"text": "📈 Wykres SOLUSDT", "callback_data": "chart_SOLUSDT"}],
        [{"text": "📊 Ostatnie z CSV", "callback_data": "show_csv"}, {"text": "🧪 Podglad Demo", "callback_data": "demo_tg"}]
    ]}
    requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": text, "parse_mode": "HTML", "reply_markup": kb}, timeout=10)

def telegram_bot_listener():
    if not os.path.exists(sc.TG_CONFIG_FILE): return
    cfg = json.load(open(sc.TG_CONFIG_FILE))
    tok, cid = cfg.get("token","").strip(), cfg.get("chat_id","").strip()
    if not tok or not cid: return
    send_tg_menu(cid, tok, "🤖 <b>Panel Gotowy!</b> Kliknij przycisk ponizej:")
    offset = 0
    while True:
        try:
            r = requests.get(tg_url(tok, "getUpdates"), params={"offset": offset, "timeout": 15}, timeout=20).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                if "message" in u: send_tg_menu(cid, tok)
                elif "callback_query" in u:
                    cb = u["callback_query"]["data"]
                    requests.post(tg_url(tok, "answerCallbackQuery"), json={"callback_query_id": u["callback_query"]["id"]})
                    if cb == "scan_now":
                        res_m = requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "⏳ <b>Uruchamiam skaner...</b>\n<code>[░░░░░░░░░░] 0%</code>", "parse_mode": "HTML"}).json()
                        mid = res_m.get("result", {}).get("message_id")
                        def bg_tg():
                            run_web_scan(cid, tok, mid)
                            hits, near = LATEST_RESULTS["hits"], LATEST_RESULTS["near"]
                            requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": mid, "text": f"✅ <b>Skan zakonczony (100%)!</b>\n🎯 Okazje: <b>{len(hits)}</b> | 👀 W poblizu: <b>{len(near)}</b>", "parse_mode": "HTML"})
                            for h in hits:
                                tp1, tp2, tp3, tp4, tp5 = h["tp"]
                                ico = "🟢" if h["side"] == "LONG" else "🔴"
                                st = "TRIGGER" if h["is_trig"] else "GOTOWY"
                                card = (
                                    f"🚨 <b>{st} | {h['symbol']}</b>\n"
                                    f"{ico} Kierunek: <b>{h['side']}</b> | 💰 Min. Kap: <b>{h['req_cap']}$</b>\n\n"
                                    f"📊 Cena teraz: <code>{sc.fmt_p(h['price']).strip()}</code>\n"
                                    f"🎯 Wejście: <code>{sc.fmt_p(h['entry']).strip()}</code>\n"
                                    f"🛑 Stop Loss: <code>{sc.fmt_p(h['stop']).strip()}</code>\n"
                                    f"───────────────\n"
                                    f"✅ 1R: <code>{sc.fmt_p(tp1).strip()}</code>  |  2R: <code>{sc.fmt_p(tp2).strip()}</code>\n"
                                    f"✅ 3R: <code>{sc.fmt_p(tp3).strip()}</code>  |  4R: <code>{sc.fmt_p(tp4).strip()}</code>\n"
                                    f"🏆 5R: <code>{sc.fmt_p(tp5).strip()}</code>"
                                )
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": card, "parse_mode": "HTML"}, timeout=10)
                            if near:
                                rows = [f"{n['symbol'].replace('USDT',''):<6} {n['side']:<5} {n['dist']:+5.2f}A ({n['missing']})" for n in near[:10]]
                                requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "👀 <b>Obserwowane / W poblizu:</b>\n<pre>" + "\n".join(rows) + "</pre>", "parse_mode": "HTML"}, timeout=10)
                            send_tg_menu(cid, tok, "Wybierz kolejna akcje:")
                        threading.Thread(target=bg_tg, daemon=True).start()
                    elif cb.startswith("chart_"):
                        sym = cb.replace("chart_", "")
                        m_c = requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": f"⏳ <b>Generuje wykres {sym}...</b>\n<code>[█████░░░░░] 50% | ~2s</code>", "parse_mode": "HTML"}).json()
                        buf = make_chart_png(sym)
                        if buf:
                            requests.post(tg_url(tok, "sendPhoto"), data={"chat_id": cid, "caption": f"📈 Wykres 1H dla <b>{sym}</b>", "parse_mode": "HTML"}, files={"photo": ("chart.png", buf, "image/png")}, timeout=15)
                            if m_c.get("result"): requests.post(tg_url(tok, "deleteMessage"), json={"chat_id": cid, "message_id": m_c["result"]["message_id"]})
                    elif cb == "demo_tg":
                        m_d = requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "⏳ <b>Generuje podglad Demo...</b>\n<code>[█████░░░░░] 50%</code>", "parse_mode": "HTML"}).json()
                        time.sleep(0.6)
                        if m_d.get("result"):
                            requests.post(tg_url(tok, "editMessageText"), json={"chat_id": cid, "message_id": m_d["result"]["message_id"], "text": "✅ <b>Podglad Demo Gotowy (100%)!</b>", "parse_mode": "HTML"})
                        demos = [
                            {"symbol": "SOLUSDT", "side": "LONG", "st": "TRIGGER", "cap": 65, "p": 142.85, "e": 142.50, "sl": 138.20, "tp": [146.8, 151.1, 155.4, 159.7, 164.0]},
                            {"symbol": "XRPUSDT", "side": "SHORT", "st": "GOTOWY", "cap": 82, "p": 0.5140, "e": 0.5120, "sl": 0.5310, "tp": [0.4930, 0.4740, 0.4550, 0.4360, 0.4170]}
                        ]
                        for d in demos:
                            tp1, tp2, tp3, tp4, tp5 = d["tp"]
                            ico = "🟢" if d["side"] == "LONG" else "🔴"
                            card = (
                                f"🚨 <b>{d['st']} [DEMO] | {d['symbol']}</b>\n"
                                f"{ico} Kierunek: <b>{d['side']}</b> | 💰 Min. Kap: <b>{d['cap']}$</b>\n\n"
                                f"📊 Cena teraz: <code>{sc.fmt_p(d['p']).strip()}</code>\n"
                                f"🎯 Wejście: <code>{sc.fmt_p(d['e']).strip()}</code>\n"
                                f"🛑 Stop Loss: <code>{sc.fmt_p(d['sl']).strip()}</code>\n"
                                f"───────────────\n"
                                f"✅ 1R: <code>{sc.fmt_p(tp1).strip()}</code>  |  2R: <code>{sc.fmt_p(tp2).strip()}</code>\n"
                                f"✅ 3R: <code>{sc.fmt_p(tp3).strip()}</code>  |  4R: <code>{sc.fmt_p(tp4).strip()}</code>\n"
                                f"🏆 5R: <code>{sc.fmt_p(tp5).strip()}</code>"
                            )
                            requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": card, "parse_mode": "HTML"})
                        obs = "BTC    SHORT +0.45A (adx,vol)\nETH    LONG  +1.12A (Blisko wybicia)"
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "👀 <b>Obserwowane / W poblizu:</b>\n<pre>" + obs + "</pre>", "parse_mode": "HTML"})
                        send_tg_menu(cid, tok, "Wybierz kolejna akcje:")
                    elif cb == "show_csv":
                        lines = open(sc.CSV_FILE).readlines()[-5:] if os.path.exists(sc.CSV_FILE) else ["Brak wpisow CSV."]
                        requests.post(tg_url(tok, "sendMessage"), json={"chat_id": cid, "text": "<b>Ostatnie wpisy CSV:</b>\n<pre>" + "".join(lines) + "</pre>", "parse_mode": "HTML"})
        except Exception: time.sleep(2)

if __name__ == "__main__":
    print(f"{sc.G}{sc.B}Otworz w Chrome: http://127.0.0.1:5000{sc.W}")
    threading.Thread(target=telegram_bot_listener, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False)
