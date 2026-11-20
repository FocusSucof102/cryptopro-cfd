import py_compile, glob
for f in glob.glob("*.py"):
    py_compile.compile(f, doraise=True)
import alpha_pro_mod as apm, auto_tuner_mod as atm
syms = apm.get_cfd_top60_symbols()
assert len(syms) >= 20
print(f"TEST OK! {len(syms)} par CFD | Prog tunera: {atm.get_tuner_params()['min_prob']}%")
