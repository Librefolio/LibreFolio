# Brief — programma colori · C2 · ruoli e serie dei grafici (DV-10, `toneClasses`, ruoli richiesti da C1)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-congenial-potato`
**Branch**: `e-alfy-dv-colori-dei-grafici`
**HEAD di partenza (da verificare)**: `89e8b2e61` (fast-forward fatto dal coordinatore).
**Corsia**: porta `6188`, cartella dati `/tmp/librefolio-r13-c2`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/README.md`, `plan-phase00ColorSystemThemeLab.prompt.md` (D-T27 ~165, D-T28 ~177, DV-10 ~309), `DV-chartColors/plan-phase00ChartColors.prompt.md` (condizioni su `LineChart` ~2032, ~2247), backlog `Phase_0/BACKLOG_POST_1.2.md` DV-10 (~3309), DV-11 (~3331), DV-12 (~3342).
**Regole**: skill `design-system` e `theme-roles`. Solo ruoli, mai `dark:` su un ruolo, nessun colore scritto a mano fuori da `tokens.css`.

## Il mandato (D-T28, confermata il 21/10)
«Migra veloce, rifinisci dopo»: le **serie dei grafici** (DV-10: 153 letterali in `frontend/src/lib/theme/chartTheme.ts`; gli altri file di `lib/theme/*.ts`: `chartCategories.ts` 54, `roleColors.ts` 46, `chartPalettes.ts` 26) passano ai ruoli più vicini, marcati «to review» per la designer. Il ratchet m2 oggi esclude `lib/theme/**`: la misura del tuo lavoro è il conteggio dei letterali che restano, da riportare prima e dopo.

## Il tuo perimetro (un solo scrittore per file in tutta la macchina)
- `frontend/src/lib/theme/**` (tranne i test di altri), incluso `toneClasses.ts` (22 classi legacy) e **`tokens.css`**: sei l'unico che aggiunge o cambia ruoli. Se C1 chiede un ruolo (tramite il coordinatore), lo aggiungi tu, nei due temi, con il contrasto WCAG verificato (`contrast.ts`).
- **Vincolo di API**: `COLORS.greenLight/greenDark/redLight/redDark` e gli altri nomi esportati da `chartTheme.ts` restano con lo stesso nome e la stessa forma (li leggono `LineChart` e Y-39b in parallelo). Cambi **i valori** (dai ruoli), non i nomi.
- DV-11 (i colori dei tipi in due copie, il Designer Lab ancora sui letterali; `chartCategories` su `--lf-cat-*`) **solo se** DV-10 è chiuso e c'è tempo: chiedi prima.

**Fuori perimetro**: `LineChart.svelte` (non toccare `echarts.init(…, chartInitOptions(chartContainer))`, gate K-13), `chartSignalRendering.ts`, ogni componente fuori da `lib/theme/` (sono di C1, Y, Z, W o rimandati), `app.css` (B6, alla chiusura), `gallerySecurity.ts` (di G).

## Come lavorare
- Prima misura (letterali per file e per funzione, quali grafici li usano). Poi una tabella «letterale → ruolo più vicino» con i casi dubbi segnati: la mandi nel primo checkpoint intermedio (**non serve aspettare la risposta per i casi ovvi**).
- Gate: `chartTheme.test.ts`, `chartShades.test.ts`, `chartCategories.test.ts`, `roleColors.test.ts`, `roleColors.dom.test.ts`, `contrast.test.ts`, `drawnColors.test.ts`, i gate dei temi (`themeRoles`, `themeTokens`, `themeModeReads`, `themeComponentTokens`), `front-portfolio chart-safety-unit`; più di 3 file → `flock`, sempre `LC_ALL=en_US.UTF-8`. `front check` in `flock` dopo `api sync`. `theme-roles --check` pulito; la baseline è condivisa con C1: **solo righe dei tuoi file**.
- Prova nei due temi cambiando tema senza ricaricare (Dashboard, dettaglio asset, rischio): screenshot nella tua cartella di lavoro, non nella galleria.
- Le risposte della designer non ti bloccano.

## Fatto quando
Letterali delle serie sostituiti dai ruoli più vicini (conteggio prima/dopo), API di `chartTheme.ts` invariata, ruoli richiesti da C1 aggiunti, gate verdi, elenco «to review» per la designer, piani DV aggiornati, riga CHANGELOG proposta (nella voce unica 🔄 del programma colori), **CHECKPOINT READY** e **FROZEN**.
