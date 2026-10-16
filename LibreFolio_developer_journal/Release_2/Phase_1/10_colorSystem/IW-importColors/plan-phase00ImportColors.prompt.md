# Piano — Workstream IW, colori dell'import (migrazione 1:1 ai ruoli `--lf-*`)

> **Workstream IW del programma colori**, sessione «IW - colori dell'import». Coordinatore: sessione «UI color
> analysis» (`aec04834-1532-4d86-9e3f-f942e82aca89`).
> Branch `e-alfy-iw-colori-import` (nato `e-alfy-solid-meme`, rinominato dall'app all'avvio). Base dell'analisi
> **`8f2824046`** (`dev_release2`, verificata il 16/10 alle 10:41); base del lavoro **`6e569084a`** (fast-forward del
> coordinatore alle 11:02: lo skill comune D-T29 di T, `c59e92dfb`; nessun file dell'area toccato).
> Corsia: porta **6151**, dati **`/tmp/librefolio-r2-iw`**.
> Comandi: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-iw …`.
>
> **Fonti:** kickoff del coordinatore del 16/10 (D-T28, D-T29); [piano generale](../plan-phase00ColorSystemThemeLab.prompt.md),
> «Workstream e corsie»; skill comune [`design-system`](../../../../../.github/skills/design-tools/design-system/SKILL.md)
> (la fonte delle regole dal 16/10, 11:02); skill [`theme-roles`](../../../../../.github/skills/design-tools/theme-roles/SKILL.md),
> regole 1–8; `frontend/src/lib/theme/tokens.css` (i valori della designer, giro 2: «Pietra e Salvia» e «Ardesia e
> Salvia»); devWiki `problems/tailwind4-same-property-utilities-sorted-by-name`.
>
> **Stato:** ✅ analisi inviata (16/10, 11:00); ✅ approvata dal developer nella sessione IW (uscita dal plan mode, ~11:05)
> e dal coordinatore con le decisioni D1–D6 (~11:15); ✅ cinque lotti scritti e rivisti (11:47); ✅ prove leggere verdi
> (12:05); ✅ checkpoint 1 `48ecea1e2`, base merge `b3162db80`; ✅ passo 5, i pulsanti di D2: checkpoint 2 `9c79d5b35`;
> ✅ C4 dopo la base merge `b2466931d`: `ec9fec52a`; ✅ slot pesante verde (15:02–15:38); ⏳ consegna finale inviata,
> FROZEN, pronto per l'ingresso nel target.

## ✅ Autorizzazione e decisioni (16/10/2026)

**Autorizzazione del developer:** approvazione diretta del piano nella sessione IW, con «avvia» (uscita dal plan mode).
**Coordinatore** (testuale, 16/10): «D4: sì, `utils/transactions/pairCellHtml.ts` va in IW-5. T non lo tocca.» — «D5: sì.
La riga `e2e/transactions/tx-brim-import.spec.ts:235` passa a `getByTestId('import-wizard-unresolved-count')`, scritta da
test-author: è coperta dall'OK generale della 1.3.» — «D1: (a). D2, D3, D6: legacy e annotati. Per D2 ho già chiesto a T
`--lf-success-hover` e `--lf-info-hover`.» — «FE8b: ho chiesto alla 1.3 di non farlo partire mentre IW e TR lavorano.»

| # | Decisione |
|---|---|
| D1 | (a) Il tris ambra/arancio/giallo della colonna «Stato» segue la tabella: tutti `warning`; distinti da icona, etichetta e anello. Nei «da rivedere» |
| D2 | I 4 pulsanti pieni success/info con hover restano legacy, annotati; T valuta `--lf-success-hover` e `--lf-info-hover` |
| D3 | Lo `<style>` di `ImportBrokerMismatchModal` sui token `--lf-cmp-broker-mismatch-*` resta (W6/B5 di T) |
| D4 | `lib/utils/transactions/pairCellHtml.ts` entra in IW-5 |
| D5 | `tx-brim-import.spec.ts:235` → `getByTestId('import-wizard-unresolved-count')`, scritto da test-author |
| D6 | Le stelle «primario» restano legacy, annotate |

## Richiesta del developer (16/10, testuale, via coordinatore)

- «l'obiettivo intanto è fattorizzare e migrare al nuvo color design sistem, poi le rifiniture le facciamo nel tempo,
  anzi sono un pò deluso che abbiamo fatto solo il 22% in 1 gg, non riesci a mettere al lavoro più agenti?»
- «è importante migrare il prima possibile i componenti prima di metterci a sviluppare funzioni grandi, quindi vedi tu.»
- «nel migrare cerca di seguire i colori dei temi che la designer ci ha intanto dato»

**Perimetro:** migrazione 1:1 ai ruoli delle classi di colore legacy e dei colori scritti a mano, senza cambiare markup,
layout o comportamento, senza decisioni di design. Dove la tabella non basta, l'elemento resta com'è e si annota.

**Area:** `frontend/src/lib/components/transactions/import/**`, `…/transactions/wizard/**`,
`…/transactions/modals/ImportWizardModal.svelte`, `ParseDetailModal.svelte`, `ImportBrokerMismatchModal.svelte`.
Fuori: `GapFixToggle.svelte` (lotto unico degli interruttori di T), `lib/theme/**`, `scripts/theme/**`, `app.css`
(salvo un selettore che il gate C4 chieda di togliere).

## Stato reale (16/10, `8f2824046`)

### Inventario (`theme-roles.mjs --report` + classificatore di sessione sullo stesso scanner)

m1 dell'area **1.304** (= baseline), m2 **1** (`#dc2626`). Divisione per significato:

| File | m1 | neutri | marchio | danger | warning¹ | success | info | segni | categorie | interruttori | resta legacy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `import/AssetGroupStep.svelte` | 108 | 73 | 0 | 0 | 17 | 14 | 4 | 0 | 0² | 0 | 14 |
| `import/BrimEvidenceTable.svelte` | 52 | 28 | 0 | 8 | 8 | 0 | 8 | 0 | 0 | 0 | 0 |
| `import/BrimNoticeList.svelte` | 8 | 0 | 0 | 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 |
| `import/FixFlaggedStep.svelte` | 205 | 119 | 2 | 21 | 34 | 21 | 8 | 0 | 0 | 0 | 0 |
| `import/GapFixStep.svelte` | 95 | 61 | 10 | 13 | 4 | 7 | 0 | 0 | 0 | 0 | 0 |
| `import/GapFixToggle.svelte` | 4 | — | — | — | — | — | — | — | — | 4 | 4 |
| `import/ImportAssetPicker.svelte` | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `import/ReportSetCard.svelte` | 75 | 43 | 10 | 2 | 16 | 0 | 4 | 0 | 0 | 0 | 0 |
| `modals/ImportBrokerMismatchModal.svelte` | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0³ |
| `modals/ImportWizardModal.svelte` (+ m2 `#dc2626`) | 222 | 95 | 9 | 20 | 52 | 20 | 26 | 0 | 0⁴ | 0 | 8 |
| `modals/ParseDetailModal.svelte` | 141 | 88 | 2 | 11 | 29 | 7 | 4 | 0 | 0⁴ | 0 | 0 |
| `wizard/AnalyzeStep.svelte` | 67 | 40 | 1 | 10 | 6 | 2 | 8 | 0 | 0 | 0 | 0 |
| `wizard/DuplicatesStep.svelte` | 77 | 63 | 2 | 0 | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| `wizard/ReviewStep.svelte` | 86 | 46 | 6 | 0 | 24 | 10 | 0 | 0 | 0⁴ | 0 | 0 |
| `wizard/SelectFilesStep.svelte` | 22 | 20 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `wizard/UploadStep.svelte` | 20 | 10 | 4 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| `wizard/WizardFooter.svelte` | 101 | 49 | 16 | 4 | 18 | 14 | 0 | 0 | 0 | 0 | 0 |
| `wizard/wizardTypes.ts` | 0 | | | | | | | | | | |
| **Totale** | **1.304** | **755** | **64** | **89** | **225** | **101** | **66** | **0** | **0** | **4** | **26** |

¹ ambra, giallo e arancio: la tabella della skill li manda tutti a `warning` (vedi D1).
² le categorie arrivano per catena: `KIND_TONES.identifier` di `lib/theme/toneClasses.ts` (T), badge degli identificativi.
³ più lo `<style>` sui token di componente di R `--lf-cmp-broker-mismatch-*` (fuori da m1/m2, D3).
⁴ i chip Ticker/ISIN e i pallini dei tag sono colori generati (`getIndexColor`, `getStringColor` di `utils/colors.ts`,
eccezione m2 di R): categoriali, restano.

**Segni:** 0. Verde e rosso nell'area sono esiti e stati (verifica OK/KO, risolto/non risolto, blocco/avviso); gli
importi con segno passano da `CurrencyAmount` (di T). **Previsione:** ~1.278 classi migrate (98%), m2 a 0; restano 26.
Con `pairCellHtml.ts` (D4) il perimetro sale a 1.310 classi: 1.282 migrate, 28 restano.

### Catene di classi

| Catena | Dove | Esito |
|---|---|---|
| `confidenceBadgeClass` | `ImportWizardModal` → prop di `ReviewStep` → `badgeClass` di `AssetSelect` (T, già sui ruoli, default `bg-lf-neutral text-lf-secondary`) | interna a IW-5; lo span di `AssetSelect` non ha altri colori |
| `duplicateTierBadgeClass` | `ImportWizardModal` → prop di `DuplicatesStep` | interna a IW-5 |
| `diffCls` | stringa accodata alle celle HTML della tabella del resolver (`ImportWizardModal`) | interna, stesso file |
| `getRowClass` | `ReviewStep` → `<tr>` di `DataTable` (già a m1 0, colori riga nel suo `<style>`) | migrabile: sul `<tr>` solo nomi semantici |
| `dotColor: '#dc2626'` | `ImportWizardModal` → pallino delle opzioni di `DataTableColumnFilter` (`style="background:…"`) | → `'var(--lf-danger)'`, m2 a 0 |
| `KIND_TONES.identifier` | `lib/theme/toneClasses.ts` (T) → badge identificativi di `AssetGroupStep` | categoriale: badge interi legacy, anello ambra compreso |
| `pairCellHtml.ts` (6 m1) | `lib/utils/transactions/` → celle «da/a» delle tabelle dell'import; **usato solo** da `ImportWizardModal` | fuori area: D4 |
| `BrimEvidenceTable` | usato anche da `TxBulkBanners` e `TransactionBulkModal` (TR) solo con `tone` | nessuna classe passa; cambia l'aspetto anche nel Bulk |

Nessuna `contentClass` verso `ModalBase`, nessuna classe verso `InfoBanner`, `ContextMenu`, `Tooltip` (solo
`wrapperClass` di layout), `OrderableList`, `DataTableToolbar`. `ModalBase` mette già `text-lf-primary` sul pannello
(regola 3 soddisfatta per tutto ciò che vive nelle modali).

### Test che asseriscono colori

- **Vitest:** nessuno nell'area (`FixFlaggedStep`, `GapFixStep`, `ReportSetCard`, `ReportSetCard.escape`,
  `ImportWizardModal`, `ParseDetailModal`, `ImportBrokerMismatchModal`: 0 asserzioni su classi). Il gate
  `htmlInterpolation.gate.test.ts` legge le stringhe HTML di `ImportWizardModal`: si cambiano solo classi.
- **E2E:** `e2e/transactions/tx-brim-import.spec.ts:235` (T4) cerca il badge dei non risolti con
  `step4.locator('[class*="amber"]')`. Dopo IW-5 non troverebbe nulla e il test passerebbe a vuoto. Cura:
  `page.getByTestId('import-wizard-unresolved-count')` (testid già presente). Spec dell'import (W, 1.3): OK prima (D5),
  poi `test-author`.
- Le altre letture di classe nelle spec delle transazioni sono marcatori semantici (`row-edited`, `tx-row-receiver`) o di
  TR (`tx-wac-mode`, `bg-libre-green`).

### File dell'area aperti altrove (sola lettura, `git --no-optional-locks status`, 10:55)

Nessuno: 20 worktree senza modifiche nell'area; nessun ramo con commit propri sui file dell'area rispetto alla base
comune (J, Z, H hanno solo il merge di `d5c3c3ae3`). Il checkout principale non è stato letto (regola dell'app).
**Pianificato:** FE8b di W (1.3, «finale») sposta `components/transactions/**` (con `wizard/` che confluisce in
`import/`): mai in parallelo con IW.

## Convenzioni (oltre alla tabella della skill; ogni voce ha un precedente)

1. Pulsante primario `bg-libre-green text-white hover:bg-libre-green/90` → `bg-lf-action text-lf-on-action hover:bg-lf-action-hover`; un `hover:opacity-90` resta com'è.
2. Stepper, barra di avanzamento, riempimento «attivo» `bg-libre-green` → `bg-lf-checked` (+ `text-lf-on-checked`); binari `bg-lf-neutral` (precedenti: `StepNav`, `OnboardingIntroScene`, D-T16).
3. Card o opzione selezionata, zona di trascinamento attiva → `border-lf-focus bg-lf-selected` (+ `ring-lf-focus`) (precedenti: `TabBar`, `DataImportModal`, `FxProviderSelect`).
4. `text-libre-green` → `text-lf-link`; `hover:text-libre-green` → `hover:text-lf-link`; `hover:border-libre-green` → `hover:border-lf-focus`.
5. Checkbox `border-gray-300 text-libre-green focus:ring-libre-green` → `border-lf-input text-lf-link focus:ring-lf-focus` (precedente: PAC `OwnerBrokerPicker`).
6. Tinta con hover `bg-X-50 hover:bg-X-100` → `bg-lf-X-soft hover:bg-lf-X-line`; hover su bianco `hover:bg-X-100` → `hover:bg-lf-X-soft` (precedenti: `SyncModalBase`, `ChangelogModal`, `SyncResultRow`).
7. Badge `bg-X-100 text-X-800/900` → `bg-lf-X-soft text-lf-X-on-soft`; `text-X-500…700` → `text-lf-X`; `ring-X-200` → `ring-lf-X-line`.
8. Badge `bg-X-200 text-X-900` sopra una card `X-50` → `bg-lf-X-line text-lf-X-on-soft` (resta un gradino sopra la tinta; precedente: pulsanti del banner qualità dati).
9. Opacità: si tiene quella della metà chiara (`bg-amber-50/60` → `bg-lf-warning-soft/60`), la metà `dark:` cade.
10. `border-X-500` (contorno tratteggiato dei buchi della timeline) → `border-lf-X`.
11. `border-gray-300/400` → `border-lf-input` su controlli (campi, checkbox, pulsanti contornati, zona di caricamento); → `border-lf-subtle` su contenitori e divisori.
12. Barra dati grigia `bg-gray-400/80` → `bg-lf-muted/80` (Q5: «`bg-lf-muted` for the dot»); barra dati verde della timeline → `bg-lf-checked/70 hover:bg-lf-checked` (come 2); binari e tracce (avanzamento, timeline, connettori dello stepper) → `bg-lf-neutral` («progress tracks», skill comune).
13. Fuoco blu (`border-blue-400 focus:ring-blue-400` del campo di rinomina, `ring-blue-400` del bersaglio di trascinamento) → `border-lf-focus`, `focus:ring-lf-focus`, `ring-lf-focus`: il fuoco della designer è verde.
14. `text-gray-300 dark:text-gray-600` (separatori `|`) → `text-lf-muted`, come da tabella.
15. Pulsante pieno d'avviso `bg-amber-500/600 hover:bg-amber-600/700 text-white` → `bg-lf-warning hover:bg-lf-warning-hover text-lf-on-status` (Q3).
16. Colori di libreria scritti a mano → variabile del ruolo (`'var(--lf-danger)'`).
17. Regola 8: la scansione di sessione non trova elementi con un colore fisso e uno condizionale della stessa proprietà; le direttive `class:` di `AnalyzeStep` hanno condizioni esclusive. Si ricontrolla a ogni revisione.
18. Hover su un pannello (skill comune, domanda aperta 3: `hover` = `panel`): un elemento `bg-gray-50 hover:bg-gray-100`, o un controllo che sta su un pannello, → `bg-lf-panel hover:bg-lf-neutral`; su card e pagine `hover:bg-lf-hover`.
19. Chip neutri per gradino e contrasto: `bg-gray-100` → `bg-lf-panel` (il testo attenuato vi è misurato a 4,5:1); `bg-gray-200` → `bg-lf-neutral` con `text-lf-secondary` (`text-gray-700/800`) o `text-lf-muted` (`text-gray-500`, come oggi).
20. Riferimento delle regole: dal 16/10 alle 11:02 lo skill comune `design-system`; in conflitto vince lui.

## Restano legacy (annotati, backlog IW-n)

- `GapFixToggle.svelte` (4): lotto unico degli interruttori di T.
- `AssetGroupStep`: badge identificativi (`KIND_TONES`, categoriali) con anello ambra e `ring-offset` del primario (2); stelle «primario» `fill-amber-400 text-amber-500` (6, legenda compresa): nessun ruolo per un segnaposto, D6; pulsanti «Conferma» `bg-emerald-600 hover:bg-emerald-700 text-white` (6): D2.
- `ImportWizardModal`: conferma degli avvisi (ramo info `bg-sky-500 hover:bg-sky-600`, 5 sull'elemento intero) e `create-primary-confirm` `bg-blue-600 hover:bg-blue-700` (3): D2. ✅ Convertiti al passo 5 con i ruoli nuovi di T, insieme alle due conferme smeraldo di `AssetGroupStep`.
- `pairCellHtml.ts` (D4, in IW-5): il chip viola del tasso implicito `text-violet-600 dark:text-violet-400` (2), categoriale; rispecchia il suggerimento di promozione del Bulk di TR (`renderDualHtml` di `TransactionBulkModal`).

Totale previsto: **28** classi legacy restano (26 dell'area + 2 di `pairCellHtml.ts`), m2 a 0. Dopo il passo 5: **14**.

## Decisioni chieste al coordinatore (✅ decise il 16/10: vedi «Autorizzazione e decisioni» in testa)

| # | Domanda | Proposta |
|---|---|---|
| D1 | Colonna «Stato» del passo 4: «probabile duplicato» ambra, «duplicato in attesa» arancio, «possibile duplicato in attesa» giallo vanno tutti su `warning`: gli ultimi due restano distinti solo da icona, etichetta e anello | (a) seguire la tabella e metterlo nei «da rivedere»; (b) lasciare legacy il solo badge giallo |
| D2 | Pulsanti pieni success/info con hover (4 elementi): mancano `--lf-success-hover` e `--lf-info-hover` | legacy + richiesta del ruolo a T (R1); in alternativa `hover:bg-lf-X/90` provvisorio, se OK |
| D3 | `ImportBrokerMismatchModal`, `<style>` sui token `--lf-cmp-broker-mismatch-*` (12, con override `.dark`): migrarlo toglie i token da `lib/theme/components/dialogs.css` (T; gate `themeComponentTokens`) | lasciarlo a W6/B5 di T; oppure OK a IW con la modifica di `dialogs.css` |
| D4 | `lib/utils/transactions/pairCellHtml.ts` (6 m1), usato solo dall'import | assegnarlo a IW-5 |
| D5 | `tx-brim-import.spec.ts` T4 (W, 1.3) | OK a `test-author` per il testid |
| D6 | Stelle «primario» (ambra) | legacy + richiesta di un ruolo «marcatore» (R2), o coi categoriali |

## Lotti (file disgiunti: si possono scrivere in parallelo)

| Lotto | File | m1 | Schermate |
|---|---|---:|---|
| **IW-1** Avvisi BRIM e dettaglio del parse | `import/BrimEvidenceTable.svelte`, `import/BrimNoticeList.svelte`, `modals/ParseDetailModal.svelte`, `modals/ImportBrokerMismatchModal.svelte` | 202 | dettaglio del parse, avvisi BRIM (anche nel Bulk di TR), mismatch del broker |
| **IW-2** Set di report e file | `import/ReportSetCard.svelte`, `wizard/UploadStep.svelte`, `wizard/SelectFilesStep.svelte` | 117 | passi 1–2, card del set, timeline |
| **IW-3** Correzioni: Fix, gap-fix, unificazione | `import/FixFlaggedStep.svelte`, `import/ImportAssetPicker.svelte`, `import/GapFixStep.svelte`, `import/AssetGroupStep.svelte` | 428 (414) | passi «Correggi», «Buchi», «Asset» |
| **IW-4** Analisi e piede | `wizard/AnalyzeStep.svelte`, `wizard/WizardFooter.svelte` | 168 | passo 3, pulsanti di ogni passo |
| **IW-5** Il guscio: modale, duplicati, revisione | `modals/ImportWizardModal.svelte`, `wizard/DuplicatesStep.svelte`, `wizard/ReviewStep.svelte`, `lib/utils/transactions/pairCellHtml.ts` (D4); spec `e2e/transactions/tx-brim-import.spec.ts:235` di test-author (D5) | 391 (381) | stepper, intestazione, duplicati, revisione, conferma avvisi, sotto-modali |

**Prove leggere** (corsia IW, `nice -n 10`, carico < 50), per lotto: `node frontend/scripts/theme/theme-roles.mjs --check`;
Vitest `src/themeRoles.gate.test.ts`, `src/themeTokens.gate.test.ts`, `src/themeComponentTokens.gate.test.ts` (IW-5 anche
`src/htmlInterpolation.gate.test.ts`); Prettier `--check` sui file del lotto; `git diff --check`; Vitest dei componenti:
IW-1 `ParseDetailModal.test.ts`, `ImportBrokerMismatchModal.test.ts`; IW-2 `ReportSetCard.test.ts`,
`ReportSetCard.escape.test.ts`; IW-3 `FixFlaggedStep.test.ts`, `GapFixStep.test.ts`; IW-4 e IW-5 `ImportWizardModal.test.ts`
(IW-5 anche `importPairs.test.ts` con D4).

**Prove pesanti** (slot del coordinatore, < 45 min l'uno): `api sync`, `front check`, `front-utility core-unit`,
`front-utility component-unit`, poi E2E `front-transaction`:
- slot A (IW-1…IW-3): `tx-import-flow`, `tx-import-broker-mismatch`, `tx-ca-contract`, `tx-bulk-diagnostics`,
  `tx-import-report-set`, `tx-import-upload`, `tx-import-file-selection`, `tx-import-degiro`, `tx-asset-identity`;
- slot B (IW-4, IW-5): `tx-import-flow`, `tx-import-duplicate-precedence`, `tx-import-resolution`, `tx-brim-import`,
  `tx-import-matching`.

**Dove guardarlo** (developer, chiaro e scuro; anteprima 6160 dopo l'ingresso, o la galleria della sera): IW-1 la
modale di dettaglio del parse (passo 3, «Vedi tutto» e dettaglio per file), avvisi BRIM nel passo «Correggi» e nel Bulk,
la modale del broker diverso; IW-2 `import-report-set-*`, passi 1–2; IW-3
`import-wizard-fix-step`, `import-wizard-gapfix-step`, `import-wizard-assets-step`; IW-4 passo 3 e piede; IW-5
`import-wizard-modal`, stepper, `import-wizard-duplicates-step`, `import-wizard-duplicate-resolver`, revisione, conferma
avvisi, `import-nway-compare`.

**Da rivedere per il developer:** in scuro il verde dello stepper e delle barre passa da `#166534`/fluo a `--lf-checked`
(`#429e79`); in chiaro l'ambra degli avvisi diventa quella della designer (`#ae4e00`, più bruna); il fuoco blu diventa
verde (convenzione 13); i bordi dei pulsanti contornati passano al 3:1 di `border-lf-input` (11); i badge di stato dei
duplicati (D1); la timeline della card del set (12).

## Passi

0. ✅ Bootstrap (16/10, 11:10–11:20): `npm ci` in `frontend/` (approvato una volta, uscita 0); piano nel journal; decisioni D1–D6 registrate.
   > **Note implementazione**: `nice -n 10 npm ci --no-audit --no-fund`, uscita 0; npm 11 avvisa che gli script
   > d'installazione di `esbuild` e `fsevents` non sono stati eseguiti (politica `install-scripts`): da verificare al primo
   > Vitest, senza approvarli né reinstallare.
   > **⚠️ Fuori pista**: alle 10:43 `theme-roles.mjs --report` (scanner node, 1 s, sola lettura) è girato con `nice` a
   > carico 84, sopra la soglia di 50 delle prove leggere; poi solo letture. Alle 11:02 il coordinatore ha portato il
   > branch a `6e569084a` (skill comune): rilette le regole, adottate le convenzioni 12, 18, 19 e 20.
1. ✅ Scrittura dei lotti IW-1…IW-5 in parallelo (16/10, 11:25–11:47), un sotto-agente per lotto (file disgiunti, niente git, niente prove,
   niente server), con la tabella della skill e le convenzioni di questo piano; revisione mia di ogni diff, elemento per
   elemento (regole 1, 2, 4, 5, 6, 8). Avviati il 16/10 alle ~11:25 (brief comune in sessione, `iw_brief.md`), più
   test-author per la riga della spec (D5).
   - ✅ **IW-1** (11:31): BrimEvidenceTable 52→0, BrimNoticeList 8→0, ParseDetailModal 141→0, ImportBrokerMismatchModal
     1→0 (lo `<style>` resta, D3). Revisione (`iw_review.mjs`): 82 righe, 0 segnalazioni, 51 mappature coerenti.
     > **Note implementazione**: commento delle evidenze `text-X-800` → `text-lf-X` (sta sulla card, non sulla tinta);
     > intestazione appiccicosa della tabella delle evidenze opaca anche in scuro (`bg-lf-panel`, il `/80` scuro cade);
     > chip d'esito dell'abbinamento (`ParseDetailModal:264`): attivo `bg-lf-panel text-lf-primary`, vuoto
     > `bg-lf-panel text-lf-muted` (oggi `gray-100` contro `gray-50`): da rivedere.
   - ✅ **IW-4** (11:33): AnalyzeStep 67→0, WizardFooter 101→0. Revisione: 58 righe; le segnalazioni sono attese (le
     condizioni doppie cadono con le direttive `class:dark:`; due tag multiriga riuniti su una riga, attributi identici).
     > **⚠️ Fuori pista**: il pulsante «riparse» (`AnalyzeStep`, fondo `bg-lf-card` dentro un pannello) aveva preso
     > `hover:bg-lf-neutral`: corretto in `hover:bg-lf-hover`. La convenzione 18 vale solo per un fondo pannello o un
     > elemento trasparente su un pannello; precisazione mandata agli agenti di IW-2, IW-3, IW-5.
   - ✅ **Spec T4** (test-author, 11:32): `tx-brim-import.spec.ts:234-235`, `step4.getByTestId('import-wizard-unresolved-count')`
     al posto di `[class*="amber"]`; non eseguita (slot B).
     > **Note di test-author** (fuori perimetro, backlog IW-8): con il campione IBKR il badge c'è sempre, quindi la
     > guardia `if` di T4 salta l'asserzione solo quando qualcosa si rompe (forma diretta: `toBeVisible()` poi
     > `toBeDisabled()`); la guardia esterna usa il testo tradotto `text=Resolve Assets` (c'è
     > `import-wizard-resolve-section`); il badge conta ogni asset non risolto, il pulsante blocca solo le righe
     > selezionate; IWR-001 di `tx-import-resolution.spec.ts` (righe ~473–485) copre già il caso senza guardie; i
     > commenti «amber badge» di quella spec (riga 43 e IWR-001) diventano falsi dopo IW-5; T1 non importa mai con
     > questo campione.
   - ✅ **IW-2** (11:38): ReportSetCard 75→0, UploadStep 20→0, SelectFilesStep 22→0. Revisione: 55 righe, 28 mappature;
     due hunk riuniti su una riga (attributi identici, < 300 caratteri).
     > **Note implementazione**: legenda dei buchi della timeline `border-lf-warning` senza riempimento, come prima;
     > checkbox del set fuori dal rimappaggio scuro di `app.css` (ora `border-lf-input`, `focus:ring-lf-focus`);
     > `dark:hover:bg-slate-750` tolto: la sfumatura 750 non esiste in Tailwind, la classe non generava nulla.
   - ✅ **IW-5** (11:45): ImportWizardModal 222→8 (m2 `#dc2626` → `var(--lf-danger)`, quindi vuoto), DuplicatesStep 77→0,
     ReviewStep 86→0, `pairCellHtml.ts` 6→2. Revisione: 127 righe, 74 mappature; segnalazioni attese (`var(--lf-danger)`,
     5 tag riuniti su una riga con attributi identici). Catene `confidenceBadgeClass`, `duplicateTierBadgeClass`,
     `diffCls` e `getRowClass` tutte su ruoli insieme ai loro elementi.
     > **Note implementazione**: maniglia di ridimensionamento della lista di priorità (`DuplicatesStep:126`,
     > `bg-gray-300 dark:bg-slate-600`) → `bg-lf-input` (un controllo a riposo; `neutral` sparirebbe in scuro): da
     > rivedere, in chiaro è più scura. Testo attenuato su `bg-lf-neutral` (cerchi dei passi futuri, iniziale del
     > plugin, nota «prima dell'apertura») ~4,0:1, coppia non misurata; oggi 3,8:1. Testo grigio sulle tinte d'avviso
     > di `ReviewStep` → `text-lf-secondary`.
   - ✅ **IW-3** (11:47): FixFlaggedStep 205→0, ImportAssetPicker 20→0, GapFixStep 95→0, AssetGroupStep 108→14 (i 14
     annotati: badge `KIND_TONES` con anello, 3 stelle, 2 conferme smeraldo). Revisione: 130 righe, 78 mappature, 6 tag
     riuniti senza token non-colore. Casi «solo dark» del controllo del coordinatore (base 594, 772, 867): sistemati
     (`bg-lf-card/70`; i due campi con `bg-lf-field text-lf-primary`).
     > **Note implementazione**: testi `-800/-900` su card (righe in attesa, riquadro della ripartizione) → `text-lf-X`
     > come da tabella: si perde il gradino rispetto ai `-600` vicini (`-on-soft` riprodurrebbe i vecchi colori): da
     > rivedere. `hover:bg-white` sulle sezioni tinte → `hover:bg-lf-card`: in scuro l'hover si vede appena.
   - ✅ **Audit d'insieme** (11:52, `iw_review.mjs` esteso ai tag riuniti): 17 file, 452 righe, nessun token non-colore
     cambiato a parte le condizioni delle direttive `class:dark:` tolte, la classe inesistente `slate-750` e
     `var(--lf-danger)`.
2. ✅ Prove leggere (16/10, 11:36–12:05), in serie, con `nice -n 10` e attesa del carico sotto 50 (`iw_light.sh` e
   `iw_comp.sh` in sessione):
   - `node frontend/scripts/theme/theme-roles.mjs --check`: pulito (prima di `--update`: 17 file scesi sotto il loro
     record; dopo: 0);
   - controllo «solo dark» del coordinatore (`dark_only_check.py 6e569084a`): 3 posizioni della base in
     `FixFlaggedStep` (594, 772, 867), verificate a mano: `bg-lf-card/70`, e i due campi (ora 764 e 859) con
     `bg-lf-field … text-lf-primary`;
   - `git diff --check` pulito; Prettier `--check` sui 18 file `.svelte`/`.ts`: pulito;
   - Vitest dei gate `themeRoles`, `themeTokens` (C4 compreso: nessun selettore del rimappaggio scuro reso morto, quindi
     `app.css` intatto), `themeComponentTokens`, `htmlInterpolation`: **4 file, 109 test verdi** (12:04);
   - Vitest dei componenti `ParseDetailModal`, `ImportBrokerMismatchModal`, `ReportSetCard`, `ReportSetCard.escape`,
     `FixFlaggedStep`, `GapFixStep`, `ImportWizardModal`, `importPairs`: **8 file, 181 test verdi** (11:55).
   > **⚠️ Fuori pista**: (1) Prettier voleva riunire su una riga lo `<span>` degli esiti di abbinamento di
   > `ParseDetailModal` (classi più corte): `prettier --write` su quel solo file, poi `--check` pulito. (2) La prima
   > corsa delle Vitest dei componenti (11:43) è caduta prima dei test: `Failed to resolve import "$lib/api/generated"`
   > (worktree nuovo). Per la regola del coordinatore, `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run
   > python dev.py api sync` fuori slot (11:49–11:50, uscita 0): ha scritto solo file ignorati
   > (`frontend/src/lib/api/generated*.ts`, `openapi.json`, `tool-contract*`) e un log vuoto
   > `backend/data/prod/logs/librefolio.log`, ignorato; nessun server, porta o DB. Seconda corsa verde. (3) Fra le 11:53 e
   > le 11:57 la rete è caduta e il turno si è chiuso con errore: nessun comando era in volo (Vitest finite alle 11:55),
   > nessun processo rimasto, porta 6151 libera.
3. ⏳ Slot pesanti A (IW-1…IW-3) e B (IW-4, IW-5), quando li assegna il coordinatore: `api sync` (fatto),
   `front check`, `front-utility core-unit`, `front-utility component-unit`, E2E mirati (elenco nella sezione dei lotti).
   Superato dal passo 7: uno slot unico per tutto, chiesto e concesso il 16/10.
4. ✅ Checkpoint 1 (16/10, 12:05; committato dal coordinatore: `48ecea1e2`): `--update` della baseline, che si stringe solo sulle 17 righe dell'area (m1 8.249 →
   **6.967**, −1.282; m2 54 → **53**, via `#dc2626`); voci IW-1…IW-8 nel backlog; messaggio al coordinatore con file,
   prove, esclusioni, conflitti, messaggio di commit, «dove guardarlo». Poi FROZEN.
   - Area dopo il lotto: m1 1.310 → **28** (AssetGroupStep 14, GapFixToggle 4, ImportWizardModal 8, `pairCellHtml.ts`
     2), m2 1 → **0**.
5. ✅ Dopo la base merge con i ruoli nuovi di T (16/10, 12:13–12:21; coordinatore: checkpoint 1 = `48ecea1e2`, base
   merge `b3162db80` con la punta `b171c058e`, che porta `f043c1b58`):
   - `api sync` dopo la base merge (12:16, uscita 0, solo file ignorati);
   - i 4 pulsanti pieni di D2 (backlog IW-1): `asset-group-confirm-all` e `asset-group-confirm-{id}` → `bg-lf-success
     text-lf-on-status hover:bg-lf-success-hover`; `import-wizard-warning-confirm` → `{… ? 'bg-lf-warning
     hover:bg-lf-warning-hover' : 'bg-lf-info hover:bg-lf-info-hover'} text-lf-on-status`; `create-primary-confirm` →
     `bg-lf-info text-lf-on-status hover:bg-lf-info-hover` (da rivedere: è l'azione primaria del suo dialogo, forse
     `action`; OK del coordinatore a segnarlo);
   - ritocco chiesto dal coordinatore: il campo dell'importo della ripartizione (`FixFlaggedStep:764`) prende
     `placeholder:text-lf-placeholder` (`app.css` colora testo e segnaposto dei campi nativi solo senza classi `-lf-`);
   - prove: `--check` pulito; `dark_only_check.py b3162db80` 0; `native_field_check.py 6e569084a` 0 su 16 file;
     `git diff --check` e Prettier puliti; Vitest dei gate più `FixFlaggedStep` e `ImportWizardModal`: **6 file, 138
     test verdi** (12:19); `--update`: m1 6.967 → **6.953** (AssetGroupStep 14 → 8, ImportWizardModal 8 → 0, riga tolta).
   - **Area:** m1 1.310 → **14** (AssetGroupStep 8: badge `KIND_TONES` con anello, 3 stelle; GapFixToggle 4;
     `pairCellHtml.ts` 2), m2 **0**.
   - ✅ Checkpoint 2 committato dal coordinatore: `9c79d5b35` (6 file); SHA messo nella voce IW-1 del backlog.
6. ✅ Preparazione dello slot (16/10, 12:22–12:53; coordinatore, 12:21: «uno alla volta, sotto `nice` e con carico sotto 50, senza server»),
   script `iw_prep.sh` in sessione, log `prep_*.log`:
   1. `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py front build --debug`: uscita 0 in
      482 s; il build lancia `svelte-check` sull'albero intero: **0 errori, 0 avvisi** (è il `front check` di
      `npm run check`, sullo stesso albero `9c79d5b35`);
   2. `… dev.py mkdocs build`: uscita 0 in 203 s, 3.076 URL relativi risolti;
   3. `… dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-iw db populate --force --clean --with-reports`
      (cartella della corsia, assente fino a ora; `--with-reports` come il populate che il runner degli E2E rifà da
      sé all'inizio di una corsa): uscita 0 in 34 s; istantanea del DB nell'archivio ignorato `.testLog/00_archive/`.
   Porta 6151 libera alla fine; nessun server avviato.
7. ✅ C4 dopo la base merge `b2466931d` (16/10, 14:58–15:01; il coordinatore ha unito la punta `e402d3b87`, con TR, BK e
   DV, e committato le note del giornale in `1bcf00187`): sull'albero unito `text-gray-900` non ha più usi, perché gli
   ultimi li ha tolti l'import, e C4 è rosso. In `frontend/src/app.css` il selettore doppio `html.dark .text-gray-800,
   html.dark .text-gray-900 {` perde la seconda riga; la regola resta su `.text-gray-800`, che ha ancora un uso (L-20).
   Verifica con `classUses()` dello scanner: `text-gray-900` 0, `text-gray-800` 1, nessun'altra classe del
   rimappaggio scuro senza usi. Prove: `--check` pulito, Prettier pulito su `app.css`, `git diff --check` pulito,
   Vitest `themeTokens.gate.test.ts` **19/19**, `themeRoles.gate.test.ts` **52/52**.
   > **⚠️ Fuori pista**: `app.css` appartiene a T; questa è l'unica eccezione del kickoff («se il gate C4 ti chiede di
   > togliere un selettore del rimappaggio scuro, perché hai tolto il suo ultimo uso, lo togli e lo dichiari nel
   > checkpoint»).
8. ✅ Slot pesante unico (16/10, 15:02–15:38, corsia 6151 + `/tmp/librefolio-r2-iw`, HEAD `ec9fec52a`, cioè la base
   merge `b2466931d` con la punta `e402d3b87` (TR, BK, DV) più il ritocco C4; taglio del coordinatore alle 15:50),
   script `iw_slot.sh` in sessione, log `slot_*.log`:
   1. `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync`: uscita 0 in 35 s;
   2. `… dev.py front build --debug`: uscita 0 in 405 s; `svelte-check` sull'albero intero **0 errori, 0 avvisi**: è il
      `front check`, non ripetuto;
   3. `… dev.py test --test-port 6151 --data-dir /tmp/librefolio-r2-iw --fresh-run --workers 4 front-transaction all`:
      uscita 0 in 1.341 s; due corse di Playwright, **381 test verdi, 0 rossi**, 32 saltati per progetto (desktop o
      mobile): 45 spec desktop, 347 verdi; le due spec dei set di report su tutti i progetti, 34 verdi e 32 saltati.
      Verdi le 13 spec dell'import del piano (tx-import-flow, tx-import-broker-mismatch, tx-ca-contract,
      tx-bulk-diagnostics, tx-import-report-set, tx-import-upload, tx-import-file-selection, tx-import-degiro,
      tx-asset-identity, tx-import-duplicate-precedence, tx-import-resolution, tx-brim-import, tx-import-matching),
      più tx-bulk-import-handoff, tx-import-asset-inspector e tutte quelle di TR appena entrate;
   4. `… front-utility core-unit`: **179 file, 6.418 test verdi** (60 s);
   5. `… front-utility component-unit`: **154 file, 4.042 test verdi** (338 s).
   Porta 6151 libera alla fine, nessun processo rimasto; solo artefatti ignorati (`.testLog/`, `frontend/build/`,
   `frontend/test-results/`, `.svelte-kit/`).
   > **Note implementazione**: `front-transaction all` al posto delle 13 invocazioni separate: un solo populate e un
   > solo server, e copre anche le spec di TR che incrociano l'import (confronto, Bulk); il coordinatore l'ha saputo
   > all'avvio dello slot.
   > **⚠️ Fuori pista**: nessuno. Il carico della macchina è arrivato a 142 durante gli E2E: i test hanno impiegato
   > 13–20 s l'uno, nessun rosso.

## Definizione di fatto

- Ogni classe legacy dei file del lotto è sui ruoli, tranne le voci annotate qui sopra; m2 dell'area a 0.
- `--check` verde (cricchetto e grammatica G1–G4); gate `themeRoles`, `themeTokens`, `themeComponentTokens` (e
  `htmlInterpolation` per IW-5) verdi; Prettier e `git diff --check` puliti; Vitest dei componenti verdi.
- Slot pesante: `front check` 0/0, `core-unit`, `component-unit` e E2E mirati verdi.
- Baseline stretta con `--update`; nessun `--accept`; nessuna riga allargata.
- Piano aggiornato a ogni passo; backlog IW-n per i rimasti legacy e le richieste di ruolo; porta 6151 libera alla consegna.

> **✅ Verifica (16/10, 15:40):** tutti i punti sono soddisfatti. Area: m1 1.310 → 14, m2 → 0. I 14 rimasti sono annotati:
> - badge `KIND_TONES` con anello e 3 stelle (IW-2, IW-3);
> - l'interruttore, che va nel lotto di T;
> - il chip viola (IW-5).
>
> Prove:
> - prove leggere verdi a ogni consegna;
> - slot pesante verde: `svelte-check` 0/0, `core-unit` 6.418, `component-unit` 4.042, E2E 381 verdi;
> - baseline solo stretta (8.249 → 6.953 per IW), nessun `--accept`;
> - porta 6151 libera.
>
> Resta, fuori dal perimetro 1:1:
> - la revisione dell'aspetto del developer, dalla galleria o dall'anteprima (D-T21), sulla lista «da rivedere» (IW-7);
> - le voci IW-2…IW-8.

## Rischi e dipendenze

- **FE8b di W** (spostamento delle cartelle): sequenza da decidere col coordinatore, mai in parallelo.
- **Baseline condivisa** `themeRoles.baseline.tsv`: conflitti testuali con gli altri workstream colori, `--resolve` al merge.
- **C4:** nessun selettore del rimappaggio scuro è usato solo nell'area; dipende dall'ordine degli altri ingressi (se
  IW toglie l'ultimo uso, toglie il selettore da `app.css` e lo dichiara).
- **Skill comune D-T29 di T:** quando arriva, le convenzioni di questo piano si riallineano a lei.
- **Aspetto misto** finché i lotti non sono tutti dentro (D-T20).
- **E2E indebolita a vuoto** (T4) se D5 non passa prima di IW-5.
