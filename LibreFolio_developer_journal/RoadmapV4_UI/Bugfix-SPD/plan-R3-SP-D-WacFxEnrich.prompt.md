# Plan: R3-SP-D-WacFxEnrich — WAC FX Missing Pairs UX + Backend Date Enrichment

**Date**: 3 Giugno 2026  
**Status**: ✅ DONE (2026-06-03)  
**Priority**: P1  
**Parent**: [`plan-R3-SP-D-WacCurrencyFix.prompt.md`](./plan-R3-SP-D-WacCurrencyFix.prompt.md)  
**Origin**: Walktest manuale post-WacCurrencyFix — issue message illeggibile + mancano date nel backend

---

## 🎯 Obiettivo

1. **Frontend**: rendere il messaggio `wacFxUnavailable` nel banner issue un link cliccabile che triggera il sync FX (rimuovere il bottone separato)
2. **Backend**: arricchire `wac_missing_pairs` con le date specifiche mancanti per ogni pair. Il backend deve **continuare** a processare tutte le conversioni anche dopo il primo errore, per raccogliere TUTTI i buchi.

---

## Target Situation (concordata)

### Banner issue (top del form)

**Prima** (rotto):
> ❌ Calcolo WAC fallito: coppia/e FX $ 🇺🇸USD/€ 🇪🇺EUR non disponibile/i. Sincronizza i tassi FX o passa alla modalità manuale.

**Dopo**:
> ❌ Calcolo WAC fallito. <u>Sincronizza i tassi FX</u> o passa alla modalità manuale.

- "Sincronizza i tassi FX" è un **link cliccabile** (stile `text-amber-700 underline cursor-pointer`) che chiama `handleSyncFx()`
- Il **bottone separato** `tx-form-sync-fx-btn` viene **rimosso**
- NO elenco pairs qui — il dettaglio è già nel WacPreviewSection sotto il campo

### WacPreviewSection (sotto il campo cost_basis) — già corretto

> ⚠️ Impossibile calcolare il PMC: tasso FX mancante
> • $ 🇺🇸USD / € 🇪🇺EUR — nessun tasso disponibile (3 date mancanti: 2025-01-15, 2025-02-20, 2025-03-10)

*Nota: le date diventano disponibili dopo Fase 2 backend.*

### Backend `wac_missing_pairs` — nuovo formato

```json
"wac_missing_pairs": [
    {
        "pair": "USD/EUR",
        "dates": ["2025-01-15", "2025-02-20", "2025-03-10"]
    }
]
```

**Invariante backend**: il calcolo si interrompe (ritorna `wac=null`) se ci sono missing pairs, MA deve comunque **provare tutte le conversioni** per raccogliere l'elenco completo dei buchi. NON cortocircuitare al primo errore.

### Sync FX mirato con date

La funzione `handleSyncFx()` oggi usa `start: draft.date, end: draft.date`. Con le date dal backend, potrà passare `start: min(dates), end: max(dates)` per coprire l'intero range necessario.

---

## Gap Analysis

| # | Gap | Dove | Effort | Fase |
|---|-----|------|--------|------|
| **B1** | `wac_service.py` raccoglie solo pair_key, scarta `_dt` | Backend L134-139: accumulare `dict[str, list[date]]` | 10 min | 2 |
| **B2** | Schema `wac_missing_pairs` è `List[str]` | `schemas/wac.py`: nuovo tipo `WACMissingPairInfo` | 5 min | 2 |
| **B3** | Issue params non include date | `transaction_service.py` L1409-1411 | 3 min | 2 |
| **B4** | Frontend WacPreviewSection type `missing_pairs: string[]` | Aggiornare interfaccia a `{pair, dates}[]` + backward compat | 5 min | 2 |
| **B5** | Nessun test backend verifica lo scenario FX missing | Nuovo test in `test_wac_inline.py` che valida il formato arricchito | 15 min | 2 |
| **F1** | Stringa i18n `wacFxUnavailable` troppo densa con pairs inline | `en/it/fr/es.json`: semplificare | 5 min | 1 |
| **F2** | Bottone sync FX separato (brutto, disconnesso dal messaggio) | `TransactionFormModal.svelte`: rimuovere bottone, rendere testo cliccabile | 10 min | 1 |
| **F3** | `handleSyncFx` usa date fisse `draft.date` | Dopo B1-B3: usare `min/max(dates)` dal backend | 5 min | 2 |
| **F4** | WacPreviewSection mostra date per pair (arricchimento) | Template: aggiungere date dopo pair name | 5 min | 2 |

