# Plan: Fix Valute Storiche, Layout Filter Bar FX (E+), Bandiere Valute

**Data creazione**: 4 Marzo 2026
**Status**: ✅ COMPLETATO (4 Marzo 2026)
**Durata stimata**: ~2-3 giorni
**Dipendenze**: Phase 5 FX pages funzionanti, plan-fxUiRefinementsRound2 Steps 1-7,9 completati
**Riferimenti**:
- `plan-phase05Fx.prompt.md` (piano principale Phase 5)
- `plan-fxUiRefinementsRound2.prompt.md` (refinements round 2)
- `plan-manualFxProvider.prompt.md` (provider MANUAL sentinel)

---

## Contesto

Tre problemi correlati emersi durante l'uso della pagina FX:

1. **Mismatch valute storiche**: Il frontend mostra ~300 valute (da Babel, include storiche come ADP/AFA/ATS) nel `CurrencySearchSelect`, ma il backend le rifiuta perché `pycountry.currencies.lookup()` accetta solo valute ISO 4217 attive (~170). L'utente seleziona ADP → il POST a `/fx/providers/pair-sources` fallisce con `"Invalid currency code: 'ADP'"`.

2. **Layout filter bar brutto a dimensioni intermedie**: Il grid `grid-cols-[auto_1fr_auto]` crea enormi spazi vuoti nella colonna centrale `1fr` a dimensioni tablet/desktop stretto. I 4 bottoni azione in griglia 2×2 sono poco leggibili.

3. **Bandiere valuta hardcoded**: `FxCard.svelte` ha una mappa statica di ~27 valute→emoji flag. Il `CurrencySearchSelect` mostra solo il simbolo (€, $), non la bandiera. L'endpoint `GET /currencies` non restituisce `flag_emoji`.

---

## Step 1: Riscrivere `list_currencies()` con pycountry come Source-of-Truth

### Problema

`list_currencies()` in `backend/app/utils/currency_utils.py` itera `locale.currencies.keys()` (Babel) che include ~300 codici, molti storici (ADP, AFA, ATS, ARA, etc.). La validazione nel backend (`_validate_currency_code_cached` in `backend/app/schemas/common.py`) usa `pycountry.currencies.lookup()` che ha solo ~170 valute attive. Risultato: il frontend offre valute che il backend rifiuta.

### Soluzione

Usare **pycountry come unica fonte** per l'elenco delle valute attive. Babel viene usato **solo per tradurre** nome e simbolo.

### Modifiche

#### 1.1 — `backend/app/utils/currency_utils.py` → `list_currencies()`

```python
import pycountry
from backend.app.schemas.common import CRYPTO_CURRENCIES

def list_currencies(language: str = "en") -> List[dict]:
    """
    List all active currencies (ISO 4217 via pycountry + crypto) with localized names and symbols.
    """
    locale = get_babel_locale(language)
    currencies = []

    # 1. Active ISO 4217 currencies from pycountry (source-of-truth)
    for currency in sorted(pycountry.currencies, key=lambda c: c.alpha_3):
        code = currency.alpha_3
        try:
            name = get_currency_name(code, locale=locale) or currency.name
            symbol = get_currency_symbol(code, locale=locale) or code
        except Exception:
            name = currency.name
            symbol = code

        flag = currency_flag_map.get(code, "🏳️")  # from Step 3
        currencies.append({
            "code": code,
            "name": name,
            "symbol": symbol,
            "flag_emoji": flag,
        })

    # 2. Crypto currencies (from CRYPTO_CURRENCIES dict in common.py)
    for code, name in sorted(CRYPTO_CURRENCIES.items()):
        currencies.append({
            "code": code,
            "name": name,
            "symbol": code,
            "flag_emoji": "🪙",
        })

    return currencies
```

#### 1.2 — Test: ogni valuta restituita deve passare validazione

Creare `backend/test_scripts/test_currency_list_validation.py`:

