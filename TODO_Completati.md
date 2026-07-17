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

## 🌐 Ripulire tutte le traduzioni non usate (i18n) ✅

**Data aggiunta**: Marzo 2026  
**Data completamento**: 20 Marzo 2026 (prima passata), 15 Aprile 2026 (consolidamento duplicati)  
**Status**: ✅ COMPLETATO

### Completato
- **Prima passata** (Phase 5 Step 9): 724→590 chiavi, 0 inutilizzate, 100% coverage 4 lingue, ~20 duplicati residui intenzionali
- **Seconda passata** (Phase 6 Step 6): 875→825 chiavi, 22 unused rimossi, 50 duplicati consolidati sotto `common.*`, 42 gruppi duplicati accettati con rationale documentato

### Riferimenti
- `plan-fxTestingCleanup.prompt.md` Step 9
- `plan-phase06Step6-i18n-dedup.prompt.md`
- `knowledge_base/08_i18n_duplicates.md`

---

## 🕐 Late interest con generate_interest ✅

**Data aggiunta**: 3 Aprile 2026 (Round 12 Finale)  
**Data completamento**: 3 Aprile 2026  
**Status**: ✅ COMPLETATO

### Completato
Il late interest ora supporta `generate_interest=True`. Genera INTEREST periodici + MATURITY_SETTLEMENT finale.
Il late interest NON è una "opportunità" ma una penale — tuttavia il flag unifica il pattern: l'utente decide se auto-generare eventi o meno, indipendentemente dalla natura del tasso.
Se l'utente non vuole auto-generare eventi di penale, lascia `generate_interest=False` sul late interest e usa eventi manuali.

---

## 🔗 Phase 7 — Collegamento AssetEvent → Transaction ✅

**Data aggiunta**: 3 Aprile 2026 (Round 12 Finale)
**Data completamento**: Maggio 2026 (SP-A, Phase 7 Part 4)
**Status**: ✅ COMPLETATO (infrastruttura)

### Completato

- `asset_event_id: Optional[int]` FK su `Transaction` model (DB + Alembic)
- Index `idx_transactions_asset_event` per lookup veloce
- Schema `TXCreateItem.asset_event_id` con validazione (`> 0`)
- FormModal: campo numerico + bottone unlink per `asset_event_id` (visibile solo quando `eventLinkable`)
- Logic di reset: se tipo TX cambia a non-event-linkable → `asset_event_id = null`

### Nota

L'infrastruttura è completa. Resta da fare il **picker modale** per selezionare eventi in modo user-friendly (Step 14 di SP-D, piano separato). La modale "cambio provider con eventi collegati" (`AssetCurrencyChangeModal`) è già implementata.

---

## 💱 FX Page — Grafico e Priorità Provider ✅

**Data aggiunta**: 20 Febbraio 2026  
**Data completamento**: 17 Aprile 2026 (Phase 5 + Phase 9)  
**Status**: ✅ COMPLETATO

### Completato
- Grafico ECharts interattivo con Data Editor (click-to-edit punti)
- Gestione provider con priorità e route (direct + chain), modal di configurazione
- Sync con progress modal (singola coppia e Sync All)
- Segnali tecnici overlay (EMA, MACD, RSI, Bollinger Bands)
- Pannello misure con tabella riepilogativa
- Add Pair modal con route discovery (direct + chain)
- Chart settings modal per personalizzazione grafico
- CSV import/export dati
- Multi-lingua (EN/IT/FR/ES) completa

---

## 📱 Mobile Column Reorder (DataTable) ✅

**Data aggiunta**: 23 Gennaio 2026
**Data completamento**: ~Maggio 2026
**Status**: ✅ COMPLETATO

### Contesto
Il riordinamento colonne nella DataTable su mobile era limitato (no drag & drop touch).

