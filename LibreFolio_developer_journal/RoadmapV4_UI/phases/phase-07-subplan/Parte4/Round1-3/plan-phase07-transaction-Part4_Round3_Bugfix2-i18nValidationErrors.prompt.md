# Plan — Phase 7 · Part 4 · Round 3 · Bugfix-2 — i18n Validation Errors

**Date**: 2026-04-29
**Status**: ✅ DONE — implementazione completa, in attesa di walkthrough utente
**Priority**: P1 (UX quality — user sees raw English backend strings like "broker 3")
**Estimated effort**: ~4–5 h

**Parent**: [`plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md`](./plan-phase07-transaction-Part4_Round3_Bugfix1-formModalRedesign.prompt.md)

---

## 🎯 Obiettivo

Il sistema di validazione transazioni invia messaggi di errore come stringhe inglesi libere. Sia `POST /transactions/validate` (campo `TXValidationIssue.error`) sia gli errori Pydantic 422 (`detail[].msg`) usano testo hardcoded. L'utente vede messaggi come `"Cash balance for USD goes negative (-1854.000000) on 2026-04-28 for broker 3"` — incomprensibili perché "broker 3" non dice nulla.

**Soluzione**: il backend invia **codici strutturati + parametri minimi** (solo ID numerici, date, importi, codici valuta — niente nomi risolti). Il frontend risolve i nomi via store (`brokerStore`, `assetStore`) e formatta gli importi con `currencyFormat.ts`, poi mostra il messaggio tradotto. Il campo `error` resta come fallback/debug.

---

## 🏗️ Design decisions (confermate dall'utente)

