# 46 · E2E qualità dati (V)

> Analisi del 12/10, scritta in plan mode e copiata qui al passo 0. **Approvata il 12/10.**
>
> **Decisioni del developer** (testuali, inoltrate dal coordinatore il 12/10):
> - D1: «(c) Entrambe»: E2 via P-10 con API vere, in più uno spec con righe «legacy» scritte nel DB della corsia
>   da un helper Python (un TRANSFER e un'ADJUSTMENT in entrata senza costo), e B1 resta.
> - D2: «Sì, procedi; e il pannello lotti si aggiorna da solo dopo il sync: V scrive il test rosso e la cura nello
>   stesso lotto».
>
> **Decisioni del coordinatore**:
> - D3 e D4 come consigliato.
> - Doc dev `data-quality-banner.md` aggiornata da V via docs-writer, in inglese, nello stesso lotto.
> - In `KpiSection.svelte` solo l'attributo a `:304`: I la tocca con M-18 (`:252-268`).
>
> **Base**: portata in fast-forward a `f0f3de0d9` (treno 53, con BU2: troncamento in `backend/app/db/precision.py`).
> Avanzamento in §9.

## 0. Contesto

| | |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-ideal-system` |
| Branch | `e-alfy-v-test-e2e-qualita-dati` (rinominato dall'app su sua richiesta; HEAD invariato) |
| HEAD | analisi su `784b357661a6a456d91d1fd22e88af38da7fefcf` (treno 51); lavoro su `f0f3de0d9d80644b9886bc6817d442f9a47ec0a2` (treno 53, fast-forward del coordinatore, nessuno dei file di questo piano toccato) |
| Corsia | porta `6175`, dati `/tmp/librefolio-r2-v-dq` |
| Coordinatore | `c8328a01-f208-4ade-a352-0486d1f14de2` |
| Wiki | `graph.json` assente (previsto). Lette: `problems/zero-purchase-cost-foreign-asset-paid-in-report-currency`, `decisions/financial-math-single-average-cost`, `sources/phase00-fx-dashboard-sync-2026-10`, backlog 38 P-10 |

## 1. Stato verificato

### 1.1 I claim del kickoff

| Claim | Esito |
|---|---|
| `test_portfolio_engine/test_portfolio_cost_currency.py` | ⚠️ path errato: è `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py`. Righe giuste: S4 `:430`, S4b `:464`, S5 `:496`, S6 `:547`, I6 `:746`, L2 `:833`, L3 `:890`, `TestPeriodUnrealizedBreakdown` `:958` |
| `test_data_quality_report.py:227` | ✓ (`test_configured_real_provider_missing_fx_produces_rates_issue`, in `test_portfolio_engine/`), ma è unitario sui DTO: **nessun DB** |
| `KpiSection.test.ts:325` | ✓ fixture, Vitest/jsdom; trova la barra per struttura (non ha testid) |
| `data-quality-banners.spec.ts:452`, `:480`, `:502` | ✓ report e sync finti (`serveMissingFxRates`, `holdFxSync`) |
| Populate: «All TRANSFER/ADJUSTMENT(qty>0) have cost_basis_override set» | ✓ `populate_mock_data.py:3944-3959`: se manca, il populate **fallisce**. Il seed non può dare `MISSING_COST_BASIS`; il commento `data-quality-banners.spec.ts:434` («the seed's MISSING_COST_BASIS») è superato |
| I buchi | ✓ tutti: «—» mai testato (`ExposureTable.test.ts` copre privacy, YOC, evidenziazione); `MISSING_COST_BASIS` mai in UI; TRANSFER senza costo mai testato (S5, L3: solo ADJUSTMENT); nessun sync reale fino al banner; tooltip 23 solo Vitest |

### 1.2 Superfici e `data-testid`

- **Banner** (Dashboard, modo grouped), `ui/feedback/DataQualityBanner.svelte`:
  - `data-quality-banner` `:211`; `data-quality-toggle` `:213`, con `aria-expanded`, chiuso di default;
  - riga `data-quality-issue-{code}` + `data-severity` `:154`;
  - CTA `data-quality-cta-{code}` `:191`, disabilitata mentre lavora;
  - link agli asset `data-quality-nav-assets-{code}` / `data-quality-nav-asset-{id}` `:177-179`, col nome nel testo;
  - la coppia è resa dallo slug (codici ISO); le date sono i `message_params` ISO interpolati (precedente accettato:
    `toContainText('2019-03-04')`, spec `:391`);
  - montato su tutte le tab (`dashboard/+page.svelte:975`); `dashboard-page` pubblica `data-busy` (`:821`).
- **CTA «Sincronizza tassi»**: `syncMissingFxRates` (`dashboard/+page.svelte:355-418`) → `POST /fx/currencies/sync`
  `{pairs, start = prima data − 7, end = ultima + 7, ≤ oggi}` → ricarica il report → evento `fx.rates.synced`
  `{origin, pairs, start, end, outcome, stillMissing}`.
- **«—»**, `dashboard/ExposureTable.svelte`: colonne `pnl` `:278`, `pnl-percent` `:291`, `pmc` `:397` (**nascosta di
  default**), «—» quando il valore è null.
  - Sta in `PositionsPanel`: `positions-panel` con `data-busy`; `positions-toggle-holdings|table`;
    `positions-column-visibility-toggle` → `column-visibility-toggle` → `column-visibility-item-pmc`.
  - Righe DataTable `tr[data-row-id="{assetId}-{brokerId}"]`; **le celle non hanno id di colonna**
    (`DataTable.svelte:1249`). `ExposureTable.test.ts:565` ripiega sull'indice dell'intestazione con la classe
    `td-data`, vietata negli E2E.
  - Stesso componente, stesso report, in `brokers/[id]` (`broker-holdings`).
- **Pannello lotti**, `brokers/lots/LotsAnalysisPanel.svelte` (`lots-analysis-panel` `:448`, `-loading` `:487`) e
  `LotDataQualityBanner.svelte` (`lot-data-quality-banner`, `lot-data-quality-toggle`, `lot-data-quality-issue-{code}`).
  - Si apre da URL: `/dashboard?tab=posizioni&asset={id}`. Codici identici al banner (`lots_analysis_service.py`,
    `_report_gaps`).
  - `loading` parte `false` (`:91`): per un'assenza serve un testimone dalla stessa risposta, le righe di
    `unified-lots-table`. `DEGRADED` non arriva al DOM.
- **Tooltip 23**, `dashboard/KpiSection.svelte`: la prima `KpiMetricBar` (`:304`) **non ha testid**; le righe
  `kpi-unrealized-breakdown-{kind}-{currency}` (`:212`) stanno nel portal `tooltip-content`, che si apre al click o
  con Invio. DOMPurify conserva i `data-*`.

### 1.3 Le condizioni, con dati reali

Come `stale-price-banner.spec.ts`: account usa-e-getta (`registerDisposableUser`, `prepareOnboardingAccount`), dati
creati via API, pulizia in `finally`.

- **21**: una coppia configurata con provider ≠ MANUAL e senza tassi dà `MISSING_FX_RATES` + `sync_fx_pair`
  (`financial_math/portfolio/data_quality.py:198-221`).
  - La cassa si converte per movimento, alla sua data (`daily_state.py:463`, `:922`): le date mancanti sono i giorni
    dei movimenti.
  - La cache L2 del report include tassi e route delle valute di cassa (`engine.py:56-101`): il sync la invalida.
- **22**: l'app **rifiuta** TRANSFER o ADJUSTMENT in entrata senza costo, anche nei promote
  (`transaction_service.py:157-165`, `transaction_batch_stages.py:879-1047`).
  - Unico percorso app: **P-10**. Un ADJUSTMENT +q legato a uno SPLIT, in Auto, si salva senza costo
    (`transaction_service.py:980-1001`); se l'evento diventa PRICE_ADJUSTMENT, la riga è un'acquisizione di costo
    ignoto. È fissato da `test_portfolio_wac.py:521-588`.
  - TRANSFER senza costo: solo dati legacy o scritti nel DB; lo dice anche la doc dev (`data-quality-banner.md:176`).
  - Per lettura del codice il motore lo segnala: `average_cost.py:252-290` e `:426-429`; `classifier.py:94-128`
    tiene entrambe le gambe; `portfolio_service.py:564`.
- **23**: una valuta Y con tassi MANUAL (`POST /fx/currencies/rate`). Non serve una route: `convert_bulk` legge
  `FxRate`.

## 2. «Sincronizza tassi» senza rete

- **MOCKFX**, la scelta:
  - è registrato: nascosto dalla lista pubblica, accettato da `POST /fx/providers/routes`;
  - il sync vero (`sync_pairs_bulk`) scrive 1,2345 per ogni giorno, per qualsiasi valuta (già usato da
    `fx-sync-mock.spec.ts` e `test_fx_sync.py`);
  - conta come provider reale, quindi la CTA è `sync_fx_pair`;
  - lo scheduler è spento in test (`_server.py:231`, `playwright.config.ts:175`), quindi nessun sync automatico.
- **MANUAL**: dà `missingFxRatesManual` con `navigate_fx`, e il sync risponde `skipped`. Non prova il bottone.
- **Inserire il tasso come il sync** (`POST /fx/currencies/rate`): salta il bottone. Va bene solo come dato di
  partenza (23).
- **Resta stub, legittimamente**:
  - il provider esterno (MOCKFX al posto di ECB);
  - `:452`: lo stato occupato della CTA richiede di trattenere la richiesta;
  - `:480`: il tetto a oggi;
  - `:502`: «ok ma ancora mancante» non si riproduce a comando, perché MOCKFX riempie ogni giorno;
  - i test con `injectDashboardIssues`: stati di tutto il portafoglio.

## 3. I test

**Valute riservate**: tutte dopo «EUR», così il tasso salvato è esattamente 1,2345, e mai usate da test, populate o E2E
(grep). Una per progetto, così desktop e mobile non si scontrano:

- E1: desktop `MKD`, mobile `RSD`;
- E3: desktop `KZT`, mobile `UAH`.

Ogni test pulisce prima gli avanzi della propria coppia, verifica la precondizione (nessuna route, nessun tasso) e
pulisce in `finally` (fixture `owned`).

### B1 · Backend · TRANSFER in entrata senza costo → `MISSING_COST_BASIS`

- **Dove**: `test_portfolio_cost_currency.py::TestCostDiagnostics`, con la variante lotti in `TestLotsAverageCostLines`.
- **Crea** (sessione con rollback, come S5):
  - un utente, i broker A e B (OWNER al 100%), un asset EUR con prezzo;
  - BUY 10 su A, costo noto;
  - TRANSFER −4 su A ↔ +4 su B, senza `cost_basis_override`;
  - parametri: coppia | orfano.
- **Asserisce**:
  - l'issue `MISSING_COST_BASIS` con l'asset, nella forma di S5;
  - holding B: `wac_per_unit` e `gain_loss` None;
  - holding A completo (caso coppia);
  - lotti: l'issue e `DEGRADED`.
- **Isolamento**: write-scoped (default della categoria); nessun FX.
- **Registrazione**: nessuna. `services roi-fifo-utils` copre la cartella.
- **Atteso**: verde per lettura del codice. Se è rosso → STOP.

### E1 · Voce 21

- **Crea**:
  - la route EUR→MKD via MOCKFX;
  - un broker con `allow_cash_overdraft`;
  - un asset EUR manuale, prezzi d1 = 100 e d2 = 110;
  - d1 (−40 gg): DEPOSIT +1234,5 MKD e BUY 10 a −1234,5 MKD;
  - d2 (−20 gg): SELL −4 a +617,25 MKD e WITHDRAWAL −617,25 MKD. La cassa MKD è a zero a fine giornata.
- **Prima del sync**:
  - il report vero: valuta EUR; `MISSING_FX_RATES` con `[EUR-MKD]`, d1–d2, 2 date, CTA sync; wac, P&L e P&L %
    null;
  - il banner: la riga contiene «EUR», «MKD», d1 e d2;
  - le posizioni: `pnl`, `pnl-percent`, `pmc` = «—»;
  - il pannello lotti: `lot-data-quality-issue-MISSING_FX_RATES`.
- **Azione**: click sulla CTA. Si asserisce:
  - il corpo `{[EUR-MKD], d1−7, d2+7}`;
  - la risposta `ok`, `MOCKFX`;
  - l'evento `fx.rates.synced` con `outcome ok` e `stillMissing false`.
- **Dopo il sync**:
  - il tasso è salvato: `POST /fx/currencies/convert` di 1234,5 MKD al giorno d1 dà 1000 EUR, `rate_date` d1;
  - il report è senza l'issue: wac 100, P&L 60, P&L % 0,1;
  - il banner è senza la riga, o assente se il report non ha issue (lo decide il JSON, non una sonda);
  - le celle mostrano cifre;
  - **il pannello lotti già aperto si aggiorna da solo** (D2): dopo la risposta del sync parte una nuova
    `POST /api/v1/portfolio/lots/analysis`; la sua risposta non ha l'issue, e `lot-data-quality-banner` sparisce
    (o, se il JSON porta altre issue, la riga `MISSING_FX_RATES` manca a banner aperto). Oggi è **rosso per lettura
    del codice**: il sync del banner non incrementa `refreshVersion`. Prima il rosso, poi la cura minima: in
    `syncMissingFxRates` (`dashboard/+page.svelte`), dopo `invalidate()`, `refreshVersion += 1`, lo stesso segnale di
    «Aggiorna» (`:698`), che `LotsAnalysisPanel.svelte:357-366` già ascolta.

### E2 · Voce 22 (via P-10)

- **Crea**:
  - un asset EUR con prezzi;
  - DEPOSIT, poi BUY 10 a −1000 (d1);
  - SPLIT (d2, rapporto 2) e ADJUSTMENT +10 legato, in Auto. Si verifica che `cost_basis_override` sia null;
  - l'evento diventa PRICE_ADJUSTMENT.
- **Asserisce**:
  - nel report, `MISSING_COST_BASIS` con id e nome dell'asset e `navigate_asset`; wac e P&L null;
  - nel banner, la riga con `data-quality-nav-asset-{id}` e il nome dell'asset;
  - «—» nelle posizioni, sulla Dashboard e sulla pagina del broker;
  - nel pannello lotti, `lot-data-quality-issue-MISSING_COST_BASIS`;
  - il link porta a `/assets/{id}`.
- **Poi** (D4): costo 0 esplicito sull'ADJUSTMENT → l'issue sparisce, wac 50, le celle mostrano cifre.

### E3 · Voce 23

- **Crea**:
  - i tassi EUR/KZT: d1 = 2, d2 = 2,5;
  - un asset KZT (prezzo da 20 a 30) e un asset EUR (prezzo da 20 a 25);
  - DEPOSIT 1000 EUR; d1 (−50 gg): BUY 10 KZT pagati −100 EUR e BUY 5 EUR pagati −100 EUR.
- **Asserisce**:
  - `period_unrealized_breakdown` = [asset EUR +25, asset KZT +40, fx KZT −20], delta 45, nessuna issue FX;
  - il tooltip (`kpi-unrealized-delta`, poi Invio) ha le tre righe in quest'ordine, nessuna `fx-EUR` né `unsplit`;
  - i valori: cifre e segno, separatori ignorati.

### E4 · Voce 22, righe «legacy» (D1 = c)

Spec separato: `frontend/e2e/portfolio/data-quality-legacy.spec.ts`.

- **Crea via API**:
  - broker A e B;
  - due asset EUR con prezzi: T (il trasferito) e J (la rettifica);
  - DEPOSIT su A; BUY 10 di T su A.
- **Poi l'helper** scrive le righe come le avrebbe lasciate una versione vecchia, cioè **senza**
  `cost_basis_override`:
  - TRANSFER −4 di T su A, legato a +4 su B;
  - ADJUSTMENT +5 di J su B.
- **L'helper** è `backend/test_scripts/test_db/legacy_cost_rows.py`, lanciato dallo spec con
  `execSync('pipenv run python -m …')` (precedente: `global-setup.ts`):
  - eredita `PIPENV_CUSTOM_VENV_NAME`, `TEST_PORT` e `LIBREFOLIO_TEST_DATA_DIR` dal runner;
  - `setup_test_database()` + `verify_test_database()`: rifiuta qualsiasi DB che non sia quello di test della corsia;
  - rifiuta broker che non appartengono, come OWNER, all'utente passato;
  - scrive solo righe marcate nella descrizione; stampa gli id in JSON.
- **Asserisce**:
  - nel report, `MISSING_COST_BASIS` con `affected_asset_ids` `[T, J]` e i nomi;
  - nel banner, la riga con esattamente i due link, `data-quality-nav-asset-{T}` e `-{J}`. Il conteggio è legittimo:
    la Dashboard è tutta del test;
  - nelle posizioni: «—» su T@B e J@B; cifre su T@A, la parte con costo noto;
  - nel pannello lotti di T: `lot-data-quality-issue-MISSING_COST_BASIS`;
  - il link di J porta a `/assets/{J}`.
- **Pulizia**: broker A e B con force (via anche le righe legacy), asset, account.

### Regole comuni a E1–E4

- **Isolamento**:
  - ogni test ha un account suo, che possiede tutta la Dashboard;
  - nessun conteggio globale;
  - si aspetta su `data-busy`, sugli eventi o sul testimone, mai sull'orologio;
  - nessun testo tradotto: testid, codici e date ISO, nomi creati dal test, «—»;
  - parallelo di default, senza `serial`.
- **Registrazione** in `_frontend_portfolio.py`:
  - `front_portfolio_data_quality_real`, `add_test(cat, "data-quality-real", …)` → E1–E3;
  - `front_portfolio_data_quality_legacy`, `add_test(cat, "data-quality-legacy", …)` → E4;
  - progetto desktop, il default del runner (come `stale-price-banner`); `all` li raccoglie da solo.

## 4. Decisioni (risolte il 12/10) e possibili rossi

- **D1 = (c)**: E2 via P-10, E4 con righe legacy, B1. Rischio di E2: P-10 attende una decisione; se la si chiude
  bloccando la riclassificazione, E2 va ricostruito, mentre E4 e B1 restano.
- **D2 = rosso e cura nello stesso lotto**: E1 controlla il pannello lotti già aperto, senza ricaricare (§3, E1).
- **D3**: `data-column-id` in DataTable.
- **D4**: pagina del broker in E2 sì; «costo impostato → avviso via» sì; MOCKFX_FAIL no.
- **Possibile rosso in E3**: se l'inizio del periodo, prima del primo movimento, desse righe `unsplit` → STOP. Per
  lettura del codice è come B1, cioè «dall'inizio».
- **Gemello di D2, fuori mandato**: anche la CTA `sync_asset_prices` (STALE_PRICE) non incrementa `refreshVersion`.
  Va segnalato al coordinatore; non si cura senza un ok.

## 5. File

- **Nuovi**:
  - `frontend/e2e/portfolio/data-quality-real.spec.ts` (E1–E3);
  - `frontend/e2e/portfolio/data-quality-legacy.spec.ts` (E4);
  - `backend/test_scripts/test_db/legacy_cost_rows.py` (helper di E4; senza prefisso `test_`, pytest non lo raccoglie);
  - il piano, al path in testa.
- **Modificati**:
  - `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py`: B1 e un helper per il
    secondo broker;
  - `scripts/test_runner/_frontend_portfolio.py`: le due registrazioni;
  - `frontend/src/routes/(app)/dashboard/+page.svelte`: la cura di D2, una riga in `syncMissingFxRates`;
  - `mkdocs_src/docs/developer/frontend/data-quality-banner.md`, via docs-writer, in inglese: come si producono
    `MISSING_FX_RATES` e `MISSING_COST_BASIS`, `:176`, la sezione dei test.
- **Solo attributi**:
  1. `frontend/src/lib/components/table/DataTable.svelte:1249`: `data-column-id={column.id}` sul `<td class="td-data">`;
  2. `frontend/src/lib/components/dashboard/KpiSection.svelte:304`: `testid="kpi-unrealized-delta"`. La prop esiste
     già e rende `data-testid`, più `-value` sul valore.
- **Non tocco**:
  - i file di I, U, T, M e la galleria;
  - `KpiSection.svelte` oltre `:304` (I, M-18).
- **Proposte al coordinatore, non scritte da V**:
  - la voce del CHANGELOG per la cura di D2;
  - il backlog, se restano residui: il gemello STALE_PRICE, il `data-busy` mancante su `LotsAnalysisPanel`.

## 6. Stima, rischi, definizione di fatto

- **Stima**: circa 1,5 giorni, più del giorno iniziale per via di E4, della cura e della doc.

  | Lavoro | Tempo |
  |---|---|
  | B1 | 1-2 h |
  | Attributi e runner | 0,5 h |
  | E1 con la cura | 3,5 h |
  | E2 | 2 h |
  | E3 | 1,5 h |
  | E4 e helper | 2,5 h |
  | Doc | 1 h |
  | Giri | 1,5 h |
- **Rischi**:
  - T e la precisione (BU2 tronca i tassi): gli importi sono scelti esatti (1,2345; 2; 2,5);
  - P-10, se chiusa, cambia E2;
  - `DataTable.svelte` è condiviso: un solo attributo;
  - righe FX globali: valute riservate, pre-pulizia e pulizia;
  - l'helper scrive nel DB mentre il backend gira: scrittura breve, già fatta così da `populate`;
  - il mobile non entra nella definizione di fatto.
- **Definizione di fatto**:
  - B1 verde;
  - E1: rosso registrato sul pannello lotti per la ragione giusta, poi verde con la cura;
  - E1–E4 verdi a `--workers 1` e a `--workers 4`;
  - `banners` e `stale-price-banner` verdi a 4 worker;
  - i Vitest dei componenti toccati verdi; svelte-check, prettier, ruff e black puliti; `check-orphans` pulito;
  - doc con `mkdocs build` (strict) e `check-links` verdi;
  - dopo i giri, lettura del DB della corsia: nessuna route o tasso MKD, RSD, KZT, UAH; nessun account, broker o asset
    degli spec;
  - porta 6175 libera;
  - ogni altro rosso che riveli un comportamento mancante → STOP e messaggio.

## 7. Comandi (corsia V)

`P="PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6175 --data-dir /tmp/librefolio-r2-v-dq"`

- `$P services roi-fifo-utils TestCostDiagnostics TestLotsAverageCostLines`
- Vitest dei componenti toccati: `frontend/node_modules/.bin/vitest run <file>`, fuori corsia; `$P front-utility
  component-unit` per il giro completo
- `$P --workers 1 front-portfolio data-quality-real`, `$P --workers 4 front-portfolio data-quality-real`
- `$P --workers 1 front-portfolio data-quality-legacy`, `$P --workers 4 front-portfolio data-quality-legacy`
- `$P --workers 4 front-portfolio banners`, `$P --workers 4 front-portfolio stale-price-banner`
- `$P check-orphans`
- Doc: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build` e `… mkdocs
  check-links`. Mai `mkdocs serve`.

## 8. Passi

0. Il file del piano nel repo; `npm ci`; `api sync`.
1. B1 (test-author), poi la sua esecuzione. Se è rosso → STOP.
2. I due attributi; poi i Vitest, svelte-check, prettier.
3. E3, poi E2, poi E1 col rosso di D2 (test-author); la registrazione nel runner.
4. La cura di D2; E1 di nuovo, verde.
5. L'helper ed E4 (test-author).
6. La doc (docs-writer).
7. I giri a 1 e a 4 worker, i vicini, il controllo degli avanzi, la porta libera.
8. Il checkpoint.

## 9. Avanzamento

- ✅ **Passo 0** (12/10).
  > **Note implementazione**:
  > - Piano copiato dalla sessione e aggiornato con le decisioni.
  > - `npm ci` da lock: exit 0, avvisi sugli install script non approvati (esbuild, fsevents, es5-ext); innocui, i
  >   Vitest girano.
  > - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync`: exit 0; scrive solo file
  >   ignorati (`openapi.json`, `generated.ts`, `generated-tools.ts`, …).
  >
  > **⚠️ Fuori pista**:
  > - Il primo Vitest è fallito prima di raccogliere i test: «Failed to resolve import "./generated"». In una worktree
  >   nuova il client generato manca; il runner lo rigenera da sé (`_ensure_frontend_build`). Corretto con `api sync`,
  >   nessun file tracciato toccato.
  > - Il coordinatore ha portato la base a `f0f3de0d9` durante il passo; nessuno dei file del piano era toccato.
- ✅ **Passo 2** (12/10): i due attributi.
  > **Note implementazione**:
  > - `DataTable.svelte:1249-1255`: `data-column-id={column.id}`; prettier ha spezzato il `<td>` su più righe.
  > - `KpiSection.svelte:305`: `testid="kpi-unrealized-delta"`.
  > - Vitest (`KpiSection`, `ExposureTable`, sei file `DataTable*`): 8 file, 282 test verdi (log
  >   `/tmp/libreFolio_v_vitest_attrs.log`).
  > - svelte-check: 0 errori, 0 avvisi. prettier pulito sui due file.
  >
  > **⚠️ Fuori pista**: prettier ha segnalato DataTable. La versione di HEAD era pulita: il difetto era della riga
  > allungata dall'attributo, corretto con `prettier --write` sul solo file.
- ✅ **Passo 1** (12/10): B1, scritto da test-author.
  > **Note implementazione** (`test_portfolio_cost_currency.py`, +143/−11):
  > - Nuovo `TestCostDiagnostics::test_s7_transfer_in_without_cost_basis_raises_missing_cost_basis[paired|orphan]`:
  >   - a B: 4 unità, `wac_per_unit` e `gain_loss` None, `current_value` 120;
  >   - ad A: completo (accoppiato: 6 a 20, P&L 60; orfano: 10 a 20, P&L 100);
  >   - `open_cost_basis`: 120 e 200;
  >   - un `MISSING_COST_BASIS` con `cta_target` = l'asset.
  > - Nuovo `TestLotsAverageCostLines::test_l4_…`, solo accoppiato: codici `["MISSING_COST_BASIS"]`, `DEGRADED`.
  > - Helper: `_add_broker`, `_seed_transfer_without_cost`, `_missing_cost_basis_issue`. Opzione `broker=` su `_tx` e
  >   `_holding`; le chiamate esistenti non cambiano.
  > - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6175 --data-dir
  >   /tmp/librefolio-r2-v-dq services roi-fifo-utils TestCostDiagnostics TestLotsAverageCostLines` → **11 passati**
  >   (`/tmp/libreFolio_v_b1_run2.log`). L'azione senza filtro: 656 passati (`/tmp/libreFolio_v_b1_full_action.log`,
  >   prima della rimozione del caso orfano di L4).
  > - black e ruff puliti; porta 6175 libera.
  >
  > **⚠️ Fuori pista**: il caso orfano di L4 fissava `FAILED`. Un TRANSFER orfano fa fallire i lotti FIFO
  > (`TRANSFER_PAIR_MISSING`), mentre la Dashboard lo conta come capitale in natura. Non è deciso e non riguarda la
  > voce 22: caso tolto da L4, l'orfano resta coperto da S7. Osservazione per il coordinatore.
  >
  > **Osservazione, da riferire**: TRANSFER accoppiato senza costo. Il FIFO sposta il lotto di A con il suo costo,
  > senza segnalare nulla; il costo medio considera ignoto l'arrivo, ed è quello che alimenta banner e «—». È
  > coerente con la decisione «un trasferimento porta il suo costo in `cost_basis_override`».
