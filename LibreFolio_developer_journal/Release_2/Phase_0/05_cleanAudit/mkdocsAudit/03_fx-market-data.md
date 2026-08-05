# 03 — FX e market data

> **Release 2 · Phase 0 · 05_cleanAudit / mkdocsAudit**
>
> Baseline: [00_BASELINE](00_BASELINE.md) — commit `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103`,
> branch `dev_release2`, worktree dirty (elenco invariato rispetto al manifest).
> Modalità: sola lettura. Nessuna correzione applicata a codice, documentazione,
> config o indice centrale.

## Scope assegnato (15 pagine EN pubblicate)

- `user/fx/index.en.md`, `sync.en.md`, `add-pair.en.md`, `chart-settings.en.md` (4)
- `user/fx/detail/{index,chart,data-editor,measures,signals,provider}.en.md` (6)
- `user/fx/providers/{index,ecb,fed,boe,snb}.en.md` (5)

Esclusi per mandato: guida developer (`developer/backend/fx/*`,
`developer/frontend/fx-chain-algorithm.md`, solo linkati, mai aperti come target di
verifica), traduzioni IT/FR/ES, altre aree utente, admin, teoria finanziaria,
community, gallery.

## Codice/sorgenti confrontati

- API: `backend/app/api/v1/fx.py` (tutti gli endpoint: `/fx/providers`,
  `/fx/providers/routes` GET/POST/DELETE, `/fx/currencies/sync`, `/rate` POST/DELETE,
  `/convert`, `/signals`), `backend/app/schemas/fx.py`
- Servizi: `backend/app/services/fx.py` (`ensure_rates_multi_source`,
  `sync_pairs_bulk`, `compute_chain_rate`, `upsert_rates_bulk`, `delete_rates_bulk`)
- Provider: `backend/app/services/fx_providers/{ecb,fed,boe,snb,manual,mockfx}.py`,
  `backend/app/services/provider_registry.py`
- DB: `FxRate`, `FxConversionRoute` (upsert on-conflict, priorità, chain_steps JSON)
- Frontend: rotte `frontend/src/routes/(app)/fx/{+page.svelte,[pair]/+page.svelte}`;
  componenti `frontend/src/lib/components/fx/*.svelte`,
  `frontend/src/lib/components/ui/select/FxProviderSelect.svelte`,
  `frontend/src/lib/components/table/DataTable.svelte`,
  `frontend/src/lib/components/ui/{OrderableList,ViewModeToggle}.svelte`,
  `frontend/src/lib/components/ui/date/DateRangePicker.svelte`; store
  `frontend/src/lib/stores/{chartSettingsStore.svelte.ts,dateRangeStore.svelte.ts,
  fxStoreRegistry.ts,currencyGraphStore.ts}`; grafo rotte
  `frontend/src/lib/utils/currency/currencyGraph.ts`; segnali
  `frontend/src/lib/charts/signals/MeasureSignal.ts`; catalogo AI Export
  `frontend/src/lib/features/ai-export/catalog/shared.ts`,
  `frontend/src/lib/i18n/en.json`
- Test: `backend/test_scripts/test_api/test_fx_{api,api_unit,sync,compress_errors,
  signals_api}.py`, `backend/test_scripts/test_services/test_fx_{core,conversion,
  sync_service}.py`, `backend/test_scripts/test_external/test_fx_providers.py`,
  `backend/test_scripts/test_db/test_fx_rates_persistence.py`,
  `frontend/e2e/fx/*.spec.ts`, `frontend/src/lib/stores/__tests__/
  fxStoreRegistry.test.ts`
- Verifica esterna live (sola lettura, nessuna scrittura): chiamata diretta alle API
  pubbliche ECB (`data-api.ecb.europa.eu`) e SNB (`data.snb.ch`) per contare le valute
  realmente supportate a oggi, a supporto/confutazione dei numeri dichiarati nelle
  pagine provider.

## Sintesi

Il gruppo FX (15/15 pagine coperte) è la parte più fedele al codice fra i comparti
finora auditati per struttura di navigazione, routing diretto/a catena, fallback fra
provider, comportamento di sync ("provider autoritativo", overwrite, MANUAL sentinel),
formula CAGR delle Measure e riordino provider (drag&drop + frecce). Tuttavia sono
emersi **6 reperti**, di cui **1 critical**, **3 major** e **2 minor**, concentrati
su tre pagine (`providers/snb.en.md`, `chart-settings.en.md`,
`detail/data-editor.en.md`, `detail/signals.en.md`) più due minori distribuiti
(`index.en.md`, `detail/chart.en.md`).

