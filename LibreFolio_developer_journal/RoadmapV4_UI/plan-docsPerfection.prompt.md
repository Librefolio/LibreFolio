# Plan: Documentazione LibreFolio — Rifinitura completa

**Data creazione**: 20 Marzo 2026
**Status**: ⏳ IN CORSO — Batch 1, 3, 4, 5 completati ✅. Batch 2 (emoji H2/H3/bullet) pendente. Rifinimenti strutturali completati (vedi `plan-docsStructuralRefinements.prompt.md` ✅).
**Priorità**: Alta
**Stima residua**: ~2 ore (solo Batch 2)
**Dipendenze**: `plan-fxDocumentation.prompt.md` Fasi 1-2.5 completate ✅

---

## Contesto

Ristrutturazione della documentazione MkDocs in 5 batch: fix immediati, emoji H2/H3 su tutti i file, riscrittura Developer Manual per comandi dev, aggiornamento Test Walkthrough, e rifinitura generale.

Le emoji H1 sono già state applicate a 68 file. Ora servono: fix di bug introdotti, emoji H2/H3/bullet, documentazione comandi dev nel Developer Manual, e verifiche cross-link.

**Ordine di esecuzione consigliato**:
```
Batch 1 (fix bug)  →  Batch 3-4 (developer manual)  →  Batch 2 (emoji pass globale)  →  Batch 5 (verifica links)
```

---

## Batch 1 — 🔧 Fix immediati (bug bloccanti)

**Stima**: ~10 min

### 1.1 Fix `user/fx/sync.md`

Rimuovere la duplicazione a riga 36 (`# 🔄 FX Synchronization` ripetuto + `// ...existing code...`).

Riscrivere il file unificando:
- Sync All
- Individual Pair Sync
- How Sync Works (con fallback)
- Data Supply Chains
- Link a `providers_list.md` e `configuration.md`

### 1.2 Fix `user/brokers/index.md`

Due problemi:

1. **Immagine sbagliata**: L'immagine tra step 3 e step 4 mostra `data-name="detail"` (broker detail page) ma dovrebbe mostrare `data-name="edit-modal"` (form di edit broker)
2. **Numerazione rotta**: Step 4 si renderizza come "1." perché markdown perde la numerazione dopo un blocco HTML. **Soluzione**: mettere l'immagine DOPO tutto l'elenco numerato, oppure usare indentazione dell'img dentro il punto 3.

---

## Batch 2 — ✨ Emoji minuziose su H2/H3/bullet (tutti i file)

**Stima**: ~2 ore per ~80 file minuziosi

Per ciascuno dei ~80 file `.md` sotto `mkdocs_src/docs/`, leggere e aggiungere emoji manualmente ai titoli H2, H3 e alle bullet list dove ha senso. Ogni file va letto, capito, e decorato con emoji tematiche coerenti.

### File da processare per area:

