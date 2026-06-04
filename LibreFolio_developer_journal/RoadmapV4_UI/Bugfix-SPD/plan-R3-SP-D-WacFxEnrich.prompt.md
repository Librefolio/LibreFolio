# Plan: R3-SP-D-WacFxEnrich — WAC FX Missing Pairs UX + Backend Date Enrichment

**Date**: 3 Giugno 2026  
**Status**: ✅ DONE (2026-06-04, Phase 3 completata)  
**Priority**: P1  
**Parent**: [`plan-R3-SP-D-WacCurrencyFix.prompt.md`](./plan-R3-SP-D-WacCurrencyFix.prompt.md)  
**Origin**: Walktest manuale post-WacCurrencyFix — issue message illeggibile + mancano date nel backend

---

## 🎯 Obiettivo

1. **Frontend**: rendere il messaggio `wacFxUnavailable` nel banner issue un **pulsante styled** che apre la FxSyncModal
2. **Backend**: arricchire `wac_missing_pairs` con le date specifiche mancanti per ogni pair + fix `currency` nei qualifying TXs
3. **UX**: tooltip FX pulito, modale sync con z-index corretto, auto-validate post-sync, fix blur→manual

---

## Target Situation (finale)

### Banner issue (top del form)

```
❌ Calcolo WAC fallito. [🔄 Sincronizza i tassi FX] o passa alla modalità manuale.
```

- Pulsante styled verde (bg-libre-green/10, icona RefreshCw) inline nella frase
- Click → apre FxSyncModal (z-index = parent + 10, sopra il FormModal)
- Al completamento sync → re-validate automatico (modale resta aperta per vedere risultati)
- Chiusura modale → utente clicca X o fuori

### WacPreviewSection (sotto il campo cost_basis)

```
⚠️ Impossibile calcolare il PMC: tasso FX mancante    [🔄 Sincronizza tassi FX]
• $ 🇺🇸USD / € 🇪🇺EUR — nessun tasso disponibile: 2026-04-15, 2026-04-29
```

- Bottone nel titolo (ml-auto, allineato a destra)
- Chiama stessa `handleSyncFx` del banner (nessun codice duplicato)
- Date effettive visibili (non più count generico)

### Qualifying TXs table — valuta target corretta

- Colonna "Unit cost": `150.00 $ 🇺🇸 USD → 127.33 € 🇪🇺 EUR` (con tooltip FX)
- Colonna "WAC": mostra nella valuta target (EUR, non USD)
- ⚠️ solo se stale (>5 giorni), niente 💱 emoji

### Tooltip FX (posizione bottom)

```
FX: 1 $ 🇺🇸 USD = 0.8489 € 🇪🇺 EUR
📅 2026-04-15 (stesso giorno)
```

- Se days > 0: "(N giorni prima)" in amber
- Se days > 5: riga rossa "⚠️ Tasso non aggiornato"

### Stale FX → Warning (non bloccante)

Il calcolo WAC prosegue anche con tassi stale. Banner giallo avvisa l'utente ma non impedisce il risultato.

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
| **F5** | `currency` nei qualifying TXs = originale, non target | `financial_utils.py` L146: `currency=target_currency` | 5 min | 3 |
| **F6** | Sync button apre FxSyncModal (non sync inline) | Rewrite `handleSyncFx` + FxSyncModal in FormModal | 15 min | 3 |
| **F7** | FxSyncModal z-index sotto il FormModal | Prop `zIndex` in SyncModalBase/FxSyncModal, `zIndex+10` | 10 min | 3 |
| **F8** | Tooltip FX caotico (↳, posizione top) | Redesign pulito, posizione bottom, colori amber/red | 10 min | 3 |
| **F9** | 💱 emoji ridondante nella cella | Rimuovere, tenere solo ⚠️ se stale | 2 min | 3 |
| **F10** | Blur su campo WAC auto → switch a manual | Confronto numerico (non stringa) per locale format | 5 min | 3 |
| **F11** | Dead code WAC in PromoteMergeModal | Rimuovere sezione WAC/props non collegati | 10 min | 3 |
| **F12** | Pulsante WacPreviewSection duplica FxSyncModal | Unica FxSyncModal nel parent, prop `onOpenFxSync` | 10 min | 3 |

