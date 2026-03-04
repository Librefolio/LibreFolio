# Plan: FX UI Feedback Round 3 — Layout, Search, Delete, Auto-Sync

**Data creazione**: 4 Marzo 2026
**Status**: 🔄 IN CORSO — Bug fix applicati, sezione lingua in analisi
**Dipendenze**: plan-fxCurrencyFixLayoutFlags completato
**Contesto**: Feedback da test manuale del layout E+, bandiere, CurrencySearchSelect

---

## Feedback Raccolti

### F1 — Layout tablet: filtri non wrappano correttamente
**Problema**: Su tablet (768-1279px) i bottoni azione diventano colonna verticale (OK), ma i 2 CurrencySearchSelect non scendono sotto il DateRangePicker. Il primo filtro resta sempre accanto alla data, solo il secondo scende. A semi-mobile i bottoni vanno sotto in riga orizzontale ma il primo filtro resta accanto al tempo. Solo a mobile pieno tutto diventa verticale.

**Causa**: I CurrencySearchSelect hanno `w-40` (larghezza fissa 10rem = 160px) e sono dentro un `flex-wrap`. Il DateRangePicker è largo e il primo filtro ci sta accanto anche a 768px, ma il secondo no. Il problema è che non c'è un breakpoint che forzi i filtri a wrappare tutti insieme.

**Soluzione**: Raggruppare DateRangePicker e i 2 currency filter in sotto-gruppi con comportamento di wrap coerente. Opzioni:
- **A**: Mettere i 2 currency filter in un `flex` con `flex-shrink-0` e `min-width` sufficiente a forzare il wrap di coppia
- **B**: Wrappare i 2 currency filter in un `<div class="flex gap-3">` così wrappano come unità
- **C** (preferita): Usare `flex-wrap` con `basis` calcolate: il DateRangePicker ha `basis: 100%` su `md` e `basis: auto` su `xl+`, forzando i filtri a stare sotto su tablet

### Modifiche

In `frontend/src/routes/(app)/fx/+page.svelte`, nella sezione filtri:

```svelte
<!-- Left: Filters -->
<div class="flex-1 flex flex-wrap items-center gap-3 justify-center md:justify-start">
    <!-- DateRangePicker prende tutta la riga su tablet, auto su desktop -->
    <div class="w-full xl:w-auto">
        <DateRangePicker ... />
    </div>

    <!-- Currency filters wrappano come coppia -->
    <div class="flex items-center gap-3">
        <div class="w-40">
            <CurrencySearchSelect ... />
        </div>
        <div class="w-40 ...">
            <CurrencySearchSelect ... />
        </div>
    </div>
</div>
```

Il `w-full xl:w-auto` sul wrapper del DateRangePicker forza i filtri valuta a stare sulla riga successiva su tablet (md-lg), mentre su desktop largo (xl+) il DateRangePicker è auto-width e tutto sta su una riga.

**File**: `frontend/src/routes/(app)/fx/+page.svelte`

---

### F2 — CurrencySearchSelect: ricerca per simbolo (€, $) non funziona più
**Problema**: Prima della modifica, il campo `searchText` includeva il simbolo. Ora con `flag_emoji` come `icon`, il `searchText` è solo `"USD US Dollar"` — manca il simbolo `$`.

**Soluzione**: Includere il simbolo nel `searchText` del SelectOption.

```typescript
// Nel build delle currencyOptions:
searchText: `${c.code} ${c.name} ${c.symbol !== c.code ? c.symbol : ''}`,
```

**File**: `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte`

---

### F3 — CurrencySearchSelect: ricerca per nazione (italia, IT, ita, etc.)
**Problema**: L'utente vorrebbe cercare "italia" e trovare EUR, cercare "US" e trovare USD. Attualmente il searchText contiene solo code + name (es. "EUR Euro").

**Soluzione**: Arricchire il backend per restituire anche i nomi delle nazioni associate a ogni valuta, oppure costruire il mapping lato frontend dal `currencyStore`.

**Approccio backend** (preferito — singola fonte di verità):
- Aggiungere un campo `countries` (o `search_hints`) a `CurrencyListItem` con le nazioni che usano quella valuta
- Es. per EUR: `["Austria", "Belgium", "Germany", "Italy", "France", ...]`
- Es. per USD: `["United States", "American Samoa", "Ecuador", ...]`
- Il frontend include questi nel `searchText`

