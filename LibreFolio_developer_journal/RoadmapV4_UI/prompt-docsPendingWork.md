# 📋 Documentazione MkDocs — Lavoro pendente

Stato al 20 Marzo 2026. Elenco chiaro di cosa manca da fare, con riferimenti ai plan sorgente.

---

## ✅ Completato (spostato in `phases/phase-05-subplan/`)

| Plan | Contenuto |
|------|-----------|
| `plan-docsStructuralRefinements.prompt.md` | Merge Architecture+Technologies, split DB schema in 5 file, Test Walkthrough Backend/Frontend, Components select+brokers, rimozione Tutorials |
| `plan-docsComponentRefinements.prompt.md` | Fix gallery settings bug, split UI Base in sotto-file con diagrammi, split Broker diagrams, fix Broker Modals image, 3 Plugin Guide flow diagrams (fasi verticali), Asset Search in Asset Plugin Guide, rename Datapoint Editor |

---

## ⏳ Pendente

### 1. Emoji H2/H3/bullet pass (~2 ore)

**Fonte**: `plan-docsPerfection.prompt.md` → Batch 2

Leggere e aggiungere emoji manualmente ai titoli **H2, H3** e alle **bullet list** in ~80 file `.md`. Le emoji H1 sono già applicate a 68 file. Ogni file va letto, capito, e decorato con emoji tematiche coerenti.

**Aree**:

- `user/` (~13 file): brokers, sharing, files, fx detail pages, chart, signals, measures, data-editor, provider, add-pair, sync, chart-settings, image-crop
- `admin/` (~6 file): index, cli_tools, settings, filesystem, docker_advanced, tailscale
- `developer/` (~30 file): architecture/patterns/database, api, backend (brim/fx/assets), frontend (components, pages, state, i18n, styling), test-walkthrough
- `financial-theory/` (~7 file): index, asset-types, transaction-types, day-count, returns, technical-indicators, synthetic-benchmarks
- `gallery/`, `faq.md`, `credits-legal.md`, `POC_UX/`

### 2. i18n Pipeline MkDocs

**Fonte**: `plan-fxDocumentation.prompt.md` → Fase 3

L'intera infrastruttura di traduzione della documentazione:

1. **Configurare `mkdocs-static-i18n`** in `mkdocs.yml` (dipendenza già nel Pipfile). Lingua default: `en`, alternative: `it`, `fr`, `es`.
2. **Rename file** — Rinominare ~20+ file `.md` traducibili → `.en.md` (sezioni user-facing e admin). Sezioni developer restano solo inglese.
3. **Selettore lingua globale** — Trasformare `gallery-lang-selector.js` in `site-lang-selector.js`, rimuovere check `isGalleryPage()`, renderlo globale.
4. **Aggiornare image loader** — `gallery-img-loader.js` deve leggere lingua da path URL (`/it/`, `/fr/`, `/es/`) oltre che dal selettore gallery.
5. **Traduzioni progressive** — Le traduzioni `.it.md`, `.fr.md`, `.es.md` seguono dopo. Opzioni: manuale, semi-automatico con `./dev.py mkdocs translate`, o pipeline markdown-aware con cache per blocco.


---

## 📋 Plan attivi nella root

| File | Status | Cosa manca |
|------|--------|-----------|
| `plan-docsPerfection.prompt.md` | ⏳ | Solo Batch 2 (emoji H2/H3/bullet su ~80 file) — Batch 1 fix completato ✅ |
| `plan-fxDocumentation.prompt.md` | ⏳ | Solo Fase 3 (i18n Pipeline MkDocs) |
| `plan-frontendDevelopment.prompt.md` | 🟡 | Master plan fasi 4-8 — phase 5 FX in corso |
| `plan-phase05-to-08-upgrade.md` | 🟡 | Roadmap macro fasi 5-8 — phase 5 FX quasi completata |
| `plan-phase7b-filePreview.md` | 📋 | Pianificato per Phase 7.5 (futuro, post-Transactions) |

