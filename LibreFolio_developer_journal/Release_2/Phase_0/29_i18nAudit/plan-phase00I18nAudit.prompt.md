# Phase 0 — 29 · Audit i18n: chiavi inutilizzate, doppioni, plurali, strumento

> **Stato: secondo turno PRONTO AL CHECKPOINT (workstream O), 2026-10-07.** Il primo turno (S0-S10) è
> committato: `8730ca823` · `08b885d43` · `2b86cc175` · `6f10f33c5` · `a8bac445d` su `bae2515bd`. Il
> secondo (S7b, S7c, S7a-bis, S7-ter, S8b, S11, S7-bis, S12) è su `d07412899`, che contiene A13 e N.
> L'analisi (§1-§10, Appendici) è stata
> scritta il 2026-10-06 su `9f06df702` in plan mode. Questa copia è entrata nel journal al passo S0,
> non committata. Script, log e tabelle dell'analisi sono in `files/` della sessione O
> (`analyze_keys.py`, `resolve_prefix.py`, `classify.py`, `dups.py`, `icu_collisions.js`,
> `prototype_rules.py`, `plural_sites.py`, `classification.json`, `dup_groups.json`).
>
> **Autorizzazione del developer**, testuale, inoltrata dal coordinatore (ask_user, 07/10 ~00:33):
> «approva tutte, anche le dubbie, ma di a o di cercare di migliorare il programma di audit per i
> falsi positivi».
>
> **Decisioni del §14** (dal coordinatore, 2026-10-07):
> 1. si tolgono le 107 morte PAC e le 2 nascoste (`routeCapMissing`, `sections.assets`);
> 2. si tolgono le 8 dubbie: la skill `devpy-i18n` si aggiorna per `*Abbr` e
>    `common.{seeAll,recentTransactions}`, e per `onboarding.welcome.skipHint` il campo resta vuoto;
> 3. M1 col ramo `many`, più il gate M2 (vitest sui cataloghi reali e caratterizzazione);
> 4. condensazioni C1-C4 adesso, C5 dopo N;
> 5. le morte `dashboard.*` e `brokers.lots.*` dopo N, ricontrollate; `risk.simulation.regimeTruncated`
>    dopo A;
> 6. `WeightBars.svelte` si toglie adesso, con le sue 2 chiavi;
> 7. entra nel lotto, su richiesta del developer, il miglioramento dello strumento contro i falsi
>    positivi: R1-R7 più il §5.3, cioè i template annidati senza creare falsi morti. Ogni regola nuova
>    ha il suo test. Resta nel backlog solo la famiglia fantasma di `evaluator.py:968`. Se il §5.3
>    diventa grande, va in un commit a parte, annunciato prima.
>
> **Permessi:** `npm ci` una volta, dal lock; in `scripts/test_runner/_frontend_utility.py` solo righe
> aggiunte, per registrare i test nuovi.
>
> **Decisioni del secondo turno** (dal coordinatore, 2026-10-07, approvate dal developer):
> - via a S7b e S7c dopo il fast-forward a `d07412899`, con C5 e il miglioramento dello strumento ancora
>   aperto; O è l'unico a scrivere nei cataloghi fino alla chiusura;
> - `AgeLabel.svelte` si toglie adesso con le sue 5 chiavi, come `WeightBars.svelte`;
> - si tolgono le 3 `planner.problems.*` trovate dal prototipo (S7a-bis);
> - R8-R12 entrano con i test rossi del test-author prima del codice;
> - `onboardingTourSurfaces.svelte.ts` ed `EditBuffer.ts` non si toccano: backlog knip del coordinatore;
> - `onboarding.settings.groups.contextual` si toglie (14:20, «Sì, toglierla»);
> - nessuna riga di CHANGELOG: le funzioni toccate non sono ancora uscite.
>
> **Regole:** corsia 6160 con `/tmp/librefolio-r2-o`, un comando per volta; cataloghi solo con
> `dev.py i18n`; nessun file di N, A o L; test nuovi scritti dal test-author e rossi prima del codice.
>
> Collegamenti: backlog delle chiavi PAC di D (`13_pacAllocator/implementation/plan-phase00PacRound5PostMerge.prompt.md:3159`,
> `plan-phase00PacP1FinalRemoval.prompt.md:33` e S8 «Fuori pista»), chiavi del vecchio tour
> (`21_onboarding/plan-phase00OnboardingRound8-PostReview.prompt.md:527`), decisione
> `LibreFolio_devWiki/wiki/decisions/i18n-key-rationalization.md` (Option B).

## 0. Contesto e baseline

| Voce | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-supreme-spoon` |
| Ramo | `e-alfy-o-audit-i18n` (rinominato dall'app) |
| HEAD dell'analisi | `9f06df7020fa…` (treno 6), dopo il fast-forward del developer |
| Bersaglio attuale | `dev_release2` = `bae2515bd` (treno 7, lotto di L). Verificato in sola lettura: cambia testo semplice di 3 chiavi (`reportSet.exclude` tolta, `reportSet.partlySelectedBlocks` nuova, `reportSet.incompleteBlocks` con la coda nuova), nessun ICU; 171 righe di sorgente cambiate, **0** riferimenti alle 354 chiavi classificate qui. L'analisi resta valida. |
| Corsia | `--test-port 6160 --data-dir /tmp/librefolio-r2-o`; server di review su 6170 |
| Coordinatore | `c8328a01-f208-4ade-a352-0486d1f14de2` |
| Ambiente | `node_modules` assente (vitest, Prettier e svelte-check richiedono `npm ci`, da autorizzare); `.env` assente; `graphify-out/graph.json` assente → pagine della devWiki lette direttamente |

Contesto wiki: `decisions/i18n-key-rationalization` (si condensa solo se significato, contesto e
valore coincidono nelle 4 lingue); `problems/i18n-key-assertion-false-green` (mai asserire sul testo
tradotto); la skill `devpy-i18n` (namespace protetti, Accepted Duplicates).

## 1. Stato verificato sul codice

| Misura | Kickoff | Verificato a `9f06df702` |
|---|---|---|
| Chiavi per lingua | 4356 | **4356**, stesso insieme nelle 4 lingue, tutte tradotte; i 4 file sono in forma canonica (`indent=2`, `ensure_ascii=False`): una rimozione con `dev.py i18n remove` dà diff minimi |
| «Probabilmente inutilizzate» | 250 | **250** |
| «Non verificate» | 86 | **86** |
| Chiavi esatte | 4689 | **4385** (il 4689 di D non si riproduce su questa base) |
| Prefissi dinamici | 108 | **108** (89 senza i test) |
| Gruppi di doppioni | — | **426**: 204 in 4 lingue, 83 in 3, 50 in 2, 89 in 1 |
| Messaggi ICU con argomenti | — | 526 per lingua; 74–77 sensibili alla lingua (`plural`, `number`, `date`…) |

`dev.py i18n audit` e `--duplicates` scrivono solo su stdout (formato `none`): eseguiti, nessun file
tracciato toccato (`git status` pulito).

## 2. Chiavi: morte, dinamiche, dubbie

### 2.1 Metodo

1. Le 250 + 86 dell'audit, più le **18** che l'audit dà per usate **solo grazie ai file di test**
   (§5): 354 chiavi.
2. Per ognuna: letterale intero nel sorgente non di test, coda relativa a una costante di prefisso
   (`const KEY = '…'` + `${KEY}.resto` o helper locale con il resto tra apici), liste fisse nello
   stesso file, prove nel backend (dizionari, f-string, codici), storia con `git log -S`.
3. I casi con evidenza ambigua li ho verificati a mano riga per riga (tabelle in Appendice A).

### 2.2 Risultato

| Classe | Totale | Dall'elenco «morte» | Dalle «non verificate» | Vive solo per i test |
|---|---|---|---|---|
| **Dinamica o indiretta** (viva, da tenere) | **179** | 118 | 50 | 11 |
| **Morta** (sicura da togliere) | **167** | 132 | 35 | — |
| **Dubbia** (decide il developer) | **8** | — | 1 | 7 |

Quindi **118 delle 250 «morte» sono vive**: il dato dell'audit è inutilizzabile senza la correzione del §5.

Per namespace (dinamica / morta / dubbia): `tools` 43/110/0 · `aiExport` 34/0/0 · `dashboard` 31/7/0 ·
`brokers` 23/11/0 · `onboarding` 1/28/1 · `chartSettings` 10/1/5 · `dataQuality` 9/2/0 ·
`providerErrors` 9/0/0 · `importWizard` 8/2/0 · `sectors` 7/0/0 · `support` 3/0/0 · `common` 1/0/2 ·
`files` 0/2/0 · `assetDetail` 0/1/0 · `assets` 0/1/0 · `changelog` 0/1/0 · `signals` 0/1/0.

**Le 179 vive**, per meccanismo:

| Meccanismo che l'audit non vede | Chiavi | Esempio (prova) |
|---|---|---|
| Wrapper con nome diverso da `t`/`_`: `translateOr($_, 'k')`, `label('k')`, `translate('k')`, `tr('k')` | 68 | `LotWacPriceChart.svelte:608-622`, `YieldOnCostCell.svelte:71-130`, `promptRenderer.ts:310-316`, `modeText.ts:21-65` |
| Proprietà `displayI18nKey`, `descriptionI18nKey` e `afterCopyKey` | 25 | `ai-export/catalog/shared.ts:133-214`, `support/supportLinks.ts:37-53` |
| Helper locale su costante di prefisso: `text('compute.title')` | 24 | `planner/result/KpiCards.svelte:25,45`, `tile()` a `:96-110` |
| Backend: dizionario `_message_key_for_issue` → `message_i18n_key` | 9 | `lots_analysis_service.py:2027-2039,1892` → `DataQualityBanner.svelte:158` |
| Backend: codici errore dei provider | 9 | `resolveProviderError.ts:48`; codici emessi in `backend/app` |
| Backend: enum `FinancialSector` senza spazi | 7 | `sector_fin_utils.py:24-33` → `assetTypes.ts:427` → `AllocationPieChart.svelte:177` |
| Backend: f-string + vocabolario camelCase | 5 | `ai_export/analyses/catalog.py:77` (`"deeperTechnical"` a `:92`) |
| Liste fisse nello stesso file: STEPS, `EVENT_BADGE_KEY`, `*_FALLBACKS`, sezioni | 26 | `ImportWizardModal.svelte:136-143` → `:4262`; `ChartSignalsSection.svelte:436-440`; `LedgerTable.svelte:38-56`; `ProofPanel.svelte:39-45`; `OriginBadge.svelte:29`; `ResultView.svelte:53` |
| Ternario multilinea, array con una cifra nel segmento (`line2`), suffisso `${displayNameKey}Full` | 6 | `ChartSettingsModal.svelte:339-343`, `OnboardingIntroScene.svelte:26`, `ChartSignalsSection.svelte:142` |

**Le 167 morte**:
- **107** `tools.pacAllocator.planner.*`: il backlog di D (decisione (a): «le chiavi restano fino a fine
  round»; poi «vanno nel backlog del coordinatore»). Ci sono 80 delle 86 dell'elenco di D a `:3159`,
  più 27 rimaste senza lettore nei round successivi. Delle altre 6, 2 sono di nuovo usate
  (`result.kpi.source`, `result.proof.floatingFinished`) e 4 sono morte nascoste (§2.3);
- **3** `tools.{contractVersion,implementationVersion,open}`: le «tre chiavi `tools.*`» di D (§7);
- **22** del vecchio tour (`onboarding.tour.steps.{assets,assetsAdd,assetsConfig,brokers,brokersAdd,brokersCurrency,fxAdd,fxPair,settings,tools,transactionsImport}.{title,description}`),
  mai lette dal codice (`git log -S` vuoto). Il Round 8 dell'onboarding le dichiara «da togliere a fine
  round»;
- **6** onboarding sostituite: `actions.{pause,skipPermanently}`, `intro.title` (l'`h1` è il testo fisso
  «LibreFolio», `OnboardingIntroScene.svelte:139`), `settings.{nextImport,replayOnNextImport,replayReady}`
  (sostituite da `armedAtNextTrigger` e `replayNextTrigger`, `OnboardingReplaySection.svelte:108-117`);
- **9** `brokers.lots.*`: doppioni delle `dashboard.*` che il codice usa davvero, o resti del FIFO v3;
- **7** `dashboard.{costsTooltip,gains,holdings,losses,realized,sharedScale,unallocated}`: resti del refactor
  `13052a006`;
- **13** senza alcun riferimento (elenco in A.2).

**Le 8 dubbie**:
- `chartSettings.signals.{assetComparison,compound,fxPair,linear,sine}Abbr`: lo schema «Abbr» è
  documentato nella skill, ma nessun codice lo legge;
- `common.{recentTransactions,seeAll}`: chiavi canoniche della skill, oggi senza lettori;
- `onboarding.welcome.skipHint`: il campo esiste ma vale `''`.

### 2.3 Morte nascoste, fuori dalle 354

L'audit le dà per «usate», ma non lo sono:
- `tools.pacAllocator.planner.problems.routeCapMissing`: la assolve il prefisso legacy;
- `tools.pacAllocator.planner.result.sections.assets`: la assolve la parola «assets» del vocabolario
  backend (le sezioni sono a `ResultView.svelte:53`);
- `tools.pacAllocator.planner.result.weights.{finalShort,targetShort}`: le legge solo `WeightBars.svelte`,
  che **nessuno importa** (codice morto);
- `risk.simulation.regimeTruncated`: zero riferimenti, nascosta dalla regressione del §5, difetto 6.

### 2.4 Chiavi composte dal backend: `evaluator.py:968`

`backend/app/services/pac_allocator/evaluator.py:968` scrive
`explanation_key=f"tools.allocation.constraints.{code.lower()}"` in `ConstraintRef` (`models.py:664`).
- È un campo interno: il frontend non lo legge.
- Gli `explanation_keys` dell'API sono sempre vuoti (`planner_report.py:628`).
- `tools.allocation.*` ha **0** chiavi nel catalogo: le ha tolte D alla riga 13.

Nessuna chiave dipende da questa riga. È una **famiglia fantasma**: lo strumento la deve segnalare
(§5, R7); la modifica del backend va nel backlog, già annotata da D.

## 3. Doppioni

I 426 gruppi, classificati con lo stesso algoritmo dell'audit:

| Categoria | Gruppi | Esito |
|---|---|---|
| Valori diversi in almeno una lingua | 211 | si tengono: la regola vuole valori uguali in tutte e 4 |
| Contengono una chiave protetta (namespace dinamico o famiglia risolta) | 55 | si tengono |
| Già in «Accepted Duplicates» | 6 | si tengono |
| Uguali senza badare alle maiuscole, diversi con le maiuscole | 13 | si tengono (la skill: le maiuscole hanno un ruolo grammaticale) |
| Spariscono togliendo le chiavi morte | 29 | risolti dal §2 |
| **Candidati**: uguali e attivi in 4 lingue | **112** (280 chiavi) | vedi sotto |

Dei 112 candidati, quasi tutti sono **doppioni di contesto**, che per la decisione Option B si tengono:
- metadati dei plugin dei segnali, emessi dal backend (`signals.<plugin>.{name,output}`;
  «Overbought», «Oversold» e «Neutral» × 4 plugin);
- namespace di modulo del planner PAC (convenzione di D: ogni modulo dichiara la sua costante);
- parole generiche in ruoli diversi («Period» è sia una tab, sia una colonna, sia un passo dell'AI Export;
  «Type», «Status», «Price»…);
- aree attive: `risk.*` (A), `dashboard.*` (N).

**Proposta di condensazione**: piccola, con i chiamanti fuori dai lavori attivi.

| # | Gruppo | Si tiene | Si toglie | Si modifica |
|---|---|---|---|---|
| C1 | «Zoom in» | `uploads.zoomIn` | `uploads.previewZoomIn` | `FilePreviewModal.svelte:683` |
| C2 | «Zoom out» | `uploads.zoomOut` | `uploads.previewZoomOut` | `FilePreviewModal.svelte:677` |
| C3 | «Size» (dimensione del file) | `uploads.fileSize` | `uploads.size` | `AssetPickerModal.svelte:200` |
| C4 | suggerimento dell'editor, desktop e mobile (stesso editor, due pagine) | nuove `dataEditor.editorTip{Desktop,Mobile}` (valori attuali) | `assetDetail.editorTip*`, `fxDetail.editorTip*` | `assets/[id]/+page.svelte`, `fx/[pair]/+page.svelte` |
| C5 (dopo N) | campi del lotto, modale e tabella | `brokers.lots.{currentValue,fifoPnl,openQuantity,openReturn,originalQuantity,totalPnl}` | `brokers.lots.modal.*` omonime, `brokers.lots.tooltip.totalPnl` | `LotCustodyModal.svelte`, `LotGanttChart.svelte`, `LotComparisonChart.svelte` |

Non si condensano:
- `dashboard.aiExport`, `assetDetail.aiExport`, `fxDetail.aiExport`: le chiavi entrano nel testo dei
  prompt (`ai-export/catalog/shared.ts`), e N tocca le pagine dashboard e broker;
- `date.today` e `datePicker.today`: guadagno minimo;
- tutto ciò che è dentro `risk.*` e `importWizard.*`.

Da aggiornare nella skill `devpy-i18n`:
- `chartSettings.signals.*` non è più un prefisso dinamico nel codice: il prefisso viene solo dai test;
- tolte dal codice `emaAbbr` e `dashboard.holdings`;
- tolte dal codice le chiavi canoniche `common.seeAll` e `common.recentTransactions`;
- il conteggio «~1476 keys» non è più vero;
- nuove regole: test esclusi, cache ICU (§4).

## 4. svelte-i18n: la cache dei formatter ignora la lingua

**Il meccanismo** (`svelte-i18n@4.0.1`, la versione del lockfile e anche l'ultima pubblicata:
`dist/runtime.js`, letto dal pacchetto su unpkg; per D sono le righe 383-392 e 496-500):
- `getMessageFormatter = monadicMemoize((message, locale = getCurrentLocale()) => new IntlMessageFormat(...))`;
- `monadicMemoize` passa **un solo argomento** e usa come chiave della cache `JSON.stringify(message)`;
- ne segue che il `locale` passato è sempre ignorato; vale la lingua corrente **alla prima compilazione** di quel testo.

Tutto ciò che dipende dalla lingua dentro il messaggio resta quello della prima lingua:
- le categorie del plurale e di `selectordinal`;
- il formato numerico di `#` e di `{n, number}`;
- date e ore (`date`, `time`).

