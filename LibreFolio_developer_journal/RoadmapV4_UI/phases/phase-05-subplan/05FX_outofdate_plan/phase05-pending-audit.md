# Audit Phase 05 FX — Stato Reale e Lavoro Pendente

**Data audit**: 12 Marzo 2026
**Autore**: Audit automatico dai plan files

---

## 🔍 Riepilogo: Lo Status "✅ COMPLETATO" del Master Plan è Fuorviante

Il master plan (`plan-phase05Fx.prompt.md`) ha nell'header:
> **Status**: ✅ COMPLETATO (12 Marzo 2026) — Tutti i sub-plan completati.

Questo si riferisce ai **7 sub-plan** (tutti effettivamente ✅), ma il master plan stesso contiene **Steps 7, 8, 9 interamente pendenti** + task sparsi non completati negli Steps 1, 3, 4, 6. Inoltre `plan-fxUiRefinementsRound2` ha Step 8 segnato `📋 TODO` ma in realtà è stato assorbito e completato.

---

## ✅ Sub-Plan Completati (Lavoro Svolto — Referenza)

| Sub-Plan | File | Completato | Contesto |
|----------|------|------------|----------|
| FX UI Refinements Round 2 | `plan-fxUiRefinementsRound2.prompt.md` | Steps 1-7, 9 ✅; Step 8 assorbito in fxCardRedesign ✅ | Fix visualMap, stale gradient, layout, MeasureOverlay, OrderableList, settings |
| Manual FX Provider | `phases/phase-05-subplan/plan-manualFxProvider.prompt.md` | ✅ (4 Mar) | Provider MANUAL sentinel |
| FxPairAddModal Redesign | `phases/phase-05-subplan/plan-fxPairAddModalRedesign.prompt.md` | ✅ (3 Mar) | Modale Add FX con CurrencySearchSelect |
| Currency Fix + Layout + Flags | `phases/phase-05-subplan/plan-fxCurrencyFixLayoutFlags.prompt.md` | ✅ (4 Mar) | Valute pycountry, flag emoji backend, layout E+ |
| UI Feedback Round 3 | `phases/phase-05-subplan/plan-fxUiFeedbackRound3.prompt.md` | ✅ (4 Mar) | F1-F17 tutti risolti |
| FxCard Redesign + Chart Settings | `phases/phase-05-subplan/plan-fxCardRedesignChartSettings.prompt.md` | ✅ (11 Mar) | Card redesign, signal library, chart settings store, sync fix, overlay, benchmark, baseline segment color |
| Signal Library Expansion | `phases/phase-05-subplan/plan-signalLibraryExpansion.prompt.md` | Steps 1-6 ✅, Step 7 parziale (7A pending) | EMA, MACD, RSI, Bollinger, dual-axis, KaTeX, MkDocs docs |
| FX Sync API Redesign | `phases/phase-05-subplan/plan-fxSyncApiRedesign.prompt.md` | ✅ (12 Mar) | POST pair-based, ErrorBanner→InfoBanner, toast, keyboard nav |

---

## 📋 Lavoro Pendente — Elenco Completo

### A. Codice / Feature (work rimanente da Steps completati)

| # | Task | Origine | Priorità | Note |
|---|------|---------|----------|------|
| A1 | **CandlestickChart.svelte** — completare OHLC sintetizzato + nota "Simulated OHLC" | Master Step 6 | 🟡 Media | Stub creato, da completare |
| A2 | **VolumeBar.svelte** — completare barre Δ% giornaliera (verde/rosso) | Master Step 6 | 🟡 Media | Stub creato, da completare |
| A3 | **EditPopup.svelte** — completare popup numerico + integrazione EditBuffer | Master Step 6 | 🟡 Media | Stub creato, da completare |
| A4 | **Bidirezionalità Edit Mode** — click chart → scroll CSV + open popup; CSV → chart preview; popup → riga CSV | Master Step 4 | 🟡 Media | CsvEditor esiste, manca il wiring bidirezionale |
| A5 | **Signal Library 7A** — Preview pair mode nel ChartSettingsModal: titolo coppia con bandiere + pulsante inversione | signalLibraryExpansion Step 7 | 🟢 Bassa | Solo UX polish, funzionalità core ok |

