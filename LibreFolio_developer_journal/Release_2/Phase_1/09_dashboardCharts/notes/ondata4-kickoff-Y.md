# Brief — workstream Y · Cruscotto e grafici · Y-41 (il confronto asset ↔ cambio funziona davvero: analisi, store, lista dei cambi) + #49 (tooltip «Valore Iniziale/Finale» e frase in 4 lingue) — bozza

> **A cosa serve (per il developer).** Nelle impostazioni di una scheda dei cambi oggi puoi scegliere «confronta con un asset», ma la scheda non lo disegna: la lista dei cambi non carica le serie degli asset (`fx/+page.svelte:860-866`, `comparisonTarget: () => null`, nota «backlog Y-41»). Con Y-41 la scheda di EUR/USD disegna davvero l'ETF che hai scelto, e l'anteprima nelle impostazioni pure, come già fa la lista degli asset. Hai deciso che il confronto deve funzionare nei due sensi, dal dettaglio dell'asset e da quello del cambio: il tuo primo passo è un'**analisi delle quattro superfici** (lista asset, lista cambi, dettaglio asset, dettaglio cambio) che dica cosa manca a ciascuna.
>
> **#49**, promesso a un utente il 17/10: le colonne nascoste «Valore Iniziale» e «Valore Finale» del Portafoglio (`ContributionTable.svelte:390-403`, chiavi `dashboard.startValue`/`endValue`) oggi non hanno un tooltip, e la frase che le spiega sta solo in `user/dashboard/positions.en.md`. Dopo: passando il mouse sulla colonna si legge «valore della posizione a inizio/fine periodo, come la colonna Valore; 0 se la posizione non c'era o era chiusa; il Valore Iniziale è la base delle % del periodo», e la frase c'è anche in it/fr/es. **Tutte e quattro le lingue subito**, come ha chiesto il developer.

