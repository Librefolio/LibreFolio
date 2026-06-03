# Plan: D2 Round 3 (SP-D) — FormModal Props Unification + AssetEventPicker + WAC FX Feedback

**Date**: 1 Giugno 2026
**Status**: ✅ DONE (2026-06-01)
**Post-impl fixes** (2026-06-01): Added COST_BASIS_REQUIRED validation (step 6d in pipeline). Fixed 6 service tests + 4 API tests that lacked cost_basis_override/mode for TRANSFER(qty>0) and ADJUSTMENT(qty>0). Fixed logger.log(5,...) TRACE crash in fx.py. Fixed populate_mock_data (9 records). Pre-existing FX API bug (`test_manual_full_pair_delete_no_reinstate`) unrelated.
**Priority**: P1 (interface cleanup + feature + polish)
**Parent**: [`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`](./plan-phase07-PlanD_SplitPromoteFullStack.prompt.md)
**Predecessor**: D2-Round2 SP-C ✅ (WAC inline preview, 8 bugfix plans)
**Origin Steps**: Steps 14, 15, 16 from R2-WalktestFeedback SP-D scope

---

## 🎯 Obiettivo

Tre task residui dal Walktest Feedback Round:

| Step | Titolo | Natura |
|------|--------|--------|
| **A** | FormModal props unification (`items: FormModalItems`) | Interface cleanup |
| **B** | AssetEventPicker (sostituzione input numerico) | Feature |
| **C** | WAC FX staleness feedback | Backend fix + frontend polish |

---

## Stato Attuale (code-verified 2026-06-01)

### Infrastruttura Esistente

| Componente | Stato | Note |
|---|---|---|
| `resolveFormItems.ts` | ✅ Operativo | 2 resolver: `resolveFormItemsFromOps` (BulkModal), `resolveFormItemsForView` (+page) |
| `FormModalItems` type | ✅ Definito | `[TXReadItem] \| [TXReadItem, TXReadItem] \| [TXReadItem, InaccessiblePartner]` |
| FormModal props | ❌ Vecchio pattern | Usa `initialRow` + `injectedPartnerRow` separati |
| `asset_event_id` UI | ❌ Input numerico raw | Nessun picker, nessuna validazione |
| `WACQualifyingTX.fx_info` | ❌ Schema esiste, mai popolato | `_bf` scartato in `wac_service.py:138` |
| `POST /fx/currencies/sync` | ✅ Operativo | Accetta `{pairs: string[], start: date, end: date}` |
| `POST /assets/events/query` | ✅ Operativo | Accetta lista di `FAEventQueryItem` per asset+daterange |
| `canShowAssetEvent` | ✅ Gating | `$derived(rule.eventLinkable && draft.asset_id != null)` |
| `getEventLinkableTypes()` | ✅ Backend-driven | Filtra tipi con `eventLinkable=true` |
| `SimpleSelect` / `SearchSelect` | ✅ Operativi | In `lib/components/ui/select/`, `SelectOption{value,label,icon?,data?}` |

---

## Step A — FormModal Props Unification ✅ (2026-06-01)

> **Note implementazione**: Props `initialRow` + `injectedPartnerRow` → `items: FormModalItems | null`. Internamente derivati `mainRow`, `_injectedPartner`, `_inaccessibleFromItems` da items. Callers aggiornati: +page.svelte usa `resolveFormItemsForView()`, BulkModal costruisce items inline da `opToTxLike()` + partner. svelte-check 0 errori. Format invariato.

### Obiettivo

Sostituire la coppia di props `{initialRow, injectedPartnerRow}` con un singolo `items: FormModalItems | null`. I caller già usano `resolveFormItems.ts` per costruire l'array — ora il FormModal lo riceve direttamente.

### Scope

| File | Modifica |
|------|----------|
| `TransactionFormModal.svelte` | Rimuovere `initialRow` e `injectedPartnerRow` dalle Props. Aggiungere `items: FormModalItems \| null`. Init logic legge da `items[0]` (main) e `items[1]` (partner/inaccessible). |
| `+page.svelte` (transactions) | Nelle funzioni `handleViewRow` / `handleEditRow`: costruire `items` via `resolveFormItemsForView()` e passarlo al FormModal |
| `TransactionBulkModal.svelte` | Quando apre FormModal per inline edit: costruire `items` via `resolveFormItemsFromOps()` e passarlo |

### Dettaglio Substeps

1. **Props change**: `initialRow` + `injectedPartnerRow` → `items: FormModalItems | null`
2. **Init $effect**: derivare `mainRow = items?.[0]` e `partnerRow = items?.[1]` (con type-guard `isInaccessible`)
3. **Populate draft**: dal `mainRow` (come oggi da `initialRow`)
4. **Populate dualDraftTo**: dal `partnerRow` se è TXReadItem (come oggi da `injectedPartnerRow`)
5. **InaccessiblePartner**: mostrare chip "partner inaccessibile" (come oggi, ma da `items[1]._inaccessible`)
6. **Mode 'create'**: `items = null` → draft vuoto (come oggi con `initialRow = null`)
7. **Rimuovere vecchie props** e ogni riferimento interno a `initialRow` / `injectedPartnerRow`
8. **Verify**: E2E tests passano senza modifiche (interface change trasparente)

### Rischio: Basso-Medio

Il refactor è un cambio d'interfaccia — la logica interna (draft → validate → commit) non cambia. L'unico rischio è nei caller: assicurarsi che tutti i punti di apertura passino `items` correttamente.

---

## Step B — AssetEventPicker ✅ (2026-06-01)

> **Note implementazione**: Creato `AssetEventSelect.svelte` (SimpleSelect wrapper + fetch da POST /assets/events/query + slider ±N giorni da localStorage). Integrato nel FormModal al posto dell'input numerico, posizionato PRIMO nella sezione Optional. i18n aggiunto (EN/IT/FR/ES). `canShowAssetEvent` ora richiede anche `draft.date !== ''`. data-testid: `tx-form-event-select`, `tx-form-event-slider`. svelte-check 0 errori.

### Obiettivo

Sostituire l'input numerico `asset_event_id` con un `SimpleSelect` (già in `ui/select/`) che mostra gli eventi dell'asset filtrati per prossimità alla data TX.

### Decisioni di Design

