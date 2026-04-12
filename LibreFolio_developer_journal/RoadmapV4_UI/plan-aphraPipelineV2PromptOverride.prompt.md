# Plan: Pipeline Aphra v2.2.0 — Prompt Override + Glossario JSON

Sfruttare `prompts_dir` di Aphra v2.2.0 per iniettare istruzioni statiche specifiche per documentazione tecnica MkDocs, e creare un glossario terminologico JSON per-lingua che garantisca coerenza cross-linguistica. Il structural diff resta iniettato a runtime via `{glossary}`.

## Contesto

### Conversazione con il maintainer (DavidLMS)

Dopo aver condiviso con David le nostre customizzazioni (shared analysis, structural diff a 13 dimensioni, post-validation), lui ha implementato in Aphra v2.2.0 esattamente quello che avevamo chiesto:

1. **`prompts_dir`** — Opzione in `config.toml` per puntare a una directory con prompt override
2. **Override completo** — Se `{prompts_dir}/{file_name}` esiste, sostituisce il prompt di default
3. **Append/Prepend** — Se `{prompts_dir}/{base}_append.txt` o `_prepend.txt` esiste, viene aggiunto prima/dopo il prompt di default
4. **Workflow selection** — Possibilità di scegliere il workflow (per ora solo `short_article`, futuro `technical_docs`)
5. **Pipenv support** — Documentato nel README come metodo di installazione

### Architettura attuale della pipeline

```
mkdocs_src/aphra-pipeline/
├── .env                    # API key + model config
├── .env.example
├── .translate-hashes.json  # Cache incrementale (MD5 + artifacts)
├── translate_docs.py       # Orchestratore (1896 righe)
├── validate_translations.py # Validazione offline (986 righe)
└── README.md
```

Il flusso attuale per ogni file:
1. **Analyze** (1×, condiviso tra lingue) — identifica termini chiave
2. **Search** (skippato, `APHRA_WEB_SEARCH=false`)
3. **Translate** — traduzione iniziale
4. **Structural Diff** (nostro, deterministico, 13 dimensioni) — confronto struttura markdown
5. **Critique** — il diff viene iniettato nel parametro `{glossary}` del critico
6. **Refine** — traduzione finale
7. **Clean** — rimozione artefatti (translator notes, tag, marker)

### Problema attuale

Il parametro `{glossary}` è usato impropriamente: ci infiliamo il structural diff report, ma il suo scopo semantico nel prompt di Aphra è essere un glossario di termini. Questo funziona ma è fragile e semanticamente scorretto.

### Soluzione

Separare le responsabilità:
- **Istruzioni statiche** → file `_append.txt` nella `prompts_dir` (preserva markdown, niente translator notes, focus finanziario)
- **Glossario terminologico** → file JSON per-lingua con mappature `EN → TARGET` obbligatorie
- **Structural diff** → continua a fluire via `{glossary}` ma insieme al glossario, con formatting distinto e istruzioni al critico su come interpretare le due sezioni

## Prompt di Aphra — Stato attuale (default short_article)

### step1_system.txt (Analyze)
```
You are an expert translator tasked with analyzing and understanding a {source_language} text. Your goal is to identify specific terms, legal {source_language} terms, phrases, and cultural references that may need explanation or adaptation for an {target_language}-speaking audience.
```

### step1_user.txt (Analyze)
Chiede di identificare: idiomatic expressions, legal terms, culturally specific terms, historical/geographical references, wordplay. Output in XML `<analysis><item>...</item></analysis>`.

### step3_system.txt (Translate)
```
You are tasked with translating a {source_language} text into {target_language} while maintaining the author's original writing style.
```

### step3_user.txt (Translate)
Chiede traduzione accurata con preservazione stile, poi `<translation>` tags + `<style_explanation>` section.

### step4_system.txt (Critique)
```
You are a professional translator [...] Your task is to critically analyze a basic {target_language} translation [...] You will also identify terms that would benefit from translator's notes.
```

