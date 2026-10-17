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
> **Stato (16/10, 18:30): area migrata, tutto nel target** (`c179a5144`). Dettagli nel passo 15.
> - **Lotti 1–8:** A `25cd00a04`, B `28aa01f8e`, C `f92675b80`, fix G6 `5cdf4c307`.
> - **AF-6:** `8dc5b864c`. **Lotto 9 e AF-4:** `8aa3904a6`.
> - **Docs:** `15f31f12e`, `830a805a3`, `8347b7713`.
> - **Area AF:** da m1 1.946 e m2 6 a **170 e 0**. Restano solo classi annotate: AF-1 109, AF-2 23, AF-3 8, AF-5 18,
>   AF-7 12.
> - **Aperte:** AF-1 (aspetta la designer), AF-2, AF-3, AF-5, AF-7 (lotto degli interruttori di T), AF-8 (da
>   confermare), AF-10 (ruolo di T).

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
9. ✅ (16/10, 12:01–12:43) **Slot pesante H1+H2** sulla base `5e759bc9b` (A, B, C committati dal coordinatore, merge
   del target `f77743d47`).
   > **Ambiente:** corsia 6157 + `/tmp/librefolio-r2-af`, 1 worker (carico fra 36 e 165).
   > Script `/tmp/libreFolio_af_slotH12.sh`, che non avvia nessun passo nuovo dopo le 12:43; log in
   > `/tmp/libreFolio_af_slotH12/`.
   >
   > **Preparazione e unità:**
   >
   > | Passo | Esito |
   > |---|---|
   > | `api sync` | rc 0 |
   > | `front build --debug` | rc 0 (4 min) |
   > | `mkdocs build` | rc 0 |
   > | `front check` | 0 errori, 0 avvisi |
   > | `front-utility component-unit` | 154 file, 4.027/4.027 |
   >
   > **E2E, 151/151** (nessun rosso né flaky):
   >
   > | Spec | Test |
   > |---|---:|
   > | asset-list | 28 |
   > | asset-modal | 17 |
   > | asset-data-editor | 26 |
   > | asset-merge | 3 |
   > | asset-mobile-layout | 21 |
   > | asset-classification | 4 |
   > | asset-browse | 8 |
   > | fx-list | 12 |
   > | fx-detail | 17 |
   > | fx-add-pair | 11 |
   > | fx-editor | 4 |
   >
   > **Saltati per il taglio:** fx-csv-import, fx-bulk, fx-sync-mock, live-pause, asset-name-xss, recuperati nella coda
   > del passo 10. Porta libera alla fine.
   >
   > **⚠️ Fuori pista:** fra le 11:53 e le 11:57 la rete è caduta e il turno della sessione AF si è chiuso con un errore;
   > il worktree era pulito. G, che occupava la corsia pesante, è morto con la sua sessione, e il coordinatore ha
   > anticipato il via.