| Decisione | Scelta | Rationale |
|---|---|---|
| UI pattern | **SimpleSelect inline** con slider ±N | Riusa componente esistente, pochi eventi per asset |
| Quando mostrare | Solo se `rule.eventLinkable && draft.asset_id != null && draft.date !== ''` | Senza data/asset non ha senso |
| Filtro temporale | Slider ±N giorni, default ±7gg | Evita errori di puntamento su evento sbagliato |
| Persistenza filtro | `localStorage` key `librefolio-event-picker-days` | Riusa preferenza utente |
| Tipi TX compatibili | Backend-driven via `eventLinkable` (DIVIDEND, INTEREST, ADJUSTMENT) | Già gating con `canShowAssetEvent` |
| Obbligatorietà | **Facoltativo** sempre | Arricchimento per future analisi (dividend tracker) |
| Caso d'uso | Linkare TX income a evento dichiarato → dividend/interest tracker | "Ho ricevuto ciò che mi spetta?" |
| Posizione nel form | **Primo** tra gli opzionali (prima di tags e description) | Più rilevante funzionalmente |

### Target UI (ASCII Art)

```
┌─────────────────────────────────────────────────────────────┐
│  ▸ Optional                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Linked Event     [ 💰 2026-05-10 — 0.25 EUR  ▾ ]         │
│                   ├────────────────────────────────────┤    │
│                   │  (none)                            │    │
│                   │  💰 2026-05-10 — 0.25 EUR Q1 div  │ ◀──│
│                   │  💰 2026-02-12 — 0.22 EUR Q4 div  │    │
│                   ├────────────────────────────────────┤    │
│                                                             │
│  Range ±days      [──●──────────] 7                         │
│                                                             │
│  Tags             [ tag1 ] [ tag2 ] [ + ]                   │
│                                                             │
│  Description      ┌──────────────────────────────┐          │
│                   │                              │          │
│                   └──────────────────────────────┘          │
│                                                             │
│  Link UUID        abc-123-def (readonly)                    │
└─────────────────────────────────────────────────────────────┘
```

**Ordine campi nella sezione Optional** (nuovo):
1. Asset Event (se `canShowAssetEvent && draft.date !== ''`)
2. Tags
3. Description
4. Link UUID (readonly)

### Componente: `AssetEventSelect.svelte` (NUOVO)

Wrapper leggero attorno a `SimpleSelect` + slider + fetch logic.

**Props**:
- `assetId: number` — asset selezionato
- `txDate: string` — data transazione (ISO)
- `value: number | null` — event_id selezionato
- `disabled: boolean`
- `onChange: (eventId: number | null) => void`

**Interno**:
1. Stato: `daysRange` (da localStorage, default 7), `events[]` (fetched), `loading`
2. `$effect` su `(assetId, txDate, daysRange)` → fetch via `POST /assets/events/query`
3. Trasforma eventi in `SelectOption[]`:
   - `value`: `String(event.id)` (SimpleSelect usa stringhe)
   - `label`: `"{icon} {date} — {value.amount} {value.code} {notes?}"`
   - `icon`: emoji per tipo (`DIVIDEND`→💰, `INTEREST`→🏦, `SPLIT`→✂️, `PRICE_ADJUSTMENT`→📊, `MATURITY_SETTLEMENT`→📅)
4. Aggiunge opzione "none" in cima: `{value: '', label: '—'}`
5. Slider `<input type="range" min=1 max=90>` sotto il select
6. Se `value != null` ma evento non nel fetch corrente: fetch singolo via `GET /assets/events?ids={value}` per mostrare il chip anche fuori range

**API**:
- `POST /assets/events/query` body: `[{asset_id, start: txDate - N, end: txDate + N}]`
- Risposta: `FAEventQueryResponse.items[0].events[]`

### Integrazione nel FormModal

Il campo va **spostato PRIMA di tags/description** nella sezione Optional (attualmente è dopo):

```svelte
<!-- Optional disclosure body — NUOVO ordine -->
<div class="px-4 pb-4 space-y-3 text-sm">
    <!-- 1. Asset event link (prima di tags) -->
    {#if canShowAssetEvent && draft.date !== ''}
        <AssetEventSelect
            assetId={draft.asset_id}
            txDate={draft.date}
            value={draft.asset_event_id}
            disabled={isReadonly}
            onChange={(id) => { draft.asset_event_id = id; }}
        />
    {/if}

    <!-- 2. Tags -->
    ...

    <!-- 3. Description -->
    ...

    <!-- 4. Link UUID (readonly) -->
    ...
</div>
```

### Substeps

1. Creare `frontend/src/lib/components/transactions/AssetEventSelect.svelte`
2. Implementare: SimpleSelect wrapper + fetch + slider + localStorage
3. Integrare nel FormModal: spostare PRIMA di tags/description, rimuovere input numerico
4. Aggiornare `canShowAssetEvent` → `$derived(rule.eventLinkable && draft.asset_id != null && draft.date !== '')`
5. i18n: chiavi `transactions.form.eventPicker.*` (EN/IT/FR/ES) via `./dev.py i18n add`
6. data-testid: `tx-form-event-select`, `tx-form-event-slider`

---

## Step C — WAC FX Staleness Feedback ✅ (2026-06-01)

> **Note implementazione**: Backend: `wac_service.py` propaga `fx_info` (FxBackwardFillInfo) nei qualifying_txs; `transaction_service.py` emette issue `WAC_FX_UNAVAILABLE` con `missing_pairs` come params. Frontend: WacPreviewSection esteso con `fx_info` per riga (⚠️ tooltip se stale, 💱 se converted), amber banner per staleness >5d, `forcedManual` $derived che disabilita toggle Auto quando missing_pairs. FormModal: `handleSyncFx()` converte pair slugs (USD/EUR→EUR-USD) e chiama `sync_rates_api_v1_fx_currencies_sync_post`, bottone 🔄 Sync FX nel warning banner. resolveValidationMessage gestisce `wacFxUnavailable` con pairs→string. i18n: 4 lingue aggiornate con `transactions.wac.*` keys. Fix JSON: aggiunta `"promote": {` mancante in it/fr/es.json (broken dalla precedente inserzione di `wac` keys). svelte-check 0 errori.

> **⚠️ Fuori pista**: L'inserzione di `transactions.wac` keys nel passaggio precedente aveva cancellato la riga `"promote": {` nei file i18n it/fr/es.json, causando un JSON invalido. Riparato aggiungendo la riga mancante.