### step4_user.txt (Critique)
Riceve `{text}`, `{translation}`, `{glossary}`. Chiede analisi di: semantic accuracy, grammar, idiomatic expressions, cultural nuances, terminology. Output in `<translation_critique>` con `<improvements>` + `<translator_notes>`.

### step5_system.txt (Refine)
```
You are tasked with creating an improved {target_language} translation of a {source_language} text.
```

### step5_user.txt (Refine)
Riceve `{text}`, `{translation}`, `{glossary}`, `{critique}`. Chiede traduzione migliorata. **Esplicitamente incoraggia** translator's notes con `[N]` markers e sezione note alla fine. Output in `<improved_translation>`.

---

## Step 1 — Aggiornare Aphra a v2.2.0 nel Pipfile

**File**: `LibreFolio/Pipfile` (riga 57)

**Modifica**: aggiungere `ref = "v2.2.0"` per pinnare la versione:

```toml
# PRIMA
aphra = {git = "https://github.com/DavidLMS/aphra.git"}

# DOPO
aphra = {git = "https://github.com/DavidLMS/aphra.git", ref = "v2.2.0"}
```

Il tag `v2.2.0` esiste nel repo (commit `d5cdd49`, stesso di `main`). Il `pyproject.toml` dice 2.1.0 perché David non ha bumpato il numero — non è un problema, il tag è quello giusto.

**Comando**: `pipenv update aphra`

---

## Step 2 — Creare la directory prompt override e i 5 file

**Struttura**:
```
mkdocs_src/aphra-pipeline/
├── prompts/
│   └── short_article/
│       ├── step1_system_append.txt
│       ├── step1_user_append.txt
│       ├── step3_user_append.txt
│       ├── step4_user_append.txt
│       └── step5_user_append.txt
```

Usiamo **solo `_append`** (niente override completi) così le nostre customizzazioni sopravvivono ad aggiornamenti di Aphra. Le istruzioni base di David restano, noi aggiungiamo le nostre in coda.

---

### `step1_system_append.txt`

Specializza il ruolo dell'analizzatore per documentazione tecnica finanziaria:

```
This text is technical documentation for LibreFolio, an open-source financial portfolio tracker. It is written in MkDocs Material markdown format.

Your analysis should focus on the financial and software domain rather than legal or cultural aspects. Relevant categories include:
- Financial terminology: ETF, FIFO, dividend, portfolio, broker, exchange rate, capital gain, NAV, benchmark, volatility, asset class, allocation
- Software/UI terms: sidebar, toggle, dropdown, modal, tooltip, pagination, API endpoint, provider, fallback
- MkDocs-specific constructs: admonition types (tip, warning, example, note), tabs, snippets

Do NOT identify markdown formatting elements (headings, links, code fences, bold markers) as translatable terms — those are structural and handled separately by an automated validator.
```

### `step1_user_append.txt`

Fornisce esempi concreti di termini da cercare:

```
Focus your analysis on terms where the target language has ambiguous or domain-specific translations. Examples of terms commonly found in this documentation:

- "stale" (referring to outdated market data, not food)
- "asset" (financial instrument, not generic possession)
- "provider" (data source/API integration, not generic supplier)
- "fallback" (automatic backup mechanism)
- "self-hosted" (deployed on user's own server)
- "signal" (technical analysis indicator like EMA, MACD, RSI)

Do NOT flag well-known acronyms (ETF, API, JSON, YAML, HTML) as needing explanation — they are universal in technical contexts.
```

### `step3_user_append.txt`

Istruzioni critiche per il traduttore — preservazione markdown e output pulito:

```
CRITICAL RULES FOR THIS TRANSLATION (technical documentation):

1. PRESERVE ALL markdown formatting exactly as-is:
   - Headings (#, ##, ###, etc.)
   - Code blocks (``` ... ```) — do NOT translate code content
   - Inline code (`...`) — do NOT translate
   - Admonitions (!!! type "Title" / ??? type "Title") — keep the type keyword in English, translate only the quoted title and the indented body
   - Links [text](url) — translate display text, keep URL unchanged
   - Images ![alt](url) — translate alt text, keep URL unchanged
   - Tables, bullet lists, numbered lists — preserve structure exactly

2. Do NOT translate: URLs, file paths, HTML attributes, CSS classes, JSON keys, CLI commands, variable names.

3. Do NOT add Translator's Notes, footnotes, or any content not present in the source.

4. Do NOT include a <style_explanation> section.

5. Preserve emoji characters exactly as they appear (e.g., 🎯, ⚠️, 📊).

6. Output ONLY the translated document inside <translation> tags. Nothing before, nothing after.
```