Il reperto più grave (**F1**, critical) è la pagina `providers/snb.en.md`, che
dichiara **tre volte** ("Current Price: updated daily", "History: Historical daily
rates", "Update Frequency: Daily on Swiss business days") una granularità che il
provider non fornisce: il codice, la stringa `description_i18n` mostrata in-app e
persino il `warning_i18n` esplicito confermano che la SNB pubblica **solo medie
mensili**, assegnate al giorno 1 del mese, e che le catene di conversione che passano
per SNB producono un tasso composito solo nei giorni in cui *tutti* i leg hanno dati —
cioè, in pratica, una volta al mese. Un utente che segua solo la pagina utente non ha
alcun modo di scoprirlo se non aprendo il modale di selezione provider (dove il
warning compare) o leggendo il codice.

Gli altri due major (**F2**, `chart-settings.en.md`; **F3**,
`detail/data-editor.en.md`) descrivono comportamenti di persistenza/validazione
protettivi che **non esistono nel codice attuale**: le impostazioni grafico sono
tenute in memoria di sessione (perse al refresh, non in `localStorage`), e
l'importazione CSV non verifica affatto che le valute dell'header combacino con la
coppia della pagina — lo scenario "fallirà" descritto nell'esempio della pagina non
si verifica: i dati vengono importati silenziosamente con l'etichetta della pagina,
senza inversione né errore. Il quarto reperto (**F4**, `detail/signals.en.md`)
documenta tre task AI Export FX quando il catalogo reale ne contiene solo due, con
nomi diversi.

I due minori (**F5**, `index.en.md`, azioni del menu contestuale; **F6**,
`detail/chart.en.md`, preset di intervallo temporale incompleti) sono imprecisioni
senza rischio dati ma con potenziale confusione UI.

---

## Copertura per pagina

| # | Pagina | Esito | Reperti |
|---|---|---|---|
| 1 | `fx/index.en.md` | ⚠️ Un reperto (menu contestuale) | F5 |
| 2 | `fx/sync.en.md` | ✅ Verificata, nessun reperto | — |
| 3 | `fx/add-pair.en.md` | ✅ Verificata, nessun reperto | — |
| 4 | `fx/chart-settings.en.md` | ❌ Claim di persistenza non veritiera | F2 |
| 5 | `fx/detail/index.en.md` | ✅ Verificata, nessun reperto | — |
| 6 | `fx/detail/chart.en.md` | ⚠️ Preset di intervallo incompleti | F6 |
| 7 | `fx/detail/data-editor.en.md` | ❌ Validazione documentata assente | F3 |
| 8 | `fx/detail/measures.en.md` | ✅ Verificata, nessun reperto | — |
| 9 | `fx/detail/signals.en.md` | ❌ Task AI Export non corrispondenti | F4 |
| 10 | `fx/detail/provider.en.md` | ✅ Verificata, nessun reperto | — |
| 11 | `fx/providers/index.en.md` | ✅ Verificata, nessun reperto | — |
| 12 | `fx/providers/ecb.en.md` | ✅ Verificata (nota informativa incrociata, vedi F1‑nota) | — |
| 13 | `fx/providers/fed.en.md` | ✅ Verificata, nessun reperto | — |
| 14 | `fx/providers/boe.en.md` | ✅ Verificata (nota informativa incrociata, vedi F1‑nota) | — |
| 15 | `fx/providers/snb.en.md` | ❌ Contraddizione critica su frequenza dati | F1 |

---

## Reperti

### 🔴 F1 — `providers/snb.en.md` dichiara dati "daily" mentre il provider SNB fornisce solo medie **mensili**

**Dove**: `mkdocs_src/docs/user/fx/providers/snb.en.md:3,7,8,14`:

> "The Swiss National Bank (SNB) provider publishes **daily** exchange rates..."
> "✅ **Current Price**: Reference rate updated **daily**"
> "✅ **History**: Historical **daily** rates"
> "**Update Frequency**: Daily on Swiss business days"

**Controprova nel codice** — `backend/app/services/fx_providers/snb.py`:

- `snb.py:5-8` (docstring modulo): *"SNB provides **monthly** average rates ... Dataset:
  `devkum` — monthly exchange rates (**no daily dataset available from SNB API**).
  Each data point represents a monthly average. We assign it to the 1st of the
  month."*
- `snb.py:60,64-66,72`: *"Provides **monthly** exchange rates... SNB does NOT offer a
  daily-rate API... Update frequency: **Monthly** (published around 2nd business day
  of next month)"*
- `snb.py:112`: `description` = `"Monthly average exchange rates from Swiss National
  Bank (**no daily data available**)"`
- `snb.py:115-122` (`description_i18n`, **mostrato in-app**): *"Swiss National Bank —
  publishes **monthly average** exchange rates for ~25 currencies against CHF.
  Updated around the 2nd business day of the following month. **One data point per
  month (⚠️ no daily data)**."*
- `snb.py:124-131` (`warning_i18n`, **mostrato in-app**): *"SNB provides only monthly
  averages (one value per month, on the 1st). In conversion chains, rates are
  computed only on dates where ALL providers have data — days without SNB data will
  have no chain rate."*
- Effetto sulle catene di conversione: `backend/app/services/fx.py:671-705`
  (`compute_chain_rate`) richiede un match esatto di data su **tutti** i leg
  (`leg_rates.get(key)`, ritorna `None` se un leg manca); combinato con SNB che
  fornisce un solo punto al mese, una catena con un leg SNB produce quindi un tasso
  composito **al massimo una volta al mese**, non giornaliero.
- Il warning è realmente visibile all'utente: `frontend/src/lib/components/ui/select/
  FxProviderSelect.svelte:349` (`getProviderDescription`) e `:368`
  (`getProviderWarning`) leggono `description_i18n`/`warning_i18n` dalla stessa
  risposta API (`GET /fx/providers`, `backend/app/schemas/fx.py` →
  `FXProviderInfo.description_i18n/warning_i18n`) e li mostrano nel modale di
  selezione provider (Add Pair / Provider Config) — lo stesso flusso descritto nelle
  pagine `add-pair.en.md` e `detail/provider.en.md`.
- Copertura valute: verifica live di `GET https://data.snb.ch/api/cube/devkum/
  dimensions/en` (5 agosto 2026) conferma **25 valute** mappate (EUR, GBP, DKK, NOK,
  CZK, HUF, PLN, RUB, SEK, TRY, USD, CAD, ARS, BRL, MXN, ZAR, JPY, AUD, CNY, HKD, KRW,
  MYR, NZD, SGD, THB), contro le **10** elencate nella pagina (`snb.en.md`, sezione
  "💰 Supported Currencies"). Questo secondo scarto è un'omissione di copertura, non
  una contraddizione (il documento non nega le altre 15 valute), quindi resta
  raggruppato qui come nota di dettaglio e non come reperto separato.

**Classificazione**: Contraddizione. **Gravità**: **critical** — la pagina descrive
esattamente il comportamento opposto sulla caratteristica più rilevante del provider
(frequenza/dati giornalieri vs mensili); un utente che scelga SNB come provider
primario per un uso quotidiano/di trading a breve termine si troverebbe con un solo
punto dato al mese (assegnato al giorno 1), un rischio concreto di decisioni basate su
aspettative di dati sbagliate, aggravato dall'effetto a cascata sulle catene di
conversione che attraversano SNB. **Confidenza**: alta — tre fonti indipendenti nello
stesso file (docstring, `description`, `description_i18n`) più il `warning_i18n`
mostrato in-app concordano tutte su "monthly, no daily data".

**Direzione di correzione suggerita**: riscrivere `snb.en.md` sostituendo ogni
occorrenza di "daily" con "monthly (one data point per month, assigned to the 1st)";
aggiungere un callout `!!! warning` equivalente al `warning_i18n` già presente in-app,
inclusa la nota sulle catene di conversione; aggiornare l'elenco valute a ~25 o
rimuovere il numero fisso a favore di un rimando dinamico (come già fatto per ECB/
FED/BOE con "~N").

---

### 🔴 F2 — `chart-settings.en.md` dichiara persistenza in `localStorage` che sopravvive alla chiusura del browser; il codice tiene le impostazioni solo in memoria di sessione

**Dove**: `mkdocs_src/docs/user/fx/chart-settings.en.md:65,67` (sezione "💾
Persistence"):

> "Chart settings are stored locally in your browser's `localStorage` and apply
> across all currency pairs. They survive across sessions — even after closing and
> reopening the browser — and will only be lost if you clear your browser cache/
> storage or if the storage expires (browser-dependent, typically months to years)."

**Controprova nel codice** — `frontend/src/lib/stores/chartSettingsStore.svelte.ts`:

- `chartSettingsStore.svelte.ts:2`: *"Chart Settings Store — **Session-level cache**
  for chart aesthetics and signal configs."*
- `chartSettingsStore.svelte.ts:9`: *"**NOT persisted to backend** — session-lifetime
  only (**lost on browser refresh**)."*
- `chartSettingsStore.svelte.ts:64-65`: lo stato è tenuto in variabili di modulo
  JavaScript (`let globalSettings = deepClone(DEFAULT_CHART_SETTINGS)`,
  `let pairOverrides = new Map()`), **non** in `localStorage`/`sessionStorage`.
- Ricerca mirata: `grep -n "localStorage" frontend/src/lib/stores/
  chartSettingsStore.svelte.ts` e `frontend/src/lib/components/charts/
  ChartSettingsModal.svelte` → **nessun risultato** in entrambi i file; nessun altro
  file nel repository referenzia `chartSettingsStore` per una persistenza aggiuntiva
  (`grep -rln "chartSettingsStore" frontend/src/lib` → solo `ChartSignal.ts`,
  `chartUtils.ts`, il file stesso).
- Per contrasto, la persistenza `localStorage` dichiarata in `fx/index.en.md:18` per
  il toggle Grid/Table **è invece reale**:
  `frontend/src/lib/components/ui/ViewModeToggle.svelte:2` ("Reusable grid/list
  toggle with **per-user localStorage persistence**"), usato da
  `frontend/src/routes/(app)/fx/+page.svelte:925`
  (`<ViewModeToggle bind:mode={viewMode} storageKey="fxViewMode" />`) — a conferma che
  il meccanismo `localStorage` esiste davvero nel progetto per altre impostazioni,
  ma non per Chart Settings.

**Classificazione**: Contraddizione. **Gravità**: major — l'utente che personalizza
colori, spessore linea, overlay segnali si aspetta (per esplicita promessa della
pagina) che le impostazioni sopravvivano alla chiusura del browser "per mesi o anni";
in realtà le perde al primo refresh della pagina, il che è un'esperienza
significativamente peggiore di quella promessa e può portare a segnalazioni di bug
verso l'utente finale o il supporto. **Confidenza**: alta — commento esplicito nel
codice sorgente conferma il comportamento contrario punto per punto.

**Direzione di correzione suggerita**: riscrivere la sezione "💾 Persistence"
descrivendo il comportamento reale (cache di sessione, sia globale sia per singola
coppia con "pair override", persa al refresh/nuova sessione), oppure — se si
preferisce mantenere la promessa UX della pagina — implementare realmente la
persistenza `localStorage` nello store (decisione di prodotto, non di
documentazione).

---

### 🔴 F3 — `detail/data-editor.en.md` descrive una validazione "Header currencies don't match" che non esiste; l'header CSV con valute diverse dalla pagina viene importato silenziosamente

**Dove**: `mkdocs_src/docs/user/fx/detail/data-editor.en.md:126-134` (esempio "❌
Invalid File") e `:140` (tabella errori comuni):

```csv
date;GBP>JPY
2024-01-02;188.45
```

> "This will fail if you're on the EUR/USD page — the header currencies must match
> the page's pair."

> | **"Header currencies don't match"** | Header has currencies not on this page |
> Check the pair and fix the header |

**Controprova nel codice** — flusso `FxDataImportModal.svelte` → `FxDataEditorSection.
svelte`:

- `frontend/src/lib/components/fx/FxDataImportModal.svelte:132-158`
  (`handleCsvTextChange`): analizza l'header CSV con le regex
  `/^([A-Za-z]{3})\s*<\s*([A-Za-z]{3})$/` e `/^([A-Za-z]{3})\s*>\s*([A-Za-z]{3})$/` e
  imposta **incondizionatamente** `directionFrom`/`directionTo` (righe 147-148,
  156-157) alle valute lette dall'header — **qualunque esse siano**, senza mai
  confrontarle con le prop `displayBase`/`displayQuote` (le valute reali della
  pagina). Non esiste nel file alcuna chiamata di validazione né alcun messaggio
  "don't match"/"mismatch" (`grep -rn "does not match|doesn't match|don't match|
  mismatch" frontend/src/lib/components/fx frontend/src/lib/components/ui/data-editor`
  → nessun risultato pertinente).
