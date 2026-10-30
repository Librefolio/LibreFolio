# Brief — workstream Y · Cruscotto e grafici · Y-39a (chiusura)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-redesigned-spork`
**Branch**: `e-alfy-y-cruscotto-e-grafici`
**HEAD di partenza (da verificare)**: `e64e9df0f` (merge di `dev_release2` `208199bf6` nel tuo ramo; genitori `d8bc582a7` e `208199bf6`). Il tuo albero è **pulito**: il tuo lavoro di Y-39a (11 file) il coordinatore l'ha committato così com'era in `d8bc582a7` (commit intermedio, soggetto «feat(charts): one signal renderer for cards and preview (Y-39a)») per non perderlo, e poi ha portato dentro dev.
**Corsia**: porta `6189`, cartella dati `/tmp/librefolio-r13-y`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md`. Leggi solo: «20/10 · Il lotto Y-39: decisioni, contratto, passi» (riga ~7902) e «I passi di Y-39a» (riga ~8044). Il tuo vecchio script dell'E2E è in `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/copilot-enel/session-state/17050e81-e75a-425a-9072-643b8a0612d8/files/scripts/y39a_e2e.sh` (ha percorsi del Mac).

## Dove eri rimasto
Il codice di Y-39a era fatto e verde in leggero (4 file di rossi 375/375, 31 vicini 1044/1044, `svelte-check` 0/0): il modulo `lib/charts/chartSignalRendering.ts`, la modale con `signalSources` al posto di `pairsDataMap`/`assetsDataMap`, le due pagine (Assets, FX) che passano dal modulo, il cancello `signalRendering.gate.test.ts`. Le **3 righe del runner** `scripts/test_runner/_frontend_utility.py` sono già autorizzate e già dentro. Mancavano l'E2E (~25 min) e il checkpoint.

## Cosa fare ora (un solo lotto: chiudere Y-39a)
1. **Verifica la base** e rileggi i file portati da dev (non dovrebbe esserci niente di tuo cambiato: la simulazione del merge era pulita).
2. **Ripulisci le parole della fase rossa** nei quattro file di test. Una revisione veloce del tuo diff ha trovato, e il coordinatore ha controllato:
   - `frontend/src/signalRendering.gate.test.ts`: righe 45-46 («Red until Y-39a…», «Registered (to be)») e i titoli dei test alle righe ~397 e ~407;
   - `frontend/src/lib/components/charts/ChartSettingsModal.test.ts`: righe 36, 41, 87, 175, 204, 225 («Red today», «Registered (to be)», copia locale di `SignalDataSources` con `as unknown as`, titoli con «RED:»);
   - `frontend/src/lib/charts/__tests__/chartSignalRendering.test.ts`: righe 42-47, 53, 70, 96-118 (import dinamico calcolato con `@vite-ignore` e tipi copiati a mano: ora il modulo esiste, vale un import statico);
   - `frontend/src/lib/components/charts/chartCoreHelpers.test.ts`: riga ~297 («Red until Y-39a»).
   Cambia **solo** parole, titoli e import. **Non cambiare le asserzioni** né il numero dei test. Il `console.error` alla riga 121 del modulo è copiato dal vecchio codice delle pagine: lascialo.
3. **Rilancia le prove leggere sulla base fusa** (una alla volta, carico sotto 8): i 4 file di rossi più i 31 vicini (prima 1044/1044), `front check`, `prettier --check` sui file toccati, `theme-roles --check`, `./dev.py test check-orphans`.
4. **E2E: è una corsa pesante (~25 min), non partire da solo.** La sequenza è: popola la corsia (`db populate --force --clean`, ~12 s), poi una spec alla volta: `front-fx fx-settings` (3 test, con la build di debug e la guardia d'allargamento), `front-fx fx-list` (~25), `front-asset asset-list` (~40). **Bloccata finché** (a) il developer non installa il Chromium di Playwright 1228 sulla macchina, e (b) il coordinatore non ti dà lo slot. Se arrivi qui prima del via, chiudi il turno con «pronto per lo slot» e dichiara cosa hai già verificato.
5. **Piano e backlog**: aggiorna il piano (✅, note, fuori pista). Y-41 e Y-42 sono già nel backlog, committati. Poi **CHECKPOINT READY** con elenco esatto dei file, prove con numeri, righe del CHANGELOG (card e anteprima disegnano da uno stesso modulo) e messaggio di commit proposto per un commit finale di rifinitura.

## Non fare
- **Non iniziare Y-39b** (anteprima come asset detail, colore della linea di base sulle card): è il lotto dopo. Le condizioni di DV su `LineChart.svelte` (non toccare `echarts.init(…, chartInitOptions(chartContainer))`, nessun colore nuovo, nessun `isDark ? … : …`) valgono per allora.
- Non toccare i file di Z (backend dei prezzi e dei segnali, `price_query.py`, `services/signals/aggregation.py`, `signal_sampling_cases.v1.json`) né quelli di H.
- Non rilanciare la galleria (è una pausa di tutta la macchina, la annuncia il coordinatore).

## Fatto quando
Le prove leggere sono verdi sulla base fusa, l'E2E dei tre spec è verde (con lo slot), le parole della fase rossa sono sparite dai quattro file, il piano è aggiornato, hai scritto **FROZEN**. Dopo l'ingresso in `dev_release2` si libera `assets/+page.svelte` per Z-29b.
