# Recap implementazione — FIFO Engine v5 (proventi D-1, FEE/TAX, metriche nette)

> **Scopo di questo file:** fotografia di *tutto ciò che è stato implementato* per il piano v5, pronto per la
> review congiunta. Companion: [`review-checklist-v5.md`](./review-checklist-v5.md) (decisioni da confermare +
> test manuali). Piano completo: [`implementation-plan-v5.md`](./implementation-plan-v5.md).
>
> **Stato git:** branch `dev`, **NESSUN commit eseguito** (come richiesto — review tutta insieme alla fine).
> Tutte le modifiche sono *unstaged*. Messaggio di commit proposto: `/tmp/libreFolio_commit_fifo_v5.txt`.

---

## 1. Stato per fase

| Fase | Titolo | Stato | Sintesi |
|------|--------|-------|---------|
| 0.1 | Validator condiviso CREATE/UPDATE segno FEE/TAX | ✅ | Regola di segno applicata anche in UPDATE (stato finale normalizzato), non solo in CREATE. |
| 0.2 | Audit segni legacy (script read-only) | ✅ | `audit_transaction_signs.py` diagnostico, nessun CHECK DB. |
| 0.3 | Vincolo DB | ⛔ (deciso NO) | Tutte le scritture passano dall'API → guardia interna nello stage economico. |
| 0.4 | Hardening `quote_base_quantity` | ✅ | Rimossi metodi non-qbq; `TradeValue=|amount|` senza scaling. |
| 1 | Income allocato dal motore (D-1, broker-scope, transfer) | ✅ | `DIVIDEND`/`INTEREST` entrano nel motore; eleggibilità `OpenQty(D-1)`; orphan+DQ. |
| 2 | Contratto unico del motore (`EconomicEvent` native+target) | ✅ | Eventi economici con `native_amount`/`target_amount`; il motore usa `abs(target)`. |
| 3 | FX e preparazione target | ✅ | Service risolve gli FX, converte il pool nativo **una sola volta** (fonte di verità canonica). |
| 4 | Pooling e allocazione FEE/TAX | ✅ | Pool FEE (trade same-day → fallback holding), pool TAX (income → trade → fallback), orphan. |
| 5 | Crossing LONG/SHORT | ✅ | Costo split close/open con `Σ = CostTrade`, closure immutabili. |
| 6 | Audit a 3 livelli | ✅ | `EconomicAllocationGroup` → operations (OPENING/CLOSURE/INCOME/HOLDING) → lot, nativo+target. |
| 7 | Metriche nette + history | ✅ | `net_total_pnl`/`net_total_return`; history netta feed-forward; DTO esteso; enum split. |
| 8 | Status a 3 stati + frontend netto/DQ | ✅ | `analysis_status` COMPLETE/DEGRADED/FAILED; colonne+modal+gantt+banner; i18n ×4. |
| 9 | Portfolio Engine + riconciliazione | 🟡 metà | **FIFO-half fatto** (conservation lock test). **Portfolio-half RINVIATO** alla review. |

Dettaglio narrativo per fase: vedi le note `> **✅ FATTO**` / `> **🟡 PARZIALE**` inline nel piano
(§Fase 0→9 di `implementation-plan-v5.md`).

---

## 2. File modificati (diffstat reale)

```
 backend/app/schemas/portfolio.py                   |  87 ++-     DTO: enum split, campi netti, audit, orphan
 backend/app/schemas/transactions.py                | 237 +++++-- validator condiviso CREATE/UPDATE segno FEE/TAX
 backend/app/services/fifo_lot_engine.py            | 668 ++++++- CORE: economic stage, pooling, crossing, audit, status
 backend/app/services/lots_analysis_service.py      | 427 ++++++- FX target, cost outputs, metriche nette, history, mapping audit
 backend/app/services/transaction_service.py        |  30 +       aggancio validator condiviso in UPDATE
 backend/test_scripts/test_api/test_transactions_validate.py        |  85 +   test regole segno CREATE/UPDATE
 backend/test_scripts/test_services/.../test_fifo_lot_engine.py     | 635 +   income/fee/tax/crossing/status/conservazione
 backend/test_scripts/test_services/.../test_lots_analysis_service.py |  70 + scenario canonico gross/net + history
 frontend/.../lots/LotCustodyModal.svelte           |  44 +       breakdown netto (gross → −fees → −taxes → net)
 frontend/.../lots/LotGanttChart.svelte             |  15 +       tooltip righe fee/tax + net P&L
 frontend/.../lots/LotsAnalysisPanel.svelte         |   9 +       banner FAILED
 frontend/.../lots/UnifiedLotsTable.svelte          |  85 +       4 colonne nette + footer
 frontend/src/lib/i18n/{en,es,fr,it}.json           |  16 ×4      chiavi modal/tabella/dataQuality/analysisFailed
 mkdocs_src/docs/developer/backend/transactions/fifo_lot_engine.md  |  12 +   doc motore aggiornata
 ── totale: 17 file, +2198 / −270
```