- `frontend/src/lib/components/fx/FxDataEditorSection.svelte:296`: il chiamante
  calcola `const needsInversion = direction.from === quote && direction.to === base;`
  — se l'header dichiara una coppia estranea alla pagina (es. `GBP>JPY` su una pagina
  EUR/USD), questa condizione è semplicemente `false` (né uguale a `base→quote` né a
  `quote→base`), quindi **non scatta l'inversione** — ma non scatta nemmeno alcun
  rifiuto: i valori vengono comunque mappati e passati a `onimport(mapped)` (riga
  304) come se fossero tassi EUR→USD, senza alcun errore visibile all'utente.
- Il validatore generico riga-per-riga, `frontend/src/lib/components/ui/data-editor/
  CsvEditor.svelte`, valida solo formato data (`:291`, `Invalid date format: "..."
  Use YYYY-MM-DD`), valori numerici (`:318`, `Invalid number in "..."`) e date
  duplicate (`:352-353`, `Duplicate date: ${date}` — singolare, non "Duplicate
  dates" come nella tabella errori della pagina) — **nessuna verifica di
  corrispondenza valuta/pagina** in nessun punto della pipeline.
- Confermato anche a livello di test: `frontend/e2e/fx/fx-csv-import.spec.ts` non
  contiene alcun test per lo scenario "header currencies don't match" (`grep -n
  "match|mismatch|GBP|currency" fx-csv-import.spec.ts` → solo asserzioni su
  "initial header matches pair direction" e "swap updates readonly currency badges",
  nessun test negativo sul mismatch).

**Classificazione**: Contraddizione (comportamento descritto non implementato) più
Limite non documentato (il rischio reale — importazione silenziosa di dati con
etichetta di valuta sbagliata — non è menzionato da nessuna parte). **Gravità**:
major — un utente che segua l'esempio della pagina si aspetta un rifiuto plateale;
nella realtà, se incolla per errore un CSV con intestazione di un'altra coppia (es.
copia/incolla da un altro file), i valori numerici vengono silenziosamente salvati
come se fossero la coppia corrente, senza alcuna inversione né avviso — un rischio
concreto di corruzione dati con nessun segnale visibile finché l'utente non nota
valori di cambio implausibili. **Confidenza**: alta — verificato leggendo l'intera
pipeline (modale FX → editor generico → CSV parser) senza trovare alcuna verifica di
corrispondenza valuta, confermato dall'assenza di test dedicati.

