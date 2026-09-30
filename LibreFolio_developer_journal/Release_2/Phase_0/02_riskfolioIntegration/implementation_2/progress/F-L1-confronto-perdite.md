# F — L1° di Asset Global, «Quanto ha fatto male ciascuno?» · piano vivo

> Nato da [F-laboratorio-postmerge.md](F-laboratorio-postmerge.md), sezione «Dopo il checkpoint 4», dove il
> componente è stato scelto (proposta di F, accettata da Risk, approvata dal developer il 2026-09-30).

## Coordinate

| | |
|---|---|
| Worktree | `e-alfy-super-dollop`, ramo `e-alfy-risk-asset-global-lab` |
| Base | `b26ca6e29` (guida D1 `73ba9f08e` + journal D2), sopra `881941e44` = punta di Risk validata |
| Corsie | 6154 per le suite (`/tmp/librefolio-r2-f`), 6164 per la copia di prod (`/tmp/librefolio-r2-f-prodcopy`) |
| Coordinamento | Risk (`0000738d-…`) per il giro; il coordinatore (`c8328a01-…`) per i file fuori famiglia |
| Sessione | rinominata «F - Confronto perdite Asset Global» |

## Decisioni del developer (ask_user, 2026-09-30, ~11:00 e ~11:25), alla lettera

> «si partiamo con l1 di asset global. il primo punto ok. il secondo in realtà l'icona va bene, il manuale è per tutta
> la card, ma mi aspetto che ci sia solo il tooltip, mentre per andare alla documentazione clicco sul manuale in alto.
> riguardo il 3° io i nomi degli asset li vedo con le icone, sei sicuro, piuttosto vanno a capo invece di scorrere, ed in
> oltre non usiamo la tabella nostra custo e ottimizzata, ma una css. […] fai bene le tue analisi, usa già questi
> feedbacke per aiutarti e creami anche un ascii art di come pensi di modificarlo»

> «se il tooltip c'è già senza info, va bene, possiamo riusare il codice pre-esistente. riguardo i nomi ho frainteso la
> domanda, grazie per aver controllato, hai ragione, mancano le icone degli asset. […] Riguardo l'ascii art dire di sì,
> con le modifiche date da questo feedback»

**Disegno approvato**:
- il `DataTable` del progetto al posto della tabella HTML scritta a mano;
- ordinamento con un clic sull'intestazione;
- tooltip sul titolo della colonna col codice che c'è già (`headerTooltip` senza URL): **niente ⓘ e niente link**. La
  documentazione resta sul manuale della cornice, in alto;
- icona del tipo più nome su una riga, che scorre se non ci sta, come nella lista Asset.

**Il nodo di calcolo** («mese storto» = 21 osservazioni, «giornata» diluita dai weekend): è del motore, di Risk, che porta
la cura al developer nella sua sessione. In L1° nessun numero cambia. Vincolo di Risk: il tooltip del «mese» non scrive
«21 osservazioni» a mano; si usa una frase neutra.

## Fatti verificati (base `b26ca6e29`)

- `AssetSetLossComparisonSection.svelte`:
  - `<table>` scritta a mano (`:127`), nome in testo nudo `{row.name}`;
  - intestazioni con `<a href=…>ⓘ</a>` verso la teoria (`:135`), che il gate dei link non riesce a leggere: esce come
    `🔵 {column.docs} … resolved at runtime`;
  - nessun ordinamento, ma il docblock (`:19`) lo promette.
- I nomi vengono da `selectionLabels` (`AssetSetRiskPanel.svelte:363-366`, id → `display_name`).
- Snapshot del developer (sola lettura, solo conteggi):
  - 15 asset; 11 nomi con un'emoji, 10 all'inizio;
  - 10 nomi oltre i 30 caratteri;
  - 0 `icon_url` propri.
  → Le «icone» viste erano emoji; l'icona del tipo manca.
- `DataTable` (`components/table/`):
  - `ColumnDef` ha `sortable`, `sortFn`, `getValue`, `headerTooltip`, `pinned` e `align`;
  - un clic ordina in crescente, il secondo in decrescente, il terzo toglie l'ordine;
  - i valori mancanti restano in fondo in entrambi i versi (`compareRowsByColumn`);
  - le celle `html` vanno in `{@html}` senza sanificazione → `escapeHtml` (`utils/core/escapeHtml.ts`);
  - `<tr data-row-id>`, `th[data-testid="dt-header-{id}"][data-sort]`, `[data-testid="dt-sort-{id}"]`;
  - con solo `headerTooltip`, il `Tooltip` avvolge il pulsante del titolo; l'icona `dt-header-tooltip-{id}` compare solo
    con un URL.
