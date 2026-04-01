# Plan: Phase 6 Step 3 — Round 11: Bug Mitigation + Scheduled Investment Redesign

Data: 2026-03-31
Post Round 10. Corregge 9 issue residui dal testing Round 10, suddivisi in **Piano A** (bug fix immediati) e **Piano B** (riprogettazione architetturale del provider `scheduled_investment`).

---

## §0 — Contesto e Stato

Round 10 ha implementato 12 item. Il testing manuale dell'utente ha rivelato:

| § | Item Round 10 | Stato post-test | Azione Round 11 |
|---|---------------|-----------------|-----------------|
| §1 | `list_assets` 500 — ProviderInputType → IdentifierType | ✅ Risolto | — |
| §2 | Cambio provider pulisce params | ✅ Risolto | — |
| §3 | DateRangePicker/SingleDatePicker scroll | ❌ Ancora rotto | Piano A §1 |
| §4 | Test "not supported" → warning giallo | ⚠️ Parziale: no wrap, manca test scheduled | Piano A §2 + Piano B §5 |
| §5 | Error summary inline vs tooltip | ✅ Funzionante (diversi come atteso) | — |
| §6 | Tooltip dblclick/long-press → clipboard | ❌ Non funziona | Piano A §3 |
| §7 | Late interest row: checkbox nascosto | ⚠️ Checkbox ok, ma click apre modale | Piano A §4 |
| §8 | Grace period: Y/M/D + totale bidirezionale | ⚠️ Funziona ma sync solo su blur | Piano A §5 |
| §9 | placeholder + help_url provider | ⚠️ Placeholder ok, manca icona ❓ | Piano A §6 |
| §10 | Docs MkDocs 7 pagine | ⚠️ index.it.md ≠ index.en.md, mancano emoji | Piano A §7 |
| §11 | Dark mode bg-white sulle icone provider | ❌ Non necessario, da rimuovere | Piano A §8 |
| §12 | Piani completati rimossi | ✅ OK | — |

### Problema architetturale scoperto: `scheduled_investment` provider

L'architettura corrente di LibreFolio è: **Asset → Provider → PriceHistory → Transazioni leggono i prezzi**. I provider normali (Yahoo, justETF, CSS Scraper) fetchano prezzi da fonti esterne e li salvano in `PriceHistory`. Le transazioni si collegano all'asset e usano quei prezzi per valutazioni.

Il `scheduled_investment` provider attuale **viola questo pattern**: legge le transazioni per calcolare il capitale, poi calcola il valore al volo. Questo crea una **dipendenza circolare** (prezzi ← transazioni ← prezzi) incompatibile con Phase 7 (Transactions).

**Soluzione**: il provider deve diventare autocontenuto — riceve un `initial_value` come parametro, calcola i prezzi autonomamente, e li salva in `PriceHistory` come qualsiasi altro provider. Le distributions (cedole, rimborsi parziali) sono eventi dell'asset che riducono il prezzo, non transazioni del portafoglio.

---

## Piano A — Bug Fix Immediati

Tutti i fix che non dipendono dalla riprogettazione del provider. Fattibili subito.

### §A1 — Rimuovere scroll listener dai calendar popover

**Problema**: Il popover del DateRangePicker/SingleDatePicker si chiude appena l'utente scrolla la pagina, anche accidentalmente. Il popover usa `position: fixed` → lo scroll della pagina non lo disallinea, quindi il listener è inutile e dannoso.

**File coinvolti**:
- `frontend/src/lib/components/ui/DateRangePicker.svelte` (L391-398)
- `frontend/src/lib/components/ui/SingleDatePicker.svelte` (L115-122)
- `frontend/src/lib/components/assets/CellDateRange.svelte` (L71-76)

**Modifica**: Rimuovere l'intero `$effect` che ascolta `window scroll capture:true` e chiama `closeCalendar()` in tutti e 3 i file.

**Effort**: 5 min

---

### §A2 — Test results: wrap + layout

