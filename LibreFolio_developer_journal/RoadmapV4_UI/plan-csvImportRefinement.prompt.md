# Plan: CSV Import Refinement — DataImportModal v2

**Dipendenze**: [`plan-fxDetailBugRound7-4.prompt.md`](plan-fxDetailBugRound7-4.prompt.md)

Redesign completo del flusso di import CSV per la pagina FX Detail. Il modale attuale (`DataImportModal`) usa un CSV a 4 colonne (`date;base;quote;base2quote`) che è ridondante ora che il Data Editor è "bloccato" su una coppia FX specifica nella pagina detail. Il redesign semplifica l'UX mantenendo la flessibilità.

**Stato**: 🔄 In corso

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

## Proposta di redesign

### Concept: Modale "Smart Import"

Il modale si adatta al contesto della pagina FX Detail:

```
┌──────────────────────────────────────────────────────┐
│  Import CSV Data                              ? ✕    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Direction:                                          │
│  ┌──────────┐          ┌──────────┐                  │
│  │ 🇪🇺 EUR  │   ──→    │ 🇺🇸 USD  │     ⇄            │
│  └──────────┘          └──────────┘                  │
│  ℹ️ Rates will be saved as EUR→USD                   │
│     (inverted automatically if needed)               │
│                                                      │
│  ┌─ Drop CSV here ─────────────────────────────────┐ │
│  │  📄 my_rates.csv                                │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  ┌─ Preview ───────────────────────────────────────┐ │
│  │ 1 │ date;rate              ← Simplified header  │ │
│  │ 2 │ 2024-01-15;1.0823  ✓                        │ │
│  │ 3 │ 2024-01-16;1.0845  ✓                        │ │
│  │ 4 │ 2024-01-17;abc     ✗  Invalid rate          │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  3 valid rows              Cancel   Import (3)       │
└──────────────────────────────────────────────────────┘
```

### Decisioni progettuali

#### A. Formato CSV semplificato

**Opzione A1** (consigliata): Solo 2 colonne — `date;rate`
- Il più semplice per l'utente
- La direzione è determinata dai selettori valuta nel modale
- Se necessario, il rate viene invertito (1/rate) prima del merge

**Opzione A2**: Mantenere 4 colonne ma auto-fill base/quote
- Backward compatible con file CSV esistenti
- Auto-parse dell'header per determinare la direzione

**Proposta**: Supportare ENTRAMBI i formati:
- Se il CSV ha 2 colonne → `date;rate`, usa la direzione del modale
- Se il CSV ha 4 colonne → `date;base;quote;rate`, auto-detect direzione dall'header e auto-populate i selettori

#### B. Direction selectors

- 2 `CurrencySearchSelect` **readonly** (non cambiabili, derivati dalla pagina)
- Freccia `→` al centro con pulsante swap `⇄`
- Cliccando `⇄` si inverte la direzione di interpretazione del CSV
- La direzione iniziale segue la pagina (se la pagina mostra USD→EUR, il modale mostra USD→EUR)

#### C. Auto-detect dalla naming convention

Se il file si chiama `EUR>USD.csv` o `EUR-USD.csv`:
- Auto-populate i selettori con EUR (base) e USD (quote)
- Se la direzione non corrisponde alla pagina, mostrare warning

#### D. Help button `?`

- Icona `?` nell'header del modale, accanto al titolo
- Cliccando: apre tooltip/popover con spiegazione rapida del formato
- Link "Learn more" → pagina documentazione MkDocs (futuro)

---

## Stato implementazione

| Step | Descrizione | Stato | Note |
|------|-------------|-------|------|
| **1** | Refactor CsvEditor: supporto 2+4 colonne | 🔲 | Auto-detect formato, validazione adattiva |
| **2** | Redesign DataImportModal v2 | 🔲 | Direction selectors, smart header, help button |
| **3** | Auto-detect direzione da filename | 🔲 | Parse `EUR>USD`, `EUR-USD`, `EUR_USD` |
| **4** | Inversione rate automatica al merge | 🔲 | Se direzione modale ≠ canonico, 1/rate |
| **5** | Help tooltip + link docs | 🔲 | Icona `?` con popover, testo i18n |
| **6** | i18n per tutte le nuove stringhe | 🔲 | EN, IT, FR, ES |
| **7** | SelectionBar nella pagina files/ | 🔲 | Aggiungere dove manca (before ColumnVisibilityToggle) |
| **8** | Verifica build + test | 🔲 | `./dev.py front check` + test manuale |

