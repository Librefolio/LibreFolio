# Plan: FxPairAddModal Redesign — CurrencySelect, FxProviderSelect & OrderableList

**Data creazione**: 3 Marzo 2026
**Status**: ✅ COMPLETATO (Step 9 — compact sizing, filter currencies, warning color)
**Dipendenze**: Phase 5 FX in corso, plan-phase05Fx.prompt.md, plan-fxUiRefinementsRound2.prompt.md
**Riferimenti**:
- `plan-phase05Fx.prompt.md` — Piano principale Phase 5
- `plan-fxUiRefinementsRound2.prompt.md` — Sub-plan fix UI (OrderableList, Settings ⚙️, etc.)
- `TODO_FUTURI.md` §Cross-Rate

---

## Obiettivo

La modale di aggiunta coppia FX va completamente riprogettata: sostituire i `<input>` testo libero con il `SearchSelect` valute già presente nel progetto, creare un nuovo componente `FxProviderSelect`, usare `OrderableList` per l'ordinamento provider, spostare `ImportPluginSelect` e `BrokerSearchSelect` nella cartella `select/` per coerenza, e tradurre tutto via i18n. Backend: estendere `/api/v1/fx/providers` per includere le target currencies nella risposta.

---

## Step 1: Estendere API backend `/fx/providers` + rimuovere `GET /fx/currencies`

### 1a. Rimuovere endpoint `GET /fx/currencies`
Questo endpoint viene **assorbito** da `GET /fx/providers` (ora esteso con target currencies).
- [x] Rimuovere l'endpoint `list_currencies` da `backend/app/api/v1/fx.py` (righe 111-140)
- [x] Rimuovere `router_currencies` e la riga `fx_router.include_router(router_currencies)` (il sub-router `/currencies` resta per convert/rate/sync che sono sotto `router_currencies`)
  - **NOTA**: il `router_currencies` è mantenuto perché usato anche da convert, rate, sync. Rimossa solo la funzione `list_currencies`.
- [x] Rimuovere `FXCurrenciesResponse` da `backend/app/schemas/fx.py` e dal relativo import in `fx.py` e `__init__.py`
- [x] Aggiornare il test `test_get_currencies` in `test_fx_api.py` → convertito in `test_providers_include_target_currencies` + `test_old_currencies_endpoint_removed`
- [x] Aggiornare il docstring del modulo `test_fx_api.py` per rimuovere il riferimento a `GET /fx/currencies`

### 1b. Estendere `/fx/providers` con target currencies
- [x] Aggiungere al campo `FXProviderInfo` in `backend/app/schemas/fx.py` un nuovo campo `target_currencies: list[str]`
- [x] Nell'endpoint `list_providers` in `backend/app/api/v1/fx.py`, chiamare `get_supported_currencies()` per ogni provider e popolare il campo
- [x] Così il frontend ha, in un'unica chiamata, le `base_currencies` e le `target_currencies` per ogni provider
- [x] Il campo `base_currency: str` (singolo) è potenzialmente obsoleto — aggiunto `# TODO: deprecate base_currency in favor of base_currencies` nel codice
- [x] Eseguire `./dev.py api sync` per rigenerare i tipi TypeScript ✅
- [x] `./dev.py front check` — 0 errori ✅
- [x] `./dev.py front build` — build pulita ✅

---

## Step 2: Spostare selector specializzati nella cartella `select/` ✅

- [x] **Spostare** `ImportPluginSelect.svelte` da `components/` → `components/ui/select/ImportPluginSelect.svelte`
- [x] **Spostare** `BrokerSearchSelect.svelte` da `components/brokers/` → `components/ui/select/BrokerSearchSelect.svelte`
- [x] **Aggiornare imports** in:
  - `BrokerForm.svelte` — `ImportPluginSelect`
  - `files/+page.svelte` — `BrokerSearchSelect`
