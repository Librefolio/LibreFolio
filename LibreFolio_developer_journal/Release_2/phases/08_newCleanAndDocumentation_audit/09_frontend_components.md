# 09 — Componenti & route frontend — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/09_frontend_components.md)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso).
> Strumenti: `grep`/`find`/`git log --no-pager` + `npx knip --no-progress` (analisi
> statica, nessun server; config `frontend/knip.json` invariata dal 2026-08-05).
> Working tree incluse le modifiche beta NON committate del 02/09 (delete transazioni via
> `TransactionBulkModal`, riscrittura `ImportWizardModal`, ecc.).

---

## Sintesi esecutiva

**Tutti e 5 i reperti strutturali del report originale risultano FATTI.** I 4 componenti
morti (I1), la libreria `tanstack-table` (I2), i 12 barrel (I3) e `db-helpers.ts` (I5)
sono stati rimossi nel commit di remediation `be8394bb` (2026-08-05) e **nulla è rinato**:
knip oggi riporta **0 file inutilizzati** su tutto il frontend (erano 20). Le due
decisioni umane richieste (LiveTicker, FxProviderConfig) sono state prese e documentate
in `15_esecuzione_s1_s3.md` — LiveTicker **non** ripristinato per scelta esplicita
dell'utente, FxProviderConfig confermato superato da `FxPairAddModal` in editMode.

La patologia dei barrel però **sopravvive in forma minore**: i 13 `index.ts` attuali sono
tutti vivi, ma knip segnala **22 ri-esportazioni morte** dentro barrel vivi (i consumatori
importano i componenti per percorso diretto) — la stessa mezza adozione denunciata nel
2026-08, spostata di livello.

Nuovi rilievi dalla tornata beta: la rimozione di `TransactionDeleteModal.svelte` è
**pulita al 100 %** (nessun riferimento morto), ma la riscrittura dell'ImportWizard ha
lasciato **24 chiavi i18n orfane × 4 lingue = 96 voci morte**, più 1 chiave
`transactions.errors.*` il cui codice non è mai emesso dal backend.

