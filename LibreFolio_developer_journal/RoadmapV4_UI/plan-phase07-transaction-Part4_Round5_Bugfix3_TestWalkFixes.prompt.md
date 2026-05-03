# Plan — Phase 07 · Part 4 · Round 5 · Bugfix 3 — Test Walk Fixes

**Data**: 2026-05-03
**Origine**: `libreFolio_testwalk_phase07_r5b2.md` (test walk 2026-05-02)
**Precedente**: `plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md`

---

## Classificazione Bug

### 🔴 CRITICAL (bloccanti funzionalità core)

| # | Test | Descrizione | Root Cause Ipotizzata |
|---|------|-------------|----------------------|
| C1 | T1.2/T2.1/T4.4 | **Doppio-click su riga bulk apre FormModal sbiancato** — la riga viene editata correttamente al salvataggio, ma il form parte vuoto invece che pre-popolato | BulkModal passa `editRow` ma FormModal non legge i dati iniziali dalla riga |
| C2 | T4.4 | **Edit coppia dalla main table: dati parziali** — apre solo metà della coppia, broker partner sbiancato, ammontare con segno raw | Edit singola riga linked non ricostruisce la coppia duale; manca fetch del partner |
| C3 | [inline] | **Delete riga paired new: elimina solo 1 metà** — rimane errore orfano per la riga partner, UI bloccata | `deleteRow` nel buffer non rimuove il partner `__pairKey` delle righe `new` |

### 🟠 HIGH (funzionalità degradata ma non bloccante)

| # | Test | Descrizione |
|---|------|-------------|
| H1 | T4.2 | **Bulk table: icone asset/broker assenti nelle celle readonly** — ok readonly text, ma mancano icone |
| H2 | T4.2 | **Qty in bulk table: mostra "-3" invece di rendering duale Da:/A:** — allineamento a destra, missing dual display |
| H3 | T4.2 | **Broker senza URL portale non mostra icona** — fallback chain (plugin icon → generic) non rispettata |
| H4 | T4.3 | **Auto-validate scatta con campi incompleti** — validate non dovrebbe partire finché tutti i campi obbligatori non sono popolati |
| H5 | T8.2 | **Campo asset opzionale non mostra "(opzionale)"** — label mancante per tipi dove asset non è required |
| H6 | T2.2 | **Tipo editabile per righe DB** — il vincolo di tipo readonly per DB rows va rivalutato (vedi analisi sotto) |

### 🟡 MEDIUM (polish UX)

| # | Test | Descrizione |
|---|------|-------------|
| M1 | T1.2 | **Banner validazione in bulk table: ancora banner top** — nella bulk dovrebbe essere inline come nel form |
| M2 | T1.2/M1 | **Banner errori/warning senza X di chiusura** — sia nel form che nella bulk, i banner non sono dismissabili |
| M3 | T5.1 | **Date Da/A disallineate** — "Da" e "A" hanno lunghezze diverse → date non allineate |
| M4 | T4.1 | **Colonne nascoste di default** — UUID collegamento, Creato, Aggiornato dovrebbero essere hidden di default |
| M5 | T4.1 | **Colonna "Override costo medio"** — allargare minWidth e spostare dopo "Evento Asset" |
| M6 | T14.1 | **Docs: icone mancanti** — tabella panoramica mostra 1 sola icona per tipi doppi; pagine tipo usano emoji invece dell'icona reale |
| M7 | T1.1 | **Bulk table toolbar on selection** — se si seleziona 1+ riga, mostrare DataTableToolbar con azioni riga |

### 🔵 LOW (nice-to-have / future)

| # | Test | Descrizione |
|---|------|-------------|
| L1 | T7.1 | **Delete modale: riepilogo tabellare** — mostrare dettagli delle transazioni da eliminare (singola: layout verticale; multipla: tabella con toggle per-riga per includere partner) |
| L2 | T7.2 | **Delete partner: toggle per-riga** — nella delete multipla, toggle inline a inizio riga per ogni transazione paired (come nella bulk table); nella delete singola, slider sotto il riepilogo |
| L3 | T7 nota | **Context menu su click destro** — menu azioni in-place per righe lunghe |
| L4 | T14 nota | **TODO Gallery**: screenshot per tipo transazione × lingua, da inserire nelle pagine docs |

