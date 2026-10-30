# Brief — workstream X · Plugin asset e ricerca · Y-42 (le pagine di dettaglio disegnano i segnali con il modulo comune)

> **A cosa serve (per il developer).** Oggi gli indicatori tecnici (medie mobili, RSI, bande…) si disegnano con **un solo codice** nelle schede della lista e nell'anteprima delle impostazioni (Y-39a), ma le due **pagine di dettaglio** (asset e cambio) hanno ancora un codice loro. Con Y-42 tutte e quattro usano lo stesso: un indicatore appare identico in lista, anteprima e dettaglio, e una correzione futura si fa in un posto solo invece che in tre. L'utente non vede differenze, se non che i casi oggi diversi diventano uguali.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-cuddly-engine` · **Branch**: `e-alfy-x-plugin-asset-e-ricerca`
**HEAD di partenza (da verificare)**: il coordinatore ha committato la tua sezione di piano rimasta sporca (+25 righe in `03_pluginsAssets/plan-phase01PluginsAssets.prompt.md`) e ha fuso `dev_release2` (`2879ae3e4`) nel tuo ramo (era 244 commit indietro): lo SHA esatto è nel messaggio d'avvio. `npm ci` fatto per Linux.
**Corsia**: porta `6191`, cartella dati `/tmp/librefolio-r13-x`.
**Piano e backlog**: Y-42 nel backlog `Phase_0/BACKLOG_POST_1.2.md` (~9860-9870) e nel piano di Y `09_dashboardCharts/plan-phase01DashboardCharts.prompt.md` (~8017, «Fuori dal lotto… Y-42»). Il tuo piano: `03_pluginsAssets/plan-phase01PluginsAssets.prompt.md` (leggi solo la tua sezione più recente).

## Cosa fare
1. `frontend/src/routes/(app)/assets/[id]/+page.svelte` (`overlaySignals`, ~711-750) e `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (~390-430) smettono di chiamare `signalFromConfig` e usano `frontend/src/lib/charts/chartSignalRendering.ts` (più `fxPointToLineDataPoint` per i cambi). Se trovi il caso, anche `FxCard.svelte` converte i punti in linea due volte: passa a `fxPointToLineDataPoint` **solo se** Y non lo sta toccando in Y-40 (chiedi prima: in questa ondata `FxCard` è di Y).
2. Il gate `frontend/src/signalRendering.gate.test.ts` (intestazione righe 1-60, `KNOWN_COPIES` ~76-86) contiene proprio queste due pagine e **fallisce** se una voce non chiama più `signalFromConfig(`: togli le due voci nello stesso lotto.
3. Prima i rossi dove il comportamento cambia (per esempio un segnale disegnato diversamente nel dettaglio rispetto alla lista: scrivi il caso), poi la cura. Se ti serve aggiungere qualcosa a `chartSignalRendering.ts` (è di **Y**), scrivilo come richiesta al coordinatore, non modificarlo tu.
4. Verdi: `core-unit` (in `flock`, `LC_ALL=en_US.UTF-8`), i Vitest delle due pagine, `front check` (in `flock`, dopo `api sync`); E2E nello slot: `front-asset asset-detail` e `front-fx fx-detail` (nomi esatti dal runner).

## Per Y-40 (sessione Y, in parallelo)
In questa ondata **le due pagine di dettaglio sono tue**. Y-40 vuole che il dettaglio si apra nella vista scelta in lista (assoluto, percentuale, rendimento mobile). Quando Y ha committato il contratto dello store (`primaryView`), il coordinatore ti chiederà di leggere quel parametro nelle pagine di dettaglio: è un secondo passo, non anticiparlo.

## Passo C — N64 (decisione del developer del 21/10: in 1.3, dopo Y-42)
> **A cosa serve.** I prezzi hanno già una cache nel browser, gli indicatori no: passi da 1 anno a 5 anni e torni a 1 anno, e RSI e medie vengono richiesti di nuovo con la rotellina. Con N64 tornano subito, come i prezzi.
- Piano: `03_pluginsAssets/plan-phase01PluginsAssets.prompt.md` (righe ~6975-7060 e ~8418-8470). X-R16, il prerequisito, è chiuso dal 20/10.
- Decisioni del developer: **Q1 sì**: se il risultato è in cache, nessuna richiesta, nessun token, nessuna rotellina, «Refresh» fermo; **Q2 sì**: dopo un aggiornamento dei prezzi in background, il passaggio successivo richiede di nuovo, con la rotellina, come i prezzi (una regola sola); **Q3**: in 1.3.
- Parte **solo dopo il via del coordinatore** (Y-42 committato). Prima di toccare un file, controlla che non sia sporco nel worktree di Y (`git -C /home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-redesigned-spork status --porcelain`): Y-40 lavora sulle liste e sullo store dei grafici. Se c'è sovrapposizione, fermati e chiedi.
- Prima i rossi (cache colpita: nessuna richiesta; refresh dei prezzi: la richiesta riparte), poi la cura; Vitest, `front check`, E2E di dettaglio nello slot.
- Consegna **CHECKPOINT READY (C)** e FROZEN.

## Non fare
- Non toccare i file di Y-40 (`assets/+page.svelte`, `fx/+page.svelte`, `AssetCard`, `FxCard`, `PriceChartCompact`, `ChartSettingsModal`, lo store delle impostazioni), `lib/theme/**`, `lib/features/transactions/**`.
- Gli altri lotti di X (CP5, CP7/FE4, FE5a, CP12) sono **dopo la 1.3**: non iniziarli. N64 è il passo C qui sopra.
- Condizioni di DV sui grafici: nessun colore scritto a mano.

## Fatto quando
Le due pagine sul modulo comune, il gate con la lista accorciata, rossi→verdi, E2E di dettaglio verdi nello slot, doc per sviluppatori (`developer/frontend/components/charts.md` se serve) e piano aggiornati, righe CHANGELOG proposte (probabilmente nessuna visibile: dillo), **CHECKPOINT READY** e **FROZEN**.