### Compatibilità test pre-esistenti

> **Verificato**: i test WAC backend esistenti (`test_wac_inline.py` P16-P28, `test_analytics_wac.py` A1-A8) 
> **NON** asseriscono su `wac_missing_pairs` — usano tutti lo stesso currency (EUR→EUR, no cross-FX).
> Il cambio di tipo da `List[str]` a `List[WACMissingPairInfo]` **non rompe nessun test esistente**.
>
> Serve però un **nuovo test** (B5) che esercita lo scenario multi-valuta senza FX rate,
> verificando che il response contenga `wac_missing_pairs[].pair` e `wac_missing_pairs[].dates`.

---

## Piano di Esecuzione

### Fase 1 — Frontend fix immediato (no backend changes)

```
✅ F1  (Stringa i18n semplificata)                      ← 2026-06-03
  ↓
✅ F2  (Rimuovere bottone, link cliccabile nel messaggio)  ← 2026-06-03
```

> **Note implementazione Fase 1**: Stringhe i18n (4 lingue) splittate in 3 parti: messaggio + link + suffisso. Bottone `tx-form-sync-fx-btn` rimosso, sostituito con `<button>` inline styled underline dentro il `{#each fieldIssues}`. Il rendering speciale è solo per `issue.code === 'wacFxUnavailable'`.

### Fase 2 — Backend enrichment + Frontend date display

```
✅ B2  (Schema WACMissingPairInfo)                      ← 2026-06-03
  ↓
✅ B1  (wac_service.py: raccogliere tutte le date)      ← 2026-06-03
  ↓
✅ B3  (Issue params con pair_details)                  ← 2026-06-03
  ↓
✅ B5  (Nuovo test: scenario FX missing multi-valuta)   ← 2026-06-03
  ↓
✅ ./dev.py test api transactions-wac → ALL PASSED      ← P16-P29 OK
  ↓
✅ API sync (./dev.py api sync)                         ← 2026-06-03
  ↓
✅ B4  (Frontend: tipo aggiornato)                      ← 2026-06-03
  ↓
✅ F3  (handleSyncFx: min/max dates dal backend)        ← 2026-06-03
  ↓
✅ F4  (WacPreviewSection: mostrare date per pair)      ← 2026-06-03
```

> **Note implementazione Fase 2**: Il test P29 ha richiesto un fix — il target_currency veniva determinato automaticamente come USD (valuta dominante), evitando la conversione. Risolto passando `cost_basis_override: {code: "EUR", amount: "0"}` per forzare il target a EUR. Il wac_service ora raccoglie TUTTE le date in un `dict[str, list[date]]` e le ritorna come `List[WACMissingPairInfo]`. I test esistenti (P16-P28) continuano a passare senza modifiche.
>
> **⚠️ Fuori pista**: `--verbose` in dev.py test è necessario per vedere i dettagli dei test — annotiamo per dopo: rendere verbose il default.

---

## Walktest post-implementazione

| # | Scenario | Risultato atteso |
|---|----------|------------------|
| **W1** | ADJUSTMENT Apple, Auto, EUR override, no FX rates | Banner: "❌ Calcolo WAC fallito. _Sincronizza i tassi FX_ o passa a manuale." Link cliccabile. |
| **W2** | W1 + click su "Sincronizza i tassi FX" | Sync avviato, ⏳ nel link, poi re-validate |
| **W3** | W1 + guarda WacPreviewSection sotto | Elenco puntato: "USD/EUR — nessun tasso (3 date: ...)" |
| **W4** | Multi-pair (BUY in GBP + cost_basis in JPY) | Backend riporta 2 entries in `wac_missing_pairs` con date distinte |
| **W5** | Tutte le conversioni OK | Nessun errore, WAC calcolato normalmente |
| **W6** | Banner link disabled durante sync | ⏳ visibile, click inibito |

---

## 🔗 Cross-links

- **Parent**: [`plan-R3-SP-D-WacCurrencyFix.prompt.md`](./plan-R3-SP-D-WacCurrencyFix.prompt.md)
- **Grandparent**: [`plan-R3-SP-D-WacCurrency.prompt.md`](./plan-R3-SP-D-WacCurrency.prompt.md)
- **Phase 7 macro**: [`../phases/phase-07-transactions.md`](../phases/phase-07-transactions.md)



