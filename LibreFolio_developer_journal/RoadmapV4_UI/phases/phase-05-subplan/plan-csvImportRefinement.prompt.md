# Plan: CSV Import Refinement — DataImportModal v2

**Dipendenze**: [`plan-fxDetailBugRound7-4.prompt.md`](plan-fxDetailBugRound7-4.prompt.md)

Redesign completo del flusso di import CSV per la pagina FX Detail. Il modale attuale (`DataImportModal`) usa un CSV a 4 colonne (`date;base;quote;base2quote`) che è ridondante ora che il Data Editor è "bloccato" su una coppia FX specifica nella pagina detail. Il redesign semplifica l'UX con un formato a 2 colonne con header semantico.

**Stato**: ✅ Completato (2026-03-18)

---

## Analisi dello stato attuale

### Componenti coinvolti

| Componente | Ruolo | File |
|------------|-------|------|
| `DataImportModal.svelte` | Modale di import con drag-drop + CsvEditor preview | `frontend/src/lib/components/ui/data-editor/` |
| `CsvEditor.svelte` | Editor CSV con numeri riga e validazione live | `frontend/src/lib/components/fx/` |
| `DataEditor.svelte` | Wrapper tabella con toolbar (Import CSV, Add Row) | `frontend/src/lib/components/ui/data-editor/` |
| `FxDataEditorSection.svelte` | FX-specific wrapper che connette DataEditor all'API | `frontend/src/lib/components/fx/` |

### Flusso attuale

1. User clicca "Import CSV" nel `DataEditor`
2. Si apre `DataImportModal` con drop zone + `CsvEditor`
3. CSV deve avere 4 colonne: `date;base;quote;base2quote`
4. Validazione per riga: formato data, valute ISO 4217, base≠quote, valore>0
5. Righe valide mergiate nella tabella `DataEditor` (upsert/append)

### Problemi

1. **Ridondanza**: Base e quote sono già fissati dalla pagina detail — l'utente deve ripeterli per ogni riga
2. **Direzione ambigua**: Il campo `base2quote` non è intuitivo — l'utente può confondersi se il CSV è nel verso giusto
3. **Nessun help**: Nessuna spiegazione del formato atteso, nessun link a documentazione
4. **Nessun adattamento invertito**: Se la pagina mostra USD→EUR (invertita), il CSV deve comunque avere valute canoniche
5. **4 colonne in CsvEditor**: Il CsvEditor è general-purpose ma hardcoded a 4 colonne

---

## Proposta di redesign (v2 — post feedback)

### Formato CSV: 2 colonne con header semantico

**Formato unico**: `date;VAL1>VAL2`

```csv
date;EUR>USD
2024-01-15;1.0823
2024-01-16;1.0845
2024-01-17;1.0901
```

- **Header obbligatorio**: la prima riga definisce la direzione del rate
- Il separatore nella colonna rate è `>` o `<`:
  - `EUR>USD` → il rate va letto come "1 EUR = X USD" (val1→val2)
  - `USD<EUR` → equivalente (val2→val1), il sistema lo normalizza
- **Il sistema scrive sempre `VAL1>VAL2`** quando genera l'header da codice
- **Solo le 2 valute della pagina** sono ammesse nell'header; altre = errore

### Concept: Layout modale (v2 — finale)

```
┌──────────────────────────────────────────────────────┐
│  Import CSV Data                              ? ✕    │
├──────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐│
│  │  📤 Drop .csv/.txt here, or click to browse      ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│         [🇦🇺 AUD ▾]    ->    [🇪🇺 EUR ▾]               │
│        (CurrencySearchSelect disabled, readonly)     │
│                                                      │
│  [⇄]  ℹ️ Rates interpreted as: 1 AUD = X EUR        │
│                                                      │
│  ┌─ Preview ───────────────────────────────────────┐ │
│  │ 0 valid rows   sep [;] · dec [.]/[,] · 000 [_] │ │
│  │ 1 H date;AUD>EUR                                │ │
│  │ 2 ✓ 2024-01-15;0.6045                           │ │
│  │ 3 ✓ 2024-01-16;0,6067                           │ │
│  │ 4 ✗ 2024-01-17;abc     Invalid rate             │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  2 valid rows              Cancel   Import (2)       │
└──────────────────────────────────────────────────────┘
```

