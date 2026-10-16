# Audit: le fonti di colore fuori dalle metriche

> **Workstream L (Designer Lab), 16/10/2026, notte.** Richiesta del coordinatore (21:52): «Voglio essere sicuro che
> non ci siano **altre fonti di colore fuori dalle metriche**. Il tuo catalogo del Designer Lab le conosce meglio di
> tutti.» Il motivo: `DataTable` coi vecchi colori, per 583 token di componente ancora letterali che il conteggio
> m1/m2 non vedeva.
>
> Sola lettura: nessun codice cambiato, nessun server, nessun E2E. Base: `5b916aa28`. Comandi sotto `nice`.
> Metodo e limiti: §6.

## In breve

- **Sì, ci sono altre fonti.** La più grande è `lib/theme/chartTheme.ts`:
  - **276 colori letterali**, della vecchia palette slate di Tailwind (`#64748b`, `#94a3b8`, `#475569`, `#cbd5e1`…);
  - li leggono **32 file**: assi, griglie, tooltip e serie di ogni grafico;
  - m2 non li conta, perché esclude `lib/theme/**`.

  È lo stesso caso di `DataTable`: i grafici di oggi sono disegnati coi vecchi grigi.
- **Altri letterali non contati:**
  - `lib/theme/drawnColors.ts`, 32 colori: foglio cheetah-grid in scuro, segnaposto delle immagini;
  - il sistema legacy di `app.css`, 65 colori: `--theme-*`, palette brand/primary/surface, rimappaggio scuro. Questo
    però si spegne da solo con m1 (B6).
- **Fonti senza letterali,** che nessun conteggio può vedere:
  - **99 ombre** Tailwind senza colore, in 34 file: il nero predefinito di Tailwind;
  - **21 controlli nativi** (checkbox, radio, range) col colore d'accento del browser: nessuna regola imposta
    `accent-color`;
  - **ECharts:** il tema d'avvio fissa solo il font. 2 riquadri di tooltip e 3 `axisPointer` restano ai colori
    predefiniti di ECharts (verificato sulle opzioni); il resto va censito a runtime;
  - il **visore PDF** (embedpdf), col suo tema a 45 colori, che segue il sistema operativo e non l'interruttore dell'app;
  - il foglio cheetah-grid in chiaro, col tema della libreria;
  - un `var(--color-libre-green)` diretto, che vince sul token (`ImageEditModal.svelte:716`).
- **Dal backend non arriva nessun colore:** 0 in plugin, schemi e API. Le email hanno 12 hex, fuori perimetro.
- **Il Lab vede quasi tutto il sorgente.** Non vede le librerie, il browser e il colore delle ombre di Tailwind. E ha un
  difetto suo: elenca ≈ 170 «colori» che stanno nei commenti (L-22).
- **Totale vero (§4):** ≈ 500 punti fuori dai ruoli che nessuna metrica conta, oltre ai 697 + 2 + 583 già noti. Tolti i
  65 di `app.css`, che spariscono con m1, il lavoro nuovo è ≈ 440.

## 1. Cosa vedono le metriche

- `frontend/scripts/theme/theme-roles.mjs` misura solo `src/**/*.{svelte,ts,js}` di produzione. Restano fuori i test,
  i `.d.ts`, i file generati e il Lab; i commenti sono tolti.
  - **m1:** classi di colore legacy, cioè famiglia con tonalità, `white`/`black`, `libre-*`, `primary-*`, `surface-*`,
    contate anche in `lib/theme/**`.
  - **m2:** letterali, cioè hex, `rgb/hsl/oklch/oklab/lab/lch/hwb` e nomi CSS in stili e attributi SVG.
    - Non conta `lib/theme/**` (`CENTRAL_PREFIX`), né le `LITERAL_EXCEPTIONS` (22 occorrenze oggi).
- **Fuori per costruzione:**
  - ogni `.css`: `app.css`, `tokens.css` e i 4 file dei token di componente;
  - `app.html` e `frontend/static/**`;
  - ogni `var(--x)`, perché non è un letterale;
  - i colori che non sono nel sorgente: librerie, browser, tema di Tailwind.
- **A `5b916aa28`,** confermati:
  - m1 **697**;
  - m2 **2**: `#1b4334` ×2 in `stores/app/themeStore.ts`, la meta `theme-color`, copia di `--lf-brand`;
  - token di componente **583** (16 + 81 + 239 + 247; 581 letterali, nessuno legge un `--lf-`).

## 2. Le fonti