---

## Analisi: Vincolo "tipo readonly per DB rows" (H6/T2.2)

**Domanda dell'utente**: ha senso impedire il cambio tipo per righe già persistite?

**Decisione finale**: **"Sign flip"** — permettere solo il cambio tra coppie di tipi con struttura campi identica (stessi campi obbligatori/opzionali). I tipi paired (composite) restano bloccati.

### Swap Groups

| Gruppo | Tipi | Logica |
|--------|------|--------|
| **Asset trade** | `BUY` ↔ `SELL` | Stessa struttura (asset+qty+price+broker), direzione opposta |
| **Cash flow** | `DEPOSIT` ↔ `WITHDRAWAL` | Solo cash+broker, direzione opposta |
| **Income** | `DIVIDEND` ↔ `INTEREST` | Entrambi income; backend valida coerenza campi (es. asset required per DIVIDEND) |
| **Cost** | `TAX` ↔ `FEE` | Entrambi costi; stessa struttura campi |
| **Singleton** | `ADJUSTMENT` | Nessun flip (unico nel suo genere) |
| **Paired 🔒** | `CASH_TRANSFER`, `ASSET_TRANSFER`, `FX_CONVERSION` | Bloccati — troppa complessità duale |

**Perché INTEREST→DIVIDEND è permesso senza guard frontend**: il backend valida la coerenza dei campi. Se l'utente flippa INTEREST→DIVIDEND senza aver compilato l'asset, la validate server-side darà errore. Nessun bisogno di duplicare la logica nel frontend.

**Implementazione**:
- UI: dropdown tipo filtrato su `swapGroup[currentType]` → mostra solo 1-2 alternative
- Al cambio tipo → ricalcolo segni (qty, amount) se necessario
- Effort stimato: ~30 min, zero rischio regressione
- **Sì, in questa iterazione** — è semplice e migliora molto la UX

---

## Design: Delete Modal (L1/L2)

### Singola standalone (es. BUY)
Layout verticale chiave-valore, nessun toggle partner.

```
┌──────────────────────────────────────────────────┐
│  🗑️  Elimina transazione                         │
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Tipo      │ 🟢 BUY                          ││
│  │ Data      │ 2025-03-15                       ││
│  │ Asset     │ 🏷️ VWCE.DE — Vanguard FTSE A.W. ││
│  │ Quantità  │ 10.000                           ││
│  │ Prezzo    │ 112.34 EUR                       ││
│  │ Broker    │ 🏦 Directa                       ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│            [Annulla]  [🗑️ Elimina]               │
└──────────────────────────────────────────────────┘
```

### Singola paired (es. CASH_TRANSFER)
Layout verticale duale (2 colonne Uscita/Entrata) + slider sotto il riepilogo.

```
┌────────────────────────────────────────────────────┐
│  🗑️  Elimina transazione collegata                  │
│                                                    │
│  Questa transazione fa parte di una coppia.        │
│                                                    │
│  ┌────────────────────────────────────────────────┐│
│  │        │ 🔴 Uscita          │ 🟢 Entrata      ││
│  │────────│────────────────────│──────────────────││
│  │ Data   │ 2025-03-15        │ 2025-03-15       ││
│  │ Broker │ 🏦 Directa        │ 🏦 Degiro        ││
│  │ Amount │ -1 000.00 EUR     │ +1 000.00 EUR    ││
│  └────────────────────────────────────────────────┘│
│                                                    │
│  ┌────── Cosa eliminare? ──────────────────────┐   │
│  │  ●━━━━━━━━━━━━━━━━━━━○                      │   │
│  │  Solo questa    Entrambe                     │   │
│  │                                              │   │
│  │  ⚠️ La transazione partner rimarrà orfana.    │   │
│  └──────────────────────────────────────────────┘   │
│                                                    │
│            [Annulla]  [🗑️ Elimina]                  │
└────────────────────────────────────────────────────┘
```

### Multipla — tabella con toggle per-riga (stile bulk table)
Toggle `[⇄]` inline a inizio riga per transazioni paired. Click → espande dettaglio partner.