### B. Documentazione (Steps 7-8 del master plan — interamente pendenti)

| # | Task | Origine | Priorità | Note |
|---|------|---------|----------|------|
| B1 | **i18n MkDocs globale** — plugin `mkdocs-static-i18n` in mkdocs.yml | Master Step 7 | 🟡 Media | Dipendenza già nel Pipfile |
| B2 | **Rename ~18 file** `.md` → `.en.md` (sezioni traducibili) | Master Step 7 | 🟡 Media | Home, FAQ, Getting Started, User, Admin, Tutorials, Gallery, Credits |
| B3 | **Rinominare** `gallery-lang-selector.js` → `site-lang-selector.js` + evoluzione logica | Master Step 7 | 🟡 Media | Rimuovere check isGalleryPage, aggiungere navigazione tradotta |
| B4 | **Aggiornare** `gallery-img-loader.js` per leggere lingua da path URL | Master Step 7 | 🟢 Bassa | Fallback per sincronizzazione lingua |
| B5 | **Scrivere `user/brokers.en.md`** — Come creare broker, significato campi, upload BRIM, sharing | Master Step 8 | 🟡 Media | Con screenshot gallery |
| B6 | **Scrivere `user/files.en.md`** — Upload file, tabella, filtri, BRIM vs statico | Master Step 8 | 🟡 Media | Con screenshot gallery |
| B7 | **Scrivere `user/settings.en.md`** — Profilo, preferenze, password, about | Master Step 8 | 🟡 Media | Con screenshot gallery |
| B8 | **Scrivere `admin/global-settings.en.md`** — Parametri globali, superutente | Master Step 8 | 🟡 Media | Con screenshot gallery |
| B9 | **Scrivere `user/fx-rates.en.md`** — Pagina FX lista+dettaglio, chart, sync, edit, provider | Master Step 8 | 🟡 Media | Richiede screenshot da E2E Phase 5 |
| B10 | **Scrivere `user/fx-csv-format.en.md`** — Formato CSV dettagliato, esempi, errori comuni | Master Step 8 | 🟡 Media | |
| B11 | **Aggiornare `user/index.en.md`** + nav in mkdocs.yml | Master Step 8 | 🟢 Bassa | Dopo creazione pagine |
| B12 | **Documentazione Backend FX** — flusso sync fallback, provider MANUAL, nuova API POST sync, SNB provider, currency utils, traduzione endpoints | Master §Documentazione | 🟡 Media | 6 argomenti da documentare |

### C. Testing & Cleanup (Step 9 del master plan — interamente pendente)

| # | Task | Origine | Priorità | Note |
|---|------|---------|----------|------|
| C1 | **Test unitari** TimeSeriesStore e EditBuffer | Master Step 1 | 🟡 Media | Implementazione ✅, test mancanti |
| C2 | **~50 chiavi i18n** FX aggiuntive in EN/IT/FR/ES | Master Step 9 | 🟡 Media | Molte chiavi già aggiunte nei sub-plan, fare audit per mancanti |
| C3 | **E2E test Playwright** — ~25 scenari (griglia, filtri, chart, edit, sync, dark mode) | Master Step 9 | 🔴 Alta | Nessun E2E test FX ancora scritto |
| C4 | **Gallery screenshot FX** (light/dark, 4 lingue) | Master Step 9 | 🟡 Media | Dipende da E2E |
| C5 | **Test cambio ordine provider** — 5 scenari end-to-end documentati | Master §Test Futuri | 🟡 Media | Swap ordine, rimuovi, aggiungi+riordina, rimuovi tutti-1, resilienza |
| C6 | **Aggiungere cross-rate** a `TODO_FUTURI.md` | Master Step 9 | 🟢 Bassa | "Coming Soon" placeholder già nella UI |
| C7 | **Aggiungere roadmap traduzioni MkDocs progressive** a `TODO_FUTURI.md` | Master Step 9 | 🟢 Bassa | |
| C8 | **Aggiornare `phases/phase-05-fx.md`** con riferimento al master plan | Master Step 9 | 🟢 Bassa | |

