# Plan: Bugfix 7 — Event Markers + FX Auto-Sync + Residual Polish

## Contesto

Leggere prima `knowledge_base/00_project_overview.md` e poi `knowledge_base/02_frontend.md`.

Siamo nella **Phase 06 Step 4 Part A** del progetto LibreFolio — asset detail page e polish responsive.
Le sessioni precedenti (Bugfix 1–6) hanno risolto la maggior parte dei problemi. Restano due feature incomplete e alcune rifiniture.

### File chiave da leggere prima di pianificare
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` — pagina asset detail
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` — pagina forex detail (per coerenza)
- `frontend/src/lib/components/charts/PriceChartFull.svelte` — componente chart
- `frontend/src/lib/components/fx/FxPairAddModal.svelte` — modale creazione coppia FX
- `frontend/src/lib/components/assets/AssetPriceSummary.svelte` — price summary con currency select
- `plan-phase06Step4PartA-Bugfix_6_ClassifTooltipEventMarkers.prompt.md` — piano precedente con specifiche A6

---

## Blocco 1 — A6: Event Markers sul grafico

### Obiettivo
Visualizzare eventi (dividendi, interessi, split, aggiustamenti prezzo, maturity) come marcatori scatter sul grafico prezzi, sia per l'asset principale che per gli asset in comparazione.

### Specifiche dettagliate
Sono nel file `plan-phase06Step4PartA-Bugfix_6_ClassifTooltipEventMarkers.prompt.md`, sezione "Piano successivo: A6 — Event Markers". Seguire i passi A6.1 → A6.7 come descritti.

### Punti chiave:
1. **Definire `EventMarker` type** + color/symbol mappings in PriceChartFull
2. **Aggiungere prop `eventMarkers?: EventMarker[]`** a PriceChartFull
3. **Scatter series** in `renderChart()` — raggruppare per tipo, usare Y dal lineData più vicino
4. **Tooltip formatter** per le scatter series → mostra tipo, valore, currency, notes
5. **Costruire `eventMarkers` derived** in `+page.svelte` combinando eventi principali + comparison
6. **i18n** per i tipi evento (DIVIDEND, INTEREST, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT, SPLIT) — 4 lingue
7. **Legenda** — le scatter series degli eventi sono toggleabili nella legenda ECharts

### Prerequisiti già soddisfatti:
- Il backend restituisce `events` via `POST /assets/prices/query` con `include_events: true`
- La variabile `events` è già caricata nella pagina asset detail
- `comparisonEvents` map è già popolata per asset in overlay

---

## Blocco 2 — FX Auto-Sync dopo creazione coppia dalla modale asset detail

### Problema attuale
Quando dalla pagina asset detail si clicca "Aggiungi coppia FX" (pulsante FX+), si apre `FxPairAddModal`. Dopo la creazione, la lista delle coppie FX viene aggiornata (`loadFxPairSlugs()`), ma:
1. Non viene eseguito il sync dei tassi per la nuova coppia nel range attualmente impostato
2. Il grafico non si aggiorna con i dati convertiti
3. La prima valuta (= valuta dell'asset) dovrebbe essere readonly nella modale
4. Se la seconda valuta cambia nella modale, la `displayCurrency` dell'asset detail non si aggiorna

### Soluzione richiesta

#### 2.1 — `FxPairAddModal`: prop `readonlyBase`
- Aggiungere prop opzionale `readonlyBase?: boolean` (default `false`)
- Quando `true`, il campo base è bloccato (disabled + stile visivo readOnly)
- Usata SOLO quando aperta dalla pagina asset detail

#### 2.2 — `oncreated` callback esteso
- Il callback `oncreated` deve ricevere `{ base, quote, hasRealProvider, slug }` (aggiungere `slug`)
- La pagina asset detail usa `slug` per triggerare il sync

#### 2.3 — Auto-sync dalla pagina asset detail
Nel handler `oncreated` della modale FX nella pagina asset detail:
```
1. Chiudi la modale
2. Reload FX pair slugs (già presente)
3. Se hasRealProvider:
   a. Sync la nuova coppia FX nel range [dateStart, dateEnd] → zodiosApi.sync_rates_...
   b. Toast di successo/errore
4. Aggiorna displayCurrency con la quote della coppia creata
5. Refresh dell'asset (handleRefresh)
```

#### 2.4 — Aggiornamento displayCurrency alla chiusura
Se la seconda valuta cambia nella modale, alla chiusura/creazione aggiornare `displayCurrency` con il valore finale di `quote`.

---

## Blocco 3 — Rifiniture residue

### 3.1 — Responsive fine-tuning delle soglie
Verificare e aggiornare i thresholds di `createResponsiveLayout` in tutte e 4 le pagine (asset detail, asset list, fx list, fx detail) affinché il comportamento sia coerente:
- `wide` → tutto in riga, price-summary affiancato
- `tablet` → filtri impilati, bottoni 2×2 a destra  
- `tablet-s` → filtri impilati, bottoni 4×1 colonna a destra
- `mobile` → tutto centrato impilato, bottoni 1×4 riga

Le soglie attuali sono elencate in `plan-phase06Step4PartA-Bugfix_6_ClassifTooltipEventMarkers.prompt.md`.

### 3.2 — DateRangePicker badge grouping (FATTO ✅)
I badge 1Y, 2Y, Custom e Info sono già raggruppati in un `<span>` per fare wrap come unità.

### 3.3 — Asset detail tablet-s layout (FATTO ✅)
Il container esterno in tablet-s usa `flex-row` (bottoni a destra), non `flex-col`.

---

## Ordine di implementazione suggerito

1. **Blocco 1** (A6 Event Markers) — è la feature più grande, iniziare da qui
2. **Blocco 2** (FX Auto-Sync) — dipende dalla modale FxPairAddModal
3. **Blocco 3.1** (Fine-tuning soglie) — opzionale, da fare dopo test visivo

---

## Test di verifica finale

### Event Markers
- [ ] Asset con dividendi → mostra marcatori triangolari blu sulle date dei dividendi
- [ ] Asset senza eventi → nessun marker visibile
- [ ] Hover su marker → tooltip con tipo localizzato, valore, currency
- [ ] Comparison asset con eventi → marker con bordo colorato del segnale
- [ ] Toggle legenda → nasconde/mostra marker per tipo

### FX Auto-Sync
- [ ] Da asset detail, click FX+ → modale si apre con base = valuta asset (readonly)
- [ ] Creo coppia con provider reale → sync automatico + toast feedback
- [ ] Dopo chiusura modale, il grafico mostra i dati convertiti nella nuova valuta
- [ ] Se cambio la seconda valuta nella modale, `displayCurrency` si aggiorna

### Responsive
- [ ] Asset detail: wide → datepicker + price a fianco, bottoni 2×2 a destra
- [ ] Asset detail: tablet → filtri impilati, bottoni 2×2 a destra
- [ ] Asset detail: tablet-s → filtri impilati, bottoni 4×1 colonna a destra
- [ ] Asset detail: mobile → tutto centrato, bottoni 1×4 riga
- [ ] FX detail: stesse transizioni coerenti