**Approccio alternativo (leggero)**:
- Aggiungere solo `country_names: string` come stringa unita (es. `"Italy, Germany, France, ..."`)
- Meno strutturato ma sufficiente per la ricerca

**Implementazione backend** in `currency_utils.py`:
- Usare la stessa mappa Babel `get_global('territory_currencies')` inversa per costruire `currency → list[country_name]`
- Babel fornisce nomi localizzati delle nazioni via `Locale.territories` (per la lingua corrente)
- Anche i codici ISO-2 e ISO-3 devono essere cercabili (IT, ITA, US, USA)

```python
@lru_cache(maxsize=1)
def _build_currency_to_countries_map() -> dict[str, list[str]]:
    """Build mapping: currency_code → list of (country_name, iso2, iso3)."""
    # Usa stessa logica di _build_currency_to_flag_map ma raccoglie tutti i paesi
    ...
```

Schema `CurrencyListItem`:
```python
country_codes: list[str] = Field(default_factory=list, description="ISO-2 country codes using this currency (e.g., ['US', 'AS', 'EC'] for USD)")
```

Frontend `searchText`:
```typescript
searchText: `${c.code} ${c.name} ${c.symbol} ${(c.country_codes ?? []).join(' ')} ${countryNamesForCodes(c.country_codes)}`,
```

> **Nota**: Per i nomi localizzati delle nazioni, il frontend può usare i dati già caricati dal `GET /countries` endpoint, oppure il backend può includere i nomi direttamente. Preferibile che il backend restituisca i nomi già nella lingua corrente per coerenza.

**File backend**: `backend/app/utils/currency_utils.py`, `backend/app/schemas/utilities.py`
**File frontend**: `frontend/src/lib/stores/currencyStore.ts`, `CurrencySearchSelect.svelte`

---

### F4 — CurrencySearchSelect: simbolo scompare dopo selezione
**Problema**: Nel dropdown, ogni opzione mostra `🇺🇸 USD $ — US Dollar`. Ma una volta selezionata, il `selectedItem` snippet mostra solo `🇺🇸 USD — US Dollar` senza il simbolo `$`.

**Soluzione**: Aggiungere il simbolo anche nel snippet `selectedItem`, come nel snippet `item`.

```svelte
{#snippet selectedItem(option)}
    <div class="flex items-center space-x-2 min-w-0">
        {#if option.icon}
            <span class="text-base shrink-0 leading-none">{option.icon}</span>
        {/if}
        <div class="min-w-0">
            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                {option.value || ''}
                {#if (option.data as any)?.symbol && (option.data as any).symbol !== option.value}
                    <span class="text-gray-400 ml-0.5 text-xs">{(option.data as any).symbol}</span>
                {/if}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{option.label}</div>
        </div>
    </div>
{/snippet}
```

**File**: `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte`

---

### F5 — Bottoni azione: testo nascosto anche a full screen
**Problema**: I bottoni Settings, Sync All, Refresh All mostrano solo l'icona. Il testo `hidden xl:inline` è stato rimosso nella riscrittura del layout E+. Su desktop largo c'è spazio per il testo.

**Soluzione**: Ripristinare `<span class="hidden xl:inline">` per i testi dei bottoni azione.

```svelte
<button ...>
    <Settings size={14} />
    <span class="hidden xl:inline">{$_('fx.actions.settings')}</span>
</button>
```

**File**: `frontend/src/routes/(app)/fx/+page.svelte`

---

### F6 — Delete FX pair: usare campo speciale "all" invece di range 1900-2099
**Problema**: Il `confirmDelete` usa `date_range: {start: '1900-01-01', end: '2099-12-31'}` per cancellare tutti i rate. Per principio, l'utente preferisce un campo esplicito che indica "cancella tutto".

**Soluzione**: Aggiungere al backend un modo per indicare "cancella tutti i rate di questa coppia" senza specificare un range. Opzioni:

**Opzione A** (preferita): Aggiungere `delete_all: bool = False` opzionale a `FXDeleteItem`. Se `true`, ignora `date_range` e cancella tutti i rate per la coppia.

