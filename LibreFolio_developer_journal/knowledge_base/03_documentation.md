# LibreFolio — Documentation Guide (MkDocs)

> **Questo file sostituisce e ingloba** il precedente `mkdocs_src/skill_agent_note.md`.

## 📁 Struttura

```text
mkdocs_src/
├── mkdocs.yml                  # Config principale
├── docs/
│   ├── user/                   # Manuale utente (17 file × 4 lingue)
│   ├── admin/                  # Manuale admin (6 file × 4 lingue)
│   ├── developer/              # Manuale sviluppatore (EN-only, ~45 file)
│   ├── financial-theory/       # Teoria finanziaria (7 file × 4 lingue, LaTeX)
│   ├── gallery/                # Screenshot UI (desktop + mobile)
│   ├── static/                 # CSS, logo, favicon, icons
│   └── javascripts/            # JS custom (gallery loader, lang selector, app sync)
├── aphra-pipeline/             # Pipeline traduzione LLM
│   ├── translate_docs.py       # Orchestrazione traduzione
│   └── validate_translations.py # Validazione strutturale
└── site/                       # Build output (gitignored)
```

---

## 1. Gallery Image Loader — `basePath` detection

`gallery-img-loader.js` auto-risolve i path degli screenshot. Quando si aggiunge una **nuova sezione top-level** ai docs, aggiornare l'array `knownSegments` in `getBasePath()`:

```javascript
var knownSegments = [
    '/gallery/', '/developer/', '/user/', '/admin/',
    '/getting-started/', '/tutorials/', '/financial-theory/',
    '/POC_UX/', '/credits-legal/', '/faq/'
];
```

Test: aprire una pagina nella nuova sezione con `<img class="gallery-img">` e controllare la console per 404.

---

## 2. Gallery Images in Non-Gallery Pages

```html
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list" alt="FX List"
         style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>
```

- `data-category`: cartella screenshot (`auth`, `dashboard`, `settings`, `files`, `brokers`, `fx`, `assets`)
- `data-name`: file senza estensione (`01-login`, `main`, `list`)
- Path risolto: `{basePath}/gallery/{viewport}/{lang}/{theme}/{category}/{name}.png`

---

## 3. MkDocs Build Validation

```bash
./dev.py mkdocs build   # equivale a: mkdocs build --strict
```

Cattura: link rotti, file mancanti, errori YAML. **NON cattura**: 404 gallery images (solo visibili in console browser).

---

## 4. Dev Server per Preview

```bash
./dev.py mkdocs serve   # porta 8002 (evita conflitti con backend 8000, test 8001)
```

---

## 5. Regole di Stile della Documentazione

### 5.1 Tono — Tre registri

| Area | Audience | Registro |
|------|----------|----------|
| `user/`, `admin/`, `faq.md` | Utenti finali | 🟢 Amichevole & guidato — "You", step-by-step |
| `developer/` | Sviluppatori | 🟡 Tecnico ma accessibile — spiega il *perché* |
| `financial-theory/` | Lettori tecnici | 🔴 Specialistico & rigoroso — formule LaTeX |

**Regole trasversali:**
- Scrivere in **inglese** (traduzioni via i18n pipeline)
- Usare **admonitions** (`!!! tip`, `!!! info`, `!!! warning`) per note laterali — mai per contenuto primario
- Tabelle preferite a bullet list quando ci sono ≥3 colonne
- Code blocks con language tag corretto: ` ```python `, ` ```bash `, ` ```mermaid `
- Paragrafo intro 1-2 righe sotto ogni H1

### 5.2 Admonition — Riga vuota obbligatoria (Prettier-safe)

**CRITICO**: inserire SEMPRE una riga vuota tra la direttiva `!!!`/`???` e il corpo indentato.

```markdown
<!-- ✅ CORRETTO — sopravvive a Prettier -->
!!! note "Titolo"

    Contenuto indentato a 4 spazi.

<!-- ❌ SBAGLIATO — Prettier rimuoverà l'indentazione -->
!!! note "Titolo"
    Contenuto indentato a 4 spazi.
