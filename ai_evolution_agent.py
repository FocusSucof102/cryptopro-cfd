import os, json, time, shutil, urllib.request, walk_forward_mod as wf
API_KEY = os.environ.get("GEMINI_API_KEY", "")

def send_tg(txt):
    env = dict(l.strip().split("=", 1) for l in open(".env") if "=" in l) if os.path.exists(".env") else {}
    tk, cid = env.get("TELEGRAM_TOKEN", ""), env.get("TELEGRAM_CHAT_ID", "")
    if not (tk and cid): return
    u = f"https://telegram.org{tk}/sendMessage"
    b = json.dumps({"chat_id": cid, "text": txt, "parse_mode": "Markdown"}).encode("utf-8")
    for _ in range(3):
        try: urllib.request.urlopen(urllib.request.Request(u, data=b, headers={"Content-Type": "application/json"}), timeout=15); return
        except Exception: time.sleep(2)
