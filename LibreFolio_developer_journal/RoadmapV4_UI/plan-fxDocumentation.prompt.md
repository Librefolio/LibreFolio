# Plan: FX Documentation — MkDocs, i18n Globale, Traduzioni

**Data creazione**: 12 Marzo 2026
**Status**: 📋 ACCENNATO — da dettagliare dopo testing
**Priorità**: Media (ultima fase di Phase 5)
**Stima**: ~3 giorni
**Dipendenze**: `plan-fxTestingCleanup.prompt.md` completato (screenshot da E2E)
**Riferimenti**:
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` Steps 7, 8 — interamente pendenti
- `phases/phase-05-subplan/05FX_outofdate_plan/phase05-pending-audit.md` §B (Documentazione)

---

## Contesto

La documentazione MkDocs va completata DOPO i test e gli screenshot. Include: infrastruttura i18n globale, nuove pagine utente, documentazione backend FX, e traduzioni progressive.

## Task pendenti (da vecchio master plan)

### B1-B4. i18n MkDocs Globale (Step 7 del vecchio master)
- Plugin `mkdocs-static-i18n` in `mkdocs.yml` (dipendenza già nel Pipfile)
- Rename ~18 file `.md` → `.en.md` (sezioni traducibili)
- Rinominare `gallery-lang-selector.js` → `site-lang-selector.js`
- Rimuovere check `isGalleryPage()`, aggiungere navigazione tradotta
- Aggiornare `gallery-img-loader.js` per leggere lingua da path URL
- Testare con `./dev.py mkdocs serve`

### B5-B11. Documentazione Utente GUI (Step 8 del vecchio master)
- `user/brokers.en.md` — broker, BRIM, sharing
- `user/files.en.md` — upload, tabella, filtri
- `user/settings.en.md` — profilo, preferenze, password
- `admin/global-settings.en.md` — parametri globali
- `user/fx-rates.en.md` — pagina FX, chart, sync, edit, provider, **chain**
- `user/fx-csv-format.en.md` — formato CSV, esempi, errori
- Aggiornare `user/index.en.md` + nav in `mkdocs.yml`

### B12. Documentazione Backend FX
- Flusso sync con fallback e chain
- Provider MANUAL sentinel pattern
- Nuovo endpoint sync pair-based + route-based config
- SNB provider (JSON API, dati mensili)
- Currency utils (flag emoji, pycountry, babel)
- Traduzione endpoints (parametro `lang`)

### B13. Documentazione Algoritmo DFS Chain (developer docs)
- `developer/fx-chain-algorithm.en.md` — spiegazione del grafo valute-provider
- Vincoli custom (archi non ripetuti, max 2 usi per provider)
- Pseudo-codice DFS con backtracking completo
- Motivazione scelta DFS vs BFS vs librerie shortest-path
- Uso di `graphology` MultiDirectedGraph come struttura dati

### Traduzioni progressive
- Le traduzioni `.it.md`, `.fr.md`, `.es.md` vengono create progressivamente
- Phase 5 include solo l'infrastruttura (plugin, rename, selettore, pagine EN)
- Documentare in TODO_FUTURI.md la roadmap traduzioni

---

## Note

Questo plan è l'ultimo della catena Phase 5 FX. Una volta completato, Phase 5 può essere chiusa.

**Ordine globale di esecuzione Phase 5:**
```
1. plan-fxConversionChain.prompt.md    (chain/route-based)
2. plan-fxDetailPage.prompt.md         (candlestick, edit popup, bidirezionalità)
3. plan-fxTestingCleanup.prompt.md     (E2E, unit test, i18n audit, gallery)
4. plan-fxDocumentation.prompt.md      (MkDocs, docs utente, traduzioni)
```

