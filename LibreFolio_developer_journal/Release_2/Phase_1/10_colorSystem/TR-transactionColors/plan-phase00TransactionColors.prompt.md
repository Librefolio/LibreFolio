# Piano — Workstream TR, colori delle transazioni (migrazione 1:1 ai ruoli)

> **Workstream TR del programma colori**, sessione «TR - colori delle transazioni». Coordinatore: sessione «UI color
> analysis» (`aec04834-1532-4d86-9e3f-f942e82aca89`).
> Branch `e-alfy-tr-transaction-colors` (rinominato dall'app; prima `e-alfy-sturdy-chainsaw`).
> - **Baseline dell'analisi:** `8f2824046` (fast-forward del coordinatore da `dae4de4fa`, verificato alle 10:45).
> - **Base attuale:** `6e569084a`, fast-forward del coordinatore con lo skill comune `design-system` di T (D-T29);
>   nessun file dell'area è cambiato.
> - **Corsia:** porta **6154**, dati **`/tmp/librefolio-r2-tr`**.
> - **Comandi:** `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6154 --data-dir /tmp/librefolio-r2-tr …`.
>
> **Fonti:**
> - [piano generale](../plan-phase00ColorSystemThemeLab.prompt.md) (D-T27, D-T28, D-T29, corsie);
> - skill [`theme-roles`](../../../../../.github/skills/design-tools/theme-roles/SKILL.md) (tabella classe → ruolo,
>   baseline) e [`design-system`](../../../../../.github/skills/design-tools/design-system/SKILL.md) (temi, palette,
>   regole 1–11, domande aperte);
> - giro 2 della designer: [README](../designer-feedback/2026-10-15-round2-palette/README.md);
> - piano di W (1.3): [`04_importTransactions`](../../04_importTransactions/plan-phase01ImportTransactions.prompt.md)
>   (FE8b, la coda di W).
>
> **Regola:** migrazione 1:1 ai ruoli, senza cambiare markup, layout o comportamento, e senza decisioni di design.
> Dove la tabella non basta l'elemento resta com'è, intero, ed è annotato qui e nel backlog (sezione TR).

## ✅ Autorizzazione

- **16/10, analisi consegnata al coordinatore** (messaggio delle ~11:05). Il piano è stato approvato nella sessione TR
  (plan mode chiuso con approvazione); D-T28 delega al coordinatore i piani «solo migrazione 1:1».
- **In attesa di risposta** (non bloccano la scrittura dei lotti, che seguono le scelte conservative sotto):
  1. OK di W su `e2e/transactions/tx-wac-mode.spec.ts:152,180,205,230` (`toHaveClass(/bg-libre-green/)` →
     `aria-pressed`);
  2. il sottotitolo della pagina fissato dallo spec del picker di L;
  3. il ruolo mancante `success-hover`;
  4. la base della tinta del broker, insieme a BK;
  5. gli slot pesanti A e B;
  6. FE8b di W dopo TR.

## 1. Inventario dal baseline

`node frontend/scripts/theme/theme-roles.mjs --report` su `8f2824046` (carico 42, `nice -n 10`): totale m1 8.249 /
m2 54, ratchet 0 violazioni, grammatica 0. La mia area: **20 file con colori, m1 1.052, m2 33** (34 file in tutto; 14 a
zero, fra cui `cells/*`, `EventExistsPanel.svelte` già sui ruoli e i `.ts`).

Legenda: N neutri · B marchio (libre-*, link, selezione, azione) · S stati · G segni · C categorie (lasciate, con i
neutri dei loro stessi elementi) · I interruttori (lotto di T) · X lasciati per ruolo mancante o vincolo.

| File | m1 | m2 | N | B | S | G | C | I | X | migro | resta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `routes/(app)/transactions/+page.svelte` | 37 | 0 | 23 | 8 | 6 | 0 | 0 | 0 | 2 | 35 | 2 |
| `TransactionsTable.svelte` | 6 | 25 | 6 | 0 | 0 | 0 | m2 4 | 0 | m2 9 | 6 + m2 12 | m2 13 |
| `modals/TransactionActionModal.svelte` | 146 | 4 | 137 | 0 | 9 | 0 | 0 | 0 | 5 | 141 + m2 4 | 5 |
| `modals/PromoteMergeModal.svelte` | 100 | 4 | 42 | 0 | 4 | 0 | 54 (+8 N) | 0 | 3 | 35 + m2 4 | 65 |
| `modals/TransactionFormModal.svelte` | 35 | 0 | 30 | 3 | 2 | 0 | 0 | 0 | 0 | 35 | 0 |
| `form/TxFormBanners.svelte` | 6 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| `form/TxFormOptionalSection.svelte` | 25 | 0 | 18 | 1 | 0 | 0 | 6 | 0 | 0 | 19 | 6 |
| `form/TxFormPairSection.svelte` | 93 | 0 | 71 | 4 | 14 | 0 | 4 | 0 | 0 | 89 | 4 |
| `form/TxFormSingleSection.svelte` | 50 | 0 | 44 | 0 | 6 | 0 | 0 | 0 | 0 | 50 | 0 |
| `shared/TransactionTypeSearchSelect.svelte` | 4 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 4 | 0 |
| `wac/WacPreviewSection.svelte` | 94 | 0 | 49 | 10 | 20 | 0 | 15 (+6 N) | 0 | 0 | 73 | 21 |
| `events/AssetEventPicker.svelte` | 72 | 0 | 46 | 10 | 4 | 0 | 12 | 0 | 0 | 60 | 12 |
| `events/EventCreateMiniModal.svelte` | 42 | 0 | 35 | 6 | 1 | 0 | 0 | 0 | 0 | 42 | 0 |
| `modals/TransactionBulkModal.svelte` | 88 | 0 | 53 | 2 | 24 | 0 | 9 | 0 | 0 | 79 | 9 |
| `bulk/TxBulkBanners.svelte` | 54 | 0 | 12 | 5 | 35 | 0 | 2 | 0 | 0 | 52 | 2 |
| `bulk/TxBulkToolbar.svelte` | 48 | 0 | 31 | 3 | 10 | 0 | 4 | 0 | 0 | 44 | 4 |
| `shared/TransactionResultBanner.svelte` | 18 | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 0 | 18 | 0 |
| `modals/TransactionPickerModal.svelte` | 20 | 0 | 18 | 2 | 0 | 0 | 0 | 0 | 0 | 20 | 0 |
| `modals/PromoteAllModal.svelte` | 32 | 0 | 23 | 9 | 0 | 0 | 0 | 0 | 0 | 32 | 0 |
| `modals/TransactionCompareModal.svelte` | 82 | 0 | 64 | 2 | 12 | 0 | 0 | 4 | 0 | 78 | 4 |
| **Totale** | **1.052** | **33** | | | | **0** | | | | **918 + m2 20** | **134 + m2 13** |

Atteso dopo TR: m1 1.052 → 134 (−87 %), m2 33 → 13. Segni (gain/loss): zero nell'area; il bordo col segno della
quantità è di T (`ExactQuantityInput`), già sui ruoli.

### Cosa resta, e perché
- **C, 120:**
  - tipi d'evento (`AssetEventPicker`, `typeConfig`: DIVIDEND ambra, INTEREST blu, SPLIT viola, PRICE_ADJUSTMENT e
    default grigi, MATURITY verde): 12;
  - codifica A/B della fusione (`PromoteMergeModal`: A blu, B rosa, «unisci» indaco, con i neutri degli stessi
    elementi): 62;
  - chip FX viola (`TxFormPairSection:360`, `TxBulkBanners:346`);
  - promozione indaco (`TxBulkToolbar:152`, `TxFormOptionalSection:87`, `TransactionBulkModal:1921`);
  - split viola (`TransactionBulkModal:1597,1672,3122`);
  - WAC: riga e pallino «in attesa» indaco, badge d'effetto add/reduce/add_at_wac (`WacPreviewSection:535,539,574–579`):
    21.