### Soluzione
Implementati bottoni freccia su/giù come controllo alternativo al drag & drop desktop. Il riordinamento funziona correttamente su dispositivi touch. Non è stato necessario implementare touch drag nativo.

---

## 🔗 Multi-Merge Promote Suggest ✅

**Data aggiunta**: 14 Maggio 2026
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
Il backend gestisce già suggerimenti multipli per TX standalone: `promote_suggest_bulk` in `transaction_service.py` ritorna `results: Dict[int, List[TXPromoteSuggestCandidate]]`. Il frontend mostra la lista multipla nel banner (`TransactionBulkModal.svelte`, `promote-suggest-item-{idx}`), già permettendo la scelta tra più candidati N-way come richiesto dal TODO originale.

---

## 📊 Aggiornamento Automatico Prezzi/FX — Dialog, Warning, Progress ✅

**Data aggiunta**: 20 Febbraio 2026
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
- `SyncModalBase.svelte` mostra già il range `dateStart → dateEnd`, conteggio elementi, e progress bar (% basata su timeout stimato)
- Il range di sync è legato al **date-range selector della pagina** (preset 1M/3M/1Y/MAX già esistente sul grafico) invece di un picker dedicato dentro la modale — stessa funzionalità, UX più unificata (nessun controllo duplicato)
- Warning/descrizione dell'operazione passata via prop `description` alla modale
- Modali dedicate per asset (`AssetSyncModal.svelte`) e per pagina (`PageSyncModal.svelte`)

---

## 🔒 TransactionPicker — Filter Inaccessible Paired TX (W4a) ✅

**Data aggiunta**: 1 Giugno 2026
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
`TransactionPickerModal.svelte` calcola già `disabledIds` e disabilita le TX con partner su broker non accessibile, usando `partner_broker_id` come fallback (righe 45-73).

---

## 🔄 FormModal Items Array Refactor (Step 8/10) ✅

**Data aggiunta**: 1 Giugno 2026
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
`TransactionFormModal.svelte` usa già il prop unificato `items: FormModalItems | null` al posto di `initialRow` + `injectedPartnerRow`. `resolveFormItems.ts` è integrato e usato da `/transactions/+page.svelte` (`resolveFormItemsForView`).

---

## 🏷️ Centralizzazione Emoji Settori nel Backend ✅

**Data aggiunta**: 11 Giugno 2026
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
- Endpoint `GET /api/v1/utilities/sectors` ritorna già oggetti strutturati `{key, emoji}` (`utilities.py:94-152`)
- `sectorStore.ts` centralizza il mapping (`getSectorEmoji()`), con una mappa hardcoded usata solo come **fallback difensivo** transitorio, non come secondo sistema parallelo
- `en.json` non contiene più emoji nelle stringhe di traduzione dei settori (es. `"Technology": "Technology"` — verificato: nessuna emoji embedded nel resto del frontend fuori da `sectorStore.ts`)
- Single source of truth raggiunta come richiesto

---

## 🌍 Normalizzazione Paese Multilingua (endpoint user-facing) ❄️

**Data aggiunta**: 13 Aprile 2026
**Data valutazione**: 17 Luglio 2026
**Status**: ❄️ SCARTATO — superato da un approccio diverso

### Nota
Il TODO proponeva di estendere `normalize_country_to_iso3()` (free-text, un paese alla volta, solo EN/ISO) con un parametro `language`. Il frontend ha invece preso una strada diversa e migliore: `GET /api/v1/utilities/countries?language=XX` restituisce l'**intera lista paesi già localizzata via Python Babel** (`geo_utils.py:253`, `translation_utils.py: get_babel_locale`), consumata da `countryStore.ts` + `CountrySearchSelect.svelte` per la ricerca client-side in qualsiasi lingua supportata (Babel copre 1067+ locale). L'endpoint `/countries/normalize` esiste ancora ma **non è più chiamato da nessuna UI** (unico uso reale rimasto: `justetf.py`, parsing lato server di nomi paese in inglese, dove il multilingua non serve). Bisogno originale pienamente soddisfatto, ma con un meccanismo diverso da quello ipotizzato nel TODO.