**Classe:**
- **legittima:** definizione di ruoli o di palette, copia guardata da un gate, colore di terzi;
- **residuo:** da migrare, con chi e la stima;
- **dubbio:** serve una scelta.

**Lab:**
- ✓ = nel catalogo, con l'anteprima dal vivo (L1 variabili, L2 fogli, L3 grafici, categorie);
- «listato» = nel catalogo, senza anteprima;
- ✗ = non lo vede.

**Stima:**
- piccola = un'ora o meno;
- media = mezza giornata;
- grande = uno o due lotti con gallery.

**Già note** (solo il numero): m1 **697** classi; m2 **2** letterali (copie del ruolo marchio); **583** token di
componente, in migrazione stanotte.

### Letterali fuori da m2

| # | Fonte | Quanti, dove | Valori | Lab | Classe, chi, stima |
|---|---|---|---|---|---|
| 1 | `lib/theme/chartTheme.ts` | **276**: 250 hex e 26 `rgba`; 65 hex distinti; letti da 32 file | vecchia palette Tailwind (slate 200–900, green, red, violet, amber). 47 coincidono per caso con un valore di ruolo, nessuno legge un ruolo | ✓ L3 | **residuo** · T (B4: un ruolo per ogni neutro dei grafici) con DV e la designer (serie, guadagno e perdita, lotti: fase B) · **grande** |
| 2 | `lib/theme/drawnColors.ts` | **32**, 17 distinti; 3 consumatori (`FilePreviewModal`, `FilesTable`, `LazyImage`) | vecchia palette slate | listato: canvas e SVG in data URL | **residuo** · chi ha l'area file, o T · media: leggere i ruoli al disegno, come `chartRoles` |
| 3 | `app.css`, sistema legacy (P1) | **65**: | vecchia palette | ✓ L1/L2 | **residuo di pulizia** · T, con B6. Nessun lavoro in più: ogni regola muore con l'ultima classe (gate `themeTokens`) |
| | | `--theme-*` 32 (16 nomi × 2 temi), usati solo dal rimappaggio di `app.css` (15 usi, nessun componente) | | | |
| | | palette brand/primary/surface 23, in `@theme` | | | |
| | | `--shadow-card*` 2 | | | |
| | | rimappaggio scuro 8: `#546175`, `#39af50`, `#166534`, e 5 in `--tw-shadow` / `--tw-ring-color` | | | |
| 4 | `lib/theme/chartPalettes.ts` | **18** | | ✓ L3 | |
| | | scala delle mappe, 12 | della designer (GR5.1) | | **legittima** |
| | | colori predefiniti dei segnali, 6 | Tailwind 500 (`#3b82f6`…) | | **dubbio** · DV, «S9» |
| 5 | `static/manifest.json`, `background_color` | 1: `#f5f4ef` | vecchio beige; il ruolo della pagina è `#f3f5f3` | listato (static) | **dubbio** · già TC-9 (T): le icone sono dipinte su quel beige |

### Fonti senza letterali