- `AssetTable.svelte:136-148` è il modello del nome: icona più span `overflowScrollTextClass`
  (`utils/overflowScroll.ts:16`) più `attachOverflowMarqueeToDescendants` in `onMount`.
  - Lì il nome non è escapato: reperto dato al coordinatore, che l'ha passato a K (Step 13, voce 0).
- `plainName` (`correlationHelpers.ts:227`): il nome senza emoji, lo stesso di «Per nome» della matrice (V6).
- Il gate dei link legge anche i commenti (`docsPath` fra apici, `/mkdocs/…`): nel codice nuovo nessun commento del genere.

## Contratto (per i test e per il codice)

- `AssetSetLossComparisonSection` riceve una prop nuova, `assetIcons: ReadonlyMap<number, string>` (id → URL
  dell'icona). `AssetSetComparisonLevels` la inoltra; il pannello la costruisce con la regola del chip:
  `icon_url || getAssetTypeIconUrl(asset_type)`.
- Il contenitore `data-testid="risk-asset-set-l1-table"` porta `data-row-count` e contiene il `DataTable`, con:
  - niente selezione, azioni, filtri, paginazione, visibilità delle colonne né menu contestuale; l'ordinamento sì;
  - `storageKey` `risk-asset-set-l1`.
- Colonne: `name`, `badDay`, `badMonth`, `worstFall`, `currentFall`, `toPeak`.
  - `name` è fissata a sinistra e ordina con `plainName`, a parità di nome per id.
  - Le cinque colonne dei valori hanno `headerTooltip` =
    `risk.assetSet.levels.l1.columnHelp.<col>`; `name` non ne ha.
  - I valori ordinano per il numero col segno mostrato, quindi in crescente la perdita più grande va prima.
- All'apertura le righe seguono l'ordine di `assetIds`.
- Cella del nome: `[data-testid="risk-asset-set-l1-name"][data-asset-id]`, che contiene:
  - `img[data-testid="risk-asset-set-l1-icon"]`, se c'è l'URL;
  - uno span `overflow-scroll-marquee` con il nome escapato.
- Celle dei valori, con i testid di oggi: `[data-testid="risk-asset-set-l1-<col>"][data-measured]`.
  - Il segno meno è U+2212; `+` per `toPeak`; `—` quando manca.
  - `worstFall` porta `data-recovery` e, se c'è, `risk-asset-set-l1-worstFall-days`.
- Restano come oggi: gli stati (errore, caricamento, risposta scartata, vuoto) e la nota dei trattini.
- Via, rispetto a oggi: `risk-asset-set-l1-row` (le righe si leggono da `tr[data-row-id]`) e `risk-asset-set-l1-docs-*`.

## Passi

| # | passo | stato |
|---|---|---|
| L1-0 | piano nel journal, rimando incrociato | ✅ 2026-09-30 |
| L1-1 | test rossi prima (test-author): unitari in jsdom subito, E2E `risk-lab` dopo il RESUME del venv | ✅ 2026-09-30 (unitari rossi; E2E scritto, da lanciare) |
| L1-2 | codice: sezione → `DataTable`, icone dal pannello, `escapeHtml`, `plainName`, tooltip, scorrimento, docblock | ✅ 2026-09-30 |
| L1-3 | 5 chiavi `risk.assetSet.levels.l1.columnHelp.*` nelle 4 lingue via `dev.py i18n` (dopo il RESUME) | ✅ 2026-09-30 |
| L1-4 | cancelli: prettier, `front check`, vitest, `front-utility`, orfani, `i18n audit`, `check-links`, `front build --debug`, E2E | ✅ 2026-09-30 |
| L1-5 | review del developer sulla 6164, con una copia di prod fresca | ✅ 2026-09-30 (terzo giro: «Va bene così») |
| L1-6 | checkpoint a Risk | ✅ 2026-09-30 (committato: `76fd7f208` … `1b62abd2e`) |

## Definizione di finito

- Il developer approva sulla 6164.
- Tutti i cancelli verdi, uno per volta nella corsia 6154.
- Nessun importo in euro.
- Nessun link nelle intestazioni, e `{column.docs}` sparito dai «Not verifiable» di `check-links`.
- Nomi su una riga, con l'icona del tipo; ordinamento funzionante.
- All'apertura l'ordine della selezione; i trattini sempre in fondo.

## Esecuzione

### L1-0 · piano ✅ 2026-09-30, 11:55

> **Note implementazione**:
> - Base verificata: HEAD `b26ca6e29`, albero pulito; i blob di D1 e D2 coincidono con quelli consegnati; `sw.js` al
>   timbro committato.
> - Pausa del venv condiviso chiesta dal coordinatore (11:52): niente Python fino al RESUME, quindi niente `dev.py`.
>   Si lavora sul frontend con i binari Node locali: vitest, prettier, svelte-check.

### L1-1 · test rossi prima ✅ 2026-09-30, 12:00–12:40 (test-author `l1-datatable-tests`)

> **Note implementazione**:
> - `AssetSetLossComparisonSection.test.ts`: fixture con `assetIcons`, `rowOf` indipendente dal layout, casi nuovi
>   `:612-838`. Coprono:
>   - la struttura e l'ordine d'apertura;
>   - la tabella a 12 righe, senza paginazione, filtri o azioni;
>   - `storageKey`;
>   - le intestazioni senza link e senza ⓘ;
>   - i 5 tooltip legati alle chiavi `columnHelp`, e nessun tooltip sul nome;
>   - le chiavi presenti nei 4 cataloghi;
>   - l'icona sì e no, lo span che scorre;
>   - l'escaping (`<b>`, `<img onerror>`, `SPDR® S&P 500®` contro il doppio escaping);
>   - le celle dei valori;
>   - l'ordinamento delle quattro perdite, di `toPeak` e del nome (emoji ignorate, parità per id).
> - `AssetSetComparisonLevels.test.ts`: `assetIcons` nelle props; la riga si cerca senza `risk-asset-set-l1-row`.
>   10 su 10 restano verdi.
> - **Rosso sul componente attuale** (vitest via Node, durante la pausa del venv): **25 rossi**, tutti sul contratto
>   nuovo, più **21 verdi** (i casi che non cambiano). I 4 della presenza nei cataloghi restano rossi fino a L1-3.
> - **Prova che i test possono diventare verdi**: test-author ha scritto una versione usa e getta del componente in
>   `/tmp` e ci ha lanciato gli stessi test: 42 su 46, con rossi solo i 4 dei cataloghi. Poi ha provato 14 mutanti,
>   presi tutti. Fra questi: ordine per il valore positivo grezzo, trattini in testa in decrescente, nomi senza parità
>   per id, escaping mancante o doppio, paginazione accesa, un link in intestazione, righe già ordinate all'apertura.
> - **E2E `risk-lab.spec.ts`**, scritto e non lanciato:
>   - localizzatori `lossRows`, `lossRow`, `lossRowAssetIds`, `lossCell` e `lossNameCell` (`:1808-1842`);
>   - via `risk-asset-set-l1-row` (`:3351`, `:3412-3413`, `:3840`). Il `:3840` sarebbe passato a vuoto col layout nuovo;
>   - intestazioni senza link, con il tooltip al passaggio (`:3541`);
>   - ordinamento su `badDay` (`:3581`), con l'opzione di stub `zigzagBadDay` definita nello spec, non in `risk-mocks.ts`;
>   - cella del nome con l'icona e `white-space: nowrap` (`:3659`).
>
> ⚠️ **Fuori pista**:
> - **Venv condiviso**: congelato e ripreso due volte dal coordinatore (11:52 → RESUME, poi FREEZE e RESUME). Durante il
>   secondo giro non girava niente di Python dalla mia corsia, come ha verificato lui.
> - **Rosso dell'E2E sul codice vecchio**: non è più provabile, perché il codice nuovo arriva prima dei comandi Python.
>   La prova si farà dopo, con mutanti temporanei nella corsia 6154, come per C1b.

### L1-2 · il codice ✅ 2026-09-30, 12:45–13:05

> **Note implementazione**:
> - `correlationHelpers.ts`: nuovo `nameComparator(locale?)`, lo stesso confronto di `nameOrder` (collator
>   `sensitivity: 'base'`, `numeric`, `plainName`), che ora lo usa. La colonna «Asset» e il «Per nome» della matrice
>   non possono più divergere. Comportamento invariato, coperto dai test di `nameOrder`.
> - `AssetSetLossComparisonSection.svelte`:
>   - la `<table>` scritta a mano diventa `DataTable`, senza selezione, azioni, filtri, paginazione, visibilità delle
>     colonne né menu contestuale; `storageKey` `risk-asset-set-l1`;
>   - le colonne sono costruite con `lossColumn()`. `getValue` = la perdita come è disegnata (`drawnLoss`, negativa),
>     quindi in crescente la perdita più grande va prima; `null` resta in fondo;
>   - `name`: `pinned: 'left'`, `sortFn` = `nameComparator` più l'id;
>   - `headerTooltip` sulle 5 colonne dei valori; nessun `headerTooltipUrl`, nessun link;
>   - celle `html` con i testid e `data-measured` di prima; nome e testi passano da `escapeHtml`;
>   - icona `risk-asset-set-l1-icon` e span `overflowScrollTextClass`, con `attachOverflowMarqueeToDescendants` sul
>     contenitore;
>   - docblock aggiornato: l'ordinamento ora esiste davvero, si apre nell'ordine della selezione, niente link nei titoli.
>     Nessun percorso di documentazione nei commenti, perché il gate legge anche quelli.
> - `AssetSetComparisonLevels.svelte`: la prop `assetIcons` passa alla sezione.
> - `AssetSetRiskPanel.svelte`: `selectionIcons`, con le stesse fonti delle etichette e la regola del chip
>   (`icon_url || getAssetTypeIconUrl(asset_type)`); un id sconosciuto resta senza icona. Rimesso l'import di
>   `getAssetTypeIconUrl`.

### L1-3 · chiavi i18n ✅ 2026-09-30, 13:05

> **Note implementazione**: 5 chiavi `risk.assetSet.levels.l1.columnHelp.{badDay,badMonth,worstFall,currentFall,toPeak}`
> via `dev.py i18n add`, nelle 4 lingue (script `/tmp/libreFolio_f4/l1_i18n_add.sh`); +7 righe per catalogo.
> - I termini sono quelli delle etichette esistenti.
> - Il tooltip del «mese» è neutro sulla durata, come chiede Risk: «su un tratto più lungo di giorni consecutivi», niente
>   «21 osservazioni», perché la durata cambierà con la cura del motore.

### L1-4 · cancelli, prima parte · 2026-09-30, 13:05–13:15

> - vitest sui 23 percorsi del laboratorio: **23 file, 825 test**, tutti verdi (erano 771), compresi i 4 controlli dei
>   cataloghi e il cablaggio dei tooltip.
> - prettier: 2 file da riformattare (la sezione, e lo spec che test-author non poteva formattare durante la pausa) →
>   `--write`, poi pulito.
> - `dev.py front check`: 3 errori e 41 avvisi in 4 file, il pavimento noto; nessuno nei miei file.
> - `dev.py front build --debug`: marcatore `1`, nessun file tracciato toccato.
> - E2E `risk-lab` (6154): **25 ⇒ 25** in 49,7 s, cioè i 22 di prima più 3 nuovi. Porta libera prima e dopo.

### L1-4 · prova dei 3 E2E nuovi con mutanti ✅ 2026-09-30, 13:15–13:25 (test-author `l1-e2e-mutants`, corsia 6154 in esclusiva)

> **Note implementazione**: tre mutanti insieme nella sezione, una sola build di debug.
> - M1: un `headerTooltipUrl` su `badDay`.
> - M2: `badDay` ordinata per la grandezza positiva grezza.
> - M3: via l'icona e la classe di scorrimento.
>
> Corsa rossa: **22 passati, 3 falliti**, ognuno sulla sua asserzione:
> - intestazione (`:3552`): «a link in L1°'s header row», con `thead a` 1 invece di 0;
> - ordinamento (`:3642`): crescente `[1,3,5,7,2,4,6,17]` invece di `[6,4,2,7,5,3,1,17]`, con l'asset non misurato
>   sempre ultimo;
> - cella (`:3676`): «no type icon beside the name».
>
> Ripristino byte per byte: sha256 `c9c2ba62…` prima e dopo, `cmp` identico. Poi build e corsa verde: **25 ⇒ 25** in
> 57,8 s. 6154 libera prima, fra una corsa e l'altra, e dopo. Log in `/tmp/l1mut_*`.
>
> ⚠️ **Fuori pista — prova incompleta sul caso della cella**: il test si è fermato all'icona, quindi l'asserzione
> `white-space: nowrap` (`:3682`), quella dell'osservazione del developer sui nomi a capo, non è stata provata da sola. Serve un
> quarto mutante: solo `whitespace-nowrap` → `whitespace-normal`, con icona e marcatore intatti.

> ✅ **Quarto mutante (13:30–13:35, io, script `/tmp/libreFolio_f4/l1_mutant4.sh`)**: solo `whitespace-nowrap` →
> `whitespace-normal` nella cella del nome, con icona e marcatore intatti.
> - Rosso: **24 passati, 1 fallito**, il caso della cella a `:3682`: «the name wraps instead of scrolling», atteso
>   `nowrap`.
> - Ripristino identico: sha256 `c9c2ba62…`.
> - Build e corsa verde: **25 ⇒ 25** (49,5 s). 6154 libera.
>
> Tutte e quattro le promesse dei 3 casi nuovi sono provate capaci di fallire.

### L1-4 · cancelli, seconda parte ✅ 2026-09-30, 13:35–13:50 (script `/tmp/libreFolio_f4/l1_gates.sh`, uno per volta)

> - `front-utility core-unit`: **103 file, 2843 test**. `front-utility component-unit`: **89 file, 2187 test** (erano
>   2161).
> - `test check-orphans`: exit 0, ogni test registrato è raggiungibile.
> - `i18n audit`: **3491 chiavi** (3486 della base più le 5 nuove), nessuna traduzione mancante.
> - `mkdocs check-links`: exit 0, **83 validi** (invariato); **non verificabili da 9 a 8**, perché `{column.docs}` è
>   sparito: il buco del gate è chiuso togliendo il link, come deciso dal developer. 3 ancore note.
> - E2E `risk` (Dashboard di A, che usa `correlationHelpers`): **13 ⇒ 13**.
> - 6154 libera alla fine.
> - Non lanciati, perché non toccati: `risk-asset-detail` (Asset Detail) e `asset-list` (tab Asset).

### L1-5 · review del developer sulla 6164 · 2026-09-30, dalle 13:55

> **Preparazione**:
> - copia di prod fresca in `/tmp/librefolio-r2-f-prodcopy` (`app.db` sha `5c0a681bc4e4b59c`, uguale alla snapshot);
> - server `dev.py server --test --port 6164 --data-dir /tmp/librefolio-r2-f-prodcopy`, shell `l1server`, PID 13812.
>
> **Primo giro (ask_user), alla lettera**: «bisogna aumentare lievemente la larghezza minima di sotto il massimo e
> risalita dal massimo, ma la tabella ora è mooolto meglio. modificherei poi "La stessa scala del danno, chiesta a ogni
> asset selezionato. Solo percentuali: un insieme di asset non ha pesi, quindi non c'è un importo da affiancare." è troppo
> informativa lato dev, serve una frase che faccia capire il contenuto della tabella».
>
> **Note implementazione**:
> - I titoli del `DataTable` vanno a capo quando non ci stanno (nessun `nowrap` in `.header-sort-btn`).
>   - `currentFall` e `toPeak` passano da 120/90 a **150/120** px (`WIDE_VALUE_*`): hanno i titoli più lunghi in ogni
>     lingua; in francese il più lungo è «Hausse jusqu'au sommet».
> - `risk.assetSet.levels.l1.description` riscritta via `dev.py i18n update`, nelle 4 lingue, perché dica cosa c'è nella
>   tabella. IT: «Per ogni asset selezionato, quanto ha perso nei momenti peggiori del periodo: la giornata storta, il
>   mese storto, la discesa più profonda e quanto è ancora sotto il suo massimo.»
>   - La guida utente non citava la vecchia frase, quindi non cambia.
> - prettier pulito; vitest su 3 file, 57 test; `front build --debug` (marcatore `1`); la 6164 serve la build nuova.

> **Secondo giro (ask_user), alla lettera**: «in italiano va bene, ma in francese non è ancora abbastanza la larghezza delle
> colonne, in oltre manca il bottone per riordinare le colonne, lo metterei accanto al manuale».
>
> **Larghezze, la causa**: i titoli del `DataTable` sono `white-space: nowrap`, in maiuscolo e spaziati
> (`DataTable.svelte:1575-1586`).
> - Con `table-layout: fixed`, un titolo lungo come «HAUSSE JUSQU'AU SOMMET» esce dalla colonna invece di andare a capo.
> - **Cura, valida per ogni lingua**: `tableLayout="auto"`, già usato da `DistributionEditor`, `MeasurePanel` e
>   `ImportWizardModal`. Ogni colonna è larga almeno quanto il suo titolo; le larghezze restano solo come minimi (110/90),
>   e via le costanti speciali del primo giro.
> - Il contenuto della cella del nome ha un tetto (`max-w-56`): in un layout `auto` il nome più lungo, che non va a capo,
>   fisserebbe la larghezza della colonna invece di scorrere.
> - Se in una lingua la tabella supera la card, il contenitore del `DataTable` scorre in orizzontale
>   (`.table-wrapper { overflow-x: auto }`) e la colonna Asset resta ferma.
>
> **Il bottone per riordinare le colonne** è l'occhio delle nostre tabelle, `table/ColumnVisibilityToggle.svelte`
> (mostra, nasconde e riordina). Accanto al manuale vuol dire nella testata della cornice (`RiskLevelSection`, di Risk),
> che non aveva un aggancio per le azioni.
> - **Permesso di Risk (14:1x), una tantum**, solo per questa aggiunta, su `levels/RiskLevelSection.svelte` e
>   `RiskLevelSection.test.ts`. Condizioni:
>   1. solo additiva: `actions?: Snippet` facoltativa, subito prima di `DocsLink`, nella stessa riga, nei due rami;
>      senza la prop il DOM resta identico e i test esistenti verdi senza ritocchi;
>   2. fuori dal pulsante che richiude la sezione: niente `<button>` dentro un `<button>`, e un clic sull'occhio non apre
>      né chiude;
>   3. test prima, con test-author;
>   4. nel checkpoint anche l'E2E `risk`: la cornice la monta la Dashboard di A.
> - Fatta l'aggiunta, il file torna a Risk.

> **Test rossi prima** (test-author `l1-actions-tests`), sui file `RiskLevelSection.test.ts`, prestato da Risk, e
> `AssetSetComparisonLevels.test.ts`:
> - **12 casi nuovi rossi** sul codice di prima, per le ragioni giuste: la cornice ignorava `actions`, e l'occhio non
>   c'era. Sono verdi, com'era giusto, i test esistenti e i casi di invarianza «senza `actions` il DOM non cambia», che
>   fissano la forma della testata nelle quattro combinazioni.
> - E2E `risk-lab` (`:3714`), scritto senza lanciarlo:
>   - l'occhio sta nella testata di L1°, prima del manuale e sulla stessa riga; in L3° non c'è;
>   - spegnere `badMonth` toglie titolo e celle, e riaccenderlo li rimette al loro posto.
> - ⚠️ **Fuori pista**: test-author ha lanciato `python3` una volta, per una sostituzione di testo nel suo file (niente
>   `dev.py`, niente venv), e l'ha dichiarato lui.
>
> **Note implementazione (14:20–14:40)**:
> - `levels/RiskLevelSection.svelte` (permesso una tantum di Risk): nuova prop `actions?: Snippet`.
>   - Ramo richiudibile: fra il pulsante e `DocsLink`, fuori dal pulsante.
>   - Ramo fisso: un contenitore `flex` con le azioni e `DocsLink`, che compare **solo** quando le azioni ci sono.
>   - Senza la prop il DOM resta identico. Il file torna a Risk.
> - `AssetSetLossComparisonSection.svelte`: prop `tableRef = $bindable()`, legata al `DataTable` con `bind:this`; tolto
>   `enableColumnVisibility={false}`, che il `DataTable` non legge e che ora sarebbe falso.
> - `AssetSetComparisonLevels.svelte`: `lossTable` (`$state`) legato alla sezione; la cornice di L1° riceve
>   `actions={lossTable ? lossActions : undefined}`, con `<ColumnVisibilityToggle tableRef={lossTable} />`. L'occhio c'è
>   solo quando c'è la tabella.
> - La lettura letterale di test-author, «l'occhio anche con una tabella senza cifre», è accettata.
>
> **Cancelli (14:40–14:55)**:
> - vitest: 3 file, 70 test, poi i 24 percorsi del giro (i 23 più `RiskLevelSection.test.ts`): **24 file, 849 test**;
> - prettier pulito dopo `--write` sulla sezione; `front check` al pavimento (3 errori e 41 avvisi in 4 file non miei);
> - `front build --debug`;
> - E2E `risk-lab` **26 ⇒ 26** ed E2E `risk` **13 ⇒ 13** (condizione 4 di Risk); 6154 libera.
>
> ⚠️ **Da fare prima del checkpoint**: provare con un mutante che l'E2E dell'occhio sa fallire. Non adesso: la 6164 del
> developer e la 6154 servono la stessa `frontend/build`, e una build mutante finirebbe sotto i suoi occhi.

> ✅ **Terzo giro (ask_user, ~15:00)**: il developer sceglie **«Va bene così»**. Larghezze in ogni lingua e occhio accanto
> al manuale approvati. **L1° approvato.**

### L1-4 · mutante dell'occhio e cancelli finali ✅ 2026-09-30, 15:00–15:25

> - **Mutante** (`/tmp/libreFolio_f4/l1_mutant5.sh`), fatto dopo aver spento la 6164: la cornice di L1° non riceve più le
>   azioni (`actions={undefined}`).
>   - Rosso: **25 passati, 1 fallito**, il caso dell'occhio (`:3714`, «L1°'s frame offers no column toggle»).
>   - Ripristino identico (sha256 `9cf05b19…`); build e corsa verde: **26 ⇒ 26**.
> - **Cancelli finali** (`/tmp/libreFolio_f4/l1_final_gates.sh`, uno per volta, nella 6154):
>   - `front-portfolio risk-levels-component`, la categoria di `RiskLevelSection.test.ts`: 3 file, 36 test;
>   - `front-utility core-unit`: 103 file, 2843 test; `component-unit`: **89 file, 2194 test**;
>   - `check-orphans`: pulito;
>   - `i18n audit`: 3491 chiavi, tutte tradotte;
>   - `check-links`: 83 validi, **8 non verificabili** (erano 9);
>   - `git diff --check`: pulito;
>   - 6154 e 6164 libere.
> - **OK dati a Risk (15:1x)**: il suo test-author, nel suo ramo, aggiunge `horizon_observations` e porta il mese a 30
>   giorni in `risk-lab.spec.ts:684-697` e `:3300`, `AssetSetComparisonLevels.test.ts:122-135`,
>   `AssetSetLossComparisonSection.test.ts:105-121` e `assetSetLevels.test.ts` (`:94`, `:98-105`, `:229`, `:594`).
>   - Prima di dare l'OK ho verificato che i miei blocchi siano a ≥ 2 righe invariate da ogni intervallo;
>     `assetSetLevels.test.ts` non l'ho toccato.

