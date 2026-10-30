# Brief — programma colori · C1 · conversione di neutri, stati e interruttori (broker, impostazioni, strumenti, UI condivisa)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-expert-barnacle`
**Branch**: `e-alfy-t-tokens-theme`
**HEAD di partenza (da verificare)**: `89e8b2e61` (fast-forward fatto dal coordinatore). Nel worktree c'è un file sporco tuo: il piano di T (`10_colorSystem/T-tokensTheme/plan-phase01TokensTheme.prompt.md`), copia in `salvataggi-worktrees-20261021/e-alfy-t-tokens-theme.tracked.diff`: **non toccarlo se non per aggiornarlo**.
**Corsia**: porta `6187`, cartella dati `/tmp/librefolio-r13-c1`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/README.md` e `plan-phase00ColorSystemThemeLab.prompt.md`: D-T27 (~165) e D-T28 (~177), la definizione del cancello (~82-90), il lotto interruttori (~202, ~256). `coordination/registro.md` (~2133, ~2435) per lo stato degli interruttori.
**Regole**: skill `design-system` e `theme-roles` (leggile prima). Solo ruoli (`bg-lf-*`, `text-lf-*`, `border-lf-*`…), **mai `dark:` su un ruolo**, nessuna classe di palette nuova, nessun colore scritto a mano.

## Il mandato (decisione del developer, D-T28 confermata il 21/10)
«Migra veloce, rifinisci dopo»: ogni classe legacy di **neutri** e **stati** va sul ruolo più vicino; dove la scelta non è ovvia, ruolo più vicino e un commento `/* colour: closest role, to review */` (o l'equivalente che il piano usa già per D-T27: verifica e usa quello). Gli **interruttori** vanno sui ruoli Q2 già esistenti (`bg-lf-checked` acceso, `bg-lf-switch-off` spento, `--lf-switch-knob-*`), oggi usati 0 volte.

## Misura del 21/10 (ratchet: m1 590 classi in 45 file, `--check` pulito)
Neutri 189 classi (28 file), stati 235 (27 file), categoriali 147 (19 file, **fuori dal tuo lotto**: aspettano i ruoli di categoria e la designer), `libre-*` 19 (10 file).

## Il tuo perimetro (solo questi file; ognuno ha un solo scrittore in tutta la macchina)
- **Area broker (~165 classi)**: `frontend/src/lib/features/brokers/**` (UnifiedLotsTable, BrokerSharingPanel, LotCustodyModal, BrokerCard, BrokerForm, LotGanttChart, LotComparisonChart), `frontend/src/routes/(app)/brokers/[id]/+page.svelte`, `frontend/src/lib/utils/broker/brokerRoleHelpers.ts`.
- **Area impostazioni, strumenti, UI condivisa (~100 classi)**: `SettingToggle`, `AboutTab`, `supportLinks` (colori dei marchi: probabilmente `--accept`, chiedi), `frontend/src/lib/features/tools/**`, `lib/features/risk/RiskReturnLevel`, `lib/components/charts/ChartAestheticsSection.svelte`, `lib/components/ui/data-editor/DataEditor`, `lib/components/table/DataTableCellContent`.
- Gli interruttori dentro questi file (ChartAestheticsSection 16, SettingToggle 18, DataEditor 5, DataTableCellContent 4, BrokerForm 4, ScheduledInvestmentEditor 4).

**Fuori perimetro** (altri scrittori o rimandati): `lib/theme/**` e `tokens.css` (di **C2**: se ti serve un ruolo nuovo, chiedilo al coordinatore, che lo gira a C2); `app.css` (B6, alla chiusura); `lib/features/transactions/**` (dopo K3a); `routes/(app)/assets/**`, `routes/(app)/fx/**`, `lib/components/assets/**` (dopo Y-39b e Z-29b); `LineChart.svelte`, `chartSignalRendering.ts`, `ChartSettingsModal.svelte`, `PriceChartFull`; le classi categoriali (viola, indaco, rosa, teal, ciano, fucsia).

## Come lavorare
- Dividi per area e affida ogni gruppo di file a un sotto-agente `sonnet` con la skill `theme-roles` (mai due sotto-agenti sugli stessi file); verifichi tu ogni diff.
- Dopo ogni gruppo: `node scripts/theme/theme-roles.mjs --check` (da `frontend/`) e `--update` per stringere la baseline **solo** per i tuoi file; la baseline `frontend/src/themeRoles.baseline.tsv` è un file condiviso con C2: **solo righe dei tuoi file** (vedi «merge conflict on the baseline» nella skill).
- Gate dei temi (Vitest, `LC_ALL=en_US.UTF-8`, più di 3 file → `flock`): `themeRoles`, `themeTokens`, `themeModeReads`, `themeComponentTokens`; i Vitest dei componenti toccati; `front check` in `flock` (dopo `api sync`).
- **E2E `front-utility theme-roles` (24 test) solo con lo slot** del coordinatore. Niente galleria (si fa una volta, in fondo).
- Le risposte della designer (verde Liquidità, flussi neutri, serie di crescita, pallino) **non** ti bloccano.

## Fatto quando
Neutri, stati e interruttori del tuo perimetro a 0 nel ratchet (categoriali esclusi), baseline stretta solo per i tuoi file, gate dei temi verdi, `front check` 0/0, elenco dei punti «to review» per la designer, piano di T aggiornato, righe CHANGELOG proposte (una sola voce 🔄 per il programma colori), **CHECKPOINT READY** e **FROZEN**; E2E nello slot.