### Compatibilità test pre-esistenti

> **Verificato**: i test WAC backend esistenti (`test_wac_inline.py` P16-P28, `test_analytics_wac.py` A1-A8) 
> **NON** asseriscono su `wac_missing_pairs` — usano tutti lo stesso currency (EUR→EUR, no cross-FX).
> Il cambio di tipo da `List[str]` a `List[WACMissingPairInfo]` **non rompe nessun test esistente**.

---

## Piano di Esecuzione

### Fase 1 — Frontend fix immediato (no backend changes) ← 2026-06-03

```
✅ F1  (Stringa i18n semplificata)
✅ F2  (Rimuovere bottone, link cliccabile nel messaggio)
```

> **Note implementazione Fase 1**: Stringhe i18n (4 lingue) splittate in 3 parti: messaggio + link + suffisso. Bottone `tx-form-sync-fx-btn` rimosso, sostituito con `<button>` inline styled underline dentro il `{#each fieldIssues}`. Il rendering speciale è solo per `issue.code === 'wacFxUnavailable'`.

### Fase 2 — Backend enrichment + Frontend date display ← 2026-06-03

```
✅ B2  (Schema WACMissingPairInfo)
✅ B1  (wac_service.py: raccogliere tutte le date)
✅ B3  (Issue params con pair_details)
✅ B5  (Nuovo test: scenario FX missing multi-valuta)
✅ ./dev.py test api transactions-wac → ALL PASSED (P16-P29 OK)
✅ API sync (./dev.py api sync)
✅ B4  (Frontend: tipo aggiornato)
✅ F3  (handleSyncFx: min/max dates dal backend)
✅ F4  (WacPreviewSection: mostrare date per pair)
```

> **Note implementazione Fase 2**: Il test P29 ha richiesto un fix — il target_currency veniva determinato automaticamente come USD (valuta dominante). Il wac_service ora raccoglie TUTTE le date in un `dict[str, list[date]]` e le ritorna come `List[WACMissingPairInfo]`.

### Fase 3 — UX Polish + Bug Fix ← 2026-06-04

```
✅ F5   (Backend: currency=target_currency nei qualifying TXs)
✅ F11  (Rimuovere dead code WAC da PromoteMergeModal)
✅ F8   (Tooltip FX redesign: pulito, bottom, amber/red per stale)
✅ F9   (Rimuovere 💱 emoji dalla cella, tenere solo ⚠️ se stale)
✅ F6   (handleSyncFx → apre FxSyncModal, non sync inline)
✅ F12  (Unica FxSyncModal nel FormModal, WacPreviewSection usa onOpenFxSync)
✅ F7   (zIndex prop in SyncModalBase/FxSyncModal, zIndex+10)
✅ F10  (Fix blur auto→manual: formatDecimalForDisplay string comparison)
✅ F13  (Placeholder campo auto: "auto (⚡ Valida)" tradotto in 4 lingue)
✅ i18n (Nuove chiavi: fxTooltipSameDay, fxTooltipDaysBefore, placeholderAuto in 4 lingue)
```

> **Note implementazione Fase 3**:
> - `financial_utils.py`: `currency=target_currency` (non `tx.original_currency`) → frontend ora vede la freccia USD→EUR
> - PromoteMergeModal: rimossi import WacPreviewSection, props WAC-related, sezione template. Dead code: nessun caller passava i props.
> - `handleSyncFx` non fa più sync inline — prepara pairs+dates e apre `showFxSyncModal`. `onsynced` → re-validate (modale resta aperta). `onclose` → chiude.
> - FxSyncModal unica nel FormModal (non in WacPreviewSection). WacPreviewSection ha prop `onOpenFxSync` che chiama `handleSyncFx` del parent.
> - z-index: `SyncModalBase` + `FxSyncModal` accettano prop `zIndex`, FormModal passa `zIndex + 10`.
> - Tooltip: `FX: 1 $🇺🇸USD = 0.8489 €🇪🇺EUR` + `📅 date (N giorni prima)` in amber se >0, riga rossa se >5.
> - **Blur fix finale**: confronto `formatDecimalForDisplay(currentRaw) === formatDecimalForDisplay(nextRaw)`. Risolve il mismatch tra precisione piena del backend ("170.3261122757978...") e troncamento a 8 decimali del display. Se la rappresentazione visibile non cambia → niente switch a manual.
> - Placeholder auto: `"auto (⚡ Valida)"` tradotto — guida l'utente a cliccare Validate Now.
> - TODO: Enhancement futuro — FxSyncModal potrebbe accettare per-pair date ranges per sync più preciso.

