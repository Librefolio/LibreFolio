# Piano: Fix Traduzioni Residue + Resize Tabelle + Pipeline Admonition

**Data creazione**: 22 Marzo 2026
**Status**: ✅ COMPLETATO
**Priorità**: Alta (blocca il consolidamento finale Phase 5)
**Stima**: ~1-2 giorni
**Completato**: 22 Marzo 2026
**Dipendenze**: `plan-postTranslationBugfixAndDocs.prompt.md` completato ✅, `plan-mkdocsI18nPipeline.prompt.md` completato ✅

### Progress Tracking

| Step | Task | Status |
|------|------|--------|
| **1** | Colonne Cash/Asset in transaction-types IT/FR/ES | ✅ Completato |
| **2** | Rimuovere note traduttore residue (6 file) + fix pipeline | ✅ Completato (6 fix manuali + 3 pattern pipeline + 2 check artifacts) |
| **3** | Fix link `settings.md` mancante in cli_tools IT/FR | ✅ Completato |
| **4** | Fix link `../chart-settings.md` aggiunto in signals IT/FR/ES | ✅ Completato |
| **5** | Ri-tradurre data-editor.it.md (file troppo rotto) | ✅ Completato (fix manuale — API key disabilitata) |
| **6** | Fix struttura heading gallery/desktop.es.md | ✅ Completato (rimosso duplicato Broker Edit sotto Settings) |
| **7** | Migliorare validazione admonition in pipeline | ✅ Completato (title preservation + body presence) |
| **8** | Investigare bug resize colonne DataTable | ✅ Completato (z-index:5, width:6px, fix auto-layout: `width` al posto di `min-width` + lettura da `columnWidths`) |

### Risultati finali

- Anomalie translate-diff: **80 → 50** (30 eliminate)
- Le 50 residue sono BOLD_MARKERS ±1-5 (~30), LINE_COUNT (~5), HORIZONTAL_RULES (~6), LINK diff in FAQ (~5), NUMBERED_LIST (~2) — tutte variazioni cosmetiche del modello LLM, da gestire via agente critico

---

## Contesto

Dopo il completamento del plan `plan-postTranslationBugfixAndDocs.prompt.md` (tutti i 49 task A1–D4 marcati ✅), una nuova esecuzione di `./dev.py mkdocs translate-diff --verbose` rivela ancora **80 anomalie in 45 file**. L'analisi manuale dei file affetti mostra che le anomalie si dividono in:

1. **6 fix strutturali manuali** — colonne HTML mancanti, note traduttore residue, righe fuse, link errati
2. **1 file da ri-tradurre** — troppo rotto per fix manuale (`data-editor.it.md`)
3. **~30 file con BOLD_MARKERS ±1-3** — rumore cosmetico, nessun intervento manuale; saranno passati all'agente critico come contesto nella prossima esecuzione della pipeline
4. **1 bug frontend** — tutte le tabelle DataTable non hanno colonne ridimensionabili via drag
5. **1 miglioramento pipeline** — validazione contenuto body/title degli admonition (`!!! tip`)

### Root cause delle note traduttore sfuggite

La funzione `_clean_translation()` in `translate_docs.py` (riga 307) ha 3 blind spot nel pattern di rimozione delle sezioni "Translator's Notes":

