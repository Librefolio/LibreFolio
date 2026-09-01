DRAFT — modifiche a scripts/test_runner/ per la coverage JS
===========================================================

1) _common.py — nessuna modifica alle firme.
   `_COVERAGE_MODE` diventa una stringa ('py' | 'js' | 'all') invece di bool.
   Resta veritiera/falsa per tutto il codice esistente (stringa non vuota = True),
   quindi i ~77 `coverage: bool = False` continuano a funzionare invariati.

   Aggiungere solo un helper:

   def coverage_wants(kind: str) -> bool:
       """kind: 'py' | 'js'. True se la modalità corrente include quel linguaggio."""
       m = _COVERAGE_MODE
       if not m:
           return False
       if m is True:          # retrocompatibilità con chiamate booleane interne
           return kind == 'py'
       return m == 'all' or m == kind


2) _cli.py — dove oggi si fa `_common._COVERAGE_MODE = coverage` (righe 538 e 626):

   _common._COVERAGE_MODE = coverage           # ora stringa
   if _common.coverage_wants('js'):
       os.environ['COVERAGE_JS'] = '1'          # ereditata da TUTTI i sottoprocessi

   Argparse:
       parser.add_argument("--coverage", nargs="?", const="all", default=None,
                           choices=["py", "js", "all"],
                           help="Coverage: py|js|all (default: all)")

   Validazione: `--coverage js` su una suite solo-backend deve dare errore chiaro,
   non un report vuoto.


3) _frontend_common.py — _run_playwright, sostituire il blocco env:

   env = os.environ.copy()
   if _common.coverage_wants('py'):
       env['COVERAGE_BACKEND'] = '1'
   if _common.coverage_wants('js'):
       env['COVERAGE_JS'] = '1'


4) _coverage.py — nuova funzione, chiamata da _cli.py accanto a _finalize_coverage:

   def _finalize_js_coverage() -> str | None:
       """Merge dei raw JS (unit + e2e) in un report unico."""
       fe = PROJECT_ROOT / "frontend"
       unit_raw = fe / "coverage-js/unit/raw"
       e2e_raw  = fe / "coverage-js/e2e/raw"
       inputs = [str(p.relative_to(fe)) for p in (unit_raw, e2e_raw) if p.exists()]
       if not inputs:
           print_warning("Nessun dato di coverage JS trovato.")
           return None
       subprocess.run(
           ["npx", "mcr", "merge",
            "--inputDir", ",".join(inputs),
            "--outputDir", "coverage-js/combined",
            "--reports", "v8,console-summary,json"],   # json = istanbul, per la Fase D
           cwd=fe, text=True
       )
       return "frontend/coverage-js/combined"


5) _coverage.py — rinomina htmlcov-frontend → htmlcov-backend-e2e
   Punti da toccare:
     _coverage.py:26   html_dir = ... ternario
     _coverage.py:83   coverage html -d htmlcov-frontend
     _coverage.py:91   messaggio
     _coverage.py:176  dir_map["frontend"]
     _common.py:292    html_dir ternario in run_command
     .gitignore
     documentazione + skill