10. ✅ (16/10, 12:45–13:00) **Coda breve** sulla base `0ff61e8c0`: merge di `be911db7e`, con W-B43 (spec di
    `asset-data-editor` e `fx-csv-import` più strette), G-18 e la correzione dello scanner di T (`18824449c`, i commenti
    nelle espressioni del markup).
    > Niente `api sync`: la base non toccava componenti né API.
    > - **Gate:** `--check` pulito; Vitest `themeRoles` + `themeTokens` 71/71 (prima 65: c'è il test nuovo dello scanner).
    > - **E2E, 70/70:** asset-data-editor 26 e fx-csv-import 22 (gli spec nuovi di W-B43), fx-sync-mock 5, fx-bulk 7,
    >   live-pause 8, asset-name-xss 2.
    > - Totale dei due slot: **221 E2E verdi**. Log in `/tmp/libreFolio_af_queueB/`.
11. ✅ (16/10, 13:02) **Ritocco G6** (la regola nuova di T per i campi nativi, `a317392d4`).
    > Il G6 trovava un solo caso nell'albero AF: in `ScheduledInvestmentEditor.svelte:1295` il campo note degli eventi
    > (`placeholder="optional"`) prende `placeholder:text-lf-placeholder`.
    > - **Prove:** `--check`, Prettier, Vitest dei gate 71/71, `git diff --check`. Gli E2E non vanno rifatti
    >   (coordinatore).
    > - **Commit** `5cdf4c307`, poi nel target con A+B+C: **`bfd33a0f5`**.
12. ✅ (16/10, 13:05) **AF-6**: il velo sull'immagine dell'asset (`AssetModalDetails:104–107`). `bg-black/40` passa a
    `bg-lf-overlay` (tabella di `theme-roles`: i fondali neri al 40–50 % vanno su `overlay`), e l'icona `Upload` da
    `text-white` a `text-lf-on-overlay`, il ruolo nuovo di T «icona sul velo».
    > - **Conteggi:** `AssetModalDetails` da 2 a 0 classi legacy; il target da m1 6.734 a 6.732 (`--update`).
    > - **Prove:** `--check` pulito, Prettier ok, `dark_only_check` 0 casi; Vitest dei gate e `AssetModal.test.ts`
    >   103/103.
    > - **Da rivedere:** il velo passa dal 40 % di nero al 60 % del fondale (`#0D1110`), quindi è più scuro.
    >   `on-overlay` è provvisorio (domanda aperta 5 dello skill).
13. ✅ (16/10, 16:53–17:06) **Lotto 9 · dettaglio asset**, dopo l'ingresso di FE5c (`a44951cf5`; base merge
    `10bcf4486`). Conteggio sui file reali: 300 classi, cioè 123 della pagina e 177 dei 7 componenti di `detail/`. Si
    scende a **55**, tutte AF-1: i tre interruttori della barra del grafico nella pagina (42); l'icona dei metadati, le
    tre viola delle misure e l'icona dei segnali (13).
    > **Note implementazione:**
    > - **Analisi breve:**
    >   - nessun ramo locale ha commit fuori dal target su quei file;
    >   - nessun test legge i loro colori (i 6 test di `detail/`, `AssetCurrencyChangeModal.test.ts`, `asset-detail.spec.ts`,
    >     le fixture della galleria);
    >   - analisi approvata dal coordinatore alle 17:0x.
    > - **Bozze:** due sotto-agenti in parallelo, uno sulla pagina e uno sui 7 componenti, riletti da me.
    >   - Pagina:
    >     - radice `text-lf-primary`;
    >     - banner d'errore ambra e cornice dell'editor sul set `warning`, come la pagina dei cambi;
    >     - spinner `text-lf-link`; primari `action`; secondari `bg-lf-panel hover:bg-lf-neutral`.
    >   - Componenti:
    >     - card `bg-lf-card shadow-lf-shadow-card border-lf-subtle`;
    >     - pallino di stato `bg-lf-success`/`bg-lf-danger`;
    >     - chip del tipo `bg-lf-neutral`; badge del fornitore sul set `success`, «Manual» sul set `warning`;
    >     - segmenti prezzi/rendimento e preset delle finestre su `checked`;
    >     - bottoni della barra `bg-lf-card border-lf-subtle hover:bg-lf-hover`.
    > - **AF-4, fatta da me:** `AssetCurrencyChangeModal` passa a `<ModalBase tone="danger">` (T, `4d8ae68c4`), senza più
    >   il `contentClass` di colore; da 2 classi a 0.
    > - **Modifiche non di colore:**
    >   - `tone="danger"`;
    >   - `text-lf-primary` sulla radice della pagina;
    >   - tolta la classe morta `dark:hover:bg-slate-750` (`AssetDetailMeasuresSection:30`: la tonalità 750 non esiste);
    >   - Prettier ha cambiato solo spazi e a capo in 5 file.
    > - **Prove:**
    >   - `--check` pulito, regola 8 a 0, `dark_only_check` 0 su 9 file, `native_field_check` 0 su 10 file;
    >   - compilazione 9/9, Prettier verde, `git diff --check` pulito;
    >   - Vitest dei gate 101/101 dopo C4 (sotto); i Vitest dei componenti li copre `component-unit` nello slot.
    > - **Baseline** (`--update`): m1 da 1.183 a 936, m2 resta 2.
    >
    > **⚠️ Fuori pista — C4:** il lotto ha tolto l'ultimo uso di `text-gray-800` in tutto il frontend, e il gate C4
    > (`themeTokens.gate.test.ts`) ha chiesto di togliere la regola `html.dark .text-gray-800` da `app.css`. L'ho tolta,
    > come prevede il mandato (unica eccezione su `app.css`). Nessun test la leggeva.
    >
    > **Da rivedere:**
    > - il link «Transazioni (n)» passa dal blu al verde dei link (`text-lf-link`, lo skill; OK del coordinatore, nella
    >   raccolta per la designer);
    > - il chip del tipo è più scuro in chiaro;
    > - in scuro i segmenti e i preset attivi hanno il testo scuro sul verde;
    > - in scuro le cornici ambra tornano visibili: prima il rimappaggio di `.rounded-xl` le rendeva grigie;
    > - il bottone di chiusura del banner ha l'hover sulla linea ambra;
    > - in scuro i secondari si staccano poco dalla card (domanda aperta 3);
    > - la nota dell'editor è su `-on-soft/70`.