- [x] **Aggiornare `index.ts`** in `select/index.ts` per esportare entrambi i nuovi componenti
- [x] **Aggiornare** import di `BrokerIcon` in `BrokerSearchSelect` (da relativo a absolute path)
- [x] **Rimuovere** file originali
- [x] `./dev.py front check` — 0 errori ✅

---

## Step 3: Creare componente `CurrencySearchSelect` in `select/` ✅

Componente già esistente con tutte le feature richieste (`CurrencySearchSelect.svelte`):

- [x] Accetta `value: string` (codice valuta) bindable
- [x] Accetta prop opzionale `allowedCurrencies?: string[]`
- [x] Accetta prop opzionale `includeAll?: boolean`
- [x] Internamente chiama `list_currencies_api_v1_utilities_currencies_get()`
- [x] Usa `SearchSelect` con snippet `item` e `selectedItem`
- [x] Esportato da `select/index.ts`

### Migrazione

- [x] `fx/+page.svelte` — già usa `CurrencySearchSelect` con `includeAll=true`
- [ ] `BrokerForm.svelte` — TODO futuro (ha errori pre-esistenti di migrazione)
- [ ] `CashTransactionModal.svelte` — TODO futuro
- [ ] `PreferencesTab.svelte` — TODO futuro
- [ ] `GlobalSettingsTab.svelte` — TODO futuro

---

## Step 4: Creare componente `FxProviderSelect` in `select/` ✅

Nuovo file `frontend/src/lib/components/ui/select/FxProviderSelect.svelte`:

- [x] Accetta `value: string` (codice provider) bindable
- [x] Accetta `baseCurrency: string` e `quoteCurrency: string` — usati per filtrare i provider selezionabili
- [x] Logica compatibilità: un provider è selezionabile se `(base in base_currencies AND quote in target_currencies) OR (quote in base_currencies AND base in target_currencies)`
- [x] Accetta `excludeCodes?: string[]` — provider già aggiunti da escludere
- [x] Accetta `disabled?: boolean` — quando base/quote non sono ancora selezionati
- [x] Internamente chiama l'API `/fx/providers` (esteso allo Step 1) e filtra
- [x] Usa `SearchSelect` con snippet che mostra: icona (da `icon_url`, con fallback a iniziali), nome, codice, descrizione troncata
- [x] Provider non compatibili con la coppia corrente: mostrati come `disabled` con tooltip "Questo provider non supporta questa coppia"
- [x] Callback `onProvidersLoaded` per esporre la lista al parent
- [x] Esportato da `select/index.ts`

---

## Step 5: Riprogettare `FxPairAddModal` layout e logica ✅

### Layout proposto (ASCII)

```
┌─────────────────────────────────────────┐
│  $_('fx.addPair.title')                 │
│─────────────────────────────────────────│
│  [CurrencySearchSelect]  →  [CurrencySearchSelect] │
│   Base Currency               Quote Currency        │
│─────────────────────────────────────────│
│  Provider Priority                [+ Add]│
│  ┌─ OrderableList ──────────────────┐   │
│  │ ⠿ 🏛 ECB — European Central...  ×│   │
│  │ ⠿ 🏦 FED — Federal Reserve...   ×│   │
│  └──────────────────────────────────┘   │
│  ⚠ Sezione disattivata se base/quote   │
│     non popolati                        │
│  🔒 Intermediate Route — Coming Soon    │
│─────────────────────────────────────────│
│              [$_('cancel')]  [$_('save')]│
└─────────────────────────────────────────┘
```
Riscritto completamente `FxPairAddModal.svelte`:

### Logica