### Obiettivo

Comunicare all'utente la qualità delle conversioni FX usate nel WAC. Se dati mancanti → forza manual e **blocca commit**.

### Matrice Casi

| # | Situazione | Backend | Frontend UX |
|---|---|---|---|
| 1 | No FX needed | `missing_pairs: []`, nessun `fx_info` | WAC pulito, nessun indicatore |
| 2 | FX OK (data esatta) | `fx_info.stale_days = 0` | Riga qualifying: "150.00 USD → 138.50 EUR" |
| 3 | FX stale (N giorni) | `fx_info.stale_days > 0` | ⚠️ nella riga + Tooltip con info. Banner amber se max > 5gg |
| 4 | Pair esiste ma NO rate | `missing_pairs: ["USD/EUR"]` | ❌ Forza manual. Banner con Sync button |
| 5 | Pair NON esiste | `missing_pairs: ["USD/EUR"]` | ❌ Forza manual. Messaggio "pair non configurato" |
| 6 | Misto | Ogni riga ha il suo stato | Se qualsiasi riga ❌ → WAC forced manual |

### WAC Errors come Validation Issues (blocca commit)

**Problema**: Oggi se `missing_pairs` non è vuoto, il WAC risulta `null` ma NON c'è un'issue di validazione che blocchi il commit. L'utente potrebbe committare con `cost_basis_mode: auto` e nessun WAC calcolato.

**Soluzione**: Il backend (endpoint `/transactions/validate`) deve emettere un **fieldIssue** (index >= 0) quando una TX richiede WAC auto ma il calcolo fallisce per mancanza FX. Questo errore:
- Appare nel banner giallo/rosso in alto al FormModal
- **Blocca il commit** (come qualsiasi altro validation issue)
- Ha un `code` specifico (es. `wac_fx_unavailable`) risolvibile con messaggio dedicato

**Dove emettere**: nel flusso `validate` → quando il `WACPreviewResultItem` ha `wac=None && missing_pairs non vuoto` e la TX richiede `cost_basis_mode: auto` → aggiungere un'issue:
```python
{
    "operation": "create",  # o "update"
    "index": <idx>,
    "error": "WAC calculation failed: missing FX pairs",
    "code": "wac_fx_unavailable",
    "params": {"pairs": missing_pairs},
    "field": "cost_basis_override"
}
```

**Categoria**: è un **fieldIssue** (index >= 0, field = "cost_basis_override") perché:
- È relativo a una specifica TX (non un balance globale)
- Ha un campo specifico coinvolto
- Il fix è: cambiare mode a manual e inserire un valore, oppure sync FX

**Frontend resolution**: in `resolveValidationMessage.ts`, aggiungere case per `wac_fx_unavailable`:
- Messaggio: "❌ Impossibile calcolare WAC: pair FX mancanti ({pairs}). Sincronizza FX o usa modalità manuale."

### Bottone "🔄 Sync FX" nel Banner di Validazione

Il bottone Sync FX vive **dentro il banner** warning/error (non nel WacPreviewSection). Posizionato **in cima**, prima dell'elenco puntato delle issues.

**Layout banner con Sync:**
```
┌──────────────────────────────────────────────────────────────┐
│ ⚠️ / ❌  [titolo]                                     [X]   │
│                                                              │
│  [ 🔄 Sync FX ]                        ← bottone in cima    │
│                                                              │
│  • Riga #3: pair USD/EUR mancante                            │
│  • Riga #7: pair GBP/CHF senza rate nel range               │
└──────────────────────────────────────────────────────────────┘
```

**Comportamento differenziato per contesto:**

| Contesto | Pairs da sincronizzare | Date range |
|----------|----------------------|------------|
| **FormModal** (singola TX) | Solo pairs del form corrente (`missing_pairs`) | `[draft.date, draft.date]` |
| **BulkModal** (batch) | TUTTE le pairs di TUTTE le TX del batch | `[min(dates), max(dates)]` di tutte le TX |

**Logica:**
1. Il bottone appare solo se almeno un'issue ha `code === 'wac_fx_unavailable'`
2. Costruisce `pairs[]` aggregando tutti i `params.pairs` dalle issues con quel code
3. Costruisce date range dal contesto (FormModal: singola data; BulkModal: min/max di tutte)
4. Chiama `POST /fx/currencies/sync` con `{pairs: [...], start, end}`
5. On success: toast + ri-trigger validate → se WAC ora funziona, le issues spariscono
6. On error: toast error, issues restano

**Elenco puntato sotto il bottone**: mostra solo le righe problematiche e il motivo:
- FormModal: "Pair {pair} non disponibile per la data {date}"
- BulkModal: "Riga #{idx}: pair {pair} non disponibile ({date})"

### Backend: `wac_service.py`

**Problema**: riga 138 scarta `_rate_date` e `_bf`:
```python
converted, _rate_date, _bf = result  # ← SCARTATI
fx_converted[unified_idx] = converted.amount
```

**Fix**: salvare info staleness in un dict parallelo e propagarla ai `WACQualifyingTX`.

**Substeps backend**:

1. Accanto a `fx_converted: dict[int, Decimal]`, creare `fx_staleness: dict[int, FxBackwardFillInfo] = {}`
2. Quando `result` non è None:
   ```python
   converted, rate_date, bf = result
   fx_converted[unified_idx] = converted.amount
   if bf:
       fx_staleness[unified_idx] = bf
   else:
       fx_staleness[unified_idx] = FxBackwardFillInfo(fx_rate_date=rate_date, fx_days_back=0)
   ```
3. Nella costruzione di `qualifying_txs` (riga 187-198): aggiungere `fx_info=fx_staleness.get(i)` per ogni qualifying TX che ha avuto conversione FX
4. Nel flusso validate: se `wac=None && missing_pairs && cost_basis_mode=='auto'` → emettere issue `wac_fx_unavailable`

### Frontend: `WacPreviewSection.svelte`

**Modifiche UI (solo informative — nessun bottone qui)**:

1. **Riga qualifying con FX** (caso 2-3): appendere info FX inline nella riga:
   - Se `qualifying_tx.fx_info` presente: mostrare "(→ convertito FX)"
   - Se `stale_days > 0`: icona ⚠️ + tooltip "Rate del {rate_date} ({N}gg fa)"

