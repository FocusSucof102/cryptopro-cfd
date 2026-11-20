import os, json
from flask import jsonify, request
from concurrent.futures import ThreadPoolExecutor

HTML_UI = """<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CRYPTO PRO CFD 2.0</title>
<style>
body{background:#0b0f17;color:#e5e7eb;font-family:system-ui,sans-serif;margin:0;padding:12px}
.card{background:#131a29;border:1px solid #1f2937;border-radius:12px;padding:14px;margin-bottom:12px}
h1{font-size:18px;margin:0 0 8px;color:#38bdf8} h2{font-size:15px;margin:0 0 8px;color:#fbbf24}
.btn{background:#2563eb;color:#fff;border:none;border-radius:8px;padding:9px 13px;font-weight:600;cursor:pointer;margin:3px 2px;font-size:13px}
.btn-g{background:#059669} .btn-y{background:#d97706}
input{background:#0b0f17;color:#fff;border:1px solid #374151;border-radius:8px;padding:8px 10px;width:130px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px}
.stat{background:#0f1623;padding:10px;border-radius:8px;border:1px solid #1e293b;font-size:13px}
.tag{display:inline-block;padding:3px 8px;border-radius:6px;font-size:12px;background:#1e293b;color:#93c5fd;margin:2px}
</style></head><body>
<div class="card"><h1>⚡ CRYPTO PRO CFD 2.0 — Pulpit Chrome</h1><div id="top-bar">Ładowanie...</div>
<div style="margin-top:8px"><button class="btn" onclick="loadState()">🔄 Odśwież</button>
<button class="btn btn-g" onclick="runCfd()">⚡ Skanuj CFD</button>
<button class="btn btn-y" onclick="runPd()">🚀 Pump & Dump (7 Wzorców)</button></div></div>
<div class="card"><h2>🛡️ Audytor Kontraktu (Honeypot / Mint / Tax)</h2>
<input id="aud-sym" value="RAVE"> <button class="btn btn-g" onclick="runAudit()">🔍 Sprawdź Kod</button>
<div id="aud-out" style="margin-top:8px;font-size:13px"></div></div>
<div class="card" id="scan-card" style="display:none"><h2 id="scan-t">Wyniki</h2><div id="scan-out"></div></div>
<div class="card"><h2>💓 Watchdog & Zdrowie Modułów 24/7</h2><div class="grid" id="wd-box"></div></div>
<div class="card"><h2>🕒 Analityk Sesji Dobowych (Netto po prowizji -0.07R)</h2><div class="grid" id="sess-box"></div></div>
<div class="card"><h2>🧪 3 Laboratoria + Live CFD (Netto po prowizji -0.07R)</h2><div class="grid" id="labs"></div></div>
<div class="card"><h2>🌐 Wywiad Sieciowy</h2><div id="news" style="font-size:13px"></div></div>
<script>
async function loadState(){
  const d=await(await fetch('/api/web_full_state')).json();
  document.getElementById('top-bar').innerHTML=`<span class="tag">${d.btc}</span> <span class="tag">Tuner: ${d.tuner.min_prob||58}%</span>`;
  let g=''; for(const[k,v] of Object.entries(d.labs)){const c=v.net_r>=0?'#34d399':'#f87171';g+=`<div class="stat"><b>${k}</b><br>${v.closed}/${v.total} | WR: <b>${v.wr}%</b><br>Netto: <b style="color:${c}">${v.net_r>=0?'+':''}${v.net_r}R</b></div>`;}
  document.getElementById('labs').innerHTML=g;
  let w=''; for(const[k,v] of Object.entries(d.watchdog||{})){const ok=v.misses===0;w+=`<div class="stat"><b>${ok?'🟢':'🔴'} ${k}</b><br><small>${v.time_str||'-'}</small><br>${v.note||'OK'} (Restarty: ${v.restarts||0})</div>`;} document.getElementById('wd-box').innerHTML=w||'Oczekiwanie na cykl...';
  let s=''; for(const[k,v] of Object.entries(d.sessions||{})){const c=v.net_r>=0?'#34d399':'#f87171';s+=`<div class="stat"><b>${k}</b><br>Próby: ${v.count} | WR: <b>${v.wr}%</b><br>Netto: <b style="color:${c}">${v.net_r>=0?'+':''}${v.net_r}R</b></div>`;} document.getElementById('sess-box').innerHTML=s;
  document.getElementById('news').innerHTML=(d.news||[]).map(x=>`<div style="margin-bottom:4px">${x}</div>`).join('')||'Brak alertów';
}
async function runAudit(){const s=document.getElementById('aud-sym').value;document.getElementById('aud-out').innerHTML='⏳ Skanuję...';const d=await(await fetch('/api/web_audit_contract?sym='+encodeURIComponent(s))).json();document.getElementById('aud-out').innerHTML=d.html;}
async function runCfd(){const c=document.getElementById('scan-card');c.style.display='block';document.getElementById('scan-t').innerText='⚡ Skaner CFD (TOP-60)';document.getElementById('scan-out').innerHTML='⏳ Skanuję...';const d=await(await fetch('/api/web_scan_cfd')).json();document.getElementById('scan-out').innerHTML=d.hits.map(h=>`<div class="stat" style="margin-bottom:6px"><b>${h.symbol} (${h.side})</b> | Szansa: <b>${h.win_prob}%</b><br>Wejście: <code>${h.entry}</code> | SL: <code>${h.stop}</code></div>`).join('')||'Brak sygnałów >=52%';}
async function runPd(){const c=document.getElementById('scan-card');c.style.display='block';document.getElementById('scan-t').innerText='🚀 Skaner Pump & Dump (7 Wzorców)';document.getElementById('scan-out').innerHTML='⏳ Skanuję...';const d=await(await fetch('/api/web_scan_pd')).json();document.getElementById('scan-out').innerHTML=d.hits.length?d.hits.map(h=>`<div class="stat" style="margin-bottom:6px"><b>${h.mode} — ${h.symbol} (${h.side})</b> | <b>${h.win_prob}%</b><br><i>${h.pattern_fit}</i><br>${h.narrative}<br>Cena: <code>${h.price}</code> | SL: <code>${h.stop}</code></div>`).join(''):`Przeskanowano ${d.scanned} aktywnych par — brak aktywnej paraboli.`;}
loadState();setInterval(loadState,30000);
</script></body></html>"""