```python
"""Test that every currency from list_currencies() is accepted by the validator."""
import pytest
from backend.app.utils.currency_utils import list_currencies
from backend.app.schemas.common import _validate_currency_code_cached

def test_all_listed_currencies_pass_validation():
    """Every code from list_currencies must be accepted by _validate_currency_code_cached."""
    currencies = list_currencies("en")
    assert len(currencies) > 150, f"Expected 150+ currencies, got {len(currencies)}"

    failures = []
    for c in currencies:
        try:
            _validate_currency_code_cached(c["code"])
        except ValueError as e:
            failures.append(f"{c['code']}: {e}")

    assert not failures, f"Validation failures:\n" + "\n".join(failures)

def test_crypto_currencies_included():
    """Crypto currencies from CRYPTO_CURRENCIES should appear in the list."""
    from backend.app.schemas.common import CRYPTO_CURRENCIES
    currencies = list_currencies("en")
    codes = {c["code"] for c in currencies}
    for crypto_code in CRYPTO_CURRENCIES:
        assert crypto_code in codes, f"Crypto {crypto_code} missing from list_currencies()"

def test_no_historic_currencies():
    """Historic currencies like ADP, AFA, ATS should NOT appear."""
    currencies = list_currencies("en")
    codes = {c["code"] for c in currencies}
    historic = ["ADP", "AFA", "ATS", "ARA", "ARL", "BEF", "DEM", "FRF", "ITL", "ESP"]
    for h in historic:
        assert h not in codes, f"Historic currency {h} should not be in the list"
```

**File coinvolti:**
- `backend/app/utils/currency_utils.py` — riscrittura `list_currencies()`
- `backend/test_scripts/test_currency_list_validation.py` — nuovo test

---

## Step 2: Layout Filter Bar "Integrated Compact Bar" (E+)

### Problema

Il layout attuale (riga 312-397 di `frontend/src/routes/(app)/fx/+page.svelte`) usa `grid-cols-1 lg:grid-cols-[auto_1fr_auto]` con 3 colonne. A dimensioni intermedie la colonna centrale `1fr` si espande troppo creando enormi spazi vuoti. Inoltre il secondo filtro valuta è nascosto con `{#if}` finché non si seleziona il primo, il che confonde l'utente.

### Layout Scelto: Alternativa E+ — "Integrated Compact + Adaptive Actions"

Il concetto: filtri in flex-wrap a sinistra, azioni a destra. **Desktop largo**: layout quasi identico all'attuale con azioni in griglia 2×2 (che funziona bene con spazio). **Tablet**: azioni impilate verticalmente a destra per risparmiare spazio. **Mobile**: tutto stacked verticalmente. Il secondo currency filter è **sempre visibile** ma **disabilitato** (con opacità ridotta) finché non si seleziona il primo.

```
Nota: [DateRangePicker] include nativamente i preset (1W,1M,3M,6M,1Y,2Y,Custom) su riga 1
e il selettore date (📅 From──To) su riga 2. È un unico componente.

DESKTOP LARGO (≥1280px) — filtri + azioni 2×2 come oggi, ma senza 1fr sprecato:
┌──────────────────────────────────────────────────────────────────────────────┐
│ ┌─DateRangePicker────────────────────┐                        ║ [Abs/%][⚙️] │
│ │ [1W 1M ▌3M▐ 6M 1Y 2Y Custom ⓘ]    │    [🇪🇺 C1] [🇺🇸 C2 dis] ║  [⟳]  [↻]  │
│ │ [📅 From Dec 04 ── To Mar 04]      │                        ║             │
│ └────────────────────────────────────┘                        ║             │
└──────────────────────────────────────────────────────────────────────────────┘
 ← filtri: flex-wrap orizzontale ──────────────────────→  ↑ azioni: griglia 2×2

TABLET (768–1279px) — filtri wrappano, azioni colonna verticale a destra:
┌──────────────────────────────────────────────────┬─────────┐
│ ┌─DateRangePicker──────────────────┐             │ [Abs/%] │
│ │ [1W 1M ▌3M▐ 6M 1Y 2Y Custom ⓘ] │             │  [⚙️]   │
│ │ [📅 From Dec 04 ── To Mar 04]   │             │  [⟳]   │
│ └──────────────────────────────────┘             │  [↻]   │
│ [🇪🇺 C1]  [🇺🇸 C2 (disabled se C1 vuoto)]      │         │
└──────────────────────────────────────────────────┴─────────┘

MOBILE (<768px) — tutto stacked, azioni come riga orizzontale in fondo:
┌──────────────────────────────┐
│ ┌─DateRangePicker──────────┐ │
│ │ [1W 1M ▌3M▐ 6M 1Y 2Y…]  │ │
│ │ [📅 From ── To]          │ │
│ └──────────────────────────┘ │
│ [🇪🇺 C1] [🇺🇸 C2]           │
│ [Abs/%][⚙️][⟳][↻]           │
└──────────────────────────────┘
```