---

## Steps dettagliati

### Step 1 — Refactor CsvEditor: supporto 2+4 colonne

**File**: `frontend/src/lib/components/fx/CsvEditor.svelte`

Il CsvEditor attualmente è hardcoded per il formato a 4 colonne (`date;base;quote;base2quote`).

**Modifiche**:

1. Aggiungere prop `mode: '2col' | '4col' | 'auto'` (default `'auto'`)
2. In modalità `auto`:
   - Se la prima riga (header) contiene 2 campi → `2col`
   - Se contiene 4 campi → `4col`
   - Se non ha header riconosciuto, guardare la prima riga dati
3. Validazione adattiva:
   - `2col`: `date;rate` — solo data e numero positivo
   - `4col`: `date;base;quote;rate` — come ora
4. L'interfaccia `ParsedRow` va estesa per gestire entrambi:
   ```ts
   export interface ParsedRow {
       date: string;
       base?: string;   // undefined in 2col mode
       quote?: string;   // undefined in 2col mode
       value: number;
       lineNumber: number;
   }
   ```
5. Prop `header` diventa opzionale in `2col` mode (default `'date;rate'`)
6. Emettere `onmodedetect?: (mode: '2col' | '4col') => void` per notificare il parent

---

### Step 2 — Redesign DataImportModal v2

**File**: `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte`

**Layout aggiornato**:

```svelte
<!-- Direction bar -->
<div class="flex items-center justify-center gap-4 py-3 px-4 bg-gray-50 dark:bg-slate-700/30 rounded-lg">
    <div class="flex items-center gap-2">
        <span class="text-lg">{baseFlag}</span>
        <span class="font-semibold">{displayFrom}</span>
    </div>
    <span class="text-gray-400 text-lg">→</span>
    <div class="flex items-center gap-2">
        <span class="text-lg">{quoteFlag}</span>
        <span class="font-semibold">{displayTo}</span>
    </div>
    <button onclick={swapDirection} title="Swap direction" class="...">
        <ArrowLeftRight size={16} />
    </button>
</div>

<!-- Info banner: explains what will happen -->
<InfoBanner variant="info">
    Rates will be interpreted as {displayFrom}→{displayTo}.
    {#if isSwapped}Rates will be inverted (1/rate) before saving.{/if}
</InfoBanner>
```

**Nuove props**:

```ts
interface Props {
    open?: boolean;
    /** Base currency of the page context */
    contextBase: string;
    /** Quote currency of the page context */
    contextQuote: string;
    /** Whether the page is already inverted from canonical */
    contextInverted: boolean;
    onimport?: (rows: ParsedRow[]) => void;
    onclose?: () => void;
}
```

**Logica di swap**:
- L'utente può cliccare `⇄` per invertire from/to
- Se `displayFrom` è diverso dalla base canonica, i rate vengono invertiti prima del merge
- Il CsvEditor usa `mode='auto'` — rileva se 2 o 4 colonne

**Logica di merge con inversione**:
```ts
function handleConfirm() {
    let rows = validRows;
    // In 2col mode, fill base/quote from direction selectors
    if (detectedMode === '2col') {
        rows = rows.map(r => ({...r, base: displayFrom, quote: displayTo}));
    }
    // If direction is swapped vs canonical, invert rates
    if (needsInversion(displayFrom, displayTo, contextBase, contextQuote)) {
        rows = rows.map(r => ({...r, value: 1 / r.value, base: r.quote, quote: r.base}));
    }
    onimport?.(rows);
}
```

---

### Step 3 — Auto-detect direzione da filename

**File**: `DataImportModal.svelte`

Quando l'utente trascina o seleziona un file:

```ts
function detectDirectionFromFilename(filename: string): {from: string; to: string} | null {
    // Match patterns: EUR>USD, EUR-USD, EUR_USD, EUR2USD (case insensitive)
    const match = filename.match(/([A-Z]{3})[>_\-]([A-Z]{3})/i);
    if (!match) return null;
    return {from: match[1].toUpperCase(), to: match[2].toUpperCase()};
}
```

