# 17 — Stabilizzazione suite — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/17_stabilizzazione_suite_completa.md) (2026-08-07, post-`be8394bb`)
> Metodo: analisi statica read-only; NESSUN test eseguito (run full in corso, DB condiviso).
> I numeri (15/15 categorie verdi, 90,66 % combinata) non sono riproducibili
> staticamente: verificata la STRUTTURA (fix presenti nel codice, selettori, guardie,
> registrazione runner). Working tree beta del 02/09 incluso.

---

## Sintesi esecutiva

**I tre blocchi del report 17 sono tutti ANCORA VALIDI: i fix sono presenti nel codice
attuale, esattamente nella forma documentata, e in due casi su tre ulteriormente
irrobustiti dalle ondate beta.**

- **B1** (runner che distruggeva il DB dei fixture): il rimedio `_api_setup()` è a
  `_backend_api.py:562-577` con docstring che racconta la causa, agganciato alla
  categoria con `setup=_api_setup` (`:639`). L'ordine delle categorie che creava il
  problema è immutato (`_suites.py:22`), quindi il fix resta strutturalmente necessario
  — e presente. L'helper `fixture_user_id()` esiste (`test_risk_api.py:49-65`) ed è
  usato dai due test (`:338,:482`).
- **B2** (eventi spariti su cache prezzi): il fall-through senza early return è a
  `assets/[id]/+page.svelte:1141-1144`, con commento che documenta il bug; le tre
  protezioni tracciate dal report (`loading`, `chartData`, `catch`) sono tutte al loro
  posto (`:1149,:1165,:1189`). Il «non ha fratelli» regge: `loadComparisonData.ts:44`
  fetcha sempre, nessun percorso di cache nato nel frattempo.
- **B3** (selettore Cash marcito): **zero** `input[type="number"]` residui nelle spec
  transazioni; `input[data-testid$="-amount"]` ovunque (9 spec). Di più: le guardie
  `isVisible().catch(() => false)` sui campi obbligatori sono state sostituite da
  `expect(...).toBeVisible()` dure (`transactions-modals.spec.ts:55-66`) — la
  raccomandazione trasversale del report applicata nel punto esatto dove era nata.

**Il buco di misurazione più grande del progetto è chiuso**: la copertura JS/Svelte
esiste (istanbul end-to-end, `d1622ee5` 2026-08-30) — vedi § Buco frontend.

