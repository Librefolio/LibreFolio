# L — Designer Lab · analisi di implementazione (14/10/2026)

> Stato: **FERMO**: solo analisi. Nessun file del repo modificato, nessun server avviato, nessun test lanciato, nessun `npm ci`.
> Il piano nel repo (`55_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md`) si crea solo dopo
> l'autorizzazione del developer.

## Identità della corsia

| Voce | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-fuzzy-robot` |
| Branch | `e-alfy-designer-lab` (rinominato dall'app, era `e-alfy-fuzzy-robot`) |
| HEAD | `b631308d5ef5482a8ffdc2878a4459fcf6909827` = base del kickoff ✓ (dopo il ff del coordinatore) |
| Destinazione | `dev_release2` @ `b631308` |
| Corsia | porta 6152 (libera), dati `/tmp/librefolio-r2-l` |
| Coordinatore | `aec04834-1532-4d86-9e3f-f942e82aca89` |
| Ambiente | Node v26.11.1, npm 11.20; Chromium di Playwright in cache; `node_modules`, `.env` e graphify assenti (atteso: wiki letta direttamente) |

## 1. Stato attuale verificato (claim del §1 contro il codice)

| Claim del progetto | Verdetto | Evidenza |
|---|---|---|
| Esiste una build di debug | ✅ | `package.json` `build:debug`; `dev.py:643`; `src/lib/debug.ts` |
| Il server di test usa sempre il debug | ✅ | `dev.py:199` (`debug_mode = True`); marcatore `dev.py:2086`; i run di coverage aggiungono istanbul (`playwright.config.ts` passa `COVERAGE_INSTRUMENT` al webServer) |
| Il frontend conosce il commit | ✅ | `vite.config.ts` `define.__APP_VERSION__`; dichiarazione in `src/lib/version.ts:9` (non in `app.d.ts`) |
| Le classi Tailwind leggono variabili a runtime | ⏳ da riverificare nello spike | manca la build (niente `node_modules`) |
| 17 grafici ridisegnano a **qualunque** cambio di classe su `<html>` | ❌ **parziale** | vedi la tabella qui sotto |
| ECharts importato direttamente, nessun modulo centrale | ✅ (29 file, 25 non di test; **tutti** da `'echarts'`, nessun `echarts/core`): un solo prototipo `ECharts` | grep degli import |
| 1.821 colori scritti a mano | ✅ come totale: hex 1.610 + funzioni 211 | `analysis/00_inventory_summary.md`; `frontend/src` è identico tra `6d0b126` e `b631308` |
| Ripartizione per zona (1.084/69/533/118/17) | ⚠️ non riproducibile | `color_inventory.py` scorre le righe con le regex e **non classifica le zone** |

**Osservatori del tema (verificati):**

| Comportamento | Componenti | Effetto del «tick» di classe |
|---|---|---|
| `renderChart()` incondizionato | LineChart:170, CandlestickChart:145, PriceChartFull:257, GeographyMap:103, AllocationPieChart:118, ExposureTreemap:92, GrowthChart:1999, AllocationHistoryChart:188, PerformanceChart:1116, LotComparisonChart:1259, LotGanttChart:1333, LotWacPriceChart:1714 | ✅ ridisegna (12) |
| Assegnano soltanto `dark = classList.contains('dark')` a un `$state` | ScatterChart:82, CorrelationHeatmap:296-300, ExposureBars:44-48, ExposureMaps:96-100 | ❌ valore uguale → nessun ridisegno (4) |
| Nessun osservatore | SemiDonutChart | ❌ (1) |
| Non è un osservatore del tema | OtherPeriodEffectsTable:208 (`data-row-id` sulla tabella) | — (il report 04 lo conta per errore) |

**Altri fatti emersi:**
- `/designer-lab` in release: il backend risponde **HTTP 200** con `200.html` (`backend/app/main.py:494-524`), poi SvelteKit disegna `+error` lato client. Il «404 su `/designer-lab`» del §3.2/§9 è un 404 **client** e `+error.svelte` non ha `data-testid`. Gli E2E girano solo in debug, quindi la release si prova con un test unitario su `+page.ts` più la guardia di build.
- Il layout radice è legacy (`$:`), con `ssr=false` e i figli montati solo dopo il caricamento di i18n. Il client del Lab va importato in `onMount` con `.catch()` (c'è anche lo spec offline).
- `app.css:224-228`: `html.dark input,select,textarea` è fuori dai layer, senza `!important`, specificità (0,1,2). Il CSS con scope dei componenti (0,2,0) vince, quindi il Lab resta isolato se non usa classi colore Tailwind.
- Gate che leggono **tutti** i sorgenti di `src`, Lab compreso: `documentTitle.guard` (nessuna scrittura del titolo), `htmlSink.gate` (`{@html}` vietato senza `sanitizeHtml`), `htmlInterpolation.gate`, `clipboardSink.gate` (solo `writeTextToClipboard`), `flagFont.gate` (nessun font emoji).
- `knip.json`: progetto `src/**` + `e2e/**`. Il modulo `virtual:` può risultare irrisolto: da verificare nello spike.
- La guardia Docker (`scripts/docker/check_frontend_build.sh`) rifiuta già le build di debug. Il Lab resta comunque fuori dalle immagini per costruzione.
- `check_frontend_needs_build` (`scripts/cli_base.py:542-585`) guarda `src/` e la config, non `frontend/scripts/designer-lab/`. Se cambia solo lo scanner non c'è rebuild: serve `--rebuild`.
- La registrazione nel runner è esplicita (`scripts/test_runner/_registry.py`, liste di file per azione) e il nav di MkDocs è esplicito (`mkdocs.yml`): entrambe sono superfici condivise.

## 2. Cosa regge e cosa va corretto

**Regge:** il gating con `define` più `import()` dinamico, la rotta fuori da `(app)`, il plugin con modulo virtuale, L1 su `html` con `!important` per `@theme`/`:root` e `--theme-*`, la riscrittura CSSOM per L2, la patch del prototipo di `setOption` (un solo modulo `echarts`), localStorage, l'export JSON+MD, `verify-export`, le decisioni del §11.

**Da correggere o rischioso:**
1. **Ridisegno L3 (§5.3).** Il tick di classe aggiorna 12 componenti su 17. Proposta: **ri-applicazione dal vivo**, indipendente dai componenti:
   - istanze trovate con `[_echarts_instance_]` + `echarts.getInstanceByDom`;
   - `getOption()` → patch sparsa con i soli colori → `setOption` in merge;
   - il wrapper del prototipo copre le chiamate future.

   Il tick diventa facoltativo. Regge anche se R sostituisce gli osservatori con `themeRevision`. Lo spike decide.
2. **Portata reale di L3 < 571.** Restano senza anteprima:
   - i colori derivati prima di `setOption` (`shadeForDepth`, `pnlColor`, `getIndexColor`, `lotColor`);
   - i colori usati nel markup Svelte dei componenti grafico.

   Proposta: un indice «visto dal vivo» per valore (CSSOM, `setOption`) mostrato dal Lab, per onestà.
3. **Variabili CSS definite nei componenti** (oggi poche; R-3 le moltiplica): un override su `html` non vince sulla definizione dell'elemento. Il catalogo registra il selettore di definizione; se non è `:root`/`html`, la variabile si modifica via CSSOM come in L2.
4. **Serializzazione CSSOM:** Chrome restituisce `rgb()` al posto dell'hex ed espande le shorthand. Il confronto si fa sul colore parsato (RGBA), mai sulla stringa. Varianti con alfa (es. `rgba(30,41,59,.95)` di P1 accanto a `#1e293b`): opzione «includi varianti alfa», attiva di default, che conserva l'alfa come L3.
5. **Neutralità più forte:** il client sempre caricato è minimo:
   - controlla la chiave in localStorage e ascolta l'evento `storage`;
   - motori L1/L2/L3 e `echarts` in chunk separati, caricati solo se ci sono modifiche;
   - nessun BroadcastChannel o osservatore da inattivo.

   Il Lab non cambia un pixel, ma aggiunge un piccolo chunk a ogni pagina di debug (anche negli E2E).
6. **Isolamento del Lab:** i colori della UI del Lab vengono solo da `--lab-*`, definite in un `<style data-lf-lab-own>` che i motori saltano. Niente classi colore Tailwind nel Lab; le variabili `--lab-*` non sono modificabili.
7. **Dichiarazione del modulo virtuale:** `app.d.ts` è un modulo (`export {}`), quindi `declare module 'virtual:…'` non funziona lì. Serve un `.d.ts` ambient in `src/lib/dev/designer-lab/`. In `app.d.ts` vanno `__LF_DESIGNER_LAB__` e `Window.__lfDesignerLab` (hook per gli E2E).
8. **Branch del template:** meglio `if (__LF_DESIGNER_LAB__)` nello `<script>` + `import()`, che Rollup elimina con certezza, invece di `{#if}{#await import()}` nel markup. `+page.ts` dà già 404 in release.
9. **Passo 5:** la DoD «export applicato da un agente con diff della gallery» cambierebbe l'aspetto dell'app, vietato a L. Proposta: round trip export/import, `verify-export` con occorrenze spostate e sparite, prova a secco della skill (elenco di modifiche, senza applicarle). L'applicazione vera spetta a chi cambia l'aspetto, dopo il report della designer.
10. **Spike «su ramo usa e getta»:** a L sono vietate le operazioni git. Lo spike usa solo file temporanei nei percorsi di L, cancellati alla fine, e gli edit temporanei a file tracciati si ripristinano a mano (`git diff` vuoto).
11. **Neutralità A/B in un solo worktree:** `define` accetta l'override d'ambiente `LF_DESIGNER_LAB=0|1`, così la gallery dello stesso giorno confronta Lab off contro Lab on sullo stesso commit. Tra le due esecuzioni si cancella `frontend/build/`, perché il controllo di staleness non vede il cambio di env.
12. `scripts/visual_review/designer_live.sh --debug` è ridondante: `--test` forza già il debug. Il Lab sarà già sulla 6160. È un ritocco al README, del coordinatore.

## 3. Superfici esatte

**Nuove (di L):**
- `frontend/scripts/designer-lab/`:
  - `scan-colors.mjs` (scanner, CLI, API);
  - `vite-plugin.mjs` (modulo virtuale, invalidazione in dev, guardia di release in `generateBundle`);
  - `verify-export.mjs`.
- `frontend/src/lib/dev/designer-lab/`:
  - `client.ts` (bootstrap minimo);
  - `engine/{vars,stylesheets,charts}.ts`;
  - `store.ts` (stato v1, varianti);
  - `color.ts` (parse, OKLCH↔sRGB, gamut, WCAG);
  - `cvd.ts`;
  - `export.ts`;
  - `i18n.ts` (IT/EN);
  - `DesignerLab.svelte` e componenti;
  - `virtual-catalog.d.ts`;
  - test `*.test.ts` e gate `designerLabImports.gate.test.ts`.
- `frontend/src/routes/designer-lab/+page.ts` e `+page.svelte`.
- `frontend/e2e/designer-lab/designer-lab.spec.ts`.

**Modifiche minime (di L):**
- `frontend/vite.config.ts`: `({mode, command})`, `define.__LF_DESIGNER_LAB__` con override d'env, plugin, `exclude` di istanbul per `src/lib/dev/**` e `src/routes/designer-lab/**`;
- `frontend/src/routes/+layout.svelte`: una riga in `onMount`;
- `frontend/src/app.d.ts`: costante globale + `Window.__lfDesignerLab`.

**Condivise, serve un'assegnazione del coordinatore:**

| Superficie | Perché |
|---|---|
| `scripts/test_runner/_registry.py` + nuovo `_frontend_designer_lab.py` (oppure azioni in `_frontend_utility.py`) | registrazione di Vitest ed E2E (`test-author`) |
| `mkdocs_src/mkdocs.yml` (una riga di nav) + nuova `mkdocs_src/docs/developer/frontend/designer-lab.md` | pagina developer (`docs-writer`) |
| `.github/skills/<gruppo>/designer-lab-apply/SKILL.md` | skill per l'agente: gruppo da decidere |
| `scripts/visual_review/color_inventory.py` | escludere le cartelle del Lab, così l'inventario non cambia; poi la decisione 4 |
| `frontend/scripts/js-coverage-report.js` (facoltativo) | escludere il Lab dal report combinato |

**Non toccate:** `app.css`, i componenti e gli helper dei grafici (R), `gallery.spec.ts` e le fixture (G), `dev.py`, `scripts/cli_base.py`, `vitest.config.ts` (i test del Lab stanno in `src/**`).

## 4. Decisioni aperte del §11, con raccomandazione

| # | Decisione | Raccomandazione L |
|---|---|---|
| 1 | URL e accesso | `/designer-lab` **senza login**: build di debug, solo client (nessuna API), dati di test. `/__lab` non aggiunge nulla |
| 2 | Lingua | **IT + EN** con dizionario locale fuori dal catalogo i18n; scelta da `$locale` (it → IT, altrimenti EN). Chiavi ed export JSON in inglese; MD nella lingua del Lab |
| 3 | Destinazione dell'export | **Solo download** nella v1, più «copia riassunto» con `writeTextToClipboard`. Il salvataggio sul server richiede il backend, fuori dal perimetro: v2 nel backlog |
| 4 | Fonti dello scanner | **Una fonte (JS)** per il catalogo. Parità con il Python dimostrata una volta al passo 1 (conteggi identici). `color_inventory.py` diventa un lettore del JSON in un passo separato, con perimetro esteso o fatto dal coordinatore |
| 5 | Granularità predefinita dei fogli di stile | **Per valore** (con varianti alfa); per occorrenza come approfondimento, solo dove il selettore combacia dal vivo |
| 6 | Campionario | **Dopo la v1** (backlog) |
| 7 | Ordine rispetto ai token | **Lab v1 prima dei token** |
| N1 | Meccanismo di ridisegno dei grafici | **Ri-applicazione dal vivo** (`getOption` + patch sparsa) come base, tick facoltativo; esito dello spike |
| N2 | Superfici condivise (tabella del §3) | assegnazione esplicita a L, tramite i sotto-agenti |
| N3 | DoD del passo 5 | senza applicazione reale (vedi §2.9) |
| N4 | Neutralità della gallery | A/B `LF_DESIGNER_LAB=0/1` nello stesso giorno sulla 6152; gallery intera una volta sola alla fine (31–34 min ×2), oppure filtrata (EN, desktop+mobile) se il coordinatore preferisce |

## 5. Conflitti previsti

**Con R:** nessun file in comune. Accoppiamenti semantici:
- R-1 può sostituire gli osservatori con `themeRevision`: per questo N1, ed eventualmente un evento dev-only su cui concordare un contratto;
- R-3 crea variabili con scope di componente: vedi §2.3;
- R sposta colori tra file e righe: il catalogo si rigenera a ogni build e `verify-export` li ritrova per valore;
- un futuro gate «niente hex fuori dai token» deve esentare le cartelle del Lab, oppure il Lab tiene la palette in un solo file in eccezione.

**Con G:** nessun file in comune. La neutralità di L si misura con la gallery, quindi le correzioni di G cambiano la base, ma l'A/B di L è sullo stesso commit e nella stessa sessione. Rischio solo se G tocca `routes/+layout.svelte`: da segnalare.

**Con T (in futuro):** nessuno, perché L non tocca `app.css`.

## 6. Complessità e rischi

Complessità complessiva **medio-alta**. Il passo più rischioso è il 3 (motore).

| Rischio | Mitigazione |
|---|---|
| Ridisegno L3 e stato d'interazione (zoom) quando si riapplicano le opzioni | patch sparsa con i soli colori; misura nello spike |
| Portata di L3 e colori derivati | indice «visto dal vivo»; limite dichiarato |
| Collisioni per valore (P5, CSS di terze parti) | modalità per occorrenza; elenco delle regole toccate |
| Variabili con scope (R-3) | percorso CSSOM |
| Serializzazione e shorthand del CSSOM | confronto sul colore parsato; spike |
| Neutralità (chunk extra, rigetti offline, console) | bootstrap minimo, `.catch`, nessun log; asserzione E2E |
| Perdita in release | eliminazione del ramo, guardia del plugin, gate, grep sulla build di release |
| Gate esistenti del repo | regole di scrittura del Lab (§1) |
| Superfici condivise | §3, assegnazione |
| Catalogo da circa 1 MB in debug, tempo dello scanner, invalidazione in dev | chunk solo per il Lab; cache per file |
| Lampo dei colori originali al ricaricamento: il client parte dopo il primo render | accettato in debug, documentato |
| Gamut: OKLCH contro sRGB | slider OKLCH, avviso fuori gamut |
| Ambito del tema nell'export (regola comune ai due temi) | campo `theme_context` per occorrenza |

## 7. Passi ordinati con definition of done

| Passo | Contenuto | DoD |
|---|---|---|
| **0. Spike** | `npm ci` (pre-approvato); prototipo dello scanner cronometrato; DB della corsia (`test db populate --force --clean` su `/tmp/librefolio-r2-l`); build di debug + server sulla 6152; file temporanei nei percorsi di L. Misure: riscrittura CSSOM di un valore di `DataTable` su `transactions`; patch di `setOption` con tick contro ri-applicazione su GrowthChart, ScatterChart o CorrelationHeatmap, SemiDonutChart; `lint:dead` con `virtual:`; classi Tailwind leggono le variabili sul CSS compilato | misure nel piano, scelta di N1; `git diff` del repo vuoto a fine spike; server fermo e porta libera |
| **1. Scanner + CLI** | `scan-colors.mjs`, schema `lf-color-catalog/1`: zone, selettori, ambito di tema, indizi grafici, `by_value` (RGB opaco con varianti alfa), `css_vars` con selettore di definizione, `palette`→`--color-*`, `meta`. Esclusi test, file generati e cartelle del Lab; zona L4 extra (`app.html`, `offline.html`, `manifest.json`) | Vitest verde; **parità** sullo stesso albero: hex 1.610, funzioni 211, classi palette 10.682, token custom 795, arbitrari 12, `var()` 84, definizioni 86; tempo ≤ 2 s |
| **2. Interruttore e rotta** | `define` + override d'env, plugin, `exclude` di istanbul, `app.d.ts` + `.d.ts` ambient, rotta stub, riga nel layout, gate test, guardia di release | build di release senza chunk del Lab né marcatore (guardia + grep, evidenza); la build di debug serve `/designer-lab` col catalogo; `svelte-check` a 0; `lint:dead` senza nuovi problemi; gate esistenti verdi |
| **3. Motore dal vivo** | client minimo; L1 (html + variabili con scope via CSSOM), L2 (CSSOM, fogli caricati dopo, ripristino), L3 (wrapper + N1), persistenza v1, sincronizzazione tra schede (`storage`), sospendi/ripristina, ricalcolo al cambio di tema, hook E2E | modifica visibile in un'altra scheda per L1, L2 e L3 su 3 pagine di riferimento; il ripristino torna esattamente all'originale; con storage vuoto nessun effetto (nessuno stile iniettato, prototipo intatto) |
| **4. Interfaccia** | sezioni, editor OKLCH, contrasto (tema corrente dal vivo, l'altro dal catalogo), daltonismo (filtro su `html`), note e codici schermata, varianti A/B, IT/EN, isolamento | accettazione dal vivo con la designer o il developer su `designer_live.sh` (6160): passo esterno |
| **5. Export e agente** | JSON + MD, import, `verify-export.mjs`, skill (se assegnata) | round trip identico; `verify-export` segnala correttamente spostati e mancanti; prova a secco della skill |
| **6. Test, documentazione e neutralità** | Vitest + E2E smoke registrati (`test-author`), pagina developer (`docs-writer`), A/B della gallery, evidenza di release, righe di backlog | tutto verde; gallery `identical` a parte le instabili note; `mkdocs build` strict + `check-links` verdi; checkpoint |

## 8. Strategia di test

- **Vitest (env node), sotto `src/lib/dev/designer-lab/`:**
  - scanner con sorgenti di prova;
  - matematica del colore;
  - mapper delle opzioni ECharts: stringhe, `rgba`, hex a 8 cifre, gradienti, funzioni e `renderItem`, nessuna mutazione dell'input, proxy;
  - tokenizer e replacer dei valori CSS;
  - export: serializzazione, validazione, import;
  - guardia di release del plugin (bundle finto);
  - `+page.ts` dà 404 col flag spento (`globalThis.__LF_DESIGNER_LAB__ = false`);
  - gate degli import del Lab.

  I gate esistenti scansionano già i file nuovi.
- **E2E** `frontend/e2e/designer-lab/`, build di debug, corsia 6152:
  - apertura del Lab;
  - modifica di una variabile e di un letterale dei fogli di stile → `getComputedStyle` su un `data-testid` noto in una seconda pagina dello stesso contesto (evento `storage`);
  - modifica di un colore di grafico → opzione letta da `window.__lfDesignerLab`;
  - export → import (evento `download`);
  - neutralità con storage vuoto.

  Le regole del repo valgono tutte: `data-testid`, niente `waitForTimeout`, niente testo tradotto. Lo stato vive nel localStorage del contesto, quindi i test possono girare in parallelo.
- I test li scrive `test-author` (file distinti, corsia 6152, senza `--force`); la pagina developer in inglese `docs-writer`; `test-triage` prima di chiamare instabile un rosso.

**Comandi candidati** (sempre `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l …`):
- `front-designer-lab unit|e2e`, dopo la registrazione;
- prima della registrazione: `frontend/node_modules/.bin/vitest run src/lib/dev/designer-lab`;
- gate esistenti: `front-utility core-unit`, e l'azione di `front-fx` con `flagFont.gate`;
- `dev.py front check`, `dev.py front format --check`, `dev.py lint --dead-code`;
- release: `dev.py front build` + grep del marcatore;
- gallery: `scripts/visual_review/gallery_snapshot.sh L-off|L-on --checkout <wt> --port 6152 --data-dir /tmp/librefolio-r2-l`.

## 9. Collocazione del piano

`LibreFolio_developer_journal/Release_2/Phase_0/55_colorSystem/L-designerLab/plan-phase00DesignerLab.prompt.md`.
Si crea al primo passo autorizzato e si aggiorna dopo ogni passo: ✅ e data, «Note implementazione», «Fuori pista», comandi ed evidenze.
Backlog: solo la sezione «L · Designer Lab (55)» del `BACKLOG_POST_1.2.md`, nei checkpoint. Voci previste:
- L-2: l'inventario Python legge il JSON;
- L-3: campionario;
- L-4: salvataggio dell'export sul server;
- L-5: contratto `themeRevision` con R.