**Quando scatta.** Si cambia lingua senza ricaricare la pagina:
- `LanguageSelector.svelte:55`;
- `PreferencesTab.svelte:166`;
- la welcome, `welcome/+page.svelte:115,152`;
- dopo il login, `auth.ts:82`, se la lingua salvata nel browser è diversa da quella dell'utente.

Nessun `$t(…, {locale})` nell'app.

**Impatto misurato** (`icu_collisions.js`, regole CLDR di Node `Intl`): **3** testi sensibili alla
lingua sono identici fra due cataloghi, tutti **EN = FR** e tutti con differenza visibile:

| Chiave | Testo (EN = FR) | Effetto |
|---|---|---|
| `importWizard.reportSet.gapFix.positions` | `{n, plural, one {# position} other {# positions}}` | n = 0: FR «0 position» con le regole FR; se compilato prima in EN resta «0 positions». Al contrario, in EN appare «0 position». Separatori: «1,000» in UI FR |
| `importWizard.reportSet.gapFix.corrections` | `{n, plural, one {# correction} other {# corrections}}` | idem |
| `tools.pacAllocator.planner.review.sources` | `{count, plural, one {# source} other {# sources}}` | idem |

I conteggi sono interi, quindi oggi l'errore visibile è solo con n = 0 dopo un cambio di lingua
(e i separatori sopra 1 000). È però una **trappola latente**: un qualsiasi testo ICU uguale fra due
lingue (sigle, «ETF», numeri soli) eredita le regole della prima.

**Mitigazione proposta:**
- **M1, dati**: rendere diversi i 3 testi FR con il ramo CLDR `many`, che è anche il francese corretto
  per i milioni: `{n, plural, one {# position} many {# de positions} other {# positions}}`, e lo stesso
  per `correction` e `source`. L'output non cambia sotto il milione. Alternativa visibile:
  `=0 {aucune position}`. **Decide il developer.**
- **M2, gate**: un test vitest puro sui 4 cataloghi reali. Fallisce se un testo con `plural`,
  `selectordinal`, `number`, `date`, `time` o `#` è identico in due lingue. In più, un test di
  caratterizzazione: `getMessageFormatter(m, 'fr')` dopo `(m, 'en')` restituisce la stessa istanza.
  Se una versione futura corregge la libreria, il test diventa rosso, ed è il segnale per togliere
  la protezione.
- Non proposte: ricaricare la pagina a ogni cambio di lingua (troppo invasivo) e una patch della
  libreria (vietati `npm install` e `patch-package`). Segnalare il difetto a monte
  (`kaisermann/svelte-i18n`) è un'azione esterna: decide il developer.
- Nota: `src/__tests__/riskWarningCatalogue.ts:65` chiama `getMessageFormatter(sentence, 'en')` come se
  la lingua contasse. È innocuo, perché usa solo `getAst()`; basta correggere il commento.

## 5. Lo strumento d'audit: difetti misurati e correzione

### 5.1 Difetti

1. **I test contano come prove.** `find_used_keys_in_sources()` (`frontend/scripts/i18n-audit.py:76-166`,
   la scansione è a `:131`) e `collect_from_source()` (`scripts/i18n_usage.py:227`) leggono anche
   `*.test.ts`, `__tests__/` e `__mocks__/` (323 file in `src/`). Misurato su una copia di `src/` senza
   i test:
   - chiavi esatte da 4385 a 3611: **774** stringhe vengono solo dai test, di cui 18 sono chiavi del
     catalogo;
   - prefissi da 108 a 89: 19 vengono solo dai test, fra cui le radici nude `common` e `onboarding` e i
     prefissi `chartSettings.signals` e `risk.warnings`;
   - **49 verdetti cambiano**. 31 chiavi «non verificate» diventano morte: 30 lo sono davvero, mentre
     `onboarding.intro.line2` è viva (difetto 2). 18 «usate» diventano morte: di queste 11 sono vive
     (difetti 2-4 e R6) e 7 sono dubbie.
2. **Chiamate e proprietà non riconosciute.** `_CALL` (`i18n_usage.py:53`) vede solo `t`/`$t`/`_`/`$_`.
   Le regex indirette (`i18n-audit.py:104-116`) vedono solo alcune proprietà `*Key`, e solo chiavi di
   3 segmenti fatti di lettere. → 93 falsi «morti», più 4 vivi solo per i test.
3. **Il backend si vede solo nelle assegnazioni `…_i18n_key="lett."`** (`i18n-audit.py:208`). Sfuggono
   i dizionari (9 chiavi `dataQuality`) e le f-string (5 `aiExport.additionalData.reason`; la famiglia
   fantasma di `evaluator.py:968`).
4. **Il vocabolario dei produttori è solo snake_case minuscolo** (`_CODE_LITERAL`, `i18n_usage.py:90`):
   sfuggono `UPPER_SNAKE` (`providerErrors`), camelCase (`deeperTechnical`) e i nomi con spazi
   (`"Health Care"`).
5. **Le chiavi relative e le liste fisse nello stesso file** non contano come prova
   (`text('compute.title')`, `titleKey: 'reportSet.gapFix.stepTitle'`, `*_FALLBACKS`): 50 chiavi.
6. **Regressione dell'unione tipata.** `RiskResultFrame.svelte:27` adesso ha `prefix: 'errors'` (un solo
   letterale). `_union_members` (`i18n_usage.py:113-120`) vuole almeno 2 membri e restituisce `None`,
   quindi la radice nuda `risk` non viene superata e **assolve tutte le 481 chiavi `risk.*`**. I test del
   gate passano solo sulla forma sintetica `'errors' | 'warnings'`. Con la correzione (patch in memoria)
   emergono 30 candidate in `risk.*`: 29 hanno foglie in liste relative (`RiskReturnLevel.svelte:117`,
   `L4Replay.svelte:124-129`, `L4WhatIf.svelte:82`), quindi servono le regole del difetto 5; morta vera
   è solo `risk.simulation.regimeTruncated`.
7. **Falsi «usati».** Il prefisso legacy assolve tutto il sotto-albero (`routeCapMissing`); il
   vocabolario backend generico copre le parole comuni (`sections.assets`); il codice morto
   (`WeightBars.svelte`) tiene in vita le sue chiavi.
8. **Template annidati.** In `` `…${$t(`risk.valueStatus.${s}`)}…` `` (`CorrelationHeatmap.svelte:487-488`)
   `_TEMPLATE` (`i18n_usage.py:56`) accoppia male i backtick; oggi quelle famiglie reggono solo grazie
   ai prefissi legacy. Il prototipo che li toglie dà 117 «morte» quasi tutte false: **i prefissi legacy
   non si tolgono in questo lotto.**

### 5.2 Correzione proposta (lotto A, in `scripts/i18n_usage.py`; `i18n-audit.py` resta la CLI)

- **R1**: un solo `iter_source_files()` / `is_test_source()` (`*.test.ts`, `*.spec.ts`, `__tests__/`,
  `__mocks__/`), usato da entrambe le scansioni.
- **R2, prova letterale**: qualunque stringa fra apici o backtick uguale a una chiave del catalogo, nel
  sorgente non di test e in `backend/app`, vale USED. Copre wrapper, proprietà, ternari, array e
  dizionari del backend.
- **R3**: unione tipata anche con un solo membro.
- **R4**: famiglie dalle f-string del backend (`f"ns.a.{…}"`), con vocabolario allargato a camelCase,
  `UPPER_SNAKE` e Title Case senza spazi.
- **R5**: per una famiglia risolta nel file X, la chiave `famiglia + resto` (anche con punti) è USED se
  `resto` compare fra apici in X. Solo per famiglie strette (≥ 3 segmenti); le larghe restano «non
  verificate».
- **R6**: composizione per suffisso, `` `${expr}Full` ``: la chiave è una chiave usata più il suffisso.
- **R7**: sezione del report «famiglie backend senza catalogo», non bloccante (`tools.allocation.constraints.`).

**Esito atteso**, verificato a mano sulle 354:
- morte = le 167, più le 8 dubbie;
- più `risk.simulation.regimeTruncated` e le 2 nascoste del PAC che R5 fa emergere (`routeCapMissing`,
  `sections.assets`);
- ogni scarto residuo va spiegato nel piano.

**Test** (test-author): nuove classi in `backend/test_scripts/test_utilities/test_i18n_usage_gate.py`
(PURE, sorgenti sintetici, già registrato come `utils gate-i18n-usage`). Ogni regola va provata nelle
due metà, quando scatta e quando permette. In più un caso con la **forma reale** `prefix: 'errors'`.

### 5.3 Fuori dal lotto (backlog)

- Sostituire l'assoluzione legacy con un tokenizer vero: template annidati, falsi «usati».
- Rendere l'audit consapevole del codice morto: `WeightBars.svelte`, con knip.

## 6. Plurali calcolati con `Number(…)`

La cura di D: `pluralCount` (`planner/format.ts:161-174`) conta dalle cifre mostrate (`1.5` dà
`1 + 0.5`; `1.00000000000000000001` è plurale) e restituisce NaN, cioè la categoria `other`, quando
il valore è mascherato o manca. Le versioni pubbliche sono `plannerPlainDecimalCount` (`:186-189`)
e `plannerQuantityCount`.

| # | Sito (verificato) | Oggi | Cura |
|---|---|---|---|
| P1 | `planner/modeText.ts:28-30` (`brokers.stepUnits`) | `count: canonical === null ? 0 : Number(canonical)` | `plannerPlainDecimalCount(canonical ?? mode.step)` |
| P2 | `planner/steps/AssetsStep.svelte:125` (`assets.perUnits`) | `Number(price.quoteBaseQuantity)` | `plannerPlainDecimalCount(price.quoteBaseQuantity)` |
| P3 | `planner/steps/AssetsStep.svelte:245-247` (`assets.priceLine`) | `Number(asset.price.quoteBaseQuantity)` | idem |
| P4 | `planner/shared/ReviewCell.svelte:90-92` (`review.price`) | `Number(value.units) \|\| 0` | `plannerPlainDecimalCount(value.units)` |

**Altri casi.** Ho cercato fra i 74 messaggi `plural` del catalogo, con chiamanti ed espressioni
(`plural_sites.py`), e con un `grep` di `count|n|…: Number(|parseFloat|…`: **nessun altro caso**.
- Gli altri conteggi sono interi: lunghezze, contatori, giorni e anni da regex
  (`importReportSets.ts:247`, `assetSetLevels.ts:443`).
- Fuori tema ma da backlog: plurali scritti a mano senza ICU, per esempio «shares» dopo una quantità
  in `LotGanttChart.svelte:701-702`.

**Test** (test-author):
- `modeText.test.ts`, nuovo e puro: `modeIncrementText` con 1, 1.5, `1.00000000000000000001`, 0.001,
  passo non valido;
- un gate sui sorgenti: nessun `count: Number(` nei messaggi plurali del planner;
- facoltativo: un test di componente su `ReviewCell`.

Attenzione per chi scrive i test: per il §4, un testo compilato in EN e poi in FR nello stesso file
di test eredita le regole EN.

## 7. Le tre chiavi `tools.*` di D

Sono `tools.contractVersion`, `tools.implementationVersion` e `tools.open`: D le cita in
`plan-phase00PacP1FinalRemoval.prompt.md`, S8 «Fuori pista». Nessun riferimento nel sorgente, nel
backend o nei test (verificato anche con `git log -S`). Sono **morte**, nel lotto D (§11).

## 8. Il debito di Prettier in `DistributionDialog.svelte` (`:74-126`)

Solo segnalazione, per il backlog: non è i18n, e qui non posso verificarlo senza `node_modules`.