Le modifiche del working tree alle spec transazioni (rework T4: addio
`TransactionDeleteModal`) **non introducono nessuna delle patologie dei report 15/16**:
campione completo dei diff — zero asserzioni tautologiche, zero container-only; la
spec `tx-delete.spec.ts` riscritta asserisce il *payload di rete* (`payload.deletes`),
non i contenitori.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| 15/15 categorie verdi | ✅ misurato | **ANCORA VALIDO come struttura; esito NON VERIFICABILE** | 7 categorie backend (`_suites.py:22`) + 8 frontend (`:23`) = 15; esito verde non riproducibile (vincolo no-test) | — |
| Copertura combinata 90,66 % (36 891 stmt) | misura | **NON VERIFICABILE STATICAMENTE** | vincolo no-test; il dato resta l'ultima misura completa dichiarata | rieseguire a run corrente conclusa |
| B1: `_ensure_db_populated` replicato in `api_test()` | fixato | **ANCORA VALIDO (forma evoluta)** | `_api_setup()` `_backend_api.py:562-577` (`db_populate(force=True)` + docstring-causa), wired `setup=_api_setup` a `:639`; il pattern frontend vive in `_frontend_common.py:159` (era `:46`) e in 10+ siti | — |
| B1: `fixture_user_id()` con `scalar_one_or_none` + messaggio di rimedio | fixato | **ANCORA VALIDO** | `test_risk_api.py:49-65` (messaggio: «Seed them with: ./dev.py test db populate --force»), chiamato a `:338,:482` — boilerplate deduplicato come promesso | — |
| B1: effetto collaterale — `test_broker_access_api.py:565` ora eseguito davvero | osservazione | **ANCORA VALIDO** | il test esiste (`:554`) e la guardia di skip (`:564-565`, «First user is not superuser») resta come rete per DB non puliti: corretto che ci sia — scatta solo a precondizione violata | — |
| B1: datazione difetto ≤ 2026-05-04 | storia | **NON RIVERIFICATA** (non rilevante: il fix c'è) | — | — |
| B2: rimosso early return su cache prezzi; fetch minima `include_price:false, include_events:true` | fixato | **ANCORA VALIDO** | `+page.svelte`: commento «No early return here: events travel in the same response as prices…» `:1141-1144`; `include_price: !pricesFromCache` `:1157`; `include_events: true` `:1158`; `events = result.events ?? []` assegnato su **ogni** percorso `:1168` | — |
| B2: tre protezioni del fall-through | tracciate | **ANCORA VALIDO** | `loading = !pricesFromCache` `:1149`; `if (!pricesFromCache)` su `chartData` `:1165`; `catch` imposta `error` solo `if (chartData.length === 0)` `:1189` | — |
| B2: datazione `5f4fabd05` (2026-07-23) | storia | **VERIFICATO** | `git log -1 5f4fabd05` → 2026-07-23 «feat: add backend signals and isolate sessions» | — |
| B2: nessun fratello (`loadComparisonData.ts` senza cache) | verifica | **ANCORA VALIDO** | `loadComparisonData.ts:38-44`: `include_events: true` + fetch diretto, nessuno store/consultazione cache | — |
| B2: debito di test in `asset-event-delete.spec.ts` (conteggi, distruttività, indipendenza) | corretto | **ANCORA VALIDO in forma evoluta** | la spec è stata riscritta: documenta i **due** eventi unlinked di Apple (`:77`) e il vincolo del secondo test sul 3M dove ogni evento è collegato (`:79,:195-199`); «Apple must have events» ora è `expect.poll(...).toBeGreaterThan(0)` con messaggio azionabile (`:199`); attese su `data-busy` invece di sleep (`:37`) | — |
| B3: `input[type="number"]` → `input[data-testid$="-amount"]` in 7 file | fixato | **ANCORA VALIDO** | `grep 'input\[type="number"\]' frontend/e2e/transactions/` → 0; il nuovo selettore è in `transactions-modals` (:58,:219), `tx-crud-full` (:60,:157), `tx-commit-all-types` (:139; form duale `:148,:158`), `tx-wac-bulk` (:121), `tx-wac-formmodal` (:113), `tx-fx-implied-rate` (:74), più i nuovi nati `tx-bulk-promote-exec` (:168) e `tx-bulk-suggest-ux` (:365) | — |
| B3: bug latente `.first()` sulla tendina valuta → scopo `.currency-wrap` | fixato | **ANCORA VALIDO** | `tx-fx-implied-rate.spec.ts:59,66` con commento che spiega il trabocchetto (`:62-64`); inoltre `fillCash` ora apre con `expect(cashWrap).toBeVisible()` dura (`:56`) | — |
| B3: datazione `ee84e078` (2026-06-05) | storia | **VERIFICATO** | `git log -1 ee84e078` → 2026-06-05 | — |
| Raccomandazione trasversale: guardie `isVisible().catch(() => false)` solo su rami opzionali | raccomandazione | **PARZIALE — in miglioramento** | indurite le spec toccate dalle ondate beta/WT (es. `tx-picker-pagination.spec.ts`: `isVisible`+`toBeTruthy` → `expect(validateBtn).toBeVisible()`; `gallery.spec.ts`: loop con 4 guardie annidate → asserzioni dure su fixture deterministico; `tx-tooltips.spec.ts`: sonda istantanea → `waitFor` con razionale). Restano **274 occorrenze** del pattern in 15+ spec (`grep -c`), la maggior parte su rami legittimamente opzionali (cleanup, opzioni UI) — da rileggere, non da vietare | Task 3 (M) |
| ⚠️ Buco frontend: nessuna copertura JS/Svelte; «`coverage show frontend` misura backend toccato da E2E» | 🔴 priorità massima | **SUPERATO — copertura JS/Svelte esistente** | `@vitest/coverage-istanbul ^4.1.11` (`frontend/package.json:38`), stack istanbul completo (`:41-44`), `vite-plugin-istanbul ^9.0.1` (`:56`); `vitest.config.ts:19-45` (provider istanbul *con motivazione misurata*: V8 non vede i branch `{#if}` di Svelte); `vite.config.ts:67-81` (strumentazione E2E via `COVERAGE_INSTRUMENT=1` + guardia `.coverage-instrumented` contro il «verde che misura nulla»); merge dei report in `frontend/coverage-js/` (`unit-report.js`); `coverage-report --lang js` documentato in `testing-backend/SKILL.md:216-219`; commit `d1622ee5` 2026-08-30 | — |
| Da riprendere 🟠: test mirati su `api/v1/assets.py` (73,9 %) | aperto | **PARZIALE (struttura)** | nuovi/aggiornati: `test_asset_merge_api.py` (toccato `52784a3a`, 2026-08-12), `test_assets_crud.py` e `test_broker_access_api.py` (toccati da `6ab295d8`, 2026-09-01), `test_assets_patch_fields.py` presente; copertura effettiva non misurabile staticamente | verifica numerica a prossima misura |
| Da riprendere 🟠: rami errore parser BRIM (75–82 %) | aperto | **PARZIALE (struttura)** | `test_brim_parse_race.py` ampliato (+84 righe, `c1755d19`), `test_external/test_brim_providers.py` toccato; i 35 `C901` dei `parse` sono però **identici** all'audit (`ruff check --select C901` riprodotto oggi): il debito di complessità che li genera non è stato attaccato | Task 4 (M) |
| Da riprendere 🟡: `fx_providers/snb.py` 59 %, modulo peggiore | aperto | **FATTO (struttura)** | `test_snb_errors.py` (`c1755d19`): 8 test sui rami di errore (`:146,:160,:175,:181,:192,:231,:254` — HTTP failure, base non-CHF, valuta non supportata, parsing mensile) | verifica numerica a prossima misura |
| Da riprendere 🟡: `identifier_utils.py` 7 stmt, vittoria facile | aperto | **PARZIALE** | nessun test unitario dedicato (`grep` su `test_scripts/` → 0); però `merge_other_identifiers` è entrata in produzione via merge asset (`asset_source.py:4475`), quindi è esercitata indirettamente da `test_asset_merge_api.py` — i 7 stmt potrebbero essersi chiusi da soli | Task 2 (S): verificare alla prossima misura |
| Da riprendere ⚪: `cleanup_test_database()` zero chiamanti | segnalazione | **ANCORA VALIDO** | `test_db_config.py:51` (era `:50`), zero chiamanti (`grep` exit 1) | Task 1 (S) |
| `front check` 0 errori · 0 warning | misura del 07/08 | **NON RIVERIFICATO** | typecheck non rieseguito: misurerebbe lo stato beta 02/09 non committato, non la veridicità del dato d'epoca | — |

---

## Dettaglio

### B3 → T4: il working tree ha *esteso* la cura, non introdotto patologie

Le spec transazioni modificate nel working tree del 02/09 sono **sei**
(`transactions-modals`, `tx-commit-all-types`, `tx-delete`, `tx-picker-pagination`,
`tx-tooltips`, `tx-wac`) più `gallery.spec.ts` e `tooltip-component.spec.ts`. Il
controllo stile report 16 (asserzioni tautologiche `toHaveCount(await x.count())`,
`toBeVisible` su contenitori come unica verifica) dà esito **pulito**:

```bash
grep -rn "toHaveCount(await" frontend/e2e/   # 0 occorrenze — pattern estinto
```

- `tx-delete.spec.ts` (+277/−…): riscrittura T4 con asserzioni sul **payload di rete**
  (`expect(payload.deletes ?? []).toEqual([txId])`), conteggi fissi
  (`toHaveCount(1)` su righe staged/deleted), flag `committed` con messaggi
  diagnostici, refusal itemizzato (`banner.locator('ul li')`).
- `transactions-modals.spec.ts` (+33): test T1 sul separatore decimale con
  `toHaveValue('1234,56')` dopo `pressSequentially` — asserzione di valore esatto sul
  bug reale (feedback loop di normalizzazione).
- `tx-tooltips.spec.ts`: la modifica **rimuove** una sonda `isVisible()` istantanea
  (falso negativo sistematico col delay di hover di 500 ms) sostituendola con
  `waitFor({state:'visible'})` — con commento che spiega la race.
- `tx-picker-pagination.spec.ts`: converte una guardia morbida in asserzione dura
  (`expect(validateBtn).toBeVisible()`).
- `gallery.spec.ts`: sostituisce uno scan testuale fragile (traducibile!) con il tag
  deterministico `delete-safe` + asserzioni dure — motivato nel commento: «a silent
  skip is doc rot».

### `TransactionDeleteModal`: riferimenti residui nei test

Il componente è eliminato nel working tree (`D` in `git status`). Riferimenti residui:

- `frontend/e2e/`: **solo un commento storico** in `tx-delete.spec.ts:4` («T4
  (2026-09): the dedicated TransactionDeleteModal no longer exists») — corretto, è
  documentazione del remapping. Zero usi del testid `tx-delete-modal`.
- `frontend/src/`: zero occorrenze; l'export è stato rimosso da
  `components/transactions/index.ts` (grep `DeleteModal` → 0).

**Pulito.**

### Nota sul numero "63 spec" del commit `c1755d19`

Il messaggio di `c1755d19` (2026-08-28) dichiara «check-orphans clean: 63 specs, 191
[file]». Oggi: **68 spec** e **196 file** `test_*.py` backend — la crescita (+5 spec,
+5 file, più il non-tracciato del WT) è coerente con le ondate beta successive e la
registrazione è stata mantenuta (verifica nel report 12 della presente tornata).

---

## Task riesumati

| # | Task | Evidenza | Stima |
|---|---|---|---|
| 1 | Rimuovere o usare `cleanup_test_database()` (reperto ⚪, sopravvissuto) | `test_db_config.py:51`, zero chiamanti | **S** |
| 2 | Alla prossima misura di copertura: verificare chiusura di `identifier_utils.py` (7 stmt) e dei rami di `merge_other_identifiers` ora che il merge asset li esercita | `identifier_utils.py:51`, `asset_source.py:4475`, `test_asset_merge_api.py` | **S** (verifica) |
| 3 | Rilettura mirata delle 274 guardie `isVisible().catch(() => false)` residue: irrobustire solo quelle su elementi **obbligatori** (il criterio è già nel report 17; le spec WT mostrano il pattern da seguire) | `grep -c` su `frontend/e2e/**/*.spec.ts` | **M** |
| 4 | Completare la copertura dei rami errore BRIM aggredendo la causa (35 `C901` identici a un mese fa): o split dei `parse` o ammissione esplicita del debito | `pyproject.toml:72-80` (C901 assente dal select); `ruff check --select C901 app/services/brim_providers` → 35 | **M/L** |
| 5 | Rieseguire la suite completa a run corrente conclusa e aggiornare 90,66 % → dato nuovo, dichiarando le categorie (regola L1) | ultima misura completa: 2026-08-07 | **S** (esecuzione schedulata) |

---

## Nuovi rilievi

1. **Nessuna nuova patologia di test introdotta dalle ondate beta** — anzi due
   miglioramenti strutturali registrabili: (a) la raccomandazione trasversale del
   report 17 (guardie morbide → asserzioni dure su elementi obbligatori) è stata
   applicata spontaneamente nelle spec toccate; (b) `test_update_js_cache.py`
   (working tree) debutta con `isolation="pure"` dichiarato in `add_test`
   (`_backend_utils.py`, diff WT) — la disciplina di isolamento si è stabilizzata.
2. **Rischio residuo noto, non nuovo**: i tre fix B1/B2/B3 reggono, ma B1 dipende da
   un invariante *di ordine* (`_BACKEND_CATEGORIES` con `services` prima di `api`,
   `_suites.py:22`). Se l'ordine cambiasse, `_api_setup` resterebbe corretto ma
   ridondante; se `services_all` smettesse di ricreare il DB, idem. Nessuna azione:
   la docstring di `_api_setup` (`_backend_api.py:562-570`) documenta già il legame.
3. **Dato strutturale cresciuto**: 68 spec E2E e 196 file test backend (erano ~63 e
   171 all'epoca dei due report) — riprodotto con `find` (comandi nel report 12 di
   questa tornata).

---

## Cross-reference

- Report gemello: [12_test_coverage.md](12_test_coverage.md) (guardia `"fast"`, FX
  flaky, `build_history_sync_entry`, incrocio codice morto, interventi 1–8).
- Fonti: [17_stabilizzazione_suite_completa.md](../../phases/05_cleanAudit/17_stabilizzazione_suite_completa.md),
  [15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md),
  [12_test_coverage.md](../../phases/05_cleanAudit/12_test_coverage.md).
- Famiglia del difetto («una verifica che non può fallire non è una verifica»):
  report 15 (half-donut, `ownership-chart-section`) e report 16 (test walk) dell'audit
  originario; nessun nuovo esemplare nella presente verifica.
- Copertura JS/Svelte: infrastruttura in `frontend/vitest.config.ts`,
  `frontend/vite.config.ts`, `frontend/scripts/unit-report.js`; documentazione in
  `.github/skills/devpy-tools/testing-backend/SKILL.md:157-229` e `testing-frontend`.
- Verifica gemella AI Export (stessa tornata): [13_ai_export.md](13_ai_export.md).