## Scheda di L1° per la review del Tempo ② (Asset Global, in %)

| | |
|---|---|
| **Domanda** | «Quanto ha fatto male ciascuno?»: la stessa scala del danno per ogni asset scelto. Giornata storta, mese storto, peggior discesa con la sua durata, quanto è sotto il massimo, quanto deve risalire |
| **Formula e plugin** | `asset_set_var`: CVaR storico al 95%, orizzonte di 1 osservazione e del «mese». `asset_set_drawdown`: massimo drawdown, durata, drawdown corrente, `remaining_to_peak_ratio` = 1/(1 + dd) − 1. Tutto sulla finestra comune della selezione |
| **Numeri da confrontare** | La peggior discesa di un ETF contro il grafico di justETF sullo stesso periodo. La risalita: dopo −20% serve +25%. Una giornata storta plausibile contro il peggior giorno visto sul grafico |
| **Limiti noti** | Finestra comune: chi parte tardi accorcia per tutti. Riporti: fino a 7 giorni non marcano, oltre la sezione è Partial |
| **C3 · prima/dopo** (owner **Risk**) | Prima: la giornata è diluita dai weekend riportati (−8/−13% sui dati del developer) e il «mese» sono 21 osservazioni, circa 3 settimane (−9/−19%). Dopo il checkpoint di Risk: i riporti di weekend e festivi non contano più come osservazioni, e il mese sono 30 giorni di calendario, convertiti in `n = max(1, round(30·f/365))` osservazioni, con `horizon_observations` nell'uscita. Voce del motore, non difetto di L1° |
| **Cosa sarebbe un difetto** | Un asset scelto senza riga; un trattino dove il dato esiste; un segno incoerente fra perdita e risalita; un ordinamento che non segue le cifre mostrate; un importo in euro |
| **Owner** | Presentazione F; motore Risk |