## 9. Superfici, dipendenze, conflitti

**Superfici di O:**

| Lotto | File |
|---|---|
| A, strumento | `scripts/i18n_usage.py`, `frontend/scripts/i18n-audit.py`, `backend/test_scripts/test_utilities/test_i18n_usage_gate.py` |
| B, plurali | `planner/modeText.ts`, `planner/steps/AssetsStep.svelte`, `planner/shared/ReviewCell.svelte`, nuovi test, registrazione in `scripts/test_runner/_frontend_utility.py` (**condiviso**) |
| C, ICU | 3 valori FR con `dev.py i18n update`, nuovo gate vitest, registrazione nel runner (**condiviso**) |
| D, rimozioni | solo i 4 cataloghi, con `dev.py i18n remove -f` (**condivisi**) |
| E, condensazioni (facoltative) | §3, C1-C5 |
| Documentazione | skill `devpy-i18n/SKILL.md`; `mkdocs_src/docs/developer/frontend/i18n.md` (docs-writer, solo EN: vi compaiono opzioni che lo strumento non ha, `--format table`, `--output report.xlsx`); facoltativa `developer/frontend/components/features/settings.md:61` (cita ancora `nextImport` e `replayReady`); `wiki-file` |

**Conflitti previsti:**
- **L**: integrato nel treno 7 (`bae2515bd`), impatto zero sulla classificazione. Il developer porta il
  ramo alla punta prima del codice, quindi nessun conflitto sui cataloghi. Le chiavi `gapFix.*` della
  mitigazione C stanno nel blocco `importWizard.reportSet`, ma in punti lontani da quelli che ha
  cambiato L.
- **A** (passo 24: `L3Benchmark.svelte`, `RiskLevelsPanel.svelte`, E2E `risk`): non tocco sorgenti
  risk. Con R3 `risk.*` diventa verificabile: segnalo le candidate, ma **non ne tolgo nessuna** finché
  A non è entrato; `risk.simulation.regimeTruncated` va dopo A.
- **N** (store, `LotsAnalysisPanel`, pagine dashboard e broker): N non aggiunge chiavi, ma potrebbe
  usare chiavi esistenti. Le morte `dashboard.*` (7) e `brokers.lots.*` (9) e la condensazione C5 vanno
  sulla base **dopo N**, ricontrollate. Le altre rimozioni toccano solo i cataloghi e nessun file di N.
- **D (PAC)**: lavoro chiuso con la riga 13 e R7. Il lotto B e le 107 + 2 rimozioni toccano il suo
  dominio: da confermare che non ci sia un worktree di D attivo.
- **Superfici condivise**: cataloghi (O scrive durante il lotto); `_frontend_utility.py` (il writer lo
  assegna il coordinatore); CHANGELOG (lo scrive il coordinatore, O propone le righe 🐛: plurale
  «1,5 unità» nel planner, plurale FR con 0 dopo un cambio di lingua).

## 10. Complessità e rischi

**Complessità media.** Quasi tutto il rischio sta nel non togliere chiavi vive.

| Rischio | Mitigazione |
|---|---|
| Togliere una chiave usata in modo dinamico | Si rilancia lo strumento corretto (lotto A) sulla punta, si confronta con l'Appendice A, si ricontrolla con `grep` chiave per chiave subito prima della rimozione. Le dubbie solo su decisione del developer. |
| Regole permissive → falsi «usati» | Test nelle due metà per ogni regola; R5 solo su famiglie strette |
| Riscrittura rumorosa dei cataloghi | Cataloghi già canonici; `dev.py i18n remove` uno alla volta; controllo di `git diff --stat` e della parità delle chiavi nelle 4 lingue |
| Il test di caratterizzazione dipende dagli interni della libreria | È voluto: è un fermo che segnala quando la libreria cambia |
| Test frontend senza `node_modules` | `npm ci` solo con il permesso del coordinatore |
| Circa 170 rimozioni in un colpo | Precedente di D (285 chiavi): uno script, uno stop al primo errore, «✓ removed» in tutte e 4 le lingue, verifica della parità |

## 11. Passi (dopo l'autorizzazione del developer, sulla punta del bersaglio)

- **S0** ✅ 2026-10-07 — Copio questo piano nel journal; HEAD alla punta; rilancio `i18n audit` e lo confronto con §1-§2.
  > **Note implementazione**:
  > - il developer ha portato il ramo a `bae2515bd` (treno 7, lotto di L); il piano è entrato nel journal;
  > - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n audit --duplicates`
  >   (`/tmp/libreFolio_o_s0_audit.log`), poi il confronto con l'analisi su `9f06df702`:
  >   - stesse **250** morte e stesse **86** non verificate, chiave per chiave;
  >   - 4356 chiavi, 108 prefissi;
  >   - 426 gruppi di doppioni, con la stessa ripartizione;
  >   - esatte 4386 invece di 4385: +1 dal lotto di L.
  > - Il lotto di L non tocca nessuna delle 354 chiavi classificate. La classificazione resta valida.
  > - `npm ci` eseguito una volta, dal lock (`/tmp/libreFolio_o_npm_ci.log`). npm 11 non ha eseguito gli
  >   script d'installazione di 5 pacchetti (esbuild, fsevents, es5-ext); vitest sarà verificato al
  >   primo uso.
  > - Con `node_modules` presente ho confermato le righe di svelte-i18n 4.0.1: `monadicMemoize` a
  >   `runtime.js:383-392`, con la chiave di cache a `:386`, e `getMessageFormatter` a `:496`.
  >
  > **⚠️ Fuori pista**: nel §5.2 ho scritto che R5 avrebbe fatto emergere `routeCapMissing` e
  > `sections.assets`. È sbagliato: la prima la assolve un prefisso legacy, la seconda il vocabolario
  > backend. Le due chiavi si tolgono a mano (decisione 1), dopo una nuova verifica con grep.
- **S1** ✅ 2026-10-07 — Test rossi per lo strumento (test-author).
  > **Note implementazione**: il test-author ha aggiunto 77 casi (47 funzioni in 9 classi, una per
  > regola) in fondo a `backend/test_scripts/test_utilities/test_i18n_usage_gate.py`. I test sono PURE,
  > su sorgenti sintetici, e provano ogni regola in entrambe le metà. Gate:
  > `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6160 --data-dir /tmp/librefolio-r2-o utils gate-i18n-usage`
  > → **24 vecchi verdi, 77 nuovi rossi** (22 `AttributeError` sui nomi nuovi, 55 asserzioni;
  > `/tmp/libreFolio_o_s1_gate.log`). Sono 9 classi: R1-R7, più il backend di R2, più i template
  > annidati. Contratti fissati dai test:
  > - una famiglia è stretta quando ha almeno due punti;
  > - R5 vale solo nel file che costruisce la famiglia, R6 vale fra file diversi;
  > - in R3 un `{prefix: 'warnings'}` non espande;
  > - l'origine di una famiglia backend è `<file>:<riga>`;
  > - `phantom_families` deve accettare un iterabile che si legge una volta sola.
- **S2** ✅ 2026-10-07 — Strumento, R1-R7 più §5.3 (template annidati); gate verde e nuovi numeri dell'audit.
  > **Note implementazione**:
  > - `scripts/i18n_usage.py`:
  >   - `is_test_source()` e `iter_source_files()` (R1);
  >   - qualunque letterale fra apici o backtick vale come chiave, nel frontend e in `backend/app`
  >     (R2, `harvest_backend_keys`);
  >   - `_union_members` accetta un solo letterale se tipizza un parametro (R3);
  >   - `harvest_backend_families` per le f-string, e un vocabolario con camelCase, `UPPER_SNAKE`,
  >     Title Case senza spazi e codici puntati (R4);
  >   - `family_vocab`: parole del file, `head.parola`, valori di una proprietà o di una mappa indicizzata (R5);
  >   - `suffixes` per `` `${expr}Full` `` (R6);
  >   - `phantom_families` (R7);
  >   - parser dei template con backtick annidati (`_template_end`, `_iter_key_templates`) (§5.3).
  > - `frontend/scripts/i18n-audit.py`: la scansione legacy usa `iter_source_files`; il report usa
  >   R2, R4 e R7, e ha la sezione 👻 «famiglie backend senza chiavi». La sezione mostra solo
  >   le famiglie il cui namespace esiste nel catalogo.
  > - **Prefissi legacy declassati** (§5.3): un prefisso troncato alla vecchia maniera tiene una chiave
  >   fuori dalle morte, ma non la prova più usata (→ non verificata). Misurato sull'albero di oggi, ogni
  >   chiave che assolveva ha già un'altra prova: il declassamento non condanna nulla e smette di
  >   nascondere le morte.
  > - Gate: **101 passati** (`/tmp/libreFolio_o_s2_gate2.log`); `ruff check` sui 3 file Python:
  >   - `i18n_usage.py` e il file dei test puliti;
  >   - `i18n-audit.py` con 35 avvisi, gli stessi della base.
  >   `black --check` vorrebbe riformattare anche le versioni della base: il progetto non lo impone.
  > - **Audit dopo la correzione** (`/tmp/libreFolio_o_s2_audit2.log`): **180 morte** (erano 250),
  >   **87 non verificate**, 1 famiglia fantasma (`tools.allocation.constraints.` ← `evaluator.py:968`).
  >   Confronto con l'Appendice A:
  >   - nessuna delle 179 dinamiche è data per morta: erano 118;
  >   - 161 morte e le 8 dubbie restano morte;
  >   - 6 morte diventano «non verificate», per prudenza: sono sotto una famiglia vera e solo una
  >     decisione umana le può togliere: `importWizard.{parseError,parsing}`,
  >     `planner.result.kpi.{fundingReachable,shortfallParts,shortfallPartsNoRounding}`,
  >     `planner.review.kind.exposures`;
  >   - 11 nuove morte, tutte attese:
  >     - 7 dalle condensazioni C1-C4, già cambiate nei chiamanti;
  >     - 2 da `WeightBars.svelte`, tolto;
  >     - `risk.simulation.regimeTruncated`;
  >     - `risk.params.process`, nuova, nascosta dalla radice `risk`.
  >
  > **⚠️ Fuori pista**:
  > - **2 errori della mia classificazione**, trovati dallo strumento corretto.
  >   `aiExport.additionalData.reason.{fifoDetail,performanceContext}` erano fra le dinamiche, ma il
  >   backend non le emette più dal commit `c9f840680` (2026-08-05, «remove legacy runtime»):
  >   `ai_export/analyses/catalog.py` usa solo `deeperTechnical`, `positionContext` e
  >   `directExposure`. Sono morte e vanno in S7a.
  > - **`risk.params.process`** è una morta nuova nel namespace di A: va con
  >   `risk.simulation.regimeTruncated` in S7c, dopo A.
  > - **`planner.result.sections.assets`** resta «usata» per lo strumento: la parola «assets» è nel
  >   vocabolario del backend, che vale per ogni famiglia. È un limite noto; la chiave si toglie a mano
  >   (decisione 1), come `planner.problems.routeCapMissing`, che lo strumento dà per non verificata.
  > - Per il test KPI, in `(kind: string)` il nome del parametro non è una chiave d'oggetto: R5 legge
  >   solo le chiavi con un valore letterale (`{primal: '…'}`).
- **S3** ✅ 2026-10-07 — Test rossi per i plurali (test-author), registrazione.
  > **Note implementazione**: il test-author ha creato
  > `planner/modeText.test.ts` (13 test) e `planner/pluralCountSites.test.ts` (19: il gate sui sorgenti e
  > il predicato provato nelle due metà). Li ha registrati in `core-unit`: 3 righe aggiunte in
  > `scripts/test_runner/_frontend_utility.py:127-129`, insieme al file di S5. Vitest col binario bloccato
  > (`/tmp/libreFolio_o_s3s5_vitest.log`) → **6 rossi su 42**:
  > - 4 di `modeText`: `0.001` e `1.00000000000000000001`, con privacy spenta e accesa;
  > - il gate sui sorgenti, con i 4 siti `modeText.ts:30`, `ReviewCell.svelte:92`, `AssetsStep.svelte:125`
  >   e `:247`;
  > - il gate ICU (S5).
  >
  > Il test-author ha aggiunto il caso con privacy accesa, che separa `plannerPlainDecimalCount` da
  > `plannerQuantityCount`. Ha anche allargato il gate sorgente ai rami dei ternari e a `??`, `||` e `&&`.
- **S4** ✅ 2026-10-07 — Plurali, P1-P4.
  > **Note implementazione**: `count: plannerPlainDecimalCount(…)` in `modeText.ts:30`, sullo stesso
  > `canonical ?? mode.step` della cifra mostrata; poi `AssetsStep.svelte:125` e `:247` e
  > `ReviewCell.svelte:92`. Gli import vengono da `format.ts`. Un passo non valido conta NaN, cioè
  > `other`, e non più 0: lo 0 in francese diventa singolare.
- **S5** ✅ 2026-10-07 — Gate ICU e caratterizzazione (test-author), registrazione.
  > **Note implementazione**: `frontend/src/lib/i18n/catalogIcuLocale.test.ts` (10 test). Analizza
  > ogni messaggio col parser di svelte-i18n e raggruppa i messaggi per testo fra chiavi diverse,
  > perché la cache ignora la chiave. Un `#` fuori da un plurale non scatta. Il latch fissa la lingua
  > corrente di svelte-i18n intorno alle due chiamate e la ripristina in `afterEach`. Era rosso sui 3
  > testi EN = FR, con il latch verde.
- **S6** ✅ 2026-10-07 — 3 valori FR (M1).
  > **Note implementazione**: `dev.py i18n update <chiave> --fr …` (`/tmp/libreFolio_o_s6_fr.log`), per
  > `importWizard.reportSet.gapFix.{positions,corrections}` e `tools.pacAllocator.planner.review.sources`.
  > Il ramo `many` è **uguale a `other`**: `{n, plural, one {# position} many {# positions} other {# positions}}`.
  > `fr.json` cambia di 3 righe, EN non cambia.
  >
  > **⚠️ Fuori pista**: il §4 proponeva `many {# de positions}`. Con le cifre scritte per intero, dal
  > `#`, «1 000 000 de positions» è un francese incerto. Il ramo uguale a `other` separa comunque il
  > testo da quello inglese, quindi chiude il problema della cache, e non cambia nessuna resa.
