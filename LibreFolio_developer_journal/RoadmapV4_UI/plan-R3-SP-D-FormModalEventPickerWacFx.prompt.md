# Plan: D2 Round 3 (SP-D) — FormModal Props Unification + AssetEventPicker + WAC FX Feedback

**Date**: 1 Giugno 2026
**Status**: ⏳ READY
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

## Step A — FormModal Props Unification

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

## Step B — AssetEventPicker

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

## Step C — WAC FX Staleness Feedback

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

