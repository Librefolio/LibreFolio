Perfetto — allora ti preparo **due piani in Markdown**, già pensati per essere dati in pasto a **Gemini CLI / coding agent** e, separatamente, a te per generare gli asset con Gemini/Nanobanana.

Parto da alcune **assunzioni sul progetto attuale** che emergono dal dump:

* il promo attuale è impostato come video da **40 secondi, 1200 frame @ 30 fps**, con **6 scene** orchestrate da `MainVideo.tsx`; i build script esistono già per `en/it/es/fr`; il progetto è quindi già concettualmente **multi-lingua**. [\[enelcom-my...epoint.com\]](https://enelcom-my.sharepoint.com/personal/emanuele_alfano_enel_com/Documents/Microsoft%20Copilot%20Chat%20Files/librefolio_remotion_dump.md)
* il progetto usa già asset sincronizzati in `public/assets/{locale}/{theme}/{device}/...`, con una distinzione tra **dark/light** e **desktop/mobile**, e ha già un primo `sync-assets.ts` che copia screenshot e verifica la presenza degli asset AI in `public/ai`. [\[enelcom-my...epoint.com\]](https://enelcom-my.sharepoint.com/personal/emanuele_alfano_enel_com/Documents/Microsoft%20Copilot%20Chat%20Files/librefolio_remotion_dump.md)
* oggi però il mapping nel sync script è ancora **molto limitato** (dashboard/echarts/datatable/signals/fx/mobile essenziali), quindi va potenziato per sfruttare davvero tutta la gallery che mi hai incollato. [\[enelcom-my...epoint.com\]](https://enelcom-my.sharepoint.com/personal/emanuele_alfano_enel_com/Documents/Microsoft%20Copilot%20Chat%20Files/librefolio_remotion_dump.md)
* ci sono già asset AI e musica di base (`chaos_bg.png`, `opensource_infographic.png`, `audio_track.mp3`), ma possiamo serenamente sostituirli o affiancarli con una nuova generazione coerente con la revisione del video. [\[enelcom-my...epoint.com\]](https://enelcom-my.sharepoint.com/personal/emanuele_alfano_enel_com/Documents/Microsoft%20Copilot%20Chat%20Files/librefolio_remotion_dump.md)

Sotto trovi:

1. **Piano 1** → per il coding agent (`PLAN_remotion_rework.md`)
2. **Piano 2** → per te, con tutti i prompt dettagliati (`ASSET_PROMPTS_nanobanana.md`)

***

# 1) `PLAN_remotion_rework.md`

> Questo è il documento da dare al coding agent.  
> È scritto con obiettivi, architettura, dettagli tecnici, deliverable e piano di esecuzione.

````md
# LibreFolio Promo Rework — Piano di Refactoring Completo (Remotion)

## Obiettivo

Evolvere il video promo Remotion da una sequenza semplice di screenshot ad un **product trailer dinamico, premium, narrativo e modulare**, mantenendo questi vincoli:

- progetto **multi-lingua** (video renderizzato per locale: `en`, `it`, `es`, `fr`);
- UI **dark/light** gestita nativamente;
- possibilità di animare partendo da **screenshot completi**, con **crop e camera movement definiti a codice**;
- manutenibilità elevata: quando la UI cambia, il video deve aggiornarsi quasi automaticamente aggiornando gli screenshot e, se necessario, pochi parametri di crop;
- supporto a build separate per lingua e possibilità di estendere la durata del video;
- integrazione con `sync-assets.ts`, da **potenziare** per sincronizzare un catalogo molto più ampio di schermate.

---

## Direzione creativa

Il nuovo promo non deve sembrare una galleria di screenshot, ma un **mini trailer di prodotto**.

Tono desiderato:
- premium SaaS / fintech / product launch;
- elegante, moderno, tecnico ma accessibile;
- motion design pulito, con glow, depth, cards, callout, diagonali, camere lente e highlight mirati;
- niente caos visivo eccessivo, ma densità narrativa più alta.

### Concetti chiave da comunicare

1. **Unifica** dati e investimenti dispersi  
2. **Analizza davvero**: non solo tracking, ma technical analysis  
3. **Importa e riconcilia**: report, wizard, duplicate detection, staging  
4. **Sempre con te**: esperienza mobile coerente  
5. **Tuo per davvero**: open source, self-hosted, cloud option **coming soon**  
6. **Invito chiaro**: Alpha + GitHub + community

---

## Nuova proposta di durata

Portare il video da **40s a 54s** (`1620 frame @ 30fps`).

Motivazione:
- permette di introdurre più contenuto senza comprimere tutto;
- consente animazioni più respirate;
- mantiene comunque un ritmo dinamico.

### Struttura proposta (7 scene)

1. **Scene 01 — Chaos / Fragmentation** → 5s → 150f  
2. **Scene 02 — Unified Dashboard Reveal** → 8s → 240f  
3. **Scene 03 — Analysis Cockpit** → 10s → 300f  
4. **Scene 04 — Import & Automation** → 9s → 270f  
5. **Scene 05 — Mobile Continuity** → 7s → 210f  
6. **Scene 06 — Open Source / Deployment Modes** → 8s → 240f  
7. **Scene 07 — CTA / Alpha / GitHub** → 7s → 210f  

**Totale:** 54s = 1620 frame.

> Se durante l’implementazione si preferisce mantenere 6 scene, si può fondere Scene 06 e Scene 07.  
> Ma la versione consigliata è a 7 scene.

---

## Testi narrativi di riferimento (EN)

### Scene 01
**Headline:**  
`Your investments are everywhere.`

**Sub:**  
`Apps. Brokers. Spreadsheets. Crypto wallets.`

---

### Scene 02
**Headline:**  
`One private dashboard.`

**Sub:**  
`All your wealth, finally connected.`

---

### Scene 03
**Headline:**  
`Portfolio tracking meets technical analysis.`

**Sub:**  
`Stocks · ETFs · Crypto · FX · Signals`

---

### Scene 04
**Headline:**  
`From broker reports to clean portfolio data.`

**Sub:**  
`Import. Reconcile. Keep everything in sync.`

---

### Scene 05
**Headline:**  
`Check. Compare. Decide.`

**Sub:**  
`Wherever you are.`

**Micro-badges opzionali:**  
`Mobile-ready · Dark/Light · Multi-language`

---

### Scene 06
**Headline:**  
`Your data. Your rules.`

**Sub:**  
`Open source · Self-hosted · Cloud option coming soon`

**Badge opzionali:**  
`Extendable · Privacy-first · Community-driven`

---

### Scene 07
**Headline:**  
`LibreFolio is in Alpha.`

**Sub:**  
`Follow the project. Join the build.`

**CTA:**  
`github.com/LibreFolio/LibreFolio`

---

## Regole narrative importanti

- **Non** mostrare più lingue nello stesso video.  
  Il video resta per-locale.  
  La natura multi-lingua può comparire come **badge breve** o in copy secondario, ma non con switch continui di lingua nello stesso render.
- **Dark/light** deve essere comunicato in modo premium usando una **transizione diagonale** (theme reveal), non semplicemente affiancando due screenshot.
- `Cloud option` va esplicitamente etichettata come **coming soon**.
- La CTA finale deve essere leggibile per almeno **1 secondo pieno** quasi statico.

---

# Architettura tecnica proposta

## 1. Nuovi file di configurazione

Creare i seguenti file:

- `src/config/videoPlan.ts`
- `src/config/galleryManifest.ts`
- `src/config/crops.ts`
- `src/config/copy.ts` (separato da i18n se utile)
- `src/config/themeReveal.ts`

### `videoPlan.ts`
Definisce:
- durata totale;
- fps;
- durata di ogni scena;
- easing standard;
- eventuali cue musicali / beat points.

### `galleryManifest.ts`
Source of truth per gli asset video.  
Deve mappare le schermate da usare nel promo per categoria.

Esempio concettuale:

```ts
export const promoGallery = {
  dashboard: {
    main: "dashboard/main.png",
    allocation: "dashboard/allocation-charts.png",
    emptyState: "dashboard/empty-state.png",
  },
  transactions: {
    list: "transactions/list.png",
    buyForm: "transactions/form-modal.png",
    dividendForm: "transactions/form-modal-dividend.png",
    fxConversion: "transactions/form-modal-fxconversion.png",
    picker: "transactions/picker-modal.png",
  },
  brokers: {
    list: "brokers/list.png",
    importStep1: "brokers/import-wizard-step1.png",
    importStep2: "brokers/import-wizard-step2.png",
    importResolution: "brokers/import-wizard-step4-resolution.png",
    importDuplicate: "brokers/import-wizard-duplicate.png",
    bulkStaging: "brokers/import-bulk-staging.png",
  },
  assets: {
    list: "assets/list.png",
    chart: "assets/detail-chart.png",
    candlestick: "assets/detail-chart-candlestick.png",
    signals: "assets/detail-signals.png",
    signalsEma: "assets/detail-signals-ema.png",
    signalsRsi: "assets/detail-signals-rsi.png",
    signalsMacd: "assets/detail-signals-macd.png",
    measures: "assets/detail-measures-active.png",
    classification: "assets/detail-classification.png",
  },
  fx: {
    list: "fx/list.png",
    chart: "fx/detail-chart.png",
    signals: "fx/detail-signals.png",
    measures: "fx/detail-measures.png",
  },
  settings: {
    schedulerConfig: "settings/scheduler-config.png",
    schedulerLog: "settings/scheduler-log.png",
  },
  files: {
    csvPreview: "files/preview-modal-csv.png",
  },
  mobile: {
    dashboard: "dashboard/main.png",
    assetsList: "assets/list.png",
    assetsChart: "assets/detail-chart.png",
  },
} as const;
````

### `crops.ts`

Definisce crop normalizzati (`0..1`) per screenshot completi.

Obiettivo:

* evitare ritagli manuali;
* mantenere aggiornabilità futura;
* centralizzare le coordinate.

Esempio:

```ts
export type CropRect = {
  x: number;
  y: number;
  w: number;
  h: number;
};

export const cropPresets = {
  dashboard: {
    heroCards: { x: 0.06, y: 0.14, w: 0.54, h: 0.20 },
    allocationChart: { x: 0.58, y: 0.30, w: 0.30, h: 0.42 },
    leftSidebar: { x: 0.00, y: 0.00, w: 0.16, h: 1.00 },
  },
  assetChart: {
    toolbar: { x: 0.08, y: 0.08, w: 0.82, h: 0.10 },
    mainChart: { x: 0.08, y: 0.18, w: 0.82, h: 0.42 },
    lowerSignals: { x: 0.08, y: 0.60, w: 0.82, h: 0.26 },
  },
  importWizard: {
    content: { x: 0.15, y: 0.15, w: 0.70, h: 0.60 },
    footer: { x: 0.55, y: 0.80, w: 0.30, h: 0.12 },
  },
};
```

***

## 2. Potenziamento di `sync-assets.ts`

Esiste già uno script di sync. Va **evoluto**, non rimpiazzato.

### Obiettivi del nuovo sync script

1. leggere un **manifest centrale** (`galleryManifest.ts` o JSON esportabile);
2. sincronizzare **tutte le schermate utili per il promo**, non solo il set minimale attuale;
3. mantenere una struttura **non flattenata**, più leggibile, ad esempio:

```text
public/assets/en/dark/desktop/dashboard/main.png
public/assets/en/dark/desktop/assets/detail-chart.png
public/assets/en/dark/desktop/brokers/import-wizard-step1.png
...
```

4. generare un **report finale** con:
   * file copiati;
   * file aggiornati;
   * file mancanti;
   * file ignorati;
5. opzionalmente generare un file macchina-leggibile:
   * `public/assets/asset-manifest.generated.json`
6. supportare future modalità:
   * `--strict` → fallisce se manca un asset richiesto;
   * `--verbose`
   * `--json-report`

### Note tecniche

* usare `fs`, `path`, `fileURLToPath` come nello script attuale;
* evitare hardcode incontrollato dei path;
* supportare le categorie dalla gallery desktop/mobile;
* preservare le directory;
* log leggibile con icone o testi chiari;
* nessuna dipendenza extra necessaria.

### Bonus consigliato

Aggiungere una validazione che controlli che per ogni asset richiesto esistano:

* almeno `en/dark` e `en/light`;
* se richiesto, anche tutte le altre lingue;
* fallback opzionale a EN se uno screenshot locale manca.

***

## 3. Nuovi componenti Remotion da creare

Creare in `src/components/`:

* `AnimatedHeadline.tsx`
* `FeaturePill.tsx`
* `GlassCard.tsx`
* `ScreenCrop.tsx`
* `DiagonalThemeReveal.tsx`
* `ScreenshotStack.tsx`
* `Callout.tsx`
* `PhoneMockup.tsx`
* `DataStream.tsx`
* `ParticlesField.tsx`
* `RepoCard.tsx`
* `SceneShell.tsx`
* `BadgeRow.tsx`

### `SceneShell`

Wrapper comune per tutte le scene:

* background layer;
* vignette/overlay;
* safe padding;
* supporto titolo/subtitolo;
* gestione easing standard;
* eventuale gradient + dark veil.

### `ScreenCrop`

Componente cruciale. Deve:

* mostrare un crop di uno screenshot completo;
* usare coordinate normalizzate;
* supportare zoom;
* supportare translate interno;
* supportare border radius, shadow, glow.

### `DiagonalThemeReveal`

Componente chiave per il dark/light premium reveal.

Input:

* `darkSrc`
* `lightSrc`
* `progress` (0..1)
* `angleDeg`
* `edgeGlowColor`
* `showHandle?: boolean`

Implementazione:

* dark come layer base;
* light come layer sopra;
* reveal via `clipPath` / `mask` / contenitore inclinato;
* bordo luminoso animato lungo la diagonale;
* leggero bagliore sul bordo.

### `PhoneMockup`

Telefono premium:

* frame del device (CSS o SVG semplice);
* screenshot interno;
* supporto swipe/replace screen;
* ombra e riflesso.

### `Callout`

Badge con linea di collegamento verso area dello screenshot.
Deve supportare:

* label;
* accent color;
* fade-in;
* line grow animation.

### `RepoCard`

Card finale per CTA:

* icona repo / GitHub style neutro;
* nome progetto;
* URL;
* badge `Alpha`.

***

## 4. Styling & motion system

Definire un piccolo sistema coerente:

### Palette

* `bgDeep`:`#050510`
* `bgNavy`:`#0A0A1A`
* `cyan`:`#67E8F9`
* `violet`:`#818CF8`
* `green`:`#34D399`
* `amber`:`#F59E0B`
* `text`:`#F8FAFC`
* `muted`: `#94A3B8`

### Motion

Usare curve diverse per:

* entrance → ease-out forte
* camera drift → lineare o ease-in-out soft
* reveal hero → cubic morbido
* CTA → spring-like controllato, senza rimbalzi vistosi

### Linee guida

* niente animazioni troppo “social cheap”;
* preferire **movimenti lenti ma intenzionali**;
* alternare momenti di intensità e momenti di respiro;
* evitare sovrapposizione eccessiva di testo.

***

# Pianificazione scena per scena

## Scene 01 — Chaos / Fragmentation (150f / 5s)

### Obiettivo

Mostrare frammentazione e overload.

### Asset

* `public/ai/chaos_bg_v2.png` (nuova versione, se disponibile)
* altrimenti fallback a `public/ai/chaos_bg.png`

### Elementi

* background AI
* cards flottanti sintetiche:
  * Brokers
  * Crypto
  * FX
  * CSV Reports
  * Spreadsheets
  * Transactions
* lieve parallax
* glitch digitale leggero
* data stream finale verso il centro

### Transizione verso Scene 02

Le cards collassano in un fascio di linee / stream.

***

## Scene 02 — Unified Dashboard Reveal (240f / 8s)

### Obiettivo

Momento wow: dal caos alla dashboard privata unificata.

### Asset desktop consigliati

* `dashboard/main`
* `dashboard/allocation-charts`
* `brokers/list`
* `assets/list`
* `transactions/list`
* `fx/list`

### Sequenza

1. reveal iniziale dashboard dark con ingresso in prospettiva;
2. mini-cards laterali con crop da broker/assets/transactions/fx;
3. callout:
   * Net worth
   * Allocation
   * Brokers
   * Assets
   * FX
4. **dark/light diagonal reveal** sulla dashboard principale;
5. hold finale pulito.

### Effetti

* leggero tilt 3D iniziale;
* zoom-out morbido;
* glow lungo il theme slider.

***

## Scene 03 — Analysis Cockpit (300f / 10s)

### Obiettivo

Far capire che LibreFolio non è solo tracking ma anche analisi tecnica.

### Asset

* `assets/detail-chart`
* `assets/detail-chart-candlestick`
* `assets/detail-signals`
* `assets/detail-signals-ema`
* `assets/detail-signals-rsi`
* `assets/detail-signals-macd`
* `assets/detail-measures-active`
* `assets/detail-classification`
* `fx/detail-chart`
* `fx/detail-signals`

### Sequenza consigliata

1. chart principale full-width
2. switch line → candlestick
3. comparsa callout `Technical Analysis`
4. reveal crop pannello segnali
5. quick card `EMA / RSI / MACD`
6. measures overlay
7. FX chart cameo
8. classification cameo
9. chiusura su headline

### Note

* questa è la scena più ricca;
* evitare di mostrare tutto insieme;
* meglio una coreografia a strati.

***

## Scene 04 — Import & Automation (270f / 9s)

### Obiettivo

Mostrare pipeline operativa e robustezza del prodotto.

### Asset

* `brokers/import-wizard-step1`
* `brokers/import-wizard-step2`
* `brokers/import-wizard-step4-resolution`
* `brokers/import-wizard-duplicate`
* `brokers/import-bulk-staging`
* `transactions/picker-modal`
* `transactions/form-modal-fxconversion`
* `settings/scheduler-config`
* `settings/scheduler-log`
* `files/preview-modal-csv`

### Narrazione

Upload → parse → resolution → duplicate detection → staging → scheduler/log.

### Sequenza

* timeline/pipeline orizzontale o diagonale;
* ogni step entra come card inclinata;
* linea dati che collega ogni step;
* indicatori:
  * Import
  * Reconcile
  * Detect duplicates
  * Stage
  * Sync
* finale: `Clean portfolio data`

### Effetti

* data pulse;
* tick ritmici allineati alla musica;
* eventuale glow verde/cyan sui passaggi completati.

***

## Scene 05 — Mobile Continuity (210f / 7s)

### Obiettivo

Far vedere continuità d’uso su smartphone.

### Asset

* mobile dashboard
* mobile assets list
* mobile chart
* opzionalmente uno sfondo AI `device_sync_bg.png`

### Sequenza

1. desktop blur in background
2. phone entra dal basso con perspective
3. swipe dashboard → assets list
4. swipe assets list → chart
5. breve diagonal dark/light sweep dentro il telefono
6. badge:
   * Mobile-ready
   * Dark/Light
   * Multi-language

### Note

* niente due telefoni statici affiancati come visual principale;
* usare al massimo un micro-confronto dark/light finale di 0.5s–1s.

***

## Scene 06 — Open Source / Deployment Modes (240f / 8s)

### Obiettivo

Comunicare libertà, proprietà del dato, roadmap deployment.

### Asset

* nuovo background AI `open_network_bg.png`
* opzionalmente l’attuale `opensource_infographic.png` come fallback

### Testo

* `Your data. Your rules.`
* `Open source · Self-hosted · Cloud option coming soon`

### Elementi

* nodo centrale “LibreFolio Core”
* moduli orbitanti / cards:
  * Open Source
  * Self-Hosted
  * Cloud option — Coming soon
  * Extendable
  * Privacy-first

### Note

* il badge `Cloud option` **deve includere “Coming soon”**;
* preferire un’architettura visuale a nodi, non solo 3 pillole statiche.

***

## Scene 07 — CTA / Alpha / GitHub (210f / 7s)

### Obiettivo

Chiusura chiara, elegante, memorabile.

### Asset

* logo
* eventuale background con particelle / data stream pulito
* repo card finale

### Sequenza

1. particelle convergono
2. logo reveal
3. `LibreFolio is in Alpha.`
4. `Follow the project. Join the build.`
5. repo card con URL
6. hold finale leggibile \~1s

### Regola

Ultimo secondo quasi fermo.

***

# i18n / copy management

L’attuale struttura i18n esiste già ma contiene placeholder in `it/es/fr`.  
Va espansa e completata.

## Fare

* aggiornare il tipo `I18nDict`;
* aggiungere chiavi per:
  * tutte le 7 scene;
  * badge e micro-pill;
  * label callout;
  * `comingSoon`;
* mantenere l’attuale approccio per-locale;
* assicurarsi che i testi non rompano i layout in FR/ES.

### Chiavi extra suggerite

* `badges.mobileReady`
* `badges.darkLight`
* `badges.multiLanguage`
* `badges.openSource`
* `badges.selfHosted`
* `badges.cloudComingSoon`
* `badges.extendable`
* `badges.privacyFirst`
* `callouts.netWorth`
* `callouts.allocation`
* `callouts.technicalAnalysis`
* `callouts.signals`
* `callouts.measures`
* `callouts.import`
* `callouts.reconcile`

***

# Refactor di Root / MainVideo

## Aggiornare `Root.tsx`

* nuova `durationInFrames = 1620`
* composizione aggiornata
* default props eventualmente:
  * `locale`
  * `themeMode?: "dark" | "light" | "dual"` se utile (ma non indispensabile)

## Aggiornare `MainVideo.tsx`

* orchestrare 7 scene via `Series`
* traccia audio principale nuova
* opzionale supporto a SFX overlay
* centralizzare i timing in `videoPlan.ts`

***

# Gestione audio

## Obiettivo

Una traccia più sincronizzata con:

* reveal dashboard;
* quick cuts analisi;
* pipeline import;
* outro logo.

## Fare

* supportare un nuovo file:
  * `public/ai/audio_track_v2.mp3`
* opzionalmente supportare anche:
  * `sfx_transition_whoosh.wav`
  * `sfx_data_pulse.wav`
  * `sfx_logo_sting.wav`

## Implementazione

* usare `<Audio />` per la traccia principale;
* opzionalmente montare SFX con offset specifici;
* tenere headroom e volumi separati.

***

# AI asset strategy

## Nuovi asset consigliati

* `public/ai/chaos_bg_v2.png`
* `public/ai/data_stream_bg.png`
* `public/ai/import_pipeline_bg.png`
* `public/ai/device_sync_bg.png`
* `public/ai/open_network_bg.png`
* `public/ai/audio_track_v2.mp3`

## Regola

Ogni scena deve avere un fallback:

* se manca l’asset AI, usare gradient + generic background interno.

***

# Punti tecnici “succulenti” da implementare bene

## 1. Crop dinamici da screenshot completo

Tutte le animazioni di dettaglio devono partire da screenshot interi, non da file ritagliati a mano.

## 2. Theme reveal diagonale premium

Implementare una maschera diagonale animata elegante, con bordo glow.

## 3. Camera motion

Introdurre lievi movimenti di camera:

* push-in;
* pan;
* tilt leggero;
* non aggressivi.

## 4. Depth / layering

Usare più layer:

* bg;
* screen principale;
* crop cards;
* callout;
* headline;
* particles.

## 5. Config-driven

Tempi, crop, asset, testi e label devono stare il più possibile in config.

## 6. Fallback robusti

Il render non deve rompersi se mancano alcuni asset AI; usare fallback interni.

***

# Piano di esecuzione per il coding agent

## Fase 1 — Preparazione struttura

1. creare branch di lavoro;
2. non toccare il commit precedente: il vecchio stato è il fallback;
3. creare directory `src/config` e `src/components`;
4. introdurre `videoPlan.ts`, `galleryManifest.ts`, `crops.ts`.

## Fase 2 — Potenziare `sync-assets.ts`

1. refactor senza rompere l’uso attuale;
2. introdurre manifest-driven sync;
3. preservare cartelle categoria/nome;
4. aggiungere report.

## Fase 3 — Costruire componenti riutilizzabili

1. `SceneShell`
2. `AnimatedHeadline`
3. `FeaturePill`
4. `ScreenCrop`
5. `DiagonalThemeReveal`
6. `Callout`
7. `PhoneMockup`
8. `RepoCard`

## Fase 4 — Rifare le scene

Ordine consigliato:

1. Scene 02
2. Scene 03
3. Scene 04
4. Scene 05
5. Scene 06
6. Scene 07
7. Scene 01

## Fase 5 — i18n

1. aggiornare tipi
2. completare EN/IT/ES/FR
3. verificare overflow testo

## Fase 6 — Audio e polish

1. integrare audio v2
2. opzionali SFX
3. allineare reveal e beat
4. regolare hold finale

## Fase 7 — Build e QA

1. `npm run sync`
2. `npm run build:en`
3. test rapido su `it/es/fr`
4. eventuale `npm run build:all`

***

# Acceptance criteria

Il lavoro è completato quando:

* il promo è passato a \~54s ed è visivamente più ricco;
* il nuovo sync script gestisce un set più ampio di schermate;
* il video usa screenshot completi con crop definiti a codice;
* il dark/light reveal è premium e diagonale;
* il mobile non è più mostrato come doppia schermata statica;
* c’è una scena chiara su import/automation;
* `Cloud option` è marcato come **Coming soon**;
* CTA finale è più forte e leggibile;
* il progetto resta renderizzabile per locale.

***

# Deliverable attesi dal coding agent

1. Refactor del codice Remotion
2. Nuovi componenti riutilizzabili
3. Sync script potenziato
4. Nuova timeline a 54s
5. Nuove scene implementate
6. i18n completato
7. README breve con:
   * come generare asset AI
   * come sincronizzare screenshot
   * come buildare i video

***

# Nota finale

Dare priorità a:

* manutenibilità;
* eleganza;
* configurabilità;
* compatibilità con futuri screenshot aggiornati.

Meglio una soluzione leggermente più semplice ma pulita, che un effetto spettacolare fragile.

````

---

# 2) `ASSET_PROMPTS_nanobanana.md`

> Questo è il piano pratico per te, con prompt dettagliati per immagini e audio.  
> Ho separato gli asset per scena e indicato **nome file desiderato**, **uso**, **stile** e **prompt**.

```md
# LibreFolio Promo Rework — Prompt dettagliati per immagini e audio (Gemini / Nanobanana)

## Obiettivo

Generare una nuova serie di asset visivi e audio per il promo Remotion di LibreFolio.

Linee guida comuni:
- estetica premium SaaS / fintech;
- dark, elegante, moderna;
- palette coerente con LibreFolio:
  - deep black `#050510`
  - dark navy `#0A0A1A`
  - cyan `#67E8F9`
  - violet `#818CF8`
  - emerald `#34D399`
- nessun testo leggibile;
- nessun logo di terze parti;
- nessuna persona;
- composizioni pulite, con spazio per sovrapporre UI e testo.

## Specifiche tecniche comuni per immagini
- risoluzione preferita: **3840×2160**
- aspect ratio: **16:9**
- formato: **PNG**
- dettaglio alto, ma non troppo rumoroso
- no watermark
- no text

---

# 1. Scene 01 — Chaos background v2

## File target
`public/ai/chaos_bg_v2.png`

## Uso
Sfondo full-screen della scena iniziale sul tema “frammentazione”.

## Prompt
Create a premium dark fintech chaos background for a product trailer.

The image should represent fragmented financial life: overlapping app windows, spreadsheet-like grids dissolving into particles, glowing chart fragments, broker panels, crypto symbols, FX tickers, and scattered financial widgets floating in a dark digital space.

The composition must feel overwhelming but elegant, not messy in a cheap way.  
Think of financial information exploding outward before being reorganized.

Style:
- cinematic SaaS trailer
- abstract but visually rich
- deep depth of field
- subtle neon glow
- premium, modern, dramatic

Colors:
- deep black #050510
- dark navy #0A0A1A
- violet #818CF8
- cyan #67E8F9
- subtle emerald #34D399 accents

Important constraints:
- no readable text
- no logos
- no people
- no single element too dominant
- leave a slightly cleaner center zone for motion overlay and headline

Resolution:
4K, 16:9

---

# 2. Scene 01→02 / Scene 07 — Data stream background

## File target
`public/ai/data_stream_bg.png`

## Uso
Transizione tra caos e dashboard, e richiamo visivo nella CTA finale.

## Prompt
Create an abstract premium financial data stream background for a modern open-source finance app trailer.

Show elegant glowing lines of data flowing and converging toward a focal point, as if scattered financial information is becoming a single organized intelligent system.

Include subtle chart fragments, tiny particles, thin geometric paths, and soft volumetric light.  
The center should feel like a convergence point where a dashboard reveal or logo reveal can happen.

Style:
- premium fintech trailer
- modern, cinematic, clean
- high-end SaaS product reveal aesthetic
- elegant, not noisy

Colors:
- deep black #050510
- dark navy #0A0A1A
- cyan #67E8F9
- violet #818CF8
- emerald #34D399

Important constraints:
- no readable text
- no logos
- no people
- no literal interface
- leave central area slightly cleaner

Resolution:
4K, 16:9

---

# 3. Scene 04 — Import pipeline background

## File target
`public/ai/import_pipeline_bg.png`

## Uso
Sfondo della scena Import & Automation.

## Prompt
Create a premium data import pipeline background for a fintech SaaS product trailer.

The image should suggest the journey from broker exports and CSV reports into clean organized portfolio data.

Visual language:
- glowing data lines moving through connected stages
- subtle representations of file import, validation, duplicate detection, reconciliation, and synchronization
- transparent cards or modular blocks
- central flow from chaotic inputs to structured output

The tone should be technical, trustworthy, and elegant.

Style:
- premium SaaS fintech
- dark cinematic
- modular and architectural
- clean, minimal, intelligent

Colors:
- deep black #050510
- navy #0A0A1A
- cyan #67E8F9
- emerald #34D399
- violet #818CF8

Constraints:
- no readable text
- no logos
- no people
- no cartoon style
- keep enough negative space for overlaying screenshots and labels

Resolution:
4K, 16:9

---

# 4. Scene 05 — Device sync background

## File target
`public/ai/device_sync_bg.png`

## Uso
Sfondo della scena mobile.

## Prompt
Create an abstract responsive app continuity background for a premium finance app trailer.

Show subtle glowing data flow moving from a large desktop interface silhouette into a smartphone silhouette, representing continuity between desktop and mobile.

Do not render literal readable UI.  
Instead, suggest synchronized information, motion, and continuity through glowing paths, layered translucent panels, and elegant geometry.

Style:
- premium product trailer
- dark, sleek, mobile-first but professional
- modern SaaS visual language
- cinematic and minimal

Colors:
- deep navy
- black
- cyan light trails
- violet accents
- subtle emerald highlights

Constraints:
- no readable text
- no logos
- no people
- keep central/lower center area clean for a phone mockup

Resolution:
4K, 16:9

---

# 5. Scene 06 — Open network / open source background

## File target
`public/ai/open_network_bg.png`

## Uso
Sfondo della scena Open Source / Self-hosted / Cloud option coming soon.

## Prompt
Create a premium open-source technology network background for a finance app trailer.

The image should suggest ownership, privacy, extensibility, self-hosting, and future cloud deployment through an abstract network of glowing nodes and modular infrastructure.

Include:
- a subtle central hub
- thin connection lines
- transparent modular blocks
- distributed nodes
- a clean architectural feeling

The visual should imply:
- open source
- self-hosted deployment
- extensibility
- privacy-first design
- cloud option coming soon

Style:
- elegant dark SaaS / infra / fintech
- cinematic but clean
- geometric and premium
- lots of negative space

Colors:
- deep black #050510
- dark teal/navy
- cyan #67E8F9
- emerald #34D399
- soft violet #818CF8

Constraints:
- no readable text
- no logos
- no people
- not too busy
- leave space in the center for animated labels

Resolution:
4K, 16:9

---

# 6. Optional — CTA background alternative

## File target
`public/ai/cta_particles_bg.png`

## Uso
Background finale alternativo per logo reveal / CTA.

## Prompt
Create a clean premium outro background for a fintech product trailer.

A dark elegant background with subtle particles, soft diagonal light streaks, and tiny glowing dots converging gently toward the center.

The composition must feel like a final reveal moment: sophisticated, calm, premium, and centered around a logo and final call to action.

Style:
- minimalist cinematic outro
- high-end SaaS reveal
- refined, clean, dark

Colors:
- deep black
- navy
- cyan
- faint violet
- subtle emerald highlights

Constraints:
- no readable text
- no logos
- no people
- do not make it crowded
- center must remain visually clean

Resolution:
4K, 16:9

---

# 7. Main music track v2

## File target
`public/ai/audio_track_v2.mp3`

## Uso
Nuova traccia principale del promo, durata 54 secondi.

## Prompt
Create a 54-second instrumental soundtrack for a premium open-source finance app product trailer.

Style:
Modern cinematic fintech trailer.  
Elegant, intelligent, confident, and premium.  
Inspired by Stripe, Linear, Vercel and Apple-style product reveal trailers.  
No vocals. No lyrics.

Duration:
Exactly 54 seconds.

Tempo:
108 BPM.

Narrative arc:
0–5s:
Fragmented digital tension. Sparse glitch pulses, subtle low bass, scattered synth textures, no full drums yet.

5–13s:
Solution reveal. A clean cinematic swell with bright synth pads and a clear sense of order and control.

13–23s:
Analysis section. Add tight electronic groove, subtle arpeggiator, precise percussion, confident motion.

23–32s:
Import and automation section. Rhythmic data-like pulse, elegant ticking digital details, forward-moving momentum.

32–39s:
Mobile continuity section. Slightly lighter and more fluid, premium synth plucks, smooth modern motion energy.

39–47s:
Open source and deployment freedom section. Warmer pads, a sense of ownership, trust, openness, community.

47–54s:
Final logo/CTA resolution. Clean emotional lift, short premium sting, then a soft tail allowing the final URL/CTA to hold clearly.

Instrumentation:
- deep synth bass
- cinematic pads
- soft electronic percussion
- clean arpeggiators
- subtle piano accents
- light string textures

Mix:
- wide stereo
- clean low end
- not aggressive
- no harsh highs
- suitable for a voiceover-free product trailer
- target around -14 LUFS

Export:
MP3 320kbps or WAV 44.1kHz

---

# 8. Optional SFX — scene transition whoosh

## File target
`public/ai/sfx_transition_whoosh.wav`

## Uso
Transizione tra Scene 01→02 e quick cuts importanti.

## Prompt
Create a premium digital whoosh transition sound for a fintech product trailer.

Characteristics:
- elegant, modern, clean
- subtle high-tech texture
- short and impactful
- no cartoon feel
- suitable for dashboard reveal and scene transitions

Duration:
0.7 to 1.2 seconds

Tone:
sleek, futuristic, refined

---

# 9. Optional SFX — data pulse

## File target
`public/ai/sfx_data_pulse.wav`

## Uso
Piccoli accenti nella scena Import & Automation.

## Prompt
Create a short premium digital data pulse sound effect for a modern fintech trailer.

Characteristics:
- precise
- subtle
- elegant
- small rhythmic tech accent
- suitable for indicating validation, sync, or successful step progression

Duration:
0.2 to 0.5 seconds

No cartoon feel.  
No harsh beeps.  
Should sound premium and modern.

---

# 10. Optional SFX — logo sting

## File target
`public/ai/sfx_logo_sting.wav`

## Uso
Logo/CTA finale.

## Prompt
Create a premium logo sting for a fintech SaaS product outro.

Characteristics:
- short
- elegant
- uplifting
- modern
- subtle emotional resolution
- premium Apple/Stripe-like finish

Duration:
1.0 to 1.8 seconds

Must feel clean and expensive, not bombastic.

---

# Checklist pratica per la generazione

## Immagini da generare con priorità alta
1. `chaos_bg_v2.png`
2. `data_stream_bg.png`
3. `import_pipeline_bg.png`
4. `device_sync_bg.png`
5. `open_network_bg.png`

## Audio con priorità alta
1. `audio_track_v2.mp3`

## Audio opzionali
1. `sfx_transition_whoosh.wav`
2. `sfx_data_pulse.wav`
3. `sfx_logo_sting.wav`

---

# Nota operativa

Quando un asset viene generato:
- salvarlo nella cartella prevista;
- verificare che il nome file corrisponda esattamente;
- se necessario creare varianti `v2`, `v3` e scegliere in seguito quella migliore;
- mantenere sempre fallback nel codice nel caso un nuovo asset non sia ancora pronto.
````

***

# Consiglio operativo finale

Questa è la sequenza che farei io, per minimizzare il rischio:

1. **commit del vecchio stato** ✅
2. dai al coding agent **solo il Piano 1** e fagli fare:
   * refactor struttura,
   * sync-assets potenziato,
   * nuovi componenti,
   * scene base rifatte con fallback visivi;
3. intanto tu generi con calma gli asset del **Piano 2**;
4. quando arrivano gli asset AI/audio:
   * li metti in `public/ai`,
   * fai un secondo pass di polish;
5. render EN;
6. solo dopo allinei bene IT/ES/FR.

***

# Suggerimento sulla durata

Ti confermo che secondo me **54 secondi** è un buon target:

* abbastanza lungo da raccontare davvero LibreFolio;
* ancora abbastanza breve da restare promo;
* permette una scena forte su **import/automation**, che è un elemento distintivo.

Se vuoi, nel messaggio successivo posso fare un ulteriore step e darti anche:

## **Piano 3 — prompt operativo per Gemini CLI**

cioè un **mega prompt unico**, già pronto da incollare nel coding agent, con tono imperativo tipo:

* cosa modificare,
* in che ordine,
* quali file creare,
* quali componenti implementare,
* quali criteri di done rispettare.

Quello sarebbe il formato più comodo da lanciare direttamente al tuo agent.


---------------------

Perfetto. Ti preparo **un unico mega-prompt dettagliato**, in italiano, pronto da **copiare e incollare in Gemini CLI / coding agent**.

L’ho costruito tenendo conto della struttura attuale del progetto Remotion che emerge dal dump: composizione `LibreFolioPromo`, scene separate in `src/scenes`, `MainVideo.tsx`, `Root.tsx`, i18n per `en/it/es/fr`, build script per lingua e `sync-assets.ts` già esistente ma ancora limitato nel catalogo di schermate sincronizzate. [\[enelcom-my...epoint.com\]](https://enelcom-my.sharepoint.com/personal/emanuele_alfano_enel_com/Documents/Microsoft%20Copilot%20Chat%20Files/librefolio_remotion_dump.md)

***

## Prompt pronto da incollare in Gemini CLI

````text
Sei un coding agent esperto in TypeScript, React, Remotion 4, motion design tecnico e refactor di progetti video code-driven.

Devi lavorare sul mio progetto Remotion per il video promo di LibreFolio e fare un refactor importante ma pulito, mantenendo alta manutenibilità e compatibilità con futuri aggiornamenti degli screenshot.

## CONTESTO

Il progetto esiste già ed è funzionante, ma il video attuale è troppo semplice e statico.
La base esistente include:
- progetto Remotion multi-scena;
- orchestrazione principale con `MainVideo.tsx`;
- composizione root in `Root.tsx`;
- scene separate in `src/scenes`;
- sistema i18n per `en`, `it`, `es`, `fr`;
- build script per locale;
- script `sync-assets.ts` già esistente che sincronizza screenshot e asset in `public/assets`.

Voglio evolvere il promo da semplice sequenza di screenshot a **product trailer dinamico, premium, elegante e modulare**, senza rompere la filosofia del progetto:
- multi-lingua;
- dark/light nativi;
- screenshot come source of truth;
- crop/zoom/animazioni fatte a codice;
- facile aggiornamento quando cambiano le UI.

## OBIETTIVO FINALE

Trasformare il promo in un trailer da circa **54 secondi** (30 fps, quindi 1620 frame), con motion design molto più curato, mantenendo il progetto pulito, configurabile e facilmente aggiornabile.

Devi:
1. rifattorizzare il progetto;
2. potenziare `sync-assets.ts`;
3. introdurre componenti riutilizzabili per crop, reveal, callout, phone mockup, ecc.;
4. riscrivere la timeline e le scene;
5. integrare i nuovi asset AI già generati;
6. integrare la nuova traccia audio e i possibili SFX ritagliati;
7. completare l’i18n;
8. lasciare il progetto buildabile almeno per `en`, e idealmente compatibile anche con `it/es/fr`.

## VINCOLI IMPORTANTI

- NON distruggere il progetto esistente. Lavora come refactor incrementale.
- NON eliminare la compatibilità multi-lingua.
- NON usare screenshot ritagliati manualmente come file separati: i ritagli devono partire da screenshot completi, con coordinate di crop definite a codice.
- NON mostrare più lingue nello stesso video. Ogni render resta per singola lingua.
- Dark/light deve essere mostrato in modo premium tramite **transizione diagonale / theme reveal**, non con semplice affiancamento statico.
- Il testo “Cloud option” deve apparire come: **Cloud option — Coming soon**.
- Se mancano asset AI, prevedi fallback con gradient/background interni.
- Mantieni il progetto elegante, configurabile e manutenibile.
- Se trovi mismatch nei path reali, ispeziona il repository e adatta il codice in modo intelligente.
- Non fermarti a fare solo scaffolding: implementa davvero la nuova struttura e le scene.

## ASSET AI DISPONIBILI

Usa, se presenti, questi file in `public/ai/`:
- `chaos_bg_v2.png`
- `data_stream_bg.png`
- `import_pipeline_bg.png`
- `device_sync_bg.png`
- `open_network_bg.png`
- `cta_particles_bg.png`

Asset vecchi ancora disponibili come fallback:
- `chaos_bg.png`
- `opensource_infographic.png`

Nota importante:
molti asset AI nuovi sono quadrati e probabilmente vanno trattati come texture/backplate, non come immagini hero full-width.
Quindi quando li usi:
- render full frame;
- `objectFit: "cover"`;
- overlay scuro;
- opzionale blur leggero;
- lieve scale drift / parallax.

## AUDIO DISPONIBILE

File disponibili:
- `public/ai/Calculated_Grace.mp3`
- `public/ai/audio_track.mp3`
- `public/ai/audio_track_v2.mp3`
- `public/ai/sfx_transition_whoosh.mp3`
- `public/ai/sfx_logo_sting.mp3`

La traccia principale da selezionare è:
- `Calculated_Grace.mp3`

Devi creare:
- `public/ai/audio_track_main_54s_fade.mp3`

Usa questo comando o equivalente:
```bash
ffmpeg -y -i public/ai/Calculated_Grace.mp3 \
  -af "afade=t=out:st=52.5:d=1.5" \
  -t 54 \
  public/ai/audio_track_main_54s_fade.mp3
````

Devi anche creare almeno queste varianti SFX:

### Transition whoosh

```bash
ffmpeg -y -i public/ai/sfx_transition_whoosh.mp3 \
  -ss 0.20 -t 1.10 \
  -acodec libmp3lame -b:a 192k \
  public/ai/sfx_transition_whoosh_cut_a.mp3
```

```bash
ffmpeg -y -i public/ai/sfx_transition_whoosh.mp3 \
  -ss 3.00 -t 1.20 \
  -acodec libmp3lame -b:a 192k \
  public/ai/sfx_transition_whoosh_cut_b.mp3
```

### Logo sting

```bash
ffmpeg -y -i public/ai/sfx_logo_sting.mp3 \
  -ss 53.8 -t 1.80 \
  -acodec libmp3lame -b:a 192k \
  public/ai/sfx_logo_sting_cut_a.mp3
```

```bash
ffmpeg -y -i public/ai/sfx_logo_sting.mp3 \
  -ss 51.8 -t 2.20 \
  -acodec libmp3lame -b:a 192k \
  public/ai/sfx_logo_sting_cut_b.mp3
```

```bash
ffmpeg -y -i public/ai/sfx_logo_sting.mp3 \
  -ss 31.5 -t 2.00 \
  -acodec libmp3lame -b:a 192k \
  public/ai/sfx_logo_sting_cut_c.mp3
```

Se non puoi lanciare ffmpeg direttamente nel contesto corrente, prepara comunque il supporto nel codice usando questi nomi file e lascia note chiare.

## NUOVA DURATA E TIMELINE

Porta il promo a:

* **54 secondi**
* **30 fps**
* **1620 frame**

Struttura consigliata a **7 scene**:

1. Scene 01 — Chaos / Fragmentation → 150f (5s)
2. Scene 02 — Unified Dashboard Reveal → 240f (8s)
3. Scene 03 — Analysis Cockpit → 300f (10s)
4. Scene 04 — Import & Automation → 270f (9s)
5. Scene 05 — Mobile Continuity → 210f (7s)
6. Scene 06 — Open Source / Deployment Modes → 240f (8s)
7. Scene 07 — CTA / Alpha / GitHub → 210f (7s)

Totale: 1620 frame.

## COPY/TESTI — VERSIONE EN DI RIFERIMENTO

### Scene 01

Headline:
`Your investments are everywhere.`
Sub:
`Apps. Brokers. Spreadsheets. Crypto wallets.`

### Scene 02

Headline:
`One private dashboard.`
Sub:
`All your wealth, finally connected.`

### Scene 03

Headline:
`Portfolio tracking meets technical analysis.`
Sub:
`Stocks · ETFs · Crypto · FX · Signals`

### Scene 04

Headline:
`From broker reports to clean portfolio data.`
Sub:
`Import. Reconcile. Keep everything in sync.`

### Scene 05

Headline:
`Check. Compare. Decide.`
Sub:
`Wherever you are.`

Badge opzionali:
`Mobile-ready`
`Dark/Light`
`Multi-language`

### Scene 06

Headline:
`Your data. Your rules.`
Sub:
`Open source · Self-hosted · Cloud option coming soon`

Badge opzionali:
`Extendable`
`Privacy-first`
`Community-driven`

### Scene 07

Headline:
`LibreFolio is in Alpha.`
Sub:
`Follow the project. Join the build.`
CTA:
`github.com/LibreFolio/LibreFolio`

## RICHIESTA i18n

Aggiorna il sistema i18n per supportare tutti i nuovi testi, badge e callout.

Devi:

* espandere i tipi in `src/types/i18n.ts`;
* aggiornare `src/i18n/en.ts`;
* completare anche `it.ts`, `es.ts`, `fr.ts`, almeno con traduzioni plausibili e coerenti;
* evitare rotture di layout in lingue più lunghe;
* mantenere fallback robusti.

## NUOVA ARCHITETTURA DA INTRODURRE

Crea/introduci una cartella `src/config/` con almeno:

* `videoPlan.ts`
* `galleryManifest.ts`
* `crops.ts`
* `themeReveal.ts` (facoltativo ma consigliato)
* `motion.ts` o `designSystem.ts` (facoltativo ma consigliato)

### 1. `videoPlan.ts`

Deve centralizzare:

* fps;
* durata totale;
* durata scene;
* timing scene;
* eventuali cue audio;
* eventuali costanti di easing.

### 2. `galleryManifest.ts`

Deve essere il source of truth degli asset promo realmente usati.

NON voglio più un set limitato di alias manuali tipo solo `dashboard_main`, `datatable_view`, ecc.
Voglio un catalogo più ampio e leggibile, basato sulle categorie reali della gallery.

Struttura consigliata:

```ts
export const promoGallery = {
  dashboard: {
    main: "dashboard/main.png",
    allocation: "dashboard/allocation-charts.png",
    emptyState: "dashboard/empty-state.png",
  },
  transactions: {
    list: "transactions/list.png",
    buyForm: "transactions/form-modal.png",
    dividendForm: "transactions/form-modal-dividend.png",
    fxConversion: "transactions/form-modal-fxconversion.png",
    picker: "transactions/picker-modal.png",
  },
  brokers: {
    list: "brokers/list.png",
    importStep1: "brokers/import-wizard-step1.png",
    importStep2: "brokers/import-wizard-step2.png",
    importResolution: "brokers/import-wizard-step4-resolution.png",
    importDuplicate: "brokers/import-wizard-duplicate.png",
    bulkStaging: "brokers/import-bulk-staging.png",
  },
  assets: {
    list: "assets/list.png",
    chart: "assets/detail-chart.png",
    candlestick: "assets/detail-chart-candlestick.png",
    signals: "assets/detail-signals.png",
    signalsEma: "assets/detail-signals-ema.png",
    signalsRsi: "assets/detail-signals-rsi.png",
    signalsMacd: "assets/detail-signals-macd.png",
    measures: "assets/detail-measures-active.png",
    classification: "assets/detail-classification.png",
  },
  fx: {
    list: "fx/list.png",
    chart: "fx/detail-chart.png",
    signals: "fx/detail-signals.png",
    measures: "fx/detail-measures.png",
  },
  settings: {
    schedulerConfig: "settings/scheduler-config.png",
    schedulerLog: "settings/scheduler-log.png",
  },
  files: {
    csvPreview: "files/preview-modal-csv.png",
  },
  mobile: {
    dashboard: "dashboard/main.png",
    assetsList: "assets/list.png",
    assetsChart: "assets/detail-chart.png",
  },
} as const;
```

Adatta ai path reali del repository, ma resta fedele a questa filosofia.

### 3. `crops.ts`

Deve contenere crop normalizzati per zoom/ritagli sugli screenshot.

Esempio concettuale:

```ts
export type CropRect = {
  x: number;
  y: number;
  w: number;
  h: number;
};

export const cropPresets = {
  dashboard: {
    heroCards: { x: 0.06, y: 0.14, w: 0.54, h: 0.20 },
    allocationChart: { x: 0.58, y: 0.30, w: 0.30, h: 0.42 },
    leftSidebar: { x: 0.00, y: 0.00, w: 0.16, h: 1.00 },
  },
  assetChart: {
    toolbar: { x: 0.08, y: 0.08, w: 0.82, h: 0.10 },
    mainChart: { x: 0.08, y: 0.18, w: 0.82, h: 0.42 },
    lowerSignals: { x: 0.08, y: 0.60, w: 0.82, h: 0.26 },
  },
  importWizard: {
    content: { x: 0.15, y: 0.15, w: 0.70, h: 0.60 },
    footer: { x: 0.55, y: 0.80, w: 0.30, h: 0.12 },
  },
};
```

I crop reali vanno adattati alle schermate effettive.

## POTENZIAMENTO DI `sync-assets.ts`

Esiste già uno script di sync.
NON sostituirlo brutalmente: evolvilo.

### Obiettivi del refactor

1. leggere il nuovo `galleryManifest`;
2. sincronizzare un catalogo molto più ricco di immagini;
3. preservare una struttura cartelle leggibile, ad esempio:
   * `public/assets/en/dark/desktop/dashboard/main.png`
   * `public/assets/en/dark/desktop/assets/detail-chart.png`
   * `public/assets/en/dark/desktop/brokers/import-wizard-step1.png`
4. supportare desktop/mobile, locale, theme;
5. generare log più chiari;
6. facoltativamente generare un manifest JSON dei file sincronizzati;
7. supportare modalità più rigorose (`strict`, `verbose`, ecc.) se utile.

### Richiesta esplicita

Il nuovo sync deve essere pensato per il promo e per i futuri aggiornamenti della gallery, non solo per l’asset set minimale del vecchio video.

## COMPONENTI REMOTION DA CREARE

Crea in `src/components/` almeno questi componenti riutilizzabili:

* `SceneShell.tsx`
* `AnimatedHeadline.tsx`
* `FeaturePill.tsx`
* `GlassCard.tsx`
* `ScreenCrop.tsx`
* `DiagonalThemeReveal.tsx`
* `ScreenshotStack.tsx`
* `Callout.tsx`
* `PhoneMockup.tsx`
* `DataStream.tsx`
* `ParticlesField.tsx`
* `RepoCard.tsx`
* `BadgeRow.tsx`

### Requisiti componenti

#### `SceneShell`

Wrapper comune con:

* background;
* overlay scuro;
* padding safe area;
* supporto ad headline/sub;
* gestione z-index chiara.

#### `ScreenCrop`

Fondamentale.
Deve:

* partire da screenshot completi;
* applicare crop normalizzato;
* supportare zoom, pan, drift;
* avere ombra e border radius.

#### `DiagonalThemeReveal`

Fondamentale.
Deve:

* ricevere `darkSrc`, `lightSrc`, `progress`, `angleDeg`, `edgeGlowColor`;
* fare reveal diagonale elegante;
* usare maschera/clipPath o strategia equivalente;
* avere bordo luminoso;
* essere riutilizzabile in Scene 02, Scene 03 e Scene 05.

#### `PhoneMockup`

Deve:

* simulare un device elegante;
* ospitare screenshot mobile interni;
* supportare swipe o transition tra schermate;
* avere shadow e riflesso.

#### `Callout`

Badge + linea di collegamento verso un punto dello screenshot.
Deve supportare fade-in, grow line, accent color.

#### `RepoCard`

Card finale per GitHub/CTA.

## DESIGN SYSTEM / STILE

Mantieni uno stile coerente e premium.

Palette consigliata:

* bgDeep: `#050510`
* bgNavy: `#0A0A1A`
* cyan: `#67E8F9`
* violet: `#818CF8`
* green: `#34D399`
* amber: `#F59E0B`
* text: `#F8FAFC`
* muted: `#94A3B8`

Linee guida:

* niente look cheap da reel/social;
* movimenti lenti ma intenzionali;
* glow controllato;
* layering pulito;
* glassmorphism leggero dove utile;
* testi molto leggibili;
* alternanza di momenti forti e momenti di respiro.

## SPECIFICA SCENE DETTAGLIATA

### Scene 01 — Chaos / Fragmentation (150f)

Obiettivo:
mostrare frammentazione e overload.

Visual:

* background AI `chaos_bg_v2.png` oppure fallback `chaos_bg.png`;
* cards sintetiche flottanti tipo:
  * Brokers
  * Crypto
  * FX
  * CSV Reports
  * Spreadsheets
  * Transactions
* leggero parallax;
* glitch o pulse discreto;
* nell’ultima parte le cards collassano in un data stream centrale.

Transizione:

* finale verso Scene 02 con feeling di convergenza/organizzazione dati.

### Scene 02 — Unified Dashboard Reveal (240f)

Obiettivo:
momento wow.

Asset principali da usare:

* dashboard/main
* dashboard/allocation-charts
* brokers/list
* assets/list
* transactions/list
* fx/list

Visual:

1. ingresso dashboard dark leggermente inclinata in prospettiva;
2. comparsa mini-cards/crop laterali da broker/assets/transactions/fx;
3. callout:
   * Net worth
   * Allocation
   * Brokers
   * Assets
   * FX
4. reveal diagonale dark → light sulla dashboard principale;
5. hold pulito finale.

Questa deve essere una delle scene più forti.

### Scene 03 — Analysis Cockpit (300f)

Obiettivo:
far percepire technical analysis e profondità prodotto.

Asset principali:

* assets/detail-chart
* assets/detail-chart-candlestick
* assets/detail-signals
* assets/detail-signals-ema
* assets/detail-signals-rsi
* assets/detail-signals-macd
* assets/detail-measures-active
* assets/detail-classification
* fx/detail-chart
* fx/detail-signals

Visual suggerito:

1. hero chart grande;
2. switch line → candlestick;
3. callout “Technical Analysis”;
4. signals panel / EMA / RSI / MACD;
5. measures;
6. quick cameo FX;
7. quick cameo classification;
8. headline finale ben leggibile.

Evita caos visivo: usa layering elegante, quick cuts misurati e camera movement pulito.

### Scene 04 — Import & Automation (270f)

Obiettivo:
mostrare pipeline forte e distintiva.

Asset:

* brokers/import-wizard-step1
* brokers/import-wizard-step2
* brokers/import-wizard-step4-resolution
* brokers/import-wizard-duplicate
* brokers/import-bulk-staging
* transactions/picker-modal
* transactions/form-modal-fxconversion
* settings/scheduler-config
* settings/scheduler-log
* files/preview-modal-csv

Visual:

* pipeline di cards inclinate o timeline modulare;
* step:
  * Upload
  * Parse
  * Resolve
  * Detect duplicates
  * Stage
  * Sync
* linea dati che collega gli step;
* ritmo visivo pensato per agganciarsi alla musica;
* finale su “clean portfolio data”.

Questa scena deve differenziare LibreFolio dai portfolio tracker basilari.

### Scene 05 — Mobile Continuity (210f)

Obiettivo:
mostrare uso mobile in modo premium.

Asset:

* mobile dashboard
* mobile assets list
* mobile chart
* background opzionale `device_sync_bg.png`

Visual:

1. dashboard desktop blur sullo sfondo;
2. phone mockup entra dal basso / in prospettiva;
3. swipe tra dashboard, list e chart;
4. piccolo reveal dark/light dentro il telefono;
5. badge:
   * Mobile-ready
   * Dark/Light
   * Multi-language

Non mostrare due telefoni statici come visual principale.

### Scene 06 — Open Source / Deployment Modes (240f)

Obiettivo:
comunicare proprietà del dato e libertà di deployment.

Asset:

* `open_network_bg.png` come sfondo principale;
* fallback `opensource_infographic.png` se necessario.

Testi:
Headline:
`Your data. Your rules.`
Sub:
`Open source · Self-hosted · Cloud option coming soon`

Visual:

* nodo centrale “LibreFolio Core”
* moduli / orbiting cards con:
  * Open Source
  * Self-Hosted
  * Cloud option — Coming soon
  * Extendable
  * Privacy-first

Questa scena deve avere un look architetturale/premium, non solo 3 pillole statiche.

### Scene 07 — CTA / Alpha / GitHub (210f)

Obiettivo:
chiusura forte e leggibile.

Asset:

* logo
* eventuale sfondo `cta_particles_bg.png` o `data_stream_bg.png`

Visual:

1. particelle/flussi convergono;
2. logo reveal;
3. headline e sub;
4. repo card GitHub;
5. URL finale;
6. ultimo secondo quasi statico.

Regola:
la CTA finale deve restare leggibile almeno \~1 secondo.

## AUDIO INTEGRAZIONE NEL VIDEO

### Main track

Usa:

* `public/ai/audio_track_main_54s_fade.mp3`

### SFX

Usa almeno:

* `sfx_transition_whoosh_cut_a.mp3` sul passaggio Scene 01 → Scene 02
* una delle varianti `sfx_logo_sting_cut_*` nel reveal finale CTA

### Filosofia audio

* musica principale continua;
* SFX pochi ma utili;
* niente sound design iper complesso se appesantisce troppo;
* priorità a chiarezza e qualità percepita.

## FILE DA TOCCARE / CREARE

Ispeziona il repo e modifica in modo coerente almeno:

* `src/MainVideo.tsx`
* `src/Root.tsx`
* `src/types/i18n.ts`
* `src/i18n/en.ts`
* `src/i18n/it.ts`
* `src/i18n/es.ts`
* `src/i18n/fr.ts`
* `scripts/sync-assets.ts`

Crea o aggiorna:

* `src/config/videoPlan.ts`
* `src/config/galleryManifest.ts`
* `src/config/crops.ts`
* componenti in `src/components/`
* nuove scene se utile rinominandole o aggiungendole

Se preferisci mantenere i nomi attuali delle scene (`Scene01Hook`, ecc.) ma con contenuti completamente nuovi, è accettabile.
Se invece vuoi rinominare a qualcosa di più coerente, fallo mantenendo chiarezza e updating di tutti gli import.

## PIANO DI ESECUZIONE ATTESO

Voglio che tu esegua il lavoro in questo ordine logico:

### Fase 1 — Analisi repo

* ispeziona struttura;
* verifica mapping attuale di scene, i18n e sync;
* individua i punti minimi da rifattorizzare.

### Fase 2 — Refactor config e sync

* crea `videoPlan.ts`, `galleryManifest.ts`, `crops.ts`;
* potenzia `sync-assets.ts`.

### Fase 3 — Componenti

* implementa i componenti base riutilizzabili.

### Fase 4 — Scene

* rifai le scene in ordine:
  1. Scene 02
  2. Scene 03
  3. Scene 04
  4. Scene 05
  5. Scene 06
  6. Scene 07
  7. Scene 01

### Fase 5 — Audio

* integra traccia principale e SFX.

### Fase 6 — i18n

* completa testi e tipi.

### Fase 7 — Build / QA

* esegui `npm run sync`
* esegui almeno `npm run build:en`
* se possibile verifica anche `build:it` o build degli altri locali
* correggi errori TypeScript / path / static assets

## DELIVERABLE FINALI

Quando hai finito, voglio:

1. codice aggiornato;
2. scene rifatte;
3. sync script potenziato;
4. audio integrato;
5. progetto buildabile;
6. riepilogo finale con:
   * file creati/modificati;
   * scelte architetturali fatte;
   * eventuali TODO residui;
   * eventuali asset ancora migliorabili;
   * eventuali note per crop/tuning futuri.

## ACCEPTANCE CRITERIA

Il lavoro è considerato completato se:

* il promo dura circa 54s;
* il video è chiaramente più dinamico e premium del precedente;
* il dark/light reveal è elegante e diagonale;
* i ritagli partono da screenshot completi via config di crop;
* esiste una scena forte su import/automation;
* esiste una scena forte su open source / self-hosted / cloud option coming soon;
* il mobile è reso bene;
* la CTA finale è forte e leggibile;
* il progetto resta multi-lingua e manutenibile.

## STILE DI LAVORO RICHIESTO

* non limitarti a scrivere TODO o pseudo-codice;
* implementa davvero;
* se trovi ambiguità su un crop, scegli una soluzione ragionevole e documentala;
* se una parte è troppo fragile, preferisci una soluzione leggermente più semplice ma robusta;
* mantieni il codice leggibile e coerente;
* lascia commenti utili solo dove servono;
* non over-engineerizzare inutilmente.

Adesso procedi:

1. analizza il repository;
2. applica il refactor;
3. implementa il nuovo promo;
4. prova il build;
5. restituisci un report finale dettagliato.

````

---

## Mini consiglio pratico prima di incollarlo

Io farei così:

1. **commit del vecchio stato**  
2. incolli questo prompt a Gemini CLI  
3. lo lasci lavorare  
4. quando ti restituisce il diff / report, se vuoi me lo giri e lo revisioniamo insieme

---

## Suggerimento extra
Se vuoi aumentare ancora la probabilità che Gemini lavori bene, puoi premettere una riga iniziale del tipo:

```text
Lavora in modo incrementale e conservativo: prima analizza il repo esistente, poi modifica solo ciò che serve, evitando regressioni inutili.
````

***

Se vuoi, come step successivo posso anche prepararti un **secondo prompt più corto, di tipo “fix/review pass”**, da usare **dopo** che Gemini ha fatto la prima implementazione, per rifinire:

* crop,
* tempi,
* easing,
* audio sync,
* leggibilità delle scene.