- **S7a** ✅ 2026-10-07 — Rimozioni, primo sottolotto.
  > **Note implementazione**: ho ricontrollato le chiavi prima della rimozione, con grep su
  > `frontend/src`, `frontend/e2e`, `frontend/scripts`, `backend`, `scripts`, `mkdocs_src/docs`, `dev.py`
  > e `.github` (`/tmp/libreFolio_o_s7a_refs.log`). Sono rimasti solo riferimenti documentali: la skill
  > (aggiornata in S9) e un commento del test del gate. Le chiavi tolte con lo script
  > `/tmp/libreFolio_o_remove_keys.sh` (`dev.py i18n remove <chiave> -f`, una per chiave, stop al primo
  > errore, «✓ removed» ×4 obbligatorio) sono **172 su 172**, in 3 min 23 s
  > (`/tmp/libreFolio_o_s7a_remove.log`; elenco in `files/s7a_s8_keys.txt` della sessione O):
  > - **165** di S7a:
  >   - 151 morte dell'Appendice A, senza le 16 `dashboard.*` e `brokers.lots.*` che vanno dopo N;
  >   - 8 dubbie;
  >   - `planner.problems.routeCapMissing` e `planner.result.sections.assets`;
  >   - `planner.result.weights.{finalShort,targetShort}`;
  >   - `aiExport.additionalData.reason.{fifoDetail,performanceContext}` (S2, Fuori pista);
  > - le **7** vecchie chiavi di C1-C4 (S8).
  >
  > Verifica: 4186 chiavi per lingua, stesso insieme nelle 4, forma canonica intatta. Rispetto a HEAD:
  > - mancano esattamente le 172;
  > - ci sono in più esattamente le 2 di C4;
  > - cambiano solo i 3 testi FR di S6.
  >
  > `git diff --stat`: 39 righe aggiunte e 831 tolte, sui 4 file.
- **S7b** ✅ 2026-10-07 (dopo N) — 9 `brokers.lots.*` e 7 `dashboard.*`, ricontrollate sulla base dopo N;
  insieme a C5 e alla voce `dashboard.holdings`/`dashboard.positions` della skill.
  > **Note implementazione**: base `d07412899` (A13 e N integrati), fast-forward fatto dal developer
  > alle 13:25. Prima di scrivere, l'audit sulla punta (copia in `/tmp/libreFolio_o_tip`) ha dato le
  > stesse 18 morte e le stesse 78 non verificate di `a8bac445d`: A13 e N non hanno cambiato chiavi né
  > riferimenti. Le 16 chiavi sono tolte nel lotto unico qui sotto (S7-bis).
- **S7c** ✅ 2026-10-07 (dopo A) — `risk.simulation.regimeTruncated` e `risk.params.process`.
  > **Note implementazione**: sono 2 e non 3, come il kickoff contava. Le 19 `risk.*` non verificate
  > sono tutte vive: i loro membri sono scritti nei moduli importati (`correlationHelpers.ts:59`,
  > `levelHelpers.ts:337`, `simulationModes.ts:37-54`, `simulationProvenance.ts:40`). R8 le prova
  > (S12).
- **S7a-bis** ✅ 2026-10-07 — `tools.pacAllocator.planner.problems.{asOfMissing,priceDateAfterReference,priceDateMissing}`.
  > **Note implementazione**: le ha trovate il prototipo di R8. Non ci sono produttori nel frontend né
  > nel backend, e sono uscite dal codice con `6f29ec1cf`. Approvate dal developer (13:25).
- **S8b** ✅ 2026-10-07 (dopo N) — Condensazione C5.
  > **Note implementazione**: 6 gruppi identici nelle 4 lingue. Chiamanti:
  > - `LotCustodyModal.svelte:298,302,314,340,345,350`: da `brokers.lots.modal.X` a `brokers.lots.X`;
  > - `LotGanttChart.svelte:721` e `LotComparisonChart.svelte:447`: da `brokers.lots.tooltip.totalPnl` a
  >   `brokers.lots.totalPnl`.
  >
  > Nessuno di questi è un file di N, che ha toccato solo `LotsAnalysisPanel.svelte`.
- **S11** ✅ 2026-10-07 — `planner/shared/AgeLabel.svelte` tolto, con le sue 5 chiavi
  `tools.pacAllocator.planner.age.{manual,sameDay,daysBefore,after,unknown}`.
  > **Note implementazione**: lo ha trovato il prototipo di R9, perché nessuna route né hook lo
  > raggiunge. Nessun riferimento nei sorgenti, nei test, negli E2E, nelle docs, negli script o nella
  > wiki. È lo stesso trattamento di `WeightBars.svelte`. Decisione del developer: «Toglierlo adesso,
  > con le sue 5 chiavi». Restano morti, senza chiavi, `onboardingTourSurfaces.svelte.ts` ed
  > `EditBuffer.ts`, che importa solo il suo test: il coordinator li mette nel backlog per knip, e io
  > non li tocco.
- **S7-bis** ✅ 2026-10-07 — rimozione unica delle 33 chiavi: S7b 16, C5 7, S7c 2, S7a-bis 3, S11 5.
  > **Note implementazione**: grep di conferma su tutto il repo. Restano 2 riferimenti documentali:
  > - `dashboard.holdings` nella skill, aggiornata in S13;
  > - `risk.simulation.regimeTruncated` in un caso sintetico del gate, che non legge il catalogo.
  >
  > `/tmp/libreFolio_o_remove_keys.sh` ha tolto **33 chiavi su 33**, ognuna dalle 4 lingue, in 43 s
  > (`/tmp/libreFolio_o_r2_remove.log`). Verifica: **4153** chiavi per lingua, stesso insieme nelle 4,
  > forma canonica. Mancano esattamente le 33, niente aggiunto né cambiato; `git diff --stat`: +4/−144.
- **S8** ✅ 2026-10-07 — Condensazioni C1-C4.
  > **Note implementazione**:
  > - chiamanti: `FilePreviewModal.svelte:677,683` usano `uploads.zoomOut` e `uploads.zoomIn`;
  >   `AssetPickerModal.svelte:200` usa `uploads.fileSize`; `assets/[id]/+page.svelte:3292` e
  >   `fx/[pair]/+page.svelte:1553` usano `dataEditor.editorTip{Mobile,Desktop}`;
  > - `dev.py i18n add dataEditor.editorTip{Desktop,Mobile}` con i valori di `assetDetail`, verificati
  >   identici a `fxDetail` nelle 4 lingue (`/tmp/libreFolio_o_s8_add.log`);
  > - le 7 chiavi vecchie sono state tolte in S7a;
  > - `WeightBars.svelte` cancellato (decisione 6): nessun import, nessun test, nessuna pagina.
- **S9** ✅ 2026-10-07 — Documentazione.
  > **Note implementazione**:
  > - skill `devpy-i18n`:
  >   - conteggio;
  >   - namespace protetti: tolto `chartSettings.signals.*`, aggiunti `providerErrors.*` e
  >     `aiExport.additionalData.reason.*`;
  >   - titoli dei passi di `importWizard`;
  >   - nuova sezione «How the Audit Decides "Used"»;
  >   - regole 5 (ICU) e 6 (conteggio dalle cifre);
  >   - nomi lunghi dei segnali (`Full`) al posto delle abbreviazioni (`Abbr`);
  >   - `common.{seeAll,recentTransactions}` tolte;
  >   - condensazioni della Release 2.
  > - Docs-writer, solo EN, su `developer/frontend/i18n.md`: opzioni vere dell'audit, verdetti e prove,
  >   nota ⚠️ sulla cache ICU, `values:` negli esempi. `mkdocs build` rc 0 con 0 avvisi; `check-links`
  >   rosso solo per il D28 accettato (`#rolling-return` in it/fr/es)
  >   (`/tmp/libreFolio_o_docs_build.log`, `/tmp/libreFolio_o_docs_links.log`).
  > - Wiki: `problems/i18n-audit-false-dead-and-false-used.md` e
  >   `problems/svelte-i18n-formatter-cache-ignores-locale.md`, con 2 righe in `index.md` e una voce in
  >   `log.md`. `check_source_paths.py`: 0 percorsi mancanti nelle due pagine (63 già mancanti altrove).
  >   graphify `--update` rinviato: `graph.json` non c'è nel worktree.
- **S10** ✅ 2026-10-07 — Gate e checkpoint.
  > **Note implementazione**: un comando per volta sulla 6160 con `/tmp/librefolio-r2-o`.
  >
  > | Comando | Esito | Log |
  > |---|---|---|
  > | `test … utils gate-i18n-usage` | 101 passati | `/tmp/libreFolio_o_s2_gate2.log` |
  > | `api sync` | rc 0; hash dei contratti `f636854e…e33a`, uguale a D; solo file ignorati | `/tmp/libreFolio_o_api_sync.log` |
  > | `test … front-utility core-unit` | 115 file, 3400 test passati (compresi i 3 nuovi) | `/tmp/libreFolio_o_s10_core_unit2.log` |
  > | `test … front-utility component-unit` | 109 file, 2825 passati | `/tmp/libreFolio_o_s10_component_unit.log` |
  > | `test … front-utility onboarding-component-unit` | 14 file, 408 passati | `/tmp/libreFolio_o_s10_onb_unit.log` |
  > | `test … check-orphans` | verde: 326 unitari frontend, 98 E2E, 237 backend, tutti registrati e raggiungibili | `/tmp/libreFolio_o_s10_orphans.log` |
  > | `front check` | svelte-check 0 errori, 0 avvisi | `/tmp/libreFolio_o_s10_front_check.log` |
  > | `lint` | «All checks passed!» | `/tmp/libreFolio_o_s10_lint.log` |
  > | `i18n audit --duplicates` | 4186 chiavi; **18 morte**, tutte rinviate (9 `brokers.lots.*` e 7 `dashboard.*` dopo N, 2 `risk.*` dopo A); 78 non verificate; 1 fantasma; 395 gruppi di doppioni (erano 426); 0 chiavi backend mancanti | `/tmp/libreFolio_o_s10_audit.log` |
  > | `git diff --check` | pulito | — |
  >
  > **⚠️ Fuori pista**:
  > - **Il primo `core-unit` era rosso per infrastruttura**: 25 file e 9 test, tutti per `Cannot find
  >   module '$lib/api/generated'`, cioè il client generato e ignorato che manca in un worktree fresco
  >   (wiki `problems/front-check-does-not-check-what-you-think`). L'ha risolto `api sync`, che scrive
  >   solo file ignorati (verificato con `git status` prima e dopo). Nessun test di prodotto era rosso.
  > - **Prettier**: `planner/steps/AssetsStep.svelte` ha 38 righe di debito già alla base, gli stessi
  >   hunk, nessuno sulle righe 125 e 247 toccate qui. Va nel backlog, come `DistributionDialog.svelte`.
  >   Gli altri file frontend toccati e i 3 test nuovi passano Prettier.
  > - **black** non è imposto dal progetto (`dev.py lint` usa solo ruff); i file Python toccati andavano
  >   già riformattati alla base.
- **S12** ✅ 2026-10-07 — Strumento: R8-R12, il miglioramento contro i falsi positivi chiesto dal
  developer, con i test rossi prima del codice.
  > **Note implementazione**:
  > - **test-author**: 94 casi nuovi in 5 classi in coda a `test_i18n_usage_gate.py`, solo aggiunte
  >   (+894/−0):
  >   - `TestOneImportHop` 40, `TestUnreferencedSources` 24, `TestGeneratedClients` 11,
  >     `TestCodesInOtherSpellings` 9, `TestSeveralRuntimeSegments` 10;
  >   - prima del codice: 94 rossi e 101 verdi. Le cause: 49 nomi mancanti, 1 `TypeError` su `skip=`,
  >     44 asserzioni sui verdetti di oggi; nessuna dal codice di test (`/tmp/libreFolio_o_r8_gate.log`).
  > - **Contratti fissati in più dal test-author**:
  >   - un client generato non fa da testimone R8;
  >   - un test non raggiunge niente;
  >   - `resolve_import` rende i percorsi come li dà la passata sui file;
  >   - in R12 la coda letterale del segmento fa parte della forma, e una posizione risolta accetta solo i
  >     suoi valori.
  > - **Motore** (`scripts/i18n_usage.py`):
  >   - R8: `resolve_import()`; `_read_sources()` legge ogni file una volta e collega gli import diretti
  >     (cache per specifier e cartella; confronto su percorsi normalizzati); `narrow_rests()` aggiunge
  >     le parole dei moduli importati, a un solo passo;
  >   - R9: `_is_entry()`, `unreferenced_sources()`, `collect_from_source(…, skip=…)`; un file saltato
  >     non viene letto, quindi non fa da testimone nemmeno a un import di distanza;
  >   - R10: `is_generated_source()` in `iter_source_files()`;
  >   - R11: `_IDENT_LITERAL` accetta la cifra iniziale ma vuole almeno una lettera; `_is_vocabulary()`
  >     confronta anche maiuscole e minuscole;
  >   - R12: `Usage.shapes` (deduplicato per pattern e testimoni), `_record_shape()`, `_shape_verdict()`
  >     in `classify()`.
  > - **CLI** (`frontend/scripts/i18n-audit.py`):
  >   - `find_used_keys_in_sources(skip=…)`;
  >   - helper `_BackendEvidence`, `_classify_keys()`, `_kept_alive_by_unreferenced()`,
  >     `_kept_alive_section()`;
  >   - nuova sezione informativa «📦 Kept Alive Only by Unreferenced Sources»;
  >   - `_keys_by_section()` sostituisce i due cicli copiati, con output identico (verificato);
  >   - nota sulle prove aggiornata.
  > - **Esiti**:
  >   - gate **195/195** (`/tmp/libreFolio_o_r2_gate_final.log`);
  >   - audit sulla punta attuale: **0 morte, 4 non verificate** (erano 78), 1 fantasma, 📦 vuota;
  >   - sulla copia di `d07412899` la sezione 📦 elenca le 5 `planner.age.*` (→ dead) e i 3 orfani
  >     (`/tmp/libreFolio_o_r9_tip_probe.log`);
  >   - sull'albero reale R9 trova 2 orfani in 0,37 s, e R10 salta 3 client generati;
  >   - l'audit completo con i doppioni dura 12,8 s;
  >   - ruff: motore 0, CLI da 35 a 34 (C901 di `generate_unused_keys_report` era 15, ora sotto 10);
  >     black: stessi hunk della base (11 e 3), nessuno su righe nuove.
  >
  > **⚠️ Fuori pista**:
  > - **Differenze dal prototipo**:
  >   - gli hook valgono solo alla radice e con il nome esatto: `lib/stores/hooks.svelte.ts` non è un
  >     entry point, come vuole il contratto;
  >   - le route valgono solo sotto `routes/`, layout reset (`+page@.svelte`) compresi;
  >   - `_record_middle_members` è tolto: le forme R12 lo coprono, con lo slot di un solo segmento;
  >   - un numero senza lettere non è un codice.
  >
  >   Il risultato sulla punta coincide con la misura del prototipo, meno le 33 chiavi tolte.
  > - **Le 4 non verificate, verificate a mano**:
  >   - `chartSettings.params.{amplitude,histogramScale}`: vive, il membro sta a 2 passi d'import;
  >   - `transactions.fields.cash_code`: viva, dal percorso di validazione `cash.code`
  >     (`resolveValidationMessage.ts:123`); `Currency.code` è un campo Pydantic, non un letterale;
  >   - `onboarding.settings.groups.contextual`: **morta in fatto**. Il gruppo `contextual` di
  >     `OnboardingReplaySection.svelte` è stato sostituito in `580bd504f` (14/09). Decisione del
  >     developer (14:20): «Sì, toglierla» → S7-ter.
