# Piano — Workstream BK, colori dei broker (migrazione 1:1 ai ruoli di colore)

> **Workstream BK del programma colori** (D-T28), sessione «BK - colori dei broker». Coordinatore: sessione «UI color
> analysis» (`aec04834-1532-4d86-9e3f-f942e82aca89`).
> Branch `e-alfy-bk-broker-colors` (rinominato dall'app; prima `e-alfy-sturdy-couscous`).
> - **Baseline dell'analisi:** `8f2824046`.
> - **Base attuale:** `2eef01e59`, base merge del coordinatore dopo il checkpoint L1–L3 (`82f304f4a`), con i ruoli nuovi
>   di T (`f043c1b58`: `text-lf-on-overlay`, `SIGN_BADGE`, gli hover pieni). Prima: `6e569084a`, fast-forward del
>   coordinatore (skill `design-system` di T, D-T29, e treni della 1.3).
> - **Corsia:** porta **6158**, dati **`/tmp/librefolio-r2-bk`**.
> - **Comandi:** `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6158 --data-dir /tmp/librefolio-r2-bk …`.
>
> **Fonti:**
> - skill [`design-system`](../../../../../.github/skills/design-tools/design-system/SKILL.md) (D-T29, la fonte delle
>   regole) e [`theme-roles`](../../../../../.github/skills/design-tools/theme-roles/SKILL.md) (tabella classe → ruolo,
>   baseline);
> - [piano generale](../plan-phase00ColorSystemThemeLab.prompt.md) (D-T27, D-T28, D-T29);
> - [piano di T](../T-tokensTheme/plan-phase01TokensTheme.prompt.md) (ricetta dei campi, lotto degli interruttori);
> - [piano di DV](../DV-chartColors/plan-phase00ChartColors.prompt.md), sezione «Inventario m1/m2 dei file dei grafici»
>   (lotti dei broker, giro dei badge);
> - devWiki: `problems/tailwind4-same-property-utilities-sorted-by-name`, `problems/colour-ratchet-resolve-drops-an-accept`,
>   `decisions/colour-factorisation-at-pixel-parity` (il grafo di graphify non c'è nel worktree: pagine lette direttamente).
>
> **Regola:** solo migrazione 1:1 ai ruoli, senza decisioni di design. Dove la tabella non basta, l'elemento resta com'è
> e si annota; i ruoli nuovi li crea solo T.

## ✅ Autorizzazione

- **Richiesta del developer (16/10, testuale, dal kickoff):** «l'obiettivo intanto è fattorizzare e migrare al nuvo color
  design sistem, poi le rifiniture le facciamo nel tempo, anzi sono un pò deluso che abbiamo fatto solo il 22% in 1 gg,
  non riesci a mettere al lavoro più agenti?»; «è importante migrare il prima possibile i componenti prima di metterci a
  sviluppare funzioni grandi, quindi vedi tu.»; «nel migrare cerca di seguire i colori dei temi che la designer ci ha
  intanto dato».
- **D-T28:** i piani d'analisi dei workstream nuovi li approva il coordinatore, nel perimetro «solo migrazione 1:1 ai
  ruoli, senza decisioni di design».
- **16/10, ~11:08:** analisi mandata al coordinatore; piano approvato (uscita dal modo piano). Le quattro decisioni
  chieste al coordinatore (set VIEWER, `<style>` `--lf-cmp-*`, sotto-agenti, slot pesante) partono dai default proposti;
  se la sua risposta li cambia, li adeguo.

## Stato attuale (verificato sul codice, 16/10, base `8f2824046`)

- **Area:** `lib/features/brokers/**` (15 file con classi legacy) e `routes/(app)/brokers/**` (2). `--report`: m1
  **1.153** (974 + 179), m2 0; ratchet 0 violazioni, grammatica 0. Programma: m1 8.249, m2 54.
- **Nessun test** dell'area (Vitest né E2E) asserisce classi di colore. Latente, non di BK: `brokers-detail.spec.ts:392–419`
  `toHaveClass(/selected/)` sulle righe di `DataTable` (T/W6; spec della 1.3): la regex prenderebbe anche un ruolo
  `bg-lf-selected`.
- **Altri worktree** (git status in sola lettura, 22 worktree, escluso il checkout principale): solo Y ha file aperti
  nell'area, `lots/LotCustodyModal.svelte` (M) e `lots/LotCustodyModal.test.ts` (nuovo). Il coordinatore lo riserva:
  migrazione dalla versione di Y, dopo il suo ingresso (lotto L4). Nessun commit pendente sull'area in nessun ramo.
- **`<style>` fuori dal perimetro:** `BrokerImportFilesModal` (28 letture `--lf-cmp-broker-import-files-*`, `files.css`)
  e `UnifiedLotsTable` (8 `--lf-cmp-lots-table-*`, `table.css`, più le variabili dei broker di DV). Portarli ai ruoli
  lascerebbe senza lettori le definizioni di T: il gate (c) di `themeComponentTokens` cadrebbe → B5/W6 di T.

### Inventario dal baseline

| File | m1 | neutri | marchio | stati | segni | categorie | interr. | resta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `BrokerCard.svelte` | 64 | 43 | 7 | 6 | – | 8 (+4 ramo VIEWER) | – | 12 |
| `BrokerDiscoveryCard.svelte` | 9 | 7 | 2 | – | – | – | – | 0 |
| `BrokerForm.svelte` | 72 | 49 | 19 | 4 | – | – | 4 | 5 |
| `BrokerImportFilesModal.svelte` | 12 | 11 | 1 | – | – | – | – | 0 |
| `BrokerModal.svelte` | 23 | 17 | – | 6 | – | – | – | 0 |
| `BrokerSharingModal.svelte` | 10 | 9 | 1 | – | – | – | – | 0 |
| `BrokerSharingPanel.svelte` | 223 | 156 | 11 | 26 | – | 30 (+15 set VIEWER) | – | 45 |
| `DeleteBrokerDialog.svelte` | 30 | 23 | 2 | 5 | – | – | – | 0 |
| `lots/LotComparisonChart.svelte` | 96 | 88 | 8 | – | – | – | – | 2 |
| `lots/LotCustodyModal.svelte` | 205 | 167 | 8 | 6 | 4 | 20 | – | 20 |
| `lots/LotDataQualityBanner.svelte` | 20 | – | – | 20 | – | – | – | 0 |
| `lots/LotGanttChart.svelte` | 36 | 32 | – | – | – | 4 | – | 4 |
| `lots/LotWacPriceChart.svelte` | 48 | 44 | 4 | – | – | – | – | 0 |
| `lots/LotsAnalysisPanel.svelte` | 42 | 32 | 2 | 8 | – | – | – | 0 |
| `lots/UnifiedLotsTable.svelte` | 84 | 30 | – | – | – | 54 (+6 CLOSED) | – | 60 |
| `routes/(app)/brokers/+page.svelte` | 38 | 23 | 10 | 5 | – | – | – | 0 |
| `routes/(app)/brokers/[id]/+page.svelte` | 141 | 113 | 13 | 7 | – | 8 (+4 ramo VIEWER) | – | 12 |
| **Totale** | **1.153** | 844 | 88 | 93 | 4 | 124 (+29) | 4 | **160** |

Il marchio conta anche lo smeraldo usato come link o selezione (6). **Esito atteso: 1.153 → 160 (−993, 86 %)**; il
programma passa da 8.249 a 7.256.

### Mappature (tabella della skill e precedenti già nel target)

- **Superfici e testi:** la tabella della skill (`bg-lf-card`, `bg-lf-panel`, `bg-lf-neutral`, `text-lf-primary`,
  `-secondary`, `-muted`, `border-lf-subtle`). Su un pannello l'hover è `hover:bg-lf-neutral` (`lf-hover` = `lf-panel`,
  domanda aperta 3): i grigi pieni diventano `bg-lf-panel … hover:bg-lf-neutral` (10 precedenti).
- **Bottoni della toolbar del dettaglio:** `bg-lf-card border-lf-subtle text-lf-secondary hover:bg-lf-hover`, come
  `AiExportMenu` nella stessa riga. **Bordati gray-300:** `border-lf-input` (7 precedenti).
- **Campi:** ricetta di T, `border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary` (+ segnaposto,
  `focus:ring-lf-focus`, `focus:border-lf-focus`). Il bordo d'errore del nome diventa un ternario (regola 4 della skill).
- **Segmenti dei grafici dei lotti:** `bg-lf-checked text-lf-on-checked` / `bg-lf-card text-lf-muted hover:bg-lf-hover`.
- **Menu:** `bg-lf-card border-lf-raised shadow-lg shadow-lf-shadow`. **Card di pagina:** `shadow-sm shadow-lf-shadow-card`.
- **Hover delle card dei broker:** `hover:border-lf-link/30 hover:bg-lf-selected/50`, come `CHOICE_CARD` del PAC (DV);
  FxCard e AssetCard hanno lo stesso hover: AF dovrebbe usare la stessa mappatura.
- **Stati:** tabella; il banner dei lotti legge `STATUS_TONES.dataQuality` (stesso legacy del `DataQualityBanner` di T);
  hover su tinta `hover:bg-lf-X-line` (domanda aperta 2); rosso pieno `bg-lf-danger-solid`; ambra piena
  `bg-lf-warning … hover:bg-lf-warning-hover`. Attivo/inattivo del broker = stato (success/danger), non segno (regola 7).
- **Segni:** commissioni e tasse della custodia → `text-lf-loss` (`SIGN_TEXT`).
- **Radice:** `text-lf-primary` su ogni componente e pagina migrati (regola 1).

### Restano legacy (→ backlog BK-n)

1. **Ruoli del broker OWNER/EDITOR/VIEWER (categoria), 69:** badge di `BrokerCard` e del dettaglio, sezioni di
   `BrokerSharingPanel`; il grigio VIEWER resta col set. Catena: `utils/broker/brokerRoleHelpers.ts` (T, categoria).
2. **Badge dei lotti, 84:** direzione, stato, in transito, custodia, marcatori degli eventi (`UnifiedLotsTable`,
   `LotGanttChart`, `LotCustodyModal`) → giro dei badge (DV-7).
3. **Interruttore «Attivo» di `BrokerForm`, 4** → lotto degli interruttori di T (nel suo inventario il percorso è ancora
   `components/brokers/…:298`).
4. **Icona `text-white` sullo scrim di `BrokerForm`, 1:** manca un ruolo per il testo sullo scrim.
5. **Campione della legenda «stimato al costo» di `LotComparisonChart`, 2:** segue `LOT_COMPARISON_COLORS.estimatedValue`
   (DV); un ruolo diverso dal colore della linea farebbe divergere legenda e linea.

## Passi

### S0 — Piano nel repo ✅ (16/10/2026)
> **Note implementazione**: piano scritto qui dall'analisi della sessione; `npm ci` in `frontend/` (approvato una volta),
> verde. Self-check di sola lettura per le bozze nella cartella di sessione (`bk_selfcheck.mjs`: m1, m2 e G1–G4 sui soli
> file dati).
> **⚠️ Fuori pista**: alla ripresa HEAD era `6e569084a`, non `8f2824046`: fast-forward del coordinatore con la skill
> `design-system` di T e i treni 105–106 della 1.3. Verificato: nessun file dell'area, del baseline né di `lib/theme/`
> cambiato. La skill nuova conferma le mappature (hover su tinta → `-line`; su un pannello → `hover:bg-lf-neutral`;
> guadagno e perdita separati da successo ed errore).
> **⚠️ Fuori pista**: `npm ci` (npm 11) ha saltato gli script d'installazione di `esbuild` e `fsevents`; il binario di
> piattaforma `@esbuild/darwin-arm64` c'è. Nessuna approvazione di script data.

### S1 — L1 · lista e modali dei broker ✅ (16/10/2026, bozza riletta; prove in S4)
`BrokerCard`, `BrokerDiscoveryCard`, `BrokerForm`, `BrokerModal`, `DeleteBrokerDialog`, `routes/(app)/brokers/+page` —
236 → 17. Bozza di un sotto-agente, riletta da me.
> **Note implementazione**: self-check sui sei file: m1 12 / 0 / 5 / 0 / 0 / 0, m2 0, grammatica 0. Diff a parole
> riletto: solo classi di colore, più la direttiva `class:border-red-300` del nome tolta e portata nel `class` come
> ternario (regola 4: `{nome vuoto ? 'border-lf-danger' : 'border-lf-input hover:border-lf-input-hover'}`; il fuoco
> `focus:border-lf-focus` vince ancora su tutti e due, come prima). Card e pagina con `text-lf-primary` sulla radice e
> `shadow-lf-shadow-card`; hover delle card `hover:border-lf-link/30 hover:bg-lf-selected/50`; campi sulla ricetta di T;
> scrim `bg-lf-overlay`; bottoni pieni sui ruoli d'azione, rosso pieno e ambra piena. Restano il badge del ruolo (BK-1),
> l'interruttore e la sua manopola (BK-3), l'icona sullo scrim (BK-4).
> **⚠️ Fuori pista**: la bozza aveva il bordo d'errore del nome su `border-lf-danger-line` (tabella: bordo 200–400 →
> `-line`). Corretto in `border-lf-danger`: la skill `design-system` (D-T29, entrata con la base `6e569084a`) dà
> `--lf-danger` per «a border (an invalid field)», e il bordo di un campo va a 3:1 (regola 5), che `-line` non raggiunge;
> è anche il ruolo del lotto input di T. Da rivedere per il developer: il rosso è più deciso del `red-300` di prima.
> - Non toccati, senza classi di colore: il divisore `border-t` sopra i saldi iniziali (`BrokerForm`, ~348) disegna nel
>   `currentColor` (Tailwind 4, nessuna regola di compatibilità in `app.css`), come prima; nominarlo `border-lf-subtle`
>   cambierebbe l'aspetto → da rivedere. Il `focus:ring-offset-2` della card tiene lo stacco bianco predefinito anche in
>   scuro, come prima.
> - **Controllo «solo scuro»** del coordinatore (`dark_only_check.py 6e569084a`, 11:28): 1 caso su 16 file,
>   `BrokerForm.svelte:307` della base (`border … dark:border-slate-700`, nessun bordo chiaro): nella bozza è già
>   `border border-lf-subtle`. In chiaro quel bordo, come quelli senza nome dei quattro campi del form, disegnava nel
>   `currentColor`: ora ha il suo ruolo (subtle, input), quindi in chiaro cambia un poco → da rivedere.