1. **Solo dati puri** nei `params`: `brokerId`, `assetId`, `currency`, `balance`, `date`. Niente `brokerName`, `assetName` — il frontend li ha già negli store e li risolve autonomamente.
2. Il campo `error: str` resta invariato per fallback/debug (visibile in DevTools, non all'utente).
3. Nuovi campi opzionali su `TXValidationIssue`: `code: Optional[str]`, `params: Optional[Dict[str, Any]]`, `field: Optional[str]`.
4. Frontend risolve `transactions.errors.<code>` con i params arricchiti (nomi risolti da store). Se la chiave manca, fallback a `error`.
5. Frontend usa `currencyFormat.ts` helpers (es. `formatCurrencyAmountPlain`) per formattare importi con simbolo/flag.

---

## 📋 Catalogo codici errore

### Pydantic schema rules (`TXCreateItem.validate_transaction_rules`)

| Code | Rule | Params | `field` |
|------|------|--------|---------|
| `assetRequired` | 5 | `{type}` | `asset_id` |
| `cashRequired` | 7 | `{type}` | `cash` |
| `cashForbidden` | 2, 8 | `{type}` | `cash` |
| `assetForbidden` | 3, 4 | `{type}` | `asset_id` |
| `qtyPositive` | 10 (BUY) | `{type}` | `quantity` |
| `qtyNegative` | 10 (SELL) | `{type}` | `quantity` |
| `qtyZero` | 10 (DIV/INT/DEP/WDR/FEE/TAX) | `{type}` | `quantity` |
| `qtyNonzero` | 10 (TRANSFER/ADJUSTMENT) | `{type}` | `quantity` |
| `cashSignPositive` | 11 | `{type}` | `cash.amount` |
| `cashSignNegative` | 11 | `{type}` | `cash.amount` |
| `linkUuidRequired` | 1 | `{type}` | `link_uuid` |
| `fxConversionCashRequired` | 3 | — | `cash` |
| `fxConversionQtyZero` | 3 | — | `quantity` |
| `transferQtyNonzero` | 2 | — | `quantity` |
| `eventRequiresAsset` | 9 | — | `asset_event_id` |
| `eventTypeIncompatible` | 9 | `{type, allowed}` | `asset_event_id` |

### Balance walker (`_validate_broker_balances`)

| Code | Params | `field` |
|------|--------|---------|
| `balanceCashNegative` | `{brokerId, currency, balance, date}` | `cash` |
| `balanceAssetNegative` | `{brokerId, assetId, balance, date}` | `quantity` |

### Service layer (`validate_batch` e helper)

| Code | Params | `field` |
|------|--------|---------|
| `accessDenied` | `{brokerId}` | — |
| `txNotFound` | `{id}` | — |
| `indexAssetForbidden` | — | `asset_id` |
| `linkUuidPairCount` | `{linkUuid, count}` | `link_uuid` |
| `pairTypeMismatch` | `{typeA, typeB}` | `type` |
| `pairSameBroker` | `{brokerId}` | `broker_id` |
| `cannotLinkEventNoAsset` | — | `asset_event_id` |

**Totale**: ~25 codici.

---

## 🧱 Steps di implementazione

### Step 1 — Extend `TXValidationIssue` schema (backend)

**File**: `backend/app/schemas/transactions.py` — class `TXValidationIssue` (line 605).

Aggiungere tre campi opzionali:
```python
code: Optional[str] = Field(default=None, description="i18n error code from the catalog (e.g. 'assetRequired')")
params: Optional[Dict[str, Any]] = Field(default=None, description="Structured params for the frontend i18n resolver (IDs, dates, amounts — no resolved names)")
field: Optional[str] = Field(default=None, description="Draft field that caused the error (e.g. 'asset_id', 'quantity', 'cash.amount')")
```

**Stima**: 5 min.

---

### Step 2 — Convert Pydantic `ValueError` → `PydanticCustomError` (backend)

**File**: `backend/app/schemas/transactions.py` — metodo `TXCreateItem.validate_transaction_rules` (line 152).

Import: `from pydantic_core import PydanticCustomError`

Sostituire ogni `raise ValueError(msg)` con `raise PydanticCustomError(code, msg_template, ctx)` dove:
- `code` → codice dal catalogo
- `msg_template` → messaggio inglese originale (preserva `detail[].msg` invariato)
- `ctx` → dict con params: `{"type": self.type.value}` ecc.

In una risposta 422, Pydantic v2 serializza `ctx` dentro `detail[].ctx` — il frontend lo leggerà per estrarre `code` + params strutturati.

**Conversioni** (~18 raise):
- R1: `linkUuidRequired` + `{type}`
- R2: 3× (`assetRequired` con alias `transferAssetRequired`… → unifico in `assetRequired`) + `qtyNonzero` alias `transferQtyNonzero` + `cashForbidden`
- R3: `assetForbidden` + `fxConversionQtyZero` + `fxConversionCashRequired`
- R4: `assetForbidden` + `{type}`
- R5: `assetRequired` + `{type}`
- R7: `cashRequired` + `{type}`
- R8: `cashForbidden` + `{type: "ADJUSTMENT"}`
- R9: `eventTypeIncompatible` + `{type, allowed}`, `eventRequiresAsset`
- R10: `qtyPositive`, `qtyNegative`, `qtyZero`, `qtyNonzero` + `{type}`
- R11: `cashSignPositive`, `cashSignNegative` + `{type}`

**Nota**: i codici R2 "TRANSFER requires asset_id" e R5 "BUY requires asset_id" condividono lo stesso code `assetRequired` perché la semantica è identica — `{type}` li distingue.

**Stima**: 45 min.

---

### Step 3 — Convert `BalanceValidationError` (backend)

**File**: `backend/app/services/transaction_service.py` — class `BalanceValidationError` (line 56) + `_validate_broker_balances` (line 734).

- Aggiungere attributi `code: str` e `params: dict` a `BalanceValidationError.__init__`.
- Cash negative (line 774): `code="balanceCashNegative"`, `params={"brokerId": broker_id, "currency": currency, "balance": str(balance), "date": str(current_date)}`.
- Asset negative (line 786): `code="balanceAssetNegative"`, `params={"brokerId": broker_id, "assetId": asset_id, "balance": str(balance), "date": str(current_date)}`.

**Stima**: 15 min.

---

### Step 4 — Update `TXValidationIssue(...)` calls in `validate_batch` (backend)

**File**: `backend/app/services/transaction_service.py` — `validate_batch` (line 558) + `_validate_linked_pair` (line 145).

4a. Ogni `TXValidationIssue(...)` call riceve `code` + `params`:
- Access denied (line 590): `code="accessDenied"`, `params={"brokerId": broker_id}`, `field=None`.
- TX not found (lines 608, 621): `code="txNotFound"`, `params={"id": tx_id}`.
- INDEX forbidden (line 659): `code="indexAssetForbidden"`.
- link_uuid pair count (line 696): `code="linkUuidPairCount"`, `params={"linkUuid": link_uuid, "count": len(pair)}`.
- BalanceValidationError catch (line 705): `code=e.code, params=e.params`.
- Update catch "Cannot link event" (line 644): `code="cannotLinkEventNoAsset"`.

4b. `_validate_linked_pair` (line 145) → cambiare return type da `Optional[str]` a `Optional[Tuple[str, str, Dict[str, Any]]]` (error_msg, code, params):
- Type mismatch: `("linked pair must share...", "pairTypeMismatch", {"typeA": a.type.value, "typeB": b.type.value})`
- Same broker: `("TRANSFER requires distinct...", "pairSameBroker", {"brokerId": a.broker_id})`

Caller (line 689–691) aggiorna per destructurare la tupla.

**Stima**: 30 min.

---

### Step 5 — Regen frontend types

```bash
./dev.py api sync
```

Dopo: `TXValidationIssue` nel generated client avrà `code?: string`, `params?: Record<string, any>`, `field?: string`.

**Stima**: 5 min.

---

### Step 6 — Frontend resolver helper (nuovo file)

**File nuovo**: `frontend/src/lib/utils/resolveValidationMessage.ts`

```typescript
/**
 * Resolve a validation issue into a translated, human-friendly message.
 *
 * Priority:
 * 1. If `issue.code` exists → try $t(`transactions.errors.${code}`, {values: resolvedParams})
 * 2. If the i18n key is missing → fall back to issue.error / issue.msg
 *
 * The resolver enriches raw params (IDs) with display names from stores:
 * - params.brokerId → resolvedParams.brokerName via brokersStore
 * - params.assetId  → resolvedParams.assetName via assetsStore
 * - params.balance + params.currency → resolvedParams.formattedBalance via formatCurrencyAmountPlain
 */
```

Dipendenze:
- `$t` (svelte-i18n `$format`)
- `brokers` store (per risolvere `brokerId → name`)
- `assets` store (per risolvere `assetId → display_name`)
- `formatCurrencyAmountPlain` da `currencyFormat.ts`

Interfaccia:
```ts
export function resolveIssueMessage(
    issue: {code?: string; params?: Record<string, any>; error?: string; msg?: string},
    t: (key: string, opts?: any) => string,
    ctx?: {brokers?: Array<{id: number; name: string}>; assets?: Array<{id: number; display_name: string}>}
): string
```

**Stima**: 30 min.

---

### Step 7 — Update `extractValidationIssues` per Pydantic `ctx`

**File**: `frontend/src/lib/utils/saveWithRetry.ts`

Estendere `ValidationIssueExtracted` con `code?: string` e `params?: Record<string, any>`.

In `extractValidationIssues`: leggere `item.ctx` dalla risposta Pydantic 422 — se presente e contiene un campo tipo `type`, usarlo come `code` (il primo argomento di `PydanticCustomError` finisce in `detail[].type` in Pydantic v2; i params finiscono in `detail[].ctx`).

Mappatura Pydantic v2 response → nostri campi:
- `detail[].type` → `code` (es. `"assetRequired"`)
- `detail[].ctx` → `params` (es. `{"type": "BUY"}`)
- `detail[].msg` → `msg` (stringa fallback, invariata)

**Stima**: 20 min.

---

### Step 8 — Wire `resolveIssueMessage` nei componenti modali

**Files**:
- `TransactionFormModal.svelte` (line 632): `{issue.error}` → `{resolveIssueMessage(issue, $t, resolverCtx)}`
- `TransactionBulkModal.svelte` (line 920): `{issue.error}` → `{resolveIssueMessage(issue, $t, resolverCtx)}`
- Nel catch 422 di entrambi i modali: popolare `code` e `params` dalla `ctx` estratta.

Costruzione `resolverCtx`:
```ts
const resolverCtx = $derived({
    brokers: $brokers,   // o dal props/store appropriato
    assets: $assets,     // idem
});
```

**Stima**: 20 min.

---

### Step 9 — i18n keys (EN/IT/FR/ES)

**Files**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

Aggiungere namespace `transactions.errors` con ~25 chiavi. I params `{brokerName}`, `{assetName}`, `{formattedBalance}` sono risolti dal frontend nel resolver (Step 6), non sono params backend.

**EN** (estratto):
```json
"transactions.errors": {
    "assetRequired": "Please select an asset",
    "cashRequired": "{type} requires a cash amount and currency",
    "cashForbidden": "{type} must not have a cash movement",
    "assetForbidden": "{type} must not have an asset",
    "qtyPositive": "Quantity must be greater than 0",
    "qtyNegative": "Quantity must be less than 0",
    "qtyZero": "Quantity must be 0 for {type}",
    "qtyNonzero": "Quantity must not be 0",
    "cashSignPositive": "Cash amount must be positive for {type}",
    "cashSignNegative": "Cash amount must be negative for {type}",
    "linkUuidRequired": "{type} requires a link UUID for pairing",
    "fxConversionCashRequired": "FX Conversion requires a non-zero cash amount",
    "fxConversionQtyZero": "FX Conversion must have quantity = 0",
    "eventRequiresAsset": "Event link requires an asset to be selected",
    "eventTypeIncompatible": "{type} cannot be linked to an asset event (only {allowed})",
    "balanceCashNegative": "Cash balance for {currency} goes negative ({formattedBalance}) on {date} at {brokerName}",
    "balanceAssetNegative": "{assetName} holdings go negative ({balance}) on {date} at {brokerName}",
    "accessDenied": "Access denied: EDITOR role required for {brokerName}",
    "txNotFound": "Transaction {id} not found",
    "indexAssetForbidden": "Cannot create transactions for INDEX assets",
    "linkUuidPairCount": "Link group has {count} items (expected 2)",
    "pairTypeMismatch": "Linked pair must share the same type (found {typeA} and {typeB})",
    "pairSameBroker": "Transfer requires distinct brokers (both assigned to {brokerName})",
    "cannotLinkEventNoAsset": "Cannot link an asset event without an asset"
}
```

**IT** (estratto):
```json
"transactions.errors": {
    "assetRequired": "Seleziona un asset",
    "cashRequired": "{type} richiede un importo e una valuta",
    "cashForbidden": "{type} non deve avere un movimento di cassa",
    "assetForbidden": "{type} non deve avere un asset",
    "qtyPositive": "La quantità deve essere maggiore di 0",
    "qtyNegative": "La quantità deve essere minore di 0",
    "qtyZero": "La quantità deve essere 0 per {type}",
    "qtyNonzero": "La quantità non deve essere 0",
    "cashSignPositive": "L'importo deve essere positivo per {type}",
    "cashSignNegative": "L'importo deve essere negativo per {type}",
    "balanceCashNegative": "Il saldo {currency} va in negativo ({formattedBalance}) il {date} su {brokerName}",
    "balanceAssetNegative": "Le posizioni di {assetName} vanno in negativo ({balance}) il {date} su {brokerName}",
    "accessDenied": "Accesso negato: ruolo EDITOR necessario per {brokerName}",
    "txNotFound": "Transazione {id} non trovata",
    "indexAssetForbidden": "Non è possibile creare transazioni per asset di tipo INDEX",
    "pairTypeMismatch": "La coppia collegata deve avere lo stesso tipo (trovati {typeA} e {typeB})",
    "pairSameBroker": "Il trasferimento richiede broker diversi (entrambi su {brokerName})",
    "cannotLinkEventNoAsset": "Impossibile collegare un evento senza un asset selezionato"
}
```

FR/ES: equivalenti tradotti.

**Stima**: 45 min (~25 chiavi × 4 lingue).

---

### Step 10 — Backend tests

**Files**:
- `backend/test_scripts/test_schemas/test_transaction_schemas.py` — verificare che le eccezioni Pydantic adesso siano `PydanticCustomError` con `type` = nostro code. Assert su almeno 5 codici rappresentativi (`assetRequired`, `qtyPositive`, `cashSignNegative`, `cashForbidden`, `eventTypeIncompatible`).
- `backend/test_scripts/test_api/test_transactions_validate.py` (o equivalente) — verificare che la response di `POST /validate` con input invalido includa `code` + `params` su `TXValidationIssue`.
- `backend/test_scripts/test_services/` — test `BalanceValidationError.code` e `.params`.

**Stima**: 30 min.

---

### Step 11 — Validate finale + svelte-check + i18n audit

- `npx svelte-check` clean (0 errors).
- `./dev.py i18n audit` — tutte le chiavi presenti in tutte e 4 le lingue.
- Walkthrough manuale: verificare messaggi tradotti con nomi risolti.

**Stima**: 15 min.

---

## ✅ Final-check

- [x] `TXValidationIssue` schema ha `code`, `params`, `field` opzionali
- [x] ~18 `ValueError` → `PydanticCustomError` in `TXCreateItem.validate_transaction_rules`
- [x] `BalanceValidationError` include `code`+`params` (solo ID, niente nomi)
- [x] Tutti i `TXValidationIssue(...)` in `validate_batch` includono `code`+`params`
- [x] `_validate_linked_pair` restituisce `(error, code, params)` (non solo stringa)
- [x] Frontend types rigenerati (`./dev.py api sync`)
- [x] `resolveIssueMessage` helper creato — risolve ID→nomi da store + formatta con `currencyFormat.ts`
- [x] `extractValidationIssues` estrae `type`→`code` e `ctx`→`params` dai Pydantic 422
- [x] `TransactionFormModal` usa `resolveIssueMessage`
- [x] `TransactionBulkModal` usa `resolveIssueMessage`
- [x] 24 chiavi i18n aggiunte in EN/IT/FR/ES (1050/1050 complete)
- [x] Backend tests passano (65/65 — 7 nuovi per codici strutturati)
- [x] svelte-check clean (0 errors, 0 warnings)
- [x] i18n audit clean (1050/1050)
- [x] lint+format clean
- [ ] Walkthrough utente

---

## 🔁 Walkthrough #1 — feedback utente (2026-04-29)

### Fix applicati

| # | Issue | Fix |
|---|-------|-----|
| W1 | Errori Pydantic built-in (es. `greater_than` per `broker_id > 0`) non tradotti — il `code` era il tipo Pydantic (`"greater_than"`) che non matchava nessuna chiave `transactions.errors.*` | Aggiunto mapping `PYDANTIC_BUILTIN_KEYS` in `resolveValidationMessage.ts` + 10 chiavi i18n `transactions.pydantic.*` in 4 lingue (greaterThan, lessThan, missing, decimalParsing, ecc.) |
| W2 | `+ Add transaction` apriva BulkModal con 1 riga vuota pre-popolata invece di griglia vuota + FormModal auto-aperta | Fix in BulkModal `$effect`: in `create-many` con `initialRows=[]`, `drafts = []` (griglia vuota) + `queueMicrotask` per auto-aprire la FormModal nested |

---

## 📝 Commit strategy

3 commit incrementali:

1. `feat(backend): structured error codes on TXValidationIssue + PydanticCustomError`
   - Steps 1–4
2. `feat(frontend): resolveIssueMessage helper + i18n keys for validation errors`
   - Steps 5–9
3. `test(backend): validation code+params coverage`
   - Step 10

---

## 🔧 Fix collaterale: DB populate — saldo negativo Directa SIM

**Già applicato** (pre-plan): aggiunto deposito USD $2000 a Directa SIM (broker 3) prima del BUY Tesla (-$1845 USD) in `backend/test_scripts/test_db/populate_mock_data.py`. Saldo risultante: +$155 USD (non più negativo).

---

## 🔁 Walkthrough #1 — feedback utente (2026-04-29)

### Fix W1 — Errori Pydantic built-in non tradotti

**Problema**: errori come `greater_than` per `broker_id > 0` producono `type: "greater_than"` con `ctx: {gt: 0}` — sono tipi Pydantic built-in, non i nostri codici custom. Il frontend mostrava l'inglese raw ("Input should be greater than 0").

**Fix**: Aggiunto mapping `PYDANTIC_BUILTIN_KEYS` in `resolveValidationMessage.ts` + 10 chiavi i18n `transactions.pydantic.*` in 4 lingue (greaterThan, lessThan, missing, decimalParsing, ecc.).

### Fix W2 — `+ Add transaction` apriva BulkModal con riga pre-popolata

**Problema**: in `create-many` con `initialRows=[]`, veniva seedata `[emptyDraft()]` (una riga vuota). L'utente si aspettava griglia vuota + FormModal auto-aperta.

**Fix**: in BulkModal `$effect`, quando `create-many` con `initialRows=[]`: `drafts = []` (griglia vuota) + `queueMicrotask` per auto-aprire la FormModal nested.

---

## 🔁 Walkthrough #2 — feedback utente (2026-04-29)

### Fix W3 — Campo mancante nel messaggio Pydantic

**Problema**: "Il valore deve essere maggiore di 0" non indicava quale campo (cash? quantity? broker?).

**Fix**:
- Aggiunto `loc` propagation: Pydantic 422 `detail[].loc` (es. `body.creates.0.broker_id`) → `extractFieldName()` estrae il campo foglia → `translateFieldName()` lo traduce via `transactions.fields.*`.
- 14 chiavi `transactions.fields.*` in 4 lingue (broker_id→"Broker", asset_id→"Asset", quantity→"Quantità", ecc.).
- Errori Pydantic built-in prefissati col campo: "Broker: Il valore deve essere maggiore di 0".

### Fix W4 — broker_id=0 → messaggio generico

**Problema**: "Broker: Il valore deve essere maggiore di 0" non è user-friendly — l'utente deve capire che serve scegliere un broker.

**Fix**: Aggiunto sistema **field-specific overrides** in `resolveValidationMessage.ts`:
- Mapping `FIELD_ERROR_OVERRIDES`: `broker_id:greater_than` → "Seleziona un broker", `asset_id:*` → "Seleziona un asset", ecc.
- 4 chiavi `transactions.fieldErrors.*` in 4 lingue.
- L'override ha priorità su il Pydantic built-in generico.

### Fix W5 — Raccogliere tutti gli errori (non 1 alla volta)

**Problema**: il `model_validator` faceva `raise` alla prima violazione. L'utente vedeva 1 errore, lo fixava, ne vedeva un altro.

**Fix**: Refactored `TXCreateItem.validate_transaction_rules` per accumulare tutti gli errori in una `list[PydanticCustomError]` e fare `raise errors[0]` alla fine.

**Nota architetturale** — due tipi di errori nel response 422:

| Tipo | Origine | Quando | Raccolta multipla |
|------|---------|--------|-------------------|
| **Errori di campo** | Pydantic field validators (`Field(gt=0)`, `@field_validator`, type coercion) | Parse del body JSON, prima del model_validator | ✅ Pydantic raccoglie TUTTI automaticamente |
| **Errori business rule** | `model_validator(mode="after")` | Dopo che tutti i campi sono validi | ⚠️ Solo il primo (Pydantic v2 limita a 1 eccezione per model_validator) |

Risultato: se `broker_id=0` (campo) E `quantity=0` (campo), li vedi entrambi. Se `broker_id` è ok ma `asset_id` manca (business rule da Rule 5) E `quantity=0` (business rule da Rule 10), vedi solo il primo business rule — ma gli errori di campo sono sempre tutti presenti.

### Fix W6 — Colonne BulkModal ridistribuite

**Problema**: le colonne erano sbilanciate (Type e Broker troppo larghi, Cash troppo stretto per il CurrencySearchSelect).

**Fix**: Nuove larghezze colonne:
| Colonna | Prima | Dopo |
|---------|-------|------|
| Date | 160 | 140 |
| Type | 170 | 140 |
| Asset | 200 | 180 |
| Qty | 110 | 100 |
| Cash | 220 | 260 |
| Broker | 200 | 160 |

### Fix W7 — CurrencySearchSelect min-width in CompactCashCell

**Problema**: il selettore valuta nel campo Cash era troppo stretto — si vedeva solo la flag emoji, non il codice.

**Fix**: `CompactCashCell.svelte` → `.currency-wrap { min-width: 6rem → 8rem }`.

### Fix W8 — SingleDatePicker FormModal non uniformata

**Problema**: il SingleDatePicker nella FormModal aveva dimensioni diverse rispetto alla BulkModal (mancava `inputStyle`).

**Fix**: Aggiunto `inputStyle={true}` al SingleDatePicker nella FormModal per uniformare l'aspetto (`w-full px-3 py-2 text-sm`).

---

## ✅ Final-check aggiornato (post-walkthrough)

- [x] `TXValidationIssue` schema ha `code`, `params`, `field` opzionali
- [x] ~18 `ValueError` → `PydanticCustomError` in `TXCreateItem.validate_transaction_rules`
- [x] `BalanceValidationError` include `code`+`params` (solo ID, niente nomi)
- [x] Tutti i `TXValidationIssue(...)` in `validate_batch` includono `code`+`params`
- [x] `_validate_linked_pair` restituisce `(error, code, params)` (non solo stringa)
- [x] Frontend types rigenerati (`./dev.py api sync`)
- [x] `resolveIssueMessage` helper creato — risolve ID→nomi da store + formatta con `currencyFormat.ts`
- [x] `extractValidationIssues` estrae `type`→`code` e `ctx`→`params` dai Pydantic 422
- [x] `TransactionFormModal` usa `resolveIssueMessage`
- [x] `TransactionBulkModal` usa `resolveIssueMessage`
- [x] 24 chiavi `transactions.errors.*` + 10 `transactions.pydantic.*` + 14 `transactions.fields.*` + 4 `transactions.fieldErrors.*` in EN/IT/FR/ES
- [x] Field-name resolution: `loc` propagation → `extractFieldName` → `translateFieldName` (prefisso per errori generici)
- [x] Field-specific overrides: `broker_id:greater_than` → "Seleziona un broker"
- [x] Pydantic built-in error mapping con prefisso campo tradotto
- [x] `model_validator` raccoglie tutti gli errori (lista) prima di raise
- [x] BulkModal: griglia vuota + auto-open FormModal su `+ Add`
- [x] BulkModal: colonne redistribuite (Cash +40px, altri -60px totale)
- [x] CompactCashCell: `currency-wrap` min-width 6rem → 8rem
- [x] FormModal: SingleDatePicker con `inputStyle={true}`
- [x] Backend tests passano (65/65)
- [x] svelte-check clean (0 errors, 0 warnings)
- [x] i18n audit clean (1078/1078)
- [x] lint+format clean
- [ ] Walkthrough #3 utente

---

## 🔁 Walkthrough #3 — fix multi-error return (2026-04-29)

### Fix W9 — model_validator ritornava solo il primo errore

**Problema**: `raise errors[0]` nel `model_validator` di `TXCreateItem` ritornava solo il primo errore business-rule. Con `{broker_id: 0, type: "BUY", quantity: 0}` l'utente vedeva solo `brokerRequired`, non `assetRequired`, `cashRequired`, `qtyPositive`.

**Fix backend**: quando ci sono errori multipli, li impacchetta tutti in un singolo `PydanticCustomError` con `type="multipleBusinessRuleErrors"` e la lista completa in `ctx.errors`. Errore singolo → raise diretto (nessun wrapper).

**Fix frontend**: `extractValidationIssues()` in `saveWithRetry.ts` riconosce `type === 'multipleBusinessRuleErrors'` ed espande `ctx.errors` in issue separati, ognuno con il proprio `code` e `params`. `resolveIssueMessage` li traduce normalmente.

**Test aggiornati**: 2 test schema (`test_transfer_requires_asset_id`, `test_fx_requires_cash`) i cui `match` pattern sono stati aggiornati per matchare `multipleBusinessRuleErrors`. 65/65 passano.

### Fix W10 — `TXUpdateItem.id` con `gt=0` bloccava altri errori

**Problema regressione**: stessa root cause di W5/W9. `TXUpdateItem.id: int = Field(..., gt=0)` era un vincolo di campo — se `id=0`, Pydantic blocca tutto e non esegue ulteriori validazioni. La response era solo `"Input should be greater than 0"`.

**Fix**: rimosso `gt=0` dal campo `id` di `TXUpdateItem`, aggiunto `model_validator(mode="after")` con codice `idRequired` + messaggio "Transaction id must be > 0". Aggiunta chiave i18n `transactions.errors.idRequired` in 4 lingue + `FIELD_ERROR_OVERRIDES['id:greater_than']` + `['id:missing']`.

### Fix W11 — CompactCashCell amount input troppo stretto

**Problema**: `.amount-input` aveva `min-width: 0` — in colonne strette il campo collassava a pochi pixel.

**Fix**: `CompactCashCell.svelte` → `.amount-input { min-width: 5rem }`.

### Fix W12 — Unused imports warning in BulkModal

**Problema**: `STANDALONE_TX_TYPES` e `formatDecimalForDisplay` non più usati producevano warning di analisi statica.

**Fix**: rimossi gli import inutilizzati.

---

## 🔁 Walkthrough #4 — UX polish: traduzione tipi + elenco puntato con header (2026-04-29)

### Fix W13 — `{type}` non tradotto nei messaggi di errore

**Problema**: i messaggi come "BUY requires a cash amount and currency" mostravano il codice tipo raw ("BUY") invece del nome tradotto ("Acquisto"). L'utente vedeva frasi miste ("BUY richiede un importo e una valuta").

**Fix**: in `resolveValidationMessage.ts`, aggiunto auto-enrichment del param `type`: se `params.type` è presente, viene tradotto via `transactions.types.<TYPE>` prima di essere passato all'interpolazione i18n. Risultato: "Acquisto richiede un importo e una valuta".

### Fix W14 — Banner errori senza header e senza elenco puntato

**Problema**: gli errori di validazione apparivano come lista piatta senza contesto visivo — mancava un "cappello" che spiegasse cosa stesse succedendo.

**Fix**:
- Aggiunta chiave i18n `transactions.validate.issuesHeader` in 4 lingue (EN: "Validation errors were found", IT: "Sono stati identificati degli errori nei campi", FR/ES equivalenti).
- `TransactionFormModal`: `<p>` header bold + `<ul class="list-disc list-inside">` per bullet points.
- `TransactionBulkModal`: stessa struttura header + bullet list.

### Fix W15 — cashSign{Positive,Negative} phrasing più naturale

**Problema**: "L'importo deve essere negativo per Acquisto" era poco leggibile. Meglio: "Acquisto richiede un importo negativo".

**Fix**: aggiornate le chiavi `cashSignPositive` e `cashSignNegative` in 4 lingue, ora con `{type}` come soggetto della frase (es. "{type} requires a negative cash amount").

---

## ✅ Final-check aggiornato (post-walkthrough #4)

- [x] `TXValidationIssue` schema ha `code`, `params`, `field` opzionali
- [x] ~18 `ValueError` → `PydanticCustomError` in `TXCreateItem.validate_transaction_rules`
- [x] `BalanceValidationError` include `code`+`params` (solo ID, niente nomi)
- [x] Tutti i `TXValidationIssue(...)` in `validate_batch` includono `code`+`params`
- [x] `_validate_linked_pair` restituisce `(error, code, params)` (non solo stringa)
- [x] Frontend types rigenerati (`./dev.py api sync`)
- [x] `resolveIssueMessage` helper — risolve ID→nomi, `type`→traduzione, formatta con `currencyFormat.ts`
- [x] `extractValidationIssues` estrae `type`→`code` e `ctx`→`params` dai Pydantic 422
- [x] `TransactionFormModal` — header + bulleted issue list
- [x] `TransactionBulkModal` — header + bulleted issue list
- [x] `TXUpdateItem.id`: `gt=0` → model_validator con codice `idRequired`
- [x] `resolveValidationMessage`: auto-translate `{type}` param via `transactions.types.*`
- [x] 25 chiavi `transactions.errors.*` + 10 `transactions.pydantic.*` + 14 `transactions.fields.*` + 4 `transactions.fieldErrors.*` + 1 `transactions.validate.issuesHeader` in EN/IT/FR/ES
- [x] Field-name resolution: `loc` → `extractFieldName` → `translateFieldName`
- [x] Field-specific overrides: `broker_id:greater_than`, `id:greater_than`, ecc.
- [x] `model_validator` raccoglie tutti gli errori (`multipleBusinessRuleErrors` wrapper)
- [x] BulkModal: griglia vuota + auto-open FormModal su `+ Add`
- [x] BulkModal: colonne redistribuite (Cash 295px)
- [x] CompactCashCell: `.amount-input min-width: 5rem`, `.currency-wrap min-width: 7rem`
- [x] FormModal: SingleDatePicker con `inputStyle={true}`
- [x] Backend tests passano (65/65)
- [x] i18n audit clean (1083/1083)
- [ ] Walkthrough #5 utente

---

## 🔁 Walkthrough #5 — feedback utente (2026-04-29)

### Findings

8 issue identificati, classificati per area.

#### UX/i18n (quick fix)

| # | Issue | Dettaglio |
|---|-------|-----------|
| W16 | Label "Cassa" → "Importo" in IT | `transactions.table.cash` = "Cassa" nella tabella, ma il campo errori usa correttamente "Importo" (`transactions.fields.cash`). L'header della colonna DataTable e del form dovrebbe diventare "Importo" per coerenza. |
| W17 | "Commit annullato" → "Salvataggio annullato" nel bulk | `transactions.bulk.rolledBackTitle` = "Commit annullato" — gergo tecnico, l'utente non sa cos'è un "commit". Uniformare a "Salvataggio annullato" (già usato nel FormModal). |
| W18 | Validate button nel BulkModal diverso dal FormModal | Il FormModal ha il validate scheduler auto; il BulkModal ha un bottone `⚡ Validate now` nel footer. UX incoerente — l'utente si aspetta lo stesso pattern. |

#### Data / Mock (quick fix)

| # | Issue | Dettaglio |
|---|-------|-----------|
| W19 | Bitcoin va in negativo su Coinbase | Root cause: BUY 0.05 BTC (riga 1012 mock data), poi TRANSFER OUT −0.1 BTC (riga 1139). Saldo: 0.05−0.1 = −0.05. Fix: aumentare il BUY a 0.15 BTC (saldo post-transfer: +0.05 BTC). |

#### Feature request (minor, rapido)

| # | Issue | Dettaglio |
|---|-------|-----------|
| W20 | Currency auto-align: "back to asset currency" button | Quando l'utente seleziona un asset, la currency del campo Cash si auto-allinea — feature apprezzata. Ma se la cambia manualmente, vorrebbe un mini-pulsante per tornare alla valuta dell'asset (come nell'FX conversion wizard). |

#### Architettura (major — richiede design)

| # | Issue | Root cause | Impatto |
|---|-------|------------|---------|
| W21 | Validate endpoint: riga 1 (balance violation) mancante dalla response | **Pydantic 422 pre-emption**: il body `TXValidateBatch.creates` è `List[TXCreateItem]`. Se QUALSIASI riga fallisce la schema-validation Pydantic (es. riga 2 con `cashSignNegative`), FastAPI restituisce un 422 raw PRIMA che l'endpoint `validate_transactions` venga invocato. Il `service.validate_batch()` (che contiene la balance walk per riga 1) non gira mai. Risultato: errori di balance (service-layer) invisibili ogni volta che coesistono con errori di schema (Pydantic). |
| W22 | Bulk create (`POST /bulk`): stessi errori raw, non strutturati | **Stessa root cause**: il body è `List[TXCreateItem]`. Pydantic 422 → raw English ("BUY requires cash.amount < 0") nel banner di rollback. Il bulk commit non passa dalla `validate_batch`, quindi nessun issue strutturato con code/params. |
| W23 | Bulk rollback banner: errori non tradotti | Corollario di W22: il banner dell'errore in commit mostra il `msg` raw di Pydantic, non il messaggio tradotto. Il frontend `extractValidationIssues` lo cattura ma il `resolveIssueMessage` poi vede il `code` = `cashSignNegative` ma senza il tradotto `type`. Per i balance errors il problema è peggiore: non arrivano mai al frontend nel flusso commit. |

---

### Analisi architetturale W21/W22/W23

#### Problema fondamentale

Il flusso attuale ha uno split nel percorso di validazione:

```
                              ┌─ Pydantic 422 (schema errors)
POST /validate ─► FastAPI ─►──┤                                    ← gli errori schema
  body: TXValidateBatch       └─ validate_batch() (service errors)    e service NON coesistono
                                                                      nella stessa response
```

FastAPI deserializza `TXValidateBatch.creates: List[TXCreateItem]` PRIMA di eseguire l'handler. Se riga N fallisce il `model_validator` di `TXCreateItem`, Pydantic ritorna 422 per TUTTE le righe fallite — ma `validate_batch` non gira mai e le righe valide non vengono controllate per balance.

**Idem per `POST /bulk`**: body è `List[TXCreateItem]` → Pydantic 422 pre-empts il service layer.

#### Soluzione proposta: "Lenient Validation Gateway"

**Idea**: disaccoppiare schema-validation da HTTP parsing, così che il service layer possa raccogliere TUTTI gli errori (schema + business + balance) in un unico pass.

**Approccio A — Raw JSON + per-row validation nel service** (preferito):

1. Cambiare `POST /validate` per accettare un body `dict` (o un modello con campi `List[dict]`):
   ```python
   class TXValidateBatchRaw(BaseModel):
       creates: List[dict] = Field(default_factory=list, max_length=500)
       updates: List[dict] = Field(default_factory=list, max_length=500)
       deletes: List[int] = Field(default_factory=list, max_length=500)
   ```

2. Nel `validate_batch`, fare try/except per-row:
   ```python
   parsed_creates = []
   for idx, raw in enumerate(raw_creates):
       try:
           item = TXCreateItem.model_validate(raw)
           parsed_creates.append(item)
       except ValidationError as e:
           for err in e.errors():
               issues.append(TXValidationIssue(
                   operation="create", index=idx,
                   error=err["msg"],
                   code=err["type"],
                   params=err.get("ctx"),
                   field=".".join(str(p) for p in err["loc"]),
               ))
   ```

3. Continuare con i `parsed_creates` validi per la balance validation.

4. **Per il bulk commit** (`POST /bulk`, `PATCH /bulk`): fare internamente la stessa "lenient parse" e se ci sono errori schema, restituire `rolled_back=True` con issues strutturate SENZA mai provare l'insert. Se tutti passano, procedere col flusso attuale.

**Vantaggi**:
- Un solo punto di validazione per schema E business E balance
- Frontend riceve SEMPRE risposta strutturata (mai 422 raw)
- Le balance violations e gli schema errors coesistono nella stessa risposta
- Il bulk commit diventa "validate-first, then commit" senza duplicare codice
- Il frontend `extractValidationIssues` non serve più per il caso Pydantic 422 (diventa solo fallback safety net)

**Approccio B — Exception handler middleware** (scartato):
Intercettare `RequestValidationError` a livello FastAPI, parsare gli errori Pydantic e trasformarli in `TXValidateResponse`. Fragile: non distingue le rotte, non può fare balance validation sulle righe valide.

**Approccio C — Validate-then-commit** (complementare ad A):
Il bulk commit chiama internamente `validate_batch` prima di procedere. Se `would_rollback=True`, restituisce gli issues strutturati senza tentare inserimenti. Se `would_rollback=False`, procede col flusso create/update.

**Raccomandazione**: **A + C combinati**.
- A per il validate endpoint (raccoglie tutto in un pass)
- C per il bulk commit (riusa `validate_batch` come pre-check: zero duplicazione di logica)

#### Effort stimato

| Task | Stima |
|------|-------|
| `TXValidateBatchRaw` + lenient per-row parse | 1 h |
| `validate_batch` refactor per accettare mix `parsed` + `issues` | 45 min |
| Bulk create/update → validate-first pattern | 45 min |
| Frontend: rimuovere 422 fallback special-cases (cleanup) | 30 min |
| Tests + walkthrough | 1 h |
| **Totale** | ~4 h |

---

### Quick fixes (W16–W20) — implementabili subito

| # | File(s) | Fix |
|---|---------|-----|
| W16 | `it.json` (+ FR/ES check) | `transactions.table.cash` → "Importo" |
| W17 | `it.json` (+ FR/ES check) | `transactions.bulk.rolledBackTitle` → "Salvataggio annullato", `.rolledBack` → "Salvataggio annullato — nessuna modifica salvata." |
| W18 | BulkModal template | Allineare bottone validate al pattern FormModal (inline nel toolbar, stessa label/icona) |
| W19 | `populate_mock_data.py` | BUY BTC quantity 0.05 → 0.15 |
| W20 | `CompactCashCell.svelte` | Mini-pulsante "↩ reset currency" quando la valuta corrente ≠ asset currency (da implementare in un pass successivo — richiede props `assetCurrency` e UI del pulsante) |

---

### Proposta di procedura

**Fase 1 (quick, ~30 min)**: W16 + W17 + W19 — label IT, bulk banner copy, mock data BTC fix.

**Fase 2 (medium, ~1 h)**: W18 + W20 — allineare validate button, currency reset button.

**Fase 3 (major, ~4 h)**: W21 + W22 + W23 — Lenient Validation Gateway (approccio A + C). Questo è il refactoring strutturale che risolve il problema fondamentale di coesistenza errori schema/business.

**Decisione utente richiesta**: procedere con Fase 1 subito, e quanto delle Fase 2/3 fare ora vs. in un piano separato?

---

## 🏗️ Decisione architetturale: Unified Batch Pipeline (2026-04-29)

### Decisione presa dall'utente

- ❌ **Approccio A** (`TXValidateBatchRaw` con `List[dict]`) — **scartato**. I tipi `TXCreateItem`/`TXUpdateItem` esistono già e sono auto-validanti. Non serve un tipo raw.
- ❌ **Thin wrappers** sui vecchi 3 endpoint — **scartato**. Rompere il frontend ora, no backward compat.
- ❌ **Middleware** (Approccio B) — **scartato**. Fragile, non distingue rotte.
- ✅ **Approccio C evoluto**: **2 soli endpoint**, stessa struttura body, stessa pipeline interna.

### Design finale: 2 endpoint

| Endpoint | Body | Semantica |
|----------|------|-----------|
| `POST /api/v1/transactions/validate` | `TXMixedBatch` | Dry-run: always rollback |
| `POST /api/v1/transactions/commit` | `TXMixedBatch` | Commit if no issues, rollback otherwise |

```python
class TXMixedBatch(BaseModel):
    """Unified batch: creates + updates + deletes in one request."""
    model_config = ConfigDict(extra="forbid")
    creates: List[dict] = Field(default_factory=list, max_length=500)
    updates: List[dict] = Field(default_factory=list, max_length=500)
    deletes: List[int] = Field(default_factory=list, max_length=500)
```

**Perché `List[dict]` nel body HTTP ma `TXCreateItem` internamente?**

Il body HTTP DEVE essere `List[dict]` (non `List[TXCreateItem]`) perché FastAPI deserializza il body _prima_ dell'handler. Se una riga ha un errore schema → Pydantic 422 → handler non gira → balance violations invisibili.

Con `List[dict]`, FastAPI non valida le singole righe. Il service fa `TXCreateItem.model_validate(raw)` per-row in try/except → raccoglie errori schema + prosegue con righe valide per balance check.

I tipi `TXCreateItem`/`TXUpdateItem` restano INVARIATI — li usiamo internamente per la validazione, non come body HTTP.

**OpenAPI**: `openapi_extra` nel decoratore per documentare lo schema atteso (es. `requestBody.content.application/json.schema`).

### Pipeline interna

```python
async def _execute_batch(batch: TXMixedBatch, user_id: int, commit: bool, session) -> TXBatchResponse:
    issues = []
    
    # 1. Lenient per-row parse
    parsed_creates, create_issues = _parse_lenient(batch.creates, TXCreateItem, "create")
    parsed_updates, update_issues = _parse_lenient(batch.updates, TXUpdateItem, "update")
    issues.extend(create_issues + update_issues)
    
    # 2. Service-layer: access check, apply deletes→updates→creates, balance walk
    #    Uses ONLY the successfully-parsed rows.
    #    Collects service issues (txNotFound, accessDenied, balance violations, pair errors).
    service_result = await service.validate_and_apply(
        parsed_creates, parsed_updates, batch.deletes, user_id
    )
    issues.extend(service_result.issues)
    
    # 3. Commit or rollback
    if issues:
        await session.rollback()
        return TXBatchResponse(committed=False, issues=issues)
    elif not commit:
        await session.rollback()
        return TXBatchResponse(committed=False, issues=[])  # dry-run OK
    else:
        await session.commit()
        return TXBatchResponse(committed=True, issues=[], results=service_result.results)
```

### Endpoint vecchi → rimossi

| Prima | Dopo |
|-------|------|
| `POST /bulk` (create) | ❌ rimosso → usa `/commit` con `creates` |
| `PATCH /bulk` (update) | ❌ rimosso → usa `/commit` con `updates` |
| `DELETE /bulk` (delete) | ❌ rimosso → usa `/commit` con `deletes` |
| `POST /validate` | ✅ refactored → usa `_execute_batch(commit=False)` |
| — | ✅ nuovo: `POST /commit` → usa `_execute_batch(commit=True)` |

### Vantaggi

1. **Zero duplicazione** — 1 pipeline per tutto
2. **Schema + business + balance errors coesistono** nella stessa response
3. **Creates + updates + deletes nella stessa request** → operazioni miste
4. **Per-day balance invariant** — ordine `delete→update→create`, balance walk per data crescente
5. **Frontend semplificato** — 1 endpoint commit, 1 preview
6. **Futuro**: edit+create simultaneo, delete nello stesso flusso

### Helper `_parse_lenient`

```python
def _parse_lenient(
    raw_list: List[dict], model_class: type, operation: str
) -> Tuple[List, List[TXValidationIssue]]:
    parsed, issues = [], []
    for idx, raw in enumerate(raw_list):
        try:
            parsed.append((idx, model_class.model_validate(raw)))
        except ValidationError as e:
            for err in e.errors():
                issues.append(TXValidationIssue(
                    operation=operation, index=idx,
                    error=err["msg"], code=err["type"],
                    params=err.get("ctx"),
                    field=_loc_to_field(err.get("loc", [])),
                ))
    return parsed, issues
```

`parsed` è `List[Tuple[int, TXCreateItem]]` — preserva l'indice originale per mappare issues → riga nel frontend.

### Response schema

```python
class TXBatchResponse(BaseModel):
    committed: bool  # True = salvato, False = rollback (dry-run o errori)
    issues: List[TXValidationIssue] = []
    results: Optional[List[TXBatchResultItem]] = None  # solo se committed=True
```

Sostituisce `TXBulkCreateResponse`, `TXBulkUpdateResponse`, `TXValidateResponse` → un solo tipo di risposta.

### Steps di implementazione

| # | Task | Effort |
|---|------|--------|
| 1 | Schema: `TXMixedBatch` + `TXBatchResponse` + `TXBatchResultItem` | 30 min |
| 2 | Service: `_parse_lenient` + refactor `validate_batch` → `execute_batch` | 1.5 h |
| 3 | Router: `POST /validate` + `POST /commit` (con `openapi_extra`) | 30 min |
| 4 | Router: rimuovi `POST /bulk`, `PATCH /bulk`, `DELETE /bulk` | 15 min |
| 5 | `./dev.py api sync` → regen TypeScript client | 5 min |
| 6 | Frontend: BulkModal/FormModal → usa `/commit` e `/validate` con `TXMixedBatch` | 1 h |
| 7 | Frontend: cleanup `extractValidationIssues` 422 fallback (safety net only) | 15 min |
| 8 | Backend tests: aggiornare per nuovi endpoint | 45 min |
| 9 | Mock data: W19 BTC fix (0.05→0.15) | 5 min |
| 10 | i18n: W16 (Cassa→Importo), W17 (Commit→Salvataggio) | 10 min |
| **Totale** | | **~5 h** |

### Nota: questo va in un piano separato

Questo refactoring è troppo grande per restare nel bugfix i18n. Creare:
`plan-phase07-transaction-Part5_UnifiedBatchPipeline.prompt.md`

Il piano corrente (Bugfix-2 i18n) si chiude con i quick fixes W16/W17/W19 e rimanda al nuovo piano per W21–W23.

**→ Piano successivo**: [`plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md`](./plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md)

