# Plan: FX Testing & Cleanup — E2E, Unit Tests, i18n Audit, Gallery

**Data creazione**: 12 Marzo 2026
**Status**: 📋 ACCENNATO — da dettagliare a sviluppi completati
**Priorità**: Alta (zero copertura E2E FX attualmente)
**Stima**: ~3 giorni
**Dipendenze**: `plan-fxConversionChain.prompt.md` + `plan-fxDetailPageRedesign.prompt.md` completati
**Riferimenti**:
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` Steps 1, 9 — test pendenti
- `phases/phase-05-subplan/05FX_outofdate_plan/phase05-pending-audit.md` §C (Testing/Cleanup)

---

## Contesto

I test E2E e unit test FX devono essere scritti DOPO il completamento di tutti gli sviluppi (chain, detail page). La gallery screenshot dipende dai test E2E. L'ordine è: sviluppi → test → gallery.

## Task pendenti (da vecchio master plan)

### C1. Test unitari — TimeSeriesStore e EditBuffer
- Implementazione ✅, test mancanti
- `src/lib/stores/TimeSeriesStore.ts` — test: getRange, getMissingIntervals, merge, invalidate
- `src/lib/stores/EditBuffer.ts` — test: add, update, remove, getAll, getCsvLines, clear

### C2. i18n Audit — ~50 chiavi FX
- Molte chiavi già aggiunte nei sub-plan
- Fare audit per chiavi mancanti (chain, detail page, nuovi componenti)
- Usare `./dev.py i18n add` + `./dev.py i18n update`
- Verificare completezza in EN/IT/FR/ES

### C3. E2E test Playwright — ~25 scenari
- Zero copertura E2E FX al momento
- Scenari: griglia card, filtri, chart, edit, sync, CRUD routes, chain config, dark mode
- Da scrivere in `frontend/tests/fx/`
- Vedi elenco dettagliato nel vecchio master plan §E2E Test Ideas

### C4. Gallery screenshot FX
- Dipende da E2E completati
- Light/dark mode, 4 lingue (EN/IT/FR/ES)
- Integrare nella gallery MkDocs esistente

### C5. Test cambio ordine provider (ora "route")
- 5 scenari end-to-end documentati nel vecchio master plan §Test Futuri
- Swap ordine, rimuovi, aggiungi+riordina, rimuovi tutti-1, resilienza

### C6. TODO_FUTURI.md updates
- Aggiornare sezione Cross-Rate (ora implementata nel plan-fxConversionChain)
- Aggiungere roadmap traduzioni MkDocs progressive

### C7. Aggiornare phases/phase-05-fx.md
- Riferimento al nuovo set di plan

---

## Note

L'ordine di esecuzione DEVE essere: C1 (unit test) → C2 (i18n) → C3 (E2E) → C4 (gallery) → C5-C7 (cleanup).
I test E2E non possono essere scritti prima che il frontend sia stabile.

