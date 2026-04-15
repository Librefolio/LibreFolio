# LibreFolio — Project Knowledge Base

> **Scopo**: fornire agli agenti AI un contesto strutturato e modulare sul progetto LibreFolio.  
> Ogni file copre un dominio specifico. Leggere **questo file per primo**, poi caricare i sotto-file pertinenti al task corrente.

---

## 🎯 Cos'è LibreFolio

LibreFolio è un **portfolio tracker finanziario self-hosted e open-source** — alternativa a Ghostfolio. Supporta asset tradizionali (ETF, azioni, obbligazioni, crypto), tassi di cambio multi-provider, asset management con analisi tecnica (EMA, MACD, RSI, Bollinger), e import da 11+ broker.

- **Privacy**: dati sul proprio server
- **Multi-utenza**: Owner/Editor/Viewer per broker condivisi
- **Multi-lingua**: UI in EN/IT/FR/ES (840+ chiavi), documentazione tradotta via LLM
- **Repository**: https://github.com/Alfystar/LibreFolio

---

## 🏗️ Tech Stack

| Layer | Tecnologia | Dettagli |
|-------|-----------|----------|
| **Backend** | Python 3.13 + FastAPI | SQLModel/SQLite, Alembic, Pipenv |
| **Frontend** | SvelteKit 2 + Svelte 5 | Tailwind CSS 4, ECharts 6, Zodios, Playwright |
| **Docs** | MkDocs Material | i18n (suffix strategy), Mermaid, LaTeX (KaTeX) |
| **Deploy** | Docker single-image | Backend serve frontend come file statici |
| **CLI** | `dev.py` | Entry point unico per tutto → vedi `04_devpy_reference.md` |

---

## 📁 Struttura Alto Livello

```text
LibreFolio/
├── backend/                    # Python FastAPI → vedi 01_backend.md
├── frontend/                   # SvelteKit SPA → vedi 02_frontend.md
├── mkdocs_src/                 # Documentazione → vedi 03_documentation.md
├── scripts/                    # CLI tools (importati da dev.py)
├── dev.py                      # CLI principale → vedi 04_devpy_reference.md
└── LibreFolio_developer_journal/
    ├── knowledge_base/         # ← QUESTO FILE
    └── RoadmapV4_UI/           # Piani attivi e archiviati
```

---

## 📐 Scelte Progettuali Chiave

1. **Calcoli solo nel Backend** — il frontend è pura presentazione
2. **FIFO a Runtime** — matching costi calcolato on-demand, non persistito
3. **Provider Registry Pattern** — auto-discovery per FX, Asset e BRIM providers con `params_schema` per form dinamici
4. **Multi-Provider con Fallback** — FX rates da ECB→FED→BOE→SNB + MANUAL sentinella
5. **Svelte 5 Runes** — `$state`, `$derived`, `$effect` nei componenti nuovi
6. **Zodios API Client** — tipi da OpenAPI, validazione Zod runtime
7. **Data Separation prod/test** — cartelle completamente isolate
8. **E2E Test Gallery** — screenshot automatici per docs (light/dark × desktop/mobile)
9. **Signal Library** — 10 segnali tecnici/analitici (EMA, MACD, RSI, Bollinger, AssetComparison, Measure…) calcolati in O(N) nel frontend
10. **Dual View** — card grid + DataTable per Assets e FX, toggle persistito in localStorage
11. **Smart Search Multi-Provider** — ricerca parallela su yfinance + JustETF + CSS Scraper con auto-fill form

---

## 📊 Stato Progetto (Aprile 2026)

| Fase | Status | Contenuto |
|------|--------|-----------|
| Phase 0-3 | ✅ | Setup, Auth, Layout, Settings |
| Phase 4 | ✅ | Brokers, Files, Component Library |
| Phase 5 | ✅ | FX Management, Charts, Signals, i18n Docs |
| Phase 6 | 🚧 | Asset Management (Step 1-4 completati, detail page + test + docs in corso) |
| Phase 7 | 📋 | Transactions + BRIM Import UI |
| Phase 8 | 📋 | Dashboard con KPI |
| Phase 9 | 📋 | Polish & Responsive finale |

---

## 📚 File di Questa Knowledge Base

| File | Quando leggerlo |
|------|----------------|
| [`01_backend.md`](LibreFolio_developer_journal/knowledge_base/01_backend.md) | Task su API, DB, services, providers, test backend |
| [`02_frontend.md`](LibreFolio_developer_journal/knowledge_base/02_frontend.md) | Task su pagine, componenti, stores, charts, i18n |
| [`03_documentation.md`](LibreFolio_developer_journal/knowledge_base/03_documentation.md) | Task su MkDocs: scrittura docs, stile, emoji, admonition, traduzione |
| [`04_devpy_reference.md`](LibreFolio_developer_journal/knowledge_base/04_devpy_reference.md) | Usare `dev.py`: command tree completo, scenari comuni |
| [`05_project_conventions.md`](LibreFolio_developer_journal/knowledge_base/05_project_conventions.md) | Convenzioni: lingua, naming, test users, dark mode, async I/O rule |
| [`06_testing_backend.md`](LibreFolio_developer_journal/knowledge_base/06_testing_backend.md) | Creare/eseguire test backend: pytest, API tests, mock data, coverage |
| [`07_testing_frontend.md`](LibreFolio_developer_journal/knowledge_base/07_testing_frontend.md) | Creare/eseguire test frontend: Playwright E2E, fixtures, gallery |
| [`08_i18n_duplicates.md`](LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md) | Duplicati i18n: strategia, gruppi accettati, regole per nuove chiavi |

---

## ⚠️ Regole Fondamentali

- **Usa SEMPRE `./dev.py`** per operazioni complesse — non comandi manuali
- **No backward compatibility** — pulisci invece di mantenere legacy
- **Codice in inglese** — commenti, docstrings, variabili
- **UI multilingue** — solo interfaccia grafica in EN/IT/FR/ES
- **Edit > Rewrite** — preferisci modifiche puntuali per evitare regressioni