- **user/** (13 file): brokers, sharing, files, fx, chart, signals, measures, data-editor, provider, add-pair, sync, chart-settings, image-crop
- **admin/** (6 file): index, cli_tools, settings, filesystem, docker_advanced, tailscale
- **developer/** (~30 file): architecture, technologies, api, backend (brim/fx/assets), frontend, test-walkthrough
- **financial-theory/** (7 file): index, asset-types, transaction-types, day-count, returns, technical-indicators, synthetic-benchmarks
- **gallery/** (3 file), `faq.md`, `credits-legal.md`, **tutorials/** (2 file), **POC_UX/**

---

## Batch 3 — 📋 Developer Manual: documentare i comandi dev

**Stima**: ~1 ora

### 3.1 Aggiornare `developer/dev-installation.md`

Aggiungere sezione **"Development Workflow"** con i comandi principali:

| Comando | Descrizione |
|---------|-------------|
| `front dev` | Avvia dev server frontend (Vite HMR) |
| `front build` | Build produzione frontend |
| `front check` | Lint + type-check frontend |
| `api sync` | Esporta OpenAPI schema + genera TypeScript client |
| `i18n audit` | Audit chiavi i18n (duplicati, mancanti) |
| `db migrate` | Applica migrazioni Alembic |
| `db create-clean` | Ricrea database pulito |

Ogni comando con breve spiegazione e link alla sezione di approfondimento.

### 3.2 Riscrivere `developer/test-walkthrough/index.md`

Riscrittura completa:

- Usare `./dev.py test` (non `./dev.sh test`)
- Aggiungere tabella completa categorie test:

| Categoria | Comando | Descrizione |
|-----------|---------|-------------|
| External | `./dev.py test external all` | Provider tests (FX, assets, BRIM) |
| Database | `./dev.py test db all` | Database layer tests |
| Services | `./dev.py test services all` | Service logic tests |
| Utils | `./dev.py test utils all` | Utility tests |
| Schemas | `./dev.py test schemas all` | Schema validation tests |
| API | `./dev.py test api all` | API endpoint tests |
| E2E | `./dev.py test e2e all` | Backend end-to-end tests |
| Front-Utility | `./dev.py test front-utility all` | Auth, settings, files, select, crop |
| Front-User | `./dev.py test front-user all` | Brokers, multi-user |
| Front-FX | `./dev.py test front-fx all` | FX unit + 7 E2E spec files |
| **All** | `./dev.py test all` | Run everything |

- Aggiungere flag `--list` per elenco test
- Aggiungere diagramma mermaid ad albero dei sottosistemi di test
- Aggiornare le sotto-pagine (`external.md`, `db.md`, `services.md`, `utils.md`, `schemas.md`, `api.md`, `e2e.md`) con informazioni aggiornate

### 3.3 Aggiornare `developer/frontend/index.md`

Aggiungere sezione **"Build & Development"** con:
- `front build` — Build produzione
- `front dev` — Dev server con HMR
- `front check` — Lint + type-check

### 3.4 Aggiornare `developer/frontend/i18n.md`

Aggiungere sezione **"i18n Audit CLI"** con:
- `i18n audit` — Audit base
- `--duplicates` — Mostra chiavi duplicate
- `--save-xlsx` — Esporta report Excel

### 3.5 Aggiornare `developer/api/overview.md`

Aggiungere sezione **"API Client Generation"** con:
- `api sync` — Esporta OpenAPI schema + genera TypeScript client

---

## Batch 4 — 🏗️ Developer Manual overview e cross-link

**Stima**: ~15 min

### 4.1 Riscrivere `developer/index.md`

Aggiungere emoji, espandere con sezioni per ogni area:
- Technologies
- Architecture
- Backend
- Frontend
- API
- Testing

Con brevi descrizioni e link. Aggiungere sezione **"Development Workflow"** che menziona `dev.py` e rimanda a `dev-installation.md`.

---

## Batch 5 — 📂 Filesystem deep-dive links (developer)

**Stima**: ~15 min

Le directory descriptions in `admin/filesystem.md` hanno già i link `:material-arrow-right:` verso le pagine developer.

**Verificare** che le pagine target contengano informazioni sufficienti sulla struttura dei dati filesystem:
- `developer/backend/database.md` — Struttura SQLite, WAL mode
- `developer/backend/file-upload.md` — Upload flow, sidecar JSON
- `developer/backend/brim/architecture.md` — Directory uploaded/parsed/failed

Se mancano informazioni, aggiungere sezioni brevi.

---

## Note implementative

### Ordine emoji

Fare il batch 2 (emoji) **dopo** i batch 3-4 per evitare conflitti con le modifiche Developer Manual che toccano gli stessi file.

### Test runner mermaid

Il diagramma ad albero va scritto come `mermaid graph TD` con le categorie test come nodi e le sotto-categorie come foglie.

### Tempo stimato totale

| Batch | Stima |
|-------|-------|
| 1 — Fix immediati | ~10 min |
| 3 — Developer Manual comandi | ~1 ora |
| 4 — Developer index rewrite | ~15 min |
| 2 — Emoji H2/H3/bullet pass | ~2 ore |
| 5 — Verifica filesystem links | ~15 min |
| **Totale** | **~3.5 ore** |