```python
class FXDeleteItem(BaseModel):
    from_currency: str = Field(...)
    to_currency: str = Field(...)
    date_range: Optional[DateRangeModel] = Field(None, description="Date range to delete. If null and delete_all=True, deletes all rates.")
    delete_all: bool = Field(False, description="If True, delete ALL rates for this pair (ignores date_range)")

    @model_validator(mode="after")
    def validate_range_or_all(self):
        if not self.delete_all and self.date_range is None:
            raise ValueError("Either date_range or delete_all=True must be specified")
        return self
```

Nel backend `delete_rates_endpoint`:
```python
if delete_req.delete_all:
    # Delete ALL rates for this pair (no date filter)
    stmt = delete(FxRate).where(
        FxRate.base == base, FxRate.quote == quote
    )
else:
    # Delete by date range (existing logic)
    ...
```

Frontend:
```typescript
await zodiosApi.delete_rates_endpoint_api_v1_fx_currencies_rate_delete([{
    from: deletingPair.base,
    to: deletingPair.quote,
    delete_all: true,
}]);
```

**File backend**: `backend/app/schemas/fx.py`, `backend/app/api/v1/fx.py`
**File frontend**: `frontend/src/routes/(app)/fx/+page.svelte`

---

### F7 — Auto-sync dopo creazione coppia non-MANUAL
**Problema**: Dopo aver creato una nuova coppia FX con provider reali (ECB, FED, etc.), la card appare vuota perché non vengono scaricati rate. L'utente deve manualmente fare Sync.

**Soluzione**: Nella callback `handlePairCreated` della pagina FX list, se la coppia ha almeno un provider non-MANUAL, chiamare immediatamente `GET /fx/currencies/sync` con la finestra temporale corrente (dateStart/dateEnd). Se fallisce, proseguire silenziosamente (la card apparirà vuota come ora).

```typescript
async function handlePairCreated(event: CustomEvent<{base: string; quote: string; providers: any[]}>) {
    // ... existing logic to add pair to list ...

    // Auto-sync if non-MANUAL providers exist
    const hasRealProvider = event.detail.providers.some(p => p.code !== 'MANUAL');
    if (hasRealProvider) {
        try {
            await zodiosApi.sync_rates_api_v1_fx_currencies_sync_get({
                queries: {
                    start: dateStart,
                    end: dateEnd,
                    currencies: `${event.detail.base},${event.detail.quote}`,
                }
            });
            // Refresh data for the new pair
            await fetchPairData(newPairSlug);
        } catch (e) {
            console.warn('Auto-sync after pair creation failed, pair will appear empty:', e);
        }
    }
}
```

**File**: `frontend/src/routes/(app)/fx/+page.svelte`

---

### F8 — compact mode: ✅ COMPLETATO
**Risultato**: Confermato che compact è migliore ovunque. Prop `compact` rimossa dal componente `CurrencySearchSelect`. Rendering sempre compact (text-base per bandiere, text-sm per testo). Rimossi tutti i `compact={true}` da FxPairAddModal, SettingCurrency, GlobalSettingsTab.

**File modificati**: `CurrencySearchSelect.svelte`, `FxPairAddModal.svelte`, `SettingCurrency.svelte`, `GlobalSettingsTab.svelte`

---

### F9 — Filtro valuta 2 intelligente + logica swap
**Problema**: Il secondo filtro valuta mostra tutte le valute configurate, anche quelle che non hanno coppie con il primo filtro. Spreco — se seleziono EUR come primo filtro, il secondo dovrebbe mostrare solo USD, GBP, JPY etc. (le valute che hanno almeno una coppia con EUR).

Inoltre: se il primo filtro va su "All currencies" mentre il secondo è selezionato, il primo deve prendere il valore del secondo e il secondo va su "All". Simmetricamente, il primo filtro deve mostrare solo le valute che hanno almeno una coppia con il secondo (se il secondo è selezionato).

**Soluzione implementata**:
- `allowedForFilter1`: se C2 selezionato, solo valute paired con C2; altrimenti tutte
- `allowedForFilter2`: se C1 selezionato, solo valute paired con C1; altrimenti tutte
- Logica swap: se C1 → "all" e C2 è set → C1 prende C2, C2 → "all"
- Se C1 cambia e C2 non è più una coppia valida → C2 resettato
- La valuta selezionata nell'altro filtro è esclusa dalle opzioni (C1 non mostra il valore di C2 e viceversa)