**Direzione di correzione suggerita**: o (a) implementare realmente la validazione
descritta — confrontare le valute rilevate nell'header con `displayBase`/
`displayQuote` e mostrare un errore bloccante prima di abilitare "Import" — oppure (b)
se si preferisce mantenere il comportamento attuale (header come override esplicito
della direzione, utile per import legittimi con export da altri sistemi), riscrivere
la pagina rimuovendo la promessa di rifiuto e spiegando invece che l'header determina
sempre la direzione effettiva di importazione, con l'avvertenza di controllarla nella
barra direzione prima di salvare.

---

### 🔴 F4 — `detail/signals.en.md` documenta tre task AI Export FX; il catalogo reale ne contiene solo due, con nomi diversi

**Dove**: `mkdocs_src/docs/user/fx/detail/signals.en.md:49-56`:

> "The **AI Export** (:material-brain:) button in the page toolbar offers three FX
> tasks:
> - **FX Trend Review**
> - **FX Exposure Impact**
> - **FX Conversion Timing Context**"

**Controprova nel codice** — `frontend/src/lib/features/ai-export/catalog/
shared.ts:191-206` (unica sorgente del catalogo pubblico AI Export, gruppo
`analysis`, `domain: 'fx'`):

```ts
{ group: 'analysis', id: 'fx.pair_analysis', domain: 'fx', ... },
{ group: 'analysis', id: 'fx.exposure_impact', domain: 'fx', ... },
```