### `step4_user_append.txt`

Istruzioni per il critico — come interpretare il contenuto del `{glossary}`:

```
IMPORTANT CONTEXT FOR YOUR CRITIQUE:

The <glossary> section above contains TWO types of objective information:

1. **TERMINOLOGY GLOSSARY** — A list of mandatory English → target language term mappings. Verify that the translation uses these EXACT terms consistently throughout the document. Flag any deviation as an improvement.

2. **STRUCTURAL DIFF REPORT** (if present) — An automated, programmatic comparison of the markdown structure between the source and the translation. Each issue listed is an OBJECTIVE FACT (counted headings, links, code blocks, etc.), not a subjective opinion. These structural issues MUST be fixed — prioritize them over stylistic preferences.

Additional rules for critiquing technical documentation:
- Code blocks must be completely untouched (identical content to source).
- MkDocs admonition syntax must be preserved: !!! or ??? followed by the type keyword in English.
- ALL URLs and image paths must be identical to the source document.
- Do NOT suggest adding Translator's Notes — the project explicitly forbids them.
- Focus on terminology consistency (using the glossary mappings) and structural correctness.
```

### `step5_user_append.txt`

Istruzioni per il refinement — output pulito senza artefatti:

```
CRITICAL RULES FOR THE IMPROVED TRANSLATION:

1. Do NOT add Translator's Notes of any kind — no [N] markers, no [^N] footnotes, no notes section at the end.
2. Do NOT add a glossary section at the end of the document.
3. Preserve ALL markdown formatting, code blocks, admonition syntax, links, and images exactly as in the source.
4. Use the term mappings from the TERMINOLOGY GLOSSARY section consistently — these are mandatory, not suggestions.
5. Fix ALL issues listed in the STRUCTURAL DIFF REPORT — those are objective, programmatically verified errors.
6. Output ONLY the final translated document inside <improved_translation> tags. No preamble, no explanation, no notes.
```

---

## Step 3 — Creare il glossario terminologico JSON

**Struttura**:
```
mkdocs_src/aphra-pipeline/
├── glossaries/
│   ├── glossary_it.json
│   ├── glossary_fr.json
│   └── glossary_es.json
```

Formato: JSON con campo `terms` (mappatura `EN → TARGET`) e `_meta` per documentazione.

### `glossary_it.json`

```json
{
  "_meta": {
    "lang": "it",
    "lang_name": "Italian",
    "description": "Mandatory EN → IT term mappings for LibreFolio documentation. LLM translators must use these exact terms."
  },
  "terms": {
    "asset": "asset",
    "portfolio": "portafoglio",
    "broker": "broker",
    "dividend": "dividendo",
    "exchange rate": "tasso di cambio",
    "stale": "obsoleto",
    "capital gain": "plusvalenza",
    "benchmark": "benchmark",
    "allocation": "allocazione",
    "volatility": "volatilità",
    "sidebar": "barra laterale",
    "toggle": "interruttore",
    "dropdown": "menu a tendina",
    "tooltip": "suggerimento",
    "settings": "impostazioni",
    "dashboard": "dashboard",
    "self-hosted": "self-hosted",
    "open-source": "open-source",
    "provider": "provider",
    "fallback": "fallback",
    "overview": "panoramica",
    "transaction": "transazione",
    "holding": "posizione",
    "watchlist": "watchlist",
    "signal": "segnale",
    "owner": "proprietario",
    "editor": "editor",
    "viewer": "visualizzatore"
  }
}
```

### `glossary_fr.json`