**Follow-up**: rimuovere l'endpoint HTTP ora morto → task di cleanup tracciato in `TODO_ProssimeAttivita.md`.

---

## 📊 "Quadrettoni" — Treemap Allocazione % (Dashboard) ✅

**Data aggiunta**: idea raccolta 20 Febbraio 2026 nel blocco "Aree di miglioramento dopo aver visto competitor" di `TODO_FUTURI.md`
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
La richiesta era: tab in dashboard/broker che mostrino l'allocazione percentuale con una visualizzazione "a quadrettoni". Già implementato: `ExposureTreemap.svelte` in Dashboard (usa `echartsTreemapZoomGuard.ts` per il comportamento zoom/pan). Non ancora verificato se replicato anche lato singolo broker — se serve, è un'estensione separata, non un TODO residuo di questa voce.

---

## 📊 AssetEvent: Dividendi/Eventi da Provider Esterni — marker sul grafico ✅

**Data aggiunta**: 1 Aprile 2026
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026 (correzione di un mio errore di verifica precedente)
**Status**: ✅ COMPLETATO

### Completato
Tutte le richieste del TODO originale sono soddisfatte:
- `yahoo_finance.py` (righe 348-420) e `justetf.py` (righe 369-390) leggono già dividendi/split e li ritornano come eventi
- **Marker sul grafico prezzi asset**: implementato in `frontend/src/routes/(app)/assets/[id]/+page.svelte` — fetch con `include_events: true` (riga 953), `chartEventMarkers` derivato (righe 615-670, con gestione FX/conversione e overlay eventi degli asset di confronto), passato come prop `eventMarkers` a `PriceChartFull.svelte` (riga 1780; consumato alle righe 111/163/582/700/891+ con tooltip dedicato)

**Nota per prossime verifiche**: il prop si chiama `eventMarkers`/`EventMarker[]`, non contiene la stringa letterale "AssetEvent" — un semplice grep su "AssetEvent" nel componente chart dà un falso negativo (errore fatto in un audit precedente, poi corretto su segnalazione dell'utente che ricordava di averci lavorato).

Il flag `supports_events` sulla base class `AssetSourceProvider` non è mai stato implementato — risulta non necessario, il flusso funziona comunque end-to-end senza di esso.

---

## 📚 Documentazione Per-Plugin FX Provider ✅

**Data aggiunta**: 15 Marzo 2026
**Data completamento**: non tracciata — rilevato già presente durante audit TODO del 17 Luglio 2026 (2° errore di verifica corretto su segnalazione utente)
**Status**: ✅ COMPLETATO — anche oltre lo scope richiesto

### Completato
Il TODO chiedeva solo pagine developer-facing. Trovato invece un lavoro completo (commit `b3729df4 feat(fx): enhance provider testing and expand documentation`):
- `mkdocs_src/docs/developer/backend/fx/providers/{ecb,fed,boe,snb,index}.md` — pagine dev dedicate per provider
- `mkdocs_src/docs/user/fx/providers/{ecb,fed,boe,snb,index}.{en,it,fr,es}.md` — **pagine anche user-facing, in tutte le 4 lingue** (non richiesto esplicitamente dal TODO, ma coerente con lo spirito)
- `docs_url` di ogni provider (`backend/app/services/fx_providers/{ecb,fed,boe,snb}.py`) punta già alla pagina specifica (es. `ecb.py:60`: `"/mkdocs/user/fx/providers/ecb/"`), non alla pagina generica — verificato

**Nota**: nel mio audit del 17/07 avevo controllato solo `developer/backend/fx/` di primo livello (trovando solo `architecture.md`/`configuration.md`) senza scendere nella sottocartella `providers/` — errore mio, corretto su segnalazione dell'utente.
