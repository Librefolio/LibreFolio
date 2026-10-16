# Piano — AF · Colori di asset e cambi (migrazione 1:1 ai ruoli)

> Workstream **AF** del programma colori, aperto il 16/10/2026 (D-T28, D-T29), coordinato dalla sessione «UI color
> analysis» (`aec04834-1532-4d86-9e3f-f942e82aca89`). Area: `components/assets/**`, `routes/(app)/assets/**`,
> `components/fx/**`, `routes/(app)/fx/**`. Mandato del coordinatore: migrazione **1:1** ai ruoli `-lf-`, senza
> decisioni di design; dove la tabella non basta, l'elemento resta com'è e si annota. Richiesta del developer (testuale):
> «l'obiettivo intanto è fattorizzare e migrare al nuvo color design sistem, poi le rifiniture le facciamo nel tempo»;
> «nel migrare cerca di seguire i colori dei temi che la designer ci ha intanto dato».
> Regole: skill [`design-system`](../../../../../.github/skills/design-tools/design-system/SKILL.md) (D-T29, la fonte) e
> [`theme-roles`](../../../../../.github/skills/design-tools/theme-roles/SKILL.md) (tabella classe → ruolo, baseline).
> Backlog: sezione «AF · Colori di asset e cambi» di [`BACKLOG_POST_1.2.md`](../../../Phase_0/BACKLOG_POST_1.2.md),
> voci `AF-n`.
> **Stato:** analisi del 16/10 mattina inviata al coordinatore; piano approvato il 16/10 alle 11:1x (uscita dal plan
> mode nella sessione AF). Decisioni chieste al coordinatore e ancora aperte: OK sui test della zona X (lotto 3), chi
> parte prima per i lotti 4–6, conferma della regola per le tinte ambigue, AF-8, sotto-agenti in parallelo.

## 0. Dati di partenza (verificati il 16/10, 10:41–11:30)