- ✅ **Passo 5, prima parte** (12/10): E4 e l'helper, scritti da test-author.
  > **Note implementazione**:
  > - `backend/test_scripts/test_db/legacy_cost_rows.py` (nuovo):
  >   - `setup_test_database()` prima di ogni altro import; `verify_test_database()`;
  >   - rifiuta un DB inesistente (SQLite lo creerebbe vuoto) con exit 2;
  >   - controlla che i broker siano OWNER dell'utente, diversi tra loro, e che gli asset esistano; altrimenti exit 3;
  >   - scrive in un'unica transazione la coppia TRANSFER e l'ADJUSTMENT, senza costo e senza cassa;
  >   - stampa gli id in JSON.
  > - `frontend/e2e/portfolio/data-quality-legacy.spec.ts` (nuovo):
  >   - un account usa-e-getta; rilegge le righe legacy via `GET /transactions?ids=`;
  >   - report: un `MISSING_COST_BASIS` per [T, J], `count` 2; T@B e J@B senza wac né P&L; T@A wac 20, P&L 60,
  >     P&L % 0,5;
  >   - banner: due link, uno per asset, coi nomi;
  >   - celle «—» su T@B e J@B, cifre su T@A;
  >   - lotti di T: `MISSING_COST_BASIS` e `DEGRADED`, ogni lotto della risposta visibile prima del banner;
  >   - il link di J porta all'asset;
  >   - pulizia: i broker con force portano via anche le righe legacy.
  > - Registrazione: `front_portfolio_data_quality_legacy`, azione `data-quality-legacy`.
  > - Comandi e risultati:
  >   - `… --workers 1 front-portfolio data-quality-legacy`: **1 passato** (`/tmp/libreFolio_v_e4_w1.log`);
  >   - `--workers 4`: **1 passato** (`/tmp/libreFolio_v_e4_w4.log`);
  >   - porta 6175 libera.
  > - L'helper ha usato `VIRTUAL_ENV/bin/python`, cioè il venv condiviso `LibreFolio-SAUMUTtc`; mai `pipenv run`.
  > - Pulizia confermata dalle risposte delle cancellazioni: broker 9 con 3 righe, broker 10 con 2, asset 18 e 19,
  >   account 12.
  >
  > **⚠️ Fuori pista**:
  > - Nel brief avevo dato `/portfolio/lots-analysis`; il path giusto è `/portfolio/lots/analysis`
  >   (`portfolio_api.py:244`). Lo spec usa quello giusto; il piano è corretto.
  > - Con un solo test, a 4 worker gira da solo: la prova accanto ai vicini sarà il giro consolidato
  >   `--workers 4 front-portfolio all`.
- ✅ **Passo 3** (12/10): E1–E3 scritti da test-author (`frontend/e2e/portfolio/data-quality-real.spec.ts`,
  registrazione `front_portfolio_data_quality_real` / `data-quality-real`).
  > **Note implementazione**:
  > - Tre test, ciascuno con un account usa-e-getta e `test.step`, in parallelo, senza `serial`.
  > - Valute riservate per progetto: E1 MKD/RSD, E3 KZT/UAH. All'inizio pulizia dei resti e verifica della
  >   precondizione (nessuna route, conversione di oggi 404); pulizia di tassi e route nel teardown.
  > - Pannello lotti: il testimone sono le righe dei lotti della risposta, perché il pannello non pubblica un
  >   `data-busy`.
  > - Pagina broker: si aspetta `broker-refresh` abilitato e `positions-panel` con `data-busy="false"`.
  > - Primo giro, `… --workers 1 front-portfolio data-quality-real` (`/tmp/libreFolio_v_e2e_w1_red.log`):
  >   - **E2 ✓** (3,7 s) ed **E3 ✓** (3,2 s);
  >   - **E1 ✘ solo al passo D2**, come previsto: `data-quality-real.spec.ts:610`, «the open lots panel did not ask
  >     again after «Sync rates»: no POST /portfolio/lots/analysis for this asset once the sync had answered»
  >     (`Received: null`; nel log ✘ alla riga 38, errore alle righe 45–53, riepilogo alle 67–74). In 45 s dopo il
  >     click non parte nessuna richiesta. Lo screenshot del fallimento (`frontend/test-results/portfolio-data-quality-rea-4ea79-…/test-failed-1.png`)
  >     mostra la Dashboard già guarita (P&L +60,00 €, +10,00%) e il pannello lotti con il vecchio avviso.
  > - I passi di E1 prima di D2 sono verdi, e confermano le date del piano:
  >   - prima del sync: `MISSING_FX_RATES` EUR-MKD da d1 a d2, 2 date; wac, P&L e P&L % null; banner, «—» e
  >     avviso lotti presenti;
  >   - il sync: risposta `ok` / `MOCKFX` con 35 punti; evento `fx.rates.synced` con `ok` e `stillMissing false`;
  >   - dopo il sync: 1234,5 MKD a d1 = 1000 EUR, senza riempimento all'indietro; report 100 / 60 / 0,1; cifre
  >     nelle celle.
  > - Pulizia verificata sul DB della corsia, in sola lettura: nessun account, broker, asset o transazione dello spec;
  >   nessun tasso né route MKD, RSD, KZT, UAH.
  >
  > **⚠️ Fuori pista**: dopo il sync resta un'issue info, `MWRR_NOT_CALCULABLE`, quindi il banner non sparisce. Lo
  > spec lo apre e verifica che la riga `MISSING_FX_RATES` non ci sia più (deciso dal JSON, come previsto in §3).
  >
  > **Secondo giro, con la cura** (12/10):
  > - `… --workers 1 front-portfolio data-quality-real`: **3 passati**, E1 3,6 s, E2 3,3 s, E3 3,3 s
  >   (`/tmp/libreFolio_v_e2e_w1_green.log`);
  > - `… --workers 4 front-portfolio data-quality-real`: **3 passati** su tre worker in contemporanea
  >   (`/tmp/libreFolio_v_e2e_w4.log`);
  > - la richiesta del pannello lotti parte circa 1 ms dopo la risposta del sync, insieme alla ricarica del report
  >   (13:36:32.804 → .805); il passo D2 dura 7 ms;
  > - nel chunk servito (`nodes/8.C7umU8qA.js`), `set(refreshVersion, …)` segue `invalidate()` nel sync;
  > - porta libera; nessun avanzo nel DB della corsia.
  >
  > **⚠️ Fuori pista, falso allarme**: test-author ha visto il bundle riscritto alle 13:35:24-13:36:04, mentre il log
  > del runner diceva «Frontend build is up to date». Era il backend condiviso del runner: `cmd_server`
  > (`dev.py:228`) esegue `auto_build_frontend()` prima di occupare la porta, poi `auto_build_mkdocs()`. Il controllo
  > successivo del runner trovava quindi la build già fresca. Nessun file è stato servito mentre veniva riscritto.
  > Conseguenza pratica: un avvio di server ricostruisce anche `mkdocs_src/site`, quindi i giri finali partono solo
  > dopo i `mkdocs build` di docs-writer.
- ✅ **check-orphans** (12/10): `… check-orphans` → tutti registrati: 108 spec e2e, 347 unit; tutti raggiungibili
  da `all` (`/tmp/libreFolio_v_check_orphans.log`).
- ✅ **Passo 4** (12/10): la cura di D2.
  > **Note implementazione**:
  > - `frontend/src/routes/(app)/dashboard/+page.svelte:381-382`: in `syncMissingFxRates`, dopo `invalidate()` e solo
  >   senza errore di trasporto, `refreshVersion += 1;` con un commento di una riga. È lo stesso segnale di «Aggiorna»
  >   (`:700`).
  > - Ascoltano: `LotsAnalysisPanel.svelte:357-366` (`loadMain(…, true)` e storie della selezione) e, se montato,
  >   `RiskLevelsPanel` (`:1051`). Anche il rischio dipende dai cambi.
  > - prettier pulito; gate `htmlSink` e `flagFont` 20/20 (`/tmp/libreFolio_v_vitest_gates.log`).
  >
  > **Da riferire**: il gemello `sync_asset_prices` (STALE_PRICE, `handleBannerAction`) non incrementa
  > `refreshVersion`. È fuori mandato e non è curato: proposta per il backlog.
  >
  > Dopo la cura: svelte-check 0 errori e 0 avvisi (`/tmp/libreFolio_v_svelte_check2.log`); prettier pulito su tutti i
  > file frontend toccati.
- ✅ **Passo 6** (12/10): la doc, scritta da docs-writer.
  > **Note implementazione** (`mkdocs_src/docs/developer/frontend/data-quality-banner.md`, +35/−4; solo inglese,
  > nessuna traduzione esistente):
  > - riga `sync_fx_pair` della tabella delle CTA: `refreshVersion`, ricarica del pannello lotti e del rischio;
  > - «How to Trigger»: riga `MISSING_COST_BASIS` riscritta. L'app rifiuta la riga ovunque, promote compresi; la
  >   condizione nasce da dati legacy o dal percorso P-10. Nuova riga `MISSING_FX_RATES` con la ricetta MOCKFX;
  > - «Test Coverage»: S7, L3 e L4; nuove sezioni per `data-quality-real.spec.ts` e `data-quality-legacy.spec.ts`,
  >   coi comandi.
  > - `… dev.py mkdocs build` (strict): exit 0, nessun avviso (`/tmp/libreFolio_v_docs_build.log`).
  > - `… dev.py mkdocs check-links`: 95 link validi, 0 rotti, 8 risolti solo a runtime
  >   (`/tmp/libreFolio_v_docs_links.log`).
- ✅ **Backlog** (12/10): nuova sezione «V · E2E qualità dati (46)» in `BACKLOG_POST_1.2.md`, righe V-1…V-6:
  - V-1: il gemello STALE_PRICE della D2;
  - V-2: il `data-busy` mancante del pannello lotti;
  - V-3: il TRANSFER orfano, `FAILED` nei lotti;
  - V-4: E2 dipende da P-10;
  - V-5: il commento superato in `data-quality-banners.spec.ts:434`;
  - V-6: la doc elenca solo una parte dei test di `data-quality-banners`.
