# Piano d'implementazione — K / Tassonomia e select

> **Origine.** Esegue le decisioni di [`analysis-phase00TaxonomySelect.md`](./analysis-phase00TaxonomySelect.md)
> (§2, D-K1…D-K5). L'analisi è la fonte dello stato verificato, delle superfici e dei conflitti.
> **Questo piano non ridecide**: dove diverge, lo dichiara come *Fuori pista*.
>
> Regola di avanzamento: dopo **ogni** passo si torna qui, si marca ✅ con data, si aggiunge
> `Note implementazione`, un `Fuori pista` per ogni deviazione, e il comando con l'evidenza.

| | |
|---|---|
| **Workstream** | K — tassonomia e select |
| **Worktree** | `LibreFolio-worktrees/e-alfy-improved-memory`, branch `e-alfy-k-tassonomia-e-select` |
| **Baseline** | `f1047f766` su `dev_release2` |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k` — **solo** `dev.py test …` |
| **Lane copia prod** | `--port 6165 --data-dir /tmp/librefolio-r2-k-prodcopy` — server, verifiche, review; **mai** un `dev.py test …` |
| **Autorizzato** | piano approvato dal developer il 2026-09-24 (plan mode della sessione K) |
| **Creato** | 2026-09-24 |

## Regole di esecuzione

- Preambolo sempre: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.
- Un comando di test alla volta nella lane. Mai `6040`/`6041`/`6042`/`5173`, mai `--force` sul server.
- Copia prod solo dallo snapshot `/tmp/librefolio-r2-prod-snapshot` con la procedura del coordinator
  (23/09); la vecchia copia va in `.prev-<data>`. Credenziali: dal coordinator, mai scritte qui.
- Nessuna migrazione Alembic. Nessun `git commit`/`push`/`merge`/`rebase`/`reset`.
- i18n solo via `dev.py i18n add`, sintassi ICU `{x}`. `CHANGELOG.md` non si tocca (voci in analisi §6).
- Test nuovi o riscritti: `test-author`, sulla test list approvata (§ Test list). Doc: `docs-writer`, solo EN.
- File condivisi: si aggiunge, non si riordina né si riformatta; elencati nell'handoff.

---

## Passi

- [x] **0. Il piano nel journal** — ✅ 2026-09-24
  > **Note implementazione**: creata `Phase_0/25_taxonomySelect/` (numero confermato dal coordinator:
  > la più alta era `24_privacyGlobal`) con `analysis-phase00TaxonomySelect.md` e questo piano,
  > copiati dal piano della sessione approvato dal developer.
  > **Fuori pista**: nel piano di sessione la tabella delle superfici era spezzata a metà
  > dall'inserimento della tabella i18n; qui le due tabelle sono separate. Nessun cambio di contenuto.

- [x] **1. Bootstrap della lane suite** — ✅ 2026-09-24
  - provare il guasto delle dipendenze frontend (`node_modules` assente) → chiedere `npm ci` al
    coordinator con l'errore in mano; `api sync` (in processo, non apre porte);
  - baseline **prima** di toccare codice: `front-utility core-unit`, `front-utility component-unit`,
    `front-asset asset-unit`, e gli E2E di §Test list colonna «regressione», per separare i rossi preesistenti.
  - DoD: baseline registrata qui con conteggi e rossi preesistenti nominati.
  > **Note implementazione** (2026-09-24, in corso):
  > - Guasto provato in sola lettura: `cd frontend && npm ls --depth=0` → `npm error missing: vitest@^4.1.0`,
  >   `vite@^7.3.5`, `typescript@^5.9.3`, `zod@3.24.1`, … (log `/tmp/libreFolio_k_npm_ls.log`).
  >   `npm ci` chiesto al coordinator con l'estratto.
  > - Baseline backend T13, lane suite: `dev.py test --test-port 6155 --data-dir /tmp/librefolio-r2-k
  >   services risk-all scenario_catalog` → **11 passed, 443 deselected** in 8.5 s
  >   (log `/tmp/libreFolio_k_back_baseline.log`). Porta 6155 libera dopo il run.
  > **Fuori pista**: `npx --no-install vitest --version` risponde `vitest/5.0.1`, cioè un binario della
  > cache npx globale, non la `^4.1.0` del lock: fuori da `node_modules` un `npx vitest` nudo userebbe
  > una major diversa. Non usato. L'ambiente ha `NODE_TLS_REJECT_UNAUTHORIZED=0` (warning di node):
  > segnalato al coordinator, non toccato. Il runner archivia il DB di test in `.testLog/00_archive/`
  > (ignorato da git, verificato con `git status -uall`).
  > **Correzione** (2026-09-24 12:15, verifica del coordinator): la lettura qui sopra era sbagliata.
  > vitest 5.0.1 non era già in cache: l'ha **scaricata proprio quel comando** (09:58). Con npm 11.19.1
  > sia `npx --no-install` sia `npm exec --no` interrogano comunque il registry, e installano nella cache
  > utente. Quel pacchetto è servito solo a leggere la versione, per nessuna misura. Tutte le misure
  > frontend di K sono successive a `npm ci` (10:47:49) e girano sui binari locali. I 9 log vitest
  > `/tmp/libreFolio_k_*.log` (10:49→12:05) stampano tutti `RUN v4.1.11`. In `frontend/node_modules`,
  > vitest 4.1.11, prettier 3.8.3, svelte-check 4.3.5, knip 6.31.0 e @playwright/test 1.61.0
  > coincidono con `package-lock.json`. Regola da qui in avanti: **mai `npx`**, con o senza opzioni.
  > Si usano `frontend/node_modules/.bin/<strumento>` oppure `npm run <script>`: se manca il binario
  > falliscono, invece di scaricare. Attenzione, il runner non rispetta la regola da solo:
  > `dev.py test front-*` lancia al suo interno `npx vitest` / `npx playwright`, e `front build` lancia
  > `npx svelte-check`, entrambi senza controllare che `node_modules` ci sia (solo knip lo controlla,
  > `dev.py:1845`). Quindi `dev.py` va lanciato su strumenti frontend solo dopo aver verificato che
  > `frontend/node_modules/.bin/<strumento>` esista. Segnalato al coordinator: il runner è una
  > superficie condivisa e non spetta a K correggerlo.
  > **Note implementazione** (2026-09-24, 10:48): via libera del coordinator → `cd frontend && npm ci`
  > (exit 0, solo dal lock, log `/tmp/libreFolio_k_npm_ci.log`; `package*.json` intatti); poi
  > `dev.py api sync` (exit 0; scrive solo `openapi.json`, `generated.ts`, `generated-tools.ts`,
  > ignorati — `git status -uall` senza voci nuove da api sync; l'enum generato contiene
  > `CROWDFUND_REAL_ESTATE`).
  > **Fuori pista**: la «baseline prima di toccare codice» non è più ottenibile per i file già
  > scritti durante l'attesa di `npm ci` (niente `git stash`: muta l'albero). Sostituita da
  > **mutazioni mirate**: ogni correzione viene disattivata a mano, i suoi test devono diventare
  > rossi, poi il file viene ripristinato e verificato identico. Per `SignalTreeSelect` la baseline
  > vera c'è: il file era ancora quello di `f1047f766` (hash blob identico) quando T0 è girato.

- [x] **2. R18 — il confronto aspetta il chooser e non ripete la domanda** — ✅ 2026-09-24
  - test rosso prima (T8, T9 via test-author), poi in `AssetModal.svelte`:
    - il confronto nato da una selezione di ricerca **non si apre** finché chooser, conferma di uscita
      o prompt di riuso della stessa selezione sono aperti: resta carico, in attesa;
    - risolto il chooser (conferma **o** uscita), si tolgono le righe che chiedono la stessa cosa
      (`identifier_<tipo>` con valore del provider fra i candidati del chooser) — anche se il probe
      arriva **dopo** la risposta; se non resta nulla, il confronto non si apre (nessun toast);
    - contesto provider cambiato o modale chiusa → l'attesa si scarta; «Chiedi al provider» manuale intatto.
  - regola pura in `components/assets/providerComparisonQueue.ts`.
  - DoD: T8, T9 verdi; `front-transaction tx-import-asset-inspector` verde.
  > **Note implementazione** (2026-09-24, in corso): `providerComparisonQueue.ts` scritto con l'API
  > dichiarata a test-author (`identifierQuestion`, `asksSameQuestion`, `pruneAnsweredRows`,
  > `decideComparison`), mentre test-author scrive T8/T9 in parallelo.
  > **Fuori pista**: T8 non potrà essere visto rosso (il modulo esiste già quando gira); il rosso
  > significativo di R18 è T9, sul `AssetModal` non ancora toccato.
  > **Note implementazione** (2026-09-24, codice scritto, test non ancora eseguiti — manca `npm ci`):
  > - test-author ha scritto T8 (28 test, `providerComparisonQueue.test.ts`) e T9 (nuovo describe in
  >   `AssetModal.providerLifecycle.test.ts`, 9 scenari con varianti: chooser, conferma di uscita,
  >   risposta prima del probe, edit con ISIN salvato, lettura manuale invariata, contesto scaduto per
  >   cambio bozza / fine sessione / chiusura del modale, prompt di riuso con e senza chooser).
  > - `AssetModal.svelte`: `applySearchResult` registra la domanda del chooser
  >   (`identifierQuestion(tipo, [provider, attuale])`) **dopo** `resetDraftReads` (che la
  >   cancellerebbe) e lancia la lettura come `fetchAndCompareMetadata('all', 'selection')`; il
  >   bottone «Chiedi al provider» resta `'manual'` e non pota nulla. A fine lettura:
  >   `decideComparison` → `open` / `hold` / `drop` (drop senza toast «tutto coincide»). Un `$effect`
  >   su `selectionPromptOpen` (chooser ∨ conferma di uscita ∨ riuso) rilascia il confronto trattenuto
  >   quando l'ultimo prompt si chiude, ricontrollando `open`, `saving` e `isMetadataCurrent` (che
  >   include sessione e sequenza). `resetDraftReads`, `reconcileProviderContext` e l'inizio di ogni
  >   nuova lettura scartano il trattenuto.
  > **Fuori pista**: T8 leggeva il contratto alla lettera — «le righe non identificative non
  > combaciano mai», anche con una domanda costruita a mano su `display_name`. `asksSameQuestion`
  > ora richiede `identifier_` nel campo. Residuo noto e **preesistente**, non di R18: se il probe
  > risponde *prima* della lista del riuso, il confronto si apre e il riuso gli arriva sopra; il
  > trattenimento copre i prompt aperti, non una ricerca ancora in volo.
  > **Evidenza** (2026-09-24, vitest diretto, nessun server):
  > - T8 + T9 + `AssetModal.test.ts` + select: 7 file, **180 verdi, 1 rosso** — il rosso è
  >   `drops a held comparison when the modal closes…`: una `GET /api/v1/assets/provider` non
  >   pianificata alla riapertura. Causa **preesistente, non R18**: alla riapertura il corpo del
  >   modale si ridisegna con lo stato vecchio (`providerExpanded` ancora vero) e monta per un istante
  >   `ProviderAssignmentSection`, che carica il catalogo prima che l'effetto di apertura resetti la
  >   bozza. Richiesta a test-author di pianificare quella lettura; il prodotto non si tocca (da
  >   segnalare nell'handoff come richiesta sprecata).
  > - Mutazione (`decideComparison` senza domande né prompt): **13 test R18 su 14 rossi**; quello
  >   verde è la lettura manuale, che per disegno passa prima e dopo. File ripristinato identico.
  >   Log `/tmp/libreFolio_k_units1.log`, `/tmp/libreFolio_k_t9_mutation.log`.
  > - test-author ha pianificato la lettura transitoria del catalogo alla riapertura (con due
  >   controlli di «bozza pulita» in più); rilancio: `AssetModal.providerLifecycle.test.ts`
  >   **37/37 verdi** (`/tmp/libreFolio_k_t9_rerun.log`).

- [x] **3. R13 — ordinamento a livelli (D-K5)** — ✅ 2026-09-24
  - test rosso prima (T1 con le 30 opzioni reali, T2, T10), poi `optionFilter.filterOptions` e il reset
    di evidenziazione/scroll in `SearchSelect`; misura di `CurrencySearchSelect` sui dati della copia prod.
  - DoD: «CSV» → «Generic CSV» prima riga ed evidenziata; T1, T2, T10 verdi; regressione R13-R verde.
  > **Note implementazione** (2026-09-24, codice scritto, test non ancora eseguiti — manca `npm ci`):
  > - test-author: T1 (nuovo `describe('ranking')` in `optionFilter.test.ts`, con le opzioni reali
  >   **lette dai sorgenti** `broker_*.py`, protette da soglia e àncore), T2 (4 test in
  >   `SearchSelect.test.ts`), T10 (E2E in `select-components.spec.ts`). Tutti già registrati.
  > - `optionFilter.filterOptions`: stesso insieme di risultati e stessa regola dei titoli, poi
  >   `rankWithinSections` — rango 0 prefisso, 1 inizio parola (dopo un carattere non `\p{L}\p{N}`,
  >   quindi anche `_`, che una `\b` avrebbe sbagliato), 2 sottostringa, 3 solo `searchText`/icona;
  >   il migliore fra valore ed etichetta, ogni occorrenza guardata; stabile; mai spostati i titoli;
  >   copia, mai l'array del chiamante. Query vuota: ordine sorgente.
  > - `SearchSelect`: un `$effect` sul **valore** della query (non sull'evento: il bottone «pulisci»
  >   cambia la query senza digitare) riporta l'evidenziazione sulla prima riga selezionabile e la
  >   lista in cima (`bind:this` sulla `listbox`).
  > **Evidenza** (2026-09-24): T1/T2 verdi insieme al resto (sopra). Mutazioni: senza ranking
  > **12 rossi** (11 in `optionFilter.test.ts`, incluso «Generic CSV primo» sulle opzioni reali, +
  > 1 in `SearchSelect`); senza reset sulla query **3 rossi**. Runner:
  > `dev.py test --test-port 6155 --data-dir /tmp/librefolio-r2-k front-utility core-unit` →
  > **90 file / 2436 test verdi**, 90 = file registrati (tutti esistenti). T10 (E2E) non ancora eseguito.

- [x] **4. R14 + R15 + R16 — una sola riscrittura** — ✅ 2026-09-24
  - 4a `assetTypes.ts`: `ASSET_TYPE_FAMILY` (sottotipo → contenitore), `ASSET_TYPE_CONTENT_ICON`,
    `assetTypeFamily()`, `buildAssetTypeTree()` al posto di `buildAssetTypeOptions()`; K2 invariato;
    docstring che registra D-K1 e risponde all'argomento di B.
  - 4b **caratterizzazione prima** (T0, verde sulla baseline); poi `ui/select/TreeSelect.svelte` con la
    meccanica spostata così com'è e i quattro assi come prop; `charts/SignalTreeSelect.svelte` ridotto ad
    adattatore; T0 resta verde **senza ritocchi**.
  - 4c icone composite: `scripts/compose_asset_type_icons.py` → 7 PNG (frontend + doc); `PNG_MAP` dei
    sottotipi puntato alle composite.
  - 4d `ui/select/AssetTypeSelect.svelte` + `AssetModal` (`testId="asset-modal-type"`).
  - gate esteso (T4–T6, test-author).
  - DoD: T0, T3–T7, T11 verdi; E2E segnali verdi; `ChartSignalsSection` diff zero.
  > **Note implementazione** (2026-09-24, in corso, in attesa di `npm ci`): creati, senza collegarli
  > a nulla, `ui/select/TreeSelect.svelte` (meccanica di `SignalTreeSelect` copiata alla lettera, poi
  > i quattro assi come prop), `ui/select/treeSelect.ts` (tipi) e `scripts/compose_asset_type_icons.py`.
  > `SignalTreeSelect.svelte` **non** è ancora toccato: diventa adattatore solo dopo che T0 è verde
  > sulla baseline. Differenze deliberate fra la copia e l'originale, tutte inerti per i segnali:
  > gruppi `inline` (i segnali non ne hanno), `showSelected` (default off), `defaultExpanded`
  > (`'first'` = il `groups[0]` di prima, quando nessun gruppo `inline` lo precede), prefisso degli id
  > DOM derivato da `testIdPrefix` (per i segnali resta `signal-tree-…`), testi di ricerca/vuoto come
  > prop (l'adattatore passa le chiavi `signals.selector.*`).
  > **Fuori pista (ordine)**: questi file nascono prima del passo 2 perché non dipendono dai test e
  > l'attesa di `npm ci` li rendeva gratuiti; nessun comportamento esistente cambia finché non sono collegati.
  > **Note implementazione** (2026-09-24, seguito, test non ancora eseguiti):
  > - test-author: T0 (`charts/SignalTreeSelect.test.ts`, 25 nomi / 28 casi) scritto sulla baseline;
  >   va eseguito **prima** di trasformare `SignalTreeSelect` in adattatore.
  > - 4a `assetTypes.ts`: `ASSET_TYPE_FAMILY` (esportata), `ASSET_TYPE_CONTENT_ICON` (privata, letta
  >   come testo dallo script e dal gate), `assetTypeFamily()`, `AssetTypeTreeItem`,
  >   `buildAssetTypeTree()`; rimossi `buildAssetTypeOptions` e `isEtfFamily`. Export chiesti da I
  >   invariati. `PNG_MAP` dei sottotipi → composite.
  > - 4c `compose_asset_type_icons.py` eseguito: 6 composite ETF in `frontend/static` e in
  >   `mkdocs_src/docs/static` (~40 KB l'una); `--check` verde; file non ignorati da git.
  > - 4d `AssetTypeSelect.svelte` (prefisso `asset-type-tree`, `showSelected`, `defaultExpanded:
  >   'selected'`, bordo da campo di form) e `AssetModal` (`testId="asset-modal-type"`); tolti
  >   `SimpleSelect` e `assetTypeOptions` dal modale. `TreeSelect` ha guadagnato `triggerBorderClass`
  >   (default = il bordo dei segnali). i18n aggiunte con `dev.py i18n add` (5 chiavi ×4, diff solo
  >   additivo: verificato che il re-dump dei cataloghi è identico al byte).
  > **Fuori pista**: l'ordine del menu ora segue **l'ordine dell'enum** (STOCK, ETF, BOND, …) con
  > ogni famiglia dove sta il suo contenitore: prima la famiglia ETF era in coda solo perché il titolo
  > di sezione di B doveva precederla. È un dettaglio di presentazione dentro la decisione A, da
  > confermare in review. Il test-author di T0 segnala comportamenti di `SignalTreeSelect` che
  > sembrano difetti (frecce che fanno il giro, Spazio che scrive uno spazio nella ricerca, focus che
  > cade su `<body>` dopo Esc) e che **non** ha fissato: la copia li conserva, per invarianza.
  > **Evidenza 4b** (2026-09-24): T0 sul `SignalTreeSelect` **originale** (blob = `f1047f766`) →
  > **28/28 verdi**; `SignalTreeSelect` riscritto come adattatore (≈50 righe: `SignalOptionContent`
  > come snippet, prefisso `signal-tree`, testi `signals.selector.*`) → T0 **28/28** senza ritocchi +
  > `ChartSignalsSection.test.ts` 13/13. Mutazioni su `TreeSelect`: primo gruppo non più aperto da
  > solo → 12 rossi; prefisso dei testid ignorato → 20 rossi. Ripristinato identico. Copia della
  > baseline in cartella di sessione. Log `/tmp/libreFolio_k_t0_*.log`.
  > **Evidenza 4a/4c/4d + gate** (2026-09-24): test-author ha scritto T3 (`TreeSelect.test.ts`),
  > T7 (`AssetTypeSelect.test.ts`), il gate esteso T4–T6 in `assetTypeTables.test.ts` (famiglie,
  > contiguità col contenitore in testa, titoli e suggerimenti ×4, invariante del colore, composite
  > `{contenitore}-{contenuto}` in app **e** in doc, regola D61 con l'eccezione D67 dichiarata,
  > comportamento di `buildAssetTypeTree`/`assetTypeFamily`, export stabili), più su mia richiesta
  > il gate di `ALL_ASSET_TYPES` della pagina asset e il `data-testid` del suggerimento. Risultato:
  > 3 file **78/78 verdi**. Mutazioni: `ETF_STOCK` di nuovo su `etf.png` → 1 rosso; famiglia ETF
  > sparsa → 3 rossi; colore di `CROWDFUND_REAL_ESTATE` diverso dal primario → 1 rosso; prefisso
  > delle righe cambiato → 6 rossi. Runner: `front-utility component-unit` → **77 file / 2076 verdi**
  > (77 = registrati); `front-utility onboarding-component-unit` → 12 / 395 verdi;
  > `front-asset asset-unit` → 16 file verdi, **1 rosso preesistente fuori perimetro** (vedi sotto).
  > E2E: `front-asset asset-modal` 17/17 (T11 compreso), `front-asset asset-list` 28/28 (T12 compreso).
  > **Fuori pista**: `chartCoreHelpers.test.ts` (dentro `asset-unit`) dà 12 rossi, tutti su
  > `GrowthChart.svelte` (di I): il test confronta il testo del componente con blocchi letterali.
  > `GrowthChart.svelte` e il test sono identici al byte a `f1047f766` → rosso preesistente, non K.
  > Segnalato al coordinator. Commenti corretti su indicazione dei due agenti:
  > `ASSET_TYPE_MENU_ORDER` (una famiglia sparsa fa smettere lo schermo di seguire l'array),
  > intestazione di `SearchSelect` (non «fuzzy»), `optionFilter` (tutte e 30 le descrizioni citano CSV,
  > 29 corrispondono solo lì), uso generico dello script.

- [x] **5. R17 — `CROWDFUND_REAL_ESTATE` (D-K3, D-K4)** — ✅ 2026-09-24
  - `models.py` enum + docstring **e** i due YAML (−0.10 / −0.10, col limite di Risk in commento) nello
    stesso commit; riga `AssetType` di `backend-db.instructions.md`; tabelle frontend, i18n ×4,
    `AssetTable`, `ALL_ASSET_TYPES`; `api sync`; seed E2E.
  - DoD: T12, T13 verdi; gate frontend verde.
  > **Note implementazione** (2026-09-24, backend fatto, frontend in attesa di `npm ci`/`api sync`):
  > - `models.py`: `CROWDFUND_REAL_ESTATE` + docstring (due famiglie con sottotipi; `CROWDFUND` è il
  >   residuo; la nuova voce contiene `REAL_ESTATE` ma negli stress è trattata come il prestito che è).
  > - `equity_crash.yml`, `global_risk_off.yml`: `CROWDFUND_REAL_ESTATE: -0.10` col limite di Risk in commento.
  > - T13: `dev.py test --test-port 6155 --data-dir /tmp/librefolio-r2-k services risk-all
  >   scenario_catalog` → **11 passed** (log `/tmp/libreFolio_k_back_r17.log`); porta 6155 libera.
  > - Frontend: `PNG_MAP`, `ASSET_TYPE_FAMILY`, `ASSET_TYPE_CONTENT_ICON`, `BADGE_CLASS_MAP` (teal),
  >   `PRIMARY_TYPE_MAP` (→ `REAL_ESTATE`), `ASSET_TYPE_MENU_ORDER`, `AssetTable` `enumOptions`,
  >   `assets/+page.svelte` `ALL_ASSET_TYPES`, i18n `assets.types.CROWDFUND_REAL_ESTATE` ×4, composita
  >   `crowdfunding-real-estate.png` (7 composite in tutto, `--check` verde).
  > - `backend-db.instructions.md`: riga `AssetType` e paragrafo sulle famiglie.
  > **Fuori pista**: `allocationHierarchy.ts` (di Risk/G) dice nel commento che nessun gruppo supera
  > `{puro, un sottotipo}`: con `CROWDFUND_REAL_ESTATE` Immobiliare arriva a 3 membri. Il codice
  > regge (sfumatura a profondità 2), il commento invecchia: da segnalare nell'handoff, non toccato.
  > **Evidenza frontend R17** (2026-09-24): enum generato da `api sync` con `CROWDFUND_REAL_ESTATE`;
  > T12 verde (vedi 4); `dev.py i18n audit`: nessuna traduzione mancante, «Likely Unused» fermo a
  > 422 e nessuna delle chiavi nuove fra queste.
  > **Evidenza backend dell'enum** (2026-09-24, lane suite): `services roi-fifo-utils
  > test_every_asset_type_uses_the_same_yield_on_cost_contract` (itera tutti i 18 tipi) → 1 passed;
  > `db validate` → 17 passed. Porta 6155 libera. Log `/tmp/libreFolio_k_back_enum.log`.
  > **Contratto per Risk** (chiesto dal coordinator, R12 rivista): `assetTypeFamily()` → `ETF` per i
  > sei `ETF_*`, `CROWDFUND` per `CROWDFUND_REAL_ESTATE`, sé stesso per basi e contenitori; stabile
  > nel round. Avvisato che normalizza come K2 (`'Liquidity'` → `'LIQUIDITY'`), a differenza di
  > `isEtfSubtype(t) ? 'ETF' : t`.

- [x] **6. Documentazione** (docs-writer, solo EN) — ✅ 2026-09-24
  - `developer/frontend/components/core-ui/select.md` (ranking, `TreeSelect`, `AssetTypeSelect`),
    `developer/frontend/components/features/asset-identity.md` (sequenza chooser → confronto);
  - `financial-theory/instruments/asset-types/index.en.md` riallineato alla tassonomia reale a due
    livelli, `real-estate.en.md`; IT/FR/ES = debito di traduzione dichiarato, nessuno stamp.
  - DoD: `mkdocs build` strict e `check-links` verdi; `translate-validate` riportato.
  > **Note implementazione** (2026-09-24): docs-writer, solo EN.
  > - `developer/…/core-ui/select.md`: diagramma rifatto (TreeSelect, AssetTypeSelect, adattatore
  >   segnali), «fuzzy» corretto in ricerca per sottostringa, sezione sul ranking, sezioni TreeSelect
  >   e AssetTypeSelect (composite e script); corretti di passaggio 4 errori preesistenti
  >   (endpoint di `ImportPluginSelect`, `FxProviderSelect` non basato su `SearchSelect`, due
  >   componenti che non esistono più, fonte dei broker di `BrokerSearchSelect`).
  > - `developer/…/features/asset-identity.md`: sequenza R18 (tabella di `decideComparison`), «quattro
  >   trigger» corretto in cinque.
  > - `financial-theory/…/asset-types/index.en.md` riscritto (11 tipi base con le etichette vere,
  >   tabelle delle due famiglie con le composite, vista contenitore/contenuto con $W_k$, stress);
  >   `real-estate.en.md` riscritto su `CROWDFUND`/`CROWDFUND_REAL_ESTATE`; `etfs.en.md` un
  >   rimando alla famiglia; `user/assets/create-edit.en.md` sezione «Choosing the Asset Type».
  > - `commodities.*.md`: la cella del codice diceva `HOLD` → `COMMODITY` in **tutte e quattro** le
  >   lingue (identificatore, non prosa) + `translate-stamp` della pagina EN.
  > - `mkdocs build` (strict) exit 0, `check-links` exit 0 (80 link validi, 3 🟡 già in eccezione);
  >   `translate-validate`: debito su `index`, `real-estate`, `etfs` (IT/FR/ES), dichiarato.
  > **Fuori pista**: R12 rivista da Risk (torta per **veicolo**, nel ramo di Risk) renderebbe falsa la
  > frase di `index.en.md` su quale vista usano i grafici di allocazione: chiesto a docs-writer di
  > tenere i due concetti e rimandare alla pagina dei grafici senza affermarlo. Lo screenshot
  > `assets/create-modal` della gallery mostra ancora il vecchio campo tipo (rigenerazione non di K).

- [x] **7. Gate integrati** — ✅ 2026-09-24
  - `front check`, lint/format frontend e backend sui file toccati, tutti i selettori della test list,
    `git diff --check`.
  > **Note implementazione** (2026-09-24, parziale):
  > - ruff + black su `scripts/compose_asset_type_icons.py` e `backend/app/db/models.py`: puliti.
  > - Prettier sui file di produzione K: 1 solo da riformattare, `AssetTable.svelte` — l'aggiunta di
  >   `CROWDFUND_REAL_ESTATE` ha spinto la riga oltre i 300 caratteri; riformattato (lo scrape del
  >   gate regge). Prettier sui test di test-author: 2 file riformattati (solo a capo).
  > - `dev.py front check` (svelte-check): **3 errori, 41 warning, tutti in 4 file fuori dal
  >   perimetro K e non toccati** (`BrokerSharingPanel.svelte`, `GlobalSettingsTab.svelte` warning;
  >   `TransactionFormModal.test.ts`, `ToolExecutionMetrics.svelte` errori). **Zero** diagnostiche nei
  >   file di K. Log `/tmp/libreFolio_k_front_check.log`.
  > - Rilancio finale: `git diff --check` pulito; Prettier su tutti i 23 file frontend toccati pulito;
  >   `dev.py lint --dead-code --scope frontend` (knip): **zero** reperti nei file di K, dopo aver tolto
  >   dal barrel `ui/select/index.ts` `TreeSelect` e i due tipi (knip li dava inutilizzati: i
  >   consumatori importano per path; `AssetTypeSelect` resta nel barrel). `i18n audit`: nessuna mancante.
  > - **E2E, lane suite** (`/tmp/libreFolio_k_e2e_round1.log`, `…round2.log`):
  >
  >   | spec | esito | verdetto |
  >   |---|---|---|
  >   | `front-utility select` | 17/17 (T10 compreso) | ✅ |
  >   | `front-asset asset-modal` | 17/17 (T11) | ✅ |
  >   | `front-asset asset-list` | 28/28 (T12) | ✅ |
  >   | `front-fx fx-detail` | 17/17 (`signal-tree-option-rsi`) | ✅ |
  >   | `front-utility onboarding-tour` | 10/10 (broker cercato + Invio) | ✅ |
  >   | `front-asset asset-classification` | 3/3 (paese/settore) | ✅ |
  >   | `front-transaction transactions-modals` | 19/19 | ✅ |
  >   | `front-asset asset-merge` | 3/3 (`AssetSelect`) | ✅ |
  >   | `front-utility utilities` | 16/16 (valuta) | ✅ |
  >   | `front-portfolio risk-lab` | 11/11 (sezioni K3) | ✅ |
  >   | `front-asset asset-detail` | 27/28 — rosso `calendar-return primary mode…`, **deterministico** | ambiente: precondizione di fixture legata alla data («MAX standalone FX-sync range 2026-08-10..2026-09-24 contains no ready-peer event fixture»); i test dei segnali dello stesso spec (`signal-tree-group-risk`, …) sono verdi. Non K |
  >   | `front-transaction tx-import-asset-inspector` | 4/5 — `E2-001` **intermittente** (rosso nel lotto, verde da solo, verde/rosso in due rilanci) | preesistente e documentato: `B-esecuzione.md` §matrice causale (4 rossi su 5 con `AssetModal` di baseline) e `STATO.md:706`; `optionsClosed()` è soddisfatto da una tendina aperta ancora vuota. Non K |
  >   | `front-transaction tx-import-resolution` | 11/12 — `IWR-006` **deterministico** | assunzione del test: il coachmark della guida import di J (`import.review`, z 83) intercetta il click sull'opzione; lo spec è del 16/08, la guida contestuale del 14/09, gli altri spec di import la gestiscono. Non K |
  >
  >   Nessuno dei tre rossi tocca un file o un comportamento di K (posizione della prima riga
  >   invariata dal ranking; `optionsClosed` e coachmark indipendenti). Segnalati al coordinator.

- [ ] **8. Review sulla copia prod e handoff** — ⏳ server di review acceso, in attesa del developer
  - copia rinfrescata dallo snapshot, server `6165`, test list manuale col developer;
  - poi spegnimento, `lsof -nP -iTCP:6155 -sTCP:LISTEN` e `…:6165…` vuoti, `FROZEN`, handoff
    (delta, esclusioni, evidenze, conflitti, CHANGELOG proposto, messaggio di commit).
  > **Note implementazione** (2026-09-24, 12:00–12:08):
  > - Copia creata dallo snapshot del coordinator (`/tmp/librefolio-r2-prod-snapshot`, 004, senza
  >   marcatore), `dev.py front build` fresco, server `--test --port 6165 --data-dir
  >   /tmp/librefolio-r2-k-prodcopy`: health 200, le composite servite (`etf-stock.png` 200).
  > - **Verifiche sui dati del developer** (API, sola lettura salvo un esperimento):
  >   - 15 asset: 8 `ETF`, 4 `CROWDFUND`, 1 `ETF_STOCK`, 1 `ETF_BOND`, 1 `BOND`;
  >   - catalogo scenari servito: `CROWDFUND_REAL_ESTATE` −0.10 in entrambi, come `CROWDFUND`;
  >   - R13 col vero `optionFilter` sulle liste **servite**: plugin «CSV» → Generic CSV da 16° a
  >     **1°**, «crypto» → Crypto.com da 4° a 1°; valute (IT) «us» → **USD da 7° a 1°** (era il
  >     rischio «probabile» dell'audit), «eur» e «€» già primi. «franco», «dollaro», «sterlina»
  >     restano in ordine alfabetico fra pari (tutte le valute con quel nome sono inizio parola):
  >     limite noto, non difetto — «usd»/«chf»/«gbp» vanno primi per codice
  >     (log `files/r13_prodcopy_ranking.log` in cartella di sessione);
  >   - **esperimento** (poi scartato): `PATCH` dell'asset 12 (un crowdfunding del developer) a
  >     `CROWDFUND_REAL_ESTATE` → 200, riletto uguale dall'API, 21 caratteri salvati in una colonna
  >     che sul DB installato è ancora `VARCHAR(14)`: su SQLite la larghezza è inerte, provato sui
  >     dati veri.
  > - Server fermato, copia **rinfrescata** (quella dell'esperimento spostata in
  >   `.prev-20260924-120604`, asset 12 di nuovo `CROWDFUND`), server riavviato sulla copia pulita:
  >   health 200. Porta 6155 (suite) libera. Cookie e JSON coi dati del developer cancellati da `/tmp`.
  > - Ultimo giro dei test di K dopo le ultime modifiche (vitest diretto): 10 file, **276/276 verdi**.
  > **Da fare**: la test list manuale col developer (sotto); poi spegnimento, porte provate libere,
  > `FROZEN`.

---

## Test list (approvata dal developer con il piano)

**Automatici** — scritti da `test-author`

| # | livello | cosa prova | file / selettore |
|---|---|---|---|
| T0 | componente | caratterizzazione `SignalTreeSelect`, verde sulla baseline: `${testId}-button`, `signal-tree-group-*` con `aria-expanded`, `signal-tree-option-*`, primo gruppo aperto all'apertura, ricerca che apre tutto e appiattisce la navigazione, tastiera (↑ ↓ Home End Invio → ←), `flat`, trigger col placeholder, `onchange` | nuovo `SignalTreeSelect.test.ts` · `front-utility component-unit` |
| T1 | unit | ranking: livelli, stabilità, sezioni e header intatti; le 30 opzioni reali: «CSV» → Generic CSV in testa | `optionFilter.test.ts` · `front-utility core-unit` |
| T2 | componente | `SearchSelect`: nuova query → evidenziata la prima, lista in cima; resto invariato | `SearchSelect.test.ts` · `front-utility component-unit` |
| T3 | componente | `TreeSelect`: gruppi `inline`, `showSelected` + `selectedItem`, `defaultExpanded: 'selected'`, prefisso testid, snippet di contenuto, testi di ricerca e vuoto | nuovo `TreeSelect.test.ts` |
| T4 | unit | gate esteso: famiglie contigue e guidate dal contenitore, invariante colore `badge(x) = badge(primario(x))`, titolo di famiglia ×4 | `assetTypeTables.test.ts` · `front-asset asset-unit` |
| T5 | unit | `buildAssetTypeTree` (gruppi `inline` + famiglie ETF e Crowdfunding, generici come prima voce), `assetTypeFamily`, export stabili | `assetTypeTables.test.ts` |
| T6 | unit | ogni sottotipo ha una composita `{contenitore}-{contenuto}.png` su disco; contenuto = icona del primario salvo D67 (`ETF_MONETARY` → `liquidity`) | `assetTypeTables.test.ts` |
| T7 | componente | `AssetTypeSelect`: righe con icona composita, emette il valore | nuovo `AssetTypeSelect.test.ts` |
| T8 | unit | regola R18 pura: attesa, potatura, vuoto → nulla, contesto scaduto → scarto | nuovo `providerComparisonQueue.test.ts` · `core-unit` |
| T9 | componente | R18 nel modale: chooser aperto → probe risolto → nessun confronto; conferma → confronto senza riga ISIN o nessun confronto; uscita → idem; risposta prima del probe → idem | `AssetModal.providerLifecycle.test.ts` |
| T10 | E2E | broker form: «CSV» → `search-select-option-broker_generic_csv` evidenziata e visibile | `select-components.spec.ts` · `front-utility select` |
| T11 | E2E | modale asset: espandi `asset-type-tree-group-ETF`, scegli `asset-type-tree-option-ETF_STOCK`, salva; la card mostra `etf-stock.png` | `asset-modal.spec.ts` · `front-asset asset-modal` |
| T12 | E2E | round trip tassonomia: `ETF_STOCK` → `etf-stock.png` (l'assert «condivide `etf.png`» riscritto), seed `CROWDFUND_REAL_ESTATE` → `crowdfunding-real-estate.png` | `asset-list.spec.ts` · `front-asset asset-list` |
| T13 | backend | gate secchi ↔ enum | `test_risk_scenario_catalog.py` · `services risk-all` filtrato |
| R | regressione | segnali invariati (F8), inspector import, onboarding | `front-asset asset-detail`, `front-transaction tx-import-asset-inspector`, `front-utility onboarding-component-unit` |
| R13-R | regressione | tutti i consumatori di `filterOptions` (tabella sotto) + `SimpleSelect` | vedi tabella |

**R13 — consumatori di `filterOptions`.** Solo `SearchSelect` lo chiama; `SimpleSelect` usa i soli
helper di navigazione, che restano invariati.

| primitivo | dove si vede | copertura automatica esistente | sonda manuale sulla copia prod |
|---|---|---|---|
| `SearchSelect` diretto | `ChartSignalsSection` (coppia FX e asset di confronto), `FixFlaggedStep`, `ImportAssetPicker`, `TransactionTypeSearchSelect` | `SearchSelect.test.ts`; E2E `asset-detail`, `fx-detail`, `tx-import-resolution` | confronto «msci»; import step 4: un ISIN e un nome parziale; tipo transazione «div» |
| `ImportPluginSelect` | `BrokerForm`, `ImportWizardModal` (cella step 1) | `select-components.spec.ts` | «CSV», «csv», «generic», «crypto» |
| `CurrencySearchSelect` | `AssetModal`, `AssetPriceSummary`, `ProviderAssignmentSection`, `ScheduledInvestmentEditor`, `BrokerForm`, `FxDataImportModal`, `FxPairAddModal`, `SettingCurrency`, `DataTableColumnFilter`, `CompactCashCell`, pagine assets / brokers / brokers/[id] / dashboard / fx | `CurrencySearchSelect.test.ts`; E2E `select-components`, `asset-modal`, `utilities` | «us», «eur», «€», «franco» |
| `CountrySearchSelect`, `SectorSearchSelect` | `DistributionEditor` (classificazione) | E2E `asset-modal`, `asset-classification` | paese «it», settore «tech» |
| `BrokerSearchSelect` | `ImportWizardModal`, `TransactionFormModal`, pagina files | E2E `onboarding-tour`, `transactions-modals` | un nome parziale di broker |
| `UserSearchSelect` | `BrokerSharingPanel` | `BrokerSharingPanel.test.ts` | un username parziale |
| `AssetSelect` (sezioni K3) | `AssetMergeModal`, `SignalAssetParamControl`, `AssetSetRiskPanel`, `L3Benchmark`, `ImportWizardModal`, `TransactionFormModal` | E2E `risk-lab`, `asset-merge`, transazioni | benchmark «world»: le sezioni restano, dentro la sezione il nome vince |

**Manuali sulla copia prod (porta 6165)**

1. Nuovo broker → plugin: «CSV», «csv», «generic», «crypto»; Invio sceglie la prima. Stesso giro sul select valuta («us», «eur»).
2. Nuovo asset → tipo: gruppi chiusi, apri ETF, scegli «ETF azionario»; cerca «immob» → Immobiliare, ETF immobiliare, Crowdfunding immobiliare; solo tastiera.
3. Pastiglia ovunque su un asset `ETF_*` senza icona personalizzata, tema chiaro e scuro: `AssetIcon`
   (card, modale, ricerca asset, dettaglio asset, custodia lotti); badge di tipo (card, tabella asset,
   dettaglio, ricerca asset); filtro tipi della lista asset; righe di `AssetSelect` e `ImportAssetPicker`;
   celle asset di tabella transazioni, bulk e import wizard; messaggi di validazione; `PageSyncModal`;
   selettore asset dei segnali di confronto e loro legenda; dashboard (legenda torta allocazione, tabelle
   esposizione e contributi, treemap). Con icona personalizzata: nulla cambia.
4. Riclassifica un Recrowd in «Crowdfunding immobiliare»: badge, filtro della lista, torta allocazione (dipende da R12 di Risk), stress.
5. Import con BTP Più → crea asset → cerca: il chooser appare **da solo**; dopo la risposta il confronto arriva senza la riga ISIN, o non arriva.
6. Pannello segnali: il selettore indicatori è identico a prima.