```
┌───────────────────────────────────────────────────────────┐
│  🗑️  Elimina 3 transazioni                                │
│                                                           │
│  ┌───────────────────────────────────────────────────────┐│
│  │     │ Tipo   │ Data       │ Asset    │ Amount         ││
│  │─────│────────│────────────│──────────│────────────────││
│  │     │ 🟢 BUY │ 2025-03-15│ VWCE.DE  │ 1 123.00 EUR   ││
│  │     │ 🔴 SELL│ 2025-04-01│ IWDA.AS  │   550.00 EUR   ││
│  │ [⇄] │ 💸 C.T.│ 2025-04-10│ —        │ 1 000.00 EUR   ││
│  └───────────────────────────────────────────────────────┘│
│                                                           │
│  [⇄] = ha partner collegato                               │
│                                                           │
│            [Annulla]  [🗑️ Elimina tutto]                   │
└───────────────────────────────────────────────────────────┘
```

Toggle `[⇄]` espanso:

```
│  │ [⇄] │ 💸 C.T.│ 2025-04-10│ —        │ 1 000.00 EUR   ││
│  │      ├────────────────────────────────────────────────-││
│  │      │ 🔀 Partner: 💸 C.T. · Degiro · +1000 EUR       ││
│  │      │ [○━━●] Elimina anche partner                    ││
```

- Toggle attivo → header: `🗑️ Elimina 4 transazioni (3 + 1 partner)`
- Toggle disattivo → footer: `⚠️ 1 transazione partner rimarrà orfana`

### Riepilogo design

| Scenario | Layout | Toggle partner |
|----------|--------|----------------|
| Singola standalone | Verticale (chiave-valore) | N/A |
| Singola paired | Verticale duale (2 colonne) | Slider sotto riepilogo |
| Multipla | Tabella orizzontale (stile bulk) | Toggle `[⇄]` inline per-riga |

---

## Piano Implementativo

### Step 1 — C1: Fix doppio-click pre-popola FormModal
**File**: `TransactionBulkModal.svelte`, `TransactionFormModal.svelte`
**Azione**:
- Quando BulkModal apre FormModal per edit di una riga esistente (doppio-click o ✎), passare i dati della riga come `initialData`
- FormModal deve leggere `initialData` e popolare il draft all'apertura
- Per righe paired, ricostruire anche `partnerDraft` dalla coppia
- **Verifiche**: doppio-click su riga new → form pre-popolato; doppio-click su riga paired → form duale pre-popolato

### Step 2 — C2: Fix edit coppia da main table
**File**: `TransactionsPage.svelte` (o dove si gestisce il trigger edit dalla main table), `TransactionFormModal.svelte`
**Azione**:
- Quando edit di una riga linked dalla main table, fare fetch del partner via `link_uuid`
- Caricare entrambe le metà nel BulkModal
- Aprire FormModal in modalità duale con entrambi i lati pre-compilati
- Se annulla → non tornare a BulkModal vuoto

### Step 3 — C3: Fix delete paired new row
**File**: `TransactionBulkModal.svelte` (buffer management)
**Azione**:
- Quando si elimina una riga `new` paired, eliminare anche il partner (stessa `__pairKey`)
- Pulire anche eventuali errori/validazioni orfane associate al partner rimosso
- Test: crea coppia new → elimina una metà → entrambe devono sparire + nessun errore orfano

### Step 4 — H1/H2: Icone e rendering duale in bulk table
**File**: `TransactionBulkModal.svelte` (definizione colonne bulk grid)
**Azione**:
- **Icone asset/broker**: usare gli stessi helper di rendering della main table (con fallback chain)
- **Qty duale**: per righe paired, renderizzare come `Da: 10 / A: 10` (valori assoluti) analogamente a cash, non mostrare segno negativo raw
- **Allineamento qty**: text-align left come le altre colonne