### Modifiche

#### 2.1 — `frontend/src/routes/(app)/fx/+page.svelte` — Filter bar

**Struttura HTML:**

```svelte
<!-- Filter Bar: E+ layout — filters flex-wrap left, actions adaptive right -->
<div class="flex flex-col md:flex-row gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700">

    <!-- Left: Filters (flex-wrap, takes available space) -->
    <div class="flex-1 flex flex-wrap items-center gap-3 justify-center md:justify-start">
        <!-- DateRangePicker -->
        <DateRangePicker ... compact={true} />

        <!-- Currency Filter 1 -->
        <div class="w-40">
            <CurrencySearchSelect
                bind:value={filterCurrency1}
                includeAll={true}
                allowedCurrencies={configuredCurrencies}
                onchange={(v) => { filterCurrency1 = v; filterCurrency2 = ''; }}
            />
        </div>

        <!-- Currency Filter 2 — ALWAYS VISIBLE, disabled when C1 empty -->
        <div class="w-40 transition-opacity {filterCurrency1 ? '' : 'opacity-50'}">
            <CurrencySearchSelect
                bind:value={filterCurrency2}
                includeAll={true}
                allowedCurrencies={configuredCurrencies}
                disabled={!filterCurrency1}
                placeholder={$_('fx.filter.secondCurrency')}
            />
        </div>
    </div>

    <!-- Right: Actions — 2×2 grid on xl+, vertical column on md-lg, horizontal row on mobile -->
    <div class="shrink-0">
        <!-- Mobile: horizontal row -->
        <!-- Tablet (md-lg): vertical column -->
        <!-- Desktop xl+: 2×2 grid (same as current) -->
        <div class="flex flex-row md:flex-col xl:grid xl:grid-cols-2 gap-1.5
                    justify-center md:justify-start">
            <!-- Abs/% toggle -->
            <div class="flex rounded-lg border ... overflow-hidden">
                <button ...>Abs</button>
                <button ...>%</button>
            </div>
            <!-- Settings -->
            <button ... title={$_('fx.actions.settings')}>
                <Settings size={14} />
            </button>
            <!-- Sync All -->
            <button ... onclick={handleSyncAll} title={$_('fx.actions.syncAll')}>
                <RotateCcw size={14} />
            </button>
            <!-- Refresh All -->
            <button ... onclick={handleRefreshAll} title={$_('fx.actions.refreshAll')}>
                <RefreshCw size={14} />
            </button>
        </div>
    </div>
</div>
```

**Cambiamenti chiave:**
- Grid `grid-cols-[auto_1fr_auto]` → `flex flex-col md:flex-row` (nessuno spazio `1fr` sprecato)
- Azioni: `flex flex-row md:flex-col xl:grid xl:grid-cols-2` — 2×2 su desktop largo (≥1280), colonna verticale su tablet (768-1279), riga orizzontale su mobile (<768)
- Currency filter 2: rimuovere `{#if filterCurrency1}`, renderizzare sempre con `disabled={!filterCurrency1}` e `opacity-50` quando disabilitato
- Testo bottoni (`hidden xl:inline`): rimuovere, solo icone per compattezza. Tooltip via `title` basta.

**File coinvolti:**
- `frontend/src/routes/(app)/fx/+page.svelte` — riscrittura filter bar (righe 312-397)

---

## Step 3: Aggiungere `flag_emoji` via Babel `get_territory_currencies()` + `currencyStore`

### 3.1 — Backend: mapping valuta → bandiera con Babel

**Approccio**: usare `babel.numbers.get_territory_currencies(territory_iso2)` per costruire una mappa inversa `currency_code → country_iso2`. Per ogni paese (`pycountry.countries`), chiedere a Babel quale valuta è legal tender oggi → invertire in `{currency → country_iso2}` → convertire in flag emoji con `iso2_to_flag_emoji()`.