### S2 — L2 · dettaglio e condivisione ✅ (16/10/2026, bozza riletta; prove in S4)
`routes/(app)/brokers/[id]/+page`, `BrokerSharingPanel`, `BrokerSharingModal`, `BrokerImportFilesModal` (solo il markup)
— 386 → 57. Bozza di un sotto-agente, riletta da me.
> **Note implementazione**: self-check sui quattro file: m1 12 / 45 / 0 / 0, m2 0, grammatica 0. Diff a parole riletto:
> solo classi di colore. Bottoni della toolbar del dettaglio `bg-lf-card border-lf-subtle text-lf-secondary
> hover:bg-lf-hover` (come `AiExportMenu`); i tre grigi pieni `bg-lf-panel text-lf-secondary hover:bg-lf-neutral`;
> attivo, scoperto e vendite allo scoperto del broker su `text-lf-success` / `text-lf-danger` / `text-lf-muted` (uno
> stato, non un segno); valore totale `text-lf-link`. Pannello di condivisione: «Ripristina» `text-lf-warning
> hover:bg-lf-warning-soft`; errore di caricamento sulla terna danger, «Riprova» `hover:bg-lf-danger-line`; i due
> bottoni del riquadro «il tuo accesso» stanno su `bg-lf-panel` → `hover:bg-lf-neutral`; trigger dei ruoli e campi
> della quota sulla ricetta del campo; menu `bg-lf-card border-lf-raised shadow-lg shadow-lf-shadow`. Restano le icone, le
> chip e gli avatar dei tre ruoli e il badge della quota (BK-1).
> - Da rivedere: l'iniziale `text-lf-muted` sull'avatar `bg-lf-neutral` della modale di modifica è una coppia che il
>   gate non misura (circa 4,0:1, prima circa 3,9:1); i campi della quota non hanno uno stile di fuoco, come prima.