| # | Fonte | Quanti, dove | Valori | Lab | Classe, chi, stima |
|---|---|---|---|---|---|
| 6 | ombre Tailwind senza utility di colore | **99** utility in 34 file: `shadow-sm` 55, `shadow-md` 26, `shadow` 8, `-lg` 4, `-xl` 4, `-2xl` 2. I primi: `settings/tabs/AboutTab` 16, `ui/date/DateRangePicker` 10, `ai-export/AiExportOptionsPanel` 6 | il nero con alfa del tema di Tailwind; in scuro `app.css` rimappa `sm`, base, `lg` e `xl`, non `md` e `2xl` | catalogo ✗; il selettore legge `box-shadow` ✓; L2 solo per valore | **residuo**, o decisione (D2: colore con `shadow-lf-*`) · T e i proprietari d'area · piccola per file: aggiungere la classe di colore |
| 7 | controlli nativi senza accento | **21**: 13 checkbox su 16, 2 radio su 5, 6 range su 8 | l'accento del browser (blu di sistema). Data, ora e colore seguono `color-scheme: dark`, che `html.dark` imposta | ✗: il selettore non legge `accent-color` | **residuo** · T: una regola globale `accent-color: var(--lf-checked)` (D-T16: controllo selezionato in verde focus) · piccola, con gallery |
| 8 | colori predefiniti di ECharts | 15 file avviano ECharts con `CHART_INIT_THEME`, che fissa solo il font. **Confermati 5 blocchi:** | predefiniti di ECharts | ✗: L3 tocca solo i colori scritti nell'opzione | **residuo** per i 5 blocchi · DV o i proprietari dei grafici · piccola |
| | | il riquadro del tooltip di `risk/CorrelationHeatmap` e di `charts/ScatterChart`: nessun colore, quindi bianco anche in scuro | | | |
| | | gli `axisPointer` di `dashboard/AllocationHistoryChart` e `dashboard/GrowthChart` (linea) e di `pac-allocator/…/ExposureBars` (ombra) | | | |
| | | il resto (palette delle serie senza colore, stati `emphasis`/`blur`, etichette di `markLine`) | | | **dubbio** · censimento a runtime, L-21 |
| 9 | visore PDF, embedpdf (`features/files/FilePreviewModal.svelte`) | tema della libreria: 45 colori. Nessun `theme` passato; la preferenza predefinita è `'system'` | palette di embedpdf; segue il sistema operativo, non l'app | ✗ | **residuo** · area file · media: passare `theme`, con la preferenza dall'app e i colori dai ruoli |
| 10 | foglio cheetah-grid in chiaro | tema `MATERIAL_DESIGN` della libreria, con 2 bordi riscritti | palette della libreria | ✗ (canvas) | **dubbio** · insieme alla riga 2 |
| 11 | `var(--color-libre-green, var(--lf-cmp-…))` | 1, `components/ui/media/ImageEditModal.svelte:716` | il vecchio verde libre: la variabile è sempre definita (`@theme`), quindi il token di riserva non si applica mai | ✓ uso di variabile | **residuo** · T (token media) · una riga |
| 12 | colori generati, con tinta calcolata | 7 generatori (`utils/colors.ts`, `utils/broker/brokerColors.ts`, `lotComparisonChartHelpers.ts`), ≈ 51 chiamate in ≈ 20 file. Usi: badge di broker, provider, priorità e stringhe; righe tinte; linee dei lotti | tinta dall'id o dal nome, luminosità fissa per tema | listati senza valore: non modificabili; il selettore ✓ (stile inline) | **dubbio** · scelta della designer: tinte generate o una palette disegnata, come le categorie di DV |

### Fonti legittime

| # | Fonte | Quanti | Note | Lab |
|---|---|---|---|---|
| 13 | `lib/theme/chartCategories.ts` | 54 (38 distinti) | palette per categoria della designer (GR1–GR5) | ✓ per chiave |
| 14 | `tokens.css` | 117 letterali + 15 `color-mix` | definizione dei ruoli | ✓ L1 |
| 15 | ponte e aiuti | 22 | `roleColors.ts` 16: copie dei ruoli per gli ambienti senza CSS, con gate di parità; `chartShades.ts` 3, `contrast.ts` 1, `chartColorScales.ts` 2 miscele di ruoli | ✓ |
| 16 | copie statiche dei ruoli | `app.html` 12, `offline.html` 44, `theme_color` del manifest | copie di `tokens.css`, guardate dal gate `themeColorMeta` (T-4) | listato (static) |
| 17 | eccezioni di m2 | 22 | marchi social 11, generatori 8 (riga 12), `#000` del segnale demo; `#a855f7` ×2 è R-6, **dubbio** in fase B | ✓ |
| 18 | `color-mix` di variabili nel codice | 20 in 6 file | di ruoli, o dei colori generati dei broker (riga 12) | listati come «mix» |
| 19 | librerie già a posto | — | KaTeX: solo `currentColor`; lucide: `currentColor`; cropperjs: le sue variabili lette da `--lf-cmp-image-cropper-*`, nei 583 | — |

### Note a margine

| # | Fonte | Quanti | Note |
|---|---|---|---|
| 20 | `src/lib/assets/favicon.svg` | 2 (`#ff3e00`, `#fff`) | il logo di Svelte del modello, non usato da nessun file. **Dubbio:** è un file morto, si può togliere |
| 21 | backend | — | plugin, schemi e API: 0 colori. Email: 12 hex in 2 file, fuori perimetro (E); un client di posta non legge le variabili CSS, quindi servono copie |

## 3. Cosa vede il Designer Lab

- **Vede, con anteprima dal vivo:**
  - classi di palette (L1);
  - variabili e loro usi (L1);
  - letterali di CSS e `<style>` (L2);
  - letterali dei grafici nei file `chart*` e nelle cartelle dei grafici (L3);
  - categorie, per chiave.
- **Vede, senza anteprima:**
  - `drawnColors.ts` (canvas e data URL);
  - i generatori (template senza valore fisso);
  - `app.html`, `offline.html`, `manifest.json`.