14. ✅ (16/10, 17:53–18:25) **Slot pesante del lotto 9** sulla base `dc360b486`: lotto 9 e AF-4 committati dal
    coordinatore (codice `8aa3904a6`, docs `8347b7713`), più la merge del target `ce5954329` con J-17.
    > Corsia 6157 + `/tmp/librefolio-r2-af`; taglio alle 18:40, nessun passo nuovo dopo le 18:35. Script
    > `/tmp/libreFolio_af_slotD.sh`, log in `/tmp/libreFolio_af_slotD/`. I worker: 2 per ogni spec partita col carico a
    > 1 minuto sotto 60, altrimenti 1.
    >
    > | Passo | Esito |
    > |---|---|
    > | `api sync` | rc 0 |
    > | `front build --debug` | rc 0 |
    > | `front check` | 0 errori, 0 avvisi |
    > | `front-utility component-unit` | 158 file, 4.092/4.092 |
    >
    > **E2E, 102/102** (nessun rosso né flaky; fra parentesi i worker):
    >
    > | Spec | Test |
    > |---|---|
    > | `front-asset` asset-detail | 34 (1) |
    > | `front-designer-lab` picker | 4 (1) |
    > | asset-browse | 8 (2) |
    > | live-pause | 8 (1) |
    > | asset-modal | 17 (2) |
    > | asset-event-delete | 4 (2) |
    > | asset-event-editor-save | 4 (2) |
    > | `front-portfolio` risk-asset-detail | 5 (2) |
    > | `front-transaction` tx-import-asset-inspector | 5 (2) |
    > | `front-fx` fx-settings | 3 (2) |
    > | fx-destructive | 10 (2) |
    >
    > Porta libera alla fine.
    >
    > **⚠️ Fuori pista — `designer-lab picker` aggiunto dal coordinatore:** il lotto aveva tolto `html.dark .text-gray-800`
    > (C4), che era il soggetto del test dell'override scuro di L-20. Lo spec sceglie dal CSSOM la regola, senza
    > nominarla, ed è passato da solo a un'altra classe ancora rimappata: 4/4.
15. ✅ (16/10, 18:27) **Ingresso nel target: `c179a5144`.** La base merge è `c403534c7`, con la punta `ccfabfd6d`; il
    frontend è identico a quello validato (`dc360b486`), con i gate a 119/119. Target m1 936.
    > **Definition of done (§10):**
    > - lotti 1–9 migrati; l'area scende da m1 1.946 a **170**, tutte con la loro voce AF-n; m2 da 6 a **0**;
    > - `--check` pulito, baseline stretto a ogni checkpoint;
    > - prove leggere e pesanti verdi in tutti gli slot: **323 E2E** (151 + 70 + 102), `component-unit` a ogni slot;
    > - nessun elemento misto nuovo; catene ricontrollate (C1 chiusa con `tone="danger"`); porta libera;
    > - journal e backlog aggiornati, «dove guardarlo» nella sezione 12.
    >
    > **Residuo dell'area, per voce:**
    >
    > | Voce | Classi | Dove |
    > |---|---:|---|
    > | AF-1 | 109 | `fx/[pair]` 54; `assets/[id]` 42; `detail/` 13 |
    > | AF-2 | 23 | `AssetTable` 12; `IdentifierPrimaryChooser` 11 |
    > | AF-3 | 8 | `assets/+page` 4; `fx/+page` 4 |
    > | AF-5 | 18 | `PriceDataImportModal` 6; `EventDataImportModal` 12 |
    > | AF-7 | 12 | `AssetModalFooter` 8; `ScheduledInvestmentEditor` 4 |
