# Audit Documentazione: Backend Architecture & Test Infrastructure
**Data:** 18 Giugno 2026
**Area:** Backend Architecture & Test Infrastructure (test_runner modulare, WorkspaceIntent API, async I/O rule, dev.py)

---

## 1. `dev.py`
**Stato:** 🟢 Completa e allineata agli standard estetici

**Analisi:**
La documentazione relativa al comando di orchestrazione `dev.py` è eccellente. Il file `dev-installation.md` agisce come entry point perfetto, contenendo tabelle ben formattate che raggruppano tutti i sub-comandi per categoria (Frontend, API Client, Internationalization, Database, Testing, ecc.). 
La documentazione fa un ottimo uso di callouts (`!!! note`), icone e markdown standard. Sono presenti anche riferimenti incrociati e coerenti nei file specifici (es. `api/overview.md`, `test-walkthrough/index.md`).

**Azioni proposte:** Nessuna.

---

## 2. Async I/O Rule
**Stato:** 🟢 Completa e allineata agli standard estetici

**Analisi:**
Le best practice per l'architettura asincrona sono documentate con grande chiarezza nel file `architecture/patterns/async.md`. Il documento illustra il razionale dell'async in FastAPI e SQLAlchemy e tratta approfonditamente la "Thread Isolation" per le dipendenze sincrone esterne (es. `yfinance`) tramite la funzione `_run_provider_in_thread`.
L' "Event Loop Blocking Rule" è evidenziata in modo marcato tramite un apposito callout warning, che elenca persino i sintomi del blocco del loop. La struttura visiva e i code snippets sono impeccabili.

**Azioni proposte:** Nessuna.

---

## 3. Test Runner Modulare
**Stato:** 🟢 Completa e allineata agli standard

**Analisi:**
Dal punto di vista dell'utilizzatore, il sistema di testing (`test-walkthrough/index.md`) è documentato in modo magistrale: è completo di diagrammi Mermaid, flag descritti e un walkthrough sul meccanismo di isolamento della code coverage (`.coverage_data`).
Tuttavia, c'era un disallineamento storico: il file faceva ancora riferimento a `test_runner.py` (linee 145, 160) ma il componente è stato rifattorizzato come un package modulare in `scripts/test_runner/` (`_backend_api.py`, `_registry.py`, `_cli.py`, ecc.). Mancava un'esposizione architetturale della sua natura modulare.

**Risoluzione (19 Giugno 2026):**
- **Sorgenti Corretti:** Aggiornato `test-walkthrough/index.md` rimuovendo i riferimenti a `test_runner.py` e sostituendoli con `scripts/test_runner/`.
- **Nuovo Documento Architetturale:** Creato `test-walkthrough/runner_architecture.md` per descrivere il Registry Pattern, l'orchestrazione delle suite, la gestione del swap-in/swap-out di `.coverage` e le guide per estendere il runner.
- **Grafici Aggiornati:** Tutti i diagrammi Mermaid del test runner sono stati configurati con il nuovo layout ELK (`layout: elk`) e la panoramica principale è stata disposta orizzontalmente (`graph LR`).
- **Navigazione:** Registrato il nuovo documento in `mkdocs.yml`.

---

## 4. WorkspaceIntent API
**Stato:** 🟢 Chiarita e Documentata (lato Frontend)

**Analisi & Chiarimento Critico:**
Non vi era alcuna traccia dell'API `WorkspaceIntent` nella documentazione per sviluppatori in `mkdocs_src/docs/developer`.
*Nota bene:* L'audit ipotizzava che fosse un'infrastruttura backend per il multi-tenancy e l'isolamento dei dati. L'analisi del codice conferma invece che il backend isola le risorse tramite cookie di sessione JWT (`get_current_user` in `auth.py`) e filtri a livello di servizio DB (es. `BrokerUserAccess`). `WorkspaceIntent` è invece una **declarative API del frontend (Svelte 5)** per definire le intenzioni di modifica massiva (create, edit, clone, delete, import) all'interno di `TransactionBulkModal.svelte` dialogando con il reactive store `txStore` ed i messaggi `ImportTodo` (BRIM).

**Risoluzione (19 Giugno 2026):**
- **Documentazione Frontend State:** Modificato il file `developer/frontend/state/transaction-draft.md` aggiungendo una sezione dedicata al pattern `WorkspaceIntent` (con definizioni dei tipi TypeScript) e al meccanismo di staging di `ImportTodo` (gestione dei warning e blocker del parser BRIM).
- **Riferimenti allineati:** Il manuale riflette ora il corretto posizionamento architetturale (lato client) di questo pattern.
