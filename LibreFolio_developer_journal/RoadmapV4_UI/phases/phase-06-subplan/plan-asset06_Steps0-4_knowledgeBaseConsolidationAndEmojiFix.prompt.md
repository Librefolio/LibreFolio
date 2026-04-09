# Plan: Consolidamento Knowledge Base + Emoji Fix + Cleanup

**Status**: ✅ COMPLETATO  
**Data**: 23 Marzo 2026

Riorganizzazione del `welcome_agent` in una knowledge base distribuita multi-file, cleanup delle librerie di test, documentazione della soluzione Prettier/admonition, archiviazione piani completati, e fix delle emoji bandiera su Windows (frontend + docs).

---

## Step 1 — Cleanup librerie di test concorrenti ✅

- ✅ `prettier` installato come devDependency nel root `package.json`
- ✅ File test temporanei `/tmp/fmt-test/` eliminati
- ℹ️ `beautifulsoup4` resta nel Pipfile (usato dal backend `css_scraper.py`); `mdformat` non era mai stato installato

---

## Step 2 — Documentare soluzione admonition nella pagina Translation Pipeline ✅

In `mkdocs_src/docs/developer/docs/translation-pipeline.md`, aggiunta sezione `## Prettier Compatibility`:

- La regola della riga vuota obbligatoria dopo `!!!`/`???`
- Perché (Prettier usa remark/CommonMark, non conosce le admonition MkDocs)
- Il check automatico in `dev.py mkdocs build` (`_check_admonition_empty_lines`)
- Il check nel `validate_translations.py` (`admonition-empty-line`)
- Il check nel `_structural_diff` di `translate_docs.py` (feedback al critic LLM)

---

## Step 3 — Ristrutturare Welcome Agent in knowledge base distribuita ✅

Creata cartella `LibreFolio_developer_journal/knowledge_base/` con 6 file:

| File | Contenuto |
|------|-----------|
| `00_project_overview.md` | Scopo progetto, tech stack (Python/FastAPI, SvelteKit, MkDocs), architettura alto livello, link ai sotto-file. ~80 righe. |
| `01_backend.md` | Struttura backend: modelli DB, API, services, providers (FX, Asset, BRIM), auth, test. Estratto dal welcome_agent attuale §Backend + tabella "Dove trovare cosa". |
| `02_frontend.md` | Struttura frontend: routes, componenti (UI/charts/FX/settings), stores, signal library, i18n, E2E tests. Estratto dal welcome_agent §Frontend. |
| `03_documentation.md` | **Ingloba** il contenuto di `mkdocs_src/skill_agent_note.md`: MkDocs config, regole stile (tono, emoji, diagrammi, admonition Prettier-safe), gallery, traduzione pipeline. |
| `04_devpy_reference.md` | Documentazione completa di `dev.py`: command tree aggiornato (incluso `mkdocs translate`, `translate-validate`, `translate-diff`, `translate-inspect`), scenari comuni, pattern `register_subparser`. |
| `05_project_conventions.md` | Note sviluppo: no backward compat, codice in inglese, UI multilingue, no migrazioni Alembic, edit > rewrite, test users, dark mode guide. |

**Azioni collaterali**:
- ✅ Eliminato `LibreFolio_developer_journal/RoadMapV1/00_project_welcome_agent.md` (sostituito dalla knowledge base)
- ✅ Eliminato `mkdocs_src/skill_agent_note.md` (inglobato in `03_documentation.md`)

---

## Step 4 — Archiviare piani completati in `phase-05-subplan/` ✅

Spostati questi file da `RoadmapV4_UI/` a `RoadmapV4_UI/phases/phase-05-subplan/`:

| File | Status |
|------|--------|
| `plan-postTranslationBugfixAndDocs.prompt.md` | ✅ COMPLETATO |
| `plan-translationResidualFixAndResize.prompt.md` | ✅ COMPLETATO |
| `plan-mkdocsI18nPipeline.prompt.md` | ✅ COMPLETATO (aggiornare status prima di spostare) |
| `plan-fxDocumentation.prompt.md` | ✅ COMPLETATO (Fase 3 delegata a mkdocsI18n, completata) |
| `plan-markdownFormatter.prompt.md` | ✅ COMPLETATO |
| `prompt-docsPendingWork.md` | ✅ Obsoleto (tutto completato) — eliminare |

Aggiornare i path cross-reference in tutti i file che li citano (grep per i nomi file).

---

## Step 5 — Fix emoji bandiera su Windows ✅

**Problema**: le emoji bandiera (`🇮🇹`, `🇫🇷`, `🇪🇸`, `🇬🇧`) non vengono renderizzate su Windows perché i font di sistema Microsoft (Segoe UI Emoji) non supportano le flag emoji regional indicators. Al loro posto appaiono i codici paese ("IT", "FR", etc.).

**Soluzione**: usare `Noto Color Emoji` di Google come web font per gli elementi che contengono bandiere.

### 5a. Frontend — `frontend/src/app.css` ✅

- ✅ Aggiunto `@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');` in cima al file
- ✅ Creata classe `.emoji-flag { font-family: 'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji', sans-serif; }`
- ✅ Applicata in `LanguageSelector.svelte` (2 span)
- ✅ Applicata in `SearchSelect.svelte` (2 span — copre CurrencySearchSelect)
- ✅ Applicata in `SimpleSelect.svelte` (2 span — copre PreferencesTab, GlobalSettingsTab, ChartSignalsSection)
- ✅ Applicata in `FxCard.svelte` (2 span)
- ✅ Applicata in `FxProviderSelect.svelte` (8 span)

### 5b. Documentazione MkDocs — `mkdocs_src/docs/static/extra.css` ✅

- ✅ Aggiunto `@import` per `Noto Color Emoji` in `extra.css`
- ✅ Aggiunta classe `.emoji-flag` in `extra.css`
- ✅ Applicata classe `emoji-flag` nel selettore lingua in `site-lang-selector.js` (3 span)

### 5c. Fix nei file markdown tradotti

Le bandiere nei file `.md` sono solo nel selettore lingua JS — **non** nei contenuti markdown stessi. Quindi nessun fix necessario nei 215 file `.md`. Le emoji normali (non-bandiera) funzionano su Windows con Segoe UI Emoji.

---

## Further Considerations

1. **`Noto Color Emoji` peso**: il font è ~24MB completo, ma Google Fonts serve solo i subset necessari via `unicode-range`. Per le bandiere, il subset è ~200KB. Se la latenza è un problema, si può self-hostare il subset. Consiglio: **partire con Google Fonts CDN** e valutare dopo.
2. **Scope della classe `.emoji-flag`**: applicarla SOLO ai container bandiera (language selector, currency flags) e NON globalmente — le altre emoji (📊, ⚙️, etc.) funzionano già bene con i font di sistema. Questo evita override indesiderati.
3. **`plan-frontendDevelopment.prompt.md` e `plan-phase05-to-08-upgrade.md`**: sono piani macro IN CORSO (roadmap fasi 5-8). NON spostarli — restano nella root. Aggiornare solo il loro status interno con i riferimenti corretti ai sub-plan spostati.