Solo **due** voci esistono per il dominio `fx` nel gruppo `analysis` (verificato
anche filtrando l'intero array con `AI_EXPORT_ANALYSIS_IDS` derivato dallo stesso
file, righe 208-209). I nomi visualizzati (`frontend/src/lib/i18n/en.json`, chiavi
`aiExport.analysis.fx.pair_analysis.display` = **"FX Pair Analysis"** e
`aiExport.analysis.fx.exposure_impact.display` = **"FX Exposure Impact"**) non
comprendono né "FX Trend Review" né "FX Conversion Timing Context" — quest'ultimo
task non esiste in alcuna forma nel catalogo attuale. Il pulsante AI Export nel
toolbar della pagina di dettaglio è invece reale e correttamente cablato
(`frontend/src/routes/(app)/fx/[pair]/+page.svelte:71-75,200-204,746-759`, import di
`AiExportMenu`, `aiExportCatalogLoader`, gestori `handleFxAiExport`/
`loadFxAiExportCompatibility`).

**Classificazione**: Contraddizione (elenco funzionalità inesatto). **Gravità**:
major — un utente che cerca "FX Conversion Timing Context" o "FX Trend Review" nel
menu AI Export non li troverà mai; il secondo dei due task reali ("FX Exposure
Impact") è correttamente documentato, ma il nome dell'altro e il conteggio totale
sono entrambi sbagliati. **Confidenza**: alta — verificato sull'unica sorgente del
catalogo pubblico più le stringhe i18n effettivamente mostrate in UI.

**Direzione di correzione suggerita**: allineare l'elenco a "FX Pair Analysis" e "FX
Exposure Impact" (due voci, non tre), rimuovendo "FX Trend Review" e "FX Conversion
Timing Context" a meno che non siano funzionalità pianificate — nel qual caso
andrebbero marcate esplicitamente come "in arrivo" per non generare aspettative
premature.

---

### 🟢 F5 — `index.en.md`: il menu contestuale della tabella FX offre "Swap, Sync, Refresh, Delete", non "Edit, Sync, Delete" come documentato

**Dove**: `mkdocs_src/docs/user/fx/index.en.md:23`:

> "🖱️ **Context Menu**: Right-click any row in the table layout for quick actions
> (**Edit, Sync, Delete**)"

**Controprova nel codice** — `frontend/src/lib/components/fx/FxTable.svelte:286-323`
(prop `rowActions` passata a `DataTable`):

```ts
rowActions={[
    { id: 'swap', label: () => $t('common.swapDirection'), ... },     // riga 288
    { id: 'sync', label: () => $t('common.sync'), ... },              // riga 294
    { id: 'refresh', label: () => $t('common.refresh'), ... },        // riga 309
    { id: 'delete', label: () => $t('common.delete'), ..., variant: 'danger' }, // riga 323
]}
```

Nessuna azione `edit`/`Edit` è presente. Il menu contestuale è realmente attivato al
right-click (`frontend/src/lib/components/table/DataTable.svelte:153`
`enableContextMenu = true` di default, `:1329-1330`
`oncontextmenu={(e) => {...}}`, `:1646` rendering di `<ContextMenu ... />`), quindi la
meccanica "right-click per azioni rapide" descritta è corretta — solo l'elenco delle
azioni non coincide: mancano "Edit", sono presenti in più "Swap" (inverti direzione
di visualizzazione) e "Refresh" (probabilmente un secondo tipo di aggiornamento
rispetto a "Sync", non distinto nella pagina).

**Classificazione**: Dettaglio obsoleto. **Gravità**: minor — nessun rischio dati,
ma un utente che cerchi "Edit" dal menu contestuale della tabella non lo troverà (la
modifica dei singoli punti dato avviene solo nel Data Editor della pagina di
dettaglio, non dalla tabella lista). **Confidenza**: alta.

**Direzione di correzione suggerita**: aggiornare l'elenco a "Swap, Sync, Refresh,
Delete" (o ai nomi effettivamente mostrati in UI dalle chiavi i18n
`common.swapDirection`/`common.sync`/`common.refresh`/`common.delete`), chiarendo la
differenza fra "Sync" e "Refresh" se concettualmente distinti.

