# Plan: Pipeline i18n MkDocs con Aphra

**Data creazione**: 21 Marzo 2026
**Status**: 🔄 IN CORSO — Step 1-6.3 completati, Step 6.4 (traduzione pilota) in test con Ollama locale, Step 6.5 (validation script) completato, nav_translations completate per it/fr/es
**Priorità**: Media (ultima fase di Phase 5)
**Stima**: ~2-3 giorni
**Dipendenze**: `plan-fxDocumentation.prompt.md` Fasi 1-2.5 completate ✅, `plan-docsPerfection.prompt.md` completato ✅
**Fonte originale**: `plan-fxDocumentation.prompt.md` → Fase 3

### Scoperte durante implementazione

- **mkdocs.yml nav con suffix strategy**: il `nav:` deve usare path SENZA suffisso lingua (`faq.md` non `faq.en.md`). Il plugin `mkdocs-static-i18n` risolve automaticamente `faq.en.md`, `faq.it.md`, ecc. Usare `.en.md` nel nav causa warning di build e link rotti (404) nelle versioni tradotte.
- **nav_translations**: completate per tutte e 3 le lingue target (it, fr, es) — 129 voci ciascuna. Tutte le label del menu (tabs + sidebar) sono tradotte.
- **Aphra config.toml**: il format atteso è `[openrouter]` + `[short_article]`, non `[llm]`. La funzione `translate()` passa il config path solo a `LLMModelClient` ma NON al workflow → il workflow usa i default hardcoded (Claude Sonnet 4 + Perplexity Sonar = costosi). **Fix**: bypass `aphra.translate()`, chiamata diretta al workflow con `load_config(global_config_path=...)`.
- **Aphra post-processing**: l'output contiene artefatti (tag `<translation>`, marker glossario `[N]`, blocco definizioni in fondo). Serve `_clean_translation()` per pulirli automaticamente.
- **Web search**: Step 2 (Search) usa il plugin `:online` di OpenRouter ($4/1000 risultati) e non è necessario per docs tecniche. Disabilitato di default via `APHRA_WEB_SEARCH=false`.
- **Modelli per ruolo**: Aphra ha 3 ruoli (writer, searcher, critiquer) ciascuno configurabile con un modello diverso via `.env`.
- **Language selector**: implementata Soluzione B ("URL is king + redirect for default") per sincronizzare URL i18n e selettore lingua.
- **--file path resolution**: risolve in 3 modi: path assoluto, relativo a CWD, fallback relativo a `docs/`. Supporta glob patterns (`*.en.md`, `**/*.en.md`).
- **Token estimation**: stima basata su dimensione file × fattore multi-step (~11.3× source tokens). 108 traduzioni totali (36 file × 3 lingue) ≈ 1.26M token.
- **Ollama 9B quality**: il modello 9B locale (`Qwen3.5-9B-Claude`) produce traduzioni con difetti strutturali (parole troncate es. "Critt valute", heading level errati, code block tradotti, sezione "Note del Traduttore" aggiunta). Il 27B è marginalmente migliore. Per qualità production-grade serve Gemini Flash via OpenRouter (~$0.50-1.00 per tutte le traduzioni).
- **Validation script**: creato `validate_translations.py` (Step 6.5) che cross-referenzia `.en.md` con `*.{lang}.md` e rileva: heading count/level mismatch, link persi, code blocks modificati, artefatti (Translator Notes, glossary markers), size ratio anomalo, LaTeX alterato, admonition corrotte. Integrato come `./dev.py mkdocs translate-validate`.
- **_clean_translation() fix**: aggiunto pattern per rimuovere automaticamente la sezione "Note del Traduttore" / "Translator's Notes" (in tutte le varianti linguistiche) che il modello LLM aggiunge in fondo ai file tradotti.
- **Structural diff (translate-diff)**: aggiunto `_structural_diff()` che confronta oggettivamente la struttura markdown EN vs tradotta (13 check: headings, code blocks, links/URL, immagini, admonitions, HR, liste, tabelle, bold, line count). Iniettato come contesto nel Step 4 (Critique) via parametro `glossary`. Comando standalone: `./dev.py mkdocs translate-diff --lang it -v`.
- **Artefatti salvati nel hash cache (v2)**: evoluto `.translate-hashes.json` per salvare per ogni file: analysis (condivisa), e per lingua: critique, structural diff, modelli usati, tempo. Migrazione automatica v1→v2. Comando `./dev.py mkdocs translate-inspect` per consultare.
- **Thinking models + Aphra**: i modelli `*-Reasoning-Distilled` producono `<think>...</think>` blocks prima della risposta. Il parser Aphra fa `str.find()` e non gestisce questo. **Fix**: monkey-patch di `call_model()` che strippa automaticamente i `<think>` blocks dall'output prima che Aphra li parsi.
- **Timeout per step**: aggiunto `_call_with_timeout()` con threading (default 600s, configurabile via `APHRA_STEP_TIMEOUT`). Previene i loop infiniti di reasoning dei thinking models. Il timeout sul Critique NON blocca la traduzione — procede con critica vuota.
- **Retry su Refine**: `_robust_refine()` ritenta fino a 2 volte quando `parse_translation()` fallisce (tag `<improved_translation>` non trovato). Gestisce anche timeout per singolo tentativo.
- **Test pilota 27B fallito**: Analyze 833s, Critique FR 573s, Refine FR fallito (no `<improved_translation>` tag), Critique ES bloccato all'infinito. Il 27B come critiquer è troppo lento su M1 Pro (~2-5 tok/s). Raccomandazione: usare 9B per tutto in locale, oppure cloud per quality.
- **Rate limit retry**: `_call_step()` ora rileva HTTP 429, pausa 90s, retry fino a 5 tentativi (flag `--rate-limit-retries N`). Se esauriti → abort con progresso salvato. Il run successivo riprende da dove si era fermato grazie al cache.
- **HTTP timeout reale**: sostituito threading con `httpx.Timeout` sull'OpenAI client. La connessione viene effettivamente chiusa e Ollama/OpenRouter smette di generare. Default 15 min (`APHRA_STEP_TIMEOUT=900`).
- **Timestamps nei log**: ogni file/lingua mostra `[HH:MM:SS]` di inizio e fine, elapsed in formato adattivo (`42s`, `2m 15s`, `4h 38m 35s`).
- **Scroll preservation**: `site-lang-selector.js` salva `scrollY/scrollHeight` in `sessionStorage` prima del cambio lingua, ripristina al caricamento.
- **Theme/Language sync app↔docs**: `app-sync.js` sincronizza `librefolio-theme` → palette MkDocs Material e `librefolio-locale` → `gallery-lang` al caricamento. `DocsLink.svelte` e `HelpMenu.svelte` leggono `librefolio-locale` per aprire i docs nella lingua corretta dell'app.
- **Traduzione completa (cloud)**: 97/100 file tradotti con `stepfun/step-3.5-flash:free` via OpenRouter in ~4.5h. 3 file falliti per rate limit temporaneo, poi completati al re-run. Costo totale: $0 (modello gratuito).