- **S7-ter** ✅ 2026-10-07 — `onboarding.settings.groups.contextual` tolta.
  > **Note implementazione**:
  > - l'unico lettore è `OnboardingReplaySection.svelte:208`, i cui gruppi sono `setup`, `core`,
  >   `transactions`, `broker`, `fx` e `asset`;
  > - non c'è nessun altro costruttore, test, E2E o pagina di documentazione che la usi (le «Contextual
  >   guides» delle pagine utente sono il concetto, non questa etichetta);
  > - rimossa con `/tmp/libreFolio_o_remove_keys.sh`: 4 «✓ removed» (`/tmp/libreFolio_o_r2b_remove.log`).
  >
  > Verifica rispetto a HEAD (`/tmp/libreFolio_o_verify_catalogs.py`): **4152** chiavi per lingua, mancano
  > esattamente le 34 attese, nessuna aggiunta né cambiata, forma canonica, stesso insieme nelle 4;
  > `git diff --stat`: +4/−148. Audit: **0 morte, 3 non verificate** (tutte vive), 1 fantasma, 📦 vuota
  > (`/tmp/libreFolio_o_r2b_audit.log`).
- **S13** ✅ 2026-10-07 — Documentazione del secondo turno.
  > **Note implementazione**:
  > - skill `devpy-i18n`:
  >   - conteggio 4 356 → 4 152, con 192 morte tolte;
  >   - tolta la voce `dashboard.holdings` dagli Accepted Duplicates, e aggiunta C5 alle condensazioni;
  >   - nelle prove: client generati esclusi, un passo d'import, forme, codici in ogni grafia o con la
  >     cifra iniziale, sezione 📦;
  >   - nel limite noto, il membro a due passi d'import.
  > - docs-writer, solo EN, su `developer/frontend/i18n.md`, +34/−3:
  >   - stesse prove della skill, e la sezione 📦 con il modo in cui si decide «unreferenced»;
  >   - corretta una frase vecchia: le parole quotate valgono solo per le famiglie strette
  >     (`_family_rests()`);
  >   - `mkdocs build` strict: rc 0, nessun avviso (`/tmp/libreFolio_o_docs_build.log`);
  >   - `check-links` rosso solo per il D28 accettato (`#rolling-return` in it/fr/es) e i 3 anchor 🟡 noti
  >     (`/tmp/libreFolio_o_docs_checklinks.log`);
  >   - la pagina non ha gemelli tradotti.
  > - wiki:
  >   - `problems/i18n-audit-false-dead-and-false-used.md`: nuovo «Second pass», con la lezione sulle
  >     non verificate da controllare una per una;
  >   - riga in `index.md`, voce in `log.md`;
  >   - `check_source_paths.py`: 0 percorsi mancanti nelle mie pagine (63 già mancanti altrove);
  >   - graphify `--update` ancora rinviato, perché `graph.json` manca nel worktree.
- **S14** ✅ 2026-10-07 — Gate e checkpoint del secondo turno.
  > **Note implementazione**: un comando per volta sulla 6160 con `/tmp/librefolio-r2-o`, base `d07412899`.
  >
  > | Comando | Esito | Log |
  > |---|---|---|
  > | `test … utils gate-i18n-usage` | 195 passati | `/tmp/libreFolio_o_r2b_gate.log` |
  > | `i18n audit --duplicates` | 4152 chiavi; **0 morte**; 3 non verificate, vive; 1 fantasma; 📦 vuota; 381 gruppi di doppioni; 0 chiavi backend mancanti | `/tmp/libreFolio_o_r2b_audit.log` |
  > | `test … front-utility core-unit` | 115 file, 3400 passati | `/tmp/libreFolio_o_r2b_core_unit.log` |
  > | `test … front-utility component-unit` | 109 file, 2829 passati | `/tmp/libreFolio_o_r2_comp_unit.log` |
  > | `test … front-utility onboarding-component-unit` | 14 file, 408 passati | `/tmp/libreFolio_o_r2b_onb_unit.log` |
  > | `test … check-orphans` | verde: 328 unitari frontend, 99 E2E, 237 backend | `/tmp/libreFolio_o_r2_orphans.log` |
  > | `front check` | svelte-check 0 errori, 0 avvisi | `/tmp/libreFolio_o_r2_front_check.log` |
  > | `lint` | «All checks passed!» | `/tmp/libreFolio_o_r2_lint.log` |
  > | Prettier `--check` sui 3 file dei lotti | pulito | — |
  > | `mkdocs build` / `check-links` | rc 0 / rosso solo D28 | vedi S13 |
  > | `git diff --check`; `lsof` 6160 e 6170 | pulito; porte libere | — |
  >
  > **⚠️ Fuori pista**:
  > - `component-unit`, `front check` e `lint` sono girati prima di S7-ter. S7-ter tocca solo i 4 JSON,
  >   su una chiave senza lettori; dopo S7-ter sono stati ripetuti audit, gate, `core-unit` (che contiene
  >   il gate dei testi delle guide) e `onboarding-component-unit`.
  > - Non sono girati gli E2E: C5 cambia solo chiavi con valori identici nelle 4 lingue, e la resa
  >   non cambia.
- **S15** ✅ 2026-10-07 — Lotto a parte, non i18n: `GET /api/v1/system/plugin-diagnostics` richiede il
  login. Trovato da Q, verificato dal coordinatore. Decisione del developer: «Sì, correggilo con O nella
  1.2». Base `1e2b08804`.
  > **Note implementazione** (verifica prima del codice):
  > - `system.py:192-202`: `get_plugin_diagnostics()` non ha `Depends(get_current_user)`, che invece c'è
  >   su `container-image-status` (`:205-211`). Restituisce il testo delle eccezioni d'import dei plugin,
  >   quindi può esporre percorsi interni. C'è dalla 1.1.0 (`81853ae81`).
  > - L'unico chiamante è `AboutTab.svelte:133`, nelle impostazioni, da utente loggato, con
  >   `.catch(() => [])`; anche l'E2E `settings.spec.ts:556` è loggato.
  > - `developer/architecture/security.md:84-95` già non elenca l'endpoint fra i pubblici: è il codice a
  >   non rispettare la doc, che non va toccata.
  > - `get_current_user` legge il cookie da `Request`, quindi l'OpenAPI non cambia.
  > - Niente frontend né i18n; il CHANGELOG lo scrive il coordinatore.
  >
  > **Esecuzione** (✅ 2026-10-07):
  > - **test-author**: classe `TestPluginDiagnosticsRequiresSession` in `test_system_api.py` (+140/−1),
  >   HTTP vero sul backend della corsia:
  >   - senza cookie → 401 «Not authenticated»;
  >   - cookie falso (`SESSION_COOKIE_NAME`) → 401 «Session expired or invalid»;
  >   - utente proprio loggato → 200, `PluginDiagnosticsResponse` valida, chiavi esatte
  >     `system`/`filename`/`error`, senza vincoli di lunghezza;
  >   - barriera strutturale: `get_current_user` fra le dipendenze della route, con il controllo positivo
  >     su `container-image-status`.
  >
  >   Prima del fix: 3 rossi (200 invece di 401, due volte; nessuna dipendenza), 25 verdi compresa la
  >   barriera del login (`/tmp/libreFolio_o_sec_red.log`).
  > - **fix**: `_current_user: Annotated[User, Depends(get_current_user)]` su `get_plugin_diagnostics`,
  >   più una riga di docstring.
  > - **gate**:
  >   - `test … api system`: 28 passati, ripetuto sull'albero finale (`/tmp/libreFolio_o_sec_green2.log`);
  >   - `lint` verde; black pulito su entrambi i file, prima e dopo; `diff --check` pulito;
  >   - porte 6160 e 6170 libere;
  >   - OpenAPI: cambia solo `description`, cioè la docstring; `operationId`, parametri e risposte sono
  >     identici, quindi il client è compatibile (`/tmp/libreFolio_o_sec_openapi.log`).
  >
  > **⚠️ Fuori pista** (segnalati, non corretti):
  > - l'azione singola `api system` non popola il DB della corsia, quindi il primo account registrato è
  >   diventato l'admin d'avvio ed è rimasto nel DB di `/tmp/librefolio-r2-o`;
  > - `_TestingServerManager.ensure_started()`, documentato in `backend-testing.instructions.md:109`,
  >   nella skill `testing-backend` e in `knowledge_base/06_testing_backend.md:138`, non esiste: c'è
  >   `start_server()`;
  > - la descrizione di `api system` nel runner («parse_pipfile, deps») è vecchia;
  > - il runner ha creato `frontend/build/`, che è ignorato.
- **S16** ⏳ 2026-10-07 — Triage del rosso di coverage `auth.spec.ts:312` («3a: completing welcome…»),
  chiesto dal coordinatore dopo il fix di sicurezza.
  > **Prove**:
  > - run completa 13:05-15:58 su `d07412899`, 2 worker, carico 30-50: a `:338` per 3 s
  >   `<html lang="en" data-i18n-ready="true">` ×10 (`/tmp/libreFolio_triage_20261007/logs/front-utility__e2e-desktop.log:198-226`).
  > - Ipotesi della skill `test-triage`, nell'ordine:
  >   - forma: no, non c'è niente di posizionale e `it` non c'è da nessuna parte (la POST porta `en`);
  >   - orologio: no, l'attesa è sullo stato giusto e lo stato finale è `en`, quindi alzare il timeout non
  >     servirebbe;
  >   - stato condiviso: no, l'utente è usa e getta;
  >   - cascata: no, è l'unico rosso di `auth`.
  >
  > **Meccanismo**:
  > 1. svelte-i18n 4.0.1, con un loader in coda, rende vero `isLoading` dopo `loadingDelay` = 200 ms e
  >    cambia `locale` solo a caricamento finito (`runtime.js:319-338`);
  > 2. `routes/+layout.svelte:43-48`, e allo stesso modo `(app)/+layout.svelte`, smontano l'intera app
  >    finché `$i18nLoading` è vero;
  > 3. al rimontaggio `(app)/+layout.svelte:45` (`initI18n()`) e `:61` (`currentLanguage.init()`)
  >    rileggono `localStorage['librefolio-locale']`, che l'anteprima del Welcome
  >    (`welcome/+page.svelte:104-110`, solo `locale.set`) non scrive mai, quindi la lingua torna `en`;
  > 4. la pagina Welcome si rimonta e riidrata la bozza da `$userSettings` (`:55-75`), cioè `en`, e il
  >    completamento invia `en`.
  >
  > Il commento di `+layout.svelte:32-35` («`locale` flips the moment the user picks») è falso con
  > svelte-i18n 4.
  >
  > **Riproduzione**, in corsia 6160, con uno spec temporaneo non tracciato e poi tolto (copia in
  > `/tmp/libreFolio_o_triage_probe.spec.ts`):
  > - con il chunk italiano instradato, a 0 ms e a 1500 ms, la traccia è `en/true > en/false > it/false >
  >   en/true`; il form del Welcome è un nodo nuovo, `lang` è `en`, la POST porta `language: en`
  >   (`/tmp/libreFolio_o_triage_run3.log`);
  > - controllo: il vero 3a senza route passa in 3,0 s (`/tmp/libreFolio_o_triage_3a.log`);
  > - il chunk italiano pesa 254 KB nel build di debug.
  >
  > **Verdetto: difetto.** Il test è giusto.
  > - Impatto per l'utente: su un'istanza remota, chi sceglie la lingua nel Welcome vede l'app sparire e
  >   tornare in inglese, e la scelta si perde.
  > - Ogni cambio di lingua successivo che superi i 200 ms (header, Preferenze) rimonta l'app e perde lo
  >   stato della pagina, anche se la lingua resta, perché `currentLanguage.set` la salva prima.
  > - Correzione proposta, in attesa dell'autorizzazione: i layout mostrano il segnaposto solo fino al
  >   primo dizionario pronto, poi l'app resta montata; `data-i18n-ready` continua a segnalare il caricamento.
  >   Il test-author scrive un E2E di regressione, rosso prima del fix.
  >
  > Decisione del developer (16:29): «Approva tutte e tre le correzioni», cioè segnaposto solo per il
  > primo dizionario, commento corretto ed E2E rosso prima; 3a non si tocca → S17.
- **S17** ✅ 2026-10-07 — Correzione: un cambio lingua non rimonta più l'app. Base `1cad0d628`, sopra il
  checkpoint di sicurezza (`95293ab51` · `1cad0d628`, verificato con i blob). Checkpoint a parte.
  > **Note implementazione**:
  > - **test-author**, rosso prima del fix:
  >   - nuovo E2E `3c: a Welcome language whose catalogue arrives late survives the load…` in
  >     `auth.spec.ts` (+107), con 3a intatto. Il chunk italiano viene trovato per contenuto nel build,
  >     leggendo il marcatore da `it.json`. La route lo trattiene finché `data-i18n-ready="false"` non è
  >     a schermo: niente orologio.
  >   - Barriera verde: chunk trattenuto e `ready=false` osservato.
  >   - Contratto rosso: form diverso (soft) e `lang` `en` invece di `it`, 10 letture
  >     (`/tmp/libreFolio_o_remount_e2e_red2.log`).
  >   - Caso unitario in `layout.gate.test.ts` (+31/−1, il mock di `i18nLoading` diventa writable): rosso,
  >     1 su 409 (`/tmp/libreFolio_o_remount_unit_red.log`).
  > - **fix**:
  >   - `routes/+layout.svelte` e `(app)/+layout.svelte`: `let i18nBooted = false; $: if (!$i18nLoading)
  >     i18nBooted = true;`, e `{#if $i18nLoading}` → `{#if !i18nBooted}`;
  >   - corretto il commento su `data-i18n-ready`;
  >   - nessun export nuovo da `$lib/i18n`, quindi il mock del gate non va toccato.
  > - **gate**, uno per volta sulla 6160 (il rebuild del frontend l'ha fatto l'avvio del backend: build
  >   delle 16:56, dopo le modifiche, con `i18nBooted` nei nodi 0 e 2):
  >
  > | Comando | Esito | Log |
  > |---|---|---|
  > | `test … front-utility auth "catalogue arrives late"` | 3c passato | `/tmp/libreFolio_o_remount_green1.log` |
  > | `test … front-utility onboarding-component-unit` | 14 file, 409 passati | `/tmp/libreFolio_o_remount_onb.log` |
  > | `test … front-utility auth` | 25 passati (3a, 3b, 3c compresi) | `/tmp/libreFolio_o_remount_auth_all.log` |
  > | `test … front-utility settings` | 45 passati (Preferenze e About, cioè anche la diagnostica plugin col login) | `/tmp/libreFolio_o_remount_settings.log` |
  > | `test … front-utility component-unit` | 109 file, 2829 passati | `/tmp/libreFolio_o_remount_comp.log` |
  > | `front check` | 0 errori, 0 avvisi | `/tmp/libreFolio_o_remount_front_check.log` |
  > | Prettier `--check` sui 4 file frontend | pulito | — |
  > | `git diff --check`; `lsof` 6160 e 6170 | pulito; porte libere | — |
  >
  > - **wiki**: nuova pagina `problems/i18n-loading-gate-remounts-app.md`, una riga in `index.md`, una
  >   voce in `log.md`; `check_source_paths.py`: 0 percorsi mancanti nella pagina.
  >
  > **⚠️ Fuori pista**:
  > - la sonda di triage era sbagliata due volte: corpi riscritti di chunk serviti in gzip davano una
  >   pagina bianca, e una Promise restituita da un helper `async` veniva adottata, bloccando il test;
  >   la lezione è nella pagina wiki;
  > - `initI18n()` nello script di `(app)/+layout.svelte` resta: ora gira solo quando il gruppo
  >   `(app)` si crea davvero, e legge la lingua salvata. Non l'ho toccato, è fuori dall'approvazione.