**Problema**: I risultati del test provider non vanno a capo — il testo viene troncato da `truncate` e la riga non wrappa.

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

**Modifiche**:
- L624: `flex items-center` → `flex flex-wrap items-baseline`
- L633: rimuovere la classe `truncate` dallo `<span>` del summary

**Effort**: 5 min

---

### §A3 — Bottone 📋 copy errore a fine riga (sostituisce dblclick/long-press)

**Problema**: La feature dblclick/long-press per copiare il contenuto del tooltip non funziona ergonomicamente — l'utente non riesce a raggiungere il tooltip col mouse prima che scompaia.

**Soluzione**: Rimuovere la feature dal Tooltip (torna passivo) e aggiungere un bottone copy inline nella riga del test result.

**File coinvolti**:
- `frontend/src/lib/components/ui/Tooltip.svelte`
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

**Modifiche Tooltip.svelte** — Rimuovere:
- `flashCopy` state (L43)
- `longPressTimer` variable (L50)
- Cleanup in `hide()` (L60)
- `copyTooltipContent()` function (L63-72)
- `handleTooltipDblClick()` function (L74-77)
- `handleTouchStart()` / `handleTouchEnd()` functions (L79-85)
- `ondblclick`, `ontouchstart`, `ontouchend`, `ontouchmove` attributes (L241-244)
- `.tooltip-flash` CSS class (L286-289)
- Import di `toasts` (L18) se non usato altrove

**Modifiche ProviderAssignmentSection.svelte** — Per ogni test result con `status === 'error'`:
- Aggiungere a fine riga un bottone icona `Copy` (lucide) con `ml-auto shrink-0`
- `onclick`: `navigator.clipboard.writeText(result.detail)` + `toasts.info('Copied to clipboard')`
- Il bottone è visivamente discreto (grigio, hover → blu)

**Effort**: 15 min

---

### §A4 — Bloccare click/dblclick su righe non-selezionabili

**Problema**: Anche se la checkbox è nascosta sulla riga late interest, cliccando sulla riga si apre comunque la modale (via `handleRowClick` / `handleRowDoubleClick`).

**File**: `frontend/src/lib/components/table/DataTable.svelte`

**Modifica** (L977-978): Nel `<tr>`, wrappare i callback con un guard:
```
onclick={() => { if (isRowSelectable && !isRowSelectable(row)) return; highlightedRowId = null; handleRowClick(row); }}
ondblclick={() => { if (isRowSelectable && !isRowSelectable(row)) return; handleRowDoubleClick(row); }}
```

**Effort**: 5 min

---

### §A5 — Grace period sync bidirezionale live (oninput)

**Problema**: La conversione Y/M/D ↔ totale giorni avviene solo su blur. L'utente si aspetta sync immediata durante la digitazione.

**File**: `frontend/src/lib/components/assets/CellDateRange.svelte` (L156-204)

**Modifiche**:
- I 3 input Y/M/D (L159, L169, L179): `onblur={handleYMDBlur}` → `oninput={handleYMDBlur}`
- Il campo totale giorni (L197): `onblur={handleGraceDaysBlur}` → `oninput={handleGraceDaysBlur}`
- `handleYMDBlur()` ricalcola `localGraceDays` e chiama `onGraceDaysChange` immediatamente
- `handleGraceDaysBlur()` ricalcola Y/M/D e chiama `onGraceDaysChange` immediatamente

**Effort**: 5 min

---

### §A6 — Icona ❓ per documentazione provider

**Problema**: Il campo `provider_help_url` esiste nello schema Pydantic ma nessun provider lo imposta. Nel frontend c'è un link testuale sotto il dropdown, ma non è visibile/intuitivo. Serve un'icona ❓ inline.

