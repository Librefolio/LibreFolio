# 📋 Documentazione MkDocs — Lavoro pendente

Stato al 21 Marzo 2026 (aggiornato). Elenco chiaro di cosa manca da fare, con riferimenti ai plan sorgente.

---

## ✅ Completato (spostato in `phases/phase-05-subplan/`)

| Plan | Contenuto |
|------|-----------|
| `plan-docsStructuralRefinements.prompt.md` | Merge Architecture+Technologies, split DB schema in 5 file, Test Walkthrough Backend/Frontend, Components select+brokers, rimozione Tutorials |
| `plan-docsComponentRefinements.prompt.md` | Fix gallery settings bug, split UI Base in sotto-file con diagrammi, split Broker diagrams, fix Broker Modals image, 3 Plugin Guide flow diagrams (fasi verticali), Asset Search in Asset Plugin Guide, rename Datapoint Editor |
| `plan-docsPerfection.prompt.md` | Batch 1 fix bug, Batch 2 emoji H2/H3/bullet su ~80 file, Batch 3-4 Developer Manual comandi+overview, Batch 5 filesystem links |

---

## ⏳ Pendente

### 1. i18n Pipeline MkDocs

**Piano dedicato**: `plan-mkdocsI18nPipeline.prompt.md` (6 step, ~7.5 ore stimate)

Setup completo: `mkdocs-static-i18n` (suffix), Aphra subrepo Poetry, selettore lingua globale con readonly su pagine EN-only, script orchestrazione con cache MD5, integrazione `./dev.py mkdocs translate`.

35 file traducibili (user + admin + financial-theory + gallery + root). `developer/` e `POC_UX/` esclusi (EN-only).

---

## 📋 Plan attivi nella root

| File | Status | Cosa manca |
|------|--------|-----------|
| `plan-mkdocsI18nPipeline.prompt.md` | 📋 | Pipeline completa (6 step) |
| `plan-fxDocumentation.prompt.md` | ⏳ | Fase 3 → ora delegata a `plan-mkdocsI18nPipeline` |
| `plan-frontendDevelopment.prompt.md` | 🟡 | Master plan fasi 4-8 — phase 5 FX in corso |
| `plan-phase05-to-08-upgrade.md` | 🟡 | Roadmap macro fasi 5-8 — phase 5 FX quasi completata |
| `plan-phase7b-filePreview.md` | 📋 | Pianificato per Phase 7.5 (futuro, post-Transactions) |
