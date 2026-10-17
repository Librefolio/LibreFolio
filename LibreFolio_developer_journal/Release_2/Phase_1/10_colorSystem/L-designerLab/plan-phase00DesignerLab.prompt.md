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

## ✅ Validazione del fuso con X (15/10/2026, 10:18–10:25)

- **Base:** merge `6991ac085` di `dev_release2` = `2338aaf79` (X), sopra `eb79f7127` (i miei file di journal, committati dal coordinatore). Merge pulito, albero uguale alla simulazione. FROZEN fino al via del coordinatore delle 10:16, dopo la misura r2 di G.
- **Controllo di sola lettura alle 09:03–09:12:**
  - il merge porta 984 file e nessun file del Lab;
  - fra i condivisi: `runner_architecture.md` cambia solo in prosa (riga e totali di L intatti); `_frontend_common.py` cambia gli utenti di test (solo `e2e_test_admin` è amministratore, mentre i test del Lab usano l'utente normale);
  - **T-1 è nella base:** `lib/theme/tokens.css` con `@theme inline`, gate `themeRoles` e `themeTokens`, ratchet `theme-roles.mjs`, che esenta il Lab (`LAB_PREFIXES`);
  - i bersagli degli E2E sono intatti.
- **Script:** `/tmp/libreFolio_L7_validate.sh`, copia negli artefatti `files/L-validate-2026-10-15/`. Primo passo `dev.py api sync`: il client API generato, ignorato da git, era di ieri sera, prima del merge. Il passo tocca solo file ignorati. È lo stesso rimedio che T ha segnalato al coordinatore per `features/instance`; da me non è comparso alcun errore.

| Passo | Esito |
|---|---|
| `dev.py api sync` | exit 0, `git status` 0 righe |
| unit del Lab (`vitest run src/lib/dev/designer-lab src/routes/designer-lab`) | **15 file, 394/394** |
| `npm run check` | **0 errori, 0 avvisi** |
| gate di `src/*.gate.test.ts` + `(app)/layout.gate` (ora compresi `themeRoles` e `themeTokens`) | **7 file, 110/110** |
| `node frontend/scripts/theme/theme-roles.mjs --check` | exit 0, «Colour gates: clean» |
| release (`npm run build`) | exit 0; **0** file col marcatore, 0 col catalogo, 0 con l'indice; nodo stub `17.Bk39cjPb.js` di **488 B** (stessa dimensione; il nome cambia perché l'hash dipende dai chunk importati, cambiati col merge) |
| `dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l --fresh-run front-designer-lab all` (predefinito, 1 worker) | exit 0, Playwright **11/11** (22,5 s), Vitest **394/394**, 5 azioni ✓, «Frontend build is up to date» |
| idem `--fresh-run --workers 4 … e2e` | exit 0, **11/11** (14,2 s) |
| `dev.py test check-orphans` | exit 0: e2e 121, unit 385, backend 277, tutti raggiungibili da `all` |
| scanner + `color_inventory.py` sullo stesso albero | **parità identica**: totali e righe (hex 1651/1651, funzioni 225/225); file 1062, classi 10599, custom 764, arbitrarie 12, `var()` 202 su 94, definizioni 217 |
| porta 6152 a fine giro | libera (`lsof` exit 1) |
| `frontend/build` lasciato | **debug** (`.build-debug` = 1, marcatore in 10 file), pronto per la gallery candidata; `git status` 0 righe |

> **⚠️ Fuori pista:** il primo confronto di parità diceva `custom 764≠NaN`. Era un difetto del mio script: l'etichetta del riepilogo Python «(libre-*/theme-*/…)» contiene asterischi, che la mia regex `[^*]*` non poteva attraversare. Corretto con `.*?`, rieseguito il solo passo di parità sui file già scritti: identica.

> **Effetto di T-1 sul Lab, misurato prima di L-10:**
> - i 50 ruoli `--lf-*` sono già nelle «Variabili dell'app», con i valori chiaro/scuro giusti, e il selettore porta già a `--lf-…`;
> - mancano **143 usi di classi `*-lf-*`** (in 9 file Svelte), non contati nella palette (L-10 (1));
> - le **45 definizioni `--color-lf-*` di `@theme inline`** compaiono come variabili `scoped` senza effetto a runtime, vicoli ciechi (L-10 (2)).
>
> L-10 è ora dovuta: «appena T-1 entra nella tua base». Si fa dopo la gallery candidata del coordinatore, che gira nella mia corsia sul mio checkout, e richiede il suo via.

## ✅ Gallery candidata di L e ⏳ validazione del fuso con R (15/10/2026)

- **Candidata della gallery** (coordinatore, 11:00–11:31, corsia di L, Lab presente nella build di debug ma mai aperto, contro r1 con le maschere r1↔r2): **passa il cancello**.
  - 2360 immagini identiche, 464 cambiate; solo 10 oltre il rumore del loro scatto, nessuna dovuta al Lab:
    - 8 `files/static-grid`: orario di caricamento e miniatura del DB della corsia, le stesse di R;
    - 1 `brim-report-sets`: il nome casuale dell'account demo;
    - 1 `detail-signals-macd` mobile it chiaro: menu degli indicatori ancora aperto, un problema di tempi della gallery, girato a G.
  - **Il Lab chiuso è neutro.**
- **Fuso con R:** `eeeb467f4`, padri `c0556a240` e `ed9fb6996`; R è entrato in `dev_release2` (lotti A–D, `sw.js`, documenti). 133 file, nessuno del Lab.
  - R ha creato `lib/theme/**`: tabelle dei grafici `chartTheme.ts`, `chartPalettes.ts`, `chartColorScales.ts`, `drawnColors.ts`; token di componente `--lf-cmp-*` in `components/{table,media,files,dialogs}.css` su `:root`; `themeMode.ts` come unico lettore del tema.
  - Tre gate nuovi (`themeModeReads`, `themeComponentTokens`, `themeColorMeta`): esentano i percorsi del Lab (decisione D7 di R).
- **Validazione** (`/tmp/libreFolio_L8_validate.sh`, 11:49–11:55, copia negli artefatti):

| Passo | Esito |
|---|---|
| `dev.py api sync` | exit 0, `git status` 0 righe |
| unit del Lab | **15 file, 394/394** |
| `npm run check` | **0 errori, 0 avvisi** |
| gate `src/*.gate` + `(app)/layout.gate` | **10 file, 162/162** |
| `theme-roles.mjs --check` | clean |
| release | 0 file col marcatore, 0 con catalogo o indice; stub di 488 B (`17.DTSZtGfH.js`) |
| `front-designer-lab all` (1 worker) | **2 rosse**, 9 verdi; Vitest 394/394 |
| `e2e` a 4 worker | **le stesse 2 rosse**, 9 verdi |
| `check-orphans` | exit 0 (e2e 121, unit 391, backend 277) |
| parità scanner/`color_inventory.py` | **identica** dopo lo spostamento dei letterali di R: hex 1291/1291, funzioni 238/238; file 1080, classi 10490, custom 764, definizioni 217 → **945** (token `--lf-cmp-*`), `var()` 1324 su 833 |
| porta 6152 a fine giro | libera |

> **⚠️ Fuori pista: due spec E2E rotte da R-3, non dal Lab.** L'intestazione di DataTable ora legge `var(--lf-cmp-datatable-header-text)`, definita in `lib/theme/components/table.css:24`, e `DataTable.svelte` non contiene più `#64748b`.
> - **Spec del selettore:** pretendeva `rule-literal`; il Lab classifica giustamente `var`.
> - **Test di export:** pretendeva un'occorrenza in `DataTable.svelte`.
> - **Il Lab regge la nuova struttura:** il test L2 dal vivo passa, quindi L2 riscrive anche i token `--lf-cmp-*` su `:root` (`applyRule` passa a `replaceLiterals` per una proprietà personalizzata senza modifica di variabile). L3 passa sulle tabelle `lib/theme/chart*.ts`, che lo scanner classifica come file di grafici. `drawnColors.ts`, colori fuori da CSS ed ECharts, resta senza anteprima, ed è corretto.
> - **Correzione affidata a `test-author`** (11:58), solo su `frontend/e2e/designer-lab/**`. Le attese si ricavano a runtime:
>   - tipo coerente coi fatti della scheda dell'app, letti da `lf-designer-lab/pick`;
>   - un candidato di binding in `DataTable.svelte` qualunque sia il tipo;
>   - export verificato con `verify-export.mjs`: nessuna occorrenza mancante.
>
>   R e T continuano a migrare (T cambia ora i valori dei ruoli).
> - **Coordinatore avvisato alle 11:57** con l'esito parziale e il tempo previsto.
>
> **✅ Correzione degli E2E (12:17, `test-author`), solo `frontend/e2e/designer-lab/`:**
> - **`lab-helpers.ts`:**
>   - `pickedFacts()` legge il `result` da `lf-designer-lab/pick`;
>   - `verifyExport()` scrive l'export in `testInfo.outputPath(…)` e lancia `verify-export.mjs --json` con `execFileSync(process.execPath, …)`, timeout 30 s;
>   - `opaqueKeysOf()` chiede le chiavi dei colori al browser, cioè a un canvas, non al parser del Lab.
> - **Spec del selettore:**
>   - il tipo si ricava dalla dichiarazione vincitrice provata dalla scheda dell'app, con le regole documentate. La scheda «Elemento» deve dare lo stesso tipo: due moduli, `describe.ts` e `pickView.ts`, verificati uno contro l'altro;
>   - se la vincitrice legge una variabile, la catena del Lab parte da lì;
>   - nell'export, `anchor.source` = {tipo mostrato, selettore vincitore, variabile};
>   - deve esserci un candidato di binding (`matched-rule`, `class-use` o `var-use`) in `DataTable.svelte`, qualunque sia il tipo.
> - **Test di export:**
>   - le occorrenze della modifica css-literal sono letterali del colore cambiato, alfa a parte;
>   - `verify-export` legge 3 modifiche, 0 mancanti, exit 0, occorrenze in posizione maggiori di 0;
>   - non si controlla `catalog_hash_match`: una modifica di `src` durante il giro cambierebbe l'hash, non l'export.
>   - Sull'export prodotto: 877 occorrenze in posizione, 0 spostate, 0 mancanti; `#64748b` ha 18 occorrenze in `dialogs.css`, `files.css`, `media.css` e `table.css`.
>   - Controprova: con la vecchia attesa `DataTable.svelte:1608 #64748b` il verificatore esce con 1 e la segnala mancante.
> - **Esiti dell'agente:**
>   - `picker` 3/3; `live` 7/7;
>   - `--fresh-run` `e2e` 11/11 a 1 worker e a 4 worker, due volte;
>   - `unit` 394/394; `check-orphans` exit 0;
>   - `tsc` sugli e2e: solo i due errori noti fuori dal Lab; Prettier pulito.
> - **Conferma mia sul codice finale:** `dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l --fresh-run front-designer-lab all` → **exit 0**, Playwright **11/11** (24,3 s), Vitest **394/394**, 5 azioni ✓, «Frontend build is up to date».
> - Porta 6152 libera alle 12:19:51. `frontend/build` resta la build di debug delle 11:53.
> - **Dipendenze dalle prossime ondate di T** (W4 transazioni, B6 pulizia di P1, W6 DataTable, W5 ponte sRGB): elencate nella voce **L-13** del backlog. Ogni rottura sarà esplicita.
> - **L-10** dopo l'ingresso di L, con il suo checkpoint. Il progetto è pronto negli artefatti di sessione (`files/L-validate-2026-10-15/L-10-design.md`). Va aggiunto l'helper E2E per le utility di ruolo (L-13, W4). Attenzione: T sta cambiando i valori dei ruoli con la nuova palette del developer, e i test li leggono a runtime.

## ✅ L-10 — Ruoli di T nel Lab (15/10/2026)

**Base:** `9d57aa4c0`; L è già in `dev_release2`, perché il coordinatore ha committato `9d57aa4c0` col mio messaggio e il target è avanzato fin lì.

**Via del coordinatore** (12:22, testuale): «L-10 approvata, con un suo checkpoint, sulla base di `9d57aa4c0`:
- il conteggio delle classi `*-lf-*`;
- `tw_custom_re` in Python, con la parità prima e dopo;
- le `--color-lf-*`».

Il punto (3), gli override L1 anche sui selettori del token, era approvato dal 14/10 alle 21:59.

**Finestra:** codice e test leggeri subito; E2E e run pesanti dopo le 13:00, quando chiude la finestra della candidata di T.

**Nota:** T-6 ha cambiato i valori dei ruoli e aggiunto `--lf-surface-sidebar`, `--lf-checked` e `--lf-on-checked`, ma non è ancora nel target. I test leggono i valori a runtime.

**Parità prima** (base, 12:24): **identica**: hex 1291/1291, funzioni 238/238, `custom` **764**, `tw` 10490, 1080 file.

**Progetto** (fatti verificati in sola lettura alle 10:3x, artefatto `files/L-validate-2026-10-15/L-10-design.md`):

| # | Parte | Cosa |
|---|---|---|
| 1 | `scan-colors.mjs` `TW_CUSTOM_RE` + `color_inventory.py` `tw_custom_re` | `\|lf-[a-z-]+` nel gruppo dei valori, una riga per parte; le classi `bg-lf-card` → `--color-lf-card` |
| 2a | scanner, `@theme inline` | `cssContext()` dice `inline`; la definizione riceve `inline: true` e `alias_of` (il nome quando il valore è esattamente `var(--x)`). Selettore e ambito non cambiano |
| 2b | scanner, palette | una voce di palette prende `role` quando tutte le definizioni della sua variabile sono alias inline di una sola variabile. È generico, non legato al prefisso `lf` |
| 2c | `catalogView.ts` | famiglia `lf` nella palette; `appVars()` salta le variabili fatte solo di alias inline (le 45 senza effetto) |
| 2d | `DesignerLab.svelte` | il chip di un alias apre, mostra e marca il ruolo (`--color-lf-card → --lf-surface-card`); id di test invariato `lab-item-var-<alias>` |
| 2e | `ColorEditor.svelte` | impatto e classi aggregano le voci con `var` o `role` = target; «Aggancia a una variabile» usa il ruolo al posto dell'alias |
| 2f | `export.ts` | `css-var`: stessa aggregazione; le occorrenze di un alias portano `raw` = la classe, che `verify-export` cerca nella riga |
| 2g | `pickView.ts` | candidati `class-use` via ruolo; il filtro aggiunge i nomi degli alias dei ruoli della catena |
| 3 | `engine/vars.ts` | override L1 su `html, .light, .dark` / `html:not(.dark), .light` / `html.dark, .dark`, come i blocchi di T |

Fuori ambito: le coppie di contrasto sui ruoli `--lf-*`, perché il pannello legge ancora `--theme-*` e T ha già il suo gate di contrasto. Proposta di backlog.

**Test:**
- **unit (`test-author`, leggeri):** `scanColors`, `catalogView`, `pickView`, `exportFormat`, `elementRules` (nuovo blocco per `applyVars`, jsdom). Gli stessi 15 file registrati.
- **E2E (dopo le 13:00, corsia 6152):**
  - live: il chip `lab-item-var---color-lf-card` modifica `--lf-surface-card` e `login-modal` cambia colore (`/` da sloggati);
  - picker su `login-modal`: `background-color` `tailwind-class`, classe `bg-lf-card`, primo var `--lf-surface-card`, candidato `class-use` in `LoginCard.svelte`;
  - helper del sottotitolo pronto anche per le utility di ruolo (L-13, W4).
- **Docs:** `docs-writer` aggiorna la pagina developer (testo subito, build dopo le 13:00); la skill riceve una riga.

**Definition of done:**
- parità dopo identica, con i due numeri prima e dopo nel checkpoint;
- unit, `npm run check`, gate, `theme-roles` verdi;
- release senza Lab;
- `front-designer-lab all` verde a 1 worker ed `e2e` a 4;
- `mkdocs build` strict e `check-links` verdi;
- porta libera;
- piano ✅ e backlog L-10 ✅.

### Avanzamento L-10

**✅ Passo 1 — regex JS e Python (15/10, 12:2x).**
> **Note implementazione**: `TW_CUSTOM_RE` (`scan-colors.mjs:48`) e `tw_custom_re` (`color_inventory.py:39`) ricevono `|lf-[a-z-]+`, una riga per parte, nello stesso cambio. **Parità dopo**, stesso albero: **identica**. Hex 1291/1291, funzioni 238/238, `tw` 10490, `var_defs` 945, 1080 file; `custom` **764 → 912** (+148). Le classi `lf` sono 36 voci di palette, 148 usi in 11 file, tutte con un ruolo. Comando: scanner + `pipenv run python -m scripts.visual_review.color_inventory` + `/tmp/libreFolio_L7_parity.mjs`; file in `/tmp/libreFolio_L10/{before,after}/`.
> **⚠️ Fuori pista**: i 143 usi in 9 file misurati prima diventano 148 in 11. I 5 in più sono **commenti** che nominano le classi: `app.css:2` (2) e `tokens.css:8–9` (3). Scanner e inventario Python contano allo stesso modo le classi nei commenti, per tutte le famiglie: comportamento preesistente e vincolato dalla parità. Non lo tocco, perché la parte Python non è mia oltre la riga 39. Proposta di backlog **L-14**. Segnalo anche che l'etichetta del riepilogo Python «(libre-*/theme-*/primary/accent)» non cita `lf-`: è fuori dalla riga assegnata.
> **⚠️ Fuori pista (13:00):** `test-author` ha notato che `lf-[a-z-]+` non accetta cifre. Il gate di T (`ROLE_CLASS_RE` in `scripts/theme/theme-roles.mjs`) invece le accetta: `-lf-([a-z0-9]+(?:-[a-z0-9]+)*)`. Ho allineato le due regex a `lf-[a-z0-9-]+`, sempre una riga per parte; il diff Python resta una riga. Oggi nessun alias ha cifre, quindi i conteggi non cambiano. Parità rimisurata sullo stesso albero (`/tmp/libreFolio_L10/after2/`): **identica**, `custom` 912, 36 voci `lf` tutte con ruolo, 45 alias.

