[REVIEWED 2026-04-24]

# Sub-Plan: Phase 7 Part 3 Closure_2 — Blocco G test coverage

Parent: plan-phase07-transaction-Part3_1_Closure_2.prompt.md (Blocco G)
Data: 24 Aprile 2026 - Stato: IN CORSO
Effort riveduto: ~8h (dopo audit coverage reale 2026-04-24)

## Revisione scope (post-audit 2026-04-24)

Audit (`/tmp/libreFolio_coverage_audit.sh`): ~85% della coverage pianificata
per G.1/G.2 e gia presente in `test_transaction_service.py` (~50 test: Blocco
A atomic + H pairing/promote) e `test_transactions_api.py` (18 test Blocco
B). Anche E.8, I-bis #26/#R6-2, FAProviderKind sono gia coperti altrove.

Conseguenze:

- G.1/G.2 declassati da "scrittura da zero" a "audit + gap-fill".
- Scoperti 3 gap dimenticati nel plan originale -> aggiunti G.6c, G.12, G.13.
- Confermati 5 gap reali -> G.3, G.4, G.5, G.10, G.11 restano P1.

## Scope riveduto

| ID | File target | Area Part3 | Stato | Effort |
|----|-------------|------------|:-----:|:------:|
| G.6 | `test_ohlc_sentinel.py` (nuovo) | F.4 sentinel | DONE 7/7 (2026-04-24) | - |
| G.6b | `test_current_price_bootstrap.py` (services) | F.2/F.3 unit `_extend_ohlc_bounds` | DONE 8/8 (2026-04-24) | - |
| G.6c (NEW) | `test_current_price_persistence.py` (api) | F.2/F.3 side-effect /current | DONE 5/5 (2026-04-24) | - |
| G.11 | `test_asset_prices_export.py` (nuovo) | I.4 export + I-bis #5 round-trip | DONE 5/5 (2026-04-24) | - |
| G.5 | `test_prices_currency_coherence.py` (nuovo) | I.2 hard-reject mismatch | DONE 5/5 (2026-04-24) | - |
| G.10 | `test_asset_currency_change.py` (nuovo) | I.3 PATCH + I-bis #7 HTTP 409 | DONE 4/4 (2026-04-24) | - |
| G.12 (NEW) | `test_prices_sync_delta.py` (nuovo) | I-bis #24 changed_points + cap 500 | DONE 5/5 (2026-04-24) | - |
| G.3 | `test_transactions_validate.py` (nuovo) | Blocco C.1 dry-run | DONE 6/6 (2026-04-24) | - |
| G.4 | `test_events_suggest.py` (nuovo) | Blocco C.2 | DONE 7/7 (2026-04-24) | - |
| G.13 (NEW) | `test_scheduled_investment_param_change.py` (services) | #R6-4 event wipe + tx disconnect | PENDING | 30min |
| G.1 | `test_transaction_service.py` (estendi) | Blocco A/H gap-fill | PENDING audit-only | 30min |
| G.2 | `test_transactions_api.py` (estendi) | Blocco B access matrix gap-fill | PENDING audit-only | 30min |
| G.7 | `scripts/test_runner.py` | tooling | PENDING | 15min |
| G.8/G.9 | meta | coverage report + `./dev.py test all-backend` | PENDING | 30min |

Totale: ~8h.

## Ordine di esecuzione

| Batch | Contenuto | Effort | Razionale |
|-------|-----------|:------:|-----------|
| G-batch1 | G.6b + G.6c + G.11 | ~2h | F.2/F.3 + export/round-trip - bassa complessita, alto valore — **DONE 2026-04-24 (25/25 test PASS)** |
| G-batch2 | G.5 + G.10 + G.12 | ~2.5h | Currency coherence + change flow + I-bis #24 delta - P1 tutti — **DONE 2026-04-24 (14/14 test PASS)** |
| G-batch3 | G.3 + G.4 | ~1.75h | Blocco C endpoints dry-run + events/suggest — **DONE 2026-04-24 (13/13 test PASS)** |
| G-batch4 | G.13 + G.1/G.2 audit | ~1.5h | #R6-4 scheduled + gap-fill residuo |
| G-batch5 | G.7 + G.8 + G.9 | ~45min | Test-runner + validazione finale |

## Commit strategy (1 per batch)

- `test(phase07-G1): OHLC sentinel + F.2/F.3 + prices export round-trip` (G.6 + G.6b + G.6c + G.11)
- `test(phase07-G2): currency coherence + asset currency change + sync delta` (G.5 + G.10 + G.12)
- `test(phase07-G3): transactions validate + events suggest` (G.3 + G.4)
- `test(phase07-G4): scheduled_investment param-change + existing-coverage gap-fill` (G.13 + G.1 + G.2)
- `test(phase07-G5): test runner groups + coverage validation` (G.7 + G.8 + G.9)

## Gap rilevati nell'audit (3 dimenticati)

1. **I-bis #24 FARefreshResult.changed_points**: nessun test esistente.
   Contratto: (a) campo popolato con delta real (new+changed, non fetched
   identici), (b) None quando oltre `CHANGED_POINTS_PAYLOAD_CAP=500`,
   (c) idempotent no-op sync -> `changed_points=[]`. -> G.12.

2. **F.2/F.3 side-effect persistente di /current**: documentato in
   `wiki/concepts/prices-current-side-effect.md` ma mai testato end-to-end.
   -> G.6c.

3. **#R6-4 scheduled_investment param-change**: retest manuale passato ma
   nessuna protezione di regressione. -> G.13.

## Copertura preesistente confermata (no-op)

- Blocco A atomic + Blocco H pairing/promote: ~50 test in `test_transaction_service.py`.
- Blocco B api: 18 test in `test_transactions_api.py`.
- E.8 target_currency: 7 test in `test_events_target_currency.py`.
- I-bis #26 + #R6-2: 15+ test in `test_synthetic_yield_integration.py`.
- FAProviderKind (Batch 2 part4b): 20 test in `test_provider_core_cache.py`.
- Blocco H api: `test_transfer_promotion.py` (3 test).

## Cross-link

- Parent: plan-phase07-transaction-Part3_1_Closure_2.prompt.md
- devWiki: `wiki/concepts/prices-current-side-effect.md`
- Audit log: `/tmp/libreFolio_coverage_audit.log`

