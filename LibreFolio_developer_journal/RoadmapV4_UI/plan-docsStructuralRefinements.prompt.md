# Plan: Rifinimenti strutturali documentazione pre-Batch 2

Quattro interventi strutturali sulla documentazione MkDocs: rimuovere Tutorials WIP, fondere Architecture+Technologies con alberatura profonda e database schema splittato, raggruppare Test Walkthrough in Backend/Frontend, esplodere componenti in sotto-file dedicati.

**Dipendenze**: `plan-docsPerfection.prompt.md` Batch 1, 3, 4, 5 completati ✅
**Status**: ✅ COMPLETATO — Tutti i 5 step eseguiti (20 Marzo 2026)
**Ordine di esecuzione**: Step 1 → 2 → 3 → 4 → 5 (dal meno al più impattante sui file)

---

## Step 1 — Rimuovere Tutorials

Il più semplice. I tutorial sono WIP stub da 11 righe ciascuno.

### Azioni

1. Eliminare in `mkdocs.yml` (righe 172-174) la sezione:
   ```yaml
   - Tutorials:
       - Track First Stock: tutorials/track-first-stock.md
       - Track P2P Loan: tutorials/track-p2p-loan.md
   ```
2. Eliminare i file:
   - `mkdocs_src/docs/tutorials/track-first-stock.md`
   - `mkdocs_src/docs/tutorials/track-p2p-loan.md`
3. Eliminare la cartella `tutorials/`
4. Grep per verificare che nessun'altra pagina linki ai tutorial

---

## Step 2 — Architecture & Technologies: fusione con alberatura profonda

Fusione delle due sezioni nav (`Technologies` 4 file + `Architecture` 7 file) in un'unica **"Architecture & Technologies"** con 3 sotto-alberi. I file vengono **spostati fisicamente** e tutti i cross-link aggiornati.

### Struttura directory finale

```
developer/architecture/
├── overview.md                  # Esistente + sezione "Tech Stack" fusa da technologies/overview.md
│
├── patterns/                    # NUOVO sotto-albero — "strumenti e pattern"
│   ├── async.md                 # ← spostato da technologies/async_architecture.md
│   ├── registry_pattern.md      # ← spostato dalla root architecture/
│   ├── alembic.md               # ← spostato da technologies/alembic.md
│   └── configuration.md         # ← spostato da technologies/configuration.md
│
├── security.md                  # Resta in architecture/ (raggruppato nella nav sotto "Core Systems")
├── users_and_brokers.md         # Resta in architecture/ (raggruppato nella nav sotto "Core Systems")
├── access_control.md            # Resta in architecture/ (raggruppato nella nav sotto "Core Systems")
├── settings.md                  # Resta in architecture/ (raggruppato nella nav sotto "Core Systems")
│
└── database/                    # NUOVO sotto-albero — split di database.md (154 righe)
    ├── index.md                 # ER overview diagram + Design Philosophy
    ├── users_access.md          # §1 User & Access Control (righe 38-61)
    ├── brokers_transactions.md  # §2 Broker & Transactions (righe 63-91)
    ├── assets_pricing.md        # §3 Asset Management (righe 92-118)
    └── fx_rates.md              # §4 FX Subsystem (righe 120-145)
```

### Nav proposta in `mkdocs.yml`

```yaml
- Architecture & Technologies:
    - System Overview: developer/architecture/overview.md
    - Technologies & Patterns:
        - Async Architecture: developer/architecture/patterns/async.md
        - Registry & Plugin System: developer/architecture/patterns/registry_pattern.md
        - Database Migrations (Alembic): developer/architecture/patterns/alembic.md
        - Configuration: developer/architecture/patterns/configuration.md
    - Core Systems:
        - Security & Authentication: developer/architecture/security.md
        - Users & Roles: developer/architecture/users_and_brokers.md
        - Access Control (RBAC): developer/architecture/access_control.md
        - Settings System: developer/architecture/settings.md
    - Database Schema:
        - Overview: developer/architecture/database/index.md
        - Users & Access: developer/architecture/database/users_access.md
        - Brokers & Transactions: developer/architecture/database/brokers_transactions.md
        - Assets & Pricing: developer/architecture/database/assets_pricing.md
        - FX Rates & Routes: developer/architecture/database/fx_rates.md
```

### Azioni file per file

| File attuale | Azione | Destinazione |
|---|---|---|
| `technologies/overview.md` (37 righe) | **Merge** il contenuto come sezione "Tech Stack" in fondo a `architecture/overview.md` | Eliminare il file |
| `technologies/async_architecture.md` | **Move** | `architecture/patterns/async.md` |
| `technologies/alembic.md` | **Move** | `architecture/patterns/alembic.md` |
| `technologies/configuration.md` | **Move** | `architecture/patterns/configuration.md` |
| `architecture/registry_pattern.md` | **Move** | `architecture/patterns/registry_pattern.md` |
| `architecture/database.md` (154 righe) | **Split** in 5 file | `architecture/database/index.md` + 4 subsystem files |