Se rilevato:
1. Auto-set i selettori di direzione
2. Se la direzione del file != pagina, mostrare InfoBanner warning
3. L'utente può sempre correggere con il pulsante swap

---

### Step 4 — Inversione rate automatica al merge

**File**: `FxDataEditorSection.svelte` → `handleImport()`

Il `handleImport` nella `FxDataEditorSection` (via `DataEditor`) già gestisce il merge. Va aggiornato per:

1. Ricevere il flag `isInverted` dalle parsed rows o dal modale
2. Se necessario, invertire `1/rate` prima dell'upsert API
3. Nota: attualmente `FxDataEditorSection.handleSave()` già gestisce l'inversione canonica nella save API — verificare che non si duplichi

---

### Step 5 — Help tooltip + link docs

**File**: `DataImportModal.svelte`

Aggiungere icona `?` circled nell'header del modale:

```svelte
<button class="..." onclick={() => showHelp = !showHelp} title="Help">
    <HelpCircle size={18} />
</button>
```

Contenuto help (popover o sezione collassabile):

> **CSV Import Guide**
>
> Supported formats:
> - **Simple**: `date;rate` — one rate per line
> - **Full**: `date;base;quote;rate` — with explicit currencies
>
> - Dates must be `YYYY-MM-DD`
> - Rates must be positive numbers
> - Use `;` as separator
>
> The direction bar above shows how rates will be interpreted.
> Click ⇄ to swap if your CSV has rates in the opposite direction.
>
> [📖 Full documentation →](/docs/fx-import) _(futuro)_

---

### Step 6 — i18n per tutte le nuove stringhe

Chiavi i18n da aggiungere (tutte le 4 lingue):

```
csvImport.title             "Import CSV Data"
csvImport.direction         "Direction"
csvImport.ratesInterpretedAs "Rates will be interpreted as {from}→{to}"
csvImport.ratesInverted     "Rates will be inverted (1/rate) before saving"
csvImport.swapDirection     "Swap direction"
csvImport.dropFile          "Drop a .csv or .txt file here, or click to browse"
csvImport.dropReplace       "Drop another file to replace"
csvImport.formatSimple      "Simple format: date;rate"
csvImport.formatFull        "Full format: date;base;quote;rate"
csvImport.helpTitle         "CSV Import Guide"
csvImport.helpBody          (vedi step 5)
csvImport.detectedDirection "Direction detected from filename: {from}→{to}"
csvImport.directionMismatch "File direction differs from current selection"
csvImport.noValidRows       "No valid rows found"
csvImport.validRows         "{count} valid row(s)"
csvImport.import            "Import ({count})"
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
2. Verificare formato 2 colonne (`date;rate`) funziona
3. Verificare formato 4 colonne backward compatible
4. Verificare swap direzione inverte i rates
5. Verificare auto-detect da filename `USD>EUR.csv`
6. Verificare help tooltip visibile e chiaro
7. Verificare SelectionBar nella pagina files/

---

## File coinvolti (stima)

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/fx/CsvEditor.svelte` | Supporto 2+4 colonne, auto-detect, nuova interfaccia |
| `frontend/src/lib/components/ui/data-editor/DataImportModal.svelte` | Redesign v2: direction bar, help, smart header |
| `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` | Passare context (base/quote/inverted) al modale |
| `frontend/src/lib/components/fx/FxDataEditorSection.svelte` | Passare base/quote/inverted al DataEditor |
| `frontend/src/routes/(app)/files/+page.svelte` | Aggiungere SelectionBar |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Nuove chiavi i18n per import CSV |

---

## Note

- Il `CsvEditor.svelte` è attualmente sotto `components/fx/` ma è usato anche dal generico `DataImportModal`. Potrebbe avere senso spostarlo in `components/ui/data-editor/` per coerenza — da valutare.
- Il redesign deve essere backward compatible: se un utente incolla un CSV a 4 colonne che già aveva, deve continuare a funzionare.
- L'inversione rate è critica: un errore qui causa dati corrotti nel DB. Serve un InfoBanner chiaro che mostra la direzione e un eventual confirm prima dell'import.

