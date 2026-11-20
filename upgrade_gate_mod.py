import os, ast, shutil, py_compile, importlib.util
from datetime import datetime

FORBIDDEN_CALLS = ("eval", "exec", "os.system", "subprocess.Popen", "__import__")

def verify_and_upgrade_module(target_py, candidate_py, benchmark_fn=None):
    """4-etapowa bramka aktualizacji: 1) Audyt zrodla/SecOps, 2) Kompilacja AST, 3) Test efektywnosci A/B, 4) Podmiana z kopia .bak."""
    if not os.path.exists(candidate_py):
        return False, "Brak pliku kandydata"
    raw = open(candidate_py, encoding="utf-8").read()
    for bad in FORBIDDEN_CALLS:
        if bad in raw:
            os.remove(candidate_py)
            return False, f"Odrzucono (SecOps): wykryto niedozwolone wywolanie '{bad}'"
    try:
        py_compile.compile(candidate_py, doraise=True)
        tree = ast.parse(raw)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and ast.get_docstring(node) is None:
                os.remove(candidate_py)
                return False, f"Odrzucono (Docstring-Guard): brak opisu funkcji '{node.name}'"
    except Exception as exc:
        os.remove(candidate_py)
        return False, f"Odrzucono (Blad skladni/AST): {exc}"

    if callable(benchmark_fn):
        try:
            spec = importlib.util.spec_from_file_location("_cand_mod", candidate_py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            ok_eff, eff_msg = benchmark_fn(mod)
            if not ok_eff:
                os.remove(candidate_py)
                return False, f"Odrzucono (Test efektywnosci A/B): {eff_msg}"
        except Exception as exc:
            os.remove(candidate_py)
            return False, f"Odrzucono (Blad w piaskownicy): {exc}"

    if os.path.exists(target_py):
        shutil.copy2(target_py, f"{target_py}.{datetime.now().strftime('%Y%m%d_%H%M')}.bak")
    shutil.move(candidate_py, target_py)
    return True, f"Zatwierdzono i zaktualizowano {target_py} (Kopia .bak zachowana)"