- [x] Usare `ModalBase` come wrapper
- [x] Usare `CurrencySearchSelect` per base e quote (NO testo libero)
- [x] Provider section grigia/disabilitata finché `baseCurrency` e `quoteCurrency` non sono entrambi popolati
- [x] Quando entrambi popolati, mostrare `FxProviderSelect` per aggiungere provider (con filtro automatico compatibilità)
- [x] Provider aggiunti appaiono in `OrderableList` con snippet custom: icona + nome + badge priorità + bottone ×
- [x] `OrderableList` già supporta drag & drop desktop + frecce mobile
- [x] Migrato da Svelte 4 (`createEventDispatcher`, `export let`, `on:click`) a Svelte 5 (`$props`, `$state`, `$derived`, `onclick`)
- [x] Footer tradotto: `$_('common.cancel')` / `$_('fx.addPair.saveConfiguration')`
- [x] Aggiornato `fx/+page.svelte` per usare nuove callback props (`oncreated`, `onclose`) invece di eventi Svelte 4

---

## Step 6: i18n — Aggiungere chiavi di traduzione ✅

Usare `./dev.py i18n add` per aggiungere:

- [ ] `fx.addPair.title` — "Add New Currency Pair" / "Aggiungi Nuova Coppia FX" / "Ajouter une Paire de Devises" / "Añadir Par de Divisas"
- [ ] `fx.addPair.baseCurrency` — "Base Currency" / "Valuta Base" / "Devise de Base" / "Divisa Base"
- [ ] `fx.addPair.quoteCurrency` — "Quote Currency" / "Valuta Quotata" / "Devise Cotée" / "Divisa Cotizada"
- [x] `fx.addPair.title` — ✅
- [x] `fx.addPair.baseCurrency` — ✅
- [x] `fx.addPair.quoteCurrency` — ✅
- [x] `fx.addPair.providerPriority` — ✅
- [x] `fx.addPair.addProvider` — ✅
- [x] `fx.addPair.providerDisabledHint` — ✅
- [x] `fx.addPair.providerIncompatible` — ✅
- [x] `fx.addPair.intermediateRouteComingSoon` — ✅
- [x] `fx.addPair.saveConfiguration` — ✅
- [x] `common.cancel` — ✅
- [x] `common.save` — ✅
- [x] `common.saving` — ✅
- [x] `fx.provider.primary` — ✅
- [x] `fx.provider.fallback` — ✅

---

## Step 7: Validazione finale ✅

- [x] Eseguire `./dev.py front check` — 0 errori nei file modificati (3 errori pre-esistenti in BrokerForm.svelte)
- [x] Eseguire `./dev.py front build` — build pulita ✅
- [ ] Testare manualmente:
  - Apertura modale → selettori valuta funzionano con ricerca
  - Selezione base + quote → sezione provider si attiva
  - Aggiunta provider compatibili → OrderableList con drag & drop
  - Provider incompatibili → mostrati come disabled
  - Riordino provider → drag & drop e frecce
  - Save → salvataggio configurazione corretta
  - Cancel → chiusura senza side-effects
  - Dark mode → tutti i componenti stilizzati correttamente
  - Mobile → layout verticale funzionante

---

## Further Considerations

### 1. Filtro valute nella FX list page
Nella pagina FX, la `allowedCurrencies` per i `CurrencySearchSelect` di filtro dovrebbe essere estratta dalle coppie configurate: `pairs.flatMap(p => [p.config.base, p.config.quote])` + dedup. Questo riduce la lista da ~160 valute a solo quelle effettivamente in uso.

### 2. `base_currency` (singolo) deprecation
Marcare il campo con un `# TODO_DEPRECATE` nel backend. Tutti i nuovi consumer frontend devono usare `base_currencies[]`. Il campo singolo resta per backward compatibility API.

### 3. Catena di conversione (cross-rate)
Oggi un provider è "compatibile" solo se supporta la coppia diretta. Quando si implementerà la catena (USD→EUR→RON), la logica di `FxProviderSelect` dovrà essere aggiornata per verificare se esiste un path transitivo. Per ora aggiungere placeholder "Coming Soon" nella modale (già menzionato in TODO_FUTURI.md §Cross-Rate). Da NON implementare adesso.