- ✅ **Passo 7** (12/10): i giri finali.
  > **Note implementazione**:
  > - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6175 --data-dir
  >   /tmp/librefolio-r2-v-dq --workers 4 front-portfolio all` (`/tmp/libreFolio_v_gate_portfolio_all_w4.log`,
  >   4 min 12 s), in una sola invocazione consolidata:
  >   - privacy-masking 18/18 su desktop e mobile;
  >   - 13 spec, 156 test a 4 worker: **155 passati, 1 fallito** (`dashboard-cache.spec.ts:338`);
  >   - Vitest della categoria: 35 file, 1218/1218.
  >   - Verdi accanto ai vicini: `data-quality-real`, `data-quality-legacy`, `banners`, `stale-price-banner` e tutte le
  >     altre azioni.
  > - Rigiro della sola unità: `… --workers 4 front-portfolio dashboard-cache` → **6/6 passati**
  >   (`/tmp/libreFolio_v_gate_dashboard_cache_w4.log`).
  > - Avviso noto: «Shared backend ignored SIGTERM for 5s» (C-49 del backlog C).
  >
  > **⚠️ Fuori pista, triage del rosso** (skill test-triage, verdetto **stato condiviso**, preesistente, non di V):
  > - **forma della risposta**: la pagina mostra «Risk data could not be loaded.», l'errore di primo caricamento del
  >   pannello Rischio di `TEST_USER` (`riskPanelController.svelte.ts`, `loadError`);
  > - **orologio**: escluso. Il test dura 33 s, e 30 s sono l'attesa delle card. La richiesta è fallita in fretta,
  >   non per il timeout client di 30 s (`zodios-client.ts:32`). Escluso anche il pool del rischio saturo: darebbe
  >   `WORKER_BUSY` sulla singola analisi;
  > - **stato condiviso**, confermato dal log del backend:
  >   - `dashboard-broker-filter-label` (#2 e #4, in parallelo) crea due broker di `TEST_USER` alle 11:52:46 UTC e li
  >     cancella alle 11:52:51 e 11:52:52;
  >   - `dashboard-cache` #5 aveva letto i broker posseduti in quel momento;
  >   - la sua `risk/query` riceve 403 «Requested portfolio broker subset is not fully accessible»
  >     (`backend/app/api/v1/risk.py:73,89`);
  > - **non è di V**: i miei spec sono partiti alle 11:53:49, un minuto dopo, su account usa-e-getta; le loro scritture
  >   FX (6 «Cache cleared» alle 11:53:51) vengono dopo il fallimento. La cura di D2 agisce solo dopo un clic su
  >   «Sincronizza tassi», che quel test non fa.
  > - Riga V-7 nel backlog.

## 10. Checkpoint (12/10) — FROZEN

- **Base**: HEAD `f0f3de0d9` (treno 53), uguale al target del coordinatore. Nessun commit, nessuno staging.
- **Delta**: 7 file tracciati modificati, 4 nuovi.

  | File | Cosa |
  |---|---|
  | `frontend/e2e/portfolio/data-quality-real.spec.ts` (nuovo) | E1–E3 |
  | `frontend/e2e/portfolio/data-quality-legacy.spec.ts` (nuovo) | E4 |
  | `backend/test_scripts/test_db/legacy_cost_rows.py` (nuovo) | helper di E4, solo DB di test della corsia |
  | `LibreFolio_developer_journal/Release_2/Phase_0/46_dataQualityE2E/plan-phase00DataQualityE2E.prompt.md` (nuovo) | questo piano |
  | `backend/test_scripts/test_services/test_financial/test_portfolio_cost_currency.py` | S7, L4 e helper |
  | `scripts/test_runner/_frontend_portfolio.py` | azioni `data-quality-real` e `data-quality-legacy` |
  | `frontend/src/routes/(app)/dashboard/+page.svelte:381-382` | cura di D2 |
  | `frontend/src/lib/components/table/DataTable.svelte:1249-1255` | `data-column-id` |
  | `frontend/src/lib/components/dashboard/KpiSection.svelte:305` | `testid="kpi-unrealized-delta"` |
  | `mkdocs_src/docs/developer/frontend/data-quality-banner.md` | doc dev |
  | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | sezione V, righe V-1…V-7 |
- **Esclusi** (ignorati o generati):
  - il client API generato (`generated.ts`, `openapi.json`, `generated-tools.ts`, …);
  - `frontend/build`, `.svelte-kit`, `node_modules`;
  - `frontend/test-results`, `playwright-report`, `.testLog`;
  - `mkdocs_src/site`, `scripts/test_runner/.run_cache.json` e `.campaign.json`;
  - `backend/data/prod/logs/librefolio.log`: vuoto, creato da `api sync`.
- **Prove**: §9, passi 0–7.
  - B1: 11/11.
  - E1–E3: a 1 e a 4 worker verdi; il rosso di D2 è registrato prima della cura.
  - E4: verde a 1 e a 4 worker.
  - `front-portfolio all` a 4 worker: 155/156; il rosso è V-7, preesistente; l'unità da sola passa 6/6.
  - Vitest: 282 test sui componenti toccati, 20 gate.
  - Statici: svelte-check 0/0, prettier, black e ruff puliti; `check-orphans` pulito.
  - Doc: `mkdocs build` strict e `check-links` verdi.
  - Porta 6175 libera.
- **Proposte al coordinatore**:
  - la riga CHANGELOG della cura di D2;
  - il commit;
  - la riconciliazione dell'indice del backlog con la nuova sezione V.

## 11. Lotto 2: V-1, V-7, V-5, V-6 (12/10)

> **Mandato** (coordinatore, 12/10, dopo il treno 56 `e7d698c4d`, che contiene il lotto 1: `15bfcf1e8`, `2f0b06346`,
> `b44b28f3d`), «nello spirito della decisione D2 del developer»:
> 1. V-1 come D2: prima il rosso, poi la cura;
> 2. V-7: `dashboard-broker-filter-label` su un account usa-e-getta;
> 3. V-5 e V-6.
>
> V-2, V-3 e V-4 restano nel backlog. Nessuna riga nel CHANGELOG: «Sincronizza tassi» (06/10) e il banner STALE_PRICE
> (D8, 30/09) sono nati dopo la 1.1. Corsia 6175. Checkpoint: manifest coi blob, commit proposti in ASCII.
>
> L'autorizzazione di V-1 è un'estensione della D2 decisa dal coordinatore, non una nuova parola del developer.

### 11.1 Stato verificato (HEAD `e7d698c4d`, worktree pulita)

- **V-1**: `frontend/src/routes/(app)/dashboard/+page.svelte:436-463`, ramo `sync_asset_prices` di
  `handleBannerAction`. Dopo la risposta del sync: i toast, poi `invalidate()` (`:456`) e `await loadAll(true)`;
  `refreshVersion` resta invariato.
  - Cura: `refreshVersion += 1` dopo `invalidate()`, solo nel `try`, dopo una risposta. È la stessa forma della cura di
    D2 (`:381-382`).
  - Il test va in `stale-price-banner.spec.ts`, che ha già l'account usa-e-getta, `mockprov` con `INVALID_TICKER_12345`
    e il sync intercettato. Asserisce che, dopo la risposta del sync, il pannello lotti già aperto chiede di nuovo
    `POST /portfolio/lots/analysis`.
- **V-7**: `frontend/e2e/portfolio/dashboard-broker-filter-label.spec.ts` entra come `TEST_USER` (`:655`) e crea e
  cancella un broker suo (`:584-622`).
  - Il trigger mostra un nome solo con un broker scelto **fra più** (`:676`): l'account usa-e-getta deve possederne
    due.
  - Pulizia: broker, poi account (`deleteDisposableUser`).
- **V-5**: `frontend/e2e/portfolio/data-quality-banners.spec.ts:433`, «(the seed's MISSING_COST_BASIS is one)». Il seed
  non può produrlo; il fratello che lo spec possiede è il `TRANSACTION_IMPLIED` iniettato (`:409-421`).
- **V-6**: `mkdocs_src/docs/developer/frontend/data-quality-banner.md`, sezione «Test Coverage»:
  - `:271-284`: elenco dei test di `data-quality-banners.spec.ts` incompleto;
  - dopo la cura di V-1, la riga `sync_asset_prices` della tabella delle CTA e la sezione `stale-price-banner`.

### 11.2 Passi

1. Test-author A scrive il test rosso di V-1; test-author B scrive V-7 e V-5. Entrambi senza corsia.
2. A gira V-1 nella corsia: rosso per la ragione giusta.
3. La cura di V-1. A rigira: verde a 1 e a 4 worker.
4. B gira `broker-filter-label` a 1 e a 4 worker.
5. docs-writer per V-6 e le righe toccate da V-1.
6. Giro finale `--workers 4 front-portfolio all`; controlli statici; manifest coi blob; checkpoint.

### 11.3 Avanzamento
- ✅ **Passo 1, V-7 e V-5** (12/10), scritti da test-author B.
  > **Note implementazione**:
  > - `dashboard-broker-filter-label.spec.ts`:
  >   - account usa-e-getta (`registerDisposableUser(request, 'brokerlabel')`, `prepareOnboardingAccount`) con due
  >     broker suoi: quello dal nome lungo e uno semplice, per avere «uno fra più»;
  >   - nessuna transazione: il trigger è sempre disegnato e il report parte appena l'account possiede un broker
  >     (`canAsk`);
  >   - nuova precondizione: il pannello del filtro elenca anche il secondo broker;
  >   - pulizia: broker per id senza `force`, poi l'account;
  >   - header «Ownership» riscritto; via gli import `TEST_USER` e `login`.
  > - `data-quality-banners.spec.ts` (~`:433`): solo il commento. Il fratello è il `TRANSACTION_IMPLIED` che il test
  >   inietta.
  > - Runner: solo il `desc=` di `broker-filter-label`.
  > - prettier pulito; tsc pulito, con prova che il controllo legge davvero il file.
- ✅ **Passo 4, V-7 e V-5 in corsia** (12/10).
  > **Note implementazione**:
  > - `… --workers 1 front-portfolio broker-filter-label`: **2 passati** (`/tmp/libreFolio_v_b2_v7_w1.log`);
  > - `--workers 4`: **2 passati**, in contemporanea (`/tmp/libreFolio_v_b2_v7_w4.log`);
  > - `… --workers 4 front-portfolio banners`: **18 passati**, compreso il test del commento V-5
  >   (`/tmp/libreFolio_v_b2_v7_banners_w4.log`);
  > - porta libera.
  > - Pulizia verificata, in sola lettura, sulle copie del DB archiviate dal runner:
  >   - nessun account `guides_brokerlabel_*` e nessun broker dello spec;
  >   - `TEST_USER` (#2) vede solo i broker del seed, #1–#7;
  >   - nel log del backend: 8 creazioni e 8 cancellazioni di broker, tutte degli account usa-e-getta, nessuna di
  >     #2; nessun 403 «not fully accessible».
  > - Resta da provare il giro accanto a `dashboard-cache`: è il giro finale consolidato.
- ✅ **Passo 1, V-1** (12/10), scritto da test-author A: nuovo test in `stale-price-banner.spec.ts`, ««Sync prices»
  refreshes the lots panel already open…».
  > **Note implementazione**:
  > - Account suo, `seedStaleHolding`, sync intercettato. Precondizioni lette dalle prime risposte: `STALE_PRICE`
  >   con `sync_asset_prices`; un lotto; testimone sull'id esatto del lotto.
  > - Attese armate prima del click, legate a «dopo la risposta del sync»: ricarica del report e richiesta principale
  >   dei lotti, annullabile, 45 s.
  > - Il passo V-1 richiede la richiesta dei lotti, la sua risposta OK con il lotto, e lo stesso
  >   `performance.timeOrigin` di prima del click: una ricarica della pagina non passerebbe.
  > - Runner: solo il `desc=` di `stale-price-banner`. prettier e tsc puliti.
- ✅ **Passo 2, il rosso di V-1** (12/10): `… --workers 1 front-portfolio stale-price-banner`
  (`/tmp/libreFolio_v_b2_v1_red.log`).
  > **Note implementazione**:
  > - D8 verde (4,4 s). Il nuovo test **rosso solo al passo V-1**, `stale-price-banner.spec.ts:419` (righe 44-52 del
  >   log): «the open lots panel did not ask again after «Sync prices»: no POST /portfolio/lots/analysis for this
  >   asset once the sync had answered», `Received: null` dopo 45 s.
  > - Lo screenshot del fallimento (`frontend/test-results/portfolio-stale-price-bann-58fd0--by-itself-without-a-reload-desktop/test-failed-1.png`)
  >   mostra la stessa scheda Posizioni, il report ricaricato e il pannello lotti ancora aperto, mai richiesto di nuovo.
  > - Pulizia verificata; porta libera.
- ✅ **Passo 3, la cura di V-1** (12/10): `frontend/src/routes/(app)/dashboard/+page.svelte:457-458`.
  > **Note implementazione**: in `handleBannerAction`, ramo `sync_asset_prices`, subito dopo `invalidate()`, dentro
  > il `try`, quindi solo dopo una risposta del sync: un commento di una riga e `refreshVersion += 1;`. È la stessa
  > forma della cura di D2 (`:381-382`). prettier pulito.
- ✅ **Passo 3, V-1 verde** (12/10).
  > **Note implementazione**:
  > - `… --workers 1 front-portfolio stale-price-banner`: **2 passati**, D8 6,0 s e V-1 3,2 s
  >   (`/tmp/libreFolio_v_b2_v1_green.log`). La richiesta dei lotti parte circa 7 ms dopo la risposta del sync,
  >   insieme alla ricarica del report. Risposta 200, il lotto c'è ancora, `performance.timeOrigin` invariato.
  > - `--workers 4`: **2 passati** in contemporanea; richiesta dei lotti dopo circa 9 ms
  >   (`/tmp/libreFolio_v_b2_v1_w4.log`).
  > - Bundle servito `nodes/8.CX12q843.js`: nel ramo `sync_asset_prices`,
  >   `invalidate(); set(refreshVersion, get(refreshVersion) + 1); await loadAll(true);`. Ricostruito all'avvio del
  >   server (14:31:59), come già visto per D2.
  > - Pulizia verificata nel DB della corsia; porta libera.
- ✅ **Passo 6, il giro finale** (12/10).
  > **Note implementazione**:
  > - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6175 --data-dir
  >   /tmp/librefolio-r2-v-dq --workers 4 front-portfolio all` (`/tmp/libreFolio_v_b2_gate_all_w4.log`, 5 min 53 s,
  >   exit 0):
  >   - privacy-masking 18/18;
  >   - **157/157** test e2e a 4 worker. `dashboard-cache:338` (#5) passa in contemporanea con i due test di
  >     `broker-filter-label` (#3, #4): **V-7 provato**;
  >   - Vitest 1218/1218;
  >   - unica riga ❌: l'avviso noto C-49 sul SIGTERM.
  > - Statici:
  >   - prettier pulito su `dashboard/+page.svelte` e sui tre spec;
  >   - svelte-check 0 errori e 0 avvisi (`/tmp/libreFolio_v_b2_svelte_check.log`);
  >   - gate `htmlSink` e `flagFont` 20/20 (`/tmp/libreFolio_v_b2_gates.log`);
  >   - `check-orphans` pulito (`/tmp/libreFolio_v_b2_check_orphans.log`).
  > - Porta 6175 libera.
- ✅ **Backlog** (12/10): chiuse V-1, V-5 e V-7, con data e rimando al §11. Nuova V-8: il pannello Rischio con un
  broker sparito, 403 e nessuna rilettura. È la domanda che il coordinatore lascia aperta; separata da V-7, così la
  voce chiusa non si cancella. V-6 si chiude con la doc.
- ✅ **Passo 5, V-6 e le righe di V-1 nella doc** (12/10), scritto da docs-writer.
  > **Note implementazione** (`mkdocs_src/docs/developer/frontend/data-quality-banner.md`, +24/−8):
  > - riga `sync_asset_prices` della tabella delle CTA: `refreshVersion` come `sync_fx_pair`; i pannelli lotti e rischio
  >   chiedono di nuovo; dopo un errore, un solo toast e nessuna ricarica;
  > - sezione `data-quality-banners.spec.ts` riscritta: perché inietta le issue (`TEST_USER`, stati di tutto il
  >   portafoglio) e tutti i 18 test, per contesto;
  > - sezione `stale-price-banner.spec.ts`: il secondo test.
  > - `… dev.py mkdocs build` (strict): exit 0, nessun avviso, 3012 URL di asset risolti
  >   (`/tmp/libreFolio_v_b2_docs_build.log`).
  > - `… dev.py mkdocs check-links`: 95 link validi, 0 rotti (`/tmp/libreFolio_v_b2_docs_links.log`).
  > - Build lanciate solo dopo il giro finale, perché l'avvio di un server ricostruisce `mkdocs_src/site`.
  >
  > **⚠️ Fuori pista**: docs-writer ha trovato errori preesistenti, fuori mandato e non corretti. Sono le nuove voci
  > V-9 (due frasi superate nella doc) e V-10 (due difetti latenti in `data-quality-banners.spec.ts`).
- ✅ **Backlog** (12/10): chiusa anche V-6; nuove V-9 e V-10.

### 11.4 Checkpoint del lotto 2 — FROZEN

Il manifest coi blob, i commit proposti in ASCII e le prove sono nel messaggio di checkpoint al coordinatore (12/10).
Le prove sono anche nelle voci di §11.3.

## 12. Lavoro 3 (12/10): V-9 e V-10, isolamento degli E2E, lacune della 1.2

> **Mandato** (coordinatore, 12/10, su richiesta del developer: «riusciamo a riassegnargli qualcosa?»). Base: il mio
> ramo con il lotto 2 committato (`a0722f755`, `4e710a1f9`, `6f5a3bcff`, `d09fb30c0`). Corsia 6175, un checkpoint
> FROZEN per passo.
> 1. V-9 e V-10;
> 2. isolamento degli E2E, la classe di V-7: prima un rapporto con le priorità, poi la cura dei casi peggiori con
>    account usa-e-getta. `gallery.spec.ts` e le sue fixture sono di M: solo segnalazioni;
> 3. sola lettura: le funzioni nuove della 1.2 senza test automatici, una tabella delle 5-10 lacune di più valore.
>
> V-3 e V-8 restano nel backlog: li porta il coordinatore al developer.

### 12.1 Passo 1, stato verificato (HEAD `d09fb30c0`)

- **V-9**, in `mkdocs_src/docs/developer/frontend/data-quality-banner.md`:
  - `:49` dice «First 3 issues are visible; an expand button appears when there are more», ma il banner raggruppato
    parte chiuso (`expanded = false`) e `data-quality-toggle` apre e chiude tutto l'elenco;
  - `:113` cita il testo inglese «still valued at cost», mentre `dataQuality.transactionImplied` dice «valued at their
    last transaction price…».
- **V-10**, in `frontend/e2e/portfolio/data-quality-banners.spec.ts`:
  - il commento a `:282` cita `hasFailedConversion` (`assets/[id]/+page.svelte:501`), che non esiste più. Oggi è
    `getComparisonEventFxDependency` (`frontend/src/lib/charts/loadComparisonData.ts:86`), chiamata da
    `assets/[id]/+page.svelte:697`;
  - il test a `:356-369` è un'asserzione vera: `expect(headerText).not.toMatch(/0 error/i)`. Ha tre difetti:
    - «10 error(s)» contiene «0 error», quindi con 10 errori o più fallirebbe senza ragione;
    - legge l'intestazione con la classe CSS `.font-medium`, vietata;
    - dipende dal seed, con una sonda da 3 s e un'annotazione se il banner non c'è.
  - La cura: prima il rosso che dimostra il difetto, iniettando 10 errori con la vecchia asserzione. Poi un test
    deterministico: issue sostituite per intero, intestazione letta da `data-quality-toggle`, controllo indipendente
    dalla lingua (nessun numero «0» fra i numeri dell'intestazione).

### 12.2 Passo 1, avanzamento

- ✅ **V-10, rosso** (12/10). Test-author di V. Il vecchio controllo, invariato, su un'intestazione decisa dal test:
  dieci `MISSING_PRICE`, ciascuna col suo `group_key`, servite come elenco intero.
  `$P --fresh-run --workers 1 front-portfolio banners`, ristretto al solo test del rosso → 1 test, ✘
  `expect(received).not.toMatch(expected)`, `Expected pattern:
  not /0 error/i`, `Received string: " 10 error(s) "` (`/tmp/libreFolio_v_w3_v10_red.log`, righe 36-50).
  > **Note implementazione**: il difetto è dimostrato, non dedotto: con dieci errori il vecchio test falliva senza
  > ragione.
- ✅ **V-10, cura** (12/10). Test-author di V, solo `frontend/e2e/portfolio/data-quality-banners.spec.ts`.
  - Quattro helper:
    - `serveDashboardIssues` sostituisce per intero `summary.data_quality.issues` del report, e controlla prima che
      ogni issue abbia la sua coppia `code + group_key`;
    - `headerIssue(severity, n)` costruisce le issue;
    - `headerCounts` legge i numeri di `data-quality-toggle`;
    - `expectHeaderCounts` fa `expect.poll(...).toEqual(...)`, poi `not.toContain('0')`.
  - Il vecchio test (sonda da 3 s, annotazione, `.font-medium`) è sostituito da tre test:
    - solo info → nessun numero; prima un testimone, la riga servita con `2019-03-04`;
    - dieci errori → `['10']`;
    - avviso, info, errore, avviso → `['1', '2']`: l'ordine segue la severità, e l'info non è contata.
  - Il commento di `injectForeignEvent` ora descrive `getComparisonEventFxDependency`
    (`charts/loadComparisonData.ts`) e cita i nomi, non le righe: `FAAssetEventPointOut` al posto di
    `schemas/prices.py:326`, anche quello superato.
  - Prove:
    - `$P --fresh-run --workers 1 front-portfolio banners` → 20 passed (2.2 min, `/tmp/libreFolio_v_w3_v10_w1.log`);
    - `$P --fresh-run --workers 4 front-portfolio banners` → 20 passed (25.5 s, `/tmp/libreFolio_v_w3_v10_w4.log`);
    - prettier pulito; tsc offline con un tsconfig temporaneo che estende `tsconfig.e2e.json`: exit 0, poi
      cancellato;
    - porta 6175 libera.
  > **Note implementazione**: il nuovo controllo legge numeri, non parole. Test-author l'ha verificato offline con
  > `intl-messageformat` sui quattro cataloghi: dà `[]`, `['10']` e `['1','2']` in ogni lingua. La vecchia regex,
  > invece, sbagliava due volte: falliva su «10 error(s)» in inglese, italiano e spagnolo, e in francese non avrebbe
  > mai visto «0 erreur(s)».
  > **⚠️ Fuori pista**: test-author ha trovato altre sonde legate al seed nello stesso spec, e non le ha toccate.
  > Vanno nel backlog come V-14:
  > - `expandDataQualityBanner` `:74`;
  > - il test «…grouped with issue rows», `:401` e `:404`;
  > - il test «range-before-data…», `:697` e `:704`;
  > - `goToFirstAssetDetail` `:44`, che apre il primo `asset-card-*` senza filtro;
  > - le righe superate nel commento del test «FX pair missing…».
- ✅ **V-9** (12/10). Docs-writer di V, solo `mkdocs_src/docs/developer/frontend/data-quality-banner.md`.
  - «Component Modes → grouped»:
    - il banner parte chiuso;
    - `data-quality-toggle` apre e chiude tutto l'elenco;
    - errori e avvisi stanno in `data-quality-actionable`, le note info in `data-quality-info`;
    - l'intestazione conta solo errori e avvisi, e nomina solo quelli diversi da zero (`en.json:1715-1717`).
  - La regola `TRANSACTION_IMPLIED` cita il testo attuale di `en.json:1719`. Docs-writer ha aggiunto una frase: le «2
    settimane» sono il periodo di grazia di 14 giorni, contato dal primo BUY/SELL (`portfolio_service.py:1083-1088`).
  - La pagina non ha traduzioni: niente stamp.
  - Prove, dopo il «SITE FREE» (nessun backend nella corsia):
    - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build` → exit 0, «Documentation
      built in 39.59 seconds», «All 3012 relative asset URL(s) in the built site resolve», nessun WARNING
      (`/tmp/libreFolio_v_w3_docs_build.log`);
    - `… dev.py mkdocs check-links` → exit 0, «95 valid link(s)», «All cross-boundary links are valid!»
      (`/tmp/libreFolio_v_w3_docs_links.log`);
    - `mkdocs_src/site` è ignorato (`.gitignore:76`).
  > **⚠️ Fuori pista**: tre rilievi fuori perimetro, verificati da me e messi nel backlog:
  > - V-11: il messaggio `TRANSACTION_IMPLIED` può sbagliare, perché `price_marks.py:197-223` prende l'osservazione
  >   più recente, e un trade di oggi batte la quotazione di ieri;
  > - V-12: il titolo `grouped` nomina solo la Dashboard, ma lo usano anche tre pannelli del Rischio;
  > - V-13: commenti del backend che dicono ancora «valued at cost».

> Checkpoint del passo 1 committato dal coordinatore sul mio ramo: `8994100b4`, `973ca3961`, `f3608a385` (12/10).

### 12.3 Passo 2: isolamento degli E2E, rapporto e mandato

Il rapporto è stato mandato al coordinatore il 12/10.

**Metodo:**
- 5 audit in sola lettura su `frontend/e2e/**`, esclusa la galleria, che è di M;
- verifica a campione delle P1, fatta da me.

**Come si propagano i danni:**
- **Dentro una categoria.** Il parallelo esiste solo lì (`fullyParallel`), quindi una scrittura temporanea su un utente
  condiviso rompe i vicini della stessa categoria: è la classe di V-7.
- **Fra categorie.** Le categorie girano in sequenza: ai-export, asset, broker, fx, portfolio, transaction, user,
  utility. Il DB si popola una volta per invocazione (`_consolidate.py:315`), quindi un resto permanente arriva a tutte
  le categorie successive.
- **Le pulizie automatiche.** txHygiene (`fixtures/playwright.ts:126-127`) e `mock-restore` puliscono solo a 1
  worker.

**A, da curare** (decisione del coordinatore, 12/10: tutte, in due checkpoint):

| # | Spec | Danno | Cura |
|---|---|---|---|
| A1 | `fx/fx-sync.spec.ts` T7 (`:52-73`) | Sync reale in rete dei provider su EUR-USD, senza mock e senza pulizia | Una coppia MOCKFX riservata, creata e tolta nel test; in alternativa `page.route` |
| A2 | `settings.spec.ts`, «theme persists» e «language persists» (`:579-690`) | Possono salvare Dark e Italiano per `TEST_USER`, senza ripristino; sonde, CSS e testo | Account usa-e-getta e asserzioni via API |
| A3 | `settings/scheduler.spec.ts` FSCH-006 e FSCH-006b (`:245-307`) | La frequenza globale `scheduler_current_price_frequency_minutes` resta a 15 o a 20. I due test, in parallelo, si scavalcano | Valore letto e ripristinato in `finally`; i due scrittori in sequenza |
| A4 | `tx-commit-all-types`, `transactions-modals` T1, `tx-wac-formmodal` FM6, `tx-wac-unit-toggle` | Commit reali nei broker del seed di `TEST_USER`, mai cancellati a 4 worker | Id presi dalla risposta del commit, cancellati in `finally` |
| A5 | `tx-split-promote` C3, `tx-paired-edit` | Dividono o modificano una coppia `delete-safe` del seed | Coppia creata dal test |
| A6 | `tx-event-picker` (`:170-203`) | Un DIVIDEND permanente su un asset globale | Evento cancellato per id |
| A7 | `brokers/brokers.spec.ts`, `brokers/multi-user.spec.ts` | Broker di `TEST_USER` che si accumulano | Account usa-e-getta |

- **Ordine.**
  - Checkpoint 2a: A1, A2, A3, che sporcano lo stato globale.
  - Checkpoint 2b: A4-A7.
  - Per ciascuno, il rosso o la prova del danno prima della cura, via test-author.
- **Prova.** Ogni categoria toccata a 4 worker, più `front-portfolio all` a 4.
- **B, la classe di V-7.** Circa 27 spec creano e cancellano broker di `TEST_USER`, con pulizia per id. Il rischio sta
  solo nella propria categoria, e non c'è un rosso dimostrato: vanno nel backlog come V-15.
- **C, note:**
  - `tx-delete` consuma una coppia che il seed gli riserva;
  - il test 2 di `asset-event-delete` conta su eventi Apple tutti collegati;
  - l'header di `fx-sync-mock` dice «writes nothing», ma sincronizza le coppie MOCKFX del seed, in modo idempotente.
- **Due casi nuovi della classe A7**, trovati il 12/10 nel censimento meccanico per V-15. Il censimento cerca con una
  regex gli spec che creano broker e citano `TEST_USER`: 33 risultati, letti uno per uno. Li
  propongo per la 2b:
  - `transactions/tx-import-resolution.spec.ts` IWR-009 (`:626`) crea dalla UI il broker `E2E Test Broker <ts>` di
    `TEST_USER` e non lo cancella. Ha anche un `return` condizionale quando il selettore non c'è;
  - `transactions/tx-clone.spec.ts`, «clone inside the workspace (cloneRow)…» (`:549`), crea via API il broker
    `T3-ws-<suffix>`, ma nel `finally` cancella solo la transazione.
  - Scartati dopo la lettura: `image-crop` e `select-components` aprono il modale del broker ma non salvano;
    `broker-sharing` registra utenti suoi.

### 12.4 Passo 3: le lacune 1.2 e la scelta del developer

La tabella è stata mandata il 12/10. La bozza intera è nei file di sessione di V, `gaps-1.2-draft.md`.

**Le 8 lacune:**
1. Rischio L1/L4 con un `/risk/query` vero fino allo schermo. Oggi tutti gli E2E sono su risposte finte.
2. La riga «FX on cash» e la cassa estera rivalutata: solo backend.
3. Il PAC allocator, in beta.
4. YOC nelle posizioni.
5. Il trasferimento in Auto, che porta il costo d'origine.
6. La cancellazione dell'account.
7. L'anteprima PDF senza CDN.
8. Scalable con un export reale.

**Lacune già coperte, scartate dopo la verifica:**
- Rolling Return;
- la diagnostica senza login;
- CLI `user deactivate`;
- le card dei broker col trasferimento;
- la riga nuova del data editor;
- il costo nel promote.

**Scelta del developer** (12/10, via coordinatore): «Tutte e 7 nella 1.2 (circa 3 giorni dopo A1–A7)».
- L'ordine: 2, 1, 6, 4, 7, 5, 3.
- Un checkpoint ogni due o tre lacune.
- Tutti i test via test-author, su account usa-e-getta, verdi a 1 e a 4 worker.
- Un comportamento sbagliato → STOP e messaggio al coordinatore.
- La lacuna 8 resta fuori finché manca il dato.
- C-42 e B9 restano nel backlog.

### 12.5 Passo 2a, avanzamento

- ✅ **A2 e A3, prova del danno** (12/10). Test-author di V, con gli spec invariati, `--fresh-run --workers 1`. Dopo
  ogni giro una lettura del DB della corsia in sola lettura (Python, `mode=ro`).

  | Giro | Comando | DB dopo il giro |
  |---|---|---|
  | 1 | `front-utility settings "preferences persist after navigating away and back"` (innocuo) | `e2e_test_user` `en`/`light`, frequenza `10` |
  | 2 | `front-utility settings "theme preference persists…" "language change persists…"` | `e2e_test_user`: **lingua `it`**, tema `light` |
  | 3 | `front-utility scheduler "FSCH-001"` (innocuo) | Lo scheduler com'è nel seed: frequenza `10`, `06:00,23:00`, `mon…sat`, orizzonte `14`, `UTC` |
  | 4 | `front-utility scheduler "FSCH-006"` (006 e 006b) | **Frequenza `20`**. Le cinque chiavi salvate dal modale hanno lo stesso `updated_at` e `updated_by_user_id` 1 |

  Log: `/tmp/libreFolio_v_a2a3_s1-{a2-harmless,a2-damage,a3-harmless,a3-damage}.log`.
  > **Note implementazione**:
  > - A2: il test della lingua salva l'italiano per `TEST_USER` e non lo ripristina. Ogni sessione successiva di
  >   `TEST_USER` lo vede in italiano, per esempio il controllo in inglese di `connection-security.spec.ts:116`;
  > - il test del tema è vuoto: `[class*="dark"]` prende il contenitore della riga, per via della classe Tailwind
  >   `dark:`, e non salva niente;
  > - A3: un salvataggio del modale riscrive **cinque** chiavi globali (frequenza, `_history_sync_times`,
  >   `_history_sync_days`, `_history_sync_horizon_days`, `scheduler_timezone`). Senza ripristino vince l'ultimo che
  >   scrive.
  >
  > **⚠️ Fuori pista**: test-author ha notato che in questi giri il setup di Playwright ripopola il DB e ricrea gli
  > utenti anche se il runner l'ha appena fatto, perché su questa strada `LF_SETUP_DONE` sembra mancare. Sono circa
  > 20 s a giro. Solo nota.
- ✅ **Attributi per A2** (12/10, applicati da me, solo attributi; le impostazioni non sono file di I, U, T o M):
  - `frontend/src/lib/components/settings/SettingTheme.svelte`: sul `<button>` di ogni opzione,
    `data-testid="setting-theme-option-{option.value}"` e
    `aria-pressed={value === option.value ? 'true' : 'false'}`. È la convenzione di `SettingsLayout.svelte`;
  - `frontend/src/lib/components/settings/SettingSelect.svelte`: su `SimpleSelect`,
    ``optionTestId={(option) => `setting-select-option-${option.value}`}``. La prop esiste già, e le opzioni pubblicano già
    `aria-selected`.
  - Usati anche da `GlobalSettingsTab` (i default dell'admin) e da `WelcomeForm` (la lingua). Il conteggio
    `[data-testid*="theme"]` di `WelcomeForm.test.ts:214` non cambia, perché `WelcomeForm` non usa `SettingTheme`.
  - Prove: prettier pulito. `frontend/node_modules/.bin/vitest run` su SettingControls, GlobalSettingsTab,
    PreferencesTab, WelcomeForm e WelcomePage → 5 file, 257 passed (`/tmp/libreFolio_v_attr_vitest.log`).
- ✅ **A1, prova del danno** (12/10). Test-author di V, spec invariato, `--fresh-run --workers 1`. Letture del DB in sola
  lettura.
  - 1a: `front-fx fx-sync "can open Sync All modal"` (innocuo) → 1 passed. EUR-USD: 275 righe; nessuna riga scritta
    dopo il seed.
  - 1b: `front-fx fx-sync "sync from detail page triggers action"` (T7) → 1 passed. EUR-USD: **65 righe riscritte
    durante il test**, tutti i giorni lavorativi della finestra di 3 mesi della pagina. Sono fixing ECB veri, a 4
    decimali, presi dalla rete: 2026-07-14 passa da 1,11247… del seed a 1,1405. La somma dei tassi della finestra va
    da 73,281088 a 75,778255.
  - Il log del backend registra `"cache_name": "portfolio_layer2", "event": "Cache cleared"` subito dopo il sync. Nel
    giro 1a non c'è.
  - T7 aspetta solo `sync-modal-results`, che compare anche in caso di errore. Offline resterebbe verde senza provare
    niente.

  Log: `/tmp/libreFolio_v_a1_step1a.log`, `/tmp/libreFolio_v_a1_step1b.log`.
  > **⚠️ Fuori pista**: test-author ha trovato un gemello di T7: `fx/fx-detail.spec.ts`, «sync single pair reports its
  > outcome in the modal» (`:1623`). Stesso sync ECB reale di EUR-USD, stessa finestra, solo l'attesa dei risultati.
  > L'ho incluso nella cura di A1 (A1b) perché è lo stesso danno, e lo segnalo al coordinatore. Non serve una seconda
  > prova: flusso, coppia e finestra sono identici a T7.
- ✅ **A1 e A1b, cura** (12/10). Test-author di V; ha toccato solo `fx/fx-sync.spec.ts` (T7) e `fx/fx-detail.spec.ts`
  («sync single pair reports its outcome in the modal»). Gli altri test non sono cambiati.
  - Ogni test ha la sua coppia, solo MOCKFX e niente rete. Per T7, EUR-TTD su desktop ed EUR-JMD su mobile; per il
    gemello, EUR-GTQ ed EUR-HNL. Sono codici ISO veri, che si ordinano dopo EUR e che nella worktree non usa nessuno
    (grep a parola intera, file ignorati compresi).
  - La coppia si crea e si toglie nella fixture locale dello spec, con la pulizia nel `finally` della fixture: così
    regge anche un timeout. Prima si tolgono gli avanzi e si verifica la coppia vuota.
  - La pagina si apre su una finestra esplicita, i 10 giorni prima di oggi.
  - Le asserzioni:
    - la richiesta è esattamente `{pairs, start, end}`;
    - la risposta, validata con lo schema generato: `ok`, MOCKFX, 10 scaricati, 10 cambiati;
    - i conteggi del modale, letti dai `data-*` di `SyncModalBase`: 1/1/0/10/10;
    - il grafico finisce a `1.2345`;
    - la rilettura via API dà 10 giorni, tutti esattamente 1,2345, nessuno riportato da un altro giorno.
  - Il timeout passa da 120 s a 60 s.
  - Prove (`--fresh-run`):

    | Comando | Esito | Log |
    |---|---|---|
    | `--workers 1 front-fx fx-sync` | 3/3 | `/tmp/libreFolio_v_a1_step3a.log` |
    | `--workers 4 front-fx fx-sync` | 3/3 | `/tmp/libreFolio_v_a1_step3b.log` |
    | `--workers 1 front-fx fx-detail` | 17/17 | `/tmp/libreFolio_v_a1_step3c.log` |
    | `--workers 4 front-fx fx-detail` | 17/17 | `/tmp/libreFolio_v_a1_step3d.log` |

  - Dopo ogni giro, il DB letto in sola lettura: niente su TTD, JMD, GTQ e HNL, nessuna riga EUR-USD scritta dopo il
    seed (la somma dei tassi resta 300,374094 come nel giro innocuo), 24 rotte e 4125 tassi come nel seed. Il log del
    backend ha un solo sync per giro, verso MOCKFX.
  - Prettier pulito; tsc strict offline exit 0, con `--noUnusedLocals` pulito.
  > **Note implementazione**: prima T7 restava verde anche offline, perché aspettava solo il riepilogo, che compare
  > anche quando il sync fallisce. Ora dimostra che il sync è riuscito.
  > **⚠️ Fuori pista**: altre note di test-author, lasciate intatte:
  > - aprire un modale di sync chiama `GET /fx/providers`, e il backend scarica una volta per processo l'elenco valute
  >   di SNB da data.snb.ch. È solo lettura, e offline l'errore è gestito;
  > - `fx-sync-mock.spec.ts` lascia tassi MOCKFX sulle sue coppie del seed. Già nota C.
- ✅ **A2 e A3, cura** (12/10). Test-author di V; ha toccato solo `frontend/e2e/settings.spec.ts` e
  `frontend/e2e/settings/scheduler.spec.ts`.
  - **A2**:
    - i due test che scrivono girano su un account usa-e-getta. Le preferenze `en`/`light` sono impostate via API
      prima del login, e l'account è cancellato in `finally`;
    - la scelta passa per i testid nuovi, dentro le righe `preference-theme`/`preference-language`;
    - si controllano il corpo della PUT, l'evento `settings.preferences.saved` e `GET /settings/user` (`dark`, `it`);
    - dopo il reload o il `goto`: `<html class="dark">`, oppure `lang="it"` con `data-i18n-ready`; poi la tab
      riaperta mostra l'opzione salvata (`aria-pressed`, `aria-selected`);
    - niente più sonde, selettori di testo o `networkidle`;
    - il test del tema prima non salvava niente: ora prova davvero.
  - **A3**:
    - ogni test che scrive legge prima le cinque chiavi dello scheduler, e in `finally` le ripristina con la PATCH
      bulk come admin, poi le rilegge;
    - il salvataggio aspetta la risposta della PATCH;
    - FSCH-006 e 006b stanno in un `describe('Saving')` seriale annidato, con la ragione scritta;
    - in FSCH-005…009, `settings-lock-toggle` e `scheduler-config-btn` sostituiscono i selettori in inglese.
      Precondizione: «Configure» disabilitato; prova dello sblocco: abilitato;
    - FSCH-005/007/008/009 non salvano niente.
  - **About Tab**: il `beforeEach` aspetta `about-tab` con `data-busy="false"`. Attesa di stato, 20 s.
  - **Prove** (`--fresh-run`):

    | Comando | Esito | Log |
    |---|---|---|
    | `--workers 1 front-utility settings` | 45/45 | `/tmp/libreFolio_v_a2a3_v2-settings-w1.log` |
    | `--workers 4 front-utility settings` | 45/45 | `/tmp/libreFolio_v_a2a3_v2-settings-w4.log` |
    | `--workers 1 front-utility scheduler` | 17/17 | `/tmp/libreFolio_v_a2a3_v2-scheduler-w1.log` |
    | `--workers 4 front-utility scheduler` | 17/17 | `/tmp/libreFolio_v_a2a3_v2-scheduler-w4.log` |

  - Il log del backend mostra quattro scritture delle cinque chiavi per giro, a coppie che non si intrecciano.
  - Dopo ogni giro il DB è pulito: `e2e_test_user` ancora `en`/`light`/`EUR` al timestamp del populate; le chiavi
    dello scheduler con i valori del seed; nessun utente usa-e-getta rimasto.
  - Prettier pulito, tsc exit 0.
  > **⚠️ Fuori pista**:
  > - il primo giro di `settings` a 4 worker ha dato 3 rossi fuori da A2 e A3. Due erano i test della About Tab
  >   (`settings.spec.ts:540` e `:555`): dopo 3 s la tab caricava ancora le sue sette richieste, e non pubblicava uno
  >   stato di pronto. La cura, approvata da me: `data-busy`/`aria-busy` sulla radice di `AboutTab.svelte` (solo
  >   attributi, convenzione dei Tool), l'attesa nel `beforeEach`, Vitest AboutTab 36/36. I test nuovi di A2 sono più
  >   pesanti (registrazione e login), e quel carico li aveva spinti oltre i 3 s;
  > - il terzo rosso era `fx/fx-chart-settings.spec.ts:37`: la pagina FX non si era assestata in 20 s all'inizio del
  >   giro. Non si è più riprodotto nei giri `settings` v2 e `front-fx all` a 4 worker. Resta senza spiegazione, perché
  >   senza retry non c'è trace;
  > - la chiave `settings` del runner raccoglie anche `fx/fx-chart-settings.spec.ts`, che fa 45 test e non 42 (V-17);
  > - bcrypt gira dentro i gestori async di login e registrazione (V-16).
- ✅ **Gate della 2a** (12/10, eseguiti da me, `--fresh-run`, uno alla volta nella corsia 6175):

  | Comando | E2E | Vitest | Log |
  |---|---|---|---|
  | `--workers 4 front-fx all` | 103/103 | 138/138 | `/tmp/libreFolio_v_2a_gate_fx.log` |
  | `--workers 4 front-utility all` | **218/224** | 6979/6979 | `/tmp/libreFolio_v_2a_gate_utility.log` |
  | `--workers 4 front-portfolio all` | 177/177 (18 + 159) | 1218/1218 | `/tmp/libreFolio_v_2a_gate_portfolio.log` |

  Altri controlli: svelte-check con 0 errori e 0 warning; prettier pulito sui 7 file; `git diff --check` pulito.
  > **⚠️ Fuori pista: i 6 rossi di `front-utility all` a 4 worker, con il triage** (skill test-triage; log
  > `/tmp/libreFolio_v_2a_triage_*.log`). Nessuno sta in un file toccato dalla 2a.
  > - **`layout/toolbar-width-sweep.spec.ts:873`, `es`, dashboard e assetDetail → difetto.** In spagnolo il gruppo
  >   «Exportación IA …» esce dalla barra in modo denseRow: +11,8 px a vw 1210 sull'asset, +11,0 px a vw 1310 sulla
  >   dashboard. Ripetuto a 1 worker (`--workers 1 front-utility toolbar-width-sweep "es: 1700"`: 2 rossi, 3 verdi),
  >   quindi deterministico e indipendente dal carico. Il delta della 2a non tocca né queste barre né i cataloghi.
  >   Backlog V-19.
  > - **`auth.spec.ts:379` e `:615` (Integrated onboarding 1 e 4) → assunzione sull'orologio, sotto carico.** Dopo
  >   `login()`, `toHaveURL(/dashboard/)` usa i 3 s di default; il test accanto (`:370`) per la stessa attesa ne usa 15.
  >   Al momento del rosso la pagina era ancora su `/`.
  > - **`layout/app-start-auth.spec.ts:184` → assunzione sull'orologio, sotto carico.** Il poll di 3 s su `/auth/me`
  >   dopo `goto('/assets')` è verde a 1 worker (3/3, `--workers 1 front-utility app-start-auth`) e rosso a 3 worker
  >   anche da solo: con soli tre test i fratelli passano da 2,7 e 5 s a 15 e 18 s.
  > - **`files.spec.ts:835` → carico.** Ha esaurito i 30 s nel giro pieno; da solo a 4 worker `files` è verde, 28/28.
  > - Lanciato da solo, `front-utility auth` a 4 worker dà 6 rossi, tutti attese di 3 s sulla prima navigazione. Su
  >   questa chiave il runner non popola, e il setup di Playwright ripopola con il backend già acceso: è **ambiente**,
  >   V-17. Nel giro consolidato non succede: lì il runner popola e il setup salta.
  > - Backlog V-20 per le attese di 3 s. Possibile concausa del rallentamento: bcrypt nell'event loop (V-16).

> Checkpoint 2a committato dal coordinatore: `e6333930c`, `495fb9e86`, `6d62171e3`, `262515898`. Treno 64 integrato:
> `dev_release2` = `0afac8e14`, e il mio ramo è stato portato lì in fast-forward (12/10). Nessuno dei 50 commit del
> treno tocca i file della 2b, le fixture o `auth.py`.

### 12.6 Passo 2b: mandato e avanzamento

**Decisioni del coordinatore** (12/10):
- **Gate di `front-utility` con i 6 rossi**: accettato per la 2a. V-19 va a I, nel lotto di rifinitura UI: nasce da
  `7c66234a7`, «Exportar IA» → «Exportación IA», e il termine resta. V-20 lo faccio io, nella 2b, con attese su uno
  stato pubblicato. V-17 resta nel backlog: `_frontend_utility.py` ora è di T.
- **IWR-009 e `tx-clone:549`**: entrano nella 2b (A7b, A7c).
- **V-16 (bcrypt nell'event loop)**: nella 1.2, da me dopo la 2b. `backend/app/api/v1/auth.py`, le tre chiamate
  (`:105`, `:205`, `:253`), con `await asyncio.to_thread(...)`.
  - Prima il rosso, via test-author.
  - Poi i gate `api` di auth e un E2E di login.
  - Altri punti dello stesso tipo: li segnalo senza toccarli.
- **Ordine**: 2b (A4-A7, A7b, A7c, V-20), poi V-16, poi le 7 lacune.

**Lavoro della 2b**, con quattro test-author su file distinti e la corsia 6175 data a turno:

| Agente | Casi | File |
|---|---|---|
| `b-tx-commit` | A4 | `transactions/tx-commit-all-types.spec.ts`, `transactions-modals.spec.ts` (T1), `tx-wac-formmodal.spec.ts` (FM6), `tx-wac-unit-toggle.spec.ts` |
| `b-tx-seed` | A5, A6 | `transactions/tx-split-promote.spec.ts` (C3), `tx-paired-edit.spec.ts`, `tx-event-picker.spec.ts` |
| `b-brokers` | A7, A7b, A7c | `brokers/brokers.spec.ts`, `brokers/multi-user.spec.ts`, `transactions/tx-import-resolution.spec.ts` (IWR-009), `transactions/tx-clone.spec.ts` (`:549`) |
| `b-v20` | V-20 | `auth.spec.ts` (`:379`, `:615`), `layout/app-start-auth.spec.ts` (`:184`), `files.spec.ts` (`:835`) |

**Gate finali**, a 4 worker: `front-transaction all`, `front-broker all`, `front-user all`, `front-utility all`,
`front-portfolio all`.
- ⏸️ **Stop dell'ambiente** (12/10, 17:23, coordinatore). Il `brew upgrade` dello sviluppatore ha rotto `node`:
  `dyld: Library not loaded: libsimdjson.33.dylib`. Nessun nuovo comando frontend (Playwright, prettier, tsc, vitest,
  svelte-check, npm) finché il coordinatore non dice che `node` è tornato sano. I rossi prodotti da `node` che aborta
  sono ambiente: niente triage, nessuna modifica al codice per loro. Ho avvisato i quattro test-author. Si può
  continuare a scrivere codice, e le letture del DB in Python vanno bene.
- ▶️ **`node` di nuovo sano** (12/10, 17:26, coordinatore): v26.11.1. Python è passato a 3.13.16, e il venv lo segue;
  il coordinatore l'ha verificato. Nuovo ordine sulla 6175, una suite alla volta: V-16 lato backend, poi l'E2E di
  login, poi la 2b. b-brokers aveva già ripreso le sue prove (P0-P4) e le finisce prima di V-16, che intanto sta
  ancora scrivendo il rosso.

### 12.7 V-16: bcrypt fuori dall'event loop (checkpoint a sé)

- **Mandato** (coordinatore, 12/10). Anticipare adesso la parte backend: il rosso via test-author (pytest), la cura e i
  gate `api` di auth. L'E2E di login quando `node` è sano. Checkpoint separato dalla 2b.
- **File assegnati**:
  - `backend/app/api/v1/auth.py`, le chiamate di login (`:123`) e del cambio password (`:253`, `:262`);
  - `backend/app/services/user_service.py`, la riga di `create_user` (`:168`), con la firma invariata perché la usa
    anche il CLI sotto `asyncio.run`.
- **Restano come sono**, d'accordo col coordinatore:
  - `user_service.reset_password` (`:204`), usata solo dal CLI;
  - `_dummy_password_hash` (`auth_service.py:69-71`), coperta dalla cura del login.
- **Cura prevista**:
  - login: `password_ok = await asyncio.to_thread(verify_password_or_dummy, …)`;
  - cambio password: `await asyncio.to_thread(verify_password, …)` e `await asyncio.to_thread(hash_password, …)`;
  - `create_user`: `hashed_password=await asyncio.to_thread(hash_password, password)`.
- **Gate**: `api auth`, `api profile`, `api account-deletion`; poi un E2E di login.
- ✅ **A7, A7b, A7c: prova del danno** (12/10). b-brokers, spec invariati, `--fresh-run`. Dopo ogni giro il DB letto in
  sola lettura; base del seed: 8 broker, 11 utenti, 76 transazioni.

  | Giro | Comando | Esito | Resti nel DB |
  |---|---|---|---|
  | P0 | `front-broker list "can access brokers page"` (innocuo) | 1/1 | nessuno |
  | P1 (A7) | `front-broker list "create broker with name\|full broker CRUD flow"` | 2/2 | `Test Broker <ts>`, OWNER `e2e_test_user` |
  | P2 (A7) | `front-user multi-user` | 2/2 | `Private Broker <ts>` e `Unique Broker <ts>`, OWNER `e2e_test_user` |
  | P3 (A7b) | `front-transaction tx-import-resolution "IWR-009"` | 1/1 in 3,2 s | **nessuno: passa in silenzio** |
  | P4 (A7c) | `front-transaction tx-clone "clone inside the workspace"` | 1/1 | `T3-ws-<suffix>`, OWNER `e2e_test_user` |

  Log: `/tmp/libreFolio_v_b_brokers_p{0_harmless,1_list,2_multiuser,3_iwr009,4_t3}.log`.
  > **Note implementazione**: IWR-009 non crea mai il broker. Il selettore esiste solo con file in attesa
  > (`ImportWizardModal.svelte:4549-4551`), il test non ne aggiunge, e quindi esce sempre dal `return` condizionale.
  > La cura gli dà un CSV nel passo 1. Il file resta nel browser, perché senza Next non viene caricato. Il selettore
  > diventa una precondizione asserita, e il broker creato si cancella per id.
  > **⚠️ Fuori pista**: i primi due tentativi di P0 sono caduti per ambiente, durante il `brew upgrade`. Il primo ha
  > avuto il backend uscito con codice 250 nella build automatica; il secondo, il backend oltre i 300 s per le
  > ricostruzioni. Il terzo è verde.
- ✅ **V-16, rosso** (12/10). Test-author di V. Una classe nuova in fondo a
  `backend/test_scripts/test_api/test_auth_api.py`, `TestPasswordWorkLeavesTheEventLoopFree`.
  - Ogni test chiama il gestore in-process, su un SQLite suo sotto `tmp_path`, con un account il cui hash è un marcatore
    (nessun bcrypt vero, niente scritture nel DB della corsia).
  - La funzione password che il gestore chiama è sostituita, via `monkeypatch`, da un sostituto che blocca il suo thread
    per 0,4 s. Un heartbeat nello stesso loop batte ogni 10 ms, e si misura il buco più lungo **durante** il
    sostituto, con limite 0,15 s.
  - Si controllano anche gli esiti, quindi un test non diventa verde saltando il lavoro: 401 per il login, l'hash del
    sostituto salvato, gli argomenti delle chiamate.
  - I test: LOOP-000 controlla lo strumento di misura e deve passare sia prima sia dopo la cura; LOOP-001 login;
    LOOP-002 register, che passa da `user_service.create_user`; LOOP-003 cambio password.
  - `… api auth "event_loop"` → **3 failed, 1 passed**. Buchi misurati: login 0,412 s, register 0,404 s, cambio
    password 0,402 s più 0,402 s; LOOP-000 verde (`/tmp/libreFolio_v_v16_red.log`).
  - ruff e black puliti.
- ✅ **V-16, cura** (12/10, applicata da me):
  - `api/v1/auth.py:123`: `password_ok = await asyncio.to_thread(verify_password_or_dummy, …)`;
  - `:254`: `await asyncio.to_thread(verify_password, …)`;
  - `:263`: `await asyncio.to_thread(hash_password, …)`;
  - `services/user_service.py`: `import asyncio`, e alla riga `:169`
    `hashed_password=await asyncio.to_thread(hash_password, password)`. La firma non cambia, quindi il CLI continua a
    funzionare.

  ruff e black puliti.
  - Prove sulla 6175, una alla volta:

    | Comando | Esito | Log |
    |---|---|---|
    | `api auth "event_loop"` | 4/4 | `/tmp/libreFolio_v_v16_green.log` |
    | `api auth` | 60/60 | `/tmp/libreFolio_v_v16_auth.log` |
    | `api profile` | 12/12 | `/tmp/libreFolio_v_v16_profile.log` |
    | `api account-deletion` | 6/6 | `/tmp/libreFolio_v_v16_accdel.log` |
    | E2E di login: `--fresh-run --workers 1 front-utility settings "Preferences Persistence"` | 3/3 | `/tmp/libreFolio_v_v16_e2e_w1.log` |
    | lo stesso con `--workers 4` | 3/3 | `/tmp/libreFolio_v_v16_e2e_w4.log` |

  - Ho scelto per l'E2E «Preferences Persistence», già committato nella 2a e non toccato dalla 2b: registra un utente
    via API (`create_user`) e fa il login dalla UI, con verifica della password. `auth.spec.ts` lo sta riscrivendo
    b-v20, e non è ancora verificato.
  > **Note implementazione**: test-author ha passato in rassegna tutti i gestori `async def` di `backend/app/api/v1`,
  > cercando chiamate dirette a bcrypt, I/O su file, `shutil`, `subprocess` e `urlopen`. Ha trovato solo i tre punti di
  > V-16; l'`open` di `uploads.serve_file` gira già in `asyncio.to_thread`. La rassegna non scende nei servizi.
  > `user_service.reset_password` (`:205`, solo CLI) resta com'è.

> Checkpoint V-16 committato dal coordinatore sul mio ramo: `a9e0fe4d9`, `0d6aee67c`, `3aabf0916`. È un commit
> parziale: solo i 5 file, verificati blob per blob, mentre gli spec della 2b restano sporchi e intatti. Treno 66:
> `dev_release2` = `b91d6d902`. Il mio ramo resta a `3aabf0916`, perché la worktree ha la 2b in corso. I treni 65 e 66
> toccano solo wiki, CHANGELOG, la pipeline delle traduzioni e V-16 (12/10).

### 12.8 Passo 2b, avanzamento (dopo V-16)

- **Ordine della corsia**: le prove di A4 (b-tx-commit) e di A5/A6 (b-tx-seed); poi le verifiche di b-brokers,
  b-tx-commit, b-tx-seed e b-v20; poi i gate di categoria.
- ✅ **Una riga in più per la 2b** (coordinatore, 12/10; l'ha trovata W). In `frontend/playwright.config.ts:42-45` il
  commento diceva «fullyParallel is off», mentre il valore è `true` (`:103`) e il commento accanto («On by default, and
  earned…») lo conferma. Il resto della frase era giusto: il default di 1 worker esiste davvero, e il runner lo alza
  esportando `E2E_WORKERS` (`_frontend_common.py:316-317`). Ora dice: «fullyParallel is on, but every test of a lane
  shares one database and one backend, so raising the workers is a decision taken per run (the test runner's
  `--workers` exports E2E_WORKERS), not a silent default». Prettier pulito.
  > **⚠️ Fuori pista**: lo stesso blocco elenca il catalogo dei blocchi seriali (`:102`, «Currently: brokers/multi-user,
  > asset-event-delete, tx-brim-import»), e l'elenco non è più vero. `asset-event-delete` seriale non è più. Mancano
  > `files-destructive`, `fx-destructive` e il blocco «Saving» di `settings/scheduler.spec.ts`, aggiunto nella 2a. Lo
  > allineo a fine 2b, quando sarà chiaro se `brokers/multi-user` resta seriale. È il terzo punto di V-17.
- ✅ **A4, prova del danno** (12/10). b-tx-commit, spec invariati, `--workers 4`. Dopo ogni giro il DB letto in sola
  lettura, confrontato col seed di P0: 76 righe, id 1-76.

  | Giro | Spec | Esito | Id assegnati | Rimasti |
  |---|---|---|---|---|
  | P0 | `tx-wac-unit-toggle "toggle is visible"` (innocuo) | 1/1 | — | seed |
  | P1 | `tx-commit-all-types` | 19/19 | 24 | **22** (19 su IB, 3 su Directa) |
  | P2 | `transactions-modals` | 19/19 | 0 | 0 |
  | P3 | `tx-wac-formmodal` | 10/10 | 3 | **3** (FM6: un BUY di 10 Apple e un TRANSFER IB→Directa) |
  | P4 | `tx-wac-unit-toggle` | 4/4 | 1 | **1** (ADJUSTMENT +4 su Charles Schwab) |

  - **26 transazioni rimaste a ogni giro** sui broker di `TEST_USER`. Nessuna riga del seed cancellata o modificata.
  - Log: `/tmp/libreFolio_v_b_txcommit_p{0..4}_*.log`.
  > **Note implementazione**:
  > - T1 di `transactions-modals` committa davvero, ma va in rollback: sceglie il primo broker della tendina, Charles
  >   Schwab, che non ha cassa, e la sua asserzione accetta il rollback. Oggi non lascia niente, ma lascerebbe una riga
  >   appena quel broker potesse pagare;
  > - T10 non cancella niente: la sua sonda su `confirm-modal-confirm` risponde sempre falso;
  > - nei giri di una sola chiave `txHygiene` non è mai attivo, a nessun numero di worker: `LF_TX_HYGIENE` lo imposta
  >   solo il giro consolidato `all` a 1 worker.
- ✅ **A5 e A6, prova del danno** (12/10). b-tx-seed, spec invariati, `--workers 1`, il DB letto dopo ogni giro. Base:
  76 transazioni, 11 eventi, 8 broker, 11 utenti. 43↔44 è la coppia `delete-safe`, 45↔46 la `delete-consume`.
  - P0, Guard (innocuo) → base invariata.
  - P1, C3 → **43 e 44 diventano due ADJUSTMENT scollegati** (−0,002 e +0,001), aggiornati durante il test. Gli id
    non cambiano, quindi nemmeno `txHygiene` la rimetterebbe a posto: lui toglie solo id nuovi, o ripopola quando ne
    manca uno. Il messaggio d'errore di `tx-bulk-suggest-ux` lo dice già.
  - P2, TODO-B di `tx-paired-edit` → colpisce la coppia **`delete-consume`**, non la `delete-safe`. Le due descrizioni
    diventano «E2E-paired-edit-<ts>», e `tx-delete` A2-confirm non la trova più, perché la cerca per descrizione
    (`findRow(page, 'delete-consume', 'ETH')`).
  - P3, A6 → **un DIVIDEND nuovo su Apple**, asset condiviso: `asset_events` 12, 1,50 USD, «E2E test event». Nessuna
    transazione salvata.

  Log: `/tmp/libreFolio_v_b_txseed_proof{0_baseline,1_c3,2_pairededit,3_eventpicker}.log`.
- ✅ **A7, A7b, A7c: cura e verifica** (12/10). b-brokers; ha toccato solo `brokers/brokers.spec.ts`,
  `brokers/multi-user.spec.ts`, `transactions/tx-import-resolution.spec.ts` (IWR-009) e
  `transactions/tx-clone.spec.ts` (`:549`).
  - **`brokers.spec.ts`**:
    - «create broker with name» e «full broker CRUD flow» girano su un account usa-e-getta, preso da una fixture
      locale. Nel teardown la fixture cancella i broker per id e poi l'account, anche dopo un rosso o un timeout;
    - l'id viene dall'evento `broker.created`;
    - «can open edit modal» e «can open delete dialog» passavano in silenzio su `if (count > 0)` e sul primo card.
      Ora agiscono per id sul broker del seed «Interactive Brokers», letto via API, e non scrivono niente.
  - **`multi-user.spec.ts`**: due account usa-e-getta, registrati in `beforeAll`, al posto di `TEST_USER` e
    `TEST_USER_2`. `afterAll` cancella i broker per id e poi i due account. Il blocco resta `serial`, con la ragione
    vera: contesti, account e id sono condivisi in ordine fra i due test.
  - **IWR-009**: niente più `return`. Il test apre il wizard e lascia un CSV nel passo 1 (resta nel browser). Il
    selettore diventa una precondizione asserita. Il broker è creato dal modale, confrontato con l'id dell'evento e
    cancellato per id nel `finally`.
  - **`tx-clone:549`**: usa il `withOwnedBroker` dello spec, che cancella prima il DEPOSIT e poi il broker per id,
    anche dopo un rosso. La sonda davanti al FormModal è diventata un'asserzione.
  - **Verifiche** (`--fresh-run`, a 1 e a 4 worker):

    | Chiave | Esito |
    |---|---|
    | `front-broker list` | 9/9 e 9/9 |
    | `front-user multi-user` | 2/2 e 2/2 (seriale) |
    | `front-transaction tx-import-resolution` | 15/15 e 15/15 |
    | `front-transaction tx-clone` | 8/8 e 8/8 |

  - Dopo ogni giro il DB contiene solo il seed: 8 broker, 11 utenti, 76 transazioni, 30 accessi.
  - Log: `/tmp/libreFolio_v_b_brokers_v{1..8}_*.log`.
  - Prettier, tsc e `git diff --check` puliti.
  > **⚠️ Fuori pista**: altre sonde rimaste negli stessi file, che b-brokers non ha toccato:
  > - `tx-import-resolution`: `openImportWizard` usa un `.first()` senza filtro; IWR-007 e IWR-010 hanno `return`
  >   condizionali; IWR-006b ha un controllo che ripiega su uno più debole;
  > - `tx-clone`: righe scelte per posizione, classi CSS, `text=new`; il test «view-only» esce presto.
  >
  > Vanno nel backlog come V-21.
- ⏸️ **STOP chiesto dallo sviluppatore** (12/10, 18:26, via coordinatore). Fermo al primo punto stabile, FROZEN fino a
  «riparti». Nessun server acceso, porta 6175 libera. Nessun checkpoint della 2b: non era pronto.

  **Stato esatto della 2b al momento dello stop:**

  | Caso | Agente | Prova del danno | Cura nei file | Verifiche | Prossimo passo |
  |---|---|---|---|---|---|
  | A4 | b-tx-commit | ✅ 26 transazioni rimaste a giro | ✅ applicata nei 4 spec | **a metà**: V1-V2 `tx-commit-all-types` 19/19 e 19/19; V3-V4 `transactions-modals` 19/19 e 19/19; V5-V6 `tx-wac-formmodal` 10/10 e 10/10. **Da fare**: V7-V8 `tx-wac-unit-toggle` w1 e w4. V7 era partito alle 18:33:58, prima che lo STOP arrivasse all'agente; l'ho fermato io per PID, porta libera alle 18:34:09: non conta | i due giri mancanti, con la lettura del DB |
  | A5, A6 | b-tx-seed | ✅ coppie 43↔44 e 45↔46 alterate, DIVIDEND su Apple | ✅ applicata nei 3 spec (prettier e tsc puliti) | **da fare**: V1-V6, cioè `tx-split-promote`, `tx-paired-edit`, `tx-event-picker` a 1 e a 4 worker | le sei verifiche |
  | A7, A7b, A7c | b-brokers | ✅ | ✅ | ✅ V1-V8 verdi, DB pulito | nessuno |
  | V-20 | b-v20 | evidenza nel gate della 2a e nel triage | ✅ applicata nei 3 spec (prettier e tsc puliti) | **da fare**: 7 giri, cioè una misura di `files "pdf preview"` e `auth`, `app-start-auth`, `files` a 1 e a 4 worker | i sette giri |
  | Commento di `fullyParallel` | io | — | ✅ `playwright.config.ts:42-45` | prettier pulito | il catalogo seriale di `:102`, dopo la 2b |

  **Da fare dopo le verifiche**:
  - allineare il catalogo seriale di `playwright.config.ts:102`. Ora è chiaro che `multi-user` resta seriale: l'elenco
    vero è `brokers/multi-user`, `files-destructive`, `fx-destructive`, `settings/scheduler` «Saving» e
    `tx-brim-import`;
  - nel backlog, V-20 ✅ e V-21, le sonde rimaste in `tx-import-resolution` e `tx-clone`;
  - i gate a 4 worker: `front-transaction all`, `front-broker all`, `front-user all`, `front-utility all`,
    `front-portfolio all`;
  - il checkpoint 2b.

  **Worktree**: 16 file sporchi. Sono i 14 spec della 2b, `frontend/playwright.config.ts` e questo piano. Il backlog
  non è sporco, perché V-16 è già committato.
- ▶️ **Riparti** (12/10, 19:24, coordinatore). Si riprende la 2b dal punto dello STOP. Stasera lo sviluppatore non c'è:
  le domande per lui le annota il coordinatore.
  > **Carico**: in parallelo, sulla corsia 6176, gira la run completa con coverage, quindi la macchina è carica. Le
  > verifiche di isolamento a 4 worker restano obbligatorie. Un rosso che sa di carico (timeout, attesa scaduta) si
  > rilancia da solo e a 1 worker prima di cercarne la causa, e il carico si registra qui.
- ✅ **Catalogo seriale di `playwright.config.ts`** (12/10). La riga «Currently: …» (`:102-103`) ora dice
  `brokers/multi-user, files-destructive, fx/fx-destructive, settings/scheduler («Saving»),
  transactions/tx-brim-import`: sono i cinque `configure({mode: 'serial'})` che esistono davvero sotto `frontend/e2e`,
  galleria compresa (grep). `asset-event-delete` non è più seriale: lo dice il suo stesso commento a `:96`.
  `multi-user` resta seriale, con la ragione verificata da b-brokers. Prettier pulito. Chiude il terzo punto di V-17.
- ✅ **A4, cura e verifica** (12/10). b-tx-commit; ha toccato solo i 4 spec (+158/−24).
  - Ogni test che committa avvia `trackTransactionWrites` dopo il login e lo pulisce in `afterEach`, che gira anche dopo
    un rosso. Ogni commit aspetta la risposta, così il tracker ha gli id prima della fine del test.
  - **`tx-wac-formmodal` FM6** apriva la prima coppia sullo schermo, che poteva essere di un vicino o del seed. Ora apre
    la coppia che ha creato: la rilegge per id, restringe la tabella con `id_min`/`id_max` e seleziona
    `dt-row-checkbox-tx-<id>`. Spariscono il ciclo `.nth()`, la classe `tx-row-receiver` e il confronto sul testo.
  - **`transactions-modals` T1** legge la risposta del commit; il rollback resta accettato.
  - **Verifiche** (`--fresh-run`; dopo ogni giro tutti gli id assegnati sono stati cancellati, e nessuna riga del seed
    toccata):

    | Spec | w1 | w4 |
    |---|---|---|
    | `tx-commit-all-types` | 19/19 | 19/19 |
    | `transactions-modals` | 19/19 | 19/19 |
    | `tx-wac-formmodal` | 10/10 | 10/10 |
    | `tx-wac-unit-toggle` | 4/4 | 4/4 |

  - V7 e V8 sono girati con il carico della coverage sulla 6176 (load average 20-27 su 10 core), senza rossi.
  - Prettier pulito; tsc offline exit 0.
  - Log: `/tmp/libreFolio_v_b_txcommit_v{1..8}_*.log`.
  > **⚠️ Fuori pista**, lasciati intatti e messi nel backlog (V-21):
  > - **T10** di `transactions-modals` non prova niente: il delete della toolbar ora apre il workspace bulk, quindi la
  >   sua sonda su `confirm-modal-confirm` risponde sempre falso. In più legge un contatore globale;
  > - **T1** non mostra mai un commit riuscito: sceglie Charles Schwab, senza cassa, e il BUY va in rollback. Cambiare
  >   il broker cambierebbe ciò che il test asserisce, quindi è una decisione;
  > - restano violazioni nel codice non toccato:
  >   - `.first()` senza filtro in T3/T9/T11 e sonde `isVisible().catch`;
  >   - classi CSS in `tx-wac-unit-toggle` e in FM10, che usa anche `.nth(count-1)`;
  >   - `.checkbox-btn` e `tr.row-deleted` in `tx-commit-all-types`, dove il test FX_CONVERSION accetta ancora
  >     «nessun commit»;
  > - un commento superato in `tx-commit-all-types` (`expectTransactionGone`) dice che gli id vengono riusati. Le
  >   transazioni usano `AUTOINCREMENT` dal piano 34.
- ✅ **A5 e A6, cura e verifica** (12/10). b-tx-seed; ha toccato solo i 3 spec.
  - **C3** (`tx-split-promote`) e **TODO-B** (`tx-paired-edit`): ciascuno registra un account usa-e-getta con due broker
    suoi. Via API finanzia il broker che manda e crea una coppia ETH collegata; ETH viene solo letto. Poi seleziona le
    due metà per id (`dt-row-checkbox-<id>`, `data-state=checked`). Il `afterEach` cancella l'account, e con lui i broker
    e le transazioni. Titoli invariati.
  - **C3**: in più asserisce che la divisione è proprio di questa coppia.
  - **TODO-B**: in più asserisce che ogni id aggiornato è della coppia e che il commit è accettato; aspetta la risposta,
    non la richiesta.
  - **A6** (`tx-event-picker`): l'evento va su un asset manuale creato dal test, non su Apple. Cancellarlo da Apple non
    sarebbe bastato: l'API degli eventi, senza id, aggiorna sul posto l'evento con la stessa data e lo stesso tipo, e
    avrebbe sovrascritto un dividendo del seed. Il default DIVIDEND si legge dall'icona 💰, non dalla parola tradotta.
    Il `afterEach` cancella l'asset.
  - **Verifiche** (`--fresh-run`):

    | Chiave | w1 | w4 |
    |---|---|---|
    | `tx-split-promote` | 6/6 | 6/6 |
    | `tx-paired-edit` | 4/4 | 4/4 |
    | `tx-event-picker` | 5/5 | 5/5 |

  - Il carico era alto per tutto il tempo (load average 16-55, la coverage sulla 6176), ma nessun rosso. Dopo ogni giro
    il DB era tornato al seed: 43↔44 e 45↔46 intatte, 76/11/8/11/17. I contatori di SQLite confermano che i dati del
    test sono stati creati e poi tolti.
  - Prettier e tsc puliti. Log: `/tmp/libreFolio_v_b_txseed_verify{1..6}_*.log`.
  > **⚠️ Fuori pista**, lasciati intatti:
  > - gli helper della coppia sono copiati in due spec, perché le fixture erano in sola lettura;
  > - sonde e classi CSS rimaste nei test non toccati (Bug 6, Bug 14, NR-1, Guard), e `pickAssetByName`, che se la sonda
  >   manca clicca il primo asset della lista;
  > - un commento sbagliato in `selectRow` («a paired row selects both halves»).
  >
  > Tutto nel backlog V-21.
  >
  > **Domanda sul prodotto**, letta nel codice e non osservata: «+ New event» potrebbe modificare in silenzio un evento
  > manuale con la stessa data e lo stesso tipo, pur dicendo di averne creato uno. Va al coordinatore come V-22.
- ✅ **V-20, cura e verifica** (12/10). b-v20; ha toccato solo `auth.spec.ts`, `layout/app-start-auth.spec.ts` e
  `files.spec.ts`. Ogni attesa di 3 s sulla prima navigazione è diventata un'attesa su uno stato pubblicato, con un
  limite esplicito:
  - **`auth.spec.ts`**:
    - `openLoginPage`: `login-page` visibile, 20 s, perché la pagina radice lo mostra solo dopo GET /auth/me;
    - `expectLandedOnDashboard`: il path `/dashboard` (15 s), poi `dashboard-page` (10 s). `login()` torna appena il
      form sparisce, mentre la radice è ancora su `/`; la vecchia regex accettava anche `/welcome?returnTo=%2Fdashboard`;
    - `expectLandedOnWelcome`, per gli account col benvenuto da fare;
    - `login-error` a 20 s;
    - timeout del file a 60 s, perché `login()` da solo può usare 10 + 10 + 20 s;
    - il test 5 ora aspetta l'atterraggio prima di controllare le assenze: prima passava senza provare niente.
  - **`app-start-auth.spec.ts:190`**: prima lo stato del layout (`app-auth-checking` o `server-unreachable`, 30 s), poi
    il poll sul gate con 10 s espliciti.
  - **`files.spec.ts:854`**:
    - `openStaticGridView` aspetta `files-page` con `data-busy=false`;
    - il test ha 60 s;
    - attese esplicite di 10 s sulla card d'errore e sulla chiusura;
    - la pulizia passa in un `afterEach`, che ha un suo slot di tempo. Nel giro pieno il file `914c9ec0` era rimasto,
      perché il timeout aveva tagliato il `finally`.
  - Prove (`--fresh-run`), con un carico alto (load average 41-56) e nessun rosso:

    | Comando | Esito |
    |---|---|
    | `--workers 4 files "pdf preview"` (misura) | 7/7 |
    | `auth` w1 / w4 | 29/29 e 29/29 (la chiave prende anche `app-start-auth`) |
    | `app-start-auth` w1 / w4 | 3/3 e 3/3 |
    | `files` w1 / w4 | 28/28 e 28/28 |

  - Prettier e tsc puliti. Log: `/tmp/libreFolio_v_b_v20_*.log`.
  > **Note implementazione**: a 4 worker `auth` non ha incontrato lo stallo del ripopolamento (V-17). Con V-16 i primi
  > login rispondono in circa 1 s. I limiti nuovi sono provati sotto carico alto, ma non contro uno stallo vero.
  > **⚠️ Fuori pista**, lasciati intatti e messi nel backlog (V-21):
  > - `logout()` della fixture usa ancora i 3 s di default;
  > - gli altri test di File Preview: i PDF puliscono ancora in `finally` con 30 s, mentre markdown, immagine,
  >   dettaglio, zoom e commenti non cancellano mai il loro upload;
  > - la vista dei file non pubblica il modo griglia/lista: i test usano la classe `active`. Servirebbe `aria-pressed`
  >   in `files/+page.svelte` (~`:704/707`);
  > - a 4 worker le anteprime aperte dalla griglia aspettano il loro fetch 5,8-10,9 s, quelle dalla lista 0-0,2 s. È
  >   plausibile una coda dietro le miniature, ma non è dimostrato.
- ✅ **Catalogo seriale e gate di categoria della 2b** (12/10, eseguiti da me, `--fresh-run --workers 4`, uno alla
  volta). Carico molto alto per la coverage sulla 6176: il load average registrato a inizio e fine di ogni gate è
  andato da 39 a 94, su 10 core.

  | Gate | E2E | Vitest | Load avg (1 min) inizio → fine |
  |---|---|---|---|
  | `front-transaction all` | 34 + **326/327** | 881/881 | 48,5 → 48,6 |
  | `front-broker all` | 2 + 51, verdi | 53/53 | 48,6 → 79,3 |
  | `front-user all` | 19/19 | 57/57 | 79,3 → 47,4 |
  | `front-utility all` | **89/90** + **224/226** | 7018/7018 | 47,4 → 72,2 |
  | `front-portfolio all` | 18 + 159, verdi | 1218/1218 | 72,2 → 94,0 |

  Log: `/tmp/libreFolio_v_2b_gate_<categoria>.log`, riepilogo in `/tmp/libreFolio_v_2b_gates_summary.log`.
  > **⚠️ Fuori pista: i 4 rossi.** Nessuno sta in un file toccato dalla 2b.
  > - **`toolbar-width-sweep` `es`, dashboard e assetDetail**: è V-19, già noto e deterministico, assegnato a I.
  > - **`onboarding-guides.spec.ts:297` T11 [mobile]**: attesa scaduta (15 s) in `completeWelcome`
  >   (`fixtures/onboarding-accounts.ts:97`), con la pagina ancora su `/welcome?returnTo=…`. Rilanciato da solo a 1
  >   worker (`--workers 1 front-utility onboarding-guides "T11 broker_page_guide"`, load 54,7 → 46,7): **2/2 verdi**,
  >   desktop e mobile. Verdetto: **carico**.
  > - **`tx-wac-bulk.spec.ts:415` WB5**: la cella WAC «auto» resta `empty` per 20 s invece di `ready`. Rilanciato da
  >   solo a 1 worker (`--workers 1 front-transaction tx-wac-bulk "WB5"`, load 86,9 → 54,7): **di nuovo rosso**, 25,3 s.
  >   Non è il carico, e non è la 2b: il giro è su una sola chiave con il seed fresco, e `tx-wac-bulk` non è toccato.
  >   Il test prende per posizione la prima coppia «giver/receiver» del seed su IB o Directa. Le coppie più recenti
  >   del seed sono le due ETH Coinbase→IB di ieri (`delete-safe`, `delete-consume`), poi AAPL IB→Hidden Admin Broker
  >   (Asym-d, ricevente nascosto). Triage in corso, solo diagnosi (test-author `b-wb5`).
  >
  > Log dei rilanci: `/tmp/libreFolio_v_2b_rerun_{wb5,t11}.log`.
- ✅ **WB5, triage** (12/10). Test-author `b-wb5`; diagnostica temporanea poi tolta, file identico a HEAD. Verdetto:
  **assunzione**. Non è un difetto del prodotto.
  - **La riga scelta**: WB5 prende per posizione `tx-41` → `tx-42`, cioè MSFT IB −2 → DEGIRO +2, seed «Asym-c,
    OWNER↔VIEWER=view-only». Salta prima le coppie ETH, perché la riga che manda è su Coinbase, e la Asym-d, il cui
    ricevente sul broker nascosto non arriva all'utente.
  - **La risposta di validate**: `accessDenied` («EDITOR required for broker 2»), `wac_results: null`. Su DEGIRO
    `e2e_test_user` è solo VIEWER, e `compute_wac_and_fx_issues` (`transaction_batch_stages.py:833`) non propone costi
    per un batch con errori. Quindi `empty` è giusto, e il banner lo spiega.
  - **Perché passava**: dal 14/08 (`9a254f812`) WB5 esige `ready`. Da allora passava solo clonando una coppia lasciata
    da altri test: per esempio quella IB→Directa che WB4, prima di lui nello stesso file, committa e non cancella.
    Oppure gli avanzi di `tx-commit-all-types`, che la cura di A4 ora pulisce.
  - **Esiti per modalità**: da solo fallisce sempre; nel gate a 4 worker parte insieme a WB4 e fallisce; in sequenza
    passava. **La pulizia della 2b l'ha smascherato**, quindi la cura entra nella 2b.
  - **Cura in corso** (`b-wb5`, solo `tx-wac-bulk.spec.ts`):
    - WB5 costruisce la sua coppia: broker e asset propri via API, come WB11; due ADJUSTMENT +10 a 100 e 200 EUR; un
      TRANSFER collegato −4/+4 a una data fissa vecchia;
    - la clona per id, e asserisce il valore esatto atteso, 150 EUR per unità;
    - WB4 cancella ciò che committa.
  - Log: `/tmp/libreFolio_v_wb5_diag1.log`.
  > **⚠️ Fuori pista**, osservazioni sul prodotto da `b-wb5`, non curate:
  > - nel bulk editor il ricevente DEGIRO compare come «To: —», perché `renderBrokerHtml` cerca il broker solo nella
  >   lista del modale;
  > - l'errore d'accesso compare sulla riga 1a, anche se riguarda il broker 2;
  > - `frontend/test-results` e `.testLog` sono condivisi per worktree, non per corsia: un giro successivo ha cancellato
  >   l'`error-context.md` di WB5.
- ✅ **WB4 e WB5, cura e verifica** (12/10). `b-wb5`; ha toccato solo `tx-wac-bulk.spec.ts` (+195/−97, quasi tutto WB4
  reindentato).
  - **WB5**:
    - crea via API due broker e un asset EUR propri. Su A salva due ADJUSTMENT +10 a 100 e 200 EUR, poi un TRANSFER
      collegato A −4 → B +4 del 2024-01-04. Il ricevente ha un costo manuale di 175, così il 150 della copia è per
      forza calcolato e non copiato;
    - rilegge lotti, collegamento e costo, apre la tabella sugli id della coppia e verifica per id che la riga che
      manda stia sopra a quella che riceve;
    - clona per id e chiama `waitForWacResolved`;
    - asserisce `ready` e le cifre `15000`, cioè 150,00 EUR per unità;
    - `cleanupOwned` gira in `finally`.
  - **WB4**: gira nello stesso involucro di pulizia. `commitBulkModal` registra gli id appena arriva la risposta del
    commit, e li cancella in `finally`.
  - **Prove**, file intero, `--fresh-run`:
    - 1 worker: 11/11, load 32,5 → 28,0;
    - 4 worker: 11/11, load 24,8 → 36,4.
  - Dopo ogni giro il DB è tornato al seed; i contatori confermano che i dati del file sono stati creati e tolti.
  - Prettier e tsc puliti. Log: `/tmp/libreFolio_v_wb5_cure_w{1,4}.log`.
- ✅ **Gate `front-transaction all` rifatto dopo WB5** (12/10, `--fresh-run --workers 4`, load 37,2 → 40,9): E2E 34 (32
  skippati) + **327/327**, Vitest 881/881 (`/tmp/libreFolio_v_2b_gate_front-transaction_v2.log`).
- **Esito dei gate della 2b**:
  - verdi: `front-transaction`, `front-broker`, `front-user` e `front-portfolio`;
  - `front-utility`: verde a parte V-19 (`es`, deterministico, assegnato a I) e T11 [mobile], che è carico e da solo
    a 1 worker è verde;
  - il gate di utility è girato con le cure di V-20 già nella worktree: `auth`, `app-start-auth` e `files` sono verdi
    anche nel giro consolidato.

> Checkpoint 2b committato dal coordinatore: 7 commit da `1b1e58fd0` a `3d7635efb`. Poi il ramo è stato portato sul
> target `b1c8f22df`: ora sono a **`bb2519108`**, pulito (12/10). La base nuova contiene il CP1 di M-18 (numeri nella
> lingua della UI) e i treni 65-70. Decisioni del coordinatore:
> - V-22 va nelle domande per lo sviluppatore, e non lo tocco;
> - V-21 e V-23 restano dopo la 1.2; il T1 di V-21 lo decide lo sviluppatore.

### 12.9 Convalida della revisione combinata e lacune 1.2

- **Convalida** (in corso, 12/10): i 15 spec toccati dalla 2b, `--fresh-run --workers 4`, una chiave alla volta. Dopo
  ogni giro il DB si confronta col seed della base nuova, fotografato da un giro innocuo
  (`/tmp/libreFolio_v_combo_dbcheck.py`; riepilogo in `/tmp/libreFolio_v_combo_summary.log`). Un rosso si triagia
  prima di toccare qualunque cosa.
- **Lacune**, nell'ordine 2, 1, 6, 4, 7, 5, 3, con un checkpoint ogni due o tre. I test-author scrivono in parallelo,
  la corsia si dà a turno:
  - lacuna 2: `g2-fx-on-cash`. Un Vitest della riga «FX on cash» (`OtherPeriodEffectsTable.test.ts`); un E2E su dati
    veri con cassa in una valuta riservata e tassi MANUAL, con oracolo; la cassa d'intestazione uguale alla somma
    delle card;
  - lacuna 1: `g1-risk-real`. Un E2E con il `/risk/query` vero fino allo schermo, L1 (VaR, CVaR) e una cifra L4, con
    la risposta validata dallo schema Zod generato.
- ✅ **Convalida della revisione combinata** (12/10, 21:18-21:50, `bb2519108`). 15 spec su 14 chiavi, `--fresh-run
  --workers 4`, una alla volta. Load average da 23 a 178 su 10 core, per la coverage sulla 6176.
  - **Esito**: tutto verde.
    - Transazioni: `tx-commit-all-types` 19, `transactions-modals` 19, `tx-wac-formmodal` 10, `tx-wac-unit-toggle` 4,
      `tx-split-promote` 6, `tx-paired-edit` 4, `tx-event-picker` 5, `tx-import-resolution` 15, `tx-clone` 8,
      `tx-wac-bulk` 11.
    - Broker e utenti: `list` 9, `multi-user` 2.
    - Utility: `auth` 29, `app-start-auth` 3, `files` 28.
  - **DB**: dopo 13 chiavi su 14 è identico al seed della base nuova (11 utenti, 8 broker, 30 accessi, 76 transazioni,
    17 asset, 11 eventi, 24 rotte, 4125 tassi, scheduler e `e2e_test_user` invariati).
  > **⚠️ Fuori pista: `files` lascia avanzi** (triage letto dal DB, in sola lettura). Restano un broker, «Preview Broker
  > <ts>» con OWNER `e2e_test_user`, e 6 upload statici (12 file con i metadati). Non vengono dalla 2b:
  > - `files.spec.ts:886`, «opens table preview for BRIM files», crea il broker e un file BRIM e non li cancella mai.
  >   È la classe A7, che nell'audit avevo messo per errore in B;
  > - gli upload sono dei test di File Preview che non cancellano mai, già notati in V-21.
  >
  > Ho proposto al coordinatore di curarli nel checkpoint delle lacune 2 e 1, con un commit a parte.
- **Lacuna 2**: `g2-fx-on-cash` ha scritto `OtherPeriodEffectsTable.test.ts` (Vitest 4/4) e
  `frontend/e2e/portfolio/foreign-cash-real.spec.ts`.
  - Valute riservate: NAD su desktop, MZN su mobile.
  - Oracolo esatto: FX on cash = 1000 × (1/1,6 − 1/1,25) = **−175 EUR**; cassa 1310 → 1135 fra due giorni consecutivi,
    uguale alla somma delle card.
  - Registrazioni: `add_test("foreign-cash-real")` in `_frontend_portfolio.py`, e una riga del Vitest nell'elenco
    `front_component_unit` di `_frontend_utility.py`, che ora è di T. Ho chiesto al coordinatore.
  - In corsia dalle 21:5x.
- **Lacuna 1**: `g1-risk-real` ha scritto `frontend/e2e/portfolio/risk-real.spec.ts`, con due test su account
  usa-e-getta che hanno Apple e Microsoft del seed:
  - R1, L1: VaR giornaliero, CVaR giornaliero e mensile, bin e osservazioni;
  - R2, L4: il replay reale, il totale e le righe per asset;
  - ogni risposta `/risk/*` è validata dallo schema Zod.

  È registrato in `_frontend_portfolio.py`, e aspetta la corsia.
- **Decisioni del coordinatore sulla convalida** (12/10). La 2b entra nel treno 72 (`bb2519108`) insieme al lotto 48
  di I.
  - Gli avanzi di `files` si curano nel checkpoint delle lacune 2 e 1, con un commit a parte. L'agente è
    `b-files-leak`. Il broker e il file BRIM di `:886` vanno in `try/finally` con `deleteOwnedBrokerAndFiles`; gli
    upload della File Preview, in `ownedStaticFiles`.
  - **Classe di `:886`, corretta**: è A, non B. Crea un broker permanente di `TEST_USER` e non ha nessuna pulizia.
  - `_frontend_utility.py` è di **I** dal treno 70, non di T. La riga del Vitest in `front_component_unit` resta nel
    mio commit, perché è un'aggiunta. Se al merge si scontra con le righe di I, si tengono tutte e due.
- In scrittura: le lacune 6 (`g6-account-delete`) e 4 (`g4-yoc`). Ordine della corsia: g2, g1, `files`, g6, g4.
- ✅ **Lacuna 2, verificata** (12/10). `g2-fx-on-cash`.
  - **Vitest** `OtherPeriodEffectsTable.test.ts`, 4/4. Controlla l'etichetta dalla chiave `dashboard.fxOnCash`, letta in
    una lingua finta `⟦key⟧`; il segno (+, −, niente sullo zero, «—» quando manca); la valuta passata; l'ordine e le
    chiavi; la cella del P&L.
  - **E2E** `portfolio/foreign-cash-real.spec.ts`, su un account usa-e-getta e con tassi MANUAL, valute riservate NAD
    e MZN:
    - `other_effects` è uguale alle righe attese: FX on cash **−175 EUR**, cioè 1000 × (0,625 − 0,8); prima viene il
      reddito, e non c'è residuo;
    - in una finestra in cui il tasso non si muove, la riga FX non c'è;
    - due report a un giorno di distanza danno 1310 → 1135 di cassa e +10 → −165 di guadagno, ogni volta uguali alla
      somma delle card (`summary.by_broker`), con i saldi nativi invariati;
    - sullo schermo, net worth `113500` e la riga FX `17500` col meno.
  - **Prove**:

    | Comando | Esito | Load |
    |---|---|---|
    | E2E `--fresh-run --workers 1` | 1/1 | 47 → 38 |
    | E2E `--fresh-run --workers 4` | 1/1 | 33 → 22 |
    | `check-orphans` | pulito (112 spec, 353 unit) | — |

  - Nessun avanzo. svelte-check 0 errori; prettier e tsc puliti.
  - Registrazioni: `foreign-cash-real` in `_frontend_portfolio.py`; il Vitest in `front_component_unit` di
    `_frontend_utility.py`, file di I, riga aggiunta e tenuta d'accordo col coordinatore.
  > **Note implementazione**: le card dei broker e la barra della cassa nel KPI non hanno testid. Le card si leggono da
  > `summary.by_broker`; su un account di sola cassa il net worth è uguale alla cassa. L'attributo possibile è
  > `broker-card-nav-{id}` in `BrokerCard.svelte`: per ora è solo una nota.
- ✅ **Lacuna 1, verificata** (12/10). `g1-risk-real`, `frontend/e2e/portfolio/risk-real.spec.ts`. Due test paralleli,
  ognuno su un account suo con un broker, un deposito USD e 10 Apple e 10 Microsoft del seed, comprati 200 giorni fa al
  prezzo del seed. Prima il test verifica che i prezzi bastino: almeno 60 giorni e un prezzo recente. **Nessun
  `page.route`.**
  - **R1, L1**: CVaR giornaliero e mensile, VaR giornaliero, bin e osservazioni a schermo, uguali al `/risk/query`
    vero. Nessuno stato d'errore o vuoto, e le quattro analitiche L1 sono `ok`. Valori visti: VaR 2,01%, CVaR 2,40% e
    11,57%.
  - **R2, L4**: il replay storico vero. Il totale (−5,00%) e il rendimento e il contributo per asset coincidono con il
    backend.
  - Ogni risposta `/risk/*` passa lo schema Zod generato.
  - Si confronta l'ultima risposta di ogni tipo, a pannello assestato; le cifre per segno e numero, entro mezza unità
    dell'ultima cifra mostrata.
  - **Prove**:

    | Comando | Esito | Load |
    |---|---|---|
    | `--fresh-run --workers 1` | 2/2 | 16,9 → 24,5 |
    | `--fresh-run --workers 4` | 2/2 | 25,3 → 32,4 |
    | `check-orphans` | pulito | — |

  - Nessun avanzo; prettier e tsc puliti. Registrato in `_frontend_portfolio.py` (`risk-real`).
  > **⚠️ Fuori pista**, osservazioni sul prodotto, non bloccanti:
  > - L1 non mostra mai il VaR come cifra a sé. Le card mostrano il CVaR, e il VaR giornaliero compare solo nella frase
  >   dell'istogramma; quello mensile mai. Il `secondaryLoss` calcolato da `buildHurtRows` non viene reso. Sembra
  >   voluto;
  > - `risk-replay-total` è una frase tradotta che contiene percentuale e importo. Il test prende la percentuale dal
  >   `%`, ma per una lettura rigorosa servirebbe un elemento a parte.
- ✅ **Gate `front-portfolio all` con i due spec nuovi** (12/10, `--fresh-run --workers 4`, load 22,1 → 45,3): E2E 18 +
  **162/162**, Vitest 1221/1221 (`/tmp/libreFolio_v_cpA_gate_front-portfolio_all.log`). In corso
  `front-utility component-unit`, dove è registrato il Vitest nuovo.
- ✅ **Attributi per la lacuna 6** (12/10, aggiunti da me, solo attributi). In
  `frontend/src/lib/components/settings/tabs/ProfileTab.svelte`, nel dialogo di cancellazione dell'account:
  `data-testid="profile-delete-confirm-input"` sul campo dello username, `profile-delete-confirm` sul pulsante di
  conferma e `profile-delete-cancel` su Annulla. Il dialogo chiede lo username, non la password. Prettier pulito,
  Vitest `ProfileTab.test.ts` 51/51.
- **Pronti per la corsia**:
  - `b-files-leak`. `ownedStaticFiles` sale a «Files Page», e ci si iscrive anche «can upload a file to static
    storage», sesto upload perso. Il broker BRIM di `:886` si cancella in un `afterEach`, che ha un suo slot di tempo:
    un `finally` sarebbe tagliato dal timeout. `createBroker` usa `uniqueSuffix()`;
  - `g4-yoc` (`yield-on-cost-real.spec.ts`):
    - Y1: un asset su due broker, con YOC 3,00% e 1,20% per (asset, broker), contro 2,10% se fosse per asset;
    - Y2: il percorso P-10 dà «—» con l'icona, poi, dopo un costo esplicito di 0, 4,00%;
  - `g6-account-delete` (`brokers/account-deletion.spec.ts`), registrato in `_frontend_user.py`.
- ✅ **Gate `front-utility component-unit`** (12/10, load 45,3 → 99,8): 115 file, **3010/3010**, con il Vitest nuovo della
  lacuna 2 (`/tmp/libreFolio_v_cpA_gate_front-utility_component-unit.log`).
- ✅ **Avanzi di `files.spec.ts`, cura** (12/10). `b-files-leak`; ha toccato solo lo spec.
  - `ownedStaticFiles` e il suo `afterEach` salgono a «Files Page».
  - Il sesto upload perso era di «can upload a file to static storage»: ora legge la risposta del suo `POST /uploads`
    e iscrive il file.
  - I test di anteprima di markdown, immagine, dettaglio, zoom, commento, host, fallback, modifica, menu e comandi
    iscrivono il loro file. Il `finally` usato solo per cancellare è tolto.
  - Il broker e il file BRIM di `:886` si cancellano in un `afterEach` di «File Preview» con
    `deleteOwnedBrokerAndFiles`: un `finally` sarebbe tagliato dal timeout, e la sua `expect` coprirebbe il rosso del
    test.
  - `createBroker` usa `uniqueSuffix()`.
  - **Prove**:

    | Giro | Esito | Load |
    |---|---|---|
    | `--fresh-run --workers 1` | 28/28 | 72,3 → 34,0 |
    | `--fresh-run --workers 4` | **24/28** | 32,6 → 52,1 |
    | i 4 rossi da soli, a 1 worker | 4/4 | 42,4 → 54,8 |

  - Dopo i tre giri il DB è al seed (11/8/30/76/17), `custom-uploads` resta a 137 e nessun upload della run è rimasto;
    `broker_reports` resta a 16 file di dati.
  - Prettier e tsc puliti.
  > **⚠️ Fuori pista: i 4 rossi a 4 worker sono carico.** Sono le prime quattro anteprime aperte dalla griglia
  > (immagine, immagine con zoom, commento PDF, host PDF), ferme con `file-preview-shell` `data-busy="true"` fino ai 30
  > s. Cadono prima di qualunque riga cambiata. Erano già le più lente nel giro verde sulla base (11-17 s), e tutto
  > girava circa due volte più piano. Il meccanismo probabile, non dimostrato, è la coda delle miniature nel thread
  > pool del backend. Rilancio `files` a 4 worker con meno carico prima del checkpoint. `custom-uploads` parte da 137
  > e non da 125 perché i 6 upload persi dal giro di convalida delle 21:49 restano: il populate non pulisce quella
  > cartella.
- ✅ **Lacuna 4, verificata** (12/10). `g4-yoc`, `frontend/e2e/portfolio/yield-on-cost-real.spec.ts`, registrato come
  `yield-on-cost-real`. Due test su account usa-e-getta, niente route né mock.
  - **Y1**: un asset manuale su due broker, con dividendi di 100 giorni fa, fuori dal periodo ma dentro la finestra YOC.
    - API: un valore per (asset, broker), esatto: 30/10 ÷ 100 = **3,00%** e 12/8 ÷ 125 = **1,20%**, contro 2,10% se
      fosse per asset;
    - finestra, `first_pair_transaction_date`, redditi e base di costo coerenti;
    - lo schermo mostra le cifre `300` e `120`, sulla Dashboard e sulla pagina del broker B.
  - **Y2**: il percorso P-10, con un costo ignoto e un dividendo di 40.
    - API: `unavailable`/`missing_wac` con il reddito contato;
    - la cella mostra il trattino `-` con l'icona, senza cifre;
    - dopo un costo esplicito di 0, WAC 50 e **4,00%**.
  - **Prove**:

    | Comando | Esito | Load |
    |---|---|---|
    | `--fresh-run --workers 1` | 2/2 | 25,1 → 25,4 |
    | `--fresh-run --workers 4` | 2/2 | 25,4 → 36,3 |
    | `check-orphans` | il suo spec registrato; l'unico orfano era lo spec di g7, non ancora registrato | — |

  - Nessun avanzo; prettier e tsc puliti.
  > **Note implementazione**: il YOC usa il trattino `-`, mentre le altre celle vuote usano `—`. Doc e Vitest dicono
  > così, quindi è voluto, e lo spec asserisce il trattino. Y2 verifica in apertura che il percorso del costo ignoto
  > sia ancora aperto, come V-4 per E2.
- **Lacuna 7**: `g7-pdf-offline` ha scritto `frontend/e2e/files-pdf-offline.spec.ts`.
  - Ogni richiesta fuori origine è abortita e registrata.
  - Il PDF latino è costruito nel test.
  - Asserisce `file-preview-pdf` `data-state="ready"` e zero richieste esterne; un GET del motore pdfium e il rifiuto
    di jsDelivr confermano che il log vede le richieste.
  - È registrato in `_frontend_utility.py`, file di I, con righe aggiunte. Aspetta la corsia dopo g6.
- ✅ **Lacuna 6, verificata** (12/10). `g6-account-delete`, `frontend/e2e/brokers/account-deletion.spec.ts` (categoria
  `front-user`, registrato in `_frontend_user.py`).
  - **Setup via API**: utenti A e B usa-e-getta, non admin. Il broker X ha A come unico owner e B come viewer, con un
    deposito e un report. Il broker Y ha A e B come owner, con un deposito.
  - **Prima della cancellazione**: accessi e letture verificati come B.
  - **La cancellazione**: A entra dalla UI e cancella l'account dal dialogo vero, con gli attributi aggiunti. Il
    pulsante resta disabilitato finché lo username non è esatto, e `DELETE /auth/users/me` risponde 200.
  - **Dopo**:
    - A è uscito: `/` e `login-page`; `/auth/me` risponde 401, anche alla vecchia sessione API, e un nuovo login fallisce;
    - come B: X, i suoi accessi e il suo report rispondono 404, e X sparisce dall'elenco;
    - Y resta, con B unico owner e nessuna riga di A, e resta leggibile solo il deposito di Y.
  - **Prove**:

    | Comando | Esito | Load |
    |---|---|---|
    | `--fresh-run --workers 1` | 1/1 | 32,5 |
    | `--fresh-run --workers 4` | 1/1 | 34,1 |
    | `check-orphans` | pulito: 115 spec, 353 unit, 260 backend | — |

  - Nessun avanzo. Gli id non si riusano, quindi il 404 di X non può essere un broker più nuovo di qualcun altro.
  - Prettier e tsc puliti.
- ✅ **Lacuna 7, verificata** (12/10). `g7-pdf-offline`, `frontend/e2e/files-pdf-offline.spec.ts`, registrato come
  `front-utility files-pdf-offline` in `_frontend_utility.py` (di I, 20 righe aggiunte).
  - Prima della prima navigazione ogni richiesta del contesto viene registrata, e ogni richiesta fuori origine è
    rifiutata (`internetdisconnected`), non finta.
  - Un PDF latino di una pagina, costruito nel test, raggiunge `file-preview-pdf[data-state=ready]`.
  - **Zero richieste ad altre origini**: 144 richieste, tutte a `localhost:6175`.
  - Il GET di `pdfium.<hash>.wasm` con 200 dal worker del motore dimostra che il log vede anche il worker; il rifiuto
    di una sonda jsDelivr è registrato.
  - Login via API, dopo aver verificato che `TEST_USER` non sia admin: un admin controllerebbe gli aggiornamenti su
    GitHub.
  - **Prove**:

    | Comando | Esito | Load |
    |---|---|---|
    | `--fresh-run --workers 1` | 1/1 | 26,0 → 22,8 |
    | `--fresh-run --workers 4` | 1/1 | 15,8 → 13,7 |
    | `check-orphans` | pulito, 115 spec | — |

  - Nessun avanzo; prettier, tsc, black e ruff puliti.
  > **Note implementazione**:
  > - un PDF latino non chiede font di ripiego (PDFium usa i suoi), quindi «font serviti in locale» resta coperto solo
  >   da `pdfViewerAssets.test.ts`;
  > - il controllo «requests nothing from third-party hosts» di `files.spec.ts` accetta qualsiasi richiesta `.wasm`,
  >   anche solo la HEAD del thread principale. È solo una nota.
- In scrittura: le lacune 5 (`g5-auto-transfer`) e 3 (`g3-pac`). Per il checkpoint rifaccio `files` a 4 worker e i gate
  di `front-portfolio`, `front-user` e `front-utility`, con il carico ora basso (load 13-14).
- ✅ **Gate del checkpoint delle lacune** (12/10, `--fresh-run --workers 4`, una chiave alla volta):

  | Gate | Esito | Load |
  |---|---|---|
  | `front-utility files` (rifatto con poco carico) | **28/28** | 12,8 → 23,0 |
  | `front-portfolio all` | 18 + **164/164**, Vitest 1221 | 23,0 → 33,1 |
  | `front-user all` | **20/20**, Vitest 57 | 31,8 → 50,3 |
  | `front-utility all` | 90/90 + **227/229**, Vitest 7231 | 50,3 → 102,3 |

  - I due rossi di `front-utility all` sono gli `es` di `toolbar-width-sweep`: V-19, deterministici, di I.
  - `files-pdf-offline` è verde nel giro consolidato.
  - Dopo ogni gate il DB è al seed. Il confronto segna solo `uploads` 125 → 137: sono i 12 file persi nel giro di
    convalida delle 21:49, che il populate non toglie, e nessun giro nuovo ha lasciato upload.
  - Log: `/tmp/libreFolio_v_cpA2_*.log`.
  > **Note implementazione**: niente checkpoint parziale. `_frontend_utility.py` contiene le righe delle lacune 2, 7 e
  > 3, e `_frontend_portfolio.py` quelle di 2, 1 e 4: un checkpoint senza la 3 porterebbe una registrazione verso uno
  > spec non verificato. Faccio un checkpoint unico con le 7 lacune appena 5 e 3 sono verificate, e l'ho detto al
  > coordinatore.
- **Lacune 5 e 3**, scritte:
  - `g5-auto-transfer`, `tx-transfer-auto-cost.spec.ts`. T1 trasferisce l'intera posizione in Auto, e B deve avere WAC
    150 e guadagno 600, non 3600. T2 è parziale, 8 unità: B ha 8 @ 150 e A ne tiene 12 @ 150;
  - `g3-pac`, `pac-allocator-real.spec.ts`, spec di radice in `front-utility`. Asserisce lo stato `ready_incumbent`.

  Verifiche in corsia, una alla volta.
- ✅ **Lacuna 5, verificata** (12/10). `g5-auto-transfer`, `frontend/e2e/transactions/tx-transfer-auto-cost.spec.ts`,
  registrato come `tx-transfer-auto-cost` in `_frontend_transaction.py`. Due test, ognuno su un account usa-e-getta,
  con i broker A e B, un asset EUR manuale e gli acquisti di A fatti via API.
  - Il trasferimento passa dalla UI: «+», poi il form TRANSFER, con il costo lasciato in Auto, poi Save
    nell'editor.
  - Si controllano:
    - il form propone 150;
    - la cella dell'editor è `ready` a 150;
    - il salvataggio manda il ricevente come `auto`, e il server risponde che ha usato la media di A, 150 EUR;
    - le righe salvate sono collegate, e il ricevente ha 150 per unità;
    - il report e la tabella, con `pmc` acceso dal menu delle colonne.
  - **Oracolo**: A compra 10 @ 100 e 10 @ 200, quindi WAC 150, con ultimo prezzo 180.
    - **T1**, trasferimento di tutta la posizione: B ha 20 / 150 / 3600 / guadagno **600**; nella 1.1 il costo era 0 e
      il guadagno 3600. A non ha più la posizione.
    - **T2**, trasferimento parziale di 8: B ha 8 / 150 / 1440 / 240; A tiene 12 / 150 / 2160 / 360.
  - **Prove**:

    | Comando | Esito | Load |
    |---|---|---|
    | `--fresh-run --workers 1` | 2/2 | 71,8 |
    | `--fresh-run --workers 4` | 2/2 | 32,0 |
    | `check-orphans` | pulito, 117 spec | 24,8 |

  - Nessun avanzo: controllati il DB vivo e lo snapshot di fine giro 1. Prettier e tsc puliti.
  > **⚠️ Fuori pista**, osservazione sul prodotto letta nel codice, non vista a schermo, nel backlog come V-24. Appena il
  > form è applicato, la cella del costo nell'editor può mostrare per un attimo «💡 0.00» come `ready`. Il form passa 0
  > come segnaposto in Auto, e la cella tratta qualsiasi importo come una proposta pronta. Si corregge quando arriva la
  > validazione, che dà 150. Per un istante l'utente vede il sintomo della 1.1, e `ready` non vuol dire «calcolato».
- ✅ **Lacuna 3, verificata** (12/10). `g3-pac`, `frontend/e2e/pac-allocator-real.spec.ts`, registrato come
  `front-utility pac-allocator-real` in `_frontend_utility.py` (di I, 21 righe aggiunte).
  - **Setup**: un account usa-e-getta con 5000 EUR e due posizioni manuali, 20 @ 90 e 30 @ 40. Il codice del tool viene
    da `GET /tools/catalog`; il planner si apre dalla sua card.
  - **«Copia da LibreFolio»**: la liquidità del broker, i due asset con i prezzi salvati, la distribuzione attuale 60/40.
  - **Il calcolo**: budget 1000, poi «Calculate plan». Il motore vero gira, e il test cattura il suo `POST
    /tools/compute`.
  - **Le verifiche**: la richiesta porta id, prezzi, cassa, pesi e il codice del tool. La risposta è `ready_incumbent`,
    con prova `optimal_proven`. A schermo coincidono stato, prova, valori per asset, piè di tabella e ordini (debito e
    commissione), e il totale investito non supera il budget.
  - **Prove**:

    | Comando | Esito | Load |
    |---|---|---|
    | `--fresh-run --workers 1` | 1/1 | 22,8 |
    | `--fresh-run --workers 4` | 1/1 | 14,3 |
    | `check-orphans` | pulito, 117 spec e 353 unit | — |

  - Nessun avanzo; prettier, tsc, ruff e black puliti.
  > **Note implementazione** (UI beta):
  > - lo stato di successo pubblicato è `ready_incumbent`, non `ok`;
  > - valore finale, valore ideale, importo e commissione non hanno un testid proprio, e si leggono dagli attributi
  >   del data table;
  > - il selettore di valuta non pubblica il valore scelto;
  > - la data del planner è la minore fra quella locale e quella UTC, quindi lo spec salva i prezzi solo fino a ieri.
- **Gate finale `front-transaction all`**: in corso.
- ✅ **Gate finale `front-transaction all`** (12/10, `--fresh-run --workers 4`, load 21,4 → 38,2): 34 (32 skippati) +
  **329/329**, Vitest 881 (`/tmp/libreFolio_v_cpA2_transaction-all.log`). Contiene la lacuna 5.
  > **⚠️ Fuori pista: il DB, dopo il giro consolidato delle transazioni, non torna al seed.** Ci sono un broker, un
  > accesso e un asset in più, e 3 transazioni in meno. Triage letto dal DB e da uno snapshot archiviato del seed:
  > - la 28 è la FEE `[delete-safe] Platform fee for delete test`: la cancella `tx-delete` «A1-confirm» (`:181-183`),
  >   per costruzione;
  > - 45 e 46 sono la coppia `delete-consume`: la consuma «A2-confirm», per costruzione e già nelle note C;
  > - il broker `T4-delref-<suffix>` (OWNER `e2e_test_user`) e l'asset `T4-delref-asset-<suffix>` sono lasciati di
  >   proposito da «A1-error» (`:390-393`, «inert reference data»).
  >
  > È tutto vecchio e documentato, non viene dalle lacune. È nel backlog come V-25: un broker permanente di `TEST_USER`
  > è della classe A7.
- ✅ **Controlli statici del checkpoint** (12/10):
  - prettier pulito su tutti i file frontend nuovi e cambiati;
  - svelte-check 0 errori e 0 warning;
  - ruff: 41 segnalazioni sui quattro file del runner sia a HEAD sia ora, quindi nessuna nuova;
  - `git diff --check` pulito;
  - `check-orphans` pulito, con 117 spec, nell'ultimo giro di g3.