### Step 5 — H3: Fallback icona broker
**File**: helper rendering broker icon (cercare dove si determina l'URL icona broker)
**Azione**:
- Se broker ha `portal_url` → favicon
- Se broker non ha `portal_url` ma ha plugin → icona plugin
- Se nessuno dei due → icona generica broker
- Verificare che helper esistenti siano usati ovunque (main table, bulk table, form)

### Step 6 — H4: Disabilitare auto-validate e Applica finché campi incompleti
**File**: `TransactionFormModal.svelte`
**Azione**:
- Calcolare `isComplete` basato sui campi obbligatori del tipo corrente (via `typeRules`)
- Disabilitare pulsante "Applica" se `!isComplete`
- Non lanciare validate automatica finché `!isComplete`
- Pulsante "Verifica ora" resta attivo (per forzare validate manuale e vedere cosa manca)

### Step 7 — H5: Label "(opzionale)" su campo asset
**File**: `TransactionFormModal.svelte`
**Azione**:
- Se `rule.assetField === 'optional'` → aggiungere ` (${$t('common.optional')})` alla label del campo asset
- Aggiungere chiave i18n `common.optional` in EN/IT/FR/ES: "optional"/"opzionale"/"optionnel"/"opcional"

### Step 8 — M1/M2: Banner validazione inline + dismissable
**File**: `TransactionBulkModal.svelte`, `TransactionFormModal.svelte`
**Azione**:
- **Bulk table**: sostituire banner success verde top con indicatore inline (come già fatto nel form)
- **Entrambi (form/bulk)**: aggiungere pulsante X per chiudere i banner errore/warning
- Pattern: `{#if showBanner} <div>... <button onclick={() => showBanner = false}>✕</button></div> {/if}`

### Step 9 — M3: Allineamento date Da/A
**File**: dove si renderizza la colonna data paired nella bulk/main table
**Azione**:
- Usare label a larghezza fissa: `<span class="inline-block w-8">Da:</span>` e `<span class="inline-block w-8">A:</span>`
- Le date così partono dalla stessa posizione indipendentemente dalla lunghezza della label

### Step 10 — M4/M5: Visibilità colonne default + ordine
**File**: definizione colonne transazioni (bulk e/o main table)
**Azione**:
- Nascondere di default: `link_uuid`, `created_at`, `updated_at`
- Allargare `minWidth` di "Override costo medio"
- Spostare "Override costo medio" dopo "Evento Asset" nell'ordine colonne

### Step 11 — Quick fixes già applicati
- ✅ `DataTable.svelte`: rimossa import `string` da zod (unused)
- ✅ `AssetSelect.svelte`: fix `as` cast → helper function `asAsset()`
- ✅ `TransactionFormModal.svelte`: rimosso `+` duplicato da `createLabel` asset

### Step 12 — M6: Fix icone documentazione mkdocs
**File**: `mkdocs_src/docs/*/financial-theory/transaction-types/`
**Azione**:
- Tabella panoramica: aggiungere entrambe le icone per tipi doppi (es. buy+sell)
- Pagine singole: sostituire emoji con immagine icona reale
- Referenziare le icone da `static/img/tx-types/` (o path corretto)

### Step 13 — L4: Annotare TODO gallery screenshots
**File**: `frontend/e2e/gallery.spec.ts` (inline commento) + `TODO_FUTURI.md`
**Azione**:
- Aggiungere TODO: "Screenshot per ogni tipo di transazione × ogni lingua (EN/IT/FR/ES), da inserire nelle pagine mkdocs delle singole transazioni"

---

## Priorità di Esecuzione

```
Step 1 (C1) → Step 2 (C2) → Step 3 (C3)     # Critical — sblocca test 6/15
    → Step 4 (H1/H2) → Step 5 (H3)            # High — visual polish paired
    → Step 6 (H4) → Step 7 (H5)               # High — form UX
    → Step 8 (M1/M2) → Step 9 (M3)            # Medium — banner + alignment
    → Step 10 (M4/M5)                          # Medium — column defaults
    → Step 11 (già fatto)                       # ✅ Done
    → Step 12 (M6) → Step 13 (L4)             # Low — docs
```

---

## Test Walk da ripetere dopo i fix

Dopo aver completato gli step, ri-testare:
- T1.2, T1.3, T2.1, T4.4 → doppio-click pre-popola
- T4.2 → icone + qty duale in bulk
- T4.3 → no auto-validate prematura
- T8.2 → label "(opzionale)"
- T6.1–T6.4 → edit/clone/view dalla main table (skippati in questa sessione)
- T15.1–T15.5 → regressioni generali (skippati)