Casi speciali (poche eccezioni):
- **EUR**: usato in ~20 paesi, ma la bandiera "giusta" è 🇪🇺. Il mapping Babel darà un singolo paese (es. DE). Override: `EUR → 🇪🇺`.
- **XAF** (CFA franc BEAC): multi-paese Africa centrale → `🌍` o bandiera del primo paese
- **XOF** (CFA franc BCEAO): multi-paese Africa occidentale → `🌍` o bandiera del primo paese
- **XCD** (East Caribbean dollar): multi-paese → bandiera del primo paese

Queste eccezioni sono gestite con un piccolo dizionario di ~5 entry, non un hardcoding di 170 valute.

#### Modifiche a `backend/app/utils/currency_utils.py`:

```python
from functools import lru_cache
from babel.core import get_global
from backend.app.utils.geo_utils import iso2_to_flag_emoji
import pycountry

# Multi-country currency overrides (flag for the "representative" entity)
_CURRENCY_FLAG_OVERRIDES = {
    "EUR": "🇪🇺",   # European Union (not a single country)
    "XAF": "🌍",    # CFA franc BEAC — Central Africa
    "XOF": "🌍",    # CFA franc BCEAO — West Africa
    "XCD": "🌍",    # East Caribbean dollar
    "XPF": "🌍",    # CFP franc — French Pacific
}

@lru_cache(maxsize=1)
def _build_currency_to_flag_map() -> dict[str, str]:
    """
    Build mapping: currency_code → flag_emoji.

    Uses Babel's territory_currencies data to find which country uses each currency
    as legal tender, then converts country ISO-2 → flag emoji.

    Multi-country currencies (EUR, XAF, etc.) use explicit overrides.
    Crypto currencies use 🪙.

    Babel territory_currencies format: dict[territory_iso2] → list of tuples
    Each tuple: (currency_code, start_date_tuple, end_date_tuple_or_None, is_tender)
    Example: ('USD', (1792, 1, 1), None, True)
    - end=None means still active
    - tender=True means legal tender
    """
    currency_to_flag: dict[str, str] = {}

    # Start with overrides (they win over auto-detected)
    currency_to_flag.update(_CURRENCY_FLAG_OVERRIDES)

    # Get Babel's territory→currencies mapping
    territory_currencies = get_global('territory_currencies')

    # Iterate all countries from pycountry
    for country in pycountry.countries:
        iso2 = country.alpha_2
        entries = territory_currencies.get(iso2, [])

        for entry in entries:
            # entry is tuple: (code, start, end, tender)
            code, _start, end, tender = entry

            # Only current (end=None) and legal tender currencies
            if end is not None or not tender:
                continue

            # Don't override multi-country currencies already set
            if code not in currency_to_flag:
                currency_to_flag[code] = iso2_to_flag_emoji(iso2)

    # Add crypto
    from backend.app.schemas.common import CRYPTO_CURRENCIES
    for code in CRYPTO_CURRENCIES:
        currency_to_flag[code] = "🪙"

    return currency_to_flag
```

> **Nota implementativa**: Babel `get_global('territory_currencies')` restituisce un dict `{territory_iso2: list[tuple]}`. Ogni tupla è `(currency_code, start_date_tuple, end_date_tuple_or_None, is_tender)`. Esempio: `('USD', (1792, 1, 1), None, True)`. Filtrare per `end is None` (valuta corrente) e `tender=True` (legal tender). Il risultato copre ~165 valute automaticamente. Le ~5 multi-paese sono gestite da `_CURRENCY_FLAG_OVERRIDES`.

#### Modifiche a `backend/app/schemas/utilities.py`:

```python
class CurrencyListItem(BaseModel):
    """Single currency in the currency list."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="ISO 4217 currency code (e.g., USD, EUR)")
    name: str = Field(..., description="Currency name in requested language")
    symbol: str = Field(..., description="Currency symbol (e.g., $, €)")
    flag_emoji: str = Field("🏳️", description="Flag emoji of primary country using this currency")
```

#### Dopo le modifiche backend:

```bash
./dev.py api sync   # Rigenera OpenAPI + client Zodios
```

### 3.2 — Frontend: `currencyStore.ts`

Creare uno store module-level che carica le valute una sola volta per sessione e le espone a tutti i componenti.

**File**: `frontend/src/lib/stores/currencyStore.ts`

```typescript
/**
 * Currency Store — Session-level cache for currency data from GET /currencies.
 *
 * Loads once, then provides getCurrencyInfo(code) for any component.
 * Used by CurrencySearchSelect, FxCard, FxPairAddModal, etc.
 */
import { zodiosApi } from '$lib/api';

export interface CurrencyInfo {
    code: string;
    name: string;
    symbol: string;
    flag_emoji: string;
}

let allCurrencies: CurrencyInfo[] = [];
let currencyMap: Map<string, CurrencyInfo> = new Map();
let loaded = false;
let loading = false;
let loadPromise: Promise<void> | null = null;

/** Ensure currencies are loaded (idempotent, call from any component). */
export async function ensureCurrenciesLoaded(): Promise<void> {
    if (loaded) return;
    if (loadPromise) return loadPromise;

    loadPromise = (async () => {
        loading = true;
        try {
            const response = await zodiosApi.list_currencies_api_v1_utilities_currencies_get();
            allCurrencies = (response.items ?? []).map((c: any) => ({
                code: c.code,
                name: c.name,
                symbol: c.symbol,
                flag_emoji: c.flag_emoji ?? '🏳️',
            }));
            currencyMap = new Map(allCurrencies.map(c => [c.code, c]));
            loaded = true;
        } catch (e) {
            console.error('Failed to load currencies:', e);
        } finally {
            loading = false;
            loadPromise = null;
        }
    })();

    return loadPromise;
}

/** Get all currencies (empty array if not loaded yet). */
export function getAllCurrencies(): CurrencyInfo[] {
    return allCurrencies;
}

/** Get info for a specific currency code. Returns fallback if not found. */
export function getCurrencyInfo(code: string): CurrencyInfo {
    return currencyMap.get(code) ?? {
        code,
        name: code,
        symbol: code,
        flag_emoji: '🏳️',
    };
}

/** Check if currencies are loaded. */
export function isCurrenciesLoaded(): boolean {
    return loaded;
}

/** Check if currencies are currently loading. */
export function isCurrenciesLoading(): boolean {
    return loading;
}
```

### 3.3 — Frontend: Aggiornare `CurrencySearchSelect.svelte`

Sostituire la chiamata diretta API con import dal `currencyStore`. Usare `flag_emoji` come icona principale.

**Cambiamenti chiave:**
- Rimuovere `loadCurrencies()` e la chiamata API diretta
- Importare `ensureCurrenciesLoaded, getAllCurrencies` dal `currencyStore`
- In `$effect`, chiamare `ensureCurrenciesLoaded()` e poi `allCurrencies = getAllCurrencies()`
- Nel build delle `SelectOption`, usare `flag_emoji` come `icon` al posto del `symbol`
- Label: `"USD — US Dollar"`, sub-label o testo secondario: `"$"`

**Snippet item aggiornato:**
```svelte
{#snippet item(option)}
    <div class="flex items-center space-x-2 min-w-0">
        {#if option.icon}
            <span class="{compact ? 'text-base' : 'text-xl'} shrink-0">
                {option.icon}  <!-- flag_emoji: 🇺🇸 -->
            </span>
        {/if}
        <div class="min-w-0">
            <div class="{compact ? 'text-sm' : ''} font-medium text-gray-900 dark:text-gray-100">
                {option.value}
                {#if option.data?.symbol && option.data.symbol !== option.value}
                    <span class="text-gray-400 ml-1">{option.data.symbol}</span>
                {/if}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400 truncate">{option.label}</div>
        </div>
    </div>
{/snippet}
```

### 3.4 — Frontend: Aggiornare `FxCard.svelte`

Rimuovere la funzione hardcoded `currencyFlag()` (righe 98-108) e usare `getCurrencyInfo(code).flag_emoji` dal `currencyStore`.

