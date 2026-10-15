# Misura finale del rumore — 15/10/2026 (`g-final3`)

> Workstream G, checkpoint 2. Numeri grezzi: [stability-2026-10-15.md](stability-2026-10-15.md); misura di partenza:
> [stability-2026-10-14.md](stability-2026-10-14.md); piano: [plan-phase00GalleryDeterminism.prompt.md](../plan-phase00GalleryDeterminism.prompt.md).

## Condizioni

- **Commit** `2338aaf79` di `dev_release2`: G checkpoint 1 più i lotti 1.3 integrati fino a quel momento. Checkout
  principale, corsia del coordinatore (6150, `/tmp/librefolio-r2-main`), altre corsie ferme. L'ha lanciata il coordinatore.
- **Due run complete**, ciascuna con `db populate` nuovo:
  - r1 `g-final3-r1`: dalle 09:14:58, 1833 s;
  - r2 `g-final3-r2`: dalle 09:45:57, 1791 s.
- **Configurazione e prove:**
  - 6 worker (`-- --workers 6`), carico 11–16;
  - exit 0, 2824 PNG ciascuna, la stessa lista di 32 scatti stale;
  - stesso `commit`, `dirty_files` 0, `app_version` `v0.0.0-review`, versione fissata dal toolkit (`70c84accc`).
- **`live_price_check`: 0 su entrambe.** Nessun prezzo live è arrivato al backend.
  - I sette marcatori che lo script cerca sono ancora nel codice dopo il riordino di X, in
    `backend/app/services/assets/price_query.py` e nel plugin Yahoo Finance: lo «0» vale come prova.
- **Diff** (`diffs/g-final3__r1__vs__r2`):
  - 2107 immagini identiche, 717 cambiate, nessuna di altezza diversa;
  - 717 maschere più `stability.json` e `stability.md`, per il cancello di R.
- **Una prima r1 a 10 worker** (`g-final2-r1`) è stata fermata dal coordinatore dopo 10 minuti: 8 test rossi a carico 65.
  Vedi G-2, sotto.

## Classi

| Classe | 14/10 (`27228466c`, 10 worker) | 15/10 (`2338aaf79`, 6 worker) |
|---|---:|---:|
| stable | 57 | 40 |
| low | 74 | 112 |
| medium | 19 | 19 |
| unstable | 27 | **6** |

Dove sono finite le 27 instabili del 14/10:

- **8 ora `stable`.** Le cause erano lo sfondo del login, lo scorrimento del pannello lotti, i percorsi del test.
  - `auth/01-login`, `assets/detail-classification`, `brokers/import-modal`, `settings/user-preferences`;
  - `brokers/fifo-lots-panel` e `-wac-chart`, `dashboard/fifo-lots-panel` e `-wac-chart`.
- **16 ora `low`**, cioè al massimo lo 0,1 % di pixel diversi:
  - `auth/02` e `auth/03`;
  - `assets/detail-chart`, `-candlestick`, `-rolling-return`, `-editor`, `-signals`, `-signals-tree`;
  - `brokers/detail`, `edit-modal`, `info-tab`, `sharing-modal`, `positions-holdings-table`, `fifo-lots-comparison-chart-return`;
  - `settings/cache-panel`, `global-settings`.
- **1 ora `medium`:** `files/static-grid`, che cambia solo per gli orari.
- **2 ancora `unstable`, di solo contenuto e già accettati:** `media/asset-picker-modal`, `brokers/import-nway-compare`.

Rispetto al 14/10, 27 schermate passano da `stable` a `low`. Non è stile:

- 24 hanno Δ massimo fra 1 e 15 livelli su 255, cioè antialiasing invisibile;
- 3 arrivano a Δ 43–70 su pochi pixel: lo spigolo di un'icona (`fx/detail-csv-import`, 28×6 px;
  `dashboard/positions-holdings-map`, 12×12 px) e due aree minime della barra del grafico (`assets/detail-events`).
  Guardati a occhio, A e B sono indistinguibili.

## Le 6 instabili

| Schermata | Varianti cambiate | Max | Cosa cambia | Verdetto |
|---|---:|---:|---|---|
| `media/asset-picker-modal` | 16/16 | 24,1 % | L'ordine delle immagini del seed: gli avatar hanno lo stesso `uploaded_at` e, a parità, la lista segue l'ordine della directory, cioè degli UUID casuali (backlog G-10) | Contenuto, accettato (coordinatore, 14/10) |
| `brokers/import-nway-compare` | 6/16 | 1,1 % | L'ordine dei due file del set: colonne scambiate | Contenuto, accettato (coordinatore, 14/10) |
| `assets/detail-measures` | 7/16 | 48,4 % | Inquadratura su mobile | **Stile**, corretto in G2; resta l'header di 1 variante (es chiaro), G-11 |
| `assets/detail-measures-active` | 5/16 | 49,3 % | Inquadratura su mobile | **Stile**, corretto in G2 |
| `settings/about-plugin-diagnostics` | 3/16 | 39,6 % | Inquadratura su mobile | **Stile**, corretto in G2 |
| `settings/scheduler-config` | 16/16 | 7,9 % | La pagina dietro il modale, in 5 varianti desktop; nelle altre solo l'orario del server | **Stile**, corretto in G2 |