- **S18** ✅ 2026-10-08 — Analisi, senza codice: i todo del bulk non sono tradotti
  (`TransactionBulkModal.svelte:3171`, trovato da M nella gallery). Base `ffa72cc2b`, pulita.
  > **Origine**: due fonti arrivano al bulk da `onImportBatch` (`:2303-2306`).
  > - I `field_todos` del parse (`BRIMFieldTodo`, `schemas/brim.py:695-711`): `reason_code` stabile,
  >   `message` di ripiego, `context` «per l'i18n». `importMerge.ts:100` li copia in `ImportTodo` con il
  >   `message` crudo.
  > - I todo del gap-fix (`brim_gap_fix.py:190`, `gap_fix_cost`) arrivano già tradotti:
  >   `ImportWizardModal.svelte:1385` → `importWizard.reportSet.gapFix.todo.<code>` →
  >   `gapFixModel.ts:253`.
  >
  > Il bulk stampa `message` in 3 punti: `:3171` (bloccanti), `:3199` (warning, `message || field`) e
  > `:2184` (`todoWarningItems`, nel dialogo di conferma al salvataggio).
  >
  > **Codici** (10 punti di emissione):
  >
  > | Codice | Dove | Campo | Gravità | Lingua del `message` |
  > |---|---|---|---|---|
  > | `ca_account_trade_sell_quantity_presumed` | `broker_credit_agricole.py:693` | quantity | warning | italiano |
  > | `ca_account_trade_bundled_amount` | `:737` | cash | warning | italiano |
  > | `derived_quantity` | `:1138` | quantity | warning | **inglese** |
  > | `ca_account_trade_unresolved` | `:1566` | asset_id | blocker | italiano |
  > | `ca_account_charge_unallocated` | `:1598` | asset_id | warning | italiano |
  > | `danske_trade_charges_included` | `broker_danske_bank.py:1553` | cash | warning | finlandese |
  > | `demerger` | `:1568` | cost_basis_override | blocker | finlandese |
  > | `demerger_old_leg` | `:1578` | quantity | warning | finlandese |
  > | `corporate_action` | `broker_generic_csv.py:451` | cost_basis_override | blocker | inglese, senza `context` |
  > | `gap_fix_cost` | `brim_gap_fix.py:190` | cost_basis_override | blocker | tradotto all'origine |
  >
  > **Il disegno** (`brim_plugin_guide.md:431-458`): il `message` è nella lingua del file, e una chiave
  > `importWizard.brimNotice.<code>`, se c'è, lo sostituisce con la lingua dell'interfaccia. I codici
  > `degiro_*` restano senza chiave apposta, e lo garantisce un test.
  > - Nessuno dei 9 codici di parse ha una chiave: `importWizard.brimNotice` ha solo
  >   `ca_succession_transfer_in`, che è una notice.
  > - La ricerca della chiave esiste in `FixFlaggedStep.svelte:133-138`, in `ParseDetailModal.svelte:181-184`
  >   (senza valori) e in `resolveBrimNotice.ts` (notice, con `context`). Il bulk non la fa.
  > - Il caso di M è `corporate_action` di generic_csv (`generic_simple.csv`, `gallery.spec.ts:2276`):
  >   inglese in ogni lingua, perché il CSV generico non ha una lingua del file.
  >
  > **Proposta**, in attesa di decisione:
  > - A: un risolutore unico per i todo, con lo stesso contratto delle notice, nei 3 punti del bulk;
  > - B: la chiave `importWizard.brimNotice.corporate_action` nelle 4 lingue;
  > - opzionale: `derived_quantity` in italiano nel plugin, oppure una chiave.
  >
  > Decisione del developer (12:30): «A+B, e derived_quantity in italiano nel plugin» → S19.
- **S19** ✅ 2026-10-08 — Todo tradotti anche nel bulk: risolutore unico, chiave `corporate_action`,
  `derived_quantity` in italiano, una riga nella guida BRIM. Base `ffa72cc2b`.
  > **Note implementazione** (verifica prima del codice):
  > - copertura delle 2 copie locali: `ParseDetailModal.test.ts` copre la regola in entrambe le metà
  >   (registra `importWizard.brimNotice.probe_localized_blocker`), quindi la sua copia si sostituisce;
  >   `FixFlaggedStep.test.ts` non verifica il testo dei todo (il `NEEDLE-…` della riga 41 non ha
  >   asserzioni), quindi quella copia resta e va nel backlog;
  > - il bulk non ha un test di componente: la prova passa dall'E2E `tx-bulk-import-handoff.spec.ts`,
  >   che già inietta `field_todos`.
  >
  > **Esecuzione** (✅ 2026-10-08):
  > - **test-author**, rossi prima del codice:
  >   - 5 casi di `resolveBrimTodoMessage` in `resolveBrimNotice.test.ts` (+77): rossi per la funzione
  >     assente, con i 7 casi delle notice verdi;
  >   - l'E2E `S19 (A, B)` in `tx-bulk-import-handoff.spec.ts` (+153): `corporate_action` e
  >     `s19_probe_unworded`, bloccante e warning; il testo atteso si legge dal JSON del catalogo per
  >     `<html lang>`. Rossi: il marcatore del plugin presente e la chiave assente; verde: il codice senza
  >     chiave mantiene il `message`;
  >   - backend: `test_credit_agricole_derived_quantity_todo_speaks_italian_and_names_the_bond` (+18),
  >     rosso;
  >   - la guardia DEGIRO era verde (169).
  > - **A**:
  >   - `resolveBrimTodoMessage` in `resolveBrimNotice.ts`: chiave `importWizard.brimNotice.<reasonCode>`,
  >     valori da `context`, e se manca la chiave il `message` del plugin;
  >   - usato nei 3 punti del bulk, con `|| field` dove c'era e `todo` al posto di `t` nelle arrow;
  >   - usato in `ParseDetailModal`; `FixFlaggedStep` resta con la sua copia (backlog).
  > - **B**: `dev.py i18n add importWizard.brimNotice.corporate_action`, nelle 4 lingue
  >   (`/tmp/libreFolio_o_s19_i18n.sh`).
  > - **C**: il `message` di `derived_quantity` in italiano (`broker_credit_agricole.py:1143`).
  > - **D** (aggiunta del developer, trovata da Q):
  >   - `dev.py i18n update tools.pacAllocator.planner.brokers.incrementHelp`: per numero di quote un
  >     intero, per importo l'importo minimo, ed è così che si comprano frazioni;
  >   - i due `default:` in linea (`BrokerEditor.svelte:226`, `BrokersStep.svelte:111`) allineati;
  >   - verificato nel codice: `request.ts:190`, `schemas/pac_allocator.py:233-236,386`,
  >     `evaluator.py:326-331`.
  > - **Documentazione**:
  >   - docs-writer: un paragrafo nella guida BRIM (`brim_plugin_guide.md:460-464`); build strict verde,
  >     `check-links` rosso solo per il D28;
  >   - wiki: `concepts/import-todo-signals.md` corretta (i todo arrivano al bulk, `message` è nella
  >     lingua del file, nuova sezione sulla traduzione) e una voce in `log.md`.
  >
  > **Gate**, uno per volta sulla 6160:
  >
  > | Comando | Esito | Log |
  > |---|---|---|
  > | `test … front-utility core-unit "resolveBrim"` | 12 passati | `/tmp/libreFolio_o_s19_resolver.log` |
  > | `test … front-transaction tx-bulk-import-handoff` | 3 passati (D4, D5, S19) | `/tmp/libreFolio_o_s19_handoff.log` |
  > | `test … front-transaction tx-unit` | 15 file, 676 passati (compreso `ParseDetailModal`) | `/tmp/libreFolio_o_s19_txunit.log` |
  > | `test … external brim-providers` | 627 passati, 1 saltato (compreso il test nuovo) | `/tmp/libreFolio_o_s19_brim_providers.log` |
  > | `test … external brim-degiro` | 169 passati, guardia compresa | `/tmp/libreFolio_o_s19_degiro.log` |
  > | `test … front-utility core-unit` | 117 file, 3435 passati | `/tmp/libreFolio_o_s19_core.log` |
  > | `i18n audit` | 4163 chiavi; 0 morte; 3 non verificate, vive; 0 chiavi backend mancanti | `/tmp/libreFolio_o_s19_audit.log` |
  > | cataloghi contro HEAD | +1 chiave (`corporate_action`), 1 cambiata (`incrementHelp`), stesso insieme, forma canonica | — |
  > | `front check` | 0 errori, 0 avvisi | `/tmp/libreFolio_o_s19_front_check.log` |
  > | `lint`; black | verde; pulito prima e dopo su entrambi i file Python | `/tmp/libreFolio_o_s19_lint.log` |
  > | Prettier | 5 file puliti; `BrokerEditor` e `BrokersStep` hanno debito già alla base, invariato (48 e 35 righe) | — |
  > | `git diff --check`; `lsof` 6160 e 6170 | pulito; porte libere | — |
  >
  > **⚠️ Fuori pista**:
  > - **Dialogo di conferma non coperto.** Il terzo punto del bulk, la lista del dialogo di conferma al
  >   salvataggio, non ha un test: `ConfirmModal` non ha `testId` passato dal bulk, e l'interruttore e
  >   le voci della lista non hanno agganci. Leggerli richiederebbe classi CSS o testo tradotto. Backlog:
  >   `testId` sul dialogo e agganci nel componente condiviso.
  > - **Pagina PAC di Q.** `user/tools/pac-allocator/index.en.md:36` promette ancora «0.001 = fractions
  >   down to three decimals», sia sulla mia base sia sulla punta di `e-alfy-q-doc-inglese-1-2`. Va
  >   corretta da Q; io non la tocco.
  > - **Descrizione nello schema.** `schemas/brim.py:705` descrive ancora `message` come «fallback
  >   (English)», contro la regola della lingua del file. Non l'ho toccata.
  > - **`svelte-check` dal test-author.** I 2 errori in `KpiSection.svelte` che aveva visto venivano da un
  >   client generato vecchio; il rebuild li ha tolti, e il mio `front check` è a 0.
  >
  > **Integrazione**: `a312797bf` · `2a8b18aad` · `be2954522` · `ec0a698cc`, merge `5d9e9af01`, nel treno
  > 14 (`dev_release2` = `9eb01c756`).