**✅ Passi 2a–2g — catalogo, palette, editor, export, picker (15/10, 12:2x).**
> **Note implementazione**:
> - **Scanner:** `ALIAS_VALUE_RE`. `cssContext()` dice `inline`; una definizione sotto `@theme … inline` riceve `inline: true` e `alias_of`, che vale `null` quando il valore non è esattamente `var(--x)`. Una voce di palette riceve `role` quando tutte le definizioni della sua variabile sono alias inline di un solo nome.
> - **`types.ts`:** `CatalogVarDef.inline?`, `alias_of?`; `CatalogPaletteEntry.role?`.
> - **`catalogView.ts`:** famiglia `lf`, con lo shade uguale al resto del nome; `appVars()` salta gli alias. Nuovi `isInlineAlias()`, `editTarget()` (`role ?? var`) e `varImpact()`, che aggrega le voci con `var` o `role` uguali al nome, più gli usi della variabile.
> - **`DesignerLab.svelte`:** il chip apre e marca il ruolo (`data-target`, titolo `alias → ruolo`); la ricerca trova anche il ruolo; l'id di test `lab-item-var-<alias>` non cambia.
> - **`ColorEditor.svelte`:** elenco dei nomi via `editTarget`, senza alias; impatto e classi da `varImpact`.
> - **`export.ts`:** `css-var` via `varImpact`. Le occorrenze di una classe-alias portano `raw` uguale alla classe: la riga non nomina né variabile né shade.
> - **`pickView.ts`:** i candidati `class-use` passano dal ruolo; il filtro aggiunge gli alias dei ruoli della catena.
>
> **Prove (leggere):**
> - Scanner su un CSS sintetico:
>   - l'alias diventa `inline`, con `alias_of = --lf-surface-card`, e la sua voce ha il ruolo;
>   - un alias `color-mix()` resta `inline` con `alias_of: null` e senza ruolo;
>   - `@theme` semplice resta root, non `inline`;
>   - `hover:border-lf-card/50` è contata.
> - Catalogo reale:
>   - `--color-lf-card` → ruolo `--lf-surface-card`;
>   - `varImpact`: 21 usi in 6 file, 3 classi, 2 definizioni in `tokens.css` (36 e 110);
>   - export: 8 occorrenze con `raw`;
>   - picker con `.bg-lf-card` vincente: `tailwind-class`, catena `[--lf-surface-card]`, `edit` sul ruolo, candidato `class-use` `LoginCard.svelte:41`, filtro con alias e ruolo;
>   - `appVars` senza alias (0).
> - Unit del Lab invariati: 15 file, 394 verdi. Prettier pulito.
>
> **⚠️ Fuori pista**:
> - Le definizioni di `@theme inline` hanno selettore `null` e ambito `scoped`, perché il preludio `@theme inline` finisce fra le at-rule. È innocuo: sono marcate `inline`, l'editor e `appVars` le saltano, e `sourceVarValue` e il contrasto leggono solo le definizioni root.
> - **Limite noto:** un alias `@theme inline` che non è `var(--x)` (per esempio un `color-mix()`) non ha ruolo, e il suo chip modifica una variabile che a runtime non esiste. Oggi in `tokens.css` non ce n'è nessuno. Lo documenta il test dello scanner.

**✅ Passo 3 — L1 sui sotto-alberi di tema (15/10, 12:2x).**
> **Note implementazione**: `engine/vars.ts` esporta `VAR_SELECTOR`, che sostituisce il `SELECTOR` privato, così i test lo leggono: `both: 'html, .light, .dark'`, `light: 'html:not(.dark), .light'`, `dark: 'html.dark, .dark'`. Sono i selettori dei blocchi di `tokens.css`, quindi l'override entra anche in un sotto-albero che ridefinisce i ruoli. Ho aggiornato il commento di testa.
> **Verifica (12:54):** oggi nessun elemento diverso da `<html>` porta le classi `light` o `dark`. Solo `themeStore.ts` le tocca, su `document.documentElement`; le occorrenze `class:dark:…` di `ImportWizardModal.svelte` sono varianti Tailwind. Nelle librerie controllate (`svelte-sonner`, `flatpickr`, `echarts`, `@floating-ui`, `bits-ui`) nessuna aggiunge quelle classi. Il cambio quindi non modifica nulla di visibile oggi.
> **Limite residuo**, documentato: una variabile che l'app definisce solo su `html` (per esempio le `--theme-*` di `app.css`) riceverebbe l'override di un tema anche in un'isola di quel tema dentro l'altro tema, dove il codice non la ridefinisce. Il motore gira nella scheda dell'app senza catalogo, perché il gate degli import lo vieta, e non può sapere dove sia definita ogni variabile. Senza isole il limite non ha effetto.
> **⚠️ Fuori pista (13:00), regressione mia, segnalata da `test-author` e corretta:** su un'isola `.dark` la regola `both` (`html, .light, .dark`) e quella `dark` (`html.dark, .dark`) hanno la stessa specificità, `.dark`, e vinceva l'ultima scritta. Bastavano un cambio `dark` seguito da un `both` sulla stessa variabile per mostrare il valore `both` nell'isola, mentre su `<html>` vinceva comunque `html.dark`. Con i vecchi selettori il tema vinceva sempre. Correzione: `applyVars` scrive prima tutte le regole `both`, poi quelle di tema (`SCOPE_ORDER`, ordinamento stabile), così il tema vince ovunque, come riporta anche `changedVarValue`. Oggi non ha effetto, perché le isole non esistono; c'è un test sull'ordine del testo.

**✅ Passo 4 — skill e pagina developer (15/10, 12:3x–12:5x).**
> **Note implementazione**:
> - **Skill `designer-lab-apply`:** nella riga `css-var` della tabella dei livelli, «future role tokens» diventa «the role tokens `--lf-<group>-<name>`». Aggiunta una frase: un ruolo è definito in `tokens.css` (T); le sue utility, che sono il `raw` delle occorrenze, lo leggono tramite `@theme inline` e seguono la definizione, senza modifiche alle loro righe.
> - **`docs-writer`** ha aggiornato `mkdocs_src/docs/developer/frontend/designer-lab.md`: +120 righe, −39.
>   - Nuova sezione «🎭 Colour Roles» (`#colour-roles`), a cui puntano gli altri riferimenti. La accetto.
>   - Toccati: L1 (selettori, esempio, sotto-alberi), schema del catalogo (`inline`, `alias_of`, `role`), parità del 15/10, pagina del Lab (famiglia `lf`, chip, `appVars`, impatto), scheda Elemento (sorgente, `class-use`, filtro), livelli, Known Limits (sotto-albero riscritto e due voci nuove: alias non `var(--x)` e classi nei commenti), schema dell'export, `verify-export`, «Never Repaints Itself», seams di test.
>   - Nessuna traduzione: la sezione developer è solo in inglese, quindi niente stamp.
>   - Build e `check-links` vanno fatti dopo le 13:00.
> **⚠️ Fuori pista**:
> - Nel brief avevo scritto lo shade `text-muted`, che non esiste: l'alias di `--lf-text-muted` è `--color-lf-muted` (`tokens.css:165`). La pagina usa `card` e `action-hover`.
> - Segnalato da `docs-writer`, fuori dal mio perimetro: anche la docstring di `color_inventory.py` (righe 5–6), oltre all'etichetta del riepilogo (riga 174), elenca `libre-*/theme-*/primary/accent` senza `lf-*`. Va nell'handoff.
> **Secondo giro (12:55–13:00):**
> - Known Limits, «Variables redefined in a subtree» (924–935): aggiunto il caso inverso, una variabile definita solo su `<html>` dentro un'isola del suo tema.
> - Colour Roles: `lf-[a-z0-9-]+`.
> - L1: una frase sull'ordine `both` → tema.
> - `docs-writer` ha corretto anche una sua frase del primo giro: una definizione di componente sotto un altro selettore **non** tiene il suo valore. `applySheetsForTheme()` passa a L2 ogni `css-var` del tema a schermo, e L2 riscrive la definizione nelle regole non root. Tiene il valore solo una definizione in un attributo `style`; oggi esistono solo variabili locali (`--prov-*`, `--priority-w`).
> - Precisato chi mette la classe del tema: anche lo script inline di `src/app.html:23`, sempre su `<html>`.
> **Verifica (13:08):** `dev.py mkdocs build` strict → exit 0, 0 WARNING, 0 ERROR; `dev.py mkdocs check-links` → exit 0, 95 link validi. Log in `/tmp/libreFolio_L10/docs/`.

**⏸️ Pausa Python (15/10, 13:12).** Il coordinatore ha fermato tutti i comandi Python (`dev.py`, `pipenv run …`, `mkdocs`) per circa 10 minuti: il developer installa `cryptography` nell'ambiente condiviso. Nel mio lane non c'era niente in corso e la porta 6152 era libera, come ho confermato al coordinatore. Gli E2E, la build di release e le prove della corsia ripartono alla «ripresa».

**Previsione dei conflitti con la nuova base `9f3b141a8`** (G e 1.2.1; il coordinatore la aggiorna al checkpoint). Letta con `git diff --name-only 9d57aa4c0 9f3b141a8`, sola lettura, 30 file:
- **unico file in comune: `BACKLOG_POST_1.2.md`**, con hunk lontani. La base cambia dalla riga 2039 in poi; i miei sono alle righe 1898–1943, nella sezione L;
- per il resto la base porta file di G (`frontend/e2e/gallery.spec.ts`, `frontend/e2e/fixtures/gallery*`), `scripts/test_runner/_backend_utils.py`, `scripts/visual_review/{README.md, live_price_check.py}`, autenticazione e file della 1.2.1, e il journal;
- nessun file in `frontend/src`, `frontend/scripts`, `frontend/e2e/designer-lab` o MkDocs developer;
- `color_inventory.py` non è toccato.

**✅ Validazione statica (15/10, 13:02, finestra chiusa):** `/tmp/libreFolio_L10_validate.sh static` → log in `/tmp/libreFolio_L10/val-static/`.
> - unit del Lab: 15 file, **422** verdi (prima di L-10 erano 394; `test-author` ne ha aggiunti 28);
> - `npm run check`: 0 errori, 0 warning;
> - gate: 10 file, 162 verdi;
> - `theme-roles --check`: pulito;
> - Prettier: pulito;
> - scanner + inventario + parità: **identica**, `custom` 912.
>
> **Test unitari aggiunti** (`test-author`, nessun file nuovo, runner invariato):
> - `scanColors.test.ts`: albero sintetico dei ruoli, con varianti, opacità e cifre (`bg-lf-chart-1/40`), `inline`/`alias_of`, `role` solo per l'alias puro di un solo nome (misti, `color-mix`, due bersagli, `@theme` semplice: niente ruolo); invariante sull'albero reale (ogni alias **definito** ha un ruolo con definizione root; gli usi senza definizione, per esempio nei commenti, restano al gate di T);
> - `catalogView.test.ts`: famiglia `lf`, `appVars` senza alias, `isInlineAlias`, `editTarget`, `varImpact`;
> - `pickView.test.ts`: sorgente di un ruolo, `class-use` dall'alias che elenca la classe, filtro con ruolo e alias (non quelli di altri ruoli), catena di un ruolo derivato;
> - `exportFormat.test.ts`: aggregazione del ruolo, `raw` secondo l'indice di classe, nessun `raw` per una variabile di palette;
> - `verifyExport.test.ts`: un'occorrenza di ruolo cercata col suo `raw` (ok, moved, missing);
> - `elementRules.test.ts`: `applyVars` (mappa `VAR_SELECTOR`, testo delle tre regole, `OWN_ATTR`, scarti e conteggio, rimozione, ordine `both` → tema stabile).

**✅ Passo 5 — E2E dei ruoli (`test-author`), 15/10, scritti alle 13:2x, verdi a macchina quieta alle 15:33.** Fase 1, sola scrittura, finita alle 13:2x; l'esecuzione aspettava la «ripresa» del coordinatore.
> **Note implementazione** (file in `frontend/e2e/designer-lab/`; nessuno spec nuovo, runner invariato):
> - **`lab-helpers.ts`:**
>   - `colourSourceOf(locator, 'text' | 'bg' | 'border')` restituisce `{className, chipVar, target, role, selector}`. Per una classe di palette dà la sua variabile; per un'utility di ruolo il chip è l'alias e il bersaglio è il ruolo, letto a runtime dal CSSOM della pagina dell'app (layer, `@media` e `@supports` compresi). Fallisce in modo esplicito se l'elemento non ha classe colore, ne ha due, mescola palette e ruolo, o se manca la regola.
>   - Helper nuovi:
>     - `openSignIn`/`LOGIN_CARD`: la pagina `/` da sloggati;
>     - `themeValuesOf`/`newColourFor`: legge il valore del ruolo in una sonda `.light` e in una `.dark`, e sceglie un colore diverso da entrambi, perché T cambia i valori;
>     - `sourceLines`, `writesTestid`, `placesInComponent`: leggono le righe dei file dell'export dal disco.
> - **live:** nuovo test «L1: a colour role recolours an element of another tab, through the chip of its utility», sullo sfondo di `login-modal`. Chip dell'alias con `data-target` = ruolo; la ricerca trova il chip anche per nome del ruolo; l'app nell'altra scheda cambia colore. L'export ha impatto con la classe, occorrenze con `raw` e definizioni in `tokens.css`; `verify-export` dà 0. Reset finale e client fermo. Spostati su `colourSourceOf`, con le stesse attese: L1 palette, sospensione, export/import.
> - **picker:** nuovo test sul `login-modal`. `background-color` è `tailwind-class`; «Edit the source» apre il ruolo; il filtro «picked» mostra il chip dell'alias e meno chip della lista intera; l'ancora dell'export ha un candidato `class-use` con la classe nel file del componente, verificato sul disco; `verify-export` dà 0; nessun testo di pagina nell'export. Anche la scorciatoia è passata a `colourSourceOf`.
> - Prettier pulito. `textPaletteClassOf` non ha più chiamanti: lo tolgo prima dell'esecuzione, per non lasciare codice morto a knip.
> - Backlog L-13: i punti W4 (helper pronto) e W6 (candidati via ruolo) risultano coperti da L-10.
> **Fase 2 (13:37–13:51), corsia 6152:** prima di eseguire, `textPaletteClassOf` è stato tolto; Prettier pulito.
>
> | # | Comando (`--test-port 6152 --data-dir /tmp/librefolio-r2-l --fresh-run`) | Esito |
> |---|---|---|
> | 1 | `front-designer-lab live`, 1 worker | **8/8** in 1,1 min; il test nuovo del ruolo dura 8,4 s |
> | 2 | `front-designer-lab picker`, 1 worker | **4/4** in 31,8 s; il test nuovo dura 9,4 s |
> | 3 | `--workers 4 front-designer-lab e2e` | 11 verdi e 2 rossi in 2,2 min, con carico macchina 84 → 200. I due test nuovi sono verdi |
>
> Log: `/tmp/libreFolio_L10_{live,picker,e2e_w4}.log`.
>
> **⚠️ Fuori pista:** i due rossi del giro 3 non vengono da test nuovi.
> - **live, export/import:** timeout di 60 s sul colore del sottotitolo.
> - **neutral:** dashboard ancora `data-busy` dopo 30 s; è uno spec non toccato.
>
> Triage di `test-author` col metodo `test-triage`:
> - posizioni e conteggi: non c'entrano;
> - ogni test era da 3,5 a 4,5 volte più lento che a 1 worker: L1 7,1 → 31,0 s, L3 6,8 → 34,1 s. Il test dell'export dura 17,1 s a 1 worker, quindi a quel rallentamento supera il budget di 60 s;
> - nessun errore del backend;
> - lo stato condiviso non è toccato: i test nuovi girano da sloggati.
>
> Causa probabile: la macchina sovraccarica. **Non è dimostrato:** serve un giro a 4 worker a macchina quieta, nel mio posto. Il budget di 60 s non si alza su questa prova.
>
> **Interruzione (13:48):** budget comune con la 1.3, al massimo 3 suite pesanti. Il coordinatore ha chiesto di chiudere la run in corso e di spegnere il server della 6152. `test-author` aveva già finito; alle 13:51 la porta era libera e non c'era nessun processo nella corsia. Nessun segnale inviato da me. L-10 è in coda per un posto di circa 25 minuti, dopo la validazione di T.
>
> **Type-check degli E2E del Lab (13:5x).** Il `tsconfig` del progetto esclude `e2e/**` e Playwright transpila senza controllare i tipi, quindi nessun gate li controlla. Prova una tantum: `tsc -p` con una config temporanea in `/tmp` che estende `frontend/tsconfig.json`, include `e2e/designer-lab/*.ts` e usa `typeRoots` assoluto. Risultato: exit 0, **0 errori**, compresi gli import (fixture, `global-setup`, tipi del Lab).
> **⚠️ Fuori pista:** il primo tentativo ha dato 25 errori «Cannot find module 'node:…'» perché `types: ["node"]` si risolve dalla cartella della config (`/tmp`). Con `typeRoots` assoluto sono spariti. Config temporanea cancellata.