### Dettaglio: merge `technologies/overview.md` → `architecture/overview.md`

Il contenuto di `technologies/overview.md` (elenco librerie Backend/Frontend/Testing) viene aggiunto come sezione finale **"## Tech Stack"** in `architecture/overview.md`, dopo "Request Flow Example". Il file `technologies/overview.md` viene poi eliminato.

### Dettaglio: split `database.md`

| File | Contenuto sorgente (righe) | Contenuto |
|---|---|---|
| `database/index.md` | 1-35 + 147-154 | Intro, Logical Data Flow mermaid, Design Philosophy |
| `database/users_access.md` | 38-61 | User & Access Control: tabelle USER, USER_SETTINGS, BROKER_USER_ACCESS, ER mermaid |
| `database/brokers_transactions.md` | 63-91 | Broker & Transactions: tabelle BROKER, TRANSACTION, self-reference, ER mermaid |
| `database/assets_pricing.md` | 92-118 | Asset Management: tabelle ASSET, PRICE_HISTORY, ASSET_PROVIDER_ASSIGNMENT, ER mermaid |
| `database/fx_rates.md` | 120-145 | FX Subsystem: tabelle FX_RATE, FX_CURRENCY_PAIR_SOURCE, alphabetical base<quote rule |

In `database/index.md` aggiungere link ai 4 file subsystem.

### Dettaglio: arricchire `registry_pattern.md`

Dopo la sezione "Guide: How to Create a New Plugin", aggiungere una sezione **"## Subsystem Documentation"** con link a:

- **BRIM**: [Architecture](../../backend/brim/architecture.md) · [Providers List](../../backend/brim/providers_list.md) · [Generic CSV](../../backend/brim/generic_csv.md)
- **Assets**: [Architecture](../../backend/assets/architecture.md) · [System Providers](../../backend/assets/system_providers.md) · [Providers List](../../backend/assets/providers_list.md)
- **FX**: [Architecture](../../backend/fx/architecture.md) · [Configuration & Routing](../../backend/fx/configuration.md) · [Providers List](../../backend/fx/providers_list.md)

### Cross-link da aggiornare

Dopo lo spostamento, grep per tutti i path `technologies/` e `architecture/database.md` e `architecture/registry_pattern.md`:

- `developer/index.md` — path alle pagine Technologies e Database
- `dev-installation.md` — link a `technologies/alembic.md`
- `architecture/overview.md` — link a `database.md` → `database/index.md`
- `admin/filesystem.md` — link a `../developer/architecture/database.md` → `../developer/architecture/database/index.md`
- `architecture/settings.md` — fix `./dev.sh` → `./dev.py`
- `architecture/users_and_brokers.md` — link a `access_control.md` (path invariato, OK)
- Qualsiasi altro file trovato con grep

### Pulizia

Eliminare la cartella `technologies/` dopo aver spostato tutti i file.
Eliminare il file `architecture/database.md` dopo averlo splittato.

---

## Step 3 — Test Walkthrough: raggruppare Backend/Frontend

Ristrutturare la nav in `mkdocs.yml` con due sotto-gruppi e creare una nuova pagina overview per i test frontend.

### Nav proposta

```yaml
- Test Walkthrough:
    - Overview: developer/test-walkthrough/index.md
    - Backend Tests:
        - External: developer/test-walkthrough/external.md
        - Database: developer/test-walkthrough/db.md
        - Services: developer/test-walkthrough/services.md
        - Utils: developer/test-walkthrough/utils.md
        - Schemas: developer/test-walkthrough/schemas.md
        - API: developer/test-walkthrough/api.md
        - E2E: developer/test-walkthrough/e2e.md
    - Frontend Tests (Playwright):
        - Overview: developer/test-walkthrough/front-overview.md
        - Front-Utility: developer/test-walkthrough/front-utility.md
        - Front-User: developer/test-walkthrough/front-user.md
        - Front-FX: developer/test-walkthrough/front-fx.md
```

### Creare `test-walkthrough/front-overview.md`

Nuova pagina che documenta:

1. **Tools & Framework**: Playwright, `@playwright/test`, `expect`, page fixtures, come i test interagiscono con browser reale
2. **Setup automatico**: Come `dev.py` avvia automaticamente il server backend + serve la build frontend prima dei test; modalità `--test` con database isolato
3. **Tabella flag dettagliata**:

| Flag | Effetto | Quando usarlo |
|------|---------|---------------|
| `--headed` | Apre un browser visibile (non headless) | Debugging visuale, vedere il flow |
| `--debug` | Abilita Playwright Inspector (step-by-step) | Analizzare selettori, breakpoint per azione |
| `--ui` | Apre Playwright UI mode (runner interattivo con timeline, DOM snapshot, trace) | Esplorare test, vedere trace, re-run selettivo |
| `--list` | Elenca i test disponibili senza eseguirli | Scoprire test, verificare naming |

4. **Playwright UI mode**: Breve descrizione di cosa offre (timeline delle azioni, DOM snapshot per ogni step, network tab, re-run singolo test, filtro per file/describe)