1. **Emoji prima del testo**: il regex `###?\s*(?:Note?...)` non cattura `## 📖 Notes du Traducteur` (l'emoji `📖` si interpone tra `##` e `Notes`)
2. **Formato bold**: `**Notas del Traductor**` non è un heading markdown, è testo grassetto
3. **Formato HTML**: `<h2>Notas del Traductor</h2>` con `<ol>` — completamente diverso da heading markdown

### Root cause colonne Cash/Asset mancanti

Le colonne Cash e Asset (con emoji ⬆️⬇️) sono state aggiunte al file EN in B13 del plan precedente, ma la ri-traduzione D1 ha usato il modello LLM che ha generato le traduzioni a partire dalla struttura pre-B13 presente nella cache. I file tradotti non sono mai stati aggiornati manualmente per includere le 2 colonne aggiuntive nella tabella HTML.

---

## Step 1 — Aggiungere colonne Cash/Asset a `transaction-types` IT/FR/ES

La differenza di 26 righe in tutte e 3 le lingue è causata dalle colonne `Cash` e `Asset` aggiunte in EN (B13) ma mai propagate alle traduzioni. Il file EN ha 6 colonne (Icon, Type, Code, Description, Cash, Asset) con `<td>` contenenti emoji frecce; le traduzioni ne hanno solo 4.

**File**:
- `mkdocs_src/docs/financial-theory/transaction-types.it.md`
- `mkdocs_src/docs/financial-theory/transaction-types.fr.md`
- `mkdocs_src/docs/financial-theory/transaction-types.es.md`

**Azione**: in ciascun file tradotto:

1. Aggiungere nell'`<thead>` le 2 `<th>` mancanti dopo `<th>Descrizione</th>`:

   | Lingua | Header Cash | Header Asset |
   |--------|------------|--------------|
   | IT | `<th style="text-align: center;">Liquidità</th>` | `<th style="text-align: center;">Asset</th>` |
   | FR | `<th style="text-align: center;">Trésorerie</th>` | `<th style="text-align: center;">Actif</th>` |
   | ES | `<th style="text-align: center;">Efectivo</th>` | `<th style="text-align: center;">Activo</th>` |

2. Aggiungere per ogni `<tr>` nel `<tbody>` i 2 `<td>` con le emoji identiche all'EN:

   | Type | Cash `<td>` | Asset `<td>` |
   |------|-------------|--------------|
   | BUY | `<td style="text-align: center;">⬇️</td>` | `<td style="text-align: center;">⬆️</td>` |
   | SELL | `⬆️` | `⬇️` |
   | DIVIDEND | `⬆️` | `—` |
   | INTEREST | `⬆️` | `—` |
   | DEPOSIT | `⬆️` | `—` |
   | WITHDRAWAL | `⬇️` | `—` |
   | FEE | `⬇️` | `—` |
   | TAX | `⬇️` | `—` |
   | FX_CONVERSION | `⬆️⬇️` | `—` |
   | TRANSFER_IN | `—` | `⬆️` |
   | TRANSFER_OUT | `—` | `⬇️` |
   | ADJUSTMENT | `⬆️⬇️` | `⬆️⬇️` |

---

## Step 2 — Rimuovere note traduttore residue (6 file) + fix pipeline

### 2a. Fix manuali — eliminare tutto dal separator/heading fino a fine file

| File | Righe da eliminare | Formato sfuggito |
|------|-------------------|------------------|
| `mkdocs_src/docs/admin/settings.fr.md` | 79–82 | `---` + `## 📖 Notes du Traducteur` (emoji) |
| `mkdocs_src/docs/admin/cli_tools.fr.md` | 113–116 | ` ``` ` dangling + `## Notes du traducteur` (dentro code fence) |
| `mkdocs_src/docs/financial-theory/returns.fr.md` | 124–126 | `## 📝 Notes du traducteur` (emoji) |
| `mkdocs_src/docs/credits-legal.es.md` | 49–50 | `**Notas del traductor**:` (bold) |
| `mkdocs_src/docs/financial-theory/synthetic-benchmarks.es.md` | 160–162 | `---` + `**Notas del Traductor**` (bold) |
| `mkdocs_src/docs/index.es.md` | 159–169 | `<hr>` + `<h2>Notas del Traductor</h2>` + `<ol>` intero blocco HTML |

### 2b. Miglioramento `_clean_translation()` in `translate_docs.py`

Aggiungere 3 nuovi pattern **dopo** i 2 pattern esistenti al punto 2 (riga 323–330), prima del punto 3:

```python
# 2b. Emoji variant: ## 📖 Notes du Traducteur, ## 📝 Note del Traduttore, etc.
r"\n---\s*\n+\s*##\s+\S+\s+(?:Note?\s+(?:del|du)\s+Trad\w+|Translator['\u2019]?s?\s+Notes?|Notas?\s+del?\s+Trad\w+).*",
r"\n##\s+\S+\s+(?:Note?\s+(?:del|du)\s+Trad\w+|Translator['\u2019]?s?\s+Notes?|Notas?\s+del?\s+Trad\w+).*",

# 2c. Bold variant: **Notas del Traductor**, **Notes du traducteur**, etc.
r"\n---\s*\n+\*\*(?:Notas?\s+del?\s+Trad\w+|Notes?\s+du\s+Trad\w+|Note?\s+del\s+Trad\w+|Translator['\u2019]?s?\s+Notes?)\*\*.*",
r"\n\*\*(?:Notas?\s+del?\s+Trad\w+|Notes?\s+du\s+Trad\w+|Note?\s+del\s+Trad\w+|Translator['\u2019]?s?\s+Notes?)\*\*.*",

# 2d. HTML variant: <h2>Notas del Traductor</h2>, <h3>Notes du traducteur</h3>, etc.
r"\n<hr\s*/?\s*>\s*\n*<h[1-6]>\s*(?:Notas?\s+del?\s+Trad\w+|Notes?\s+du\s+Trad\w+|Note?\s+del\s+Trad\w+|Translator['\u2019]?s?\s+Notes?)\s*</h[1-6]>.*",
r"\n<h[1-6]>\s*(?:Notas?\s+del?\s+Trad\w+|Notes?\s+du\s+Trad\w+|Note?\s+del\s+Trad\w+|Translator['\u2019]?s?\s+Notes?)\s*</h[1-6]>.*",
```

Tutti con `flags=re.DOTALL | re.IGNORECASE` per catturare fino a fine file.

### 2c. Miglioramento `check_artifacts()` in `validate_translations.py`

Aggiungere check per le 3 varianti:

```python
# Bold translator notes (not caught by heading check)
bold_notes = re.findall(
    r'\*\*(?:Notas?\s+del?\s+Trad\w+|Notes?\s+du\s+Trad\w+|Note?\s+del\s+Trad\w+)\*\*',
    translated, re.IGNORECASE
)
if bold_notes:
    issues.append(Issue(
        severity=Severity.ERROR, file=cache_key, lang=lang,
        check="artifact-translator-notes-bold",
        message=f"Translator notes in bold format: {bold_notes[0]}",
    ))

# HTML translator notes
html_notes = re.findall(
    r'<h[1-6]>\s*(?:Notas?\s+del?\s+Trad\w+|Notes?\s+du\s+Trad\w+|Note?\s+del\s+Trad\w+)\s*</h[1-6]>',
    translated, re.IGNORECASE
)
if html_notes:
    issues.append(Issue(
        severity=Severity.ERROR, file=cache_key, lang=lang,
        check="artifact-translator-notes-html",
        message=f"Translator notes in HTML heading: {html_notes[0]}",
    ))
```

---

## Step 3 — Fix link `settings.md` mancante in `cli_tools` IT/FR

In EN riga 71 c'è `[Global Settings](settings.md)`, ma:

- **cli_tools.it.md** riga 71: "Impostazioni Globali predefinite" → testo senza link
- **cli_tools.fr.md** riga 71: `[Paramètres globaux]` → sintassi markdown link rotta (manca URL)

**File**:
- `mkdocs_src/docs/admin/cli_tools.it.md`
- `mkdocs_src/docs/admin/cli_tools.fr.md`

**Fix IT** (riga 71):
```markdown
Popola il database con le [Impostazioni Globali](settings.md) predefinite, se non esistono già.
```

**Fix FR** (riga 71):
```markdown
Remplit la base de données avec les [Paramètres Globaux](settings.md) par défaut s'ils n'existent pas déjà.
```

---

## Step 4 — Fix link `../chart-settings.md` aggiunto in `signals` IT/FR/ES

Il diff segnala LINK_URLS / LINK_COUNT per tutte e 3 le lingue. In EN la sezione "How to Use" (righe 41–45) ha 5 step senza link esterni:

```markdown
1. Click the **Signals** toggle button (📈) in the chart toolbar
2. The signals panel opens below the chart
3. Add indicators from the categorized dropdowns (Technical Indicators, Data Comparison, Synthetic Benchmarks)
4. Each indicator's parameters can be adjusted inline
5. Signals are rendered as overlays directly on the chart
```

Le traduzioni hanno riscritto i passi 3-5 aggiungendo un riferimento a `../chart-settings.md` inesistente nel source EN.

**File**:
- `mkdocs_src/docs/user/fx/detail/signals.it.md` righe 41–45
- `mkdocs_src/docs/user/fx/detail/signals.fr.md` righe 41–45
- `mkdocs_src/docs/user/fx/detail/signals.es.md` righe 41–45

**Fix IT** — sostituire righe 41–45 con:
```markdown
1. Fai clic sul pulsante di attivazione **Segnali** (📈) nella barra degli strumenti del grafico
2. Il pannello segnali si apre sotto il grafico
3. Aggiungi indicatori dai menu a discesa categorizzati (Indicatori Tecnici, Confronto Dati, Benchmark Sintetici)
4. I parametri di ogni indicatore possono essere regolati direttamente inline
5. I segnali sono visualizzati come sovrapposizioni direttamente sul grafico
```

**Fix FR** — sostituire righe 41–45 con:
```markdown
1. Cliquez sur le bouton bascule **Signaux** (📈) dans la barre d'outils du graphique
2. Le panneau des signaux s'ouvre sous le graphique
3. Ajoutez des indicateurs depuis les menus déroulants catégorisés (Indicateurs Techniques, Comparaison de Données, Benchmarks Synthétiques)
4. Les paramètres de chaque indicateur peuvent être ajustés directement en ligne
5. Les signaux s'affichent en superposition directement sur le graphique
```

**Fix ES** — sostituire righe 41–45 con:
```markdown
1. Haz clic en el botón de alternancia **Señales** (📈) en la barra de herramientas del gráfico
2. El panel de señales se abre debajo del gráfico
3. Agrega indicadores desde los menús desplegables categorizados (Indicadores Técnicos, Comparación de Datos, Benchmarks Sintéticos)
4. Los parámetros de cada indicador pueden ajustarse directamente en línea
5. Las señales se representan como superposiciones directamente en el gráfico
```

---

## Step 5 — Ri-tradurre `data-editor.it.md` (file troppo rotto)

Questo file ha righe fuse in almeno 6 punti — heading+numbered list (righe 23, 28), numbered items fusi (riga 34), code block fusi (righe 61, 102-103, 109), mancano 5 horizontal rules, -3 numbered list items, -2 code blocks. Non è correggibile manualmente in modo pratico.

**Azione**:

```bash
./dev.py mkdocs translate --force --file user/fx/detail/data-editor.en.md --lang it
```

Dopo la ri-traduzione, verificare con:
```bash
./dev.py mkdocs translate-diff --lang it --verbose | grep data-editor
```

Se la ri-traduzione produce ancora difetti, applicare fix manuali alle righe fuse.

---

## Step 6 — Fix struttura heading `gallery/desktop.es.md`

In ES, `### ✏️ Edición de Broker` (righe 93–99) è posizionato sotto `## ⚙️ Configuración` anziché sotto `## 🏦 Brokers` come nell'EN. L'EN ha la seguente struttura:

```
## ⚙️ Settings
  ### 🎛️ User Preferences
  ### 🛡️ Global Settings (Admin)
  ### ℹ️ About
  ### 🔐 Password Change
  ### 👤 Profile
## 📁 Files
  ...
```

Nell'ES c'è un `### ✏️ Edición de Broker` extra tra `### 👤 Perfil` e `## 📁 Archivos` che nell'EN non esiste in quella posizione — si trova più sotto, sotto `## 🏦 Brokers`:

```
## 🏦 Brokers
  ### 📋 Broker List
  ### 🔍 Broker Detail
  ### ✏️ Broker Edit     ← dovrebbe essere qui
  ### 📥 Import Modal
  ### 🤝 Broker Sharing
```

**File**: `mkdocs_src/docs/gallery/desktop.es.md`

**Fix**: tagliare il blocco righe 93–99 (heading `### ✏️ Edición de Broker` + paragrafo + `<div>` screenshot) dalla sezione Configuración, e incollarlo nella posizione corretta sotto la sezione `## 🏦 Brokers`, dopo `### 🔍 Detalle de Broker`.

---

## Step 7 — Migliorare validazione admonition in pipeline

In `mkdocs_src/aphra-pipeline/validate_translations.py`, i check esistenti per admonition sono:
- `check_admonitions` (riga 513) — verifica conteggio e tipo keyword
- `check_admonition_indent` (riga 375) — verifica indentazione 4 spazi

**Mancante**: verifica che il **title text** (`"..."`) sia preservato e che il **body content** (testo indentato) sia effettivamente presente.

### 7a. Arricchire `check_admonition_indent()` — title preservation

Confrontare la lista di titoli `"..."` degli admonition tra source e traduzione:

```python
# Extract admonition titles
src_titles = re.findall(r'^(?:!!!|[?]{3})\s+\w+\s+"([^"]*)"', source, re.MULTILINE)
tr_titles = re.findall(r'^(?:!!!|[?]{3})\s+\w+\s+"([^"]*)"', translated, re.MULTILINE)

if len(src_titles) != len(tr_titles):
    issues.append(Issue(
        severity=Severity.WARN,
        file=cache_key, lang=lang,
        check="admonition-title-count",
        message=f"Admonition titles: source {len(src_titles)}, translation {len(tr_titles)}",
    ))

# Check for empty titles (source has text, translation is empty)
for idx, (src_t, tr_t) in enumerate(zip(src_titles, tr_titles)):
    if src_t.strip() and not tr_t.strip():
        issues.append(Issue(
            severity=Severity.ERROR,
            file=cache_key, lang=lang,
            check="admonition-title-empty",
            message=f"Admonition #{idx+1}: title lost (source: \"{src_t}\")",
        ))
```

### 7b. Arricchire `check_admonition_indent()` — body presence

Dopo un `!!! type "title"`, verificare che almeno 1 riga non-vuota indentata a 4 spazi esista entro le 10 righe successive:

```python
# Check that admonition body is present (not just a title box)
for i, line in enumerate(lines):
    if re.match(r'^(?:!!!|[?]{3})\s+\w+', line):
        has_body = False
        for j in range(i + 1, min(i + 10, len(lines))):
            next_line = lines[j]
            if next_line.startswith('    ') and next_line.strip():
                has_body = True
                break
            if (next_line.strip() and not next_line.startswith('    ')
                    and not next_line.strip() == ''):
                break  # Content outside admonition
        if not has_body:
            issues.append(Issue(
                severity=Severity.ERROR,
                file=cache_key, lang=lang,
                check="admonition-body-missing",
                line=i + 1,
                message=f"Admonition has title but no indented body content: "
                        f"'{line.strip()[:60]}'",
            ))
```

### 7c. Sotto-comando `translate-fix-indent`

Creare un sotto-comando `./dev.py mkdocs translate-fix-indent` che:

1. Scansiona tutti i file `*.{it,fr,es}.md` in `mkdocs_src/docs/`
2. Per ogni admonition (`!!!`/`???`) trovato, verifica che le righe successive di body siano indentate a 4 spazi
3. Se una riga di body ha meno di 4 spazi di indentazione (ma non è una riga vuota, un nuovo blocco `!!!`/`???`, o un `---`), ri-indenta automaticamente a 4 spazi
4. Mostra un report dei file modificati e del numero di righe fixate
5. Con flag `--dry-run` mostra solo cosa farebbe senza scrivere

---

## Step 8 — Investigare bug resize colonne DataTable

**File**: `frontend/src/lib/components/table/DataTable.svelte`

Il sistema di resize è implementato (righe 582–611 per la logica, righe 1246–1274 per il CSS, riga 83 per `enableColumnResize = true` di default, riga 1130 per `position: relative` su `<th>`). Il `.resize-handle` è `width: 4px`, `opacity: 0`, appare su `th:hover`. Ma il resize non funziona su **nessuna** tabella nell'app.

**Debug steps**:

1. **DOM check**: aprire DevTools → Elements → hover su un `<th>` → verificare che `.resize-handle` sia presente nel DOM e visibile (opacity cambia a 1)

2. **Event check**: aggiungere `console.log` temporaneo in `startResize()` (riga 582) per verificare che `onmousedown` si triggera

3. **Z-index/overlap**: `.resize-handle` è `position: absolute; right: 0` ma non ha z-index. Potrebbe essere coperto da:
   - `.header-content` (flex container a riga 1173)
   - `.filter-btn` (adiacente al resize handle nell'HTML)
   - `.header-sort-btn` che copre l'intera area cliccabile
   
   **Probabile fix**: aggiungere `z-index: 5` a `.resize-handle` e/o aumentare la `width` a 6-8px per una zona di presa più ampia

4. **Pointer events**: verificare che nessun wrapper parent (`.table-container`, `table`) abbia `pointer-events: none` o `overflow: hidden` che intercetta gli eventi mouse

5. **Touch devices**: il sistema usa solo `mousedown/mousemove/mouseup`. Se testato su iPad/touch → non funzionerà. Ma il report è per mouse, quindi questo è un follow-up.

**Possibili fix** (da verificare dopo il debug):

```css
.resize-handle {
    /* ...existing code... */
    z-index: 5;        /* Sopra filter-btn e header-content */
    width: 6px;        /* Area di presa più ampia */
}
```

Se il problema è che `.header-sort-btn` copre l'area:
```css
.header-content {
    /* ...existing code... */
    padding-right: 8px; /* Lascia spazio al resize handle */
}
```

---

## Ordine di Esecuzione

```
┌─────────────────────────────────────────────────┐
│  Step 1–4, 6 (fix manuali docs, parallelizzabili) │
│  ~0.5 giorni                                      │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│  Step 2b,2c (miglioramento pipeline)             │
│  Step 7 (validazione admonition)                 │
│  ~0.5 giorni                                      │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│  Step 5 (ri-traduzione data-editor.it.md)        │
│  ~15 min (automatico)                            │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│  Step 8 (debug resize DataTable)                 │
│  Indipendente, parallelizzabile con Steps 1–7    │
│  ~0.5 giorni                                      │
└─────────────────────────────────────────────────┘
```

---

## Tempo Stimato Totale

| Step | Stima |
|------|-------|
| 1 — Colonne Cash/Asset (3 file HTML) | ~30 min |
| 2 — Note traduttore (6 fix manuali + 2 pattern pipeline) | ~45 min |
| 3 — Link settings.md (2 file, 1 riga ciascuno) | ~5 min |
| 4 — Link chart-settings.md (3 file, 5 righe ciascuno) | ~15 min |
| 5 — Ri-traduzione data-editor.it.md | ~15 min (automatico) |
| 6 — Heading gallery/desktop.es.md | ~10 min |
| 7 — Validazione admonition pipeline | ~1 ora |
| 8 — Debug resize DataTable | ~2-4 ore |
| **Totale** | **~5-7 ore** |