---

### 🟢 F6 — `detail/chart.en.md`: preset di intervallo temporale incompleti (mancano YTD e MAX, sempre disponibili)

**Dove**: `mkdocs_src/docs/user/fx/detail/chart.en.md:31,54`:

> "You can also use the **time range presets** (1W, 1M, 3M, 6M, 1Y, 2Y) or select a
> **Custom** date range..."
> "⏱️ **Time range** — 1W, 1M, 3M, 6M, 1Y, 2Y, Custom"

**Controprova nel codice** — `frontend/src/lib/components/ui/date/
DateRangePicker.svelte:179-187` (array `presets`, usato dal componente condiviso
montato sulla pagina di dettaglio FX,
`frontend/src/routes/(app)/fx/[pair]/+page.svelte:970`):

```ts
{key: '1W', label: '1W', weeks: 1},
{key: '1M', label: '1M', months: 1},
{key: '3M', label: '3M', months: 3},
{key: '6M', label: '6M', months: 6},
{key: '1Y', label: '1Y', years: 1},
{key: '2Y', label: '2Y', years: 2},
{key: 'YTD', label: $_('datePicker.presets.ytd')},   // riga 186 — non menzionato
{key: 'MAX', label: $_('datePicker.presets.max')},   // riga 187 — non menzionato
```