## Checkpoint · 2026-09-30, 15:30 (verso Risk)

> Il delta, i gruppi e i digest stanno nel messaggio a Risk. Stato: FROZEN fino al commit.

> ✅ **Committato** dal developer (14:2x):
> - `76fd7f208` G1 · `2f0d12e99` G2 · `ae4079510` G3 · `c9f8de31d` G4 · `9b38a65cc` G5 · `1b62abd2e` G6;
> - verificato in sola lettura (`/tmp/libreFolio_f4/verify_l1.sh`): **PASS**, con messaggi e file uguali per ogni
>   commit, digest del contenuto `51497c65…`, 15 file, +1979/−106.
>
> **Fusione e fast-forward**:
> - il checkpoint del calendario di Risk (`b32ddea77` e seguenti) è entrato prima della fusione F → Risk `3c46c8e60`,
>   validata da Risk (`risk-lab` 26/26 sulla revisione combinata);
> - il coordinatore mi porta in fast-forward su `3c46c8e60`. Verificato: HEAD `3c46c8e60`, `1b62abd2e` suo antenato,
>   albero pulito;
> - adattamenti di Risk nei miei file, con i miei OK: `horizon_observations` nei fixture e negli stub di VaR, il mese a
>   30 giorni di calendario, il pin E2E `[1, 30]`, e i commenti di `assetSetLevels.test.ts` e dei due file dei
>   fixture.

