# MkDocs Agent Notes — Tricks & Gotchas

This file documents non-obvious behaviors, gotchas, and patterns for agents working on the LibreFolio MkDocs documentation.

---

## 1. Gallery Image Loader — `basePath` detection

**File**: `docs/javascripts/gallery-img-loader.js`

The `gallery-img-loader.js` script auto-resolves screenshot paths for `<img class="gallery-img">` elements on any page. It detects the MkDocs site base path (e.g., `/LibreFolio`) by scanning the current URL for **known top-level doc segments**.

### The Problem

If you add a new top-level section to the docs (e.g., `/user/`, `/admin/`) and forget to add it to the `knownSegments` array in `getBasePath()`, the script will fail to detect the base path correctly. Instead of resolving images at `/LibreFolio/gallery/desktop/...`, it will try `/LibreFolio/user/gallery/desktop/...` → **404**.

### The Fix

When adding a new top-level section to `mkdocs.yml`, **always update the `knownSegments` array** in `gallery-img-loader.js`:

```javascript
var knownSegments = [
    '/gallery/', '/developer/', '/user/', '/admin/',
    '/getting-started/', '/tutorials/', '/financial-theory/',
    '/POC_UX/', '/credits-legal/', '/faq/'
];
```

### How to Test

Open a page in the new section that uses `<img class="gallery-img" ...>` and check the browser console for 404 errors on image paths. If the base path is wrong, the image URL will contain the section path twice (e.g., `/user/gallery/` instead of `/gallery/`).

---

## 2. Gallery Image Usage in Non-Gallery Pages

To embed a gallery screenshot in any documentation page, use:

```html
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list" alt="FX List"
         style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>
```

- `data-category`: Maps to the screenshot folder (e.g., `auth`, `dashboard`, `settings`, `files`, `media`, `brokers`, `fx`)
- `data-name`: Maps to the file name without extension (e.g., `01-login`, `main`, `list`)
- The loader resolves the full path as: `{basePath}/gallery/{viewport}/{lang}/{theme}/{category}/{name}.png`
- `viewport` defaults to `desktop` unless `data-gallery="mobile"` is set
- `lang` and `theme` are auto-detected from localStorage and MkDocs theme attributes

Available screenshots can be found in `docs/gallery/desktop.md` by grepping for `data-category` and `data-name`.

---

## 3. Relative Links After Moving Files

MkDocs resolves relative links from the file's directory. When moving files into subdirectories (e.g., `user/files.md` → `user/files/index.md`), **all relative links break**:

- `../admin/settings.md` → `../../admin/settings.md` (one more `..` needed)
- `misc/image-crop.md` → `../misc/image-crop.md`

Always check and fix relative links after moving files. `mkdocs build --strict` will catch broken links.

---

## 4. MkDocs Build Validation

Always run after changes:

```bash
cd mkdocs_src && python -m mkdocs build --strict
```

This catches:
- Broken links (files referenced in nav but not on disk)
- Broken relative links in markdown
- Syntax errors in `mkdocs.yml`

Note: It does NOT catch gallery image 404s — those are runtime JS errors visible only in the browser console.

---

## 5. MkDocs `nav` Section Names vs File Paths

In `mkdocs.yml`, nav entries like:

```yaml
- Brokers:
    - Overview: user/brokers/index.md
    - Broker Sharing: user/brokers/sharing.md
```

The section name ("Brokers") creates a collapsible group in the sidebar. The `index.md` convention makes the overview the landing page for that section.

---

## 6. Dev Server for Preview

```bash
cd mkdocs_src && python -m mkdocs serve --dev-addr 127.0.0.1:8002
```

The `--dev-addr` avoids conflict with the main LibreFolio backend (port 8000) and test backend (port 8001).

---

## 7. 📝 Regole di Stile della Documentazione

Queste regole governano **tono, emoji, diagrammi e alberature** nella documentazione MkDocs di LibreFolio. Ogni agente deve applicarle in modo coerente.

