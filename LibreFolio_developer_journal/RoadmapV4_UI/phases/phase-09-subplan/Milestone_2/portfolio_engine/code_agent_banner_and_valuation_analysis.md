# Portfolio Engine — Banner & Valuation Analysis

**Data:** 2026-06-19  
**Autore:** Claude Sonnet 4.6  
**Riferimento:** `portfolio_engine.py`, `schemas/portfolio.py`, `dashboard/+page.svelte`, `assets/[id]/+page.svelte`, `fx/[pair]/+page.svelte`

---

## 1. Analisi fix matematica: transaction-implied valuation

### Problema

Uno scenario comune: BTP acquistato in collocamento primario (o qualsiasi asset comprato prima che sia disponibile il primo prezzo storico). La transazione BUY abbassa la cash, ma `_market_value_for()` restituisce `None` → `market_value += 0` → NAV crolla artificialmente.

### Dove si trova il problema

**File:** `backend/app/services/portfolio_engine.py`  
**Funzione:** `DailyStateBuilder._market_value_for()` (riga ~565)

```python
def _market_value_for(self, asset_id, qty, dt):
    prices = self.price_map.get(asset_id)
    if not prices:
        return None, False, False, None   # ← asset detenuto, NAV crolla

    result = self._price_on_date(prices, dt)
    if result is None:
        return None, False, False, None   # ← price map vuota per quella data
```

### Regola proposta: tre livelli di valutazione

```text
Priorità 1 — MARKET_PRICE
  PriceHistory <= data esiste → usa prezzo di mercato × FX
  (comportamento attuale)

Priorità 2 — TRANSACTION_IMPLIED
  Nessun PriceHistory <= data MA asset detenuto con WAC disponibile:
  → implied_market_value = open_cost_basis già calcolato (WAC × qty convertito)
  Non ricalcolare: riusare il valore già presente in _compute_open_cost_basis()

Priorità 3 — STALE_MARKET_PRICE
  Già gestita con STALE_PRICE_THRESHOLD_DAYS = 7
  (flag is_stale = True, ma valore calcolato normalmente)

Priorità 4 — MISSING
  Nessun prezzo, nessun WAC, nessun BUY → NAV incompleto
```

### Formula TRANSACTION_IMPLIED

**Preferibile:** usare `open_cost_basis` già calcolato da `_compute_open_cost_basis()` — evita doppie conversioni FX e rispetta già `quote_base_quantity` attraverso il WAC.

**Alternativa (solo se WAC non disponibile):** implied price dal primo BUY:
```python
implied_price = abs(buy_tx.amount) / buy_tx.quantity * (quote_base or 1)
```
⚠️ Attenzione: il BUY amount include commissioni se non separato. Preferire WAC.

### File/funzioni da modificare

| File | Funzione | Modifica |
|------|----------|---------|
| `portfolio_engine.py` | `DailyStateBuilder._market_value_for()` | Aggiungere fallback TRANSACTION_IMPLIED |
| `portfolio_engine.py` | `DailyStateBuilder.build()` | Passare `wac_result` per il fallback |
| `schemas/portfolio.py` | `MissingPriceAsset` | Aggiungere `valuation_source: PriceSource` |
| `schemas/portfolio.py` | Nuovo enum `PriceSource` | `MARKET_PRICE`, `TRANSACTION_IMPLIED`, `STALE_MARKET_PRICE`, `MISSING` |

### DTO da aggiungere

```python
class PriceSource(str, Enum):
    MARKET_PRICE = "MARKET_PRICE"
    TRANSACTION_IMPLIED = "TRANSACTION_IMPLIED"
    STALE_MARKET_PRICE = "STALE_MARKET_PRICE"
    MISSING = "MISSING"
```

Aggiungere `valuation_source: PriceSource` a `MissingPriceAsset` (già include `open_cost_basis`) e a `DailyPortfolioState` per tracking interno.

### Signature modificata

```python
def _market_value_for(
    self, asset_id: int, qty: Decimal, dt: date_type, wac_val: Decimal | None = None
) -> tuple[Decimal | None, PriceSource, str | None]:
    """
    Returns: (value_in_target_ccy, source, missing_fx_pair)
    """
```

### Test minimi