**File coinvolti (Backend)**:
- `backend/app/services/asset_source.py` — Aggiungere property `provider_help_url` su `AssetSourceProvider` (default `None`)
- `backend/app/services/asset_source_providers/yahoo_finance.py` — `return "/mkdocs/user/assets/providers/yahoo-finance/"`
- `backend/app/services/asset_source_providers/justetf.py` — `return "/mkdocs/user/assets/providers/justetf/"`
- `backend/app/services/asset_source_providers/css_scraper.py` — `return "/mkdocs/user/assets/providers/css-scraper/"`
- `backend/app/services/asset_source_providers/scheduled_investment.py` — `return "/mkdocs/user/assets/providers/scheduled-investment/"`
- `backend/app/api/v1/assets.py` (L348-356) — Aggiungere `provider_help_url=instance.provider_help_url` al costruttore `FAProviderInfo`

**File coinvolti (Frontend)**:
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` (L436-441) — Sostituire il link testuale sotto il dropdown con un'icona `CircleHelp` (lucide) posizionata inline a destra del select provider. L'icona è un `<a target="_blank">` che apre la URL. Visibile solo se `selectedProvider?.provider_help_url` è valorizzato.

**Effort**: 20 min

---

### §A7 — Merge docs IT→EN + Emoji su tutte le pagine

**Problema**: `index.it.md` e `index.en.md` hanno contenuti divergenti. Le pagine docs mancano di emoji/icone per migliorare la leggibilità.

**File coinvolti**:
- `mkdocs_src/docs/user/assets/index.it.md` — Sovrascrivere con contenuto di `index.en.md`
- `mkdocs_src/docs/user/assets/index.en.md` — Arricchire con emoji
- `mkdocs_src/docs/user/assets/providers/index.en.md` — Arricchire con emoji
- `mkdocs_src/docs/user/assets/providers/yahoo-finance.en.md` — Arricchire con emoji
- `mkdocs_src/docs/user/assets/providers/justetf.en.md` — Arricchire con emoji
- `mkdocs_src/docs/user/assets/providers/css-scraper.en.md` — Arricchire con emoji
- `mkdocs_src/docs/user/assets/providers/scheduled-investment.en.md` — Arricchire con emoji

**Pattern emoji** (coerente con docs FX già presenti):
- `# 📈 Yahoo Finance Provider`
- `## 🔧 Configuration`
- `## 📊 Capabilities`
- `## 💡 Examples`
- `## 📝 Notes`
- `## ⚡ Late Interest`
- `## 🔍 How to Find the CSS Selector`
- `## 🧮 How Value is Calculated`
- `## 🎯 Use Cases`

**Effort**: 15 min

---

### §A8 — Rimuovere bg-white p-0.5 dalle icone provider