| Metrica | Audit 2026-08-07 | Oggi 2026-09-02 | Comando |
|---|---:|---:|---|
| File inutilizzati (frontend) | 20 | **0** | `cd frontend && npx knip --no-progress` |
| — di cui barrel `index.ts` | 11 | 0 | idem |
| Export di componenti inutilizzati | 25 | 22 (solo ri-esportazioni in barrel vivi) | sezione "Unused exports" |
| Tipi di componenti inutilizzati | 32 | ~30 | sezione "Unused exported types" |
| `lib/components/` (no test) | 219 file / 80 515 righe | 233 file / 86 748 righe | `find src/lib/components -type f \( -name '*.ts' -o -name '*.svelte' \) ! -name '*.test.ts' ! -path '*__tests__*'` |
| `routes/` | 22 / 11 553 | 21 + 1 test / 11 537 (no test) | idem su `src/routes` |

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| I1a — `HoldingsPanel.svelte` (148 righe) assorbito | 🟡 da rimuovere | **FATTO** | File rimosso in `be8394bb` (`git log --diff-filter=D` sul path → `be8394bb 2026-08-05`); `grep -rn "HoldingsPanel" src/ e2e/` → 0. Il sostituto `PositionsPanel.svelte` è vivo: importato in `brokers/[id]/+page.svelte:23`, montato a `:577` (stessa riga citata dal vecchio audit) e in `dashboard/+page.svelte` | nessuna |
| I1b — `BrokerImportFiles.svelte` (223 righe) assorbito | 🟡 da rimuovere | **FATTO** | Rimosso in `be8394bb`; `grep "BrokerImportFiles\b"` → 0. `BrokerImportFilesModal.svelte` vivo: importato in `brokers/[id]/+page.svelte:17`, montato a `:769` (era `:759` — spostato dalle modifiche beta); il commento z-index in `ui/modals/ModalBase.svelte:15` che lo cita è ancora corretto | nessuna |
| I1c — `LiveTicker.svelte` (233 righe) rimosso dall'interfaccia | 🟡 decisione umana | **FATTO (SUPERATO per decisione)** | File rimosso in `be8394bb`; `grep -rn "LiveTicker" src/ e2e/` → **0 risultati, inclusi i 3 commenti** che lo citavano (`assetStore.ts:9`, `AssetModal.svelte:1158,1297` — tutti spariti). Decisione documentata in `15_esecuzione_s1_s3.md:199-206` e `388-415`: l'utente ha scelto di **non ripristinare** la striscia prezzi in dashboard | nessuna |
| I1d — `FxProviderConfig.svelte` (314 righe) da verificare | 🟡 da verificare | **FATTO (SUPERATO per decisione)** | Rimosso in `be8394bb`; `grep "FxProviderConfig" src/` → 0. Il commento obsoleto in `OrderableList.svelte` è stato **aggiornato**: ora recita *"Used by: FxProviderSelect, ColumnVisibilityToggle, ChartSignalsSection, ImportWizardModal"* (`:14`). Decisione documentata in `15_esecuzione_s1_s3.md:184-197`: capacità spostata in `FxPairAddModal` editMode → `FxProviderSelect`, superset stretto (drag-drop priorità + pathfinding DFS depth 4) | nessuna |
| I2 — `src/lib/tanstack-table/` (188 righe) + `@tanstack/table-core` | 🟡 da rimuovere | **FATTO** | `ls src/lib/tanstack-table` → inesistente; `@tanstack/table-core` assente da `package.json`; `grep -rn "@tanstack" src/ e2e/` → 0 import residui. Rimosso in `be8394bb` (incluso il suo `index.ts`, il 13° barrel) | nessuna |
| I3 — 12 barrel `index.ts` morti | 🟡 da rimuovere | **FATTO — nessuna rinascita** | `find src -name "index.ts"` → 13 file, **nessuno** dei 12 vecchi presente (`src/lib/index.ts`, `components/{assets,charts,fx,layout,settings/tabs,ui,ui/data-editor,ui/date,ui/display,ui/input,ui/modals}/index.ts` tutti spariti; `git show --stat be8394bb` conferma 13 `index.ts` eliminati). Degli attuali: **10 vivi** con importatori diretti (`$lib/api` 82, `$lib/i18n` 160, `$lib/types` 46, `$lib/charts/signals` 30, `$lib/components/ui/select` 29, `table` 9, `transactions` 4, `ui/feedback` 4, `ui/media` 4, `ai-export/serialization` 2); **3 sub-barrel** `transactions/{events,shared,wac}/index.ts` senza importatori diretti ma ri-esportati dal padre vivo (`transactions/index.ts:8-10`) → vivi transitivamente | sorveglianza: la mezza adozione persiste (vedi Nuovi rilievi N2) |
| I4 — 32 tipi di componenti inutilizzati | 🟢 aperto | **ANCORA VALIDO** (~30) | knip 2026-09-02: 24 tipi in `components/table/index.ts:54-87`, 3 duplicati in `table/types.ts:416,483,615`, `TableRow` in `ui/data-editor/DataEditorTypes.ts:78`, `SelectProps` in `ui/select/types.ts:53`, `AssetEvent`/`ValidationIssue` in `transactions/index.ts:11`. Mai campionati | campionare prima di rimuovere (task C1) |
| I5 — `e2e/fixtures/db-helpers.ts` inutilizzato | 🟢 da rimuovere | **FATTO** | `ls e2e/fixtures/` → `db-helpers.ts` assente (rimosso in `be8394bb`); nessun import residuo. Nota: `db-cleanup.ts` (nome simile, file diverso) è vivo — usato da `tx-clone.spec.ts` e `tx-bulk-promote-exec.spec.ts` | nessuna |

