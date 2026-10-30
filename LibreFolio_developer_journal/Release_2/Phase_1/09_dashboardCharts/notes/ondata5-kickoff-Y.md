# Kickoff Y · Cruscotto e grafici — ondata 5 — bozza

Regole comuni: `kickoff-common.md` (leggilo per primo).

> **A cosa serve (per il developer).** (1) **Z-14b + Z-15**: dopo un recupero dei prezzi, le quattro pagine dei prezzi (lista e dettaglio di asset e cambi) e i pannelli di rischio e lotti già aperti si **ricaricano da soli e in silenzio** (niente spinner, niente `aria-busy`: la lezione di Z-18). Esempio: lasci aperto il dettaglio di VWCE mentre il computer dorme; al risveglio il grafico prende i prezzi nuovi senza premere «Aggiorna». (2) **Ritocchi dal feedback della checklist** (Y5-F1…F4): un'icona al posto di «Abs» nelle barre strumenti delle card, tooltip con ritardo sui tre pulsanti, Chart Settings coerenti con il dettaglio, badge del livello di aggregazione sulla card, il selettore dell'asset di confronto uguale a quello del pannello «+» del rischio. (3) **#48, il frontend**: sotto «Le tue posizioni» → «Portafoglio» il rendimento di ogni posizione come linee sovrapposte (Abs e %, «base 100»), «Dettaglio lotto» al posto della vista e «← Portafoglio» per tornare; più una **torta del peso di oggi per asset** e la storia della distribuzione, chiuse comprese.

**Modello**: Sonnet. **Giorni**: 4,5-6 (Y5-1 1; F1 0,5; F2 0,25; F3 0,25; F4 0,5-1; Y5-2 2-3).
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-redesigned-spork` · **Branch**: `e-alfy-y-cruscotto-e-grafici`
**HEAD di partenza (da verificare)**: `1fd80c481` (= `dev_release2`, treni 9 e 10 dentro; già fast-forward).
**Corsia**: porta `6189`, cartella dati `/tmp/librefolio-r13-y`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` (sezione nuova «Ondata 5»); Z-14b/Z-15: piano 06 ~3555-3690 (`06_sleepWake/`, «pronto»), backlog ~8628 e ~8638; #48: `PROSSIMI_LAVORI.md:390-444`. Skill: `design-system`, `devpy-i18n`, `testing-frontend`.

## Decisioni del developer che ti riguardano
- **Z-14b/Z-15**: decisione 22/10, piano «pronto». Il piano 06 (:3688) dice ancora «aspetta il sì» su tre scelte di UX (ricarica silenziosa dei pannelli di rischio; le analisi a richiesta restano come sono; i punti vecchi mostrati subito): il coordinatore ha preso il sì del 22/10 come dato. Se rileggendo il piano vedi un dubbio vero, dillo nell'analisi, ma **parti**.
- **#48**: i colori categoriali per peso aspettano la designer: **parti con i ruoli `cat-*` esistenti** e li cambi dopo (nessun blocco).
- Y5-F1: nel dettaglio asset in modalità prezzi il selettore **Abs/% resta**.