---

## Walktest post-Fase 3

> **Risultato**: ✅ TUTTI I WALKTEST PASSANO (2026-06-04)

| # | Scenario | Risultato |
|---|----------|-----------|
| **W1** | Banner pulsante sync styled verde | ✅ |
| **W2** | WacPreviewSection: date effettive + bottone sync | ✅ |
| **W3** | FxSyncModal sopra FormModal (z-index) | ✅ |
| **W4** | Sync risultati visibili, modale resta aperta, re-validate in background | ✅ |
| **W5** | Chiusura modale → WAC calcolato, banner sparito | ✅ |
| **W6** | Qualifying table: USD → EUR con freccia | ✅ |
| **W7** | Tooltip FX: formato pulito, posizione bottom | ✅ |
| **W8** | Stale: ⚠️ nella cella + tooltip rosso | ✅ |
| **W9** | Focus + blur senza modifica → resta Auto | ✅ |
| **W10** | Modifica ultima cifra → switch Manual | ✅ |
| **W11** | Auto → Manual → Auto: tabella pulita, placeholder "auto (⚡ Valida)" | ✅ |
| **W12** | Same-currency (no cross-FX) → WAC ok | ✅ |
| **W13** | Stale rate 3gg → warning non bloccante | ✅ |

### Fix aggiuntivi post-walktest

- **Anti-bounce bypass per manual**: `useValidateScheduler` ora bypassa `antiBounceMs` per trigger `'manual'` (post-sync re-validate era bloccato dall'anti-bounce 10s)
- **Reset previewResult su auto senza externalResult**: quando si torna in auto mode, la tabella qualifying vecchia viene cancellata in attesa del ricalcolo

### Copertura test automatici

| Walktest | Coperto da E2E? | Note |
|----------|-----------------|------|
| W1-W5 (Sync FX flow) | ✅ `tx-wac-fx.spec.ts` | Tests graceful: se FX completo → skip, se missing → verifica sync modal flow |
| W6-W8 (Qualifying table + tooltip) | ✅ `tx-wac-fx.spec.ts` | Verifica rendering tabella, formato valuta, stale banner |
| W9-W11 (Blur/mode switch) | ✅ `tx-wac-mode.spec.ts` | Focus/blur stay auto, edit→manual, toggle clears table, placeholder ⚡ |
| W12-W13 (Same-ccy, stale) | ⚠️ Parziale | Backend tests P16-P29 coprono il calcolo, non la UI |

> **E2E creati (2026-06-04)**:
> - `frontend/e2e/transactions/tx-wac-fx.spec.ts` — 9 test (W1-W8)
> - `frontend/e2e/transactions/tx-wac-mode.spec.ts` — 5 test (W9-W11 + placeholder + validate)
> - Registrati in `scripts/test_runner/_frontend_transaction.py`
> - Comandi: `./dev.py test front-transaction tx-wac-fx` / `tx-wac-mode`

---

## 🔗 Cross-links

- **Parent**: [`plan-R3-SP-D-WacCurrencyFix.prompt.md`](./plan-R3-SP-D-WacCurrencyFix.prompt.md)
- **Grandparent**: [`plan-R3-SP-D-WacCurrency.prompt.md`](./plan-R3-SP-D-WacCurrency.prompt.md)
- **Phase 7 macro**: [`../phases/phase-07-transactions.md`](../phases/phase-07-transactions.md)