| Voce | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-congenial-spoon` |
| Branch | `e-alfy-af-colori-asset-cambi` (rinominato dall'app all'avvio; era `e-alfy-congenial-spoon`) |
| HEAD | `8f2824046` = baseline del kickoff ✅ all'analisi; portato dal coordinatore a `6e569084a` (= target, con Z7c-1, W-B17 e lo skill D-T29) prima del primo passo |
| Target | `dev_release2` = `6e569084a` (16/10, 11:1x) |
| Corsia | `--test-port 6157`, `--data-dir /tmp/librefolio-r2-af` |
| Coordinatore | `aec04834-1532-4d86-9e3f-f942e82aca89` |
| Bootstrap | niente `.env`, niente `frontend/node_modules`, niente `graphify-out/graph.json`: atteso. Wiki letta dalle pagine committate |
| Carico | 43–90 durante l'analisi: le prove leggere solo sotto 50 |

Letti: `copilot-instructions.md`, `frontend.instructions.md`, `frontend-testing.instructions.md`, skill `theme-roles`,
`tokens.css`, `toneClasses.ts`, la parte P1 di `app.css`, piano generale (D-T1…D-T29), piano di T (W1–W3, lotto degli
interruttori), registro del coordinatore (16/10), giro 2 della designer, backlog (sezioni AF, T colori, TC-10), wiki
`problems/tailwind4-same-property-utilities-sorted-by-name` (cita già la catena di `AssetCurrencyChangeModal`).

## 1. Inventario dal baseline (`theme-roles.mjs --report` + scansione per elemento)

Area: **36 file con classi legacy, m1 1.946, m2 6** (`components/assets` 972 + 6 letterali in 25 file,
`routes/(app)/assets` 546 in 2, `components/fx` 162 in 7, `routes/(app)/fx` 266 in 2). I 21 file `.ts` dell'area
misurano 0.

Divisione per elemento (script della sessione AF, fuori dal repo):
- **neutri** → ruoli di superficie, testo e bordo;
- **marchio** → `action`, `link`, `focus`, `selected`, `checked`;
- **stati** → triadi di stato, anche dove il significato è più morbido (filtro attivo, «Manual», ciclo di vita
  inattivo): è il precedente di T (`CheckMenu`, `CompactDurationBadge`);
- **segni** → `gain`/`loss`;
- **restano legacy:** categorie (tinte che distinguono tipi, precedente `KIND_TONES`), interruttori (lotto di T),
  catena (TC-10) e ruolo mancante.

| Lotto | File | m1 | m2 | neutri | marchio | stati | segni | categorie | interruttori | catena | ruolo mancante |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `fx/FxCard.svelte` | 63 | · | 49 | 8 | 6 | · | · | · | · | · |
| 1 | `fx/FxDataEditorSection.svelte` | 15 | · | 7 | 2 | 6 | · | · | · | · | · |
| 1 | `fx/FxDataImportModal.svelte` | 20 | · | 14 | · | 6 | · | · | · | · | · |
| 1 | `fx/FxPairAddModal.svelte` | 49 | · | 35 | 4 | 10 | · | · | · | · | · |
| 1 | `fx/FxPriceSummary.svelte` | 4 | · | 4 | · | · | · | · | · | · | · |
| 1 | `fx/FxSyncModal.svelte` | 2 | · | 2 | · | · | · | · | · | · | · |
| 1 | `fx/FxTable.svelte` | 9 | · | 5 | · | 4 | · | · | · | · | · |
| 2 | `routes/fx/+page.svelte` | 97 | · | 71 | 12 | 10 | · | 4 | · | · | · |
| 2 | `routes/fx/[pair]/+page.svelte` | 169 | · | 91 | 3 | 21 | · | 54 | · | · | · |
| 3 | `assets/AssetBrowseNav.svelte` | 6 | · | 6 | · | · | · | · | · | · | · |
| 3 | `assets/AssetCard.svelte` | 70 | · | 43 | 9 | 14 | 4 | · | · | · | · |
| 3 | `assets/AssetIcon.svelte` | 4 | · | · | 4 | · | · | · | · | · | · |
| 3 | `assets/AssetPriceSummary.svelte` | 13 | · | 10 | 1 | 2 | · | · | · | · | · |
| 3 | `assets/AssetTable.svelte` | 23 | 4 | 3 | 2 | 6 | · | 12 | · | · | · |
| 4 | `assets/AssetModal.svelte` | 26 | · | 22 | · | 4 | · | · | · | · | · |
| 4 | `assets/AssetModalDetails.svelte` | 79 | · | 55 | 9 | 13 | · | · | · | · | 2 |
| 4 | `assets/AssetModalFooter.svelte` | 29 | · | 19 | 2 | · | · | · | 8 | · | · |
| 4 | `assets/AssetModalIdentifiers.svelte` | 12 | · | 12 | · | · | · | · | · | · | · |
| 4 | `assets/AssetModalImportNotices.svelte` | 10 | · | · | · | 10 | · | · | · | · | · |
| 4 | `assets/AssetModalProvider.svelte` | 20 | · | 16 | 2 | 2 | · | · | · | · | · |
| 4 | `assets/AssetModalSelectionPrompts.svelte` | 38 | · | 32 | 5 | 1 | · | · | · | · | · |
| 5 | `assets/AssetSearchAutocomplete.svelte` | 57 | · | 47 | 8 | 2 | · | · | · | · | · |
| 5 | `assets/IdentifierPrimaryChooser.svelte` | 38 | · | 22 | 5 | 4 | · | 7 | · | · | · |
| 5 | `assets/ProviderAssignmentSection.svelte` | 95 | · | 72 | 5 | 18 | · | · | · | · | · |
| 5 | `assets/ProviderComparisonModal.svelte` | 60 | · | 48 | 10 | 2 | · | · | · | · | · |
| 6 | `assets/AssetCurrencyChangeModal.svelte` | 79 | · | 56 | · | 21 | · | · | · | 2 | · |
| 6 | `assets/AssetDataEditorSection.svelte` | 17 | · | 9 | 2 | 6 | · | · | · | · | · |
| 6 | `assets/AssetMergeModal.svelte` | 68 | · | 55 | 1 | 12 | · | · | · | · | · |
| 6 | `assets/BoundaryDateModal.svelte` | 37 | · | 27 | 2 | 8 | · | · | · | · | · |
| 6 | `assets/DistributionDataImportModal.svelte` | 3 | · | 1 | 2 | · | · | · | · | · | · |
| 6 | `assets/EventDataImportModal.svelte` | 18 | · | 2 | · | 4 | · | · | · | · | 12 |
| 6 | `assets/PriceDataImportModal.svelte` | 14 | · | 4 | · | 4 | · | · | · | · | 6 |
| 7 | `assets/CellDateRange.svelte` | 49 | · | 43 | 5 | 1 | · | · | · | · | · |
| 7 | `assets/ScheduledInvestmentEditor.svelte` | 107 | 2 | 90 | 5 | 8 | · | · | 4 | · | · |
| 8 | `routes/assets/+page.svelte` | 234 | · | 180 | 20 | 30 | · | 4 | · | · | · |
| 9 | `routes/assets/[id]/+page.svelte` | 312 | · | 201 | 17 | 39 | · | 55 | · | · | · |
| | **Totale** | **1.946** | **6** | **1.373** | **145** | **274** | **4** | **136** | **12** | **2** | **20** |

- **Migrabili: 1.776 classi e i 6 letterali.** Restano 170 classi, ognuna con la sua voce AF-n (§7).
- **I segni sono già sui ruoli:** `SIGN_TEXT.market` (W3-b di T) è in `AssetCard`, `AssetTable`, `AssetPriceSummary`,
  `FxCard`, `FxTable` e `FxPriceSummary`, e gli elementi che lo ricevono non hanno altre classi di colore. Resta solo il
  bordo del lampeggio di `AssetCard:134–136` (smeraldo/rosso): va su `border-lf-gain/NN` e `border-lf-loss/NN`, come T
  in `CompactCashCell` (`color-mix(var(--lf-gain) 70%)`).
- **I letterali m2 vanno sui ruoli con `var()` nel `<style>`:**
  - `AssetTable`, righe inattive: `#fffbeb`, `#fef3c7` e i due `rgb(120 53 15/…)` → `var(--lf-warning-soft)`, con
    l'hover in `color-mix` su `--lf-warning-line`; le regole `.dark` doppie spariscono;
  - `ScheduledInvestmentEditor`, `.late-row` tratteggiata: `rgb(209 213 219)` e `rgb(71 85 105)` →
    `var(--lf-border-subtle)`.
- **Interruttori: 12 classi.** `AssetModalFooter:46–48` e `:69–71`, `ScheduledInvestmentEditor:1218–1222`: restano per
  il lotto unico di T, già nel suo inventario.
- **Il dettaglio asset dopo FE5c:** `[id]/+page.svelte` scende a 155 e 145 classi vanno nei 6 componenti di
  `components/assets/detail/`, cioè 300 in tutto.

## 2. Catene di classi che escono dall'area