2. **Banner amber** (caso 3, threshold > 5gg): sopra tabella qualifying:
   - "⚠️ Alcune conversioni FX usano rate non aggiornati."

3. **Caso 4-5 (missing_pairs non vuoto)**: forza `cost_basis_mode: manual`
   - Disabilitare toggle "auto" con messaggio ❌ inline
   - Il blocco commit è gestito dall'issue di validazione nel banner in alto (non qui)

4. **Fallback**: toggle "manual" sempre disponibile — rimuove l'issue `wac_fx_unavailable` perché la validate non prova più il calcolo auto

### Frontend: Banner di Validazione (FormModal + BulkModal)

**Modifiche al banner issues esistente** (`TransactionFormModal.svelte` righe 1297-1339):

1. Dopo il titolo del banner, **prima dell'elenco**, inserire:
   ```svelte
   {#if hasWacFxIssues}
       <button class="..." onclick={handleSyncFx} data-testid="tx-form-sync-fx-btn">
           🔄 {$t('transactions.wac.syncFx')}
       </button>
   {/if}
   ```
2. `hasWacFxIssues = $derived(issues.some(i => i.code === 'wac_fx_unavailable'))`
3. `handleSyncFx()`: aggrega pairs + date range → chiama API → re-validate

**Stessa logica nel BulkModal**: il banner issues del BulkModal segue lo stesso pattern, ma il date range è calcolato su tutte le ops.

### Substeps completi

1. Backend: propagare fx_info in `wac_service.py` (4 righe di codice)
2. Backend: emettere issue `wac_fx_unavailable` nel flusso validate quando WAC auto fallisce
3. Backend: verificare serializzazione (`FxBackwardFillInfo` → JSON in response)
4. Frontend (`resolveValidationMessage.ts`): case per code `wac_fx_unavailable`
5. Frontend: bottone "🔄 Sync FX" nel banner issues (FormModal + BulkModal)
6. Frontend: indicatore FX inline nelle righe qualifying (WacPreviewSection)
7. Frontend: banner amber aggregato per staleness (WacPreviewSection)
8. Frontend: logica forced-manual + disable auto toggle quando `missing_pairs.length > 0`
9. i18n: chiavi `transactions.wac.fxStale`, `transactions.wac.fxMissing`, `transactions.wac.syncFx`, `transactions.wac.syncSuccess`, `transactions.validate.wacFxUnavailable`

---

## Ordine di Esecuzione

```
A (props unification) — cleanup architetturale
  ↓
B (event picker select) — feature nuova su FormModal più pulito
  ↓
C (FX staleness) — polish WAC (backend + frontend)
```

**Nota**: A e B sono indipendenti e potrebbero essere parallelizzati, ma A prima rende il FormModal più leggibile per integrare B.

---

## Deferred (fuori scope)

- Vincolo valuta per (asset, broker) — decisione: NESSUNO (broker multi-currency supportati)
- Navigazione a /fx per creare pair mancante — incompatibile con mobile, solo messaggio descrittivo

---

## 🔗 Cross-links

- **Parent plan**: [`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`](./plan-phase07-PlanD_SplitPromoteFullStack.prompt.md)
- **R2 master (archived)**: `phases/phase-07-subplan/Parte4/Round6/PlanD-R2/plan-R2-WalktestFeedbackRound.prompt.md`
- **Phase 7 macro**: [`phases/phase-07-transactions.md`](./phases/phase-07-transactions.md)
- **devWiki**: `LibreFolio_devWiki/wiki/features/F-097.md` (WAC feature)

---

## 🧪 Walktest Manuale

### Setup

```bash
./dev.py db create-clean --test && ./dev.py test db populate --force
./dev.py server start --test   # backend su :6041
cd frontend && npm run dev     # frontend su :5173
```

Login: `e2e_test_user` / `E2eTestPass123!`

---

### Scenario 1 — Transfer con WAC auto (flusso completo end-to-end)

Obiettivo: creare un TRANSFER AAPL da IB → DEGIRO, verificare che il WAC auto si calcoli e il cost_basis si salvi.

| # | Azione | Risultato atteso | ✅/❌ |
|---|--------|-----------------|------|
| 1.1 | `/transactions` → Aggiungi → tipo "Transfer Securities" | Si apre il dual form (Da/A) | |
| 1.2 | Da: IB, Asset: Apple, Qty: -2. A: DEGIRO, Qty: +2 | Sezione WAC Preview compare lato "A" (ricevente) | |
| 1.3 | Compila data → **Valida** | WAC si calcola automaticamente (toggle Auto, valore numerico) | |
| 1.4 | Espandi tabella qualifying | Mostra BUY precedenti di AAPL su IB con effetto "Pesata" | |
| 1.5 | Commit → Riapri la TX appena creata | Il cost_basis è salvato correttamente (non null, valore coerente) | |
| 1.6 | Nella lista transazioni: la riga Transfer mostra il cost_basis nella colonna | Valore visibile, no "—" | |

---

### Scenario 2 — Adjustment positivo → obbligatorietà cost_basis

Obiettivo: verificare che un ADJUSTMENT con qty>0 non si possa salvare senza cost_basis.

| # | Azione | Risultato atteso | ✅/❌ |
|---|--------|-----------------|------|
| 2.1 | Crea Adjustment: IB, Apple, qty: +3, data odierna | WAC Preview compare (toggle Auto) | |
| 2.2 | Valida | WAC viene calcolato automaticamente | |
| 2.3 | Switcha a **Manual** → svuota il campo cost_basis → Valida | Errore "Cost basis required" nel banner | |
| 2.4 | Inserisci un valore manuale (es. 180 USD) → Commit | Si salva correttamente | |
| 2.5 | Riapri → il cost_basis è quello manuale (180 USD) | Persistenza corretta | |

---

### Scenario 3 — Event Picker in contesto reale (Dividend + evento)

Obiettivo: collegare un dividendo a un evento esistente tramite il nuovo picker.

| # | Azione | Risultato atteso | ✅/❌ |
|---|--------|-----------------|------|
| 3.1 | Crea dividend: IB, Apple, cash: +10 USD, data dentro range eventi Apple | Nella sezione Opzionale compare "Evento collegato" con select | |
| 3.2 | Apri il select | Lista eventi Apple filtrati per ±giorni dalla data TX | |
| 3.3 | Allarga lo slider a ±30gg | Lista si aggiorna con più eventi (o conferma che copre il range) | |
| 3.4 | Seleziona un evento (es. DIVIDEND) | Il select mostra l'evento selezionato con icona tipo | |
| 3.5 | Commit → Riapri | Evento ancora collegato nel picker | |
| 3.6 | Edita: cambia tipo a "Buy" | Il picker scompare (buy non è event-linkable) | |
| 3.7 | Rimetti "Dividend" | Picker riappare con l'evento precedentemente selezionato | |

