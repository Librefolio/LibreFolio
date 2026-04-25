# Phase 7 — Sub-Plans Index

Questa directory raccoglie i sotto-piani di implementazione per la **Phase 7 (Transactions System)**.

## Piano principale

→ [`phase-07-transactions.md`](../phase-07-transactions.md) — Macro plan ufficiale di Phase 7.

## Struttura per Parte

| Parte | Stato | Contenuto |
|-------|:-----:|-----------|
| **Parte 1** | ✅ DONE | DB & Schema realignment + AssetEvent bulk delete (Apr 2026) |
| **Parte 2** | ✅ DONE (Revisione 2) | BRIM come parser puro — 11 plugin v2 + commit atomico |
| **Parte 3** | ✅ **DONE 2026-04-25** | API consolidation full-bulk + Blocco I currency simplification + I-bis closure (#1..#26) + Blocco G test coverage 87.06% |
| Parte 4 | ⏳ TODO | Pagina `/transactions` DataTable |
| Parte 4b | ⏳ TODO | File Preview System (assorbito da `plan-phase7b-filePreview.md`) |
| Parte 5 | ⏳ TODO | Staging Modal unificata |

> Le cartelle `Parte4/`, `Parte4b/`, `Parte5/` sono pre-create (vuote) e accoglieranno i piani man mano che vengono scritti.

## Sotto-piani archiviati

### Parte 1 — DB & Schema Realignment

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Parte1/plan-phase07-transaction-Part1.md`](./Parte1/plan-phase07-transaction-Part1.md) | Riallineamento DB Transaction↔AssetEvent + bulk delete eventi | ✅ |

### Parte 2 — BRIM Plugin v2

| File | Descrizione | Status |
|------|-------------|:------:|
| [`Parte2/plan-phase07-transaction-Part2.prompt.md`](./Parte2/plan-phase07-transaction-Part2.prompt.md) | BRIM parser puro + commit atomico (Revisione 2 Apr 2026) | ✅ |

### Parte 3 — API Consolidation + Closure chain

Catena di 6 piani, parent + closure + sub-plans. Tutti chiusi 2026-04-25.

| File | Ruolo | Status |
|------|-------|:------:|
| [`Parte3/plan-phase07-transaction-Part3.md`](./Parte3/plan-phase07-transaction-Part3.md) | Parent — API atomic per-broker + events/suggest + blocchi A..I | ✅ |
| [`Parte3/plan-phase07-transaction-Part3_1_Closure.md`](./Parte3/plan-phase07-transaction-Part3_1_Closure.md) | Decisioni terminali Blocco E + coda I-bis pendente + Batch 1..3 | ✅ |
| [`Parte3/plan-phase07-transaction-Part3_1_Closure_2.prompt.md`](./Parte3/plan-phase07-transaction-Part3_1_Closure_2.prompt.md) | Companion: Batch 4 (I-bis #2/#5/#7/#19/#22/#24/#26) + #R6-1..#R6-8 | ✅ |
| [`Parte3/plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart2.prompt.md`](./Parte3/plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart2.prompt.md) | Sub-plan I-bis #22 retest 4.d-part2 | ✅ |
| [`Parte3/plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart3.prompt.md`](./Parte3/plan-phase07-transaction-Part3_1_Closure_2-Batch4dPart3.prompt.md) | Sub-plan #R6-6/#R6-7/#R6-8 + I-bis #5 CSV + #19 cross-link | ✅ |
| [`Parte3/plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`](./Parte3/plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md) | Test coverage Blocco G (G-batch1..7) — backend 57% → **87.06%** | ✅ |

## Riepilogo finale Part 3

| Stage | Coverage backend | Note |
|-------|:----------------:|------|
| Pre-Blocco G (2026-04-24) | ~57% | Baseline pre-coverage push |
| Post G-batch5 (2026-04-24) | 76.05% | 60 nuovi test (G.3..G.13) |
| Post G-batch6 (2026-04-25) | 85.34% | +17 test 0%-functions + fix `e.error_code` |
| Post G-batch7 (2026-04-25) | **87.06%** | +22 test gap-fill + fix `normalize_currency` |

**Bug di produzione scoperti durante i test**: 2
1. `assets.py::market_data_summary/wipe_market_data` — `e.code` → `e.error_code` (HTTP 500 → 404 corretto)
2. `currency_utils.py::normalize_currency` — strict `pycountry.currencies.get(alpha_3=...)` lookup (prima accettava qualsiasi stringa non vuota)

## Plan companion non archiviati

→ [`./plan-phase7b-filePreview.md`](./plan-phase7b-filePreview.md) — assorbito in Parte 4b (manterrà il file fino a quando Parte 4b non sarà scritta).