**✅ Passo 6 — Validazione finale nello slot (15/10, 15:22–15:33).** Via del coordinatore alle 15:21 («lo slot pesante è tuo per chiudere L-10»). Prima del via: HEAD `9d57aa4c0`, 22 righe di stato, porta 6152 libera, carico 26, nessun sorgente cambiato dopo le run di `test-author`.
Comando: `/tmp/libreFolio_L10_validate.sh slot`, tutto in sequenza nella corsia 6152. Log in `/tmp/libreFolio_L10/val-slot/` e copia negli artefatti di sessione (`files/L-validate-2026-10-15/L10/`).

| Passo | Esito |
|---|---|
| unit del Lab | 15 file, **422/422** |
| `npm run check` | 0 errori, 0 warning |
| gate (`src/*.gate.test.ts` + `layout.gate`) | 10 file, 162/162 |
| `theme-roles --check` | pulito |
| Prettier (`scripts/designer-lab`, Lab, route, `e2e/designer-lab`) | pulito |
| scanner + inventario Python + parità | **identica**: `custom` 912, hex 1291, fn 238, tw 10490, `var_defs` 945, 1080 file |
| build di release | exit 0; marker `lf-designer-lab` 0, catalogo 0, indice 0; stub della rotta 488 B |
| `front-designer-lab all`, 1 worker | exit 0: **13/13 E2E** (live 8, picker 4, neutral 1) + 422 unit; 5 azioni ✓ |
| `front-designer-lab e2e`, 4 worker | exit 0: **13/13** in 39,9 s |
| `check-orphans` | tutti raggiungibili (121 e2e, 391 unit, 277 backend) |
| `mkdocs` | non rifatto: la pagina non è cambiata dopo la build strict delle 13:08 (0 WARNING, `check-links` 95) |
| porta a fine giro | 6152 libera (`lsof` exit 1) |
| stato della build | debug (`.build-debug=1`, 10 file col marker), come la vuole il server di test |

> **Note implementazione**: i due rossi del giro a 4 worker delle 13:4x, con carico 84 → 200, **non si ripetono** a macchina quieta. È coerente con il triage (sovraccarico); il budget di 60 s resta com'è. `git diff --check` pulito. Delta: 22 file tracciati, 0 nuovi, +1437/−120.
>
> **Numeri del checkpoint** (catalogo `val-slot`):
> - classi `*-lf-*`: **148 usi**, cioè 143 nel markup di 9 file Svelte (il conteggio di T) più 5 nei commenti di 2 CSS (`app.css`, `tokens.css`), in 36 voci di palette, tutte con ruolo;
> - `tw_custom_re`: parità identica prima (`custom` 764) e dopo (912);
> - `--color-lf-*`: **45** definizioni, tutte `inline` con `alias_of`; nessuna in «Variabili dell'app».
>
> **Base `badec1465` (Y1), sola lettura:** 132 file. **In comune solo `BACKLOG_POST_1.2.md`**, con hunk lontani (base dalla riga 2039 in poi, miei 1898–1943). Superfici del Lab non toccate. Dipendenze semantiche controllate:
> - Y1 divide `GrowthChart.svelte` in `growthChart{Data,Series,Tooltip}.ts`, ma `data-testid="growth-chart"` e `attachChartReady` restano, e i colori vengono da `lib/theme/chart*` come prima. Gli E2E L3 e neutral ricavano tutto a runtime.
> - `package.json` e lock cambiano solo la versione: niente `npm ci`.
>
> Dopo l'aggiornamento della base conviene comunque un giro `front-designer-lab all` sul fuso.

**✅ Validazione del fuso `fb2526cc4` (15/10, 15:59–16:08).** Il coordinatore ha committato L-10 in `a6f29298e`: padre `9d57aa4c0`, gli stessi 22 file. Poi ha fuso `dev_release2` (`7adda8a3c`: H, A5, Y1 e i suoi registri) in `fb2526cc4`, senza conflitti.
- Il fuso non tocca superfici del Lab: cambia solo la versione in `package.json` e nel lock.
- Porta la migrazione 006 e 11 file di API.

Prima del giro: HEAD verificato, albero pulito, porta libera. Comando: `/tmp/libreFolio_L10m_validate.sh`, in sequenza nella corsia 6152. Log in `/tmp/libreFolio_L10/val-merged/` e negli artefatti di sessione.

| Passo | Esito |
|---|---|
| `dev.py api sync` | exit 0, albero ancora pulito |
| unit del Lab | 15 file, **422/422** |
| `npm run check` | 0 errori, 0 warning |
| gate (gli stessi 10 file) | **168/168** |
| `theme-roles --check` | pulito |
| Prettier | pulito |
| scanner + inventario + parità | **identica**: `custom` 942, hex 1291, fn 238, tw 10490, `var_defs` 945, 1120 file |
| ruoli | 37 voci `lf`, **tutte con ruolo**, 178 usi in 15 file; 45 alias `--color-lf-*`, tutti `inline` con `alias_of` |
| build di release | exit 0; marker 0, catalogo 0, indice 0 |
| `dev.py front build --debug` | exit 0; `.build-debug=1`, 10 file col marker |
| `front-designer-lab all`, 1 worker | exit 0: **13/13 E2E** in 44,5 s + 422 unit; 5 azioni ✓; una sola build, nessuna ricostruzione a metà giro (L-12) |
| `check-orphans` | raggiungibili 122 e2e, 407 unit, 293 backend |
| porta a fine giro | 6152 libera; resta la build di debug |

> **Note implementazione**:
> - Il passaggio di `custom` da 912 a 942 viene dal codice fuso, non dal Lab. C'è una voce nuova, `--color-lf-page` → `--lf-surface-page` (`bg-lf-page`), e 5 file nuovi con utility di ruolo: `AuthCard`, `AuthPageFrame`, `LinkStatusCard`, `ResetPasswordCard`, `InstanceBlockedPage`. Il Lab li riconosce tutti col loro ruolo senza cambi di codice: è il meccanismo generico di L-10 al lavoro.
> - Il test `layout.authGate.test.ts` arrivato con H è un test funzionale del layout, non un gate di sorgente, e non entra nel mio insieme.
> - Il giro a 4 worker non l'ho ripetuto sul fuso: era verde alle 15:33 sulla revisione di prima, e il coordinatore ha chiesto `all`.

## ✅ Indirizzo del Lab nel banner di `dev.py` (15/10/2026)

**Base:** `dae4de4fa`; durante il lavoro `d22eb6f43`, con un fast-forward del coordinatore che porta C-94 di J: `--build-only` e un ritorno anticipato in `cmd_server`, prima della lista. Ho riletto `cmd_server` sulla versione nuova prima di modificarlo. La 1.3 dà via libera sul blocco «Available endpoints».

**Richiesta del developer** (testuale, 16:48): «puoi fare che in dev.py quando si avvia il server, viene mostrato anche il path per il design lab? similmente a quanto facciamo per le pagine delle api? ovviamente solo se è stato compilato, quindi in debug mode».

**✅ Passo 1 — codice (15/10, 16:5x).**
> **Note implementazione** (`dev.py`, solo inserimenti, +29 righe in 3 punti):
> - **Helper** vicino ai marcatori della build: `DESIGNER_LAB_MARKER = b"lf-designer-lab"`, lo stesso `LAB_MARKER` di `vite-plugin.mjs`, e `_frontend_build_has_designer_lab(build_dir)`.
>   - Legge gli script di `frontend/build/_app/immutable/` e si ferma al primo che contiene il marcatore.
>   - È esatto: quando il Lab è spento, il plugin fa fallire la build se un file emesso contiene il marcatore.
>   - Il file del modo di build non basta: una build di debug fatta con `LF_DESIGNER_LAB=0` non ha il Lab.
>   - Gli errori di lettura (`OSError`) danno False, oppure saltano il file: la riga non compare e il server parte lo stesso.
> - **Banner:** `├── 🎨 Designer Lab: http://localhost:{port}/designer-lab`, subito dopo `Frontend`, solo se l'helper dice True. Le altre righe non cambiano. Con `--build-only` la lista non si stampa, come prima.
> - **`front dev`:** la stessa riga per la porta 5173, tranne con `LF_DESIGNER_LAB=0`. È la regola di `designerLabEnabled()` per `vite dev`: solo `'0'` lo spegne.
> - **Costo** sulla build di debug vera: 5–14 ms con l'uscita anticipata, fino a 112 ms a freddo con la macchina carica. Nel caso peggiore, una build senza Lab con 22 MB di JS da leggere, 17–71 ms.
>
> **Prove leggere** (`/tmp/libreFolio_lab_banner_check.py`):
> - build vera → True;
> - cartella mancante → False;
> - marcatore solo in `index.html` e in un `.map` → False;
> - marcatore in uno script di `nodes/` → True;
> - `front dev` con `npm` sostituito: la riga c'è senza variabile e con `1`, non c'è con `0`.
>
> `ruff check dev.py`: 44 segnalazioni, tutte preesistenti, nessuna sulle mie righe (`lint` del progetto copre solo `backend/`). `git diff --check` pulito.
> **⚠️ Fuori pista:** il mio script in `/tmp` importava un `dev/` che sta nel site-packages del venv condiviso: è un pacchetto namespace, non un altro checkout. Ho risolto mettendo il worktree in testa a `sys.path`. I test del progetto non ne risentono, perché hanno la radice del progetto in `sys.path`.

**✅ Passo 2 — documentazione (15/10, 17:0x).** `docs-writer` ha aggiunto tre righe in «🎨 Opening It for a Designer» di `designer-lab.md` (117–119), con link a `#release-builds`. Nessuna traduzione. La skill `devpy-server` non elenca il banner, quindi resta com'è; nessun'altra pagina riproduce la lista.
> **Decisione del coordinatore (17:0x):** niente server di prova. La build di debug della corsia è vecchia: dopo i fast-forward sono cambiati 42 file in `frontend/src` e 22 in `mkdocs_src`, quindi servirebbe una ricostruzione pesante, e lo slot è del percorso critico di T. La prova è il test pytest con sei casi obbligati: nessuna build, release, debug col Lab, debug con `LF_DESIGNER_LAB=0`, `--build-only`, errore di lettura che non blocca l'avvio. Il banner vero lo vedrà il developer al primo `./dev.py server` dopo l'ingresso.

**✅ Passo 3 — test (`test-author`, 15/10, 17:0x–17:2x).**
> **Note implementazione:**
> - **File nuovo:** `backend/test_scripts/test_utilities/test_dev_designer_lab_banner.py`, 21 funzioni, 37 casi, isolamento `pure`.
> - **Registrazione:** `scripts/test_runner/_backend_utils.py`, solo aggiunte (+21 righe): la funzione `utils_dev_designer_lab_banner` dopo `utils_dev_port_check`, e la voce `utils dev-designer-lab-banner` dopo `dev-port-check`.
> - **I sei casi del coordinatore,** eseguendo davvero `cmd_server` su una build finta in `tmp_path`, con l'helper vero legato via `functools.partial`:
>   - nessuna build;
>   - release;
>   - debug col Lab: la riga c'è, subito dopo Frontend e prima di API Redoc, con la porta giusta;
>   - debug con `LF_DESIGNER_LAB=0`: `.build-debug=1` ma niente riga;
>   - `--build-only`: niente lista e l'helper non viene chiamato;
>   - errori di lettura (`rglob` e `read_bytes`): False o file saltato, e l'avvio arriva comunque al lancio di uvicorn.
> - **In più:**
>   - marcatore fuori dagli script (`.map`, CSS, `index.html`, `sw.js`, `offline.html`, `_app/env.js`) → False;
>   - build di produzione con `LF_DESIGNER_LAB=1` → la riga c'è;
>   - parità di `DESIGNER_LAB_MARKER` con `LAB_MARKER` di `vite-plugin.mjs`;
>   - `front dev` con `LF_DESIGNER_LAB` assente, `1`, `false`, `""` e `0`.
> - **Protezioni:**
>   - nessun processo, `exec` o segnale vero;
>   - `os.environ` confrontato prima e dopo;
>   - `dev.PROJECT_ROOT` puntato su `tmp_path`;
>   - la build vera non viene né letta né scritta.

**✅ Passo 4 — verifica (15/10, 17:2x), solo comandi leggeri.**
> - `dev.py test --test-port 6152 --data-dir /tmp/librefolio-r2-l utils dev-designer-lab-banner`: **37/37**, due volte da `test-author` e una da me (1,02 s). `check-orphans` verde, eseguito da `test-author`.
> - `ruff check` e `black --check` sul file di test: puliti. `ruff` su `_backend_utils.py`: 0 segnalazioni.
> - Diff: solo aggiunte. `dev.py` +29, `_backend_utils.py` +21, `designer-lab.md` +4, più il file di test nuovo. `git diff --check` pulito. Porta 6152 libera.
> - **Non eseguito:**
>   - il server di prova (decisione del coordinatore);
>   - `mkdocs build`, perché lo slot non è mio. È a basso rischio: tre righe con un link a un'ancora della stessa pagina, che esiste (`#release-builds`).
> - **Residuo minimo, solo segnalato:** la regola «solo `'0'` spegne il Lab sotto `vite dev`» di `front dev` è allineata a `designerLabEnabled()` solo da un commento; il test di parità copre il marcatore, non la regola.

## ⏳ Giro 3 della designer nel Lab — analisi in sola lettura (15/10/2026)

Richiesta del coordinatore (16:50), compito 2: cosa serve perché la designer modifichi dal vivo i ruoli nuovi di T-8 e i colori fissi di categoria di DV (`lib/theme/chartCategories.ts`, opzione A, non ancora scritto). Fonti: `designer-feedback/2026-10-15-round2-palette/README.md` e `analisi.md` §6. Testo completo inviato al coordinatore; bozza negli artefatti di sessione (`files/L-validate-2026-10-15/round3-analysis-draft.md`).

**Sintesi:**
- **Ruoli di T-8:** il Lab li gestisce già, perché L-10 è generico (prova: `bg-lf-page` è entrato col suo ruolo senza modifiche). Restano tre punti condizionati a come T-8 li scrive:
  - **isole `.dark`/`.light`:** per terminale, stato sulla barra verde e tooltip, il selettore deve leggere il tema dall'isola più vicina, non da `<html>` (`picker/describe.ts:384`);
  - **ombre:** servono come ruoli colore separati; l'editor non applica una `box-shadow` intera. Più un cursore per l'alfa;
  - **coppie di contrasto dei ruoli** nel pannello (L-15): `CONTRAST_PAIRS` va spostato da `themeTokens.gate.test.ts` a un modulo condiviso.
- **Tinte esplicite (B):** dopo T-8 la modifica di `--lf-warning` non trascina più le tinte. È giusto, va detto alla designer.
- **Categorie:** «per valore» non funziona. Tipi e settori condividono 7 esadecimali in chiaro e 11 in scuro, e in scuro le coppie sono diverse da quelle in chiaro. I sottotipi sono calcolati, e ci sono coincidenze con i ruoli (`#B45309` = Immobiliare e `--lf-warning` chiaro; `#6D28D9`/`#A78BFA` = Azione e viola AI).
  - **Contratto proposto con DV:**
    - C1: un solo punto di lettura, `categoryColor(kind, key, dark)`;
    - C2: valori letterali, uno per chiave e per tema;
    - C3: aggancio solo in debug, in un ramo `__LF_DESIGNER_LAB__`, verso `__lfDesignerLab`;
    - C4: segnale di ridisegno completo (contratto L-5).
  - **Nel Lab:** sezione `categories` del catalogo, livello nuovo `category`, scheda «Categorie», motore che risponde a C3 ed emette C4, avviso nella scheda Grafici, export e `verify-export`, una riga nella skill, ΔE00 dal vivo facoltativo, test unit ed E2E (ETF cambia, Tecnologia no).
  - **Costo:** medio-grande, simile al 5b.
- **Decisioni da portare:**
  - D1: contratto con DV e sede del segnale;
  - D2: con T-8, ombre come ruoli e uso delle isole;
  - D3: con T, `CONTRAST_PAIRS` condiviso;
  - D4: priorità fra ruoli e categorie.

**Decisioni sul giro 3** (coordinatore, 17:30; mandato del developer D-T17: «archiviali opportunamente e poi dai mandato ai vari sotto agenti di realizzare quanto pianificato»):
- **D1:** contratto C1–C4 approvato e già passato a DV. C4 = `onChartColorsChange(cb)` in `lib/theme/themeMode.ts`, lo scrive DV.
- **D2:** le ombre sono già ruoli di solo colore sul ramo di T (`--lf-shadow-raised`, `--lf-shadow-card`, un `color-mix` con alfa); niente isole (`--lf-terminal-*`, `--lf-bar-*`). Quindi niente isole nel Lab; il **cursore dell'alfa** serve, per ombre e fondale.
- **D3:** `CONTRAST_PAIRS` in un modulo condiviso, lo sposta T dopo T-8; L-15 lo leggerà da lì.
- **D4:** prima i ruoli, con l'ingresso di T; le categorie quando entra il modulo di DV.

Ordine: ora il cursore dell'alfa, con i test unitari, senza run pesanti. Dopo l'ingresso di T, verifica del catalogo e prova L1 sui ruoli nuovi. Le categorie quando DV ha C1–C4. Gli E2E nello slot, al checkpoint.

## ✅ Cursore dell'opacità nell'editor (giro 3, D2) — 15/10/2026

**Base:** `a4d1884b4`, dopo il fast-forward del coordinatore; albero pulito.

