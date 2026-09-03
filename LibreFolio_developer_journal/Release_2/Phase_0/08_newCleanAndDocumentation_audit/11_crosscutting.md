# 11 — Trasversali — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/11_crosscutting.md)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso).
> Branch `dev_release2`, working tree con modifiche non committate del 02/09 considerate realtà.

---

## Sintesi esecutiva

Gli interventi "da un'ora" del vecchio report sono stati **tutti eseguiti** nel ciclo
S1–S3 (2026-08-05) e sono **tenuti**: licenza AGPL-3.0 in `pyproject.toml`, task di
pre-warm trattenuto, `open()` bloccante avvolta in `to_thread`, gli 11 `S110` loggati,
i 77 autofix applicati e mai regrediti (`PIE790` e `RUF010` restano a 0). La
strumentazione introdotta (vulture, knip, `./dev.py lint --dead-code`) è presente e
funzionante. Il debito strutturale invece è **cresciuto**: `C901` 138 → 157 (con
`execute_batch` da 112 a 115), `$:` legacy 101 → 109 (`BrokerSharingPanel` da 20 a 24),
`TRY400` 53 → 55, e i 38 candidati N+1 nominati sono tutti ancora al loro posto. Due
sorprese: una **regressione S110** in `utils/cache_utils.py:82` introdotta il 2026-08-13,
otto giorni dopo la bonifica che li aveva portati a zero; e la scoperta che la tabella K5
citava `wac_service.py`, file **rimosso il 2026-06-10** — già fantasma al momento
dell'audit.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza (file:riga attuale) | Azione |
|---|---|---|---|---|
| K1 🔴 licenza MIT su progetto AGPL | aperto | **FATTO** (S1–S3) | `pyproject.toml:7` `version = "1.1.0"`, `:10` `requires-python = ">=3.13"`, `:15` `Development Status :: 4 - Beta`, `:17` `License :: OSI Approved :: GNU Affero General Public License v3`; `frontend/package.json:4` `"version": "1.1.0"` | nessuna |
| K2 🟡 unica violazione Async I/O | aperto | **FATTO** (S1–S3) | `backend/app/api/v1/uploads.py:377-384` — `_read_text_preview()` in `await asyncio.to_thread(...)` | nessuna |
| K3 🟡 38 candidati N+1 | aperto | **ANCORA VALIDO** — siti nominati tutti presenti | `portfolio_api.py:49`; `fx.py:965,1014`; `services/fx.py:647,750,1609`; `settings_service.py:212`; `brim_provider.py:1550`; `asset_source.py` ancora il concentrato | verifica uno per uno, mai fatta |
| K4 🟡 11 `try/except/pass` | aperto | **FATTO all'epoca, 1 REGRESSIONE** | `ruff check app/ --select S110` → 1: `app/utils/cache_utils.py:82`, introdotto da `c8cd0fb2` (2026-08-13). Vecchi siti bonificati verificati: `provider_registry.py:461`, `yahoo_finance.py:358,630`, `version.py:41,56`, `system.py:91`, `uploads.py:83` | loggare il nuovo sito |
| K4 correlato: 53 TRY400 | aperto | **ANCORA VALIDO** — 55 oggi | `ruff check app/ --select TRY400` → 55; di cui 28 in `api/v1/` | conversione meccanica |
| K5 🟡 138 funzioni oltre soglia | aperto | **ANCORA VALIDO e peggiorato** — 157 oggi | `ruff check app/ --extend-select C901 --statistics` → 157; top: `execute_batch` **115** (`transaction_service.py:937`, era 112), `build` 97 (`portfolio_engine.py:562`), `get_summary` 73 (`portfolio_service.py:943`) | fissare `max-complexity` + lavorare la top-20 |
| K5 nota: `max-complexity = 25` raccomandato | voce nulla (report 14, 1.2) | **confermato nullo** | nessuna `[tool.ruff.lint.mccabe]` in `pyproject.toml:60-90`; con soglia 25 oggi: 19 funzioni (comando sotto) | opzionale: aggiungere la config |
| K6 🟡 `create_task` non trattenuto | aperto | **FATTO** (S1–S3) | `backend/app/main.py:74` `_background_tasks: set[asyncio.Task]`; `:263-265` add + `add_done_callback(_background_tasks.discard)` | nessuna |
| K7 🟢 101 statement `$:` legacy | aperto | **ANCORA VALIDO e cresciuto** — 109 oggi | `grep -rn '\$:' frontend/src --include="*.svelte" \| wc -l` → 109; `BrokerSharingPanel.svelte` 20 → **24**; `charts/` ancora 0 | migrazione dedicata di BrokerSharingPanel |
| K8 🟢 77 autofix applicati, 111 RUF100 lasciati | fatto / decisione | **FATTO e mantenuto; RUF100 crollato** | `PIE790` 0, `RUF010` 0; `RUF100` → 9 (`--extend-select RUF100`); noqa totali in `backend/app` = 58 (`grep -rn "noqa" ... \| wc -l`), di cui `ARG001` 0, `E402` 1 | nessuna |
| Reperto declassato: `if not __debug__: raise` in main.py | declassato 🔵 | **SUPERATO** | mai esistito nel codice — era il rimedio M2-A proposto dal report 13; `grep -rn "__debug__" backend/ scripts/` → 0 hit; declassamento documentato in INDEX | nessuna (decisione presa) |
| Strumentazione: vulture / knip / `--dead-code` | introdotta | **presente e funzionante** | vulture 2.16 (`Pipfile:70`, `[tool.vulture]` `pyproject.toml:99+`); knip 6.31.0 (`frontend/package.json:46`, script `lint:dead` `:16`, `frontend/knip.json`); `dev.py:1648-1649` dispatch, `cmd_dead_code` `:1693`; skill `.github/skills/devpy-tools/*` aggiornate | nessuna |
| Metrica: 702 rilievi ruff estesi | — | **non riproducibile alla virgola** (vedi sotto) | con l'elenco esatto delle 16 regole del report: 594 oggi | — |
| Metrica: TODO/FIXME/HACK backend = 8 | — | **decaduta** — 4 reali oggi | `grep -rn "TODO\|FIXME\|HACK" backend/app --include="*.py"` → 5 hit, di cui 1 falso positivo (`TODOS` in spagnolo, `snb.py:129`) | — |
| Metrica: violazioni Async I/O = 1 su 104 siti | — | **0 sul sito originale; 1 nuovo rilievo** | Pillow bloccante in `uploads.py:423,435,440` — vedi report [01](01_api_layer.md) N1 | avvolgere in `to_thread` |
| Metrica: baseline `./dev.py lint` = 36 | — | **ancora valida** — 37 oggi | `ruff check backend/ --statistics` → 36 PLC0415 + 1 B905, quasi tutti in `test_scripts/`; unico in `app/`: `settings.py:168` | opzionale |