```
test_transaction_implied_no_price_history
  → BUY 100 nominale a 100 EUR, no PriceHistory, WAC = 100 EUR
  → market_value = 100 EUR (TRANSACTION_IMPLIED)
  → NAV non crolla

test_transaction_implied_with_quote_base
  → BTP: qty=10000 nominale, WAC=98.5 EUR/100 nominale
  → implied_value = WAC × qty = 98.5 × 100 = 9850 EUR

test_market_price_overrides_implied
  → giorno T+7: PriceHistory finalmente disponibile
  → fallback a MARKET_PRICE, TRANSACTION_IMPLIED abbandonato

test_missing_no_wac_no_price
  → asset senza WAC (transfer senza cost_basis_override, senza BUY)
  → PriceSource.MISSING
```

---

## 2. Analisi banner esistenti (asset detail + FX detail)

### Asset Detail — `frontend/src/routes/(app)/assets/[id]/+page.svelte`

**Banner implementati:**

| Banner | Trigger | Severità colore | CTA |
|--------|---------|----------------|-----|
| Archived | `assetInfo.active === false` | Amber ⚠️ | Nessuna |
| Error generico | `error` string | Amber ⚠️ | [×] close |
| Range starts before data | `dateStart < firstDataDate` | Sky 📊 (info) | Nessuna (solo info) |
| FX pair status × N | `requiredFxPairs.filter(p.status !== 'ok')` | Amber (missing/no-data) o Sky (partial-gap) | [Add FX pair] / [↻ Sync] / [→ FX detail] |

**Dati backend usati:**
- `assetInfo.active` → `GET /assets/{id}/info` → `FAinfoResponse.active`
- `chartData[0].date` → primo punto della serie prezzi
- `requiredFxPairs[i].status` → calcolato client-side da `currencyGraphStore`, confrontando le coppie richieste con quelle disponibili

**Pattern riusabili:**
- Banner multi-FX separati per pair (non aggregati): chiaro ma verbose
- CTA inline contestuale (add / sync / navigate) ben collegata all'azione
- Distinzione amber vs sky: amber = bloccante/mancante, sky = informativo/parziale
- Etichetta asset nell'FX banner (disambigua "per quale asset")

### FX Detail — `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

**Banner implementati:**

| Banner | Trigger | Colore | CTA |
|--------|---------|--------|-----|
| Error | `error` string | Amber | [×] close |
| Range starts before data | `rangeStartsBeforeData` | Sky | Nessuna |
| Stale gradient | `lineData[i].staleDays > 0` | Gradient sul grafico | Nessuna visiva |
| No data (inline chart) | `chartData.length === 0` | Inline nel chart area | [Insert manually] |

**Dati backend usati:**
- `p.backward_fill_info.days_back` → da `FXRateResponse` (ogni punto)
- `p.backward_fill_info.fx_days_back` → FX secondario
- `staleDays` derivato client-side come `max(days_back, fx_days_back)`

**Pattern riusabili:**
- `BackwardFillInfo` come segnale per stale data — pattern già maturo
- Stale gradient visivo nel chart (senza banner separato) — meno invasivo
- `staleDays` come numero grezzo esposto → il frontend decide la soglia

---

## 3. Stato attuale banner dashboard portfolio

### Cosa mostra oggi

**File:** `frontend/src/routes/(app)/dashboard/+page.svelte` (righe 412–431)

| Banner | Dato backend | Campo schema |
|--------|-------------|-------------|
| Missing prices (asset names) | `summary.missing_price_assets[].name` | `List[MissingPriceAsset]` |
| Missing FX pairs | `summary.missing_fx_pairs[].pair` | `List[WACMissingPairInfo]` |

### Cosa manca

1. **Stale prices** — `DataQualityReport.stale_prices` esiste nel DTO ma non è mai popolato né mostrato
2. **NAV incompleto** — `DataQualityReport.incomplete_nav_dates` non mostrato
3. **In-transit cost basis warnings** — non mostrati
4. **Share mismatch** — non mostrato
5. **data_quality object** — `PortfolioSummary.data_quality` è popolato ma **non usato nel frontend**
6. **Severity** — tutti i warning hanno lo stesso stile amber, nessuna distinzione critico/informativo
7. **CTA contestuale** — nessuna: "missing price" mostra solo i nomi, senza link all'asset né al provider

### Cosa è vecchio/fallato