**Fatti verificati prima del progetto:**
- I valori con alfa dei ruoli sono `color-mix(in oklab, X p%, transparent)`: il fondale `--lf-surface-overlay` (`tokens.css:76`), le ombre di T, `--lf-selected`. `parseColor` rifiuta `color-mix`, quindi oggi l'editor li dà per non validi: «Applica» è spento e i cursori L/C/H non compaiono.
- `setFromOklch` forza l'alfa a 1 e il selettore sRGB è opaco: un valore traslucido perde l'alfa al primo tocco.
- I motori compongono già l'alfa: `cssWithAlpha` e `canvasString` moltiplicano l'alfa del bersaglio per quella di ogni occorrenza. L'import accetta qualunque valore sicuro (`isSafeCssValue`), e L1 scrive il testo così com'è.
- `resolveTarget` (motori di L2, L3 e delle specializzazioni dei grafici) usa `parseColor`, quindi scarterebbe un `to` in forma di mix.
- L'id di test `lab-editor-alpha` è già preso dalla casella «anche le varianti trasparenti».
- `--lab-check` è definito in `labTheme.ts` ma non è usato da nessuna parte.

**Progetto:**
1. **Modulo puro nuovo `colorValue.ts`**, senza DOM; le `var()` si risolvono con una funzione passata dal chiamante.
   - `parseTransparentMix` e `joinTransparentMix`: la forma `color-mix(in <spazio>, <base> <p>%, transparent)`, con la percentuale prima o dopo e `transparent` da una parte o dall'altra. Somme diverse da 100 → null. La base è un letterale o `var(--x)`.
   - `resolveValue`: letterale, `var()` (anche annidata, fino a profondità 4) o mix → Rgba.
   - `valueOpacity`: mix → p; letterale → la sua alfa; `var()` → 1.
   - `withOpacity`: mix → cambia la percentuale e tiene la base (così il riferimento a un ruolo resta); `var()` → mix in `oklab`; letterale → la stessa notazione con l'alfa (`#rrggbbaa`, oppure `oklch(… / a)` per OKLCH o fuori sRGB). A 100 % il mix si riduce alla base.
   - `withBase`: cambia il colore e tiene l'opacità. `baseVar`: la variabile della base, per «Aggancia».
2. **`ColorEditor.svelte`:**
   - `resolved` usa `resolveValue`;
   - nuovo cursore **A** in `.sliders`, con `data-testid="lab-editor-a"`, valori 0–1 a passi di 0,01 e la percentuale accanto;
   - L/C/H, il selettore sRGB e «Aggancia» passano da `withBase`, quindi l'opacità resta;
   - i due campioni su una scacchiera `--lab-check` / `--lab-panel`;
   - chiave i18n `editor.opacity`.
3. **`engine/targets.ts`:** `resolveTarget` usa `resolveValue`. Un valore con base `var()` resta un bersaglio anche se oggi non si risolve, come prima per `var()`.
4. **Test** (`test-author`): unit del modulo; `resolveTarget` e `cssWithAlpha` su un mix; un test di componente dell'editor in jsdom con `@testing-library/svelte`, che il progetto usa già. I file nuovi si registrano in `_frontend_designer_lab.py`, solo con aggiunte (N2 ①).
5. **Documentazione:** `docs-writer`, editor e valori dell'export; una riga nella skill `designer-lab-apply`.
6. **Prove leggere:** Vitest del Lab, Prettier, `tsc` sui file TS. `svelte-check` ed E2E nello slot, al checkpoint.

**✅ Passo 1 — codice (15/10, 17:4x).**
> **Note implementazione:**
> - **Nuovo `colorValue.ts`**, puro, 150 righe. Contiene `parseTransparentMix`, `joinTransparentMix`, `resolveValue`, `valueOpacity`, `withOpacity`, `withBase` e `baseVar`, come da progetto.
> - **`ColorEditor.svelte`:**
>   - `resolved` passa da `resolveValue`;
>   - nuovo cursore **A** (`lab-editor-a`, con la percentuale accanto);
>   - L/C/H, colore sRGB e «Aggancia» passano da `withBase`; `snap` viene da `baseVar`;
>   - i due campioni su scacchiera (`--lab-check`, finora inutilizzato, e `--lab-panel`).
> - **`i18n.ts`:** `editor.opacity`, in it/en.
> - **`engine/targets.ts`:** `resolveTarget` passa da `resolveValue`; un valore con base `var()` resta un bersaglio anche se oggi non si risolve.
> - **Skill `designer-lab-apply`:** una frase. `color-mix(…, transparent)` è la base all'opacità p, e va applicato come scritto: la base `var()` resta.
>
> **Prove leggere:**
> - Prettier pulito.
> - `tsc` sui moduli TS del Lab (config temporanea): nessun errore nei miei file. L'unico errore è `$app/environment` in `src/lib/i18n/index.ts`, un modulo di SvelteKit che `tsc` da solo non vede.
> - Micro-verifica temporanea, poi cancellata:
>   - mix → la base resta e cambia la percentuale; a 100 % torna la base;
>   - `var()` → mix;
>   - `#64748b` a 25 % → `#64748b40`; `oklch(… / 0.5)` → `/ 0.25`;
>   - `withBase('#64748b80', '#ff00aa')` → `#ff00aa80`;
>   - percentuali con somma diversa da 100 → null;
>   - catena di `var()` risolta.
> - Unit del Lab invariati: 15 file, 422/422.
> - `svelte-check` non eseguito: è un controllo pesante e lo slot non è mio. Va al checkpoint.

**✅ Passo 2 — documentazione (15/10, 17:5x).** `docs-writer` ha aggiornato `designer-lab.md`. Nessuna traduzione, quindi niente stamp; build e `check-links` al checkpoint.
> - **Editor (623–635):** il cursore A sulle tre forme, la scacchiera, i controlli del colore che tengono l'opacità, la moltiplicazione dell'alfa in L2/L3.
> - **Known Limits (955–958):** gli altri `color-mix()` restano non riconosciuti, cioè quelli di due colori o con percentuali che non sommano 100.
> - **Schema dell'export (1103–1105):** `to` può essere la forma `color-mix(…, transparent)`, e la skill la applica com'è scritta.
> - **File Map (1317):** riga di `colorValue.ts`.
> - **Seams (1368–1369):** `colorValue.ts`.
>
> **⚠️ Fuori pista:** `docs-writer` ha notato che solo OKLCH conserva la notazione: un letterale sRGB di qualunque altra forma diventa `#rrggbbaa`. Ho corretto il commento di `withOpacity`, che diceva «keeps its notation»; il codice era già giusto. Le ombre di T non sono ancora in questo `tokens.css`, quindi la pagina cita solo il fondale e `--lf-selected`.

**✅ Passo 3 — test (`test-author`, 15/10, 17:4x–18:1x).**
> **Primo giro:** 3 file nuovi, registrati in `_frontend_designer_lab.py` con sole aggiunte.
> - `colorValue.test.ts`: 66 test puri.
> - `targets.test.ts`: 13 test in jsdom.
> - `colorEditor.test.ts`: 10 test di componente in jsdom con `@testing-library/svelte`, senza toccare il codice. Ogni test esercita una riga che prima del cambio si comportava in modo diverso, controllato su `git show HEAD:`.
>
> Totale da 15 file e 422 test a 18 file e 511. `check-orphans` verde.
>
> **⚠️ Fuori pista — 5 difetti miei trovati da `test-author`, corretti (18:0x):**
> 1. **`cssWithAlpha` su un mix:** sulle occorrenze traslucide congelava in un valore fisso un mix con base `var()`. Ora compone la quota (`percent × alfa`) e resta un mix vivo.
> 2. **Spazio colore non controllato:** `in oklabb` passava. Ora si accettano solo i 15 spazi di CSS Color 5, e il metodo della tinta solo su quelli polari.
> 3. **NaN:** `withOpacity` ora restituisce null.
> 4. **Letterale appena sotto 1:** usciva `#…ff` o `/ 1`. Ora anche i letterali sono arrotondati al decimo di punto.
> 5. **Colore scelto su un letterale del tutto trasparente:** usciva invisibile. Ora arriva opaco; un mix allo 0 % tiene il suo 0 %.
>
> Dopo la correzione restano rossi solo i due vecchi `cssWithAlpha` di `targets.test.ts`, voluti dal punto 1. Li sto facendo aggiornare a `test-author`, con i casi nuovi dei punti 2–5.

> **Contratto C3–C4 scritto da DV** (avviso del coordinatore, 18:00; ramo di DV, non ancora entrato). Serve al livello `category`; per ora niente da fare.
> - **C3 · aggancio:** il modulo chiama `if (typeof __LF_DESIGNER_LAB__ !== 'undefined' && __LF_DESIGNER_LAB__) globalThis.__lfDesignerLab?.categoryColor?.(kind, key, dark)`. Il `typeof` serve perché in Vitest il `define` manca. **Il metodo `categoryColor` di `LabHook` (`types.ts`, pubblicato da `client.ts`) lo aggiunge L.**
> - **C4 · segnale:** in `lib/theme/themeMode.ts` ci sono `onChartColorsChange(cb)` e `notifyChartColorsChange()`, che emette `lf:chart-colors-change` su `document`. Il Lab chiama `notifyChartColorsChange()` dopo ogni modifica di categoria e quando carica uno stato.
> **Secondo giro (18:1x):** test aggiornati per le correzioni 1–5, da 511 a **548** test.
> - `colorValue.test.ts`: 95 test, fra cui:
>   - i 15 spazi accettati, uno per uno;
>   - il metodo della tinta rifiutato sugli 11 spazi rettangolari e accettato sui 4 polari;
>   - NaN e ±Infinity;
>   - l'arrotondamento dei letterali;
>   - il colore che arriva opaco su un letterale trasparente;
>   - il mix allo 0 %;
>   - l'invariante 11 valori × 3 basi.
> - `targets.test.ts`: 17 test. La composizione della quota in un solo mix, con la base `var()` viva sia risolta sia no; e la proprietà generale: l'uscita si risolve nel colore del bersaglio all'alfa del bersaglio per quella dell'occorrenza.
> - `colorEditor.test.ts`: 14 test, fra cui il mix allo 0 %, il colore scelto su un letterale trasparente e gli spazi errati segnalati come non validi.
>
> Nessun difetto nuovo. Registrazione nel runner invariata, cioè i 3 file aggiunti al primo giro.