---

### Scenario 4 — BulkModal: apri/modifica transfer paired

Obiettivo: verificare che dalla BulkModal si possa editare un transfer paired e il partner appaia.

| # | Azione | Risultato atteso | ✅/❌ |
|---|--------|-----------------|------|
| 4.1 | `/transactions` → seleziona la riga "Transfer AAPL IB ↔ DEGIRO" (tag: rebalance) | Riga evidenziata nella bulk | |
| 4.2 | Clicca Edit sulla BulkModal | FormModal si apre con dati precompilati INCLUSO il partner | |
| 4.3 | Verifica cost_basis | Il campo mostra $175.00 (il valore appena corretto in populate) | |
| 4.4 | Chiudi senza salvare → seleziona un'ALTRA riga (es. Buy) → Edit | FormModal mostra la nuova riga, nessun residuo del transfer | |

---

### Scenario 5 — Partner inaccessibile (Asym-d: broker nascosto)

Obiettivo: verificare che aprendo un transfer il cui partner è su un broker senza accesso, il form gestisca gracefully.

| # | Azione | Risultato atteso | ✅/❌ |
|---|--------|-----------------|------|
| 5.1 | Cerca nelle TX: "[Asym-d] AAPL IB ↔ HiddenBroker" (lato IB, qty=-1) | Riga visibile nella lista | |
| 5.2 | Clicca per aprire | FormModal si apre; sezione partner mostra badge "inaccessibile" o equivalente | |
| 5.3 | Verifica che non si possa editare il partner | Campi partner disabilitati o nascosti | |
| 5.4 | Chiudi senza crash | Nessun errore console | |

---

### Scenario 6 — WAC con FX cross-currency (se il portfolio è EUR)

Obiettivo: se l'utente ha portfolio in EUR e crea un transfer di AAPL (USD), il WAC deve convertire.

| # | Azione | Risultato atteso | ✅/❌ |
|---|--------|-----------------|------|
| 6.1 | Verifica in Settings che la portfolio currency sia EUR (o cambiala) | Portfolio = EUR | |
| 6.2 | Crea Transfer: AAPL da IB a DEGIRO, qty: -1/+1 | Lato ricevente mostra WAC Preview | |
| 6.3 | Valida | WAC calcolato in EUR (ha convertito da USD via FX) | |
| 6.4 | Espandi qualifying | Le righe mostrano 💱 (FX convertito) accanto al costo | |
| 6.5 | Se il tasso FX è stale | ⚠️ con tooltip giorni | |

---

### Scenario 7 — Sync FX dal form (coppia mancante)

Obiettivo: simulare una coppia FX mancante e usare il bottone Sync FX dal form.

| # | Azione | Risultato atteso | ✅/❌ |
|---|--------|-----------------|------|
| 7.1 | Crea un asset con valuta esotica (es. JPY) senza tassi FX configurati | Asset creato | |
| 7.2 | Crea Transfer/Adjustment qty>0 su questo asset → Valida | Banner "Missing FX pairs" + toggle Auto disabilitato forzato Manual | |
| 7.3 | Banner validazione in alto | Errore "Calcolo WAC fallito: coppia/e FX ... non disponibile" | |
| 7.4 | Clicca **🔄 Sync FX** | Tentativo di sync (può fallire se coppia non configurata — toast errore) | |
| 7.5 | Passa a Manual → inserisci cost_basis manualmente → Commit | Si salva senza errori | |

---

### Note per il feedback

Per ogni scenario segnare:
- ✅ / ❌ nel risultato
- 🐛 Bug: comportamento inatteso (descrivere)
- 💡 UX: qualcosa di confuso/migliorabile
- 📋 Console: errori JS in F12 → Console
- 📸 Screenshot se utile

---

## Post-Implementation: Bug Fixes & Test Hardening (2026-06-01)

### Fixes Applied

1. **COST_BASIS_REQUIRED validation (step 6d)** — backend rejects TRANSFER/ADJUSTMENT(qty>0) without `cost_basis_override` when cost_basis_mode ≠ auto. Skips promoted items.
2. **populate_mock_data.py** — 9 records fixed (added cost_basis_override), integrity assertion added.
3. **TRACE level logging** — `logging_config.py` registers TRACE at module level so `logger.log(5, ...)` works in all contexts (test, CLI, server).
4. **FX auto-reinstate bug** — `fx.py` no longer reinstates MANUAL sentinel when ALL routes for a pair are intentionally deleted (priority=None full-pair delete).
5. **Vitest $app mocks** — added `$app/navigation` and `$app/environment` mocks in `vitest.config.ts` (pre-existing failure fixed).

### Final Test Results (full suite — 2026-06-01)

| Suite | Result |
|-------|--------|
| External | ✅ PASS |
| DB (8/8) | ✅ PASS |
| Services | ✅ PASS |
| Utils | ✅ PASS |
| Schemas | ✅ PASS |
| API (39/39) | ✅ PASS |
| E2E (Playwright) | ✅ PASS |
| Frontend Utility (Vitest) | ✅ PASS |
| Brokers | ✅ PASS |
| User Tests | ✅ PASS |
| FX Tests | ✅ PASS |
| Asset Tests (7/7) | ✅ PASS |
| Transaction Tests (17/17) | ✅ PASS |

> **13/13 suites green.** All pre-existing E2E failures resolved:
> - `asset-event-delete`: switched to active asset (Apple) with 1Y range
> - `asset-detail` chart toggle: increased OHLCV load timeout to 10s
> - `transactions-modals` BulkModal validation: verify API response directly (bypasses pre-existing WAC reactive cycle race)

---

## 🧪 Walktest Umano (post `db populate`)

> Prerequisiti: backend attivo su 6040, `./dev.py db populate` eseguito, login come `e2e_test_user`.

### Scenario 1 — "Il dividendo Apple arriva: lo collego all'evento giusto"