**Problema**: Nel Round 10 è stato aggiunto `bg-white p-0.5` alle icone provider nel dropdown per dark mode. L'utente conferma che non era necessario — va rimosso.

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte`

**Modifiche**:
- L422: `class="w-4 h-4 rounded-sm object-contain bg-white p-0.5"` → `class="w-4 h-4 rounded-sm object-contain"`
- L430: identica modifica

**Effort**: 2 min

---

### Piano A — Riepilogo

| § | Item | Effort | Stato |
|---|------|--------|-------|
| §A1 | Scroll listener removal (DateRangePicker, SingleDatePicker, CellDateRange) | 5 min | ✅ DONE |
| §A1b | DataTableColumnFilter: scroll reposition instead of close (Files page regression) | 5 min | ✅ DONE |
| §A2 | Test results wrap | 5 min | ✅ DONE |
| §A2b | Test results: force vertical list layout (flex-col, not inline) | 5 min | ✅ DONE |
| §A3 | Copy error button + cleanup Tooltip | 15 min | ✅ DONE |
| §A4 | Block click on non-selectable rows | 5 min | ✅ DONE |
| §A5 | Grace period live sync | 5 min | ✅ DONE |
| §A6 | Provider help icon ❓ (backend endpoint + CircleHelp inline) | 20 min | ✅ DONE |
| §A7 | Docs merge EN↔IT + emoji on all 7 asset doc pages | 15 min | ✅ DONE |
| §A8 | Remove bg-white p-0.5 from provider icons | 2 min | ✅ DONE |
| §A9 | Late interest row: hide from table when toggle is off | 5 min | ✅ DONE |
| §A10 | DateRangePicker/SingleDatePicker: reposition on scroll (follows parent popover) | 10 min | ✅ DONE |
| §A11 | CSS Scraper: currency param type `"currency"` → CurrencySearchSelect | 10 min | ✅ DONE |
| **Totale** | | **~107 min** | ✅ |

#### Post-testing Notes (commit 2)

- **§A1b**: Il fix §A1 (rimozione scroll listener) non copriva `DataTableColumnFilter.svelte` usato nella pagina Files/. Lo scroll handler è stato cambiato: ora riposiziona il popover sullo scroll, e chiude solo se l'anchor esce dal viewport.
- **§A2b**: I risultati test erano inline per via del `display: inline-flex` di `Tooltip.svelte`. Cambiato container a `flex flex-col gap-1.5` per forzare layout verticale.
- **§A9**: La riga late interest disabilitata era ancora visibile e cliccabile (apriva grace modal). Ora la riga è completamente nascosta quando il toggle è off. Rimosso CSS `late-row-disabled` non più necessario.

#### Post-testing Notes (commit 3)

- **§A10**: I popover calendario (DateRangePicker/SingleDatePicker) non seguivano il parent popover durante lo scroll. Aggiunto `$effect` con scroll listener `capture:true` che riposiziona il calendario, e chiude solo se il trigger esce dal viewport. Applicato a entrambi i componenti.
- **§A11**: Il campo `currency` del CSS Scraper era un semplice input testuale. Backend: tipo cambiato da `"string"` a `"currency"` in `params_schema`. Frontend: aggiunto ramo `field.type === 'currency'` nel loop parametri generici di `ProviderAssignmentSection.svelte` che renderizza `CurrencySearchSelect` con ricerca, bandiere e simboli valuta.

---

## Piano B — Riprogettazione `scheduled_investment` Provider

> ✅ **ESTRATTO in piano dedicato**: `plan-phase06Step3Round12-AssetEventAndScheduleRedesign.prompt.md`
> Il design di alto livello qui sotto è stato raffinato con l'utente e formalizzato in un piano completo
> con 8 blocchi (DB → Schema → Provider → Service → Test → Frontend → Docs), ~6h stimate.

### Problema architetturale

| Aspetto | Attuale (rotto) | Nuovo (corretto) |
|---|---|---|
| **Capitale** | Calcolato da transazioni DB | `initial_value` nei `provider_params` |
| **Prezzi** | Calcolati al volo, mai salvati in PriceHistory | Generati e salvati in `PriceHistory` come tutti i provider |
| **Dividendi/cedole** | Non gestiti | Lista di `distributions` nei params: riducono il prezzo ex-date |
| **Transazione BUY** | Provider la legge per il capitale | Phase 7: utente compra 1 quota al prezzo del giorno |
| **Dipendenza** | Circolare: prezzi ↔ transazioni | Unidirezionale: params → prezzi → transazioni |
| **Test probe** | Richiede `_transaction_override` hack | Standard: params → calcolo → risultato |

### Nuovo modello dati

#### `FAScheduledInvestmentSchedule` (esteso)

```python
class FAScheduledInvestmentSchedule(BaseModel):
    initial_value: Decimal          # Capitale iniziale (obbligatorio)
    schedule: List[FAInterestRatePeriod]   # Periodi con tassi (invariato)
    late_interest: Optional[FALateInterestConfig] = None  # (invariato)
    distributions: Optional[List[FADistribution]] = None  # NUOVO

class FADistribution(BaseModel):
    date: date
    amount: Decimal                 # Importo staccato
    type: DistributionType          # "coupon" | "partial_repayment"