### 4. UserSearchSelect
L'utente ha menzionato di creare un componente selettore utente. Attualmente la ricerca utenti è inline in `BrokerSharingModal.svelte` (debounced, con dropdown custom). Documentato come TODO futuro — non fa parte di questo step.

### 5. Caching risposte API provider
La lista dei provider è statica per sessione (i plugin non cambiano a runtime). Il caching è responsabilità dei singoli componenti/chiamate, non serve un layer extra.

---

## Commit message suggerito

```
feat(fx): redesign add pair modal with CurrencySearchSelect, FxProviderSelect & OrderableList

- Extend /fx/providers API to include target_currencies per provider
- Create CurrencySearchSelect: reusable currency picker with optional allowedCurrencies filter
- Create FxProviderSelect: provider picker with base/quote compatibility check
- Move ImportPluginSelect & BrokerSearchSelect into ui/select/ for consistency
- Rewrite FxPairAddModal: SearchSelect for currencies, OrderableList for provider priority,
  disabled provider section until both currencies selected, full i18n
- Migrate FxPairAddModal from Svelte 4 to Svelte 5 runes
- Add i18n keys for add pair modal (EN/IT/FR/ES)
```

---

## Step 8: Fix da test manuale — Round di rifinitura ✅

**Feedback ricevuti dal test manuale** (3 Marzo 2026):

### 8a. Dropdown provider troncato nella modale
- [x] Il dropdown del `FxProviderSelect` viene tagliato da `overflow: hidden` di `ModalBase`
- **Fix**: passare `allowOverflow={true}` a `ModalBase` nel `FxPairAddModal`

### 8b. Impossibile aggiungere il secondo provider
- [x] Dopo aver aggiunto il primo provider, il `FxProviderSelect` non permette selezione successiva
- **Root cause**: il `value` del select rimane vuoto ma la `excludeCodes` filtra correttamente — il problema è che dopo l'`addProvider()` il componente SearchSelect non re-renderizza
- **Fix**: auto-add — quando l'utente seleziona un provider dal dropdown, viene aggiunto automaticamente alla lista senza bisogno del pulsante +

### 8c. Auto-add on select (rimuovere pulsante +)
- [x] Rimuovere il pulsante `+` separato
- [x] Usare `onchange` del `FxProviderSelect` per aggiungere automaticamente il provider appena selezionato
- [x] Dopo l'aggiunta, resettare il valore del select a '' per permettere una nuova selezione
- [x] Il pulsante `+` era all'inizio della sezione e apriva la riga — ora reso implicito: cliccare il dropdown = aggiungere

### 8d. Estetica modale — margini e spaziatura
- [x] **Padding mancante**: il `<div class="space-y-5">` non ha padding — la modale BrokerModal usa `p-4` con header/footer separati
- **Fix**: Ristrutturare layout modale con:
  - Header: `p-5 pb-0` con titolo + eventuale X button
  - Body: `p-5` con contenuto scrollabile
  - Footer: `p-5 pt-3 border-t` separato
- [x] Allineare allo stile BrokerModal (header con border-b, scrollable body, sticky footer)

### 8e. Mobile — valute una sotto l'altra
- [x] Quando lo schermo è piccolo, i 2 `CurrencySearchSelect` (base + quote) vanno oltre lo schermo
- **Fix**: cambiare il layout da `flex items-end gap-3` a `flex flex-col sm:flex-row items-end gap-3`
- [x] La freccia `→` diventa `↓` in modalità verticale (nascondere con `hidden sm:inline`, mostrare alternativa con `sm:hidden`)

### 8f. Warning su cancel con modifiche in corso
- [x] Quando l'utente clicca Cancel o fuori dalla modale, se ci sono inserimenti/modifiche (dirty state), mostrare un ConfirmDialog
- **Fix**: tracciare `isDirty` = `baseCurrency !== '' || quoteCurrency !== '' || providerEntries.length > 0`
- [x] Se dirty, intercettare `handleClose` e mostrare un `ConfirmDialog` prima di chiudere
- [x] Se non dirty, chiudere direttamente