**File**: `frontend/src/routes/(app)/fx/+page.svelte`
**Status**: ✅ COMPLETATO

---

## Ordine di Esecuzione

| # | Feedback | Complessità | Stato |
|---|----------|-------------|-------|
| 1 | F2 — Ricerca per simbolo (€, $) | Bassa | ✅ Completato |
| 2 | F4 — Simbolo visibile dopo selezione | Bassa | ✅ Completato |
| 3 | F5 — Testo bottoni azione su desktop | Bassa | ✅ Completato |
| 4 | F1 — Layout tablet wrap coerente | Media | ✅ Completato |
| 5 | F8 — Compact mode | Bassa | ✅ Completato |
| 6 | F9 — Filtro valuta 2 intelligente + swap | Media | ✅ Completato |
| 7 | F6 — Delete con `delete_all` | Media | ✅ Completato |
| 8 | F3 — Ricerca per nazione | Media-Alta | ✅ Completato |
| 9 | F7 — Auto-sync dopo creazione | Media | ✅ Completato |
| 10 | F10 — DatePicker max-width + centratura | Bassa | ✅ Completato |
| 11 | F11 — Tooltip label troncati | Bassa | ✅ Completato |
| 12 | F12 — Auto-sync spinner in modale | Media | ✅ Completato |
| 13 | F13 — Ricerca "unite" non funziona | Bassa | 🔍 Da investigare |
| 14 | F14 — Utilities API localizzazione lingua | Alta | 📋 Da fare |
| 15 | F15 — Layout programmatico ResizeObserver | Alta | ✅ Completato |
| 16 | F16 — DateRangePicker calendario orizzontale | Bassa | ✅ Completato |
| 17 | F17 — Allineamento tablet (filtri sx, azioni dx) | Bassa | ✅ Completato |

**Step 1-3**: Fix immediati frontend (nessun cambio backend)
**Step 4**: Layout fix (solo frontend)
**Step 5**: Attesa feedback
**Step 6**: Backend `delete_all` flag + frontend
**Step 7**: Backend `country_codes` + frontend searchText
**Step 8**: Auto-sync logic

---

## Riepilogo Implementazione (4 Marzo 2026)

### Backend

| File | Modifica |
|------|----------|
| `backend/app/schemas/fx.py` | F6: `FXDeleteItem` — aggiunto `delete_all: bool = False` + `date_range` ora `Optional`. Validatore: `date_range` o `delete_all=True` obbligatorio. Aggiunto import `model_validator`. |
| `backend/app/api/v1/fx.py` | F6: `delete_rates_endpoint` gestisce `delete_all=True` — query diretta senza date filter. |
| `backend/app/utils/currency_utils.py` | F3: Aggiunto `_build_currency_to_countries_map()` (currency→list[ISO-2]) + `country_codes` in output `list_currencies()`. |
| `backend/app/schemas/utilities.py` | F3: Aggiunto `country_codes: list[str]` a `CurrencyListItem`. |

### Frontend

| File | Modifica |
|------|----------|
| `CurrencySearchSelect.svelte` | F2: `searchText` include simbolo (€,$). F3: include ISO-2 country codes + nomi nazione via `Intl.DisplayNames`. F4: `selectedItem` snippet mostra simbolo. F8: rimossa prop `compact`, rendering sempre compact. |
| `FxPairAddModal.svelte` | F7: `oncreated` ora passa `{base, quote, hasRealProvider}`. F8: rimosso `compact={true}`. |
| `fx/+page.svelte` | F1: DateRangePicker `w-full xl:w-auto`, currency filters raggruppati. F5: testo bottoni `hidden xl:inline`. F6: `delete_all: true`. F7: auto-sync dopo creazione. F9: filtri intelligenti + swap + esclusione valuta altro filtro. |
| `SettingCurrency.svelte` | F8: rimosso `compact={true}`. |
| `GlobalSettingsTab.svelte` | F8: rimosso `compact={true}`. |
| `currencyStore.ts` | F3: aggiunto `country_codes: string[]` a `CurrencyInfo` + fallback + mapping da API. |