- **S20** ✅ 2026-10-08 — Sei reperti di Q, approvati dal developer («Affidali tutti e tre a O, prima della
  1.2», più tre testi): analisi breve, poi correzione, test rossi prima dove ha senso. Base `108a2adf5`
  (treno 17: solo doc e CHANGELOG rispetto a `cf4248bd9`).
  > **Analisi**, confermato / non confermato:
  > 1. **Stringhe FX in inglese: confermato.**
  >    - In `fx/[pair]/+page.svelte`: `:1120` e `:1184` («Sync failed: …»), `:838` (ripiego «Failed to
  >      load rates»), `:385` e `:442` (`Asset #${id}`, nome di riserva della serie di confronto).
  >    - In `FxCard.svelte:286`: i titoli del pulsante di sync.
  >    - In `FxDataEditorSection.svelte`:
  >      - le colonne `:56` «Rate» e `:125` «Preview»;
  >      - l'errore `:166` «N row(s) have invalid rate values…»;
  >      - il toast `:224-227` con i contatori «saved», «deleted», «skipped»;
  >      - `:246-248` «unknown error», «Failed to save:» e «FX save failed»;
  >      - `:318-322` Saving…, Save (N) e Cancel.
  >    - In `FxTable.svelte:193`: l'intestazione «Rate».
  >    - In `FxDataImportModal`: una mappa di 4 lingue scritta a mano (`:27-31`) fuori dal catalogo.
  >      Il `title` mancante invece è **non confermato** (correzione del test-author): `:184` passa già
  >      `title={$t('csvImport.title')}`, e il default «Import CSV Data» di `DataImportModal:54` non si
  >      vede mai, perché tutti i chiamanti passano un titolo.
  >    - Nei componenti condivisi usati dall'area FX:
  >      - `SyncModalBase` `:192` e `:196` (timeout), `:199` («Sync failed»), `:439` e `:511`
  >        («Retry N failed»);
  >      - `DataImportModal:265` (placeholder);
  >      - `CsvEditor:320-430` (11 errori CSV).
  >    - Non confermati: i `$t(…) ?? 'English'` di `SyncModalBase`, `FxSyncModal` e `PageSyncModal`
  >      sono ripieghi morti, perché `$t` non restituisce mai null; `FxCard:170` `'Enter'` è un tasto.
  >    - `fx/+page.svelte:355` e `:870` sono veri, ma il file era di K: li ho fatti dopo che K ha
  >      chiuso (messaggio del coordinatore), con `fx.loadFailed` e `common.error`. La `:864` di K
  >      (`count` → `n`, treno 18) non l'ho toccata: fra le due modifiche restano 5 righe invariate,
  >      quindi la fusione è pulita.
  > 2. **Aiuto di Borsa Italiana: confermato.** `borsa_italiana.py:376-377` punta alla pagina sviluppatori;
  >    gli altri quattro provider puntano a `/mkdocs/user/assets/providers/<slug>/`, e
  >    `user/assets/providers/borsa-italiana.*.md` esiste in 4 lingue.
  > 3. **Sync a 120 s: confermato, e vale anche per `AssetSyncModal:52`.**
  >    - Le richieste sono fisse a 120 s: `FxSyncModal:45`, `PageSyncModal:90` e `:120`,
  >      `AssetSyncModal:52`.
  >    - Il campo Timeout di `SyncModalBase` muove solo il conto alla rovescia.
  >    - Cura: la richiesta dura `max(120 s, timeout scelto + 5 s)`, così non si accorcia nulla rispetto a
  >      oggi; il messaggio cita il limite applicato.
  > 4. **justETF «history only»: confermato.** `justetf.py:227`: per USD, CHF e GBP il provider dà il
  >    `latestQuote` giornaliero (`:262-264`, `:294-303`). Il tooltip è la descrizione del backend; non
  >    esistono chiavi `assets.providerParams.justetf.*`.
  > 5. **Conteggi delle valute.**
  >    - BOE «20+»: **confermato**, la mappa ne ha 15.
  >    - ECB «30+» nei testi per l'utente: **confermato**; misurato sull'API pubblica il 2026-10-08, le
  >      valute pubblicate ogni giorno sono 29 (BGN si ferma al 2025-12-31).
  >    - ECB «45+» nella docstring: **non confermato**, perché la scoperta restituisce 44 valute più EUR,
  >      dismesse comprese. Va solo chiarito.
  >    - FED «20+» con 20 valute: vero, non lo tocco.
  > 6. **Tooltip dei livelli di AI Export: confermato.** `aiExport.detailLevelHelp.*` dice «fino a
  >    30/14/7 giorni». È vero per i prezzi (`policy.py:48-52`); per gli indicatori, secondo la classe
  >    temporale, si arriva a 84/28/14 giorni (`:54-82`). La doc utente non cita i numeri, la tabella per
  >    sviluppatori (`ai_export_sampling.md`) concorda col codice. L'E2E `ai-export-panel.spec.ts:194`
  >    fissa il testo inglese attuale e va aggiornato.
  >
  > **Note implementazione** (2026-10-08, base `108a2adf5`):
  > - **Rossi prima, dal test-author.**
  >   - 5 nel backend, in `services provider-contracts`: l'URL d'aiuto di Borsa e la copertura «20+» di
  >     BOE nelle 4 lingue (log del 18:27: 5 falliti, 15 passati).
  >   - 1 E2E `front-fx fx-editor` (Save/Cancel in italiano).
  >   - I vitest dei 4 modali di sync: il limite della richiesta e il banner del timeout.
  >   - In totale 21 rossi nel frontend, dal suo rapporto.
  >   - Adattato senza rosso: `ai-export-panel.spec.ts:194` ora legge la frase da `en.json`.
  > - **Timeout del sync (punto 3).**
  >   - `syncRequestTimeoutMs(sec) = max(120 000, sec × 1000 + 5000)` in `utils/sync/syncHelpers.ts`.
  >   - `SyncModalBase.doSyncSection` lo ricalcola a ogni richiesta, retry compresi, e lo passa a
  >     `doSyncFn(ids, {timeoutMs})`.
  >   - `FxSyncModal`, `PageSyncModal` (2 chiamate) e `AssetSyncModal` lo passano ad axios come `{timeout}`.
  >   - I due testi di timeout citano i secondi applicati: `fx.sync.timeoutAfter` e `fx.sync.requestTimedOut`.
  > - **Stringhe FX (punto 1).**
  >   - 32 chiavi nuove nelle 4 lingue con `dev.py i18n add`:
  >     - `common.unknownError`, `fx.rate`, `fx.loadFailed`, `fx.card.{manualOnly,syncFromProvider}`;
  >     - `fx.sync.{timeoutAfter,requestTimedOut,failed,retryFailed}`;
  >     - `fxDetail.{syncFailed,loadFailed,assetFallback,invalidRates,savedSummary,savedCount,deletedCount,skippedCount,saveFailed}`;
  >     - `dataEditor.saveFailed`, `csvImport.{placeholder,headerMismatch}`, `csvImport.errors.*` (11).
  >   - Riusate: `common.{preview,cancel,error}` e `dataEditor.{save,saving}`.
  >   - `FxDataImportModal` perde la mappa scritta a mano.
  > - **Testi del backend (punti 2, 4 e 5).**
  >   - `borsa_italiana.py:377` → `/mkdocs/user/assets/providers/borsa-italiana/`.
  >   - `justetf.py:227` descrive l'ultimo prezzo giornaliero per USD, CHF e GBP.
  >   - BOE «20+» → «15».
  >   - ECB «30+» → «circa 30» nelle 4 lingue; la docstring `:30` è riscritta (44 valute più EUR, 29
  >     pubblicate ogni giorno).
  > - **Tooltip AI Export (punto 6).** `aiExport.detailLevelHelp.{compact,standard,full}` aggiornate con
  >   `dev.py i18n update`: 30/14/7 giorni per i prezzi, 84/28/14 per gli indicatori più lenti.
  > - **Cambi di testo voluti, in inglese:**
  >   - «row(s) have invalid rate values» diventa un plurale ICU;
  >   - «Sync failed: unknown» → «Sync failed: unknown error», lo stesso ripiego dell'editor;
  >   - «Saving...» → «Saving…»: è la stessa chiave dell'editor degli asset (`AssetDataEditorSection:565`),
  >     fissata dallo spec del test-author;
  >   - il timeout cita il limite applicato.
  >
  >   Ogni altro testo spostato nel catalogo è identico all'originale.
  >
  > **⚠️ Fuori pista**:
  > - **Il primo `front-fx all` ha dato 1 rosso su 103.** `fx-csv-import.spec.ts:227` fissa «Header
  >   currencies don't match», e io avevo messo l'apostrofo tipografico (’), cambiando il testo visibile.
  >   - Corretto con `dev.py i18n update`, tornando ai testi originali della mappa (apostrofo ASCII in
  >     EN, IT e FR).
  >   - Con la stessa regola il placeholder torna a «...».
  >   - L'errore in linea dell'editor torna a «Failed to save: X», con la chiave nuova
  >     `dataEditor.saveFailed`, distinta dal toast `fxDetail.saveFailed`.
  >   - Il test non è stato toccato.
  > - **Prettier.** Una riga vuota doppia in `FxDataImportModal.svelte`, rimasta dopo aver tolto la mappa:
  >   corretta. La base era pulita.
  > - **La guardia di K sui nomi in `values`** (treno 18) non è ancora nel mio albero. L'ho approssimata
  >   con uno script che usa il parser ICU di `node_modules`, sui 13 file toccati: 181 chiamate, tutte
  >   coerenti, tranne due casi non miei:
  >   - `fx/+page.svelte:864`, la riga di K;
  >   - `fx/[pair]/+page.svelte:1484-1485` (`chart.tooltip.stale` e `fxStale`), preesistenti dal
  >     2026-04-17: passano il testo grezzo senza `values`, e il grafico sostituisce `{days}` da sé.
  > - **Fuori dall'area FX, non toccati:**
  >   - `AssetDataEditorSection.svelte:458-462` ha le stesse stringhe fisse («Failed to save:», «Save
  >     failed:»);
  >   - i parametri di justETF non hanno chiavi `assets.providerParams.justetf.*`;
  >   - FED «20+» con 20 valute è vero;
  >   - `test_provider_contracts.py` è offline, ma catalogato `write-scoped`.
  >
  > **Gate** (corsia 6160, `/tmp/librefolio-r2-o`, uno per volta):
  > - `front-utility component-unit`: 111 file, 2863 test ✅ (prima il filtro `"SyncModal"`: 4 file, 89);
  > - `front-utility core-unit`: 117 file, 3435 ✅, `catalogIcuLocale` compreso;
  > - backend:
  >   - `services provider-contracts`: 419 ✅, 1 saltato (`mockprov` senza URL, voluto);
  >   - `borsa-italiana-search` 5 ✅, `borsa-italiana-funds` 17 ✅, `provider-errors` 134 ✅;
  > - E2E:
  >   - `front-fx all` sull'albero finale: 103 E2E e 126 vitest ✅, 13 azioni;
  >   - `front-portfolio risk-lab`, il sync della pagina (`:6809` e `:6903`): 2 ✅;
  >   - `front-ai-export panel`: 6 ✅;
  > - `utils gate-i18n-usage`: 195 ✅;
  > - `i18n audit`: 4198 chiavi per lingua, complete, 0 morte. Le 3 non verificate sono preesistenti:
  >   `chartSettings.params.{amplitude,histogramScale}` e `transactions.fields.cash_code`;
  > - cataloghi contro `108a2adf5`: +32 chiavi, stesso insieme nelle 4 lingue, 3 valori cambiati
  >   (`detailLevelHelp`), forma canonica;
  > - controlli statici:
  >   - `front check`: 0 errori, 0 avvisi;
  >   - Prettier pulito sui 20 file toccati e sui 4 cataloghi;
  >   - `dev.py lint` ✅; black lascia invariati i 5 file;
  >   - `git diff --check` pulito;
  > - porte 6160 e 6170 libere.
  >
  > **Aggiunta prima del commit** (2026-10-08, reperto di M, girato dal coordinatore): i 3 avvisi
  > `importWizard.reportSet.{incompleteBlocks,partlySelectedBlocks,ungroupedBlocks}` dicevano «Continue /
  > Continua / Continuer / Continuar è disattivato».
  > - **Verificato.**
  >   - Gli avvisi compaiono solo nel piede del passo `select` (`ImportWizardModal.svelte:5257-5266`),
  >     accanto a `import-wizard-parse`, che è disattivato da `!step2CanParse` (`:338`, `:5280`) e ha
  >     l'etichetta `importWizard.parse` («Parse ({n})»).
  >   - `common.continue` è il pulsante dei passi successivi (`:5323` e seguenti).
  >   - Le chiavi vengono da `8c3271235` (01/10), `955148dfb` (07/10) e `38dd5d1b4` (08/10); nessuna è
  >     in `v1.1.0`.
  > - **Cambia solo il nome del pulsante**, in 12 stringhe, con `dev.py i18n update`
  >   (`/tmp/libreFolio_o_s20_parse_button.py`).
  >   - I nomi li ricava dai cataloghi: il vecchio da `common.continue`, il nuovo da `importWizard.parse`
  >     senza « ({n})». Così diventano Parse, Analizza, Analyser e Analizar.
  >   - Prima di scrivere controlla che il nome compaia una volta sola; dopo, rilegge i valori scritti.
  >   - Accordo e genere restano: entrambe le etichette sono verbi usati come nome, e il participio
  >     (disabled, disattivato, désactivé, desactivado) va bene così.
  > - **La doc era già giusta.** `developer/frontend/components/features/import-wizard.md:322` e
  >   `user/transactions/import/danske-bank.en.md:49,60` dicono che il set blocca **Parse**. Il piano di
  >   L (`26_brimDanskeBank/plan-phase00BrimDanskeBankStep7ButtonAndR6.prompt.md:130`) aveva già notato
  >   la discrepanza e l'aveva messa nel backlog.
  > - **Gate:**
  >   - `i18n audit`: 4198 chiavi, 0 morte, le stesse 3 non verificate;
  >   - `front-utility core-unit`: 117 file, 3435 ✅;
  >   - `front-transaction tx-import-report-set`: 32 ✅. I 32 saltati sono la divisione per progetto
  >     (`@mobile` solo su mobile); R3, R4, R6-E1 e U1, i test dell'avviso, sono verdi;
  >   - cataloghi contro `108a2adf5`: +32 chiavi e 6 valori cambiati (3 `detailLevelHelp` e i 3 avvisi),
  >     forma canonica.
  > - **Backlog per il test-author.** Il titolo di U1 (`tx-import-report-set.spec.ts:2863`) dice «block
  >   Continue», mentre il test controlla `import-wizard-parse`. Non l'ho toccato.

## 12. Definition of done

- L'audit esclude i test e riconosce i meccanismi del §5.2; la lista delle morte coincide con quella
  approvata, e ogni scarto è spiegato; `utils gate-i18n-usage` è verde.
- Cataloghi: stesso insieme di chiavi nelle 4 lingue; tolte esattamente quelle approvate; nessun altro
  testo cambiato, salvo i 3 FR di M1; `front check` verde (Prettier sui `.json`).
- Plurali: P1-P4 usano `plannerPlainDecimalCount`; i test provano «1 unit», «1.5 units» e il plurale
  quando il valore è mascherato.
- Gate ICU verde: 0 testi sensibili alla lingua identici fra due lingue.
- Skill e pagina developer allineate; piano aggiornato a ogni passo; porta 6160 libera.

## 13. Strategia di test e comandi