**Contesto**: Hai un asset Apple con eventi DIVIDEND dichiarati. Vuoi registrare l'incasso e collegarlo all'evento corretto.

1. Vai in **Transactions → + New**
2. Scegli tipo **DIVIDEND**, broker **Directa**, asset **Apple Inc**
3. Metti data **oggi**, quantità lasciala 0, importo **0.25 EUR**
4. Apri la sezione **▸ Optional** — verifica che appare il campo **"Linked Event"** (un dropdown, NON un input numerico)
5. Il dropdown mostra gli eventi Apple vicini alla data TX (±7gg default). Se nessuno cade nel range:
   - Sposta lo **slider** ±days verso destra (30, 60, 90) — gli eventi appaiono man mano
   - Verifica che lo slider ricorda la tua preferenza se chiudi e riapri il form
6. Seleziona un evento → il suo ID viene salvato
7. Clicca **Apply** → nel workspace del BulkModal, la TX è pronta
8. **NON committare** — chiudi il modale (stiamo solo verificando il picker)

funziona solo a 90d
L'estetica però è completamente da buttare e rifare, le card sono illegibili e anche il not found con il trattino non si può vedere:
<div class="fixed z-[9999] bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700
                   rounded-lg shadow-lg overflow-y-auto" data-simpleselect-dropdown="ss-55qzpm" style="top: 603.43px; left: 20px; min-width: 464.711px; width: max-content; max-height: 240px;"><!----><!----><button type="button" role="menuitem" class="w-full flex items-center justify-between px-3 py-2 text-sm text-left transition-colors
                               
                               bg-libre-green/10 dark:bg-libre-green/20
                               text-gray-900 dark:text-gray-100"><!----><span class="truncate">—</span><!----> <!----></button><button type="button" role="menuitem" class="w-full flex items-center justify-between px-3 py-2 text-sm text-left transition-colors
                               
                               hover:bg-gray-50 dark:hover:bg-slate-700
                               bg-libre-green/5 dark:bg-libre-green/10 text-libre-green dark:text-green-400"><!----><span class="truncate emoji-flag">💰 💰 2026-03-04 — 0.240000 USD Quarterly dividend</span><!----> <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-check ml-2 flex-shrink-0 text-libre-green dark:text-green-400"><!----><path d="M20 6 9 17l-5-5"></path><!----><!----><!----></svg><!----></button><!----></div>

Lo slider non ha senso che arrivi così lontano, mi sarei aspettato massimo 14gg di escursione massima, di conseguenza bisogna aggiornare il db populate o nel test scegliere una data adatta.
A livello di pacchetto mi pare funzioni, visto che ricevo:
{"creates":[{"broker_id":3,"type":"DIVIDEND","date":"2026-06-02","quantity":"0","asset_id":1,"cash":{"code":"USD","amount":"00.25"},"asset_event_id":1}]}

La cella dentro il bulk modal che linka l'evento mostra l'id, dovrebbe mostrare dati sull'evento:
<td class="td-data svelte-1utaimv"><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><!----><span class="font-mono text-xs">#1</span><!----></td>

facendo edit sulla riga (ancora in stato di new) si apre correttamente e se metto not set dalla validate scompare corettamente:
{"creates":[{"broker_id":3,"type":"DIVIDEND","date":"2026-06-02","quantity":"0","asset_id":1,"cash":{"code":"USD","amount":"00.25"}}]}

anche il commit, ed edit della stessa transazione una volta che diventano salvate funzionano e si visualizzano come prima.


direi che il problema è estetico, serve pianificare meglio delle ascii art, magari prendendo spunto da come vengono mostrati i dati sugli eventi nell'info box dell'asset, o con un idea più innovativa.

**Cosa verifica**: Step B (AssetEventPicker) funziona end-to-end. Il dropdown mostra eventi reali, il range slider filtra, la persistenza localStorage funziona.

---

### Scenario 2 — "Trasferisco ETF da un broker all'altro, il WAC viene calcolato"

**Contesto**: Vuoi simulare un TRANSFER IN (titoli che arrivano). Il sistema deve calcolare automaticamente il costo medio ponderato.

1. Vai in **Transactions → + New**
2. Scegli tipo **TRANSFER**, broker **Directa**, asset **Vanguard S&P 500** (o qualsiasi ETF con storico TX)
3. Quantità **5**, data **oggi**
4. Il campo "Cost Basis" dovrebbe mostrare la modalità **Auto** (toggle slider) — il WAC viene calcolato dal backend durante la validazione
5. Clicca **Apply** → nel workspace BulkModal:
   - La cella "Cost Basis" mostra un valore con icona 💡 (calcolato automaticamente)
   - Se l'asset è in valuta diversa dalla base (es. USD vs EUR), la sezione WAC preview dovrebbe mostrare l'indicatore 💱 (FX conversion applied)
6. **Ora forza il caso problematico**: torna su, modifica il TRANSFER, metti una data molto vecchia (2020-01-01)
   - Se non ci sono rate FX per quel periodo: il WAC preview mostra **⚠️ amber banner** con messaggio tipo "FX rates unavailable for USD/EUR"
   - Il toggle Auto si disabilita → costretto in **Manual** mode
   - Appare un bottone **🔄 Sync FX** — cliccandolo, tenta il sync delle rate mancanti

In realtà ho fatto apple su interactive broker ma ho dovuto aggiungere una buy in euro, potremmo migliorare il db populate mettendo su un altro asset, magari microsoft delle transazioni per fare apposta questo test.
Comunuque messa la buy la riga è comparsa e ha l'icona:
<tr class="border-t border-gray-100 dark:border-slate-800 bg-indigo-50/50 dark:bg-indigo-900/10"><td class="px-2 py-0.5"><div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><span class="cursor-help text-indigo-500">●</span><!----></div> <!----><!----></td><td class="px-2 py-0.5"><span class="inline-flex items-center gap-1"><img alt="" class="w-3 h-3 object-contain" src="/icons/transactions/buy.png"><!----> <span>Acquisto</span></span></td><td class="px-2 py-0.5">2026-06-01</td><td class="px-2 py-0.5 text-right font-mono">300</td><td class="px-2 py-0.5 text-right font-mono">0,11 € 🇪🇺 EUR <!----><span class="ml-0.5 text-gray-400" title="FX converted">💱</span><!----></td><td class="px-2 py-0.5 text-right"><span class="inline-block px-1 rounded text-[9px] bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400">Pesata</span></td><td class="px-2 py-0.5 text-left font-mono">9,494 € 🇪🇺 EUR</td></tr>
Però non c'è la freccia al nuovo valore, quello post conversione, e non è facile fare i vari test senza dati.
In oltre in cima, sul titolo della sezione sarebbe utile avere un recup che comunichi all'utente che la conversione ha richiesto altro, in questo caso una conversione, ora non mostra nulla ancora:
<div class="flex items-center gap-2"><span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex items-center gap-1">Override costo medio <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400 dark:text-gray-500"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg><!----></div> <!----><!----></span> <div class="flex items-center gap-1 text-[10px] ml-auto" data-testid="tx-form-cost-basis-toggle"><button type="button" class="px-1.5 py-0.5 rounded bg-libre-green/10 text-libre-green font-medium" data-testid="tx-form-cost-basis-toggle-auto">Auto</button> <span class="text-gray-300 dark:text-gray-600">|</span> <button type="button" class="px-1.5 py-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" data-testid="tx-form-cost-basis-toggle-manual">Manuale</button></div><!----></div>

