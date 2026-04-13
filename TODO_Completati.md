# TODO COMPLETATI

Questo file documenta i TODO che sono stati completati durante lo sviluppo di LibreFolio.

---

## 🖼️ File Uploader Image Preview ✅

**Data aggiunta**: 23 Gennaio 2026  
**Data completamento**: 19 Febbraio 2026  
**Status**: ✅ COMPLETATO

### Contesto
Il FileUploader supporta upload multiplo di qualsiasi tipo di file. Per le immagini era necessario:
- Anteprima dell'immagine con crop prima dell'upload
- Resize/crop tramite ImageEditModal (cropperjs v2)
- Pulsante Edit (matita) nella lista file pending per le immagini
- Pulsante Restore per annullare le modifiche

### Implementazione
- Migrato a **cropperjs v2** (Web Components) per crop interattivo con maniglie
- Creato **ImageEditModal** con preset (Avatar 200×200, Icon 64×64, Custom)
- Creato **FileEditModal** per rinominare file non-immagine
- Creato **ImageCropper** con zoom unificato, rotazione, flip, preview ellisse
- Integrato in files page con pulsanti edit/restore nella lista pending
- Output size editabile con scale factor e quality control

### File coinvolti
- `frontend/src/lib/components/ui/media/ImageCropper.svelte`
- `frontend/src/lib/components/ui/media/ImageEditModal.svelte`
- `frontend/src/lib/components/ui/media/FileEditModal.svelte`
- `frontend/src/lib/components/ui/media/FileUploader.svelte`
- `frontend/src/lib/utils/imageCrop.ts`

---

## 🖼️ Image Crop Component ✅

**Data aggiunta**: 22 Gennaio 2026  
**Data completamento**: 20 Febbraio 2026  
**Status**: ✅ COMPLETATO

### Contesto
Implementare crop avanzato per avatar e icone broker.

### Implementazione
Implementato con cropperjs v2 (non svelte-easy-crop come inizialmente pianificato).
Vedi `LibreFolio_developer_journal/RoadmapV4_UI/plan-imageCropModal.prompt.md` per dettagli completi.

---


## 🌐 i18n: Stringhe hardcoded FX/Broker tradotte ✅

**Data aggiunta**: 19 Marzo 2026  
**Data completamento**: 19 Marzo 2026  
**Status**: ✅ COMPLETATO (solo fix stringhe hardcoded puntuali)

### Completato
- Colonne MeasurePanel (`Δ Abs`, `Δ %`, `Δ%/yr`) passate a `$t()`
- Aggiunta chiave `common.dismiss` per FX detail
- Aggiunta chiave `brokers.createdInSystem` per broker detail

### Nota
La pulizia completa delle 146+ chiavi potenzialmente inutilizzate e la razionalizzazione restano in `TODO_FUTURI.md`.

---

## 🧪 FX Testing & Cleanup — Phase 5 Finale 🔍

**Data aggiunta**: 12 Marzo 2026  
**Data implementazione**: 19 Marzo 2026  
**Status**: 🔍 UNDER REVIEW — implementato, da testare step per step

### Contesto
Phase 5 FX Management completata funzionalmente. Necessario cleanup, bug fix, e test coverage.

### Completato
- **Pre-Step 0A**: Eliminato `FxEditSection.svelte` (dead code)
- **Pre-Step 0B**: Spostato `CsvEditor.svelte` in `ui/data-editor/`
- **Pre-Step 0C**: 20 `data-testid` aggiunti nella pagina FX detail
- **Pre-Step 0D**: Eliminato `fx-routes.spec.ts` obsoleto, creato `e2e/fx/fx-helpers.ts`
- **Pre-Step 0E**: Fix bug FxPairSignal — aggiunto `_resolvedData` nella detail page
- **Pre-Step 0F**: Fix bug `annualizedPct` in `MeasureSignal.getMeasurementForSignal()`
- **Step 1**: 27 unit test Vitest (15 TimeSeriesStore + 12 EditBuffer), configurazione Vitest
- **Step 2**: i18n audit, stringhe hardcoded tradotte
- **Steps 3-9**: 7 file E2E spec Playwright creati (list, detail, add-pair, data-editor, sync, api, chart-settings)
- **Step 10**: Registrazione in `dev.py test front` (9 nuove entry: fx-unit, fx-list, fx-detail, fx-add-pair, fx-editor, fx-sync, fx-api, fx-settings, fx)

### Riferimento
Vedi `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-05-subplan/plan-fxTestingCleanup.prompt.md`.

---

## 💾 FX Rate Cache a Livello Core (TTL 5 min) ✅

**Data aggiunta**: 13 Aprile 2026
**Data completamento**: 13 Aprile 2026
**Status**: ✅ COMPLETATO

### Implementazione

- `_fx_fetch_cache = get_ttl_cache("fx_provider_responses", maxsize=200, ttl=300)` in `fx.py`
- Cache key: `(provider_code, frozenset(target_currencies), date_range)`
- Cache hit → skip fetch provider; cache miss → fetch + store
- Cleanup automatico via `close_all_caches()` nel lifespan shutdown

### Riferimento
Vedi `plan-partCCurrencyConversion.prompt.md` § C15c.

---

## 📁 Upload Metadata Cache TTL 1h ✅

**Data aggiunta**: 13 Aprile 2026
**Data completamento**: 13 Aprile 2026
**Status**: ✅ COMPLETATO

### Implementazione

- `_upload_meta_cache = get_ttl_cache("upload_metadata", maxsize=500, ttl=3600)` in `static_uploads.py`
- `_load_metadata()` → check cache → disco se miss
- `_save_metadata()` → aggiorna cache dopo scrittura
- `delete_upload()` → invalida entry cache

### Riferimento
Vedi `plan-partCCurrencyConversion.prompt.md` § C15d.

---

## 🔄 Fallback Sync per Global Settings ❄️

**Data aggiunta**: 13 Aprile 2026
**Status**: ❄️ SCARTATO
**Nota**: Le funzioni sync `get_session_ttl_hours_sync()`, `get_max_upload_mb_sync()`, `is_registration_enabled_sync()` erano fallback mai usati. Rimosse in C14a. Ricreazione banale se necessario: leggono `GLOBAL_SETTINGS_DEFAULTS[key]["value"]`.

---