```json
{
  "_meta": {
    "lang": "fr",
    "lang_name": "French",
    "description": "Mandatory EN → FR term mappings for LibreFolio documentation."
  },
  "terms": {
    "asset": "actif",
    "portfolio": "portefeuille",
    "broker": "courtier",
    "dividend": "dividende",
    "exchange rate": "taux de change",
    "stale": "obsolète",
    "capital gain": "plus-value",
    "benchmark": "benchmark",
    "allocation": "allocation",
    "volatility": "volatilité",
    "sidebar": "barre latérale",
    "toggle": "interrupteur",
    "dropdown": "menu déroulant",
    "tooltip": "infobulle",
    "settings": "paramètres",
    "dashboard": "tableau de bord",
    "self-hosted": "auto-hébergé",
    "open-source": "open-source",
    "provider": "fournisseur",
    "fallback": "fallback",
    "overview": "aperçu",
    "transaction": "transaction",
    "holding": "position",
    "watchlist": "liste de suivi",
    "signal": "signal",
    "owner": "propriétaire",
    "editor": "éditeur",
    "viewer": "lecteur"
  }
}
```

### `glossary_es.json`

```json
{
  "_meta": {
    "lang": "es",
    "lang_name": "Spanish",
    "description": "Mandatory EN → ES term mappings for LibreFolio documentation."
  },
  "terms": {
    "asset": "activo",
    "portfolio": "cartera",
    "broker": "bróker",
    "dividend": "dividendo",
    "exchange rate": "tipo de cambio",
    "stale": "obsoleto",
    "capital gain": "plusvalía",
    "benchmark": "benchmark",
    "allocation": "asignación",
    "volatility": "volatilidad",
    "sidebar": "barra lateral",
    "toggle": "interruptor",
    "dropdown": "menú desplegable",
    "tooltip": "información emergente",
    "settings": "configuración",
    "dashboard": "panel de control",
    "self-hosted": "autoalojado",
    "open-source": "open-source",
    "provider": "proveedor",
    "fallback": "fallback",
    "overview": "descripción general",
    "transaction": "transacción",
    "holding": "posición",
    "watchlist": "lista de seguimiento",
    "signal": "señal",
    "owner": "propietario",
    "editor": "editor",
    "viewer": "visor"
  }
}
```

---

## Step 4 — Modificare translate_docs.py

### 4.1 Nuove costanti

Aggiungere dopo le costanti esistenti (dopo riga ~60):

```python
PROMPTS_DIR = SCRIPT_DIR / "prompts" / "short_article"
GLOSSARIES_DIR = SCRIPT_DIR / "glossaries"
```

### 4.2 Nuova funzione `_load_glossary(target_lang: str) -> str`

Legge il JSON e formatta come testo leggibile dal LLM:

```python
def _load_glossary(target_lang: str) -> str:
    """
    Load terminology glossary for a target language.

    Reads glossaries/glossary_{lang}.json and formats as a readable
    text block for injection into the {glossary} prompt parameter.

    Returns formatted glossary string, or empty string if file not found.
    """
    glossary_file = GLOSSARIES_DIR / f"glossary_{target_lang}.json"
    if not glossary_file.exists():
        return ""

    try:
        data = json.loads(glossary_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ⚠️  Failed to load glossary for {target_lang}: {e}", file=sys.stderr)
        return ""

    meta = data.get("_meta", {})
    lang_name = meta.get("lang_name", target_lang)
    terms = data.get("terms", {})

    if not terms:
        return ""

    lines = [
        f"## TERMINOLOGY GLOSSARY (English → {lang_name})",
        f"Use these exact translations consistently throughout the document:",
        "",
    ]
    for en_term, target_term in terms.items():
        lines.append(f"- {en_term} → {target_term}")

    return "\n".join(lines)
```

### 4.3 Aggiornare `_generate_config_toml()`

Aggiungere `prompts_dir` nella sezione `[short_article]`:

```python
def _generate_config_toml(api_key: str, models: dict) -> None:
    config_content = f"""[openrouter]
api_key = "{api_key}"

[short_article]
writer = "{models['writer']}"
searcher = "{models['searcher']}"
critiquer = "{models['critiquer']}"
prompts_dir = "{PROMPTS_DIR}"
"""
    CONFIG_TOML.write_text(config_content, encoding="utf-8")
```