### S3 — L3 · analisi dei lotti ✅ (16/10/2026, bozza riletta; prove in S4)
`LotsAnalysisPanel`, `LotDataQualityBanner`, `LotComparisonChart`, `LotWacPriceChart`, `LotGanttChart`,
`UnifiedLotsTable` — 326 → 66. Bozza di un sotto-agente, riletta da me.
> **Note implementazione**: self-check sui sei file: m1 0 / 0 / 2 / 0 / 4 / 60, m2 0, grammatica 0. Diff a parole
> riletto: cambiano solo classi di colore, più l'import di `STATUS_TONES` in `LotDataQualityBanner`, che ora restituisce
> `STATUS_TONES.dataQuality.{attention,info}.{container,button}` (stesso legacy del `DataQualityBanner` di T, migrato
> così in `d80b9e0cd`). Radici: `text-lf-primary` sulle card e sui riquadri; pannello e skeleton su card, panel/80 e
> neutral; segmenti dei quattro grafici `bg-lf-checked text-lf-on-checked` / `bg-lf-card text-lf-muted hover:bg-lf-hover`;
> card di pagina `shadow-sm shadow-lf-shadow-card`; errore del pannello sulla terna danger. Restano: il trattino
> «stimato al costo» (BK-5), la chip «in transito» di Gantt e i badge di `UnifiedLotsTable` (BK-2).
> - Il banner dei lotti non prende `text-lf-primary` sulla radice: il suo testo è già il `-on-soft` di `STATUS_TONES`, e
>   due colori di testo sullo stesso elemento andrebbero contro la regola 4.
> - Le celle di `UnifiedLotsTable` senza un colore proprio (il nome del broker della custodia) ereditano ora
>   `text-lf-primary` dalla sezione invece del colore legacy del `body`: è la regola 1 della skill.

