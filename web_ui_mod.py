import os, json
from flask import jsonify, request
from concurrent.futures import ThreadPoolExecutor
import session_analytics_mod as sam
import risk_guard_mod as rgm

HTML_UI = """<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CRYPTO PRO CFD 2.0</title>
<style>
body{background:#0b0f17;color:#e5e7eb;font-family:system-ui,sans-serif;margin:0;padding:12px}
.card{background:#131a29;border:1px solid #1f2937;border-radius:12px;padding:14px;margin-bottom:12px}
h1{font-size:18px;margin:0 0 8px;color:#38bdf8} h2{font-size:15px;margin:0 0 8px;color:#fbbf24}
.btn{background:#2563eb;color:#fff;border:none;border-radius:8px;padding:9px 13px;font-weight:600;cursor:pointer;margin:3px 2px;font-size:13px}
.btn-g{background:#059669} .btn-y{background:#d97706} .btn-r{background:#dc2626}
input{background:#0b0f17;color:#fff;border:1px solid #374151;border-radius:8px;padding:8px 10px;width:120px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:8px}
.stat{background:#0f1623;padding:10px;border-radius:8px;border:1px solid #1e293b;font-size:13px}
.tag{display:inline-block;padding:3px 8px;border-radius:6px;font-size:12px;background:#1e293b;color:#93c5fd;margin:2px}
.safe-on{background:#7f1d1d;color:#fca5a5;font-weight:bold}
.safe-off{background:#064e3b;color:#6ee7b7;font-weight:bold}
</style></head><body>
<div class="card"><h1>⚡ CRYPTO PRO CFD 2.0 — Pulpit Chrome</h1><div id="top-bar">Ładowanie...</div>
<div style="margin-top:8px"><button class="btn" onclick="loadState()">🔄 Odśwież</button>
<button class="btn btn-g" onclick="runCfd()">⚡ Skanuj CFD</button>
<button class="btn btn-y" onclick="runPd()">🚀 Pump & Dump (7 Wzorców)</button></div></div>

<div class="card"><h2>🛡️ Strażnik Ryzyka & Bezpiecznik Safe-Lock (200 USDT Baza)</h2>
<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
  <label>Kapitał ($): <input id="risk-cap" type="number" step="10" value="200"></label>
  <label>Ryzyko (%): <input id="risk-pct" type="number" step="0.5" value="1.0"></label>
  <label>Max DD (%): <input id="risk-dd" type="number" step="1.0" value="6.0"></label>
  <button class="btn btn-g" onclick="saveRisk()">💾 Zapisz Ryzyko</button>
  <span id="safe-badge" class="tag safe-off">SAFE-LOCK: STANDBY</span>
</div>
<div id="risk-status" style="margin-top:8px;font-size:13px;color:#94a3b8">Ładowanie parametrów depozytu...</div>
</div>

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
  try{
    const r=await fetch('/api/web_full_state');
    if(!r.ok) return;
    const d=await r.json();
    document.getElementById('top-bar').innerHTML=`<span class="tag">${d.btc||'BTC OK'}</span> <span class="tag">Tuner: ${d.tuner.min_prob||58}%</span>`;
    if(d.risk){
      document.getElementById('risk-cap').value=d.risk.capital_usdt||200;
      document.getElementById('risk-pct').value=d.risk.risk_pct||1.0;
      document.getElementById('risk-dd').value=d.risk.max_drawdown_pct||6.0;
      const sl=d.risk.safe_lock_active;
      const b=document.getElementById('safe-badge');
      b.className='tag '+(sl?'safe-on':'safe-off');
      b.innerText=sl?`🚨 SAFE-LOCK AKTYWNY (DD -${d.risk.current_drawdown_pct}%)`:'🟢 SAFE-LOCK: STANDBY';
      document.getElementById('risk-status').innerHTML=`Kapitał: <b>${d.risk.capital_usdt}$</b> | Stawka ryzyka: <b>${(d.risk.capital_usdt*d.risk.risk_pct/100).toFixed(2)}$</b> | Obsuwa: <b>-${d.risk.current_drawdown_pct}%</b> (Max: ${d.risk.max_drawdown_pct}%)`;
    }
    let g=''; for(const[k,v] of Object.entries(d.labs||{})){const c=v.net_r>=0?'#34d399':'#f87171';g+=`<div class="stat"><b>${k}</b><br>${v.closed}/${v.total} | WR: <b>${v.wr}%</b><br>Netto: <b style="color:${c}">${v.net_r>=0?'+':''}${v.net_r}R</b></div>`;}
    document.getElementById('labs').innerHTML=g;
    let w=''; for(const[k,v] of Object.entries(d.watchdog||{})){const ok=v.misses===0;w+=`<div class="stat"><b>${ok?'🟢':'🔴'} ${k}</b><br><small>${v.time_str||'-'}</small><br>${v.note||'OK'} (Restarty: ${v.restarts||0})</div>`;} document.getElementById('wd-box').innerHTML=w||'Oczekiwanie na cykl...';
    let s=''; for(const[k,v] of Object.entries(d.sessions||{})){const c=v.net_r>=0?'#34d399':'#f87171';s+=`<div class="stat"><b>${k}</b><br>Próby: ${v.count} | WR: <b>${v.wr}%</b><br>Netto: <b style="color:${c}">${v.net_r>=0?'+':''}${v.net_r}R</b></div>`;} document.getElementById('sess-box').innerHTML=s;
    document.getElementById('news').innerHTML=(d.news||[]).map(x=>`<div style="margin-bottom:4px">${x}</div>`).join('')||'Brak alertów';
  }catch(e){console.error(e);}
}
async function saveRisk(){
  const cap=parseFloat(document.getElementById('risk-cap').value)||200;
  const pct=parseFloat(document.getElementById('risk-pct').value)||1.0;
  const dd=parseFloat(document.getElementById('risk-dd').value)||6.0;
  try{
    const r=await fetch('/api/save_risk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({capital_usdt:cap,risk_pct:pct,max_drawdown_pct:dd})});
    const res=await r.json();
    if(res.ok){ alert('Zapisano ustawienia ryzyka!'); loadState(); }
  }catch(e){alert('Błąd zapisu: '+e);}
}
async function runAudit(){
  const s=document.getElementById('aud-sym').value;
  document.getElementById('aud-out').innerHTML='⏳ Skanuję...';
  try{
    const r=await fetch('/api/web_audit_contract?sym='+encodeURIComponent(s));
    const d=await r.json();
    document.getElementById('aud-out').innerHTML=d.html;
  }catch(e){document.getElementById('aud-out').innerHTML='⚠️ Błąd zapytania: '+e;}
}
async function runCfd(){
  const c=document.getElementById('scan-card');c.style.display='block';
  document.getElementById('scan-t').innerText='⚡ Skaner CFD (TOP-60)';
  document.getElementById('scan-out').innerHTML='⏳ Skanuję...';
  try{
    const r=await fetch('/api/web_scan_cfd');
    const d=await r.json();
    document.getElementById('scan-out').innerHTML=(d.hits||[]).map(h=>`<div class="stat" style="margin-bottom:6px"><b>${h.symbol} (${h.side})</b> | Szansa: <b>${h.win_prob}%</b><br>Wejście: <code>${h.entry}</code> | SL: <code>${h.stop}</code></div>`).join('')||'<div class="stat" style="background:#3f1219;border:2px solid #ef4444;color:#fca5a5;font-weight:bold;text-align:center">⛔ BRAK AKTYWNYCH OKAZJI >= 52% ⛔</div>';
  }catch(e){document.getElementById('scan-out').innerHTML='⚠️ Błąd: '+e;}
}
async function runPd(){
  const c=document.getElementById('scan-card');c.style.display='block';
  document.getElementById('scan-t').innerText='🚀 Skaner Pump & Dump (7 Wzorców)';
  document.getElementById('scan-out').innerHTML='⏳ Skanuję...';
  try{
    const r=await fetch('/api/web_scan_pd');
    const d=await r.json();
    document.getElementById('scan-out').innerHTML=(d.hits||[]).length?'<div class="stat" style="background:#064e3b;border:2px solid #10b981;color:#6ee7b7;font-weight:bold;text-align:center;margin-bottom:8px">✅ ZNALEZIONO AKTYWNE SYGNAŁY! ✅</div>'+(d.hits||[]).map(h=>`<div class="stat" style="margin-bottom:6px"><b>${h.mode} — ${h.symbol} (${h.side})</b> | <b>${h.win_prob}%</b><br><i>${h.pattern_fit}</i><br>${h.narrative}<br>Cena: <code>${h.price}</code> | SL: <code>${h.stop}</code></div>`).join(''):`<div class="stat" style="background:#3f1219;border:2px solid #ef4444;color:#fca5a5;font-weight:bold;text-align:center">⛔ BRAK AKTYWNEJ PARABOLI (Przeskanowano ${d.scanned} par) ⛔</div>`;
  }catch(e){document.getElementById('scan-out').innerHTML='⚠️ Błąd: '+e;}
}
loadState();setInterval(loadState,30000);
</script></body></html>"""

