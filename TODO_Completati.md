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

---

## 🧹 Rimuovere endpoint `/countries/normalize` ✅

**Data aggiunta**: 8 Giugno 2026
**Data completamento**: 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
Rimosso l'endpoint HTTP morto (feature scartata, vedi voce "Normalizzazione Paese Multilingua" sopra) e i suoi helper diventati orfani:
- `backend/app/api/v1/utilities.py`: rimossa la route `GET /countries/normalize` e la funzione `normalize_country()`
- `backend/app/utils/geo_utils.py`: rimossi `is_region()`/`expand_region()` (usati solo da quell'endpoint) — **mantenuto** `normalize_country_to_iso3()`, ancora in uso interno da `justetf.py`
- `backend/app/schemas/utilities.py`: rimosso `CountryNormalizationResponse`
- Rimossi i test dedicati in `backend/test_scripts/test_api/test_utilities.py`, la classe `TestExpandRegion` in `backend/test_scripts/test_utilities/test_geo_utils.py`, e 4 test e2e in `frontend/e2e/utilities.spec.ts` che chiamavano l'endpoint direttamente
- `./dev.py api sync` rigenerato client FE
- **Non toccato**: `/currencies/normalize` (endpoint diverso, ancora valido) e `test_normalize_country_to_iso3` (testa la funzione sottostante, ancora usata)

### File coinvolti
- `backend/app/api/v1/utilities.py`, `backend/app/schemas/utilities.py`, `backend/app/utils/geo_utils.py`
- `backend/test_scripts/test_api/test_utilities.py`, `backend/test_scripts/test_utilities/test_geo_utils.py`, `frontend/e2e/utilities.spec.ts`

---

## 🧹 Rimuovere `preview_columns` dai plugin BRIM ✅

**Data aggiunta**: 8 Giugno 2026
**Data completamento**: 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
Rimossa la feature mai utilizzata (progettata per la "Staging Modal" v4, superata dal redesign v5 ImportWizard):
- `BRIMPreviewColumn` rimossa da `backend/app/schemas/brim.py`, campo `preview_columns` rimosso da `BRIMPluginInfo`
- Metodo abstract `preview_columns()` rimosso da `backend/app/services/brim_provider.py` (base class + `to_plugin_info()`)
- Implementazione rimossa da tutti gli 11 plugin in `backend/app/services/brim_providers/*.py`
- Test aggiornati: `backend/test_scripts/test_external/test_brim_providers.py` (rimosso `test_preview_columns_baseline` + `_BASELINE_COLUMN_KEYS`), più 2 test stub (`test_brim_provider_base.py`, `test_brim_create_transaction.py`) che implementavano il metodo abstract e non ne avevano più bisogno
- `./dev.py api sync` rigenerato client FE — verificato zero riferimenti residui a `preview_columns`/`BRIMPreviewColumn` in tutto il repo
- 195/195 test BRIM passano

### File coinvolti
- `backend/app/schemas/brim.py`, `backend/app/services/brim_provider.py`
- `backend/app/services/brim_providers/*.py` (11 plugin)
- `backend/test_scripts/test_external/test_brim_providers.py`, `backend/test_scripts/test_services/{test_brim_provider_base,test_brim_create_transaction}.py`

---

## 📸 Gallery: 4 tipi transazione mancanti (WITHDRAWAL/INTEREST/FEE/TAX) ✅

**Data aggiunta**: idea raccolta durante audit TODO del 17 Luglio 2026 (transazioni introdotte dopo la creazione originale della gallery)
**Data completamento**: 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
- `frontend/e2e/gallery.spec.ts`: aggiunti i 4 tipi mancanti a `TX_FORM_VARIANT_TYPES` (loop già generico, zero logica aggiuntiva)
- Carosello transazioni aggiornato nello stesso punto (`carousel-desktop-1`/`carousel-mobile-1`) in tutti gli 8 file `mkdocs_src/docs/gallery/{desktop,mobile}.{en,it,fr,es}.md`, con `data-title` tradotto e `alt` localizzato per lingua (pattern esistente: "Modulo Transazione — X" IT, "Formulaire de Transaction — X" FR, "Formulario de Transacción — X" ES — coerente con le voci già presenti nello stesso carosello)
- 64 nuovi screenshot generati (2 viewport × 4 lingue × 2 temi × 4 tipi) via `./dev.py mkdocs gallery`
- `./dev.py mkdocs build` verificato senza errori

### File coinvolti
- `frontend/e2e/gallery.spec.ts`
- `mkdocs_src/docs/gallery/{desktop,mobile}.{en,it,fr,es}.md`

---

## ⚙️ Default lang/currency/theme da global settings (non più hardcoded) ✅

**Data aggiunta**: idea raccolta durante audit TODO del 17 Luglio 2026 (gap segnalato dall'utente, confermato)
**Data completamento**: 17 Luglio 2026 (lang/currency), stessa giornata estesa al tema su richiesta successiva dell'utente
**Status**: ✅ COMPLETATO

### Completato
`get_or_create_user_settings()` e il ramo "crea se non esiste" di `update_user_settings()` in `backend/app/services/settings_service.py` leggono ora `default_language`/`default_currency`/**`default_theme`** da `GlobalSetting` (via `get_setting_value()`, già esistente in `global_settings_service.py`, che gestisce già il fallback a `GLOBAL_SETTINGS_DEFAULTS`), invece di avere `"en"/"EUR"/"light"` hardcoded come valore primario.

**Aggiunta successiva — Default Theme in admin panel**: inizialmente il tema era stato lasciato fuori scope (nessun default globale equivalente). L'utente ha poi chiesto esplicitamente di aggiungerlo. Scoperto che gran parte del frontend era **già pronto** ma mai completato: `globalSettings.ts` e `PreferencesTab.svelte` leggevano/attendevano già una key `default_theme` dai global settings (sempre no-op perché la key non esisteva lato backend). Completato:
- `GLOBAL_SETTINGS_DEFAULTS["default_theme"]` aggiunto (seed `"auto"`, non `"light"` — scelto per coerenza con il fallback già presente nel codice FE in 2 punti indipendenti)
- Nuovo branch UI in `GlobalSettingsTab.svelte` (categoria "Defaults"), mirror esatto del branch `default_language` esistente, select con le 3 opzioni light/dark/auto (chiavi i18n già esistenti)
- Nuove chiavi i18n `globalSettingNames.default_theme` / `globalSettingDescriptions.default_theme` in 4 lingue
- Ora anche il pulsante "reset to default" del tema nella pagina Preferenze utente (`PreferencesTab.svelte`) funziona realmente (prima era permanentemente no-op)

Aggiunti/estesi test in `test_settings_service.py` (pattern setup/cleanup su `GlobalSetting`): un caso con default globali custom (lang/currency/theme tutti e 3 verificati), uno con i default seedati (fallback a `en`/`EUR`/`auto`). 9/9 test passano, incluso il test pre-esistente `test_creates_settings_when_missing` (nessuna regressione). Verificato anche via e2e (`./dev.py test front-utility settings`, 37/37 pass) e `svelte-check`/`i18n audit` (0 errori, 100% completo).

### File coinvolti
- `backend/app/schemas/settings.py`, `backend/app/services/settings_service.py`
- `backend/test_scripts/test_services/test_settings_service.py`
- `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte`
- `frontend/src/lib/i18n/{en,it,fr,es}.json`

---

## 🤖 AI Export — FX Pair Detail (snapshot + spiegazione trend) ✅

**Data aggiunta**: idea raccolta durante audit TODO del 17 Luglio 2026
**Data completamento**: 17 Luglio 2026
**Status**: ✅ COMPLETATO

### Completato
Aggiunto AI export su `/fx/[pair]`, mirror ridotto (2 varianti) del pattern asset — niente su `/transactions` (deciso, non ha senso per quel dominio):
- `fx_snapshot` (dati puri) e `fx_trend` (spiega perché il tasso si muove in questa direzione, via ricerca su differenziali di tasso/politica monetaria/eventi macro)
- Fotografia dati include **entrambe le direzioni del tasso già calcolate** (`rate_base_to_quote` e `rate_quote_to_base` = `1/rate`, sempre in direzione canonica base→quote, indipendente dal toggle di inversione visuale della pagina) — l'LLM non deve invertire nulla
- Segnali tecnici: EMA(20/50/200) + MACD, **niente RSI** (deciso, dominio senza vero overbought/oversold strutturale) — reso possibile generalizzando `technicalExportBuilder.ts` esistente con un `loadPrices` iniettabile + flag `computeRsi` (default `true`, comportamento asset/portfolio invariato — verificato dopo il refactor con `svelte-check` 0 errori e riletture manuali dei 2 call site esistenti, dato che non esiste test automatico su questi builder)
- Nuovi file mirror di `ai-export/asset/*`: `frontend/src/lib/features/ai-export/fx/{fxTypes,fxPromptCatalog,fxExportBuilder,fxPromptRenderer,fxExportClipboard}.ts`
- Wiring in `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (bottone accanto ai controlli del pannello Segnali, con collasso a icona su schermi stretti come nella pagina asset) + nuove chiavi i18n `fxDetail.aiExportMenu.*` in 4 lingue
- Verificato: `svelte-check` 0 errori, `fx-detail.spec.ts` 12/12 pass (nessuna regressione sul toggle pannello Segnali dopo il refactor del DOM header)

### File coinvolti
- `frontend/src/lib/features/ai-export/technical/technicalExportBuilder.ts` (generalizzato)
- `frontend/src/lib/features/ai-export/asset/assetExportBuilder.ts`, `frontend/src/lib/features/ai-export/aiExportBuilder.ts` (adattati al nuovo builder generico)
- `frontend/src/lib/features/ai-export/fx/*` (nuovo)
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte`
- `frontend/src/lib/i18n/{en,it,fr,es}.json`

---

## 💸 BRIM: FEE/TAX non collegati all'asset — Fase 1 (fix import) ✅

**Data aggiunta**: 17 Luglio 2026 (bug), 18 Luglio 2026 (fix Fase 1)
**Data completamento**: 18 Luglio 2026 (solo Fase 1 — Fase 2 motore FIFO/lotti resta aperta in `TODO_ProssimeAttivita.md`)
**Status**: ✅ Fase 1 COMPLETATA

### Completato

Correzione di un errore dell'audit originale (17/07): riverificando riga-per-riga contro i CSV campione bundled nel repo (`sample_reports/`), il bug reale era più circoscritto dei "7 plugin" documentati:

| Plugin | Verificato | Esito |
|---|---|---|
| Directa | 🐛 confermato (CSV reale utente: `Rit.cedola obb.` con ISIN identico al BUY) | **Fix applicato** |
| Schwab | 🐛 confermato — prova nel sample bundled `schwab-export.csv:105-106` (`ADR Mgmt Fee`/`Foreign Tax Paid`, `Symbol=IBN`) | **Fix applicato** |
| Finpension | ⚠️ FEE strutturalmente di conto, sample bundled con ISIN sempre vuoto | **Fix difensivo** (no-op oggi) |
| Revolut | ⚠️ idem (custody fee, ticker sempre vuoto) | **Fix difensivo** (no-op oggi) |
| eToro | ✅ non era questo bug — "Withdraw Fee"/"Conversion Fee" scartate a monte (`SKIP_TYPES`), mai create come transazione | **Non toccato**, segnalato come bug diverso in `TODO_FUTURI.md` |
| Freetrade | ✅ non era questo bug — nessun tipo FEE/TAX nel mapping | **Non toccato** |
| Trading212 | ✅ non era questo bug — TAX già collegato correttamente (riuso `asset_id` dalla transazione madre) | **Non toccato** |

Pattern di fix: nuova categoria `asset_optional` per FEE/TAX accanto alla `asset_required` esistente — collega l'asset se ISIN/ticker/symbol presente sulla riga, mai skip della riga né placeholder fittizio se il dato è genuinamente assente (fee di conto). Verificato che una versione naive ("aggiungi FEE/TAX ad `asset_required`") avrebbe introdotto un bug peggiore: placeholder fittizio per ogni fee di conto in Directa, transazione **interamente scartata** (non solo non collegata) negli altri plugin con pattern skip-on-missing.

4 nuovi test in `test_brim_providers.py` (`test_directa_parse_sample_links_tax_to_asset`, `test_schwab_parse_sample_links_adr_fee_and_tax_to_asset`, `test_finpension_parse_sample_fee_without_asset_stays_unlinked`, `test_revolut_parse_sample_fee_without_asset_stays_unlinked`), tutti su sample CSV già bundled nel repo (nessuna fixture sintetica necessaria — i sample di Directa e Schwab contenevano già righe reali col bug, semplicemente non testate prima). 199/199 test passano (195 preesistenti + 4 nuovi). Lint/format puliti su tutti i file toccati.

**Fase 2 (integrare il costo nel motore FIFO/lotti) resta aperta**, tracciata come item 0 in `TODO_ProssimeAttivita.md` — rimandata dall'utente a dopo il lavoro principale in corso.

### File coinvolti

- `backend/app/services/brim_providers/{broker_directa,broker_schwab,broker_finpension,broker_revolut}.py`
- `backend/test_scripts/test_external/test_brim_providers.py`