Il prop `compact={true}` usato nella pagina FX (riga 970 del file rotta) modifica solo
la resa grafica (`DateRangePicker.svelte:894,1076,1081-1094`), non nasconde alcun
preset — YTD e MAX restano sempre selezionabili nello stesso menu.

**Classificazione**: Omissione. **Gravità**: minor — nessun comportamento errato,
solo un elenco incompleto che potrebbe far pensare all'utente che "tutto il periodo
disponibile" (MAX) o "da inizio anno" (YTD) non siano opzioni rapide raggiungibili
senza usare "Custom". **Confidenza**: alta.

**Direzione di correzione suggerita**: aggiungere "YTD" e "MAX" all'elenco preset in
entrambi i punti della pagina.

---

## Aree verificate senza reperti (evidenza positiva)

- **Sync: provider autoritativo, overwrite, nuovi punti** (`sync.en.md`,
  `detail/data-editor.en.md` sezione "Merge Behavior"): confermato da
  `backend/app/services/fx.py:391-461` (`ensure_rates_multi_source`) — upsert
  `on_conflict_do_update` su `(date, base, quote)` che sovrascrive sempre
  `rate`/`source`/`fetched_at` con i valori del provider, mai il contrario.
- **Fallback automatico fra provider** (`sync.en.md`, `detail/provider.en.md`):
  confermato da `backend/app/services/fx.py:770-1000+` (`sync_pairs_bulk`,
  `_process_route`) — le route vengono provate in ordine di priorità, con log
  esplicito "primary route failed, used fallback route N" e `fallback_errors`
  accumulati per route scartate.
- **Catene di conversione (moltiplicazione dei tassi intermedi)** (`add-pair.en.md`,
  `providers/index.en.md`): confermato da `backend/app/services/fx.py:671-705`
  (`compute_chain_rate`), che moltiplica (o divide, se verso inverso) i tassi
  normalizzati lungo la catena — coerente con l'esempio RON→EUR→JPY della pagina.