### File nuovi (untracked)
- `backend/test_scripts/test_db/audit_transaction_signs.py` — **mio** (Fase 0.2), script diagnostico read-only.
- `LibreFolio_developer_journal/.../implementation-plan-v5.md` — **mio**, il piano con le note di avanzamento.
- `implementation-recap-v5.md` + `review-checklist-v5.md` — **questi due file** (review).
- `idee_per_grafici.md` (root) — **NON mio**, nota utente, lasciato intatto.

### Non compare in `git status`
- `frontend/src/lib/api/generated.ts` — **gitignored**, rigenerato con `./dev.py api sync`. Su disco riflette
  già i 3 valori enum + tutti i nuovi campi netti/audit (verificato).

---

## 3. Decisioni di design chiave (per capire il diff)

1. **Due metriche "net" diverse e volute** (NON è un bug di doppio conteggio):
   - **value-history:** `net_pnl = pnl − fees − taxes` (esclude income, perché `pnl` esclude income).
   - **summary:** `net_total_pnl = total_pnl − fees − taxes` (include income, perché
     `total_pnl = market_pnl + realized_pnl + asset_income`).
2. **`analysis_status` a 3 stati derivato dalla *natura* delle issue** (`fifo_lot_engine.py`):
   `_QUANTITATIVE_FAILURE_CODES = {SHORT_TRANSFER_NOT_SUPPORTED, SHORT_ADJUSTMENT_NOT_SUPPORTED,
   FIFO_SOURCE_QUANTITY_MISSING, TRANSFER_PAIR_MISSING}` → **FAILED** (domina). Issue economiche/reference
   isolabili → **DEGRADED**. Nessuna issue → **COMPLETE**. Campo DTO pubblico resta `calculation_status`
   (mappato 1:1, no churn API).
3. **Enum di stato separati** (`schemas/portfolio.py`): globale `LotAnalysisStatus = COMPLETE|DEGRADED|FAILED`;
   per-lotto `LotNetMetricsStatus = AVAILABLE|UNAVAILABLE`. Il vecchio `UNAVAILABLE` globale ("nessun dato")
   migrato a `COMPLETE`.
4. **Fonte di verità del pool target:** `TargetPool = FXConvert(NativePool)` convertito **una sola volta**;
   i `target_amount` per-evento servono a pesi e audit; running-remainder riconcilia le allocazioni.
5. **Motore assoluto e broker-scoped:** il FIFO non riceve `share_percentage`; l'invariante di conservazione è
   `Σ(allocato ai lotti) + asset_orphan == pool target assoluto`.

---

## 4. Evidenza di verifica (tutta verde)

**Backend** (da root repo, `PYTHONPATH=. pipenv run pytest <path> -q`):
- `test_services/test_financial` + `test_portfolio_engine` (vnext): **298** passed.
- `test_schemas`: **274** passed.
- `test_api/test_transactions_validate.py`: **10** passed.
- `test_api` lots analysis: **7** passed.
- `ruff` + `black` puliti sui file toccati.

**Frontend** (`./dev.py …`):
- `front check` → **0 errori / 0 warning** (type-check contro `generated.ts` aggiornato).
- `i18n audit` → **Incomplete: 0** (parità EN/IT/FR/ES). Le 2 chiavi `dataQuality.*NoEligibleLots` risultano
  "unused" perché risolte dinamicamente via `message_key` API (come tutti i codici dataQuality).
- `front format` pulito · `front build` OK.

**Test aggiunti in questa sessione:** `TestAnalysisStatus` (4) + `TestEconomicConservation` (2) in
`test_fifo_lot_engine.py`.

---

## 5. Cosa NON è stato implementato (rinvii deliberati)

Elenco sintetico; motivazioni e proposte operative in [`review-checklist-v5.md`](./review-checklist-v5.md) §2.

1. **Fase 9 lato Portfolio Engine** — accumulatori assoluti pre-share + riconciliazione runtime. Doppio path
   (`portfolio_engine.py` vs `portfolio_service.py`), nessun consumer, file caldo → decisione di design.
2. **`LotComparisonChart` serie nette parallele** — rifinitura §8.3, da verificare visivamente prima.
3. **Provenienza pool nel modal** (§8.2, opzionale) — breakdown mostra importi ma non il mapping
   `economic_allocation_groups`→lotto.
4. **Trigger `net_metrics_status=UNAVAILABLE`** — machinery FE pronta ma latente finché il backend non emette
   `FX_RATE_MISSING_FOR_ALLOCATION`/`ALLOCATION_CONSERVATION_FAILED`.

---

## 6. Come riprendere / rieseguire

```bash
# Verifica backend (dalla root)
PYTHONPATH=. pipenv run pytest backend/test_scripts/test_services/test_financial -q
PYTHONPATH=. pipenv run pytest backend/test_scripts/test_schemas -q
LIBREFOLIO_TEST_MODE=1 PYTHONPATH=. pipenv run pytest backend/test_scripts/test_api/test_transactions_validate.py -q

# Verifica frontend
./dev.py front check && ./dev.py i18n audit && ./dev.py front build

# Rigenera client se si tocca l'API
./dev.py api sync

# Audit segni legacy (diagnostico, sul DB interessato)
PYTHONPATH=. pipenv run python backend/test_scripts/test_db/audit_transaction_signs.py

# Messaggio di commit proposto (NON committato)
cat /tmp/libreFolio_commit_fifo_v5.txt
```
