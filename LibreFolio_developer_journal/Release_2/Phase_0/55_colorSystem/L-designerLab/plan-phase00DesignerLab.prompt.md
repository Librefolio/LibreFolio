# Piano — L · Designer Lab v1 (pagina nascosta per regolare i colori dal vivo, solo build di debug)

> **Workstream L** del programma colori 55. Piano di dettaglio del figlio, aperto il 14/10/2026.
> Indietro: progetto del coordinatore [`../design-designerLab.md`](../design-designerLab.md) e piano generale
> [`../plan-phase00ColorSystemThemeLab.prompt.md`](../plan-phase00ColorSystemThemeLab.prompt.md).
> Backlog: sezione «L · Designer Lab (55)» di [`../../BACKLOG_POST_1.2.md`](../../BACKLOG_POST_1.2.md).

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
| 5b | Selettore di elementi (ispettore): si punta un elemento nell'app, il Lab si filtra sulle sorgenti dei suoi colori; «specializza qui» con un'ancora nell'export (richiesta del developer del 14/10 sera) | da fissare con l'analisi | ⏳ analisi inviata al coordinatore il 14/10; **nessun codice prima del via** |
| 6 | Test registrati, documentazione, gallery A/B, evidenza di release, backlog | tutto verde; gallery `identical` a parte le instabili | ⏳ in corso; checkpoint dei passi 0–5 il 14/10 sera (vedi «▶️ Ripresa del 14/10 sera») |

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