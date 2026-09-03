# P1 — Quick win tecnici: piano di esecuzione (08_newCleanAndDocumentation_audit)

> **Creato**: 2026-09-02, giorno dell'audit. **Fonte**: [`99_task_riesumati.md`](99_task_riesumati.md) §P1 (18 voci) + i P0-5 secondari.
> **Metodo**: workstream paralleli per area di file (mai due sullo stesso file),
> **nessuna suite di test durante lo sviluppo parallelo** — run targeted solo se un
> workstream è solo; **una run full seriale alla fine** (`dev.py test all`, workers=1).
> **Chiusura**: a fine giro, aggiornare lo stato nei report d'area che citavano le voci
> (come fatto per i P0 il 02/09) + CHANGELOG + questo piano.

## Decisioni pendenti (bloccano i rispettivi task)

| # | Questione | Stato |
|---|---|---|
| D-1 (P1-2) | Soglia complessità | ✅ **Deciso 03/09 (utente)**: soglia BASSA (10) → i flat packer saltano fuori e vengono marcati uno a uno con `# noqa: C901 — flat mapping, no nested logic` (commento mirato, non per-file); sui residui si legge il valore reale e si decide il massimo sensato. ~157 funzioni da triaggiare: NON è una quick win — WS-B diventa M, esecuzione a lotti per modulo |
| D-2 (P1-16) | Prova migrazione su DB 1.0.1 | ✅ **Deciso 03/09 (utente)**: container dall'**immagine pubblicata vecchia** (è online) → popolare → stoppare → riavviare con l'**immagine locale nuova** sullo stesso volume → osservare la migrazione (log alembic, integrità, boot, dashboard). Via `./dev.py docker` tooling |
| D-3 (P1-11 coda) | Metadati componenti AI export drawdown (`version=1`/`WINDOWED` vs payload full-history) prima del tag V1. Nota: il bump `implementation_version` 1.1.0 del plugin è **già fatto** (02/09, la policy lo richiedeva e la semantica era appena cambiata) | ⏳ da decidere con P2 |

## Workstream paralleli

```
WS-A api contracts      P1-1  response_model ×6 (system.py, settings.py, uploads.py) + api sync
WS-B lint hygiene       P1-2  (dopo D-1) config complessità + triage violazioni
                          P1-3  55 TRY400 → logger.exception
WS-C backend dead code  P1-4  orfani backend (_price_on_date, test-only helpers, aggregate_*)
                          P0-5b N+1 verbatim: portfolio_api.py:49, fx.py:965/:1014
                          P1-6  fifo_utils.py removal — SOLO dopo mappatura casi limite (sotto-step proprio)
WS-D frontend dead/i18n P1-7  orfani frontend
                          P1-8  96 voci importWizard + 4 cannotLinkEventNoAsset + 30 aiExport.dataset
                                — via `dev.py i18n remove` (autorizzato: riordino/format dei JSON ok)
                          P1-9  barrel re-export + tipi orfani
WS-E frontend stores    P1-10 grafo valute: completare l'invalidazione (vedi sotto)
WS-F test infra         P1-5  stringhe stale del runner
                          P1-13 coverage spawn workers (vedi sotto)
                          P1-14 expectChartCanvas generalizzato
WS-G meta/docs          P1-12 regola E2 nella skill audit · P1-15 · P1-17
WS-H release gate       P1-16 (dopo D-2) prova migrazione
CHIUSURA                P1-18 suite completa + misura coverage dichiarata + incrocio JS×knip
                          (per ultimo: misura ciò che gli altri WS hanno cambiato)
```

## Note di soluzione concordate

### P1-10 — grafo valute mezzo cablato (`stores/currencyGraphStore.ts`)
`cachedProvidersHash` è calcolato (:96) e mai confrontato; `invalidateCurrencyGraph()`
(:135) ha **zero chiamanti**. Il grafo ha per spigoli le coppie FX configurate — e le
coppie **cambiano a runtime** (FxPairAddModal crea/elimina route, incl. MANUAL). Quindi la
risposta giusta è *completare*, non rimuovere: chiamare `invalidateCurrencyGraph()` nei
punti di mutazione coppie (add/edit/delete pair), e **rimuovere il campo hash mai letto**
(o collegarlo come confronto — ma confrontare richiede un refetch dei provider a ogni
accesso, il che nega la cache: no). La sync dei RATE non tocca il grafo (spigoli = coppie,
non valori) → niente invalidazione lì.

### P1-13 — coverage dei worker spawn
`.coveragerc` ha già `concurrency = multiprocessing,thread,gevent` (necessario ma non
sufficiente per `spawn`): manca l'avvio di coverage **dentro** il figlio. Ricetta standard
coverage.py: (1) un `sitecustomize.py` con `coverage.process_startup()`; (2) runner con
`--coverage` imposta `COVERAGE_PROCESS_START=<repo>/.coveragerc` e prepend al PYTHONPATH la
cartella col sitecustomize; (3) i figli spawn ereditano l'env → scrivono
`.coverage.<host>.<pid>.<rand>` → il combine li raccoglie. Verifica: una riga di
`spawn_worker.py` toccata da un test risk appare coperta.

### P1-2 — complessità (risposta alla domanda dell'utente)
Sì: McCabe/C901 conta **ogni** punto decisionale — inclusi ternari e operatori booleani —
quindi un flat packer "spacchetta e ripacchetta" con 12 ternari segna 13 pur essendo
lineare. La metrica "onesta" per quel caso sarebbe la cognitive complexity (penalizza il
nesting, non il flat data-shuffling), **ma ruff non la supporta**. Con la toolbox ruff:
C901@25 ora (19 violazioni, triage con fix o `# noqa: C901 — flat mapping` motivato) +
PLR0915 (troppi statement, default 50) come rete per i muri di statement, e cricchetto
verso 15/10 in una tornata successiva. Soglia 10 subito = ~157 funzioni da toccare: non è
una quick win, è un progetto.

## Regole
- Test nuovi/riparati via test-author; mai due suite in parallelo (DB condiviso).
- `./dev.py api sync` dopo WS-A (schemi). `./dev.py i18n` per WS-D (mai edit a mano dei JSON).
- Nessun `git commit` — proposta di messaggio a fine giro.
- A fine giro: stato nei report d'area + 99_task_riesumati.md + questo piano + CHANGELOG.
