- Create FxBackwardFillInfo in common.py (fx_rate_date + fx_days_back).
- AssetBackwardFillInfo now inherits from BackwardFillInfo + FxBackwardFillInfo.
- FAAssetEventPointOut replaces flat fx_rate_date/fx_days_back with a single
  fx_info: Optional[FxBackwardFillInfo]. Events have no price-backward-fill
  semantics (discrete real dates) — only FX staleness is meaningful.
- Frontend +page.svelte reads ev.fx_info?.fx_rate_date / .fx_days_back.
- Tests updated to nested access.
- Wire format for prices is unchanged (mixin preserves field order).
**Prossimo commit suggerito**: batch refactor `FxBackwardFillInfo` da solo (piccolo e coeso). Messaggio:
```
Refactor: extract FxBackwardFillInfo as standalone building block

**Da testare con utente prima del commit**:
1. goBack FX → asset detail: deve tornare al detail corretto, non alla lista FX.
2. Toast currency change: 3 toast distinti (delete + changedTo + sync esito reale).
3. BTP Italia 2028: dopo `./dev.py db create-clean`, grafico deve essere retta pulita (no reset).
4. Log debug: `./dev.py server start` + sync BTP, cercare "scheduled_investment cache" nei log.
- `frontend/src/lib/stores/navigationStore.ts` (refactor stack-based + debug helper).
- `frontend/src/routes/(app)/+layout.svelte` (pass pathname to trackNavigation).
- `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` (3-toast refactor + buildAssetSyncToast integration).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+2 chiavi: `currencyChange.{deleteSuccess, changedTo}`).
- `backend/test_scripts/test_db/populate_mock_data.py` (BTP Italia 2028 → DAILY + no interest).
- `backend/app/services/asset_source_providers/scheduled_investment.py` (+logging debug cache HIT/MISS).

**Validazione batch 2 part3**:
- Part2 puntava alla minimizzazione (1 solo toast) ma perdeva informazioni importanti (l'errore sync post-wipe veniva nascosto).
- Part3 trova il giusto equilibrio: **1 toast per ogni step significativo**. Delete è un'operazione distruttiva — meritocraticamente degna di conferma. Patch è rapida ma produce la notifica chiave "currency changed" che l'utente si aspetta. Sync ha tutti i suoi stati compressi nel unified helper.
---

## 🎯 Obiettivo

Questo plan raggruppa:
1. **Decisioni terminali sul Blocco E** — stato di cose "fatte e da modificare", "non da fare", "da fare ora".
2. **Tasks I-bis pendenti** — coda di follow-up UX/Backend emersa dai test manuali 2026-04-22.
3. **Validazione finale di Part 3** — formato + lint + test + aggiornamento phase doc.

Obiettivo di chiusura: poter dichiarare Part 3 **completato** e procedere a Part 4 (pagina `/transactions`) con la roadmap pulita.

---

## 📜 Decisioni terminali sul Blocco E (post-Blocco I, dopo Q&A 2026-04-22)

Tabella autoritativa. Sostituisce la sezione Blocco E del parent plan (che resta solo
per traccia storica del design originale).

| # | Design originale (Part 1 §8) | Decisione terminale | Rationale |
|---|------------------------------|---------------------|-----------|
| **E.1** | `FAPricePoint.original_currency` sempre + `AssetBackwardFillInfo.fx_error` discriminator (`pair_missing`/`no_rate_at_date`) | ✅ `original_currency` **tenuto** (già implementato).<br>❌ `fx_error` **cancellato dal design**. | Gli scenari `pair_missing` e `no_rate_at_date` sono **ancora possibili** (conversione display-currency con pair non registrata o history FX incompleta). Ma il surface UI alternativo `requiredFxPairs` (in `routes/(app)/assets/[id]/+page.svelte` L267–337, L1081–1153) li gestisce **a monte** con 4 stati (`ok`/`missing`/`no-data`/`partial-gap`), banner inline e CTA one-click (`Add FX Pair` / `Sync`). Aggiungere `fx_error` al response sarebbe duplicazione. Verifica: `grep fx_error` → 0 risultati sia in backend sia frontend → non c'era mai stato da rimuovere. |
| **E.2** | `FAPriceQueryResult.currency_breakdown` | ❌ **Cancellato** | Superseded da I.1 (Blocco I): tutti i punti di un asset hanno per definizione la stessa currency (I.2 hard-reject). Breakdown ridondante. |
| **E.3** | `upsert_prices_bulk`: mismatch → `errors.append` + skip soft | 🟡 **Rimpiazzato** da I.2 (hard 400 reject). Design originale da cancellare; codice già allineato. | Con la column `currency` rimossa dal DataEditor (I.8), i mismatch possono arrivare solo da caller "scorretti" (import CSV malformato, chiamate API manuali). Failare rumoroso > silenziare. |
| **E.4** | `fx_provider_manager.ensure_pair_registered` — auto-registrazione FX pairs | ❌ **Cancellato (design era sbagliato)** | Auto-magic viola la filosofia self-hosted (controllo esplicito dell'utente su provider/quota/sync). La UX `requiredFxPairs` già mette l'utente in condizione di capire e agire (banner + CTA "Add FX Pair" con slug pre-compilato). |
| **E.5** | `PriceCurrencyMismatchBanner` + endpoint `POST /prices/normalize` + azioni Normalize/Ignore | ❌ **Cancellato** | Superseded da I.5. Post-I.2 non possono più esistere punti dissonanti → banner + endpoint non necessari. |
| **E.6** | Banner FX-missing differenziato (`pair_missing`/`no_rate_at_date`) | ❌ **Cancellato** | Superseded da I.5 + `requiredFxPairs` (granularità superiore: 4 stati vs 2). |
| **E.7** | DataEditor: pre-fill colonna currency + warning | ❌ **Cancellato** | Superseded da I.5/I.8: colonna rimossa. |
| **E.8** | `query_events_bulk` param `target_currency` + conversione event.value | ⏳ **Da fare ora** — vedi §E.8 sotto | Sblocca visualizzazione corretta di dividendi/cash events nella display-currency scelta dall'utente, pre-requisito funzionale per Phase 9 Dashboard. |

---

## 🛠️ Task E.3 — Source cleanup + doc update  ✅ DONE (2026-04-22 sera)

### Lavoro eseguito
- Verificato: il codice `bulk_upsert_prices` in `backend/app/services/asset_source.py` L1160–1175 **era già allineato** a I.2 (hard `ValueError` → 400 nel router API).
- Verificato: endpoint `upsert_prices_bulk` in `backend/app/api/v1/assets.py` L620–624 già gestisce `ValueError` → `HTTPException(400, detail=str(e))`.
- Verificato: **nessun residuo** di pattern "soft-skip con `errors.append` per currency mismatch" (grep confermato).
- **Aggiunto**: docstring esplicita in `bulk_upsert_prices` che documenta la semantica I.2 hard-400 + rinvio a questo closure plan.

### Validazione
- `./dev.py format` → ✅ 0 changes.
- `./dev.py lint` → ✅ all checks passed.

### Lavoro
- **Grep** residui di linguaggio "soft-skip + errors[]" in:
  - `backend/app/services/asset_source.py` (docstring di `upsert_prices_bulk`, commenti inline).
  - `backend/app/api/v1/assets.py` (endpoint prezzi).
  - `backend/app/schemas/assets.py` (response schemas per upsert).
  - Test `backend/test_scripts/api/test_assets_price.py` (search per `errors: [` in assert che aspettano 200).
- **Sostituire** con la nuova semantica: HTTP 400 su qualsiasi mismatch currency, body `{detail, asset_currency, offending_dates[]}`.
- **Parent plan**: nella sezione Blocco E §E.3, aggiungere nota `> **SUPERSEDED** by I.2 (2026-04-21) — hard 400 reject. See Closure plan §E.3.` senza cancellare il testo originale (traccia storica).

### Validazione
```bash
./dev.py format && ./dev.py lint
./dev.py test api assets-price
```

---

## 🛠️ Task E.8 — `query_events_bulk` target_currency + infobox FX-converted

### Design rules (specchio del pattern prezzi)

Il sistema prezzi ha già consolidato un design per i valori convertiti FX.
**Riusare le stesse funzioni e gli stessi token** per evitare divergenze.

#### Funzioni/utility già esistenti da riusare tali e quali

| Utility | File | Uso |
|---------|------|-----|
| `getCurrencyInfo(code)` → `{flag_emoji, ...}` | `$lib/stores/currencyStore` | Lookup bandiera da ISO3. |
| `ensureCurrenciesLoaded()` | idem | Prefetch registry currency prima del render. |
| `signalLabelToHtml(sigInfo, maxLen=15)` | `$lib/components/charts/...` (cercato in `PriceChartFull.svelte` L904+) | Rendering label con icona + troncamento 15 char. |
| Lookup map pattern `Map<date, value>` | `PriceChartFull.svelte` L729–738 | Pre-compute lookup O(1) per tooltip. |

#### Token di design (estratti da `PriceChartFull.svelte` L849–955 + `MeasurePanel.svelte` L408–416)

| Token | Valore | Esempio |
|-------|--------|---------|
| **Currency badge (no conversione)** | `(${flag} ${ISO3})` fontsize 10px opacità 0.7 | `(🇺🇸 USD)` |
| **Currency badge (con conversione)** | `(${flag_display} ${ISO3_display}) 💱` fontsize 10px | `(🇪🇺 EUR) 💱` |
| **Valore originale (MeasurePanel suffix)** | `<span style="font-size:10px;opacity:0.7">(${origFlag} ${origISO3})</span>` | `(🇺🇸 USD)` in coda al valore |
| **Troncamento nome serie** | `> 15 char → slice(0,15) + '…'` | `AAPL — Tech…` |
| **Format valore numerico** | `>= 1 → toFixed(2)`, altrimenti `toFixed(4).replace(/\.?0+$/,'')` | `89.52`, `0.0425` |
| **Converted indicator** | `💱` sempre **alla fine** del pattern `(flag ISO3)` | vedi riga sopra |

### E.8.1 — Backend: `query_events_bulk`  ✅ DONE (2026-04-22 sera)

**Stato**: endpoint + conversion pass **già implementati** in precedenza.
Mancavano solo i campi `original_*` / `fx_*` sul response schema.

**Fatto**:
- Esteso `FAAssetEventPointOut` (`backend/app/schemas/prices.py` L295+) con:
  - `original_value: Optional[Currency]` (cattura amount + code originali in un unico oggetto Currency, coerente con il pattern del resto dello schema).
  - `fx_rate_date: Optional[date]`.
  - `fx_days_back: Optional[int]`.
- Service `query_events_bulk` (`backend/app/services/asset_source.py` L2637+): popola i 3 campi su conversione riuscita; skip su identity conversion (from==to) per distinguere "converted" da "passthrough" lato FE.
- **Bonus cleanup (E.1 closure discovery)**: rimosso `fx_error` discriminator (era implementato nel backend per i prezzi ma non consumato dal FE). Coerente con la decisione E.1. 6 riferimenti puliti in `asset_source.py` + 1 field in `FAPricePoint.backward_fill_info`.
- `./dev.py api sync` → client TS rigenerato con nuovi campi visibili.
- `./dev.py format && lint && front check && test api assets-events/assets-price` → ✅ tutti verdi.

### E.8.2 — Frontend: event infobox nel chart  ✅ DONE (2026-04-22 sera)

**Fatto**:
- Esteso `EventMarker` interface in `PriceChartFull.svelte` L24+ con: `originalValue`, `originalCurrency`, `originalCurrencyFlag`, `currencyFlag`, `fxRateDate`, `fxDaysBack`.
- Tooltip formatter (L673+) riscritto per pattern design-consistente:
  - `💰 {value} (flag ISO3) 💱` — emoji currency indicator **alla fine** (token standard).
  - `orig. {originalValue} (origFlag origISO3)` — font-size 10px opacity 0.7, pattern mirror di `MeasurePanel.svelte`.
  - `fx @ {date} ({days}d back)` — font-size 10px opacity 0.6.
- Hide rule: eventi con conversione fallita **non vengono renderizzati** (filtro in `chartEventMarkers` $derived del +page.svelte).

### E.8.3 — Frontend: estendere `requiredFxPairs` a include event currencies  ✅ DONE (2026-04-22 sera)

**Fatto**:
- Esteso `$derived requiredFxPairs` in `routes/(app)/assets/[id]/+page.svelte` L336+ per aggiungere le pair derivate dalle event currencies (own + comparison) ≠ `displayCurrency`.
- Logica `missing` / `no-data` (failed conversion detection su `!ev.original_value`).
- `forAsset` etichettato via nuova chiave i18n `events.fxBannerContext` ("for dividend/cash events" / "per eventi dividendi/cassa" / "pour les événements dividendes/cash" / "para eventos dividendo/efectivo") → propagata nelle 4 lingue.
- Banner esistente (L1081–1153) riusato as-is: stesso markup, CTA "Add FX Pair" + "Sync" già pronti.

### E.8.4 — Bonus backend cleanup  ✅ DONE (2026-04-22 sera)

Durante il lavoro E.8 ho scoperto che la conversione FX dei prezzi `get_prices_bulk` (con `include_events=True`) **non includeva** gli eventi nel conversion pass. Aggiunto mirror di 27 righe dopo il loop prezzi che applica la stessa logica a `result.events`, popolando `original_value` + `fx_rate_date` + `fx_days_back` e surfacing degli errori FX come stringhe non-fatali in `result.errors`. Così la conversione eventi funziona sia dall'endpoint `/assets/events/query` sia da `/assets/prices/query?include_events=true` (path usato in produzione dal +page.svelte).

### Validazione E.8
- `./dev.py format && lint` → ✅ 0 errori.
- `./dev.py api sync` → ✅ client TS rigenerato con i 3 campi aggiunti.
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py test api assets-events / assets-price` → ✅ entrambi PASSED.
- Test backend dedicato E.8 (`test_events_target_currency.py`) → **demandato al Blocco G** qui sotto.

### E.8.4 — Test

**Backend** (`backend/test_scripts/api/test_events_target_currency.py`):
- `test_no_target_currency_returns_raw_values`.
- `test_same_currency_passthrough` (event USD, target USD → no-op, original_* = None).
- `test_conversion_same_day_fx` (original_* popolati, fx_days_back=0).
- `test_conversion_backward_fill_fx` (fx_days_back > 0).
- `test_missing_fx_appends_to_errors_not_hard_fail`.
- `test_mixed_events_some_converted_some_not`.
- `test_original_value_always_populated_on_success`.

**Frontend**:
- Unit/component test (se esiste infrastruttura) su rendering infobox converted vs non-converted.
- Playwright E2E: caricare asset con dividend events in currency diversa, switchare displayCurrency → verifica che il tooltip contenga entrambi i valori, verifica che banner `requiredFxPairs` sia visibile se pair manca.
- Test manuale estetico esplicito (🎨).

### E.8.5 — Validazione
```bash
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check
./dev.py test api events-target-currency
./dev.py test all-backend
# Test manuale: asset con dividend USD, displayCurrency=EUR, verifica infobox
```

---

## 🔍 Blocco F — Verifica finale (codice presente, test da consolidare)

Il Blocco F (OHLC partial upsert + sentinel `-1` + current-price auto-extend) **è implementato nel codice**:

- **F.3 `_extend_ohlc_bounds`** ✅ validato in produzione (conferma log 2026-04-22 sera, plan Part3 §I-bis).
- **F.4 sentinel `-1` → NULL** ✅ presente in `backend/app/services/asset_source.py` L1191–1193 (helper merge).
- **F.1/F.2** (provider > utente, bootstrap OHLC) ✅ inferibili dalla presenza di F.4.
- **F.5** eraser 🧽 + placeholder `notSet` ✅ validato via I-bis #9 fix su `ErasableNumberCell`.

### Task pendente F: test di copertura

→ Copertura di F demandata al **Blocco G.6** (`test_ohlc_sentinel.py`, vedi sotto). Nessun lavoro di codice residuo.

---

## 🧪 I.9 — Backend test adaptations (Blocco I)  ✅ DONE (2026-04-22 sera)

**Fatto** in `backend/test_scripts/test_api/test_assets_prices.py`:
- `test_upsert_mismatch_single_row_rejects_400` → single EUR row on USD asset → 400 "Currency mismatch".
- `test_upsert_mismatch_partial_rejects_entire_batch_400` → 1/3 mismatch rejects atomicamente (verificato query post-400 → 0 rows).
- `test_upsert_same_currency_succeeds_200` → regression test che il happy path non è rotto.

**Validazione**: `./dev.py test api assets-price` → ✅ tutti 17 tests PASSED (14 preesistenti + 3 I.9).

---

## ✅ I.10 — Validazione finale Blocco I

```bash
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check
./dev.py test api assets-price
./dev.py test api assets-currency-change   # da G.10
./dev.py test api assets-prices-export     # da G.11
```

Da eseguire **dopo** G.10 e G.11 (che i test file li creano).

---

## 🚀 Batch pendenti — spostati in file companion

> 📄 **I Blocchi G (test coverage) e la Coda I-bis pendente sono stati
> spostati nel file companion [`plan-phase07-transaction-Part3_1_Closure_2.prompt.md`](./plan-phase07-transaction-Part3_1_Closure_2.prompt.md)**
> per tenere questo plan in dimensioni gestibili. Questo file resta la fonte
> canonica per il lavoro **già completato** (Blocchi E, F, I, batch 2 part1-4b)
> e per le decisioni di design (#R3-1..#R3-4, Policy D R3-3, design backup
> endpoint R3-3b).

Per i batch ancora da eseguire consulta il file `_2`:
- **Blocco G** — 11 suite di test (G.1..G.11), coverage target ≥ 90%
- **Coda I-bis pendente** — 14 ticket (#1, #2, #3, #4, #5, #6, #7, #12,
  #19, #22, #23, #24, #25, #26)
- **Retest findings Batch 2 part4b** — 5 follow-up (#R4-1..#R4-5) dal giro
  di smoke test del 2026-04-23 pomeriggio

---


## 🗺️ Ordine di esecuzione suggerito

1. **E.3 source cleanup** (30 min) — quick, chiude la narrativa Blocco E.
2. **E.8 backend + test** (2h) — foundation per infobox FE.
3. **E.8 frontend infobox + `requiredFxPairs` estensione** (1.5h) — chiude E.
4. **I-bis #1 + #23** (combinati, 2h) — unico handler per "sync 0 rows" + `status=partial`.
5. **I-bis #12** (1h) — toast reduction (quick win).
6. **I-bis #3 + #4 + #6** (1h combinati) — micro-UX.
7. **I-bis #5** (1.5h) — CSV import resilience.
8. **I-bis #2** (1h) — provider dirty gating.
9. **I-bis #22** (3–4h) — save error handling generalizzato. **Prerequisito Part 4/5**.
10. **I-bis #7** (30 min) — backend 409 semantics, non urgente.
11. **I.9 test adaptations** (1h) — hard-400 currency mismatch tests.
12. **G.1 + G.2** extend existing (2h) — rollback, matrix access control.
13. **G.3 transactions/validate** (1.5h).
14. **G.4 events/suggest** (1h).
15. **G.5 prices-currency-coherence** (1h — versione ridotta post-I.11).
16. **G.6 ohlc-sentinel** (1.5h) — copertura Blocco F.
17. **G.10 asset-currency-change** (1h).
18. **G.11 asset-prices-export** (1.5h).
19. **G.7 test_runner.py** (15 min).
20. **G.8 coverage verification** (30 min) + eventuale top-up.
21. **I.10 + G.9 validazione finale** (30 min).

**Totale stimato**: ~13–14h lavoro UX/feature + ~12h test coverage + validazione = **~25–26 ore** totali per la chiusura completa.

> Se si vuole accelerare, i blocchi G.1/G.2/G.3/G.4 (matrix transazioni + validate + suggest) possono essere parallelizzati da un secondo agent/dev perché toccano area isolata.

---

## ✅ Deliverable di chiusura

### Backend
- `query_events_bulk` con `target_currency` param (E.8).
- Schema `FAEventOut` esteso con `original_value`, `original_currency`, `fx_rate_date`, `fx_days_back`.
- Source cleanup docstring/commenti E.3.
- (Opzionale I-bis #7) HTTP 409 per batch patch all-failed.

### Frontend
- Event infobox con valore converted + originale (pattern prezzi mirror).
- `requiredFxPairs` esteso a event currencies.
- Event markers/rows nascosti se conversione FX fallisce.
- Handler unificato `PriceSyncResponse` con 4 stati toast (I-bis #1+#23).
- 3 toast currency change → 1 (I-bis #12).
- Tab label currency+flag (I-bis #3).
- CSV import banner + resilience (I-bis #4 + #5).
- Empty-state "Add manually" (I-bis #6).
- Provider dirty gating per "Save Without Testing?" (I-bis #2).
- `saveWithRetry` helper + adozione in 8 modal (I-bis #22).

### i18n (nuove chiavi × 4 lingue)
- `events.fxBannerContext`, `events.hiddenDueToMissingFx` (E.8).
- `sync.postWipeZeroRows`, `prices.sync.{success,noChanges,partial,failed}` (I-bis #1+#23).
- `dataEditor.pricesInCurrency`, `dataEditor.eventsInCurrency` (I-bis #3).
- `import.csv.currencyReminder`, `import.csv.extraColumnsIgnored` (I-bis #4).
- `assetDetail.addPricesManually` (I-bis #6).
- Messaggi errore generici `save.failed.*` (I-bis #22).

### Test
- `test_events_target_currency.py` (E.8, 7 test case).
- `test_transactions_validate.py` (G.3, 6 casi).
- `test_events_suggest.py` (G.4, 5 casi + parametrizzati).
- `test_prices_currency_coherence.py` (G.5, 3 casi post-I.11).
- `test_ohlc_sentinel.py` (G.6, 8 casi).
- `test_asset_currency_change.py` (G.10, 5 casi).
- `test_asset_prices_export.py` (G.11, 7 casi).
- `test_transaction_service.py` estensione (G.1, 10 nuovi casi).
- `test_transactions_api.py` matrix estesa (G.2).
- `test_assets_prices.py` hard-400 cases (I.9).
- `scripts/test_runner.py` entries (G.7, 7 nuove).
- Coverage `transaction_service ≥ 90%`, `asset_source (funzioni toccate) ≥ 85%` (G.8).
- Unit FE su infobox converted (se infrastruttura disponibile).
- Playwright E2E scenario: asset con dividend USD, display EUR, hide-on-missing-FX, banner scatter.

### Documentazione
- Parent plan `plan-phase07-transaction-Part3.md` con nota di rinvio a questo closure.
- Phase doc `phases/phase-07-transactions.md` aggiornata al termine.

---

## 🔗 Cross-link

- **Parent**: [`plan-phase07-transaction-Part3.md`](./plan-phase07-transaction-Part3.md).
- **Predecessori**: [`plan-phase07-transaction-Part1.md`](./plan-phase07-transaction-Part1.md) ✅, [`plan-phase07-transaction-Part2.prompt.md`](./plan-phase07-transaction-Part2.prompt.md) ✅.
- **Successori**: Part 4 (pagina `/transactions`), Part 4b (File Preview), Part 5 (Staging Modal). **Gated da I-bis #22**.
- **Phase 8 follow-up**: [`phases/phase-08-scheduler.md`](./phases/phase-08-scheduler.md) — consumer `Asset.active` + scheduler demone.
- **Phase 9 follow-up**: Dashboard — consumer `Asset.active` hide su breakdown + estensione `requiredFxPairs` a viste multi-asset.
- **Phase 9 follow-up**: Dashboard — consumer `Asset.active` hide su breakdown + estensione `requiredFxPairs` a viste multi-asset.

---

## 🚧 Rischi & Mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| E.8 backward-fill FX policy divergente dai prezzi | Riusare la stessa funzione `fx_service.get_rate_at_date(..., backward_fill_days=14)` |
| Event currencies miste → banner rumoroso | Dedup `toSlug` + `seenSlugs` già gestito in `requiredFxPairs` |
| I-bis #22 refactor rompe modal esistenti | Rollout progressivo: adotta `saveWithRetry` un modal alla volta + test manual regressivo |
| Ordine E → I-bis rotto da nuovi feedback utente | Accettabile: questo plan è "closure" non "frozen" — eventuali nuovi I-bis si accodano |

---

## ✅ Come validare esternamente

```bash
# 1) Format + lint + sync
./dev.py format && ./dev.py lint
./dev.py api sync && ./dev.py front check

# 2) Test mirati Blocco E residuo
./dev.py test api assets-price          # E.3 cleanup
./dev.py test api events-target-currency # E.8

# 3) Test regressione
./dev.py test all-backend

# 4) Smoke E2E
./dev.py test e2e asset-currency-change
./dev.py test e2e events-fx-conversion   # nuovo

# 5) Test manuale estetico
#    - Asset USD, displayCurrency=EUR, verifica infobox converted + banner requiredFxPairs
#    - Currency change flow: 1 solo toast finale
#    - CSV re-import dal CSV export
#    - Edit modal asset senza toccare provider → no "Save without testing?" modal
```

---

## 🧭 Giornale di viaggio (per reset conversazione)

> **Scopo**: in caso di reset del contesto, questa sezione è il backup delle intenzioni, dello stato e dei prossimi step. Aggiornata a ogni fine-sessione.

### 📍 Dove sono arrivato (2026-04-22 sera tardi, batch 1 + refactor FxBackwardFillInfo + batch 2 part1)

**Commit batch 1** (già fatto dall'utente, hash `66ad026a` + un commit successivo): Closure plan batch 1 completo.

**Sessione post-commit (questa)** — refactor schema:
- Creata nuova classe `FxBackwardFillInfo` in `backend/app/schemas/common.py` (accanto a `BackwardFillInfo`). Contiene `fx_rate_date` + `fx_days_back`.
- `AssetBackwardFillInfo` (in `prices.py`) ora eredita da **entrambi** (`BackwardFillInfo, FxBackwardFillInfo`) via mixin Pydantic → wire format prezzi identico, **zero breaking change** lato client per i prezzi.
- `FAAssetEventPointOut`: sostituiti i 2 campi piatti `fx_rate_date`+`fx_days_back` con un unico `fx_info: Optional[FxBackwardFillInfo]`. `original_value` resta standalone (non è backward-fill metadata).
- Motivazione: gli eventi **non hanno semantica di price backward-fill** (ex-date, cedola etc. sono date reali non-interpolabili). Solo la FX staleness è rilevante → raggrupparla in un oggetto dedicato, riusabile per futuri consumer (dashboard aggregati Phase 9).
- Backend (`asset_source.py`): 2 siti di costruzione `FAAssetEventPointOut` aggiornati per usare `fx_info=FxBackwardFillInfo(...)`. Import top-level esteso con `FxBackwardFillInfo`.
- Frontend (`+page.svelte`): accessi `ev.fx_rate_date`/`ev.fx_days_back` → `ev.fx_info?.fx_rate_date`/`ev.fx_info?.fx_days_back`.
- Test (`test_events_target_currency.py`): accessi aggiornati a `ev["fx_info"]["fx_rate_date"]`/`["fx_days_back"]` (sia doppi che singoli apici).
- Client TS rigenerato: `FxBackwardFillInfo` ora è un tipo Zod esportato, `fx_info` esposto come campo opzionale su `FAAssetEventPointOut`.
- Validazione post-refactor:
  - `./dev.py format && lint` → ✅ all checks passed.
  - `./dev.py front check` → ✅ 0 errors, 0 warnings.
  - `./dev.py test api events-target-currency` → ✅ 7/7 PASSED.
  - `./dev.py test api assets-price` → ✅ PASSED (regression OK).
  - `./dev.py test api assets-events` → ✅ PASSED.

**File toccati post-commit batch 1**:
- `backend/app/schemas/common.py` (+~45 righe: nuova classe `FxBackwardFillInfo`).
- `backend/app/schemas/prices.py` (AssetBackwardFillInfo rifattorizzato a inheritance, FAAssetEventPointOut con `fx_info`).
- `backend/app/services/asset_source.py` (import + 2 siti di costruzione).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (2 blocchi event markers).
- `backend/test_scripts/test_api/test_events_target_currency.py` (assert nested).

**Sessione batch 2 part1** (questa, continuazione post-reset "actual_rate_date_str") — I-bis UX quick wins:
- **Fix pregresso**: `common.py` aveva il metodo `actual_rate_date_str()` erroneamente spostato dentro `FxBackwardFillInfo` (bug introdotto nel refactor precedente). Ripristinato dentro `BackwardFillInfo` (campo corretto: `actual_rate_date`). Verificato con one-liner runtime ✅.
- **I-bis #3** ✅ Tab label "Prices in {currency} 🇺🇸" / "Events in {currency} 🇺🇸" in `AssetDataEditorSection.svelte`:
  - Aggiunta prop `currency?: string`.
  - Derived `currencyFlag` via `getCurrencyInfo(currency).flag_emoji`.
  - Label `ml-auto` nella tab bar (switcha tra pricesInCurrency/eventsInCurrency in base ad `activeTab`).
  - `+page.svelte` passa `currency={assetInfo?.currency}`.
  - i18n keys nuove: `assetDetail.pricesInCurrency` + `assetDetail.eventsInCurrency` (4 lingue).
- **I-bis #4** ✅ Import CSV banner reminder in `PriceDataImportModal.svelte`:
  - Aggiunta prop `currency?: string`.
  - Nuovo `InfoBanner variant="warning"` nell'header slot con "Currency must match asset currency ({currency} 🇺🇸)." + "Extra columns (like currency, source_plugin_key, fetched_at from Export) are ignored."
  - `AssetDataEditorSection.svelte` propaga `currency` al modal.
  - i18n keys nuove: `import.csv.currencyReminder` + `import.csv.extraColumnsIgnored` (4 lingue).
- **I-bis #6** ✅ Empty-state "Add manually" button in `+page.svelte`:
  - Nel ramo `{:else}` (zero prezzi, provider-backed asset) aggiunto secondo bottone "Add manually" accanto a "Sync from provider". Apre il data editor salvando lo stato dei panel (pattern identico al ramo `isManualOnly`).
  - i18n key nuova: `assetDetail.addPricesManually` (4 lingue).
- **Gotcha #1 confermato**: shell strippa accenti (É, é, à, ñ). Per ogni `./dev.py i18n add` con chars non-ASCII ho creato script `/tmp/libreFolio_fix_*.py` con escape unicode (`\u00f1`) per fixare il file JSON post-add.
- Validazione batch 2 part1:
  - `./dev.py front check` → ✅ 0 errors, 0 warnings (eseguito 3 volte, dopo ogni task).
  - `./dev.py front format` → ✅ tutti i file unchanged (già formattati).

**File toccati in batch 2 part1**:
- `backend/app/schemas/common.py` (spostato `actual_rate_date_str` dal posto sbagliato).
- `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` (prop currency + tab label).
- `frontend/src/lib/components/assets/PriceDataImportModal.svelte` (prop currency + warning banner).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (passa currency al data editor + bottone "Add manually" nell'empty state).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (5 nuove chiavi × 4 lingue = 20 entries).

### 📍 Retest batch 2 part1b (2026-04-22 sera tardi, post-utente-feedback)

Dopo retest manuale dell'utente:
- **I-bis #3** ✅ confermato + traduzioni OK.
- **I-bis #6** ✅ confermato + regressione manual-only verificata. Emerso nuovo task I-bis #24 (vedi sotto).
- **I-bis #4** 🔧 2 issue da fixare:
  1. **Banner design**: non un 2° banner warning, ma **un unico InfoBanner info** con ordine: currency reminder → struttura (min/extended) → hint separatore → nota extra-columns.
  2. **Banner i18n**: le 3 righe esistenti (Minimum/Extended/separator hint) erano hardcoded in inglese → tradotte con 3 nuove chiavi i18n.
  3. **Tooltip CSV errors**: in `CsvEditor.svelte` gli errori di parsing erano comunicati via `title=` HTML nativo. Migrato al componente custom `Tooltip.svelte` (mostra istantaneo su hover della X rossa + del numero riga con error). Posizionamento `right` per non coprire la textarea. Tooltip applicato condizionalmente solo se `v.error` non vuoto (evita wrapper spurio sulle righe valide).

**i18n nuove (batch 2 part1b)** in `import.csv.*`:
- `labelMinimum` ("Minimum" / "Minimo" / "Minimum" / "Mínimo").
- `labelExtended` ("Extended" / "Esteso" / "Étendu" / "Extendido").
- `separatorHint` con placeholder `{sep}` iniettato via `@html` (il codice `<code>;</code>` non si interpola con `{values}` di svelte-i18n, quindi passo HTML escapato). 4 lingue.

**File toccati in batch 2 part1b**:
- `frontend/src/lib/components/assets/PriceDataImportModal.svelte` (collassato i 2 banner in 1, traduzioni).
- `frontend/src/lib/components/ui/data-editor/CsvEditor.svelte` (import Tooltip, 2 siti `title=""` → `<Tooltip text={v.error}>…</Tooltip>`).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+3 chiavi).

**Validazione batch 2 part1b**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py front format` → ✅ all unchanged.

**Nuovo task tracciato** (non ancora implementato): `I-bis #24 — Auto-refresh mirato post-sync` (aggiornato solo il last-point dopo sync, no full reload; transizione fluida empty→chart se finestra include oggi). Vedi sezione dedicata sopra nel plan.

**Issue emersa ma NON fixata in questa sessione** (perché scope = #5): il CSV esportato da `/prices/export?format=csv` oggi ha colonne extra (`currency, source_plugin_key, fetched_at`) che `CsvEditor` rifiuta con "too many fields". Il round-trip export→import richiede l'header-tolerance di I-bis #5. Per ora il banner informa l'utente che le extra columns sarebbero ignorate; il parser va reso effettivamente tollerante in batch successivo.

### 📍 Retest batch 2 part1c (2026-04-22 sera tardi, 3° giro feedback utente)

Dopo il 3° retest manuale emersi 3 nuovi issue:

**Issue A — Missing FX quick-link icon**:
- Nella filterBar del detail asset (`AssetPriceSummary.svelte`), **dopo** il dropdown "Converti in", non c'era più un link rapido alla detail page della coppia FX.
- Fix: aggiunta prop `fxPairUrl?: string`. Quando valorizzata (solo se pair **healthy**) mostra un bottone `<a>` con icona `ExternalLink` e `Tooltip` "Open FX pair detail". Click → naviga a `/fx/{slug}?start=...&end=...`.
- Parent `+page.svelte`: nuovo derived `mainFxPairUrl` che cerca la main pair in `requiredFxPairs` e ritorna URL solo se `status === 'ok'`. Se missing/no-data/partial-gap → `undefined` (niente bottone). Il banner full-width gestisce già quegli stati con le CTA specifiche → evitiamo doppioni/ambiguità.
- `data-testid="asset-detail-fx-pair-link"` per E2E futuri.
- i18n: `assetDetail.openFxPair` (4 lingue, "Ouvrir le détail de la paire FX" per FR).

**Issue B — Modal import title hardcoded + Events CSV banner hardcoded**:
- `PriceDataImportModal.svelte`: `title="📥 Import Prices CSV"` → `title={$t('import.csv.titlePrices')}`.
- `EventDataImportModal.svelte`:
  - Stesso fix sul titolo.
  - Tradotte le 2 righe del banner esistente: "Format:" → `{$t('import.csv.eventsFormatLabel')}`, "Types:" → `{$t('import.csv.eventsTypesLabel')}` (elevato a `<strong>` per coerenza col pattern prezzi).
  - **Aggiunta** la nota "Extra columns ignored" (`import.csv.extraColumnsIgnored`, riutilizzo della chiave di I-bis #4) → anche events CSV ora avverte che colonne in più sono ignorate.
- i18n nuove: `import.csv.{titlePrices, titleEvents, eventsFormatLabel, eventsTypesLabel}` (4 chiavi × 4 lingue).

**Issue C — fr.json accidentally zeroed**:
- Durante un tentativo di fix accent via Python inline con surrogate escape (`\ud83d\udce5`), `write_text(..., encoding='utf-8')` ha failato ma DOPO aver aperto il file in `w` → `fr.json` → 0 byte. Ripristinato via `git checkout HEAD` + script `/tmp/libreFolio_restore_fr_keys.py` che riapplica TUTTE le 13 chiavi FR aggiunte in questa sessione (pricesInCurrency, eventsInCurrency, addPricesManually, openFxPair, currencyReminder, extraColumnsIgnored, labelMinimum, labelExtended, separatorHint, titlePrices, titleEvents, eventsFormatLabel, eventsTypesLabel) con escape unicode `\u00e9` / `\u00c9` / `\u00e0` e emoji 📥 pescato da `en.json`.
- **Lezione/gotcha nuovo**: MAI usare surrogate pair escape per l'emoji 📥 in python — usare `\N{INBOX TRAY}` o copiarla da un altro file.

**File toccati in batch 2 part1c**:
- `frontend/src/lib/components/assets/AssetPriceSummary.svelte` (+prop fxPairUrl + link).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (+derived mainFxPairUrl, passa al summary).
- `frontend/src/lib/components/assets/PriceDataImportModal.svelte` (title i18n).
- `frontend/src/lib/components/assets/EventDataImportModal.svelte` (title i18n + banner tradotto + extra-columns note).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+5 chiavi × 4 lingue = 20 entries; fr.json integralmente ripristinato).

**Validazione batch 2 part1c**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py front format` → ✅ all unchanged.

**i18n finale cumulativo batch 2 part1+1b+1c** (da committare insieme):
- `assetDetail.{pricesInCurrency, eventsInCurrency, addPricesManually, openFxPair}` — 4 chiavi.
- `import.csv.{currencyReminder, extraColumnsIgnored, labelMinimum, labelExtended, separatorHint, titlePrices, titleEvents, eventsFormatLabel, eventsTypesLabel}` — 9 chiavi.
- **Totale: 13 chiavi × 4 lingue = 52 entries**.

### 📍 Batch 2 part2 (2026-04-22 sera tardi, 4° giro) — I-bis #12 + #1+#23 + bugfix

**Bug A fixati in apertura** (da retest utente post-commit batch 2 part1c):
- **FX icon**: il link FX quick-access nel filterBar usava `ExternalLink`, ma l'icona standard del progetto per le coppie FX è `ArrowLeftRight` (usata in `FxTable/FxCard/FxSyncModal/FxPairAddModal/FxProviderConfig`). Sostituita in `AssetPriceSummary.svelte`.
- **DataEditor buttons hardcoded**: i bottoni "Import CSV" e "Add Row" nel toolbar di `DataEditor.svelte` erano in inglese fisso (sia nel tab Prices sia nel tab Events). Tradotti con nuove i18n:
  - `dataEditor.importCsv` ("Import CSV" / "Importa CSV" / "Importer CSV" / "Importar CSV")
  - `dataEditor.addRow` ("Add Row" / "Aggiungi riga" / "Ajouter une ligne" / "Agregar fila")
  - `dataEditor.emptyMessage` (messaggio empty-state quando non ci sono righe, "No data. Use 'Add Row'..." tradotto).

**I-bis #12 — Toast reduction currency change (5 → 1)**:
- `AssetCurrencyChangeModal.svelte`: rimossi i 3 `toasts.info` di progress (`progressDelete`, `progressPatch`, `progressSync`). Sostituiti con uno stato `progressStep: null | 'delete' | 'patch' | 'sync'` che renderizza inline nel footer del modal (sinistra dei bottoni) uno spinner CSS + la label i18n corrispondente. Le 3 chiavi i18n esistenti sono state **riutilizzate** — non rimosse dai JSON perché ora compongono il messaggio inline.
- `AssetModal.svelte` `onconfirmed` callback: rimosso il `toasts.success($t('assets.modal.saveSuccess'))` duplicato (il `currencyChange.done` che emette il modal figlio è sufficiente). Commento inline I-bis #12.
- **Risultato UX**: flusso provider-backed = **1 toast finale** `done` (era 5). Flusso no-provider = **1 toast finale** `done` (era 3). Toast di errore/warning (syncFailedManualRetry, failed) intatti.

**I-bis #1 + #23 — Unified PriceSyncResponse handler**:
- `lib/utils/syncToastHelpers.ts`: refactor `buildAssetSyncToast` con firma estesa `(result, label, tr)`. Ora gestisce **5 stati** coerenti:
  1. `ok` + `points_changed>0` → `success` (messaggio esistente).
  2. **`ok` + `points_changed===0 && events_changed===0` → `warning`** con suffix `prices.sync.noChanges` ("No new data (already up to date)"). **Questo è il fix per I-bis #1**: post-wipe scenario dove il provider restituisce 0 righe valide (es. currency mismatch silently dropped) non viene più silenziosamente colorato di verde.
  3. `partial` → `warning` con **`result.message` appended** quando presente (I-bis #23: surface del messaggio scheduled_investment tipo "Current value only, history unavailable").
  4. `skipped` → `info`.
  5. altro/errore → `error` con fallback `result.message || prices.sync.failedDefault`.
- `buildFxSyncToast`: stesso refactor per i suffissi hardcoded (`Partial`, `Skipped`, `Failed`, `manual only`) → `tr('prices.sync.{partialSuffix, skippedSuffix, failedDefault, manualOnly}')`.
- 2 callsite aggiornati: `+page.svelte` di `assets/[id]` e `fx/[pair]` — passano `tr` come 3° arg.
- i18n nuove: `prices.sync.{noResponse, partialSuffix, skippedSuffix, failedDefault, noChanges, manualOnly}` — **6 chiavi × 4 lingue = 24 entries**. Accenti ripristinati via script Python (FR: "réponse", "ignoré", "échec", "donnée déjà à"; IT: "già").

**Bug C — tracked, non fixato** (regressione goBack da asset detail → fx detail → back):
- **I-bis #25 — goBack regression `/fx/{pair}` → `/fx` instead of `/assets/{id}`** ⏳ PENDING
- **Sintomo**: dall'asset detail cliccando il nuovo link FX quick-access si naviga a `/fx/{slug}`. Cliccando il bottone back sulla pagina FX detail si torna a `/fx` (lista) invece che tornare all'asset detail di partenza.
- **Ipotesi**: `navigationStore.depth` potrebbe non essere incrementato correttamente per navigazioni via `<a href>` (anche se SvelteKit dovrebbe gestirle come SPA navigation e triggerare `afterNavigate` con `nav.type='link'`). Oppure `history.back()` è corretto ma FX detail fa `goto(..., {replaceState: true})` in qualche path che rompe lo stack.
- **Possibili fix**:
  - (a) Sostituire `<a href>` con `onclick={() => goto(fxPairUrl)}` → forzare esplicitamente il routing SPA.
  - (b) Investigare `fx/[pair]/+page.svelte` linea 662 `goto(..., {replaceState: true})` — potrebbe sovrascrivere l'entry della history che doveva contenere l'asset detail.
  - (c) Salvare un `referrer` in sessionStorage al momento del click sul link, e al back del FX detail usare quel referrer invece del fallback `/fx`.
- **Priorità**: P2 — la navigazione funziona (back del browser dovrebbe funzionare comunque), solo il bottone custom "back" del FX detail ha comportamento imprevisto. Rimandato a batch 3 o successivo.

**File toccati in batch 2 part2**:
- `frontend/src/lib/components/assets/AssetPriceSummary.svelte` (icona ExternalLink → ArrowLeftRight).
- `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` (3 stringhe tradotte).
- `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` (#12 refactor: progress toasts → inline spinner).
- `frontend/src/lib/components/assets/AssetModal.svelte` (rimosso toast duplicato saveSuccess nel callback currency change).
- `frontend/src/lib/utils/syncToastHelpers.ts` (#1+#23 refactor: 5 stati + i18n suffixes).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (passa tr a buildAssetSyncToast).
- `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (idem).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+9 chiavi: 3 dataEditor + 6 prices.sync).

**Validazione batch 2 part2**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py front format` → ✅ all unchanged.

**i18n cumulativo batch 2 part1+1b+1c+2** (da committare separatamente da part1/1b/1c già commitati):
- Part2: 9 nuove chiavi × 4 lingue = **36 entries**.

### 📍 Batch 2 part3 (2026-04-23 mattina, 5° giro feedback utente)

**Feedback utente che ha scatenato part3**:
1. Link FX nel filterBar c'è ma icona era generica (`Coins` → l'utente l'ha corretta in commit precedente — **nessun'azione** qui).
2. `goBack` su FX detail torna sempre a `/fx` invece che all'asset di origine. L'utente ricorda che esisteva un sistema di "stack di pagine" con reset sui click sidebar — va verificato perché non funziona più.
3. Toast currency change: con valuta non fornita dal provider, il toast dice **sia** "currency changed" **sia** "refreshed with success", ma la refresh è fallita. L'utente vuole 2 toast distinti: "delete success" + "sync result" (via `buildAssetSyncToast`, come fa `/assets` global che dà toast perfetti tipo `"Sincronizzazione fallita per Apple Inc.: DB upsert failed: Currency mismatch ..."`).
4. BTP Italia 2028: configurato DAILY + no-cedola, primi mesi grafico cresce (retta), poi si resetta a 10000 e resta piatto. Cambiando frequenza non cambia nulla → sospetto hashing cache broken.

**Fix I — goBack regression (refactor `navigationStore.ts` stack-based)**:
- Root cause identificato: il sistema `depth` con `history.back()` era fragile perché altre pagine fanno `history.replaceState` / `goto({replaceState:true})` che corrompono la browser history. **Fix**: rifatto `navigationStore.ts` con **stack esplicito di pathnames** (`string[]`).
  - `trackNavigation(type, pathname)`: push su link/goto/form, pop su popstate, reset su enter. Dedup su push consecutivo stesso pathname (per gestire replaceState con stesso path ma diversa query).
  - `goBack(fallback)`: se stack ha ≥2 entry → pop + `goto(stack[top])`. Altrimenti `goto(fallback)`.
  - `resetNavDepth()`: svuota lo stack (chiamato dalla Sidebar sui click top-level, pattern già esistente).
  - Aggiunto helper `_debugStack()` per diagnostics.
- `+layout.svelte`: `trackNavigation(nav.type, nav.to?.url.pathname)` (path passato esplicitamente).
- Nota: usa `goto` invece di `history.back()` per determinismo — costo: una nuova entry in history, ma risoluzione pulita.
- **Sidebar era già OK** (`resetNavDepth()` chiamato sui 3 link principali): grep confermato. Il bug era solo nella logica di `goBack`.

**Fix II — Toast currency change v2 (2 toast distinti)**:
- `AssetCurrencyChangeModal.svelte` refactor di `handleConfirm`:
  - Inline spinner (delete/patch/sync) resta per UX feedback (I-bis #12).
  - **Toast #1** — `deleteSuccess`: "Deleted N prices" — sparato appena la DELETE risolve.
  - **Toast #2** — `changedTo`: "Currency changed from X to Y" — sparato appena la PATCH risolve (sempre, quando delete+patch OK).
  - **Toast #3** — sync outcome via `buildAssetSyncToast(r, tr('common.sync'), tr)`: 5 stati (ok / noChanges / partial+msg / skipped / error). In caso di exception, surface del `response.data.detail` del backend (es. "DB upsert failed: Currency mismatch for asset 1: expected EUR ...") via `toasts.error`.
  - Rimosso il vecchio `toasts.success(currencyChange.done)` e il `warning(syncFailedManualRetry)` (entrambi sostituiti dalla logica sopra).
- i18n nuove: `assetDetail.currencyChange.{deleteSuccess, changedTo}` (4 lingue, accenti FR fix via script).
- **Differenza rispetto al flow `/assets` global**: la global usa il costrutto `toasts.success($t('assets.sync.toastOk'))` / `toasts.error($t('assets.sync.toastFailed') + ': ' + r.errors[0])`. Ora il currency change flow usa `buildAssetSyncToast` che è **strettamente più espressivo** (gestisce partial, skipped, noChanges, aggiunge icons SVG inline per prezzi/eventi). Volendo in futuro si può migrare anche `/assets` global al helper, per uniformità totale.

**Fix III — Icona FX corretta dall'utente** (verificata in AssetPriceSummary.svelte): ora usa `Coins` (icona monete, più evocativa di valuta rispetto a ArrowLeftRight che è per le coppie FX directional). **No action needed**.

**Fix IV — DataEditor i18n completato** (dal feedback part2): bottoni "Import CSV" / "Add Row" + empty-state message tradotti. i18n: `dataEditor.{importCsv, addRow, emptyMessage}` (già in part2).

**Indagine V — BTP Italia 2028 (tracked come I-bis #26)**:
- `db_populate`: passato BTP Italia 2028 da `SEMIANNUAL` + `generate_interest=True` a **`DAILY` + `generate_interest=False`** (request utente). Prossimo `db create-clean` produrrà la retta lineare pulita.
- Aggiunto logging debug in `_generate_schedule_values`: `cache HIT/MISS key=... periods=... first_freq=... first_gen_int=...`. Dal prossimo retest l'utente può vedere se il cache key cambia realmente quando modifica la config.
- Bug reset **non** fixato in questa sessione (scope troppo grande, richiede riordino Step 2/4 + regression test + verifica frontend editor). Documentato come I-bis #26 con 2 bug candidati + 3 ipotesi hashing + action items.

**Elenco flussi toast asset — prima/dopo (per decisione collettiva)**:

| Scenario | Prima (pre-batch2) | Dopo part2 | Dopo part3 (ora) |
|---|---|---|---|
| Sync normale OK (/assets global) | ✓ 1 success "N fetched, M changed" | identico (non toccato) | identico |
| Sync KO (/assets global) | ✓ 1 error "Sync failed per {name}: detail" | identico | identico |
| Sync dal detail (handleSyncAsset signal) | ✓ 1 toast via buildAssetSyncToast (hardcoded EN suffixes) | ✓ 1 toast via buildAssetSyncToast (5 stati i18n) | identico part2 |
| Currency change (provider assigned, sync OK) | 5 toast: 3 progress info + 1 success done + 1 success saveSuccess | 1 toast success done | **3 toast**: deleteSuccess + changedTo + syncOk |
| Currency change (provider assigned, sync PARTIAL) | 5 toast (come sopra) | 1 toast success done ❌ fuorviante | **3 toast**: deleteSuccess + changedTo + syncWarning con result.message |
| Currency change (provider assigned, sync FAIL es. Currency mismatch) | 5 toast + 1 warning syncFailedManualRetry | 1 success done + 1 warning generic ❌ | **3 toast**: deleteSuccess + changedTo + **error con detail backend** |
| Currency change (NO provider) | 3 toast (progress + done + saveSuccess) | 1 toast done | **2 toast**: deleteSuccess + changedTo |
| Currency change (delete KO) | error | error failed | identico part3 (error, toast #1 non parte) |
| Currency change (patch KO) | error | error failed | identico part3 (toast #1 parte, #2 no) |

**Raziocinio**:
- Part2 puntava alla minimizzazione (1 solo toast) ma perdeva informazioni importanti (l'errore sync post-wipe veniva nascosto).
- Part3 trova il giusto equilibrio: **1 toast per ogni step significativo**. Delete è un'operazione distruttiva — meritocraticamente degna di conferma. Patch è rapida ma produce la notifica chiave "currency changed" che l'utente si aspetta. Sync ha tutti i suoi stati compressi nel unified helper.

**File toccati in batch 2 part3**:
- `frontend/src/lib/stores/navigationStore.ts` (refactor stack-based + debug helper).
- `frontend/src/routes/(app)/+layout.svelte` (pass pathname to trackNavigation).
- `frontend/src/lib/components/assets/AssetCurrencyChangeModal.svelte` (3-toast refactor + buildAssetSyncToast integration).
- `frontend/src/lib/i18n/{en,it,fr,es}.json` (+2 chiavi: `currencyChange.{deleteSuccess, changedTo}`).
- `backend/test_scripts/test_db/populate_mock_data.py` (BTP Italia 2028 → DAILY + no interest).
- `backend/app/services/asset_source_providers/scheduled_investment.py` (+logging debug cache HIT/MISS).

**Validazione batch 2 part3**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- Backend format/lint → da rifare (ho modificato 2 file Python).

**Da testare con utente prima del commit**:
1. goBack FX → asset detail: deve tornare al detail corretto, non alla lista FX.
2. Toast currency change: 3 toast distinti (delete + changedTo + sync esito reale).
3. BTP Italia 2028: dopo `./dev.py db create-clean`, grafico deve essere retta pulita (no reset).
4. Log debug: `./dev.py server start` + sync BTP, cercare "scheduled_investment cache" nei log.

### 🎯 Cosa devo fare dopo (priorità in ordine)

**Prossimo commit suggerito**: batch refactor `FxBackwardFillInfo` da solo (piccolo e coeso). Messaggio:
```
Refactor: extract FxBackwardFillInfo as standalone building block

- Create FxBackwardFillInfo in common.py (fx_rate_date + fx_days_back).
- AssetBackwardFillInfo now inherits from BackwardFillInfo + FxBackwardFillInfo.
- FAAssetEventPointOut replaces flat fx_rate_date/fx_days_back with a single
  fx_info: Optional[FxBackwardFillInfo]. Events have no price-backward-fill
  semantics (discrete real dates) — only FX staleness is meaningful.
- Frontend +page.svelte reads ev.fx_info?.fx_rate_date / .fx_days_back.
- Tests updated to nested access.
- Wire format for prices is unchanged (mixin preserves field order).
```

**Poi batch 2** (~4-5h): I-bis UX quick wins
- **#3** Tab label "Prices in {currency} 🇺🇸" → 20 min (`AssetDataEditorSection.svelte`) ✅ DONE (batch 2 part1)
- **#4** Import CSV banner reminder → 20 min (`PriceDataImportModal.svelte`) ✅ DONE (batch 2 part1)
- **#6** Empty-state "Add manually" → 40 min (panel con 0 prezzi) ✅ DONE (batch 2 part1)
- **#12** Ridurre 5 toast currency-change → 1 (refactor `AssetCurrencyChangeModal.svelte`) ✅ DONE (batch 2 part2)
- **#1 + #23** combinati: handler unificato `PriceSyncResponse` con 5 stati toast i18n (ok/noChanges/partial+msg/skipped/failed) ✅ DONE (batch 2 part2)

**Prossimo batch 2.5** (~1h): retest + possibile fix I-bis #25 (goBack regression)
- Retest manuale I-bis #12 (flow currency change con e senza provider) + I-bis #1+#23 (sync che restituisce 0 changes, status partial, etc.).
- Se I-bis #25 è bloccante, fix (opzione a/b/c proposte nel journal).

**Batch 3** (~3-4h): Test coverage Blocco G (ordine per valore decrescente)
- **G.6** `test_ohlc_sentinel.py` — 8 casi (copre Blocco F dichiarato done ma non testato).
- **G.10** `test_asset_currency_change.py` — 5 casi (copre I.3 + I.6, flusso wipe+PATCH+re-sync).
- **G.11** `test_asset_prices_export.py` — 7 casi (copre I.4, endpoint `/prices/export`).
- **G.5** `test_prices_currency_coherence.py` — 3 casi post-I.11 (versione ridotta dopo i drop).

**Batch 4** (~4h): Test Blocco G coda + I-bis #22 prerequisito Part 4/5
- **G.3** `test_transactions_validate.py` — 6 casi.
- **G.4** `test_events_suggest.py` — 5+ casi parametrizzati.
- **G.1/G.2** estensioni `test_transaction_service.py` + matrix `test_transactions_api.py` (10+casi combinati).
- **G.7** entries nel `scripts/test_runner.py` (mancano ancora: transactions-validate, events-suggest, prices-currency, ohlc-sentinel, assets-currency-change, assets-prices-export).
- **G.8** coverage verification: `./dev.py test coverage services transaction` (target ≥90%) e `asset-source` (target ≥85%).

**Batch 5** (~3-4h): I-bis #22 refactor error handling
- Helper `$lib/utils/saveWithRetry.ts` o store `createSaveAction<T>`.
- Censimento dei modal impattati (AssetModal, AssetProviderAssignmentModal, AssetCurrencyChangeModal, BrokerModal, PriceDataImportModal, DataEditor save, futuro TransactionModal).
- Rollout progressivo + i18n `save.failed.*`.

**Batch 6** (~1h): code tails
- **#2** Provider dirty gating per "Save Without Testing?"
- **#5** CSV import resilience (auto-detect separator + header tolerance).
- **#7** `patch_assets_bulk` HTTP 409 semantics (non urgente).
- **I.10** validazione finale Blocco I (run completo test suite).
- Aggiornamento `phases/phase-07-transactions.md` con stato "Part 3 completed".
- Archiviazione plan chain in `phases/phase-07-transactions-subplan/` (skill `plan-archive`).

### ⚠️ Gotcha / note operative da ricordare

1. **Pipeline UTF-8 in shell**: `echo "é"` dal prompt zsh strippa accenti. Per aggiornare file `i18n/*.json` con caratteri non-ASCII → scrivere uno script `.py` a file (`/tmp/libreFolio_*.py`) + lanciarlo. Esempio già presente: `/tmp/libreFolio_restore_fr_indent.py`. **Non usare** `json.dump(..., indent=4)` su `fr.json`: il file usa indent=2 (come en/it/es) e `indent=4` fa un mega-diff di 2000 righe.
2. **Test FX pair pollution**: nel test DB alcune coppie (EUR/USD, GBP/USD) possono avere rate già seedati da altri test → le assertion su valore esatto falliscono. Per nuovi test: usare coppie esotiche (NZD/SGD, ILS/PHP, CAD/ZAR) + `_ensure_fx_rate` helper già presente in `test_events_target_currency.py`.
3. **`./dev.py lint --fix`**: dopo una cleanup (es. rimozione fx_error), può capitare di lasciare import orfani. Sempre girare `lint --fix` se `lint` segnala 1 errore auto-fixabile.
4. **Sintassi `./dev.py i18n add`**: richiede flag `--en --it --fr --es` (non posizionali). Esempio: `./dev.py i18n add foo.bar --en "Foo" --it "Bar" --fr "Baz" --es "Qux"`. Gli accenti **vanno comunque sistemati a mano dopo** (lo script strippa i chars non-ASCII in un pass intermedio).
5. **Non eseguire mai `git commit`** — solo proporre messaggi (regola copilot-instructions). Oggi sto scrivendo i messaggi in `/tmp/libreFolio_commit_*.txt` e l'utente committa.
6. **`requiredFxPairs` derived in `+page.svelte` L267–337**: non esiste un componente `FxPairBanner` separato — il banner è inline nel `{#each pairs}` a L1081–1153. Se si vuole riusare altrove (Phase 9 Dashboard), estrarlo prima in componente.
7. **FxBackwardFillInfo wire format**: `{fx_rate_date: "YYYY-MM-DD" | null, fx_days_back: number | null}`. Lato FE è `Partial<{...}>` (Zod) quindi entrambi i campi sono tecnicamente opzionali anche quando l'oggetto è presente — usare sempre optional chaining `obj?.fx_rate_date`.
8. **Emoji in Python scripts per i18n**: MAI usare escape surrogate pair (`\ud83d\udce5`) perché `write_text(encoding='utf-8')` fallisce con `UnicodeEncodeError: surrogates not allowed` DOPO aver truncato il file → file i18n azzerato. Alternative sicure: `\N{INBOX TRAY}` (Python named-char escape) oppure leggere l'emoji da un file già presente (es. `en.json`) e riusarla. Recovery: `git checkout HEAD -- frontend/src/lib/i18n/fr.json` + script che riapplica tutte le chiavi della sessione.

### ✅ Check-list di "sessione riaperta correttamente"

Quando la conversazione riparte, verificare:
- [ ] `git log --oneline | head -5` → identificare ultimo commit Closure (cercare "Part 3 Closure" o "FxBackwardFillInfo").
- [ ] `git status` → capire se ci sono file pendenti del refactor FxBackwardFillInfo (se sì, vedi sopra batch).
- [ ] Leggere questa sezione **Giornale di viaggio** per localizzare il cursore.
- [ ] Scorrere il Closure plan dall'alto cercando sezioni ancora **senza** ✅ DONE nel titolo → ordine di attacco.
- [ ] Verificare che i test API sopracitati passino (`./dev.py test api assets-price && assets-events && events-target-currency`). Se rossi → NON procedere: qualcosa nella sessione precedente è rimasto monco.

### 📍 Batch 2 part4+5 — fix #R3-1 + #R3-2 + #R3-4 (2026-04-23 mezzogiorno)

Implementati 3 dei 4 issue emersi nel retest batch 2 part3. #R3-3 (policy `asset_events` al
cambio currency) rimane in sospeso: richiede decisione utente fra policy A (niente) /
B (delete non-manual + re-sync) / C (conversione FX).

**Decisioni di design (riviste durante la sessione)**:
- **#R3-2**: la proposta iniziale era "(a) BE force FAILED when upsert fails + (c) FE fallback a `errors[0]`".
  Discussione con l'utente: il bug vero è che **`fetched_count` conta anche i punti con currency
  inesatta**. Quei punti, dal punto di vista dell'asset, sono indistinguibili da "no data". Fix
  finale: **filtro pre-count** nel sync, prima del bulk_upsert. Gli scartati vanno in `errors`
  con messaggio aggregato tipo "20 points discarded: currency mismatch (got 20 USD, expected
  EUR)". `fetched_count` conta solo gli accettati → `status=FAILED` cade naturalmente. Nessuna
  modifica FE.
- **#R3-4**: la proposta iniziale era "(a) hash params in cache key + (c) banner opt-in dopo
  params change". Discussione con l'utente: per `scheduled_investment` (provider *particolare*
  dove i params **definiscono** la serie) il wipe+resync dev'essere **atomico sulla Save**,
  previa conferma esplicita. Niente banner post-fatto da cliccare come seconda azione.
  Fix finale: **(a) cache key params-aware + (b) ConfirmDialog al Save che, confermato, fa
  PATCH+assign+wipe+resync in un unico flow**. Gated su `provider_plugin_key ==
  'scheduled_investment'` per non toccare provider esterni (yfinance, ECB, …).

**File toccati**:
- `frontend/src/lib/components/assets/AssetPriceSummary.svelte` — #R3-1: sostituzione
  `<a href={fxPairUrl}>` con `<button onclick={() => goto(fxPairUrl)}>`. Il `Tooltip` wrapper
  chiama `stopPropagation()` sui click, che per un `<a>` reale provoca full-page reload →
  `navigationStore` resetta lo stack → `goBack` perde la destinazione. Il `<button>` con handler
  esplicito esegue SPA navigation e preserva lo stack.
- `backend/app/services/asset_source.py` — #R3-2: in `_fetch_single`/`_persist_single` (sync
  per singolo asset) aggiunto filtro pre-count dei punti con `currency != asset.currency`.
  Messaggio aggregato in `errors`. Popolato `message = errors[0]` nel ramo errors (FAILED o
  PARTIAL) perché il FE lo mostra direttamente nel toast.
- `backend/app/services/asset_source.py` — #R3-4 (a): helper `_provider_params_hash()` MD5 su
  `json.dumps(params, sort_keys=True)[:8]` + cache key estesa a 4-tupla `(provider_code,
  identifier, identifier_type, params_hash)` per `_asset_history_cache` e
  `_asset_current_cache`.
- `backend/app/services/asset_source.py` — #R3-4 (b): in `bulk_assign_providers`, quando
  l'assignment esistente è `scheduled_investment` e `existing.provider_params !=
  params_to_store`, atomicamente: `DELETE FROM price_history WHERE asset_id=X AND
  source_plugin_key='scheduled_investment'` + `.delete()` delle vecchie chiavi cache con hash
  dei params pre-update. La logica è scope-limited a `scheduled_investment`.
- `frontend/src/lib/components/assets/AssetModal.svelte` — #R3-4 (c): nuovo stato
  `showScheduledRegenConfirm` + `ConfirmModal` "Regenerate Prices?" mostrato all'inizio di
  `saveEdit` quando il provider è `scheduled_investment` AND `providerParams` differiscono da
  `initialProviderParamsJson` (snapshot iniziale catturato in `loadFromData`). Alla conferma:
  prosegue la `saveEdit` normale (PATCH+assign, che BE fa wipe+invalidate automaticamente),
  poi chiama `sync_prices_bulk_api_v1_assets_prices_sync_post` con range 5 anni per
  rigenerare i prezzi. Il flag `pendingSaveAssetId` evita il loop di riapertura modal al
  secondo passaggio.
- `frontend/src/lib/i18n/{en,it,fr,es}.json` — +3 chiavi:
  `assets.modal.scheduledRegenTitle`, `assets.modal.scheduledRegenMessage`,
  `assets.modal.scheduledRegenConfirm`. Accenti FR/IT/ES ripristinati via script
  `/tmp/libreFolio_fix_accents_r34.py`.

**Validazione**:
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `./dev.py lint --fix && ./dev.py format` → ✅ clean (1 file riformattato da black).
- `pipenv run pytest backend/test_scripts/test_utilities/test_provider_core_cache.py` →
  ✅ 20/20 passed.
- `pipenv run pytest backend/test_scripts/test_api/test_assets_prices.py` → 14/16 al primo run;
  i 2 falliti (`test_query_without_sync_returns_empty`, `test_bulk_sync_multi_asset`) sono
  **flaky per timeout `httpcore.ReadTimeout` su yfinance metadata** — rigirati singolarmente
  passano 2/2 in 42s. Pre-esistenti, non correlati alle modifiche.

**Da testare manualmente con utente**:
1. #R3-1: dal dettaglio asset, click icona moneta "Open FX pair" → `/fx/{slug}` → Back →
   torna al dettaglio asset (non alla lista FX).
2. #R3-2: Apple USD con prezzi storici → cambio currency a EUR → il toast post-sync ora è
   **error** con testo tipo `"20 points discarded: currency mismatch (got 20 USD, expected
   EUR)"`, non più un generico warning.
3. #R3-4 confirm path: BTP Italia 2028 DAILY → sync → chart retta. Apri modal edit, cambia
   frequency a WEEKLY → click Save → appare `ConfirmModal` "Regenerate Prices?" → Confirm →
   dopo chiusura il chart mostra gradini weekly (non più retta daily).
4. #R3-4 cancel path: stessa modifica, al confirm clicca Cancel → modal si chiude, niente
   PATCH inviata, chart invariato.

**Commit message proposto**: vedi `/tmp/libreFolio_commit_batch2_part45.txt`.

**#R3-3 ancora pending — decisione da prendere con utente**: policy `asset_events` al cambio
currency. La raccomandazione nel plan è **Policy B** (cancella eventi non-manuali + re-sync),
ma richiede conferma prima dell'implementazione perché impatta il wizard E2E e i test.

**Poi batch 2** (~4-5h): I-bis UX quick wins
- **#3** Tab label "Prices in {currency} 🇺🇸" → 20 min (`AssetDataEditorSection.svelte`) ✅ DONE (batch 2 part1)
- **#4** Import CSV banner reminder → 20 min (`PriceDataImportModal.svelte`) ✅ DONE (batch 2 part1)
- **#6** Empty-state "Add manually" → 40 min (panel con 0 prezzi) ✅ DONE (batch 2 part1)
- **#12** Ridurre 5 toast currency-change → 1 (refactor `AssetCurrencyChangeModal.svelte`) ✅ DONE (batch 2 part2)
- **#1 + #23** combinati: handler unificato `PriceSyncResponse` con 5 stati toast i18n (ok/noChanges/partial+msg/skipped/failed) ✅ DONE (batch 2 part2)

**Prossimo batch 2.5** (~1h): retest + possibile fix I-bis #25 (goBack regression)
- Retest manuale I-bis #12 (flow currency change con e senza provider) + I-bis #1+#23 (sync che restituisce 0 changes, status partial, etc.).
- Se I-bis #25 è bloccante, fix (opzione a/b/c proposte nel journal).

**Batch 3** (~3-4h): Test coverage Blocco G (ordine per valore decrescente)
- **G.6** `test_ohlc_sentinel.py` — 8 casi (copre Blocco F dichiarato done ma non testato).
- **G.10** `test_asset_currency_change.py` — 5 casi (copre I.3 + I.6, flusso wipe+PATCH+re-sync).
- **G.11** `test_asset_prices_export.py` — 7 casi (copre I.4, endpoint `/prices/export`).
- **G.5** `test_prices_currency_coherence.py` — 3 casi post-I.11 (versione ridotta dopo i drop).

**Batch 4** (~4h): Test Blocco G coda + I-bis #22 prerequisito Part 4/5
- **G.3** `test_transactions_validate.py` — 6 casi.
- **G.4** `test_events_suggest.py` — 5+ casi parametrizzati.
- **G.1/G.2** estensioni `test_transaction_service.py` + matrix `test_transactions_api.py` (10+casi combinati).
- **G.7** entries nel `scripts/test_runner.py` (mancano ancora: transactions-validate, events-suggest, prices-currency, ohlc-sentinel, assets-currency-change, assets-prices-export).
- **G.8** coverage verification: `./dev.py test coverage services transaction` (target ≥90%) e `asset-source` (target ≥85%).

**Batch 5** (~3-4h): I-bis #22 refactor error handling
- Helper `$lib/utils/saveWithRetry.ts` o store `createSaveAction<T>`.
- Censimento dei modal impattati (AssetModal, AssetProviderAssignmentModal, AssetCurrencyChangeModal, BrokerModal, PriceDataImportModal, DataEditor save, futuro TransactionModal).
- Rollout progressivo + i18n `save.failed.*`.

**Batch 6** (~1h): code tails
- **#2** Provider dirty gating per "Save Without Testing?"
- **#5** CSV import resilience (auto-detect separator + header tolerance).
- **#7** `patch_assets_bulk` HTTP 409 semantics (non urgente).
- **I.10** validazione finale Blocco I (run completo test suite).
- Aggiornamento `phases/phase-07-transactions.md` con stato "Part 3 completed".
- Archiviazione plan chain in `phases/phase-07-transactions-subplan/` (skill `plan-archive`).

### ⚠️ Gotcha / note operative da ricordare

1. **Pipeline UTF-8 in shell**: `echo "é"` dal prompt zsh strippa accenti. Per aggiornare file `i18n/*.json` con caratteri non-ASCII → scrivere uno script `.py` a file (`/tmp/libreFolio_*.py`) + lanciarlo. Esempio già presente: `/tmp/libreFolio_restore_fr_indent.py`. **Non usare** `json.dump(..., indent=4)` su `fr.json`: il file usa indent=2 (come en/it/es) e `indent=4` fa un mega-diff di 2000 righe.
2. **Test FX pair pollution**: nel test DB alcune coppie (EUR/USD, GBP/USD) possono avere rate già seedati da altri test → le assertion su valore esatto falliscono. Per nuovi test: usare coppie esotiche (NZD/SGD, ILS/PHP, CAD/ZAR) + `_ensure_fx_rate` helper già presente in `test_events_target_currency.py`.
3. **`./dev.py lint --fix`**: dopo una cleanup (es. rimozione fx_error), può capitare di lasciare import orfani. Sempre girare `lint --fix` se `lint` segnala 1 errore auto-fixabile.
4. **Sintassi `./dev.py i18n add`**: richiede flag `--en --it --fr --es` (non posizionali). Esempio: `./dev.py i18n add foo.bar --en "Foo" --it "Bar" --fr "Baz" --es "Qux"`. Gli accenti **vanno comunque sistemati a mano dopo** (lo script strippa i chars non-ASCII in un pass intermedio).
5. **Non eseguire mai `git commit`** — solo proporre messaggi (regola copilot-instructions). Oggi sto scrivendo i messaggi in `/tmp/libreFolio_commit_*.txt` e l'utente committa.
6. **`requiredFxPairs` derived in `+page.svelte` L267–337**: non esiste un componente `FxPairBanner` separato — il banner è inline nel `{#each pairs}` a L1081–1153. Se si vuole riusare altrove (Phase 9 Dashboard), estrarlo prima in componente.
7. **FxBackwardFillInfo wire format**: `{fx_rate_date: "YYYY-MM-DD" | null, fx_days_back: number | null}`. Lato FE è `Partial<{...}>` (Zod) quindi entrambi i campi sono tecnicamente opzionali anche quando l'oggetto è presente — usare sempre optional chaining `obj?.fx_rate_date`.
8. **Emoji in Python scripts per i18n**: MAI usare escape surrogate pair (`\ud83d\udce5`) perché `write_text(encoding='utf-8')` fallisce con `UnicodeEncodeError: surrogates not allowed` DOPO aver truncato il file → file i18n azzerato. Alternative sicure: `\N{INBOX TRAY}` (Python named-char escape) oppure leggere l'emoji da un file già presente (es. `en.json`) e riusarla. Recovery: `git checkout HEAD -- frontend/src/lib/i18n/fr.json` + script che riapplica tutte le chiavi della sessione.

### 📍 Retest batch 2 part3 (2026-04-23 mattina, post-commit part2)

Test manuale completo del flow currency-change + Apple USD→EUR→USD + asset manuale + BTP scheduled_investment. Emersi 4 issue, alcuni **lato FE**, altri **lato BE**, uno **di design** (scelta di policy).

**Issue #R3-1 — `goBack` dal link coin quick-FX non funziona, dalla signal card sì**

Sintomo: cliccando il bottone "Open FX pair detail" (l'icona moneta vicino al dropdown "Convert to" in `AssetPriceSummary.svelte`) si va a `/fx/{slug}` ma il bottone "Back" poi fallisce il fallback → l'utente resta sulla detail FX. Invece cliccando lo stesso slug da una signal card sulla dashboard il back funziona correttamente.

**Root cause probabile** (da confermare con debug): il bottone quick-link è renderizzato come `<a href={fxPairUrl}>` **wrappato in `<Tooltip>`**. In `frontend/src/lib/components/ui/Tooltip.svelte` L71-93 l'handler `toggle(event)` e il click esterno chiamano `event.stopPropagation()` (e in certi path `event.preventDefault()`). Se `stopPropagation` ferma l'evento prima che SvelteKit lo intercetti tramite il listener globale di navigation, il browser ricade su **full-page reload** invece di SPA navigation. Dopo il full-reload il modulo JS viene re-inizializzato → `navigationStore` (o equivalente stack che sostiene `goBack`) viene azzerato → al click di "Back" lo stack ha lunghezza 0 → fallback a `/fx` lista.

Le signal card invece usano `goto()` programmatico (senza `<a>` e senza Tooltip), quindi la history SPA viene aggiornata correttamente e `goBack` funziona.

**Opzioni di fix**:
- (a) Rimuovere il `Tooltip` wrapper e usare solo `title=` native HTML (regressione UX minima ma risolve).
- (b) Sostituire `<a>` con `<button onclick={() => goto(fxPairUrl)}>` stylato come link — Tooltip può restare perché non c'è più href da "perdere".
- (c) Modificare `Tooltip.svelte` per NON fare `stopPropagation` quando il click arriva da un elemento figlio che è `<a>` o `<button>` con handler proprio (più invasivo, rischio regressioni in altre pagine).

Raccomandazione: **(b)**. Minimale, aderente al pattern già usato dalle signal card, zero impatto su altri Tooltip.

**Issue #R3-2 — Toast "Sync (partial): 20↓ 0Δ" senza menzione dell'errore di currency**

Flow: Apple con 20 prezzi USD → cambio currency a EUR. Il wizard:
1. Delete 22 prices → `toast.success("Deleted 22 prices")` ✅
2. PATCH currency → `toast.success("Currency changed from USD to EUR")` ✅
3. Auto-sync post-wipe → `toast.warning("Sync (partial): 20↓ 0Δ")` ❌ **atteso: error con messaggio chiaro** "currency mismatch: fetched USD but asset is EUR".

**Root cause (lato BE)** — `backend/app/services/asset_source.py` L2259-2304:
```python
try:
    await AssetSourceManager.bulk_upsert_prices([upsert_obj], persist_session)
    inserted_count = new_count
    updated_count = changed_count
except Exception as e:
    errors.append(f"DB upsert failed: {str(e)}")   # <-- errore catturato
...
# Determine status
message = None
if errors:
    status = SyncStatus.FAILED if fetched_count == 0 else SyncStatus.PARTIAL   # <-- diventa PARTIAL
elif fetched_count > 0:
    ...
```

Quando il backend ha **fetched 20 righe USD** e il bulk_upsert_prices le rifiuta con `HTTPException(400, "Currency mismatch: USD vs EUR")`:
- `errors = ["DB upsert failed: 400: Currency mismatch ..."]`
- `fetched_count = 20 > 0` → `status = PARTIAL` (non FAILED)
- `message = None` (non viene mai popolato dal ramo errors)
- `points_changed = 0` (l'eccezione impedisce di aggiornare i counter)

Il risultato inviato al FE ha `status=partial`, `points_fetched=20`, `points_changed=0`, `message=null`, `errors=[...]`. Il FE (`buildAssetSyncToast` branch partial) legge solo `message`, **ignora `errors`** → toast vago "20↓ 0Δ".

**Riformulazione del bug (dopo discussione utente)**: il problema a monte è che `fetched_count` conta **anche le righe con currency mismatch**, cioè righe che non sono "fetchabili" per questo asset. Un punto con currency sbagliata, dal punto di vista dell'asset, è indistinguibile da "nessun dato disponibile" dal provider. Da qui il toast PARTIAL che maschera un fallimento totale.

**Fix scelto — filtro pre-count lato BE** (`asset_source.py`, blocco sync prezzi):

1. **Prima** di calcolare `fetched_count` e prima del `bulk_upsert_prices`, filtrare il payload del provider scartando i punti con `currency != asset.currency`.
2. Gli scartati vengono aggregati in `errors` con un messaggio tipo `"N points discarded: currency mismatch (got USD, expected EUR)"`.
3. `fetched_count` = len(punti sopravvissuti al filtro). Nel caso Apple USD→EUR → `fetched_count = 0`.
4. La logica esistente `if errors: status = FAILED if fetched_count == 0 else PARTIAL` cade **naturalmente** nel ramo FAILED senza modifiche.
5. Nel ramo FAILED popolare `message = errors[0]` (se non già valorizzato) così il FE ha il testo pronto.

**Niente patch FE**: `buildAssetSyncToast` ramo FAILED già legge `message`. Non serve il fallback `errors[0]` perché lato BE il messaggio è sempre valorizzato.

Vantaggi:
- Fix simmetrico al caso "provider ritorna 0 righe": stesso stato, stesso messaggio.
- Non forza artificialmente PARTIAL→FAILED: è FAILED *per natura*, perché non è stato fetchato nulla di utilizzabile.
- Evita di catturare l'exception di `bulk_upsert_prices` per ricostruire il motivo: la validazione è esplicita e lato sync.

**Issue #R3-3 — [DESIGN] Cosa fare con gli `asset_events` al cambio valuta?**

Attualmente il flow wipe-on-currency-change cancella **solo `asset_prices`** ma **lascia intatti `asset_events`** (dividendi, interessi, split, buyback, …). Gli eventi hanno un campo `original_value = {code, amount}` con la **vecchia currency**.

Impatto concreto: dopo cambio USD→EUR un asset Apple avrà:
- Prezzi nuovi in EUR (ok)
- Dividendi storici salvati con `original_value.code = "USD"` (disallineati)

Il calcolo del P&L userà l'FX rate al momento del consolidamento → funziona, **ma**:
- Il `target_currency=asset` display mostrerà i dividendi in USD storico, non in EUR (UX sorprendente).
- Se la nuova currency riporta eventi dal provider (sync successivo porta dividendi EUR da `yfinance`), si creerà un mix temporale: storico in USD, futuro in EUR.
- Eventi manuali (INTEREST su bond manual) sono inseriti dall'utente con una specifica currency: non vanno toccati senza consenso.

**Tre policy storicamente considerate (per traccia)**:

| Policy | Pro | Contro |
|--------|-----|--------|
| **A) Nulla** (stato attuale) | Zero perdite di dati. | Mismatch semantico visibile nei report. |
| **B) Cancella tutti gli eventi fetched dal provider** (preserva `source=MANUAL`) + re-sync | Coerenza piena con i prezzi. Preserva l'input utente. | UX ambigua: perché tenere i manuali se poi restano disallineati? |
| **C) Convertire `original_value`** via FX rate alla data dell'evento | Conserva tutti i dati. | Dipende da disponibilità FX rate a quella data. Converti-e-ri-converti accumula errori. Eventi manuali modificati senza consenso. |

**Decisione finale (dopo discussione utente, 2026-04-23)** — **Policy D: wipe totale simmetrico + disconnessione transazioni linkate**.

Premesse di design:
1. Il vincolo "event.currency == asset.currency" deve essere **esteso dai prezzi agli eventi** (simmetria I.2 hard-400): un asset_event con currency diversa da quella dell'asset è semanticamente incoerente tanto quanto un prezzo in valuta diversa. Applicare il reject in upsert (endpoint `/assets/events` + import path) con lo stesso pattern di `bulk_upsert_prices`.
2. Al cambio currency, **tutti gli eventi dell'asset** sono "currency-mismatch" rispetto al nuovo valore → vanno **eliminati**, senza distinguere `source=MANUAL` vs `source=PROVIDER`. L'utente conosce il proprio stato e si riassume la responsabilità del re-insert (manualmente o via sync).
3. Se un evento ha **transazioni collegate** (`Transaction.asset_event_id == event.id`, es. dividendo con stacco transazione `DIVIDEND_PAYMENT` abbinata), NON si possono cancellare le transazioni (sono dati contabili indipendenti). La strategia è **disconnettere**: `UPDATE transactions SET asset_event_id = NULL WHERE asset_event_id IN (...)` + `DELETE FROM asset_events WHERE asset_id = ?`.
4. Il modal di conferma deve comunicare chiaramente sia il numero di eventi da eliminare sia il numero di transazioni che verranno disconnesse (ma NON cancellate). Dopo la conferma, l'utente è responsabile di re-inserire/re-associare eventi e transazioni se lo desidera.

**Implementazione BE**:
1. Nuovo endpoint/servizio `wipe_market_data_for_currency_change(asset_id, dry_run=False)`:
   - Count `asset_events` per asset + per `source` (MANUAL vs PROVIDER) — solo per mostrare il breakdown nel modal.
   - Count `transactions` con `asset_event_id IN (events_of_asset)` — per il messaggio di disconnessione.
   - Se `dry_run=False` e confermato:
     - `UPDATE transactions SET asset_event_id = NULL WHERE asset_event_id IN (…)`.
     - `DELETE FROM asset_events WHERE asset_id = ?`.
     - `DELETE FROM price_history WHERE asset_id = ?`.
     - Cache invalidation (history + current).
2. Attuale blocker `CURRENCY_CHANGE_BLOCKED_BY_PRICES` viene generalizzato a `CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA` e include nel payload: `price_count, event_count, linked_tx_count, oldest_date, newest_date`.
3. Hard-400 su upsert event con currency mismatch (nuovo test).

**Implementazione FE**:
1. `AssetCurrencyChangeModal.svelte` esteso con una seconda riga informativa:
   > "This will also delete N events (M manual + K auto-fetched) and disconnect L linked transactions from them (the transactions themselves are preserved). You are responsible for re-inserting any manual data you wish to keep."
2. **Pre-wipe export**: il modal espone **2 bottoni** di download prima della conferma:
   - "Export prices (CSV / JSON)" → endpoint esistente `/assets/{id}/prices/export?format=...`.
   - "Export events (CSV / JSON)" → **nuovo endpoint** (vedi sotto #R3-3b).
3. i18n: `currencyChange.eventsWillBeDeleted`, `currencyChange.linkedTxsWillBeDisconnected`, `currencyChange.exportEventsCsv`, `currencyChange.exportEventsJson` × 4 lingue.

---

**Issue #R3-3b — [DESIGN] Estensione endpoint export: eventi + FX + spostamento in Backup block**

Sull'endpoint esistente `GET /api/v1/assets/{asset_id}/prices/export` c'è un TODO lasciato in precedenza (`backend/app/api/v1/assets.py:649`):
```python
# TODO: spostare l'endpoint nel blocco dei backup e fare una cosa simile anche per le forex e gli eventi.
```

**Design proposto (da implementare in batch dedicato, insieme a #R3-3)**:

1. **Nuovo router `backup_router`** in `backend/app/api/v1/backup.py` (o estensione di `system.py`), montato su `/api/v1/backup`. Scope: export/snapshot read-only di qualsiasi serie storica prima di operazioni distruttive.

2. **Endpoints generalizzati** (tutti `GET ?format=csv|json`, streaming response):
   - `GET /backup/asset/{asset_id}/prices` — equivalente all'attuale `/assets/{id}/prices/export`. L'endpoint vecchio diventa un redirect 308 al nuovo (o è rimosso se nessun consumer esterno).
   - `GET /backup/asset/{asset_id}/events` — NUOVO. Colonne: `date, type, source, amount, currency, fx_rate_date, fx_days_back, original_amount, original_currency, description, provider_assignment_id`.
   - `GET /backup/fx/{base}/{quote}/rates` — NUOVO. Colonne: `date, rate, source_plugin_key, fetched_at`. Rispetta la pair resolution (direzione normalizzata).
   - *(opzionale futuro)*: `GET /backup/asset/{asset_id}/transactions`, `GET /backup/broker/{id}/transactions`.

3. **Response shape**: uniforme fra tipi di serie — un enumerato `BackupScope: prices|events|fx_rates` nei metadati del JSON wrapper:
   ```json
   {
     "scope": "events",
     "entity": {"type": "asset", "id": 42, "slug": "apple-inc"},
     "exported_at": "2026-04-23T10:20:00Z",
     "row_count": 17,
     "rows": [ { ... }, ... ]
   }
   ```
   Il CSV mantiene solo `rows` (header + data, coerente con l'export prezzi attuale).

4. **Helper comune** `_stream_rows_as_csv(iter_rows, filename)` + `_json_snapshot(meta, iter_rows, filename)` in un modulo `backend/app/services/backup_service.py` per evitare duplicazione.

5. **Integrazione con `AssetCurrencyChangeModal`**: il modal chiama i 2 nuovi endpoint `backup/asset/{id}/prices` e `backup/asset/{id}/events` (in sostituzione dell'endpoint legacy) prima di confermare il wipe.

6. **Test** (blocco G.11 esteso, rinominato `test_backup_endpoints.py`):
   - `test_backup_prices_csv_format` (regression dell'export legacy).
   - `test_backup_events_csv_contains_all_columns`.
   - `test_backup_events_empty_returns_header_only`.
   - `test_backup_fx_rates_streaming_large_dataset`.
   - `test_backup_requires_asset_access`.
   - `test_backup_legacy_prices_redirect_308`.

**Priorità**: questo batch di lavoro (R3-3 + R3-3b) va insieme a #R3-3 policy D, **da discutere con utente prima dell'implementazione** per confermare la shape JSON wrapper e la strategia legacy redirect vs remove.

**Issue #R3-4 — Cambio maturation_frequency su scheduled_investment non aggiorna il chart (retta invece dei gradini)**

Flow BTP Italia 2028: schedule inizialmente `DAILY` → sync → chart mostra retta liscia (giusto, un punto/giorno). Utente cambia `maturation_frequency` a `WEEKLY` → PATCH /assets + POST /assets/provider vanno OK (confermato dal payload). Ma:
- Il chart continua a mostrare la retta liscia (niente gradini).
- Il log recente riporta: `scheduled_investment cache HIT key=58957d74 periods=1 first_freq=DAILY first_gen_int=False`.

**Root cause** — **due bachi sommati**:

1. **Cache `_asset_history_cache` non include `provider_params` nella chiave** (`asset_source.py` L2047):
   ```python
   cache_key = (provider_code, identifier, str(prep["identifier_type"]))
   ```
   Per un asset scheduled_investment `identifier` è vuoto (AUTO_GENERATED), quindi la chiave è la stessa **prima e dopo** il cambio a WEEKLY. TTL 15 min → la cache continua a servire la serie DAILY fino alla scadenza naturale.

2. **Cambio `provider_params` NON invalida i prezzi già persistiti**. A differenza del currency-change (che wipe-a i prezzi), modificare la schedule o la frequency del provider **non triggera alcun wipe/resync forzato**. I prezzi DAILY già in `asset_prices` restano; anche se `_asset_history_cache` fosse corretta, il chart legge dal DB → vede la serie fitta.

Il log `first_freq=DAILY` che l'utente ha visto proviene da una chiamata `_generate_schedule_values` che è avvenuta **prima del cambio WEEKLY** (probabilmente lo sync automatico iniziale con config DAILY). Dopo il POST /provider con WEEKLY, la sync successiva può anche usare i nuovi params, ma:
- Se l'utente non ha ricliccato "Sync" dopo il PATCH → i prezzi DAILY restano nel DB e il chart li mostra.
- Se l'utente clicca "Sync" → `_asset_history_cache` HIT (cache key non cambia) → prices_data popolato dalla cache vecchia DAILY → upsert nel DB reinserisce i DAILY → chart resta liscio.

**Fix scelto (dopo discussione utente)** — `scheduled_investment` è un provider *particolare*: i prezzi sono **generati deterministicamente dai `provider_params`**, non fetchati da una fonte esterna. Cambiare `schedule` / `maturation_frequency` / `annual_rate` equivale a dire "la serie precedente è obsoleta per definizione". Quindi:

1. **(a) Cache key con hash `provider_params`** — fix di correttezza sempre valido:
   - In `_asset_history_cache` e `_asset_current_cache` estendere la chiave a `(provider_code, identifier, identifier_type, params_hash)` dove `params_hash = md5(json.dumps(provider_params, sort_keys=True))[:8]`.
   - Esporre un helper `.delete(key)` sulle cache theine (o usare TTL=0 + set con None) per invalidazioni esplicite.

2. **Conferma esplicita + wipe+resync automatico al submit** — specifico per `scheduled_investment`:
   - Nel form di edit dei params provider (frontend), quando l'utente preme "Save" e il diff tocca campi impattanti (`schedule`, `maturation_frequency`, `annual_rate`, …), aprire un **ConfirmDialog**:
     > "Changing these parameters will regenerate all prices for this asset. The existing series will be replaced. Continue?"
   - Se l'utente **conferma**, il FE chiama `POST /assets/provider` con un flag `regenerate=true` (o endpoint dedicato `POST /assets/{id}/provider/regenerate`).
   - Lato BE, dentro la stessa transazione:
     1. `UPDATE assets SET provider_params = ...`
     2. `DELETE FROM asset_prices WHERE asset_id = ? AND provider_plugin_key = 'scheduled_investment'` (scope limitato al provider per non toccare prezzi manuali o di altri provider in scenari futuri).
     3. Invalidate `_asset_history_cache` + `_asset_current_cache` per la vecchia chiave.
     4. Trigger sync immediato con i nuovi params → ripopola `asset_prices` con WEEKLY.
   - Se l'utente **annulla**, nessuna PATCH viene inviata. Lo stato è consistent: prezzi vecchi + params vecchi.

**Differenza vs. la "invalidazione automatica" scartata**: quella avrebbe cancellato i prezzi *silenziosamente* al solo cambio di params. Qui il wipe+resync è **parte integrante** della conferma: l'utente sa che premendo "Continue" sta rigenerando la serie. È un'azione singola dal punto di vista dell'utente (un click su "Save" → un confirm → tutto fatto), non un flow in due fasi con banner post-submit.

**Perché solo per `scheduled_investment`**: per provider esterni (yfinance, ECB, …) cambiare i params non invalida i dati storici (es. cambiare il simbolo secondario di yfinance non dovrebbe buttare via le candele). Quindi la logica di wipe+resync on-confirm è gated sul `provider_plugin_key == 'scheduled_investment'`. Per altri provider, in futuro, si potrà adottare la policy (c) originale (banner opt-in) se serve.

**Rationale sintetico**:
- (a) è un bug fix puro sul caching, indipendente dal resto.
- Conferma esplicita + azione atomica rispetta sia il principio "no azioni distruttive implicite" sia l'UX "un'azione = un click" (niente banner post-fatto da cliccare come seconda operazione).
- Scope-limited al provider `scheduled_investment` perché è l'unico dove i params *definiscono* la serie.

**Nota collaterale**: BTP con retta al posto dei gradini oggi **sembra funzionare** se l'asset è nuovo (nessun prezzo DAILY pregresso). Il bug emerge solo quando si **modifica la frequency** di un asset già syncato. Serve un test E2E dedicato: crea scheduled_investment DAILY → sync → cambia a WEEKLY → sync → verifica che i punti nel DB siano ≤7× rispetto a prima.

---

**Sintesi stato e prossimi passi post-batch2-part3 retest**:

| Issue | Lato | Severità | Fix proposto | Batch target |
|-------|------|----------|--------------|--------------|
| #R3-1 goBack da quick-link | FE (Tooltip) | Media (UX) | Sostituire `<a>` con `<button onclick={goto}>` | Batch 2 part4 (piccolo, ~15min) |
| #R3-2 toast partial invece di error | BE only | Alta (UX fuorviante) | Filtro pre-count: scartare punti con currency mismatch prima di `fetched_count` → cade naturalmente in FAILED con `message=errors[0]` | Batch 2 part4 |
| #R3-3 eventi al cambio currency | BE + FE + design | Alta (correttezza semantica) | **Policy D** (wipe totale simmetrico + disconnessione transazioni) + vincolo currency-mismatch su eventi + nuovo endpoint `backup/events` | Batch 3 (insieme a R3-3b export endpoint refactor) |
| #R3-3b backup endpoints generalizzati | BE + design | Media (refactor) | Nuovo `backup_router` con `/prices`, `/events`, `/fx` + legacy redirect | Batch 3 (combinato con R3-3) |
| #R3-4 cambio params provider non aggiorna chart | BE (cache key) + FE (confirm dialog) | Alta (bug funzionale) | (a) hash `provider_params` in cache key + (b) ConfirmDialog on save → wipe+resync atomico, **solo per `scheduled_investment`** | Batch 2 part5 |

Il commit batch2-part2 è stato fatto dall'utente (vedi `/tmp/libreFolio_commit_batch2_part2.txt`). **Non aprire batch2-part3-retest come nuovo commit finché non si decide la strategia per #R3-3 e si implementano almeno #R3-1 + #R3-2.**

### ✅ Check-list di "sessione riaperta correttamente"

Quando la conversazione riparte, verificare:
- [ ] `git log --oneline | head -5` → identificare ultimo commit Closure (cercare "Part 3 Closure" o "FxBackwardFillInfo").
- [ ] `git status` → capire se ci sono file pendenti del refactor FxBackwardFillInfo (se sì, vedi sopra batch).
- [ ] Leggere questa sezione **Giornale di viaggio** per localizzare il cursore.
- [ ] Scorrere il Closure plan dall'alto cercando sezioni ancora **senza** ✅ DONE nel titolo → ordine di attacco.
- [ ] Verificare che i test API sopracitati passino (`./dev.py test api assets-price && assets-events && events-target-currency`). Se rossi → NON procedere: qualcosa nella sessione precedente è rimasto monco.

### 📍 Batch 2 part4b — generalizzazione `FAProviderKind` + policy R3-3 (2026-04-23 pomeriggio)

Su richiesta utente, dopo il batch 2 part4+5 (che usava ancora l'hardcoded
`provider_code == "scheduled_investment"`), ho generalizzato il discriminante
con un enum di tipo provider sulla classe astratta. Inoltre aggiornata la
sezione R3-3 del plan con la policy finale e un design dedicato per l'endpoint
di export/backup.

**Nuova astrazione — `FAProviderKind`**:
- Enum `StrEnum` in `backend/app/schemas/provider.py` con 2 valori:
  - `ONLINE_SCRAPER` (default): yfinance, justetf, cssscraper, mockprov. I params
    non invalidano i dati storici (provengono da una fonte esterna).
  - `PARAMETRIC_GENERATION`: scheduled_investment. I params **definiscono** la
    serie; un cambio significa "serie obsoleta per definizione".
- Proprietà `provider_kind` aggiunta alla classe astratta `AssetSourceProvider`
  con default `ONLINE_SCRAPER`. Override in `scheduled_investment.py` →
  `PARAMETRIC_GENERATION`. Tutti gli altri provider ereditano il default.
- Esposta sul frontend via `FAProviderInfo.kind` (campo opzionale, default
  backend-side → sempre popolato). Endpoint `GET /assets/provider` aggiornato
  per passare `kind=instance.provider_kind`.

**Refactor backend** (`asset_source.py`, `bulk_assign_providers`):
- Sostituito il check `existing.provider_code == "scheduled_investment"` con
  `prov_instance.provider_kind == FAProviderKind.PARAMETRIC_GENERATION`, via
  `AssetProviderRegistry.get_provider_instance(code)`.
- Il wipe SQL passa da `source_plugin_key == "scheduled_investment"` (hardcoded)
  a `source_plugin_key == a.provider_code` (scope dinamico sul provider stesso).
- Log message generalizzato: `"parametric provider '{code}' params changed …"`.
- Risultato: aggiungere in futuro un secondo provider parametrico (es. un
  calcolatore obbligazionario custom) non richiederà nessuna modifica in
  `asset_source.py` — basterà override di `provider_kind`.

**Refactor frontend**:
- `providerHelpers.ts` esteso: la cache lazy `assetProviderKinds: Map<code, kind>`
  viene popolata insieme a icons/names al primo `ensureAssetProvidersCached()`.
  Nuove helper `getAssetProviderKind(code)` e `isParametricProvider(code)` con
  fallback "online_scraper" sicuro.
- `AssetModal.svelte`: le 2 branch `#R3-4` (confirm dialog trigger +
  post-regenerate sync) ora chiamano `isParametricProvider(providerCode)`
  invece del match diretto sulla stringa. Aggiunto `await
  ensureAssetProvidersCached()` all'inizio di `saveEdit` per garantire che
  la cache sia popolata prima del check.
- `routes/(app)/assets/[id]/+page.svelte`: la derivata `isScheduledInvestment`
  rinominata in `isParametric` e basata su `isParametricProvider(providerAssignment?.provider_code)`.
  La toolbar label resta `assetDetail.recalculate` vs `common.sync` in base
  al kind — funzionalità identica ma desumibile dal dato invece che dal
  codice provider hardcoded.
- **NON** toccati:
  - `ProviderAssignmentSection.svelte` `uiComponent === 'scheduled_investment'`
    (scelta del widget editor, specifica del provider, non del kind).
  - `skipProviderAssignment` in `AssetModal.svelte` (check sul shape dei
    params `providerParams.schedule?.length` → provider-specifico, non
    kind-specifico; generalizzabile in futuro via metodo astratto
    `provider.is_configured(params)`).

**Gotcha svelte-check**: il docstring Python di `FAProviderKind` conteneva
doppi-backtick RST (``VALUE``) che, trasferiti nel JSON schema OpenAPI e poi
in un template-literal TypeScript da `openapi-zod-client`, terminavano
prematuramente il template causando TS2349 "This expression is not callable"
sul metodo `.describe()`. Fix: riscritto il docstring con apici singoli invece
di backtick. Gotcha da aggiungere alla check-list: **docstrings che finiscono
in OpenAPI description devono evitare backtick** (sia singoli che doppi).

**Policy R3-3 aggiornata** (già modificata nel plan L1224+):
- **Policy D** (wipe totale simmetrico + disconnect tx) sostituisce la Policy B.
- Vincolo `event.currency == asset.currency` esteso dai prezzi agli eventi
  (hard-400 su upsert).
- Al cambio currency: tutti gli `asset_events` eliminati (manuali + auto);
  transazioni linkate `Transaction.asset_event_id` vengono **disconnesse**
  (`SET asset_event_id = NULL`) ma NON cancellate — l'utente riassume la
  responsabilità del re-insert.
- Modal di conferma esteso con riga informativa sugli eventi eliminati +
  transazioni disconnesse.
- Export pre-wipe esteso: modal mostra 2 bottoni download (prices + events,
  CSV + JSON cadauno).

**Design endpoint backup R3-3b** (nuova sezione nel plan L1250+):
- Nuovo `backup_router` su `/api/v1/backup` per export read-only di serie
  storiche prima di operazioni distruttive.
- 3 endpoint generalizzati: `/backup/asset/{id}/prices`, `/backup/asset/{id}/events`,
  `/backup/fx/{base}/{quote}/rates`.
- Response shape uniforme con wrapper `{scope, entity, exported_at, row_count, rows}`.
- Helper comune `_stream_rows_as_csv()` + `_json_snapshot()` in
  `services/backup_service.py` per evitare duplicazione.
- Endpoint legacy `/assets/{id}/prices/export` → redirect 308 al nuovo.
- Test suite `test_backup_endpoints.py` (6 casi).

Entrambi (policy D + backup endpoint refactor) sono **da implementare in un
batch dedicato (Batch 3)** insieme — richiedono conferma finale utente prima
del lavoro.

**File toccati in batch 2 part4b**:
- `backend/app/schemas/provider.py` (+enum `FAProviderKind` + campo `kind` su `FAProviderInfo`).
- `backend/app/services/asset_source.py` (+import `FAProviderKind` + proprietà astratta `provider_kind` + refactor check `bulk_assign_providers`).
- `backend/app/services/asset_source_providers/scheduled_investment.py` (+override `provider_kind = PARAMETRIC_GENERATION`).
- `backend/app/api/v1/assets.py` (list_providers popola `kind=instance.provider_kind`).
- `frontend/src/lib/api/generated.ts` (rigenerato da `./dev.py api sync`).
- `frontend/src/lib/api/openapi.json` (rigenerato).
- `frontend/src/lib/utils/providerHelpers.ts` (+cache `assetProviderKinds` + helper `getAssetProviderKind`/`isParametricProvider`).
- `frontend/src/lib/components/assets/AssetModal.svelte` (2 branch `#R3-4` usano `isParametricProvider(providerCode)` invece di string match).
- `frontend/src/routes/(app)/assets/[id]/+page.svelte` (derivata rinominata `isScheduledInvestment → isParametric`, usa `isParametricProvider`).
- `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part3_1_Closure.md` (R3-3 policy aggiornata + R3-3b sezione export endpoint design).

**Validazione**:
- `./dev.py lint && ./dev.py format` → ✅ clean.
- `./dev.py api sync` → ✅ client TS rigenerato con `kind?: FAProviderKind`.
- `./dev.py front check` → ✅ 0 errors, 0 warnings.
- `pipenv run pytest backend/test_scripts/test_utilities/test_provider_core_cache.py` → ✅ 20/20 passed.

**Commit message proposto**: vedi `/tmp/libreFolio_commit_batch2_part4b.txt`.



---

## 🔁 Retest findings — spostati in file companion

> 📄 Le rifiniture **#R4-1 .. #R4-5** emerse dal retest post-commit di batch
> 2 part4b (2026-04-23 pomeriggio) sono state trasferite nel file companion
> [`plan-phase07-transaction-Part3_1_Closure_2.prompt.md`](./plan-phase07-transaction-Part3_1_Closure_2.prompt.md),
> sezione "Retest findings — Batch 2 part4b (#R4-1..#R4-5)".

Riepilogo sintetico (il dettaglio è nel file `_2`):
- **#R4-1** — R3-2 messaggio Pydantic troppo tecnico → short-circuit quando
  tutti i punti sono filtrati per currency mismatch.
- **#R4-2** — ConfirmModal R3-4 giallo → rosso (variante `danger`).
- **#R4-3** — Grafico resta retta dopo regen WEEKLY (bloccato su diagnosi
  Network trace utente; 3 ipotesi in lista).
- **#R4-4** — Warning BE `FAProviderAssignmentResult.metadata_updated` non
  esistente (refactor leftover).
- **#R4-5** — Feature: toasts `console.log` in modalità DEV
  (`import.meta.env.DEV`).
