# Piano — L · Designer Lab v1 (pagina nascosta per regolare i colori dal vivo, solo build di debug)

> **Workstream L** del programma colori 55. Piano di dettaglio del figlio, aperto il 14/10/2026.
> Indietro: progetto del coordinatore [`../design-designerLab.md`](../design-designerLab.md) e piano generale
> [`../plan-phase00ColorSystemThemeLab.prompt.md`](../plan-phase00ColorSystemThemeLab.prompt.md).
> Backlog: sezione «L · Designer Lab (55)» di [`../../../Phase_0/BACKLOG_POST_1.2.md`](../../../Phase_0/BACKLOG_POST_1.2.md).

## Identità della corsia

| Voce | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-fuzzy-robot` |
| Branch | `e-alfy-designer-lab` (rinominato dall'app; era `e-alfy-fuzzy-robot`) |
| Base | `dev_release2` @ `b631308d5ef5482a8ffdc2878a4459fcf6909827`. Il worktree è nato su `6d0b126` (`origin/dev_release2`); il coordinatore l'ha portato avanti con `merge --ff-only` su autorizzazione del developer |
| Corsia | porta **6152**, dati **`/tmp/librefolio-r2-l`** |
| Coordinatore | sessione `aec04834-1532-4d86-9e3f-f942e82aca89` |
| Autorizzazione | il developer ha approvato questo piano nella sessione L (approvazione del piano dell'app), 14/10/2026 |

## Decisioni (✅ 14/10/2026)

Autorizzazione del developer, testuale, inoltrata dal coordinatore: «Approvo L: piano, decisioni consigliate (§11 e
N1–N4) e file condivisi assegnati a L; parte in modalità interattiva».

| # | Decisione | Esito |
|---|---|---|
| 1 | URL e accesso | ✅ `/designer-lab` senza login: solo client, nessuna API, dati di test |
| 2 | Lingua del Lab | ✅ IT + EN con dizionario locale fuori dal catalogo i18n, scelta da `$locale` |
| 3 | Destinazione dell'export | ✅ solo download + «copia riassunto» |
| 4 | Fonti dello scanner | ✅ una (JS); parità col Python dimostrata al passo 1; il passaggio di `color_inventory.py` a lettore del JSON è separato |
| 5 | Granularità dei fogli di stile | ✅ per valore (con varianti alfa), per occorrenza come approfondimento |
| 6 | Campionario | ✅ dopo la v1 |
| 7 | Ordine rispetto ai token | ✅ Lab prima dei token |
| N1 | Ridisegno dei grafici | ✅ ri-applicazione dal vivo (`getOption` → patch con i soli colori → `setOption` in merge) più il wrapper di `setOption` sul prototipo; nessun tick di classe. **Confermata dallo spike**: 6 istanze su 6, 1,9–6,8 ms, zoom invariato, ripristino esatto; il tick avrebbe ridisegnato solo 3 grafici su 6 |
| N2 | Superfici condivise assegnate a L | ✅ ① registrazione nel runner, tramite `test-author`, solo aggiunte; ② una riga in `mkdocs.yml` e la pagina developer, tramite `docs-writer`; ③ la skill `designer-lab-apply`; ④ **solo** l'esclusione delle cartelle del Lab in `scripts/visual_review/color_inventory.py`; ⑤ `js-coverage-report.js` facoltativo |
| N3 | DoD del passo 5 | ✅ senza applicazione reale all'app |
| N4 | Neutralità della gallery | ✅ gallery **completa** con Lab spento e acceso, alla fine; **avvisare il coordinatore prima** di lanciarla, per non sovrapporsi a G e R. Le esecuzioni filtrate (`-f` per nome, viewport) le lancia L; la CLI non filtra per lingua |
| §5.2 | Modifica per occorrenza la cui regola non è caricata | ✅ **decisione del developer** (14/10 sera, testuale: «va bene fare così se si modifica qualcosa che non c'è è corretto non si veda»). **Nessuna ricaduta sul valore**: finché nessuna regola caricata ha selettore e proprietà dell'occorrenza, la modifica non si vede, ma finisce nell'export. Il pulsante «estendi a tutto il colore» non è richiesto. Progetto aggiornato dal coordinatore in `dev_release2` @ `898aea974` (§5.2, §5.5, nuovo §5.6). Il flusso di riferimento è a due schede: Lab in una, app nell'altra, aggiornamento con `storage` |

Vincoli aggiunti dal coordinatore (14/10):
- R creerà `frontend/src/lib/theme/**` (`themed()`, `components/*.css` con `--lf-cmp-*` su `:root`): lo scanner deve
  includerli. Lo scanner legge tutto `frontend/src`, e le `--lf-cmp-*` su `:root` sono modificabili con L1.
- Snapshot e rumore del 14/10 sono per ora in `~/LibreFolio_visual_review/`. Il coordinatore comunicherà il nuovo
  percorso quando la cartella di lavoro sarà spostata.

## Analisi (14/10/2026, sul codice di `b631308`)

### Claim del progetto verificati

| Claim | Verdetto | Evidenza |
|---|---|---|
| Il server di test usa sempre la build di debug | ✅ | `dev.py:199` forza `debug_mode`; marcatore `dev.py:2086`; i run di coverage aggiungono istanbul (`playwright.config.ts` passa `COVERAGE_INSTRUMENT` al webServer) |
| Esiste una build di debug | ✅ | `package.json` `build:debug`; `dev.py:643`; `src/lib/debug.ts` |
| Il frontend conosce il commit | ✅ | `define.__APP_VERSION__`, dichiarato in `src/lib/version.ts:9` |
| ECharts senza modulo centrale | ✅ | 29 file di import (25 non di test), tutti da `'echarts'`: un solo prototipo |
| 1.821 colori scritti a mano | ✅ | hex 1.610 + funzioni 211; `frontend/src` è identico tra `6d0b126` e `b631308` |
| Ripartizione per zona | ⚠️ | non riproducibile: `color_inventory.py` non classifica le zone |
| 17 grafici ridisegnano a qualunque cambio di classe | ❌ parziale | 12 sì; ScatterChart:82, CorrelationHeatmap:296, ExposureBars:44 ed ExposureMaps:96 assegnano solo `dark` a un `$state`; SemiDonutChart non ha osservatore; OtherPeriodEffectsTable:208 non è un osservatore del tema |
| Le classi Tailwind leggono variabili | ⏳ | riverifica nello spike, sul CSS compilato |

**Altri fatti:**
- In release, `/designer-lab` risponde HTTP 200 con `200.html` (`backend/app/main.py:494-524`) e il 404 lo disegna il client. `+error.svelte` non ha `data-testid`.
- Gate che leggono tutto `src`, Lab compreso:
  - `documentTitle.guard`: nessuna scrittura del titolo;
  - `htmlSink.gate`: niente `{@html}`;
  - `htmlInterpolation.gate`;
  - `clipboardSink.gate`: solo `writeTextToClipboard`;
  - `flagFont.gate`.
- `app.css:224` (`html.dark input,select,textarea`) è fuori dai layer e senza `!important`: il CSS con scope dei componenti del Lab vince.
- `check_frontend_needs_build` non guarda `frontend/scripts/`: se cambia solo lo scanner serve `--rebuild`.
- Il runner (`scripts/test_runner/_registry.py`) e il nav di MkDocs sono registrazioni esplicite, cioè superfici condivise.

### Correzioni al progetto

1. **Ridisegno L3.** Ri-applicazione dal vivo indipendente dai componenti: istanze trovate con `[_echarts_instance_]` + `getInstanceByDom`, poi `getOption` → patch con i soli colori. Il tick copre 12 componenti su 17.
2. **Portata reale di L3** sotto 571 occorrenze:
   - restano esclusi i colori derivati prima di `setOption` (`shadeForDepth`, `pnlColor`, `getIndexColor`, `lotColor`) e il markup Svelte dei grafici;
   - il Lab mostra un indice «visto dal vivo».
3. **Variabili definite nei componenti** (R-3 ne aggiungerà): si modificano via CSSOM sulla regola di definizione, non con un override su `html`.
4. **Confronto CSSOM sul colore parsato** (Chrome serializza gli hex come `rgb()` ed espande le shorthand). Varianti alfa incluse di default, conservando l'alfa.
5. **Client sempre caricato minimo:** controlla la chiave in localStorage e ascolta l'evento `storage`. Motori ed `echarts` in chunk lazy. Da inattivo, niente BroadcastChannel né osservatori.
6. **UI del Lab isolata:** solo variabili `--lab-*`, in uno stile proprio che i motori saltano. Nessuna classe colore Tailwind.
7. **Dichiarazione del modulo virtuale** in un `.d.ts` ambient dentro `lib/dev/designer-lab`, perché `app.d.ts` è un modulo.
8. **Eliminazione del ramo in release:** `if (__LF_DESIGNER_LAB__)` nello script invece di `{#if}{#await import()}` nel template.
9. **DoD del passo 5** senza applicazione reale all'app.
10. **Spike** con file temporanei, o meglio senza toccare il repo: Playwright contro la build di debug.
11. **Override d'ambiente `LF_DESIGNER_LAB=0|1`** per la gallery A/B nello stesso worktree. Tra le due esecuzioni si cancella `frontend/build/`.

### Superfici

- **Nuove:**
  - `frontend/scripts/designer-lab/**`;
  - `frontend/src/lib/dev/designer-lab/**`;
  - `frontend/src/routes/designer-lab/**`;
  - `frontend/e2e/designer-lab/**`.
- **Modifiche minime:**
  - `frontend/vite.config.ts`: `define`, plugin, `exclude` di istanbul;
  - `frontend/src/routes/+layout.svelte`: una riga in `onMount`;
  - `frontend/src/app.d.ts`.
- **Condivise:** quelle elencate in N2.
- **Vietate:** `app.css`, grafici e helper (R), gallery e fixture (G).

### Conflitti previsti

- **R:**
  - `themeRevision` (R-1): N1, eventualmente con un evento dev-only da concordare;
  - variabili con scope (R-3): correzione 3;
  - spostamenti di file e righe: catalogo rigenerato e `verify-export` per valore;
  - un futuro gate «niente hex» deve esentare il Lab.
- **G:** nessun file in comune; rischio solo se G tocca `routes/+layout.svelte`.

## Passi

| Passo | Contenuto | DoD | Stato |
|---|---|---|---|
| 0 | Spike: `npm ci`, DB della corsia, build di debug + server 6152, Playwright senza modificare il repo: riscrittura CSSOM, tick contro ri-applicazione su 3 grafici, `var()` nel CSS compilato | misure scritte qui, N1 deciso, repo intatto, server fermo | ✅ 14/10 |
| 1 | Scanner + CLI `lf-color-catalog/1` | parità esatta con l'inventario Python: hex 1.610, funzioni 211, classi 10.682, custom 795, arbitrari 12, `var()` 84, definizioni 86; tempo ≤ 2 s; Vitest verde | ✅ 14/10 (parità esatta, 1,4–1,6 s); Vitest al passo 6 |
| 2 | Interruttore, plugin, rotta, guardia di release, gate | release senza Lab (evidenza); debug serve `/designer-lab`; `svelte-check` 0; `lint:dead` pulito | ✅ 14/10; gate al passo 6 |
| 3 | Motore L1/L2/L3, persistenza, sincronizzazione | effetto in un'altra scheda, ripristino esatto, nessun effetto a storage vuoto | ✅ 14/10 (verifica funzionale); E2E al passo 6 |
| 4 | Interfaccia | accettazione dal vivo (passo esterno) | ✅ 14/10 codice; accettazione ⏳ |
| 5 | Export, import, `verify-export`, skill | round trip identico, `verify-export` corretto, prova a secco della skill | ✅ 14/10 |
| 5b | Selettore di elementi (ispettore): si punta un elemento nell'app, il Lab si filtra sulle sorgenti dei suoi colori; «specializza qui» con un'ancora nell'export (richiesta del developer del 14/10 sera) | vedi «Passo 5b» sotto | ✅ 14/10 sera (codice e verifica funzionale a due schede); test con `test-author` al passo 6 |
| 6 | Test registrati, documentazione, gallery A/B, evidenza di release, backlog | tutto verde; gallery `identical` a parte le instabili | ✅ 14/10 alle 22:55 (test, documentazione, evidenza di release, backlog); ⏳ gallery A/B in attesa del via del coordinatore (N4) |

## Avanzamento

### Passo 0 — Spike ✅ (14/10/2026)

> **Note implementazione**:
> - **Preparazione:**
>   - `frontend/node_modules/.bin/vitest` assente (exit 127) → `npm ci --no-audit --no-fund` pre-approvato, exit 0;
>   - npm 11 ha saltato gli script d'installazione (esbuild, fsevents), ma esbuild 0.19/0.27 e Vite 7.3.5 funzionano;
>   - `dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l db populate --force --clean --with-reports`: verde, 8 s;
>   - server `dev.py server --test --port 6152 --data-dir /tmp/librefolio-r2-l --no-scheduler --no-reload`: build di debug di circa 40 s, marcatore `.build-debug` = 1.
> - **Spike senza toccare il repo:** script Playwright `/tmp/libreFolio_L_spike.mjs` contro la build di debug, log `/tmp/libreFolio_L_spike.log`.
> - **Tailwind, sul CSS compilato `0.C3P6fEz2.css`:**
>   - `.text-red-500{color:var(--color-red-500)}`;
>   - `--color-red-500:oklch(63.7% .237 25.331)` dentro `@layer theme`;
>   - le opacità hanno un fallback letterale sRGB (`#fb2c36cc`) più `@supports (color:color-mix(in lab,red,red))` con `color-mix(in oklab,var(--color-red-500)80%,transparent)`;
>   - il claim del §1 regge.
> - **L2 (CSSOM, `/transactions`):**
>   - 24 fogli, 3.718 regole, 15.046 dichiarazioni: scansione completa in **13,5 ms**, riscrittura di 33 dichiarazioni in **0,3 ms**;
>   - il colore calcolato di `th` passa da `rgb(100, 116, 139)` a quello nuovo e torna esattamente all'originale;
>   - Chrome serializza `#64748b` come `rgb(100, 116, 139)` ed espande le shorthand nelle longhand;
>   - una variabile personalizzata mantiene il testo originale (`--theme-text-muted` = `"#6b7280"`).
>   - **Collisioni per valore confermate (P5):** lo stesso `#64748b` compare in 33 regole (ConfirmModal, paginazione, DataTable…).
> - **L3 (ECharts):**
>   - tutte le istanze condividono **un prototipo**;
>   - il tick di classe ridisegna `growth-chart`, `allocation-panel` e `risk-l1-underwater-chart`, ma **non** `risk-correlation-heatmap`, `risk-l3-scatter` e `ownership-chart-section` (SemiDonut). L'analisi è confermata;
>   - la **ri-applicazione dal vivo** (`getOption` → patch con le sole proprietà colore → `setOption` in merge) funziona su **6 istanze su 6**: 1,9–6,8 ms, patch di 151–650 byte, zoom invariato, ripristino esatto.
> - **N1 deciso:** ri-applicazione dal vivo per le istanze esistenti più il wrapper del prototipo per le chiamate future; nessun tick.

> **⚠️ Fuori pista**:
> - Il chunk ECharts dell'app esporta solo ciò che l'app importa: `getInstanceByDom` è eliminato dal tree-shaking (resta `init$1`). Lo spike ha usato `init(dom)`, che restituisce l'istanza esistente.
>   Nel prodotto il motore del Lab importa `getInstanceByDom` da `'echarts'`: il chunk condiviso guadagna un export solo nella build di debug. In release il Lab non esiste.
> - Lo scanner non ha avuto un prototipo a parte: il tempo si misura sullo scanner reale al passo 1.
> - Il server della corsia resta acceso per i passi 2–3, perché `front build --debug` riscrive `frontend/build` che lo stesso server serve. Va spento prima di ogni comando del runner sulla corsia e prima di ogni handoff.

### Passo 1 — Scanner + CLI ✅ codice (14/10/2026); test con `test-author` al passo 6

> **Note implementazione**:
> - **Modulo colore condiviso** `frontend/src/lib/dev/designer-lab/color.js`: ESM + JSDoc, importato sia da Node (scanner) sia dal browser (motori).
>   - Parsing di hex 3/4/6/8, `rgb[a]`, `hsl[a]`, `oklch`, `oklab`, `color(srgb|srgb-linear|display-p3)`;
>   - OKLab/OKLCH con le matrici di Ottosson, gamut sRGB e riduzione della crominanza, `colorKey` (hex opaco oppure `oklch` arrotondato), WCAG (2,54:1 per `#9ca3af` su bianco);
>   - `replaceColorTokens`. P11 riprodotto: `#ef4444` = `oklch(63.68% 0.2078 25.33)`.
> - **Scanner** `frontend/scripts/designer-lab/scan-colors.mjs`, schema `lf-color-catalog/1`, CLI `--out/--pretty/--summary/--root`.
>   - Conteggio identico a `color_inventory.py`; annotazione con zona, selettore, at-rule, proprietà, tema (catena CSS; chiavi `dark:`/`light:` e ternari negli script), `via` del markup, livello (`css-literal`, `chart-color`, `script`, `markup`, `static`) e anteprima;
>   - `css_vars` con selettore e `scope` root/scoped; `palette` → `--color-*` con le occorrenze; `by_value`; `meta.hash`, stabile perché esclude i campi volatili.
> - **Parità esatta:** `node frontend/scripts/designer-lab/scan-colors.mjs --out /tmp/libreFolio_L_catalog.json --summary` dà file 1.047, classi 10.682, custom 795, arbitrari 12, hex 1.610, funzioni 211, `var()` 84 (40 distinte), definizioni 86.
>   - L'inventario Python sullo stesso albero (`pipenv run python -m scripts.visual_review.color_inventory --out /tmp/libreFolio_L_inventory`) dà **gli stessi totali**;
>   - confronto riga per riga (`/tmp/libreFolio_L_paritydiff.py`): multinsiemi `(file, riga, valore)` identici, 1.610 hex e 211 funzioni.
> - **Livelli:** css-literal 1.153 (= 1.084 + 69 del progetto), chart-color 578, script 73, markup 17, static 56. Totale 1.877 = 1.821 + 56 fuori bundle (`app.html`, `offline.html`, `manifest.json`).
> - **Tempo** 1,39–1,59 s su 1.047 file (DoD ≤ 2 s); catalogo da 750 KB.
> - **④ assegnata:** `scripts/visual_review/color_inventory.py` esclude `lib/dev/designer-lab/` e `routes/designer-lab/` (costante `LAB_DIRS`, una condizione in `source_files()`); ruff e black puliti.

> **⚠️ Fuori pista**:
> - Variabili con scope di componente trovate oggi: 12 (`--highlight-*` in DataTable, `--cropper-*`, `--lf-price-flash-*`, `--lot-highlight-*`…). Vanno sul percorso CSSOM, come previsto dalla correzione 3.

### Passo 2 — Interruttore, plugin, rotta ✅ (14/10/2026); gate test con `test-author` al passo 6

> **Note implementazione**:
> - `frontend/scripts/designer-lab/vite-plugin.mjs`:
>   - `designerLabEnabled`: `VITE_DEBUG`, `mode=development`, `vite dev`, override `LF_DESIGNER_LAB=0|1`;
>   - modulo `virtual:lf-color-catalog`, costruito pigramente come `JSON.parse` di una stringa;
>   - invalidazione in dev, più l'evento `lf-designer-lab:catalog-stale`;
>   - **guardia di release** in `generateBundle`: errore se un file emesso contiene `lf-designer-lab`.
> - **`vite.config.ts`** (+7/−2): import, `({mode, command})`, plugin, `define.__LF_DESIGNER_LAB__`, `exclude` di istanbul per le cartelle del Lab.
> - **`app.d.ts`:** `const __LF_DESIGNER_LAB__` e `Window.__lfDesignerLab`. Il modulo virtuale è dichiarato a parte in `lib/dev/designer-lab/virtual-catalog.d.ts`.
> - **Rotta:**
>   - `routes/designer-lab/+page.ts`: `load()` dà 404 a flag spento;
>   - `+page.svelte`: `import()` del Lab in `onMount`, dentro il ramo.
> - **Layout radice:** una riga in `onMount` con `.then(start, () => {})`.
> - **Evidenze:**
>   - `svelte-check`: 0 errori, 0 avvisi su 5.664 file;
>   - `npm run build` (release): exit 0, guardia muta, **nessun file** di `build/` contiene `lf-designer-lab`; `/designer-lab` appare solo nel manifest delle rotte; nodo stub di 488 byte (`error(404)` + `onMount` vuoto); nessuna mappa; 24 MB;
>   - `npm run build:debug`: 47 s; il Lab sta in chunk separati, il catalogo in un chunk da 752 KB caricato solo dalla pagina del Lab; `GET /designer-lab` → 200.

> **⚠️ Fuori pista**:
> - `npm run build` cancella `frontend/build/.build-debug`, che scrive solo `dev.py`. Dopo le build fatte a mano con npm il marcatore va riscritto a `1`, altrimenti `server --test` ricostruisce.
> - Il chunk ECharts esporta solo ciò che l'app importa (spike): il motore del Lab importa `getInstanceByDom`, e Rollup lo aggiunge all'export solo in debug.

### Passo 3 — Motore dal vivo ✅ verifica funzionale (14/10/2026); E2E con `test-author` al passo 6

> **Note implementazione**:
> - **Client sempre caricato**, `client.ts` + `store.ts`:
>   - legge `localStorage['lf-designer-lab/v1']`, ascolta `storage` e pubblica `window.__lfDesignerLab` (`active`, `stats`, `chartColors`);
>   - carica `engine/` solo se lo stato ha un effetto.
> - **Motori** in `engine/`:
>   - `vars.ts` (L1): `<style data-lf-lab-own>` con `html`, `html:not(.dark)` o `html.dark` e `!important`;
>   - `stylesheets.ts` (L2 + variabili con scope): riscrittura CSSOM per colore parsato con varianti alfa, priorità conservata, ripristino esatto, fogli caricati dopo seguiti con un osservatore su `<head>`, regole proprie saltate, confronto per occorrenza su selettore normalizzato + proprietà;
>   - `charts.ts` (L3): wrapper di `setOption` sul prototipo, mappatura copy-on-write con memoria inversa dei colori scritti, funzioni avvolte una volta sola, patch sparse da `getOption()` per le istanze già sullo schermo;
>   - `cvd.ts`: filtro SVG su `<html>`;
>   - `index.ts`: orchestrazione e ricalcolo al cambio di tema, attivo solo con uno stato attivo.
> - **Verifica** con lo script `/tmp/libreFolio_L_engine_check.mjs`, log `/tmp/libreFolio_L_engine_check.log`, due schede dello stesso contesto:
>   - **inattivo:** hook presente, `active=false`, 0 nodi `data-lf-lab-own`, statistiche a zero;
>   - **stato scritto dall'altra scheda:**
>     - 2 override di variabili: la sonda `text-emerald-600` passa a `oklch(0.6 0.2 300)` e la trasparenza `bg-red-500/20` segue la variabile;
>     - 34 dichiarazioni CSS riscritte;
>     - 2 istanze di grafico applicate;
>   - **dopo la navigazione nell'app:** `th` di transazioni = colore nuovo, anche nel foglio caricato dopo;
>   - **dopo il ricaricamento:** il colore app di un grafico (`#ffffff`) è mappato dal wrapper al primo disegno;
>   - **cambio scuro/chiaro:** il letterale con ambito `dark` vale solo in scuro (`rgb(255,170,0)` ↔ `rgb(255,0,170)`);
>   - **pulizia:** variabili e fogli tornano esatti; nella prima esecuzione il grafico è tornato agli stessi colori (`growthSame=true`).

> **⚠️ Fuori pista**:
> - I colori della palette predefinita di ECharts (es. `#5070dd`) stanno solo in `getOption()` e non nel sorgente dell'app, quindi non sono nel catalogo. Il Lab non li propone.
>   La patch dal vivo li tratterebbe, ma dopo un ricaricamento il wrapper non li vede: è un limite dichiarato, non un difetto, perché il catalogo elenca i colori del codice.

### Passo 4 — Interfaccia ✅ codice e verifica funzionale (14/10/2026); accettazione con la designer: passo esterno

> **Note implementazione**:
> - `DesignerLab.svelte`:
>   - **testata:** versione, hash del catalogo, tema in modifica, sospendi, conteggio, varianti A/B, daltonismo, export JSON+MD, JSON, MD, copia riassunto, importa, ripristina tutto;
>   - **9 schede:** panoramica, palette Tailwind (famiglia × sfumatura), variabili dell'app, fogli di stile, grafici, senza anteprima, modifiche, contrasto, note; ricerca per nome, valore e file;
>   - **editor laterale** `ColorEditor.svelte`: valore di partenza e nuovo; slider OKLCH con avviso fuori sRGB; `<input type=color>`; «aggancia a» una variabile; varianti alfa; ambito per occorrenza (selettore + proprietà del catalogo); nota e codici schermata; impatto (classi, file, definizioni) o elenco delle occorrenze;
>   - **contrasto** `ContrastPanel.svelte` + `contrast.ts`: coppie dichiarate (`--theme-text-*` × `--theme-bg-*`, bordi sulla card) prima e dopo, nei due temi, più una coppia libera.
> - **Dizionario IT/EN** locale (`i18n.ts`), scelto da `$locale`, come da decisione 2.
> - **Isolamento:** i colori del Lab esistono solo come `--lab-*` nello style inline della radice (`labTheme.ts`); il foglio del Lab non contiene colori. Così L2 non lo riscrive mai e L1 non lo tocca.
> - **Evidenze:**
>   - `svelte-check`: 0/0;
>   - Prettier pulito sui file del Lab;
>   - i 5 gate esistenti che leggono tutto `src` (`htmlInterpolation`, `htmlSink`, `clipboardSink`, `flagFont`, `documentTitle`) **62/62 verdi** con i file del Lab;
>   - `knip`: nessun import irrisolto né file inutilizzato del Lab. Restano 3 export che useranno i test (`toCanvasColor`, `replaceColorTokens`, `clearState`); la baseline di knip è già rossa per altri 50+ elementi.
> - **Verifica di interfaccia** (`/tmp/libreFolio_L_ui_check.mjs`, screenshot in `/tmp/libreFolio_L_shots/`), con una modifica per livello fatta dall'interfaccia:
>   - **L1** `--color-emerald-600`: la sonda dell'app passa a `oklch(0.6 0.2 300)`;
>   - **L2** `#64748b`: 34 dichiarazioni nell'altra scheda;
>   - **L3** `#64748b` nei grafici: 2 istanze;
>   - **export JSON:** 52 occorrenze e impatto 53 per la variabile, 31 per il letterale, 29 per il grafico, con nota e codici schermata;
>   - **export MD:** scaricato come `designer-lab-changes.md`;
>   - **ripristina tutto:** la sonda torna originale; **importa** → di nuovo 3 modifiche e sonda modificata;
>   - **daltonismo:** il filtro arriva all'altra scheda;
>   - Lab in chiaro e in scuro leggibile; 18 righe di contrasto; nessun errore di pagina.

> **⚠️ Fuori pista**:
> - Il primo export elencava, per una modifica con ambito `light`, anche un'occorrenza solo scura (`app.css:161 html.dark`). Ora `literalsOf` filtra per `theme_context`: una modifica di un solo tema lascia stare le occorrenze dell'altro.
> - Ritocchi: conteggio scritto «Modifiche: N»; slider e checkbox con l'accento del Lab.

### Passo 5 — Export, import, verifica, skill ✅ (14/10/2026)

> **Note implementazione**:
> - **`export.ts`:**
>   - `buildExport` produce `lf-designer-lab/1` con `catalog_hash`. Per `css-var`: impatto, definizioni e occorrenze delle classi. Per i letterali: granularità, varianti alfa, occorrenze con file, riga, colonna, valore, selettore, proprietà e `theme_context`. Note, schermate, contrasti cambiati, varianti;
>   - `renderMarkdown` (IT/EN), `renderSummary`;
>   - `parseImport` rifiuta i valori pericolosi, avvisa su un hash diverso e **ri-ancora** un'occorrenza singola al catalogo corrente per file + riga + valore.
> - **`frontend/scripts/designer-lab/verify-export.mjs`:** per occorrenza dice in posto, spostata (riga più vicina) o mancante; controlla le definizioni (`value_now`) e l'hash; `--json` per l'agente; exit 0/1/2.
>   - Sull'export reale: 112 in posto, hash identico. Quindi **l'hash del catalogo di build coincide con quello rigenerato dalla CLI**.
>   - Su una copia alterata: 1 spostata (164 → 161), 1 mancante, hash diverso, exit 1.
> - **③ assegnata:** skill `.github/skills/design-tools/designer-lab-apply/SKILL.md`:
>   - regole: niente sostituzione globale (P5), tema e `theme_context`, proprietari dei file;
>   - passi: verifica → livelli → applicazione → gallery dello stesso giorno → rapporto.
>
>   Come da N3, niente applicazione reale all'app in L.

### Passo 6 — Test, documentazione, gallery A/B, evidenza di release ⏳ in corso → ⏸️ in pausa (14/10/2026)

> **Note implementazione** (quanto fatto prima della pausa):
> - **Ritocchi dopo il passo 5:**
>   - `CHART_PATH_RE` di `scan-colors.mjs` riconosce anche i file `*chart*` fuori dalle cartelle dei grafici; i livelli non cambiano (chart-color resta 578);
>   - `engine/charts.ts` esporta `mapChartOption` e `chartPatch`, funzioni pure per i test.
> - **Backlog, solo la sezione L:** aggiunte L-2…L-7 (inventario Python sul catalogo JS, campionario, export sul server, contratto `themeRevision` con R, indice «visto dal vivo», accettazione con la designer).
> - **`test-author`** (unit Vitest), fermato alla pausa: vedi la tabella dei file nella sezione «Pausa del 14/10».
> - **`docs-writer`** (pagina developer), fermato alla pausa:
>   - `mkdocs_src/docs/developer/frontend/designer-lab.md` completa;
>   - `mkdocs_src/mkdocs.yml` + 1 riga di nav dopo Styling;
>   - `dev.py mkdocs build` strict verde due volte; `dev.py mkdocs check-links` verde, 95 link validi.
> - **Server della corsia fermato;** porta 6152 libera, verificata con `lsof`.

> **⚠️ Fuori pista**:
> - Due difetti dello scanner, trovati da `test-author` leggendo il codice: **✅ corretti alla ripresa** (14/10 sera), vedi «▶️ Ripresa del 14/10 sera».
>   1. `themeOfChain` legge `html:not(.dark)` come tema `dark`: il test `/\.dark\b/` scatta prima del controllo `:not(.dark)`.
>   2. `scriptThemeHint` con un ternario su più righe: unisce le righe precedenti in ordine inverso (`[riga-1, riga-2]`), quindi un ramo `? '#…'` su una riga sua resta senza indizio, salvo che la riga due sopra sia vuota.
>
>   Entrambi toccano solo le annotazioni del catalogo (tema), **non** i conteggi né la parità. Misura alla ripresa: **nessuno dei due casi esiste oggi nel codice** (0 letterali sotto `:not(.dark)`, 0 righe di produzione che aprono un ramo `?`/`:` con un colore), quindi non spiegano l'asimmetria dark 201 / light 222 / null 228.
>   Quei 228 senza indizio sono soprattutto palette dichiarate per nome (`const PALETTE_DARK = [...]`): un indizio da nome di variabile resta fuori di proposito, perché i nomi possono descrivere il colore e non il tema.
> - **Scostamenti dal progetto** segnalati da `docs-writer` (la pagina documenta il codice):
>   - sincronizzazione tra schede con l'evento `storage` e non `BroadcastChannel`: è voluto, correzione 5, client inattivo minimo;
>   - nessuna classe `lf-lab-tick`: N1;
>   - id delle modifiche `css-var:…` invece di `var:…` dell'esempio §7;
>   - skill in `.github/skills/design-tools/…`;
>   - ~~una modifica per occorrenza la cui regola non è caricata non ricade sul valore~~ → **non è più uno scostamento**: è la decisione del developer del 14/10 sera (riga «§5.2» delle Decisioni). La pagina developer la descrive come comportamento voluto.
> - `test-author` ha lanciato una volta `python3` puro: un heredoc non chiuso, fallito subito per un errore di sintassi, nessun file cambiato. È una violazione della regola «Python solo via pipenv», registrata qui.

## ⏸️ Pausa del 14/10/2026

Richiesta del developer tramite il coordinatore. **Non si riprende senza «RIPRENDI» del coordinatore.**

### Stato al momento della pausa

| Voce | Valore |
|---|---|
| HEAD | `b631308d5ef5482a8ffdc2878a4459fcf6909827`, uguale alla base |
| `git status --porcelain` | **12 righe**: 6 file tracciati modificati, 6 percorsi nuovi. Niente commit, stage o stash |
| Corsia | nessun server, porta 6152 libera; DB in `/tmp/librefolio-r2-l` lasciato com'è |
| Sotto-agenti | `test-author` e `docs-writer` fermati con un messaggio di stop; entrambi `idle`, nessun comando in corso |
| `frontend/build` | build di **debug** fatta con `npm run build:debug`, marcatore `.build-debug` riscritto a mano a `1`. È precedente alle ultime modifiche (`export.ts`, `i18n.ts`, `ColorEditor.svelte`, `engine/charts.ts`, `scan-colors.mjs`): alla ripresa `dev.py server --test` la ricostruisce da solo |
| Evidenze di `/tmp` | copiate negli artefatti della sessione L: `/Users/ea_enel/.copilot/session-state/13212938-4f86-497c-a242-e21e069a8280/files/L-pause-2026-10-14/tmp-evidence/`, 20 elementi: script e log dello spike, del motore e della UI, screenshot, export JSON/MD di prova, catalogo, inventario, log di build, gate, knip, populate e server |

- **Ultimo passo completo:** passo 5 (export, import, `verify-export`, skill). I passi 0–5 sono ✅ come codice e verifica funzionale; il passo 4 aspetta l'accettazione esterna con la designer (L-7).
- **Passo in corso:** passo 6. File toccati o creati e loro stato:

  | File | Chi | Stato |
  |---|---|---|
  | `frontend/src/lib/dev/designer-lab/color.test.ts` | `test-author` | **completo ma non verificato**: l'ultima esecuzione dava 22/23 verdi; l'unico rosso era una tolleranza troppo stretta sul giro `#ef4444` ↔ OKLCH (2,2e-9). La tolleranza è stata allargata a 6 decimali, ma la correzione non è stata rieseguita. Prettier e `svelte-check` non ancora eseguiti |
  | `frontend/src/lib/dev/designer-lab/scanColors.test.ts` | `test-author` | **a metà, mai eseguito**: ci sono intestazione, helper e test di zone e regole CSS. Mancano indizi di tema degli script, `via` del markup, livelli, conteggi di parità, definizioni di variabili, `scanColors` su albero sintetico e reale. Contiene già un test che fallirà (`:not(.dark)`, difetto 1) |
  | `mkdocs_src/docs/developer/frontend/designer-lab.md` | `docs-writer` | completo; build strict e check-links verdi. Diagrammi Mermaid non guardati in un browser |
  | `mkdocs_src/mkdocs.yml` | `docs-writer` | completo: 1 riga di nav |
  | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` | L | completo: righe L-2…L-7 nella sezione L |
  | **Non ancora creati** | — | gli altri 8 file unit del brief (`vitePlugin`, `store`, `exportFormat`, `catalogView`, `contrast`, `chartMapping`, `verifyExport`, `page`, il gate `designerLabImports`); `frontend/e2e/designer-lab/`; la registrazione nel runner (`front-designer-lab`) |

### Primo comando alla ripresa

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-fuzzy-robot && git rev-parse HEAD && git status --porcelain | wc -l && cd frontend && ./node_modules/.bin/vitest run src/lib/dev/designer-lab/color.test.ts
```

Atteso:
- HEAD uguale alla base comunicata dal coordinatore (oggi `b631308`). Se la base è avanzata, prima il fast-forward del coordinatore;
- 12 righe;
- `color.test.ts` verde, cioè la tolleranza è confermata.

### Ordine alla ripresa

1. Correggere i difetti 1 e 2 dello scanner; decidere la ricaduta sul valore per le modifiche per occorrenza (§5.2).
2. Rilanciare `test-author`: completare `scanColors.test.ts`, poi gli 8 file mancanti, l'E2E `frontend/e2e/designer-lab/` e la registrazione `front-designer-lab` (unit + e2e, solo aggiunte, ①).
3. Chiudere con `docs-writer` il rapporto sugli scostamenti; allineare la pagina se cambia la ricaduta.
4. Evidenza di release e di debug: `npm run build` + grep del marcatore, poi `dev.py front build --debug`.
5. Gallery A/B (`LF_DESIGNER_LAB=0/1`): **avvisare il coordinatore prima** della gallery completa (N4); `LF_VISUAL_REVIEW_DIR=/Users/ea_enel/Documents/00_My/LibreFolio_subRepo/LibreFolio_visual_review`.
6. Checkpoint al coordinatore.

### Attese aperte

- ~~«RIPRENDI» del coordinatore.~~ Arrivato il 14/10 alle 19:29.
- Slot per la gallery completa, Lab spento e acceso (N4).
- Accettazione dal vivo con la designer (L-7).
- Prossimo allineamento della base: il coordinatore aggiorna nel toolkit il predefinito di `LF_VISUAL_REVIEW_DIR`.
- `knip`: 3 export ancora senza uso (`toCanvasColor`, `replaceColorTokens`, `clearState`) più `mapChartOption` e `chartPatch`, aggiunti dopo l'esecuzione di knip. Li useranno i test.

## ▶️ Ripresa del 14/10/2026 sera

«RIPRENDI» del coordinatore alle 19:29. Stato verificato: HEAD `b631308`, 12 righe di `git status`, porta 6152 libera.
Il Mac si è riavviato alle 19:10, durante la pausa, e `/tmp` è stato svuotato: **la cartella dati della corsia
`/tmp/librefolio-r2-l` non esiste più**. Le evidenze erano già negli artefatti di sessione. Prima del primo comando
sulla corsia: `db populate --force --clean` sulla 6152 e `/tmp/librefolio-r2-l` (pre-approvato dal coordinatore).

Ordine del coordinatore: cose piccole aperte → checkpoint dei passi 0–5 → analisi del selettore di elementi, senza
codice prima del via → resto del passo 6, con il via anche per la gallery A/B.

### Cose piccole aperte ✅ (14/10 sera)

> **Note implementazione**:
> - `color.test.ts` rieseguito: **23/23 verdi**. La tolleranza allargata regge.
> - **Difetto 1** (`scan-colors.mjs`):
>   - nuova funzione `selectorTheme()`: `.dark` o `:not(.light)` danno dark, `.light` o `:not(.dark)` danno light;
>   - `themeOfChain()` ragiona per livello della catena: un livello fissa il tema solo se tutti i suoi selettori sono d'accordo, quindi una lista mista come `.a, html.dark .b` vale per entrambi; le media query `prefers-color-scheme` restano.
> - **Difetto 2** (`scriptThemeHint()`): un ramo `?` o `:` su una riga sua risale alla riga `?` del suo ternario e alla condizione sopra, nella forma di Prettier; `!isDark` scambia i lati; si ferma su un altro ramo `:`.
> - **Colori nel markup:** il tema viene dalla variante `dark:` della **classe che contiene il colore**, non più da qualunque `dark:` nei 40 caratteri precedenti, che poteva essere quello di una classe vicina.
> - **Export più prudente** (`literalsOf()` in `export.ts`): una modifica di un solo tema esclude le occorrenze dell'altro tema solo quando il loro tema è **certo**, cioè nei fogli di stile (dal selettore) e nel markup (dalla variante `dark:`).
>   - Un'occorrenza in uno script resta sempre, con il suo `theme_context`, perché il tema di uno script è un'ipotesi da nomi e ternari.
>   - Prima un indizio sbagliato poteva togliere dall'export un'occorrenza che il motore aveva davvero cambiato sullo schermo.
> - **Liste dei selettori radice allineate** tra scanner (`ROOT_SELECTOR_RE`) e motore (`ROOT_SELECTOR` in `engine/stylesheets.ts`): ora entrambe contengono `html:not(.dark)` e `html:not(.light)`, con un commento che rimanda all'altra. Lo ha segnalato `docs-writer`.
>   - Prima una variabile definita su `html:not(.dark)` sarebbe finita come `scoped` nel catalogo e come radice nel motore.
> - **Prove:**
>   - 20 casi sintetici (`/tmp/libreFolio_L_themefix_check.mjs`), tutti verdi: difetti 1 e 2, negazione, catene annidate, condizione estranea, riga singola, chiavi, markup con classe vicina e catena di varianti;
>   - ambito delle variabili su un albero temporaneo (`/tmp/libreFolio_L_scope_check.mjs`): `html:not(.dark)` root/light, `html:not(.light)` root/dark, `.card` scoped;
>   - **sull'albero reale nulla cambia:** parità identica (1.047 file, 10.682 classi, 795 custom, 12 arbitrari, 1.610 hex, 211 funzioni, `var()` 84 su 40, definizioni 86), livelli identici, **0** etichette di tema cambiate su 1.877 letterali e 86 definizioni;
>   - i difetti 1 e 2 sono **latenti**: oggi 0 letterali sotto `:not(.dark)` e 0 rami di ternario su righe proprie con un colore. La correzione serve al codice che R sta per scrivere (`lib/theme/**`).
> - **Pagina developer allineata** da `docs-writer` (nuova istanza, la precedente non esisteva più dopo la pausa):
>   - la modifica per occorrenza passa dai limiti al punto L2 «One occurrence» come comportamento voluto (decisione §5.2), senza ricaduta;
>   - il paragrafo sul filtro per tema dell'export riflette `literalsOf()` (certi contro ipotesi);
>   - il paragrafo «Theme hint» del catalogo riflette i nuovi casi.
>
>   `dev.py mkdocs build` strict verde (26,7 s), `dev.py mkdocs check-links` verde (95 link). `git status` invariato: 12 righe.

> **⚠️ Fuori pista**:
> - Misurato che i difetti 1 e 2 **non** spiegano l'asimmetria degli indizi negli script (dark 201, light 222, null 228). I 228 senza indizio sono soprattutto palette dichiarate per nome (`const PALETTE_DARK = [...]`).
>   Un indizio dal nome di una variabile resta fuori di proposito: un nome come `darkGreen` può descrivere il colore e non il tema. Oggi i 4 nomi composti con indizio (`darkBg`, `darkText`, `darkBorder`) sono davvero di tema (`colors.ts`, `FilesTable.svelte`).
> - `dev.py test check-orphans` esce con **1** a causa dei soli due file di test del Lab, ancora non registrati nel runner (`color.test.ts`, `scanColors.test.ts`). Per non lasciare `dev_release2` con un gate rosso, i due file **restano fuori dal checkpoint** ed entrano con la registrazione `front-designer-lab` del passo 6.
> - Anche `docs-writer` ha lanciato una volta `python3` di sistema, in sola lettura, per controllare l'HTML generato: la regola è «Python solo via `pipenv run python dev.py …`». Registrato come per `test-author`.
> - Il primo controllo dell'ambito delle variabili non stampava nulla per un errore del controllo stesso: la regex delle definizioni, uguale a quella dell'inventario Python, vuole ogni `--var:` a inizio riga, mentre il CSS sintetico stava su una riga sola. Rieseguito con una dichiarazione per riga.

### Checkpoint dei passi 0–5 (14/10 sera)

> **Note implementazione**:
> - **Evidenza di release** sul codice del checkpoint (`npm run build`, exit 0):
>   - **0** file di `build/` con il marcatore `lf-designer-lab`, **0** con lo schema `lf-color-catalog/1`, **0** con i nomi dei componenti del Lab (`DesignerLab`, `ColorEditor`, `ContrastPanel`, `__lfDesignerLab`);
>   - `/designer-lab` solo nel manifest delle rotte;
>   - nodo stub di 488 byte, **identico** a quello del passo 2 (`17.CmL9VVVP.js`);
>   - 0 sourcemap, 24 MB.
>
>   Ora `frontend/build` è una build di release: al primo `server --test` sulla corsia `dev.py` ricostruisce in debug da solo, perché il marcatore manca.
> - **Controlli statici:**
>   - `svelte-check`: 0 errori, 0 avvisi;
>   - Vitest: 7 file, **91/91** (`color.test.ts` 23, `scanColors.test.ts` 6, i 5 gate del repo 62);
>   - Prettier pulito su tutti i sorgenti del Lab, il layout, `app.d.ts` e `vite.config.ts`;
>   - `git diff --check` pulito; ruff e black puliti su `color_inventory.py`.
> - Il contenuto del checkpoint e le esclusioni sono nel messaggio `CHECKPOINT READY` al coordinatore. In sintesi: tutto tranne i due file di test non registrati.
> - **Evidenze** negli artefatti della sessione L:
>   - `files/L-pause-2026-10-14/tmp-evidence/`: spike, motore, UI, screenshot, export di prova;
>   - `files/L-checkpoint-2026-10-14/`: cataloghi prima e dopo, controlli sintetici, log di release, `svelte-check`, Vitest, orfani, MkDocs.

### Selettore di elementi (passo 5b): richiesta e analisi

Richiesta del developer (testuale, 14/10 sera): «anzi servirebbe al contrario avere qualcosa che mi permette, puntando
un elemento, di avere un filtro per quelle proprietà, così lo modifico e posso farmi un giro nell'app per vedere che
effetto ha sul resto. mi immagino che se un colore va specializzato a quel punto l'app deve creare un css path o
qualcosa di simile a indicare il componente così che l'ia poi sappia a quale componente legare la nuova varabile. se
servisse».

L'analisi di implementazione va al coordinatore dopo il checkpoint. Copre:
- come funziona con due schede;
- la descrizione dell'elemento con le sorgenti dei colori;
- la corrispondenza con il catalogo;
- il nuovo livello `element` per «specializza qui», con anteprima;
- il formato dell'ancora;
- le aggiunte allo schema `lf-designer-lab/1`, allo scanner (indice dei `data-testid`), a `verify-export` e alla skill;
- test, costo e rischi.

Il dettaglio entra qui come passo 5b **dopo il via**. Fino ad allora nessun codice.

### Primo comando alla prossima ripresa del lavoro (dopo il via)

```bash
cd /Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-fuzzy-robot && git rev-parse HEAD && git status --porcelain | wc -l && PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l db populate --force --clean --with-reports
```

HEAD atteso: quello del commit del coordinatore dopo il checkpoint, con la base aggiornata a `dev_release2`.
Righe di `git status` attese: solo i due file di test esclusi, se il coordinatore ha committato tutto il resto.
## ▶️ Checkpoint committato e via al passo 5b (14/10/2026, 19:56)

- **Commit del coordinatore:** checkpoint `6e967202e` (`feat(frontend): add debug-only Designer Lab`, 33 file, padre `b631308d5`), poi merge di `dev_release2` (`2dca0105c`).
  **HEAD `150f2716a91c64c558bef2e61de45bacb9b4d5a9`**, verificato.
- **Il merge porta:**
  - il progetto aggiornato (§5.2 decisione, §5.5 flusso a due schede, nuovo §5.6 selettore);
  - le nuove regole Git: solo il coordinatore committa e fa i merge, i figli mai;
  - il toolkit che trova da solo la cartella di lavoro in `LibreFolio_subRepo`, quindi `LF_VISUAL_REVIEW_DIR` non serve più;
  - documenti della 1.3.

  Nessun file del frontend.
- **Nel worktree:** solo i 2 test esclusi, non tracciati, come previsto.
- **Corsia ricreata:** `dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l db populate --force --clean --with-reports` verde.
- **Via al 5b.** Il coordinatore conferma i tre punti dell'analisi:
  - (a) «specializza» vale per ogni istanza del componente;
  - (b) Alt+Shift+D solo dove il Lab è già stato aperto;
  - (c) schema `lf-designer-lab/1`, solo aggiunte.

  Regola confermata: **nessun testo dell'elemento nell'export**. Due suggerimenti accolti: il numero di elementi presi dal selettore generato, accanto al selettore; la scorciatoia letta da `event.code === 'KeyD'`, perché su macOS Alt+Shift+D dà «Î» in `event.key`.

### Passo 5b — Selettore di elementi ✅ codice e verifica funzionale (14/10/2026 sera); test con `test-author` al passo 6

**Richiesta** (testuale, developer, 14/10 sera): vedi «Selettore di elementi (passo 5b): richiesta e analisi».
Analisi completa negli artefatti di sessione: `files/L-element-picker-analysis.md`.

**Fatti verificati in più dopo l'analisi:**
- **Test id passati come prop:** `testid=` e `testId=` ai componenti compaiono **2.594 volte**, contro 2.276 `data-testid=` scritti direttamente; i componenti li rendono con `data-testid={testid}`. L'indice dello scanner li deve includere entrambi (`via: attr | prop`).
- **Niente top layer:** l'app non usa `<dialog>.showModal()` né popover, quindi il velo con lo z-index massimo resta sopra tutto.
- **Utility Tailwind importanti:** l'app ne usa alcune (`!bg-white`, `dark:!bg-slate-800` in `qty-input`). Un `!important` fuori dai layer perderebbe contro di loro.
  - Le regole di anteprima di «specializza» stanno quindi nel layer `lf-designer-lab`, **dichiarato per primo** in `<head>`.
  - Tra le dichiarazioni `!important` vince il primo layer, sia sugli altri layer sia sugli override P1 di `app.css`, che sono fuori dai layer.
  - Solo uno stile inline `!important` resterebbe sopra.

**Progetto** (dall'analisi, con le decisioni a/b/c):

| Parte | File | Cosa |
|---|---|---|
| Protocollo | `pick.ts` | chiavi `lf-designer-lab/pick` (`start`, `cancel`, `result`) e `lf-designer-lab/seen`, lettura e scrittura |
| Client | `client.ts` | lo stesso listener `storage` reagisce anche alla chiave del puntamento. La scorciatoia Alt+Shift+D (`event.code`) si registra solo con `seen`; la pagina del Lab non entra mai in modalità puntamento |
| Velo | `picker/overlay.ts` (chunk pigro) | velo trasparente con stili inline e z-index massimo, riquadro ed etichetta; `elementsFromPoint` (l'elemento non va in `:hover`); eventi intercettati in capture; `Esc` annulla; la rotella scorre il contenitore sotto il puntatore |
| Descrizione | `picker/describe.ts` | proprietà visibili: `color`; `background-color` visibile, anche da un antenato; bordi, outline e decorazione se visibili; `fill`/`stroke` SVG; `box-shadow` e gradienti solo elencati. Per ognuna: valore calcolato, dichiarazioni candidate (regole con `el.matches`, anche nei layer, `@media`, `@supports` e abbreviate; stile inline; attributi SVG), antenato se ereditata, vincitrice provata per perturbazione (vedi sotto) |
| Ancora | `picker/anchor.ts` | catena dei testid, percorso CSS dal testid più vicino, selettore di componente (testid più vicino + tag + classi senza `.svelte-…`; id con suffisso numerico generalizzati a `^=`), numero di elementi presi. **Nessun testo** |
| Lab | `pickView.ts`, `PickedElement.svelte`, `DesignerLab.svelte`, `ColorEditor.svelte` | pulsante «Punta un elemento», scheda «Elemento» con le sorgenti per proprietà (var → definizioni, classe → usi nei file del componente, regola → `file:riga` esatti, inline o attributo → proposta, currentColor → `color`, grafico → colori), «Modifica la sorgente» (editor esistente, con l'ancora come contesto), «Specializza qui» (livello `element`); filtro «solo l'elemento puntato» sulle liste |
| Motore | `engine/anchors.ts` | `element` → regole `@layer lf-designer-lab { html… :is(<selettore>) { <prop>: <valore> !important } }`; grafici: `element` con `property: chart` → colore mappato solo nelle istanze dentro il selettore |
| Scanner | `scan-colors.mjs` | `testids` (statici `id → [file, riga, via]`, prefissi dei template); `palette[].occ` con l'indice della classe; `css_vars[].use_sites` (`file`, riga, selettore) per la riga esatta di una regola P1. Fuori dalla parità |
| Export | `export.ts`, `types.ts` | layer `element` (`target` = selettore, `property`, `from` = valore calcolato, `to`, `anchor`, `occurrences` = candidati con `why` e `raw` = ago); `anchor` facoltativa sugli altri livelli; import validato (selettore sicuro, proprietà ammesse, ancora tipizzata e limitata); Markdown e riassunto |
| Verifica | `verify-export.mjs` | candidati con `locate()` sul loro ago; presenza dei testid della catena nei sorgenti (indice statico e prefissi); `anchor_status` e totali; exit 1 se a una modifica `element` non resta alcun candidato |
| Skill | `designer-lab-apply/SKILL.md` | sezione `element`: non si tocca la sorgente condivisa; variabile di componente nel candidato, legata per tema; le variabili dei temi si segnalano a R/T |

**Vincitrice provata per perturbazione:**
1. Le candidate si ordinano: `!important`, poi inline, poi ordine nel foglio.
2. Per ognuna, in quest'ordine, si sostituisce il colore con un valore di prova, si legge il valore calcolato e si ripristina il `cssText` intero.
3. Vince la prima che cambia il valore calcolato.

La prova avviene con `transition: none` iniettata, per non leggere un valore a metà transizione, ed è sincrona: nessun fotogramma viene disegnato. Le altre candidate compaiono come «scavalcate» (il caso P1).

**Definition of done:**
- Si punta un elemento in un'altra scheda; il Lab mostra le sorgenti attese su tre casi: classe Tailwind e variabile; regola di componente con `file:riga` esatti (`DataTable.svelte`); override P1 in scuro.
- «Specializza» cambia solo il componente: un altro elemento con lo stesso colore non cambia.
- L'ancora è nell'export e `verify-export` la controlla.
- Neutralità: senza `seen` né puntamento, nessun nuovo listener e nessun chunk.
- `svelte-check` 0/0, gate verdi, Prettier pulito.
- I test li scrive `test-author` nel passo 6, che copre anche il 5b.

> **Note implementazione** (14/10 sera):
> - **File nuovi:** `pick.ts`, `cssProps.ts`, `pickView.ts`, `PickedElement.svelte`, `engine/anchors.ts`, `picker/{anchor,describe,overlay}.ts`.
>   **Modificati:** `types.ts`, `store.ts`, `client.ts`, `export.ts`, `i18n.ts`, `ColorEditor.svelte`, `DesignerLab.svelte`, `engine/{index,charts,stylesheets,targets}.ts`, `virtual-catalog.d.ts`, `scripts/designer-lab/{scan-colors,verify-export,vite-plugin}.mjs`, skill `designer-lab-apply`.
> - **Client** (sempre caricato nelle build di debug, chunk di 6,2 KB): lo stesso listener `storage` segue `lf-designer-lab/pick`; carica il chunk del selettore (73,6 KB, indice dei testid compreso) solo davanti a una richiesta fresca o alla scorciatoia. La scorciatoia (`event.code === 'KeyD'` con Alt+Shift, senza Ctrl/Meta né ripetizione) si registra solo con `lf-designer-lab/seen`, scritto dal Lab al mount; mai sulla pagina del Lab.
> - **Selettore di specializzazione per proprietà**, calcolato nella scheda dell'app:
>   - si specializza **l'elemento che dichiara il colore**, se sta dentro il componente dell'elemento puntato (il `th` per un testo ereditato, la card per uno sfondo visto attraverso); sopra il componente (`body`, layout), l'elemento puntato;
>   - selettore = testid più vicino (il suo prefisso per un id templato) + **percorso strutturale senza posizioni** fino all'elemento, con figli diretti (al massimo 6 segmenti);
>   - dell'elemento si scrivono **solo le classi nominate dalla regola vincitrice** (`p.text-gray-500` sì, `flex`/`sorted` no);
>   - per ogni proprietà, accanto a «Specializza qui», il selettore e il numero di elementi presi nella pagina aperta (suggerimento del coordinatore).
> - **Indice dei testid:** secondo modulo virtuale `virtual:lf-testid-index` (statici + prefissi), importato solo da `picker/describe.ts`.
>   - Un id della pagina che non è statico ma inizia con un prefisso noto è un'istanza di un id templato: nel selettore diventa `^="prefisso"`, nella catena e nell'export `prefisso*`.
>   - Così nessun valore di record (codici, id) finisce nell'export e il selettore prende tutte le istanze.
>   - Senza indice (test jsdom) resta l'euristica del suffisso numerico.
> - **Scanner** (fuori dalla parità, che resta identica: 1047 file, 10682 classi, 1610 hex…):
>   - `testids`: 1.828 id statici in 1.947 punti, 1.708 attributi e 239 prop;
>   - `testid_prefixes`: 235;
>   - `testidValues()` legge anche i letterali in posizione di valore di un'espressione (`cond ? 'a' : 'b'`, `x ?? \`tab-${id}\``), mai gli operandi di un confronto;
>   - `palette[].occ` = `[file, riga, indiceClasse]`; `css_vars[].use_sites` = `[file, riga, selettore]`.
> - **Lab:**
>   - scheda «Elemento» con, per ogni proprietà: tipo di sorgente, catena delle variabili cliccabile, regola vincitrice, `file:riga` del catalogo, badge P1 «override del tema scuro», «sopra la classe …», «già specializzato», candidati e dichiarazioni (richiudibili);
>   - «Modifica la sorgente» apre l'editor esistente con l'ancora come contesto; «Specializza qui» apre l'editor in modalità `element`;
>   - filtro «Solo i colori dell'elemento puntato» su palette, variabili, fogli, grafici e senza anteprima;
>   - a un nuovo puntamento si chiude un editor rimasto su una specializzazione precedente, e «Modifica» segue il tema del puntamento (salvo «entrambi»).
> - **Export** (`lf-designer-lab/1`, solo aggiunte): layer `element` con `property`, `color_key`, `anchor`, `occurrences` = candidati (`raw` = testo atteso, `why`); `anchor` facoltativa sugli altri livelli; Markdown con «Dove legare la nuova variabile»; import con `sanitizeAnchor()` (tipi, lunghezze, enum, selettore sicuro).
> - **`verify-export`:**
>   - i candidati si contano a parte (`candidates_*`);
>   - `anchor.status` vale `ok`, `testid-missing`, `no-candidates` o `lost`; exit 1 solo per `lost`;
>   - si controlla che i testid dell'ancora siano ancora scritti nel codice;
>   - un percorso fuori da `frontend/` non viene letto: un export è input.
>
> **Comandi ed evidenza** (corsia 6152, `/tmp/librefolio-r2-l`):
> - `npm run check` → `svelte-check found 0 errors and 0 warnings`; Prettier pulito su `src/lib/dev/designer-lab` e `scripts/designer-lab`; `git diff --check` pulito.
> - `node_modules/.bin/vitest run` dei 5 gate + `color.test.ts` + `scanColors.test.ts` → **89/89**.
> - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server --test --port 6152 --data-dir /tmp/librefolio-r2-l --no-scheduler --no-reload`, poi lo script a due schede `/tmp/libreFolio_L_5b_pick_check.mjs` (copia negli artefatti di sessione):
>   - **neutralità** prima che il Lab sia aperto: `seen` assente, nessun velo, Alt+Shift+D senza effetto;
>   - puntamento dal pulsante su un'intestazione della tabella transazioni: `color` = `rule-literal`, `th { color: #64748b }` → `DataTable.svelte:1607`; testid `tx-table` → `TransactionsTable.svelte:993`;
>   - «Specializza» di `color` → `[data-testid="tx-table"] > div > div > table > thead > tr > th`, **12 elementi**: 12/12 `th` cambiano, 0 elementi fuori dai `th`, gli altri 58 `#64748b` invariati;
>   - export: ancora con route, testid, `css_path`, selettore, 12 elementi e 2 candidati; **nessuno dei 371 testi** delle celle compare nell'export;
>   - classe Tailwind con Alt+Shift+D: `text-gray-500` → `--color-gray-500`, selettore `… > p.text-gray-500`;
>   - lo stesso elemento in scuro: `var` `--theme-text-muted` con badge P1, «sopra la classe dark:text-gray-400»; lo sfondo dal layout è senza «Specializza»;
>   - filtro: palette 172 → 4, variabili 3;
>   - Esc annulla: velo tolto, «Selezione annullata» nel Lab;
>   - grafico `growth-chart`: 32 colori, il puntato per primo; «Specializza» del primo → verde presente nell'istanza;
>   - «Ripristina tutto» → statistiche a 0 e nessuno stile del Lab residuo;
>   - nessun errore di pagina. L'unico errore in console è il 401 di `GET /api/v1/auth/me` prima del login, comportamento dell'app.
> - `node frontend/scripts/designer-lab/verify-export.mjs <export>` → exit 0, «2 candidates in place». Export manomessi (`/tmp/libreFolio_L_5b_tamper.sh`):
>   - un candidato sparito e un testid rinominato → exit 0 con `testid-missing`;
>   - tutti i candidati spariti → exit 1 `lost`;
>   - percorso `../../…/etc/hosts` → non letto, exit 1.
> - Chunk della build di debug: il client (6,2 KB) importa **solo dinamicamente** il selettore (73,6 KB) e i motori.
> - `npm run build` (release): **0 file** con il marker `lf-designer-lab`, nessuna traccia del selettore o dell'indice; il nodo stub resta di 488 B (`17.CmL9VVVP.js`).
> - Server fermato; `lsof -nP -iTCP:6152 -sTCP:LISTEN` → nessun processo in ascolto. `frontend/build` è ora una build di **release**: `dev.py server --test` la ricostruisce in debug.
>
> **⚠️ Fuori pista:**
> - **Indice dei testid nella scheda dell'app**, non previsto dall'analisi. Gli id templati con un codice in coda (`filter-currency-row-${item.code}`) avrebbero dato un selettore su una sola riga e portato il codice nell'export.
> - **Selettore riprogettato dopo la prima verifica dal vivo.** La prima versione (testid + tag + tutte le classi) prendeva **52 elementi** per il `div` di layout dentro un `th`, celle del corpo comprese: il conteggio accanto al selettore ha mostrato il problema subito. Si è passati alla versione per proprietà descritta sopra.
> - **Filtro allargato** alle dichiarazioni scavalcate: in scuro la palette filtrata era vuota, perché vinceva l'override P1.
> - **Contatore dei grafici:** dopo «Ripristina tutto» `chartInstances` valeva 1 (contava il passaggio di ripristino); ora vale 0 senza stato.
> - **`parseImport`:** la granularità `occurrence` vale solo per `css-literal`, come già facevano l'editor e il motore.
> - **Primo giro dello script:** il grafico era sotto la piega e il clic non colpiva nulla. Era un difetto dello script, non del prodotto: ora fa `scrollIntoViewIfNeeded`.
> - **Scanner:** 2–3 s di norma, una corsa a 7,8 s con la macchina carica.
> - **Slittamento di regola:** una modifica di testo (tipi JSDoc in `scan-colors.mjs`) fatta con `python3` di sistema invece che con lo strumento di modifica. Risultato corretto e verificato; le modifiche successive sono passate dallo strumento.

### Passo 6 — ripresa dopo il 5b ⏳ (14/10/2026 sera)

> **Note implementazione** (avvio):
> - **Tre sotto-agenti in parallelo**, su file disgiunti:
>   - `test-author` **unit**: completa `scanColors.test.ts` e scrive 13 file Vitest nuovi, più `src/routes/designer-lab/page.test.ts`. Usa solo Vitest, senza corsia;
>   - `test-author` **E2E + runner**: `frontend/e2e/designer-lab/designer-lab-{live,picker,neutral}.spec.ts`, il nuovo `scripts/test_runner/_frontend_designer_lab.py` e solo aggiunte a `_registry.py` e `_suites.py` (file condiviso ①). Usa la corsia 6152 in esclusiva mentre lavora;
>   - `docs-writer`: la pagina developer per il 5b. Valida con `mkdocs build` strict e `check-links`, senza corsia.
> - **Elenco esatto dei file unit**, uguale nei due brief, perché la registrazione e i file coincidano:
>   - `color`, `scanColors`, `vitePlugin`, `store`, `pick`, `exportFormat`, `catalogView`, `contrast`, `chartMapping`, `verifyExport`, `pickView`, `anchor` (jsdom), `elementRules` (jsdom), `designerLabImports.gate`;
>   - più `routes/designer-lab/page`.
> - **Verificato prima di scrivere i brief:** il runner costruisce il frontend in produzione (`_ensure_frontend_build`, `debug=False`), ma poi avvia `dev.py server --test`, che ricostruisce in debug quando la modalità non coincide. Quindi gli E2E girano davvero con il Lab, come diceva il kickoff.
> - **Backlog, sezione L:** aggiunte L-8 (file del componente dalla classe di scope) e L-9 (limiti noti del selettore).

> **⏸️ Finestra di quiete 21:25–22:45** (coordinatore, 21:14). G fa la misura finale del rumore della gallery: 2 gallery complete a 10 worker. In quella finestra, niente:
> - build, anche `front build --debug`;
> - Vitest, Playwright, server della corsia, `npm ci`;
> - sotto-agenti che li lanciano.
>
> Alle 21:15, ai tre sotto-agenti:
> - chiudere entro le 21:25 i comandi pesanti in corso; l'agente E2E ferma il proprio server e prova la porta libera;
> - nella finestra solo lettura e scrittura dei propri file, più Prettier, ruff e black sui propri file;
> - chiudere il turno con lo stato e riprendere solo al mio via dopo le 22:45.
>
> Stato alle 21:15: porta 6152 libera; in corso solo uno `svelte-check` dell'agente unit, partito da 11 s.
> `npm run lint:dead` (knip), lanciato prima della finestra, segnala due cose del Lab: `MULTI_COLOR_PROPERTIES` in `cssProps.ts` e due helper non usati dell'agente E2E (`pointOnItself`, `pickedProperty`). Gli altri avvisi sono preesistenti e fuori dal Lab.

> **Revisione statica durante la finestra** (solo lettura e scrittura; build e test rimandati a dopo le 22:45):
> - **knip:** `MULTI_COLOR_PROPERTIES` ora ha un uso vero. `picker/describe.ts` tipizza su di essa i valori di prova delle proprietà con più colori (`probeFor()`), così una proprietà nuova in quella lista deve avere il suo valore di prova.
> - **Scanner, `VALUE_LITERAL_RE`:** una `(` vale come inizio di un valore solo se è una parentesi di raggruppamento. Gli argomenti di una chiamata (`testid={fn('x')}`) non diventano più id statici.
>   - Controllo puntuale: 9 casi su 9, prima delle 21:25.
>   - Sull'albero reale parità, `testids` e `testid_prefixes` restano identici: oggi nessuna chiamata del genere.
> - **Chiavi dei blocchi `{#each}` ripetute.** In `vite dev` Svelte si ferma con `each_key_duplicate`; nella build di debug (compilata in produzione) il comportamento non è definito.
>   - «Aggancia a una variabile» di `ColorEditor` aveva **3 chiavi ripetute** (`--color-libre-beige`, `--color-libre-dark`, `--color-libre-green`: sono sia palette sia variabili definite). Difetto latente del passo 4, ora la lista passa da un `Set`;
>   - i candidati dell'ancora nell'editor (un'ancora importata può ripeterli) e le condizioni `@media` di una dichiarazione (possono ripetersi se annidate) ora hanno come chiave l'indice;
>   - `parseImport` tiene **una modifica per id**: una ripetuta sostituisce la precedente, con un avviso. Prima un export con due modifiche uguali dava due righe con la stessa chiave.
> - **Chiavi i18n:** tutte le chiavi statiche dei componenti del Lab esistono (130) e coprono tutti i valori dei modelli dinamici (`source.*`, `element.breadth.*`, `layer.*`, `scope.*`, `tab.*`, `cvd.*`). È un controllo utile perché le chiavi con il punto sfuggono al controllo dei tipi.
> - **Varianti importate:** passano dall'import senza validazione (passo 5). Ogni motore però valida da sé:
>   - le variabili, con il nome e `isSafeCssValue`;
>   - i fogli di stile e i grafici, con `resolveTarget`;
>   - le specializzazioni, con selettore sicuro, valore sicuro e proprietà ammessa.
>
>   Nessuna iniezione possibile. Non tocco altro.
>
> **Correzioni nate dal rapporto di `docs-writer`** (21:30–21:40, solo scrittura; verifiche puntuali in millisecondi con `node`, il resto dopo le 22:45):
> - **Dati che potevano ancora uscire.** Il rapporto ha trovato due strade per cui un valore di record finiva nell'export.
>   - **Test id che l'indice non conosceva:**
>     - **id costruiti negli script:** `kpi-unrealized-breakdown-${row.kind}-${currency}`, scritto in `KpiSection.svelte`;
>     - **prop `*TestId=`:** `optionTestId=`, `filterRowTestId=` e simili;
>     - **chiavi di oggetto:** `testId: 'x'` nelle configurazioni, circa 130 assegnazioni.
>
>     Correzioni:
>     - lo scanner ora indicizza anche le prop `*TestId=` del markup (`via: prop`) e le proprietà o variabili degli script il cui nome finisce in `testid`/`testId` con un letterale (`via: script`). Restano escluse le funzioni freccia, i confronti, i nomi `…Prefix` e le annotazioni di tipo;
>     - per un id ancora sconosciuto, `recordPrefix()` taglia prima del primo token che sembra un record: un numero intero, o un token con una maiuscola (`row-42`, `asset-row-42-menu`, `kpi-gain-EUR`). Le cifre dentro le parole non contano: 71 id statici ne hanno, come `risk-l2-weight`, e nessuno ha maiuscole;
>     - `testidSites` e il `testidKnown` di `verify-export` riconoscono un `prefisso*` che estende un prefisso del catalogo. Un id generalizzato non dà quindi un falso «test id mancante».
>   - **Rotte con parametri:** `routeOf()` usa l'id di rotta di SvelteKit (`page.route.id` da `$app/state`) senza i gruppi: un dettaglio dà `/assets/[id]`, mai l'id del record. Le rotte statiche non cambiano: `/transactions` resta `/transactions`.
>   - **Prove:**
>     - 17 casi su 17 per `testidValues` e `scriptTestidValues`;
>     - un componente sintetico dà esattamente le 8 voci attese, comprese le esclusioni (confronto, `…Prefix`, tipo, `hasTestId = true`);
>     - 10 casi su 11 per `recordPrefix`: l'undicesimo era una mia attesa sbagliata, perché `ab-` ha esattamente 3 caratteri, la soglia documentata;
>     - 8 casi su 8 per `testidKnown`;
>     - `routeOf` corretto su dettaglio, dashboard con `?tab=`, rotta senza id e radice.
>   - **Primo errore della regex:** `TESTID_SCRIPT_RE` all'inizio non riconosceva i nomi `testId`/`testid` senza nulla davanti, perché la classe iniziale consumava la `t`. Corretto con una parte iniziale facoltativa, dopo il caso sintetico.
> - **Chiusura della scheda del Lab:** su `pagehide` il Lab scrive `cancel` se sta aspettando un puntamento. Prima, chiudendo la scheda, le schede dell'app restavano col velo e la richiesta restava valida 5 minuti.
> - **Commento di `pick.ts` reso esatto:**
>   - un `result` chiude il puntamento in tutte le schede;
>   - un `cancel` chiude solo la richiesta che nomina, mentre la scorciatoia dà a ogni scheda un id proprio;
>   - cancellare la chiave chiude tutto.
> - **Etichetta P1:** «override !important del tema scuro», senza più nominare `app.css`. Il codice non controlla il file; il file giusto compare tra i candidati.
>
> **Assegnazione del coordinatore (21:4x)**, estensione di ①. Citare la categoria `front-designer-lab` nei 5 posti dove la documentazione elenca le categorie del runner:
> - `test-walkthrough/front-overview.md`;
> - `test-walkthrough/index.md`;
> - `test-walkthrough/api.md`;
> - `test-walkthrough/runner_architecture.md`;
> - `.github/instructions/frontend-testing.instructions.md`.
>
> Regole:
> - solo aggiunte, una riga per posto, senza toccare le righe vicine né riordinare le tabelle;
> - le scrive `docs-writer`;
> - `mkdocs build` strict e `check-links` dopo le 22:45;
> - se le pagine sono tradotte, basta `translate-stamp`;
> - un conflitto con altri che aggiungono righe si risolve sommando, e lo fa chi arriva secondo;
> - va nel prossimo checkpoint, con i 5 file elencati nell'handoff.
>
> Unica riga non aggiungibile: `index.md:195`, «All Frontend (front-utility → front-ai-export)». Ne cambia solo l'estremo, perché `all-frontend` ora esegue anche `front-designer-lab`. Lo segnalo nell'handoff.
>
> **Difetti latenti trovati da `test-author` unit** (nessuno compare nel codice di oggi), corretti alle 21:47–21:51 e verificati su casi sintetici:
> 1. **`!$isDark`** (store Svelte negato) perdeva il `!`, perché `\b` non coglie il confine tra `!` e `$`; l'indizio di tema risultava invertito. Ora le due regex usano `(?<![\w$.])`. Prova: 10 letterali sintetici su 10, anche nella forma su più righe di Prettier.
> 2. **`sourceVarValue()`** (passo 4):
>    - in scuro poteva usare una definizione radice solo chiara;
>    - in chiaro prendeva la prima non scura, anche se dopo veniva un `html.light`.
>
>    Ora prende la definizione del tema chiesto, altrimenti una condivisa, **mai quella dell'altro tema**; a parità vince l'ultima, come nella cascata.
> 3. **`commit()` del Lab:** se lo storage rifiuta la scrittura (pieno o disattivato), l'eccezione ora è gestita. Il Lab mostra `storageFailed` e tiene l'ultimo stato salvato; le altre schede non avrebbero mai visto quello nuovo.
> 4. **`TESTID_SCRIPT_RE`:** ora `(?<![\w$-])`. Un `data-testid="x"` dentro una stringa di script non entra più nell'indice, come dice la regola documentata.
> 5. **`testidKnown('*')`:** ora `false`, perché il prefisso è vuoto.
>
> **Corsia per dopo le 22:45:**
> 1. Prima l'agente unit: Vitest dei suoi file, `npm run check`, gate.
> 2. Poi l'agente E2E, con nessuno che modifica `frontend/src` nel frattempo: `_ensure_frontend_build()` ricostruisce in release se un sorgente è più nuovo della build, mentre il server della corsia serve la build di debug.
> 3. In parallelo `docs-writer`, solo `mkdocs build` e `check-links`.
> 4. Per ultimo l'evidenza di release, a server fermo.
>
> **Nota per il merge** (decisione del coordinatore, opzione (a)). Nei posti aggiornati da `docs-writer`:
> - `runner_architecture.md`: riga di `front-designer-lab`, totale e frase sotto;
> - `index.md:169`: conteggio delle categorie;
> - `index.md:195`: estremo della riga «All Frontend».
>
> Se nel frattempo un altro ha aggiunto una categoria, chi arriva per secondo **ricalcola** totale, frase e conteggi; non sceglie una delle due versioni.
>
> **Gallery A/B (N4), preparata; parte solo col via del coordinatore:**
> - Il server della gallery (`webServer` di Playwright → `dev.py server --test`) ricostruisce solo se cambiano i sorgenti o la modalità debug/release, non se cambia `LF_DESIGNER_LAB`. Per questo:
>   - **A, Lab spento:** `LF_DESIGNER_LAB=0 … dev.py front build --debug`. Prima e dopo la gallery, `grep -rl lf-designer-lab frontend/build` deve dare **0**: è la prova che la build servita era senza Lab;
>   - **B, Lab acceso:** `dev.py front build --debug`, marcatore presente.
>   - Gallery: `scripts/visual_review/gallery_snapshot.sh L-lab-off-<data>` / `L-lab-on-<data>` con `--checkout <worktree> --port 6152 --data-dir /tmp/librefolio-r2-l`, dopo `export PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`; cartella di lavoro predefinita del toolkit.
>   - Confronto: `gallery_tool diff $W/snapshots/L-lab-off-… $W/snapshots/L-lab-on-… --ignore-masks <maschere del rumore> --stability <stability.json>`. Le maschere sono quelle che il coordinatore indicherà dopo la misura finale di G.
>   - Atteso: `identical`, a parte il rumore sulle schermate `unstable`.
>
> **Workstream T approvato** (avviso del coordinatore, 21:56). La palette della designer diventa ruoli `--lf-<gruppo>-<nome>` in `lib/theme/tokens.css`, scritto solo da T, nella forma `:root, html.light` / `html.dark, .dark`. I componenti li usano con utility `*-lf-<nome>` da `@theme inline`.
>
> Decisioni di L:
> - **Selettore di elementi:** nessuna modifica, perché con `inline` la regola vincitrice legge già `var(--lf-…)`.
> - **Scanner, L1 e catalogo:** voce **L-10**, dopo che T-1 entra nella base. Comprende:
>   - le classi `lf-`, con la parità Python da decidere;
>   - l'alias `@theme inline` che va rediretto alla variabile vera;
>   - gli override L1 anche sui selettori del token.
>
>   Oggi `app.css` ha solo `@theme {`, non `inline`.
> - **«Mostra i rimasti indietro»**, proposta di T: voce **L-11**, dopo questo checkpoint. Il passo 6 resta verifica di ciò che esiste; la lista legacy la fissa T.
> - **Skill `designer-lab-apply`:** le modifiche ai ruoli `--lf-*` vanno in `tokens.css`, di T.
> - **Limite L1 da documentare subito:** gli override stanno su `html`, quindi un sotto-albero che ridefinisce una variabile tiene il suo valore.
>
> **Assegnazione del coordinatore (21:59), L-10 (1).** La riga `tw_custom_re` di `scripts/visual_review/color_inventory.py` è assegnata a L, come estensione di ④.
> - Appena T-1 entra nella base, `lf-` si aggiunge alla regex JS e a quella Python nello stesso cambio, una riga per parte.
> - Subito dopo si verifica la parità JS/Python sullo stesso albero.
> - I numeri di parità, prima e dopo, vanno nell'handoff.
>
> Approvati anche L-10 (2) e (3), L-11 nel backlog e la skill aggiornata.
>
> **▶️ Finestra chiusa in anticipo alle 22:20** (coordinatore: G ha finito; seguiranno solo rerun filtrati di G a 1 worker). Il DB della corsia è quello ricreato alle 19:5x, ancora presente, con la porta 6152 libera.
>
> Ripresa nell'ordine:
> 1. agente unit: Vitest, `npm run check`, gate;
> 2. in parallelo `docs-writer`: limite L1 «sotto-albero», `mkdocs build` strict e `check-links`;
> 3. agente E2E, solo correzioni ai propri file finché l'agente unit non ha finito di modificare `frontend/src`.
>
> Il test di export non deve più pretendere che `#64748b` sia anche un colore di grafico del catalogo.
>
> **Riscansione dopo tutte le correzioni** (`scan-colors.mjs`, 1,6 s):
> - parità, livelli ed etichette di tema **identici** al catalogo del passo 5;
> - indice dei testid:
>   - prima, solo markup: 1.828 id in 1.947 punti, 235 prefissi;
>   - ora: **1.887 id in 2.006 punti** (attr 1.708, prop 251, script 47) e **256 prefissi** (attr 224, prop 20, script 12);
>   - `kpi-unrealized-breakdown-` ora è indicizzato da `KpiSection.svelte:213` (`script`);
>   - 0 id anomali, nessun id statico con maiuscole.
>
> **Unit ✅ (22:25), `test-author`.** 15 file Vitest, **389 test** verdi in due giri completi; gate del repo 60/60; Prettier pulito.
> - Conteggi per file: `color` 23, `scanColors` 49, `vitePlugin` 20, `store` 23, `pick` 20, `exportFormat` 66, `catalogView` 18, `contrast` 11, `chartMapping` 13, `verifyExport` 20, `pickView` 45, `anchor` 30 (jsdom), `elementRules` 22 (jsdom), `designerLabImports.gate` 27, `routes/designer-lab/page` 2.
> - Le correzioni 1, 2, 4 e 5 sono fissate da test che sul codice vecchio fallirebbero (verifica a mano dell'agente). `commit()` è un componente, senza test unit.
> - Fuori dagli unit, coperti dagli E2E: `picker/describe.ts` e `picker/overlay.ts`, il comportamento di `client.ts`, i motori dal vivo, i componenti.
> - Piccoli helper puri fuori dal brief, da aggiungere quando serve: `applyVars`, `cssWithAlpha`, `declares()`, `downloadText`, la CLI dello scanner.
>
> **`npm run check` era rosso:** 6 errori di tipo JSDoc, latenti, in `verify-export.mjs`. `verifyExport.test.ts` è il primo file che lo importa, e così lo porta nel controllo dei tipi `checkJs`.
> - I fallback `{status: 'missing'}` si allargavano a `{status: string}`: ora sono tipizzati come `ReturnType<typeof locate>`.
> - `doc.changes.map` restituiva `any`: ora è tipizzato come array.
> - Dopo la correzione: `npm run check` → **0 errori, 0 avvisi**; `verifyExport.test.ts` 20/20.
>
> **Docs ✅ (22:23), `docs-writer`:**
> - `dev.py mkdocs build` strict → exit 0, nessuna riga WARNING o ERROR;
> - `dev.py mkdocs check-links` → exit 0, 95 link validi, 0 rotti;
> - nuovo limite noto «Variables redefined in a subtree» (L1 su `html`);
> - nessuna pagina ha traduzioni, quindi nessun `translate-stamp`;
> - righe cambiate nei 4 posti, prima e dopo:
>   - `front-overview.md`: 60, e la riga nuova 107;
>   - `index.md`: 169 «15 → 16 categorie, 8 → 9 frontend»; la riga nuova 188; 196 (era la 195), estremo «All Frontend» `front-ai-export` → `front-designer-lab`; la riga nuova 258;
>   - `runner_architecture.md`: la riga nuova 443 (`3 | 15 | 18 | 2`); il totale alla riga 449 (era la 448), 59/61/120/16 → 62/76/138/18; la frase alla riga 453 (era la 452), «21 rather than 16» → «23 rather than 18»;
>   - `frontend-testing.instructions.md`: la riga nuova 452.
>
>   `api.md` è tornato all'originale.
>
> **E2E:** via all'agente alle 22:26, con la corsia 6152 in esclusiva.
>
> **E2E ✅ (22:42), `test-author`, corsia 6152.** Comandi `dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l … front-designer-lab …`:
>
> | Azione | Esito | Tempo dei test / dell'invocazione |
> |---|---|---|
> | `live` (dopo la correzione) | 7/7 | 15,9 s / 55 s |
> | `picker` | 3/3 | 8,8 s / 38 s |
> | `--fresh-run --workers 1 … e2e` | 11/11 | 24,5 s / 1m13s |
> | `--fresh-run --workers 4 … e2e` | 11/11 | 19,4 s / 47 s |
> | `unit` | 15 file, 389/389 | 5,3 s / 7 s |
> | `--fresh-run … all` | 11/11 Playwright + 389/389 Vitest | 57 s |
>
> Poi `check-orphans`: **exit 0**, con 120 spec e 376 file unit tutti registrati.
> - Ogni giro ha stampato «Frontend build is up to date». Prove della build di debug: `.build-debug` vale `1`, il marcatore compare in 10 file di `build/_app/immutable`, e ogni test che apre il Lab verifica `data-catalog-hash`.
> - Nessun errore `tsc` nuovo sugli e2e; i 2 che restano sono preesistenti e fuori dal Lab. knip non segnala più nulla del Lab né di `e2e/designer-lab`. Prettier, ruff e black puliti sui file dell'agente.
> - Porta 6152 libera alle 22:42:19, provata con `lsof`.
>
> **⚠️ Fuori pista: difetto reale di L3 trovato dal primo `live` (deterministico, non instabile).**
> - **Sintomo:** `engine/charts.ts` ricordava ogni originale sotto la stringa prodotta (`produced`). Due originali mappati sulla stessa uscita condividevano una voce, e vinceva l'ultimo: dopo «Ripristina tutto», i `#fff` del grafico tornavano `#ffffff`.
> - **Caso grave:** due colori **diversi** portati allo stesso valore nuovo tornavano entrambi come uno dei due, finché l'app non ridisegnava il grafico. Anche il selettore riportava l'originale sbagliato.
> - **Correzione (22:47), `produce()`:** una stringa prodotta sta per **un solo colore**. Se l'uscita sta già per un colore diverso (chiave o alfa), il nuovo prende un'altra grafia dello stesso colore: un decimale di alfa in più, identica sul canvas. Le grafie dello stesso colore condividono l'uscita e tornano come la prima vista: è una differenza solo di grafia.
> - **Per i test:** nuovo export `forgetProducedColors()`.
> - **Test:** quello E2E ora confronta i colori per valore. `chartMapping.test.ts` aveva un caso che fissava la vecchia grafia unica (riga 125: due alfa diverse sulla stessa uscita) e va adattato; c'è anche un test di regressione da aggiungere. Entrambi sono stati chiesti a `test-author` unit.
>
> **Chiusura del passo 6** (22:48–22:55):
> - **`chartMapping.test.ts`, `test-author`:**
>   - `beforeEach` con `forgetProducedColors()`;
>   - il test delle alfa diviso in due;
>   - fissata la regola della prima grafia;
>   - 4 test di regressione: tre colori portati allo stesso valore tornano ognuno al suo originale, sia con `mapChartOption` sia con `chartPatch`; due alfa sulla stessa uscita; il caso misto `#fff`/`#ffffff`;
>   - il file passa da 13 a 18 test. Suite del Lab **394/394** (15 file), `npm run check` 0/0, gate 60/60, Prettier pulito.
> - **Commento di `produce()`:** oltre 32 colori diversi portati allo stesso valore, l'ultima grafia torna condivisa e vince l'ultimo, come prima della correzione. Caso non pratico, segnalato dall'agente.
> - **Suite completa della categoria sul motore corretto:**
>   - comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l --fresh-run --workers 4 --log-dir /tmp/libreFolio_L6_logs front-designer-lab all` → **exit 0**;
>   - Playwright **11/11** (13,3 s), Vitest **394/394**, le 5 azioni ✓;
>   - «Frontend build is up to date», `.build-debug` = `1`, marcatore presente in 10 file.
> - **Gate:**
>   - `dev.py test check-orphans` → **exit 0** (376 file unit e 263 file backend raggiungibili da `all`);
>   - `npm run lint:dead` (knip): nessun avviso del Lab né di `e2e/designer-lab`; gli altri sono preesistenti;
>   - `git diff --check` pulito.
> - **Release** (`npm run build`, exit 0), a server fermo:
>   - **0** file con `lf-designer-lab`;
>   - 0 con `lf-color-catalog/1`, `lf-testid-index`, l'indice dei testid, le stringhe del selettore, `DesignerLab` o `__lfDesignerLab`;
>   - nodo stub di 488 B **identico** a prima (`17.CmL9VVVP.js`);
>   - nessun `.build-debug`, 0 sourcemap, 24 MB.
>
>   `frontend/build` resta in release; `dev.py server --test` lo ricostruisce in debug da solo.
> - **Porta 6152 libera**, provata con `lsof`; nessun sotto-agente al lavoro.
> - **Delta per il checkpoint:** 26 file tracciati modificati, 28 file nuovi (7.446 righe), `+1.964/−197` sui tracciati.

## ✅ Checkpoint 2 committato (14/10/2026, 22:58)

- **Commit del coordinatore:**
  - `87ceceede` `feat(frontend): add Designer Lab element picker and tests`: 54 file, padre `150f2716a`;
  - `bb87b0ab7`, merge di `dev_release2` (`afea11fe2`). Porta solo documenti: lo spostamento del programma colori in `Phase_1/10_colorSystem`, il materiale della designer, i piani della 1.3, `meta.json` del toolkit. Niente in `frontend/`, runner, MkDocs o `.github`;
  - `93bf8c98a`, questo piano spostato qui.

  **HEAD `93bf8c98a6669072b0d53b68864b3123904ed86c`**, worktree pulito, verificato. Il controllo a campione del coordinatore dà unit del Lab 15 file e 394 test verdi.
- **Link dopo lo spostamento:**
  - riga 6 del piano: `../../BACKLOG_POST_1.2.md` → `../../../Phase_0/BACKLOG_POST_1.2.md`;
  - sezione L del backlog: 9 link da `55_colorSystem/…` → `../Phase_1/10_colorSystem/…`;
  - verifica con uno script che risolve ogni link relativo: 0 rotti nel piano e nella sezione L.

  Nel backlog restano link verso `55_colorSystem/` in altre sezioni, per esempio la 1857 di R (report 04): non sono miei e li segnalo al coordinatore.
- **Backlog:** aggiunta **L-12**, il runner che può ricostruire in release a metà giro. Proprietario: chi mantiene il runner; richiesta del coordinatore.
- **Gallery A/B (N4)**, decisioni del coordinatore:
  - **ordine (a):** commit fatto. Domani G entra in `dev_release2` **prima** delle gallery di L, perché corregge il prezzo live di Yahoo che sporcava le catture. Il coordinatore aggiorna la base di L con G, poi A e B girano sullo stesso albero, senza cambi di base fra l'una e l'altra;
  - **fascia oraria:** domani, dopo la misura finale di G, fissata dal coordinatore;
  - **maschere e `stability.json`:** quelle della misura finale di G, sul `dev_release2` che contiene G; il percorso arriva dal coordinatore;
  - **integrazione di L:** dopo la gallery A/B.
- **Dipendenza del test L3 dai colori del grafico della crescita:** la segna il coordinatore nella lista di controllo dell'integrazione di R.

**Stato:** in attesa. Prossime azioni, in ordine:
1. gallery A/B al via del coordinatore, dopo il suo aggiornamento della base con G;
2. L-10, quando T-1 è nella base, con la riga JS e la riga Python di `tw_custom_re` nello stesso cambio e la parità prima e dopo;
3. L-11 al via.
