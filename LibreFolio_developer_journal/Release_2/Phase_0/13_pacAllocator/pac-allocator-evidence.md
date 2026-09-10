# Evidenze checkpoint PAC P1

## 1. Provenienza

- Baseline letta e implementata: `4a73f5f63447e01b51993afb2e3c73e2c22a9a28`.
- Commit runtime disponibile ma non incorporato:
  `916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`.
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
| Service/evaluator | non eseguito |
| Legacy-heavy imports | non eseguito |
| C codegen/roundtrip | non eseguito |
| Runtime combinato | non eseguito |

Il selector schema e stato eseguito dal coordinatore prima del commit runtime.

## 5. Controlli checkpoint

- `git diff --check`: pulito sui file tracked.
- Residui cercati: `__pycache__`, `*.pyc`, `.pytest_cache`, `.coverage*`.
- Residui trovati nelle directory P1: nessuno.
- `backend/data/test/sqlite/app.db`: assente.
- Overlap path D contro `4a73f5f6..916f12bd`: nessuno.
- Blob dei cinque file tracked D: identici tra baseline e runtime.
- Directory `13_pacAllocator` assente nel runtime: nessun conflitto di path.

Questo prova applicabilita testuale probabile, non compatibilita semantica finale.

## 6. Rischi da ricontrollare sulla revisione combinata

1. Runner `916f12bd`: isolamento, data-dir e lifecycle cambiati.
2. I selector P1 devono usare solo `/tmp/librefolio-r2-d`.
3. Import lazy devono preservare tutti gli export dopo le modifiche E.
4. TypeAdapter P1 deve attraversare il codegen C reale senza perdere:
   - union discriminate;
   - max 80/384 issue;
   - `normalized` ready/non-ready;
   - code point Unicode;
   - stringhe Decimal esatte.
5. Wrapper C deve chiamare `context.checkpoint()` e lasciare tempi/errori platform
   fuori dal risultato PAC.

## 7. Ripresa verificabile

Dopo commit e integrazione manuali:

```text
./dev.py test --test-port 6143 --data-dir /tmp/librefolio-r2-d schemas pac-analyze
./dev.py test --test-port 6143 --data-dir /tmp/librefolio-r2-d services pac-analyze
```

Attesi:

- nessun `--force`;
- porta 6143 non condivisa;
- nessuna scrittura fuori dal data-dir dedicato;
- nessun uso di 6041;
- errore esplicito se dipendenze mancanti;
- nessuna installazione automatica.

## 8. Esclusioni dal checkpoint

Restano solo nella sessione:

- log `source-*.log`;
- patch di handoff `p1-import-boundary.patch`;
- database sessione Copilot;
- artifact intermedi duplicati.

Non sono sorgenti del prodotto e non vanno copiati nel repository.