| # | Catena | Stato | Cosa faccio |
|---|---|---|---|
| C1 | `AssetCurrencyChangeModal:174` → `ModalBase.contentClass="border-2 border-red-300 dark:border-red-700"`. `ModalBase` (T, W1-e) ha già `border border-lf-raised text-lf-primary` sullo stesso elemento | Misto a runtime da W1-e. Oggi il rosso vince per l'ordine dei nomi (`border-red-300` > `border-lf-raised`); con `border-lf-danger-line` perderebbe (wiki, TC-10) | La lascio legacy. AF-4: serve una variante della modale (T) |
| C2 | Entrano costanti categoriali da fuori area: `assetTypeBadgeClass` (`utils/assetTypes.ts`, 80 m1), `PROVIDER_COLORS`/`DEFAULT_PROVIDER_COLOR` tramite `asset/fxProviderBadgeHtml` (`utils/providerHelpers.ts`, 20 m1), `getIndexColor` (stili in linea, `AssetModal:1479`) | Gli elementi che le ricevono hanno solo classi di layout | Non aggiungo ruoli a quegli elementi (G3). Tipi e fornitori seguono le tabelle di T e DV (W4) |
| C3 | Entra `SIGN_TEXT.market` (T) | Già ruoli, elementi puliti | Niente |
| C4 | `AssetTable`/`FxTable` → `DataTable`: celle HTML (elementi miei), `getRowClass → asset-row-inactive` (lo stile è nel mio `<style>`), `variant: 'danger'` delle azioni (lo disegna `DataTable`) | Nessun misto: i `<td>` sono di `DataTable` | Migro solo le mie stringhe e il mio `<style>` |
| C5 | `Price/EventDataImportModal` → figli dentro `InfoBanner` (T, migrato): i chip `<code class="bg-white/30 dark:bg-slate-700/50">` | Sono elementi miei, ma nessun ruolo dà «bianco al 30 % in chiaro e chip più chiaro in scuro» su una tinta; `htmlSink.gate.test.ts:73` fissa alla lettera uno dei tre | Li lascio. AF-5 |
| C6 | `AssetDataEditorSection`/`FxDataEditorSection`: linea d'anteprima `#a855f7` | Eccezione R-6 in `LITERAL_EXCEPTIONS`, colore di ECharts | Non la tocco |

Nessun componente dell'area dichiara una prop di classe: non entrano catene dai chiamanti.

I componenti dell'area usati fuori, con cambio visivo ma senza catena:
- `ImportWizardModal` (IW) usa `AssetModal`, `AssetMergeModal` e `IdentifierPrimaryChooser`;
- `TransactionFormModal` (TR) usa `AssetModal` e `FxSyncModal`;
- `DistributionEditor` (T) usa `DistributionDataImportModal`;
- `AssetIcon` è usato da `LotCustodyModal` (BK) e da quattro file del PAC (DV);
- `FxPairAddModal` è usato da `FxStep` del PAC (DV) e dalla dashboard (DV).

**Regola 8:** la scansione per elemento (script della sessione AF) non trova coppie della stessa proprietà fra la parte fissa
e quella condizionale di una classe. Il rischio resta C1 e va ricontrollato su ogni ternario migrato.

## 3. Test che asseriscono classi di colore

| Test | Righe | Cosa asserisce | Proprietario | Proposta |
|---|---|---|---|---|
| `src/lib/components/assets/AssetTable.test.ts` | 135–136 | pallino `bg-emerald-500`/`bg-red-400` nella tabella | zona asset di X (1.3) | `test-author` → aggancio `data-lifecycle` sul pallino (attributo, non colore, nella stringa HTML) — **serve OK** |
| idem | 164–168 | superfici di `AssetCard` (`bg-white`, `dark:bg-slate-800`, `bg-amber-50`, `dark:bg-amber-950/30`) | X | `data-lifecycle`, che c'è già sulla card — **serve OK** |
| idem | 190–192, 209 | badge `txScope` (`bg-emerald-100`, `bg-blue-100`, `bg-gray-100`) | X | invariato: il badge resta categoriale (AF-2) |
| `e2e/assets/asset-list.spec.ts` | 483–488 | superfici delle card attive e inattive | X | `data-lifecycle` — **serve OK** |
| idem | 782–795 | badge `txScope` via `[class*="bg-…-100"]` | X | invariato (AF-2) |
| `src/htmlSink.gate.test.ts` | 73 | fissa l'espressione con il `<code>` legacy di `PriceDataImportModal:71` | gate condiviso | invariato: i chip restano (AF-5) |

Controllati tutti gli E2E e tutti i `*.test.ts` che importano o leggono i file dell'area. Nessun altro asserisce colori;
quelli che leggono le pagine come sorgente (`comparisonSignalPages`, `chartCoreHelpers`, `assetTypeTables`,
`htmlInterpolation.gate`) non guardano le classi. Nessun ramo tocca questi test.

## 4. File dell'area aperti in altri worktree (letti solo dai ref di git, mai i checkout)

- **X** (`e-alfy-x-plugin-asset-e-ricerca`, `c9502ac16`): 27 commit fuori dal target, di cui 19 file nell'area (FE5c):
  - 18 nuovi in `components/assets/detail/`: 6 `.svelte` (11, 20, 28, 19, 54 e 13 classi), 6 moduli `.ts` e 6 test;
  - modificato `routes/(app)/assets/[id]/+page.svelte`, da 312 a 155 classi;
  - nel suo baseline nessuna riga `~split`: all'ingresso la sistemate tu con X.
- **Z** (`e-alfy-z-sospensione-e-risveglio`): **0 commit fuori dal target.** Z7c-1, che tocca le due rotte asset senza
  classi, è in `dev_release2` da `dd4a97e01` (`69c95454b`), dopo il mio baseline.
- **Nessun commit nell'area** su W, J, A, B, H, Y, E, `hotfix-1.2.1`, `preview-colori-t8c-dv` e sui rami colori
  (T, DV, L, G, IW, TR, BK, IM).
- **Il lavoro non committato degli altri worktree non l'ho guardato** (regola: mai leggere un altro checkout): lo
  conferma il coordinatore.
- **Voci aperte della 1.3 sui miei file** (piani, non codice):
  - X: O-8 su `AssetDataEditorSection:444–467`, O-20 su `AssetModal:1462` e `assets/+page:1834–1840`, C-66 su
    `FxSyncModal`/`AssetSyncModal`, C-90 su `ProviderAssignmentSection:372`;
  - W: E0/E1b su `EventDataImportModal`/`AssetDataEditorSection`, già nel target.

## 5. Lotti, in ordine (ognuno validabile da solo)

Il primo numero è m1 del baseline, il secondo quello che resta dopo il lotto.