```typescript
// BEFORE (righe 98-108):
function currencyFlag(code: string): string {
    const map: Record<string, string> = {
        EUR: '🇪🇺', USD: '🇺🇸', GBP: '🇬🇧', ... // 27 entry hardcoded
    };
    return map[code] || '💱';
}

// AFTER:
import { getCurrencyInfo, ensureCurrenciesLoaded } from '$lib/stores/currencyStore';

// In $effect o onMount:
ensureCurrenciesLoaded();

// Usage:
function currencyFlag(code: string): string {
    return getCurrencyInfo(code).flag_emoji;
}
```

**File coinvolti Step 3:**
- `backend/app/utils/currency_utils.py` — `_build_currency_to_flag_map()`, aggiornamento `list_currencies()`
- `backend/app/schemas/utilities.py` — `flag_emoji` field su `CurrencyListItem`
- `frontend/src/lib/stores/currencyStore.ts` — nuovo store (session-level cache)
- `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte` — usa currencyStore + flag_emoji
- `frontend/src/lib/components/fx/FxCard.svelte` — rimuove mappa hardcoded, usa currencyStore

---

## Ordine di Esecuzione

| # | Azione | Dipende da |
|---|--------|-----------|
| 1 | Step 3.1 — Backend: `_build_currency_to_flag_map()` + `flag_emoji` su schema | — |
| 2 | Step 1 — Backend: riscrittura `list_currencies()` con pycountry + crypto + flag | Step 3.1 |
| 3 | Step 1 test — Test validazione valute | Step 2 |
| 4 | `./dev.py api sync` | Step 2 |
| 5 | Step 3.2 — Frontend: `currencyStore.ts` | Step 4 |
| 6 | Step 3.3 — Frontend: `CurrencySearchSelect.svelte` aggiornato | Step 5 |
| 7 | Step 3.4 — Frontend: `FxCard.svelte` aggiornato | Step 5 |
| 8 | Step 2 — Frontend: Layout filter bar E+ | indipendente (può essere parallelo) |
| 9 | `./dev.py front check && ./dev.py front build` | Step 6-8 |
| 10 | `./dev.py test all` | Step 9 |

---

## Note Implementative

1. **Babel `get_global('territory_currencies')`**: restituisce un dict `{territory_iso2: list[tuple]}`. Ogni tupla è `(currency_code, start_date_tuple, end_date_tuple_or_None, is_tender_bool)`. Esempio: `('USD', (1792, 1, 1), None, True)`. Filtrare per `end is None` (valuta corrente) e `tender=True` (moneta a corso legale). Il risultato copre ~165 valute automaticamente. Le ~5 multi-paese sono gestite da `_CURRENCY_FLAG_OVERRIDES`.

2. **Secondo currency filter**: il `CurrencySearchSelect` ha già la prop `disabled`. Basta passare `disabled={!filterCurrency1}` e aggiungere `opacity-50` al wrapper. Quando l'utente resetta il primo filtro, il secondo si resetta a `''` (già gestito: `onchange={(v) => { filterCurrency1 = v; filterCurrency2 = ''; }}`).

3. **currencyStore vs chiamata diretta**: attualmente ogni `CurrencySearchSelect` fa una sua `GET /currencies` al mount. Con il `currencyStore` condiviso, la chiamata avviene una sola volta per sessione. Tutti i `CurrencySearchSelect` (FX list, FX detail, FxPairAddModal, Settings) e tutti i `FxCard` usano la stessa cache.

4. **Testo bottoni azione rimosso**: nella versione E+ i bottoni azione mostrano solo icone (con tooltip `title`). Il testo `hidden xl:inline` viene rimosso per compattezza. Ogni bottone ha larghezza fissa nella colonna verticale.

5. **`_CURRENCY_FLAG_OVERRIDES`**: dizionario con ~10 entry: 5 valute sovranazionali (EUR, XAF, XOF, XCD, XPF) + 5 valute principali dove il territorio alfabeticamente primo non è il paese "owner" (USD→US non American Samoa, INR→IN non Bhutan, NOK→NO non Bouvet Island, NZD→NZ non Cook Islands, ZAR→ZA non Lesotho). Il restante ~95% viene da Babel automaticamente.

---

## Riepilogo Implementazione (4 Marzo 2026)

### Backend