```

**Perché**: Prettier usa il parser remark (CommonMark). `!!! note` non esiste in CommonMark → le righe indentate vengono normalizzate → l'indentazione sparisce. Con la riga vuota, Prettier non tocca nulla.

**Check automatici**: `dev.py mkdocs build` avvisa pre-build; `validate_translations.py` check `admonition-empty-line`; `translate_docs.py` inietta nel critic LLM.

### 5.3 Emoji — Heading

| Livello | Regola | Esempio |
|---------|--------|---------|
| H1 (`#`) | **Sempre** 1 emoji | `# 🔐 Authentication` |
| H2 (`##`) | **Sempre** 1 emoji | `## 📊 Dashboard` |
| H3 (`###`) | **Sempre** 1 emoji | `### ⚙️ Parameters` |
| H4+ | Solo se compare in sidebar | `#### 📝 Detail` |

- Mai doppia emoji. Consistenza intra-file e cross-file.
- Bullet list emoji solo quando aggiungono informazione semantica (✅/❌ checklist).

### 5.4 Diagrammi — Mermaid

Tutti i diagrammi sono **Mermaid inline** (no PNG). Usare `subgraph` per raggruppare, `-->` per flusso, `-.->` per opzionale, `==>` per critico.

### 5.5 Alberature — Directory tree

Code block `text` con box-drawing Unicode (`├──`, `└──`, `│`). Max 3 livelli, commento inline `# descrizione` dopo ogni cartella significativa.

### 5.6 Separatori

`---` tra H2 solo in pagine lunghe (>80 righe). Mai tra H3 consecutive.

---

## 6. Pipeline di Traduzione (i18n)

- **Strategia**: `mkdocs-static-i18n` con suffix (`index.en.md`, `index.it.md`)
- **Lingue**: EN (sorgente) → IT, FR, ES
- **LLM**: Aphra workflow (Analyze → Translate → Critique → Refine)
- **Scope**: 90 file sorgente (user + admin + financial-theory + gallery + root). Developer = EN-only.
- **EN-only sections**: `Developer Manual`, `POC UX` (configurato in `EN_ONLY_SECTIONS`)

### Comandi CLI

| Comando | Descrizione |
|---------|-------------|
| `./dev.py mkdocs translate` | Esegui traduzione (con `--file`, `--lang`, `--workers`) |
| `./dev.py mkdocs translate-diff` | Structural diff EN vs traduzioni (con `--issues-only`, `-v`) |
| `./dev.py mkdocs translate-check` | Verifica setup pipeline |
| `./dev.py mkdocs translate-inspect` | Ispeziona artefatti cache (analysis, critique, diff) |
| `./dev.py mkdocs translate-validate` | Validazione offline (indentazione, artefatti, LaTeX) |

### Architettura Pipeline v2

```text
Per ogni file .en.md:
  [1] Analyze (shared)  ─── 1 chiamata, riusata per tutte le lingue
  Per ogni lingua (parallelizzabile con --workers N):
    [2] Search (disabled)  ─── APHRA_WEB_SEARCH=false
    [3] Translate
    [4] Critique  ─── riceve structural diff (13 dimensioni) come dati oggettivi
    [5] Refine
    → _clean_translation() ─── 10 step di pulizia automatica
    → write .XX.md
```

### `_clean_translation()` — 10 step automatici

1. Strip `<translation>` tags
2. Rimuovi "Translator's Notes" (6+ varianti multilingual)
3. Rimuovi glossary block `[N] term: definition`
4. Strip inline `[N]` markers (preserva link markdown)
5. Rimuovi footnote definitions `[^N]: ...`
6. Strip inline footnote references `[^N]`
7. Normalizza doppi spazi
8. Collassa 3+ blank lines → 2
9. Normalizza link interni (`.XX.md` → `.md`)
10. **Fix indentazione admonition** (1 spazio → 4 spazi per MkDocs)

### Structural Diff — 13 dimensioni

Confronto deterministico EN vs traduzione su: heading count/levels, code blocks, link URLs/count, image URLs, admonitions, horizontal rules, bullet lists, numbered lists, table rows, bold markers, line count. Report con dettaglio per-riga (L{n}: src={x} trn={y}).

### Cache

File `.translate-hashes.json`: MD5 del sorgente + lingue tradotte + artefatti (analysis, critique, diff). Skip automatico se MD5 non cambiato.

Per dettagli completi: vedi `mkdocs_src/docs/developer/docs/translation-pipeline.md`.

---

## 7. Relative Links

MkDocs risolve link relativi dalla directory del file. Quando si spostano file in subdirectory, **tutti i link relativi si rompono** (servono più `../`). Usare `mkdocs build --strict` per verificare.