---

## Contesto

Setup completo della traduzione automatica della documentazione MkDocs in 4 lingue (en, it, fr, es) usando `mkdocs-static-i18n` (strategia **suffix**) e **Aphra** come agente di traduzione LLM (Google Gemini via OpenRouter BYOK).

La lista dei file traducibili viene derivata dal `nav:` di `mkdocs.yml`, escludendo le sezioni `Developer Manual` e `POC UX` (EN-only). Il selettore lingua diventa globale con modalità readonly sulle pagine EN-only.

### File traducibili (35 file)

| Sezione | File | Count |
|---------|------|-------|
| **Root** | `index.md`, `faq.md`, `credits-legal.md` | 3 |
| **User Manual** | `user/index.md`, `user/getting-started.md`, `user/installation.md`, `user/brokers/index.md`, `user/brokers/sharing.md`, `user/files/index.md`, `user/fx/index.md`, `user/fx/add-pair.md`, `user/fx/sync.md`, `user/fx/detail/index.md`, `user/fx/detail/chart.md`, `user/fx/detail/signals.md`, `user/fx/detail/measures.md`, `user/fx/detail/data-editor.md`, `user/fx/detail/provider.md`, `user/fx/chart-settings.md`, `user/misc/image-crop.md` | 17 |
| **Admin Manual** | `admin/index.md`, `admin/cli_tools.md`, `admin/settings.md`, `admin/filesystem.md`, `admin/docker_advanced.md`, `admin/tailscale_exposure.md` | 6 |
| **Financial Theory** | `financial-theory/index.md`, `financial-theory/asset-types.md`, `financial-theory/transaction-types.md`, `financial-theory/day-count.md`, `financial-theory/returns.md`, `financial-theory/technical-indicators.md`, `financial-theory/synthetic-benchmarks.md` | 7 |
| **Gallery** | `gallery/index.md`, `gallery/desktop.md`, `gallery/mobile.md` | 3 |
| **EN-only** (esclusi) | `developer/` (~45 file), `POC_UX/index.md` | — |