---

## Dettaglio reperti ancora aperti / regrediti

### K3 — 38 candidati N+1: mai verificati uno per uno

Il backlog (voce 4.4) non è mai stato eseguito. Riproduzione con euristica AST propria
(await contenente `session` dentro loop `for`, deduplicata):

```bash
cd backend && python3 -c "
import ast
def scan(path):
    hits=set()
    class V(ast.NodeVisitor):
        def _loop(self,node):
            for ch in ast.walk(node):
                if isinstance(ch,ast.Await) and 'session' in ast.dump(ch.value): hits.add(ch.lineno)
            self.generic_visit(node)
        visit_For=_loop; visit_AsyncFor=_loop
    V().visit(ast.parse(open(path).read()))
    return sorted(hits)
for f in ['app/services/asset_source.py','app/api/v1/fx.py','app/services/fx.py','app/services/settings_service.py','app/services/brim_provider.py','app/api/v1/portfolio_api.py']:
    print(f, scan(f))"
```

Risultato: `asset_source.py` 40 siti, `api/v1/fx.py` 9, `services/fx.py` 3,
`settings_service.py` 1, `brim_provider.py` 1, `portfolio_api.py` 2 → **56** contro i 38
dell'audit. Le euristiche differiscono (il vecchio report filtrava i cicli su insiemi
fissi), quindi i totali non sono confrontabili alla virgola; ciò che conta è che **tutti
i candidati nominati sono ancora presenti**, incluso il miglior rapporto valore/costo
dell'audit (bulk in `asset_source.py`, oggi la zona di `:4091-4116` con
`session.execute`/`session.delete`/`session.flush` per elemento nel loop delete bulk).