16. 🔄 (16/10, dalle 21:09) **I component tokens di file, media e menu contestuale** (richiesta del developer: sull'app
    questi componenti mostravano ancora i colori vecchi, dai letterali di R-3 in `lib/theme/components/*.css`). Base
    `fa16ce787`; fino all'ingresso sono il solo writer di `media.css`, `files.css`, `dialogs.css`. Il metodo è quello di
    T (piano T, «I component tokens, parte 1–2c»), con gli skill `design-system` e `theme-roles`.
    1. ✅ (21:09–21:2x) **Analisi**, approvata dal coordinatore (21:2x).
       > **Note implementazione:** 336 token in **8** componenti: `ImageEditModal` 69, `FileUploader` 54,
       > `FileEditModal` 47, `AssetPickerModal` 45, `ImageCropper` 24 (`media.css`); `FilePreviewModal` 36 e la pagina dei
       > file 45 (`files.css`); `ContextMenu` 16 (`dialogs.css`). Nessuno di questi file ha righe nel baseline dei ruoli:
       > il lavoro è tutto negli `<style>`. Nessun test legge i loro colori (`FilePreviewModal.test` legge `fontFamily`,
       > `files-uploader.spec` overflow, raggio e misure).
       >
       > **⚠️ Fuori pista — il perimetro:** la tabella del coordinatore dava a `FilePreviewModal` tutti gli 81 token di
       > `files.css`; 45 sono della pagina dei file (`routes/(app)/files/+page.svelte`). Il coordinatore ha verificato che
       > nessun ramo la tocca e l'ha aggiunta.
    2. ✅ (21:2x–21:33) **Gli 8 componenti sui ruoli**, con uno script che verifica il testo di partenza
       (`files/ct/ct_transform.py` della sessione: ogni file uguale a HEAD; una mappa per token, con eccezioni per
       selettore; una regola `.dark` si toglie solo se ogni sua dichiarazione legge un token `-dark`).
       > **Note implementazione:** 296 letture sui ruoli (294 nelle regole chiare, più lo spinner della guardia e lo
       > `style` del bottone che svuota l'URL), 129 regole `.dark` tolte, 7 import tolti; 334 token cancellati,
       > `dialogs.css` e `files.css` cancellati, `media.css` ridotto a 2 token. La mappa, sui precedenti di T
       > (`ConfirmModal`, `FileGrid`, `BrokerImportFilesModal`) e del sistema (`DataImportModal`, `SchedulerConfigModal`,
       > `TabBar`):
       > - **neutri:** divisori e cornici `border-subtle`; il menu contestuale `border-raised` con le due ombre su
       >   `shadow-raised` (regola 9); titoli `text-primary`, testi 600–700 `secondary`, muted e faint `muted`; campi
       >   `border-input` su `surface-field` col testo `primary` e il bordo `focus`; i pozzetti dei contenuti
       >   dell'anteprima (pdf, griglia, tabella, testo, markdown) `surface-field`; lo stage dell'immagine, i piedi, il
       >   pannello in basso dell'editor, le aree di caricamento, le testate di tabella e il blockquote `surface-panel`;
       >   le righe al passaggio `surface-hover`; il bottone «svuota» della ricerca `surface-neutral`;
       > - **controlli:** i primari `action`/`action-hover` con `on-action`; segmenti, preset e vista attivi `checked` con
       >   `on-checked` (D-T16); i preset a riposo `surface-card` con `border-input` e testo `secondary`, al passaggio bordo
       >   `focus` e testo `link`; la tab attiva `link` con la sottolineatura `focus`; lo spinner `link` (prima
       >   `--color-libre-green`, una variabile della palette); la matita BRIM al passaggio `link` su `selected`;
       > - **secondari:** quelli dei media e di `FileUploader`, su piedi e aree a `panel`, nello stile 2a di T
       >   (`surface-card`, testo `secondary`, il bordo `subtle` disegnato dentro con `box-shadow: inset`; al passaggio
       >   `surface-hover` e `primary`); quelli della modale della pagina dei file, su `card` e col bordo vero,
       >   `surface-panel` con `border-subtle`, al passaggio `surface-neutral` (domanda aperta 3);
       > - **stati:** i riquadri d'errore `danger-soft`/`-line`/`-on-soft`; lo stato d'errore `danger`; l'errore inline
       >   ambra dell'anteprima `warning`; reset e ripristino `warning-soft` con `warning`, al passaggio `warning-line` con
       >   `warning-on-soft` (domanda aperta 2); la conferma: titolo `warning`, bottone `warning`/`warning-hover` con
       >   `on-status`; il bottone di pericolo `danger-solid`/`danger-hover` con `on-danger-solid`; il disabilitato
       >   `surface-neutral` col testo `muted`; «rimuovi» e la voce di pericolo del menu `danger`, al passaggio
       >   `danger-soft`;
       > - **sull'immagine:** veli, barre e ombra fuori dal ritaglio `surface-overlay`; i bianchi (testo, bordi, maniglie,
       >   contorno della selezione) `on-overlay`, con `color-mix` per l'alfa; i bottoni chiari `surface-card` al 90 % col
       >   testo `secondary`, al passaggio `card` pieno e `link`; gli attivi `checked` al 90 % (l'occhio all'80 %) con
       >   `on-checked`, al passaggio `checked` pieno; l'occhio dell'ellisse `surface-overlay` all'80 %, al passaggio pieno;
       >   la guardia del cropper un velo `surface-card` al 55 %;
       > - **markdown:** `pre` su `terminal-bg`/`terminal-text` (Q6), il codice inline su `surface-panel`.
       >
       > **Regole del sistema applicate** (approvate dal coordinatore, 21:2x): `::placeholder` su `text-placeholder` per i
       > 4 campi col segnaposto (nome del file nei due editor, URL e ricerca del picker); la ricerca del picker come campo,
       > come quella di `FileGrid` (`border-input-hover` al passaggio, `focus` su `:focus-within`: prima `outline: none`
       > senza alcun segno del fuoco, regola 8); `color: var(--lf-text-primary)` sulla radice della pagina dei file
       > (regola 3: il `main` della shell non dà un ruolo di testo); la select della barra della tabella nomina il suo
       > testo `primary` (regola 1, campo nativo).
       >
       > **Due applicazioni in più delle stesse regole**, trovate rileggendo il diff (21:4x, dichiarate nel checkpoint):
       > - la select del formato di `ImageEditModal` aveva `outline: none` senza alcun segno del fuoco: ora
       >   `.format-select:focus` mette il bordo `focus`, come il campo del nome accanto (regola 8);
       > - nella zona di rilascio di `FileUploader`, durante il trascinamento (`selected`), il suggerimento passa da `muted`
       >   a `secondary` (regola 5, TC-15: il muted sulla tinta scende sotto 4,5:1).
       >
       > **Una correzione della mappa:** la select del formato era andata su `surface-field`; la tabella dà al suo
       > grigio-100 `surface-panel`, come all'estensione di `FileEditModal` (lo stesso tassello attaccato al nome del
       > file): ora è `surface-panel`, col bordo `input` e il testo `primary`.
       >
       > **Lasciato legacy:** l'icona immagine blu di `FileUploader`, una categoria (un colore per tipo di file):
       > restano i suoi 2 token in `media.css`, con la regola `.dark` e l'import di `FileUploader`. Tiene anche verde il
       > punto (e) del gate dei token quando T svuoterà `table.css`.
       >
       > **Tolti senza sostituto:** il bordo solo scuro della conferma di `ImageEditModal`, una seconda cornice dentro
       > `ModalBase` (regola 9); il testo solo scuro del pdf, che eredita già `primary` da `ModalBase`; lo sfondo scuro
       > del contenitore dei bottoni della vista, coperto dai bottoni.
       >
       > **Da rivedere** (nella raccolta per la designer, dal coordinatore): il file «modificato» di `FileUploader` su
       > `info`, con la matita al passaggio `info-soft`/`info` (su un file modificato il passaggio resta `info-soft`: il
       > segno è il colore dell'icona); il fondo del cropper su `terminal-bg` (scuro nei due temi, coperto dalla
       > scacchiera del canvas; T può dare un ruolo «stage»); i bordi forti (cornice del pdf, barra del blockquote) su
       > `border-input`, perché `subtle` sparirebbe in scuro; le voci di `ContextMenu` su `primary`, come gli altri menu;
       > i trascinamenti sulla zona di caricamento su `selected` (col suggerimento a `secondary`, sopra); la zona di
       > rilascio al passaggio su `surface-hover`, che oggi è uguale a `panel` (domanda aperta 3): il segno del passaggio
       > resta il bordo `focus`; gli hover sull'immagine fatti con gradini d'alfa dello stesso ruolo.
    3. ✅ (21:52–21:53) **Prove leggere**, una alla volta sotto `nice -n 19` (via del coordinatore alle 21:46: il carico,
       fra 52 e 247, era soprattutto attesa di I/O).
       > | Prova | Esito |
       > |---|---|
       > | Prettier `--check` sui 9 file | verde |
       > | `theme-roles.mjs --check` | pulito (0 file sotto il record) |
       > | Compilatore di Svelte 5.48, HEAD e albero a confronto (`/tmp/libreFolio_af_ct_compile.mjs`) | 0 avvisi prima e dopo negli 8 file; le 8 regole aggiunte arrivano nel CSS; `.dark` e `--lf-cmp-` restano solo nella regola dell'icona di `FileUploader` |
       > | Vitest `themeComponentTokens.gate` | 18/18 |
       > | Vitest `themeRoles.gate` | 80/80 |
       > | Vitest `themeTokens.gate` | 21/21 |
       > | `dark_only_check` e `native_field_check` | 0 e 0 sugli 8 file |
       > | `git diff --check` | pulito |
       >
       > Porta 6157 libera: nessun server avviato.
    4. 🔄 (16/10, 22:04–22:47) **Slot pesante E**, nella 6157 su `943d46378` (codice `4b1b74ab2`, docs `03324bac3`, base
       merge con la punta `bf2c22791`): la 1.3 ha prestato il suo slot 2; nessun passo nuovo dopo le 22:45. Script
       `/tmp/libreFolio_af_slotE.sh` (controlla HEAD, albero pulito e porta libera prima di partire), log in
       `/tmp/libreFolio_af_slotE/`. Tutte le E2E con 1 worker: il carico a 1 minuto era fra 65 e 151 a ogni partenza.
       > | Passo | Esito |
       > |---|---|
       > | `api sync` (la merge cambia 5 file dell'API) | rc 0 |
       > | `front build --debug` | rc 0 |
       > | `front check` | 0 errori, 0 avvisi |
       > | `front-utility component-unit` | 163 file, 4.246/4.246 |
       > | E2E `front-utility` files | 29/29 |
       > | image-crop | **41/42**: F1 rosso, sotto |
       > | files-uploader | 8/8 |
       > | files-destructive | 6/6 |
       > | files-pdf-offline | 1/1 |
       > | `front-broker detail`, `front-asset asset-list`, `front-transaction tx-import-upload` | non partite (taglio) |
       >
       > Porta libera alla fine; HEAD `943d46378`, albero pulito.
       >
       > **⚠️ Fuori pista — `image-crop` F1 («ImageEditModal renders in dark mode»), triage con lo skill `test-triage`:**
       > - l'asserzione (`expect(hasDark).toBeTruthy()`, riga 647) fallisce subito, dopo 8,7 s di corpo: non è un timeout;
       > - lo screenshot mostra la pagina **in chiaro**, con la modale giusta sui ruoli: il `beforeEach` non ha prodotto il
       >   tema scuro. Decide se cliccare il toggle con due `isVisible()` istantanei: sul toggle, senza attenderlo (carico
       >   97), e sul primo elemento `[class*="dark"]` della pagina (`.first()` su un locatore non filtrato). F1 accetta come
       >   prova lo stesso ripiego sulle classi, che la migrazione svuota: le classi `dark:` spariscono;
       > - il lotto non c'entra: non cambia nessuna classe del DOM (0 righe con «dark» tolte; gli hash di scoping degli 8
       >   componenti sono uguali prima e dopo), né il toggle, né `themeStore`, né il login;
       > - **verdetto: assunzione** (§1 e §2 dello skill). La correzione: aspettare il toggle, leggere e asserire
       >   `html.dark` con `toHaveClass`, togliere il ripiego sulle classi. La spec non è dell'area AF: la scrive test-author
       >   con l'OK del coordinatore, poi F1 si rilancia da solo (AF-12).
       >
       > **⚠️ Fuori pista — una build in più:** `files-uploader` ha rifatto la build del frontend («Frontend sources changed,
       > rebuilding...», circa 7 minuti col carico a 160), perché macOS ha toccato `frontend/src/.DS_Store` alle 22:29:54.
       > Il controllo di freschezza del runner (`check_frontend_needs_build` in `scripts/cli_base.py`) confronta l'mtime di
       > ogni file sotto `src/`, file nascosti compresi. Senza, `front-broker detail` sarebbe probabilmente partita prima
       > del taglio (AF-13).
       >
       > **Restano per uno slot di recupero:** `front-broker detail`, `front-asset asset-list`,
       > `front-transaction tx-import-upload`, e F1 da solo.
    5. ✅ (16/10, 22:49–23:00) **La correzione di `image-crop` F1** (AF-12; OK del coordinatore alle 22:49, «nel tuo lotto,
       con un commit solo test»): test-author, sulla sola spec `frontend/e2e/image-crop.spec.ts`, blocco «Dark Mode - Image
       Crop Components».
       > **Note implementazione:** prima ho verificato che nessun ramo locale ha commit sulla spec oltre il mio HEAD
       > (`332b9e268`, letti solo i ref). Il `beforeEach` aspetta il toggle del tema (`toBeVisible`), legge la classe di
       > `<html>`, clicca solo se non è scuro e asserisce `html.dark` con `toHaveClass`; F1 asserisce lo stesso con la
       > modale aperta, dopo la navigazione a `/files` e il caricamento. Niente più ripiego sulle classi `dark:`, nessun
       > `isVisible()` istantaneo usato come attesa. Il tema regge alla navigazione: `app.html` lo riapplica da
       > `localStorage` prima del primo disegno, e lo cambiano solo il login, il toggle e il salvataggio delle preferenze.
       > Prove leggere: Prettier verde; `tsc` sul solo file con le opzioni di `tsconfig.e2e.json` verde; `git diff --check`
       > pulito. L'E2E va nello slot di recupero: il runner non filtra per titolo, quindi gira tutta `image-crop` (42
       > test), che copre F1–F3 (lo stesso `beforeEach`).
       >
       > **Resta debole** (fuori dall'OK): F2 e F3 decidono con `isVisible()` istantanei se aprire le modali, e possono
       > passare senza aprirne nessuna; nessuno dei due verifica il tema. Seguito possibile, annotato in AF-12.
    6. ✅ (16–17/10, 23:37–00:09) **Slot di recupero**, nella 6157 su `285a1cb39` (base merge del coordinatore con la
       punta `db506eb21`: FE8b, B, E e J della 1.3; i commit `f2f13184b` e `391087b35` dentro). Nessun passo nuovo dopo
       le 00:30. Script `/tmp/libreFolio_af_slotR.sh`, con la scadenza assoluta (il taglio passava la mezzanotte); log in
       `/tmp/libreFolio_af_slotR/`.
       > | Passo | Esito |
       > |---|---|
       > | `api sync` | rc 0 |
       > | `front build --debug` | rc 0 |
       > | E2E `front-utility` image-crop (1 worker) | **42/42**, F1–F3 compresi, col nuovo `beforeEach` |
       > | `front-broker detail` (1 worker) | 37/38; **rilanciata da sola: 38/38** |
       > | `front-asset asset-list` (1 worker) | 30/30 |
       > | `front-transaction tx-import-upload` (2 worker) | 10/10 |
       >
       > Porta libera alla fine; HEAD `285a1cb39`, albero pulito. Con lo slot E, tutte le spec dell'elenco del lotto sono
       > verdi.
       >
       > **⚠️ Fuori pista — `brokers-detail`, «clicking the "Analyze Lots" row action opens the FIFO lots panel»:** un
       > timeout nell'helper `goToBrokerWithHoldings`. Dopo il clic sulla card di Interactive Brokers la pagina del
       > dettaglio non era montata entro 10 s: l'istantanea mostra ancora la lista dei broker, col carico fra 80 e 113.
       > Rilanciata da sola (carico 59, 1 worker): 38/38 in 2,8 minuti, contro i 5,2 della prima corsa. Verdetto del
       > triage: lentezza sotto il carico della macchina, non il lotto. Il lotto non tocca la lista dei broker né la
       > navigazione, e gli altri 37 test passano con lo stesso helper.
       >
       > **⚠️ Fuori pista — AF-13 di nuovo:** macOS ha toccato `frontend/src/.DS_Store` alle 23:52:26, e `asset-list` ha
       > rifatto la build all'avvio.
17. ✅ (17/10, 00:14–03:29) **`lib/theme/drawnColors.ts` sui ruoli**, fuori area (`lib/theme`, dichiarato), richiesta del
    coordinatore dopo l'ingresso `9d3607eb6`. Sono i 32 letterali slate (17 distinti) del rapporto di L
    (`L-designerLab/audit-colori-fuori-metrica.md`, riga 2): il tema scuro del foglio di cheetah-grid in
    `FilePreviewModal` (26), i due bordi del foglio in chiaro, la riga indicata, i segnaposto di `LazyImage` (2),
    l'iniziale degli avatar di `FilesTable`.
    1. ✅ (00:14–00:20) **Analisi.** Tutti disegnati fuori dal CSS (canvas e SVG in data URL), quindi ogni ruolo si legge a
       runtime con `chartRoles(dark, scope)` di `roleColors.ts` (DV). L'API di allora leggeva 7 ruoli: la mappa 1:1 ne
       chiedeva altri, e un tema mezzo ruoli e mezzo slate sullo stesso canvas è il caso del G3. **Decisione del
       coordinatore:** in fila dopo B4, tutto in un colpo; DV aggiunge 8 ruoli (`--lf-surface-field`,
       `--lf-surface-hover`, `--lf-selected`, `--lf-checked`, `--lf-focus`, `--lf-action`, `--lf-on-action`,
       `--lf-mark-bg`); `--lf-warning`, `--lf-text-muted`, `--lf-border-subtle`, `--lf-border-input` e
       `--lf-surface-neutral` arrivano già con B4.
       > **Scelte provvisorie** (approvate, punto 35 della raccolta per la designer): la riga indicata su `mark`
       > (risultato evidenziato, Q7; distinta dalla selezione); l'iniziale dell'avatar con `readableText(disco)` (l'uso
       > che `roleColors` documenta: su un disco chiaro diventa scura); in chiaro resta il tema `MATERIAL_DESIGN` della
       > libreria, coi soli due bordi sui ruoli.
    2. ✅ (00:20–00:46) **Le bozze, su copie** (cartella della sessione `files/drawn/`), verificate in una sandbox in
       `/tmp` col `roleColors.ts` di B4 letto dal ref di DV più gli 8 ruoli simulati: `tsc` verde, le tre bozze Svelte
       compilate senza avvisi, il test d'unità di test-author 13/13 con 13 mutazioni tutte prese.
       > **⚠️ Fuori pista — `oklab()` dal canvas** (segnalato da test-author, verificato in Chromium 149): il `fillStyle`
       > di un canvas restituisce `color-mix(in oklab, …)` come `oklab(… / 0.12)`, non come `rgba()`, contro il commento
       > di `roleColors`; `parseRgba` non lo legge, e la selezione del foglio sarebbe rimasta traslucida. cheetah-grid non
       > pulisce la cella prima di riempirla (`_drawCell`), quindi un fondo traslucido si somma ai pixel di prima: la
       > selezione va composta sul campo e resa opaca. **Decisione del coordinatore: opzione 1**, la correzione è in
       > `roleColors.resolve()` (DV, col commit dei ruoli): sempre sRGB, `#rrggbb` o `rgba()`. Il mio ripiego locale su
       > un canvas 1×1 è stato tolto dalle bozze. Due sonde in Chromium lanciate col carico a 53 e 64, sopra la soglia.
    3. ✅ (01:53–01:56) **Applicazione** su `323c61b73` (B4 e gli 8 ruoli entrati; i quattro file uguali alle copie
       delle bozze):
       > **Note implementazione:**
       > - `drawnColors.ts`: costruttori da un `ChartRoles`, senza letterali (19 righe di letture letterali
       >   `roles.color('--lf-…')`, come vuole il gate dei lettori): `buildDarkSpreadsheetTheme(roles)`,
       >   `spreadsheetLightBorders(roles)`, `spreadsheetTargetRowBg(roles)`, `imagePlaceholderColors(roles)`,
       >   `fileAvatarInitialColor(roles, disco)`. La mappa del tema scuro: celle `field`, intestazioni `panel` con testo
       >   `secondary`, testo `primary`, cella attiva `hover` col bordo `focus`, selezione `selected` composta sul campo
       >   (opaca), linee `border-subtle`, bordo delle intestazioni e dei controlli vuoti `border-input`, freccia
       >   d'ordinamento `muted`, controlli spuntati `checked`, bottone `action` con `on-action`, messaggi `info`,
       >   `danger`, `warning` (il riquadro prende lo stato, il segno il fondo della cella). Segnaposto: fondo `neutral`,
       >   figura `muted`.
       > - `FilePreviewModal`: `chartRoles(isDarkTheme(), host)` sull'elemento della griglia, quando la griglia si
       >   costruisce (come prima, il tema si sceglie all'apertura).
       > - `LazyImage`: i colori del segnaposto sono uno stato, letti sul contenitore (`bind:this`, unica aggiunta al
       >   markup) mentre il segnaposto si vede, e di nuovo al cambio di tema o a una modifica del Designer Lab; gli
       >   osservatori si staccano quando l'immagine arriva.
       > - `FilesTable`: l'iniziale con `readableText` quando l'avatar si costruisce.
       > - `roleColors.test.ts` (di DV): `PENDING_READERS` svuotato, gli 8 ruoli ora letti; `_frontend_utility.py`: il
       >   nuovo `drawnColors.test.ts` nella lista di `core-unit`.
    4. ✅ (01:54–01:56) **Prove leggere** (`nice -n 19`, carico 42–46): Prettier verde sui 6 file del frontend;
       `theme-roles.mjs --check` pulito; il compilatore di Svelte sui tre componenti, 0 avvisi prima e dopo;
       `py_compile` del runner; Vitest **8 file, 286/286** (`drawnColors`, `roleColors` e `roleColors.dom`, i tre gate
       dei colori, `FilePreviewModal.test`, `FilesTable.test`); `git diff --check` pulito.
    5. ✅ (17/10, 03:06–03:29) **Slot F** nella 6157 su `c37c55649` (codice `cfa78f210`, docs `fd6e7b3d9`, base merge
       con la punta `2818924b7`: X O-8, H-27, E-11; il runner si è unito da solo con quello della 1.3, la riga di
       `drawnColors.test.ts` c'è). Nessun passo nuovo dopo le 03:40. Script `/tmp/libreFolio_af_slotF.sh`, log in
       `/tmp/libreFolio_af_slotF/`.
       > | Passo | Esito |
       > |---|---|
       > | `api sync`, `front build --debug` | rc 0 |
       > | `front check` | 0 errori, 0 avvisi |
       > | `front-utility component-unit` | 166 file, 4.418/4.418 |
       > | E2E `front-utility files` (2 worker) | 29/29 |
       > | `front-transaction tx-import-report-set` (1 worker) | 32/32; gli altri 32 sono i test dell'altro progetto (desktop o mobile), saltati per contratto |
       > | `front-asset asset-list` (1 worker) | 30/30 |
       > | `front-utility image-crop` (2 worker) | 42/42 |
       >
       > Nessuna build in più (AF-13 non si è ripetuto); porta libera alla fine; HEAD `c37c55649`, albero pulito.

## 12. Dove guardarlo (per il developer)

- **A, lotti 1–3:**
  - `/fx` in griglia e lista: card (hover, fuoco, %, «Manual», icone, sync disabilitata), segmenti assoluto/%, stati
    vuoto, errore e caricamento;
  - `/fx/<coppia>`: banner ambra, cornice di «Modifica tassi», nessun dato (manuale e non). Gli interruttori della barra
    non cambiano (AF-1);
  - modali «Aggiungi coppia» e import CSV dei cambi;
  - `/assets`: card attive e inattive (superficie ambra, hover, lampeggio dei prezzi), riga inattiva della lista,
    pallini di stato, ‹ n/N › del dettaglio;
  - il riepilogo del prezzo nella pagina del dettaglio.
- **B, lotti 4–7:**
  - modale asset: campi, quantità di base non valida, avvisi d'importazione, fornitore, identificativi, velo
    sull'icona (AF-6);
  - ricerca (chip dei fornitori, tendina), test del fornitore, confronto con il fornitore, scelta dell'identificativo
    primario, anche dentro il wizard d'importazione;
  - cambio valuta, unione di asset, taglio o eliminazione delle date, import CSV di prezzi ed eventi;
  - editor dell'investimento programmato, col segnaposto delle note (G6).
- **C, lotto 8:** la barra di `/assets` (ricerca, filtri attivi e inattivi, tipo, pastiglie delle valute, segmenti).
- **Galleria:** le scene `fx-*`, `assets*`, `asset-modal*`, `asset-detail-*`.
- **D, lotto 9:**
  - il dettaglio asset `/assets/<id>`: intestazione (pallino di stato, chip del tipo, link «Transazioni (n)» ora verde,
    badge del fornitore o «Manual», ‹ n/N ›);
  - la barra delle azioni; i segmenti prezzi/rendimento; i preset delle finestre del rendimento;
  - il banner d'errore, la cornice «Modifica dati», i pannelli segnali, misure e metadati;
  - nessun dato: i bottoni sincronizza e inserisci a mano;
  - la modale del cambio valuta, ora con la cornice `tone="danger"`.
- **E, i component tokens (passo 16)**, in chiaro e in scuro:
  - `/files`: l'intestazione coi bottoni della vista, l'area di caricamento con `FileUploader` (zona di rilascio al
    passaggio e trascinando un file, elenco dei file, un file modificato, errori, bottoni), la modale BRIM (riga
    «assegna a tutti», righe dei file, matita al passaggio, conferma disabilitata), la conferma di chiusura;
  - l'anteprima di un file: barra, interruttore della vista, immagine, pdf, tabella, testo, markdown (citazione,
    tabella, codice e blocco di codice);
  - l'editor dell'immagine (dall'avatar o da un'icona): guardia di caricamento, occhio dell'ellisse, preset, campi, piede,
    conferma di chiusura; il cropper coi bottoni sopra l'immagine; l'editor del file e il picker degli asset (URL con
    l'anteprima circolare, ricerca, griglia e lista);
  - il menu contestuale di una tabella (clic destro su una riga), con la voce di pericolo.
- I «da rivedere», lotto per lotto, sono nei passi 2–8, 12, 13 e 16.
