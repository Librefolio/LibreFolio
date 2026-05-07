# Plan B — Bugfix Round 1 (Test Walk T1-T8)

**Date**: 2026-05-06
**Status**: ✅ COMPLETATO (test automatici + verifica manuale pendente)
**Parent**: [`plan-phase07-transaction-Part4_Round6_PlanB_DeletePickerAccess.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanB_DeletePickerAccess.prompt.md) (Fase 1 — Broker Access Visibility)

---

## Riepilogo

7 bug + 1 enhancement emersi dal test walk manuale della Fase 1 (Broker Access Visibility).
Tutti i bug risolti. Test automatici E2E implementati e verdi (5/5 suite).

---

## Test Automatici E2E — Status

Comando: `./dev.py test front-transaction all`

| Suite | File | Test | Status |
|-------|------|------|--------|
| Transaction Modals | `transactions-modals.spec.ts` | 14 test (CRUD, paired, i18n, sign-flip) | ✅ |
| TransactionsTable | `transactions-table.spec.ts` | 23 test (read-view, pairs, pulse, TT9b hidden) | ✅ |
| TX Broker Access | `tx-broker-access.spec.ts` | 4 test (Bug 1, 3, 13) | ✅ |
| TX Paired Edit | `tx-paired-edit.spec.ts` | 3 test (Bug 6, 7, 14) | ✅ |
| TX Tooltips | `tx-tooltips.spec.ts` | 2 test (Bug 8, hidden broker tooltip) | ✅ |

Backend: `pipenv run pytest test_transactions_api.py::test_get_transactions_partner_broker_id -v` → ✅

### Test notevoli aggiunti

- **TT9** (pulse): loop su più link icon fino a trovarne uno con partner visibile (evita falso negativo su Asym-d)
- **TT9b** (hidden partner): verifica che il link icon esista e abbia tooltip (`Hidden Admin Broker` + SVG lock), ma **non** produca pulse (partner non nel DOM)
- **Bug 6**: trova INTEREST via `img[alt]` (il tipo è un'icona PNG, non testo nella riga)
- **Bug 14**: verifica che il BulkModal si apra con la paired row, senza selezionare coppie con hidden broker
- **Tooltip hidden**: scorre tutte le righe `access-test` fino a trovare un tooltip contenente `Hidden Admin Broker`
- **Backend `partner_broker_id`**: crea 2 broker + 1 asset + 1 linked pair → verifica che GET /transactions ritorni `partner_broker_id` correttamente

### Lezioni apprese (pattern di test)

1. **La colonna "description" non è visibile nella tabella** → cercare per broker name + asset display name + tag, non per `[Asym-x]`
2. **Il tipo è un'icona PNG** → cercare via `img[alt]` con regex, non `textContent()`
3. **Le coppie con hidden broker non possono essere editate** → filtrare per broker editabili prima di selezionare
4. **`test.skip()` vietato per mock data mancante** → throw con messaggio verso `populate_mock_data.py`
5. **Tooltip.svelte usa `stopPropagation`** → il click non passa al capture handler della tabella, ma non è un bug: il TT9 funziona perché `{force: true}` bypassa l'actionability check

---

## Status Riepilogo (Final)

### ✅ Funzionanti (verificati da test automatici)
- **T-F1** — Form create: dropdown broker mostra solo broker OWNER/EDITOR (no VIEWER) ✅ `tx-broker-access`
- **T-F3** — Clone INTEREST: quantity resettata a 0 ✅ `tx-paired-edit`
- **T-F4** — Flat mode: paired adiacenti ✅ `tx-paired-edit`
- **Bug 1** — Broker dropdown filtrato ✅ `tx-broker-access`
- **Bug 3** — Matita edit nascosta per VIEWER ✅ `tx-broker-access`
- **Bug 6** — Clone INTEREST qty=0 ✅ `tx-paired-edit`
- **Bug 7** — Flat mode adjacency ✅ `tx-paired-edit`
- **Bug 8** — Tooltip favicon + SVG role icon ✅ `tx-tooltips`
- **Bug 9** — Asym-d dual view ✅ (coperto da Bug 13)
- **Bug 11** — BulkModal asset icona ✅ `transactions-modals`
- **Bug 12** — BulkModal descrizione troncata + tooltip ✅ `transactions-modals`
- **Bug 13** — Hidden broker lock + nome + "not accessible" ✅ `tx-broker-access`
- **Bug 14** — BulkModal edit paired UUID preservato ✅ `tx-paired-edit`
- **TT9b** — Hidden partner: icona + tooltip presenti, no pulse ✅ `transactions-table`

### 📝 TODO (non bloccanti)
- Test enum filter default (deselezionato) → richiede `data-testid` sul trigger button del filtro in `DataTableColumnFilter.svelte`
- **T-F2** — Edit paired TRANSFER → commit con update corretto (richiede test più complesso con modifica + commit + verifica payload)

---

## Bug 1 — Form broker dropdown mostra broker VIEWER

**Sintomo**: BrokerSearchSelect nel FormModal mostra DEGIRO, eToro, Recrowd (VIEWER) oltre a IB, Directa, Coinbase.
**Causa**: `TransactionFormModal.svelte:474` usa `getAllBrokers()` → ritorna tutti (OWNER/EDITOR/VIEWER/null).
**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`
**Fix**:
- Riga 176 (`emptyDraft()`): `getAllBrokers()` → `getEditableBrokers()`
- Riga 474 (computed `brokers`): `getAllBrokers()` → `getEditableBrokers()`
- Aggiungere import `getEditableBrokers` da `brokerStore`

---

## Bug 2 — Edit paired TRANSFER apre form singola (non dual)

**Sintomo**: Edit su Asym-a (IB↔Directa) apre il form come transazione singola, non dual Da:/A:.
**Causa**: `TransactionBulkModal:211` assegna `link_uuid = null` in edit-many mode (non è create). Poi `findPartnerDraft:378` esce subito con `undefined` (`if (!d.link_uuid) return undefined`), quindi il FormModal non riceve il partner iniettato e non attiva il dual form.
**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`
**Fix**: In `mergePairedRows()`, dopo aver identificato la coppia (from/to), generare un UUID condiviso e assegnarlo a entrambi i draft:
```ts
const sharedUuid = generateUUID();
fromDraft.link_uuid = sharedUuid;
toDraft.link_uuid = sharedUuid;
```
Così `findPartnerDraft` li trova tramite `link_uuid` e il FormModal riceve `injectedPartnerRow`, attivando il dual form.

---

## Bug 3 — Pulsante Edit (matita) visibile in view-only per tx non editabili

**Sintomo**: In view-only su Asym-c (VIEWER su DEGIRO), il bottone ✏ compare in cima. Cliccandolo si va in edit → banner errore "Accesso negato: ruolo EDITOR necessario per DEGIRO".
**Causa**: `TransactionFormModal:1158` condiziona il bottone a `isReadonly && onSwitchToEdit` senza verificare l'accesso broker.
**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`, `frontend/src/routes/(app)/transactions/+page.svelte`
**Fix**:
- Aggiungere prop `canEdit?: boolean` (default `true`) al FormModal
- Condizione bottone: `isReadonly && onSwitchToEdit && canEdit`
- In `+page.svelte:907`, calcolare `canEdit` dalla `formInitial` usando `canEditBroker(formInitial.broker_id)` per standalone, e `canEditPaired(formInitial.broker_id, partnerBrokerId)` per paired
- Se `canEdit = false`, non passare `onSwitchToEdit` (o passare `canEdit={false}`)

---

## Bug 4 — Backend: aggiungere `partner_broker_id` a TXReadItem

**Sintomo**: Tooltip paired mostra "?" per Hidden Admin Broker (partner inaccessibile). Form mostra "Seleziona Broker" vuoto nel lato "A:".
**Causa**: Il partner row non viene restituito dalla GET transactions (utente non ha accesso a quel broker), quindi il frontend non sa il broker_id del partner.
**File**: `backend/app/schemas/transactions.py`, `backend/app/services/transaction_service.py`
**Fix**:
- In `TXReadItem` (schemas/transactions.py:331): aggiungere `partner_broker_id: Optional[int] = None`
- In `transaction_service.py:query()`: dopo aver ottenuto i risultati, fare un batch lookup dei `related_transaction_id` per ottenere i `broker_id` dei partner:
  ```python
  partner_ids = {tx.related_transaction_id for tx in txs if tx.related_transaction_id}
  if partner_ids:
      stmt = select(Transaction.id, Transaction.broker_id).where(Transaction.id.in_(partner_ids))
      rows = await self.session.execute(stmt)
      partner_map = {r.id: r.broker_id for r in rows}
      for item in items:
          if item.related_transaction_id:
              item.partner_broker_id = partner_map.get(item.related_transaction_id)
  ```
- **Post-fix**: `./dev.py api sync` per rigenerare client TS

---

## Bug 5 — Frontend: usare `partner_broker_id` per tooltip e form

**Sintomo**: Vedi Bug 4.
**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`, `frontend/src/lib/components/transactions/TransactionFormModal.svelte`
**Fix tooltip** (TransactionsTable:449-452):
- Quando `partner` non trovato nel `partnerLookup` ma `d.tx.partner_broker_id` presente, usare `getBrokerInfo(d.tx.partner_broker_id)?.name ?? '?'` come `partnerBroker`
- Aggiungere nel tooltip l'icona ruolo del broker partner (es. `👑`/`✏️`/`👁`/`🔒`) via emoji fallback

**Fix form view-only** (TransactionFormModal):
- Quando il fetch del partner fallisce E `initialRow.partner_broker_id` è presente, mostrare nel lato "A:" il nome broker con icona lock e testo "non accessibile" al posto di "Seleziona Broker" vuoto
- Usare `getBrokerInfo(initialRow.partner_broker_id)` per il nome

---

## Bug 6 — Clone INTEREST copia quantity non-zero

**Sintomo**: Clone di una transazione INTEREST su Coinbase produce `quantity: "0.002000"` → backend rifiuta (`INTEREST requires quantity = 0`).
**Causa**: `handleCloneRow` (+page.svelte:707-711) copia tutti i campi verbatim, senza resettare i campi che per quel tipo devono avere valori forzati.
**File**: `frontend/src/routes/(app)/transactions/+page.svelte`
**Fix**: Dopo aver copiato la row, applicare le regole del tipo:
```ts
const rule = getTypeRule(row.type);
const clone = {...row, id: 0, date: today, related_transaction_id: null};
if (rule.quantityRule === 'zero') clone.quantity = '0';
// cash sign forzato se necessario
```

---

## Bug 7 — Flat mode perde ordinamento paired-adiacente

**Sintomo**: Filtrando per tag `access-test`, le paired si riordinano per ID e le frecce non si guardano più.
**Causa**: In flat mode (`isGrouped === false`), `displayRows` segue l'ordine di `mainRows` (backend: date DESC, id DESC). Ogni riga è indipendente, le paired non vengono raggruppate.
**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`
**Fix**: Aggiungere un campo `sortIndex: number` a `DisplayRow`. Algoritmo in flat mode:
1. Prendere `mainRows` ordinato per data DESC (come dal backend)
2. Iterare e assegnare `sortIndex` incrementale (0, 1, 2, ...)
3. Quando si incontra una riga paired il cui partner è ancora in `mainRows` e non ancora processato:
   - Assegnare `sortIndex = N` alla riga giver (qty < 0 per TRANSFER)
   - Assegnare `sortIndex = N + 0.5` al receiver (qty > 0)
   - Marcare entrambe come processate
4. In flat mode `displayRows`, ordinare per `sortIndex` ASC (date DESC + paired adiacenti con frecce che si guardano)
5. DataTable in flat mode non ha sort iniziale → mostra i dati nell'ordine di `displayRows` (riga 310-311: `if (!sortState) return filteredData` ✅ confermato)

---

## Enhancement — Tooltip paired: icona broker + ruolo

**Sintomo**: Tooltip della catena mostra solo `📥 Ricevuto da Interactive Brokers` senza icona broker né ruolo.
**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`
**Fix**: Nella `linkedPairTooltip()`, aggiungere:
- Emoji ruolo mapping: `OWNER→👑, EDITOR→✏️, VIEWER→👁, null→🔒`
- Includere il ruolo dell'utente sul broker partner: es. `📥 Ricevuto da Interactive Brokers 👑`
- Usare `getBrokerRole()` o fallback su `partner_broker_id`

---

## Ordine di esecuzione

1. **Bug 4** — backend `partner_broker_id` (serve per Bug 5)
2. `./dev.py api sync` — rigenerare client TS
3. **Bug 1** — form broker dropdown
4. **Bug 2** — paired edit dual form
5. **Bug 3** — matita edit nascosta per non-editabili
6. **Bug 5** — frontend tooltip + form con `partner_broker_id`
7. **Bug 6** — clone INTEREST quantity
8. **Bug 7** — sortIndex flat mode
9. **Enhancement** — tooltip broker + ruolo
10. Test walk di verifica

---

## Note tecniche

- Il batch-lookup backend per `partner_broker_id` è 1 query extra (SELECT id, broker_id WHERE id IN (...)) — trascurabile. Non espone dati sensibili (solo un integer ID che il frontend ha già da GET /brokers).
- Per il `sortIndex`, il DataTable mostra i dati nell'ordine fornito quando nessun sort header è attivo — confermato dal codice DataTable riga 310-311: `if (!sortState || !enableSorting) return filteredData`.

---

## Bug 8 — Tooltip link: manca icona broker partner

**Sintomo**: Il tooltip della catena paired mostra solo testo + emoji ruolo, ma non l'icona (favicon) del broker partner.
**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`, `frontend/src/lib/components/transactions/cells/TxLinksCell.svelte`
**Causa originale**: il tooltip era plaintext (`title=""`) → impossibile icone. Migrato a `<Tooltip html={...}>` (componente UI), ma mancava `$brokerStoreVersion` per la reattività → `getBrokerInfo(id)?.icon_url` era null alla prima valutazione.
**Fix applicato**:
1. `linkedPairTooltip()` ora genera HTML con `brokerLabelHtml()`: `<img>` favicon + `<strong>nome</strong>` + emoji ruolo
2. `TxLinksCell.svelte`: `text={linkTooltip}` → `html={linkTooltip}`
3. Importato `brokerStoreVersion` + aggiunto `void $brokerStoreVersion;` nella cella links per reattività
**Status**: ✅ RISOLTO

---

## Bug 9 — Asym-d (Hidden): view si apre come tx singola, non dual

**Sintomo**: La view di #37 (IB→Hidden) mostra form singola "👁 View transaction #37" invece di dual "📦 👁 Asset Transfer #37 ↔ #38".
**Causa**: `pairLayout` è `$derived` che chiama `getTypeRule(draft.type)` ma non traccia `$typesVersion`. Se i types non sono ancora caricati dal server, la FALLBACK_RULE ha `requiresPair: false` e `pairFormLayout: null`. Il `$derived` non si re-evalua quando i types arrivano perché `getTypeRule` legge da un modulo-level store non reattivo.
**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`
**Fix**: Aggiungere `void $typesVersion;` all'inizio del `$derived.by` di `pairLayout` (riga 511) per forzare re-evaluazione quando i types si caricano dal server.

---

## Bug 10 — Asym-c (VIEWER): lato "To" mostra "Select Broker" vuoto

**Sintomo**: Nella view di #34 (IB→DEGIRO, viewer), il lato "To" mostra il dropdown vuoto "Select Broker" perché DEGIRO non è in `getEditableBrokers()`.
**Causa**: Il `BrokerSearchSelect` per il lato "To" usa `brokersForTo` derivato da `brokersForSelect` che ora è `getEditableBrokers()` (Bug 1 fix). Ma in view mode il dropdown è disabilitato — dovrebbe comunque mostrare il nome del broker selezionato, anche se non editabile.
**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`
**Fix**: In view mode (isReadonly), per il lato "To" del dual form, mostrare il broker come testo statico (nome + icona) usando `getBrokerInfo(dualTo.broker_id)` anziché il dropdown `BrokerSearchSelect`. Il dropdown serve solo in edit mode.

---

## Bug 11 — BulkModal: asset senza icona

**Sintomo**: L'asset nella BulkModal mostra solo il nome senza l'icona del tipo.
**Causa**: `renderAssetHtml` usa `info?.icon_url` che per gli asset mock potrebbe essere null. Manca il fallback all'icona del tipo (come `asset-types/stock.png`).
**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`
**Fix**: In `renderAssetHtml`, quando `icon_url` è null, usare `getAssetTypeIconUrl(info?.asset_type)` come fallback.

---

## Bug 12 — BulkModal: descrizione lunga troncata senza tooltip

**Sintomo**: La colonna descrizione tronca testi lunghi con `truncate block` ma non mostra tooltip al passaggio del mouse. Primo fix usava `whitespace-normal break-words` → testo a capo → altera altezza riga (indesiderato).
**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`
**Fix applicato**: `truncate block` (singola riga, `...`) + `HtmlCell.tooltip` → usa `<Tooltip>` component (instant hover, positioned). Altezza riga fissa. Al passaggio mouse compare il tooltip completo.
**Status**: ✅ RISOLTO

---

## Bug 13 — Asym-d (Hidden): lato "To" mostra "—" senza nome broker né lock

**Sintomo**: Nella view di #37 (IB→Hidden), il lato "To" mostra solo `—` (trattino) senza il nome del broker hidden né l'icona lock. Data "To" mostrata nonostante partner inaccessibile.
**Causa root (Round 3)**: GET /brokers con LEFT JOIN restituisce broker #7 "Hidden Admin Broker" con `user_role: null`. Quindi `getBrokerInfo(7)` torna un oggetto truthy → il branch `{#if toInfo}` si attiva → mostra nome+icona del broker senza lock. Ma il broker ha `icon_url: null`, `portal_url: null` → nessuna icona visibile. E la condizione `!getBrokerInfo(dualTo.broker_id)` per nascondere la data era false (info esiste, solo role è null).
**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`
**Fix applicato (Round 3)**:
1. Branch readonly broker "To": ora controlla `getBrokerRole(dualTo.broker_id)` — se `role == null` mostra lock rosso + nome + "not accessible", se role truthy mostra icona+nome normali
2. Branch `inaccessiblePartnerBrokerId`: aggiunta icona broker se disponibile (`BrokerIcon` component), altrimenti Lock
3. Condizione data "To": basata su `toDateRole == null` (non su `!getBrokerInfo`)
4. Importato `getBrokerRole` nel FormModal
**Status**: ✅ RISOLTO (v3)

---

## Bug 14 — BulkModal edit paired: partner diventa "create" al salvataggio

**Sintomo**: Edit di Asym-b (BTC IB→Coinbase) in BulkModal → validate/commit produce `creates[{broker_id:0, ...}]` + `updates[{id:33, qty:-0.05}]` → errore "Please select a broker". Il receiver (partner) viene trattato come "new" anziché "edited".
**Causa**: `collectDualCreates()` nel FormModal genera **sempre un nuovo UUID** (`generateUUID()` riga 774). Quando il payload ritorna al BulkModal, `patchDualRowFromForm()` cerca il partner hidden con `d.link_uuid === linkUuid` (nuovo UUID) → non lo trova → crea un nuovo draft "new" senza `id` né `original`. Il vecchio partner hidden (con UUID originale) resta nel drafts array come orfano.
**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`, `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`
**Fix applicato**:
1. (FormModal) `collectDualCreates()`: riusa `draft.link_uuid` se già presente (edit mode), genera UUID solo per create
2. (BulkModal) `patchDualRowFromForm()`: cerca partner hidden anche tramite `visibleDraft._partnerId` (fallback difensivo su link_uuid mismatch)
3. (BulkModal) rimosso duplicato `const visibleDraft` (ora definito una volta sopra)
**Status**: ✅ RISOLTO

---

## Bug 8 update — Tooltip link: favicon + SVG ruolo

**Sintomo confermato (Round 2)**: `brokerLabelHtml()` usava `getBrokerInfo(id)?.icon_url` → null perché il store non aveva il campo. Emoji ruolo (👑/✏️/👁/🔒) non coerenti col resto del progetto.
**Fix applicato**:
1. `brokerLabelHtml()` ora usa `getBrokerIconUrlById(id, brokers)` (full fallback chain: icon_url → portal_url/favicon → plugin icon) con la prop `brokers` che ha i dati completi
2. Emoji ruolo sostituite con `getRoleSvgHtml(role)` — stessi SVG inline lucide usati nelle celle broker (Crown/Pencil/Eye/Lock)
3. Rimossa funzione `roleToEmoji()` (dead code)
**Status**: ✅ RISOLTO


---

## 🧪 Checklist Manuale di Verifica (Pre-avanzamento)

Login: `e2e_test_user` / `E2eTestPass123!` — porta 8001 (test mode)

### 1. Tabella principale (`/transactions`)

| # | Cosa verificare | Come |
|---|----------------|------|
| M1 | Le coppie paired sono adiacenti (⬇ sopra, ⬆ sotto) | Guardare le frecce nelle righe con 🔗 |
| M2 | Colonna tipo mostra icone PNG (non testo) | Ogni riga ha un'icona colorata, non "BUY"/"SELL" |
| M3 | Colonna tag mostra badge colorati | Cercare righe con `access-test` |
| M4 | Nessun banner errore rosso al caricamento | La pagina si carica pulita |

### 2. Tooltip linked pair (hover su 🔗)

| # | Cosa verificare | Come |
|---|----------------|------|
| M5 | Tooltip ha **favicon** del broker partner | Hover su 🔗 di una riga Asym-a (IB↔Directa) → deve mostrare img favicon |
| M6 | Tooltip ha **nome broker in grassetto** | `<strong>Directa</strong>` o `<strong>Interactive Brokers</strong>` |
| M7 | Tooltip ha **icona SVG ruolo** (non emoji) | Corona (OWNER), Matita (EDITOR), Occhio (VIEWER), Lucchetto (hidden) |
| M8 | Tooltip Asym-d mostra `Hidden Admin Broker` + 🔒 SVG | Hover su 🔗 della riga IB con tag access-test che ha partner hidden |

### 3. Form view-only (doppio-click su riga)

| # | Cosa verificare | Come |
|---|----------------|------|
| M9 | **Asym-a** (IB↔Directa): dual form con broker "To" = Directa | Doppio-click → "📦 👁 Asset Transfer" — lato To mostra Directa |
| M10 | **Asym-c** (DEGIRO, VIEWER): NO matita ✏ in alto | Doppio-click sulla riga DEGIRO → la matita edit non deve comparire |
| M11 | **Asym-d** (IB→Hidden): lato To mostra 🔒 + "Hidden Admin Broker" + messaggio "non accessibile" | Doppio-click → dual form — lato To ha lucchetto rosso, nome, NO data |
| M12 | **Asym-d**: la data del lato "To" è **nascosta** | Nel dual form, il campo data NON compare per il lato hidden |

### 4. Create & Clone

| # | Cosa verificare | Come |
|---|----------------|------|
| M13 | Il dropdown broker nel form create mostra solo OWNER/EDITOR | Click "+" → aprire dropdown broker → NON devono comparire DEGIRO/eToro/Recrowd |
| M14 | Clone INTEREST: quantity = 0 | Selezionare un INTEREST → Clone → nel form la quantity deve essere `0` |

### 5. Edit paired (BulkModal)

| # | Cosa verificare | Come |
|---|----------------|------|
| M15 | Selezionare coppia Asym-a (2 righe) → Edit → BulkModal + FormModal dual | La FormModal deve mostrare Da/A (dual), non form singola |
| M16 | BulkModal: icona asset visibile | Nella riga del BulkModal, l'asset ha la sua icona (PNG tipo o favicon) |
| M17 | BulkModal: descrizione lunga troncata con `...` | Se troppo lunga, hover mostra tooltip completo |

### 6. GoTo pulsazione

| # | Cosa verificare | Come |
|---|----------------|------|
| M18 | Click su 🔗 di una paired con partner visibile → la riga partner lampeggia blu | Provare su Asym-a o Asym-b |
| M19 | Click su 🔗 di Asym-d (hidden partner) → **nessun** lampeggio | Il partner non è nella tabella, niente pulse |

### 7. Filtri

| # | Cosa verificare | Come |
|---|----------------|------|
| M20 | Il filtro colonna "Type" parte con tutte le opzioni **deselezionate** (= nessun filtro attivo) | Aprire il filtro del tipo → nessuna checkbox selezionata |

---

**Quando tutti i punti M1–M20 sono ✅, il Bugfix Round 1 è chiuso e si può procedere.**

---
---

# Bugfix Round 2 — Completato

**Date**: 2026-05-06
**Status**: ✅ COMPLETATO (test automatici 5/5 + verifica manuale OK)
**Parent**: questo stesso file (Round 1)

---

## Panoramica

5 issue risolte: 2 bug, 1 enhancement, 2 test TODO.
Tutti i test E2E verdi (5/5 suite, 50+ test).

---

## Bug 15 — Edit paired: `openEditRowForm(next[0])` apriva il draft hidden

**Sintomo**: View di IB↔Directa → click ✏ → si apre in edit → broker "To" vuoto, data resetta a oggi.
**Causa root VERA**: `openEditRowForm(next[0])` nel BulkModal `$effect` apriva sempre il PRIMO elemento del drafts array. Ma dopo `mergePairedRows()`, se la riga passata all'edit era il *receiver* (qty > 0), veniva posizionata come `draftArr[0]` e poi marcata `_hidden = true`. Quindi `next[0]` era il draft hidden, non il giver visibile!
**Fix applicato (3 parti)**:
1. `openEditRowForm(next.find(d => !d._hidden) ?? next[0])` — apre sempre il primo draft VISIBILE
2. `formKey` counter nel BulkModal, incrementato ad ogni open, passato come prop `openKey` al FormModal
3. FormModal `$effect` dipende da `openKey` → re-init garantito anche senza toggle di `open`
**File**: `TransactionBulkModal.svelte`, `TransactionFormModal.svelte`
**Status**: ✅ RISOLTO

---

## Bug 16 — Label "Broker:" residua sopra box locked

**Sintomo**: Nel lato "To" del form per partner inaccessibile, la label "Broker:" era visibile sopra il box rosso locked.
**Fix**: Condizionata con `{#if inaccessiblePartnerBrokerId == null}` — la label si mostra solo nei branch broker normali.
**File**: `TransactionFormModal.svelte` (~riga 1418)
**Status**: ✅ RISOLTO

---

## Bug 16b — Icona ruolo mancante nel lato "To" readonly

**Sintomo**: Directa nel lato "To" readonly mostrava favicon + nome ma mancava l'icona SVG del ruolo (Crown/Pencil/Eye).
**Fix**: Aggiunto `<RoleIcon>` SVG dopo il nome nel branch `toInfo && toRole != null` del readonly "To".
**File**: `TransactionFormModal.svelte` (~riga 1441)
**Status**: ✅ RISOLTO

---

## Enhancement — Colonna "Description" nella tabella principale

**Implementazione**:
- Nuova colonna `description` dopo `id` in `TransactionsTable.svelte`
- `type: 'text'`, `filterable: true`, `urlKey: 'description'`
- Troncamento dinamico con `w-full truncate` (si adatta alla larghezza della colonna, non fisso a 180px)
- Tooltip via `HtmlCell.tooltip` per testi > 20 char
- i18n EN/IT/FR/ES per `transactions.table.description`
- `width: 180`, `hiddenByDefault: false`, `sortable: true`
**Status**: ✅ IMPLEMENTATO

---

## TODO-A — Test filtro enum default (TT23)

**Fix**: Aggiunto `data-testid="col-filter-trigger-{column.id}"` al bottone filtro in `DataTable.svelte`.
**Test**: `TT23` in `transactions-table.spec.ts` — clicca `col-filter-trigger-typeIcon`, verifica 0 checkbox checked.
**Status**: ✅ COMPLETATO

---

## TODO-B — Test edit paired commit payload

**Test**: Aggiunto in `tx-paired-edit.spec.ts` — seleziona coppia → Edit → BulkModal → FormModal → modifica description → commit → intercept POST → verifica `payload.updates` con `id > 0`.
**Status**: ✅ COMPLETATO

---

## Test Automatici E2E — Status Finale

Comando: `./dev.py test front-transaction all`

| Suite | File | Test | Status |
|-------|------|------|--------|
| Transaction Modals | `transactions-modals.spec.ts` | 14 test | ✅ |
| TransactionsTable | `transactions-table.spec.ts` | 24 test (+TT23) | ✅ |
| TX Broker Access | `tx-broker-access.spec.ts` | 4 test | ✅ |
| TX Paired Edit | `tx-paired-edit.spec.ts` | 4 test (+TODO-B) | ✅ |
| TX Tooltips | `tx-tooltips.spec.ts` | 2 test | ✅ |

**Totale**: 48+ test, **5/5 suite verdi** 🎉

---

## Checklist Manuale M1–M20 — Status

Tutti i punti M1–M20 dalla checklist Round 1 → ✅ verificati manualmente dall'utente.

**Bugfix Round 2 chiuso. Pronto per Fase 2 (DeleteModal + PickerModal).**