import session_analytics_mod as sam
def register_web_ui(app, cp_mod, apm, atm, cam, wpr):
    """Realizuje logike: register web ui. Parametry: app, cp_mod, apm, atm, cam, wpr."""
    if "api_web_full_state" in app.view_functions: return
    @app.route("/api/web_full_state")
    def api_web_full_state():
        t_st = atm.get_tuner_params()
        _, btc_lbl = cp_mod.get_live_btc_regime()
        news, _ = wpr.fetch_web_pump_intel()
        labs = {}
        for k_l, fn_l in [("TOP60_SHADOW", "market_shadow_lab.json"), ("WILD_61_160", "wild_market_lab.json"), ("MICRO_161_PLUS", "micro_market_lab.json"), ("LIVE_CFD", cp_mod.CFD_HIST_FILE)]:
            arr = json.load(open(fn_l)) if os.path.exists(fn_l) else []
            closed = [x for x in arr if x.get("closed_final")]
            net_r = round(sum(float(x.get("res_r", 0)) - 0.07 for x in closed), 2)
            wr = round(sum(1 for x in closed if float(x.get("res_r", 0)) > 0) / max(1, len(closed)) * 100.0, 1)
            labs[k_l] = {"total": len(arr), "closed": len(closed), "wr": wr, "net_r": net_r}
        wd_data = json.load(open("module_heartbeats.json")) if os.path.exists("module_heartbeats.json") else {}
        return jsonify({"tuner": t_st, "btc": btc_lbl, "news": news, "labs": labs, "watchdog": wd_data, "sessions": sam.compute_session_edge()})

    @app.route("/api/web_audit_contract")
    def api_web_audit_contract():
        return jsonify({"html": cam.audit_token_contract(request.args.get("sym", "RAVE"))})

    @app.route("/api/web_scan_cfd")
    def api_web_scan_cfd():
        syms, rules, hits = apm.get_cfd_top60_symbols(), cp_mod.load_settings().get("rules", {}), []
        with ThreadPoolExecutor(max_workers=12) as p:
            for h in p.map(lambda sm: cp_mod._scan_one_coin(("BITGET", sm, 1.0, rules, ["15m", "1h", "4h", "1d"], 1000.0, 1.5)), syms):
                if h and isinstance(h, dict) and h.get("win_prob", 0) >= 52: hits.append(h)
        hits.sort(key=lambda x: -x.get("win_prob", 0))
        return jsonify({"hits": hits})

    @app.route("/api/web_scan_pd")
    def api_web_scan_pd():
        syms, hits = apm.get_all_futures_symbols(), []
        with ThreadPoolExecutor(max_workers=20) as p:
            for r in p.map(apm.scan_macro_pump_dump_coin, syms):
                if r: hits.append(r)
        hits.sort(key=lambda x: -x.get("win_prob", 0))
        return jsonify({"scanned": len(syms), "hits": hits})

    app.view_functions["index"] = lambda: HTML_UI