- **I, 4:** l'interruttore di `TransactionCompareModal:188–191`, nel lotto unico di T (domanda aperta 4 dello skill
  `design-system`).
- **X, 10:**
  - pulsanti pieni verdi con hover `green-700`, senza un ruolo `success-hover` (`PromoteMergeModal:262`;
    `TransactionActionModal:387`, col ramo ambra sullo stesso elemento): 8;
  - sottotitolo della pagina (`+page.svelte:738`), fissato dallo spec del picker del Designer Lab: 2.
- **m2 13**, nello `<style>` di `TransactionsTable`:
  - base della tinta del broker `white`/`#0f0f18` (4): la stessa ricetta di BK in `UnifiedLotsTable`, via
    `--lf-cmp-lots-table-row-tinted-bg`;
  - hover traslucido dell'icona del tipo `rgb(0 0 0/.05)`/`rgb(255 255 255/.08)` (2): nessun ruolo traslucido, e un
    valore unico sarebbe una scelta;
  - pallino evento viola (4): C;
  - impulso di riga indaco (3): nessun ruolo d'evidenza.

## 2. Catene di classi che escono dall'area

- **Pulite, nessun colore attraversa il confine:**
  - `overflowScrollTextClass` (`utils/overflowScroll.ts`): senza colori;
  - `ModalBase contentClass="max-w-[95vw] w-[95vw]"`: ModalBase ha già `border-lf-raised text-lf-primary`;
  - `BrokerBadge` `rootClass`/`nameClass` (`tx-broker-cell`, `tx-broker-name`);
  - `CompactCashCell` e `Tooltip`: solo testo;
  - `TransactionTypeSearchSelect`, usato da `import/FixFlaggedStep` (IW) senza classi;
  - `TransactionCompareModal`, usato da `ImportWizardModal` (IW) con l'HTML di `cell.display` scritto da IW;
  - il `className` di `ExactQuantityInput`: già ruoli (T).
- **Fuori area, lasciate:**
  - stati di riga del Bulk (`row-deleted/edited/appended/todo-blocker`, `highlighted`), disegnati da `DataTable.svelte`
    e `lib/theme/components/table.css` (T, W6);
  - tinta del broker (`getBrokerColor`, `--broker-*`) e tavolozza dei tag (`--badge-*` di `utils/colors.ts`):
    categoriali;
  - tooltip Q10 (`WacPreviewSection:321–322`, già ruoli) e `fxConversionHelper.ts` (T).
- **Dentro l'area, da tenere insieme:**
  - `TransactionActionModal`, `borderColor` (`:85`, usato in 4 elementi);
  - `cfg.bg` di `AssetEventPicker`: elementi senza altri colori, nessun misto a runtime;
  - l'HTML delle celle (`TransactionsTable`, `TransactionBulkModal`, `cells/*`), stilato dallo `<style>` di
    `TransactionsTable`;
  - `TransactionResultBanner`, con lo snippet `titleAction` di `TxBulkBanners`.