- **Non vede:**
  - ciò che non è in `frontend/src`: il tema di Tailwind (ombre), i predefiniti di ECharts, embedpdf, cheetah-grid,
    l'accento del browser;
  - `frontend/static/` oltre `offline.html` e `manifest.json`;
  - `favicon.svg`.
- **Difetto suo (L-22):** il catalogo elenca anche i colori dei commenti, ≈ 170 voci su 1450. Per esempio
  `/* rgba(147, 51, 234, 0.25) */` accanto a un token: 87 nei file dei token di componente, 33 in `lib/theme/*.ts`, 27
  in `tokens.css`. Non sono fonti, e il cricchetto li ignora. È parente di L-14, le classi nei commenti.

## 4. Il totale vero

| | Conteggio |
|---|---|
| Già misurato: classi m1 | 697 |
| Già misurato: letterali m2 | 2 (copie del ruolo marchio) |
| Noto, in migrazione: token di componente | 583 |
| **Fuori dalle metriche:** letterali della vecchia palette | **373**: `chartTheme.ts` 276 + `drawnColors.ts` 32 + `app.css` 65 (questi 65 si spengono con m1) |
| Fuori dalle metriche: letterali da decidere | 7: colori dei segnali 6 + `background_color` 1 |
| Fuori dalle metriche: punti senza letterale | **126**: ombre 99, controlli nativi 21, blocchi ECharts 5, variabile legacy 1 |
| Fuori, non numerabili da qui | 2 temi di libreria (embedpdf, cheetah-grid in chiaro), il resto dei predefiniti di ECharts (L-21), i colori generati (≈ 51 chiamate, per scelta) |

**Fuori dai ruoli oggi:**
- i **1282 già contati** (697 + 2 + 583);
- **≈ 506 punti che nessuna metrica conta:** 373 + 7 letterali e 126 punti senza letterale;
- di questi, **≈ 441 sono lavoro nuovo:** i 65 di `app.css` muoiono con m1.

Più le librerie e i colori generati.

## 5. Domande per il developer

Nessuna è bloccante per stanotte.

1. **`chartTheme.ts`, 276 colori.** Chi e quando?
   - Proposta: T con B4 per i neutri (assi, griglie, tooltip, letti dai ruoli col ponte `chartRoles`, come fanno già 5
     grafici); DV con la designer per serie, guadagno e perdita, lotti.
   - Per D-T3 («niente ponte, chi non è migrato resta visibilmente vecchio») i grafici restano vecchi finché non
     migrano.
2. **Ombre:** tutte su `shadow-lf-*` (D2), oppure il nero di Tailwind va bene dove non c'è un ruolo?
3. **Controlli nativi:** una regola globale `accent-color: var(--lf-checked)`, oppure classe per classe nelle aree?
4. **Visore PDF:** tema dai ruoli e preferenza dall'app, oppure resta quello della libreria?
5. **Colori generati** (badge di broker e provider, righe, lotti): restano generati, oppure diventano una palette della
   designer?
6. **ECharts:** il censimento completo dei predefiniti richiede uno slot con un server (L-21).

## 6. Metodo e limiti

- **Script,** nella cartella della sessione di L (`files/L-audit-2026-10-16/`), non nel repository:
  - `audit.mjs`: catalogo del Lab, totali del cricchetto, definizioni e usi delle variabili per famiglia, variabili
    lette a runtime, classi dinamiche, ombre, nomi di colore nei CSS, `static/`;
  - `details.mjs`: i casi aperti dal primo giro;
  - `counts.mjs`: conteggi senza commenti, con la regola del cricchetto (un `rgb()`/`hsl()` è letterale se ha un
    numero fuori da `var()` e da `${}`).
- **Comandi `grep` di sola lettura** per librerie, controlli nativi, opzioni ECharts e backend. Carico fra 45 e 96: tutto
  sotto `nice -n 10`.
- **Limiti:**
  - le ombre sono contate per lista di classi: una lista composta con un ternario può sfuggire;
  - i controlli nativi sono contati sul tag `<input>`;
  - ECharts è verificato solo sulle opzioni scritte nel codice;
  - embedpdf e cheetah-grid non sono stati aperti a runtime.
- **Risultati senza runtime:**
  - 0 usi della palette Tailwind con `var(--color-…)`;
  - 0 variabili legacy lette per nome a runtime (si leggono solo i 7 ruoli del ponte);
  - 0 classi di colore costruite dinamicamente;
  - 0 `@apply` o `@utility` di colore;
  - nessun `--theme-*` usato fuori da `app.css`.