**Note layout**:
- Drop zone **compatta** in cima (riga singola, non box alto)
- **CurrencySearchSelect in modalità disabled** (stile FxPairAddModal editMode) centrati con `↔`
- **`[⇄]` + InfoBanner sulla stessa riga** sotto i selettori valuta
- Status bar CsvEditor con **`<kbd>` box individuali** per ogni carattere speciale: sep `[;]` · decimale `[.]`/`[,]` · migliaia `[_]` (label i18n: `csvImport.sep`, `.decimal`, `.thousands`)
- CsvEditor preview sotto

**Parser numeri flessibile** (`parseNumber()`):
- `_` come separatore migliaia (stile JS/Rust): `1_000.50`, `1_000_000`
- Sia `.` che `,` come separatore decimale: `0.6045`, `0,6045`
- Se entrambi presenti, l'ultimo è il decimale: `1.000,50` → 1000.50, `1,000.50` → 1000.50

**Confirm discard**:
- Se l'utente ha modificato il CSV (oltre al solo header iniziale) e prova a chiudere (✕, Cancel, backdrop click), appare un `ConfirmModal` (warning amber)
- Dirty detection: confronta `csvValue` con `initialCsvValue` (testo header-only memorizzato all'apertura)
- Swap da solo non rende dirty (cambia solo l'header, che viene tracciato come parte dell'init)

**Architettura swap — single source of truth**:
- La direction bar è guidata SOLO da `ondirectiondetect` (emesso dal CsvEditor)
- `handleSwap()` modifica SOLO l'header nel testo CSV → CsvEditor re-parsa → emette `ondirectiondetect` → label si aggiornano
- Nessuna mutazione diretta di `directionFrom`/`directionTo` nel handler di swap
- Init `$effect` usa un guard `wasOpen` per non ri-eseguirsi quando `csvValue` cambia

### Decisioni progettuali

#### A. Header semantico `date;VAL1>VAL2`

- L'header è la chiave per determinare la direzione del rate
- Il sistema scrive sempre `>` quando genera l'header (non `<`)
- Il parser accetta sia `>` che `<` per robustezza:
  - `date;EUR>USD` → direction labels: EUR → USD, rate = "1 EUR = X USD"
  - `date;USD<EUR` → direction labels: EUR → USD (**normalizzato**, `<` inverte l'ordine di lettura), rate = "1 EUR = X USD"
  - Nota: `EUR>USD` e `USD<EUR` esprimono lo stesso significato semantico, e la direction bar mostra la stessa direzione normalizzata per entrambi. Solo lo swap `⇄` riscrive l'header (con `>`).
- Se l'header ha valute diverse da quelle della pagina → **errore rosso**:
  _"This page manages EUR/USD rates. The CSV header contains GBP/JPY which is not compatible. Please use EUR>USD or USD>EUR."_
- Se l'header è assente o non riconosciuto → **errore rosso**:
  _"Missing or invalid header. Expected format: date;EUR>USD"_

#### B. Direction bar e swap

- Mostra le 2 valute della pagina con flag emoji, **readonly** (non selettori, solo label)
- La direzione iniziale segue la pagina (se la pagina mostra USD→EUR, il modale mostra USD→EUR)
- I label seguono la **direzione logica dell'header**, cioè la valuta "from" a sinistra e "to" a destra:
  - Se l'header è `date;EUR>USD` → label: `EUR → USD`
  - Se l'header è `date;USD<EUR` → label: `EUR → USD` (**normalizzato**)
- **Pulsante swap `⇄`**: posizionato accanto all'InfoBanner, grande e prominente
  - Cliccando swap, il sistema **riscrive l'header** nel CsvEditor sempre con `>`:
    - Header era `date;EUR>USD` → diventa `date;USD>EUR`
    - Header era `date;USD<EUR` → diventa `date;EUR>USD` (swap della direzione logica, scritto con `>`)
  - I label della direction bar si aggiornano di conseguenza
  - Le righe dati restano identiche — il significato dei valori cambia perché la direzione è invertita
- L'utente vede immediatamente l'effetto dello swap nella preview

#### C. Auto-detect direzione dall'header del CSV

Quando l'utente trascina/incolla un file:
1. Il testo viene inserito **per intero** nel CsvEditor, sovrascrivendo tutto il contenuto
2. Il testo non viene modificato dal sistema finché l'utente non interagisce
3. Il sistema parsa l'header e determina la direzione logica (**normalizzata**):
   - `date;EUR>USD` → direction labels: `EUR → USD`
   - `date;USD<EUR` → **normalizzato** a `EUR → USD` (il `<` inverte l'ordine di lettura)
   - `date;GBP>JPY` → **errore**: valute non della pagina
   - Nessun header valido → **errore**: header mancante
4. I label della direction bar si **aggiornano automaticamente** per riflettere la direzione normalizzata

**Esempio concreto**: pagina mostra EUR→USD, utente importa file con header `date;USD<EUR`:
- Direction bar mostra: `EUR → USD` (**normalizzato** da `USD<EUR`)
- InfoBanner: "Rates interpreted as: 1 EUR = X USD"
- L'header nel CSV **non viene toccato** (resta `date;USD<EUR`)
- Se l'utente clicca swap `⇄`:
  - Header riscritta: `date;USD>EUR` (swap della direzione normalizzata, scritto con `>`)
  - Direction bar: `USD → EUR`
  - I valori delle righe restano identici ma ora significano USD→EUR

#### D. Drop behavior

- Il drop/paste **sovrascrive** tutto il contenuto esistente nel CsvEditor
- Il testo originale del file viene conservato intatto — nessuna modifica automatica
- Solo quando l'utente clicca swap `⇄` o l'edit manuale, il testo cambia

#### E. Help button `?`

- Icona `?` nell'header del modale, accanto al titolo
- Cliccando: collassa/espande una sezione help con formato atteso
- Link "Learn more" → pagina documentazione MkDocs (futuro)

---

## Stato implementazione

| Step | Descrizione | Stato | Note |
|------|-------------|-------|------|
| **1** | Refactor CsvEditor: formato 2 colonne con header semantico | ✅ | `date;VAL1>VAL2`, validazione 2-col, error handling header |
| **2** | Redesign DataImportModal v2 | ✅ | Drop zone in cima, direction bar, swap header, help |
| **3** | Auto-detect direzione dall'header del CSV | ✅ | Parse `>` e `<`, aggiornamento direction bar, errori valute |
| **4** | Inversione rate automatica al merge | ✅ | Se direzione modale ≠ canonico, 1/rate prima del save |
| **5** | Help tooltip con formato atteso | ✅ | Icona `?` con sezione collassabile, testo i18n |
| **6** | i18n per tutte le nuove stringhe | ✅ | EN, IT, FR, ES |
| **7** | SelectionBar nella pagina files/ | ✅ | Aggiungere dove manca (before ColumnVisibilityToggle) |
| **8** | Verifica build + test | ✅ | `./dev.py front check` + test manuale |

---

## Steps dettagliati

### Step 1 — Refactor CsvEditor: formato 2 colonne con header semantico

**File**: `frontend/src/lib/components/fx/CsvEditor.svelte`

Il CsvEditor va riscritto per il formato a 2 colonne con header semantico.

**Nuove props**:

```ts
interface Props {
    /** Current CSV text content (bindable) */
    value?: string;
    /** The two currencies of the page context (used for header validation) */
    allowedCurrencies: [string, string];
    /** Whether the editor is read-only */
    readonly?: boolean;
    /** Minimum height of the textarea */
    minHeight?: string;
    /** Placeholder text when textarea is empty */
    placeholder?: string;
    /** Called when valid parsed rows change */
    onvalidchange?: (validRows: ParsedRow[], errorCount: number, hasDuplicates: boolean) => void;
    /** Called when direction is detected from header */
    ondirectiondetect?: (from: string, to: string) => void;
    /** Called on every input (raw text) */
    oninput?: (text: string) => void;
}
```

**Nuova interfaccia `ParsedRow`** (semplificata):

```ts
export interface ParsedRow {
    date: string;
    value: number;
    lineNumber: number;
}
```

Nota: `base` e `quote` non servono più in `ParsedRow` — la direzione è determinata dall'header e gestita dal modale.

**Validazione header** (prima riga non vuota):

```ts
function parseHeader(line: string): {from: string; to: string} | {error: string} {
    const trimmed = line.trim().toLowerCase();
    // Match: date;VAL1>VAL2 or date;VAL1<VAL2
    const match = trimmed.match(/^date;([a-z]{3})([><])([a-z]{3})$/);
    if (!match) return {error: 'Invalid header format. Expected: date;EUR>USD'};

    const [, cur1, sep, cur2] = match;
    // Normalize: always emit the semantic from→to direction
    // date;EUR>USD → from=EUR, to=USD  (EUR → USD)
    // date;USD<EUR → from=EUR, to=USD  (normalized: < means read backwards)
    const from = (sep === '>' ? cur1 : cur2).toUpperCase();
    const to = (sep === '>' ? cur2 : cur1).toUpperCase();

    // Check currencies are in the allowed pair
    const allowed = new Set(allowedCurrencies);
    if (!allowed.has(from) || !allowed.has(to)) {
        return {error: `Only ${allowedCurrencies[0]} and ${allowedCurrencies[1]} are allowed on this page`};
    }
    if (from === to) return {error: 'Base and quote must differ'};

    return {from, to};
}
```

**Validazione righe dati** (dalla riga 2 in poi):

```ts
function parseDataRow(line: string): ParsedRow | {error: string} {
    const parts = line.trim().split(';');
    if (parts.length !== 2) return {error: `Expected 2 columns (date;rate), got ${parts.length}`};

    const [dateStr, valueStr] = parts.map(p => p.trim());

    // Validate date (YYYY-MM-DD)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return {error: `Invalid date: "${dateStr}"`};
    const dateObj = new Date(dateStr + 'T00:00:00Z');
    if (isNaN(dateObj.getTime())) return {error: `Invalid date: "${dateStr}"`};

    // Validate rate (positive number)
    const value = parseFloat(valueStr);
    if (isNaN(value) || value <= 0) return {error: `Invalid rate: "${valueStr}". Must be > 0`};

    return {date: dateStr, value, lineNumber: 0}; // lineNumber filled by caller
}
```

**Emissione direzione**: quando l'header viene parsato con successo, emette `ondirectiondetect(from, to)` per aggiornare la direction bar del modale.

**Public API aggiuntiva**:

```ts
/** Update only the header row (called by swap button) */
export function setHeader(from: string, to: string) {
    const lines = value.split('\n');
    lines[0] = `date;${from}>${to}`;
    value = lines.join('\n');
}
```

---

### Step 2 — Redesign DataImportModal v2

**File**: `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte`

**Layout** (top to bottom):
1. Header del modale con titolo + `?` help + `✕` close
2. Drop zone (drag & drop / file picker)
3. Direction bar (flag + label readonly × 2 + swap `⇄`)
4. InfoBanner con interpretazione direzione
5. CsvEditor preview
6. Footer con counter + Cancel/Import

**Nuove props**:

```ts
interface Props {
    open?: boolean;
    /** Display base currency (follows page direction, not canonical) */
    displayBase: string;
    /** Display quote currency (follows page direction) */
    displayQuote: string;
    onimport?: (rows: ParsedRow[], direction: {from: string; to: string}) => void;
    onclose?: () => void;
}
```

**Stato interno**:

```ts
let directionFrom = $state('');   // initialized from displayBase
let directionTo = $state('');     // initialized from displayQuote
let csvValue = $state('');
let headerValid = $state(false);
let headerError = $state<string | null>(null);
```

**Inizializzazione**: quando il modale si apre per la prima volta, pre-popola l'header. Usa un guard `wasOpen` per evitare la re-inizializzazione quando `csvValue` cambia:
```ts
let wasOpen = false;

$effect(() => {
    if (open && !wasOpen) {
        wasOpen = true;
        directionFrom = displayBase;
        directionTo = displayQuote;
        csvValue = `date;${displayBase}>${displayQuote}\n`;
    }
    if (!open && wasOpen) {
        wasOpen = false;
    }
});
```

**Swap handler** (single source of truth — only modifies header text):
```ts
function handleSwap() {
    // Read current direction, write the opposite
    const newFrom = directionTo || displayQuote;
    const newTo = directionFrom || displayBase;
    csvEditor?.setHeader(newFrom, newTo);
    // ondirectiondetect will fire from CsvEditor → updates directionFrom/directionTo
}
```

**Nota**: lo swap modifica SOLO la riga header via `setHeader()`. I label della direction bar si aggiornano tramite `ondirectiondetect` emesso dal CsvEditor dopo il re-parse. Le righe dati restano identiche — il significato dei valori cambia perché l'header ora indica la direzione opposta.

**Drop handler**:
```ts
function handleFileContent(file: File) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const text = e.target?.result as string;
        if (text) {
            // Overwrite entire editor content — no modifications to the file text
            csvValue = text;
        }
    };
    reader.readAsText(file);
}
```

Il CsvEditor parserà l'header e emetterà `ondirectiondetect(from, to)` → il modale aggiorna `directionFrom`/`directionTo`.

**Import handler**:
```ts
function handleConfirm() {
    if (validRows.length === 0) return;
    onimport?.(validRows, {from: directionFrom, to: directionTo});
    handleClose();
}
```

La direzione viene passata al parent insieme alle righe, cosicché `DataEditor` / `FxDataEditorSection` possano gestire l'eventuale inversione.

---

### Step 3 — Auto-detect direzione dall'header del CSV

**File**: Integrato in Step 1 (CsvEditor) e Step 2 (DataImportModal)

Flusso completo:

1. **User drops file** → testo inserito intero nel CsvEditor
2. **CsvEditor** parsa la prima riga non vuota come header
3. **Se header valido** (es. `date;EUR>USD`):
   - Emette `ondirectiondetect('EUR', 'USD')`
   - Modale aggiorna direction bar → mostra `EUR → USD`
   - Righe dati validate normalmente
4. **Se header con `<`** (es. `date;USD<EUR`):
   - La direzione viene **normalizzata**: `USD<EUR` → `EUR → USD` (il `<` inverte l'ordine di lettura)
   - Emette `ondirectiondetect('EUR', 'USD')`
   - Modale aggiorna direction bar → mostra `EUR → USD`
   - L'header nel CsvEditor **non viene toccato** (resta `date;USD<EUR`)
   - Nessun errore — il parser capisce `<` come semanticamente equivalente
5. **Se header ha valute della pagina ma ordine diverso** (es. pagina mostra EUR→USD, header `date;USD>EUR`):
   - Emette `ondirectiondetect('USD', 'EUR')`
   - Modale aggiorna direction bar → mostra `USD → EUR`
   - Nessun errore — l'utente sceglie consapevolmente la direzione
6. **Se header ha valute NON della pagina** (es. `date;GBP>JPY`):
   - Header marcato come errore rosso (✗) nel CsvEditor
   - Errore: _"This page manages EUR/USD. Only EUR and USD are allowed in the header."_
   - Tutte le righe dati NON vengono validate (contano come errore globale)
   - Import button disabilitato
7. **Se header mancante o malformato** (es. `date;rate`, `pippo`, riga vuota):
   - Header marcato come errore rosso
   - Errore: _"Missing or invalid header. Expected format: date;EUR>USD"_
   - Import disabilitato

**Esempio swap dopo `<`**: utente importa file con `date;USD<EUR`
- Direction bar mostra: `EUR → USD` (**normalizzato** da `USD<EUR`)
- L'utente clicca swap `⇄`
- Il sistema **riscrive l'header con `>`**: `date;USD>EUR` (swap della direzione normalizzata)
- Direction bar diventa: `USD → EUR`
- I rate nelle righe dati restano identici ma ora significano USD→EUR

---

### Step 4 — Inversione rate automatica al merge

**File**: `FxDataEditorSection.svelte` e/o `DataEditor.svelte`

Quando `DataImportModal` chiama `onimport(rows, {from, to})`:

1. `DataEditor` riceve le righe + la direzione
2. Passa tutto a `FxDataEditorSection` via callback
3. `FxDataEditorSection` confronta la direzione dell'import con la direzione corrente dell'editor:
   - Se `from === displayBase && to === displayQuote` → nessuna inversione, i rate sono già nella direzione corretta della pagina
   - Se `from === displayQuote && to === displayBase` → invertire i rate `1/value` prima del merge

**Nota importante**: `FxDataEditorSection.handleSave()` già normalizza verso il canonico al momento del save API (righe 172-183 attuali). L'inversione nell'import deve portare i rate nella direzione della PAGINA (display), non del canonico. Il save gestirà poi la normalizzazione verso il canonico.

---

### Step 5 — Help tooltip con formato atteso

**File**: `DataImportModal.svelte`

Icona `?` nell'header del modale → sezione collassabile:

```svelte
{#if showHelp}
    <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800
                rounded-lg px-4 py-3 text-sm text-blue-700 dark:text-blue-300 space-y-2">
        <p class="font-semibold">{$t('csvImport.helpTitle')}</p>
        <p>{$t('csvImport.helpFormat')}</p>
        <pre class="bg-white/50 dark:bg-slate-800/50 rounded p-2 text-xs font-mono">
date;EUR>USD
2024-01-15;1.0823
2024-01-16;1.0845</pre>
        <ul class="list-disc list-inside space-y-1 text-xs">
            <li>{$t('csvImport.helpDateFormat')}</li>
            <li>{$t('csvImport.helpRatePositive')}</li>
            <li>{$t('csvImport.helpSemicolon')}</li>
            <li>{$t('csvImport.helpDirection')}</li>
        </ul>
    </div>
{/if}
```

---

### Step 6 — i18n per tutte le nuove stringhe

Chiavi i18n aggiunte (4 lingue EN/IT/FR/ES):

```
csvImport.title               "Import CSV Data"
csvImport.direction           "Direction"
csvImport.ratesInterpretedAs  "Rates interpreted as: 1 {from} = X {to}"
csvImport.swapDirection       "Swap direction"
csvImport.dropFile            "Drop a .csv or .txt file here, or click to browse"
csvImport.dropReplace         "Drop another file to replace"
csvImport.noValidRows         "No valid rows found"
csvImport.validRows           "{count} valid row(s)"
csvImport.import              "Import ({count})"
csvImport.headerMissing       "Missing or invalid header. Expected format: date;{from}>{to}"
csvImport.headerWrongPair     "This page manages {pair}. Only {cur1} and {cur2} are allowed."
csvImport.helpTitle           "CSV Import Guide"
csvImport.helpFormat          "Use 2-column format with a header indicating direction:"
csvImport.helpDateFormat      "Dates must use YYYY-MM-DD format"
csvImport.helpRatePositive    "Rates must be positive numbers"
csvImport.helpSemicolon       "Use semicolon (;) as column separator"
csvImport.helpDecimals        "Both . and , are accepted as decimal separators. Use _ as optional thousands separator (e.g. 1_000.50)"
csvImport.helpDirection       "Use the ⇄ button or header to set rate direction"
csvImport.sep                 "sep"
csvImport.decimal             "decimal"
csvImport.thousands           "thousands"
csvImport.discardTitle        "Discard import?"
csvImport.discardMessage      "You have edited CSV data. Are you sure you want to close without importing?"
```

---

### Step 7 — SelectionBar nella pagina files/

**File**: `frontend/src/routes/(app)/files/+page.svelte`

Il componente `SelectionBar` è già presente in `BrokerImportFilesModal` e `DataEditor`, ma manca nella pagina files/.

**Modifiche**:
1. Importare `SelectionBar` dalla libreria table
2. Aggiungere stato `selectedFileIds: string[]`
3. Passare `onSelectionChange` a `FilesTable`
4. Posizionare `SelectionBar` prima del `ColumnVisibilityToggle` nella toolbar
5. Azioni: "Delete selected" (per file static), "Re-import selected" (per BRIM)

---

### Step 8 — Verifica build + test

```bash
./dev.py front check    # 0 errori, 0 warnings
./dev.py front build    # Build produzione OK
```

Test manuale:
1. Aprire `/fx/EUR-USD`, entrare in edit mode, cliccare Import CSV
2. Verificare che il modale si apre con header pre-popolato `date;EUR>USD`
3. Digitare righe nel formato `2024-01-15;1.0823` — validazione verde ✓
4. Cliccare swap `⇄` → header cambia a `date;USD>EUR`, direction bar aggiornata
5. Drag & drop un file `.csv` con header `date;USD>EUR` → auto-detect direzione, direction bar si aggiorna
6. Drag & drop un file con header `date;GBP>JPY` → errore rosso, import disabilitato
7. Cliccare `?` → sezione help visibile
8. Import → righe merge nella tabella, rate invertiti se necessario
9. Verificare SelectionBar nella pagina files/

---

## File coinvolti (stima)

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/fx/CsvEditor.svelte` | Rewrite: 2 colonne, header semantico `date;VAL1>VAL2`, validazione, API `setHeader()` |
| `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` | Redesign v2: drop zone in cima, direction bar, swap, help, auto-detect |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | Passare `displayBase`/`displayQuote` al modale, ricevere direzione dall'import |
| `frontend/src/lib/components/fx/FxDataEditorSection.svelte` | Gestire inversione rate al merge se direzione import ≠ display |
| `frontend/src/routes/(app)/files/+page.svelte` | Aggiungere SelectionBar |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Nuove chiavi i18n per import CSV |

---

## Note

- **No backward compatibility 4 colonne**: il vecchio formato `date;base;quote;base2quote` non è supportato. Il nuovo formato è più semplice e il vecchio non è mai stato usato da utenti reali (progetto embrionale).
- **CsvEditor location**: è sotto `components/fx/` ma è usato dal generico `DataImportModal`. Potrebbe avere senso spostarlo in `components/ui/data-editor/` per coerenza — da valutare durante l'implementazione.
- **Inversione rate: 2 livelli**: (1) all'import, il modale allinea i rate alla direzione display della pagina; (2) al save API, `FxDataEditorSection` normalizza verso il canonico. Non devono duplicarsi.
- **Testo intatto al drop**: quando l'utente fa drop di un file, il testo è inserito verbatim. Solo lo swap `⇄` o l'edit manuale modificano il contenuto.
