# Rosso della run completa (treno 14): `data-quality-banners.spec.ts:387`, un link in più

> Lotto di N, 08/10. Coordinator: c8328a01. Base `9eb01c756`, worktree pulito. Corsia 6159/6169, `/tmp/librefolio-r2-n`.
> Collegato al piano dell'FX nella Dashboard (`plan-phase00FxDashboardSync.prompt.md`), dove sono nati
> `serveMissingFxRates` e i test del banner per `MISSING_FX_RATES`.

## 1. Il rosso

- **Il test**: «missing price issue renders one navigate link per affected asset» (`:387`), in desktop.
- **L'errore**: `expect(locator('[data-testid^="data-quality-nav-asset-"]')).toHaveCount(2)` → **Received: 3** (`:410`).
- **Dove**: run completa con coverage sul treno 14 (`9eb01c756`), corsia 6150.

## 2. Analisi (`test-triage`)

- **§1, la forma della risposta.** Il test inietta un `MISSING_PRICE` con due asset (901234 e 901235) e lo
  **aggiunge** alle anomalie vere del report (`injectDashboardIssues`, `:100-112`). Poi conta i link
  `data-quality-nav-asset-*` di **tutta la pagina**.
- **Riprodotto in corsia, a DB appena popolato, senza altri spec: rosso deterministico, 3 contro 2**
  (`/tmp/libreFolio_n_dq_baseline.log`). Lo snapshot della pagina mostra:
  - la riga `MISSING_PRICE` iniettata, con i suoi **due** link;
  - una riga **vera** `MISSING_COST_BASIS`, «1 asset(s) have an acquisition without a purchase cost», con il suo
    link a **Ethereum**.
- **L'origine del terzo link.** Dal commit `de252a38a` (#32, «single average cost», 07/10 16:33) il motore segnala
  `MISSING_COST_BASIS` con `cta_action="navigate_asset"` (`portfolio_engine.py:2073-2088`), per ogni asset con
  un movimento di costo ignoto (`portfolio_service._missing_cost_basis_assets`, `:561-567`). Il seed contiene la
  ricompensa di staking ETH: `INTEREST`, quantità 0,002, senza costo (`populate_mock_data.py:1430-1438`).
  - La run del 07/10 (`d07412899`) era precedente al #32: per questo era verde.
  - Il movimento esatto lo conferma P, se la segnalazione in sé è in discussione: non è materia di questo lotto.
- **Il rischio gemello, stessa causa (`:101`).** Il banner raggruppato ha come chiave delle righe
  `code + group_key` (`DataQualityBanner.svelte:232`, `:240`, `:249`).
  - Un'anomalia vera con lo stesso codice di quella iniettata produce due righe con la stessa chiave.
  - In produzione Svelte 5.48 **non** controlla le chiavi duplicate: `validate_each_keys` si inserisce solo
    `if (dev && node.metadata.keyed)` (`EachBlock.js:341`). Gli elementi stanno in una Map per chiave
    (`each.js:278`), quindi una riga rimpiazza l'altra in silenzio. In più il testid
    `data-quality-issue-{code}` diventerebbe ambiguo.
  - Ne è esposto anche `:364` (`NAV_INCOMPLETE`), se il report vero porta un `NAV_INCOMPLETE`.
  - `serveMissingFxRates` (`:188-202`) toglie già le anomalie con lo stesso codice: è il precedente.
- **Gli altri spec che intercettano `/portfolio/report`: nessuno condivide la causa.**
  - `stale-price-banner`: legge il report vero e cerca la sua riga e il suo asset.
  - `dashboard-cache`: trattiene le risposte, non inietta.
  - `dashboard-broker-filter-label`: blocca solo le origini esterne.
  - `gallery`: sostituisce l'intero corpo.
  - Nello stesso spec, `:342` è un controllo di presenza (`.first()` visibile), non un conteggio.

**Verdetto: assumption.** Il test conta su tutta la pagina un numero che riguarda la sua sola riga. Il prodotto è
corretto: la riga iniettata ha esattamente i suoi due link, quella vera il suo.

## 3. Correzione (test-author), solo `frontend/e2e/portfolio/data-quality-banners.spec.ts`

1. `injectDashboardIssues` toglie dal report vero le anomalie con lo stesso `code` di quelle iniettate, prima di
   aggiungerle, come `serveMissingFxRates`. Così ogni riga del test è unica.
2. `:387` conta i link **dentro la propria riga** (`data-quality-issue-MISSING_PRICE` →
   `data-quality-nav-assets-MISSING_PRICE`): devono essere 2. Verifica anche i due id (`901234` e `901235`),
   ciascuno visibile nella riga. Il conteggio dentro la riga è l'oggetto del test: un link solo per due asset era
   il difetto originale.
3. Una riga sorella esplicita: il test inietta anche un'altra anomalia `navigate_asset` (con un suo id) e verifica
   che il suo link stia nella **sua** riga. Così la garanzia non dipende dal seed.

Nessuna chiave i18n, nessun file del runner, nessun codice di prodotto.

## 4. Passi

1. ✅ (08/10) Triage e verdetto. Rosso riprodotto con l'anomalia **vera** del seed (baseline in corsia: `:387`
   rosso, 3 contro 2; `:364` verde).
2. ✅ (08/10) Correzione (test-author), solo nello spec: +38 righe, −7.
   > **Note implementazione**:
   > - `injectDashboardIssues` toglie dal report vero le anomalie con lo stesso codice di quelle iniettate. Il
   >   parametro ora ha tipo `Array<{code: string; …}>`, perché il filtro legge il codice; il commento spiega
   >   perché.
   > - `:394`, lo stesso test (prima `:387`): conta 2 link dentro `data-quality-nav-assets-MISSING_PRICE`, verifica
   >   che 901234 e 901235 siano visibili nella riga, e che il link 901236 della sorella `TRANSACTION_IMPLIED` stia
   >   nella sua riga.
   > - Contro il conteggio vecchio, su tutta la pagina, la sorella da sola porterebbe il totale a 4: il rosso non
   >   dipende più dal seed.
3. ✅ (08/10) Verde in corsia, sullo stesso stato del rosso:
   - i due test (`:371` NAV, `:394` MISSING_PRICE): 2 passati (`/tmp/libreFolio_n_dq_green.log`);
   - `front-portfolio banners` completo: **18 passati a 1 worker** (45,7 s) e **18 passati a 4 worker**
     (26,5 s) (`/tmp/libreFolio_n_dq_banners_w1.log`, `_w4.log`);
   - Prettier pulito sullo spec. `tsc -p tsconfig.e2e.json`: 0 errori nello spec; i 2 errori presenti sono già
     su HEAD e in altri file (`onboarding-tour.spec.ts:863`, `src/lib/types/files.ts:9`).
4. ✅ (08/10) Checkpoint: 2 commit proposti in `/tmp/libreFolio_commits/libreFolio_commit_n_dq_C1..C2.txt` (lo spec;
   questo piano). Le liste dei path sono in `n_dq_paths_C1..C2.txt`, i blob in `n_dq_blobs.txt` e l'albero
   finale in `n_dq_final_tree.txt`. Stato: FROZEN.