### 8g. Ogni riga provider dovrebbe essere editabile on hover
- [ ] Quando l'utente passa sopra una riga, mostrare i controlli (remove, move) — attualmente sempre visibili è ok come primo step, hover-only è un'ottimizzazione futura

---

## Commit message suggerito (Step 8)

```
fix(fx): improve add pair modal UX — auto-add provider, overflow fix, mobile layout, dirty warning

- Fix dropdown truncation by enabling allowOverflow on ModalBase
- Auto-add provider on selection (remove separate + button)
- Add proper padding/spacing matching BrokerModal style
- Responsive mobile layout: currencies stack vertically with ↓ arrow
- Add dirty state tracking with ConfirmDialog on cancel/close
- Fix second provider addition issue
```

---

## Step 9: Rifinitura dimensioni modale + filtro valute + colore warning ✅

**Feedback ricevuti dal test manuale** (4 Marzo 2026):

### 9a. Campi troppo grandi nella modale
- [x] Tutti i campi (CurrencySearchSelect, FxProviderSelect, provider entries) avevano dimensioni oversized rispetto alle altre modali
- **Fix**: Aggiunto prop `compact` a `CurrencySearchSelect` che riduce icone (da `w-9 h-9` a `w-6 h-6`) e testo
- [x] Usato `compact={true}` nella modale FxPairAddModal per entrambi i selettori valuta
- [x] Ridotto dimensioni icone/testo provider nella OrderableList (da `w-7 h-7` a `w-6 h-6`, text da `text-sm` a `text-xs`)
- [x] Ridotto dimensioni icone/testo in `FxProviderSelect` (da `w-8 h-8` / `w-7 h-7` a `w-6 h-6`)
- [x] Ridotto padding body (da `p-5 space-y-5` a `px-5 py-4 space-y-4`)
- [x] Ridotto padding footer (da `p-5 pt-4` a `px-5 py-3`) e bottoni (da `px-4 py-2` a `px-3 py-1.5`)
- [x] Ridotto hint e placeholder sections (da `p-3` a `p-2.5`, `text-sm` a `text-xs`)

### 9b. Filtro valute FX mostra tutte le valute
- [x] Il `CurrencySearchSelect` nel filtro della pagina FX mostrava ~160 valute (tutte)
- **Fix**: Aggiunto `configuredCurrencies = [...new Set(pairs.flatMap(p => [p.config.base, p.config.quote]))]` come derived
- [x] Passato `allowedCurrencies={configuredCurrencies}` a entrambi i `CurrencySearchSelect` nel filtro
- [x] Ora mostra solo le valute presenti nelle coppie configurate

### 9c. ConfirmModal colore da rosso a giallo
- [x] Il `ConfirmModal` per discard changes usava `danger={true}` (bottone rosso) — troppo "ansiogeno"
- **Fix**: Cambiato in `danger={false} warning={true}` per usare il colore amber/giallo

### 9d. Vecchio componente valuta verificato
- [x] Il vecchio endpoint `GET /fx/currencies` è già rimosso (Step 1)
- [x] `CurrencySearchSelect` usa `utilities/currencies` (corretto)
- [x] 3 altri posti (PreferencesTab, GlobalSettingsTab, CashTransactionModal) usano ancora l'API direttamente — documentato come TODO futuro

### Validazione
- [x] `./dev.py front check` — 0 errori ✅
- [x] `./dev.py front build` — build pulita ✅

---

## Commit message suggerito (Step 9)

```
fix(fx): compact modal sizing, filter currencies by config, warning color for discard

- Add compact prop to CurrencySearchSelect (smaller icons/text for modals)
- Reduce FxPairAddModal field sizes: icons, padding, buttons all tighter
- Reduce FxProviderSelect dropdown item sizes for better modal fit
- Filter currency dropdown in FX page to show only configured currencies
- Change discard ConfirmModal from danger (red) to warning (amber)
```