## Dopo L1° · la guida e il prossimo componente · 2026-09-30, dalle 15:55

**Richieste di Risk, in ordine**:
1. la guida `user/assets/correlation.en.md`, falsa in due punti dopo il calendario (solo EN, via docs-writer, con build
   e `check-links`; i passi del replay restano fermi fino all'F3 di Risk);
2. proporre a Risk il prossimo componente, con la stessa analisi di L1°; niente codice prima del via del developer.

**Fatti verificati sulla base `3c46c8e60`**:
- **Il mese**: `asset_set_var` 2.0.0 (`risk_plugins/asset_set_var.py:73-99`) prende l'orizzonte in giorni di
  calendario e lo converte con `calendar_days_to_observations` (`risk/metrics.py:731`, giorni × f / 365, arrotondato,
  mai meno di 1). Il mese sono 30 giorni: 21 osservazioni su una serie quotata nei giorni di borsa, 30 su una quotata
  ogni giorno. Il frontend usa `MONTHLY_VAR_HORIZON_DAYS = 30` (`riskAnalysisHelpers.ts:271`) e non mostra
  `horizon_observations` da nessuna parte.
- **I riporti memorizzati**: `_mark_market_closed_carries` (`series_preparation.py:132`). Una riga datata di sabato, di
  domenica o in un festivo di una delle borse principali, con la chiusura **esattamente** uguale alla riga precedente,
  è un riporto, non una quotazione: non aggiunge date alla finestra comune. È documentato in
  `data-quality.en.md#stored-carries`.
- **Frasi false nella guida**:
  - `:99`, la riga «Bad month»: «21 consecutive observations… three weeks when it counts every day — as it does when one
    of the selected assets comes from a source that records prices at weekends too»;
  - la regola 2: «Some sources record prices at weekends too, and those weekends then count for the whole selection».

### La guida dopo il calendario ✅ 2026-09-30, 16:00–16:20 (docs-writer `guide-calendar-fix`, solo EN)

> **Note implementazione**: tre passaggi di `user/assets/correlation.en.md`.
> - **`:99`, «Bad month»**: 30 giorni di calendario, composti dai rendimenti veri; circa 21 osservazioni se la scheda
>   conta solo i giorni di borsa, 30 se conta ogni giorno. Via «three weeks» e la frase sulle fonti che scrivono i
>   weekend.
> - **Regola 2 (`:159`)**: un prezzo del weekend o di un festivo che ripete esattamente la chiusura precedente è un
>   **riporto, non una quotazione** (link a `data-quality.md#stored-carries`) e non aggiunge date. Un weekend conta solo
>   se un prezzo si è mosso davvero, come può fare quello di una cripto.
> - **Punto «equità» (`:167`)**: «a weekend on which its price really moves».
> - La pagina non promette il numero di osservazioni del mese, perché l'interfaccia non lo mostra.
>
> **Reperto lasciato** per la riscrittura dei passi del replay dopo l'F3 di Risk:
> - nelle regole dei bordi (`:138-143`), «price» vuol dire in realtà «quotazione», perché anche il replay salta i
>   riporti (`eligibility.py:246-247`);
> - la differenza si vede solo se, vicino a un capo del periodo, le uniche righe di un asset sono chiusure ripetute di
>   weekend o festivi.
>
> **Cancelli**:
> - `dev.py mkdocs build`: exit 0, 0 WARNING; nella pagina generata c'è il link a `…/data-quality/#stored-carries`;
> - `dev.py mkdocs check-links`: exit 0, **88 validi** (la base è cresciuta con la correzione di A), 8 non verificabili,
>   3 ancore note.
> - ⚠️ La build ha riscritto di nuovo il timbro di `frontend/static/sw.js`: non toccato, fuori dal checkpoint.