| # | Lotto | File esatti (`frontend/src/…`) | m1 → resta | Condizione |
|---|---|---|---|---|
| 1 | Cambi, componenti | `lib/components/fx/{FxCard,FxDataEditorSection,FxDataImportModal,FxPairAddModal,FxPriceSummary,FxSyncModal,FxTable}.svelte` | 162 → 0 | libero (C-66 di X su `FxSyncModal`: tocco 2 neutri) |
| 2 | Cambi, pagine | `routes/(app)/fx/+page.svelte`, `routes/(app)/fx/[pair]/+page.svelte` | 266 → 58 | libero |
| 3 | Asset, lista (componenti) | `lib/components/assets/{AssetCard,AssetTable,AssetPriceSummary,AssetIcon,AssetBrowseNav}.svelte` + `AssetTable.test.ts`, `e2e/assets/asset-list.spec.ts` (test-author) | 116 → 12; m2 4 → 0 | **OK sui test della zona X** |
| 4 | Asset, modale | `lib/components/assets/{AssetModal,AssetModalDetails,AssetModalFooter,AssetModalIdentifiers,AssetModalImportNotices,AssetModalProvider,AssetModalSelectionPrompts}.svelte` | 214 → 10 | chi parte prima con O-20 di X |
| 5 | Asset, ricerca e fornitori | `lib/components/assets/{AssetSearchAutocomplete,ProviderAssignmentSection,ProviderComparisonModal,IdentifierPrimaryChooser}.svelte` | 250 → 7 | chi parte prima con C-90 di X |
| 6 | Asset, modali di gestione e dati | `lib/components/assets/{AssetCurrencyChangeModal,AssetMergeModal,BoundaryDateModal,AssetDataEditorSection,PriceDataImportModal,EventDataImportModal,DistributionDataImportModal}.svelte` | 236 → 20 | chi parte prima con O-8 di X |
| 7 | Piano programmato | `lib/components/assets/{ScheduledInvestmentEditor,CellDateRange}.svelte` | 156 → 4; m2 2 → 0 | libero (l'interruttore resta a T) |
| 8 | Pagina lista asset | `routes/(app)/assets/+page.svelte` | 234 → 4 | baseline aggiornato al target ≥ `69c95454b` e tuo via |
| 9 | Dettaglio asset | `routes/(app)/assets/[id]/+page.svelte` + `lib/components/assets/detail/*.svelte` | ~300 → ~55 | dopo l'ingresso di X FE5c |

**Esecuzione.**
- Le bozze dei lotti possono andare in parallelo, a sotto-agenti `general-purpose`:
  - ognuno lavora su file disgiunti, con la skill `theme-roles` e la tabella del §6;
  - nessuno lancia test né server.
- Le rivedo e lancio io, in serie, le prove leggere.
- I test li scrive `test-author` (lotto 3).
- **Checkpoint:** A con i lotti 1–2 (più il 3 se c'è l'OK), B con i lotti 4–7, C con l'8 e il 9.
- A ogni checkpoint: `--update` del baseline e FROZEN.

## 6. Regole di conversione e «da rivedere»

**Regole comuni** (tabella della skill e precedenti di T):
- **Card e superfici:** card `bg-lf-card`, pannelli `bg-lf-panel`, campi `bg-lf-field border-lf-input
  hover:border-lf-input-hover`, `placeholder:text-lf-placeholder`, testi primary/secondary/muted, bordi `subtle`.
- **Marchio e controlli:**
  - pulsante primario `bg-lf-action hover:bg-lf-action-hover text-lf-on-action`;
  - accenti, link e spinner `text-lf-link`;
  - fuoco `focus:ring-lf-focus` e `focus:border-lf-focus`;
  - segmento, preset, filtro o radio attivi `bg-lf-checked text-lf-on-checked` (D-T16);
  - checkbox `border-lf-input text-lf-link focus:ring-lf-focus`;
  - secondari pieni grigi `bg-lf-panel text-lf-secondary hover:bg-lf-neutral` (precedente di `DateRangePicker`).
- **Stati:**
  - rosso pieno `bg-lf-danger-solid hover:bg-lf-danger-hover text-lf-on-danger-solid`;
  - ambra piena `bg-lf-warning text-lf-on-status hover:bg-lf-warning-hover` (Q3);
  - tinte `-soft` + `-line` + testo 500–700 → `text-lf-X`, 800–900 → `-on-soft`;
  - campo non valido `border-lf-danger` (precedente di T);
  - hover su una tinta `bg-lf-X-line/50` (precedente di `dataQuality`).
- **Fondali** `bg-lf-overlay`.
- **Regola 3:** `text-lf-primary` sulla radice dei componenti migrati.
- **Regola 8:** un ternario per proprietà.
- **Mai `dark:`.** Un elemento migra tutto o niente.

**Da rivedere per il developer** (scelte dentro la tabella che cambiano un po' l'aspetto; l'elemento migra):
1. Lotto 1:
   - l'hover della card dei cambi passa dalla tinta verde al neutro `hover:bg-lf-hover`, con bordo `hover:border-lf-focus/30`;
   - l'icona di sync disabilitata è su `text-lf-muted/50`;
   - il riquadro «coppie intermedie» è sulla triade info, con hover `hover:bg-lf-info-line/40`;
   - l'hover dell'icona sync è su `hover:text-lf-warning`.
2. Lotto 2:
   - assoluto/% è su `checked`, il verde del fuoco, più chiaro del vecchio verde scuro;
   - la cornice dell'editor è sui ruoli dell'avviso, mentre il suo bottone nella barra resta ambra legacy (AF-1);
   - il banner d'errore resta ambra, come oggi;
   - «Inserisci a mano» è un pieno d'avviso;
   - «Riprova» è un rosso pieno.
3. Lotto 3:
   - la card e la riga inattive vanno su `warning-soft`: in chiaro ambra-100, un passo più carica dell'ambra-50 di oggi;
   - il bordo del lampeggio va su `gain/loss` con opacità;
   - il fondo dell'icona va su `bg-lf-selected`.
4. Lotto 4:
   - i bordi dei campi diventano più scuri (3:1, D-T6/D-T18);
   - il campo «quantità di base» non valido va su `border-lf-danger`.
5. Lotto 5:
   - il chip del fornitore scelto va su `selected` + `focus/40`;
   - i bordi dei risultati del test vanno su `-line`, più tenui dei 400 di oggi.
6. Lotti 6 e 7:
   - i pulsanti con `hover:bg-libre-green-dark` oggi non cambiano al passaggio, perché la classe non esiste: la
     migrazione aggiunge `action-hover` (AF-8, da confermare);
   - il fondale di `BoundaryDateModal` passa al 60 %;
   - la riga tratteggiata va su `border-subtle`.
7. Lotti 8 e 9:
   - il filtro «Inattivi» acceso è un pieno d'avviso;
   - il filtro tipo attivo usa la triade info;
   - il link alle transazioni del dettaglio è blu: lo metto su `text-lf-info`, che tiene la tinta, invece di
     `text-lf-link`.

## 7. Restano legacy, con la voce nel backlog (sezione AF)

- **AF-1 · Accenti degli strumenti della barra del grafico:** misura viola, editor ambra, estetica smeraldo, e le icone di
  sezione (segnali blu, metadati azzurro). Sono tinte che distinguono strumenti, e restano per la designer e T. La Q12
  («niente arcobaleno») suggerisce un colore unico.
- **AF-2 · Tipi distinti dalla tinta:** badge `txScope` (proprio, altri, analisi) e origine dell'identificativo (fornitore,
  salvato), sul precedente di `KIND_TONES`.
- **AF-3 · Riquadri decorativi degli stati vuoti:** monete ambra della pagina cambi, grafico verde della pagina asset.
- **AF-4 · Bordo rosso di `AssetCurrencyChangeModal`** via `ModalBase.contentClass` (C1, TC-10): serve una variante
  della modale (T).
- **AF-5 · Chip `<code>` sulle tinte dei banner** (`Price/EventDataImportModal`): manca un ruolo; uno è fissato da
  `htmlSink.gate`.
- **AF-6 · Velo e icona bianca sull'immagine dell'asset** (`AssetModalDetails:104–107`): manca un ruolo «testo sul
  velo».
- **AF-7 · Tre interruttori** → lotto unico di T.
- **AF-8 · `hover:bg-libre-green-dark`**, classe morta: va confermato l'hover aggiunto.
- **AF-9 · Dettaglio asset** in attesa di X FE5c.

## 8. Ricette di prova

**Leggere** (corsia AF, una alla volta, `nice -n 10`, carico < 50; `npm ci` approvato una volta prima della prima):

```bash
cd frontend && nice -n 10 node scripts/theme/theme-roles.mjs --check
cd frontend && nice -n 10 npm run test:unit -- src/themeRoles.gate.test.ts src/themeTokens.gate.test.ts <vitest del lotto>
cd frontend && nice -n 10 node_modules/.bin/prettier --check <file del lotto>
git diff --check
```

I Vitest di ogni lotto:

| Lotto | Vitest |
|---|---|
| 1 | `src/lib/components/fx/{FxPairAddModal,FxSyncModal,FxMissingRate}.test.ts` |
| 2 | `src/lib/components/charts/chartCoreHelpers.test.ts`, `src/lib/charts/signals/__tests__/comparisonSignalPages.test.ts` |
| 3 | `src/lib/components/assets/{AssetTable,AssetTable.privacy,AssetBrowseNav}.test.ts`, `src/htmlInterpolation.gate.test.ts` |
| 4 | `src/lib/components/assets/{AssetModal,AssetModal.providerLifecycle}.test.ts` |
| 5 | `src/lib/components/assets/{AssetSearchAutocomplete,ProviderAssignmentSection,ProviderComparisonModal}.test.ts` |
| 6 | `src/lib/components/assets/AssetCurrencyChangeModal.test.ts`, `src/lib/components/ui/data-editor/DataEditor.test.ts`, `src/htmlSink.gate.test.ts` |
| 7 | `src/lib/components/assets/{ScheduledInvestmentEditor,CellDateRange,scheduleSerialization}.test.ts` |
| 8 | `chartCoreHelpers.test.ts`, `src/lib/utils/__tests__/assetTypeTables.test.ts` |

**Pesanti**, solo nello slot assegnato, con
`P="PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py"`:
- in testa `$P api sync`;
- **solo la prima volta:** `$P front build --debug` e `$P mkdocs build`;
- poi `$P front check` e `$P test --test-port 6157 --data-dir /tmp/librefolio-r2-af front-utility component-unit`;
- poi gli E2E, una categoria alla volta, nella stessa corsia:

| Slot | Lotti | E2E |
|---|---|---|
| H1 | 1–2 (+3) | `front-fx fx-list`, `fx-detail`, `fx-add-pair`, `fx-editor`, `fx-csv-import`, `fx-sync-mock`, `fx-bulk`, `fx-settings`, `fx-destructive`; col lotto 3: `front-asset asset-list`, `asset-browse`, `asset-name-xss`, `live-pause` |
| H2 | 4–7 | `front-asset asset-modal`, `asset-mobile-layout`, `asset-classification`, `asset-merge`, `asset-data-editor`, `asset-event-delete`, `asset-event-editor-save`; in sola lettura, gli spec di IW che aprono le mie modali: `front-transaction tx-import-asset-inspector`, `tx-ca-contract` |
| H3 | 8–9 | `front-asset asset-list`, `asset-browse`, `live-pause`, `asset-name-xss`, `asset-detail`, `asset-data-editor` |

- Facoltativo, guardia globale: `front-utility theme-roles`.
- Ogni slot sta sotto i 45 minuti; se H1 sfora, il lotto 3 passa in H2.
- Alla fine di ogni slot: `lsof -nP -iTCP:6157 -sTCP:LISTEN` vuoto.

## 9. Rischi e dipendenze

- **X FE5c** (lotto 9): numeri di riga e file nuovi. Parto solo dopo il suo ingresso e la sistemazione del baseline.
- **Il target è avanti di 8 commit (Z7c-1):** prima del lotto 8, e meglio prima del checkpoint A, mi serve un
  fast-forward.
- **Baseline TSV condiviso:** i conflitti si risolvono a ogni ingresso con `--resolve`, senza mai allargare.
- **App.css e C4:** se tolgo l'ultimo uso di una classe con regola nel rimappaggio scuro, tolgo il selettore e lo
  dichiaro. È improbabile: le classi rimappate sono comuni a tutte le aree.
- **Lotto degli interruttori di T** su `AssetModalFooter` e `ScheduledInvestmentEditor`: hunk vicini, rischio basso.
- **`placeholder-gray-400`** (6 coppie) è sintassi v3: se oggi v4 non la genera, il segnaposto migrato cambia colore.
  Lo verifico sul CSS compilato in H1.
- **Cambi visivi attesi, voluti dai ruoli:**
  - verde del marchio → `action`/`focus`;
  - bordi dei campi al 3:1;
  - tinte di stato della designer;
  - in scuro gli elementi migrati escono dal rimappaggio legacy.

  Li valuta il developer dalla galleria (D-T21/D-T27).
- **Carico della macchina** (40–90): le prove leggere aspettano il carico sotto 50.
- **Dipendenze:**
  - T: interruttori, variante di `ModalBase` (TC-10), ruoli per chip e velo, skill D-T29;
  - DV/T: tabelle categoriali dei tipi e dei fornitori;
  - X: OK sui test, FE5c;
  - coordinatore: slot, fast-forward, chi parte prima.

## 10. Definition of done

- **Classi:** lotti 1–8 (e 9 dopo FE5c) migrati; m1 dell'area da 1.946 a circa 170, tutte con voce AF-n; m2 da 6 a 0.
- **Gate:** `--check` pulito, con 0 violazioni del cricchetto e della grammatica; baseline stretto con `--update` a ogni
  checkpoint.
- **Prove:** leggere e pesanti verdi; nessun elemento misto nuovo, catene ricontrollate; porta 6157 libera.
- **Journal:** piano aggiornato dopo ogni passo (✅, «Note implementazione», «Fuori pista»), sezione AF del backlog
  compilata, «dove guardarlo» per ogni lotto, checkpoint inviati e FROZEN.

## 11. Passi

Dopo ogni passo: ✅ con la data, «Note implementazione», «Fuori pista» per le deviazioni, comandi ed evidenze.

1. ✅ (16/10) Piano nel journal (questo file), voci AF-1…AF-9 nella sezione AF del backlog, `npm ci` (approvato una volta).
   > **Note implementazione**:
   > - piano e voci scritti dopo l'approvazione. Il coordinatore ha portato il branch a `6e569084a`: c'è lo skill
   >   D-T29, che conferma le scelte del piano (regola 9 su `AssetCurrencyChangeModal`, domanda aperta 3 per l'hover
   >   su `panel`, regola 10 per i test);
   > - `npm ci` verde (`/tmp/libreFolio_af_npmci.log`);
   > - per le Vitest dei componenti serve un `api sync` fuori slot (regola del coordinatore delle 11:2x), sotto `nice`
   >   e con carico < 50.
   >
   > **Decisioni del coordinatore (16/10, 11:1x–11:2x):**
   > - la 1.3 dà il via su tutti i lotti 1–8 e AF passa per primo. X ha piccole voci in attesa (C-66, O-20, F21/C-90,
   >   O-8), quindi hanno precedenza i lotti 1, 4, 5, 6 e 8;
   > - il fast-forward non serve: la base `6e569084a` contiene `69c95454b`;
   > - **checkpoint:** A = lotti 1–3, B = lotti 4–7, C = solo il lotto 8, D = lotto 9 dopo FE5c;
   > - **via ai test del lotto 3:** X ha confermato che `AssetTable.test.ts`, `AssetTable.svelte` e
   >   `asset-list.spec.ts` non sono aperti.
   >
   > **⚠️ Fuori pista:** `originClass()` di `IdentifierPrimaryChooser` ha tre rami (fornitore, salvato, documento grigio).
   > Il terzo resta legacy con gli altri, come `KIND_TONES.identifier.name`: al lotto 5 restano quindi 11 classi, non 7.
2. ✅ (16/10) Lotto 1 · cambi, componenti: 7 file, da 162 a **0**.
   > **Note implementazione**:
   > - scritto da me;
   > - `--check` pulito, nessuna violazione di grammatica; `af_count` dà m1 0 su tutti e 7;
   > - card dei cambi:
   >   - radice `bg-lf-card text-lf-primary shadow-lf-shadow-card border-lf-subtle`, hover `hover:bg-lf-hover
   >     hover:border-lf-focus/30`, fuoco `focus:ring-lf-focus`;
   >   - le icone dentro la card hovano con `hover:bg-lf-neutral`: la card sotto il puntatore diventa `hover`, cioè
   >     `panel`, e un hover `hover` sui bottoni non si vedrebbe (domanda aperta 3);
   >   - «Manual» sulla tinta d'avviso;
   >   - la sync disabilitata è `text-lf-muted/50`;
   > - errori sul set `danger`; il riquadro «coppie intermedie» sul set `info` con hover `hover:bg-lf-info-line/50`;
   > - «Annulla» `bg-lf-panel text-lf-secondary hover:bg-lf-neutral` (precedente di `DataImportModal`); i campioni
   >   `<pre>` su `bg-lf-card/50`;
   > - lo scheletro di caricamento è `bg-lf-neutral`, come dice lo skill per gli scheletri.
   >
   > Le prove leggere (Vitest, Prettier) aspettano un carico sotto 50.
3. ✅ (16/10) Lotto 2 · cambi, pagine: da 266 a **58**, cioè 4 + 54.
   > **Note implementazione**:
   > - bozza di un sotto-agente `general-purpose`, riletta da me;
   > - `af_count` dà 4 in `fx/+page` (il riquadro delle monete, AF-3) e 54 in `fx/[pair]` (AF-1: i tre interruttori
   >   degli strumenti, la sezione misure e l'icona dei segnali);
   > - `af_diffcheck` conferma un diff di sole classi di colore; l'unica eccezione è `text-lf-primary` aggiunto sulle
   >   due radici di pagina (regola 1);
   > - nessun ternario ristrutturato.
   >
   > **Da rivedere:**
   > - assoluto/% è su `checked`: più chiaro, e in scuro il testo è scuro;
   > - il reset dei filtri disabilitato è `text-lf-muted/50`;
   > - in scuro le cornici del box d'errore, del banner ambra e dell'editor mostrano il loro `-line`. Prima il
   >   rimappaggio `.rounded-xl` di `app.css` le rendeva grigie;
   > - i testi `-on-soft` sulle tinte;
   > - la nota dell'editor, che sta sulla card e non sulla tinta, è su `text-lf-warning-on-soft/70`: circa 3,5:1
   >   contro 3,0:1 di `text-lf-warning/70`;
   > - «Inserisci a mano» è un pieno d'avviso, con il testo scuro in scuro;
   > - sei card prendono `shadow-lf-shadow-card`.
4. ✅ (16/10) Lotto 3 · asset, lista: da 116 a **12** (il badge `txScope`, AF-2); m2 da 4 a 0. I test sono di
   `test-author`.
   > **Note implementazione**:
   > - **Scritto da me:**
   >   - `AssetCard`: superficie attiva `bg-lf-card hover:bg-lf-hover`, inattiva `bg-lf-warning-soft
   >     hover:bg-lf-warning-line/50`; bordi `border-lf-subtle`/`border-lf-warning-line` e lampeggio
   >     `border-lf-gain/50`/`border-lf-loss/50`, tutti nella stessa funzione;
   >   - radice di `AssetCard` con `text-lf-primary shadow-lf-shadow-card hover:border-lf-focus/30 focus:ring-lf-focus`;
   >     pallino `bg-lf-success`/`bg-lf-danger`; icone `hover:bg-lf-neutral`, come le card dei cambi;
   >   - `AssetTable`: pallino con aggancio `data-lifecycle` (approvato); «Manual»; icona di riserva; `<style>` delle
   >     righe inattive su `var(--lf-warning-soft)` con hover `color-mix(in oklab, var(--lf-warning-line) 50%,
   >     transparent)`, senza più le regole `.dark`;
   >   - `AssetPriceSummary`, `AssetIcon` (riquadro `bg-lf-selected`, icona `text-lf-link`), `AssetBrowseNav`.
   > - **Test di `test-author`:**
   >   - `AssetTable.test.ts`: i pallini via `span[data-lifecycle]`, con l'helper `lifecycleDotsIn` e `toEqual` per
   >     riga; via le asserzioni sulle superfici della card; test rinominato; commento d'intestazione aggiornato;
   >   - `asset-list.spec.ts` 480–485: solo `data-lifecycle`;
   >   - `txScope` invariato in tutti e due i file.
   > - `af_diffcheck`: diff di soli colori, salvo l'aggancio, il `<style>` e un `dark:disabled:hover:bg-transparent`
   >   ormai superfluo in `AssetBrowseNav`.
   >
   > **Da sapere** (da `test-author`): `badgeIn` trova il badge come primo `span.font-mono` della riga; e
   > `[data-testid^="asset-card-"][data-lifecycle]` conta le card, quindi nessun elemento interno della card deve avere
   > insieme `data-lifecycle` e un testid `asset-card-…`.
   >
   > **Da rivedere:**
   > - card e riga inattive su `warning-soft`, un passo più carico in chiaro;
   > - l'opacità del lampeggio;
   > - l'icona di riserva su `bg-lf-selected`;
   > - l'hover della card attiva è neutro, non più la tinta verde.
5. ✅ (16/10) Lotto 4 · modale asset, bozza: da 214 a **10** (8 dei due interruttori, AF-7; 2 del velo, AF-6).
   > **Note implementazione**:
   > - sotto-agente, riletto da me;
   > - `af_count` conferma; `af_diffcheck` dà soli colori, più `hover:border-lf-input-hover` sui 4 campi (ricetta del
   >   campo);
   > - nessun ternario ristrutturato.
   >
   > **Da rivedere:**
   > - bordi dei campi più scuri, con l'hover;
   > - `border-lf-danger` sulla quantità di base non valida;
   > - avvisi d'importazione su `warning-soft`;
   > - in scuro i bottoni a contorno perdono il fondo ardesia (ora `bg-lf-card`);
   > - il bordo del «Annulla» della scelta del codice è più tenue in scuro;
   > - le testate «Altre informazioni» e «Fornitore» sono su `bg-lf-panel` con hover `bg-lf-neutral`;
   > - il divisore del piede è su `bg-lf-subtle`.
5. ⏳ **Checkpoint A** → FROZEN → commit del coordinatore → slot H1.
6. ⏳ Lotti 4–7 (bozze in parallelo, prove in serie) → **checkpoint B** → slot H2.
   > ✅ **Lotto 5 · ricerca e fornitori, bozza** (16/10): da 250 a **11**: `originClass()` di `IdentifierPrimaryChooser`,
   > i suoi tre rami (AF-2).
   >
   > **Note implementazione:**
   > - sotto-agente, riletto da me;
   > - `af_count` e `af_diffcheck` puliti;
   > - **una correzione:** nel riquadro del fornitore (`ProviderComparisonModal`) didascalia, chiavi e trattino tornano
   >   grigi (`text-lf-muted`, `text-lf-secondary`), come nel riquadro accanto. Solo i valori restano su
   >   `text-lf-success-on-soft`: la bozza aveva messo tutto su `-on-soft` e la distinzione si perdeva.
   >
   > **Da rivedere:**
   > - bordi dei campi più scuri;
   > - riquadro del tipo bloccato e URL in sola lettura con l'aspetto disabilitato di `SimpleSelect`;
   > - tendina dei risultati su `border-lf-raised` + `shadow-lf-shadow`;
   > - chip del fornitore scelto su `selected`;
   > - barra dei risultati del test sui ruoli pieni, più scuri dei 400 in chiaro, e il ramo neutro su `subtle`;
   > - banner di streaming su `bg-lf-panel`, opaco in scuro.
   >
   > ✅ **Lotto 6 · modali di gestione e dati, bozza** (16/10): da 236 a **20**. Restano 2 della catena di `ModalBase`
   > (AF-4) e 6 + 12 chip `<code>` (AF-5); la riga di `PriceDataImportModal` fissata da `htmlSink.gate:73` è identica.
   >
   > **Note implementazione:** sotto-agente, riletto da me, con quattro correzioni sul precedente di T:
   > - i bottoni a contorno con bordo 300 vanno su `border-lf-input` (`OnboardingReplaySection`, `WelcomeForm`): «Indietro»
   >   e «Annulla» dell'unione, e i quattro dell'export;
   > - l'export, che sta su un riquadro `panel`, hovera con `bg-lf-neutral` (domanda aperta 3);
   > - il chip dell'identificativo dell'unione va su `bg-lf-neutral`, come i chip neutri di `STATUS_TONES`;
   > - il «Annulla» del piede `panel` di `AssetCurrencyChangeModal` va su `bg-lf-neutral hover:bg-lf-input/30`:
   >   `panel` su `panel` non si vedeva e nessun ruolo dà un neutro più forte (AF-10).
   >
   > **Da rivedere:**
   > - il fondale di `BoundaryDateModal` al 60 %;
   > - l'hover aggiunto su `action-hover` (AF-8);
   > - l'anello dello spinner del cambio valuta su `border-lf-muted`;
   > - la lista rossa a `/60` anche in scuro.
   > ✅ **Lotto 7 · piano programmato, bozza** (16/10): da 156 a **4** (l'interruttore della mora, AF-7); m2 da 2 a 0.
   > **Note implementazione:**
   > - sotto-agente, riletto da me;
   > - `.late-row` è su `var(--lf-border-subtle)`, senza la regola `.dark`;
   > - aggiunti `hover:border-lf-input-hover` sui 7 campi e `shadow-lf-shadow` sul popover di `CellDateRange`.
   >
   > **Da rivedere:**
   > - l'hover aggiunto a «aggiungi il primo periodo» (AF-8);
   > - la riga tratteggiata e il riquadro vuoto tratteggiato più tenui in scuro;
   > - ⚡ su `--lf-warning`, più scuro in chiaro;
   > - la testata della tabella degli eventi su `bg-lf-panel`.
7. ✅ (16/10) Lotto 8 · pagina lista asset, bozza: da 234 a **4** (il riquadro dello stato vuoto, AF-3).
   > **Note implementazione:**
   > - sotto-agente, riletto da me;
   > - aggiunto da me `text-lf-primary` sulla radice `assets-page`, come le pagine dei cambi;
   > - filtri: «attivi» acceso su `checked`, «inattivi» acceso su pieno d'avviso, a riposo
   >   `bg-lf-card text-lf-muted hover:bg-lf-hover`;
   > - filtro tipo attivo sul set `info` (precedente di `CheckMenu`); chip dei tipi scelti su `checked`;
   > - pastiglie delle valute sul set `warning`, con la × in `hover:text-lf-danger`;
   > - tendina dei tipi `bg-lf-card border-lf-raised shadow-lf-shadow`; «seleziona tutto» e «azzera» `bg-lf-panel
   >   hover:bg-lf-neutral`.
   >
   > **Da rivedere:**
   > - il campo di ricerca ha il bordo più scuro e l'hover;
   > - in scuro i segmenti attivi e «inattivi» hanno il testo scuro;
   > - la × rossa sulla tinta d'avviso non è una coppia misurata.
8. ✅ (16/10, 11:35–11:50) Prove leggere dei lotti 1–8 e checkpoint **A** (lotti 1–3), **B** (4–7), **C** (8).
   **D** = lotto 9, dopo FE5c.
   > **Prove:**
   > - `api sync` fuori slot, rc 0;
   > - Vitest dei gate e dei componenti toccati, 23 file: 22 verdi, 861 test. L'unico rosso era il G3 qui sotto, poi
   >   risolto; dopo la correzione i gate fanno 65/65;
   > - Prettier `--check` verde sui 37 file;
   > - compilazione Svelte dei 35 `.svelte`: tutti ok, nessun avviso;
   > - regola 8 (scansione delle classi fisse contro quelle condizionali): 0 casi;
   > - `dark_only_check` (coordinatore): 0 casi su 35 file;
   > - `--check` pulito, 35 file sotto il record;
   > - `git diff --check` pulito.
   >
   > **Baseline** (`--update`): m1 da 8.249 a **6.734**, m2 da 54 a **48**. L'area AF scende da 1.946 a 431 (312 sono il
   > dettaglio, che aspetta FE5c). Per i commit separati ci sono le versioni intermedie del TSV, A e AB.
   >
   > **⚠️ Fuori pista:**
   > - **G3 falso** su `routes/(app)/assets/+page.svelte:1639` (`onfitperiod`).
   >   - `codeOf` non toglie i commenti JS dentro i `{…}` del markup. L'apostrofo e i backtick del commento di 1643–1644
   >     aprono per lo scanner una stringa che arriva a riga 1699 e mescola ruoli e il riquadro legacy.
   >   - Rimedio autorizzato dal coordinatore: il commento riscritto senza apostrofo né backtick, con lo stesso testo.
   >     È l'unica modifica non di colore del checkpoint C.
   >   - La correzione dello scanner va a T: è anche un punto cieco del gate.
   > - **Prettier** ha spostato il `>` di chiusura in 6 file, per la nuova lunghezza delle classi; i token sono
   >   verificati identici.
   >
   > **Ruoli nuovi di T** (`f043c1b58`, arrivano con la base merge): `text-lf-on-overlay` risolve AF-6.