### Verifiche

- `./dev.py front check` — 0 errori, 0 warning
- `./dev.py front build` — ✅
- `./dev.py test -v utils currency-utils` — 12/12 passed
- `./dev.py api sync` — OpenAPI + client rigenerati con `delete_all` e `country_codes`

---

## Bug Fix Round 2 (4 Marzo 2026 — secondo giro)

### F10 — DateRangePicker: max-width + centratura blocchi ✅
**Problema**: Quando i filtri valuta vanno sotto il DateRangePicker (tablet), il picker si espande a tutta la larghezza e diventa deforme. Filtri e azioni non centrati tra loro.
**Fix**: `max-w-md` sul wrapper DateRangePicker. Container filtri passa a `flex-col xl:flex-row` con `items-center`. Azioni `flex-row xl:grid` centrate.
**File**: `frontend/src/routes/(app)/fx/+page.svelte`

### F11 — Tooltip su label troncati ✅
**Problema**: Le label delle valute nel dropdown vengono troncate con `...` ma non c'è modo di vedere il nome completo.
**Fix**: `title={option.label}` sui div con `truncate`, sia in `item` che `selectedItem` snippet.
**File**: `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte`

### F12 — Auto-sync: spinner nella modale ✅
**Problema**: La modale Add Pair si chiudeva subito e l'auto-sync avveniva in background, richiedendo un refresh.
**Fix**: Spostato auto-sync dentro `FxPairAddModal.handleSave()`. Dopo il save, se ha provider reali, mostra `RotateCcw animate-spin` + "Syncing..." sul bottone. Cancel disabilitato durante sync. Modale chiude solo dopo sync completato (o fallito silenziosamente). Parent (`handlePairCreated`) fa solo reload senza sync.
**File**: `FxPairAddModal.svelte` (+ `dateStart`/`dateEnd` props), `fx/+page.svelte`

### F13 — Ricerca "unite"→"United Kingdom" non funziona
**Problema**: L'utente conferma che "unit" trova GBP ma "unite" no. Probabilmente `Intl.DisplayNames` funziona, ma c'è un bug nella costruzione del `searchText` o nel filtro.
**Stato**: 🔍 Da investigare — il filtro `SearchSelect` usa `.includes()` che è substring match, quindi "unite" dovrebbe matchare "United Kingdom". Probabile che `Intl.DisplayNames` non risolva tutti i codici ISO-2 o che il `searchText` non venga costruito correttamente. Investigare nel browser.

### F15 — Layout programmatico con ResizeObserver ✅
**Problema**: I breakpoint CSS causavano stati intermedi incoerenti (filtri wrappati con azioni 2×2, oscillazione tra layout). Il `flex-wrap` creava zone di overlap tra stati CSS e stati logici.
**Fix**: Riscritta completamente la filter bar con approccio 100% programmatico:
- **ResizeObserver** misura `contentRect.width` del container (esclude padding 32px + border 2px)
- **3 layout modes** (`wide`, `tablet`, `mobile`) determinati da soglie fisse, NO `flex-wrap`
- **`showActionLabels`** flag indipendente per testo bottoni
- Ogni stato disegna una struttura diversa:
  - **wide** (≥936 contentRect ≈ 970px box): `flex-row` container, filtri `flex-row` + azioni `grid 2×2`
  - **tablet** (≥601 contentRect ≈ 635px box): `flex-row` container, filtri `flex-col` (stacked) + azioni `grid 2×2`
  - **mobile** (<601 contentRect): `flex-col` container centrato, azioni `flex-row`
- Labels visibili ≥686 contentRect (≈720px box)
- Il file è stato completamente convertito da Svelte 4 (`$:`) a **Svelte 5 runes** (`$state`, `$derived`, `$effect`)
**File**: `frontend/src/routes/(app)/fx/+page.svelte`

### F16 — DateRangePicker calendario verticale troppo presto ✅
**Problema**: Il popup calendario a 2 mesi andava verticale anche con spazio orizzontale sufficiente, perché usava `flex-wrap`.
**Fix**: Cambiato da `flex flex-wrap` a `flex flex-col sm:flex-row` — i 2 mesi sono affiancati sopra sm (640px), verticali solo su mobile stretto. Popup centrato con `left-1/2 -translate-x-1/2` su mobile, `left-0` su sm+.
**File**: `frontend/src/lib/components/ui/DateRangePicker.svelte`