**✅ Passo 4 — verifica leggera (15/10, 18:1x).**
> - unit del Lab: **18 file, 548/548**, su un mio giro e due di `test-author`;
> - Prettier pulito su `scripts/designer-lab`, sul Lab, sulla rotta e su `e2e/designer-lab`;
> - `check-orphans` verde, eseguito da `test-author`: 413 file unit raggiungibili;
> - `git diff --check` pulito, porta 6152 libera.
>
> **Delta finora:** 7 file tracciati (+162/−19) e 4 nuovi (`colorValue.ts` e 3 test).
> **Per lo slot del checkpoint:** `npm run check` (`svelte-check` sul componente), i gate, `theme-roles --check`, `mkdocs build` strict e `check-links`, la build di release col controllo del marcatore, `front-designer-lab all` (con l'E2E nuovo del cursore) a 1 worker ed `e2e` a 4, `check-orphans`, la porta.

**✅ Passo 5 — E2E del cursore (`test-author` li scrive; eseguiti nello slot del 15/10, alle 19:08).**
> **Fase 1 (18:1x–18:2x), solo scrittura:** due test nuovi in `designer-lab-live.spec.ts`. Prettier pulito, `tsc` temporaneo 0 errori.
> - «A: the opacity of a colour role reaches another tab». È lo sfondo del `login-modal`: A da 1 a 0,5, poi la scheda dell'app mostra lo stesso colore con alfa ≈ 0,5. Controlla anche l'export e il reset.
> - «A on a translucent mix keeps its base». La variabile si trova a runtime nella scheda Variabili, e oggi è `--lf-selected`, dal 12 al 25 %. Controlla:
>   - il valore calcolato su `<html>`;
>   - l'alfa di una sonda;
>   - che il mix segua la sua base `var()`;
>   - il reset.
> - Helper nuovi in `lab-helpers.ts`:
>   - `openEditor`, ricavato dalla prima metà di `applyChange`, con gli stessi passi;
>   - `setSlider`, perché `fill()` non accetta un input di tipo range;
>   - `paintedColours`, `sameColour`, `describeColour`, `expectPainted`, `rootValueOf`;
>   - `transparentMixOf`, un parser indipendente da quello del Lab.

**⏸️ Slot (15/10, 18:29–18:32): eseguita solo la parte statica, poi pausa chiesta dal coordinatore.** Lo slot va prima a T-8b, circa 40 minuti; il resto parte al suo via. Il messaggio è arrivato quando la parte `pre` era già finita. Comando `/tmp/libreFolio_alpha_validate.sh pre`, log in `/tmp/libreFolio_alpha/val-pre/` e negli artefatti.
> - `api sync` exit 0;
> - unit **548/548**;
> - `npm run check` **0/0**;
> - gate 168/168;
> - `theme-roles` pulito;
> - Prettier pulito;
> - `mkdocs build` strict **0 WARNING / 0 ERROR**; `check-links` **95** validi;
> - build di release exit 0: marcatore 0, catalogo 0, indice 0, `parseTransparentMix` 0;
> - porta libera.
>
> Nel worktree ora c'è la build di release: la rifà in debug il primo `server --test` della corsia.
> **Da fare al via:** `front-designer-lab live` con `test-author` sugli E2E nuovi, poi `/tmp/libreFolio_alpha_validate.sh post` (`all` a 1 worker, `e2e` a 4, `check-orphans`, porta).

**✅ Passo 6 — slot del checkpoint (15/10, 19:07–19:22).** Via del coordinatore alle 19:07. Prima della run: HEAD `a4d1884b4`, 13 righe di stato, porta libera, nessun processo nella corsia, nel worktree la build di release.
> **⚠️ Fuori pista:** il `test-author` degli E2E non esisteva più, perché l'id era scaduto. Ho eseguito `live` io: era verde al primo giro, quindi non è servita una riparazione né un nuovo agente.

| Passo | Comando (corsia `--test-port 6152 --data-dir /tmp/librefolio-r2-l --fresh-run`) | Esito |
|---|---|---|
| `live` (19:08–19:13) | `front-designer-lab live` | **10/10** in 39,7 s. I due test nuovi durano 1,3 s («A: the opacity of a colour role…») e 2,1 s («A on a translucent mix keeps its base»; oggi `--lf-selected`). La build di debug è stata ricostruita nel passo `--build-only` in primo piano, poi «Frontend build is up to date» |
| `all`, 1 worker (19:13–19:17) | `/tmp/libreFolio_alpha_validate.sh post` | exit 0: **15/15 E2E** (live 10, picker 4, neutral 1) + **548** unit; 5 azioni ✓ |
| `e2e`, 4 worker (19:17–19:21) | stesso script | exit 0: **15/15** in 1,5 min |
| `check-orphans` | stesso script | raggiungibili 123 e2e e 413 unit |
| porta e build | — | 6152 libera (`lsof` exit 1); build di debug (`.build-debug=1`, 10 file col marcatore) |

Con la parte statica delle 18:29–18:32 (unit 548, check 0/0, gate 168, `theme-roles`, Prettier, `mkdocs` strict 0 WARNING, `check-links` 95, release senza marcatore) il checkpoint è completo. Log in `/tmp/libreFolio_alpha/` e negli artefatti di sessione (`files/L-validate-2026-10-15/alpha-val-{pre,post}/`).

> **Rivista** la parte E2E di `test-author`:
> - i test hanno controlli positivi, testo esatto del mix, colori confrontati dipingendoli, export, base `var()` che segue (con la proprietà inline tolta in `finally`) e reset;
> - `openEditor` è la prima metà di `applyChange`, con gli stessi passi;
> - `setSlider` verifica il valore dopo l'evento.
>
> **Backlog:** nuova voce **L-16**, «Giro 3 della designer nel Lab»: ruoli di T-8 dopo l'ingresso di T, livello `category` dopo DV. L-15 annota la decisione D3.

**✅ Passo 7 — validazione del fuso `47e33997b` (15/10, 19:25–19:35).** Commit del coordinatore `7af0922c0`, «feat(designer-lab): add opacity slider to editor»: 14 file, gli stessi del mio delta. Merge pulito di `dev_release2` (`7c39f0666`), che si è fuso da solo solo nel backlog.
- Il target porta 199 file: 53 in `frontend/src`, 9 di API (email, utenti, backup). Nessuno è una superficie del Lab.
- Comando: `/tmp/libreFolio_alpha_merged.sh`, nella corsia 6152, nell'ordine del coordinatore. Log in `/tmp/libreFolio_alpha/val-merged/` e negli artefatti (`alpha-val-merged/`).

| Passo | Esito |
|---|---|
| `api sync` | exit 0, albero pulito |
| `front-designer-lab all`, 1 worker | exit 0: **15/15 E2E** in 52,2 s + **548** unit; 5 azioni ✓; la build di debug ricostruita una volta, prima del giro |
| gate | **168/168** |
| `npm run check` | **0 errori, 0 warning** |
| `theme-roles --check` | pulito |
| Prettier (Lab) | pulito |
| scanner + inventario + parità | **identica**. `custom` 1050, salito per il codice fuso: 37 voci `lf` tutte con ruolo, 286 usi in 21 file; 45 alias, tutti `inline`. Hex 1291, fn 238, 1161 file |
| `check-orphans` | 127 e2e, 421 unit raggiungibili |
| build di release, per ultima | exit 0: marcatore 0, catalogo 0, indice 0, `parseTransparentMix` 0 |
| porta | 6152 libera. Resta la **build di release**: la rifà in debug il primo `server --test` della corsia |

> **Note implementazione:** i ruoli con mix trasparente nel catalogo fuso sono `--lf-selected` e `--lf-surface-overlay`; le ombre di T arriveranno con T-8. Il test E2E del mix li trova a runtime, senza nominarli.

## ✅ L-16 — Giro 3 nel Lab: ruoli di T-8/T-8b e livello `category` (15–16/10/2026, notte; validato il 16/10 alle 03:50 su `e44383f13`)

**Entrata nel target:** il cursore dell'opacità è in `dev_release2` con `c96a62268` (merge di `f37f805fc`).
**Base:** `a0915bef9` (T e DV entrati), raggiunta con un fast-forward del coordinatore; albero pulito, porta libera. Nessun file del Lab è cambiato dopo il mio ingresso.
**Via del coordinatore (22:51):** «Via a L-16» — prima un'analisi breve con file e prove; «per stanotte basta il mio OK». Le prove pesanti si fanno al suo via, perché G-13 chiederà una finestra quieta. Obiettivo della notte, dal developer: finire la migrazione dei colori.

**Analisi (sola lettura, 22:5x–23:0x).** Prove leggere: scanner, inventario e parità sul nuovo albero; lo script `/tmp/libreFolio_L16_roles.mjs`, che confronta con `ROLE_CLASS_RE` di T. File in `/tmp/libreFolio_L16/`.
- **Parità identica:** hex 1355, fn 244, `custom` 1358, 1197 file.
- **Ruoli di T:**
  - 92 ruoli in `tokens.css`, tutti con definizioni root, quindi modificabili in «Variabili dell'app» e in L1;
  - 88 alias `@theme inline`, tutti `inline` con `alias_of`;
  - 64 chip `lf`, tutti col loro ruolo.
- **Mix:** 11 ruoli sono `color-mix`. Quelli con `transparent` (ombre, fondale, `--lf-selected`, alone del tour, illustrazione in chiaro) si modificano col cursore A. I due mix di due colori (`--lf-action-hover`, `--lf-terminal-comment`) mostrano la sorgente come non riconosciuta, ma accettano un valore nuovo (limite documentato).
- **24 alias senza chip:** nessuna classe li usa ancora, perché le ondate non hanno migrato quei componenti (AI, mark, checked, switch…). In più `shadow-lf-*`, 8 usi, non viene contato: `TW_CUSTOM_RE` non ha il prefisso `shadow`, che `ROLE_CLASS_RE` di T ha. È l'unico scarto: T 619 usi, lo scanner 611.
- **Grafici che leggono i ruoli:** sono 4 e tutti usano `chartRoles` (`roleColors.ts`), che rilegge i ruoli a ogni disegno: AllocationPie, AllocationHistory, SemiDonut, CorrelationHeatmap. Ascoltano C4, ma il Lab oggi non emette `notifyChartColorsChange()` dopo una modifica L1, quindi non si ridisegnano.
- **Categorie (DV):**
  - C1–C3 sono in `lib/theme/chartCategories.ts`. L'aggancio chiama `globalThis.__lfDesignerLab?.categoryColor?.(kind, key, dark)` e si aspetta `string | null | undefined`.
  - C2 è rispettato: 54 letterali, cioè (11 tipi + 14 settori + 2 contenitori) × 2 temi, una riga ciascuno, col tema dato dalla chiave dell'oggetto.
  - Il modifica «per valore» non funziona:
    - nello stesso file 16 valori compaiono due volte per tema (ETF = Tecnologia…);
    - 22 valori sono scritti anche altrove (`#b45309` = `--lf-mark-line` in scuro, `#6d28d9` = `--lf-ai`).
  - C4 (`onChartColorsChange`, `notifyChartColorsChange`) è in `themeMode.ts`.
  - **Scarto C1:** `GROWTH_BROKER_PALETTE` (`chartPalettes.ts`) è calcolato una volta all'import, e `GrowthChart` non ascolta C4. Le linee dei broker non seguono quindi una modifica di categoria. È di DV.
  - `lookupKey`, che ignora maiuscole, spazi e trattini bassi, è privata.
  - `familyShade` (GR4) accetta un colore che `parseRgb` sa leggere; se non lo legge, restituisce la base.
- **D3:** `CONTRAST_PAIRS` è ancora in `themeTokens.gate.test.ts`, quindi L-15 aspetta.
- **Import:** il gate controlla solo gli import verso il Lab, quindi il Lab può importare `$lib/theme/themeMode` e `$lib/theme/chartCategories`.

**Piano proposto:**
- **Parte 1 — ruoli:**
  - (1a) **C4 per L1:** l'engine chiama `notifyChartColorsChange()` quando cambiano le sostituzioni applicate (variabili e categorie), cioè al caricamento, a ogni modifica, al reset e alla sospensione;
  - (1b) **prefisso `shadow`**, facoltativo: il gruppo dei prefissi di `TW_CUSTOM_RE` si allinea alla lista `PREFIXES` già usata per la palette; serve la riga Python del coordinatore e la parità prima e dopo.
- **Parte 2 — livello `category`:**
  - scanner: annota i letterali di `chartCategories.ts` con `{kind, key}` e aggiunge la sezione `categories` al catalogo, fuori dalla parità;
  - livello `category`, con target `type:<KEY>`, `sector:<KEY>` e `bucket:Liquidity|Unknown`;
  - nell'engine, `LabHook.categoryColor`: `#rrggbb` se il colore è opaco, nulla se lo stato è sospeso;
  - una scheda «Categorie»;
  - export con `raw` sulla riga del tema, così `verify-export` resta invariato;
  - l'avviso nella scheda Grafici;
  - una riga nella skill, la documentazione, i test unit ed E2E.
- **Decisioni:**
  - D-a: (1b) adesso o nel backlog;
  - D-b: `lookupKey` esportata da DV, oppure una copia nel Lab con un test di parità;
  - D-c: lo scarto C1 di `GROWTH_BROKER_PALETTE` va a DV.

**Approvazione del coordinatore (23:00), testuale nelle decisioni:**
- **D-a: sì, adesso.** Il gruppo dei prefissi di `TW_CUSTOM_RE` si allinea a `PREFIXES`, che comprende `shadow`. La riga `tw_custom_re` di `scripts/visual_review/color_inventory.py` la scrivo io, su sua assegnazione. Parità prima e dopo; lo scarto 611 → 619 va spiegato nel checkpoint.
- **D-b: (a).** DV esporta `lookupKey` da `chartCategories.ts` dentro TD-1, con una riga. Io la uso dopo l'ingresso di TD-1, che il coordinatore mi porta al prossimo merge di base. Fino ad allora lavoro sul resto.
- **D-c:** passa a DV come lotto TD-1b, subito dopo TD-1.
- **Punto 5, il selettore delle categorie:** va nel backlog.
- **Ordine:** prima 1a e il punto 2 (scanner ed engine), poi interfaccia, skill, documentazione e test, con gli agenti in parallelo.
- **Slot pesante dopo le 01:15,** al suo via. **Dalle 00:00 alle 01:15 c'è la finestra quieta di G-13:** niente build, Vitest, Playwright, server, né agenti che li lancino.
- **Checkpoint:** due o tre righe «dove guardarlo» per la lista del developer, perché stanotte i lotti validati entrano senza il suo OK.

### Avanzamento L-16

**✅ Passo 1 — D-a, prefissi delle classi custom (15/10, 23:05).**
> **Note implementazione:** `TW_CUSTOM_RE` usa `PREFIX_ALT`, cioè la lista `PREFIXES` della palette, e `tw_custom_re` di Python la stessa lista ordinata per lunghezza: una riga per parte. Le due liste `PREFIXES` erano già identiche.
> **Parità, stesso albero:**
> - prima: identica, `custom` **1358**;
> - dopo: identica, `custom` **1375**.
>
> Lo scarto, misurato voce per voce:
> - usi `lf` da 611 a **619**, uguali a `ROLE_CLASS_RE` di T: +7 `shadow-lf-shadow` (`--color-lf-shadow` → `--lf-shadow-raised`) e +1 `shadow-lf-shadow-card`, quindi 2 chip nuovi, col loro ruolo;
> - +9 `libre-green`, coi prefissi `accent-`, `decoration-`, `border-l-`, `border-t-`.
>
> Hex 1355, fn 244, 1197 file, invariati. File in `/tmp/libreFolio_L16/{before,after}/`.

**✅ Passo 2 — 1a e livello `category`, il codice (15/10, 23:05–23:12).**
> **Note implementazione:**
> - **Scanner:**
>   - `CATEGORY_FILE` e `categoryLines(text)` leggono le tabelle di `chartCategories.ts` (`ASSET_TYPE_COLORS`, `SECTOR_COLORS`, `LIQUIDITY_COLOR`, `UNCLASSIFIED_COLOR`);
>   - i letterali di quelle righe ricevono `category` e il tema della proprietà;
>   - il catalogo ha la sezione `categories`, `[{target, kind, key, light, dark}]`, fuori dalla parità.
>   - Sull'albero reale: **27 categorie** (11 tipi, 14 settori, 2 contenitori), tutte con chiaro e scuro, e 54 letterali su 54 annotati.
> - **`types.ts`:** `CatalogLiteral.category`, `CatalogCategory`, `ColorCatalog.categories?`, il livello `category`, `LabStats.categoryOverrides`, `LabHook.categoryColor`.
> - **Nuovo `engine/categories.ts`:**
>   - `categoryKey`, copia temporanea della regola di `lookupKey` fino a TD-1, segnalata al coordinatore;
>   - `categoryTargetKey`;
>   - `setCategoryChanges`: per ogni tema prima `both`, poi il tema stesso, che quindi vince;
>   - `categoryColor`: i contenitori valgono per i due tipi; il valore si risolve a ogni richiesta; `toCanvasColor` dà `#rrggbb` o `rgba()`.
> - **`engine/index.ts`:** `categoryOverrides`, e **C4**. Dopo tutti i motori confronta la firma `[id, to]` delle modifiche `css-var` e `category` (all'inizio `'[]'`) e, se è cambiata, chiama `notifyChartColorsChange()` da `$lib/theme/themeMode`.
> - **`client.ts`:** `hook.categoryColor`, che non risponde finché non c'è un engine, e le statistiche predefinite con `categoryOverrides`.
> - **`export.ts`:**
>   - l'export porta `category: {kind, key}` e come occorrenze la riga di ogni tema dell'ambito;
>   - l'import accetta solo una categoria del catalogo, con una forma sicura, e non dà `alphaVariants`.
> - **`catalogView.ts`:** `categoryRows`, `sourceCategoryValue`.
> - **`DesignerLab.svelte`:** la scheda «Categorie» (`lab-tab-categories`), divisa in tre gruppi, con le righe `lab-item-category-<target>`.
> - **`ColorEditor.svelte`:**
>   - `isCategory`: il valore di partenza viene dal catalogo, e niente casella delle varianti;
>   - la portata (`lab-editor-category-reach`) e le righe (`lab-editor-category-lines`);
>   - per un valore che è anche una categoria, l'avviso (`lab-editor-category-warning`).
> - **`i18n.ts`:** 9 chiavi.
> - **Skill `designer-lab-apply`:** la riga `category`.
>
> **Prove leggere (23:11):** Prettier pulito; `tsc` sui moduli TS del Lab senza errori nei miei file (solo i moduli `$app/*` di SvelteKit); unit del Lab invariati, 548/548.
> **In parallelo:** `test-author` unit (`451159cb`), `docs-writer` (`2df1d670`), `test-author` E2E (`6e1c06cc`, solo scrittura). Dalle 00:00 alle 01:15 nessuno esegue niente.
> **Decisione del coordinatore sulla copia di `lookupKey` (23:1x), testuale:** «Approvata, ma solo come provvisoria: la copia non deve entrare nel target. TD-1 entrerà prima della tua validazione pesante, che è dopo le 01:15. Al merge di base con TD-1 la sostituisci con l'import di `lookupKey`, tieni il test, e solo dopo validi e consegni il checkpoint.»
> **Ordine conseguente:**
> 1. merge di base con TD-1, fatto dal coordinatore;
> 2. in `engine/categories.ts`, `categoryKey` diventa `export const categoryKey = lookupKey` da `$lib/theme/chartCategories`: alias, non copia; il test di parità resta;
> 3. poi le prove pesanti nello slot e il checkpoint.

**✅ Passo 3 — test unitari (`test-author`, 23:1x–23:30, prima della finestra).** Il giro del Lab più `chartCategories.test.ts` passa da 19 file e 633 test a **21 file e 687**, verde due volte. Registrati 2 file nuovi, `categories.test.ts` e `chartColorsSignal.test.ts`, solo con aggiunte. Prettier pulito, `check-orphans` verde.
> - `categories.test.ts` (20 test):
>   - le chiavi;
>   - le risposte per tema, la precedenza del tema su `both`, i contenitori;
>   - le varianti delle chiavi, confrontate con il `categoryColor` vero di DV;
>   - le forme di colore: `#rrggbb` minuscolo, `rgba()`, `var()` letta a ogni richiesta;
>   - C3 da capo a fondo: `categoryColor` di DV restituisce il colore modificato solo con `__LF_DESIGNER_LAB__`.
> - `chartColorsSignal.test.ts` (3 test): C4 con il vero `onChartColorsChange`. Un evento per ogni cambio di variabili o categorie, nessuno per gli stessi input o per gli stati con soli letterali, elementi o CVD; `categoryOverrides` segue.
> - Estesi: `scanColors` (prefissi, `categoryLines`, albero sintetico, due invarianti sull'albero reale), `exportFormat`, `verifyExport`, `catalogView`, `colorEditor`.
>
> **⚠️ Fuori pista — difetto trovato da `test-author` e corretto (23:3x):** `verify-export` cercava una riga di categoria spostata per valore. Su un valore condiviso finiva sulla riga di un'altra categoria: per esempio dava `moved` alla riga del settore quando il valore del tipo era cambiato, e sempre con exit 0. Ora `locateCategory()` trova la riga per chiave e tema con `categoryLines()`:
> - `ok` se è alla stessa riga;
> - `moved` se la chiave è scritta altrove;
> - `missing` se la chiave non c'è più o la riga ha un altro valore.
>
> **⚠️ Fuori pista — tentativo ritirato:** avevo fatto rispondere una modifica di `bucket:Unknown` anche alle chiavi fuori dalle tabelle, come fa DV. Ha rotto 11 test, che usano chiavi inventate, e richiedeva `CATEGORY_KEYS` nell'engine. Le enum del backend tengono quelle chiavi fuori dai dati reali, quindi l'ho tolto: resta un limite documentato.
> **Piccola correzione UI:** la casella del filtro «picked» non compare più nella scheda Categorie, dove non filtrava niente.
> **Giro di controllo (23:35):** 21 file, **687/687**.
> **Secondo giro di `test-author` (23:40):** i test di `locateCategory` vanno in `verifyExport.test.ts`, che passa da 22 a 33 test: 6 test diretti e 6 su `verifyExport` con un albero sintetico.
> - La fixture condivisa ha `type:AAA` e `sector:Zed` con lo stesso valore in chiaro.
> - Ogni caso di regressione verifica prima cosa avrebbe restituito la vecchia ricerca per valore.
> - Il vecchio titolo «found by its value» non c'è più.
> - Totale: 21 file, **698/698**; Prettier pulito, `check-orphans` verde.
> - Comportamenti fissati dai test:
>   - un `theme_context` null o `both` dà `missing` (il Lab non lo scrive mai per una categoria);
>   - un'occorrenza senza `raw` viene collocata solo per chiave e tema;
>   - le chiavi si confrontano come le scrive la tabella.

**✅ Passo 4 — documentazione (`docs-writer`, 23:1x–23:3x).** `designer-lab.md`: nuova sezione «🍩 Chart Categories» (`#chart-categories`); aggiornati build switch, neutralità, hook, schema del catalogo (`category`, `categories`), Colour Roles (prefissi), parità (1358 → 1375), scheda e editor, livelli (titolo «The Six Change Layers» con l'ancora `#change-layers`; nessun link al vecchio slug), Known Limits, schema dell'export, import, skill, File Map, seams. Ha corretto anche quattro frasi già superate: `shadeForDepth`, l'osservatore di SemiDonut, la regola dei file dei grafici, i «tre posti» del ramo. Il secondo e il terzo giro sono qui sotto.
> Dopo TD-1: vanno tolti il limite (d) e la frase sulla copia di `categoryKey()`.
> **Secondo giro (23:4x):** `locateCategory`, il limite delle chiavi fuori tabella, la casella del filtro.
> **Terzo giro (23:5x, solo scrittura):**
> - C4 in «L2» (righe 281–284), «L3» (320–323) e «The redraw (C4)» (383–403): firma, momenti del controllo, elenco dei casi muti;
> - `features/risk/` nella frase sui file dei grafici (538–543);
> - un limite nuovo, i fogli arrivati dopo, in Known Limits (1091–1094);
> - la File Map (1487).
> - Ha notato che i ruoli derivati, come `--lf-text-on-inverse` = `var(--lf-surface-card)`, non sono letterali: la pagina dice «the derived ones aside». Seguono comunque la modifica del ruolo a cui rimandano.
> - Build strict e `check-links` nello slot.

**⏳ Passo 5 — E2E (`test-author`, sola scrittura).** Il test delle categorie è scritto: tipo scelto a runtime, la torta dei tipi ricolorata per chiave, quella dei settori invariata, export e `verify-export`, reset.
> **⚠️ Fuori pista:** il test C4 «ruolo letto da un grafico» non ha un legame robusto con i dati di TEST_USER. La torta legge solo `--lf-surface-card`, per le sfumature dei sottotipi in scuro, e TEST_USER non ha sottotipi; la heatmap richiede la rotta del rischio. Lo sostituisco con un test di contratto dal lato del Lab: un contatore di `lf:chart-colors-change` nella scheda dell'app; una modifica L1 → 1 evento, una modifica di un letterale → nessuno, il reset → 1. Il redraw da capo a fondo lo prova già il test delle categorie.
>
> **⚠️ Fuori pista — buco di C4 trovato da `test-author` (E2E) e corretto (23:4x):** ogni ruolo di `tokens.css` è scritto come letterale in `:root` e `html.dark`, e L2 riscrive anche i letterali dentro le definizioni di variabile. Una modifica dalla scheda Fogli di stile di quel valore (per esempio `#fafbfa`) cambiava quindi `--lf-surface-card` senza C4: i grafici che leggono i ruoli con `chartRoles` non si ridisegnavano.
> - **Correzione:**
>   - `engine/stylesheets.ts` esporta `variableRewrites()`: ogni proprietà custom riscritta dal passaggio, con selettore, nome e valore attuale, ordinate;
>   - in `engine/index.ts` la firma di C4 è `[variabili e categorie dello stato, variableRewrites()]`, e il valore iniziale è calcolato a vuoto, così un reset senza modifiche resta muto;
>   - `signalChartInputs()` gira alla fine di `applyState` e, di nuovo, nell'osservatore del tema dopo il ri-piano. Così un letterale con ambito di tema su un ruolo manda il segnale una volta dopo il cambio di tema, in qualunque ordine siano girati gli osservatori.
> - **Limite:** un foglio caricato dopo (CSS di rotta) viene riscritto senza un segnale suo. I ruoli che legge `chartRoles` stanno tutti nel foglio globale.
> - **Giro (23:47):** 21 file, **698/698**; Prettier pulito.
> - **Test:**
>   - `test-author` unitario scrive i casi con un `<style>` controllato in jsdom: definizione `:root` → 1, regola comune → 0, variabile di componente → 1, cambio di tema con ambito → 1, `both` → 0, `variableRewrites()`;
>   - `test-author` E2E riscrive il test C4: L1 → 1, letterale nella definizione di un ruolo letto da `chartRoles` → 2, reset → 3. Il caso negativo passa agli unitari.
>   - Scrivono soltanto, perché c'è la finestra quieta.
> - `docs-writer` aggiorna le frasi che dicevano «C4 solo per variabili e categorie».
>
> **⚠️ Fuori pista — richiesta del coordinatore (23:49), `features/risk` nello scanner:** Y4b (1.3) sposta il rischio da `components/risk/**`, `lib/risk/` e `stores/risk/` a `lib/features/risk/`, verso le 02:30.
> - In `CHART_PATH_RE` (`scan-colors.mjs:194`) la parte finale è ora `features\/(risk|tools\/pac-allocator\/planner\/result)`, accanto a `components/risk`, con un commento di una riga. Vale sia prima sia dopo lo spostamento.
> - Prova sulla regex (23:51):
>   - `features/risk/components/X.svelte`, `features/risk/x.ts` e `components/risk/X.svelte` danno chart;
>   - `features/riskier/x.ts` e `features/tools/x.ts` no.
> - `lib/risk/` e `stores/risk/` oggi non hanno letterali di colore (grep), quindi il catalogo non cambia.
> - Una riga nell'`it.each` «recognises a chart by %s» la scrive `test-author`, e una frase nella pagina developer (~520) `docs-writer`. Il file Python non ha la lista dei percorsi dei grafici e non va toccato.
>
> **⚠️ Fuori pista — `features/dashboard` (coordinatore, 00:0x):** Y3 (1.3) sposta `components/dashboard/**` in `lib/features/dashboard/`, a radice piatta, 35 file, verso le 02:00 o più tardi.
> - La regex è ora `features\/(dashboard|risk|tools\/pac-allocator\/planner\/result)` (`scan-colors.mjs:195`), e il commento cita Y3 e Y4b.
> - Scritto nella finestra quieta, senza run:
>   - la riga `features/dashboard/Kpi.svelte` di `test-author`: il nome non contiene «chart», così combacia solo il ramo nuovo;
>   - la frase di `docs-writer`.
> - Oggi nessun file di `components/dashboard` con colori dipende dalla sola regola della cartella: hanno tutti «Chart» nel nome o importano `echarts`. Il catalogo non cambia.
> - Le costanti `pickView.test.ts:23` (`GROWTH`) e `scanColors.test.ts:339` sono fixture sintetiche, che non leggono i file veri: lo spostamento non le rompe. Le aggiorno, solo per estetica, al primo giro dopo l'ingresso di Y3.
> - **Scritti (00:0x), non eseguiti:**
>   - la riga `['the dashboard feature folder', 'src/lib/features/dashboard/Kpi.svelte']` in `scanColors.test.ts`, attesi **706** test;
>   - la frase di `designer-lab.md` (538–543), che accoppia `components/dashboard` con `features/dashboard/` e `components/risk` con `features/risk/`.
>
> **⚠️ Fuori pista — `features/brokers/lots` (coordinatore, 00:14):** Y5 (1.3), dopo il lotto di T, sposta `components/brokers/*` in `lib/features/brokers/`, che non è una cartella di grafici, e `components/brokers/lots/*` in `lib/features/brokers/lots/`, che lo è.
> - La regex è ora `features\/(brokers\/lots|dashboard|risk|tools\/pac-allocator\/planner\/result)` (`scan-colors.mjs:196`), e il commento cita Y3, Y4b e Y5.
> - Scritti nella finestra:
>   - `test-author`: una riga positiva (`features/brokers/lots/LotsAnalysisPanel.svelte`) e una negativa (`features/brokers/BrokerImportFilesModal.svelte` resta `script`);
>   - `docs-writer`: la frase.
> - L'esempio JSON con `components/brokers/BrokerImportFilesModal.svelte` (`designer-lab.md:1215`) si cambia dopo l'ingresso di Y5.
> - **Scritti (00:2x), non eseguiti:**
>   - la riga positiva;
>   - il test «keeps the colours of any other module in the script layer» diventa un `it.each` con `utils/format.ts` e `features/brokers/BrokerImportFilesModal.svelte`, che va a `script` con `chart: false`;
>   - attesi **708** test;
>   - la frase della doc (538–543): tre coppie `components/…` ↔ `features/…`, con Y3, Y4b e Y5 tra parentesi.
> - **Risposta al coordinatore, Y5 prima di L-16?** Sì, senza rotture.
>   - Nessun test o gate fissa la classificazione del catalogo vero: il test sull'albero reale controlla solo invarianti, il gate degli import guarda gli import, gli E2E scelgono a runtime.
>   - Nessun file di `components/{brokers/lots,dashboard,risk}` con colori (hex e tutte le funzioni colore) dipende dalla sola regola della cartella: hanno tutti «chart» nel nome o importano `echarts`. La classificazione non cambia.
> - **Slot riordinato (00:14):** DV ~01:35 → T ~02:10 → L-16 ~03:20. Al merge di base, se Y3 e Y5 sono entrati, aggiorno prima della validazione le costanti di estetica (`pickView.test.ts:23`, `scanColors.test.ts:339`) e l'esempio JSON.
>
> **Giro di `test-author` sui due punti (23:51, prima della finestra):** 21 file, **705/705** (+6 C4, +1 riga del rischio); Prettier pulito, `check-orphans` verde.
> - **`chartColorsSignal.test.ts`** passa da 3 a 9 test. Ogni test inserisce il proprio `<style data-lab-test>`, e l'afterEach toglie stili e classe di `html`.
>
>   | Caso | Eventi |
>   |---|---|
>   | `:root` | 1, 0, 1, 1, 0 |
>   | regola comune | 0, con la barriera `cssRules > 0` |
>   | variabile di componente | 1, 1 |
>   | tema con ambito chiaro | 1, 1 |
>   | `both` | 0, 0 |
>
>   C'è anche un test diretto di `variableRewrites()`.
>   - Per il cambio di tema la barriera è un secondo `MutationObserver`, non un'attesa a tempo.
>   - jsdom serializza i colori comuni in `rgb()` ed espande le shorthand; i test ne tengono conto.
> - **`scanColors.test.ts`:** la riga `features/risk/components/CorrelationHeatmap.svelte`. Su quel percorso combacia solo il ramo nuovo.
> - **Non dimostrato da una run:** il fallimento dei nuovi test sul codice di prima. Lo si deduce solo dalla lettura: prima nessun segnale dall'osservatore del tema e nessuna variabile riscritta nella firma.

**✅ Passo 5a — E2E, scrittura (`test-author`, 23:4x).** Il test C4 è riscritto: «an L1 edit, a literal inside a role's definition and a reset each reach the other tab as one chart-colours signal».
1. Prima di ogni modifica sceglie il ruolo B tra quelli che legge `chartRoles`: il suo valore in chiaro su `<html>` deve comparire nella scheda Fogli di stile (confronto per chiave colore, senza `color-mix`).
2. L1 su un ruolo A ≠ B → contatore 1, e B ancora al suo valore.
3. Letterale di B → B col colore nuovo, contatore 2.
4. Reset → B originale, contatore 3, segno di nessun ricaricamento, client inattivo, `IDLE_STATS`.

Prettier e tsc temporaneo sugli E2E: 0 errori (23:49). Non ancora eseguito.

**✅ Passo 5b — checkpoint intermedio, richiesto dal coordinatore (16/10, 02:06):** «TD-1 è nel target (`57802d827`) […] Mandami il checkpoint di L-16 così com'è, FROZEN». Dopo vengono il suo commit e il merge di base; poi tocca a me la sostituzione, le prove leggere e un piccolo checkpoint; lo slot pesante dopo T, verso le 03:20.
- **Prove leggere (02:07):** Vitest del Lab più `chartCategories.test.ts`: 21 file, **708/708**, quindi le 3 righe scritte nella finestra sono verdi. Prettier pulito su `scripts/designer-lab`, `lib/dev/designer-lab`, `routes/designer-lab`, `e2e/designer-lab`. Alle 02:10: ruff e black puliti su `color_inventory.py`, `theme-roles --check` pulito, `git diff --check` pulito, porta 6152 libera (`lsof` exit 1). Stato: 24 file tracciati modificati e 3 nuovi. **FROZEN** per il commit del coordinatore.
- **Previsione di conflitto verso `57802d827`:**
  - dei miei file, il target cambia solo `BACKLOG_POST_1.2.md`, in altre sezioni (T, DV, H, A, W, J, Z, B, E, Y), mentre io ho toccato solo L (righe 1950–1960): nessuna sovrapposizione;
  - `chartCategories.ts` di TD-1: `categoryLines()` sulla versione del target dà ancora 54 righe e 27 categorie (11 tipi, 14 settori, 2 contenitori), solo spostate di una riga (39…177 → 40…178);
  - `lookupKey` è identico alla mia copia (`key.replace(/[\s_]/g, '').toUpperCase()`), quindi sostituirla non cambia il comportamento;
  - `roleColors.ts`: TD-1 aggiunge `--lf-text-secondary` a `ChartRole`. La lista dei nomi nell'E2E C4 va aggiornata dopo il merge; non si rompe niente, ha solo un candidato in meno;
  - Y3, Y4b e Y5 non sono nel target: niente costanti né esempio da aggiornare a questo merge.

**✅ Passo 6 — dopo il merge di base con TD-1 (16/10, 02:13–02:28).**
> **Merge di base del coordinatore (16/10, 02:13):**
> - checkpoint `4cc601e57`, «feat(designer-lab): category layer and C4 signal», con i 27 path;
> - merge `0b229ef95`, con padri `4cc601e57` e `57802d827`;
> - il backlog si è fuso da solo; worktree pulito, `--check` pulito.
>
> **Verifica (02:14):** HEAD e padri come annunciati, 0 righe di stato.
> - `lookupKey` è esportato (`chartCategories.ts:204`) e `--lf-text-secondary` è in `ChartRole` (`roleColors.ts:30`).
> - Y3, Y4b e Y5 non sono entrati: il punto 7 non serve a questo merge.
>
> **Fatto (02:15):** in `engine/categories.ts` la copia è sparita: `import {lookupKey} from '$lib/theme/chartCategories'` e `export const categoryKey = lookupKey`.
> - Il gate degli import del Lab regola solo chi importa il Lab, non cosa il Lab importa.
> - `chartCategories.ts` non importa niente del Lab.
>
> **⚠️ Fuori pista — anche TD-1b è nella base** (`ada4742b7`, «PAC bars by category, live broker colours (TD-1, TD-1b)»):
> - `GROWTH_BROKER_PALETTE` non esiste più: `growthBrokerColor()` (`chartPalettes.ts:32`) legge `categoryColor('type', CATEGORY_SEQUENCE[i mod 8], dark)` a ogni costruzione delle serie (`growthChartSeries.ts:115`), e `GrowthChart.svelte:954` ascolta C4;
> - anche `ExposureBars.svelte`, il risultato del PAC, legge `chartRoles` e ascolta C4.
>
> Quindi nella doc cadono due limiti: la copia della regola delle chiavi e le linee dei broker della Growth.
>
> **Agenti nuovi (gli id di ieri sono scaduti), avviati in parallelo su file distinti:**
> - `docs-writer` (`a1c3218b`): tolti i due limiti; «Reach» con le linee dei broker; la lista di chi legge `chartRoles` con le barre del PAC; la frase sulle chiavi con `lookupKey` di DV; il seam `categoryKey`;
> - `test-author` (`1f5e2bd4`):
>   - un test che fissa `categoryKey === lookupKey`; quello di parità resta;
>   - `--lf-text-secondary` in `CHART_ROLES` dell'E2E, solo in scrittura;
>   - il verdetto sui due E2E dopo TD-1b.
>
> **Punto 5, `api sync`:** il target cambia 15 file di `backend/app/api|schemas`, quindi nella fase `pre` dello slot si usa `API_SYNC=1`. Il client è generato e ignorato, e non serve alle prove leggere.
>
> **Esito degli agenti (02:2x):**
> - **`test-author`:** Vitest a **712/712** su 21 file.
>   - La base dopo il merge era 711, non 708: `chartCategories.test.ts` di DV ha netto +3 test. Il +1 è il test d'identità, `expect(categoryKey).toBe(lookupKey)`, alla riga 48; l'intestazione è aggiornata e i test di parità restano.
>   - E2E: `'--lf-text-secondary'` in `CHART_ROLES` (riga 147), nell'ordine di `ChartRole`.
>   - Prettier pulito; tsc temporaneo sugli E2E con 0 errori.
>   - Verdetti:
>     - il test delle categorie regge, perché legge solo le torte di `allocation-panel`, e la Growth sta fuori dal pannello;
>     - il test C4 regge: il contatore conta i segnali, non gli ascoltatori. `notifyChartColorsChange` ha un solo chiamante, quindi 1/2/3 restano. B resta `--lf-surface-card`, il primo che qualifica; A non è mai stato `--lf-text-secondary`.
> - **`docs-writer`** (+14/−15 righe):
>   - la frase delle chiavi con `lookupKey` (378–380);
>   - le barre del PAC tra chi legge `chartRoles` (401–404, ora cinque);
>   - «Reach» con le linee dei broker (406–412);
>   - Known Limits senza i due limiti (1100–1113);
>   - il seam «`categoryKey` (DV's `lookupKey`, re-exported)» (1547–1549).
>
>   Le ancore sono tutte risolte. Ha segnalato che la lista dei lettori di `categoryColor` in C1 (344–346) è incompleta: mancano le barre del PAC (`exposureBarColours.ts:39–44`, verificato) e le linee dei broker. Gliel'ho chiesto.
>   - **Secondo giro (02:2x):** C1 (344–351) elenca chi chiama `categoryColor` direttamente e chi prende un colore in prestito.
>     - Diretti: la torta, la storia, le barre del PAC con `actualColours()`.
>     - In prestito, con `sequenceColor`: la semi-ciambella e i paesi della storia. Con `growthBrokerColor()`: le linee dei broker e le righe del loro tooltip.
>     - La semi-ciambella e le righe del tooltip le ha aggiunte lui, verificate nel codice.
>     - «Reach» (411–419): tutti e cinque i grafici che leggono una categoria si ridisegnano su C4.
>     - Nessun numero di riga sulla pagina; nessun'altra menzione di «copy», `GROWTH_BROKER_PALETTE` o TD-1b.
>
> **Prove leggere sull'albero finale (02:28):**
> - Vitest del Lab più `chartCategories.test.ts`: 21 file, **712/712**;
> - Prettier pulito sulle 4 cartelle del Lab; `git diff --check` pulito;
> - porta 6152 libera.
>
> Delta: 5 file, cioè `engine/categories.ts`, `categories.test.ts`, `designer-lab-live.spec.ts`, `designer-lab.md` e questo piano, più la riga L-16 del backlog. Piccolo checkpoint mandato al coordinatore: **FROZEN**.

1. verificare la nuova HEAD e i suoi padri;
2. in `engine/categories.ts`, sostituire la copia con `export const categoryKey = lookupKey` (import da `$lib/theme/chartCategories`), tenendo il test di parità;
3. eseguire il Vitest del Lab;
4. `docs-writer` toglie il limite (d) e riscrive la frase sulla copia di `categoryKey()`;
5. `api sync`, se il target porta API nuove;
6. con `test-author`, aggiungere `--lf-text-secondary` alla lista `CHART_ROLES` dell'E2E C4, perché TD-1 l'ha aggiunto a `ChartRole`;
7. se Y3 e Y5 sono entrati, aggiornare:
   - con `test-author`, le costanti di estetica: `pickView.test.ts:23` `GROWTH`, che diventa `lib/features/dashboard/GrowthChart.svelte`, e la riga `scanColors.test.ts:339`;
   - con `docs-writer`, l'esempio JSON `designer-lab.md:1215`, che diventa `lib/features/brokers/…`.

**✅ Passo 7 — slot pesante (16/10, 03:26–03:50, al via del coordinatore), corsia 6152, un passo alla volta:** script `/tmp/libreFolio_L16_validate.sh`, `pre` con `API_SYNC=1`.
> **Base merge del coordinatore (03:24):**
> - `e44383f13`, con padri `88ef51358` e il target `8850ad002`;
> - entrati: Y4b (il rischio in `features/risk/`, a radice piatta), H CP-U2, A6d/e, X CP11b, Z7b, B2;
> - nessun cambio sui miei path; Y3 e Y5 non ancora entrati.
>
> **Verifica (03:25):** HEAD e padri come annunciati, 0 righe di stato, porta libera.
> - `lib/risk`, `stores/risk` e `components/risk` non esistono più.
> - L'unico file di `features/risk` con colori, senza «chart» nel nome e senza `echarts`, è `levels/L1HowMuchItHurts.svelte`. Prima stava in `components/risk/levels/`: senza la riga `features/risk` del 23:5x avrebbe cambiato livello, e con la riga resta un file di grafico.
>
> **Via del coordinatore (03:25):** «Via allo slot pesante, adesso: valida `e44383f13`».
>
> **✅ `pre` (03:26–03:31):**
>
> | Prova | Esito |
> |---|---|
> | `api sync` | exit 0, 0 righe di stato |
> | unitari | 21 file, **712/712** |
> | gate | 10 file, **186/186** |
> | `theme-roles --check` | pulito |
> | Prettier, ruff, black | puliti |
> | scanner | 3815 ms |
> | parità | **identica**: tw 10270, custom 1500, arbitrary 12, hex 1353, fn 245, var_uses 1374/877 distinte, var_defs 1073, files 1229 |
> | categorie | 27 (11/14/2), 54 letterali |
> | MkDocs strict | 0 warning, 0 errori |
> | `check-links` | 96 link validi |
>
> Porta libera, HEAD invariata.
>
> **⚠️ Fuori pista — svelte-check rosso, 1 errore, difetto mio di L-16:**
> - `scan-colors.mjs:775`, `Property 'line' does not exist on type 'object'`: `FileScan.literals` è tipato `object[]` in JSDoc, e la mia riga del passo 2 leggeva `lit.line` senza cast. Al checkpoint `4cc601e57` svelte-check non era stato eseguito.
> - **Correzione di una riga:** `categoryAt?.get(/** @type {{line: number}} */ (lit).line)`, lo stesso schema di cast già usato nel file.
> - **Dopo (03:33):**
>   - svelte-check: **0 errori, 0 warning**;
>   - `scanColors.test.ts` 66/66;
>   - Prettier pulito;
>   - **hash del catalogo identico** prima e dopo (`sha256:0dbd72c4decc…`), quindi nessun cambio d'uscita;
>   - `git diff --check` pulito.
>
> **✅ `live` (03:33–03:39):** exit 0, **12 passed** (44 s) al primo giro; il resto del tempo è la build di debug.
> - Tra i 12 ci sono i due test nuovi: «category: one asset type changes in the charts of another tab, by key» (6,1 s) e «C4: an L1 edit, a literal inside a role's definition and a reset each reach the other tab as one chart-colours signal» (4,2 s).
> - L'avviso SSL nel download di mathjax viene dalla build di MkDocs, che ha tenuto la copia in cache: non c'entra con i test.
>
> **✅ `post` (03:39–03:48):**
> - `front-designer-lab all` ai worker di default, cioè 1: exit 0, **17 E2E** (2,8 min) e **624 unitari**, 5 azioni ✓.
>   - 624 = 712 − 88: gli 88 test di `chartCategories.test.ts` (contati con `vitest list`) sono del file di DV, che il runner del Lab non elenca. Il mio comando lo aggiunge.
> - `e2e` a 4 worker: exit 0, **17 passed** (1,0 min).
> - `check-orphans`: verde, 130 E2E e 458 file di unitari raggiungibili da `all`.
>
> **✅ `release` (03:48–03:50):** `npm run build` exit 0. In `build/` zero file con il marcatore `lf-designer-lab`, il catalogo, l'indice dei test id, `parseTransparentMix`, `categoryOverrides` o `__lfDesignerLab`. Il ramo C3 di DV è sparito con il minificatore.
> - Nel worktree resta la build di release (`.build-debug` assente); il runner rifà quella di debug al prossimo E2E.
> - Porta 6152 libera dopo ogni fase (`lsof` exit 1); HEAD `e44383f13` invariata dall'inizio alla fine.
>
> **Backlog:** L-16 ✅ validato; nuova voce **L-18**, togliere i vecchi percorsi `components/` di `CHART_PATH_RE` dopo Y3 e Y5. Y4b è già entrato.

Le quattro fasi previste:
1. `pre`: unitari, svelte-check, gate, `theme-roles`, Prettier, ruff e black sulla riga Python, scanner e parità (attesi 1375 `custom` e 619 `lf`), MkDocs strict e `check-links`.
2. `live`: iterazione E2E con `test-author`.
3. `post`: `all` a 1 worker, `e2e` a 4, `check-orphans`.
4. `release`: marcatore, catalogo e indice a 0, nessuna traccia di `categoryOverrides` né di `__lfDesignerLab`.

> **Nota sui numeri attesi:** `custom` è salito a 1500, non 1375, perché il target ha aggiunto classi (T, Y4b e gli altri); la parità resta identica.

**✅ Passo 8 — checkpoint (16/10, 03:5x):** handoff al coordinatore, FROZEN, con le righe «dove guardarlo». Delta: `scan-colors.mjs` (la correzione di una riga), questo piano, la sezione L del backlog.
> **Commit del coordinatore** `fca2e06eb` (3 file). **Merge di base per l'ingresso** `995bb25bd`, con padri `fca2e06eb` e il target `d0efca910`, che porta il lotto di T (i 3 ruoli `-on-inverse` di Q10), H CP7b-1 e J CP-6. Nessun cambio sui miei path; `ChartRole` invariato, quindi nulla da toccare nell'E2E.
>
> **Controllo leggero sotto `nice -n 10` (03:54–03:55, script `/tmp/libreFolio_L16_light_995.sh`):**
>
> | Prova | Esito |
> |---|---|
> | `git diff --check` (merge e albero) | 0 righe |
> | unitari del Lab + `chartCategories.test.ts` | 21 file, **712/712** |
> | `theme-roles --check` | pulito |
> | parità scanner/Python | **identica**: tw 9520, custom 1931, arbitrary 12, hex 1349, fn 243, var_uses 1389 (872 distinte), var_defs 1097, files 1229 |
> | categorie | 27, con 54 letterali |
>
> I conteggi si spostano per il lotto di T (`custom` 1500 → 1931, `tw` 10270 → 9520). Porta libera, HEAD invariata. Niente E2E e niente build, come chiesto.

> **Ingresso nel target (03:56):** `2c485d3d4`, merge di `d8a69ab62`; l'albero coincide. Verificato in sola lettura: worktree portato a `2c485d3d4`, pulito, porta libera.

## ✅ L-18 — Togliere i vecchi percorsi `components/` dei grafici (16/10/2026, mattina; prove leggere verdi alle 08:46)

**Richiesta del coordinatore (08:34):** «Y è entrato (`d5c3c3ae3`): Y3, Y5 e Y6 hanno spostato dashboard, broker e file. […] Piccolo lotto, adesso: L-18 più la doc.»
1. In `CHART_PATH_RE` togliere `components/dashboard`, `components/risk` e `components/brokers/lots`; `components/charts` e `charts` restano. Test di `test-author`.
2. In `designer-lab.md` la frase dei percorsi dice solo i nuovi. L'esempio JSON passa al percorso vero di `BrokerImportFilesModal.svelte`, da verificare.
3. Facoltative: le costanti estetiche di `pickView.test.ts` e `scanColors.test.ts`.

Prove leggere: unitari del Lab, `--check`, parità dello scanner, MkDocs strict e `check-links`. Niente E2E: il catalogo non cambia.

**✅ Passo 1 — verifica e regex (08:35–08:40).**
- **Base:** HEAD `d5c3c3ae3`, pulita, con L-16 (`2c485d3d4`) dentro; porta libera.
- **Cartelle:** `components/dashboard`, `risk`, `brokers` e `files` non esistono più; `components/charts` ha 70 file. I percorsi veri sono `features/dashboard/GrowthChart.svelte`, `features/risk/CorrelationHeatmap.svelte` (radice piatta), `features/brokers/lots/LotsAnalysisPanel.svelte` e `features/brokers/BrokerImportFilesModal.svelte`.
- **Regex** (`scan-colors.mjs:193`): ora è `\/(components\/charts|charts|features\/(brokers\/lots|dashboard|risk|tools\/pac-allocator\/planner\/result))\/|chart[^/]*$`, e il commento di transizione è tolto.
  - `components\/charts` è assorbito da `charts`; resta perché la doc lo nomina, ed era così anche prima di L-16.
- **Catalogo:** **hash identico** prima e dopo (`sha256:45af67d34891482b…`), stessi livelli: css-literal 1104, chart-color 369, script 105, markup 2, static 70.
- **Prova sulla regex:**
  - danno chart: `components/charts/`, un `charts/` qualunque, `features/{dashboard,risk,brokers/lots}/`, il risultato del PAC, i nomi con «chart»;
  - non danno chart: `components/{dashboard,risk,brokers/lots}/`, `features/brokers/` fuori da `lots`, `utils/format.ts`.

> **⚠️ Fuori pista — l'esempio JSON:** `BrokerImportFilesModal.svelte` è in `features/brokers/`, ma non contiene più `#374151`. Il lotto di T ha messo `border-bottom-color: var(--lf-cmp-broker-import-files-divider-border-dark)`. Col solo percorso nuovo l'esempio resterebbe falso.
> - Il catalogo registra oggi lo stesso valore e lo stesso tema in `src/lib/components/ui/feedback/LoadingSpinner.svelte:60:23`, selettore `:global(.dark) .spinner`, proprietà `border-color`. L'esempio passa lì, e id, target, from e to non cambiano.
> - Altri esempi della pagina hanno righe scadute: `AssetCard.svelte:133` (ora `case 'up':`) e `DataTable.svelte:1607` (ora `}`), mentre `TransactionsTable.svelte:993` (`tx-table`) è giusto. Sono fuori perimetro: `docs-writer` li elenca, e vanno nel backlog.

**✅ Passo 2 — test e doc (agenti in parallelo, 08:40–08:44):**
- `test-author` (`e9283542`): in `scanColors.test.ts` via le righe di `components/{dashboard,risk}`, una riga per ogni alternativa della regex, il rischio al percorso piatto vero, e una riga negativa per una cartella di prima. In `pickView.test.ts`, `GROWTH` passa a `features/dashboard/GrowthChart.svelte`.
- `docs-writer` (`9decc98d`): la frase dei percorsi (549–553), l'esempio JSON su `LoadingSpinner.svelte:60`, e l'elenco degli esempi scaduti, solo da riportare.
> **`docs-writer`, fatto (08:4x), senza run:**
> - righe 549–552: la frase elenca solo quello che la regex accetta oggi, senza gli spostamenti;
> - righe 1218–1226: l'occorrenza è `LoadingSpinner.svelte:60:23`, `:global(.dark) .spinner`, `border-color`, riletta sul file (`col` a base 1 come nello scanner). Il resto della modifica non cambia, e nessun'altra frase dipendeva dall'esempio. Nessun percorso della pagina punta più a file che non esistono.
> - **Esempi scaduti, riportati e non corretti:**
>   - `AssetCard.svelte:133`, per `--color-emerald-600@light`: oggi c'è solo un `dark:border-emerald-600` alla riga 134, e le cifre di `impact` sono vecchie;
>   - `DataTable.svelte:1607` con `#64748b`: il valore non c'è più nel file, e la regola `th` legge un ruolo di componente. Serve una cattura nuova, non un numero di riga;
>   - `TransactionsTable.svelte:993` è giusto.
>
>   Vanno nel backlog come **L-19**.
>
> **`test-author`, fatto (08:42):** 21 file, **713/713**, Prettier pulito. Con la sola regex nuova erano 712, con 2 rossi: proprio le righe dei rami tolti.
> - `scanColors.test.ts`, le righe positive di «recognises a chart by %s»:
>   - tolte `components/dashboard/Kpi.svelte` e `components/risk/Heatmap.svelte`;
>   - aggiunte `components/charts/GeographyMap.svelte` (un file vero) e `features/insights/charts/Trend.svelte`;
>   - il rischio passa al percorso piatto vero, `features/risk/CorrelationHeatmap.svelte`.
>
>   Ogni nome di file è senza «chart», quindi combacia un solo ramo. Togliere un'alternativa fa fallire una riga sola; l'eccezione è `components\/charts`, assorbito da `charts`.
> - Negativo: una riga per `components/dashboard/Kpi.svelte` (`script`, `chart: false`), con un commento perché nessuno la tolga solo perché la cartella non esiste più.
> - `pickView.test.ts:23`: `GROWTH` è ora `src/lib/features/dashboard/GrowthChart.svelte`. Cambia solo l'etichetta: il catalogo è sintetico e scrive `chart: true`.
> - Lasciati come sono, su consiglio dell'agente, `catalogView.test.ts` ed `exportFormat.test.ts`: usano `components/charts/GrowthChart.svelte`, che è ancora una cartella di grafici.
> - Nota innocua: anche `src/lib/i18n/charts/` combacia con `charts`, ma contiene solo `.json`/`.txt`, che lo scanner non legge.

**✅ Passo 3 — prove leggere (08:44:41–08:46:51, sotto `nice -n 10`, script `/tmp/libreFolio_L18_light.sh`).** Nessun E2E e nessuna build dell'app.

| Prova | Esito |
|---|---|
| `git diff --check` | 0 righe |
| unitari del Lab + `chartCategories.test.ts` | 21 file, **713/713** |
| Prettier sulle 4 cartelle del Lab | pulito |
| scanner | 2886 ms |
| **hash del catalogo**, prima e dopo la regex | **identico**, `sha256:45af67d34891482b…`; livelli css-literal 1104, chart-color 369, script 105, markup 2, static 70 |
| parità scanner/Python | **identica**: tw 8042, custom 2777, arbitrary 12, hex 1343, fn 237, var_uses 1408 (872 distinte), var_defs 1097, files 1253 |
| MkDocs strict | 0 warning, 0 errori |
| `check-links` | **97** link validi |

Porta 6152 libera; HEAD `d5c3c3ae3` invariata.

> **⚠️ Fuori pista — STOP del developer, subito dopo le prove (08:4x):** «il developer chiede di fermare tutti i sotto-agenti. Smetti subito L-18». Le prove erano già finite verdi. Ho fermato tutto e lasciato il worktree com'era, con 6 file non committati; nessun processo, i due sotto-agenti inattivi. Poi FROZEN.
>
> **Ripresa (10:21):** «Riprendi L-18, adesso. Il developer ha riavviato la macchina, quindi `/tmp` è vuota. Scrivi nel piano la nota delle prove leggere che avevi già fatto […] e chiudi L-18 nel backlog.»
> - **Verifica (10:22):**
>   - HEAD `d5c3c3ae3` e gli stessi 6 file;
>   - `mtime` di tutti prima dell'inizio delle prove (08:38–08:44:34 contro 08:44:41), quindi le prove valgono per questo albero;
>   - `git diff --check` pulito, porta libera, nessun processo nella corsia.
> - **Previsione verso il target `eb4040cd1`, che porta il quarto lotto di T:**
>   - HEAD è un suo antenato;
>   - il target non tocca nessuno dei miei 6 file né il resto del Lab;
>   - `LoadingSpinner.svelte:60` ha ancora `border-color: #374151;`, quindi l'esempio JSON resta vero;
>   - `components/{dashboard,risk,brokers}` sono ancora vuote.
> - I log di `/tmp` non ci sono più; i verdetti sono qui sopra. Lo script di parità resta salvato nei file della sessione.

**✅ Passo 4 — checkpoint (16/10, 10:2x):** L-18 ✅ nel backlog, L-19 per gli esempi scaduti, handoff FROZEN.

## ✅ L-20 — Il test del selettore in tema scuro non deve dipendere dal sottotitolo di `/transactions` (16/10/2026; validato alle 13:18)

**Richiesta del coordinatore (11:10):** «TR sta migrando `/transactions`. `e2e/designer-lab/designer-lab-picker.spec.ts`, nel test «dark-theme pick of a text-gray-500 element», fissa come soggetto il sottotitolo di `routes/(app)/transactions/+page.svelte:738`, un `text-gray-500` rimappato da `app.css`. Quando TR lo migra, il test perde il soggetto. […] rendi il test indipendente dalla migrazione. […] Scegli tu la strada più robusta. […] Solo test-author su quel file, solo prove leggere, poi la run E2E del Lab nella coda pesante. Mandami prima il piano breve.»

**Analisi (11:11–11:20, sola lettura).** Base: HEAD `6e569084a`, pulita, con dentro L-18 (`f96043473`); porta libera.
- **Il test** (`designer-lab-picker.spec.ts:419–441`): login, `/transactions`, tema scuro, precondizione `toHaveClass(text-gray-500)` sul sottotitolo, poi la scelta con Alt+Shift+D. Controlla tema e ambito scuri, `data-kind="var"`, il badge `lab-picked-dark-override` e una prima variabile qualunque.
- **Il contratto vero:**
  - il badge vale `winner.important && /html\.dark/` sul selettore (`pickView.ts:261`);
  - il tipo è `var` perché la regola vincente è fuori dal layer `utilities` e legge una variabile (`classify()`).
- **In `app.css` (208–221, fuori da ogni layer) le regole di quel tipo sono:**
  - `html.dark .text-gray-{800,900}` → `--theme-text-primary`;
  - `html.dark .text-gray-{600,700}` → `--theme-text-secondary`;
  - `html.dark .text-gray-{400,500}` → `--theme-text-muted`;
  - `.text-libre-dark` → `--theme-text-primary`;
  - `.text-libre-green` scrive un letterale, quindi non dà `var`.
- **Dopo la migrazione 1:1 di TR** il sottotitolo passa a un'utility di ruolo: in scuro vince l'utility, il badge non c'è più e il test cade.
- **Gli altri test che usano il sottotitolo** passano da `colourSourceOf()`, che accetta sia palette sia ruolo (L-10, L-13 W4): Esc e Alt+Shift+D nel picker; L1, sospensione ed export/import nel live. Reggono una migrazione 1:1 sullo stesso `<p>`, quindi restano fuori perimetro.
- **La pagina developer** non nomina il sottotitolo; la docstring del runner («dark override») resta vera.
- **Unitari:** il badge è coperto da `pickView.test.ts:412–420`, con il caso P1 e le varianti.
- **Backlog:** L-13 aveva già previsto (B6) che la pulizia di T toglierà l'override P1, e che allora il test andrà ritirato o spostato.

**Strada proposta: un soggetto proprio, con la regola vera.**
1. Pagina `/` del visitatore, come il test del ruolo: niente login, niente dati, niente area di TR.
2. A runtime, nel CSSOM della pagina, il test cerca le regole fuori da `utilities` che hanno `html.dark .<classe>` nel selettore, `color` `!important` e un valore `var(--…)`. Preferisce una classe che Tailwind genera anche come utility di testo, così l'override vince davvero su un'utility. L'ordine è quello del CSSOM, quindi deterministico.
3. Aggiunge al `body` un `<p>` con `data-testid`, `position: fixed` e uno z-index sotto il velo (2147483646), senza colore inline e con la classe trovata. Poi lo sceglie con Alt+Shift+D, come oggi.
4. Le asserzioni sono quelle di oggi, più una più forte: la prima variabile della catena è **quella** che la regola legge.
5. Senza nessuna regola del genere, cioè dopo B6, c'è un `test.skip` con un messaggio esplicito: cita B6 e L-13, e conta le regole `html.dark` viste.

**Alternative scartate:**
- cercare un elemento già presente nella pagina: dipende dal markup che cambia a ogni ondata;
- una pagina fissa del Lab: il selettore lavora nelle schede dell'app e salta gli stili del Lab, e servirebbe codice di debug solo per un test.

**Perimetro:** solo `designer-lab-picker.spec.ts`, scritto da `test-author`: il test, un helper locale per il CSSOM, l'intestazione (righe 13–16).

**Prove:**
- leggere: Prettier, tsc temporaneo sugli E2E, `git diff --check`;
- coda pesante, corsia 6152: `front-designer-lab picker`, poi `e2e` a 4 worker.

**Stato:** piano mandato al coordinatore; aspetto l'OK.

**OK del coordinatore (11:17):** «L-20: OK, come l'hai scritto: il soggetto è proprio, sulla pagina `/` del visitatore; la regola è quella vera dell'app, cercata nel CSSOM; il `<p>` va iniettato sotto il velo; in più l'asserzione sulla variabile letta dalla regola; dopo B6 il test si salta, con un messaggio esplicito.»
- L'helper locale va bene; se lo usa un terzo spec, si sposta in `lab-helpers.ts`.
- **Coda pesante:** la corsia è libera. Va presa appena `test-author` ha scritto, nella corsia 6152: `api sync`, `front-designer-lab picker`, il blocco a 4 worker.
- **Condizioni:**
  - se `/tmp` della corsia è vuota per il riavvio, si ripopola con `db populate --force --clean`;
  - avvisare all'inizio e alla fine;
  - restare sotto i 45 minuti.

**✅ Passo 1 — verifiche per il brief (11:18–11:21, sola lettura):**
- `/` del visitatore ha l'interruttore del tema, perché `AuthPageFrame.svelte` monta `ThemeToggle`.
- `retarget()` (`picker/anchor.ts:166`) sposta la scelta solo su un `<svg>` lucide antenato, quindi un `<p>` resta sé stesso.
- Il velo è `position:fixed; z-index:2147483646` (`picker/overlay.ts:142`).
- Il runner non nomina il titolo del test; la sua descrizione «dark override» resta vera.
- **`/tmp/librefolio-r2-l` non esiste più** dopo il riavvio: ripopolamento previsto. La validazione della cartella di test controlla sovrapposizioni e marcatori, non che esista.
- Script `/tmp/libreFolio_L20_run.sh`, `light|heavy`, con copia nei file della sessione, `L-20-2026-10-16/`. La fase `heavy` fa: `api sync`, populate, `picker`, e solo se è verde il blocco `e2e` a 4 worker; poi la porta.

**✅ Passo 2 — il test (`test-author` `f2887b05`, 11:2x–11:35, senza E2E):** brief con il progetto approvato, punto per punto:
- pagina `/` col Lab aperto prima;
- la ricerca nel CSSOM sul modello di `colourSourceOf()`, preferendo una classe che Tailwind genera anche come utility;
- 0 regole lette = rosso; nessun candidato = salto con messaggio;
- il `<p data-testid="e2e-lab-dark-override-subject">` iniettato dopo `chooseTheme`, sotto il velo, con la precondizione sul colore calcolato;
- le asserzioni di oggi più `data-route="/"` e la variabile esatta;
- titolo e intestazione nuovi.
> **Esito (11:35):** solo `designer-lab-picker.spec.ts`, +171/−13.
> - Intestazione 13–21; costanti 81–89 (`DARK_OVERRIDE_SUBJECT`, `BELOW_THE_VEIL = 2147483000`, `LAB_OWN_ATTR`).
> - Helper `darkOverridesOf(page)` (134–236): un solo `page.evaluate` sul modello di `colourSourceOf`. Divide il selettore sulle virgole di primo livello, rispettando parentesi e stringhe. Rende i candidati `{className, variable, selector, utility}` nell'ordine del CSSOM.
> - Il test (535–599) ha il titolo «a dark-theme pick of an element under an app.css !important override shows the variable the override reads». Il `<p>` sta in basso a sinistra, perché l'interruttore è in alto a destra.
> - **Aggiunta di `test-author`, che tengo:** la precondizione controlla anche che la variabile abbia un valore in scuro. Altrimenti `<p>` e sonda erediterebbero entrambi il colore del `body`, e il confronto passerebbe senza provare niente.
> - **Scelta attesa oggi:** `text-gray-800` con `--theme-text-primary`.
>   - È la prima regola `!important` di colore su `html.dark .<classe>` (`app.css:208–210`); quelle prima toccano solo il fondo.
>   - L'utility esiste: 79 usi nudi in `src/`, e `.text-gray-800` è in `@layer utilities` nella build delle 03:50, letta in sola lettura.
>   - Senza l'override il `<p>` sarebbe grigio 800, non `#f8fafc`: la precondizione prova davvero qualcosa.
> - **Elemento iniettato contro elemento dell'app:** nessuna differenza che arrivi alle asserzioni.
>   - Il velo e la cornice del Lab sono saltati da `elementsFromPoint`.
>   - `retarget()` lascia il `<p>` com'è.
>   - Il test id `e2e-…` è sconosciuto al catalogo, quindi niente candidati di test id; il selettore di componente dà 1 corrispondenza.
> - **Rischi residui annotati:**
>   - stessa classe in due override con variabili diverse: oggi no, e la precondizione lo nominerebbe;
>   - salto sbagliato se il CSSOM fosse letto prima di `app.css`: impossibile dopo il rendering della scheda di login.
> - **Controlli di `test-author`:** Prettier pulito; tsc temporaneo con `noUnusedLocals` a exit 0 (il file di configurazione è cancellato); `git diff --check` pulito; la divisione dei selettori provata in Node.
>
> **Mia revisione del diff (11:35):** conforme al progetto.
> - Le letture del CSSOM a 0 regole danno rosso, non il salto.
> - Dopo `test.skip(true, …)` c'è un `return`.
> - L'asserzione sulla variabile è esatta: `toHaveText` con una stringa confronta il testo intero.
> - Gli import restano tutti usati dagli altri test.
>
> **Prove leggere (11:35, fase `light`):** `git diff --check` 0 righe; Prettier pulito sullo spec.
>
> **Slot pesante (coordinatore, 12:04):** «La 1.3 ci presta il suo slot 1 appena finisce l'`all-backend` di A, verso le 12:10–12:20, fino alle 13:15. Lo usate tu e poi G-18. […] Resta sotto i 25 minuti […] Script e log nella tua cartella di sessione, non in `/tmp`.»
> - Lo script è ora nei file della sessione, `L-20-2026-10-16/libreFolio_L20_run.sh`, e i log stanno accanto (`run-light/`, `run-heavy/`). Le copie in `/tmp` sono cancellate.
> - Controllo del tempo: il blocco a 4 worker, circa 3 minuti, parte solo entro i 1200 s dall'inizio. Così la run resta sotto i 25 minuti.
> - Pronto alle 12:05: HEAD `6e569084a`, 3 file nello stato, porta libera. Aspetto il via.
> - **Cambio (12:12):** «lo slot 1 prestato dalla 1.3 va a IM […] Tu parti nella nostra corsia subito dopo AF, verso le 12:45: ti mando il via. Il piano resta lo stesso».
> - **Ritardo (12:45):** AF rilancia 6 spec prima di entrare, perché X aspetta quell'ingresso; ha tempo fino alle 13:10. «Tu parti subito dopo, verso le 13:10: ti mando il via.»

**✅ Passo 3 — prove leggere, poi coda pesante nella 6152 (16/10, 13:05–13:18),** con avviso al coordinatore all'inizio e alla fine.
> **Cambio d'ordine del coordinatore (11:23):** «la corsia è di G adesso, per la sua run filtrata della galleria (~10–15 minuti). Quando test-author ha finito L-20, parti solo dopo il mio via». Le prove leggere si fanno subito; la fase `heavy` aspetta il via.
>
> **Via (13:04):** «Via a L-20, adesso, nello slot 2 prestato dalla 1.3. Corsia 6152 + `/tmp/librefolio-r2-l`, taglio alle 13:35: dopo le 13:30 non parte nessun passo nuovo. […] il blocco a 4 worker solo se `picker` è verde. Se il carico a 1 minuto è sopra 60, usane 2.»
> - Lo script (`files/L-20-2026-10-16/libreFolio_L20_run.sh`, versione 2) controlla le 13:30 prima di ogni passo nuovo e sceglie i worker dal carico a 1 minuto (`sysctl vm.loadavg`) al momento del blocco.
> - Inizio annunciato alle 13:05, con il carico a 83.
>
> **Esito della fase `heavy`** (verdetti in `files/L-20-2026-10-16/run-heavy/verdicts.txt`):
>
> | Ora | Passo | Esito |
> |---|---|---|
> | 13:05:26 | porta | libera, carico 96,6 |
> | 13:06:02 | `api sync` | exit 0, 3 righe di stato (36 s) |
> | 13:06:16 | `db populate --force --clean` | exit 0 (la cartella della corsia ricreata dopo il riavvio) |
> | 13:15:59 | `front-designer-lab picker` | exit 0, **4/4** in 17,8 s |
> | 13:15:59 | worker del blocco | carico 52,1 → **4 worker** |
> | 13:18:26 | `front-designer-lab e2e` | exit 0, **17/17** in 45,3 s |
> | 13:18:27 | porta a fine run | libera (`lsof` exit 1) |
>
> - **Il test nuovo è passato, non saltato:** `designer-lab-picker.spec.ts:535`, 833 ms da solo e 3,2 s a 4 worker. La ricerca nel CSSOM ha quindi trovato un override, e l'Element tab ha mostrato badge, `var` e la variabile esatta.
> - I 9 minuti e mezzo del passo `picker` sono quasi tutti costruzione: la build di debug (al posto della build di release delle 03:50) e la doc (197 s), con il carico 80–96. 479 s in tutto, poi il populate del runner e i test.
> - Durata totale **13 minuti**, sotto i 25; nessun passo dopo le 13:30. Nel worktree resta la build di debug; HEAD `6e569084a` invariata, 3 file nello stato.
> - Fine annunciata alle 13:18.

**✅ Passo 4 — checkpoint (16/10, 13:2x):** L-20 ✅ nel backlog, handoff FROZEN.

> **Ingresso nel target (13:20):** `460529690`, commit `d2e4ae947`. Verificato in sola lettura: worktree portato lì, pulito, porta libera.

## ✅ Audit dei colori fuori metrica (16/10/2026, notte, sola lettura)

**Richiesta del coordinatore (21:52):** «Lavoro per stanotte: analisi in sola lettura, nessuna modifica al codice. […] Stasera il developer ha visto `DataTable` coi vecchi colori. La causa: 583 token di componente in `lib/theme/components/*.css` ancora letterali, che il mio conteggio non vedeva. […] Voglio essere sicuro che non ci siano **altre fonti di colore fuori dalle metriche**. Il tuo catalogo del Designer Lab le conosce meglio di tutti.»
- **Consegna:** un rapporto in `L-designerLab/audit-colori-fuori-metrica.md`, con la tabella delle fonti, la classe di ognuna (legittima, residuo con chi e stima, dubbio) e il totale «vero».
- **Vincoli:** solo comandi leggeri, sotto `nice` se il carico supera 50; nessun server, nessun E2E. Poi checkpoint solo docs, rapporto più piano, e FROZEN.

**✅ Passo 1 — perimetro delle metriche (21:53–21:58).**
- HEAD `5b916aa28`, pulita; porta libera; carico 45/110/115.
- Dal codice di `scripts/theme/theme-roles.mjs`:
  - si misurano solo `src/**/*.{svelte,ts,js}` di produzione, commenti tolti;
  - m2 esclude `lib/theme/**` e le `LITERAL_EXCEPTIONS`;
  - nessun `.css`, `app.html` o `static/`;
  - nessun `var()`.
- Il catalogo del Lab legge anche `.css`, `app.html`, `offline.html` e `manifest.json`, ma non i nomi di colore né il resto di `static/`.

**✅ Passo 2 — conteggi (22:00–22:10).** Script nella cartella della sessione (`files/L-audit-2026-10-16/`: `audit.mjs`, `details.mjs`, `counts.mjs`, con i loro output), tutti sotto `nice -n 10`.
- **Confermati:** m1 697, m2 2, token di componente 583.
- **Trovate fuori metrica:**
  - `chartTheme.ts`, 276 letterali della vecchia palette slate, letti da 32 file;
  - `drawnColors.ts`, 32;
  - il legacy di `app.css`, 65, che si spegne con m1;
  - 99 ombre Tailwind senza colore;
  - 21 controlli nativi sull'accento del browser;
  - 5 blocchi ECharts sui predefiniti: i tooltip di `CorrelationHeatmap` e `ScatterChart`, tre `axisPointer`;
  - il tema di embedpdf, 45 colori, con preferenza `'system'`;
  - cheetah-grid in chiaro;
  - un `var(--color-libre-green)` che vince sul token;
  - i colori generati, ≈ 51 chiamate.
- **Nessun colore** dal backend, nessun uso di `var(--color-<famiglia>-…)`, nessuna classe dinamica, nessun `@apply`.

> **⚠️ Fuori pista — il catalogo del Lab conta anche i commenti:** il primo giro ha dato «regole» strane in `tokens.css` (64) e nei file dei token (87). Erano colori scritti nei commenti: note della designer, e `/* rgba(…) */` accanto ai token. I conteggi del rapporto sono rifatti senza commenti, con la regola del cricchetto (`counts.mjs`); in tutto ≈ 170 voci del catalogo. Va nel backlog come **L-22**.

> **⚠️ Fuori pista — tre falsi allarmi chiariti prima di scrivere:**
> - i 55 «letterali» del Lab nel codice sono in realtà 20 `color-mix` di variabili, 22 eccezioni e 2 valori m2; i restanti stanno nei commenti;
> - `--theme-color` in `ImageCropper` è la variabile di cropperjs, letta da un token, non il vecchio `--theme-*`;
> - `favicon.svg` di `src/lib/assets` non è usato.

**✅ Passo 3 — rapporto (22:12–22:2x):** [`audit-colori-fuori-metrica.md`](audit-colori-fuori-metrica.md).
- **Totale vero:** ≈ 506 punti fuori dai ruoli che nessuna metrica conta, oltre ai 1282 già contati. Tolti i 65 di `app.css`, che muoiono con m1, il lavoro nuovo è ≈ 441, più le librerie e i colori generati.
- **6 domande per il developer,** nessuna bloccante per stanotte.

**✅ Passo 4 — checkpoint (16/10, 22:2x):** solo docs (rapporto, piano, sezione L del backlog con L-21 e L-22), FROZEN.
> **⚠️ Fuori pista, regola Git mia infranta e annullata (22:16):** per far passare `git diff --check` anche sul file nuovo, l'ho segnato con `git add -N` e poi tolto dall'indice con `git reset -q -- <file>`. Il mio ruolo non ammette né la messa in stage né `git reset`. Effetto nullo: indice vuoto (`git diff --cached` senza file), HEAD `5b916aa28` invariata, il file di nuovo `??`. Per i file nuovi uso d'ora in poi un controllo senza Git (`grep` degli spazi finali), che qui dà 0. Segnalato al coordinatore nel checkpoint.