### S4 — Prove leggere e baseline ✅ (16/10/2026)
`nice -n 10`, carico < 50, una alla volta: `--check`; Vitest `themeRoles`, `themeTokens`, `themeComponentTokens`,
`moneyRenderSites`; Vitest dei componenti toccati; Prettier sui file; `git diff --check`; scan «stessa proprietà» e
catene. Poi `--update` una volta.
> **Note implementazione** (prima tornata, 11:43–11:47, script `bk_light_gates2.sh` della sessione, base `6e569084a`):
> - `api sync` prima (coordinatore, 11:20: le Vitest dei componenti chiedono `./generated`): 11:36, exit 0, sotto `nice`
>   a carico 44.
> - `node scripts/theme/theme-roles.mjs --check`: pulito, 16 file sotto il loro record.
> - `vitest run` dei gate `themeRoles`, `themeTokens`, `themeComponentTokens`, `moneyRenderSites`: 4 file, 89/89.
> - `vitest run src/lib/features/brokers/`: 15 file, 638/638 (componenti `BrokerCard`, `BrokerModal`,
>   `BrokerSharingPanel`, `BrokerImportFilesModal` e gli helper dei lotti).
> - `git diff --check`: pulito. Controllo «solo scuro» del coordinatore: 1 caso, già risolto (vedi S1).
> - Self-check BK sui 16 file: m1 140 (area 345 con i 205 di `LotCustodyModal`), m2 0, G1–G4 0. Scan «stessa
>   proprietà» (con controllo positivo: 3 casi su 3 trovati in un file finto): 1 sola segnalazione, l'interruttore lasciato
>   legacy di `BrokerForm` (due direttive `class:` che si escludono), quindi nessun caso reale.
> - Prettier `--check`: 6 file segnalati (`BrokerForm`, `BrokerSharingPanel`, `LotComparisonChart`, `LotWacPriceChart`,
>   `LotsAnalysisPanel`, `[id]/+page`).
>
> ✅ **Chiusura** (11:54–12:01): le sei versioni della base erano pulite per Prettier (controllo via `--stdin-filepath`),
> quindi `prettier --write` su quei sei file tocca solo righe cambiate da noi: a capo degli attributi, perché le stringhe
> di classe si sono accorciate (elementi raccolti su una riga) o allungate (i campi di `BrokerForm`, aperti su più righe).
> Poi `node scripts/theme/theme-roles.mjs --update`: **m1 8.249 → 7.441, m2 54 → 54**; area 1.153 → 345 (140 nei 16 file,
> più i 205 di `LotCustodyModal`). `--check` pulito; Vitest `themeRoles.gate` 47/47; Prettier pulito sui 16 file;
> `git diff --check` pulito; self-check BK dopo la formattazione invariato (m1 140, m2 0, G1–G4 0).
> - Le Vitest dei componenti (638/638) sono girate prima della formattazione: dopo ci sono solo a capo dentro i tag e
>   dentro le `{…}`, che non cambiano il codice compilato. Non rilanciate per non pesare sulla macchina.
> - **⚠️ Fuori pista**: alle 11:53–11:57 la rete è caduta e il turno si è chiuso con errore; nessun comando era in corso
>   (`api sync`, le prove e il controllo della base erano già finiti). Ripreso dal piano.