Le 4 di stile, con le impronte (`🔎`) delle due run:

- **`assets/detail-measures` e `-active`, mobile.** Desktop identico in ogni run: `y` 281, header nascosto.
  - Impronte:
    - it/light: `y` 495 → 420;
    - es/light: `y` 491 con l'header visibile → `y` 416 con l'header nascosto;
    - es/dark: `y` 491 con l'header visibile → `y` 491 con l'header nascosto.
  - Causa: `detailChart.scrollIntoViewIfNeeded()` dopo il clic sul toggle delle misure. Scorre solo «se serve» e centra,
    quindi l'esito dipende da dove l'ha lasciata il clic. L'header (`Header.svelte`) segue il verso dell'ultimo
    scorrimento.
- **`settings/about-plugin-diagnostics`, mobile.** Desktop identico in ogni run.
  - Impronte: en/light `y` 1754 → 1662; it/dark 1786 → 1694; es/light 1716 → 1808. La pagina ha la stessa altezza, e
    lo scroll cade a 92 px esatti di distanza.
  - Causa: lo scroll corre contro il pannello Tools, che fa crescere il blocco quando arriva il suo catalogo. Il
    commento del test descriveva già questa gara (b5_c4_5), ma l'attesa di `ready|degraded` c'era solo su desktop.
- **`settings/scheduler-config`.**
  - In r2 «Configurer…» sta al centro dello schermo (y≈360): è l'inquadratura della baseline del 14/10 (y≈359), dove
    cambiava solo l'orologio.
  - In r1 la pagina è scrollata 59 px in meno e il pulsante sta a y≈419.
  - Causa: `configBtn.scrollIntoViewIfNeeded()` su una pagina non ancora ferma, partendo da una posizione che varia. Il
    pulsante a volte era già nello schermo e restava dov'era, a volte no e veniva centrato.
  - `🔎` non lo vede: `ModalBase` blocca lo scroll del body (`position: fixed`, `top: -scrollY`), quindi su ogni scatto
    con un modale `y` vale 0 e l'altezza della pagina è quella dello schermo.
  - `settings/scheduler-log` ha lo stesso schema. Il 14/10 sera è saltato al 7,5 % in una variante; oggi è `low`.

**Perché sono comparse dopo G.** Il 14/10 queste 4 erano `stable` o `low`. G non ha introdotto il difetto: l'inquadratura
era già fragile, e G l'ha messa a nudo.

- Prima lo scatto partiva 200 ms dopo un `networkidle` che in una SPA si risolve subito, quindi coglieva sempre lo stesso
  stato transitorio. Per esempio, il pannello Tools era ancora in caricamento.
- Ora `settleShot` aspetta il contenuto finale, e lo scroll fatto prima nel test corre contro il layout.

**La correzione** (checkpoint 2, test-author) tocca solo il percorso instabile:

- measures e diagnostica su mobile usano `frameTarget`; la diagnostica aspetta il pannello Tools su entrambi i viewport;
- i due modali dello scheduler usano un nuovo helper: pagina ferma, pagina in cima, poi `scrollIntoViewIfNeeded`. Dalla
  cima l'attivatore è sotto il primo schermo, quindi viene centrato ogni volta allo stesso modo;
- `🔎` legge anche l'offset bloccato dal modale.

Le inquadrature desktop non cambiano. Cambiano le 3 mobile. Dietro `scheduler-config` resta l'inquadratura centrata,
quella del 14/10 e di r2, ora in ogni run.

## Le 19 medie