```

#### Logica di calcolo del prezzo

Per ogni giorno `d`:
1. `base_value = initial_value`
2. `accrued_interest = Σ interesse_maturato(schedule, base_value, d)`
3. `total_distributions = Σ distributions dove date ≤ d`
4. `prezzo(d) = base_value + accrued_interest - total_distributions`

Per `partial_repayment`: riduce anche il `base_value` per i calcoli successivi (il capitale su cui maturano interessi diminuisce).

### Steps di implementazione (alto livello)

| Step | Descrizione | Effort stimato |
|------|-------------|----------------|
| B1 | Schema: aggiungere `initial_value`, `FADistribution`, `distributions` a `FAScheduledInvestmentSchedule` | 30 min |
| B2 | Backend: riscrivere `get_current_value` e `get_history_value` — rimuovere dipendenza transazioni | 1h |
| B3 | Backend: rimuovere `_get_transactions_from_db`, `_calculate_face_value_from_transactions`, `_transaction_override` | 15 min |
| B4 | Frontend: aggiungere campo `Initial Value` nello `ScheduledInvestmentEditor` | 20 min |
| B5 | Frontend: aggiungere sezione `Distributions` (tabella editabile: data, importo, tipo) | 45 min |
| B6 | Frontend: abilitare bottone Test Configuration per `scheduled_investment` (§4b) — non serve più `_transaction_override`, basta mandare i params | 15 min |
| B7 | Test backend: aggiornare `test_synthetic_yield.py` e `test_asset_schemas.py` | 30 min |
| B8 | Docs: aggiornare `scheduled-investment.en.md` con nuovo modello | 15 min |
| **Totale** | | **~3h** |

### Compatibilità Phase 7

Quando si implementeranno le transazioni:
- **BUY**: l'utente compra 1 quota dell'asset al prezzo del giorno (letto da `PriceHistory`)
- **Dividendi/cedole BRIM**: l'importer crea sia la `distribution` sull'asset (evento prezzo) che la transazione `INTEREST` sul portafoglio (evento cash)
- **Vendita anticipata**: SELL riduce la quantità, il prezzo continua a essere generato dal provider

### Domanda aperta per l'utente

Le **distributions** (cedole, rimborsi parziali) nel Piano B sono dati dell'asset — l'equivalente di un "dividend event" su un'azione: l'asset stacca cedola → il prezzo scende. In Phase 7, il BRIM importer creerebbe sia la distribution sull'asset che la transazione INTEREST sul portafoglio. Questo approccio è corretto o serve una logica diversa?

L'approccio che proponi, di connettere i 2 oggetti attraverso il codice frontend mi torna, è un aiuto che diamo all'utente che altrimenti dovrebbe aggiornare per conto suo l'asset.
Anzi apre la strada ad un idea più radicale, provare a catturare i dividendi con tutti i provider così da poter usare in seguito questa info per avvisare l'utente se dei dividendi registrati per quell'asset sono stati staccati mentre lui lo possedeva.
So che justETF sulla pagina web mostra queste info, e probabilmente anche yhaoo, anche se da verificare, sarebbe un ulteriore info catturata mentre si cerca la history, e credo che vada salvata nel DB in una nuova tabella, anche essa collegata all'asset di tipo "dividend_event".
Quando poi andremo a fare la pagina di assetDetail, dovremo far si che si veda anche questo e che sia possibile editarlo, quindi credo bisognerà potenziare l'attuale endpoint per ottenere il prezzo dell'asset per elencare nel giorno in cui è stata stattaca una cedola/dividendo l'evento e la quantità per azione.
Tornando però alla logica di calcolo del prezzo per lo scheduled_investment, quello che proponi mi torna, sia nell'initial valude che nei distribution event, non sono però sicuro sul calcolo degli interessi, negli scenari reali che mi vengono in mente, quando si fanno prestiti su una piattaforma l'interesse è sempre rispetto al valore iniziale, ma se credi possa avere senso fare un interesse composito rispetto il valore attuale, come tracciamo i 2 casi? Credo dipenda dal tipo di interesse da applicare alla sezione.