- **Sentinel MANUAL auto-gestito** (`providers/index.en.md`, `detail/provider.en.md`):
  confermato da `backend/app/services/fx_providers/manual.py` (docstring, priorità
  fissa `MANUAL_PRIORITY = 999`) e dalla logica di auto-rimozione/re-inserimento in
  `backend/app/api/v1/fx.py:846-871` (`create_routes_bulk`, blocco "Auto-remove
  MANUAL sentinel for pairs that now have real providers").
- **Riordino route: drag&drop + frecce** (`detail/provider.en.md`, "Reorder routes
  ... drag & drop or arrow buttons"): confermato da
  `frontend/src/lib/components/ui/OrderableList.svelte:98-154`
  (`moveUp`/`moveDown` con `ChevronUp`/`ChevronDown`, più `draggable`/`ondragstart`
  righe 127-128), usato da `FxProviderConfig.svelte`.
- **Sync automatico dopo la creazione di una coppia** (`add-pair.en.md`, punto 4
  "data synchronization begins automatically"): confermato da
  `frontend/src/routes/(app)/fx/+page.svelte:875-879`
  (`handlePairCreated`, commento "sync already done by modal").
- **Toggle Grid/Table persistito in `localStorage`** (`index.en.md:18`): confermato,
  vedi dettaglio nel reperto F2 sopra (`ViewModeToggle.svelte:2`,
  `storageKey="fxViewMode"`) — contrasto voluto con l'assenza di persistenza di
  Chart Settings.
- **Formula CAGR delle Measure** (`detail/measures.en.md`, "Annualized Return"):
  confermato da `frontend/src/lib/charts/signals/MeasureSignal.ts:99-100,130`:
  `(1 + deltaPct/100)^(365/days) - 1`, esattamente il CAGR descritto.
- **Buffer locale prima del salvataggio (Data Editor)** (`detail/data-editor.en.md`,
  "Merge Behavior" — "not persisted... until you click Save"): confermato da
  `frontend/src/lib/components/fx/FxDataEditorSection.svelte:104-159`
  (`rows` con `status` `edited`/`appended`/`deleted`/`original`, POST/DELETE solo in
  `handleSave`).
- **Sovrascrittura selettiva per data in import/merge**: confermato dallo stesso
  meccanismo di upsert on-conflict del backend (vedi punto Sync sopra) applicato alle
  righe importate — coerente con "existing dates overwritten, new dates added, other
  dates untouched".
- **Route discovery diretta/a catena lato client** (`add-pair.en.md`): confermato da
  `frontend/src/lib/utils/currency/currencyGraph.ts` (`buildCurrencyGraph`,
  `findAllPaths`, DFS con backtracking, max 2 usi per provider, percorsi semplici) —
  coerente con la descrizione utente, che non specifica (correttamente, essendo un
  dettaglio implementativo fuori target per un utente finale) se il calcolo avvenga
  lato client o server.
- **Capacità dei quattro provider** ("Current Price" ✅, "History" ✅, "Search" ❌):
  coerenti con l'assenza di ricerca asset in tutti e quattro i file provider
  (`ecb.py`, `fed.py`, `boe.py`, `snb.py`) — nessuno implementa una ricerca, solo
  `get_supported_currencies`/`fetch_rates`.
- **Conteggi valute FED (~20) e BOE (~15)**: confermati contando le chiavi di
  `CURRENCY_SERIES` in `fed.py` (20 voci) e `boe.py` (15 voci) — coincidono con le
  tabelle di `providers/index.en.md` e le rispettive pagine dedicate.
- **Formato quotazione ECB/FED/BOE e inversione automatica**: confermati nei
  rispettivi metodi `fetch_rates` (`ecb.py` righe ~163-235, quota EUR→X diretta;
  `fed.py` righe ~200-260, quota invertita X→USD "as provided", poi normalizzata da
  `normalize_rate_for_storage` in `fx.py:342`; `boe.py` righe ~190-250, quota diretta
  GBP→X).
- **Multi-unit SNB (quotazione per 100 unità)**: confermato dalla verifica live delle
  dimensioni SNB (`JPY100`, `SEK100`, `NOK100`, `DKK100` fra gli id D1 con
  moltiplicatore `100`, contro `EUR1`/`USD1`/`GBP1` con moltiplicatore `1`) e dal
  parsing in `snb.py` (`_D1_RE`, `_walk_dimension_items`) che normalizza sempre al
  valore per-unità.

---

## Nota informativa incrociata (non un reperto separato)

Le descrizioni `description_i18n` mostrate in-app per **ECB** e **BOE** (visibili
nello stesso modale di selezione provider citato in F1) riportano cifre di copertura
valute diverse da quelle nelle rispettive pagine `providers/ecb.en.md` e
`providers/boe.en.md`, pur non contraddicendole in modo grave:

- ECB: pagina dichiara "~45" (`ecb.en.md:3`, confermato da verifica live
  `data-api.ecb.europa.eu` → 44 valute), ma `ecb.py:66` mostra in-app "30+
  currencies" — un forte sottostima interna, non un errore della pagina mkdocs.
- BOE: pagina dichiara "~15" (`boe.en.md:3`, confermato contando `CURRENCY_SERIES` in
  `boe.py` → 15 voci), ma `boe.py:91` mostra in-app "20+ currencies" — qui è la
  stringa in-app a sovrastimare rispetto al codice dello stesso provider.

Questi due scarti riguardano la stringa `description_i18n` restituita
dall'endpoint `GET /fx/providers` (quindi tecnicamente "API/schema", in perimetro),
ma **non sono errori delle pagine mkdocs auditate**, che al contrario riportano cifre
più accurate. Si segnalano qui per completezza incrociata, senza contarli come
reperto a carico delle pagine utente.

## Non verificabile / fuori dal perimetro locale

- Nessuna claim delle 15 pagine assegnate è risultata non verificabile dal
  repository locale: tutte le affermazioni riguardano comportamento di
  backend/frontend/test ispezionabile, oppure (per ECB/SNB) API pubbliche esterne
  interrogabili in sola lettura per una controprova indipendente.
- Non sono stati rilevati link rotti nella navigazione interna delle 15 pagine
  (`index.md`, `add-pair.md`, `sync.md`, `chart-settings.md`,
  `detail/{index,chart,data-editor,measures,signals,provider}.md`,
  `providers/{index,ecb,fed,boe,snb}.md`) — tutti i target risolvono a file `.en.md`
  realmente presenti nello scope assegnato.

## Nota per la sintesi finale (00_INDEX.md)

Aggiornamento suggerito alla riga "03" della tabella di copertura: stato da
"In corso" a completato, 15/15 pagine coperte, **6 reperti** (1 critical, 3 major, 2
minor), 0 non verificabili, 0 problemi di navigazione/link.