### S5 — Checkpoint L1–L3 ✅ (16/10/2026, inviato ~12:05; FROZEN fino al commit del coordinatore)
Backlog BK-n, messaggio CHECKPOINT READY al coordinatore, FROZEN.
> **Note implementazione**: backlog BK-1…BK-8 nella sezione BK; checkpoint con 18 file tracciati (16 sorgenti, baseline,
> backlog) più questo piano, nuovo. Commit proposto: `feat(theme): brokers and lots on colour roles`. Dopo la base merge
> (ruoli nuovi di T, `f043c1b58`): BK-4 su `text-lf-on-overlay`.

### S5b — Mini-checkpoint dopo la base merge: BK-4 e verifica di `SIGN_BADGE` ✅ (16/10/2026, inviato ~12:10; FROZEN)
Richiesta del coordinatore (12:03): `api sync`; BK-4 con `text-lf-on-overlay`; vedere se i badge dei lotti con un segno
(BK-2) vanno su `SIGN_BADGE`.
> **Note implementazione**: L1–L3 committati dal coordinatore in `82f304f4a`, base merge `2eef01e59` (HEAD verificato,
> albero pulito).
> - **BK-4:** `BrokerForm`, l'icona `Upload` sullo scrim `bg-lf-overlay`: `text-white` → `text-lf-on-overlay` (bianco nei
>   due temi, provvisorio). `BrokerForm` 5 → 4: resta solo l'interruttore (BK-3).
> - **`SIGN_BADGE` (`bg-lf-gain-soft text-lf-gain-on-soft` / `loss`):** nessun badge di BK-2 dice un guadagno o una
>   perdita. LONG/SHORT (`directionCell`, smeraldo/rosa con le frecce) è la direzione della posizione, non il segno di un
>   numero finanziario (regola 7 della skill: P&L, rendimento, variazione di prezzo); una posizione corta non è una
>   perdita. In più quei badge hanno un bordo e `SIGN_BADGE` non ha un ruolo di bordo (niente `gain-line`). Gli altri
>   sono stati del lotto (aperto, parziale, chiuso, distribuito, in transito, degradato: nei grafici il colore viene da
>   `LOT_STATE_COLORS`, cielo/ambra/ardesia) o categorie (custodia, in transito, marcatori della custodia). Restano tutti in
>   BK-2, per il giro dei badge.
> - **Prove** (12:06–12:09, `bk_mini_gates.sh` della sessione, nice, carico < 50 all'avvio): `api sync` exit 0; `--check`
>   pulito (1 file sotto il record) → `--update` **m1 7.441 → 7.440**, m2 54 → 54 → `--check` pulito; Vitest dei gate
>   `themeRoles`, `themeTokens`, `themeComponentTokens` 84/84; `BrokerModal.test.ts` (monta il form) 15/15; Prettier
>   pulito su `BrokerForm`; `git diff --check` pulito; controllo «solo scuro» 0.

### S6 — Slot pesante L1–L3 ✅ (16/10/2026, 14:15–14:46, verde)
> **Stato** (12:13): L1–L3 committati in `82f304f4a`, base merge `2eef01e59`, mini-checkpoint BK-4 in `cb1fb5690`
> (HEAD verificato, albero pulito). Il coordinatore concorda: LONG/SHORT resta in BK-2.
> **Vincoli della 1.3 sui due file delle pagine:** Z-13 e Y11 toccano subito lo `<script>` di
> `routes/(app)/brokers/+page.svelte` e di `routes/(app)/brokers/[id]/+page.svelte`; Y11 tocca anche i loro bottoni
> «Aggiorna», ma dopo l'ingresso di BK. Da qui: né lo `<script>` né quei bottoni.
> **Preparazione fuori slot** (OK del coordinatore, 12:14: uno alla volta, `nice`, carico a 1 minuto < 50, nessun server
> né porta, populate solo nella mia cartella): `front build --debug`, `mkdocs build`, `test --test-port 6158 --data-dir
> /tmp/librefolio-r2-bk db populate --force --clean --with-reports` (script `bk_prep_slot.sh` della sessione). Lo slot
> gira sulla base attuale: gli ingressi di AF non toccano l'area; la base merge la fa il coordinatore all'ingresso.
> ✅ **Preparazione fatta** (12:18–12:25, HEAD `cb1fb5690`, ciascun passo avviato a carico < 50):
> - `front build --debug`: exit 0 in 213 s; il suo svelte-check: **0 errori, 0 avvisi** (vale come `front check` su
>   quest'albero: nello slot non lo ripeto, salvo una base merge);
> - `mkdocs build`: exit 0 in 144 s, 3.076 URL relativi risolti;
> - `db populate --force --clean --with-reports` nella corsia: exit 0 in 31 s (istantanea della DB in `.testLog/00_archive/`,
>   ignorata da git).
> Script dello slot pronto (`bk_slot_l1l3.sh`): `api sync`, poi le E2E in ordine di priorità (broker list, detail,
> condivisione, create-feedback, recovery, data-quality legacy e real, multi-user, privacy), poi le tre Vitest del runner;
> smette di avviare passi dopo 42 minuti e dice cosa resta.
> ✅ **Slot fatto** (16/10, 14:15:13–14:46:31, 31 min, su `cb1fb5690`, corsia 6158 + `/tmp/librefolio-r2-bk`; senza `nice`,
> nessun passo dopo le 14:55 per il taglio del coordinatore):
> - `api sync`: exit 0;
> - E2E, **94/94**: `front-broker list` 9, `detail` 37, `broker-create-feedback` 2, `broker-recovery` 5;
>   `front-user broker-sharing` 17, `multi-user` 2; `front-portfolio data-quality-legacy` 1, `data-quality-real` 3,
>   `privacy-masking` 18. Nessun flaky, nessun tentativo ripetuto;
> - Vitest del runner: `component-unit` 154 file, 4.027/4.027; `onboarding-component-unit` 15 file, 449/449; `core-unit`
>   179 file, 6.406/6.406;
> - `front check`: lo svelte-check della build debug delle 12:18 sullo stesso albero, 0 errori e 0 avvisi;
> - fine: nessun listener sulla 6158 (`lsof`), albero pulito a parte questo piano.
`api sync`; `front build --debug` e `mkdocs build` se mancano; `db populate --force --clean` sulla corsia se vuota;
`front check`; `front-utility core-unit`, `component-unit`, `onboarding-component-unit`; E2E
`front-broker list|detail|broker-recovery|broker-create-feedback`, `front-user broker-sharing|multi-user`,
`front-portfolio data-quality-legacy|data-quality-real|privacy-masking`. Server spento, porta 6158 libera.

### S7 — L4 · modale di custodia ✅ (16/10/2026 sera; committato in `16087f0fd`, slot verde)
> **Nota del coordinatore (17:54, da G-18):** `lot-custody-modal > div` è un elemento misto composto a runtime:
> `ModalBase` mette `border border-lf-raised text-lf-primary {contentClass}`, `LotCustodyModal` gli passa
> `contentClass="bg-white dark:bg-slate-800"`. In scuro vince la regola legacy `html.dark .bg-white { … !important }`
> (slate di prima) sul `background: var(--lf-surface-card)` dello `<style>` di `ModalBase`. In L4: via quel fondo dalla
> prop (`ModalBase` dà già la superficie card); un fondo diverso solo con un ruolo. Si vede negli scatti `brokers` e
> `dashboard/fifo-lots-custody-modal`.
`LotCustodyModal` dalla versione di Y — 205 → 20: `contentClass` di `ModalBase` senza colore (o `bg-lf-card`);
commissioni e tasse `text-lf-loss`; riga selezionata dello storico `border-lf-checked bg-lf-selected`; restano i
marcatori degli eventi e le icone «in transito».
> **Note implementazione** (16/10, sera): via del coordinatore alle 19:58. Y è entrato (`0c79932a7`); HEAD `855227a26`
> (nota G-18 committata in `2db15d1c5`, poi base merge), pulito. Analisi breve mandata al coordinatore, poi lavoro diretto
> (1:1, nessuna scelta di design).
> - 37 sostituzioni di stringhe esatte, ognuna col suo conteggio atteso (`bk_l4_apply.mjs` della sessione: scrive solo
>   se tutti i conteggi tornano). **m1 205 → 20**, m2 0, G1–G4 0, scan «stessa proprietà» 0.
> - Il misto di G-18: via `contentClass="bg-white dark:bg-slate-800"` dalla chiamata a `ModalBase`.
> - Card delle metriche e righe di custodia `bg-lf-panel`; etichette `text-lf-muted`; valori `text-lf-primary`; bordi,
>   divisori e vuoti tratteggiati `border-lf-subtle`; chiudi `text-lf-muted hover:bg-lf-hover hover:text-lf-secondary`;
>   «Chiudi» del piede `bg-lf-panel text-lf-secondary hover:bg-lf-neutral`; azione primaria sui ruoli d'azione; info
>   `hover:text-lf-link`; riga dello storico `{attiva ? 'border-lf-checked bg-lf-selected' : 'border-lf-subtle bg-lf-card
>   hover:bg-lf-hover'}`; nota «stimato al costo» `text-lf-warning`; chip degli stati `bg-lf-success-soft
>   text-lf-success-on-soft`; commissioni e tasse `{SIGN_TEXT.portfolio.loss}`.
> - Restano (BK-2): i 4 marcatori degli eventi (16) e le 2 icone «in transito» (4).
> - Nessun test legge i colori: `LotCustodyModal.test.ts` (Y), `brokers-detail.spec.ts`, `privacy-masking.spec.ts`
>   leggono test id e testi. `moneyRenderSites` non registra righe di questo file, e le righe cambiate non hanno template
>   né `style: 'currency'`.
> - Da rivedere: chip degli stati tutte in verde successo (anche CLOSED e DEGRADED: l'aspetto di oggi); vuoti tratteggiati
>   da `slate-300` a `subtle`, più chiari.
> - **Prove** (20:03–20:09, `bk_l4_gates.sh` della sessione, nice, carico < 50 all'avvio): `api sync` exit 0 (la base
>   porta Y12a e il nuovo `original_cost`); `dark_only_check` 0; `native_field_check` 0; `--check` pulito; Prettier: la
>   base era pulita, `--write` ha solo rimesso su una riga il ternario dello storico; `--update` **m1 930 → 745**, m2 2 → 2;
>   `--check` pulito; Vitest dei gate `themeRoles`, `themeTokens`, `themeComponentTokens`, `moneyRenderSites` 125/125;
>   `vitest run src/lib/features/brokers/lots/` 12 file, 554/554 (con `LotCustodyModal.test.ts` di Y); `front check`
>   (svelte-check) 0 errori, 0 avvisi; `git diff --check` pulito.
> - **Commit e slot:** checkpoint committato dal coordinatore in `16087f0fd`, base merge `f4eeb3b63` (record della 1.3,
>   niente frontend). Preparazione fuori slot (20:11–20:17, nice, carico < 50): `front build --debug` 243 s, `mkdocs
>   build` 83 s; `api sync` non ripetuto nello slot, perché un `generated.ts` nuovo avrebbe fatto rifare la build al
>   runner (era successo nello slot L1–L3). **Slot L4 verde** (20:16:52–20:24:06, 7 min, corsia 6158, un worker, build
>   trovate aggiornate): `front-broker detail` 38/38, `front-portfolio privacy-masking` 18/18, `front-broker list` 9/9
>   (**65/65**), nessun flaky; alla fine nessun listener sulla 6158.

### S8 — Consegna finale ⏳

## Definizione di fatto

- m1 dell'area 1.153 → 160, m2 0; `--check` pulito e baseline stretto con `--update`; gate `themeRoles`, `themeTokens`
  (C4 compreso), `themeComponentTokens` e `moneyRenderSites` verdi. **Raggiunto il 16/10 sera: 1.153 → 159** (una in
  meno della stima: BK-4 chiuso con `text-lf-on-overlay` di T); restano BK-1 69, BK-2 84, BK-3 4, BK-5 2, tutte annotate.
- Nessun elemento misto, nemmeno a runtime (catene di classi controllate); nessuna coppia della stessa proprietà fuori
  da un ternario.
- Prove leggere verdi per ogni lotto; slot pesante verde.
- Piano aggiornato a ogni passo; voci BK-n nel backlog; nessun server acceso alla consegna.