- **C4 (`app.css`):** nessuna delle 19 classi del rimappaggio scuro usate nell'area è usata solo nell'area: nessun
  selettore da togliere (ricontrollo all'ingresso).

## 3. Test che asseriscono colori

| Test | Righe | Proprietario | Effetto di TR | Azione |
|---|---|---|---|---|
| `e2e/transactions/tx-wac-mode.spec.ts` | 152, 180, 205, 230: `toHaveClass(/bg-libre-green/)` | W (1.3) | rotto da TR-2 | → `toHaveAttribute('aria-pressed', …)`, già pubblicato dal componente (come `tx-wac-unit-toggle:137–139`); test-author, **con l'OK** |
| `e2e/designer-lab/designer-lab-picker.spec.ts` | test «dark-theme pick of a text-gray-500 element»: precondizione `text-gray-500` sul sottotitolo | L | rotto se il sottotitolo migra | il `<p>` resta legacy finché L non sposta il soggetto |
| `e2e/designer-lab/designer-lab-live.spec.ts` | L1, sospensione, export: il sottotitolo via `colourSourceOf` | L | pronto ai ruoli | nessuna |
| `e2e/transactions/tx-wac-bulk.spec.ts` | 676: `span.text-indigo-500` | W | invariato (categoria lasciata) | data-attribute col passaggio categoriale |
| `e2e/transactions/transactions-modals.spec.ts` | 1171–1203 | W (righe di T) | invariato (ruoli di T) | nessuna |
| `TransactionFormModal.test.ts` | 351–353, 791–792, 833–837 | W (righe di T) | invariato | nessuna |
| Vitest dell'area senza colori: `PromoteAllModal`, `PromoteMergeModal`, `TransactionCompareModal`, `WacPreviewSection`, `EventExistsPanel`, `TransactionsTable.privacy`, `resolveFormItems`, `eventSaveError`, `filterState` | — | W | reti di regressione | girano invariati |

## 4. File dell'area aperti altrove (verifica del 16/10, sola lettura)

Fatta con `git --no-optional-locks status`, gli hash dell'indice e i refs.
- Nessun worktree ha modifiche sue nella mia area.
- **X (`e-alfy-cuddly-engine`):** merge di base in corso (`MERGE_HEAD 69c95454b`, antenato del baseline). Ha in stage 6
  miei file **identici al baseline** (`TxFormPairSection`, `TxFormSingleSection`, `PromoteMergeModal` e il suo test,
  `TransactionFormModal` e il suo test): traffico della merge, nessun conflitto.
- **W (`e-alfy-fluffy-meme`):** pulito; nessun commit non integrato nella mia area.
- Nessun ramo locale ha commit non integrati nella mia area: solo il vecchio `preview-colori-1015`, sullo spec del
  picker. Il checkout principale non è stato ispezionato (regola).
- **Piani della 1.3 sui miei file:**
  - FE8b di W (spostamento in `features/transactions`, ⏳ «dopo il lotto D»): rischio di rinomine;
  - coda attuale di W (N2, W-B20, A-14, decisione 47): solo backend e doc.

## 5. Convenzioni applicate

Dallo skill `design-system` (16/10) e dai precedenti di T:

| Oggi | Ruolo | Fonte |
|---|---|---|
| campo (`input`, `textarea`, trigger): `border-gray-200/300 bg-white` + `dark:` | `border-lf-input bg-lf-field hover:border-lf-input-hover`, fuoco `focus:border-lf-focus focus:ring-lf-focus/…` | W1-a di T (`1c16151a1`), D-T18 |
| riquadro in sola lettura e testate di tabella `bg-gray-50` + `dark:` | `bg-lf-panel` | tabella `theme-roles` |
| Annulla `bg-gray-100/200 text-gray-6/700 hover:bg-gray-200/300` + `dark:` | `bg-lf-panel text-lf-secondary hover:bg-lf-neutral` | domanda aperta 3; precedenti di T |
| pulsante fantasma `text-gray-600 hover:bg-gray-100` + `dark:` | `text-lf-secondary hover:bg-lf-hover` | tabella |
| chiudi (X) `text-gray-400 hover:text-gray-600 hover:bg-gray-100` | `text-lf-muted hover:text-lf-secondary hover:bg-lf-hover` | tabella |
| menu flottante `bg-white border-gray-200 shadow-xl` + `dark:` | `bg-lf-card border-lf-raised shadow-xl shadow-lf-shadow` | regola 9, N3, Q8 |
| card della pagina `bg-white shadow-sm border-gray-100` + `dark:` | `bg-lf-card shadow-sm shadow-lf-shadow-card border-lf-subtle` | regola 9 |
| verde tenue `bg-libre-green/10 text-libre-green hover:bg-libre-green/20` + `dark:` | `bg-lf-selected text-lf-link hover:bg-lf-checked/20` | `DataEditor.svelte:671` |
| riga «crea nuovo» `text-libre-green hover:bg-libre-green/10` + `dark:` | `text-lf-link hover:bg-lf-selected` | `SearchSelect.svelte:564` |
| opzione scelta `border-libre-green bg-green-50` + `dark:` | `border-lf-checked bg-lf-selected` | D-T16 |
| cursore, radio `accent-libre-green` | `accent-lf-checked` | D-T16, precedenti PAC |
| pulsante su tinta di stato `bg-X-100 hover:bg-X-200` + `dark:` | `bg-lf-X-line/50 hover:bg-lf-X-line` | `STATUS_TONES.dataQuality`, domanda aperta 2 |
| `<mark>` ambra | `bg-lf-mark text-lf-on-mark inset-ring inset-ring-lf-mark-line` | Q7, `ChangelogModal.svelte:170` |
| fallback dei chip dei tag in `<style>` | `var(--badge-*, var(--lf-surface-neutral))`, testo `var(--lf-text-secondary)` | `TagInput.svelte` |
| testi della cassa in `<style>` (`#1e293b`/`#e2e8f0`, `#475569`/`#cbd5e1`) | `var(--lf-text-primary)`, `var(--lf-text-secondary)`, una regola sola | tabella |

Regole sempre applicate:
- elemento intero (G3, comprese tutte le alternative di un attributo `class`);
- niente `dark:` sui ruoli;
- regola 8 (un ternario per proprietà);
- classi letterali intere;
- `text-lf-primary` sulla radice della pagina (le modali lo prendono da `ModalBase`).

## 6. Lotti

File disgiunti: scritti in parallelo da sotto-agenti, rivisti elemento per elemento. Un commit per lotto. Ogni lotto
aggiorna `frontend/src/themeRoles.baseline.tsv` con `--update`.

### TR-1 · Pagina, tabella, azioni dalla pagina: m1 217 + m2 20 ⏳
- **File:**
  - `frontend/src/routes/(app)/transactions/+page.svelte` (37 → 2);
  - `frontend/src/lib/components/transactions/TransactionsTable.svelte` (6 → 0; m2 25 → 13);
  - `frontend/src/lib/components/transactions/modals/TransactionActionModal.svelte` (146 → 5; m2 4 → 0);
  - `frontend/src/lib/components/transactions/modals/PromoteMergeModal.svelte` (100 → 65; m2 4 → 0).
- **E2E:** `transactions-table`, `tx-split-promote`, `tx-selection-after-bulk`, `tx-bulk-promote-exec`,
  `tx-split-refusal`.
- **Vitest:** `PromoteMergeModal`, `TransactionsTable.privacy`.
- **Da rivedere:**
  - `/transactions` in chiaro e scuro;
  - modale Dividi/Promuovi: tabelle Prima/Dopo; icone Link/Unlink → success/warning;
  - modale di fusione: A/B/«unisci» e la conferma verde restano con i colori vecchi;
  - il sottotitolo resta legacy.

### TR-2 · Form, WAC ed eventi: m1 378 ⏳
- **File:**
  - `modals/TransactionFormModal.svelte` (35 → 0);
  - `form/TxFormBanners.svelte` (6 → 0);
  - `form/TxFormOptionalSection.svelte` (25 → 6);
  - `form/TxFormPairSection.svelte` (93 → 4);
  - `form/TxFormSingleSection.svelte` (50 → 0);
  - `shared/TransactionTypeSearchSelect.svelte` (4 → 0);
  - `wac/WacPreviewSection.svelte` (94 → 21);
  - `events/AssetEventPicker.svelte` (72 → 12);
  - `events/EventCreateMiniModal.svelte` (42 → 0).
- **Test (W, con l'OK):** `e2e/transactions/tx-wac-mode.spec.ts`, 4 righe → `aria-pressed` (test-author).
- **E2E:** `transactions-modals`, `tx-wac`, `tx-wac-formmodal`, `tx-wac-mode`, `tx-wac-unit-toggle`, `tx-wac-fx`,
  `tx-event-picker`, `tx-event-create-exists`, `tx-fx-implied-rate`, `tx-transfer-auto-cost`.
- **Vitest:** `TransactionFormModal`, `WacPreviewSection`, `EventExistsPanel`, `resolveFormItems`.
- **Da rivedere:**
  - selettori a segmenti WAC: attivi Auto/Totale `bg-lf-selected text-lf-link` (1:1; D-T16 vorrebbe il segmento attivo
    pieno, `bg-lf-checked`); attivi Manuale/Per unità `bg-lf-neutral text-lf-secondary`; inattivi muted;
  - segni «(+)/(−)» ambra → `text-lf-warning`;
  - picker eventi: la riga scelta passa da `libre-green/5` a `bg-lf-selected`, un po' più visibile.

### TR-3 · Bulk e picker: m1 245 ⏳
- **File:**
  - `modals/TransactionBulkModal.svelte` (88 → 9);
  - `bulk/TxBulkBanners.svelte` (54 → 2);
  - `bulk/TxBulkToolbar.svelte` (48 → 4);
  - `shared/TransactionResultBanner.svelte` (18 → 0);
  - `modals/TransactionPickerModal.svelte` (20 → 0);
  - `modals/PromoteAllModal.svelte` (32 → 0).
- **E2E:** `tx-bulk-operations`, `tx-bulk-suggest-ux`, `tx-bulk-promote-cost-basis`, `tx-bulk-diagnostics`,
  `tx-picker-pagination`, `tx-wac-bulk`, `tx-delete`, `tx-fx-completeness`.
- **Vitest:** `PromoteAllModal`.
- **Da rivedere:**
  - badge new/edited/delete → success/warning/danger tenui (lo split viola resta);
  - banner dei suggerimenti → success; il suo «unisci» blu → info;
  - link alle righe: l'hover blu diventa `text-lf-link` (verde).

### TR-4 · Confronto, aperto dall'import di IW: m1 78 ⏳
- **File:** `modals/TransactionCompareModal.svelte` (82 → 4, l'interruttore resta).
- **Vitest:** `TransactionCompareModal`.
- **E2E di IW:** `tx-import-duplicate-precedence`, `tx-import-resolution`.
- **Da rivedere:** righe e celle diverse → warning tenue; `<mark>` → ruoli Q7.

## 7. Ricetta di prova

**Leggere**, nella mia corsia: `nice -n 10`, carico < 50, una alla volta.
- Da `frontend/`, dopo ogni lotto:
  - `node scripts/theme/theme-roles.mjs --check`;
  - `node_modules/.bin/vitest run src/themeRoles.gate.test.ts src/themeTokens.gate.test.ts`;
  - `node_modules/.bin/prettier --check <file del lotto>`;
  - i Vitest dei componenti toccati.
- `git diff --check`.
- La prima volta, prima di tutto: `npm ci` (approvato una volta).

**Pesanti**, solo nello slot assegnato:
1. Avvio della corsia (`/tmp` è vuota dopo il riavvio): `front build --debug`, `mkdocs build`, poi
   `test … db populate --force --clean` sulla mia cartella.
2. `api sync`.
3. `front check`.
4. `test … front-utility component-unit`.
5. Gli E2E dei lotti.

Slot A = TR-1 + TR-2, slot B = TR-3 + TR-4, ognuno sotto i 45 minuti. A fine slot `lsof -nP -iTCP:6154 -sTCP:LISTEN`
deve essere vuoto.

## 8. Rischi e dipendenze

1. **FE8b di W:** se entra prima, conflitti di rinomina su tutti i file; il ratchet accoppia gli spostamenti (R4).
2. **`success-hover`:** 2 pulsanti restano legacy.
3. **Sottotitolo** e spec del picker di L.
4. **Base della tinta del broker:** da decidere insieme a BK.
5. **Baseline condiviso:** `--resolve`, mai allargato.
6. **E2E sotto carico:** `test-triage` prima di dire «instabile».
7. **IW:** TR-4 da annunciare.

## 9. Passi

0. ✅ (16/10) Piano nel journal; `npm ci`.
   > **Note implementazione:** piano creato da quello approvato in sessione (plan mode, che vietava le scritture nel
   > repo). `cd frontend && nice -n 10 npm ci --no-audit --no-fund`, uscita 0 a carico 37. npm 11 non ha eseguito gli
   > script d'installazione di `fsevents` ed `esbuild` (approvazione degli script). `node_modules/.bin/esbuild --version`
   > risponde comunque; ci sono `vitest`, `prettier` e `svelte-check`.
   > **⚠️ Fuori pista:** prima del passo 0 HEAD è passato da `8f2824046` a `6e569084a`. È un fast-forward del
   > coordinatore che porta lo skill comune `design-system` di T (D-T29) e i treni 105–106 della 1.3 (W-B17, Z7c-1, Z-9).
   > Nessun file dell'area cambiato (`git diff --stat 8f2824046 HEAD` sull'area: solo i due skill). Lo skill nuovo è
   > ora la fonte delle regole. Ha confermato le convenzioni del §5 (Annulla `bg-lf-panel hover:bg-lf-neutral`, hover di
   > una tinta `hover:bg-lf-X-line`, interruttori fermi, categorie lasciate). Ne ha aggiunte due: testo su una tinta
   > `-on-soft` («set, never split») e card di pagina `shadow-lf-shadow-card`.
   > **Lotti scritti in parallelo** da quattro sotto-agenti, su file disgiunti. Unico comando permesso: il controllo per
   > file `tr_check.mjs`, cartella di sessione, solo lettura (m1, m2, G1–G4). Le prove ufficiali le faccio io, in serie.
1. ✅ (16/10) TR-1 scritto e rivisto (le prove al passo 5).
   > **Note implementazione:** obiettivi raggiunti, misurati per file con `tr_check.mjs`:
   > - `+page.svelte` 37 → 2, `TransactionsTable` 6 → 0 (m2 25 → 13), `TransactionActionModal` 146 → 5 (m2 4 → 0),
   >   `PromoteMergeModal` 100 → 65 (m2 4 → 0); G1–G4 a 0;
   > - rilettura hunk per hunk (`git diff --word-diff`): nessun markup cambiato, solo classi e lo `<style>`.
   >
   > In dettaglio:
   > - la pagina prende `text-lf-primary` sulla radice;
   > - la tabella prende i testi della cassa sui ruoli (`var(--lf-text-primary|secondary)`, le regole `.dark` tolte) e i
   >   ripieghi dei chip dei tag sul precedente di `TagInput`;
   > - restano il sottotitolo, le conferme verdi, le categorie A/B/«unisci» e i 13 letterali previsti.
   >
   > **⚠️ Fuori pista:** in revisione ho aggiunto `text-lf-primary` sulla radice `tx-table-wrap` (regola 3 di
   > `theme-roles`): la tabella vive anche nella dashboard, in `brokers/[id]` e nel picker, dove il genitore è ancora
   > legacy.
   > Il sotto-agente TR-1 ha scritto per un attimo un log `tr1_check_before.log` nella radice del worktree e l'ha tolto
   > subito: `git status` pulito su quel percorso.
   >
   > **Da rivedere:**
   > - in scuro `.currency-code` e `.currency-symbol` scendono di un gradino: erano `#e2e8f0`/`#cbd5e1`, ora
   >   secondario, come dice la tabella per gray-600 + gray-200;
   > - il titolo h2 della pagina passa a `text-lf-secondary` (era gray-700/200);
   > - la textarea della fusione resta senza stile di fuoco, come prima (outline del browser);
   > - in scuro l'ombra della card «caricamento» la sostituisce ancora `html.dark .shadow-sm` di `app.css`: vale per
   >   tutte le card con la ricetta di T.
2. ✅ (16/10) TR-2 scritto e rivisto (lo spec di `tx-wac-mode` dopo l'OK di W; le prove al passo 5).
   > **Note implementazione:** obiettivi raggiunti:
   > - `TransactionFormModal` 35 → 0, `TxFormBanners` 6 → 0, `TxFormOptionalSection` 25 → 6, `TxFormPairSection`
   >   93 → 4, `TxFormSingleSection` 50 → 0, `TransactionTypeSearchSelect` 4 → 0, `WacPreviewSection` 94 → 21,
   >   `AssetEventPicker` 72 → 12, `EventCreateMiniModal` 42 → 0; G1–G4 a 0.
   >
   > **Regola 8, un caso:** `AssetEventPicker:466`, «evidenziata» e «scelta» erano due sfondi condizionali
   > indipendenti. Ora sono un ternario solo: `{isSelected ? 'bg-lf-selected' : highlightedIndex === idx ? 'bg-lf-hover'
   > : ''}`. Prima, in chiaro vinceva la scelta (per nome) e in scuro l'evidenziata (variante); ora vince la scelta in
   > entrambi.
   >
   > **⚠️ Fuori pista: i campi nativi migrati escono dalla regola scura di `app.css`.** La regola è
   > `html.dark input|select|textarea:where(:not([class*='-lf-']))`: bordo, colore del testo e segnaposto, che ora non
   > arrivano più. È lo stesso rischio segnalato da DV per i `dark:` senza chiaro, ma per la via di `app.css`, che lo
   > strumento `dark_only_check.py` non vede. Corretti in revisione, sulla ricetta dei campi di T:
   > - `text-lf-primary placeholder:text-lf-placeholder` sui due input di `EventCreateMiniModal`;
   > - `text-lf-primary` sulla textarea di `TxFormOptionalSection` (senza segnaposto);
   > - la textarea di `PromoteMergeModal` aveva già il testo e non ha segnaposto.
   >
   > I campi a cursore e a radio (`accent-lf-checked`) non usano né il bordo né il testo.
   >
   > **Da rivedere:**
   > - i selettori a segmenti WAC (Auto/Totale attivi `bg-lf-selected text-lf-link`; Manuale/Per unità attivi
   >   `bg-lf-neutral text-lf-secondary`): 1:1, ma D-T16 vorrebbe il segmento attivo pieno;
   > - i bordi del trigger del picker eventi e della textarea della descrizione: da gray-200 a `border-lf-input` (3:1,
   >   D-T18), più scuri in chiaro;
   > - i segni «(+)/(−)» ambra e gli avvisi WAC sul ruolo `warning`;
   > - l'Annulla della mini-modale, da `bg-gray-200` a `bg-lf-panel`;
   > - `scrollbar-thumb-gray-300 dark:scrollbar-thumb-slate-600` sulla tabella WAC: classi di colore che il gate non
   >   conta (prefisso `scrollbar-thumb`), con il loro `dark:` esplicito; nessun ruolo per la barra di scorrimento.
3. ✅ (16/10) TR-3 scritto e rivisto (le prove al passo 5).
   > **Note implementazione:** obiettivi raggiunti:
   > - `TransactionBulkModal` 88 → 9, `TxBulkBanners` 54 → 2, `TxBulkToolbar` 48 → 4, `TransactionResultBanner`
   >   18 → 0, `TransactionPickerModal` 20 → 0, `PromoteAllModal` 32 → 0; G1–G4 a 0; nessuna regola 8.
   > - Il lampo del banner (`classList.add('ring-2', 'ring-lf-success')`) resta tutto sui ruoli, perché il banner
   >   bersaglio è migrato.
   >
   > **Da rivedere:**
   > - i badge new/edited/delete sulle tinte di stato;
   > - i bordi dei banner di risultato in scuro: erano `/40` traslucidi, ora `-line` pieni, più evidenti (domanda
   >   aperta 2 dello skill);
   > - i link alle righe nel banner dei suggerimenti: `text-lf-secondary hover:text-lf-link`, verde su tinta verde al
   >   passaggio;
   > - il pallino «originale», più scuro in chiaro;
   > - il lampo dell'anello, verde più scuro in chiaro.
4. ✅ (16/10) TR-4 scritto e rivisto (le prove al passo 5).
   > **Note implementazione:** `TransactionCompareModal` 82 → 4 (l'interruttore), G1–G4 a 0. Il tag d'apertura di
   > «tieni tutti» è passato su una riga sola: sta sotto i 300 caratteri, quindi lo vuole Prettier; solo spazi.
   >
   > **Da rivedere:**
   > - il `<mark>` (Q7) dentro le celle anomale: in chiaro `#fde68a` su `warning-soft` stacca meno del vecchio
   >   amber-300 su amber-100;
   > - la riga «diversa» `bg-lf-warning-soft/40`, un gradino più forte in chiaro;
   > - i pulsanti bordati su `border-lf-subtle` (come prima, sotto il 3:1 di un controllo).
   >
   > **Controllo `dark_only_check.py`** (coordinatore, 11:28), base `6e569084a`: 6 casi, poi dichiarati falsi
   > positivi dal coordinatore (una classe su più righe letta riga per riga). Con lo strumento corretto: 0.
5. ✅ (16/10) Prove leggere complessive, Prettier e `--update`.
   > **Note implementazione:** tutte in serie, sotto `nice -n 10`, ciascuna partita solo con carico < 50.
   > - **`api sync`** (regola del coordinatore per i worktree nuovi): 11:36, uscita 0. Ha scritto solo file ignorati
   >   (`openapi.json`, `generated.ts`, contratti dei tool).
   > - **Primo giro** (11:44–11:55):
   >   - `theme-roles.mjs --check`: pulito, 20 file scesi sotto il loro record;
   >   - gate Vitest: `themeRoles.gate` e `themeTokens.gate`, 65/65;
   >   - `git diff --check`: pulito;
   >   - Vitest dei componenti: 10 file, 335/335 (`PromoteMergeModal`, `PromoteAllModal`, `TransactionCompareModal`,
   >     `TransactionFormModal`, `WacPreviewSection`, `EventExistsPanel`, `eventSaveError`, `TransactionsTable.privacy`,
   >     `resolveFormItems`, `filterState`);
   >   - **Prettier rosso su 8 file.**
   > - **Prettier** (12:03): `prettier --write` sugli 8 file. Prima ho salvato le copie in sessione; dopo, il confronto
   >   senza spazi è identico per tutti e 8. Le stringhe di classi più corte fanno stare i tag sotto le 300 colonne e
   >   Prettier ne unisce gli attributi su una riga (24 righe in `TxBulkToolbar`, la più toccata). Nessun nodo di testo
   >   toccato; il plugin di ordinamento delle classi non c'è (`.prettierrc`).
   > - **Giro finale** (12:07–12:08), sull'albero formattato:
   >   - Prettier pulito sui 20 file; `git diff --check` pulito;
   >   - controllo per file: tutti gli obiettivi del §6, G1–G4 a 0;
   >   - `dark_only_check.py` (strumento corretto del coordinatore, lanciato dalla radice): 0 casi in 20 file;
   >   - `--check` pulito; **`--update`: m1 8.249 → 7.331 (−918), m2 54 → 34 (−20)**, come previsto; `--check` di
   >     nuovo pulito, 0 file sotto il record;
   >   - gate 65/65; componenti 335/335.
   > - **Baseline:** 20 righe cambiate. 8 file escono (a zero: `EventCreateMiniModal`, `TxFormBanners`,
   >   `TxFormSingleSection`, `PromoteAllModal`, `TransactionFormModal`, `TransactionPickerModal`,
   >   `TransactionResultBanner`, `TransactionTypeSearchSelect`); 12 righe si stringono.
   >
   > **⚠️ Fuori pista:**
   > - **11:53–11:57, la rete è caduta** (il coordinatore). Nessun mio comando interrotto: `api sync` e il primo giro
   >   erano già finiti con uscita 0.
   > - **Il primo lancio di `dark_only_check.py`** l'ho fatto da `frontend/` e ha dato «0 file»: il suo `git diff` vuole
   >   la radice del worktree. Rilanciato dalla radice: 0 casi in 20 file.
   > - **Il target va avanti:** `f043c1b58` porta i ruoli nuovi di T (`hover:bg-lf-success-hover`,
   >   `hover:bg-lf-info-hover`, `text-lf-on-overlay`, tinte di gain e loss). Nel mio perimetro tocca solo
   >   `BACKLOG_POST_1.2.md`, in righe lontane dalla sezione TR (627, 631, 2588, 3888): niente conflitto previsto, né sul
   >   baseline né sui file dell'area.
6. ✅ (16/10) Base merge con i ruoli nuovi; lotto 5: le due conferme verdi su `bg-lf-success hover:bg-lf-success-hover
   text-lf-on-status` (chiude il backlog TR-2); spec `tx-wac-mode` su `aria-pressed`.
   > **Note implementazione:**
   > - **Il coordinatore ha committato il primo checkpoint:** codice `1a01ae733` (21 file), docs `e0b180e12`. Ha fatto
   >   la base merge con la punta `005ebcbf9`: **HEAD `d02b0c37c`**, albero uguale alla simulazione, `--check` pulito.
   >   La merge non tocca l'area. Porta lo skill `design-system` riscritto (`palette.md` a parte; i pulsanti di stato
   >   pieni `bg-lf-X text-lf-on-status hover:bg-lf-X-hover`, con `on-status` su `success-hover` e `warning-hover` fra
   >   le coppie misurate) e le regole sulla macchina condivisa nel file dell'agente.
   > - **Decisioni del coordinatore** (12:12):
   >   - il lotto 5 con il ramo ambra dello split su `bg-lf-warning hover:bg-lf-warning-hover`, nello stesso ternario;
   >   - lo spec `tx-wac-mode`: l'OK della 1.3 c'era già;
   >   - slot A+B insieme, verso le 14:45;
   >   - la base della tinta del broker passa a T;
   >   - il sottotitolo si sblocca con L-20.
   > - **`api sync`** dopo la base merge: 12:18, uscita 0.
   > - **Lotto 5:**
   >   - `PromoteMergeModal:262` → `text-lf-on-status bg-lf-success hover:bg-lf-success-hover`;
   >   - `TransactionActionModal:387` → `text-lf-on-status {mode === 'split' ? 'bg-lf-warning
   >     hover:bg-lf-warning-hover' : 'bg-lf-success hover:bg-lf-success-hover'}`, un ternario solo (regola 8).
   >   - m1: `PromoteMergeModal` 65 → 62, `TransactionActionModal` 5 → 0.
   > - **Spec** (test-author, sola scrittura): `e2e/transactions/tx-wac-mode.spec.ts`, le righe 152, 205 e 230
   >   `toHaveClass(/bg-libre-green/)` → `toHaveAttribute('aria-pressed', 'true')`. In più la 180 →
   >   `toHaveAttribute('aria-pressed', 'false')`: era un `not.toHaveClass(/bg-libre-green/)` che dopo la migrazione
   >   passava sempre. Commenti aggiornati; i `font-medium` del pulsante Manuale (177, 196, 228) restano. Precedente:
   >   `tx-wac-unit-toggle.spec.ts:137–139`.
   > - **Prove leggere** (12:20–12:22, `nice`, carico 35–43):
   >   - controllo per file: G1–G4 a 0;
   >   - Prettier: `TransactionActionModal` riformattato (le classi dei ruoli sono più lunghe, il tag supera le 300
   >     colonne e torna su più righe; confronto senza spazi identico), poi pulito sui 2 componenti e sullo spec;
   >   - `git diff --check` pulito; nessuna classe di colore rimasta nello spec;
   >   - `dark_only_check.py` 0 in 21 file e `native_field_check.py` 0 in 20 file, entrambi dalla base pre-TR
   >     `6e569084a`, dalla radice;
   >   - `--check` pulito; **`--update`: m1 7.331 → 7.323 (−8), m2 34**; `--check` di nuovo pulito;
   >   - gate 66/66 (uno in più col target: G-18); Vitest dei componenti `PromoteMergeModal`, `PromoteAllModal`,
   >     `TransactionFormModal`, `WacPreviewSection`, 57/57.
   >
   > **⚠️ Fuori pista:** il nome «TR-5» del lotto si scontrava con la voce TR-5 del backlog (scrollbar). Il lotto si
   > chiama «lotto 5» nel backlog e qui.
7. ⏳ Slot A+B insieme. **Coordinatore, 12:57:** `front-transaction all` al posto delle 25 azioni singole (un server e
   un populate, e copre di più); niente `front check`, perché vale lo `svelte-check` della build delle 12:24 sullo
   stesso albero. Lo slot è il **2, prestato dalla 1.3**, dopo L-20, verso le 13:40, con **fine tassativa alle
   14:30**: dopo le 14:20 non partono passi nuovi. I rossi fuori dalle mie spec passano prima da `test-triage`.
   > Script `slot_ab2.sh` (cartella di sessione), tre passi in serie: `api sync`; `front-utility component-unit`;
   > `front-transaction all`.
   > - Ogni passo gira in un gruppo di processi suo (`set -m`). Dopo le 14:20 non ne parte uno nuovo.
   > - Alle 14:30 il passo in corso riceve SIGINT al gruppo, poi SIGTERM; mai SIGKILL, così il runner smonta il suo
   >   server.
   > - Quello che resta nel gruppo riceve SIGTERM e viene elencato.
   > - Provato a vuoto con `sleep` e una scadenza a 3 s: taglio, passo dopo saltato, gruppo pulito.
   > **Preparazione della corsia** (coordinatore, 12:23: «come BK e IW, uno alla volta, sotto `nice` e con carico sotto
   > 50, senza server»). Lo script `prep_lane.sh` e i log stanno nella cartella di sessione. Comandi, in serie:
   > - `front build --debug`;
   > - `mkdocs build`;
   > - `test --test-port 6154 --data-dir /tmp/librefolio-r2-tr db populate --force --clean --with-reports`, lo stesso
   >   populate che il runner del frontend fa prima degli E2E (`_frontend_common._ensure_db_populated`).
   >
   > Il secondo checkpoint è committato in tre: `70bae91b4` (le conferme), `a5e229084` (lo spec), `505a28289` (il
   > diario). Lo SHA di TR-2 è nel backlog.
   >
   > **Esito della preparazione** (12:24–12:53, tre comandi, uscita 0 per tutti; porta 6154 libera alla fine):
   > - `front build --debug`: 467 s. `svelte-check` dentro la build: **0 errori, 0 avvisi**, un primo segnale per
   >   `front check`.
   > - `mkdocs build`: 204 s; tutti i 3.076 URL relativi del sito si risolvono.
   > - populate: 34 s. Dati in `/tmp/librefolio-r2-tr` (`sqlite/`, `custom-uploads/`, `broker_reports/`, `logs/`);
   >   l'istantanea del DB va nella cartella dei log del runner, `.testLog/00_archive/`, ignorata da git.
   >
   > **⚠️ Fuori pista:** il log complessivo di `tee` non si è scritto, perché la cartella `prep/` non c'era ancora
   > quando `tee` l'ha aperta. Per questo lo script esce con 1, mentre i suoi tre passi escono con 0. I log dei passi
   > ci sono.
   >
   > ✅ **Slot A+B eseguito il 16/10, 13:20–14:21**, sul ramo portato dal coordinatore alla punta `1248b7908` (lotti di
   > AF e IM). Due note del diario committate (`9691e8936`), base merge **`814b93319`** (baseline col `--resolve`,
   > m1 combinato 4.814). Albero pulito; porta 6154 libera prima e dopo.
   >
   > **Passi**, tutti finiti prima delle 14:20, senza tagli. Sulla scorta del coordinatore (13:19) la build di prima era
   > vecchia: lo slot l'ha rifatta con `server --test --build-only`, e il suo `svelte-check` vale come `front check`.
   >
   > | Passo | Uscita | Durata | Esito |
   > |---|---|---|---|
   > | `api sync` | 0 | 81 s | — |
   > | `server --test --build-only` | 0 | 322 s | `svelte-check` **0 errori, 0 avvisi**; build di debug e MkDocs ok |
   > | `front-utility component-unit` | 0 | 188 s | **154 file, 4.041 test passati** |
   > | `front-transaction all` (consolidato, 47 spec) | 1 | 51 min | **376 passati** (342 desktop + 34 del gruppo «all-projects»), **5 rossi**, 32 saltati (le spec `@mobile` sul desktop); Vitest della categoria **23 file, 907 test passati** |
   >
   > **Le mie 25 spec mirate sono tutte verdi.** Fra queste:
   > - `tx-wac-mode`, con le asserzioni nuove su `aria-pressed`;
   > - `transactions-modals`, `transactions-table`, tutte le `tx-wac*`, `tx-bulk-*` e `tx-event-*`;
   > - `tx-import-duplicate-precedence`, che apre il confronto (TR-4), e IWR-006b di `tx-import-resolution`, «il
   >   badge ⚠ dei duplicati apre la modale di confronto».
   >
   > **I 5 rossi**, tutti nelle spec dell'import fuori dalle mie: `tx-import-flow` R1 e G2, `tx-import-matching` E4-01
   > ed E4-03, `tx-import-resolution` IWR-001.
   > - **Errore:** fallisce sempre l'ingresso, prima della UI delle transazioni:
   >   - `login()` resta su `auth-loading` o su `/dashboard` senza `app-shell` per 30 s;
   >   - nella fixture «owned», `login-page` resta visibile per 20 s;
   >   - in G2, `/welcome` non passa a `/dashboard` entro 15 s.
   > - **Durate:** fuori misura, più lunghe del timeout dei test stessi (E4-01 15,4 min con un timeout di 120 s).
   >
   > **Triage** (skill `test-triage`, in sola lettura sui log, nessun rilancio: pausa del developer):
   > - **§1, la forma della risposta:** no, la schermata d'accesso non ha posizioni né conteggi.
   > - **§2, l'orologio:** no, le attese sono su condizioni.
   > - **§4, il sintomo più forte:** sì. Il log del backend della corsia (`/tmp/librefolio-r2-tr/logs/librefolio.log`)
   >   ha quattro silenzi totali, senza nessun record, nemmeno DEBUG, che coincidono con la durata dei rossi:
   >   - 13:45:02–13:47:04 (R1);
   >   - 13:47:49–14:03:14 (E4-01);
   >   - 14:03:17–14:08:45 (E4-03);
   >   - 14:09:30–14:12:52 (IWR-001).
   > - **`pmset -g log`:** il portatile **dormiva**, a batteria. Ci sono «Entering Sleep» alle 14:03:14 e alle
   >   14:09:28, DarkWake alle 14:03:12 e alle 14:08:43, e alle 14:12:45 «Wake … due to … lid … HID Activity» (il
   >   coperchio riaperto), con il display riacceso. Nessuna attività di sistema registrata fra le 13:47 e le 14:03.
   > - **Verdetto: ambiente.** I cinque test erano in corso a cavallo di un sonno della macchina, che ha sospeso
   >   browser e backend. Nessun difetto del prodotto e nessun legame con TR.
   >
   > **Seguito, alla ripresa:** rilanciare solo le tre spec rosse (`--resume` del runner oppure le tre azioni), a
   > macchina sveglia.
   >
   > **Reperti per altri:**
   > - MkDocs, nella build: `developer/backend/transactions/wac.md` punta a `split_promote.md#transfer-giving-leg`,
   >   un'ancora che non esiste (doc di W);
   > - nel log del backend, 13:43:08: `wipe_market_data: cache invalidation skipped — 'Asset' object has no attribute
   >   'provider_code'` (`services/assets/currency_change`, di X/AF).
   >
   > Ho girato al coordinatore entrambi i reperti.
8. ✅ (16/10) Lotto 6: il sottotitolo di `/transactions` (TR-1), sbloccato da L-20 (`460529690`).
   > **Pausa e ripresa:** il developer ha chiesto una pausa durante lo slot; si riparte dalle 14:14 (coordinatore,
   > 14:27). Indicazioni: il lotto 6 con le prove leggere e senza un checkpoint a sé; poi uno slot breve (al massimo
   > 30 minuti, nella nostra corsia, dopo BK, verso le 15:00) con la build, le tre spec dei rossi e la spec del
   > sottotitolo; poi il checkpoint (passo 7 e lotto 6) e l'ingresso. Reperti: l'ancora di `wac.md` l'aveva già
   > corretta la 1.3 (`ed500643f`); il log di `currency_change` lo gira il coordinatore alla 1.3.
   >
   > **Note implementazione:** `+page.svelte:738`, `text-gray-500 dark:text-gray-400` → `text-lf-muted`. Prove leggere
   > (14:30, carico 46–48), tutte con uscita 0:
   > - controllo per file: m1 2 → 0, G1–G4 a 0;
   > - Prettier e `git diff --check` puliti;
   > - `dark_only_check.py` 0 in 78 file e `native_field_check.py` 0 in 77 (base `6e569084a`: dentro ci sono anche i
   >   file di AF e IM già uniti);
   > - `--check` pulito; **`--update`: m1 4.814 → 4.812**, m2 22; `--check` di nuovo pulito;
   > - gate 71/71; C4 non chiede di togliere selettori.
   >
   > Backlog: TR-1 chiusa ✅, lo SHA arriva col checkpoint.
   >
   > **⚠️ Fuori pista:** L-20 è entrato in `dev_release2` (`460529690`) dopo che il mio ramo era stato portato a
   > `814b93319`, quindi qui c'è ancora la versione vecchia di `designer-lab-picker.spec.ts`. Il suo test «dark-theme
   > pick of a text-gray-500 element» vuole il sottotitolo in `text-gray-500`: sul mio ramo, col lotto 6, fallisce per
   > costruzione, mentre nel target L-20 lo ha già staccato. Per lo slot basta `front-designer-lab live`: legge il
   > sottotitolo con `colourSourceOf`, che regge sia la classe di palette sia il ruolo. Il picker si valida dopo
   > l'ingresso, o dopo una base merge con L-20.
9. ✅ (16/10) Slot breve, 14:47–14:56 (8 minuti), sulla base merge **`6c6d1979f`** del coordinatore: la punta
   `1c7b9def2` con L-20, DV, IM e il fix di C4 (la regola morta `bg-white/90` tolta da `app.css`). I gate sull'albero
   unito li ha verificati il coordinatore: 89/89.
   > **Note implementazione:** `api sync` è stato lanciato fuori dallo slot appena è arrivata la merge (14:35, uscita 0,
   > da un osservatore che aspettava HEAD nuovo, nessuna merge in corso e albero pulito). Lo slot (`slot_c.sh`, tagli
   > assoluti: nessun passo nuovo dopo le 15:15, taglio alle 15:20; nessuno è servito) ha fatto, in serie, carico 19–45:
   >
   > | Passo | Uscita | Durata | Esito |
   > |---|---|---|---|
   > | `server --test --build-only` | 0 | 156 s | `svelte-check` **0 errori, 0 avvisi** |
   > | `front-transaction tx-import-flow` | 0 | 90 s | **10/10** |
   > | `front-transaction tx-import-matching` | 0 | 61 s | **6/6** |
   > | `front-transaction tx-import-resolution` | 0 | 85 s | **15/15** |
   > | `front-designer-lab picker` | 0 | 45 s | **4/4**: la versione di L-20, col sottotitolo migrato |
   > | `front-designer-lab live` | 0 | 66 s | **12/12**: i tre test del sottotitolo leggono il ruolo |
   >
   > Porta 6154 libera alla fine. **I rossi dello slot A+B sono confermati «ambiente»:** le stesse tre spec, a macchina
   > sveglia, passano tutte (31/31). Il backlog ha lo SHA di TR-1 (`546204732`).
10. ⏳ L'ingresso in `dev_release2` (coordinatore).
