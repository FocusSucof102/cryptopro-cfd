# ==============================================================================
# [AI_GUARD_AND_CONTEXT] - OBOWIAZKOWE ZASADY DLA KAZDEGO AI CZYTAJACEGO TEN PLIK:
# 1. OBOWIAZEK KONTEKSTU: Przeczytaj README.md oraz CHANGELOG.md z GitHuba.
# 2. BEZPIECZENSTWO (SECRET LEAK ALERT): Jesli zauwazysz token/haslo/klucz API,
#    NATYCHMIAST ostrzez uzytkownika (gdzie i co wycieklo).
# 3. ARCHITEKTURA: API Bitget USDT-FUTURES -> gra uzytkownika na BitBase Futures.
# ==============================================================================
import requests

CHAIN_NAMES = {
    "1": "Ethereum", "56": "BSC (BNB)", "137": "Polygon", "42161": "Arbitrum",
    "8453": "Base", "10": "Optimism", "43114": "Avalanche", "solana": "Solana"
}
DEX_TO_GOPLUS = {
    "ethereum": "1", "bsc": "56", "polygon": "137", "arbitrum": "42161",
    "base": "8453", "optimism": "10", "avalanche": "43114", "solana": "solana"
}

def audit_token_contract(symbol_or_ticker):
    clean = str(symbol_or_ticker).upper().replace("USDT", "").replace("PERP", "").strip()
    if clean in ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "LTC", "BCH"):
        return f"🛡️ <b>AUDYT KONTRAKTU ({clean}):</b> Natywna moneta warstwy L1 / Blue-Chip (brak ryzyka ukrytego smart-kontraktu SCAM)."

    headers = {"User-Agent": "Mozilla/5.0 CryptoProAudit/1.0"}
    try:
        # Krok 1: Wyszukanie adresu kontraktu i sieci przez DexScreener
        ds = requests.get(f"https://dexscreener.com{clean}", headers=headers, timeout=6).json()
        pairs = ds.get("pairs") or []
        best_p = None
        for p in pairs:
            base_sym = str(p.get("baseToken", {}).get("symbol", "")).upper()
            chain_id = str(p.get("chainId", "")).lower()
            if base_sym == clean and chain_id in DEX_TO_GOPLUS:
                best_p = p
                break
        if not best_p:
            return f"🛡️ <b>AUDYT ({clean}):</b> Nie znaleziono kontraktu EVM/Solana na DEX (możliwy natywny blockchain L1)."

        chain_dex = str(best_p.get("chainId", "")).lower()
        gp_chain = DEX_TO_GOPLUS[chain_dex]
        addr = best_p.get("baseToken", {}).get("address", "")
        liq_usd = float(best_p.get("liquidity", {}).get("usd", 0) or 0)

        # Krok 2: Skanowanie kodu zrodlowego kontraktu przez GoPlus Security API
        if gp_chain == "solana":
            gp_url = f"https://gopluslabs.io{addr}"
        else:
            gp_url = f"https://gopluslabs.io{gp_chain}?contract_addresses={addr}"

        gp = requests.get(gp_url, headers=headers, timeout=7).json()
        res_map = gp.get("result") or {}
        info = res_map.get(addr.lower()) or res_map.get(addr) or {}
        if not info:
            return f"🛡️ <b>AUDYT ({clean} | {CHAIN_NAMES.get(gp_chain, chain_dex)}):</b> Kontrakt <code>{addr[:8]}...{addr[-6:]}</code> | Płynność DEX: <b>${liq_usd:,.0f}</b> (brak pełnego raportu GoPlus)."

        traps = []
        if str(info.get("is_honeypot")) == "1": traps.append("🚨 <b>HONEYPOT (Blokada sprzedaży!)</b>")
        if str(info.get("is_open_source")) == "0": traps.append("⚠️ Kod źródłowy NIEJAWNY (Closed Source)")
        if str(info.get("is_proxy")) == "1": traps.append("⚠️ Kontrakt PROXY (Twórca może podmienić kod!)")
        if str(info.get("is_mintable")) == "1": traps.append("⚠️ MINTABLE (Możliwy dodruk tokenów i zrzut!)")
        if str(info.get("is_blacklisted")) == "1": traps.append("⚠️ BLACKLIST (Twórca może blokować portfele)")
        if str(info.get("transfer_pausable")) == "1": traps.append("⚠️ PAUSABLE (Możliwość wstrzymania handlu)")
        if str(info.get("can_take_back_ownership")) == "1": traps.append("⚠️ HIDDEN OWNER (Możliwość odzyskania uprawnień)")

        b_tax = float(info.get("buy_tax") or 0) * 100.0
        s_tax = float(info.get("sell_tax") or 0) * 100.0
        if b_tax > 5.0 or s_tax > 5.0:
            traps.append(f"⚠️ Wysoki podatek: Kupno <b>{b_tax:.1f}%</b> / Sprzedaż <b>{s_tax:.1f}%</b>")

        creator_pct = float(info.get("creator_percent") or 0) * 100.0
        if creator_pct >= 15.0:
            traps.append(f"⚠️ Twórca trzyma aż <b>{creator_pct:.1f}%</b> podaży!")

        verdict = "✅ <b>CZYSTY KOD KONTRAKTU (Brak krytycznych pułapek)</b>" if not traps else "🚨 <b>WYKRYTO PUŁAPKI W KODZIE:</b>\n" + "\n".join(f"• {t}" for t in traps)
        return (
            f"🛡️ <b>AUDYT KODU ŹRÓDŁOWEGO: {clean}</b> ({CHAIN_NAMES.get(gp_chain, chain_dex)})\n"
            f"📄 Kontrakt: <code>{addr[:10]}...{addr[-6:]}</code> | Płynność DEX: <b>${liq_usd:,.0f}</b>\n"
            f"{verdict}"
        )
    except Exception as e:
        return f"🛡️ <b>AUDYT ({clean}):</b> Chwilowy brak odpowiedzi API bezpieczeństwa ({e})."