### 4.4 Aggiornare `_analyze_source()`

Impostare `prompts_dir` nella workflow config PRIMA di chiamare `analyze()`, affinché `step1_*_append.txt` venga applicato:

```python
def _analyze_source(source_text, model_client, models):
    # ...existing code fino a workflow_config...
    workflow_config = workflow.load_config(global_config_path=str(CONFIG_TOML))

    # Ensure prompts_dir is set for step1 append files
    if 'prompts_dir' not in workflow_config:
        workflow_config['prompts_dir'] = str(PROMPTS_DIR)

    # Store prompts_dir on workflow for self.get_prompt()
    workflow._prompts_dir = workflow_config.get('prompts_dir')

    workflow_config['writer'] = models['analyzer']
    # ...rest unchanged...
```

### 4.5 Aggiornare `_translate_one_lang()`

Cambiare la costruzione del `glossary` parametro per includere la terminologia:

```python
def _translate_one_lang(...):
    # ...existing code...

    # Load terminology glossary for this target language
    terminology = _load_glossary(target_lang)

    # ...after Step 3 Translate...

    # Step 3.5: Structural diff
    struct_diff = _structural_diff(source_text, translation)

    # Build combined glossary: terminology + structural diff
    glossary_parts = []
    if terminology:
        glossary_parts.append(terminology)
    if struct_diff:
        glossary_parts.append(struct_diff)
    glossary_combined = "\n\n---\n\n".join(glossary_parts) if glossary_parts else ""

    # Step 4: Critique — pass combined glossary
    critique = _call_step(
        workflow.critique, context, source_text, translation, glossary_combined,
        step_name="Critique",
    )

    # Step 5: Refine — also pass combined glossary
    translated = _robust_refine(
        workflow, context, source_text,
        translation=translation, glossary=glossary_combined, critique=critique,
    )
    # ...rest unchanged...
```

---

## Step 5 — Test incrementale

### Comando

```bash
./dev.py mkdocs translate --file faq.en.md --lang it --force
```

### Checklist di verifica

1. ✅ Il `config.toml` generato contiene `prompts_dir = "..."` nella sezione `[short_article]`
2. ✅ Step 1 Analyze focalizzato su termini finanziari/software (non "legal terms")
3. ✅ Step 3 Translate non produce `<style_explanation>` section
4. ✅ Step 3 Translate non aggiunge Translator's Notes
5. ✅ Step 4 Critique cita sia TERMINOLOGY GLOSSARY che STRUCTURAL DIFF REPORT
6. ✅ Step 5 Refine produce output pulito senza note/footnote/marker
7. ✅ Post-clean (`_clean_translation`) non deve rimuovere quasi nulla (perché il LLM non produce più artefatti)
8. ✅ I termini del glossario (asset, portafoglio, obsoleto, etc.) sono usati coerentemente
9. ✅ `validate_translations.py` non rileva errori sulla traduzione prodotta

### Debug opzionale

Per ispezionare i prompt effettivi inviati al LLM, impostare temporaneamente `log_calls=True` nel `TranslationContext`:

```python
context = TranslationContext(
    model_client=model_client,
    source_language="English",
    target_language=target_name,
    log_calls=True,  # TEMPORARY — remove after testing
)
```

---

## Implementation Log (2026-04-12)

### ✅ Completed

#### Step 1 — Aphra v2.2.0
- Pipfile updated with `ref = "main"` (tag `v2.2.0` = same commit `d5cdd49`)
- `pipenv run pip install --force-reinstall` to get `prompts_dir` support
- Verified: `get_prompt()` now accepts `prompts_dir` parameter ✓
- Verified: `AbstractWorkflow` has `_prompts_dir` and `get_prompt()` ✓

#### Step 2 — Prompt Override Files (REVISED from plan)