### Decisioni architetturali

- **Strategia**: `suffix` → i file coesistono nella stessa cartella (`index.en.md`, `index.it.md`)
- **Aphra**: installato come **dev dependency** Pipenv (`--dev`) da GitHub URL; fork solo quando servirà aggiungere feature custom
- **Cache**: hash MD5 per file → skip file non modificati tra run successivi
- **Selettore lingua**: globale su tutte le pagine, readonly sulle EN-only (grigio, click disabilitato)
- **financial-theory/**: incluso (Gemini gestisce LaTeX), da monitorare nel pilot
- **Script di traduzione**: vive in `mkdocs_src/aphra-pipeline/`, espone `register_subparser()` per dev.py (pattern identico a `scripts/update_js_cache.py`)
- **Lingue target**: derivate da `frontend/src/lib/i18n/index.ts` → `SUPPORTED_LOCALES` = `['en', 'it', 'fr', 'es']`, escludendo `en` (sorgente)

---

## Step 1 — Setup directory `aphra-pipeline/`

**Stima**: ~30 min

> ✅ **Nota**: lo spazio nel nome cartella (`mkdocs_src/ aphra-pipeline`) è già stato fixato manualmente.

### 1.1 Riscrivere `.env`

Il file attuale contiene la chiave raw senza nome variabile. Riscriverlo con formato corretto:

```env
# OpenRouter API Key for Aphra translation pipeline
# Account: alfystar1701@gmail.com
# Key name: Aphra-translate-pipeline
# Setup: OpenRouter BYOK → Google Gemini
OPENROUTER_API_KEY=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
```

### 1.2 Creare `.env.example`

```env
# OpenRouter API Key for Aphra translation pipeline
# See README.md for setup instructions (OpenRouter BYOK + Google Gemini)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 1.3 Creare `.gitignore` locale

```gitignore
# Secrets
.env

# Temporary Aphra config (generated by translate script, contains API key)
config.toml

# Translation cache (local state, not committed)
.translate-hashes.json

# Python
__pycache__/
*.pyc
```

### 1.4 Creare `README.md`

Contenuto in 4 sezioni:

#### A — Panoramica

Cosa fa la pipeline: traduce automaticamente i file `.en.md` della documentazione MkDocs in `it`, `fr`, `es` usando Aphra (agente LLM). I file tradotti (`*.it.md`, `*.fr.md`, `*.es.md`) vengono letti da `mkdocs-static-i18n` per generare il sito multilingue.

#### B — Prerequisiti

1. Aphra installato come dev dependency Pipenv (`pipenv install --dev git+...aphra.git`)
2. File `.env` con chiave OpenRouter (copiare da `.env.example`)
3. Python + Pipenv nell'ambiente LibreFolio

#### C — Guida Setup Chiavi (BYOK OpenRouter + Google Gemini)

Passo-passo completo:

1. **Ottenere API key Google Gemini**: Andare su [Google AI Studio](https://aistudio.google.com/) → "Get API key" → creare chiave in un progetto
2. **Creare account OpenRouter**: Registrarsi su [OpenRouter.ai](https://openrouter.ai/)
3. **Inserire chiave Google in OpenRouter (BYOK)**: Dashboard → Keys → Integrations/BYOK → provider Google → incollare chiave Gemini → salvare
4. **Generare chiave API OpenRouter**: Keys → "Create Key" → nome "MkDocs Translation Pipeline" → copiare (inizia con `sk-or-v1-`)
5. **Configurare `.env` locale**: Creare `.env` da `.env.example`, incollare la chiave OpenRouter

#### D — Uso

```bash
# Tradurre tutto (skip file non modificati)
./dev.py mkdocs translate

# Tradurre solo italiano e francese
./dev.py mkdocs translate --lang it --lang fr

# Forzare ri-traduzione (ignora cache hash)
./dev.py mkdocs translate --force

# Tradurre file specifici
./dev.py mkdocs translate --file user/getting-started.en.md --file faq.en.md --lang it

# Dry run (mostra cosa farebbe senza tradurre)
./dev.py mkdocs translate --dry-run
```

---

## Step 2 — Installare Aphra come dipendenza dev Pipenv

**Stima**: ~30 min

### 2.1 Installare Aphra

Aphra **non è pubblicato su PyPI**. Il suo README suggerisce `pip install .` da un clone locale, ma Pipenv supporta l'installazione diretta da URL GitHub.

Trattandosi di uno strumento per sviluppatori (traduzione docs), va installato come **dev dependency**:

```bash
pipenv install --dev git+https://github.com/DavidLMS/aphra.git#egg=aphra
```

Questo aggiunge in `Pipfile` sotto `[dev-packages]`:
```toml
[dev-packages]
aphra = {git = "https://github.com/DavidLMS/aphra.git"}
```

### 2.2 Verificare funzionamento

```bash
pipenv run aphra --help
# oppure
pipenv run python -c "import aphra; print(aphra.__version__)"
```

### 2.3 Fork futuro

**Non forkare Aphra adesso.** Il fork sarà necessario solo quando vorremo aggiungere feature custom (es. preservazione LaTeX, prompt personalizzati). A quel punto:

1. Fork `DavidLMS/aphra` → `Alfystar/aphra`
2. Clone in `LibreFolio_subRepo/aphra` (come `justetf-scraping`)
3. Aggiornare Pipfile: `aphra = {git = "https://github.com/Alfystar/aphra.git"}` (oppure `{path = "../LibreFolio_subRepo/aphra", editable = true}` per sviluppo locale)

### 2.4 Verifica CLI/API

Testare che Aphra si possa invocare:
- Se espone un CLI: `pipenv run aphra "English" "Italian" input.md output.md`
- Se espone solo API Python: creare un wrapper minimale in `mkdocs_src/aphra-pipeline/translate_docs.py` che importa e invoca programmaticamente

---

## Step 3 — Configurare `mkdocs-static-i18n` in mkdocs.yml

**Stima**: ~30 min

### 3.1 Aggiungere blocco `plugins:`

In `mkdocs_src/mkdocs.yml`, **prima** di `extra_javascript:`, aggiungere:

```yaml
plugins:
  - search
  - i18n:
      docs_structure: suffix
      default_language: en
      languages:
        - locale: en
          name: English
          default: true
          build: true
        - locale: it
          name: Italiano
          build: true
        - locale: fr
          name: Français
          build: true
        - locale: es
          name: Español
          build: true
```

> **Nota**: `search` va dichiarato esplicitamente quando si aggiunge `plugins:`, altrimenti viene disabilitato.

### 3.2 Verificare build

```bash
cd mkdocs_src && pipenv run python -m mkdocs build --strict
```

A questo punto il build deve funzionare normalmente — il plugin con suffix strategy tratta i file `*.md` (senza suffisso lingua) come default language.

---

## Step 4 — Rinominare file traducibili in `*.en.md`

**Stima**: ~1 ora

### 4.1 Script di rename

Creare uno script bash temporaneo o usare un loop:

```bash
cd mkdocs_src/docs

# Root files
for f in index.md faq.md credits-legal.md; do
  mv "$f" "${f%.md}.en.md"
done

# User Manual (17 files)
for f in user/index.md user/getting-started.md user/installation.md \
         user/brokers/index.md user/brokers/sharing.md \
         user/files/index.md \
         user/fx/index.md user/fx/add-pair.md user/fx/sync.md \
         user/fx/detail/index.md user/fx/detail/chart.md user/fx/detail/signals.md \
         user/fx/detail/measures.md user/fx/detail/data-editor.md user/fx/detail/provider.md \
         user/fx/chart-settings.md user/misc/image-crop.md; do
  mv "$f" "${f%.md}.en.md"
done

# Admin Manual (6 files)
for f in admin/index.md admin/cli_tools.md admin/settings.md \
         admin/filesystem.md admin/docker_advanced.md admin/tailscale_exposure.md; do
  mv "$f" "${f%.md}.en.md"
done

# Financial Theory (7 files)
for f in financial-theory/index.md financial-theory/asset-types.md \
         financial-theory/transaction-types.md financial-theory/day-count.md \
         financial-theory/returns.md financial-theory/technical-indicators.md \
         financial-theory/synthetic-benchmarks.md; do
  mv "$f" "${f%.md}.en.md"
done

# Gallery (3 files)
for f in gallery/index.md gallery/desktop.md gallery/mobile.md; do
  mv "$f" "${f%.md}.en.md"
done
```

### 4.2 Aggiornare `nav:` in mkdocs.yml

Con `docs_structure: suffix`, il `nav:` deve usare path **senza** suffisso lingua. Il plugin risolve automaticamente `faq.en.md`, `faq.it.md`, ecc.

```yaml
nav:
  - Home: index.md           # ← risolve index.en.md / index.it.md
  - FAQ: faq.md              # ← risolve faq.en.md / faq.it.md
  - User Manual:
      - Overview: user/index.md
      - Getting Started: user/getting-started.md
      # ... tutti i 17 file (senza .en)
  - Admin Manual:
      - Overview: admin/index.md
      # ... tutti i 6 file (senza .en)
  - Financial Theory:
      - Overview: financial-theory/index.md
      # ... tutti i 7 file (senza .en)
  - Developer Manual:        # ← INVARIATO (restano .md, EN-only)
      - Overview: developer/index.md
      # ...
  - Gallery:
      - Overview: gallery/index.md
      # ... tutti i 3 file (senza .en)
  - POC UX: POC_UX/index.md  # ← INVARIATO (resta .md, EN-only)
  - Credits & Legal: credits-legal.md
```

> ⚠️ **IMPORTANTE**: NON usare `index.en.md` nel nav — causa warning di build e link 404 nelle versioni tradotte.

### 4.3 Verificare build + cross-link

```bash
cd mkdocs_src && pipenv run python -m mkdocs build --strict
```

I link tra sezioni tradotte e EN-only devono funzionare. Il plugin `mkdocs-static-i18n` gestisce il fallback: se manca `*.it.md`, serve `*.en.md`.

**Attenzione**: i link relativi nei file `.en.md` che puntano a file `developer/` (che restano `.md`) devono continuare a funzionare. Verificare con build strict.

---

## Step 5 — Globalizzare il language selector

**Stima**: ~2 ore

### 5.1 Rinominare file

`gallery-lang-selector.js` → `site-lang-selector.js`

### 5.2 Rimuovere guardia `isGalleryPage()`

Nella funzione `init()` (riga 216-240):

- Rimuovere `if (!isGalleryPage()) return;`
- Rimuovere `document.body.setAttribute('data-gallery-page', 'true');`
- Eliminare la funzione `isGalleryPage()` (righe 22-24)

### 5.3 Aggiungere rilevamento pagine EN-only

```javascript
// EN-only sections: developer docs and POC UX (not translated)
function isEnOnlyPage() {
    var path = window.location.pathname;
    return path.includes('/developer/') || path.includes('/POC_UX/');
}
```

Nella funzione `init()`, dopo aver creato il selettore:

```javascript
if (isEnOnlyPage()) {
    // Force English and disable selector
    setCurrentLang('en');
    container.classList.add('lang-readonly');
}
```

### 5.4 Aggiornare `setCurrentLang()`

Quando l'utente sceglie una lingua su una pagina traducibile, navigare all'URL i18n corrispondente:

```javascript
function setCurrentLang(lang) {
    localStorage.setItem(STORAGE_KEY, lang);
    window.dispatchEvent(new CustomEvent('gallery-lang-change', {detail: {lang}}));
    
    // Navigate to the i18n URL if not EN-only
    if (!isEnOnlyPage() && lang !== getCurrentLangFromUrl()) {
        // mkdocs-static-i18n generates URLs like /it/user/getting-started/
        // For default language (en), the URL has no prefix
        navigateToLang(lang);
    }
}
```

### 5.5 Rinominare classi CSS

In tutto il file: `gallery-lang-*` → `site-lang-*`.

### 5.6 Aggiornare CSS

Rimuovere:
```css
body:not([data-gallery-page]) .gallery-lang-selector { display: none; }
```

Aggiungere:
```css
.site-lang-selector.lang-readonly {
    opacity: 0.4;
    pointer-events: none;
}
.site-lang-selector.lang-readonly .lang-chevron {
    display: none;
}
```

### 5.7 Aggiornare `gallery-img-loader.js`

La funzione `getCurrentLang()` (riga 73) deve leggere la lingua dal path URL come prima fonte:

```javascript
function getCurrentLang() {
    // 1. Try to extract from URL path (i18n plugin generates /it/, /fr/, /es/)
    var path = window.location.pathname;
    var base = basePath();
    var afterBase = path.substring(base.length);
    var langMatch = afterBase.match(/^\/(it|fr|es)\//);
    if (langMatch) return langMatch[1];
    
    // 2. Fallback to localStorage
    return localStorage.getItem('gallery-lang') || 'en';
}
```

### 5.8 Aggiornare `mkdocs.yml`

```yaml
extra_javascript:
  - javascripts/site-lang-selector.js    # was: gallery-lang-selector.js
  - javascripts/gallery-img-loader.js    # unchanged
```

---

## Step 6 — Script di orchestrazione + integrazione dev.py

**Stima**: ~3 ore

### 6.1 Creare `mkdocs_src/aphra-pipeline/translate_docs.py`

Script Python che vive in `mkdocs_src/aphra-pipeline/` (coerente con la directory pipeline). Espone un `register_subparser()` per l'integrazione con dev.py, seguendo il pattern di `scripts/update_js_cache.py`.

Funzionalità:

1. **Carica `.env`** da `mkdocs_src/aphra-pipeline/.env` (usa `python-dotenv`)
2. **Parsa `mkdocs.yml`** con PyYAML — estrae ricorsivamente i path `.en.md` dal `nav:`, escludendo le sezioni `Developer Manual` e `POC UX`
3. **Lingue target**: derivate da `frontend/src/lib/i18n/index.ts` → `SUPPORTED_LOCALES`. Lo script parsa il file TS con un regex per estrarre le lingue, escludendo `en` (sorgente). Questo garantisce allineamento automatico se si aggiungono lingue in futuro.
4. **Per ogni file × ogni target lang** (it, fr, es):
   - Calcola MD5 del sorgente `.en.md`
   - Confronta con `.translate-hashes.json` (in `mkdocs_src/aphra-pipeline/`). Se hash identico → skip
   - Altrimenti: genera `config.toml` temporaneo con model `google/gemini-2.5-flash` e API key
   - Invoca Aphra (via `pipenv run aphra` o importando programmaticamente)
   - Salva output come `*.{lang}.md` nella stessa directory del sorgente
   - Aggiorna hash in `.translate-hashes.json`
5. **Cleanup**: elimina `config.toml` anche in caso di errore (try/finally)
6. **Istruzioni speciali per Aphra** (nel config o come prompt):
   - Preservare front-matter YAML (`---`)
   - Preservare blocchi HTML/CSS (gallery pages hanno `<div>`, `<style>`)
   - Preservare LaTeX `$...$` e `$$...$$`
   - Preservare admonition syntax MkDocs (`!!! tip`, `??? note`, `!!! info`)
   - Preservare code blocks (` ``` `)
   - NON tradurre nomi propri: LibreFolio, Ghostfolio, Docker, FastAPI, SvelteKit, ecc.
   - NON tradurre anchor IDs `{ #anchor-name }`
7. **Flag CLI** (con supporto multi-valore — sia ripetibili che space-separated):
   - `--lang <lang> [lang ...]` — **`action="extend"`, `nargs="+"`**: accetta sia `--lang it fr` che `--lang it --lang fr`. Le scelte sono le lingue target rilevate da `SUPPORTED_LOCALES` del frontend (attualmente: `it`, `fr`, `es`)
   - `--force` — ignora cache hash, ri-traduce tutto
   - `--file <path> [path ...]` — **`action="extend"`, `nargs="+"`**: accetta sia `--file a.md b.md` che `--file a.md --file b.md` (relativi a `docs/`)
   - `--dry-run` — mostra cosa farebbe senza tradurre

### 6.2 Struttura `.translate-hashes.json`

```json
{
  "user/index.en.md": {
    "md5": "a1b2c3d4e5f6...",
    "last_translated": "2026-03-21T14:30:00Z",
    "langs_done": ["it", "fr", "es"]
  },
  "faq.en.md": {
    "md5": "f6e5d4c3b2a1...",
    "last_translated": "2026-03-21T14:32:00Z",
    "langs_done": ["it"]
  }
}
```

### 6.3 Integrare in `dev.py`

Lo script `mkdocs_src/aphra-pipeline/translate_docs.py` espone `register_subparser(mk_sub)` che dev.py chiama nel blocco mkdocs:

```python
# In dev.py, dopo gli altri mk_sub.add_parser(...):
sys.path.insert(0, str(PROJECT_ROOT / "mkdocs_src" / "aphra-pipeline"))
from translate_docs import register_subparser as register_translate_parser
register_translate_parser(mk_sub)
```

Dentro `translate_docs.py`:

```python
def register_subparser(mk_sub) -> None:
    """Register as sub-command under 'mkdocs' in dev.py."""
    # Detect target languages from frontend SUPPORTED_LOCALES
    target_langs = _detect_target_languages()  # e.g. ['it', 'fr', 'es']
    
    mk_p = mk_sub.add_parser("translate", help="Translate docs via Aphra (LLM agent)")
    mk_p.add_argument("--lang", action="extend", nargs="+", choices=target_langs, metavar="LANG",
                       help=f"Target language(s). Detected from frontend: {target_langs}")
    mk_p.add_argument("--file", action="extend", nargs="+", metavar="PATH",
                       help="File(s) to translate (relative to docs/)")
    mk_p.add_argument("--force", action="store_true",
                       help="Re-translate all files (ignore MD5 cache)")
    mk_p.add_argument("--dry-run", action="store_true",
                       help="Show plan without translating")
    mk_p.set_defaults(func=cmd_translate)
```

> **Nota**: `_detect_target_languages()` parsa `frontend/src/lib/i18n/index.ts` cercando la riga:
> ```
> export const SUPPORTED_LOCALES = ['en', 'it', 'fr', 'es'] as const;
> ```
> Con regex: `SUPPORTED_LOCALES\s*=\s*\[([^\]]+)\]`
> Questo garantisce che se aggiungiamo una lingua al frontend (es. `de`), lo script la rileva automaticamente senza bisogno di aggiornare due posti. Se il file non è leggibile, fallback hardcoded a `['it', 'fr', 'es']`.

### 6.4 Traduzione pilota

Tradurre 3-4 file in `it` come test:

1. `faq.en.md` — semplice, pochi concetti tecnici
2. `user/getting-started.en.md` — step-by-step con screenshot
3. `user/index.en.md` — overview con link interni
4. `financial-theory/returns.en.md` — **test critico**: formule LaTeX `$$...$$`

Verifiche:
- `mkdocs build --strict` — zero warning
- Navigazione lingua funzionante (selettore → switch URL)
- Screenshot gallery corretti nella lingua scelta
- Formule LaTeX renderizzate correttamente
- Link interni cross-sezione funzionanti (user → developer resta EN)

---

## Note implementative

### Ordine di esecuzione critico

```
Step 1 (setup dir)  →  Step 2 (install Aphra)  →  Step 3 (plugin config)
                                                        ↓
                                                   Step 4 (rename files)
                                                        ↓
                                                   Step 5 (language selector)
                                                        ↓
                                                   Step 6 (script + pilot)
```

⚠️ **Step 3 PRIMA di Step 4**: il plugin i18n deve essere attivo prima di rinominare i file, altrimenti il build si rompe perché i path `*.en.md` nel nav non vengono risolti.

### Pattern di integrazione dev.py

Lo script segue lo stesso pattern di `scripts/update_js_cache.py`:
- Funzione `register_subparser()` che riceve il parent subparser (`mk_sub` per mkdocs, non il root `subparsers`)
- dev.py fa `sys.path.insert(0, ...)` e poi importa
- Lo script è autonomamente eseguibile (`if __name__ == "__main__"`) per debug/test rapido

### Rilevamento lingue da frontend

Lo script parsa `frontend/src/lib/i18n/index.ts` cercando la riga:
```
export const SUPPORTED_LOCALES = ['en', 'it', 'fr', 'es'] as const;
```
Con regex: `SUPPORTED_LOCALES\s*=\s*\[([^\]]+)\]`
Questo garantisce che se aggiungiamo una lingua al frontend (es. `de`), lo script la rileva automaticamente senza bisogno di aggiornare due posti.

### nav_translations ✅

Completate per tutte e 3 le lingue target (it, fr, es) — 129 voci ciascuna in `mkdocs.yml`. Tutte le label del menu (tabs + sidebar) sono tradotte correttamente.

### CI/CD (futuro)

Lo script è pensato per esecuzione manuale (`./dev.py mkdocs translate`). Una GitHub Action che triggera su push di file `.en.md` può essere aggiunta in futuro ma NON fa parte di questo piano.

### Monitoraggio LaTeX

I file `financial-theory/` contengono formule LaTeX dense (`$...$`, `$$...$$`). Gemini gestisce bene il markdown, ma va verificato che:
- Le formule non vengano alterate (simboli, variabili, pedici/apici)
- I blocchi `$$...$$` restino su righe separate
- Le variabili matematiche non vengano tradotte (es. `$R_{simple}$` non diventi `$R_{semplice}$`)

Se la qualità è scarsa, i file `financial-theory/` possono essere spostati in EN-only (come `developer/`).

### Gallery pages con HTML

I file `gallery/desktop.md` e `gallery/mobile.md` contengono pesanti blocchi `<div>`, `<img>`, e `<style>` che **non devono essere tradotti**. Le uniche stringhe traducibili sono le descrizioni H3 e i paragrafetti sotto. Aphra va istruito di preservare tutti i tag HTML e tradurre solo il testo visibile in markdown.

### Fork di Aphra

Per ora Aphra si installa as-is come dev dependency via Pipenv da GitHub URL. **Non forkare** finché non ci serve customizzare il codice. Quando servirà:

1. Fork `DavidLMS/aphra` → `Alfystar/aphra`
2. Clone in `LibreFolio_subRepo/aphra`
3. Aggiornare Pipfile: `aphra = {git = "https://github.com/Alfystar/aphra.git"}` (oppure `{path = "../LibreFolio_subRepo/aphra", editable = true}` per sviluppo locale)

---

## Tempo stimato totale

| Step | Stima |
|------|-------|
| 1 — Setup directory | ~30 min |
| 2 — Install Aphra | ~30 min |
| 3 — Plugin config | ~30 min |
| 4 — Rename files | ~1 ora |
| 5 — Language selector | ~2 ore |
| 6 — Script + pilot | ~3 ore |
| **Totale** | **~7.5 ore** |

