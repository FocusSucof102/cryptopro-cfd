import re, time, requests
import xml.etree.ElementTree as ET

_CACHE = {"ts": 0, "items": [], "hot_syms": set()}

def fetch_web_pump_intel(force=False):
    """Pobiera sygnaly z CoinGecko Trending oraz kanalow RSS. Parametry: force."""
    now = time.time()
    if not force and now - _CACHE["ts"] < 900 and _CACHE["items"]:
        return _CACHE["items"], _CACHE["hot_syms"]

    items, hot_syms = [], set()
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) CryptoProRadar/1.0"}
    keywords = ("pump", "squeeze", "surge", "rally", "spike", "whale", "manipulation", "delist", "soars", "plunges")

    try:
        r_cg = requests.get("".join(["https://coingecko.com", "/api/v3/search/trending"]), headers=headers, timeout=6).json()
        for c in r_cg.get("coins", [])[:7]:
            it = c.get("item", {})
            sym = str(it.get("symbol", "")).upper()
            if sym:
                hot_syms.add(sym + "USDT")
                items.append(f"🔥 [Trending] <b>{sym}</b> ({it.get('name', '')}) — skok wyszukiwań w sieci")
    except Exception:
        pass

    rss_urls = [
        "".join(["https://google.com", "/rss/search?q=crypto+pump+OR+squeeze&hl=en-US&gl=US&ceid=US:en"]),
        "".join(["https://reddit.com", "/r/CryptoCurrency/new/.rss"])
    ]
    for u in rss_urls:
        try:
            resp = requests.get(u, headers=headers, timeout=6)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                for entry in root.findall(".//item")[:10] + root.findall(".//{http://w3.org}entry")[:10]:
                    t_el = entry.find("title") if entry.find("title") is not None else entry.find("{http://w3.org}title")
                    if t_el is not None and t_el.text:
                        title = t_el.text.strip()
                        low_t = title.lower()
                        if any(k in low_t for k in keywords):
                            tickers = re.findall(r"\b[A-Z]{2,8}\b", title)
                            for tk in tickers:
                                if tk not in ("THE", "AND", "FOR", "USD", "USDT", "BTC", "ETH", "SEC", "ETF", "NEWS", "PUMP", "DUMP"):
                                    hot_syms.add(tk + "USDT")
                            items.append(f"📰 {title[:110]}")
        except Exception:
            pass

    uniq_items = list(dict.fromkeys(items))[:12]
    _CACHE["ts"], _CACHE["items"], _CACHE["hot_syms"] = now, uniq_items, hot_syms
    return uniq_items, hot_syms