### K4 — S110: bonifica tenuta, ma una regressione nuova di zecca

Dopo S1–S3 il conteggio era 0. Oggi:

```bash
cd backend && pipenv run ruff check app/ --select S110
# → 1 error: app/utils/cache_utils.py:82 — except Exception: pass
#   (commento: "a cache that cannot be closed must not break a clear")
```

`git log -S` lo data a `c8cd0fb2` (2026-08-13, "perf(test-runner): batch playwright
groups under JS coverage") — **otto giorni dopo** la bonifica. Il caso è del tipo
"degrado atteso" (come `version.py`), quindi il rimedio è il solito `logger.debug(...,
exc_info=True)`: una riga. Ma è un segnale di processo: la regola "mai except/pass" non è
ancora automatizzata (S110 non è nella config ruff di progetto, `pyproject.toml:71-90`) —
se lo fosse, questa regressione non sarebbe entrata.

### K5 — C901: 138 → 157, e il podio peggiora

```bash
cd backend && pipenv run ruff check app/ --extend-select C901 --output-format=json | python3 -c "..."
# → 157 totali; >20: 47; >25: 19
```

| Complessità | Funzione | File:riga oggi | Audit |
|---:|---|---|---:|
| **115** | `execute_batch` | `services/transaction_service.py:937` | 112 |
| **97** | `build` | `services/portfolio_engine.py:562` | 97 |
| 73 | `get_summary` | `services/portfolio_service.py:943` | 73 |
| 71 | `_parse_account_movements` | `brim_providers/broker_credit_agricole.py:929` | *(nuovo in top-10)* |
| 62 | `get_positions_contribution` | `services/portfolio_service.py:1707` | 62 |
| 62 | `bulk_refresh_prices` | `services/asset_source.py:2697` | 59 |
| 54 | `sync_pairs_bulk` | `services/fx.py:768` | 54 |
| 47 | `get_prices_bulk` | `services/asset_source.py:2161` | 46 |

**Correzione alla fonte**: la tabella K5 citava `compute_wac_iterative*` in
`wac_service.py`, ma quel file è stato rimosso il 2026-06-10 (`79ea14e5`, *"replaces
wac_service.py"*) — già assente all'epoca dell'audit. Le funzioni vivono in
`portfolio_service.py` (`compute_wac_iterative` a `:95`, `..._multi_broker` a `:347`,
entrambe 32 oggi). Il vecchio report andava letto con questo scarto.

La raccomandazione `max-complexity = 25` resta applicabile e la voce 1.2 del report 14
("non esiste alcuna configurazione da alzare") è confermata: la sezione
`[tool.ruff.lint]` (`pyproject.toml:71-90`) non ha né `mccabe` né `C901` in `select`.
Con soglia 25 la lista di lavoro oggi sarebbe di **19 funzioni** — l'audit stimava "una
ventina": la stima regge.

### K7 — `$:` legacy: 101 → 109

```bash
grep -rn '\$:' frontend/src --include="*.svelte" | wc -l   # → 109
```

Per area (stesso comando per directory): `components/ui` 26 (=), `components/brokers` 30
(era 26), `components/settings` 28 (era 25), `routes` 22 (era 21), `components/layout` 3
(=), `charts/` **0** (=). La migrazione dedicata di `BrokerSharingPanel.svelte` (voce
6.10 del backlog) **non è mai stata fatta**: il file è passato da 20 a 24 statement —
nuovo codice scritto in modalità legacy dentro il file che il report indicava come il
candidato numero uno alla migrazione. File densi oggi: `BrokerSharingPanel` 24,
`ImageEditModal` 10, `PreferencesTab` 9, `GlobalSettingsTab` 9.

### K8 — Autofix tenuti; i 111 RUF100 sono spariti per altra via

`PIE790` 0 e `RUF010` 0: i 77 autofix non sono mai regrediti. I 111 `RUF100`
"deliberatamente lasciati" (decisione documentata nel report 15) oggi sono **9**: i `noqa`
`ARG001` (52) ed `E402` (45) sono spariti come effetto collaterale della rimozione di
codice morto dello stesso ciclo (es. `b10449b6` del 2026-08-05), non di una pulizia
dedicata. La preoccupazione del vecchio report ("rimuoverli cancella un'intenzione
documentata") è stata quindi superata dai fatti: le funzioni annotate non esistono più.

### Riproducibilità del totale "702"

Il totale 702 del vecchio report non è riproducibile alla virgola: la somma delle 16
regole tabellate dà 612 (675 con la correzione RUF100 48→111), e il report stesso
documenta che i conteggi provenivano da scansioni con configurazioni diverse. Con
l'elenco esatto delle 16 regole in `--extend-select` oggi si ottengono **594** rilievi.
Il confronto onesto è per-regola (tabella sopra): il segnale è che il debito è stabile o
in crescita su tutte le voci non auto-correggibili (`C901` +19, `ARG001` 14→78,
`RUF022` 12→24, `RUF007` 9→18), in calo solo su quelle auto-fixate e su `S110`/`RUF100`
per via della bonifica.

---

## Task riesumati

1. **Loggare il nuovo S110 in `cache_utils.py:82`** (S, una riga): `logger.debug(...,
   exc_info=True)` nel ramo "cache che non si chiude". Regressione del 2026-08-13.
2. **Valutare `S110` (ed eventualmente `TRY400`) nella config ruff di progetto** (S):
   `pyproject.toml:72-81` non include `S`; con la regola attiva la regressione 1 non
   sarebbe entrata. Stessa famiglia della decisione `TRY003` lasciata aperta (voce 1.5).
3. **Verificare i candidati N+1 in ordine di N atteso** (M): mai fatta. Partire da
   `asset_source.py` (bulk delete `:4091+`, bulk patch) e dagli endpoint
   `portfolio_api.py:49` / `fx.py:965,1014` (coperti dal report gemello 01).
4. **Fissare `max-complexity = 25` in `pyproject.toml`** (S): rende il segnale C901
   utilizzabile (19 funzioni invece di 157); la voce 1.2 era nulla perché la config non
   esisteva — va *creata*, non alzata.
5. **Convertire i 55 `TRY400` in `logger.exception`** (M): mai fatto, cresciuto di 2.
6. **Migrare `BrokerSharingPanel.svelte` alle Runes** (M): 24 `$:` oggi, in crescita —
   più si attende, più costa.
7. **Piano di attacco per la top-20 C901** (L): `execute_batch` (115) e `build` (97)
   sono di un altro ordine di grandezza; intoccate da un mese e `execute_batch` cresciuta.

---

## Nuovi rilievi

- **N1 (vedi report 01)**: Pillow bloccante in `uploads.py:423,435,440` — violazione
  Async I/O sfuggita all'audit pur essendo presente dal 2026-01-20. Il claim "104 siti
  verificati, 1 violazione" andrebbe quindi letto come "104 siti verificati, 2
  violazioni di cui 1 non rilevata".
- **N2**: la tabella K5 della fonte citava un file inesistente (`wac_service.py`,
  rimosso 2026-06-10). Reperto di forma, non di sostanza — le funzioni e le complessità
  erano e sono reali — ma conferma il monito del progetto: *un path citato non è un path
  esistente* (cfr. `check_source_paths.py` del devWiki).

---

## Cross-reference

- Fonte archiviata: [05_cleanAudit/11_crosscutting.md](../../phases/05_cleanAudit/11_crosscutting.md)
- Esecuzione S1–S3 (licenza, pre-warm, S110, autofix): [05_cleanAudit/15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md)
- Backlog per complessità (voci 1.2, 1.5, 4.4, 6.9, 6.10): [05_cleanAudit/14_backlog_per_complessita.md](../../phases/05_cleanAudit/14_backlog_per_complessita.md)
- Report gemello di questa tornata: [01_api_layer.md](01_api_layer.md)