| Schermata | Varianti | Max | Cosa cambia | Verdetto |
|---|---:|---:|---|---|
| `tools/pac-result-proof` | 8/16 | 1,00 % | Le durate misurate in ms (richiesta, worker, calcolo) e la ripartizione del tempo | Contenuto |
| `brokers/import-wizard-fix-step` | 6/16 | 0,70 % | I numeri di riga (#4 e #10, #3 e #9) | Contenuto (ordine dei file) |
| `files/static-tab` | 16/16 | 0,65 % | Gli orari di caricamento, l'ordine delle immagini del seed | Contenuto |
| `files/brim-report-sets` | 16/16 | 0,56 % | Il nome dell'account usa e getta | Contenuto |
| `brokers/import-wizard-assets-step` | 6/16 | 0,52 % | L'ordine dei due file, il nome dell'asset unificato | Contenuto |
| `brokers/import-wizard-duplicates-step` | 6/16 | 0,52 % | La descrizione del gruppo, presa dal primo file | Contenuto |
| `dashboard/fifo-lots-table` | 10/16 | 0,44 % | Le celle della colonna fissata (sticky) | Residuo di resa: persiste anche da solo (14/10) |
| `brokers/import-report-set-pairing` | 16/16 | 0,37 % | Il codice casuale del set | Contenuto |
| `settings/about-tool-diagnostics` | 16/16 | 0,35 % | L'hash dello snapshot del processo, i job completati | Contenuto |
| `transactions/bulk-todo-banner` | 8/16 | 0,25 % | Il codice casuale del set | Contenuto |
| `files/static-grid` | 16/16 | 0,22 % | Gli orari | Contenuto |
| `media/file-uploader-empty` | 8/16 | 0,16 % | Gli orari | Contenuto |
| `onboarding/contextual-guide` | 8/16 | 0,15 % | L'account usa e getta | Contenuto |
| `dashboard/fifo-lots-comparison-chart` | 7/16 | 0,13 % | La colonna fissata della tabella dei lotti | Residuo di resa |
| `dashboard/fifo-lots-comparison-chart-return` | 7/16 | 0,13 % | Come sopra | Residuo di resa |
| `onboarding/core-tour-step` | 8/16 | 0,13 % | L'account usa e getta | Contenuto |
| `media/image-edit-modal` | 10/16 | 0,12 % | Gli orari | Contenuto |
| `assets/detail-signals-rsi` | 3/16 | 0,11 % | L'antialiasing delle linee, Δ massimo 14 | Resa del canvas |
| `assets/detail-signals-macd` | 5/16 | 0,10 % | L'antialiasing delle linee | Resa del canvas |

I ritagli A | B di ogni riga sono in `LibreFolio_visual_review/g-workstream/2026-10-15/final3/crops/`.

## Impronte

Su 2696 scatti per run, il frame (`y`, `dh`, `vh`, `hdr`) cambia solo nei 3 scatti mobile della tabella.

- `charts` differisce in 213 scatti: conta i render, non i pixel.
- `focus` differisce in 32: è l'UUID del segnale creato, che finisce nel test id.

## G-2: i rossi sotto carico

- **10 worker.** La r1 a 10 worker (`g-final2-r1`) ha avuto 8 rossi, tutti desktop, nei primi 10 minuti:
  - `main dashboard`, `dashboard fifo lots panel`, `dashboard empty state`;
  - `user preferences`, `changelog modal`, `static resources grid view`;
  - `transaction list`, `transaction picker modal`.

  Le richieste sono rimaste in volo 10–20 s: un chunk JS 20 s, `GET /api/v1/brokers/8` 10 s, icone statiche 10 s.
  Rifatti da soli, gli 8 test passano.
- **6 worker:** 0 rossi in 2 run complete.
- **Verdetto:** saturazione della macchina. `dev.py mkdocs gallery` avvia di default un worker browser per CPU più 3
  worker server.
- **Conseguenze:**
  - il README del toolkit dice `-- --workers 6`, circa il 60 % dei core;
  - il default in `dev.py` passa a J (C-94), decisione del coordinatore.

## Verifica delle correzioni (checkpoint 2, 15/10 pomeriggio)

**Condizioni.** `verify_frames_c2.sh`, corsia 6153, i 4 test (8 esecuzioni, desktop e mobile) da soli a 1 worker.

- **A** (`g-c2-w1-a`): populate nuovo e rebuild debug con la versione fissata; 12:23–12:35, carico 13 → 72.
- **B** (`g-c2-w1-b`): `--no-populate`; 12:35–12:43, carico 72 → 28.
- In parallelo girava la candidata di T a 6 worker, nella corsia 6155.

**Esito**

- 8 passati in A e 8 in B; `live_price_check` dà 0 su entrambe.
- Diff A↔B: 80 immagini, 47 identiche.

| Schermata | Classe A↔B | Max | Nota |
|---|---|---:|---|
| `settings/about-plugin-diagnostics` | stable | 0 % | Era instabile (39,6 %) |
| `settings/scheduler-log` | stable | 0 % | |
| `settings/scheduler-config` | low | 0,026 % | Solo l'orario del server |
| `assets/detail-measures-active` | low | 0,0095 % | Antialiasing, Δ ≤ 5 |
| `assets/detail-measures` | unstable | 5,79 % | 1 variante su 16: mobile es/light, l'header |

**Impronte.** Su 80 scatti per run, il frame (`y`, `lock`, `dh`, `vh`) è identico in A e B. L'unica differenza è l'header
di `mobile/es/light/assets/detail-measures`: `visible` in A, `hidden` in B. I `charts` cambiano in 16 scatti, ma contano
i render, non i pixel.

**Inquadrature misurate**

| Schermata | Desktop | Mobile |
|---|---|---|
| `detail-measures` | `y` 281, invariata | La pagina finisce prima: scroll fermo a 556 px (552 in es), registrato con `↕️` |
| `detail-measures-active` | `y` 281, invariata | 621 px (617 in es) |
| `about-plugin-diagnostics` | 1367/1397, invariata | `frameTarget`: 1746–1818 secondo la lingua |
| `scheduler-config` | 880 px sotto il blocco, in tutte le 8 varianti | 1452–1504 |
| `scheduler-log` | 716 px sotto il blocco | 1260–1292 |

Desktop di `scheduler-config`: «Configurer…» è centrato, come nella baseline del 14/10 e in r2 di `g-final3`.

**⚠️ La previsione era sbagliata.** Avevo scritto che dietro `scheduler-config` la pagina sarebbe tornata «in cima». Non
è così: dalla cima l'attivatore sta sotto il primo schermo, quindi viene centrato. È l'inquadratura del 14/10; la variante
diversa era r1, con la pagina 59 px più in alto. Corretti il commento di `bringIntoViewFromTop` e questa analisi.

**Residuo: l'header a scroll fermo, solo in spagnolo (backlog G-11).**

- Quando la pagina finisce prima del grafico (mobile measures), lo scroll verso il basso dovrebbe nascondere l'header.
- In 4 run è rimasto visibile 3 volte, sempre in spagnolo:
  - `g-final3-r1`, con il percorso vecchio: es chiaro e scuro;
  - `g-c2-w1-a`, con `frameTarget`: es chiaro. Lo dice già la riga ↕️ («header visible»), quindi è successo prima dello
    scatto.
- Nelle altre lingue non è mai successo.
- `Header.svelte` rimette `visible` senza scroll a ogni `syncScrollContext()`. Lo chiamano:
  - il focus che esce dall'header;
  - il ResizeObserver dell'header;
  - un `resize` della finestra;
  - il cambio di `routeKey` (`pathname + search`);
  - menu e blocco dei modali.
- Quale scatti in spagnolo non si vede dal codice: serve una run strumentata.
- Proposta: nella gallery, a scroll fermo, un breve su-e-giù che riporti l'header nello stato di uno scroll in basso,
  più la diagnosi della causa.

**Rispetto alla misura (`g-final3-r1` ↔ `g-c2-w1-a`)**

- Cambiano una volta:
  - le 3 inquadrature mobile previste (`detail-measures`, `-active`, `about-plugin-diagnostics`);
  - `scheduler-config` desktop, nelle 5 varianti che r1 aveva non centrate.
- Restano uguali: desktop di measures e della diagnostica, quest'ultima identica 0/8.
- `scheduler-log` cambia solo per il contenuto. Il log seminato ha orari fissi del giorno prima, e il filtro «Last 24
  hours» fa uscire le voci con l'ora del giorno: alle 09:15 tre voci, alle 12:29 due, perché quella delle 12:10 è uscita.
  Il modale cambia altezza. È contenuto legato all'orario (D2: nessuna normalizzazione).

## Per R

Il cancello usa `--ignore-masks diffs/g-final3__r1__vs__r2/masks --stability diffs/g-final3__r1__vs__r2/stability.json`.

Le inquadrature corrette cambiano una volta con il checkpoint 2 di G: le 3 mobile e il desktop di `scheduler-config`. Il
prossimo riferimento dello stesso giorno deve quindi contenere G2.

Riferimento e candidata vanno catturati dalla stessa parte delle ore del log seminato (circa 06:00, 12:10, 18:00,
23:00). Altrimenti `settings/scheduler-log` cambia per contenuto.

## Artefatti

Sono in `LibreFolio_subRepo/LibreFolio_visual_review/`, fuori dal repo:

- `snapshots/g-final3-r1`, `g-final3-r2`, `g-final2-r1` (quest'ultima interrotta);
- `diffs/g-final3__r1__vs__r2/`: maschere, stabilità, compositi;
- `g-workstream/2026-10-15/final3/`:
  - `stability-final3-vs-baseline.md`;
  - `moves_of_the_27.txt`;
  - `stable_to_low.txt`;
  - `crops/` e `crops-low/`.
- Verifica del checkpoint 2:
  - `snapshots/g-c2-w1-a` e `g-c2-w1-b`;
  - `diffs/g-c2-w1__a__vs__b/`, `diffs/g-final3-r1__vs__g-c2-w1-a/`;
  - log e impronte in `g-workstream/2026-10-15/logs/`.