def register_web_ui(app, cp_mod, apm, atm, cam, wpr):
    """Rejestruje trasy interfejsu przegladarkowego Web UI, API ryzyka i skanerow."""
    if "api_web_full_state" in app.view_functions: return

    @app.route("/api/web_full_state")
    def api_web_full_state():
        """Zwraca pelny stan skanera, tunera, laboratoriow i straznika ryzyka."""
        t_st = atm.get_tuner_params()
        _, btc_lbl = cp_mod.get_live_btc_regime()
        news, _ = wpr.fetch_web_pump_intel()
        risk_data = rgm.load_risk_config()
        labs = {}
        for k_l, fn_l in [("TOP60_SHADOW", "market_shadow_lab.json"), ("WILD_61_160", "wild_market_lab.json"), ("MICRO_161_PLUS", "micro_market_lab.json"), ("LIVE_CFD", cp_mod.CFD_HIST_FILE)]:
            arr = json.load(open(fn_l, encoding="utf-8")) if os.path.exists(fn_l) else []
            closed = [x for x in arr if x.get("closed_final")]
            net_r = round(sum(float(x.get("res_r", 0)) - 0.07 for x in closed), 2)
            wr = round(sum(1 for x in closed if float(x.get("res_r", 0)) > 0) / max(1, len(closed)) * 100.0, 1)
            labs[k_l] = {"total": len(arr), "closed": len(closed), "wr": wr, "net_r": net_r}
        wd_data = {}
        return jsonify({
            "tuner": t_st, "btc": btc_lbl, "news": news,
            "labs": labs, "watchdog": wd_data, "risk": risk_data,
            "sessions": sam.compute_session_edge()
        })

    @app.route("/api/save_risk", methods=["POST"])
    def api_save_risk():
        """Zapisuje parametry zarzadzania depozytem i progi Safe-Lock z formularza Web UI."""
        payload = request.get_json(silent=True) or {}
        cap = float(payload.get("capital_usdt", 200.0))
        rpct = float(payload.get("risk_pct", 1.0))
        mdd = float(payload.get("max_drawdown_pct", 6.0))
        ok = rgm.save_risk_config({"capital_usdt": cap, "risk_pct": rpct, "max_drawdown_pct": mdd})
        return jsonify({"ok": ok, "config": rgm.load_risk_config()})

    @app.route("/api/web_audit_contract")
    def api_web_audit_contract():
        """Zwraca audyt bezpieczenstwa smart-kontraktu w formacie HTML."""
        return jsonify({"html": cam.audit_token_contract(request.args.get("sym", "RAVE"))})

    @app.route("/api/web_scan_cfd")
    def api_web_scan_cfd():
        """Uruchamia szybki skan par TOP-60 CFD z poziomu przegladarki."""
        syms, rules, hits = apm.get_cfd_top60_symbols(), cp_mod.load_settings().get("rules", {}), []
        with ThreadPoolExecutor(max_workers=12) as p:
            for h in p.map(lambda sm: cp_mod._scan_one_coin(("BITGET", sm, 1.0, rules, ["15m", "1h", "4h", "1d"], 1000.0, 1.5)), syms):
                if h and isinstance(h, dict) and h.get("win_prob", 0) >= 52: hits.append(h)
        hits.sort(key=lambda x: -x.get("win_prob", 0))
        return jsonify({"hits": hits})

    @app.route("/api/web_scan_pd")
    def api_web_scan_pd():
        """Uruchamia skaner 7 wzorcow Pump & Dump z poziomu przegladarki."""
        syms, hits = apm.get_all_futures_symbols(), []
        with ThreadPoolExecutor(max_workers=20) as p:
            for r in p.map(apm.scan_macro_pump_dump_coin, syms):
                if r: hits.append(r)
        hits.sort(key=lambda x: -x.get("win_prob", 0))
        return jsonify({"scanned": len(syms), "hits": hits})

    app.view_functions["index"] = lambda: HTML_UI
