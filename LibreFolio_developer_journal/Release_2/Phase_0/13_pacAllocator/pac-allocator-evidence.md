# Evidenze checkpoint PAC P1

## 1. Provenienza

- Baseline letta e implementata: `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`.
- Checkpoint D creato dal dev:
  `cf1dd37974b2191877093e641cf00f261a241d20`.
- Commit runtime incorporato manualmente:
  `916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`.
- HEAD combinato:
  `d018e8a677289b9bc38e65b437a86e1f2684caa7`.
- Merge-base: `4a73f5f6`.
- Commit intermedi runtime: `ef722b55`, `916f12bd`.
- Worktree D isolato: `e-alfy-friendly-dollop`.
- Nessun accesso a portfolio/export personali.
- Nessuna dipendenza o solver installato.

Fonti obbligatorie lette integralmente alla baseline:

- `README.md`;
- `Release_2/Phase_0/09_feedbackJobs/README.md`;
- `05_pac_allocation_tool.md`;
- `06_piano_sprint.md`;
- `Release_2/guida_allocazione_pac_multi_etf.md` (1.167 righe).

## 2. Evidenze sorgente principali

| Fonte baseline | Conseguenza |
|---|---|
| `05_pac_allocation_tool.md:20-149` | piattaforma C separata; plugin puro; niente `/tools/prefill` |
| `06_piano_sprint.md:495-617` | contratto/evaluator prima del solver; core non dipende da HTTP |
| `06_piano_sprint.md:626-769` | writer unici, runtime condiviso, review dev non sostituita da test |
| `guida_allocazione_pac_multi_etf.md:228-411` | esempi 3484.14/3493.24 non sono golden del nuovo obiettivo |
| `guida_allocazione_pac_multi_etf.md:508-820,1101-1167` | buffer/costi separati da investimento; pesi/budget storici non sono default |
| `portfolio_service.py:1003-1014` | cash nativo puo sparire con FX mancante: P1 lo preserva |
| `portfolio_service.py:1040-1046` | percentuali display arrotondate non sono target canonici |
| `schemas/portfolio.py:257-290` | prezzo report convertito distinto da quote nativa/Q |
| `api/v1/assets.py:762-807` | current price puo scrivere OHLC: nessun auto-prefill |
| `schemas/brokers.py:352-374` | ruolo e quota economica non sono la stessa cosa |

Il codice e le decisioni dev prevalgono sugli appunti precedenti.

## 3. Delta D esatto prima degli artifact

### Modificati

1. `backend/app/schemas/__init__.py`
2. `backend/app/services/__init__.py`
3. `backend/app/utils/financial/__init__.py`
4. `scripts/test_runner/_backend_schemas.py`
5. `scripts/test_runner/_backend_services.py`

### Nuovi

1. `backend/app/schemas/pac_allocator.py`
2. `backend/app/services/pac_allocator/__init__.py`
3. `backend/app/services/pac_allocator/evaluator.py`
4. `backend/app/services/pac_allocator/models.py`
5. `backend/app/services/pac_allocator/normalize.py`
6. `backend/app/services/pac_allocator/numeric.py`
7. `backend/app/services/pac_allocator/report.py`
8. `backend/test_scripts/test_schemas/test_pac_analyze_schemas.py`
9. `backend/test_scripts/test_services/test_pac_analyze.py`

Nessun file C platform, API, DB, frontend, docs utente, i18n o CHANGELOG modificato.

## 4. Stato prove

| Prova | Evidenza |
|---|---|
| Selector | `schemas pac-analyze` |
| Risultato | 816 passed |
| Durata | 2.48 s |
| DB worktree | assente prima/dopo |
| Fingerprint schema | invariato |
| Service/evaluator sulla baseline | non eseguito |
| Legacy-heavy imports sulla baseline | non eseguito |
| C codegen/roundtrip | non eseguito |
| Runtime combinato finale, schema | 816 passed, 2.47 s |
| Runtime combinato finale, service | 194 passed, 2.93 s |
| Legacy-heavy initializer | 3 casi passati nel service selector |
| Ruff mirato | verde sui 14 file Python P1 |
| Black check mirato | verde sui 14 file Python P1 |

Tentativo combinato successivo:

```text
./dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas pac-analyze
```

Il comando e terminato prima di pytest durante l'import del runner con
`ModuleNotFoundError: No module named 'pydantic'`. Non sono stati creati
`/tmp/librefolio-r2-d` o il DB del worktree; nessuna installazione o seconda suite.

Il retry richiesto con `pipenv run python dev.py ...` ha creato automaticamente il venv
D vuoto `/Users/ea_enel/.local/share/virtualenvs/e-alfy-friendly-dollop-bwI0S8St`
e si e fermato prima di pytest con `ModuleNotFoundError: No module named 'argcomplete'`.
Nessun pacchetto progetto installato, nessun data-dir/DB e nessun test service. Il venv
resta intatto finche il coordinatore non autorizza ambiente o cleanup.

Risoluzione senza install: selezionato il venv locked esistente
`/Users/ea_enel/.local/share/virtualenvs/LibreFolio-SAUMUTtc` tramite
`PIPENV_CUSTOM_VENV_NAME`. Entrambi i selector sono poi passati serialmente nella lane
6153. Il service runner ha creato il DB solo in
`/tmp/librefolio-r2-d/sqlite/app.db`; il DB del worktree resta assente.

Ruff ha trovato due import block non formattati e tre problemi test-only:
`zip()` senza `strict`, closure su variabili di loop e encoding UTF-8 ridondante.
Test-author ha corretto i test; ruff/Black hanno formattato i file P1. Il confronto AST
contro HEAD mostra cambi semantici solo nei due test, non nei file production formattati.

## 5. Controlli checkpoint

- `git diff --check`: pulito sui file tracked.
- Residui cercati: `__pycache__`, `*.pyc`, `.pytest_cache`, `.coverage*`.
- Residui trovati nelle directory P1: nessuno.
- `backend/data/test/sqlite/app.db`: assente.
- Overlap path D contro `4a73f5f6..916f12bd`: nessuno.
- Blob dei cinque file tracked D: identici tra baseline e runtime.
- Directory `13_pacAllocator` assente nel runtime: nessun conflitto di path.

Questo prova applicabilita testuale probabile, non compatibilita semantica finale.

## 6. Rischi residui

1. TypeAdapter P1 deve attraversare il codegen C reale senza perdere:
   - union discriminate;
   - max 80/384 issue;
   - `normalized` ready/non-ready;
   - code point Unicode;
   - stringhe Decimal esatte.
2. Wrapper C deve chiamare `context.checkpoint()` e lasciare tempi/errori platform
   fuori dal risultato PAC.
3. Il venv vuoto D e un residuo ambientale noto da rimuovere solo con autorizzazione.

## 7. Comandi verificati

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas pac-analyze
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d services pac-analyze
```

Attesi:

- nessun `--force`;
- porta 6153 non condivisa;
- nessuna scrittura fuori dal data-dir dedicato;
- nessun uso di 6041;
- nessuna installazione automatica.

## 8. Esclusioni dal checkpoint

Restano solo nella sessione:

- log `source-*.log`;
- patch di handoff `p1-import-boundary.patch`;
- database sessione Copilot;
- artifact intermedi duplicati.

Non sono sorgenti del prodotto e non vanno copiati nel repository.