---

## 📊 Statistiche

| Categoria | Totale | Dettaglio |
|-----------|--------|-----------|
| **Feature/Code** | 5 | CandlestickChart, VolumeBar, EditPopup, Bidirezionalità Edit, Signal 7A |
| **Documentazione** | 12 | i18n MkDocs (4), pagine utente (6), backend docs (1), nav update (1) |
| **Testing/Cleanup** | 8 | Unit test, i18n audit, E2E (25 scenari), gallery, provider test, TODO updates |
| **TOTALE** | **25 task** | |

### Per priorità:
- 🔴 Alta: 1 (E2E test — zero copertura FX)
- 🟡 Media: 18
- 🟢 Bassa: 6

---

## 📝 Incoerenze Trovate nei Plan (da correggere)

### 1. `plan-phase05Fx.prompt.md` (Master)
- **Header**: dice `✅ COMPLETATO` ma Steps 7, 8, 9 sono interamente `[ ]`
- **Step 3 task "Sync All"**: checkbox `[ ]` ma completato nel sub-plan fxSyncApiRedesign
- **Correzione**: Cambiare status a `🔄 IN CORSO — Sub-plan tutti ✅. Steps 7-9 (Docs, i18n MkDocs, E2E) pendenti`

### 2. `plan-fxUiRefinementsRound2.prompt.md`
- **Step 8**: dice `📋 TODO` ma è stato assorbito e completato in fxCardRedesignChartSettings
- **Header status**: dice `🔄 IN CORSO — Steps 1-7, 9 ✅ completati, Step 8 📋 TODO` ma Step 8 è ✅ (assorbito)
- **Correzione**: Aggiornare Step 8 a `✅ ASSORBITO in fxCardRedesignChartSettings`

### 3. `plan-signalLibraryExpansion.prompt.md`
- **Header**: dice `Steps 6-7 TODO` ma Step 6 è effettivamente `✅` (6A-6E tutti completati)
- **Step 7**: 7B ✅, 7C ✅, solo 7A è pending
- **Correzione**: Aggiornare status a `Steps 1-6 ✅, Step 7 parziale (7A pending)`

### 4. `plan-phase05-to-08-upgrade.md` (Roadmap globale)
- **Header line 5**: dice `🟡 IN CORSO (Pre-work schema completato, Phase 4.8 Sharing GUI da fare)` ma Phase 4.8 è ✅
- **Phase 5 §4 line 256**: dice `⏳ TODO` ma è largamente completato
- **Section 3.5 task checkboxes**: tutti `[ ]` ma Phase 4.8 è ✅
- **Correzione**: Aggiornare header, section 3.5 tasks, Phase 5 status

---

## 🎯 Suggerimento: Ordine di Completamento

```
1. C6, C7, C8 (TODO_FUTURI + riferimenti) ← quick wins, 15 min
2. Correggere incoerenze plan (questo audit) ← 30 min
3. B12 (Documentazione Backend FX) ← importante prima di E2E
4. C1 (Test unitari TimeSeriesStore/EditBuffer) ← veloce, alta qualità
5. C3 (E2E test FX) ← priorità alta, zero copertura
6. A1-A3 (CandlestickChart, VolumeBar, EditPopup) ← feature complete
7. A4 (Bidirezionalità Edit) ← feature complete
8. B1-B4 (i18n MkDocs globale) ← infrastruttura per docs
9. B5-B11 (Documentazione utente GUI) ← dopo infrastruttura i18n
10. C4 (Gallery screenshot) ← dopo E2E
11. A5, C2, C5 ← polish finale
```