**Modello**: Sonnet.
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-redesigned-spork` · **Branch**: `e-alfy-y-cruscotto-e-grafici`
**HEAD di partenza (da verificare)**: `c042f2481` (fast-forward dal coordinatore da `5e5c6b64a`).
**Corsia**: porta `6189`, cartella dati `/tmp/librefolio-r13-y`.
**Piano e backlog**: Y-41 nel backlog `Phase_0/BACKLOG_POST_1.2.md:9907-9915` e nel tuo piano `09_dashboardCharts/plan-phase01DashboardCharts.prompt.md`, «20/10 · Il lotto Y-39» (~7902-8020, Y-41 alla ~8015).

## Cosa fare
0. **Subito, prima di tutto, un checkpoint piccolo**: un `data-testid` sul pulsante delle impostazioni di `frontend/src/lib/components/assets/AssetCard.svelte` (lo chiede Z per l'E2E di Z-29d). Una riga, nessun test tuo da cambiare se non uno che lo fissi. Consegna **CHECKPOINT READY (0)**: il coordinatore lo committa e sblocca Z.
1. **Analisi (mezza giornata)**, sola lettura e una prova a mano sulla tua corsia:
   - lista cambi (`fx/+page.svelte`, `FxCard.svelte`, `ChartSettingsModal.svelte`, `PriceChartCompact.svelte`): cosa manca per disegnare `asset-comparison`;
   - lista asset (`assets/+page.svelte:844`, `:1494-1505`: `comparisonTargetIds`, query ridotta `reducedPriceQuery.ts`, `fxPairData`): già disegna un cambio sopra un asset? e un asset sopra un asset?
   - dettaglio cambio (`fx/[pair]/+page.svelte:927-987`, `loadComparisonAssetsData`): dal codice sembra già caricare gli asset confrontati: verifica a mano che li disegni;
   - dettaglio asset (`assets/[id]/+page.svelte:915`, segnale `fx-pair`): verifica a mano che disegni un cambio.
   Scrivi una tabella «superficie × cosa funziona × cosa manca × chi lo fa» (Y: liste e store; X: dettagli). Consegna e chiudi il turno: il coordinatore gira a X la sua parte.
2. **Il contratto dello store** (per X): come una scheda o una pagina trova la serie dell'asset confrontato partendo dalle impostazioni salvate (lo store `chartSettingsStore.svelte.ts`), con la stessa forma che `chartSignalRendering.ts` già legge (`SignalDataSources.comparisonTarget`). Se basta ciò che c'è, dillo.
3. **La lista dei cambi**: carica le serie degli asset confrontati come fa la lista asset (query ridotta per le sole schede che hanno un confronto configurato, con la cache di N64 dove possibile), e passa `comparisonTarget` reale a `renderLocalSignals`. Anche l'anteprima delle impostazioni. Domanda 11 del piano: qualche richiesta in più sulla lista dei cambi va bene? Se il developer non ha ancora risposto, procedi: il consiglio è sì.
4. **Prima i rossi**: un Vitest che monta `FxCard` con un `asset-comparison` configurato e si aspetta la linea; un E2E in `front-fx fx-list` (la scheda disegna il confronto) e `fx-settings` (l'anteprima). Poi la cura.
5. Se trovi il caso: `FxCard.svelte` converte i punti del cambio in linea due volte (nota di X dell'ondata 3): usa `fxPointToLineDataPoint`.
6. Verdi: Vitest dei file toccati (in `flock` se più di 3), `front check` (dopo `api sync`), E2E `front-fx fx-list`, `fx-settings`, `front-asset asset-list` nello slot. Ratchet dei colori pulito.
7. **#49** (mezza giornata, dopo l'analisi di Y-41, checkpoint a parte): il tooltip sulle due colonne di `ContributionTable.svelte` con il testo di `PROSSIMI_LAVORI.md` §«#49» («Risposta data»), chiavi nuove in `i18n/dashboard/{en,it,fr,es}.json` (`./dev.py i18n add …`), con lo stesso meccanismo dei tooltip delle altre colonne della tabella; un Vitest che fissa il tooltip. Poi la frase in `user/dashboard/positions.{it,fr,es}.md`: cerca prima in `positions.en.md` dove sta davvero (il #49 dice «riga ~96», il grep del 22/10 su «Start Value» non la trova: verifica), e scrivila nelle tre lingue con le stesse parole della UI. **Solo se è l'unica modifica di `positions.en.md`**: `./dev.py mkdocs translate-stamp --file user/dashboard/positions.en.md`. `i18n check`, `mkdocs build`, `check-links`.

## File condivisi
- Tuoi in questa ondata: `chartSettingsStore.svelte.ts`, `chartSignalRendering.ts`, `reducedPriceQuery.ts`, `fx/+page.svelte`, `assets/+page.svelte`, `FxCard.svelte`, `AssetCard.svelte`, `ChartSettingsModal.svelte`, `PriceChartCompact.svelte`.
- Di X: `assets/[id]/+page.svelte`, `fx/[pair]/+page.svelte`, `chartPageSignals.ts`, `loadComparisonData.ts`. Se Y-41 chiede qualcosa lì, scrivilo nell'analisi: lo fa X.
- Z aspetta solo la riga del punto 0.

## Non fare
- Non toccare i file di X e di Z. Niente colori a mano. Non iniziare Y-43 (tassi ridotti sulle schede dei cambi): dopo la 1.3.

## Fatto quando
Checkpoint 0 consegnato; analisi delle 4 superfici consegnata; contratto dello store scritto (doc `developer/frontend/components/charts.md` se serve); la lista dei cambi disegna il confronto nelle schede e nell'anteprima; rossi→verdi; E2E verdi nello slot; #49 con tooltip e frase nelle 4 lingue, `i18n check` e `mkdocs build` verdi, timbro Aphra solo se dovuto; piano aggiornato; righe CHANGELOG proposte (✨ «le schede dei cambi disegnano il confronto con un asset»; 🔄 «tooltip su Valore Iniziale e Valore Finale» — o nessuna, dillo), **CHECKPOINT READY** e **FROZEN**.