### F17 — Allineamento tablet: filtri centrati a sinistra, azioni a destra ✅
**Problema**: In tablet, datepicker e currency filters non erano centrati tra loro, e le azioni non erano allineate a destra né centrate verticalmente.
**Fix**: Container tablet/wide usa `items-center justify-between` — filtri a sinistra, azioni a destra, centrati verticalmente. Filtri in tablet usano `flex-col items-center` per centrare datepicker e currency orizzontalmente tra loro come blocco.
**File**: `frontend/src/routes/(app)/fx/+page.svelte`

---

## F14 — Utilities API: Localizzazione con lingua frontend 📋

### Analisi Backend

**Stato attuale**:
- `GET /currencies?language=it` → nomi valute in italiano ✅ (Babel `get_currency_name()`)
- `GET /countries?language=it` → nomi paesi in italiano ✅ (Babel `Locale.territories`)
- `GET /currencies/normalize` → `language` param per fuzzy match ✅
- `GET /countries/normalize` → **MANCA** parametro `language` ❌ (fallback sempre inglese)
- `GET /sectors` → nomi settori hardcoded in inglese ❌ (non localizzabili senza dizionario)

**Problemi backend**:
1. `normalize_country` non accetta `language` — usa solo pycountry (inglese). Dovrebbe accettare nomi in tutte le lingue supportate via Babel.
2. `list_currencies` è ora cachata con `@lru_cache` ma la cache ignora la lingua (costruisce la mappa flag/countries una sola volta). Le funzioni `_build_currency_to_flag_map()` e `_build_currency_to_countries_map()` sono indipendenti dalla lingua, ma `list_currencies()` chiama `get_currency_name(code, locale=locale)` ad ogni chiamata — OK, non cachata.
3. I settori (`FinancialSector`) sono enum con nomi inglesi. Per localizzarli serve un dizionario i18n.

### Analisi Frontend

**Stato attuale**:
- `currencyStore.ts` chiama `GET /currencies` senza parametro `language` → sempre inglese.
- Il currency store è un singleton session-level (`loaded` flag). Se l'utente cambia lingua, lo store non si ricarica.

**Cosa serve**:
1. **Passare la lingua corrente** dall'utente alle API utilities.
2. **Invalidare la cache** del `currencyStore` quando l'utente cambia lingua.
3. **Sottoscrivere** `currentLanguage` store e ri-caricare quando cambia.

### Piano di implementazione

**Step 1 — Backend: `normalize_country` con lingua** (bassa complessità)
- Aggiungere `language: str = Query("en")` a `normalize_country`
- Usare `Locale(language).territories` per matchare nomi in altre lingue
- Es: `GET /countries/normalize?name=Germania&language=de` → `DEU`

**Step 2 — Frontend: passare lingua al `currencyStore`** (media complessità)
- `ensureCurrenciesLoaded(language: string)` accetta la lingua
- Se la lingua cambia rispetto all'ultima caricata → invalida e ricarica
- Sottoscrivere `currentLanguage` nei componenti che usano il store
- Il CurrencySearchSelect deve reagire al cambio lingua

**Step 3 — Backend: settori localizzati** (bassa complessità, opzionale)
- Aggiungere un dizionario i18n per i settori (EN, IT, FR, ES)
- `GET /sectors?language=it` → nomi in italiano

**Step 4 — Frontend: country store** (opzionale)
- Creare `countryStore.ts` simile a `currencyStore.ts`
- Usato da futuri componenti (es. country picker per broker)

### Note
- La ricerca per nazione nel CurrencySearchSelect usa `Intl.DisplayNames` del browser (lingua del browser, non dell'app). Per coerenza, dovrebbe usare la lingua dell'app. L'opzione migliore: il backend include i nomi dei paesi nella risposta `GET /currencies`, oppure il frontend usa il `countryStore` per risolvere i nomi.
- Decisione: usare backend per coerenza (singola fonte di verità). Aggiungere `country_names: list[str]` a `CurrencyListItem` nel backend, con nomi nella lingua richiesta via Babel.