Tutti con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`, uno alla volta:

- `test --test-port 6160 --data-dir /tmp/librefolio-r2-o utils gate-i18n-usage`
- `test --test-port 6160 --data-dir /tmp/librefolio-r2-o front-utility core-unit` e `component-unit` (servono `node_modules`)
- `test --test-port 6160 --data-dir /tmp/librefolio-r2-o check-orphans`, dopo ogni registrazione nel runner
- `i18n audit` e `i18n audit --duplicates`, prima e dopo
- `front check`, poi `git diff --stat -- 'frontend/src/lib/i18n/*.json'`, lo script della parità e `git diff --check`

I test nuovi li scrive il **test-author**, con le regole della corsia. Non servono E2E: nessun
comportamento di pagina cambia, salvo un testo FR e il plurale «unit/units».

## 14. Decisioni per il developer

1. **Backlog PAC**: togliere ora le 107 morte, più le 2 nascoste (`routeCapMissing`, `sections.assets`)?
   Consigliato sì.
2. **Le 8 dubbie**: togliere `*Abbr` (5) e `common.{seeAll,recentTransactions}` (2) aggiornando la
   skill, e togliere `onboarding.welcome.skipHint` lasciando il campo vuoto? Consigliato sì.
3. **M1**: ramo `many` (invisibile, consigliato) oppure `=0 {aucune …}`?
4. **Condensazioni**: C1-C4 adesso e C5 dopo N, oppure nessuna?
5. **`dashboard.*` e `brokers.lots.*` morte**: aspettare N (consigliato) o togliere subito, visto che
   toccano solo i cataloghi?
6. **`WeightBars.svelte`** (codice morto, 2 chiavi): backlog per knip, o adesso?
7. **Il lavoro di fondo sullo strumento (§5.3) e `evaluator.py:968`**: backlog?
8. **`npm ci`** nel worktree O per i test frontend: autorizzato?

## Appendice A — classificazione delle 354 chiavi

Le prove sono `file:riga` nel sorgente non di test. Per il dettaglio chiave per chiave, vedi
`classification.json` nella cartella della sessione O.

### A.1 — Dinamiche o indirette: vive, da tenere e da rendere visibili all'audit (179)

| Meccanismo / motivo | Prova | Chiavi | N | Origine nell'audit |
|---|---|---|---|---|
| array di chiavi (segmento con cifra) | `lib/components/onboarding/OnboardingIntroScene.svelte:26` | `onboarding.intro.line2` | 1 | non verificata |
| backend: codice errore provider | `resolveProviderError.ts:48 'providerErrors.${code.toUpperCase()}'` | `providerErrors.{FETCH_ERROR,MISSING_PARAMS,NOT_FOUND,NOT_IMPLEMENTED,NO_DATA,PARSE_ERROR,SCRAPE_ERROR,TIMEOUT,UNSUPPORTED_PAGE}` | 9 | non verificata |
| backend: enum FinancialSector senza spazi | `sector_fin_utils.py:24-33 → assetTypes.ts:427 → AllocationPieChart.svelte:177` | `sectors.{BasicMaterials,ConsumerDiscretionary,ConsumerStaples,CorporateBonds,GovernmentBonds,HealthCare,RealEstate}` | 7 | non verificata |
| backend: f-string + vocabolario camelCase | `ai_export/analyses/catalog.py:77,92… → promptRenderer.ts:307` | `aiExport.additionalData.reason.{deeperTechnical,directExposure,fifoDetail,performanceContext,positionContext}` | 5 | viva solo grazie ai test |
| backend: mappa _message_key_for_issue → message_i18n_key | `backend/app/services/lots_analysis_service.py:2027-2039,1892 → DataQualityBanner.svelte:158` | `dataQuality.{assetCostNoEligibleLots,assetIncomeNoEligibleLots,currentPriceAssumedAtCost,fifoSourceQuantityMissing,referencePriceFallback,referencePriceUnavailable,shortAdjustmentNotSupported,shortTransferNotSupported,transferPairMissing}` | 9 | morta per l'audit |
| helper locale text() su const KEY | `planner/result/KpiCards.svelte:25,45 (+ tile() :96-110)` | `tools.pacAllocator.planner.result.kpi.{allInvested,allReachable,finalInvested,noCost,orders}`, `tools.pacAllocator.planner.result.kpi.compute.{budget,budgetHelp,engine,help,nodeLimit,objectives,objectivesHelp,time,timeHelp,title}`, `tools.pacAllocator.planner.result.kpi.help.{explicitCost,finalInvested,fixedReference,orders,selectedFunding}`, `tools.pacAllocator.planner.result.kpi.parts.{currentInvested,freeCash,reachable,trapped}` | 24 | morta per l'audit, non verificata |
| lista fissa FALLBACKS/HELP_FALLBACKS | `planner/result/LedgerTable.svelte:38-56 → :84-85` | `tools.pacAllocator.planner.result.ledger.fields.{final_physical,final_spendable}`, `tools.pacAllocator.planner.result.ledger.help.{alwaysZero,final_physical,final_spendable}` | 5 | non verificata |
| lista fissa HELP_FALLBACKS | `planner/result/ProofPanel.svelte:39-45 → :63` | `tools.pacAllocator.planner.result.proof.help.{absoluteGap,dual,primal,relativeGap}` | 4 | non verificata |
| lista fissa ORIGIN_FALLBACKS | `planner/shared/OriginBadge.svelte:29 (labels.ts:47)` | `tools.pacAllocator.planner.origin.{copied,modified}` | 2 | non verificata |
| lista fissa STEPS.titleKey | `ImportWizardModal.svelte:136-143 → :4262` | `importWizard.reportSet.gapFix.stepTitle`, `importWizard.{step1Title,step2Title,step3Title,step4Title,stepAssetsTitle,stepDuplicatesTitle,stepFixTitle}` | 8 | morta per l'audit, non verificata |
| lista fissa delle sezioni | `planner/result/ResultView.svelte:53 → :84` | `tools.pacAllocator.planner.result.sections.{exposures,ledger}` | 2 | non verificata |
| mappa EVENT_BADGE_KEY | `ChartSignalsSection.svelte:436-440 → :570` | `chartSettings.{badgeDividend,badgeInterest,badgeMaturitySettlement,badgePriceAdjustment,badgeSplit}` | 5 | non verificata |
| prop afterCopyKey (4 segmenti) | `support/supportLinks.ts:37-53 → SocialShareModal.svelte:138` | `support.share.facebook.afterCopy`, `support.share.instagram.afterCopy`, `support.share.tiktok.afterCopy` | 3 | viva solo grazie ai test |
| prop displayI18nKey/descriptionI18nKey | `lib/features/ai-export/catalog/shared.ts:133,134,141,142,149,150,157,158,165,166,173,174,181,182,189,190,197,198,205,206,213,214` | `aiExport.analysis.asset.market_analysis.{description,display}`, `aiExport.analysis.asset.position_review.{description,display}`, `aiExport.analysis.broker.fiscal_lots.{description,display}`, `aiExport.analysis.broker.performance_market_drivers.{description,display}`, `aiExport.analysis.broker.review.{description,display}`, `aiExport.analysis.fx.exposure_impact.{description,display}`, `aiExport.analysis.fx.pair_analysis.{description,display}`, `aiExport.analysis.portfolio.fiscal_lots.{description,display}`, `aiExport.analysis.portfolio.pac_planning.{description,display}`, `aiExport.analysis.portfolio.performance_market_drivers.{description,display}`, `aiExport.analysis.portfolio.rebalancing.{description,display}` | 22 | morta per l'audit |
| suffisso ${displayNameKey}Full | `ChartSignalsSection.svelte:142 (registry.ts:89-107)` | `chartSettings.signals.{assetComparisonFull,fxPairFull}` | 2 | viva solo grazie ai test |
| ternario multilinea | `lib/components/charts/ChartSettingsModal.svelte:339,341,343` | `chartSettings.{backendPreviewApply,backendPreviewRealTarget,backendPreviewUnavailable}` | 3 | non verificata |
| wrapper label() | `lib/components/dashboard/YieldOnCostCell.svelte:71,91,96,100,102,121,123,130` | `dashboard.{yieldOnCostFirstTransaction,yieldOnCostFxPair,yieldOnCostFxRateDate,yieldOnCostGrossPerUnit,yieldOnCostIssueDate,yieldOnCostNoIncome,yieldOnCostNoIncomeTitle,yieldOnCostPeriod,yieldOnCostUnavailable,yieldOnCostValue}` | 10 | morta per l'audit |
| wrapper label() | `lib/components/brokers/lots/UnifiedLotsTable.svelte:99,101,103` | `brokers.lots.states.{DEGRADED,DISTRIBUTED,IN_TRANSIT}` | 3 | morta per l'audit |
| wrapper label() | `lib/components/dashboard/ContributionTable.svelte:292,305,428` | `dashboard.{annualizedReturnPeriodTooltip,periodPnlTooltip,status}` | 3 | morta per l'audit |
| wrapper label() | `lib/components/dashboard/ExposureTable.svelte:320,321,322` | `dashboard.{yieldOnCost,yieldOnCostDisplayName,yieldOnCostTooltip}` | 3 | morta per l'audit |
| wrapper tr() | `lib/features/tools/pac-allocator/planner/modeText.ts:21,28,36,57,64,65` | `tools.pacAllocator.planner.brokers.{feeMax,feeMin,feeZero,fundingChipHelp,stepUnits}`, `tools.pacAllocator.planner.units.shares` | 6 | morta per l'audit |
| wrapper translate() | `lib/features/ai-export/templates/promptRenderer.ts:310,311,312,313,314,315,316` | `aiExport.additionalData.steps.{dataset,detail,exportType,feature,openLibreFolio,page,period}` | 7 | morta per l'audit |
| wrapper translateOr() | `lib/components/brokers/lots/LotWacPriceChart.svelte:608,609,610,611,612,613,614,615,616,617,618,619,620,621,622` | `brokers.lots.chartMarkers.{adjustmentType,completeSale,eventDate,nextPrice,nextQuantity,openingValue,partialSale,previousPrice,previousQuantity,quantityEffect,quantitySold,residualQuantity,salePrice,totalCost,unchanged}` | 15 | morta per l'audit |
| wrapper translateOr() | `lib/components/dashboard/OtherPeriodEffectsTable.svelte:64,65,66,73,74,75,230,233` | `dashboard.{categoryCost,categoryIncome,categoryOther,otherPeriodEffects,otherPeriodEffectsSubtitle,otherReconciliationResidual,unallocatedCosts,unallocatedIncome}` | 8 | morta per l'audit |
| wrapper translateOr() | `lib/components/dashboard/PerformanceChart.svelte:307,310,311,312,313,314,315` | `dashboard.{closedByPeriodEnd,closedPositions,costs,endValue,openAtPeriodEnd,openPositions,startValue}` | 7 | morta per l'audit |
| wrapper translateOr() | `lib/components/brokers/lots/LotGanttChart.svelte:698,701,702,704,721` | `brokers.lots.tooltip.{initialValue,shares,sharesOpenOutOf,since,totalPnl}` | 5 | morta per l'audit |
| wrapper translateOr() | `OtherPeriodEffectsTable.svelte:117, PerformanceChart.svelte:317` | `common.category` | 1 | viva solo grazie ai test |

### A.2 — Morte: sicure da togliere (167)

| Meccanismo / motivo | Prova | Chiavi | N | Origine nell'audit |
|---|---|---|---|---|
| backlog PAC di D (decisione (a)), nessun lettore | `PacRound5PostMerge:3159; P1FinalRemoval:33` | `tools.pacAllocator.planner.{add,restore,restoreCopied}`, `tools.pacAllocator.planner.assetEditor.{addCategory,categoryId,categoryLabel,class,classHint,compositionModifiedHelp,dimension,exposureAdd,exposures,idDuplicate,idMissing,idTooLong,manualId,manualIdPlaceholder,neverByName,overHundred,priceDate,priceModifiedHelp,title,unclassified,weight}`, `tools.pacAllocator.planner.assets.{compositionModifiedHelp,copyClassifications,copyPrices,noAutoPrice,noExposures,priceModifiedHelp}`, `tools.pacAllocator.planner.brokerCopy.currencies`, `tools.pacAllocator.planner.brokerEditor.{feeRule,localCash,notIn200,origin,stepRule}`, `tools.pacAllocator.planner.brokers.{conversions,fee,funding,localCash,localHere,stepAmount}`, `tools.pacAllocator.planner.copy.alreadyInDraft`, `tools.pacAllocator.planner.copyNotice.when`, `tools.pacAllocator.planner.distribution.change`, `tools.pacAllocator.planner.fx.{addFrom,addTo,copy,limitsHelp,notInVersion,notStored,openFxPage,pairsHint,remove}`, `tools.pacAllocator.planner.result.allocationHint`, `tools.pacAllocator.planner.result.assets.{final,target}`, `tools.pacAllocator.planner.result.exposures.public`, `tools.pacAllocator.planner.result.kpi.{fundingReachable,shortfallParts,shortfallPartsNoRounding}`, `tools.pacAllocator.planner.result.outcomes.{incumbent_found,infeasible_proven,no_incumbent,no_op}`, `tools.pacAllocator.planner.result.plan.{funding,fxTitle,privacyHint,sequence}`, `tools.pacAllocator.planner.result.proof.{decimalVerified,exactValue,infeasible,notProven,optimal,ordinal,tieBreak,tieBreakClosed}`, `tools.pacAllocator.planner.result.proof.sources.solver_status`, `tools.pacAllocator.planner.result.states.noIncumbent.rejected`, `tools.pacAllocator.planner.review.{exposureDimension,exposureRows,exposuresHelp,factsAll,factsChanged,factsLabel,fx,intro,noFx,noOrders}`, `tools.pacAllocator.planner.review.kind.exposures`, `tools.pacAllocator.planner.route.{capHint,fee,noPrice,none,priorityHint,ready}`, `tools.pacAllocator.planner.routing.{capRule,next,previous,unitRule}`, `tools.pacAllocator.planner.scenario.{asOf,noValues}`, `tools.pacAllocator.planner.strategy.{fromContract,noParameters}`, `tools.pacAllocator.planner.summary.{date,pairs}`, `tools.pacAllocator.planner.targets.control` | 107 | morta per l'audit, non verificata |
| dashboard: resti di refactor (Exposure/Contribution → Holdings/Performance) | `git -S: 13052a006` | `dashboard.{costsTooltip,gains,holdings,losses,realized,sharedScale,unallocated}` | 7 | morta per l'audit |
| le 3 tools.* di D, senza riferimenti | `P1FinalRemoval S8 Fuori pista` | `tools.{contractVersion,implementationVersion,open}` | 3 | morta per l'audit |
| lotti: doppioni delle dashboard.* o resti FIFO v3 | `OtherPeriodEffectsTable/PerformanceChart usano 'dashboard.*'` | `brokers.lots.{allLots,buyDate,categoryCost,categoryIncome,categoryOther,dateRange,otherReconciliationResidual,unallocatedCosts,unallocatedIncome}` | 9 | morta per l'audit |
| nessun riferimento (letterale, famiglia, backend) | `grep frontend/src, backend/app` | `assetDetail.fxPairCreatedSynced`, `assets.lastPrice`, `brokers.{forceDelete,quota}`, `changelog.copied`, `chartSettings.tooltips.currencyPair`, `dataQuality.{hideDetails,showDetails}`, `files.{loadFailed,uploadFailed}`, `importWizard.{parseError,parsing}`, `signals.visual.zones` | 13 | morta per l'audit, non verificata |
| onboarding: testo sostituito o mai letto | `OnboardingReplaySection/IntroScene/OverlayHost attuali` | `onboarding.actions.{pause,skipPermanently}`, `onboarding.intro.title`, `onboarding.settings.{nextImport,replayOnNextImport,replayReady}` | 6 | non verificata |
| vecchio tour, mai cablato | `Onboarding Round8 PostReview:527 «da togliere a fine round»` | `onboarding.tour.steps.assets.{description,title}`, `onboarding.tour.steps.assetsAdd.{description,title}`, `onboarding.tour.steps.assetsConfig.{description,title}`, `onboarding.tour.steps.brokers.{description,title}`, `onboarding.tour.steps.brokersAdd.{description,title}`, `onboarding.tour.steps.brokersCurrency.{description,title}`, `onboarding.tour.steps.fxAdd.{description,title}`, `onboarding.tour.steps.fxPair.{description,title}`, `onboarding.tour.steps.settings.{description,title}`, `onboarding.tour.steps.tools.{description,title}`, `onboarding.tour.steps.transactionsImport.{description,title}` | 22 | non verificata |

### A.3 — Dubbie: decide il developer (8)

| Meccanismo / motivo | Prova | Chiavi | N | Origine nell'audit |
|---|---|---|---|---|
| campo WelcomeCopy.skipHint tenuto ma valorizzato '' | `routes/(app)/welcome/+page.svelte:47; features/onboarding/welcome.ts:23` | `onboarding.welcome.skipHint` | 1 | non verificata |
| chiave canonica della skill (merge 2026-07) senza lettori | `vive solo per 'common.${…}' in ProfileTab/PreferencesTab.test.ts` | `common.{recentTransactions,seeAll}` | 2 | viva solo grazie ai test |
| schema «Abbr» documentato (skill, Accepted Duplicates) ma nessun lettore | `nessun 'Abbr' nel sorgente; vive solo per 'chartSettings.signals.${…}' nei test` | `chartSettings.signals.{assetComparisonAbbr,compoundAbbr,fxPairAbbr,linearAbbr,sineAbbr}` | 5 | viva solo grazie ai test |

## Appendice B — i 112 gruppi di doppioni candidati

Elenco completo, con valori e chiavi: `dup_candidates.txt`; dati in `dup_groups.json`.

Ripartizione per namespace:

| Namespace | Gruppi |
|---|---|
| `signals` | 18 |
| `tools` | 13 |
| `brokers` | 10, di cui 6 sono C5 |
| `risk` | 6 |
| `importWizard` | 5 |
| misti | 4 |
| `common+tools` | 3 |
| `tools+transactions` | 3 |
| `uploads` | 3: C1-C3 |
| `assetDetail+fxDetail` | 2: C4 |
| `brokers+tools`, `brokers+dashboard`, `common+settings`, `dashboard`, `risk+signals`, `brokers+tools+transactions` | 2 ciascuno |
| altri | 1 ciascuno |

Si propone di condensarne 11: C1-C4 (5 gruppi) e C5 (6 gruppi, dopo N). Gli altri 101 si tengono,
con i motivi del §3: contesto o ruolo diverso, metadati dei plugin dei segnali, convenzione di modulo
del planner PAC, aree attive di A e N.
