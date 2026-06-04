# Plan: R3-SP-D — "+ New Event" Inline Create in AssetEventPicker

**Date**: 3 Giugno 2026
**Status**: ✅ COMPLETE
**Priority**: P3
**Parent**: [`plan-R3-SP-D-BugfixRound2.prompt.md`](./plan-R3-SP-D-BugfixRound2.prompt.md)
**Wiki Source**: [`phase07-part4-round2`](../../../LibreFolio_devWiki/wiki/sources/phase07-part4-round2.md)

---

## 🎯 Obiettivo

Aggiungere un bottone **"+ Nuovo evento"** nel footer del dropdown `AssetEventPicker` che apre un mini-form inline per creare un evento direttamente dalla transazione — stessa UX di "Create new" per broker e asset.

---

## Contesto Architetturale

- **Pattern di riferimento**: `BrokerSearchSelect.createLabel` + `onCreateNew` → `BrokerModal`
- **API**: `POST /api/v1/assets/events` — accetta `[{asset_id, events: [{date, type, value: {code, amount}, notes?}]}]`
- **Policy D**: `event.currency == asset.currency` (backend hard-400 `EVENT_CURRENCY_MISMATCH`)
- **Campi evento**: `type` (enum filtrata a 3 tipi), `amount` (decimal), `notes` (string opzionale)
- **Data**: pre-compilata da `txDate` del picker (la data della transazione)
- **Valuta**: ereditata da `asset.currency` (non editabile dall'utente)
- **Logica upsert**: riusa `zodiosApi.upsert_events_bulk_api_v1_assets_events_post` (stessa chiamata di `AssetDataEditorSection`)
- **Enum condivisa**: estrarre `getEventTypeOptions(t, filter?)` in `$lib/utils/eventTypes.ts` per evitare duplicazione con `AssetDataEditorSection`

---

## ASCII Art — Flow UX

```
┌─────────────────────────────────────────────────┐
│  AssetEventPicker (dropdown aperto)             │
│                                                 │
│  ┌───────────────────── Header ──────────────┐  │
│  │  ◀ [slider ±N gg] ▶   da XX a YY         │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─── Item ──────────────────────────────────┐  │
│  │  💰 Dividend · 28 mag · 0.25 $ 🇺🇸 USD    │  │
│  │       Δ +0.25  (verde)                    │  │
│  └───────────────────────────────────────────┘  │
│  ┌─── Item ──────────────────────────────────┐  │
│  │  📋 Nessun evento collegato               │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ─────────────── separator ──────────────────── │
│                                                 │
│  [ + Nuovo evento ]  ← bottone footer (indigo) │
│                                                 │
└─────────────────────────────────────────────────┘

        ↓ Click "+ Nuovo evento"
        ↓ (dropdown si chiude, si apre mini-modal)

┌─────────────────────────────────────────────────┐
│  ✨ Crea evento per {asset_name}                │
│  ─────────────────────────────────────────────  │
│                                                 │
│  Tipo:    [ 💰 Dividendo       ▼ ]             │
│                                                 │
│  Data:    [ 2026-06-03 ]  (pre-compilata)       │
│                                                 │
│  Importo: [ 0.25 ]  {currency}                  │
│                                                 │
│  Note:    [ _________________________ ]         │
│           (opzionale)                           │
│                                                 │
│         [ Annulla ]    [ ✅ Crea ]              │
│                                                 │
└─────────────────────────────────────────────────┘

        ↓ Click "✅ Crea"
        ↓ API call → success → refresh list → auto-select

┌─────────────────────────────────────────────────┐
│  AssetEventPicker (trigger chiuso)              │
│  💰 28 mag · 0.25 $ 🇺🇸 USD  Δ +0.25          │
│  (evento appena creato auto-selezionato)        │
└─────────────────────────────────────────────────┘
```

---

## Decisioni di Design

| Decisione | Scelta | Rationale |
|-----------|--------|-----------|
| Dove appare il form? | **Mini-modal overlay** (non nel dropdown) | Il dropdown è troppo stretto per un form. Usa position:fixed come Tooltip/BrokerModal. |
| Tipo default? | **DIVIDEND** (pre-selezionato) | È il caso d'uso primario (collegare dividendo a transazione) |
| Data editabile? | **Sì** (pre-compilata da txDate) | L'utente potrebbe voler creare un evento con data diversa |
| Importo obbligatorio? | **Sì** (required, min 0.01) | Un evento senza importo non ha senso |
| Filtro tipi? | **Solo event_compatible** (DIVIDEND, INTEREST, ADJUSTMENT) | SPLIT e MATURITY_SETTLEMENT non sono linkabili a transazioni |
| Dopo creazione? | **Auto-select + refresh lista + toast** | UX fluida, l'utente non deve selezionare manualmente |
| Riuso codice? | **Estrarre `getEventTypeOptions()` in shared util** | Evita duplicazione con `AssetDataEditorSection` (stessa enum, stessi emoji) |
| z-index mini-modal | **zIndex prop + 10** (sopra FormModal) | Consistente con pattern BrokerModal/AssetModal |

---

## Step

### Step A — Estrarre shared util `eventTypes.ts` + bottone footer ✅ (2026-06-03)

> **Note implementazione**: Creato `frontend/src/lib/utils/eventTypes.ts` con `getEventTypeOptions`, `EVENT_TYPES_TX_COMPATIBLE`, `EVENT_TYPES_ALL`. Refactored `AssetDataEditorSection.svelte` per importare da util. Aggiunto prop `onCreateNew` + footer button con `<hr>` in `AssetEventPicker.svelte`. Aggiunte chiavi i18n (Step D anticipato). svelte-check: 0 errori.

1. Creare `frontend/src/lib/utils/eventTypes.ts`:
   - `getEventTypeEmoji(type: string): string` — già esiste in scope locale, estrarre
   - `getEventTypeOptions(t: TranslationFn, filter?: string[]): EventTypeOption[]` — costruisce le opzioni con label, emoji, tooltip
   - `EVENT_TYPES_TX_COMPATIBLE = ['DIVIDEND', 'INTEREST', 'ADJUSTMENT']`
2. Refactorare `AssetDataEditorSection.svelte` per importare da questo util
3. In `AssetEventPicker.svelte`:
   - Aggiungere prop `onCreateNew?: () => void`
   - Rendere bottone footer separato da `<hr>` (solo se `onCreateNew` è fornito)
   - Click → chiude dropdown + chiama `onCreateNew()`

### Step B — Mini-modal `EventCreateMiniModal.svelte` ✅ (2026-06-03)

> **Note implementazione**: Creato `EventCreateMiniModal.svelte` con form 4 campi (type, date, amount, notes), backdrop overlay, keyboard ESC, API upsert + re-fetch per ID. Usa `getEventTypeOptions` da shared util. Toast su successo. svelte-check: 0 errori.

Creare `frontend/src/lib/components/transactions/EventCreateMiniModal.svelte`:

**Props**:
```typescript
interface Props {
    open: boolean;
    assetId: number;
    assetName: string;
    assetCurrency: string;
    defaultDate: string;
    zIndex?: number;
    oncreated?: (eventId: number) => void;
    onclose?: () => void;
}
```

**Implementazione**:
- Overlay backdrop + card centrata (max-w-sm, rounded-xl, shadow-xl)
- Importa `getEventTypeOptions` da `$lib/utils/eventTypes.ts` con filtro `EVENT_TYPES_TX_COMPATIBLE`
- 4 campi: type `<select>`, date `<input type="date">`, amount `<input type="number">`, notes `<input type="text">`
- Submit: `zodiosApi.upsert_events_bulk_api_v1_assets_events_post([{asset_id, events: [{date, type, value: {code, amount}, notes}]}])`
- Parse response → estrai `event_id` → `oncreated(event_id)` + toast
- Keyboard: Esc = close, Enter = submit
- Click-outside = close

### Step C — Integrazione in TransactionFormModal ✅ (2026-06-03)

> **Note implementazione**: Aggiunto `createEventOpen` state, import `EventCreateMiniModal`, passato `onCreateNew` prop a AssetEventPicker, montato modale con wiring `oncreated → draft.asset_event_id`. svelte-check: 0 errori.

1. Stato `createEventOpen = $state(false)`
2. Import `EventCreateMiniModal`
3. Passare `onCreateNew={() => createEventOpen = true}` a `<AssetEventPicker>` (solo se `!isReadonly && draft.asset_id`)
4. Montare `<EventCreateMiniModal>` con props da draft + asset cache
5. `oncreated` → `draft.asset_event_id = id` + close

### Step D — i18n (4 lingue) ✅ (2026-06-03)

> **Note implementazione**: Chiavi aggiunte in Step A (anticipato): `eventPickerCreateNew`, `eventCreateTitle`, `eventCreateSuccess`, `eventCreateAmountRequired`, `eventCreateDateRequired` in 4 lingue via `./dev.py i18n add`.

| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `transactions.form.eventPickerCreateNew` | + New event | + Nuovo evento | + Nouvel événement | + Nuevo evento |
| `transactions.form.eventCreateTitle` | Create event for {asset} | Crea evento per {asset} | Créer événement pour {asset} | Crear evento para {asset} |
| `transactions.form.eventCreateSuccess` | Event created | Evento creato | Événement créé | Evento creado |

### Step E — Test E2E ✅ (2026-06-03)

> **Note implementazione**: Aggiunto test "create new event via inline modal" in `tx-event-picker.spec.ts`. Verifica: apre dropdown → click "+ New event" → fill form → submit → modal chiude → trigger mostra 💰. 5/5 test passano.

In `tx-event-picker.spec.ts`:
1. Test: "create new event via inline modal"
   - Selezionare tipo DIVIDEND, data, asset
   - Aprire dropdown → click "+ Nuovo evento"
   - Fill form (type, amount) → submit
   - Verificare che l'evento appena creato è auto-selezionato nel trigger

### Step F — Cleanup + Verifica ✅ (2026-06-03)

> **Note implementazione**: svelte-check 0 errori. Prettier applicato a tutti i file. E2E 5/5 pass. Aggiunto `$effect` in AssetEventPicker per force re-fetch quando value punta a evento non in lista (fix auto-select post-create).

1. `npx svelte-check --threshold error`
2. `./dev.py test front-transaction tx-event-picker`
3. Format con Prettier
4. `git add` tutto

---

## File da creare/modificare

| File | Azione | Step |
|------|--------|------|
| `frontend/src/lib/utils/eventTypes.ts` | CREATE | A |
| `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` | EDIT (import refactor) | A |
| `frontend/src/lib/components/transactions/AssetEventPicker.svelte` | EDIT | A |
| `frontend/src/lib/components/transactions/EventCreateMiniModal.svelte` | CREATE | B |
| `frontend/src/lib/components/transactions/TransactionFormModal.svelte` | EDIT | C |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | EDIT | D |
| `frontend/e2e/transactions/tx-event-picker.spec.ts` | EDIT | E |

---

## Execution Order

```
Step A  (shared util + footer button)  ← 10 min
  ↓
Step B  (EventCreateMiniModal)         ← 20 min
  ↓
Step C  (integrate in FormModal)       ← 10 min
  ↓
Step D  (i18n 4 lingue)                ← 5 min
  ↓
Step E  (E2E test)                     ← 10 min
  ↓
Step F  (cleanup + verifica)           ← 5 min
```

---

## Rischi / Note

- **Duplicati API**: l'upsert de-duplica per `(asset_id, date, type)`. Se stessa data+tipo esiste → aggiorna (non duplica). Comportamento desiderato.
- **Refresh lista picker**: dopo creazione, il picker ri-fetcha perché `value` cambia → reactivity triggera re-fetch.
- **BulkModal**: il "+ Nuovo evento" è solo nel FormModal per ora. BulkModal non ha AssetEventPicker inline. Futuro.
- **getEventTypeEmoji**: attualmente definita localmente sia in AssetEventPicker che in AssetDataEditorSection — l'estrazione elimina questa duplicazione.

---

## Post-completion: Bugfix QA (2026-06-03)

Feedback utente dopo primo walktest. Tutti risolti nello stesso commit:

| # | Issue | Fix |
|---|-------|-----|
| 1 | `ADJUSTMENT` non è un enum `AssetEventType` valido (backend ha `PRICE_ADJUSTMENT`) | Fix `EVENT_TYPES_TX_COMPATIBLE` → `['DIVIDEND', 'INTEREST', 'PRICE_ADJUSTMENT']` |
| 2 | `assetDetail.eventType.ADJUSTMENT` non tradotto (key inesistente) | Conseguenza di #1 — risolto |
| 3 | `transactions.form.fields.amount` key path errato | Fix → `transactions.fields.amount` |
| 4 | Modal non usa `ModalBase.svelte` | Rewrite completo con ModalBase + header/body/footer pattern |
| 5 | Footer annulla/crea: styling diverso dalle altre modali | Ora usa `bg-gray-200`/`bg-libre-green` come FxPairAddModal |
| 6 | Calendario di sistema invece di `SingleDatePicker` | Sostituito con `<SingleDatePicker inputStyle allowFuture>` |
| 7 | Valuta forzata a asset currency | Confermato corretto (Policy D: `event.currency == asset.currency`) |
| 8 | Amount con frecce: step=0.0001 causa incrementi assurdi | Cambiato a `type="text" inputmode="decimal"` |
| 9 | Errore API mostrato inline rosso invece che banner | Ora usa `<InfoBanner variant="error">` in cima al body |
| 10 | Click-outside senza conferma dirty form | Aggiunto `isDirty` check + `confirm()` su `handleClose()` |

---

## 🔗 Cross-links

- **Parent (Round 2)**: [`plan-R3-SP-D-BugfixRound2.prompt.md`](./plan-R3-SP-D-BugfixRound2.prompt.md)
- **Grandparent (R3-SP-D)**: [`../plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md`](../plan-R3-SP-D-FormModalEventPickerWacFx.prompt.md)
- **Riferimento codice eventi**: `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` (linee 84-104, 338-374)
- **Wiki Source**: [`phase07-part4-round2`](../../../LibreFolio_devWiki/wiki/sources/phase07-part4-round2.md)
- **Phase 7 macro**: [`../phases/phase-07-transactions.md`](../phases/phase-07-transactions.md)