**Key decision change:** After the first test run, we switched from `_append` files to **full replacement** for most prompts. Reason: the default Aphra prompts contain instructions that **directly contradict** our requirements (e.g., step5 encourages `[N]` translator notes, step3 asks for `<style_explanation>`, step4 encourages translator notes). An `_append` saying "don't do X" after a prompt saying "do X" is a weak contradiction — full replacement is cleaner.

Final file structure:
```
mkdocs_src/aphra-pipeline/prompts/short_article/
├── step1_system.txt          # FULL REPLACE — financial/software domain focus (removes "legal terms")
├── step1_user_append.txt     # APPEND — domain examples + XML format reminder (original user prompt has correct XML structure)
├── step3_system.txt          # FULL REPLACE — MkDocs technical docs, preserve structure
├── step3_user.txt            # FULL REPLACE — detailed markdown preservation rules, <translation> only, no <style_explanation>
├── step4_system.txt          # FULL REPLACE — no translator notes, structural correctness focus
├── step4_user.txt            # FULL REPLACE — interprets TERMINOLOGY GLOSSARY + STRUCTURAL DIFF in {glossary}, <improvements> only (no <translator_notes>)
├── step5_system.txt          # FULL REPLACE — clean output, no notes
└── step5_user.txt            # FULL REPLACE — zero [N] markers, <improved_translation> clean output
```

Strategy rationale:
- **step1_user**: kept as append because the default user prompt already has the correct `<analysis><item><name>...<keywords>...` XML format that Aphra's `parse_analysis()` expects. We only add domain guidance.
- **All others**: full replacement because default prompts contain instructions incompatible with our use case.

#### Step 3 — Glossary (REVISED from plan)

**Key decision change:** Instead of 3 per-language JSON files, created a **single monolithic** `glossary.json`:
```
mkdocs_src/aphra-pipeline/glossaries/
└── glossary.json     # {"terms": {"asset": {"it": "asset", "fr": "actif", "es": "activo"}, ...}}
```

- 29 terms mapped across 3 languages (it/fr/es)
- `_load_glossary(target_lang)` extracts the relevant language column and formats as readable text for the LLM
- Single source of truth — no duplication across files

#### Step 4 — translate_docs.py Changes

1. **New constants**: `PROMPTS_DIR`, `GLOSSARIES_DIR`
2. **New function**: `_load_glossary(target_lang)` — reads monolithic JSON, formats for LLM
3. **`_generate_config_toml()`** — now includes `prompts_dir = "{PROMPTS_DIR}"` in `[short_article]` section
4. **`_analyze_source()`** — sets `workflow._prompts_dir` so step1 append is applied
5. **`_translate_one_lang()`** — refactored:
   - Loads terminology glossary per target language
   - Builds `glossary_combined` = terminology + search results + structural diff
   - Passes combined glossary to both critique and refine steps
   - New `log_buf` parameter for silent mode (parallel execution)
   - `_log()` helper: prints to stdout or appends to buffer based on mode
6. **Parallelization** — `--workers N` CLI flag:
   - `ThreadPoolExecutor` for per-language translations within each file
   - `log_buf=[]` captures all output per-language silently
   - After all languages complete for a file, prints grouped output in order
   - Sequential mode (`--workers 1`) unchanged — direct print as before
   - Hash cache updates happen after all threads join (thread-safe)

#### Step 5 — Testing

- First test (nemotron-3-super-120b-a12b:free): Analyze returned `NoneType` errors — model too slow/unreliable for free tier
- Second test (same model, before prompt rewrite): Completed with warnings (`<name>` tags not found in analyze output — model not following XML format)
- Translation quality of second test: good (markdown preserved, glossary terms used, no translator notes), but HTML indentation slightly changed
- Model changed to `google/gemma-4-31b-it:free` for reliability
- Multi-file parallel test pending (2 files × 3 langs × 3 workers)

### 📋 Still TODO

- [ ] Run full translation suite and evaluate quality
- [ ] Tune glossary terms based on actual output review
- [ ] Consider `step2_system.txt` override if web search is ever re-enabled
- [ ] Update `plan-aphraPipelineV2PromptOverride.prompt.md` with final test results
- [ ] Update `03_documentation.md` knowledge base with new pipeline architecture