### 7.1 Tono — Tre registri

La documentazione si rivolge a tre audience diverse. Il tono cambia di conseguenza:

| Area | Audience | Registro | Voce | Esempio |
|------|----------|----------|------|---------|
| **`user/`**, **`admin/`**, **`faq.md`** | Utenti finali, self-hoster | 🟢 **Amichevole & guidato** — step-by-step, frasi brevi, niente jargon tecnico. "Tu" diretto. | 2ª persona ("Navigate to…", "Click…", "You'll see…") | _"Click **Register** to create a new account."_ |
| **`developer/`** | Sviluppatori, contributori | 🟡 **Tecnico ma accessibile** — spiega il *perché* oltre al *come*. Assume conoscenze di programmazione, non dell'architettura LibreFolio. | 3ª persona o impersonale ("The service layer handles…", "Each plugin implements…") | _"The EMA recurrence is a first-order IIR low-pass filter."_ |
| **`financial-theory/`** | Lettori tecnici / accademici | 🔴 **Specialistico & rigoroso** — formule LaTeX, definizioni formali, doppia prospettiva (finanziaria + signal processing). Tono da paper accademico. | Impersonale, linguaggio matematico ("The normalisation maps… ", "Given a total return over $d$ days…") | _"The RSI is the ratio of the positive envelope to the total envelope, rescaled to $[0, 100]$."_ |

**Regole trasversali a tutti i registri:**

- Scrivere in **inglese** (la documentazione è single-language `en`; le traduzioni seguono via i18n pipeline).
- Usare i **MkDocs admonitions** (`!!! tip`, `!!! info`, `!!! warning`, `!!! example`) per evidenziare note laterali — mai per contenuto primario.
- Le tabelle sono preferite agli elenchi puntati quando ci sono ≥3 colonne di attributi (es. parametri, flag CLI, confronti).
- I blocchi di codice usano sempre il language tag corretto: ` ```python `, ` ```bash `, ` ```typescript `, ` ```mermaid `, ` ```text `.
- Ogni pagina inizia con un paragrafo introduttivo di 1-2 righe sotto l'H1, senza heading.

### 7.2 Emoji — Regole di applicazione

Le emoji servono a **guidare l'occhio** nella scansione rapida della sidebar e delle heading. Non sono decorative — sono segnali semantici.

#### Heading

| Livello | Regola | Esempio |
|---------|--------|---------|
| **H1** (`#`) | **Sempre** 1 emoji tematica all'inizio. Scelta in base al dominio della pagina. | `# 🔐 Authentication` |
| **H2** (`##`) | **Sempre** 1 emoji prima del testo. Coerente col sotto-tema. | `## 📊 Dashboard` |
| **H3** (`###`) | **Sempre** 1 emoji prima del testo. Spesso riflette il dominio del genitore H2 o il concetto specifico. | `### ⚙️ Parameters` |
| **H4+** (`####`) | Solo se la pagina è lunga e le H4 compaiono nella sidebar (raro). | `#### 📝 Transaction Detail` |

#### Principi

- **Mai doppia emoji** sullo stesso heading (es. ~~`## 🔐🔑 Login`~~).
- **Consistenza intra-file**: lo stesso concetto ricorrente usa la stessa emoji (es. tutte le H3 "Parameters" → ⚙️, tutte le H3 "Financial Meaning" → 💡).
- **Consistenza cross-file**: sezioni strutturalmente identiche (es. `## Purpose`, `## Running` nei test walkthrough) condividono le stesse emoji in ogni file.
- **Bullet list emoji**: usare emoji sulle bullet **solo quando aggiungono informazione semantica** (es. ✅/❌ per checklist, 👤/📧/🔑 per campi form). Non decorare bullet generiche.

#### Palette emoji per dominio

