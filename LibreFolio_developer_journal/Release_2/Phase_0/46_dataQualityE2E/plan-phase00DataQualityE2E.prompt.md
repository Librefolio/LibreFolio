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