| File | Modifica |
|------|----------|
| `backend/app/utils/currency_utils.py` | Riscritta `list_currencies()` con pycountry come source-of-truth + crypto da `CRYPTO_CURRENCIES`. Aggiunto `_build_currency_to_flag_map()` con Babel `get_global('territory_currencies')` inverso. Aggiunto `_CURRENCY_FLAG_OVERRIDES` (10 entry: 5 sovranazionali + 5 major multi-territorio). |
| `backend/app/schemas/utilities.py` | Aggiunto `flag_emoji: str` su `CurrencyListItem`. |
| `backend/test_scripts/test_utilities/test_currency_utils.py` | **NUOVO** — 12 test: validazione coerenza, no storiche, crypto incluse, flag corrette per 28 valute principali, localizzazione. |
| `scripts/test_runner.py` | Aggiunto `utils_currency_utils()` + entry `"currency-utils"` in `TEST_REGISTRY["utils"]`. |
| `backend/test_scripts/test_api/test_fx_sync.py` | **FIX** `test_sync_auto_config_no_pairs`: usava `FXPairSourceItem` (priority obbligatoria) per cancellare, causando auto-reinserimento MANUAL sentinel. Fix: usa `FXDeletePairSourceItem` con `priority=None` per cancellare intere coppie. |

### Frontend

| File | Modifica |
|------|----------|
| `frontend/src/lib/stores/currencyStore.ts` | **NUOVO** — Store session-level: carica `GET /currencies` una sola volta, espone `ensureCurrenciesLoaded()`, `getAllCurrencies()`, `getCurrencyInfo(code)`. |
| `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte` | Usa `currencyStore` anziché chiamata API diretta. `flag_emoji` come icona, simbolo valuta come testo secondario. |
| `frontend/src/lib/components/fx/FxCard.svelte` | Rimossa mappa hardcoded `currencyFlag()` (27 entry), sostituita con `getCurrencyInfo(code).flag_emoji` dal `currencyStore`. |
| `frontend/src/routes/(app)/fx/+page.svelte` | Layout filter bar E+: `grid-cols-[auto_1fr_auto]` → `flex flex-col md:flex-row`. Azioni: `flex-row md:flex-col xl:grid xl:grid-cols-2`. Currency filter 2 sempre visibile con `disabled={!filterCurrency1}` e `opacity-50`. |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | **FIX CRITICO** — `handleRemoveProvider` cancellava l'intera coppia (ignorava `providerCode`). `handleSaveProviderOrder` usava "delete all + recreate" rischioso. Entrambi riscritti con `applyProviderDiff()`: (1) POST desired state (upsert su chiave base+quote+priority), (2) GET fresh state dal backend, (3) DELETE solo le entry che non corrispondono al desired. Ordine POST→GET→DELETE garantisce zero perdita dati. |
| `frontend/src/routes/(app)/fx/+page.svelte` (confirmDelete) | **FIX** — `confirmDelete` ora: (1) cancella provider sources con singolo delete senza priority, (2) cancella TUTTI i rate storici della coppia via `DELETE /fx/currencies/rate` con range 1900-2099. Prima mandava N delete items identici e aveva un TODO per i rate. Rimossa variabile `deleteAlsoRates` inutilizzata. Messaggio modale aggiornato per informare l'utente. |

### Comandi eseguiti

- `./dev.py api sync` — Rigenerato OpenAPI + client Zodios con `flag_emoji`
- `./dev.py front check` — 0 errori, 0 warning
- `./dev.py front build` — Build produzione riuscita
- `./dev.py test -v utils currency-utils` — 12/12 passed

### Bug collaterale risolto

Il test `test_sync_auto_config_no_pairs` falliva (expected 400, got 200) perché il provider MANUAL sentinel si auto-reinseriva dopo la cancellazione di ogni provider reale (comportamento corretto del backend). Il test cancellava con `FXPairSourceItem` (priority obbligatoria), ma il delete con priority specificata triggerava l'auto-reinserimento. Fix: usare `FXDeletePairSourceItem` con `priority=None` che cancella l'intera coppia senza auto-reinserimento (come da logica backend riga 958: "ONLY when deleting specific providers, NOT when deleting entire pair").