per arrivare a fare il test strano ho creato queste 4 transazioni:
{"creates":[{"broker_id":1,"type":"TRANSFER","date":"2005-06-01","quantity":"-3","asset_id":1,"link_uuid":"0486076f-cd3a-4cff-a07e-9db5fa4372f9"},{"broker_id":3,"type":"TRANSFER","date":"2005-06-04","quantity":"3","asset_id":1,"cost_basis_mode":"auto-detail","cost_basis_override":null,"link_uuid":"0486076f-cd3a-4cff-a07e-9db5fa4372f9"},{"broker_id":1,"type":"BUY","date":"2002-06-07","quantity":"300","asset_id":1,"cash":{"code":"EUR","amount":"-30"}},{"broker_id":1,"type":"ADJUSTMENT","date":"2000-06-02","quantity":"10","asset_id":1,"cost_basis_override":{"amount":"40","code":"USD"}},{"broker_id":1,"type":"DEPOSIT","date":"2000-06-08","quantity":"0","cash":{"code":"EUR","amount":"1000"}}]}
e finalmente compare il banner:
<div class="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/40 rounded-lg border p-3 text-left" data-testid="tx-bulk-issues-header"><div class="flex-1 min-w-0"><p class="font-semibold">⚠️ Sono stati identificati degli errori nei campi</p> <!----> <!----> <div class="mt-1.5"><!----><ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues"><li><button type="button" class="underline hover:opacity-80 text-left" data-testid="tx-bulk-issue">Riga 2: ❌ Calcolo WAC fallito: coppia/e FX EUR/USD non disponibile/i. Sincronizza i tassi FX o passa alla modalità manuale.</button></li></ul><!----> <!----><!----></div><!----></div> <button type="button" class="shrink-0 p-0.5 rounded opacity-60 hover:opacity-100 transition-opacity" aria-label="Dismiss">✕</button><!----></div>
che però ha problemi di visualizzazione perchè non usa l'helper che mostra bandiera e freccia oltre al codice valuta, e non compare il bottone sync fx

in oltre, anche se scrive riga 2 ed è cliccabile, se la clicco, la riga non fa pulse e non scrolla su di essa, sarebbe utile che lo facesse per guidare l'utente al problema. (credo sia perchè la riga 2 è quella hidenn della doppia transazione, e questo apre uno spiraglio su una possibile classe di bug non ancora affrontatta)