## Cosa fare (nell'ordine; treno tra parentesi)
1. **Y5-1 · Z-14b + Z-15** (**11a**, PARTI SUBITO). Helper nuovo `features/price-refresh/onPricesCaughtUp.ts`; le 4 pagine (`routes/(app)/assets/+page.svelte`, `assets/[id]/+page.svelte`, `fx/+page.svelte`, `fx/[pair]/+page.svelte`), `riskPanelController.svelte.ts` (`:86`, `:651`), `LotsAnalysisPanel.svelte`. Oggi si ricaricano solo Dashboard (`dashboard/+page.svelte:760`) e broker (`brokers/[id]/+page.svelte:491`). **Non usare** `refreshVersion`/`requestPortfolioRefresh` (sono l'«Aggiorna» dell'utente e girano l'icona). Ricarica **silenziosa**: nessuno spinner, nessun `aria-busy`. **Prima i rossi**: Vitest dell'helper e E2E nuovo `price-refresh-reload.spec.ts` (registrato nel runner, riga additiva, `check-orphans` verde). `front-portfolio`, `front-asset asset-list`, `front-fx fx-list`, lo spec nuovo (~15 min, nello slot).
   **Appena committato (il coordinatore ti avvisa)**, **X** può scrivere X5-F1 in `fx/[pair]/+page.svelte`.
2. **Y5-F1** (**11a**): al posto di «Abs» nelle barre strumenti delle **liste Asset e FX** un'**icona** delle card; nel dettaglio asset in modalità prezzi resta il selettore Abs/%. **Tooltip con ritardo e una riga di spiegazione sui tre pulsanti** della barra, **4 lingue** (`./dev.py i18n`). Rossi: Vitest/E2E (`data-testid`, nessun testo).
3. **Y5-F2** (**11a**): in **Chart Settings**, con un segnale di rendimento sovrapposto **spariscono gli indicatori tecnici**, come nel dettaglio. **Y5-F3** (**11a**): **badge del livello di aggregazione** sulla card appena la serie è campionata, come nel dettaglio. Rossi prima.
4. **Y5-F4** (**11a**; **X rivede**): il selettore dell'asset di confronto nelle impostazioni diventa **quello del pannello «+» del rischio**. Riusa il componente esistente (se per riusarlo serve cambiarlo in `features/risk/**`, **non farlo**: richiesta al coordinatore, il file non è tuo).
5. **Y5-2 · #48 frontend + torta** (**11b**; **dopo J5-1**, ma **parti col componente su dati finti**). Appena J (e MF per i segmenti) ti manda il **contratto della serie per posizione** (schema), disegna contro di esso con dati finti: linee sovrapposte (Abs e %, «base 100»), selettori di riga come la tabella dei lotti, «Dettaglio lotto» al posto della vista, «← Portafoglio»; più la torta del peso di oggi per asset e la storia della distribuzione, chiuse comprese. Riusa `LotComparisonChart`/`lotComparisonChartHelpers.ts`. Colori: i ruoli `cat-*` esistenti. Quando J committa l'endpoint (`api sync`), collega i dati veri. Doc `user/dashboard/positions.en.md` (docs-writer, inglese; **timbro Aphra solo se è l'unica modifica**), i18n `dashboard` in 4 lingue. Rossi: Vitest dei helper, E2E del nuovo grafico (`front-portfolio`).
6. **La riga di B5 di MF** (**11b**, su richiesta di MF tramite il coordinatore): `PerformanceChart.svelte`, `OtherPeriodEffectsTable.svelte`, i18n `dashboard`: **scrivi tu** il file, con il testo e lo schema che MF ti manda; è una riga.

## Dipendenze da altre sessioni
- **MF → J → te** (#48): P4, poi la serie per posizione (contratto presto, endpoint dopo). **Tu → X**: il commit di Y5-1 sblocca X5-F1. **X** rivede Y5-F4. **MF → te**: la riga B5.

## File condivisi
- **Tuoi in questa ondata**: `frontend/src/routes/(app)/assets/+page.svelte`, `assets/[id]/+page.svelte`, `fx/+page.svelte`, `fx/[pair]/+page.svelte` (per Z-14b; poi X5-F1 di X), `features/risk/riskPanelController.svelte.ts`, `features/brokers/lots/LotsAnalysisPanel.svelte`, `features/price-refresh/**`; `AssetCard`, `FxCard`, `ChartSettingsModal`, `PriceChartCompact`, `chartSettingsStore.svelte.ts`, `chartSignalRendering.ts`, `reducedPriceQuery.ts` (per F1-F4); `features/dashboard/**`, `lotComparisonChartHelpers.ts`, `i18n/dashboard`, `user/dashboard/positions.en.md`; `PerformanceChart.svelte`, `OtherPeriodEffectsTable.svelte` (su richiesta di MF).
- **Di altri**: backend di #48 (**J**); `features/risk/**` salvo `riskPanelController` (resta com'è); `transactions/+page.svelte` (**X**).

## Non fare
- Nessun colore a mano. Non usare `refreshVersion`/`requestPortfolioRefresh`. Non toccare il backend. Y-43 e la galleria G-22…G-27 sono fuori (designer).
- Non collegare i dati veri di #48 prima dell'endpoint di J.

## Domande
Nessuna (vedi la nota su Z-14b: assunto sì).

## Fatto quando
Per checkpoint: rossi→verdi con comandi e conteggi, `front check` 0/0 (dopo `api sync`), `i18n check`, ratchet dei colori pulito, doc, piano. Righe CHANGELOG proposte: 🔄 «le pagine dei prezzi e i pannelli di rischio si aggiornano da soli dopo un recupero dei prezzi» (Y5-1); 🔄 «icona al posto di «Abs», tooltip sui pulsanti della barra, badge di aggregazione sulle card, impostazioni del grafico coerenti con il dettaglio» (F1-F3); 🔄 «il selettore di confronto è lo stesso del rischio» (F4, o «nessuna»); ✨ «il grafico delle singole posizioni e la torta per asset» (Y5-2). Checkpoint: Y5-1 · Y5-F1/F2/F3 (insieme) · Y5-F4 · Y5-2 · riga B5; ciascuno con **CHECKPOINT READY** e **FROZEN**.
