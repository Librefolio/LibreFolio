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
**Stato:** 🟡 Gap da colmare (analisi del gap)

**Analisi:**
Dal punto di vista dell'utilizzatore, il sistema di testing (`test-walkthrough/index.md`) è documentato in modo magistrale: è completo di diagrammi Mermaid, flag descritti e un walkthrough sul meccanismo di isolamento della code coverage (`.coverage_data`).
Tuttavia, c'è un disallineamento storico: il file fa ancora riferimento a `test_runner.py` (linee 145, 160) ma il componente è stato rifattorizzato come un package modulare in `scripts/test_runner/` (`_backend_api.py`, `_registry.py`, `_cli.py`, ecc.). Manca un'esposizione architetturale della sua natura modulare.

**Proposte per colmare il gap:**
- **Dove:** Aggiornare `test-walkthrough/index.md` rimuovendo l'estensione `.py` o, meglio, aggiungere un sub-documento `test-walkthrough/runner_architecture.md`.
- **Cosa:** Documentare il funzionamento del modulo `scripts/test_runner/`, in particolare il meccanismo in `_registry.py`, la gestione delle suite differenziate (`_suites.py`), e come definire un nuovo layer di frontend/backend test.

---

## 4. WorkspaceIntent API
**Stato:** 🔴 Assente

**Analisi:**
Non vi è alcuna traccia dell'API `WorkspaceIntent` nella documentazione per sviluppatori all'interno di `mkdocs_src/docs/developer`. Il termine non compare in alcun `.md` file, il che rappresenta una lacuna importante per comprendere il ciclo di vita delle richieste e il multi-tenancy/isolamento degli asset nel backend.

**Proposte per colmare il gap:**
- **Dove:** Creare un nuovo file in `architecture/patterns/workspace_intent.md` o inserirlo in una sezione ad-hoc sotto `backend/`.
- **Cosa:**
  1. Definizione dell'astrazione `WorkspaceIntent` (cosa rappresenta e quando va usata).
  2. Implementazione tecnica: come viene passato il contesto (es. tramite Header HTTP, Token JWT) e intercettato dai dependency injectors di FastAPI.
  3. Scope a livello Database: come il servizio interagisce con SQLAlchemy per filtrare o isolare le entity a livello di workspace (RBAC e sharing models).
  4. Code snippet o diagramma architetturale per le best practices di integrazione di questa API su nuovi endpoint.
