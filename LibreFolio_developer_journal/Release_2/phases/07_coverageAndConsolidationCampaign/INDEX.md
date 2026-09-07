# 07 — Campagna copertura e consolidamento

> Fonti primarie della campagna che va dalla migrazione del test runner alla chiusura dei
> sedici difetti fissati come caratterizzazione. **Sono le fonti citate dalle pagine
> `sources/` del devWiki**: prima di questa copia vivevano in una directory di sessione
> fuori dal repository, dove il rilevamento di deriva (`git diff {hash} HEAD`) non poteva
> funzionare per costruzione, e una pulizia le avrebbe fatte sparire lasciando nove pagine
> wiki senza modo di essere verificate.

## Cosa contiene

### Infrastruttura di test

| file | di cosa parla |
|---|---|
| `plan-p7-js-coverage.md` | strumentazione della copertura JS/Svelte |
| `plan-p8-runner-migration.md` | architettura parallela del runner — **piano in attesa di approvazione**, vedi avvertenza sotto |
| `plan-p9-test-semantics-COMPLETO.md` | semantica dei test |
| `plan-tappe-7-11-parallelismo-COMPLETO.md` | parallelizzazione della suite frontend |
| `tappa9-desleep.md` | rimozione degli `sleep` e sostituzione con stati osservabili |
| `coda-beta-parametrici-forkserver.md` | provider parametrici e forkserver |
| `draft-runner-changes.md`, `draft-fixtures-playwright.ts` | bozze superate dai rispettivi `-COMPLETO` |

### Campagne di copertura

| file | di cosa parla |
|---|---|
| `plan-storico-fase012.md` | fasi 0-1-2 |
| `plan-storico-coverage-campaign.md` | campagna di copertura, prima parte |
| `plan-storico-coverage-campaign-2.md` | campagna di copertura, seconda parte |
| `plan-storico-corsie-sync-e-logica.md` | corsia sync e logica pura |
| `plan-storico-corsia-impostazioni-COMPLETO.md` | corsia impostazioni, condivisione, logica pura |

### Chiusura dei difetti

| file | di cosa parla |
|---|---|
| `difetti-aperti-corsia-impostazioni.md` | **il più denso**: i sedici difetti con le decisioni motivate dell'utente, risposta per risposta |
| `plan-storico-undici-difetti-COMPLETO.md` | il piano di chiusura |
| `plan-storico-scheduler-e-fx-COMPLETO.md` | scheduler nel fuso configurato (D1) e tasso FX annullabile (D2) |

## ⚠️ Due avvertenze per chi legge queste fonti

**Un piano non è una cronaca.** `plan-p8-runner-migration.md` si apre dichiarando *«piano in
attesa di approvazione, nessun file del repository è stato toccato»*. L'architettura è poi
atterrata davvero — `_inventory.py`, `_scheduler.py`, `_executor.py`, `_run_cache.py`
esistono — ma **i nomi dei file sono quelli proposti, non quelli consegnati**. Un lint del
2026-09-01 ha trovato pagine wiki che citavano `_orphans.py`, `_schedule.py` e un package
`actions/` che non sono mai esistiti, derivati da questa lettura.

**Verificare i path contro l'albero, sempre.** Lo stesso lint ha trovato che **144 path su
1 828** citati dalle tabelle `## Source files` del devWiki puntano a file inesistenti: in
parte deriva da refactor databili (giugno 2026), in parte proposte mai atterrate, in tre
casi invenzioni. Un path preso da un piano non è un path verificato.

## Esito della campagna

Suite 15/15 verde in 46 m 55 s. Linee 78,02 %, arm di ramo 59,45 %, backend 90,18 %.

> Le cifre di copertura in queste fonti sono state prese con formule e conteggi di worker
> diversi e **non sono riconciliabili a posteriori**. Vedi
> `LibreFolio_devWiki/wiki/problems/coverage-percent-mixed-lines-and-branches.md`.