---

## Dettaglio reperti ancora aperti / regrediti

### I4 — tipi orfani dei componenti: immutato nel numero, concentrato nel barrel `table/`

Il grosso dei ~30 tipi orfani sta nel barrel `components/table/index.ts` (24 ri-export di
tipi da `types.ts` che nessuno importa via barrel) più 3 duplicazioni omonime fra
`table/index.ts` e `table/types.ts` (`ColumnFilter`, `DataTableProps`, `TablePreferences`
esistono in entrambi — knip li elenca due volte). È lo stesso nodo del vecchio I3:
finché il barrel espone più di quanto i consumatori chiedano, knip continuerà a segnalare.

### Rinascite: nessuna

Controllati esplicitamente: nessun `index.ts` barrel puro morto è rinato (lista completa
in I3 sopra); nessuna bandiera `isXLoaded` rinata (report 08, H1); nessun riferimento ai
4 componenti rimossi in codice, test o commenti.

---

## Task riesumati

| # | Task | Evidenza | Stima |
|---|---|---|---|
| C1 | Campionare i ~30 tipi orfani dei componenti (24 nel barrel `table/`) e decidere: rimozione o adozione via barrel | knip "Unused exported types", righe in I4 | **S** |
| C2 | Sfoltire le 22 ri-esportazioni morte nei barrel vivi (vedi N2): o i consumatori importano via barrel, o il barrel smette di ri-esportare quei simboli | knip "Unused exports", tabella in N2 | **S** |
| C3 | Rimuovere le 24 chiavi `importWizard.*` orfane da tutte e 4 le lingue (96 voci) — residuo della riscrittura beta del wizard | elenco in N3 | **S** |
| C4 | Rimuovere `transactions.errors.cannotLinkEventNoAsset` (4 lingue) o emettere il codice dal backend se la casistica è viva | N4 | **S** |
| C5 | Sfoltire le fixture e2e orfane (5 `TEST_USER_*`, `chartRenders`, `waitForChartRerender`, `forAllLanguages`, `DEFAULT_LANGUAGE`, `pageUntilVisible`, `exists`, `API_BASE` fx-helpers) e 2 tipi e2e | N5 | **S** |

> **Stato 03/09 (esecuzione P1, Lane C) — tutti e 5 i task eseguiti**:
> - **C1+C2+C5** ✅ (P1-9): 22 ri-esportazioni morte sfoltite, tipi orfani dei componenti
>   rimossi, fixture e2e orfane rimosse. **Scoperta in corsa**: 2 file completamente
>   orfani ulteriori (`BaseDropdown.svelte`, `TransactionTypeBadge.svelte`) — decisione
>   utente richiesta, tracciata nel piano (fuori pista del 03/09).
> - **C3** ✅ (P1-8) — **con scarto di conteggio**: rimosse **25** chiavi × 4 lingue
>   (totale 2 523 → 2 498), non 24: il giro ha coperto anche la chiave di C4.
>   Verificato: `globalBrokerHint` e le altre assenti da `en.json`.
> - **C4** ✅ (P1-8): `transactions.errors.cannotLinkEventNoAsset` rimossa dalle 4 lingue
>   (strada «rimozione»: il codice backend non esiste). ⚠️ Le ~30 chiavi
>   `aiExport.dataset.*` citate nel 99 come candidate **NON erano orfane** (risoluzione
>   dinamica backend-driven dal catalogo) — tenute, non rimosse.

---

## Nuovi rilievi

### N1 — `TransactionDeleteModal.svelte`: rimozione beta pulita al 100 %

Il file è eliminato nel working tree (`git status`: `D
frontend/src/lib/components/transactions/modals/TransactionDeleteModal.svelte`) e **non
resta alcun riferimento morto**:

- import/componenti: `grep -rn "TransactionDeleteModal" src/ e2e/` → solo il commento
  esplicativo in `e2e/transactions/tx-delete.spec.ts:4` (*"the dedicated
  TransactionDeleteModal no longer exists…"*) — corretto tenerlo;
- barrel: `transactions/index.ts` (11 righe, vivo con 4 importatori) non lo esporta più;
- i18n: **zero** chiavi `deleteModal.*` in tutte e 4 le lingue (`grep -c deleteModal
  src/lib/i18n/{en,it,fr,es}.json` → 0/0/0/0). La funzione delete vive ora in
  `TransactionBulkModal` con le chiavi `transactions.bulk.markDelete/unmarkDelete/
  deleteSelected/confirmEditDelete/confirmEditDeleteMessage`, tutte referenziate.

`importRowState.ts` (73 righe, 5 funzioni + 2 tipi) è coerente con il suo test
(`importRowState.test.ts:5` importa esattamente i 5 export) ed è usato in produzione da
`ImportWizardModal.svelte:72`. Nessun disallineamento beta qui.

### N2 — 22 ri-esportazioni morte in barrel vivi (la mezza adozione persiste)

> ✅ **Risolto 03/09** (P1-9, Lane C): le 22 ri-esportazioni elencate sotto sono state
> sfoltite (strada «il barrel smette di ri-esportare»; es. `components/table/index.ts` non
> esporta più `DataTablePagination`/`SelectionBar` — verificato). La questione di policy
> (regola scritta barrel vs path diretto) resta da codificare.

knip 2026-09-02, sezione "Unused exports" — i simboli sono vivi come **file** (importati
per percorso diretto), morti come **ri-esportazioni di barrel**:

| Barrel | Ri-esportazioni morte |
|---|---|
| `components/table/index.ts:44-48` | `DataTablePagination`, `DataTableToolbar`, `DataTableColumnFilter`, `ColumnVisibilityToggle`, `SelectionBar` |
| `components/transactions/index.ts:2,7` | `ImportWizardModal` (importato diretto da `TransactionBulkModal.svelte:65`), `TransactionPickerModal` |
| `components/transactions/events/index.ts:1-2` | `AssetEventPicker`, `EventCreateMiniModal` |
| `components/transactions/shared/index.ts:1-3` | `TransactionResultBanner`, `TransactionTypeBadge`, `TransactionTypeSearchSelect` |
| `components/transactions/wac/index.ts:1` | `WacPreviewSection` |
| `components/ui/feedback/index.ts:2-5` | `InfoBanner`, `LoadingSpinner`, `ToastContainer`, `Tooltip` (usato via path diretto in ≥4 componenti, es. `DataEditor.svelte:28`) |
| `components/ui/media/index.ts:2,4,5,7` | `FileUploader`, `LazyImage`, `ImageCropper`, `AssetPickerModal` |
| `components/ui/select/index.ts:9` | `BaseDropdown` |

È la diagnosi del vecchio I3 ribaltata: i barrel non sono più conservanti di codice
morto, ma restano **mezza adozione** — alcuni consumatori passano dal barrel
(`brokers/[id]/+page.svelte:28`, `dashboard/+page.svelte:48`,
`transactions/+page.svelte:19`), altri dal path diretto. La regola andrebbe scelta e
scritta.

### N3 — 24 chiavi `importWizard.*` orfane × 4 lingue = 96 voci morte

> ✅ **Risolto 03/09** (P1-8, Lane C) — **25 chiavi, non 24**: la pulizia ha rimosso le 24
> elencate qui **più** `transactions.errors.cannotLinkEventNoAsset` (N4), ×4 lingue
> (2 523 → 2 498 chiavi totali). Via `./dev.py i18n`, mai edit a mano.

Residuo della riscrittura beta dell'ImportWizard. Verifica: 296 chiavi `importWizard.*`
in `en.json`; cercato ogni FQN come stringa fissa in `src/` ed `e2e/`; esclusi i lookup
dinamici confermati (`step*Title` via `STEP_DEFS`/`titleKey` a `ImportWizardModal.svelte:122-129,3551`;
`confidence.*`/`confidenceTip.*` a `:4169-4171`; `fixStep.splitKind.*` a
`FixFlaggedStep.svelte:385,413,817`; `brimNotice.*` a `resolveBrimNotice.ts:29`). Orfane
reali (presenti in tutte e 4 le lingue, verificato):

```
globalBrokerHint, uploadHint, uploadMultiHint, selectFiles, filterBrokers,
onlyUnparsed, pluginDefault, noBrokers, bulkDeleteConfirm, uploadError, parseResult,
transactionsCount, review, fieldTodos, fieldTodoBlocker, fieldTodoWarning,
fileParseError, resolveHint, suggested, likelyDupIncluded, compareTitle,
status.tooltip.possibleDup, status.tooltip.likelyDup, status.tooltip.pendingDuplicateJump
```

(`status.tooltip` definisce 8 chiavi, ne usa 5: `beforeOpening`, `unresolvedAction`,
`unresolvedReason`, `pendingDuplicate`, `possiblePendingDuplicate` —
`ImportWizardModal.svelte:1682,1694,1714,1723`.)

### N4 — `transactions.errors.cannotLinkEventNoAsset`: chiave senza codice backend

> ✅ **Risolto 03/09** (P1-8): chiave rimossa dalle 4 lingue (verificato: assente da
> `en.json`). Confermata la strada «casistica morta», non «backend rinominato».

Presente in tutte e 4 le lingue (es. `en.json:2156`), ma il codice
`cannotLinkEventNoAsset` **non è emesso da alcun punto del backend** (`grep -rn
"cannotLinkEvent" backend/` → 0) né referenziato staticamente dal frontend (il resolver è
dinamico: `resolveValidationMessage.ts:219` `transactions.errors.${code}`). Delle 33
chiavi `transactions.errors.*` senza ref statico, 32 corrispondono a codici reali del
backend (`grep` per codice su `backend/app/` → ≥1 occorrenza ciascuno); questa è l'unica
orfana vera. O il backend ha rinominato il codice, o la casistica è morta.

### N5 — Fixture e2e orfane

> ✅ **Risolto 03/09** (P1-9, Lane C): le 5 fixture `TEST_USER_*`, gli helper
> (`chartRenders`, `waitForChartRerender`, `forAllLanguages`, `DEFAULT_LANGUAGE`,
> `pageUntilVisible`, `exists`, `API_BASE`) e i 2 tipi e2e sono stati rimossi.

knip 2026-09-02: `TEST_USER_ALICE/BOB/CAROL/DAVE/EVE` (`e2e/fixtures/test-users.ts:26-50`
— definiti e mai usati dagli spec), `chartRenders`/`waitForChartRerender`
(`app-events.ts:109,115`), `forAllLanguages`/`DEFAULT_LANGUAGE` (`i18n-data.ts:86,91`),
`pageUntilVisible` (`paging.ts:40`), `exists` (`probe.ts:37`), `API_BASE`
(`fx/fx-helpers.ts:12`); tipi `AiExportDetailLevel` (`ai-export/helpers.ts:21`) e
`TestInfo` (`playwright.ts:337`). Stessa famiglia del vecchio I5: helper preparati "per
simmetria" e mai adottati.

---

## Cross-reference

- Fonte: [09_frontend_components.md archiviato](../../phases/05_cleanAudit/09_frontend_components.md)
- Decisioni LiveTicker/FxProviderConfig: [15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md) §"Le due scoperte" e lezione 3; [16_feature_perse_nei_redesign.md](../../phases/05_cleanAudit/16_feature_perse_nei_redesign.md) istanza 2
- Report gemelli: [08 — Stato & API](08_frontend_state_api.md) (H1 bandiere, H8 dipendenze, falso positivo istanbul), [10 — Grafici](10_frontend_charts.md) (conteggio `$:` per area)
