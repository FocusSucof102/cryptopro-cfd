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
import py_compile, glob
for f in glob.glob("*.py"):
    py_compile.compile(f, doraise=True)
import alpha_pro_mod as apm, auto_tuner_mod as atm
syms = apm.get_cfd_top60_symbols()
assert len(syms) >= 20
print(f"TEST OK! {len(syms)} par CFD | Prog tunera: {atm.get_tuner_params()['min_prob']}%")