- Il banner missing prices mostra `.map((a) => a.name).join(', ')` → **lista flat, non cliccabile**, non scala con molti asset
- Il banner FX pairs mostra solo le coppie, senza info su quali asset ne dipendono
- Non c'è banner per `TRANSACTION_IMPLIED` (assente nel sistema attuale)
- Non c'è banner per allocation/performance calcolate su NAV parziale

---

## 4. Scenari da coprire nel nuovo sistema banner

| Scenario | Severity | Impatto | CTA consigliata |
|----------|----------|---------|----------------|
| Missing price, senza cost basis | ERROR 🔴 | NAV crolla, allocation errata, performance distorta | → aggiungi almeno un prezzo manuale |
| Missing price, TRANSACTION_IMPLIED usato | WARNING 🟡 | NAV stimato (non di mercato), allocation approssimata | → aggiungi prezzo di mercato |
| Stale market price (> 7gg) | WARNING 🟡 | NAV usa prezzo vecchio, può essere impreciso | → ↻ sync provider |
| Missing FX per market value | ERROR 🔴 | Market value escluso, NAV sottostimato | → aggiungi coppia FX |
| Missing FX per cost basis / WAC | WARNING 🟡 | Book value incompleto, UGL errato | → aggiungi coppia FX |
| Asset in transit senza prezzo | WARNING 🟡 | in_transit_asset_mv = 0, NAV sottostimato | → aggiungi prezzo |
| Asset in transit con fallback cost basis | INFO 🔵 | in_transit_book_value stimato (non da CBO) | nessuna |
| Linked tx rotta (pair non trovato) | WARNING 🟡 | Classificato come normal tx, possibile ECF errato | → verifica transazioni |
| Share mismatch broker linked | INFO 🔵 | In-transit usa share sorgente, warning nei log | → verifica configurazione broker |
| NAV incompleto (missing price) | ERROR 🔴 | Performance distorta, allocation % errata | → vedi missing prices |
| Allocation su NAV parziale | WARNING 🟡 | % allocation distorte | implicit da NAV incompleto |
| Performance su NAV parziale | WARNING 🟡 | TWRR/MWRR/ROI potenzialmente errati | implicit da NAV incompleto |
| MWRR non calcolabile | INFO 🔵 | Mostra None (già gestito) | nessuna |
| Asset manuale valorizzato a costo | INFO 🔵 | market_value = cost basis, UGL = 0 | → aggiorna prezzo manuale |
| Asset manuale senza valorizzazione | WARNING 🟡 | Escluso da NAV | → inserisci prezzo manuale |

---

## 5. Proposta modello banner unificato

### DTO: `DataQualityIssue`

```python
class IssueSeverity(str, Enum):
    ERROR = "error"      # NAV significativamente errato/incompleto
    WARNING = "warning"  # NAV parzialmente impreciso
    INFO = "info"        # Informativo, nessun impatto critico

class IssueCode(str, Enum):
    MISSING_PRICE         = "MISSING_PRICE"
    TRANSACTION_IMPLIED   = "TRANSACTION_IMPLIED"
    STALE_PRICE           = "STALE_PRICE"
    MISSING_FX_MARKET     = "MISSING_FX_MARKET"
    MISSING_FX_COST_BASIS = "MISSING_FX_COST_BASIS"
    IN_TRANSIT_NO_PRICE   = "IN_TRANSIT_NO_PRICE"
    IN_TRANSIT_CB_FALLBACK = "IN_TRANSIT_CB_FALLBACK"
    LINKED_TX_BROKEN      = "LINKED_TX_BROKEN"
    SHARE_MISMATCH        = "SHARE_MISMATCH"
    NAV_INCOMPLETE        = "NAV_INCOMPLETE"
    MWRR_NOT_CALCULABLE   = "MWRR_NOT_CALCULABLE"

class DataQualityIssue(BaseModel):
    code: IssueCode
    severity: IssueSeverity
    message_i18n_key: str                   # es. "dataQuality.missingPrice"
    affected_asset_ids: List[int] = []
    affected_fx_pairs: List[str] = []
    affected_dates: List[date] = []
    cta_action: Optional[str] = None        # es. "add_price", "add_fx_pair", "sync_provider"
    cta_target: Optional[str] = None        # es. asset_id o fx_slug
    details: Optional[str] = None
```

### Integrazione con DataQualityReport

Sostituire i campi flat attuali con una lista unificata:

```python
class DataQualityReport(BaseModel):
    issues: List[DataQualityIssue] = []
    # campi legacy mantenuti per backward compat, derivati da issues:
    missing_price_assets: List[MissingPriceAsset] = []
    stale_prices: List[StalePriceAsset] = []
    missing_fx_pairs: List[WACMissingPairInfo] = []
    incomplete_nav_dates: List[date] = []
    warnings: List[str] = []
```

### Frontend: componente `DataQualityBanner.svelte`

Pattern uguale all'asset detail:
- Un banner per `IssueCode`, non uno per asset
- Amber = ERROR + WARNING, Sky = INFO
- CTA inline: pulsante per azione (navigate/sync/add)
- Accordion se `affected_asset_ids.length > 3` (mostra "3 asset + 2 altri")

```svelte
{#each issues.filter(i => i.severity !== 'info') as issue}
  <div class="{issue.severity === 'error' ? 'amber' : 'sky'} banner">
    {$_(`dataQuality.${issue.code}`)}
    {#if issue.cta_action === 'add_price'}
      <a href="/assets/{issue.cta_target}">→ {$_('dataQuality.addPrice')}</a>
    {/if}
    {#if issue.affected_asset_ids.length > 0}
      <!-- expandable list -->
    {/if}
  </div>
{/each}
```

---

## Raccomandazione finale

**Priorità 1 — TRANSACTION_IMPLIED valuation (backend):**
- Modifica `DailyStateBuilder._market_value_for()` per usare `open_cost_basis` come fallback
- Aggiungere `PriceSource` enum e campo `valuation_source` a `DailyPortfolioState`
- Test critici: BTP in collocamento, P2P loan, asset pre-quotazione

**Priorità 2 — DataQualityIssue DTO unificato:**
- Introduce `IssueCode` + `IssueSeverity` + `DataQualityIssue` in `schemas/portfolio.py`
- Popola in `DerivedViewsBuilder.build_data_quality_report()` (oggi non costruisce `DataQualityReport` aggregato)
- Non serve api sync se i campi legacy sono mantenuti

**Priorità 3 — DataQualityBanner.svelte:**
- Componente unico che sostituisce i due banner separati in `+page.svelte`
- Legge da `summary.data_quality.issues`
- Stile coerente con asset detail (amber/sky, CTA inline)

### File da modificare

| File | Modifica |
|------|---------|
| `backend/app/services/portfolio_engine.py` | `_market_value_for()` + fallback TRANSACTION_IMPLIED |
| `backend/app/schemas/portfolio.py` | `PriceSource` enum, `DataQualityIssue`, aggiornare `DataQualityReport` |
| `backend/app/services/portfolio_service.py` | propagare `PriceSource` nel `DataQualityReport` restituito |
| `frontend/.../dashboard/AllocationHistoryChart.svelte` | Nessuna modifica |
| `frontend/.../dashboard/+page.svelte` | Sostituire banner inline con `<DataQualityBanner>` |
| `frontend/.../dashboard/DataQualityBanner.svelte` | **Nuovo** — componente banner unificato |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Chiavi `dataQuality.*` per ogni IssueCode |

### Test minimi

```
backend:
  test_transaction_implied_no_price
  test_transaction_implied_quote_base
  test_market_price_overrides_implied_after_first_price
  test_data_quality_issue_list_built_correctly
  test_issue_severity_error_for_missing_price

frontend:
  e2e: dashboard_shows_dq_banner_missing_price
  e2e: dashboard_shows_dq_banner_stale_price
  e2e: dashboard_no_banner_when_no_issues
```

### Domande aperte residue

1. **TRANSACTION_IMPLIED nel report:** mostrare come "NAV stimato" o "asset a costo"? I due concetti sono diversi per l'utente finale.
2. **Soglia stale:** 7 giorni è ok per asset liquidi (ETF), ma troppo aggressivo per P2P loan o immobili. Configurabile per asset_type?
3. **CTA "add price":** navigare direttamente a `/assets/{id}` con l'editor aperto o mostrare un quick-insert inline nel banner?
4. **Aggregazione issue:** raggruppare per code+severity o mostrare un issue per asset? Con portafogli da 50+ asset, la granularità per-asset può essere verbosa.
5. **MWRR not calculable:** today mostra `None` silenziosamente — merita un INFO banner esplicito?