| Dominio | Emoji frequenti |
|---------|----------------|
| Auth / Sicurezza | 🔐 🔑 🛡️ 🔒 |
| Dashboard / Overview | 📊 📈 📉 |
| Settings / Config | ⚙️ 🎛️ 🔧 |
| File / Filesystem | 📁 📂 📄 📤 📥 |
| Broker / Finanza | 🏦 💰 💸 💼 |
| FX / Valute | 💱 🔄 |
| Test / Verifica | 🎯 ✅ 🧪 🚀 |
| Architettura / Patterns | 🏗️ 🧩 📐 |
| Matematica / Formule | 🔢 📐 📏 |
| Signal Processing | 🎛️ 📡 ⚡ |
| Info / About | ℹ️ 📖 💡 |
| Warning / Errori | ⚠️ 🚨 |
| Guide / How-to | 📝 📋 🗺️ |

### 7.3 Diagrammi — Mermaid

Tutti i diagrammi usano **Mermaid** (supporto nativo MkDocs Material). Niente immagini PNG per diagrammi architetturali — solo Mermaid inline.

| Tipo di diagramma | Sintassi Mermaid | Quando usarlo |
|-------------------|-----------------|---------------|
| **Flusso dati / Architettura** | `graph TD` o `flowchart TD` | Overview di sistema, data flow tra componenti, plugin pipeline |
| **Sequenza API** | `sequenceDiagram` | Flussi request-response, auth flow, sync lifecycle |
| **Schema DB** | `classDiagram` | Relazioni tra tabelle, ER diagrams |
| **Fasi verticali** | `graph TD` con `subgraph` | Pipeline multi-step (es. BRIM parse, plugin lifecycle) |
| **Dependency map** | `graph TD` con `-.->` (tratteggiato) per le dipendenze | Componenti frontend, import graph |

**Stile Mermaid:**

- Usare `subgraph "Nome Leggibile"` per raggruppare nodi logicamente.
- Colorare i subgraph con `style` per distinguere i layer (es. `fill:#f3e5f5` per modals, `fill:#e3f2fd` per pickers).
- Etichette nodi: `NomeBreve["Nome Completo Leggibile"]` — mai ID criptici.
- Frecce: `-->` per flusso dati, `-.->` per dipendenza opzionale, `==>` per percorso critico.

### 7.4 Alberature — Directory tree

Le strutture directory usano **code block `text`** con caratteri box-drawing Unicode:

```text
backend/
├── app/
│   ├── api/              # FastAPI routers
│   ├── models/           # SQLAlchemy ORM models
│   ├── services/         # Business logic layer
│   └── utils/            # Shared utilities
├── data/
│   ├── sqlite/           # Production database
│   └── test/             # Test database (isolated)
└── alembic/              # Database migrations
```

**Regole:**

- Usare `├──` per elementi intermedi, `└──` per l'ultimo elemento di un livello, `│` per la linea verticale.
- Aggiungere un **breve commento inline** (`# descrizione`) dopo ogni cartella/file significativo.
- Profondità massima: **3 livelli**. Se serve di più, fare una sezione separata per il sotto-albero.
- Le alberature **non** usano emoji nei nomi — le emoji sono solo per le heading markdown.
- La cartella root del tree deve essere il contesto minimo necessario (es. `backend/`, non `/Users/ea_enel/Documents/...`).

### 7.5 Separatori e struttura pagina

- Usare `---` (horizontal rule) tra sezioni H2 **solo** nelle pagine lunghe (>80 righe) per separare visivamente blocchi tematici.
- Non usare `---` tra H3 consecutive sotto la stessa H2.
- Le pagine seguono questo schema tipico:

```
# 🎯 Titolo Pagina                 ← H1 con emoji
                                    ← paragrafo intro 1-2 righe
---                                 ← separatore opzionale
## 📊 Sezione Principale           ← H2 con emoji
### 💡 Sotto-sezione               ← H3 con emoji
   contenuto, tabelle, code blocks
### ⚙️ Altra sotto-sezione         ← H3 con emoji
---                                 ← separatore tra H2
## 🔧 Seconda Sezione              ← H2 con emoji
```