### Aggiornare `test-walkthrough/index.md`

Spostare la sezione "Frontend-Specific Flags" (righe 32-40) dalla index alla nuova `front-overview.md`. In `index.md` lasciare solo un breve rimando:

> For frontend-specific testing tools and flags, see the [Frontend Tests Overview](front-overview.md).

---

## Step 4 — Componenti: esplodere in sotto-file dedicati

### File esistenti (invariati)

I file già ben scritti restano come sono:

- `data-table.md` (138 righe) ✅
- `auth.md` (122 righe) ✅
- `settings.md` (124 righe) ✅
- `file-upload.md` (125 righe) ✅

### Nuovi file da creare

#### `components/select.md` — Select & Dropdown Components

Componenti da `lib/components/ui/select/`:

| Componente | Scopo | Dove è usato |
|---|---|---|
| `BaseDropdown` | Dropdown base con click-outside, keyboard nav, positioning | Base per tutti i select |
| `SimpleSelect` | Select da lista opzioni (come `<select>` nativo) | Filtri, form semplici |
| `SearchSelect` | Dropdown con ricerca fuzzy (sostituisce vecchio FuzzySelect) | Selezione utenti nel sharing modal |
| `CurrencySearchSelect` | SearchSelect specializzato per valute (flag emoji, codice ISO) | Add Pair modal, broker form |
| `FxProviderSelect` | Select per provider FX con info bar e link docs | FxProviderConfig |
| `ImportPluginSelect` | Select per plugin BRIM con icona provider | BrokerImportFilesModal |
| `BrokerSearchSelect` | Select broker con icona e search | Filtri transazioni |

Per ogni componente: breve descrizione (3-5 righe), props principali (senza firma completa — per quella si va nel codice), screenshot dove utile.

#### `components/brokers.md` — Broker Components

Componenti da `lib/components/brokers/`:

| Componente | Scopo | Dove è usato |
|---|---|---|
| `BrokerCard` | Card display broker con icona, nome, valuta | Lista broker `/brokers` |
| `BrokerForm` | Form creazione/modifica broker (nome, valuta, icona) | BrokerModal |
| `BrokerIcon` | Icona smart con fallback chain (icon_url → favicon → plugin → Briefcase) | BrokerCard, BrokerSearchSelect |
| `BrokerModal` | Modale creazione/modifica broker (wraps BrokerForm in ModalBase) | Pagina broker |
| `BrokerImportFilesModal` | Modale import file BRIM con plugin select | Pagina broker detail |
| `BrokerSharingModal` | Modale sharing RBAC (search utenti, ruoli, percentuale) | Pagina broker detail |
| `DeleteBrokerDialog` | Conferma eliminazione broker (ConfirmModal) | Pagina broker detail |
| `CashBalanceCard` | Card saldo cash del broker | Pagina broker detail |
| `CashTransactionModal` | Modale per operazioni cash (deposito, prelievo) | Pagina broker detail |

### Riscrivere `components/index.md`

Trasformare in overview breve con link ai 6 sotto-file. Ogni categoria con titolo bold, 1-2 righe di descrizione, link al sotto-file. Mantenere la sezione "Component Guidelines" in fondo (invariata).

### Aggiornare nav in `mkdocs.yml`

```yaml
- Components:
    - Overview: developer/frontend/components/index.md
    - DataTable: developer/frontend/components/data-table.md
    - Authentication: developer/frontend/components/auth.md
    - Settings: developer/frontend/components/settings.md
    - File Upload & Media: developer/frontend/components/file-upload.md
    - Select & Dropdowns: developer/frontend/components/select.md
    - Brokers: developer/frontend/components/brokers.md
```

---

## Step 5 — Aggiornare `developer/index.md`

Dopo i passi 2-4, aggiornare tutti i link nella panoramica developer per riflettere la nuova struttura:

- Path `technologies/…` → `architecture/patterns/…`
- Path `architecture/database.md` → `architecture/database/index.md`
- Aggiungere link ai nuovi componenti (select, brokers)
- Aggiornare la sezione Testing per riflettere il raggruppamento Backend/Frontend
- Rimuovere eventuali riferimenti ai tutorial eliminati

---

## Considerazioni

### Ordine e rischio

Lo Step 2 (Architecture merge) è il più impattante: sposta 5 file, splitta 1 file in 5, elimina 1 cartella. Fare grep esaustivo prima e dopo per non lasciare broken link. Build mkdocs dopo ogni step per validare.

### Database Settings

Le tabelle GlobalSetting e UserSetting sono piccole. Includere in `database/users_access.md` (sono dati user-scoped). Non creare un file separato `database/settings.md`.

### Tempo stimato

| Step | Stima |
|------|-------|
| 1 — Rimuovere Tutorials | ~5 min |
| 2 — Architecture merge + DB split | ~45 min |
| 3 — Test Walkthrough grouping | ~20 min |
| 4 — Components sub-files | ~30 min |
| 5 — Developer index update | ~10 min |
| **Totale** | **~2 ore** |