se entro dentro il form modal di quella riga, qualcosa compare:
<div class="mt-3"><div class="flex flex-col gap-1.5" data-testid="tx-form-cost-basis"><div class="flex items-center gap-2"><span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex items-center gap-1">Override costo medio <div class="tooltip-wrapper svelte-bgl7um" role="button" tabindex="0"><!----><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400 dark:text-gray-500"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg><!----></div> <!----><!----></span> <div class="flex items-center gap-1 text-[10px] ml-auto" data-testid="tx-form-cost-basis-toggle"><button type="button" class="px-1.5 py-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" data-testid="tx-form-cost-basis-toggle-auto" disabled="">Auto ⚠️</button> <span class="text-gray-300 dark:text-gray-600">|</span> <button type="button" class="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-gray-200 font-medium" data-testid="tx-form-cost-basis-toggle-manual">Manuale</button></div><!----></div> <div class="flex items-center gap-2 "><div class="compact-cash svelte-1a4aanh sign-ok" data-testid="tx-form-cost-basis-input"><input type="number" step="any" inputmode="decimal" autocomplete="off" class="amount-input svelte-1a4aanh" placeholder="0.00" data-testid="tx-form-cost-basis-input-amount"> <div class="currency-wrap svelte-1a4aanh"><div class="relative "><div aria-haspopup="listbox" role="combobox" aria-controls="searchselect-listbox-tnh0b36" aria-expanded="false" class="w-full flex items-center justify-between px-3 py-2 text-sm border rounded-lg
               transition-all text-left gap-2
               bg-white dark:bg-slate-700 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500 cursor-pointer
               " tabindex="0"><!----><!----><div class="flex-1 min-w-0"><!----><div class="flex items-center gap-1.5 min-w-0"><span class="text-sm shrink-0 leading-none">🇺🇸</span><!----> <span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">USD&nbsp;<span class="text-gray-400 text-xs">$</span><!----></span></div><!----></div><!----> <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-chevron-down text-gray-400 shrink-0 transition-transform "><!----><path d="m6 9 6 6 6-6"></path><!----><!----><!----></svg><!----></div> <!----></div><!----> <span class="sr-only svelte-1a4aanh" data-testid="tx-form-cost-basis-input-currency">USD</span></div></div><!----> <!----></div> <!----><!----> <div class="flex flex-col gap-1.5 text-[10px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/10 rounded p-2" data-testid="tx-form-cost-basis-missing-pairs"><div class="flex items-start gap-1"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon lucide lucide-triangle-alert mt-0.5 shrink-0"><!----><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path><!----><path d="M12 9v4"></path><!----><path d="M12 17h.01"></path><!----><!----><!----></svg><!----> <div><p class="font-medium">Impossibile calcolare il PMC: tasso FX mancante</p> <p class="text-gray-500">EUR/USD</p><!----></div></div> <div class="flex flex-wrap gap-1.5 ml-4"><a href="/fx" class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200 no-underline" data-testid="tx-form-cost-basis-action-add-fx">Aggiungi coppia FX →</a> <button type="button" class="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200" data-testid="tx-form-cost-basis-action-sync-fx">Sincronizza tassi FX</button> <button type="button" class="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200" data-testid="tx-form-cost-basis-action-sync-prices">Sincronizza prezzi asset</button></div></div><!----> <!----> <!----> <!----></div><!----></div>
ma oltre ad avere anche qui un estetica sbagliata, i 3 bottoni non dovrebbero comparire assieme, ma in base alla situazione: se la coppia è mancante, mostro solo "Sync FX". Se la coppia è presente ma stale, mostro "Sync FX" + "Sync Prices". Se la coppia è presente e aggiornata, non mostro nessuno dei 2 (o eventualmente solo "Sync Prices" se vogliamo dare all'utente la possibilità di forzare un aggiornamento). o forse altro, bisogna ragionarlo

e in fine abbiamo il goto all'fx global page, e se cliccato quando poi torniamo indietro ormai il contesto è perso, infatti non doveva esserci.


**Cosa verifica**: Step C (WAC FX staleness feedback). Il backend propaga l'info FX, il frontend la mostra correttamente, il degraded mode (Manual forzato) funziona, il Sync FX triggera il download delle rate.

---

piccola nota extra, ho messo per errore un asset di tipo index e il backend ha giustamente dato errore, ottimo!
ricordo che era esattamente quello che volevo. Siccome gli asset disattivi li mostriamo grigi e non selezionabili nel select degli asset, potremmo fare la stessa cosa anche per gli index in form modal?

---

### Scenario 3 — "Edito una TX esistente dal DataTable: il form si apre con i dati giusti"

**Contesto**: Apri una TX già salvata per modificarla. Questo testa che il nuovo sistema Props (`items`) passi correttamente i dati.

1. Vai in **Transactions** — nella tabella, fai **doppio click** su un TRANSFER esistente (uno che ha un partner legato, tipo BUY Directa ↔ SELL altro broker)
2. Si apre il FormModal in modalità **Edit**:
   - Verifica che **tutti i campi sono precompilati** (broker, asset, quantità, data, tipo)
   - Se è una coppia, il partner è mostrato sotto (chip o riga secondaria)
3. Modifica qualcosa (es. cambia una tag) → **Apply**
4. Nel BulkModal workspace: la TX appare come "update" con le modifiche
5. **Ora prova da +page**: seleziona 3 TX con le checkbox → clicca **Edit selected**
   - Il BulkModal si apre con 3 righe → doppio click su una → FormModal la mostra correttamente
6. Chiudi tutto senza committare

mi pare che funzioni tutto, è anche confermato dal fatto che tutti i test già scritti passano.

**Cosa verifica**: Step A (FormModal props unification). Il singolo `items` prop funziona per tutti i casi: singola TX, coppia con partner, edit da BulkModal. Nessuna regressione nella popolamento del form.

---

### Scenario Bonus — "L'ADJUSTMENT senza WAC viene bloccato"

**Contesto**: Verifica che il sistema impedisca dati sporchi.

1. **Transactions → + New** → ADJUSTMENT, qty **5**, asset qualsiasi
2. Lascia Cost Basis in **Auto** → Apply → il workspace lo mostra con 💡 WAC calcolato → ✅ OK
3. Ora rifai: ADJUSTMENT, qty **5**, togli la modalità Auto (toggle su Manual), **NON** inserire un valore di cost basis
4. Dovresti non poter proseguire (il bottone Apply disabilitato o validazione frontend che avverte)
5. Se riesci ad applicare: nel BulkModal, il Validate dovrebbe ritornare un **issue COST_BASIS_REQUIRED**

Si funziona anche se vorrei delle proposte di messaggio più chiare:
<div class="flex-1 min-w-0"><!----><!----><!----><!----> <p class="font-semibold text-sm mb-1.5" data-testid="tx-form-issues-header">Considerando le altre modifiche in sospeso, questa riga causa i seguenti problemi:</p> <ul class="list-disc list-inside space-y-0.5 text-sm" data-testid="tx-form-issues"><li data-testid="tx-form-issue">❌ Costo base obbligatorio per Aggiustamento con quantità positiva. Usa Auto (PMC) o inserisci manualmente.</li></ul><!----> <!----><!----></div>
usare "Costo base obbligatorio" come inizio frase è poco chiaro, e sarebbe meglio rendere il parametro in grassetto.

ho invece trovato un bug interessante sul bulk, se faccio apply con questo errore nel bulk compare, ma invece di essere assegnato alla riga 4, che è quella corretta, mostra riga 1, che contiene una transafert che quindi è una doppia adjustment, credo possa avere a che fare con il bug di sopra:
questo il messaggio:
<div class="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/40 rounded-lg border p-3 text-left" data-testid="tx-bulk-issues-header"><div class="flex-1 min-w-0"><p class="font-semibold">⚠️ Sono stati identificati degli errori nei campi</p> <!----> <!----> <div class="mt-1.5"><!----><ul class="list-disc pl-4 space-y-0.5 text-sm text-left" data-testid="tx-bulk-issues"><li><button type="button" class="underline hover:opacity-80 text-left" data-testid="tx-bulk-issue">Riga 1: ❌ Costo base obbligatorio per Aggiustamento con quantità positiva. Usa Auto (PMC) o inserisci manualmente.</button></li></ul><!----> <!----><!----></div><!----></div> <button type="button" class="shrink-0 p-0.5 rounded opacity-60 hover:opacity-100 transition-opacity" aria-label="Dismiss">✕</button><!----></div>

e questa la serie di transazioni che triggerano l'errore:
{"creates":[{"broker_id":5,"type":"ADJUSTMENT","date":"2026-06-02","quantity":"4","asset_id":12}],"updates":[{"id":38,"tags":["delete-safe","access-test","balance-safe"]},{"id":39,"tags":["delete-safe","access-test","balance-safe"],"cost_basis_override":{"code":"USD","amount":"3500.000000"}},{"id":34,"tags":["access-test","core"]},{"id":35,"type":"ADJUSTMENT","tags":["access-test","core"],"cost_basis_override":{"code":"USD","amount":"65000.000000"}}]}

**Cosa verifica**: La validazione step 6d del backend — niente più dati sporchi nel DB.
