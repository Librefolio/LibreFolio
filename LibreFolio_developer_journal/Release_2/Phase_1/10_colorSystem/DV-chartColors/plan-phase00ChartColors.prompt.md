# Piano — Workstream DV, colori dei grafici (GR1–GR5 del giro 2 della designer)

> **Workstream DV del programma colori**, sessione «DV - colori dei grafici». Coordinatore: sessione «UI color analysis»
> (`aec04834-1532-4d86-9e3f-f942e82aca89`).
> Branch `e-alfy-dv-colori-dei-grafici` (rinominato dall'app; prima `e-alfy-congenial-potato`).
> - **Baseline dell'analisi:** `8f1abf89e`.
> - **Base attuale:** `dae4de4fa`, fast-forward del coordinatore; nessun file dell'analisi è cambiato.
> - **Corsia:** porta **6156**, dati **`/tmp/librefolio-r2-dv`**.
> - **Comandi:** `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6156 --data-dir /tmp/librefolio-r2-dv …`.
>
> **Fonti:**
> - giro 2 della designer: [README](../designer-feedback/2026-10-15-round2-palette/README.md) (GR1–GR5, le due tabelle);
>   vale l'originale [`risposta-2-grafici-originale.txt`](../designer-feedback/2026-10-15-round2-palette/risposta-2-grafici-originale.txt);
> - [analisi del coordinatore](../designer-feedback/2026-10-15-round2-palette/analisi.md): §4 coppie vicine (ΔE00),
>   §5 interpretazioni, §6 instradamento;
> - [piano generale](../plan-phase00ColorSystemThemeLab.prompt.md), [piano di T](../T-tokensTheme/plan-phase01TokensTheme.prompt.md)
>   (D-T5: ponte sRGB in B4; W5);
> - piani della 1.3: [Y](../../09_dashboardCharts/plan-phase01DashboardCharts.prompt.md) (FE2, Y8–Y10),
>   [J](../../05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md) (`derived_views.py`, PL1).
>
> **Regola:** i valori della designer si applicano come sono, comprese le coppie vicine del §4, che vanno al giro 3.

## ✅ Autorizzazione e decisioni

- **15/10, analisi consegnata al coordinatore.**
  - Il developer ha approvato questo piano nella sessione DV.
  - Il coordinatore ha sbloccato S1 col via di J sulle tre righe di `derived_views.py`. Testuale: «J ha dato l'OK alle
    tue 3 righe in `derived_views.py`: S1 è sbloccato».
  - Vincolo di J: in `_alloc` (righe 231–243) un cambio minimo, solo l'import e il nome della mappa, perché CP-11 e
    CP-13 di J ne riscriveranno il corpo.
- **15/10, circa 16:25, via del developer, inoltrato alla lettera dal coordinatore:** «Sì, approva DV così».
  - Prima aveva fatto due osservazioni, anche queste testuali.
  - Sul punto 6: «riguardo il punto 6 parliamo dei colori proposti vero? perchè poi l'utente è sempre libero di
    cambiarli».
  - Sul punto 8: «sul punto 8 non sono daccordo alla copia nel frontend, se la andasse a prendere dal backend per
    essere centralizzati».
- **15/10, 17:12, coordinatore:**
  - S1 committato in `8b8571f9a`.
  - Ordine della 1.3, testuale: «prima DV, poi Y9 e Y10». Strada libera su `CorrelationHeatmap`,
    `AllocationHistoryChart`, `AllocationPieChart`, `SemiDonutChart`, `allocationHierarchy` e `allocationRings`.
  - `npm ci` approvato una volta, dal lock del worktree.
  - DV-1 lo gira il coordinatore alla 1.3.
  - Slot pesante: Vitest `core-unit`/`component-unit`, `front check`, E2E e build si chiedono. I pytest mirati e il
    Vitest di un file singolo no.

| # | Decisione | Esito (15/10) |
|---|---|---|
| 1 | Dove vivono i colori di categoria | **A**: tabella TS in `lib/theme/chartCategories.ts`, più il ponte per i ruoli |
| 2 | GR4, ranghi 4–6 (l'ETF ha fino a 6 sottotipi) | stessi passi verso il polo opposto. ΔE00 minimo 3,2–6,0: va al giro 3 |
| 3 | Sequenza senza chiave (storico geografico) | settori 1–14, più «Non classificato» fisso; dal quindicesimo una sfumatura |
| 4 | Colore di un tipo `Unknown` | quello di «Non classificato» |
| 5 | Linee dei broker | i primi 8 tipi: S8 sì |
| 6 | Indicatori con colori per tema | S9 dopo Y4, Y8 e FE5c di X; fino ad allora restano come oggi. Cambiano solo i colori proposti, l'utente li cambia sempre |
| 7 | Segnali già salvati | migrano solo quelli ancora sul vecchio default; i colori scelti a mano restano |
| 8 | Emoji dei settori nel frontend | **niente specchio**: il frontend le legge dall'endpoint dei settori in ogni vista, compresa la torta della dashboard. Via il ripiego scritto a mano di `sectorStore`, store reattivo, collegati i consumatori che non lo caricano |
| 9 | Badge dei tipi | per famiglia; li converte T in W4 con le funzioni di DV. `utils/assetTypes.ts` non si tocca |
| 10 | `POLARITY_TONES` della correlazione | cambiano insieme alla matrice |
| 11 | R-7 della semi-ciambella | la chiude DV |
| 12 | Il ponte `roleColors.ts` | lo costruisce DV; la proposta di API va al coordinatore, che la gira a T |
| DV-2 | Settore senza emoji | un solo ripiego, ❓, accanto alla mappa in `sector.py`, uguale per l'endpoint e per il motore, fissato in un test |

## Stato attuale (verificato sul codice, 15/10)

- **Torta per tipo**
  - Il colore della famiglia va per posizione: `palette[groupIndex % 14]` in
    `components/charts/allocationHierarchy.ts`, con `ALLOCATION_PIE_PALETTE` (`lib/theme/chartPalettes.ts:17`).
  - Sottotipi: `shadeForDepth` (luminosità HSL ±20, regola «B» oltre 3 membri) e l'anello esterno di
    `allocationRings.ts`.
- **Torta per settore:** nessun colore per fetta. Lo dà `option.color = palette` per indice
  (`AllocationPieChart.svelte:468`).
- **Emoji della torta per settore:** il campo `emoji` del backend, `derived_views.SECTOR_EMOJIS`.
- **Storico** (`components/dashboard/AllocationHistoryChart.svelte`):
  - tipo con `familyStyling` (riga 601), sempre per posizione; settore e paese con `palette[i % 14]` (riga 696);
  - ordine per peso medio;
  - oltre la 14ª categoria il colore si ripete in silenzio, con un `debug.warn`.
- **Chiavi**
  - `by_type`: valori di `AssetType`, più `"Liquidity"` (`daily_state.py:716`) e `"Unknown"` (`:1222`).
  - `by_sector`: valori di `FinancialSector`, più `Liquidity` e `Unknown`.
  - `by_geography`: ISO3 più `Unknown`, senza Liquidità.
- **Mappe:** `GEO_CHOROPLETH_SCALE`, letta da `GeographyMap.svelte:300` e `ExposureMaps.svelte:63`.
- **Semi-ciambella:** `SEMI_DONUT_PALETTE`, solo chiara. Avatar con fondo `PALETTE[i]` e iniziale `#fff`. Nessun
  osservatore del tema (R-7).
- **Correlazione:** `CORRELATION_SCALE`; testo delle celle sempre `#f1f5f9` in scuro. La lista delle coppie è sulla
  stessa polarità (`POLARITY_TONES`).
- **Segnali:** `SIGNAL_DEFAULT_PALETTE`, unica per i due temi; il colore si salva come hex in `style.color`
  (localStorage `lf_<utente>_chartSettingsStore` v2) e i salvati lo tengono per sempre.
- **Linee dei broker:** `GROWTH_BROKER_PALETTE`, per indice (`growthChartSeries.brokerColor`).
- **Badge:** `BADGE_CLASS_MAP` in `utils/assetTypes.ts`, per contenuto (`AssetTable`, `AssetCard`,
  `ProviderComparisonModal`). Le altre viste mostrano icone o emoji.
- **Emoji:** `derived_views.SECTOR_EMOJIS` diverge (💊 🏢 🔌 💵). `utilities.SECTOR_EMOJI` e il ripiego di
  `sectorStore.ts` coincidono già con la tabella della designer. La fixture `e2e/dashboard-report.json` ha le emoji
  vecchie congelate («never edit by hand»).
- **Ponte sRGB:** non esiste (D-T5/B4 di T).
- **Lab:** lo scanner tratta come colore di grafico un file di `lib/theme` solo se il nome contiene «chart».

## Architettura proposta

- **A (raccomandata)**
  - `lib/theme/chartCategories.ts`, pura, senza client generato:
    - le tabelle per famiglia di tipo e per settore;
    - le costanti condivise Liquidità e «Non classificato»;
    - le sequenze `CATEGORY_SEQUENCE` (i primi 8 tipi) e `KEYLESS_SEQUENCE` (i settori 1–14);
    - la normalizzazione delle chiavi.
  - `lib/theme/chartShades.ts` per GR4.
  - `lib/theme/roleColors.ts`, il ponte: `getComputedStyle` più normalizzazione via canvas, con lettore iniettabile.
    Lo usano GR5.3 e la card scura di GR4.
- **B**
  - Variabili `--lf-cat-*` per categoria nel Lab (oggi 7 hex in chiaro e 11 in scuro sono identici fra tipi e
    settori).
  - Richiede l'import di T e un ridisegno dei grafici dopo una modifica L1 del Lab.
- **GR4:** miscela in OKLab.
  - Chiaro: verso `#FFFFFF` al 15, 30 e 45 %.
  - Scuro: verso `--lf-surface-card` al 18, 32 e 45 %.
  - `buildAllocationHierarchy` prende `colorOf(primary)`; `buildAllocationRings` prende `shade`; `shadeForDepth` va in
    pensione.
- **GR5**
  - Mappe: cambiano solo i valori.
  - Semi-ciambella: sequenza per tema, osservatore, iniziale dell'avatar scelta per contrasto.
  - Correlazione: ruoli `--lf-danger`, `--lf-surface-panel`, `--lf-info` e testo per contrasto.
  - Storico geografico: sequenza senza chiave più giri di sfumatura.

## Passi

### S0 — Piano nel repo ✅ (15/10/2026)

> **Note implementazione:** analisi del 15/10 trascritta qui, con le decisioni aperte. Le voci DV-n del backlog nascono
> con i passi: DV-1 e DV-2 sono nate in S1.
> **⚠️ Fuori pista:** prima dell'analisi HEAD era `f27e83448`, non la baseline `8f1abf89e`: fermo e rapporto, poi
> fast-forward del coordinatore. Dopo l'analisi HEAD è passato a `dae4de4fa` (altro fast-forward, 59 commit):
> verificato che non tocca i file dell'analisi.

### S1 — Una mappa sola per le emoji dei settori, nel backend ✅ (15/10/2026; `api utilities` verde dopo `npm ci`)

- `backend/app/utils/asset/sector.py`: nasce `SECTOR_EMOJI`, con i valori della designer, cioè quelli di oggi di
  `utilities.py`.
- `backend/app/api/v1/utilities.py`: legge `SECTOR_EMOJI`, la sua copia locale sparisce.
- `backend/app/services/financial_math/portfolio/derived_views.py`: solo l'import e il nome della mappa (vincolo di J).
  Cambiano 4 emoji nelle risposte (Sanità, Immobiliare, Servizi pubblici, Liquidità) e nell'AI Export.
- Test (`test-author`): copertura di `FinancialSector` più Liquidità e «Non classificato»; la vista dell'allocazione e
  `/utilities/sectors` dicono la stessa emoji.

> **Note implementazione:**
> - **Mappa:** `SECTOR_EMOJI` ha chiavi `FinancialSector` (StrEnum, quindi si cerca anche con la stringa) più
>   `"Liquidity"` e `"Unknown"`.
> - **Chiamanti:** `utilities.py` mantiene il ripiego `📊`; `derived_views.py` cambia solo l'import e il nome in
>   `_alloc`. Diff 3 file, +28/−42. ruff e black puliti.
> - **Test di `test-author`:**
>   - `test_sector_normalization.py`: classe `TestSectorEmojiMap`, 4 test;
>   - nuovo `test_financial/test_portfolio_engine/test_allocation_emoji.py`, 7 test, preso dalla cartella di
>     `services roi-fifo-utils` (nessuna voce di catalogo);
>   - `test_api/test_utilities.py`: un aiuto chiamato dai due test dei settori.
> - **Golden:** `backend/test_scripts/fixtures/native_cash_guard/eur_only_golden.json`, 4 righe, Liquidità 💵 → 💰.
>   È la conseguenza voluta; il diff del test mostrava solo quelle.
> - **Verifiche nella corsia 6156:**
>   - `services roi-fifo-utils`: 681 passati, prima 680 più il solo golden rosso;
>   - `utils sector-normalization`: 64 passati;
>   - `services financial-math`: 212 passati, confini del layer compresi;
>   - `git diff --check` pulito.
>
> **⚠️ Fuori pista:**
> - **Rigenerazione del golden:** il comando documentato
>   (`LIBREFOLIO_REGEN_NATIVE_CASH_GUARD=1 … native_cash_guard`) non rigenera, perché la corsia scarta le
>   `LIBREFOLIO_*` non `TEST_` (`cli_base._test_lane_drops`). Golden aggiornato a mano, sulle sole 4 righe del diff del
>   test, poi provato verde byte per byte. Voce DV-1.
> - **`api utilities` non eseguito:** il backend condiviso non parte.
>   - Comando: `… dev.py test --test-port 6156 --data-dir /tmp/librefolio-r2-dv api utilities`; fallito in avvio, prima
>     della raccolta dei test.
>   - Causa, da un avvio diagnostico dello stesso comando server, poi fermato: `dev.py server --test` ricostruisce il
>     frontend, mai costruito in questo worktree, e senza `node_modules` fallisce (`Cannot find package 'typescript'`).
>   - Toccati: solo il DB della corsia e artefatti ignorati (`frontend/src/lib/api/{generated.ts,openapi.json,
>     tool-contracts.openapi.json}`, `frontend/static/fonts/`).
>   - Serve `npm ci`, con l'OK del coordinatore.
> - **Dal `test-author`:** per un settore senza emoji l'endpoint dà 📊 e il motore `None`. Non fissato; voce DV-2.
>
> **Note implementazione (seguito, 15/10 pomeriggio):** S1 committato dal coordinatore in `8b8571f9a`. `npm ci`
> approvato ed eseguito una volta dal lock (exit 0). Poi `… api utilities` nella corsia 6156: 9 passati, porta libera.
>
> **Golden di `native_cash_guard`, regola della 1.3 (coordinatore, 15/10 alle 18:02):**
> - DV-1 la chiude J in CP-4 (`LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD=1`).
> - Sul golden il conflitto è certo: J aggiunge un campo, +116 righe; DV ha cambiato 4 righe a mano.
> - **Chi entra per secondo rigenera**, con la variabile nuova, sulla revisione fusa, senza unire a mano.
>   - Se J entra prima: al merge di base di DV, rigenero io
>     (`LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD=1 … services roi-fifo-utils native_cash_guard`), poi verifico che il
>     diff contro il golden di J sia solo Liquidità 💵 → 💰.
>   - Se entro prima io: rigenera J.
> - **J è entrato per primo** (coordinatore, 15/10 alle 18:14): CP-4 è in `dev_release2` col merge `322d55042`, e la
>   variabile `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD` è nel docstring del test (`_REGEN_ENV`, verificato sul target).
>   DV-1 chiusa nel backlog. Il golden lo rigenero io, al merge di base che fa il coordinatore prima della validazione:
>   vedi S10, prova 0.

### DV-2 e decisione 8, lato backend ✅ (15/10/2026)

- `backend/app/utils/asset/sector.py`: `LIQUIDITY_BUCKET`, `UNKNOWN_BUCKET`, `ALLOCATION_BUCKETS`,
  `SECTOR_EMOJI_FALLBACK = SECTOR_EMOJI[UNKNOWN_BUCKET]` (❓) e `sector_emoji(key)`. È l'unico ripiego, uguale per
  l'endpoint e per il motore (decisione del coordinatore su DV-2).
- `backend/app/api/v1/utilities.py`: `/utilities/sectors` risponde `{items, buckets, fallback_emoji}`. I bucket non
  entrano mai in `items`, quindi mai in una select. Il docstring ora descrive la risposta vera.
- `backend/app/schemas/utilities.py`: `SectorListResponse` ha `buckets` e `fallback_emoji`.
- `backend/app/services/financial_math/portfolio/derived_views.py`: in `_alloc` cambiano solo l'import e il nome
  (`sector_emoji`), come concordato con J.

> **Note implementazione:**
> - **Test (`test-author`):** 9 casi in `test_sector_normalization.py`, 1 in più in `test_allocation_emoji.py`, e
>   `buckets`/`fallback_emoji` nei due test API.
> - **Esiti nella corsia 6156:** `utils sector-normalization` 73, `services roi-fifo-utils` 682,
>   `services financial-math` 212.
> - **`dev.py api sync`:** eseguito, scrive solo file ignorati.
>
> **⚠️ Fuori pista:**
> - **Il backend espone ora le emoji dei bucket.** La decisione 8 toglie lo specchio del frontend, che era l'unica
>   fonte delle emoji di Liquidità e «Non classificato»: l'endpoint dei settori non le restituiva.
> - **Client generato in ritardo:** in un worktree senza `api sync`, `SectorListResponse` era
>   `z.object({items}).partial()` senza `passthrough`, quindi scartava i campi nuovi. Dopo il merge serve `api sync`.
> - **`api utilities` rimandato:** non rieseguito dopo DV-2. L'avvio del server ricostruisce il frontend se un
>   sorgente è più nuovo della build (`cli_base.check_frontend_needs_build`): va nello slot pesante.

### S2 — Fondamenta in `lib/theme` e contratto C1–C4 con il Lab ✅ (15/10/2026)

- `lib/theme/chartCategories.ts` (nuovo)
  - Le tabelle della designer: 11 famiglie, 14 settori, Liquidità e «Non classificato». Una riga per letterale (C2):
    54 righe.
  - Le tabelle non si esportano. Si leggono solo con `categoryColor(kind, key, dark)` (C1), che in debug interroga
    `globalThis.__lfDesignerLab?.categoryColor?.(kind, key, dark)` (C3).
  - `CATEGORY_KEYS`, `CATEGORY_BUCKETS`, `CATEGORY_SEQUENCE` (i primi 8 tipi), `KEYLESS_SEQUENCE` (i 14 settori),
    `sequenceColor` (sequenza, poi giri di sfumature GR4) e `isUnclassifiedCountry`.
- `lib/theme/chartShades.ts` (nuovo)
  - `mixOklab` e `familyShade`, cioè GR4 a miscela in OKLab:
    - chiaro: verso `#FFFFFF` al 15, 30 e 45 %, poi verso `#1C2420`;
    - scuro: verso la card al 18, 32 e 45 %, poi verso `#FFFFFF`.
  - `shadePoles` e `scaleColor` (interpolazione sRGB, come il `visualMap` di ECharts); il contrasto ora è in
    `contrast.ts`.
- `lib/theme/roleColors.ts` (nuovo): il ponte sRGB, con `chartRoles(dark, scope?)` → `{color, readableText}` e
  `setRoleReader`. Forma rivista con T: vedi «Fuori pista».
- `lib/theme/contrast.ts` (nuovo): WCAG dell'app, con `srgbToLinear`, `relativeLuminance`, `over`, `contrastRatio`
  e `readableOn`.
- `lib/theme/themeMode.ts`: `onChartColorsChange(cb)` e `notifyChartColorsChange()` (C4), con l'evento
  `lf:chart-colors-change` su `document`.
- `lib/theme/colorAlpha.ts`: `parseRgb` e `Rgb` esportati, così la lettura dei colori ha una sola casa.
- `lib/stores/reference/sectorStore.ts` (decisione 8)
  - Niente emoji scritte a mano. Legge items, bucket e ripiego dall'endpoint, con chiamata tipizzata.
  - Reattivo con `createSubscriber`: i consumatori runes si aggiornano senza modifiche, compreso il `$derived` di
    `DistributionEditor`.
  - `sectorEmojiVersion()` serve ai grafici, che scrivono le emoji in un'opzione costruita fuori dal contesto reattivo.

> **Note implementazione:**
> - **Calcoli:** i risultati TS coincidono cifra per cifra con lo script Python indipendente dell'analisi:
>   - GR4 dell'ETF, ranghi 1–6, nei due temi;
>   - contrasto bianco su `#6D28D9` 7,10;
>   - scala della correlazione.
> - **Gate:** `theme-roles.mjs --check` pulito.
> - **Compilazione:** il compilatore Svelte non dà avvisi, ed esbuild compila tutti i moduli TS.
>
> **⚠️ Fuori pista:**
> - **Contratto C1–C4 (coordinatore, 15/10, dopo l'approvazione):** proposto da L e approvato dal coordinatore come
>   accordo tecnico fra workstream. Entrato in S2.
> - **`typeof` davanti a `__LF_DESIGNER_LAB__`:** Vitest non ha il `define`, e il nome nudo lancerebbe un errore in ogni
>   test dei grafici. Verificato con esbuild e `minify`, come nella build di release: con `false` spariscono il ramo e
>   la stringa `__lfDesignerLab`.
> - **Revisione di T dell'API del ponte** (approvata dal coordinatore, 15/10 alle 18:04, quattro cambi, fatti):
>   1. **Lettura sull'elemento del grafico.** `chartRoles(dark, scope?)` restituisce `{color(role), readableText(bg)}`,
>      con un solo `getComputedStyle(scope ?? <html>)` per disegno, preso alla prima lettura. Ogni grafico passa il
>      proprio elemento. `dark` serve solo a scegliere il ripiego.
>   2. **Ripieghi uguali a `tokens.css`, non ai valori della designer**, con un gate di parità in
>      `roleColors.test.ts`: `resolveColour(readTokens(), 'var(<ruolo>)', tema)` di
>      `scripts/theme/theme-roles.mjs`. Serve perché `lib/theme/` è esente dal cricchetto, e `--lf-danger` scuro sta
>      per cambiare.
>   3. **Nuovo `lib/theme/contrast.ts`,** la sola implementazione WCAG dell'app: luminanza, rapporto, un colore
>      traslucido composto sulla card. Le altre due restano quella del gate (`theme-roles.mjs`) e quella del Lab, che
>      lo importerà in L-15.
>      - `contrastRatio` e `readableOn` lasciano `chartShades.ts`, che ora prende `srgbToLinear` da `contrast.ts`.
>      - `colorAlpha.ts` guadagna `parseRgba`.
>   4. **Alfa:** il canvas restituisce `rgba()` per i colori traslucidi, e lo lasciamo così.
> - **Bug trovato da una prova, e corretto:** il lettore iniettato non arrivava mai al test in ambiente node, perché
>   l'assenza di `document` usciva prima. Ora il lettore viene chiamato per primo, e `RoleReader` riceve
>   `Element | null`.
> - **T-8b sul ripiego del pericolo scuro** (coordinatore, 15/10, da T): `--lf-danger` scuro diventa
>   `#FF7A86` (D-T25). Messo in `STAND_INS`, poi **tolto** su richiesta del coordinatore alla revisione del
>   checkpoint 2: torna `#f25f5c`.
>   - I 6 `STAND_INS` restano i valori del `tokens.css` della base. T-8 e T-8b cambiano quasi tutti i valori: card,
>     pannello, testo, `on-inverse`, il rosso chiaro e info. Con un solo valore anticipato DV sarebbe rosso adesso su
>     una coppia, e dopo T su 11.
>   - **Regola al punto d'incontro con T:** chi entra per secondo allinea tutti e 6 i ripieghi al `tokens.css` della
>     revisione unita, e il gate di parità lo impone. Se T entra prima, come è probabile, lo fa DV al merge di base
>     che porta T.
>   - `--lf-success` scuro `#5ED69A` (D-T26) non è un `ChartRole`.
>   - ΔE00 fra le categorie scure e il nuovo rosso: il più vicino è a 25.9 (`#E879F9`, Obbligazioni societarie e
>     Indice), nessun problema.
>   - Il nuovo verde `#5ED69A` invece sta a 11.4 da Crowdfunding e Finanziari `#2DD4BF`, contro 16.8 dal verde di
>     guadagno della designer `#4ADE80`. Lo registra il coordinatore per il giro 3; i valori non si toccano.

### S3 — Torta, anelli, gerarchia ✅ (15/10/2026)

- `allocationHierarchy.ts`
  - Opzioni `{resolvePrimary, colorOf, shade}`: il colore di un gruppo è il suo, per chiave (GR1).
  - L'ordine resta per totale.
  - `shadeForDepth` va in pensione, con la sua logica HSL e l'avviso di tavolozza esaurita.
- `allocationRings.ts`: `shade(base, rango)` iniettato.
- `AllocationPieChart.svelte`
  - Tipo: `categoryColor('type', famiglia)` più le sfumature GR4, con la card letta dal ponte.
  - Settore: `categoryColor('sector', chiave)`; l'emoji dallo store, mai dai dati (`AllocationEntry.emoji` rimosso).
  - Niente più `option.color`.
  - Ricostruzione completa su C4 e su una nuova lista di emoji: la scorciatoia «stesso tema» non scatta.

### S4 — Storico ✅ (15/10/2026)

- `AllocationHistoryChart.svelte`
  - Tipo: colori di famiglia dalla gerarchia, nessuna sfumatura (D375).
  - Settore: `categoryColor`.
  - Paesi: `sequenceColor('sector', KEYLESS_SEQUENCE, rango)` sui soli classificati. «Non classificato»
    (`Unknown`/`Other`) resta fisso e non consuma rango.
  - Oltre 98 paesi: `debug.warn`.
  - Ridisegno su C4.
- Via il commento sui 14 posti e la ripetizione silenziosa.

### S5 — Scale delle mappe ✅ (15/10/2026)

- `GEO_CHOROPLETH_SCALE` con le due scale di GR5.1.
- `GeographyMap` ed `ExposureMaps` non cambiano.

### S6 — Semi-ciambella ✅ (15/10/2026)

- `SemiDonutChart.svelte`
  - Il proprietario `i` prende `sequenceColor('type', CATEGORY_SEQUENCE, i)`, la stessa per la fetta e per il disco
    dell'avatar.
  - L'iniziale prende `readableText`.
  - Ridisegno al cambio di tema (chiude R-7) e su C4.
- `SEMI_DONUT_COLORS.avatarInitial` è tolto da `chartTheme.ts`.

> **⚠️ Fuori pista:** il disco dell'avatar usava `PALETTE[i]` sull'indice di tutti i proprietari, mentre la fetta
> prendeva il colore di ECharts sull'indice dei soli dati disegnati: con un proprietario allo 0 % i due non
> coincidevano. Ora la fetta ha il suo `itemStyle.color`.

### S7 — Correlazione ✅ (15/10/2026)

- `CorrelationHeatmap.svelte`
  - Scala `[--lf-danger, --lf-surface-panel, --lf-info]` dal ponte, riletta al cambio di tema e su C4.
  - Testo delle celle: `readableText` del colore della cella (`scaleColor`).
  - `ensureSectorsLoaded()` quando ci sono settori: le emoji dei badge diventano reattive.
- `toneClasses.ts`: `POLARITY_TONES.correlationText/Tag` sui ruoli `danger` e `info` (decisione 10).
- `CORRELATION_COLORS.cellValue` è tolto da `chartTheme.ts`.
- `CorrelationPairsList.svelte`: cambia solo il commento che citava i vecchi esadecimali.

### S8 — Linee dei broker ✅ (15/10/2026)

- `GROWTH_BROKER_PALETTE` sono le 8 coppie di `CATEGORY_SEQUENCE`, lette con `categoryColor`.
- `growthChartSeries.ts` (Y) non cambia.

### S9 — Indicatori per tema ⏸️

Dopo Y4, Y8 e FE5c di X (decisione 6). Migrano solo i default salvati (decisione 7).

### S10 — Verifiche e gallery ✅ (15/10/2026; in attesa dell'approvazione dell'aspetto dal developer, D-T21)

- **Test:** due `test-author` in parallelo, su file distinti. Entrambi hanno finito il 15/10; i conteggi sono i loro,
  ciascun file lanciato da solo. La mia riprova sull'insieme fuso è più sotto.
  - **TA-1** (`lib/theme`, store e aiuti): 12 file, 290 test.
    - Nuovi: `chartCategories` 85, `chartShades` 25, `contrast` 14, `roleColors` 24, `roleColors.dom` 11,
      `sectorStore` 8.
    - Modificati: `themeMode` 24, `chartTheme` 5, `colorAlpha` 24, `palettes.test` 14, `utils/__tests__/colors` 34.
    - Riparato: `L4Shock` 22, prima 3 rossi.
    - Aiuti in `src/__tests__/`: il nuovo `colorDistance.ts`, cioè CIEDE2000 provato sui dati di riferimento di
      Sharma; `palettes.ts` riconvertito alle tabelle di categoria.
  - **TA-2** (grafici): 6 file, 139 test.
    - Modificati: `allocationHierarchy` 23, `allocationRings` 41, `AllocationPieChart` 23, `AllocationHistoryChart` 38.
    - Nuovi: `SemiDonutChart` 8, `CorrelationHeatmap` 6.
    - E2E `e2e/portfolio/dashboard.spec.ts`: scritto, da lanciare nello slot pesante.
- **Catalogo:** solo voci aggiunte in `scripts/test_runner/_frontend_utility.py`.
  - `core-unit` (`front_utility_unit`):
    - righe 126–130: `chartCategories`, `chartShades`, `contrast`, `roleColors`, `roleColors.dom`;
    - riga 144: `sectorStore`.
  - `component-unit` (`front_component_unit`): riga 281 `SemiDonutChart`, riga 288 `CorrelationHeatmap`.

> **⚠️ Fuori pista (dai rapporti dei `test-author`):**
> - **Difetto latente, corretto:** `getSectorEmoji` cercava le chiavi in un oggetto semplice. `'constructor'` restituiva
>   una funzione, e `'__proto__'` un oggetto. Ora le emoji stanno in una `Map`, e TA-1 aggiunge il test di regressione.
> - **DV-6:** un'etichetta di settore comincia con uno spazio finché l'elenco non arriva, in `stressBucketLabel.ts`
>   (zona di Y) e in `categoryLabels.svelte.ts` (PAC). Va ai proprietari.
> - **Descrizione stantia, corretta:** quella di `allocation-unit` in `_frontend_portfolio.py:460` parlava ancora delle
>   4 tavolozze da 14 posti e delle sfumature HSL. L'ho cambiata su incarico del coordinatore (15/10), solo la stringa
>   `desc=`: il resto del file è uguale a HEAD, verificato.
>   - Su quel file ruff dà 28 rilievi (27 E701, 1 PLC0415), e black lo riformatterebbe in 12 blocchi.
>   - Sono preesistenti: su HEAD i rilievi sono identici e i blocchi gli stessi. Non li ho toccati.
> - **Commento di `chartShades.ts`:** il polo lontano chiaro, `#1C2420`, ora è detto «testo primario del giro 2, dalla
>   tabella dei ruoli della designer». È un letterale di proposito, mentre `tokens.css` ha ancora `#292d27` del
>   giro 1.
> - **Ordine dentro i file:** il primo test dei settori della torta e i due della heatmap devono girare prima di ogni
>   altro caricamento dei settori nel loro file. Vitest qui non mescola l'ordine (nessun `sequence.shuffle`), e ogni
>   test verifica la sua precondizione con un messaggio.
- **Catalogo (coordinatore, 15/10 alle 18:00):** registrazione approvata in `core-unit` e `component-unit`, con sole
  voci aggiunte e nessun riordino; `_frontend_utility.py` lo toccano anche le sessioni della 1.3.
- **Slot pesante, in coda:** dopo la ripresa di Y2 e dopo T-8b. Ordine previsto delle prove, tutte con
  `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …` e, per i test, con la corsia
  `--test-port 6156 --data-dir /tmp/librefolio-r2-dv`:

| # | Prova | Perché, in quell'ordine |
|---|---|---|
| 0 | Dopo il merge di base del coordinatore: `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD=1 … test … services roi-fifo-utils native_cash_guard`, poi lo stesso senza variabile, poi `services roi-fifo-utils` e `services financial-math` interi | Il golden si rigenera sulla revisione fusa, senza unire a mano. Il diff contro quello di J (`MERGE_HEAD`) dev'essere solo Liquidità 💵 → 💰 su 4 righe. Pytest mirato, non pesante. Se il merge porta T, nello stesso passo allineo i 6 `STAND_INS` al `tokens.css` unito (regola del punto d'incontro) |
| 0b | DV-6, dopo la prova 0 e prima dello slot pesante (OK della 1.3, 15/10): le due righe in file di altri, `components/risk/stressBucketLabel.ts` (Y) e `features/tools/pac-allocator/planner/categoryLabels.svelte.ts` (PAC, J). Il test lo scrive `test-author`; poi un file Vitest per volta | Così le prove 1–7 le coprono. Nell'handoff vanno dichiarate come righe in file di altri |
| 1 | `front check` | Tipi su tutti i consumatori: export tolti, chiamata tipizzata dello store, `AllocationEntry` |
| 2 | `test … front-utility core-unit` | Gate dei colori e del Lab, `lib/theme`, store dei settori, segnali |
| 3 | `test … front-utility component-unit` | Componenti montati: semi-ciambella, heatmap |
| 4 | `test … front-portfolio allocation-unit`, poi `front-portfolio risk-levels-component` | Gerarchia, anelli, torta, storico, guardia delle tavolozze, `colors`; poi `L4Shock` |
| 5 | `test … api utilities` | Endpoint con `buckets` e `fallback_emoji`. L'avvio del server ricostruisce il frontend |
| 6 | `test … front-portfolio dashboard`, `front-portfolio risk`, `front-user broker-sharing` | E2E: torta e storico (GR1), correlazione e coppie, semi-ciambella |
| 7 | Gallery filtrata, **sulla revisione fusa dopo l'ingresso di T**, con il ramo allineato dal coordinatore | `scripts/visual_review/gallery_snapshot.sh dv-cand --checkout <worktree> --port 6156 --data-dir /tmp/librefolio-r2-dv -- --workers 6 -f "<Dashboard\|Brokers\|Assets\|Tools\|Risk Analysis>"`, poi `gallery_tool diff` contro un riferimento dello stesso giorno, con `--common-only`, maschere e stabilità |

**Prova 0, sulla revisione fusa `0182d890d`** (genitori `c5bca76ae` e `10d5ccd2d`, 15/10 alle 19:04): ✅
- Il golden si era già unito da solo: il golden di J con le 4 righe 💰, nessun 💵, JSON valido, 14 513 righe.
- `LIBREFOLIO_TEST_REGEN_NATIVE_CASH_GUARD=1 … test --test-port 6156 --data-dir /tmp/librefolio-r2-dv services
  roi-fifo-utils native_cash_guard`: il test salta per rigenerare, e il file viene riscritto (mtime 19:04:47).
  **Il diff contro HEAD è vuoto**, cioè byte identico.
- Lo stesso senza la variabile: 1 passato.
- Categorie intere: `services roi-fifo-utils` 687 e `services financial-math` 265, entrambe più alte per i test di
  CP-4; in più `utils sector-normalization` 73.
- `dev.py api sync`: rc 0, nessun file tracciato cambiato. Il client generato ha `buckets` e `fallback_emoji`.
- T non è nel target: i `STAND_INS` restano quelli della base.

**Prova 0b, DV-6** (15/10): ✅
- `stressBucketLabel.ts` (Y): ramo del settore con ``emoji ? `${emoji} ${name}` : name``; il doc di
  `StressBucketVocabulary.sectorEmoji` dice che è `''` finché l'elenco non arriva.
- `categoryLabels.svelte.ts` (PAC, J): lo stesso in `exposureCategoryLabel`.
- Test di TA-1:
  - nuovi `stressBucketLabel.test.ts` 9 e `categoryLabels.test.ts` 9, nessuno dei due aveva un test diretto;
  - il mirror `expectedLabel` di `L4Shock.test.ts` allineato, 22;
  - registrazione in `core-unit`, solo voci aggiunte in `_frontend_utility.py`: riga 93 (`stressBucketLabel`) e riga
    157 (`categoryLabels`).
- Riprova mia, un file per volta: i tre file sopra, più `riskAnalysisHelpers.test.ts` 96, tutti verdi. Prettier
  pulito, `git diff --check` pulito, porta 6156 libera.
- Osservazione di TA-1 per J, nessun cambio: `exposureCategoryLabel` ignora maiuscole e minuscole per tipi e paesi,
  ma non per i settori. Le chiavi arrivano dagli enum del backend.

**Slot pesante, prove 1–7, sulla revisione `d0065fb8e`** (genitori `fb59c7bec` e `e70be943b`; via del coordinatore il
15/10 alle 19:48). Una prova alla volta, nella corsia 6156:
- `api sync` per primo, perché B porta le API del backup: rc 0, nessun file tracciato cambiato.
- **1 · `front check`:** prima 1 errore, poi **0 errori e 0 avvisi**.
  > **⚠️ Fuori pista:** l'errore era di tipo, in un test, `CorrelationHeatmap.test.ts:163`: un `new Map([...])` dedotto
  > troppo stretto per `ReadonlyMap<number, Readonly<Record<string, number>> | null>`. TA-2 ha aggiunto l'argomento di
  > tipo al costruttore, nient'altro. Vitest non controlla i tipi, quindi il file passava già: ora 6/6.
- **2 · `front-utility core-unit`:** 163 file, 5243 test verdi.
- **3 · `front-utility component-unit`:** 134 file, 3524 test verdi.
- **4 · `front-portfolio allocation-unit`:** 6 file, 173 test; `front-portfolio risk-levels-component`: 9 file, 273.
- **5 · `api utilities`:** 9 passati, dopo DV-2 sulla revisione fusa.
- **6 · E2E:** `front-portfolio dashboard` 27 passati, compreso il nuovo «Allocation by type: each family in a colour
  of its own, the same in the pie and in the history (GR1)»; `front-portfolio risk` 38; `front-user broker-sharing`
  17; `front-utility utilities` 16, aggiunto perché prova l'endpoint dei settori dal frontend. Nessun test saltato
  né instabile.
- **7 · Galleria filtrata** per il contact sheet del developer (D-T21), nei due temi, desktop e telefono, quattro
  lingue. Sono 9 test:
  - `main dashboard`, `dashboard allocation charts`, `dashboard growth P&L submodes`;
  - `broker sharing modal` (semi-ciambella);
  - `Asset detail classification` (torta dei settori e mappa);
  - `risk lab correlation`, `dashboard risk diversification`, `risk what-if simulation`;
  - `PAC allocator result` (mappe di esposizione ed etichette di settore).

  Comando: `/tmp/libreFolio_dv_heavy_7.sh`, cioè `gallery_snapshot.sh dv-charts-d0065fb8e`, poi `live_price_check`
  e `gallery_tool browse --langs it,en`. Oggi non c'è un riferimento del target con lo stesso filtro: il diff si fa
  solo se il coordinatore ne cattura uno.
  - **Primo giro, 20:29–20:38, a 6 worker:** 6 passati e 12 rossi.
    > **⚠️ Fuori pista: era saturazione della macchina, non un difetto. Triage con `test-triage`.**
    > - **Carico:** `uptime` alle 20:39 dava 57 / 89 / 87 su 10 core. Nella finestra giravano anche le corsie della
    >   1.3, porte 6181–6189: E `api system`, Y frontend a 2 worker, H, J, X, Z.
    > - **Sintomi:** sono quelli che il README di `visual_review` registra per la saturazione.
    >   - I 6 desktop della prima ondata: login fermo su `auth-loading at /` per 30 s.
    >   - Rischio, desktop: «header still sliding».
    >   - Mobile: timeout di `waitForLoadState`, dei click (20 s, sul main thread) e dello screenshot (60 s). Uno scatto
    >     che non è di DV ha impiegato 24.9 s.
    >   - Nessuna asserzione sui colori.
    > - **Rilancio dei soli 12 rossi**, a `--workers 2 --no-populate`, in due snapshot, `-retry-desktop` e
    >   `-retry-mobile`, dentro la finestra tranquilla chiesta dal coordinatore alla 1.3.
    >   - Risultato: 8/8 e 4/4.
    >   - `uptime`: 51.70 / 78.54 / 83.33 prima, 39.81 / 62.62 / 74.84 dopo il desktop, 35.06 / 47.99 / 65.81 dopo il
    >     mobile.
    >   - **Verdetto: ambiente.** Il dashboard mobile non si blocca più.
  - `live_price_check` è pulito su tutti e tre gli snapshot.
  - **Contact sheet unico:** `<visual_review>/snapshots/dv-charts-d0065fb8e-sheet/index.html`, con le pagine desktop e
    telefono in italiano e in inglese, chiaro e scuro affiancati.
    - È unito dal primo giro e dai due rilanci: lo scatto di un rilancio sostituisce quello del primo giro con lo
      stesso percorso, e `origin.json` dice da dove viene ogni immagine.
    - 352 PNG, cioè 22 scatti × 2 viewport × 4 lingue × 2 temi, nessuno senza uno dei due temi.
  - **Controllo a occhio:**
    - GR1: torta e storico per tipo con gli stessi colori di famiglia;
    - le sfumature GR4 al buio;
    - la correlazione rosso → pannello → blu, con il testo delle celle leggibile;
    - la semi-ciambella;
    - le emoji dei settori dal backend.
  - **Per il giro 3, valori non toccati:** nello storico geografico il primo paese prende il primo colore senza
    chiave, Industriali, un ardesia. Le aree traslucide stanno a ΔE00 12.8 (chiaro) e 15.2 (scuro) da «Non
    classificato»; le basi a 31.9 e 29.4.
- **Il target si è mosso** a `a744e5f89`, con J CP-4c e A6b. Merge simulato con `git merge-tree`: pulito, nessun
  conflitto. In comune ci sono solo il backlog e `_frontend_utility.py`, in blocchi separati.
- **Delta da committare:** `CorrelationHeatmap.test.ts`, una riga (l'argomento di tipo), e il piano.

**Controllo leggero sul fuso `31d2b15d8`** (genitori `4321da3e6` e `ab2ddf86e`; via del coordinatore il 15/10 alle
21:08, dopo la galleria di G). Uno alla volta, nella corsia 6156, con la 1.3 ripartita (load all'inizio 60 / 71 / 67):
tutto verde.
- `api sync`: rc 0, nessun file tracciato cambiato.
- `front check`: 0 errori, 0 avvisi.
- `front-portfolio allocation-unit`: 173 test.
- I file di `lib/theme/`, uno per volta: `chartCategories` 85, `chartShades` 25, `contrast` 14, `roleColors` 24,
  `roleColors.dom` 11, `themeMode` 24, `chartTheme` 5, `colorAlpha` 24. Poi `sectorStore` 9.
- `api utilities`: 9. `utils sector-normalization`: 73.
- Script `/tmp/libreFolio_dv_light_final.sh`, riepilogo in `/tmp/libreFolio_dv_light_final.summary`. Porta 6156
  libera alla fine. L'ingresso aspetta l'OK del developer sull'aspetto (D-T21).

**Riprova sull'insieme, prima del checkpoint (15/10):** un file per volta, senza corsia né server.
- Comando: `/tmp/libreFolio_dv_vitest_batch.sh`, cioè `node_modules/.bin/vitest run <file>` con
  `PYTHON=$(PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv --py)`. Riepilogo in
  `/tmp/libreFolio_dv_vitest_batch.summary`, un log per file.
- **39 file, 1295 test: 1294 verdi, 1 rosso atteso.** Il rosso è la parità di `--lf-danger` scuro:
  `expected '#ff7a86' to be '#f25f5c'`.
  - **I 18 file dei `test-author`:** 430 test.
  - **13 test non toccati** che usano i moduli cambiati: 703 verdi. Sono `AssetModal.providerLifecycle` 41,
    `AssetModal` 32, `BrokerSharingPanel` 58, `lotChartShared` 25, `lineChartHelpers` 42, `chartCoreHelpers` 265,
    `geographyMapHelpers` 25, `AllocationPanel` 3, `AssetSetComparisonLevels` 57, `AssetSetCorrelationSection` 16,
    `DataEditor` 88, `aiExportUi` 6 e `formatPercent` 45.
  - **8 gate:** 162 verdi. Sono `themeModeReads` 24, `themeRoles` 36, `themeComponentTokens` 18, `themeTokens` 14,
    `designerLabImports` 27, `htmlSink` 7, `htmlInterpolation` 26 e `themeColorMeta` 10.
- **Statici:**
  - Prettier pulito su tutti i file toccati;
  - `node scripts/theme/theme-roles.mjs --check`: pulito;
  - `ruff check` e `black --check` sui 7 file del backend: puliti;
  - `git diff --check`: pulito;
  - porta 6156 libera.
- **Non lanciati, perché pesanti:** le prove 1–7, comprese `api utilities` dopo DV-2 e la gallery.

**Il target si è mosso** a `be7de95b6`, con E2 e le decisioni 48–50.
- E2 aggiunge voci in `_frontend_utility.py` a 12–20 righe dalle mie: il merge dovrebbe essere automatico.
- La decisione 49 (D-Y11, la liquidità negativa sotto lo zero) è lavoro di Y10 sullo storico, dopo DV. La Liquidità
  tiene il suo colore GR3 sopra e sotto lo zero, e DV non deve cambiare nulla.
- **T-8b non è ancora nel target.**

**Checkpoint 2 (15/10):** consegnato al coordinatore e da lui rivisto: 48 path corrispondenti, `diff --check` pulito,
backlog solo nella sezione DV. Ha chiesto due ritocchi, fatti:
- il ripiego scuro di `--lf-danger` torna `#f25f5c`;
- la `desc` di `allocation-unit` è nuova.

Prove leggere dopo i ritocchi:
- `roleColors.test.ts` 24/24 e `roleColors.dom.test.ts` 11/11, quindi l'insieme ora è **verde, 1295 su 1295**;
- Prettier su `roleColors.ts`: pulito;
- ruff e black su `_frontend_portfolio.py`: rilievi solo preesistenti, vedi «Fuori pista»;
- `git diff --check`: pulito.

**49 path**, nessuno in stage. Stato FROZEN.

### TD-1 — Barre «Esposizioni — ideale vs reale» del PAC, con TD-1b ✅ (16/10/2026, validato su `d3ba25ae9`)

**Origine.** Dalla review unica del developer sull'anteprima `ec1ddba96` (15/10, 22:08–22:20), il coordinatore ha
assegnato a DV un compito tecnico: il PAC usava ancora `PAC_EXPOSURE_BAR_COLORS`, cioè il verde vecchio `#1a4031` e, in
scuro, il fluo `#00d681`. Rientra in GR1, il colore di un tipo riconoscibile «in qualsiasi vista» (D-T22: «Sì, approva
DV così»). Il via è arrivato dopo l'ingresso unico di T e DV (`dev_release2` = `a0915bef9`, 15/10 alle 22:51).

**Decisioni del coordinatore** (15/10: alle 22:27 sull'analisi in sola lettura, e dopo la rimisura su T-8b):
1. **«Ideale» nel ruolo neutro `--lf-text-secondary`,** con un test che lo tiene a ΔE00 ≥ 10 da ogni categoria.
   - Rimisurato sui valori di T-8b, con il resolver di T.
     - **Chiaro:** `#4a5550`, 7.48:1 sulla card, categoria più vicina Industriali a 13.40.
     - **Scuro:** `#9ba8a2`, 7.08:1, ma a **9.05 da «Altro»** (`#7F8C87`, che è sia il tipo `OTHER` sia il settore
       `Other`).
   - Su 92 ruoli, solo `--lf-text-primary` e `--lf-surface-inverse` passano ovunque: troppo forti per una barra.
   - **Scelta (a):** una sola eccezione registrata, «Altro» in scuro a 9.0. Il test fallisce se quella distanza scende
     ancora, o se un'altra categoria va sotto 10.
   - L'eccezione è annotata anche nel pacchetto del giro 3, `package/grafici-giro3-2026-10-15/`, al punto 2.7, sia
     nel `.md` sia nell'`.html`. Lo zip non è ricostruito.
2. **`ChartRole`:** il ruolo lo aggiunge DV, col ripiego uguale al `tokens.css` della base. B4 di T partirà da lì.
3. **Sottotipi:** le sfumature GR4 della famiglia, come nell'anello della torta.
   - Il membro generico prende il colore base.
   - Gli altri prendono `familyShade` per rango di peso ideale decrescente, a pari peso per id; mai il colore base.
4. **Legenda:** «ideale» col quadratino neutro pieno, «reale» bordato nel colore del testo.
5. **Galleria (a):** lo scatto `tools/pac-result-exposures` lo scrive G (G-16), nel suo perimetro. L'evidenza di TD-1
   sarà quello scatto in una galleria filtrata, più i test di componente.
- Si fanno anche il modulo puro `exposureBarColours.ts` e la rimozione di `PAC_EXPOSURE_BAR_COLORS`. I file del PAC
  sono di J, che ora non ci lavora: si dichiarano all'ingresso.

**Passi:**
- [x] `api sync` sulla base `a0915bef9`: rc 0, nessun file tracciato cambiato.
- [x] Rimisura del neutro su T-8b, ed eccezione decisa.
- [x] `roleColors.ts`: `--lf-text-secondary` in `ChartRole`, col ripiego uguale a `tokens.css` (`#4a5550` / `#9ba8a2`).
  Il commento del modulo cita TD-1. `roleColors.test.ts` 26/26: la parità copre il ruolo nuovo, e il controllo «ogni
  ruolo è letto da un grafico» è soddisfatto.
- [x] Nuovo `exposureBarColours.ts`, con `idealColour(roles)` e `actualColours(rows, dimension, dark, poles)`, e il
  cablaggio di `ExposureBars.svelte`:
  - colori della serie «reale» per riga;
  - legenda;
  - dots del tooltip;
  - segnale C4;
  - `chartRoles(dark, container)`.

  Il compilatore Svelte dà 0 avvisi, e Prettier è pulito.
- [x] `exposureTooltip.ts`, solo il commento di `dots`. `PAC_EXPOSURE_BAR_COLORS` tolto da `chartTheme.ts`: nessun altro
  riferimento in `src`, `e2e` o `mkdocs_src`. `theme-roles --check` pulito.
- [x] **Richiesta di L (L-16), dentro TD-1:** `lookupKey` esportata da `chartCategories.ts` e documentata nel commento
  del modulo. Il controllo C1 (`DOCUMENTED_EXPORTS`) diventa rosso finché `test-author` non lo aggiorna.
- [x] Test, scritti da `test-author` (15/10):
  - **TA-1:**
    - `exposureBarColours.test.ts` (nuovo, node): 24. Ogni regola nei due temi; il controllo ΔE00 su 27 colori di
      categoria per tema; l'unica eccezione, «Altro» in scuro a 9.0 (misurato 9.047; il secondo più vicino in scuro è
      Holding/Industriali a 12.997, in chiaro 13.404). Ogni via di fallimento è dimostrata su grigi sintetici.
    - `chartCategories.test.ts`: 88, con `DOCUMENTED_EXPORTS` + `lookupKey`, il comportamento di `lookupKey`, e
      `growthBrokerColor` che segue una modifica del Lab.
    - `chartTheme.test.ts`: 6. I controlli positivi spostati su tabelle che esistono; la funzione si salta.
    - Catalogo: riga 158 (`core-unit`, `exposureBarColours`) e riga 357 (`component-unit`, `ExposureBars`), solo
      aggiunte.
  - **TA-2:**
    - `ExposureBars.test.ts` (nuovo, jsdom, ECharts registrato): 12. Due fixture nei due temi, con ruoli inventati sul
      contenitore del grafico; serie, legenda, dots del tooltip, cambio di tema, C4; nessun verde vecchio.
    - `GrowthChart.test.ts`: 166, con un caso C4 in coda (solo aggiunte, 75 righe). Fallirebbe senza il `true` di
      `renderChart(true)`.
- [x] Prove leggere: 18 file, uno per volta, 629 test verdi.
  - I nuovi e gli aggiornati, sopra.
  - Invariati: `roleColors` 26, `roleColors.dom` 11, `GrowthChart.tooltip` 6, `ResultCell` 7, `StateNotice` 6, `model`
    11, `text` 95, `categoryLabels` 9, i gate `themeRoles` 47, `themeTokens` 16, `themeComponentTokens` 18,
    `designerLabImports` 27, e `scanColors` 54.
  - Statici: compilatore Svelte 0 avvisi su `ExposureBars` e `GrowthChart`; Prettier; `theme-roles --check`;
    `git diff --check`; ruff e black sul catalogo, uguali a HEAD.
- [x] **Checkpoint e base merge** (coordinatore): checkpoint `ada4742b7` con TD-1 + TD-1b (16 path); poi le base merge
  `cec865899`, `dad643109` e `d3ba25ae9`, sopra il target `c7dea8be6` (J CP-15/16, X CP11a, Z3, il lotto di doc di W,
  E4a). Tutte uguali alla simulazione. `tokens.css` non è cambiato, quindi ripieghi e controllo ΔE restano validi.
  `api sync` rifatto su ogni base: rc 0, nessun file tracciato cambiato.
- [x] **Prove pesanti su `d3ba25ae9`** (16/10, via del coordinatore alle 01:48; load 35 / 31 / 35), una alla volta
  nella 6156: tutto verde.
  - `front check`: 0 errori, 0 avvisi.
  - `front-utility core-unit`: 171 file, 5900 test.
  - `front-utility component-unit`: 145 file, 3806 test.
  - E2E `front-utility pac-allocator-real`: 1; E2E `front-portfolio dashboard`: 27.
  - Script `/tmp/libreFolio_dv_td1_heavy.sh`, riepilogo in `/tmp/libreFolio_dv_td1_heavy.summary`. Porta 6156 libera,
    nessun file tracciato cambiato.
- [x] **Galleria filtrata prima dell'ingresso: saltata** (coordinatore, 15/10 alle 23:37). Y3 aspetta l'ingresso di DV
  per spostare `GrowthChart`. Gli scatti PAC (`tools/pac-result-exposures`, G-16) e P&L li copre la galleria di fine
  notte, confrontata con G-13.

**Dove guardarlo, per il developer:**
- **Strumenti › PAC › risultato › «Esposizioni»:** la barra «reale» è nel colore della categoria, con i sottotipi in
  sfumatura della famiglia; quella «ideale» è grigia (`--lf-text-secondary`). In chiaro e in scuro.
- **Dashboard › Crescita del portafoglio › P&L:** le linee dei broker hanno i colori dei primi 8 tipi. Nel Designer
  Lab, una modifica a un colore di categoria le ridisegna subito.

> **⚠️ Fuori pista:**
> - **Il ruolo si legge con una chiamata letterale.** Il controllo di TA-1 sui ruoli cerca
>   `.color('--lf-…')` nei sorgenti, e una costante `IDEAL_ROLE` lo nascondeva. Ora è `idealColour(roles)`, che contiene
>   la chiamata letterale e serve anche al test ΔE.
> - **TD-1b, dopo TD-1** (richiesta di L, 15/10): `GROWTH_BROKER_PALETTE` è calcolata all'import, e `GrowthChart` non
>   ascolta C4. L'elenco dei file è andato al coordinatore per la 1.3:
>   - `chartPalettes.ts`;
>   - `growthChartSeries.ts` (Y), circa 4 righe;
>   - `GrowthChart.svelte` (Y), circa 3 righe;
>   - il commento di `chartTheme.ts`;
>   - i test `chartCategories`, `chartTheme` e `GrowthChart` (Y).
>
>   Si tocca solo con l'OK.
> - **TD-1b unito a TD-1** (coordinatore, 15/10 alle 23:10, con l'OK della 1.3 sui file di Y): un lotto, un checkpoint
>   e una validazione, così entra prima di Y3 (FE6b). Dopo le 01:30 circa Y3 sposta `GrowthChart.svelte`,
>   `growthChartSeries.ts` e il test in un'altra cartella. Fatto:
>   - `chartPalettes.ts`: al posto di `GROWTH_BROKER_PALETTE`, calcolata all'import, c'è `growthBrokerColor(index,
>     dark)`, che chiama `categoryColor` a ogni disegno;
>   - `growthChartSeries.ts` (Y): `brokerColor` delega a `growthBrokerColor`;
>   - `GrowthChart.svelte` (Y): `onChartColorsChange(() => renderChart(true))`. Il `true` serve:
>     `renderChart()` prende la via dei soli dati quando modo, tema, mascheramento e serie non cambiano, cioè la
>     scorciatoia che C4 esclude;
>   - `chartTheme.ts`: solo il commento.
>
>   Prove: compilatore Svelte 0 avvisi; `GrowthChart.test.ts` 165 e `GrowthChart.tooltip.test.ts` 6, come prima;
>   Prettier e `theme-roles --check` puliti. I test di TD-1b li scrivono TA-1 (`chartCategories`, `chartTheme`) e TA-2
>   (un caso C4 in `GrowthChart.test.ts`).

### W5-PAC — Ruoli di colore nel PAC ✅ (16/10/2026, validato su `35a55cf39`)

**Mandato.** Proposta del coordinatore, alle 02:16, approvata alle 02:20, con l'OK di J (stanotte lavora solo sul
backend). Rientra nel mandato del developer delle 22:20: «mergia il lavoro fatto, correggi gli aspetti tecnici e
avanza sulle altre wave».

**Perimetro: 39 file di `features/tools/pac-allocator/`,** più `frontend/src/themeRoles.baseline.tsv` (`--update` sul
ramo di DV; i conflitti con T li risolve il coordinatore con `--resolve`) e il piano. Si migrano i neutri, il marchio
e gli stati, con la tabella della skill `theme-roles`. Con l'OK del coordinatore (02:36), anche 2 righe di
`frontend/src/app.css`, che è di T: il selettore morto `html.dark .bg-white\/95`, chiesto dal gate C4.

**Esclusi:**
- `ExposureMaps.svelte` ed `ExposureBars.svelte`, perché Y9 tocca i loro `echarts.init`.
- Le costanti `INPUT` e `TITLE_INPUT` di `ui.ts`, e ogni elemento che le usa.
  - `INPUT` va come `className` a `ExactDecimalInput`, ancora legacy, in `TargetInputCell`, `AssetsStep`,
    `AssetEditor`, `BrokerEditor` (×7), `RoutingStep` (×2), `FxStep` e `ManualAccountDialog` (×2). Va anche su
    `<input>` semplici, in `AssetEditor` (182, 193) e in `BrokerEditor` (397).
  - `TITLE_INPUT` sta su `<input>` semplici (`BrokerEditor`:149, `LiquidityStep`:207).
  - Restano col lotto di T sull'input: due stili di campo diversi fino ad allora sarebbero peggio (coordinatore).
- Le 6 fasi colorate di `BackendTimingBar`: categorie, in attesa dei punti 2.1 e 2.5. Ogni segmento ha solo quella
  classe, quindi non resta un elemento misto.
- **La traccia della barra di `TargetsStep`** (`bg-gray-100 dark:bg-slate-700`). La barra «sconosciuta» che ci corre
  sopra diventa `bg-lf-neutral` nel lotto di T delle 03:25. Misure sui ruoli di T-8b:

  | Traccia | Sulla card | Contro `bg-lf-neutral` | Contro gli stati |
  |---|---|---|---|
  | `bg-lf-neutral` o `border-lf-subtle` | 1.30 / 1.21 | ΔE00 0, la barra sparisce | — |
  | `bg-lf-panel` o `bg-lf-hover` | 1.15 / 1.10 | ΔE00 3.4 / 2.5, quasi invisibile | ≥ 4.5:1 |
  | **palette, invariata** | 1.06 / 1.69 | **ΔE00 6.9 / 15.3** (1.22:1 / 1.39:1) | — |

  Nessun ruolo distingue la traccia dalla barra «sconosciuta», quindi la traccia resta in palette, come dice il
  commento di T in `toneClasses.ts`.

**Regole:**
- Si converte per significato e per gradino, non per famiglia di colore.
- Un elemento migra intero.
- Niente `dark:` sui ruoli.
- Ogni `border` nomina il suo ruolo.
- La radice del componente prende `text-lf-primary`.
- Convenzioni già usate da T:
  - un bottone secondario è `bg-lf-card` + `border-lf-input` + `hover:bg-lf-hover`;
  - uno pieno è `bg-lf-action text-lf-on-action`, o `bg-lf-<stato> text-lf-on-status`;
  - un segmento attivo o un preset scelto prendono `bg-lf-checked text-lf-on-checked` (D-T16).

**Passi:**
- [x] ✅ (16/10/2026) Costanti di `ui.ts`, tranne `INPUT` e `TITLE_INPUT`.
  > **Note implementazione**: 26 costanti convertite a mano; m1 di `ui.ts` da 118 a 15, che sono `INPUT` e
  > `TITLE_INPUT`. `BADGE` e `NOTICE` usano già `STATUS_TONES` di T e non li ho toccati.
- [x] ✅ (16/10/2026) I file, uno per volta. Gli elementi che non si possono convertire sono annotati.
  > **Note implementazione**: i 38 file li converte uno script riga per riga, `/tmp/libreFolio_dv_w5pac_convert.py`,
  > fuori dal repo. 204 pezzi convertiti. Lo script:
  > - divide la riga in pezzi a virgolette, graffe, backtick e `$`;
  > - converte un pezzo solo se ogni sua classe di colore ha un ruolo, quindi nessun elemento resta misto;
  > - toglie i `dark:`;
  > - salta le righe con `INPUT`, `TITLE_INPUT` o `className=`, e i frammenti esclusi.
  >
  > Gradini usati:
  >
  > | Cosa | Gradino | Ruolo |
  > |---|---|---|
  > | Testo neutro | 800+ / 600–700 / 300–500 | `text-lf-primary` / `-secondary` / `-muted` |
  > | Fondo neutro | 50–100 / 200–300 | `bg-lf-panel` / `bg-lf-neutral` |
  > | `hover:bg` neutro | ≤ 200 | `hover:bg-lf-hover` |
  > | Bordo neutro | ≤ 200 / ≤ 400 | `-subtle` / `-input` |
  > | Stati | testo ≥ 800 / fondo ≤ 100 / fondo ≥ 400 / bordo ≤ 400 | `-on-soft` / `-soft` / pieno / `-line` |
  > | `bg-white` | con anello o bordo di fuoco / altrimenti | `bg-lf-field` / `bg-lf-card` |
  > | `text-white` | solo accanto a `bg-libre-green` / a uno stato pieno | `text-lf-on-action` / `text-lf-on-status` |
  >
  > **Ritocchi a mano:**
  > - `AssetTable`:148, il quadratino della legenda «quota obiettivo», e `ResultCell`:78, la barra dell'obiettivo,
  >   prendono `bg-lf-secondary` (`--lf-text-secondary`): lo stesso neutro di «ideale» in TD-1.
  > - `StepNav`:100, il riempimento dell'avanzamento, prende `bg-lf-checked`: `bg-lf-action` in scuro è spento sulla
  >   traccia.
  > - `StepNav`:69, il passo corrente, prende `bg-lf-selected`.
  > - Regola 3: `text-lf-primary` sulla radice di `PacPlannerTool` (299) e sul pannello di `PlannerDialog` (26).
  >
  > **Residuo m1 del PAC: 42 (prima 581).**
  > - `ui.ts`, 15: `INPUT` e `TITLE_INPUT`.
  > - `BackendTimingBar`, 16: le 6 fasi, l'attesa in coda e il `border-white` dei segmenti (punti 2.1 e 2.5).
  > - `ExposureMaps`, 4: escluso (Y9).
  > - `TargetsStep`, 2: la traccia (tabella sopra).
  > - `DistributionDialog`, 3: la stessa traccia e la barra del peso.
  > - `AssetTable`, 1, e `ResultCell`, 1: la barra e il quadratino «quota dopo il piano», `bg-libre-green`.
  >
  > **⚠️ Fuori pista:** le barre «dopo il piano» restano `bg-libre-green`. Lì il verde è un colore di dato accanto
  > al neutro dell'obiettivo, non il marchio. `bg-lf-action` in scuro è spento sulla traccia, e la scelta tocca alla
  > designer (punto 2.7) o ai colori di tipo di GR1. Backlog DV-7.
  >
  > **⚠️ Fuori pista:** la traccia di `DistributionDialog`:102 è la stessa di `TargetsStep`, sotto la barra verde del
  > peso. Resta in palette anche lei, così le due tracce non divergono finché non c'è un ruolo per la traccia.
- [x] ✅ (16/10/2026) `theme-roles.mjs --update`, poi `--check`; il gate `themeRoles.gate.test.ts`, cioè G1–G4,
  compreso «nessun elemento misto».
  > **Note implementazione:**
  > - `--update`: m1 10980 → 10441 (−539, cioè il PAC da 581 a 42), m2 83 → 83.
  > - Il diff del baseline tocca solo righe del PAC: 33 file escono a zero e 6 restano col residuo.
  > - `--check` pulito; `themeRoles.gate.test.ts` 47/47, prima e dopo `--update`.
  >
  > **⚠️ Fuori pista: `app.css`.** Il gate C4 di `themeTokens.gate.test.ts` era rosso, 15/16. La barra fissa in
  > fondo a `PacPlannerTool` era l'ultimo uso di `bg-white/95` (ora `bg-lf-card/95`), e il gate vuole la regola
  > tolta da `app.css` nella stessa modifica.
  > - Con l'OK del coordinatore (16/10, 02:36), dal gruppo «Dark mode: Cards and modals» ho tolto solo il selettore
  >   `html.dark .bg-white\/95`.
  > - Resta `bg-white\/90`, che ha ancora degli usi.
  > - Poi 16/16. Il lotto di T delle 03:25 tocca `app.css` più in basso (righe ~310–340).
- [x] ✅ (16/10/2026) Prove leggere: Prettier, compilatore Svelte, i test del PAC uno per volta.
  > **Note implementazione:**
  > - Prettier ha riscritto 4 file (`ui.ts`, `PlannerDialog`, `BrokerScopeCopyDialog`, `OwnedAssetsDialog`); poi tutti
  >   puliti, `app.css` compreso.
  > - Compilatore Svelte: 37 file, 0 avvisi. `git diff --check` pulito.
  > - Vitest, un file per volta:
  >   - 12 test del PAC, 487 in tutto: `categoryLabels` 9, `decimal` 150, `format` 107, `modeText` 13,
  >     `pluralCountSites` 19, `request` 34, `ExposureBars` 12, `ResultCell` 7, `StateNotice` 6,
  >     `exposureBarColours` 24, `model` 11, `text` 95;
  >   - 7 gate, 201 in tutto: `themeRoles` 47, `themeTokens` 16, `themeComponentTokens` 18, `themeColorMeta` 15,
  >     `themeModeReads` 24, `designerLabImports` 27, `scanColors` 54;
  >   - 4 test che importano il PAC da fuori, 21 in tutto: `ToolsHub` 3, `ToolHost` 4, `registry` 8,
  >     `moneyRenderSites` 6.
  > - Nessun test asserisce classi del PAC, E2E compreso: test-author non serve.
- [x] ✅ (16/10/2026) Checkpoint: commit `4743b1542` del coordinatore (02:41), 43 file. Le merge simulate con il
  target `db384eaf5` e con il ramo di T (`abc4c84de`) sono pulite, compreso il baseline.
- [x] ✅ (16/10/2026) Prove pesanti nello slot delle 06:45, insieme a W5-charts, sulla base merge `35a55cf39` (target
  `72e66d1a6`, col secondo lotto di T: W1-c, W1-e con `ModalBase`, W2-a). Tutto verde: i conteggi stanno nella sezione
  «W5-charts», passo «Prove pesanti».

**Dove guardarlo, per il developer:**
- Strumenti › PAC, in chiaro e in scuro: tutti i passi, cioè scenario, strategia, asset, obiettivi, broker, liquidità,
  cambi, instradamento e revisione, con i loro dialoghi, poi il risultato (testata, KPI, tabella degli asset,
  piano operativo, prova, barra dei tempi).
- I campi di testo restano com'erano fino al lotto di T sull'input. Le barre verdi «dopo il piano» e la traccia
  degli obiettivi restano anche loro come prima.

### W5-charts — Ruoli di colore nei componenti di `components/charts/` ✅ (16/10/2026, validato su `35a55cf39`)

**Mandato.**
- Proposta del coordinatore alle 02:41, dopo il commit di W5-PAC (`4743b1542`): «i file di `components/charts/` che
  Y9 e K-15 non toccano». Stesse regole di W5-PAC: niente catene di classi, solo neutri, marchio e stati.
- Elenco approvato alle 02:50; via libera della 1.3 alle 02:5x: stanotte nessuna sessione tocca quei file, e Y4a
  (FE2a), che ne sposta 8 in `features/signals/`, parte dopo l'ingresso di DV.
- Checkpoint in un commit separato da W5-PAC, entro le 06:30, per entrare nello slot delle 06:45.

**Perimetro: 11 file**, più `frontend/src/themeRoles.baseline.tsv` (`--update`), questo piano e la riga DV-7 del
backlog.

| File | m1 → resto atteso | Con Y4a |
|---|---|---|
| `ChartSignalsSection.svelte` | 95 → 14 (2 campi) | `features/signals` |
| `ChartAestheticsSection.svelte` | 78 → 30 (2 campi, 4 interruttori) | resta |
| `ChartSettingsModal.svelte` | 47 → 0 | `features/signals` (D-Y14) |
| `SignalStyleEditor.svelte` | 42 → 0 | `features/signals` |
| `ChartToolbar.svelte` | 38 → 0 | resta |
| `MeasurePanel.svelte` | 34 → 0 | `features/signals` (D-Y14) |
| `SignalParamControl.svelte` | 24 → 14 (2 campi) | `features/signals` |
| `SignalVisualLegend.svelte` | 16 → 0 | `features/signals` |
| `ResolutionBadge.svelte` | 6 → 0 | resta |
| `SignalOptionContent.svelte` | 6 → 0 | `features/signals` |
| `SignalAssetParamControl.svelte` | 1 → 0 | `features/signals` |

Nessuno ha `echarts.init`. Ho simulato C4 prima di cominciare: nessuna regola del rimappaggio di `app.css` muore.

**Esclusi:**
- I file di Y9 e K-15: `ScatterChart`, `CandlestickChart`, `SemiDonutChart`, `AllocationPieChart`, `LineChart`,
  `PriceChartFull`, `GeographyMap`.
- **I 6 campi di testo e numerici, 42 classi:** `ChartSignalsSection`:609 e 798, `ChartAestheticsSection`:221 e 237,
  `SignalParamControl`:79 e 93.
  - Stanno accanto a `SimpleSelect` e `SearchSelect`, ancora legacy (40 e 63), quindi vanno col lotto di T sull'input,
    come `INPUT` nel PAC.
- **I 4 interruttori di `ChartAestheticsSection`, 16 classi:** traccia e manopola, alle righe 111/119, 133/141, 155/162
  e 176/184.
  - Nell'app nessun interruttore usa ancora i ruoli Q2. Il coordinatore (02:50) li vuole tutti insieme in un lotto di
    T, così in scuro non ce n'è uno diverso dagli altri. Annotati in DV-7.

**Catene di classi: nessuna.**
- Le prop di classe vanno solo alle icone lucide, dove la classe finisce sull'svg e ha una fonte sola.
- `itemTone` di `OrderableList` passa un tono (`default`, `warning`, `error`), non classi: le classi le sceglie
  `OrderableList`.
- `ModalBase` è già migrato; `InfoBanner`, `OrderableList`, `SimpleSelect` e `SearchSelect` sono legacy, ma da questi
  file non ricevono classi.

**Scelte approvate dal coordinatore (02:50), coerenti con il PAC:**
- segmenti attivi (7) → `bg-lf-checked text-lf-on-checked` (D-T16);
- opzioni scelte di `SignalStyleEditor` (4) → `border-lf-checked bg-lf-selected`;
- «Salva» → `bg-lf-action text-lf-on-action hover:bg-lf-action-hover`;
- «Annulla» (`bg-gray-100 hover:bg-gray-200`) → `bg-lf-panel hover:bg-lf-neutral`;
- icona di sincronizzazione (`hover:text-blue-500`) → `hover:text-lf-link`, come le altre icone della riga;
- bottoni d'avviso del cambio (`text-amber-500 hover:text-amber-600`) → `text-lf-warning hover:text-lf-warning-hover`,
  che scurisce al passaggio in entrambi i temi come oggi;
- banner e note ambra → terna warning; elimina ed errori → `danger`;
- selettori di colore: solo il bordo; casella → `accent-lf-checked`.

**⚠️ Punto aperto per la designer** (coordinatore, 02:50): `--lf-surface-panel` e `--lf-surface-hover` coincidono in
entrambi i temi, `#e8ece9` in chiaro e `#1b2421` in scuro.
- Un `hover:bg-lf-hover` su un fondo `bg-lf-panel` non si vede.
- Per ora, su un fondo panel l'hover è `hover:bg-lf-neutral`: «Annulla» di `ChartSettingsModal` e le righe di
  `MeasurePanel`.
- Domanda: l'hover deve distinguersi dal panel, o è voluto che un fondo panel non abbia hover?
- **Instradato** (coordinatore, 03:08): va nel pacchetto delle domande sui token di T, col caso di `SignalStyleEditor`.
  È una questione dei ruoli, non dei grafici, e il coordinatore la riporta nel resoconto del mattino.

**Passi:**
- [x] ✅ (16/10/2026) Conversione: il convertitore di W5-PAC, adattato, poi i ritocchi a mano.
  > **Note implementazione**: `/tmp/libreFolio_dv_w5charts_convert.py`, fuori dal repo, ricavato da quello di W5-PAC.
  >
  > | Novità | Effetto |
  > |---|---|
  > | Esclusioni per frammento | `focus:ring-libre-green`, cioè i 6 campi; la traccia `'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'`; la manopola `transform rounded-full bg-white`. Nessun'altra riga le contiene. |
  > | Contesto «segmento» | una stringa fatta solo di `bg-libre-green text-white` diventa `bg-lf-checked text-lf-on-checked` |
  > | Contesto «su panel» | un `hover:bg` accanto a un fondo `gray-50/100` diventa `hover:bg-lf-neutral` |
  > | Contesto «tenue» | il testo di stato accanto a un fondo di stato tenue diventa `-on-soft` (terna dell'avviso) |
  > | Mappe fisse | `hover:text-blue-500` → `hover:text-lf-link`; `hover:text-amber-600` → `hover:text-lf-warning-hover` |
  >
  > - 135 stringhe convertite. Restano solo i 6 campi, le 4 tracce e le 4 manopole, come previsto.
  > - **Ritocchi a mano:**
  >   - `MeasurePanel`:544, la riga della misura: `bg-lf-panel` con `hover:bg-lf-neutral`, perché la classe sta su
  >     due righe e il convertitore non vede il fondo;
  >   - `SignalStyleEditor`:94–95, il popover che galleggia: `border-lf-raised` e `shadow-lf-shadow`, come
  >     `HelpMenu`;
  >   - `ChartToolbar`:42, il divisore di 1 px: `bg-lf-subtle`, che è un divisore, non un riempimento. Oggi `subtle` e
  >     `neutral` hanno gli stessi valori;
  >   - regola 3, `text-lf-primary` sulla radice di `ChartSettingsModal` (il contenuto dentro `ModalBase`),
  >     `ChartSignalsSection` e `ChartAestheticsSection` (usati anche dalle pagine di asset e cambi), `MeasurePanel` e
  >     `ChartToolbar`. Gli altri sei stanno dentro questi, o hanno già il testo esplicito (`SignalOptionContent`,
  >     `ResolutionBadge`).
  > - **Scelte per significato:**
  >   - le etichette `bg-gray-100` vanno su `bg-lf-panel` per gradino: il testo `muted` sopra fa 4,52/4,54:1, contro
  >     4,01/4,11:1 su `neutral`;
  >   - la nota ambra di `MeasurePanel`:530 prende la terna con `-on-soft`: 6,37:1, contro 4,85:1 di `text-lf-warning`.
  > - Altri contrasti, chiaro/scuro:
  >   - segmento attivo `on-checked` su `checked`: 6,17/5,32;
  >   - segmento spento `secondary` su `card`: 7,48/7,08;
  >   - `warning-hover` su `card`: 6,83/5,48.
  >
  > **⚠️ Fuori pista: indentazione.** Il convertitore comprimeva l'indentazione delle righe di continuazione di una
  > classe su più righe. Qui sono `MeasurePanel`:544 e `SignalStyleEditor`:94; le ho ripristinate da `HEAD`, e il PAC
  > non ne ha. Corretto anche il convertitore: l'indentazione iniziale ora resta.
  >
  > **⚠️ Fuori pista: Prettier.** Ha riscritto 3 file (`ChartSettingsModal`, `ChartSignalsSection`, `ChartToolbar`),
  > che a `HEAD` erano puliti: le classi più corte fanno stare gli elementi su meno righe. Tocca solo elementi
  > convertiti.
  >
  > **Nota per la domanda alla designer:** il bottone di `SignalStyleEditor`:75 ha `hover:bg-lf-hover`.
  > - Si vede dove l'editor sta sulla card (`ChartSignalsSection`).
  > - Non si vede dove sta su un panel: le scatole di `SignalVisualLegend` e le righe di `MeasurePanel`.
  > - È così anche oggi, in chiaro: `gray-50` su `gray-50`. Il componente non conosce il suo ospite, quindi resta.
- [x] ✅ (16/10/2026) `theme-roles.mjs --update`, poi `--check`; i gate `themeRoles` (G1–G4) e `themeTokens` (C4).
  > **Note implementazione:**
  > - Prima di `--update`: `--check` pulito (11 file sotto il loro record), `themeRoles` 47/47, `themeTokens` 16/16.
  >   Nessuna regola di `app.css` muore.
  > - `--update`: m1 10441 → 10112 (−329 = 387 − 58), m2 83 → 83.
  > - Il diff del baseline tocca solo righe di `components/charts/`: 8 file escono a zero, mentre
  >   `ChartAestheticsSection` resta a 30, `ChartSignalsSection` a 14 e `SignalParamControl` a 14.
  > - Poi `--check` pulito.
- [x] ✅ (16/10/2026) Prove leggere: Prettier, compilatore Svelte, i test dei componenti e i gate, uno per volta.
  > **Note implementazione:**
  > - Prettier pulito e compilatore Svelte 11 file, 0 avvisi; `git diff --check` pulito.
  > - Vitest, un file per volta, 14 file che importano o nominano i componenti: 762/762.
  >   - `ChartSignalsSection` 21, `MeasurePanel` 23, `SignalTreeSelect` 28, `PriceChartFull` 36, `LineChart` 5,
  >     `BenchmarkSelect` 73;
  >   - `chartCoreHelpers` 287, `priceChartHelpers` 148, `echartsTooltipHelpers` 47, `measureSignal` 31,
  >     `signalLabel` 16, `colors` 34;
  >   - `htmlSink` 7, `moneyRenderSites` 6.
  > - 7 gate, 201/201: `themeRoles` 47, `themeTokens` 16, `themeComponentTokens` 18, `themeColorMeta` 15,
  >   `themeModeReads` 24, `designerLabImports` 27, `scanColors` 54.
  > - Nessun test asserisce colori di questi file: le classi asserite sono `animate-spin`, `lf-compact-number-input` e
  >   `hidden`, quindi test-author non serve.
- [x] ✅ (16/10/2026) Checkpoint: commit `7d3896011` del coordinatore (03:08), 14 file. Le merge simulate con il target
  `8850ad002` e con T (`abc4c84de`) sono pulite.
- [x] ✅ (16/10/2026) Prove pesanti, W5-PAC e W5-charts in una sola validazione, sulla base merge `35a55cf39` del
  coordinatore.
  > **Note implementazione**: la base merge porta il target `72e66d1a6`, col secondo lotto di T (W1-c, W1-e con
  > `ModalBase`, W2-a). L'albero era uguale alla simulazione e il worktree pulito; `app.css`, baseline e backlog si sono
  > fusi da soli. Sulla revisione: m1 8.833, m2 64.
  >
  > - Corsia 6156, `/tmp/librefolio-r2-dv`, dalle 06:47:45 alle 07:09:20 (21,5 minuti, sotto lo stop di 50); carico da
  >   25 a 78.
  > - Script `/tmp/libreFolio_dv_w5_heavy.sh`, un passo per volta:
  >
  > | Passo | Esito | Tempo |
  > |---|---|---|
  > | `api sync` | verde, 0 file tracciati cambiati | 27 s |
  > | `front check` | 0 errori, 0 avvisi | 136 s |
  > | `front-utility core-unit` | 174 file, 6220 test | 87 s |
  > | `front-utility component-unit` | 150 file, 3980 test | 337 s |
  > | gate Vitest `themeRoles.gate.test.ts` | 47/47 | 13 s |
  > | gate Vitest `themeTokens.gate.test.ts` | 18/18 (2 in più, dal secondo lotto di T) | 6 s |
  > | E2E `front-utility pac-allocator-real` | 1 passed, senza tentativi ripetuti | 609 s, quasi tutti di popolamento |
  > | E2E `front-fx fx-settings` | 3 passed | 79 s |
  >
  > - L'avviso di mathjax del runner (`CERTIFICATE_VERIFY_FAILED`, ripiego sul CDN) c'era già nel lancio di TD-1;
  >   non tocca le prove.
  > - Alla fine la porta 6156 è libera (`lsof` vuoto), HEAD `35a55cf39`, worktree pulito.

**Dove guardarlo, per il developer:**
- Dettaglio di un asset e di un cambio, in chiaro e in scuro:
  - la barra del grafico, cioè linea o candele e assoluto o %;
  - le misure sul grafico (pannello sotto il grafico);
  - il badge della risoluzione.
- ⚙️ Impostazioni del grafico (`assets/chart-settings` e `fx/chart-settings` in galleria): indicatori con le loro
  icone, avvisi e stili, il popover dello stile, l'estetica con la scala dell'asse, l'anteprima, «Annulla» e «Salva».
- Restano come prima i campi numerici e di testo (lotto di T sull'input) e i 4 interruttori dell'estetica (lotto di T
  sugli interruttori).

### W6 — Ruoli di colore in rischio, dashboard, strumenti e grafici ⏳ (dal 16/10/2026)

**Mandato.**
- Coordinatore, 16/10 alle 10:43, dopo D-T28 del developer (10:16): «è importante migrare il prima possibile i
  componenti prima di metterci a sviluppare funzioni grandi». Il programma colori si divide in sei aree; DV ha
  `features/risk/**`, `features/dashboard/**`, `routes/(app)/dashboard/**`, `features/tools/**` e `components/charts/**`.
- I broker sono passati a BK, che parte dal mio inventario.
- Elenco, ordine e scelte approvati alle 10:58.
- Il coordinatore manda il «chi parte prima» alla 1.3 e mi gira ogni cambio prima che io arrivi a quei file.

**Base:** `8f2824046`. `/tmp` è vuota dopo il riavvio delle 10:16, quindi il convertitore l'ho ricostruito nella
cartella della sessione (`files/dv_w6_convert.py`), con la correzione dell'indentazione di W5-charts.

**Area: 57 file, m1 1.493, m2 0.** L'inventario usa le regole del gate (`listSources`, `codeOf`, `LEGACY_CLASS_RE`).

| Lotto | File | m1 | Resto atteso |
|---|---|---|---|
| W6-c · strumenti e grafici | 9 | 348 | 0 |
| W6-a · rischio | 30 | 763 | 4 |
| W6-b · dashboard | 10 | 295 | 6 + 4 |
| W6-d · dopo l'ingresso di Y (W7) | 2 | 48 | — |
| Restano | 6 | 39 | — |

- **W6-c:**
  - in `features/tools/`: `ToolsHub` 84, `ToolDiagnosticsPanel` 78, `ToolAboutPanel` 58, `ToolHost` 56,
    `components/ToolExecutionMetrics` 24, `pac-allocator/planner/result/ExposureMaps` 4;
  - in `components/charts/`: `PriceChartFull` 36, `ScatterChart` 4, `GeographyMap` 4.
- **W6-a,** in `features/risk/`:
  - `RiskAnalysisPanel` 192, `AssetSetRiskPanel` 71, `CorrelationHeatmap` 33, `AssetSetLossComparisonSection` 26,
    `CorrelationPairsList` 25, `AssetSetRiskReturnSection` 22, `AssetSetCorrelationSection` 20, `RiskReturnLevel` 14,
    `AssetRiskScenariosView` 13, `LabAssetPicker` 8, `BenchmarkSelect` 3, `AssetChip` 2, `assetSetTable.ts` 2;
  - `levels/`: `l4/L4Simulation` 45, `l4/L4Replay` 29, `RiskLevelSection` 29, `L4WhatIf` 27, `l4/L4Shock` 25,
    `L2Diversification` 23, `RiskPanelHeader` 22, `RiskPartialNotice` 20, `SimulationProvenance` 20,
    `l1/ReturnHistogram` 16, `L1HowMuchItHurts` 11, `l1/UnderwaterChart` 8, `RiskLevelsPanel` 6, `L3RiskAdjusted` 4,
    `l4/TornadoChart` 4, `L3Benchmark` 2.
- **W6-b:**
  - in `features/dashboard/`: `GrowthChart` 86, `KpiSection` 50, `OtherPeriodEffectsTable` 28, `ContributionTable` 14,
    `KpiCard` 14, `ExposureTreemap` 10, `YieldOnCostCell` 8, `AllocationHistoryChart` 4, `PerformanceChart` 4;
  - `routes/(app)/dashboard/+page.svelte` 77.
- **W6-d:** `ExposureTable` 2 e `PositionsPanel` 46. Y (W7) ci ha scritto modifiche di sola logica, non ancora
  committate: si migrano dalla versione di Y dopo il suo ingresso (coordinatore, 10:43).
- **Restano:**
  - `ChartAestheticsSection` 16: i 4 interruttori, per il lotto di T;
  - i residui DV-7 del PAC: `AssetTable` 1, `ResultCell` 1, `TargetsStep` 2, `BackendTimingBar` 16 e
    `DistributionDialog` 3;
  - `DistributionDialog` è anche riservato a J-17 (coordinatore, 11:0x): non lo tocco.

**Resto atteso, da annotare in DV-7:**
- `KpiSection` 6: catene verso `KpiMetricBar`, ancora legacy (18, in `components/ui/display`).
  - Sono `valueColor`@354 e le due barre @398/@409, «valore contabile» blu e «liquidità» smeraldo.
  - La catena la prende T, che ha `ui/display` nel suo resto (coordinatore, 10:58).
- `OtherPeriodEffectsTable` 4: i badge di segno (coordinatore, 10:58).
  - `--lf-gain` e `--lf-loss` hanno oggi i valori di success e danger, ma restano ruoli distinti.
  - Il coordinatore chiede a T gli alias `gain-soft`/`loss-soft` dopo lo skill (D-T29); poi li migro.
- `RiskReturnLevel` 4: le forme della legenda, categorie uguali alla serie ECharts (punto 2.5 della designer).

**Scelte approvate (coordinatore, 10:58):**
1. **Campi semplici del rischio** (10): la convenzione di T, `border-lf-input bg-lf-field text-lf-primary
   hover:border-lf-input-hover`, focus `lf-focus`.
   - Righe: `L4Shock`:175, `L4Simulation`:181, 185 e 209, `RiskAnalysisPanel`:641, 779, 795, 900, 904 e 1012.
   - Select e lotto input di T sono entrati, quindi il motivo di W5-charts per lasciarli non vale più.
2. **Numeri con segno:** `LOSS_CLASS` di `AssetSetLossComparisonSection` → `text-lf-loss`; le barre dell'istogramma
   sotto il taglio → `bg-lf-loss/80`, come `SIGN_BAR.tornado`.
3. **Preset di `L4Shock`:145:** pieni, `bg-lf-checked text-lf-on-checked` (D-T16). Le card dei modi di
   `L4Simulation`:157 → `border-lf-checked bg-lf-selected`, come le card scelte del PAC.
4. **Filtro dei broker della dashboard** (`+page` 886–936): attivo → `bg-lf-selected text-lf-link border-lf-focus`,
   come `FxProviderSelect` aperto e `TabBar`; spento → bottone secondario; spunta della voce scelta → `text-lf-link`.
   Va fra i «da rivedere» del developer.

**Scelte per significato:**
- bottoni d'azione L4 (`hover:bg-primary-600`) → ruoli `action`;
- suggerimento bordato di `L4Replay`:318 → `border-lf-link text-lf-link hover:bg-lf-selected`;
- segmenti di `GrowthChart`, `PriceChartFull` e `CorrelationHeatmap` → D-T16;
- linea di 1 px di `RiskAnalysisPanel`:683 → `bg-lf-input`;
- barrato di `AssetChip` → `decoration-lf-input`;
- sottolineatura e sfumatura di bordo di `CorrelationHeatmap` → `decoration-lf-link` e `from-lf-card`;
- regola 3 sulle radici.

**Verifiche fatte prima di cominciare:**
- **C4 simulato:** nessuna regola del rimappaggio di `app.css` muore.
- **Test che asseriscono classi colore:** nessuno nell'area, né unit né E2E, quindi test-author non serve.
- **Condivisi:** baseline (`--update` per lotto), questo piano, la sezione DV del backlog.

**Passi:**
- [x] ✅ (16/10/2026) W6-c: conversione, ritocchi, `--update`/`--check`, prove leggere (carico sotto 50), checkpoint
  consegnato al coordinatore (11:1x), in attesa del commit.
  > **Note implementazione** (16/10, 11:00–11:12): il convertitore ha cambiato 116 stringhe in 9 file, senza resti.
  >
  > **Ritocchi a mano:**
  > - **Testo di stato fuori da una tinta.** `ToolDiagnosticsPanel`:138 (disponibilità del pool) e `ToolAboutPanel`:313
  >   e 318 (interfaccia compatibile o no) erano `text-green-800` e `text-amber-800`, ma senza un fondo tenue dietro.
  >   - La regola del convertitore (gradino 800 → `-on-soft`) vale solo su una tinta, quindi qui vanno `text-lf-success`
  >     e `text-lf-warning`.
  >   - Contrasti su `card`: 5,21 e 5,20 in chiaro, 9,61 e 8,13 in scuro.
  > - **Anello di focus verde.** `ToolExecutionMetrics`:94 è `focus-visible:outline-green-700`: un focus, non uno
  >   stato, quindi `focus-visible:outline-lf-focus`. Ho corretto anche il convertitore: un anello verde sotto `focus`
  >   va a `lf-focus`.
  > - **Ombra delle card dei tool** (`ToolsHub`:218): `hover:shadow-sm` prende anche `hover:shadow-lf-shadow-card`, come
  >   le card di pagina di T (`PageToolbar`, `DataEditor`, `AllocationPanel`).
  > - **Regola 3:** `text-lf-primary` sulla radice di `ToolsHub`, `ToolHost`, `ToolAboutPanel` e
  >   `ToolDiagnosticsPanel`; `ToolExecutionMetrics` ce l'aveva già (`text-gray-900`).
  >   - Nelle primitive dei grafici (`PriceChartFull`, `ScatterChart`, `GeographyMap`) e in `ExposureMaps` nessun testo
  >     eredita il colore: ogni elemento con testo ha il suo ruolo, quindi la radice resta com'è.
  >
  > **Scelte già approvate, applicate:**
  > - segmenti di `PriceChartFull` (linea/candele, assoluto/%) → `bg-lf-checked text-lf-on-checked` (D-T16), 6,17/5,32;
  > - bottoni secondari di `ToolsHub`, `ToolHost`, `ToolAboutPanel` e `ToolDiagnosticsPanel` → `border-lf-input`,
  >   `hover:bg-lf-hover`; con `bg-lf-card` dove l'originale aveva `bg-white`;
  > - riquadri d'errore e d'avviso → terne `danger` e `warning`;
  > - icone del marchio (chiave inglese, freccia, icona del tool) → `text-lf-link`, come i link.
  >
  > - Prettier ha riscritto 4 file (`PriceChartFull`, `ToolAboutPanel`, `ToolHost`, `ToolsHub`), puliti a `HEAD`: solo
  >   elementi convertiti, che con classi più corte stanno su meno righe.
  > - Compilatore Svelte 9 file, 0 avvisi; `git diff --check` pulito.
  > - `--update`: m1 8.249 → 7.901 (−348), m2 54 invariato. Tutti i 9 file escono dal baseline a zero, poi `--check`
  >   pulito.
  > - **Prove leggere** (carico 43, sotto 50), un file per volta:
  >   - 18 file che importano o nominano i componenti, 853/853, tra cui `ToolsHub` 3, `ToolHost` 4, `PriceChartFull` 36,
  >     `PriceChartFull.tooltipEscape` 17, `ScatterChart` 14, `geographyMapHelpers` 25, `chartFlagFont` 16,
  >     `AssetSetRiskReturnSection` 136 e `scanColors` 67;
  >   - 7 gate, 156/156: `themeRoles` 47, `themeTokens` 18, `themeComponentTokens` 18, `themeColorMeta` 15,
  >     `themeModeReads` 24, `designerLabImports` 27, `htmlSink` 7.
  > - **Regola 4 dello skill `design-system`** (D-T29, `6e569084a`: «un colore, una ternaria»). In Tailwind 4 due
  >   utility sulla stessa proprietà si ordinano per nome, e vince la seconda. Il passaggio ai ruoli rovescia l'ordine:
  >   un `border-lf-subtle` fisso batte un `border-lf-checked` condizionale.
  >   - Ho scritto un controllo in sola lettura, `files/dv_rule4_check.mjs` nella cartella della sessione. Cerca un ruolo
  >     fisso e uno condizionale sulla stessa proprietà, risolvendo anche le costanti importate (`ui.ts`) e i template.
  >   - Prova su un file sintetico: 2 errori e 2 casi «fortunati» trovati, il caso corretto ignorato.
  >   - Su W5-PAC, W5-charts e W6-c: **0 casi**. Lo rilancio a ogni lotto di W6.
  >
  > **⚠️ Fuori pista: rilettura dello skill `design-system`** (coordinatore, 11:1x): sezione «Charts» e righe dei
  > grafici della mappa di `lib/theme/`, controllate sul codice; correzioni mandate al coordinatore per T. Fra queste,
  > un difetto mio: `growthBrokerColor` ripete gli 8 colori dal nono broker, senza la sfumatura di GR5 (DV-8).
- [x] ✅ (16/10/2026) W6-a: conversione, ritocchi, `--update`/`--check`; checkpoint consegnato al coordinatore (11:3x)
  senza le Vitest.
  > **⚠️ Fuori pista: le Vitest di W6-a rimandate.** Dalle 11:21 il carico è salito a 85–144, sopra la soglia di 50.
  > Il coordinatore (11:3x) ha chiesto il checkpoint senza: le 55 Vitest collegate girano insieme a quelle di W6-b
  > appena il carico scende. I test sono per componente, quindi un rosso resta attribuibile; lo slot unico copre tutto.
  >
  > **Regola 7, seguito** (coordinatore, 11:3x): T aggiunge `SIGN_TEXT.riskTable` (gain/loss) e `SIGN_BAR.histogram`
  > (gain e loss a `/80`) nel suo lotto dei ruoli, con `SIGN_BADGE`. Le adotto dopo il suo ingresso (DV-9); fino ad
  > allora restano `text-lf-loss` e `bg-lf-loss/80`.
  > **Note implementazione** (16/10, 11:14–11:21), sulla base `b5fafb1ad` (W6-c `5d2c1ce62` più lo skill
  > `design-system`). Da qui la ricetta è lo skill `design-system` (coordinatore, 11:1x).
  >
  > - Il convertitore ha cambiato 276 stringhe in 30 file. Ne ha lasciate 5: le 4 previste a mano più la legenda di
  >   `RiskReturnLevel`, esclusa.
  > - **Catene di classi** (regola 3): portano solo layout. `panelClass="w-64"`, `wrapperClass="ml-auto"` e
  >   `boxClass="w-full"` in `AssetSetRiskPanel` e `L3Benchmark`; `triggerClass`/`fieldsClass` `h-8` in `L4Replay`.
  >   `getRowClass` di `RiskReturnLevel` dà nomi propri (`risk-return-row-*`).
  > - **Tooltip** (regola 6): tutti con `text=`, nessun testo colorato dentro la superficie invertita.
  > - **Superfici galleggianti** (regola 9): nessuna nei file del rischio, i menu sono `SelectPopover`, già migrato.
  >
  > **Ritocchi a mano:**
  > - **Campi:** sono **12**, non 10 come nell'elenco: l4 `L4Shock`:170, `L4Simulation`:181, 185 e 209;
  >   `RiskAnalysisPanel`:633, 770, 795, 900, 904, 1003, 1023 e 1036.
  >   - Il convertitore li aveva presi per scatole (`border-lf-subtle`, e `bg-lf-card text-lf-secondary` nel pannello),
  >     perché non avevano un anello di focus.
  >   - Ora hanno la convenzione di T: `border-lf-input bg-lf-field text-lf-primary hover:border-lf-input-hover
  >     focus:border-lf-focus focus:ring-1 focus:ring-lf-focus` (regola 8).
  >   - Le caselle e il radio non hanno classi di colore e restano col colore del browser.
  > - **Segni** (regola 7):
  >   - `LOSS_CLASS` di `AssetSetLossComparisonSection` → `text-lf-loss`, non `danger`;
  >   - barre dell'istogramma sotto il taglio → `bg-lf-loss/80`, come `SIGN_BAR.tornado`;
  >   - la barra e l'etichetta del taglio restano `warning`.
  >   - Lo skill vuole i segni presi da `SIGN_TEXT`/`SIGN_BAR`, ma nessuna voce esistente ha questo significato (una
  >     tabella del rischio, un istogramma). Ho messo i ruoli diretti approvati alle 10:58, da rivedere: due voci per T
  >     (`SIGN_TEXT.riskTable`, `SIGN_BAR.histogram`?).
  > - **Preset di `L4Shock`:** pieni, `border-lf-checked bg-lf-checked text-lf-on-checked` (D-T16). Le card dei modi di
  >   `L4Simulation` → `border-lf-checked bg-lf-selected`.
  > - **Suggerimento di `L4Replay`:318** → `border-lf-link text-lf-link hover:bg-lf-selected`.
  > - **Bottoni d'azione** di `RiskAnalysisPanel` (5): prendono `hover:bg-lf-action-hover`, come i bottoni L4 (che lo
  >   avevano da `hover:bg-primary-600`) e come vuole lo skill per il bottone principale.
  > - **Resti del convertitore:** barrato di `AssetChip` → `decoration-lf-input`; sottolineatura dell'ordinamento di
  >   `CorrelationHeatmap` → `decoration-lf-link`; sfumatura di bordo → `from-lf-card`; linea di 1 px di
  >   `RiskAnalysisPanel` → `bg-lf-input`.
  > - **Regola 3:** `text-lf-primary` sulle radici montate dalle pagine: `RiskLevelsPanel` (dashboard, broker),
  >   `AssetSetRiskPanel` (asset), `AssetRiskScenariosView` (dettaglio asset), `RiskAnalysisPanel`.
  >
  > **Da rivedere (D-T27):**
  > - la «x» dei chip degli asset (`AssetSetRiskPanel`:691): `hover:bg-lf-hover` su un chip `bg-lf-neutral`, più
  >   chiaro in chiaro e più scuro in scuro, ma visibile;
  > - i bottoni «aggiorna» bordati di `RiskAnalysisPanel` e `RiskPanelHeader`: `border-lf-subtle bg-lf-card`, senza
  >   hover, fedeli all'originale.
  >
  > **⚠️ Fuori pista: i `dark:` senza metà chiara.** Il convertitore toglie ogni `dark:`. Se un elemento aveva solo
  > `dark:bg-*`, senza un fondo chiaro, il fondo scuro spariva.
  > - Ho scritto un controllo sulle versioni originali, `files/dv_dark_only_check.py`.
  > - In W6-a i soli casi sono i 4 campi l4 (`dark:bg-slate-700`), già sistemati con `bg-lf-field`.
  > - Sugli originali di W6-c (`8f2824046`), W5-PAC (`74e332076`) e W5-charts (`4743b1542`): **0 casi**.
  >
  > - Regola 4 (il mio controllo): 0 casi nel rischio.
  > - Prettier ha riscritto 7 file, puliti a `HEAD`, solo negli elementi toccati. Compilatore Svelte 29 file, 0 avvisi;
  >   `git diff --check` pulito.
  > - `--update`: m1 7.901 → 7.142 (−759 = 763 − 4), m2 54 invariato. 29 file escono a zero, `RiskReturnLevel` resta a 4
  >   (la legenda, punto 2.5); poi `--check` pulito.
- [x] ✅ (16/10/2026) W6-b: conversione, ritocchi, `--update`/`--check`; checkpoint consegnato senza le Vitest, come
  W6-a.
  > **Note implementazione** (16/10, 11:31–11:35), sulla base `622683733` (W6-a). Il convertitore ha cambiato 95
  > stringhe in 10 file. Ne ha lasciate 5, tutte per decisione:
  > - **`KpiSection`, 3 righe (6 classi):** le catene verso `KpiMetricBar`, ancora legacy: `valueColor`@354 e le barre
  >   @405 (valore contabile, blu) e @417 (liquidità, smeraldo).
  >   - Le prende T, che ha `ui/display` (coordinatore, 10:58).
  >   - La barra della liquidità dipende anche dal punto 2.2.
  > - **`OtherPeriodEffectsTable`, 2 righe (8 classi):** i badge «Income» e «Cost» restano legacy (coordinatore, 10:58).
  >   - Migrano con `SIGN_BADGE` di T (DV-9).
  >   - L'elemento non resta misto: la parte fissa della classe non ha colori, e il ramo neutro `default` passa ai
  >     ruoli (`bg-lf-panel text-lf-secondary`).
  >
  > **Ritocchi a mano:**
  > - **Filtro dei broker della dashboard** (scelta 4, da rivedere):
  >   - attivo → `bg-lf-selected text-lf-link border-lf-focus`;
  >   - spento → `bg-lf-card text-lf-secondary border-lf-input hover:bg-lf-hover`;
  >   - voce scelta e spunta → `text-lf-link`.
  >   - Il convertitore aveva messo le terne `info`, dal blu di oggi.
  > - **Il menu a tendina del filtro** (`fixed z-50`, regola 9) → `border-lf-raised` e `shadow-lf-shadow`. I bottoni
  >   «tutti/nessuno» dentro sono pieni secondari, `bg-lf-panel hover:bg-lf-neutral`, come dice lo skill.
  > - **Card di pagina** (regola 9) → `shadow-sm shadow-lf-shadow-card`, come T: `GrowthChart`, `KpiCard`, le 3 card di
  >   `KpiSection` e 3 card della pagina (liquidità, caricamento del rischio).
  > - **Regola 3:** `text-lf-primary` sulla radice della pagina e su `GrowthChart`, `KpiCard`, `KpiSection` e
  >   `PerformanceChart`, che la pagina del broker monta anche lei.
  > - **Badge di stato di `ContributionTable`:** «aperta» → `bg-lf-success-soft text-lf-success-on-soft`, come
  >   `STATUS_TONES.fileSet.set`; «venduta tutta» → `bg-lf-panel text-lf-secondary`.
  >
  > **Controlli:**
  > - segmenti di `GrowthChart` (D-T16);
  > - tooltip dei KPI: `tooltipRows` con le emoji, nessun colore dentro;
  > - regola 4: 0 casi;
  > - `dark:` senza metà chiara: 0;
  > - test che asseriscono classi: nessuno.
  >
  > - Prettier ha riscritto 3 file (`ExposureTreemap`, `GrowthChart`, `+page`), puliti a `HEAD`, solo negli elementi
  >   toccati. Compilatore Svelte 10 file, 0 avvisi; `git diff --check` pulito.
  > - `--update`: m1 7.142 → 6.861 (−281 = 295 − 14), m2 54 invariato. 8 file escono a zero, `KpiSection` resta a 6 e
  >   `OtherPeriodEffectsTable` a 8; poi `--check` pulito.
  > - **Vitest:** le 92 collegate a W6-a e W6-b (55 + 38, una in comune) girano appena il carico scende sotto 50, prima
  >   dello slot. Alle 11:33 era 73.
- [x] ✅ (16/10/2026) DV-9, piccolo lotto prima dello slot (coordinatore, 11:36), sulla base `63e3a22d8` (W6-b
  `daea7b31c` più il lotto dei ruoli di T `f043c1b58`, che porta `SIGN_TEXT.riskTable`, `SIGN_BAR.histogram` e
  `SIGN_BADGE`).
  > **Note implementazione** (16/10, 11:37–11:40):
  > - `AssetSetLossComparisonSection`: `LOSS_CLASS` = `` `tabular-nums ${SIGN_TEXT.riskTable.loss}` ``.
  > - `ReturnHistogram`: le barre sotto il taglio prendono `SIGN_BAR.histogram.loss`. Le altre restano `bg-lf-neutral`
  >   e quella del taglio `bg-lf-warning`, quindi `histogram.gain` non serve.
  > - `OtherPeriodEffectsTable`: «Income» → `SIGN_BADGE.gain`, «Cost» → `SIGN_BADGE.loss`, cioè le tinte di guadagno e
  >   perdita, non quelle di successo e pericolo.
  > - Le altre tabelle del rischio usavano già `POLARITY_TONES` (correlazione, divergenza) o `SIGN_BAR.tornado`.
  > - Prettier pulito, compilatore 3 file 0 avvisi, `git diff --check` pulito.
  > - `--update`: m1 6.861 → 6.853 (−8); `OtherPeriodEffectsTable` esce dal baseline. `--check` pulito.
  > - Le Vitest di questi 3 file sono già fra le 92 di W6-a e W6-b.
- [x] ✅ (16/10/2026) Le 92 Vitest collegate a W6-a, W6-b e DV-9 (55 + 38, una in comune), un file per volta.
  > **Note implementazione:**
  > - Dalle 11:43:35 (carico 49,7) alle 12:17:42, su `bf2afbba3` e poi sul worktree che intanto riceveva DV-8 e
  >   `ui/display`.
  > - Quattro pause automatiche quando il carico superava 90, ripartendo sotto 60: alle 11:46, 11:50, 12:05 e 12:13.
  > - **92 file, 3.742 test, 0 rossi** (`/tmp/libreFolio_dv_w6ab_vitest.summary`).
  > - I file girati dopo le 12:03 vedono anche `ui/display`: per esempio `L2Diversification.test.ts`, 17/17.
- [x] ⚠️ (16/10/2026) Slot pesante unico, sotto i 45 minuti: `api sync`, `front check`, `core-unit`, `component-unit`, i
  gate Vitest `themeRoles` e `themeTokens`, E2E `front-portfolio dashboard`, `risk`, `risk-lab` e `front-utility
  pac-allocator-real`; se c'è tempo, `front-portfolio broker-filter-label` e `front-fx fx-settings`. **Tutto verde
  tranne 1 rosso di test, un'assunzione da riparare alla ripresa.**
  > **Note implementazione:**
  > - Via del coordinatore alle 13:04, sulla base merge **`9da2e5da9`**. È la punta `bfd33a0f5` con i lotti 1–8 di AF;
  >   il baseline era in conflitto, risolto con `--resolve`, e il m1 combinato è 5.284.
  > - Contiene W6-c, W6-a, W6-b, DV-9, DV-8 e `ui/display` (commit `5d2c1ce62`, `622683733`, `daea7b31c`,
  >   `bf2afbba3`, `28f4bed75`, `a694d8fb2`).
  > - Corsia 6156, `/tmp/librefolio-r2-dv`, dalle 13:06:43 alle 13:38:30 (32 minuti), carico da 91 a 99, sceso a 33
  >   nel mezzo.
  > - Guardie a orario fisso: gli E2E partono fino alle 13:40, i passi leggeri fino alle 13:45. Nessun passo è saltato.
  >
  > | Passo | Esito | Tempo |
  > |---|---|---|
  > | `api sync` | verde, 0 file tracciati cambiati | 34 s |
  > | `front check` | 0 errori, 0 avvisi | 118 s |
  > | `front-utility core-unit` | 179 file, 6.418 test | 125 s |
  > | `front-utility component-unit` | **1 rosso**: 153/154 file, 4.040/4.041 test | 277 s |
  > | gate Vitest `themeRoles.gate.test.ts` | 52/52 | 3 s |
  > | gate Vitest `themeTokens.gate.test.ts` | 19/19 | 2 s |
  > | E2E `front-portfolio dashboard` | 27 passed | 677 s, col rebuild unico di frontend e documentazione dopo la merge con AF |
  > | E2E `front-portfolio risk` | 38 passed | 237 s |
  > | E2E `front-portfolio risk-lab` | 44 passed | 292 s |
  > | E2E `front-utility pac-allocator-real` | 1 passed | 45 s |
  > | E2E `front-portfolio broker-filter-label` | 2 passed | 51 s |
  > | E2E `front-fx fx-settings` | 3 passed | 45 s |
  >
  > - Gli E2E sono 115 test, nessuno ripetuto; ogni E2E ha ripopolato il DB. Alla fine la porta 6156 è libera e
  >   l'HEAD è `9da2e5da9`.
  > - Script, riassunto e log del passo stanno nella cartella della sessione, `files/w6-slot-2026-10-16/`, perché `/tmp`
  >   non sopravvive a un riavvio.
  >
  > **Il rosso:** `src/lib/components/ui/display/KpiMetricBar.test.ts`:47, «draws the fill at the requested percentage
  > with the default colour».
  > - Asserisce `expect(bar.className).toContain('bg-slate-400')`, la classe palette della barra di default.
  > - Il lotto `ui/display` l'ha portata sul ruolo `bg-lf-input`.
  > - **Verdetto (`test-triage`): assunzione.** Il test asserisce una classe colore (la regola 10 dello skill
  >   `design-system` lo vieta); il prodotto è giusto.
  > - Gli altri test dei tre componenti passano. `KpiDivergingFlowBar.test.ts`:198–202 passa un proprio colore nella
  >   prop e ne controlla l'arrivo, quindi non dipende dai miei valori.
  > - Gli E2E non asseriscono classi colore dei tre componenti.
  >
  > **⚠️ Fuori pista: un'analisi mancata.** Nel lotto `ui/display` ho controllato le asserzioni di classe nei test dei
  > chiamanti, ma non nei test dei tre componenti, che stanno accanto a loro. Da qui la ricerca copre ogni file
  > `*.test.ts` che nomina i file toccati, non solo quelli dei chiamanti.
  >
  > **Pausa del developer** (coordinatore, durante lo slot): finito lo slot, FROZEN. Niente commit, niente comandi nuovi, niente
  > sotto-agenti. Riparazione e ingresso alla ripresa.
- [x] ✅ (16/10/2026) Alla ripresa, prima dell'ingresso: test-author ripara `KpiMetricBar.test.ts`:47, poi rilancio quel file da solo,
  con carico sotto 50.
  > **Correzione del coordinatore** (13:39): l'asserzione non va portata su `bg-lf-input`, che sarebbe ancora una classe
  > colore (regola 10 dello skill `design-system`). Test-author asserisce qualcosa di semantico:
  > - **il comportamento**: la larghezza richiesta, già asserita, e, con un valore di prova in `barColor`, che il colore
  >   del chiamante arriva sulla barra, come fa `KpiDivergingFlowBar.test.ts`:198–202. Nessuna modifica al prodotto, e
  >   la mia proposta: la barra di default non la usa nessun chiamante (gli 11 `KpiMetricBar` di `KpiSection` passano
  >   tutti `barColor`);
  > - **oppure lo stato con un attributo**: un `data-*` che `KpiMetricBar` pubblica sulla barra quando usa il colore di
  >   default. È una piccola modifica d'interfaccia in un mio file, da decidere col coordinatore (`test-triage` §6).
  > - `KpiDivergingFlowBar.test.ts`:198–202 usa `bg-blue-500` e `bg-red-500` come valori di prova: non dipendono dai
  >   colori del prodotto, ma per coerenza con la regola 10 test-author può passare a valori di prova neutri.
  >
  > **Deciso** (coordinatore, 13:41): il comportamento, senza toccare il prodotto. Ripresa alle 14:14 (pausa del
  > developer dalle 13:2x). Resta fuori `KpiDivergingFlowBar.test.ts`: i suoi sono valori di prova, non colori del
  > prodotto.
  >
  > **Note implementazione** (16/10, 14:15–14:19):
  > - **Cosa ha fatto test-author:**
  >   - il test diventa «draws the fill at the requested percentage» e asserisce solo la larghezza (`42.5%`);
  >   - il test nuovo «paints the fill with the colour the caller passes in» passa `barColor: 'kpi-bar-test-colour'`,
  >     che non è né una classe palette né un ruolo, e controlla che arrivi sulla barra;
  >   - l'intestazione del file ora dice «never on a colour class or a translated string».
  >
  >   Il componente non è toccato.
  > - **Esito:** `KpiMetricBar.test.ts` 10/10 (erano 9 test, 1 rosso), girato col carico a 49. Gate Vitest
  >   `themeRoles` 52/52 e `themeTokens` 19/19. Prettier, `--check` e `git diff --check` puliti.
- [x] ✅ (16/10/2026) DV-8, le linee dei broker dal nono in poi (coordinatore, 11:48: prima di `ui/display`, perché Y8 della 1.3 aspetta
  DV-8 su `GrowthChart.svelte`).
  > **Note implementazione** (16/10, 11:50–12:0x), sulla base `bf2afbba3` (DV-9).
  > - `growthBrokerColor(index, dark, poles?)` in `lib/theme/chartPalettes.ts`: le prime 8 linee restano i primi 8 tipi
  >   della designer. Dalla nona passa da `sequenceColor('type', CATEGORY_SEQUENCE, index, dark, poles)`, cioè gli
  >   stessi 8 colori una sfumatura più in là a ogni giro (GR5), come la semi-ciambella e lo storico geografico.
  > - **I poli:** se il chiamante non li passa, quelli della card della pagina, `shadePoles(dark,
  >   chartRoles(dark).color('--lf-surface-card'))`, letti solo dalla nona linea. Il grafico della crescita sta sulla
  >   card della pagina, senza un tema forzato. Il parametro `poles` resta per un grafico che voglia il proprio elemento.
  > - **Più piccolo del previsto:** con i poli di default DV-8 si chiude tutto in `chartPalettes.ts`. `GrowthChart.svelte`
  >   e `growthChartSeries.ts` non cambiano (OK della 1.3 non usato), quindi Y8 non ha incroci.
  > - **Test:** il blocco `growthBrokerColor` di `lib/theme/chartCategories.test.ts` asseriva proprio la ripetizione (16
  >   linee = gli stessi 8 due volte). Lo riscrive test-author: 56 colori distinti, la 57ª uguale alla nona, i poli
  >   espliciti, la lettura dei ruoli solo dalla nona, il Lab che arriva alla sfumatura.
  >   - **⚠️ Fuori pista:** il primo test-author è morto sul timeout della rete (11:53–11:57) senza fare nulla;
  >     rilanciato alle 11:59.
  > - `GrowthChart.test.ts` usa 2 broker e non cambia.
  > - **Test di test-author** (secondo lancio, 12:00–12:10): il blocco di `chartCategories.test.ts` passa da 2 test
  >   (3 casi) a 6 test (10 casi). Il file è 95/95, girato col carico a 40,4. Copre:
  >   - le prime 8 linee;
  >   - dalla nona, le sfumature con i poli della card;
  >   - 56 colori distinti, e la 57ª uguale alla nona;
  >   - i poli espliciti che vincono;
  >   - la card letta solo dalla nona linea, una volta;
  >   - il Lab che arriva alla sfumatura.
  >
  >   Ha anche un `afterEach` che rimette il lettore dei ruoli.
  > - **⚠️ Fuori pista minore:** un secondo lancio di test-author, di 4 secondi sullo stesso file, è partito col carico a
  >   53,3; l'ha dichiarato lui.
  > - **Note di test-author sul codice, non toccato:**
  >   - Dal nono broker in poi, ogni linea rifà `chartRoles` (un `getComputedStyle` di `<html>`), non uno per disegno. Costa
  >     solo oltre gli 8 broker; si toglie passando i poli dal chiamante, che oggi non serve.
  >   - In chiaro la card si legge e `shadePoles` la ignora.
  >   - Si legge su `<html>`, non sull'elemento del grafico: va bene finché la crescita non sta in un tema forzato, come
  >     dice il commento.
  > - Prettier pulito sui 2 file; `git diff --check` pulito.
  > - **Non girati per il carico (92):** `roleColors.test.ts` (il controllo dei ruoli morti: la nuova chiamata
  >   `.color('--lf-surface-card')` legge un ruolo già letto), `chartTheme.test.ts`, `designerLabImports` e
  >   `scanColors`. Li copre `core-unit` nello slot di W6.
- [x] ✅ (16/10/2026) `ui/display`: `KpiMetricBar`, `KpiDivergingFlowBar` e `RiskMetricCard` (52 classi), passati da T a
  DV con i loro chiamanti (coordinatore, 11:48). OK della 1.3 alle 11:5x.
  > **Note implementazione** (16/10, 11:55–12:20), sulla base `28f4bed75` (DV-8).
  > - Il convertitore ha cambiato 19 stringhe. I chiamanti (`KpiSection`, i livelli L1 e L2, `RiskCardGrid`) passano solo
  >   layout o ruoli (`SIGN_*`, `POLARITY_TONES`), tranne `KpiSection`.
  >
  > **Ritocchi a mano, per significato** (skill `design-system`):
  > - **Tracce delle barre** (`KpiMetricBar`, le due metà di `KpiDivergingFlowBar`) → `bg-lf-neutral`. Lo skill mette
  >   le tracce sul `neutral`; il convertitore le avrebbe messe su `panel`.
  > - **Divisorio di 1 px** al centro di `KpiDivergingFlowBar` → `bg-lf-input`, per restare visibile sulla traccia
  >   `neutral` (come la linea di `RiskAnalysisPanel`).
  > - **Barra di default** di `KpiMetricBar` (`bg-slate-400`, nessun chiamante la usa) → `bg-lf-input`, che per contratto
  >   fa 3:1 su card e pannello.
  > - **Triangolo del marcatore** (`border-b-gray-600`) → `border-b-lf-secondary`.
  >   - **⚠️ Fuori pista:** il convertitore non riconosce le classi di un lato solo (`border-b-*`), che il gate invece
  >     conta. Qui era il solo caso, e in W6 i conteggi tornavano esatti.
  > - **Scheletri** di `RiskMetricCard` → `bg-lf-neutral`.
  > - **`RiskMetricCard`** è una card di pagina: `text-lf-primary` (regola 3) e `shadow-lf-shadow-card` (regola 9).
  > - **`KpiSection`**: la catena `valueColor`@354 (`font-bold text-gray-800 dark:text-gray-100`) → `font-bold
  >   text-lf-primary`.
  >
  > **Restano legacy come categorie** (coordinatore, 12:07, scelta (a), regola 11 dello skill), 4 classi in
  > `KpiSection`:
  > - le barre @405 «valore contabile» (`bg-blue-500`) e @417 «liquidità» (`bg-emerald-500`) sono colori d'identità di
  >   due misure, non segni né stati;
  > - un ruolo di stato o di controllo non si usa per il suo colore;
  > - l'elemento della barra prende solo `barColor`, quindi non resta misto. In DV-7, con una riga per la designer.
  >
  > **In più (coordinatore, 12:1x):** i due campi di `ChartAestheticsSection`:217 e 233, migrati dal lotto input di T,
  > avevano un segnaposto senza ruolo. Ora hanno `placeholder:text-lf-placeholder`, perché `app.css` colora i campi
  > nativi solo se non hanno classi `-lf-`.
  > - Il controllo del coordinatore (`native_field_check.py --all`) non trova più nulla nella mia area.
  > - Nel resto dell'app restano 2 casi, di T: `ui/input/TagInput.svelte`:214 e `ui/select/TreeSelect.svelte`:357.
  >
  > - Prettier pulito, compilatore 5 file 0 avvisi, regola 4 a 0 casi, `dark:` senza metà chiara a 0, `git diff --check`
  >   pulito.
  > - `--update`: m1 6.853 → 6.799 (−54 = 52 + 2), m2 54 invariato. I tre componenti escono, `KpiSection` passa da 6 a
  >   4; poi `--check` pulito.
- [x] ✅ (16/10/2026) Ingresso di W6 nel target: `adbc2a4b7` (coordinatore, 14:21). La riparazione è `b52575a3e`, la base
  merge `f0bcf550e`, col baseline risolto. Il target scende da 5.740 a 4.290 classi m1.
- [x] ✅ (16/10/2026) TC-15 in `ChartSignalsSection` (coordinatore, 14:21, su segnalazione di T): il testo attenuato
  sulle righe selezionate sta sotto 4,5:1. Proposta seguita: sulla riga selezionata il testo attenuato passa a
  `secondary`, e `link` non va mai sopra un `panel`. Le regole arriveranno con lo skill aggiornato dal lotto del gate di
  T, non ancora entrato.
  > **Note implementazione** (16/10, 14:22–14:30), sulla base `f0bcf550e`.
  >
  > **Misure** (carta, pannello e `selected` del selettore sopra la card, chiaro/scuro):
  >
  > | Testo | card | panel = hover | selected/card | selected/panel |
  > |---|---|---|---|---|
  > | `muted` | 5,20 / 4,99 | 4,52 / 4,54 | **4,38 / 4,25** | 3,84 / 3,84 |
  > | `secondary` | 7,48 / 7,08 | 6,51 / 6,45 | 6,30 / 6,03 | 5,53 / 5,45 |
  > | `link` | 6,17 / 5,32 | 5,36 / 4,84 | 5,19 / 4,53 | 4,56 / **4,09** |
  >
  > - `SearchSelect` colora la riga evidenziata `bg-lf-selected`. `TreeSelect` colora `bg-lf-selected` la riga attiva
  >   e anche quella sotto il puntatore.
  >
  > **Fatto, solo classi:**
  > - `ChartSignalsSection`, i 4 bottoni icona (sincronizza e dettaglio, della coppia di cambi e dell'asset):
  >   `hover:bg-lf-hover hover:text-lf-link` → `hover:text-lf-primary`, come i bottoni «chiudi» di `PlannerDialog` e
  >   `L4WhatIf`. `hover` ha il valore di `panel`, quindi `link` ci stava sopra.
  > - `ChartSignalsSection`, l'interruttore «inverti la coppia»: acceso resta `text-lf-link`, ma senza fondo al
  >   passaggio, quindi sulla card. L'hover di fondo c'è solo da spento: una sola ternaria (regola 4).
  > - `ChartSignalsSection`:704, l'icona di ripiego nelle righe dell'elenco degli asset (`item`): `muted` → `secondary`.
  >   Il campo chiuso (`selectedItem`, :717) resta `muted`, perché sta su `field`.
  > - **In più, la stessa regola nella stessa sezione:** i due sottotitoli di `SignalOptionContent`, cioè le righe dei
  >   tre selettori di indicatori di `ChartSignalsSection` (`SignalTreeSelect`): `muted` → `secondary`. Era il vero
  >   testo attenuato su `selected`, a 11 e 10 px.
  > - Nella mia area non ci sono altri `muted` o `link` dentro le opzioni dei selettori (ricerca sugli `{#snippet}`).
  >
  > **Prove:**
  > - `ChartSignalsSection.test.ts` 21/21, `SignalTreeSelect.test.ts` 28/28, `htmlSink` 7/7, `themeRoles` 52/52;
  > - Prettier, compilatore, regola 4 e `--check` puliti;
  > - nessun test asserisce queste classi.
  >
  > **⚠️ Fuori pista: C4 rosso sul target.** `themeTokens.gate.test.ts` fa 18/19: `bg-white/90` non ha più usi, né
  > sul mio HEAD né su `dev_release2`, ma `app.css`:254–257 ne tiene ancora la regola scura.
  > - Gli ultimi usi li hanno tolti W5-charts, W6-c, W6-b e IM (`b5abcbdaa`); la merge li ha messi insieme.
  > - `--check` non vede C4, e il mio slot era verde su `9da2e5da9`, perché lì IM non c'era ancora.
  > - Segnalato al coordinatore alle 14:31, con la proposta di togliere il blocco nel checkpoint di TC-15.
  > - **Rimedio** (coordinatore, 14:32: subito, separato da TC-15): ho tolto da `app.css` solo il blocco morto, cioè il
  >   commento «Dark mode: Cards and modals» e la regola `html.dark .bg-white\/90`.
  >   - Poi `themeTokens.gate.test.ts` 19/19 e `themeRoles` 52/52, col carico a 48; `--check`, Prettier e
  >     `git diff --check` puliti.
  >   - Il coordinatore lo committa da solo e lo fa entrare subito, prima di TC-15.
  >   - Da allora agli ingressi lancia anche il file Vitest del gate, non solo `--check`.
- [x] ✅ (16/10/2026) G-18: un elemento misto in `BackendTimingBar`, visto a runtime dalla prima galleria completa
  (`designer-16b`, 2.862 scatti; coordinatore, 17:54). Entra insieme a TC-15 (`a6c79a8f3`) dopo una prova breve.
  > **Note implementazione** (16/10, 17:55–18:00), sulla base `a6c79a8f3`.
  > - **Il caso:** il segmento del timing (`pac-planner-timing-segment`) aveva il separatore legacy (`border-r
  >   border-white … dark:border-gray-800`) e, solo per il tratto «non attribuito», il ruolo `bg-lf-neutral`. La
  >   classe si compone a runtime (`{segment.colour}`), quindi il gate statico non la vede. Si vedeva in 4 scatti del
  >   PAC, 40 varianti.
  > - **⚠️ Fuori pista, errore mio di W5-PAC:** il convertitore aveva portato il colore «non attribuito» (`bg-gray-300
  >   dark:bg-gray-600`, una stringa a sé) su `bg-lf-neutral`, e aveva lasciato legacy il separatore («i segmenti
  >   hanno un colore di fase»). Non avevo guardato i valori che entrano nell'elemento a runtime.
  > - **Perché non `border-lf-card` sul segmento,** come proponeva il coordinatore: i 7 segmenti delle fasi, ancora
  >   legacy perché categorie (punti 2.1 e 2.5), sarebbero diventati misti al contrario.
  > - **Fatto:** il separatore passa al contenitore della barra, `divide-x divide-lf-card`, cioè una riga di 1 px fra
  >   un segmento e l'altro nel colore della card su cui sta la sezione. Il segmento porta solo `h-full
  >   transition-opacity {segment.colour}`.
  >   - La geometria non cambia: `divide-x` mette il bordo destro dentro ogni figlio tranne l'ultimo, come faceva
  >     `border-r … last:border-r-0`.
  >   - In scuro il separatore passa da `#1f2937` al colore della card (`#151b19`).
  >   - Un commento nel markup spiega perché il separatore sta sul contenitore.
  > - **Controllo G3 sulle stringhe composte,** con le regex del gate: contenitore, 8 segmenti e 8 quadratini della
  >   legenda, 17 stringhe, 0 miste. Nel resto della mia area ho riguardato gli elementi rimasti legacy (le barre
  >   «dopo il piano», le tracce, la legenda del rischio, le barre dei KPI): la parte fissa della classe non ha colori,
  >   quindi nessuno si mescola a runtime.
  > - **`app.css`:** nessuna regola del rimappaggio scuro su `border-white` o `border-gray-800`, quindi C4 non cambia.
  > - Nessun test legge i segmenti, né unit né E2E.
  > - Prettier, compilatore (0 avvisi), regola 4 a 0, `git diff --check` puliti.
  > - `--update`: m1 4.290 → 4.288; `BackendTimingBar` da 16 a 14, restano solo le categorie delle fasi.
  > - **Vitest** (carico 49,7): `themeRoles` 52/52, `themeTokens` 19/19 (C4 compreso), `ChartSignalsSection` 21/21,
  >   `SignalTreeSelect` 28/28 (le righe di `SignalOptionContent`, TC-15), `scanColors` 67/67.
  > - Commit `7f918f075` del coordinatore (18:04). Base merge `1a1dadba2` (con `ce5954329`), poi `baac53f99` (con
  >   `c179a5144`, il lotto 9 di AF) e `ec3d54ca3` (con `5eaf67ff1`, C-97a della 1.3 e i docs di AF), tutte pulite.
  >   Su `ec3d54ca3` i gate del coordinatore danno 119/119.
  > - **Slot breve** (via del coordinatore alle 18:36), su `ec3d54ca3`, corsia 6156 e `/tmp/librefolio-r2-dv`, dalle
  >   18:37:11 alle 18:42:22, carico da 20 a 92. Script e log in `files/w6-g18-slot/` della sessione.
  >
  >   | Passo | Esito | Tempo |
  >   |---|---|---|
  >   | `api sync` | verde, 0 file tracciati cambiati | 15 s |
  >   | `ChartSignalsSection.test.ts` | 21/21 | 18 s |
  >   | `SignalTreeSelect.test.ts` | 28/28: le righe di `SignalOptionContent` (TC-15) sulla regola centrale di T per le select | 21 s |
  >   | `TreeSelect.test.ts` | 28/28 | 20 s |
  >   | `htmlSink.gate.test.ts` | 7/7: ha un'eccezione su `SignalOptionContent` | 6 s |
  >   | E2E `front-utility pac-allocator-real`, 1 worker | 1 passed, nessun tentativo ripetuto | 231 s: il build della base nuova, il popolamento, il test in 6,8 s |
  >
  >   - `SignalOptionContent` non ha un test suo; lo coprono i due test delle select.
  >   - Alla fine la porta 6156 è libera e l'HEAD è `ec3d54ca3`.
- [x] ✅ (16/10/2026) W6-e, micro-lotto: le ultime 5 classi dell'area dentro stringhe HTML, cioè le tracce e il
  riempimento delle barre di `DistributionDialog`:102 e `TargetsStep`:63 (coordinatore, 18:44). Base `986c26a0b`,
  stesso albero del target `81bc305b9`.
  > **Note implementazione** (16/10, 18:44–19:00).
  > - **Analisi** (18:47): la traccia di `DistributionDialog` va su `bg-lf-neutral` 1:1. Quella di `TargetsStep` no:
  >   il riempimento «sconosciuto» di `STATUS_TONES.pacTargetBar` era `bg-lf-neutral`, ΔE00 0 dalla traccia. Il
  >   commento di T in `toneClasses.ts` lo prevedeva.
  > - **Decisione del coordinatore** (dopo la conferma della 1.3 che i due file erano liberi, e il controllo dei 31
  >   rami locali): la (a), tutta mia.
  >   - `pacTargetBar.unknown` → **`bg-lf-secondary`**, il colore che l'obiettivo ha già nel risultato (`ResultCell`:78,
  >     legenda di `AssetTable`:148), lo stesso neutro «ideale» di TD-1.
  >   - Le due tracce su `bg-lf-neutral`.
  >   - È una scelta provvisoria: il coordinatore la porta alla designer, punto 27 della raccolta.
  > - **⚠️ Fuori pista, errore mio dell'analisi:** avevo dato solo il ΔE00 e il contrasto sulla card, non quello del
  >   riempimento sulla traccia. Il coordinatore aveva scelto `bg-lf-input`, che sulla traccia nuova fa 2,69/2,73:1,
  >   sotto il 3:1 non testuale. L'ho misurato prima di toccare i file e il coordinatore è passato a `secondary`.
  > - **Fatto:**
  >   - `TargetsStep`:63, la traccia `bg-gray-100 dark:bg-slate-700` → `bg-lf-neutral`. Il riempimento era già
  >     interpolato (`${escapeHtml(BAR_CLASS[totalState])}`).
  >   - `DistributionDialog`: due costanti, `TRACK` (`h-3 overflow-hidden rounded-full bg-lf-neutral`) e `FILL`
  >     (`h-full rounded-full bg-libre-green`), interpolate nel template. Il gate legge ogni stringa di script per
  >     intero (G3), quindi un solo template con la traccia sui ruoli e il riempimento legacy sarebbe misto. Il markup
  >     a runtime resta identico.
  >   - Il riempimento `bg-libre-green` resta legacy: è il peso attuale di ogni asset, un colore di dato (DV-7).
  >   - **Fuori area, dichiarato:** `lib/theme/toneClasses.ts` è di T. Cambia solo `pacTargetBar.unknown` col suo
  >     commento; `pacTargetBar` lo usa solo `TargetsStep`.
  > - **Misure a mano** (`files/dv_w6e_measure*.py` della sessione, col risolutore del gate). Il gate C3 copre i
  >   riempimenti sulle superfici (`text-secondary` a 4,5, gli stati a 4,5), non sulla traccia `neutral`:
  >
  >   | Sulla traccia `neutral` | Chiaro | Scuro |
  >   |---|---|---|
  >   | `secondary` («sconosciuto») | 5,77:1 | 5,84:1 |
  >   | `success` | 4,02:1 | 7,92:1 |
  >   | `danger` | 4,09:1 | 5,74:1 |
  >   | `warning` | 4,01:1 | 6,70:1 |
  >   | `libre-green` (`DistributionDialog`) | 8,57:1 | 7,50:1 |
  >   | prima: `neutral` sulla traccia legacy | 1,22:1 | 1,39:1 |
  >   | scartato: `input` | 2,69:1 | 2,73:1 |
  >
  >   - ΔE00 di `secondary` dagli stati: success 20,4/21,8, danger 36,9/34,9, warning 32,6/31,5.
  >   - La traccia sulla card: 1,30/1,21:1, ΔE00 7,2/5,6. Prima, la traccia legacy: 1,06/1,69:1, ΔE00 2,1/17,9. In
  >     chiaro si vede di più, in scuro di meno: come le altre tracce su `bg-lf-neutral`.
  > - **Controllo G3 sulle stringhe composte a runtime,** con le regex del gate: 7 stringhe (2 tracce, il riempimento
  >   di `DistributionDialog`, i 4 riempimenti di `TargetsStep`), 0 miste.
  > - Nessun test legge queste barre: niente Vitest dei due componenti. `text.test.ts` legge il sorgente di
  >   `DistributionDialog` solo per i testi d'aiuto. L'E2E `pac-allocator-real` non asserisce classi. Nessuna pagina
  >   della documentazione descrive i colori delle barre.
  > - **Prove leggere** (`files/dv_w6e_light.sh` della sessione, log in `files/w6e-light/`, 18:55, carico
  >   25–31):
  >   - Prettier, compilatore (0 avvisi), regola 4 (0), dark-only (0), campi nativi (0 su 412 file), `git diff
  >     --check` puliti.
  >   - `--update`: m1 934 → 930. `DistributionDialog` da 3 a 1, resta solo `FILL`; `TargetsStep` da 2 a 0.
  >     `--check` pulito.
  >   - Vitest: `themeRoles` 80/80, `themeTokens` 21/21 (C3 e C4), `themeComponentTokens` 18/18, `htmlInterpolation`
  >     26/26, `htmlSink` 7/7, `text` 95/95.
  > - Restano, al via del coordinatore: l'E2E `front-utility pac-allocator-real` e lo scatto di galleria
  >   `tools/pac-step-targets`, se G ha la corsia libera.
  > - Commit `63880bc8b` del coordinatore (18:58); la punta è ferma a `81bc305b9` e la simulazione dell'ingresso è
  >   pulita. Lo scatto `tools/pac-step-targets` si salta: entra nella prossima galleria completa, quella del giro
  >   della designer.
  > - **Slot breve** (via del coordinatore alle 18:58), su `63880bc8b`, corsia 6156 e `/tmp/librefolio-r2-dv`, dalle
  >   18:59:35 alle 19:08:56, carico da 62 a 91 per le altre sessioni. Script e log in `files/w6e-slot/` della
  >   sessione.
  >
  >   | Passo | Esito | Tempo |
  >   |---|---|---|
  >   | `api sync` | verde, 0 file tracciati cambiati | 29 s |
  >   | E2E `front-utility pac-allocator-real`, 1 worker | 1 passed, nessun tentativo ripetuto | 532 s: build di frontend e documentazione 411 s (la base aveva i docs di AF), il popolamento, il test in 11,5 s |
  >
  >   - A fine slot la porta 6156 è libera, l'HEAD è `63880bc8b` e il worktree non ha file tracciati cambiati.
- [x] ✅ (16/10/2026) W6-d: `PositionsPanel` 46 e `ExposureTable` 2, dalla versione di Y dopo il suo ingresso (W7 nel
  target `0c79932a7`, via del coordinatore alle 19:58), più `aria-pressed` sui 4 bottoni di `PositionsPanel`.
  > **Note implementazione** (16/10, 19:58–20:20), sulla base `0c79932a7`: la punta, per fast-forward, con dentro
  > anche MF wave 1b.
  > - **Analisi** (20:03): tutto 1:1, niente resta legacy. La mappa segue le ricette della Dashboard (`GrowthChart` di
  >   W6-b; `AllocationPanel` e `KpiCard` di T):
  >   - la card: `bg-lf-card text-lf-primary … border-lf-subtle shadow-sm shadow-lf-shadow-card`; il titolo
  >     `text-lf-secondary`; le cornici dei due gruppi segmentati `border-lf-subtle`;
  >   - Holdings/Performance: attivo `bg-lf-checked text-lf-on-checked` (D-T16), come `GrowthChart`; inattivo
  >     `text-lf-muted hover:bg-lf-hover`, trasparente sulla card come prima;
  >   - Tabella/Mappa, il selezionato grigio: `bg-lf-neutral text-lf-secondary`, come `WacPreviewSection` (stesso
  >     originale). Il convertitore proponeva `bg-lf-panel`, ma `panel` = `hover`: l'inattivo sotto il puntatore
  >     sarebbe uguale al selezionato. Con `neutral` restano distinti, ΔE00 3,4/2,5 (prima 1,3 in chiaro, 0 in scuro).
  >     Le icone: `secondary` su `neutral` 5,77/5,84:1, `muted` sulla card 5,20/4,99:1;
  >   - «Vedi tutte»: `text-lf-link`; gli scheletri: `bg-lf-neutral`, come dice lo skill (il convertitore diceva
  >     `panel`); i due vuoti: `text-lf-muted`;
  >   - `ExposureTable`:218, il nome dell'asset nella cella HTML: `text-lf-secondary`, come la cella gemella di
  >     `ContributionTable`. Il template resta senza classi legacy.
  > - **`aria-pressed` sui 4 bottoni** (sì del coordinatore, 20:00), come i fratelli `GrowthChart` e `AllocationPanel`:
  >   il segnale di stato che i test leggono al posto del colore (regola 10). Chiude Y-17, che il coordinatore segnala
  >   alla 1.3.
  > - **⚠️ Fuori pista: `AllocationPanel` e TD-3.** Nell'analisi avevo segnalato che il selezionato dei suoi 3 gruppi
  >   segmentati, `bg-lf-action`, in scuro fa 1,95:1 sulla card, contro i 5,32:1 di `checked`. Il coordinatore aveva
  >   detto sì al cambio, poi l'ha ritirato quando gli ho segnalato TD-3 nel backlog (TC-10, sezione di T): lì T ha
  >   seguito un'indicazione esplicita della designer (giro 2), che vale più della regola generale D-T16. Le 3 righe
  >   sono tornate come nel target: **`AllocationPanel` invariato, TD-3.** La misura va alla designer, punto 30 della
  >   raccolta.
  > - **⚠️ Fuori pista: C4 rosso.** Gli ultimi 4 usi di `hover:bg-gray-50` erano nei bottoni di `PositionsPanel`:
  >   `themeTokens` dava 20/21. Col sì del coordinatore (20:10), come AF nel lotto 9, ho tolto da `app.css` (di T) le
  >   righe 255–259: il commento «Dark mode: Hover states», la regola `html.dark .hover\:bg-gray-50:hover` e la riga
  >   vuota. `--theme-bg-hover` resta usata alla riga 229.
  > - Prettier ha riformattato i due bottoni la cui riga passava i 300 caratteri.
  > - **Test:** nessuno legge questi colori. `ExposureTable.test.ts` asserisce `row-analyzed`, una classe di stato;
  >   `PositionsPanel` non ha test; le 10 spec E2E che lo usano cliccano i 4 bottoni senza leggerne lo stato.
  > - **Prove leggere** (`files/dv_w6d_light.sh` della sessione, log in `files/w6d-light/`, 20:05–20:20, carico
  >   39–46):
  >   - compilatore (0 avvisi), regola 4 (0), dark-only (0), campi nativi (0 su 412 file), Prettier e `git diff
  >     --check` puliti;
  >   - `--update`: m1 930 → 882; `PositionsPanel` ed `ExposureTable` escono dal baseline. `--check` pulito;
  >   - Vitest: `themeRoles` 80/80, `themeTokens` 21/21 dopo il rimedio di C4, `themeComponentTokens` 18/18,
  >     `htmlInterpolation` 26/26, `htmlSink` 7/7, `ExposureTable` 17/17, `AllocationPanel` 3/3,
  >     `AllocationPanel.negativeCash` 10/10.
  > - Resta lo slot, al via del coordinatore dopo BK: l'E2E `front-portfolio dashboard`, che guida le 4 viste di
  >   `PositionsPanel`. Gli scatti di galleria aspettano la prossima galleria completa.
  > - Commit `45f582eeb` del coordinatore (20:14). Base merge `8f1f27a44` con la punta `624fa5609` (A-25 della 1.3:
  >   `ProfileTab`, `emailCase`), pulita; gate del coordinatore 119/119.
  > - **Slot** (via del coordinatore alle 20:14, in parallelo a BK), su `8f1f27a44`, corsia 6156 e
  >   `/tmp/librefolio-r2-dv`, dalle 20:15:17 alle 20:23:08, carico da 51 a 30. Script e log in `files/w6d-slot/`
  >   della sessione.
  >
  >   | Passo | Esito | Tempo |
  >   |---|---|---|
  >   | `api sync` | verde, 0 file tracciati cambiati | 24 s |
  >   | E2E `front-portfolio dashboard`, 1 worker | 27 passed, nessun tentativo ripetuto | 447 s: build di frontend e documentazione 243 s, il popolamento, i 27 test in 2,4 min |
  >
  >   - La spec guida le 4 viste di `PositionsPanel` e quelle di `AllocationPanel` («adesso», «storico» e le schede).
  >   - A fine slot la porta 6156 è libera, l'HEAD è `8f1f27a44` e il worktree non ha file tracciati cambiati.

### Inventario m1/m2 dei file dei grafici, per il lotto dopo Y3, Y4b e Y5 (16/10/2026, sola lettura)

**Richiesta del coordinatore** (16/10 alle 02:06): per ciascun file dei grafici, cosa resta in m1 (classi colore
legacy) e in m2 (letterali), con il conteggio, la destinazione (un ruolo o una categoria) e se dipende da una risposta
della designer (grafici giro 3, punti 2.1–2.9). Nessun codice toccato.

**Base:** `20558ead5`, uguale al target `57802d827`. I percorsi sono quelli di oggi: Y3, Y4b e Y5 spostano dashboard,
rischio e broker. Per uno spostamento puro il baseline non va toccato, perché il gate accoppia i file per nome.

**Metodo:** le regole stesse del gate (`theme-roles.mjs`: `listSources`, `codeOf`, `LEGACY_CLASS_RE`,
`measureSource`), in uno script in sola lettura.
- Le classi neutre (`slate`, `gray`, `zinc`, `neutral`, `stone`, `white`, `black`) e quelle del marchio (`libre-*`,
  `primary-*`, `surface-*`) vanno ai ruoli diretti della skill `theme-roles`.
- Le classi colorate le ho classificate a mano, riga per riga.

**Totale: 103 file, m1 2628, m2 0.** I letterali stanno già nelle tabelle di `lib/theme/`.
- **Neutri, 2081:** `text-lf-primary`/`secondary`/`muted`, `bg-lf-card`/`panel`/`field`/`hover`/`neutral`,
  `border-lf-subtle`/`input`, `ring-lf-focus`.
- **Marchio, 154:** `bg-lf-action`, `text-lf-link`, `bg-lf-selected`, `bg-lf-checked`.
- **Colorati, 393:**
  - gli stati (warning, danger, info, success) → `lf-<stato>`, `-soft`, `-line`, `-on-soft`, senza dipendenze;
  - i numeri con segno → `text-lf-gain`/`text-lf-loss`, che dipendono dal punto 2.8;
  - le categorie vere sono poche.

**Dipendono dalla designer 9 file, uno di T.**
- **2.8, numeri con segno:** `LotCustodyModal`, `OtherPeriodEffectsTable`, `AssetSetLossComparisonSection`,
  `ReturnHistogram`, e `KpiSection` (TD-2, di T).
- **2.1 e 2.5:** `BackendTimingBar` e `RiskReturnLevel`.
- **Giro dei badge:** `UnifiedLotsTable` e `LotGanttChart`.

Tutto il resto si può convertire già.

**Ordine consigliato del lotto,** per area e dopo gli spostamenti:
1. i file con soli neutri e marchio, che sono il grosso e non chiedono decisioni;
2. gli stati;
3. infine i file che aspettano la designer.

**`lib/components/charts/`**: 14 file, m1 431, di cui neutri 368 e marchio 39; colorati 24. m2 0.

| File | m1 | Neutri / marchio | Colorati | Destinazione dei colorati | Designer |
|---|---:|---:|---:|---|---|
| `ChartSignalsSection.svelte` | 95 | 73 / 7 | 15 | banner ambra, icone d'errore e d'avviso, elimina → ruoli warning e danger | — |
| `MeasurePanel.svelte` | 34 | 26 / 0 | 8 | nota ambra → warning-soft; elimina → `hover:text-lf-danger` | — |
| `SignalAssetParamControl.svelte` | 1 | 0 / 0 | 1 | errore → `text-lf-danger` | — |

Solo neutri e marchio, quindi ruoli diretti senza dipendenze: `ChartAestheticsSection.svelte` 78, `ChartSettingsModal.svelte` 47, `SignalStyleEditor.svelte` 42, `ChartToolbar.svelte` 38, `PriceChartFull.svelte` 36, `SignalParamControl.svelte` 24, `SignalVisualLegend.svelte` 16, `ResolutionBadge.svelte` 6, `SignalOptionContent.svelte` 6, `GeographyMap.svelte` 4, `ScatterChart.svelte` 4.

**`lib/components/risk/`**: 30 file, m1 763, di cui neutri 596 e marchio 32; colorati 135. m2 0.

| File | m1 | Neutri / marchio | Colorati | Destinazione dei colorati | Designer |
|---|---:|---:|---:|---|---|
| `RiskAnalysisPanel.svelte` | 192 | 177 / 5 | 10 | riquadro d'errore → ruoli danger; note ambra → warning | — |
| `AssetSetRiskPanel.svelte` | 71 | 48 / 3 | 20 | avvisi ambra ed errore rosso → ruoli warning e danger | — |
| `levels/l4/L4Simulation.svelte` | 45 | 34 / 5 | 6 | avviso di deriva → warning-soft | — |
| `RiskResultFrame.svelte` | 41 | 28 / 1 | 12 | badge e riquadro ambra → warning-soft | — |
| `levels/RiskLevelSection.svelte` | 29 | 23 / 0 | 6 | avviso → warning-soft | — |
| `levels/l4/L4Replay.svelte` | 29 | 9 / 4 | 16 | note ambra → warning-soft; bottone bordato → ruoli di azione | — |
| `levels/L4WhatIf.svelte` | 27 | 19 / 2 | 6 | avviso del modello → warning-soft | — |
| `AssetSetLossComparisonSection.svelte` | 26 | 22 / 0 | 4 | `LOSS_CLASS`, le perdite → `text-lf-loss`; errore → danger | 2.8 |
| `levels/l4/L4Shock.svelte` | 25 | 16 / 6 | 3 | chip del preset scelto → `bg-lf-selected`/azione; nota → warning | — |
| `AssetSetRiskReturnSection.svelte` | 22 | 20 / 0 | 2 | errore → `text-lf-danger` | — |
| `levels/RiskPanelHeader.svelte` | 22 | 16 / 0 | 6 | riquadro d'errore → ruoli danger | — |
| `AssetSetCorrelationSection.svelte` | 20 | 18 / 0 | 2 | errore → `text-lf-danger` | — |
| `levels/RiskPartialNotice.svelte` | 20 | 4 / 0 | 16 | varianti info e warning → info-soft e warning-soft | — |
| `levels/SimulationProvenance.svelte` | 20 | 14 / 0 | 6 | avviso di troncamento → warning-soft | — |
| `levels/l1/ReturnHistogram.svelte` | 16 | 10 / 0 | 6 | barra del taglio → warning; barre sotto il taglio → `bg-lf-loss` | 2.8 |
| `RiskReturnLevel.svelte` | 14 | 10 / 0 | 4 | legenda: punto «portafoglio» cielo e rombo «asset» ambra → categorie del grafico rischio/rendimento, coerenti con la serie ECharts | 2.5 |
| `levels/L1HowMuchItHurts.svelte` | 11 | 10 / 0 | 1 | hover del link alla documentazione → `text-lf-link` | — |
| `levels/RiskLevelsPanel.svelte` | 6 | 0 / 0 | 6 | avviso → warning-soft | — |
| `BenchmarkSelect.svelte` | 3 | 0 / 0 | 3 | errore → danger; icona «misurato» → warning | — |

Solo neutri e marchio, quindi ruoli diretti senza dipendenze: `CorrelationHeatmap.svelte` 33, `CorrelationPairsList.svelte` 25, `levels/L2Diversification.svelte` 23, `AssetRiskScenariosView.svelte` 13, `LabAssetPicker.svelte` 8, `levels/l1/UnderwaterChart.svelte` 8, `levels/L3RiskAdjusted.svelte` 4, `levels/l4/TornadoChart.svelte` 4, `AssetChip.svelte` 2, `assetSetTable.ts` 2, `levels/L3Benchmark.svelte` 2.

**`lib/components/brokers/lots/`**: 7 file, m1 545, di cui neutri 399 e marchio 17; colorati 129. m2 0.

| File | m1 | Neutri / marchio | Colorati | Destinazione dei colorati | Designer |
|---|---:|---:|---:|---|---|
| `LotCustodyModal.svelte` | 219 | 173 / 4 | 42 | importi con segno, commissioni e tasse → `text-lf-gain`/`text-lf-loss`; nota ambra → `text-lf-warning`; badge → `bg-lf-success-soft`; hover → `text-lf-link` | 2.8 |
| `UnifiedLotsTable.svelte` | 84 | 30 / 0 | 54 | badge di direzione e custodia del lotto (smeraldo, ambra, viola, cielo, rosso) → categoria «stato del lotto», da allineare a `LOT_STATE_COLORS` | giro dei badge (registro, 19:2x) |
| `LotsAnalysisPanel.svelte` | 42 | 32 / 1 | 9 | errore → ruoli danger; hover → `text-lf-link` | — |
| `LotGanttChart.svelte` | 36 | 32 / 0 | 4 | chip tratteggiata viola, il marcatore «altro» → categoria del marcatore | giro dei badge |
| `LotDataQualityBanner.svelte` | 20 | 0 / 0 | 20 | banner warning e info → `bg-lf-warning-soft`/`bg-lf-info-soft` con `-line` e `-on-soft` | — |

Solo neutri e marchio, quindi ruoli diretti senza dipendenze: `LotComparisonChart.svelte` 96, `LotWacPriceChart.svelte` 48.

**`lib/components/dashboard/`**: 12 file, m1 308, di cui neutri 274 e marchio 15; colorati 19. m2 0.

| File | m1 | Neutri / marchio | Colorati | Destinazione dei colorati | Designer |
|---|---:|---:|---:|---|---|
| `KpiSection.svelte` | 50 | 46 / 0 | 4 | barre dei KPI blu e smeraldo → TD-2 di T (W3/W5) | 2.8 (di T) |
| `PositionsPanel.svelte` | 46 | 42 / 3 | 1 | link → `text-lf-link` | — |
| `OtherPeriodEffectsTable.svelte` | 28 | 20 / 0 | 8 | badge per segno (smeraldo, rosso) → gain/loss tenui | 2.8 |
| `ContributionTable.svelte` | 14 | 8 / 2 | 4 | badge «aperta» smeraldo → `bg-lf-success-soft text-lf-success-on-soft` | — |
| `YieldOnCostCell.svelte` | 8 | 6 / 0 | 2 | icona ambra → `text-lf-warning` | — |

Solo neutri e marchio, quindi ruoli diretti senza dipendenze: `GrowthChart.svelte` 86, `AllocationPanel.svelte` 42, `KpiCard.svelte` 14, `ExposureTreemap.svelte` 10, `AllocationHistoryChart.svelte` 4, `PerformanceChart.svelte` 4, `ExposureTable.svelte` 2.

**`lib/features/tools/pac-allocator/`**: 40 file, m1 581, di cui neutri 444 e marchio 51; colorati 86. m2 0.

| File | m1 | Neutri / marchio | Colorati | Destinazione dei colorati | Designer |
|---|---:|---:|---:|---|---|
| `planner/ui.ts` | 118 | 78 / 21 | 19 | bottoni: primario → `bg-lf-action text-lf-on-action`; pericolo bordato → `border-lf-danger-line text-lf-danger`; avviso pieno → `bg-lf-warning text-lf-on-status` | — |
| `planner/result/BackendTimingBar.svelte` | 32 | 20 / 0 | 12 | 6 fasi colorate (cielo, viola, smeraldo, ambra, rosa, verde acqua) → sequenza di categoria (`sequenceColor`) | 2.1, 2.5 |
| `planner/steps/BrokersStep.svelte` | 32 | 30 / 0 | 2 | problema → `text-lf-danger` | — |
| `planner/steps/BrokerEditor.svelte` | 24 | 12 / 4 | 8 | avvisi → warning-soft | — |
| `planner/steps/AssetsStep.svelte` | 22 | 18 / 0 | 4 | note senza prezzo → `text-lf-warning-on-soft` | — |
| `planner/shell/StepNav.svelte` | 20 | 11 / 3 | 6 | icone → warning e success; passo corrente → `bg-lf-selected` | — |
| `planner/shared/IssueList.svelte` | 18 | 12 / 0 | 6 | icone errore, avviso, info → danger, warning, info | — |
| `planner/shared/ReviewCell.svelte` | 18 | 12 / 0 | 6 | icone e data vecchia → warning e success | — |
| `planner/steps/LiquidityStep.svelte` | 16 | 14 / 0 | 2 | liquidità oltre il disponibile → `text-lf-danger` | — |
| `planner/steps/RoutingStep.svelte` | 16 | 8 / 0 | 8 | problema e avviso → danger e warning-soft | — |
| `planner/steps/FxStep.svelte` | 12 | 8 / 0 | 4 | cambio mancante → `text-lf-warning-on-soft` | — |
| `planner/result/FailurePanel.svelte` | 10 | 6 / 0 | 4 | icone d'esito → warning e danger | — |
| `planner/steps/TargetsStep.svelte` | 9 | 6 / 0 | 3 | ✅, eccesso e mancanza → success, danger, warning | — |
| `planner/shell/SummaryPanel.svelte` | 8 | 6 / 0 | 2 | valore da controllare → `text-lf-warning` | — |

Solo neutri e marchio, quindi ruoli diretti senza dipendenze: `planner/result/OrderDetail.svelte` 28, `planner/steps/StrategyStep.svelte` 19, `planner/steps/DistributionDialog.svelte` 18, `planner/result/KpiCards.svelte` 16, `planner/steps/BrokerScopeCopyDialog.svelte` 16, `planner/shared/PlannerDialog.svelte` 15, `planner/steps/OwnedAssetsDialog.svelte` 15, `planner/result/ProofPanel.svelte` 14, `planner/result/OperationalPlan.svelte` 12, `planner/shared/AutoManualToggle.svelte` 11, `planner/PacPlannerTool.svelte` 8, `planner/shared/OwnerBrokerPicker.svelte` 8, `planner/result/ResultCell.svelte` 7, `planner/result/AssetTable.svelte` 5, `planner/result/ExposureMaps.svelte` 4, `planner/result/ExposureSection.svelte` 4, `planner/result/ResultView.svelte` 4, `planner/result/ToolErrorPanel.svelte` 4, `planner/steps/AssetEditor.svelte` 4, `planner/steps/ReviewStep.svelte` 3, `planner/result/OutcomeHeader.svelte` 2, `planner/shared/ConflictDialog.svelte` 2, `planner/shared/MarqueeName.svelte` 2, `planner/shared/columnHelp.ts` 2, `planner/steps/ScenarioStep.svelte` 2, `planner/result/ResultSection.svelte` 1.

| Passo | Contenuto | File | Conflitti |
|---|---|---|---|
| S2 | Fondamenta in `lib/theme` e gate | `lib/theme/chartCategories.ts`, `chartShades.ts`, `roleColors.ts` (nuovi), `themeMode.ts`, `colorAlpha.ts` | nessuno |
| S3 | Torta, anelli, gerarchia; emoji dei settori dallo store | `allocationHierarchy.ts`, `allocationRings.ts`, `AllocationPieChart.svelte`, `chartPalettes.ts`, `sectorStore.ts` | Y9 (K-13) |
| S4 | Storico per tipo, settore e paese | `AllocationHistoryChart.svelte` | Y10 (627/707/779/806), Y9 |
| S5 | Scale delle mappe | `chartPalettes.ts`, solo valori | nessuno |
| S6 | Semi-ciambella (GR5.2, R-7) | `SemiDonutChart.svelte`, `chartTheme.ts` | Y9 |
| S7 | Correlazione sui ruoli | `CorrelationHeatmap.svelte`, `toneClasses.ts`, `chartTheme.ts` | Y9 (C-34 riga 330), T (W3) |
| S8 | Linee dei broker | `chartPalettes.ts`, solo valori | nessuno |
| S9 | Indicatori per tema (via a parte) | `lib/charts/signals/*`, UI dei segnali, `chartSettingsStore`, pagina asset riga 916 | Y4, Y8, X |
| S10 | Verifiche e gallery (strumenti di G, slot pesante), checkpoint | — | — |
| TD-1 + TD-1b | Barre «Esposizioni — ideale vs reale» del PAC; linee dei broker lette al disegno, con C4 | `ExposureBars.svelte`, `exposureTooltip.ts`, `exposureBarColours.ts` (nuovo), `chartTheme.ts`, `roleColors.ts`, `chartCategories.ts` (`lookupKey`), `chartPalettes.ts`, `growthChartSeries.ts`, `GrowthChart.svelte` | J (PAC, non attivo), Y (Y3 sposta i file della crescita dopo le 01:30), T (B4 su `ChartRole`), G (G-16, lo scatto) |

**Gallery che cambia:**
- `dashboard/allocation-{type,sector,geo}-{now,history}`;
- `brokers/detail`, `brokers/sharing-modal`, `info-tab`;
- `assets/detail-classification`;
- `tools/pac-result`;
- `risk/lab-correlation`, `dashboard/risk-diversification`;
- con S9, gli scatti dei segnali di asset e cambi.

### B4 — I neutri dei grafici sui ruoli ✅ (notte 16→17/10/2026)

Mandato del coordinatore (22:18), valgono D-T27 e D-T28; base `07700355f`. Fonte: l'inventario in sola lettura di L
(`L-designerLab/audit-colori-fuori-metrica.md`, sul ramo di L): `lib/theme/chartTheme.ts` tiene 277 letterali della
vecchia palette slate, letti da 33 file, e il ratchet m2 non li conta perché esclude `lib/theme/**`. In più ECharts usa
i suoi predefiniti in 5 punti. Perimetro: i neutri (assi, linee e griglie, etichette, cornici e fondi dei tooltip,
`axisPointer`), sui ruoli letti a runtime col ponte `roleColors.ts`; le serie e le categorie restano per la designer.

**Analisi** (22:18–23:00, sola lettura; misure in `files/dv_b4_measure.py` della sessione, col risolutore del gate).
- **Il piano di T per B4 è superato.** L'analisi di T del 14/10 voleva ruoli nuovi `--lf-chart-*` sulla palette della
  designer; il mandato chiede invece i ruoli che l'interfaccia dà alle stesse cose. Il registro conta in B4 anche
  guadagno e perdita: qui restano fuori, salvo una decisione (domanda 1).
- **Come si ridisegnano oggi:** 17 grafici ridisegnano al cambio di tema (`onThemeClassChange`); solo 6 sentono anche
  il Lab (`onChartColorsChange`, C4): `AllocationPieChart`, `AllocationHistoryChart`, `GrowthChart`, `SemiDonutChart`,
  `CorrelationHeatmap`, `ExposureBars`. Gli altri 11 vedrebbero una modifica del Lab ai ruoli solo al prossimo cambio
  di tema (domanda 2). Nessun grafico vive oggi in un sottoalbero a tema forzato.
- **Regola della mappa,** voce per voce:
  - testo, per tono legacy come la migrazione delle classi (W6): 800 e oltre `primary`, 600–700 `secondary`, 300–500
    `muted`;
  - il riquadro del tooltip è un popover (skill, regola 9): `card`, bordo `raised`, testo `primary` e `muted`. Non il
    tooltip invertito di Q10, che è quello piccolo dell'interfaccia;
  - le linee prendono, fra `subtle`, `input` e `muted`, il ruolo col contrasto più vicino al loro di oggi: la struttura
    (assi, griglie, separatori, cornici) va su `subtle`; le linee di riferimento, i puntatori e le linee guida su
    `input`; la linea dello zero di Performance su `muted`;
  - i varchi e gli anelli «nel colore della card» su `card`; aloni e fondi delle etichette su `card` con l'alfa di
    oggi; la banda al passaggio e l'ombra del puntatore su `muted` con l'alfa di oggi (il puntatore di ECharts sta a
    `z: 50`, sopra le barre, quindi resta traslucido);
  - il testo su un pieno di stato (i bottoni di stato del Gantt) su `on-status`.
- **La mappa, per ruolo** (le voci tengono i nomi delle tabelle di oggi):

  | Ruolo | Voci |
  |---|---|
  | `--lf-text-primary` | `tooltip.box.text`; `candlestickBox.text`, `heading`; `allocation.historyAreaLabel`; `semiDonut.label`; `geoMap.label`; `correlation.emphasisBorder`; `performance.zeroValue`, `axisName`; `lots.markerEmphasisRing`; Gantt `selectedSegmentBorder`, `segmentLabel`; Gantt `lineageConnector` al 45/48 % |
  | `--lf-text-secondary` | `riskReturn.axisText`; `allocation.caption`; `correlation.axisLabel`, `tooltipBadge.text`; `performance.axisSection`; `treemap.groupLabel` |
  | `--lf-text-muted` | `priceAxis.label`; `dashboard.text`; `secondaryAxisFallback`; `referenceLevelLabel`; `tooltip.box.muted`; `candlestickBox.muted`; `tooltip.aside`; `performance.axisSecondary`, `zeroLine`; `legendPageIconInactive` al 40 %; `performance.rowHighlight` 16/14 % e `axisPointerShadow` 14/12 %; l'ombra predefinita di `ExposureBars` al 20 % |
  | `--lf-border-subtle` | `priceAxis.line`, `gridLine`; `dashboard.gridLine`; `riskReturn.axis`; `correlation.tooltipDivider`; `performance.sectionSeparator`; `treemap.groupBorder`, `tileBorder` |
  | `--lf-border-raised` | `tooltip.box.border`; `candlestickBox.border` |
  | `--lf-border-input` | `candlestickBox.crosshair`; `price.baseline`; `riskReturn.capitalMarketLine`; `semiDonut.labelLine`; `growth.pnlReference`, `bucketSeparator`; la linea zero del WAC; la linea predefinita del puntatore di storico e crescita |
  | `--lf-surface-card` | `tooltip.box.background`; `price.pendingEditPointRing`; `allocation.sliceBorder`, `historyAreaLabelShadow`; `semiDonut.avatarBorder`, `sliceGap`; `geoMap.border`; `correlation.cellGap`; `lots.markerRing`; con alfa: `semiDonut.labelShadow` 80/60 %, `geoMap.labelBackground` 72/55 %, `correlation.emphasisHalo` 95 %, `treemap.groupLabelBackground` 80 %; il riquadro predefinito dei tooltip di correlazione e rischio/rendimento |
  | `--lf-surface-panel` | `correlation.tooltipBadge.background` |
  | `--lf-surface-neutral` | `semiDonut.available`, cioè una traccia |
  | `--lf-on-status` | Gantt `stateChipText` |

- **Restano,** serie, categorie, stati e segni: `PRICE_SERIES.line`, `pendingEditPoint`, `comparisonMarkerFallback`;
  `CHART_GAIN_LOSS`; i punti di `RISK_RETURN_COLORS`; `ALLOCATION_CHART_COLORS.iconBubble`; `GEO_MAP_COLORS.land` e
  `highlight`; `SIGNAL_COLORS`; `INCOME_EVENT_COLORS`; `GROWTH_SERIES`; le serie e i badge di `PERFORMANCE_COLORS`;
  `TREEMAP_COLORS.noPnl`, `tileLabel`, `tileLabelShadow`; `RISK_OVERLAY_COLORS`; `LOT_STATE_COLORS`; serie, bande ed
  eventi di Gantt, WAC e confronto; `CHART_TOOLTIP_COLORS.staleWarning` e `seriesFallback`.
  - **⚠️ `GEO_MAP_COLORS.land` non va su un ruolo:** su `neutral` i paesi senza peso staranno a ΔE00 4,1/3,7 dal primo
    gradino di `GEO_CHOROPLETH_SCALE` (oggi 7,8/17,9), cioè si confondono col peso più basso. È lo zero della scala
    GR5.1: resta con la scala, per la designer.
- **Effetto misurato** (contrasto sulla card, prima → dopo, chiaro/scuro):
  - in chiaro quasi nulla cambia; in scuro assi e griglie si attenuano, da 1,93 a 1,21:1 (`subtle`, come i divisori
    dell'interfaccia): da rivedere;
  - le linee di riferimento e i puntatori si vedono di più in chiaro, da 2,54 a 3,49:1;
  - le note dei tooltip in chiaro passano da 2,56 a 5,20:1 (oggi sotto AA);
  - i riquadri dei tooltip perdono la tinta slate in scuro; quelli di correlazione e rischio/rendimento non sono più
    bianchi in scuro (il badge dentro va su `panel`/`secondary`, 6,5:1);
  - il testo dei bottoni di stato del Gantt su `on-status` resta come oggi, sotto 4,5:1 sui pieni ambra e cielo (3,07 e
    3,95:1): è un difetto dei pieni di stato legacy, non di questo lotto.
- **Architettura:** `chartNeutrals(dark, scope)` in `chartTheme.ts` legge i ruoli con `chartRoles(dark, scope)`, una
  volta per disegno, sull'elemento del grafico, e restituisce gli stessi gruppi di oggi (`priceAxis`, `dashboard`,
  `tooltip.box`, `semiDonut`…). Ogni lettura passa da `themed(CHART_NEUTRALS.x.y, dark)` a `neutrals.x.y`. Gli helper
  condivisi (`buildTooltipTheme`, `buildGridColors`, `getChartColors`) tengono la firma, più uno `scope` facoltativo.
  - I gate reggono senza modifiche: `chartTheme.test.ts` salta le funzioni; la parità di `roleColors.test.ts` vede le
    chiamate letterali `.color('--lf-…')` di `chartNeutrals`. In `ChartRole` entrano 6 ruoli, coi ripieghi uguali a
    `tokens.css`: `--lf-text-muted`, `--lf-border-subtle`, `--lf-border-raised`, `--lf-border-input`,
    `--lf-surface-neutral`, `--lf-on-status`.
  - Il commento di `themePair.ts` («il giorno che i colori diventano token, cambia questa funzione») va aggiornato.
- **Test:** nessun test unitario né E2E legge i valori dei neutri, salvo due riparazioni per `test-author`:
  - il controllo positivo di `chartTheme.test.ts` nomina `CHART_TOOLTIP_COLORS.box.background` e `.aside`;
  - `chartCoreHelpers.test.ts`:4206 legge `GROWTH_CHART_COLORS.pnlReference`.
  - Nuovo, sempre a `test-author`: un test di `chartNeutrals` (ogni voce è il suo ruolo, nei due temi, letta sullo
    `scope`).
  - Gli altri (`echartsTooltipHelpers`, `AllocationHistoryChart`, `ExposureBars`, i lettori iniettati di
    `CorrelationHeatmap` e `SemiDonutChart`) passano dai ripieghi: da verificare.
- **L:** il motore L3 del Lab (`engine/charts.ts`) rimappa i colori delle opzioni per valore; dopo B4 i neutri portano
  i valori dei ruoli. Va detto a L.

**Passi**
- [x] ✅ (16/10/2026) B4-0, analisi e piano.
  > **Decisioni del coordinatore** (23:05): `staleWarning` → `--lf-warning` nel lotto (fix di contrasto, 2,1:1 in
  > chiaro); guadagno e perdita al lotto con la designer; C4 sugli 11 grafici che non lo sentono; la sezione «Charts»
  > dello skill la aggiorno io, nel lotto (T tocca la regola 5 e la riga 59: hunk diversi); test a `test-author`. La 1.3
  > libera i 25 path; FE2 è sospeso; Y-18 (`candlesLoading` in `GrowthChart`) partirà sopra B4, se il developer lo
  > approva.
- [x] ✅ (16/10/2026) B4-1 `roleColors.ts`, `chartTheme.ts`, `themePair.ts`.
  > **Note implementazione:** `ChartRole` passa da 7 a 14 ruoli, scritti uno per riga; i 7 nuovi (`surface-neutral`,
  > `text-muted`, `border-subtle`, `border-raised`, `border-input`, `on-status`, `warning`) hanno i ripieghi presi dal
  > risolutore del gate. `chartNeutrals(dark, scope)` restituisce i gruppi della tabella del piano; i valori traslucidi
  > passano da `toRgba` (`rgba()`, letto da zrender e dall'HTML dei tooltip). Escono dalle tabelle `CHART_NEUTRALS`,
  > `SEMI_DONUT_COLORS`, `CORRELATION_COLORS`, `GROWTH_CHART_COLORS`, `LOT_CHART_COLORS` e le voci neutre delle altre;
  > `CHART_TOOLTIP_COLORS` tiene solo `candlestickBox.seriesFallback`. `GEO_MAP_COLORS.land` resta, col motivo nel
  > commento. Il commento di testa di `chartTheme.ts` e quello di `themePair.ts` dicono dove sono andati i neutri.
- [x] ✅ (16/10/2026) B4-2 Gli helper condivisi.
  > **Note implementazione:** `buildTooltipTheme`, `buildGridColors` e `getChartColors` leggono `chartNeutrals`, con
  > uno `scope` facoltativo in coda; `buildSecondaryYAxes`, `buildSignalReferencePrimitives`, `buildScatterOption` e la
  > serie di riferimento della crescita leggono il loro gruppo. **`buildStaleTooltipHtml` prende il colore come terzo
  > parametro**, come `buildTooltipHeader(date, textColor)`: un helper puro non legge il tema. Le sue 5 chiamate in
  > `priceChartHelpers.test.ts` vanno aggiornate: terza riparazione per `test-author`.
- [x] ✅ (16/10/2026) B4-3 I componenti, coi 5 predefiniti e C4.
  > **Note implementazione** (22:30–22:50). Le letture meccaniche (`themed(TABELLA.voce, dark)` →
  > `neutrals.gruppo.voce`) le ha riscritte uno script (`files/dv_b4_rewrite.py` della sessione), 114 letture in 15
  > componenti, col conteggio uguale alla tabella dell'analisi. Il `const neutrals = chartNeutrals(dark, contenitore)`
  > l'ho messo a mano, dove il disegno ha il suo tema e il suo elemento:
  > - in testa alla funzione che costruisce l'opzione (`LineChart`, `PriceChartFull`, `CandlestickChart`,
  >   `AllocationPieChart`, `SemiDonutChart`, `GeographyMap`, `AllocationHistoryChart`, `ExposureTreemap`,
  >   `GrowthChart`, le 4 funzioni di `PerformanceChart`, `ExposureMaps` sul riquadro delle due mappe, `ExposureBars`);
  > - come `$derived` del componente dove le letture sono sparse o stanno nel markup (i 3 grafici dei lotti, i bottoni
  >   di stato del Gantt; `CorrelationHeatmap`, accanto ai suoi `roles`), coi grilletti del tema e di C4.
  > - **I 5 predefiniti:** i tooltip di `CorrelationHeatmap` e `ScatterChart` prendono il riquadro comune; le linee
  >   del puntatore di `AllocationHistoryChart` e `GrowthChart` `neutrals.axisPointer.line` (resta tratteggiata, come
  >   il predefinito); l'ombra di `ExposureBars` `neutrals.axisPointer.shadow`.
  > - **C4 sugli 11 grafici:** lo stesso ridisegno del tema dove c'era una funzione di ridisegno; un contatore di
  >   revisione dove il disegno parte da un `$derived` o da un `$effect` (`ScatterChart`, `ExposureMaps`, i lotti).
  > - Gli helper condivisi ricevono lo scope dove il componente lo ha (`buildTooltipTheme`, `buildGridColors`,
  >   `getChartColors`); i grafici dei lotti li chiamano ancora senza, cioè su `<html>`: oggi è lo stesso tema.
  > - **Skill:** le righe di `chartTheme.ts` e `roleColors.ts` nella tabella dei file, e i due punti della sezione
  >   «Charts» sui neutri (fuori area, col sì del coordinatore; T tocca altri hunk dello stesso file).
  > - Controlli: nessun riferimento alle voci tolte nel codice di produzione; ogni file che legge `neutrals` lo
  >   definisce; nessun import rimasto inutile; i 17 componenti compilano senza avvisi.
- [x] ✅ (16/10/2026) B4-4 `test-author`: le tre riparazioni e il test nuovo.
  > **Note implementazione** (22:35–23:00, `test-author`, log in `files/b4-tests/` della sessione).
  > - `chartTheme.test.ts`: il controllo positivo nomina `LOT_WAC_COLORS.markers.buy` e `SIGNAL_COLORS.measure`; il
  >   test delle funzioni saltate copre anche `chartNeutrals`. Un `describe` nuovo con 4 test: ogni neutro legge il suo
  >   ruolo con la sua alfa, nei due temi; la tabella attesa e i neutri coincidono nei due sensi (67 foglie, 11 ruoli);
  >   lo scope arriva al lettore, `null` senza scope; senza lettore i colori sono ben formati e dipendono dal tema.
  >   Prova del rosso: rompendo la tabella attesa (ruolo sbagliato, alfa sbagliata, riga in più, riga mancante) due test
  >   vanno rossi e nominano i 4 difetti; il file è tornato identico (stesso md5).
  > - `chartCoreHelpers.test.ts`: solo l'import e la riga di `pnlReference`.
  > - `priceChartHelpers.test.ts`: il colore come terzo argomento in ogni chiamata, più un test (ogni riga di avviso
  >   porta il colore del chiamante).
  > - Esiti: `chartTheme` 10/10, `priceChartHelpers` 158/158, `chartCoreHelpers` 287/287. La tabella del codice e quella
  >   del piano coincidono voce per voce.
  > - **⚠️ Fuori pista: una prova sopra il carico 50.** La prova del rosso è partita a 60,12: il carico era salito da 38
  >   dopo la corsa precedente, e il ciclo d'attesa mancava. Le altre corse sono partite sotto 50.
  > - **Tre osservazioni di `test-author`, verificate:**
  >   - quattro helper puri leggono i ruoli senza scope, cioè su `<html>`: `buildSecondaryYAxes`,
  >     `buildSignalReferencePrimitives`, `buildScatterOption`, `buildGrowthFullSeries` (come già `growthBrokerColor`,
  >     TD-1b). Oggi nessun grafico sta in un sottoalbero a tema forzato, e il Lab cambia le regole `--lf-*` del foglio
  >     di stile stesso (`engine/stylesheets.ts`), quindi anche su `<html>` le vede: nessun effetto. Resta annotato;
  >   - `toRgba` sostituisce l'alfa del ruolo invece di moltiplicarla: tutti i ruoli letti sono opachi, e il gate di
  >     parità di `roleColors.test.ts` diventa rosso se uno smette di esserlo;
  >   - nessun test DOM di `chartNeutrals` con uno scope vero: delega a `chartRoles`, che `roleColors.dom.test.ts`
  >     copre.
  > - **Riparazione aggiunta, `ScatterChart.test.ts`** (dopo il rosso delle prove leggere, B4-5): il test «hands ECharts
  >   exactly today's option» fissava il tooltip senza riquadro; ora lo aspetta col riquadro comune, letto da
  >   `buildTooltipTheme` (nessun esadecimale). Due test nuovi: in scuro il riquadro è quello scuro, diverso dal chiaro;
  >   il segnale del Lab (`notifyChartColorsChange`) ridisegna col ruolo della card cambiato. `test-author` non l'ha
  >   lanciato: lo lancio io nel passaggio a carico controllato.
  >   - Osservazione di `test-author`, verificata: con un solo punto e nessun `borderColor`, ECharts 6 dava al bordo
  >     del tooltip il colore del punto; col riquadro comune il bordo è il neutro di tutti i tooltip. Va alla designer
  >     (DV-10).
- [x] ✅ (17/10/2026) B4-5 Prove leggere, checkpoint.
  > **Note implementazione** (16/10 23:04 – 17/10 00:18, una cosa alla volta sotto `nice`, ognuna partita col carico
  > sotto 50; script `files/dv_b4_light.sh` della sessione, log in `files/b4-light/`).
  > - Prettier, compilatore (17 componenti, 0 avvisi), `--check` del ratchet (nessuna classe toccata), campi nativi (0
  >   su 415 file), `git diff --check`: puliti.
  > - **Vitest, 49 file** (i 6 gate e i 43 test che importano un modulo toccato): 1.959 test, 47 file verdi al primo
  >   passaggio. Gate: `themeRoles` 80, `themeTokens` 21, `themeComponentTokens` 18, `themeModeReads` 24,
  >   `htmlInterpolation` 26, `htmlSink` 7. Grafici, fra gli altri: `chartCoreHelpers` 287, `GrowthChart` 166,
  >   `priceChartHelpers` 158, `lotComparisonChartHelpers` 162, `chartCategories` 95, `echartsTooltipHelpers` 47,
  >   `AllocationHistoryChart` 38, `PriceChartFull` 36, `AllocationPieChart` 23, `PerformanceChart` 17, `ExposureBars`
  >   12, `CorrelationHeatmap` 6, `chartTheme` 10, `roleColors.dom` 11.
  > - **⚠️ Fuori pista, due rossi, tutti e due colpa del lotto e riparati da `test-author`:**
  >   - `ScatterChart.test.ts`, 1 su 14: il test fissava l'opzione di oggi chiave per chiave, cioè il tooltip senza il
  >     riquadro comune. Ripetuto dopo la riparazione: 16/16.
  >   - `roleColors.test.ts`, 1 su 40: con 14 ruoli l'unione `ChartRole` supera la `printWidth` (300) e Prettier la
  >     scrive un membro per riga dopo un `|` iniziale; il raschietto del gate (`split('|')`) leggeva il primo membro
  >     vuoto. Il raschietto ora accetta un `|` iniziale e segnala ancora ogni membro illeggibile, con un controllo
  >     positivo. Ripetuto: 41/41.
  > - **⚠️ Fuori pista: `front check` rosso, 27 errori in 7 file di `features/backup/**`,** nessuno dei miei: il client
  >   API generato era quello del mio `api sync` di W6-d, più vecchio della base (mancavano gli endpoint e i campi del
  >   ripristino). `api sync` (esporta l'OpenAPI dentro il processo, nessun server; 0 file tracciati cambiati), poi
  >   `front check`: 0 errori, 0 avvisi.
  > - Lo script delle prove aveva un difetto: la variabile del ciclo d'attesa sovrascriveva il contatore dei file,
  >   quindi le etichette `#NN` del riassunto sono sbagliate (l'ordine e i nomi no). Corretto per la prossima volta.
- [x] ✅ (17/10/2026) B4-6 Slot pesante al via del coordinatore.
  > **Note implementazione.** Commit `38e17c2a5` del coordinatore (00:19), base merge `f35fd9026` con la punta
  > `3e5336a0a` (T: tabelle, i 23, lo skill, unito da solo coi miei hunk; AF: file e media); gate del coordinatore sul
  > ramo unito 119/119. Via alle 00:40; slot dalle 00:40:41 alle 01:26:28, corsia 6156 e `/tmp/librefolio-r2-dv`, taglio
  > alle 01:45 (galleria di G alle 02:01), carico da 38 a 68. Script e log in `files/b4-slot/` della sessione; i passi
  > lunghi in testa, così dopo il taglio potevano partire solo quelli corti.
  >
  > | Passo | Esito | Tempo |
  > |---|---|---|
  > | `api sync` | verde, 0 file tracciati cambiati | 24 s |
  > | `front-utility core-unit` | 195 file, 7.618 test | 104 s |
  > | `front-utility component-unit` | 166 file, 4.373 test | 356 s |
  > | E2E `front-portfolio dashboard` | 27 passed | 576 s, col build della base nuova (281 s) |
  > | E2E `front-asset asset-detail` | 35 passed | 313 s |
  > | E2E `front-portfolio risk-lab` | 44 passed | 323 s |
  > | E2E `front-portfolio risk` | 38 passed | 392 s |
  > | E2E `front-broker detail` | 38 passed | 302 s |
  > | E2E `front-fx fx-detail` | 17 passed | 153 s |
  > | E2E `front-utility pac-allocator-real` | 1 passed | 105 s |
  > | E2E `front-portfolio allocation-negative-cash` | 4 passed | 97 s |
  >
  > - Le E2E a 1 worker, 204 test, nessun tentativo ripetuto. A fine slot la porta 6156 è libera, l'HEAD è
  >   `f35fd9026` e il worktree non ha file tracciati cambiati.
  > - La galleria filtrata dei grafici la fa G dopo le 02:00 (fra le 00:00 e le 02:00 non si cattura).

### B4b — I ruoli che leggerà AF, e il ponte sempre in sRGB ✅ (17/10/2026)

Richiesta del coordinatore per AF (17/10 00:20, decisioni alle 00:21 e alle 00:55): il prossimo lotto di AF porta
sui ruoli `lib/theme/drawnColors.ts`, cioè i colori disegnati su canvas da cheetah-grid e quelli degli SVG dei
segnaposto, letti con `chartRoles`. `roleColors.ts` ha un solo writer, DV; AF prepara le bozze sul contratto. Commit a
parte, dopo lo slot di B4: solo `roleColors.ts` e i suoi test; nessun grafico cambia.

- [x] ✅ (17/10/2026) B4b-1 Gli 8 ruoli e la correzione di `resolve()`.
  > **Note implementazione** (01:26).
  > - `ChartRole` passa da 14 a 22 ruoli: `--lf-surface-field`, `--lf-surface-hover`, `--lf-focus`, `--lf-selected`,
  >   `--lf-checked`, `--lf-action`, `--lf-on-action`, `--lf-mark-bg` (`--lf-warning` c'era già, da B4). Gli stand-in
  >   sono i valori del risolutore del gate. **`--lf-selected` è traslucido** (il verde del fuoco al 12 %,
  >   `color-mix(in oklab, var(--lf-focus) 12%, transparent)`): il suo stand-in è un `rgba()`.
  > - **⚠️ Fuori pista: un difetto del ponte, trovato da AF.** In Chromium 149 (quello di Playwright) il `fillStyle`
  >   di un canvas riporta una `color-mix(in oklab, …)` come `oklab(…)`, anche opaca, e una `in srgb` come
  >   `color(srgb …)`: `resolve()` la passava così, contro il commento del modulo («`#rrggbb` when opaque, `rgba()`
  >   when translucent»), e né `parseRgba` né `toRgba` la leggono. Dei 14 ruoli di B4 nessuno è una miscela in nessun
  >   blocco di `tokens.css` (verificato), quindi B4 non ne soffre; dei 22 solo `--lf-selected`.
  > - **Correzione** (decisione del coordinatore: in `resolve()`, nello stesso commit; il modo a me): una funzione
  >   privata `toSrgb` riporta in sRGB quello che il canvas restituisce. Esadecimali e `rgba()` passano come sono;
  >   `oklab()`, `oklch()` e `color(srgb …)` sono convertiti (OKLab → sRGB con le matrici di Ottosson, come CSS Color 4,
  >   tagliati alla gamma e arrotondati a 8 bit): `#rrggbb` se opachi, `rgba()` se traslucidi; un'altra notazione torna
  >   allo stand-in. Scartata la lettura di un pixel 1×1 sopra il nero e il bianco: al 12 % d'alfa sbaglia i canali fino
  >   a ±4.
  > - Verifica a mano, in node su una copia: il campione di AF `oklab(0.474452 -0.0824938 0.0265417 / 0.12)` →
  >   `rgba(35,107,77,0.12)`, cioè `#236b4d` al 12 %; la stessa opaca → `#236b4d`; in `oklch` → `#236b4d`;
  >   `color(srgb …)`, `oklab(100% 0 0)`, `oklab(0 0 0 / 50%)` giusti; `color(display-p3 …)`, `hsl()` e una `oklab`
  >   con due componenti → stand-in. 12 casi su 12.
- [x] ✅ (17/10/2026) B4b-2 `test-author`: il gate di parità impara l'alfa; `PENDING_READERS` con gli 8 ruoli («AF,
  `lib/theme/drawnColors.ts`»), che diventa rosso quando AF comincia a leggerli (AF ne toglie le righe nel suo lotto);
  i casi `oklab`/`oklch`/`color(srgb)` nel test jsdom.
  > **Note implementazione** (01:28–01:37, log in `files/b4-tests/` della sessione; ogni corsa partita col carico
  > sotto 50, dopo un ciclo d'attesa).
  > - `roleColors.test.ts`, 60/60 (erano 41): i ruoli opachi come prima; i traslucidi passano da un aiuto puro che
  >   vuole un `rgba(r,g,b,a)` con le virgole, canali uguali e alfa entro 1e-3; una barriera mostra che `--lf-selected`
  >   è traslucido nei due temi; un controllo positivo rifiuta un canale sbagliato, un'alfa sbagliata, un esadecimale,
  >   un `rgb()` senza alfa, un `rgba()` senza virgole. `PENDING_READERS` con gli 8 ruoli; il controllo dei ruoli morti
  >   accetta un ruolo letto o in attesa; un test nuovo diventa rosso per un nome che non è in `ChartRole` e per un
  >   ruolo in attesa che la produzione legge già (prova del rosso: con `--lf-warning` in elenco, «remove --lf-warning
  >   from PENDING_READERS: production code reads it now»; file tornato identico, stesso md5).
  > - `roleColors.dom.test.ts`, 21/21 (erano 11): il campione di AF (`oklab(… / 0.12)` → `rgba(35,107,77,0.12)`, letto
  >   da `parseRgba`), i 6 valori convertiti, e `color(display-p3 …)`, `hsl()` e una `oklab` con due componenti allo
  >   stand-in, con la barriera che il canvas li ha riportati davvero.
  > - **Tre osservazioni di `test-author`:**
  >   - il passaggio di consegne vede solo le chiamate letterali `.color('--lf-…')`: AF deve leggere i ruoli così, come
  >     `chartNeutrals`, o le righe di `PENDING_READERS` resterebbero per sempre;
  >   - `lab()`, `lch()`, `color(display-p3 …)` e `color(srgb-linear …)` vanno allo stand-in senza segnale: oggi nessun
  >     effetto, perché `tokens.css` mescola solo `in oklab`. Annotato in DV-10;
  >   - zrender legge `rgba()` dividendo alle virgole, e disegna nero un `rgba()` senza virgole: lo stand-in le ha, e
  >     anche quel che `toSrgb` produce (`toRgba`).
- [x] ✅ (17/10/2026) B4b-3 Prove leggere sotto 50, checkpoint.
  > **Note implementazione** (01:40–01:48, ognuna partita col carico sotto 50, sotto `nice`; script
  > `files/dv_b4b_light.sh` della sessione, log in `files/b4b-light/`).
  > - Prettier (i 4 file), `--check` del ratchet, `git diff --check`: puliti.
  > - Vitest, 16 file e 765 test: i gate `themeRoles` 80 e `themeTokens` 21, e ogni test che importa `chartTheme` o
  >   `roleColors`: `chartCoreHelpers` 287, `chartCategories` 95, `roleColors` 60, `allocationRings` 41,
  >   `AllocationHistoryChart` 38, `exposureBarColours` 24, `AllocationPieChart` 23, `allocationHierarchy` 23,
  >   `roleColors.dom` 21, `ScatterChart` 16, `ExposureBars` 12, `chartTheme` 10, `SemiDonutChart` 8,
  >   `CorrelationHeatmap` 6.
  > - **⚠️ Fuori pista: `front check` con 1 errore di tipo,** che Vitest non vede: `INJECTED_COLOURS` di
  >   `chartTheme.test.ts`, un `Record<ChartRole, string>` completo, aveva i 14 ruoli di B4. `test-author` gli ha dato
  >   gli 8 nuovi (`chartTheme` ripetuto, 10/10); di nuovo `front check`: 0 errori, 0 avvisi.
  > - **Y-22/23 della 1.3** (due test del layout con molti `vi.mock`, sulla punta): nessuno finge un modulo dei grafici
  >   o del tema, e il layout `(app)` non li importa; nessun test, nel worktree o sulla punta, finge `chartTheme`,
  >   `roleColors` o gli helper dei grafici. Gli export nuovi non possono mancare sotto un mock.
  > - Commit `9080122a9` (i ruoli) e `b1350a2ea` (i docs) del coordinatore, base merge `65fd0f0fb`, ingresso
  >   `323c61b73` (17/10, 01:53): gate 119/119, test dei ruoli 91/91, `front check` 0 e 0; i letterali di
  >   `chartTheme.ts` da 277 a 152, tutti serie, categorie, stati e segni (DV-10).
- [x] ✅ (17/10/2026) B4b-4 Lo skill `design-system`, dopo l'ingresso di AF (`55b53d8c1`: `drawnColors.ts` sui
  ruoli, `PENDING_READERS` vuoto).
  > **Note implementazione** (03:33–03:40, solo docs, sulla base `55b53d8c1`, avuta per fast-forward dal
  > coordinatore).
  > - La riga di `roleColors.ts` nella tabella dei file: i 22 ruoli raggruppati; chi li legge (i grafici: i neutri, le
  >   sfumature GR4 e le linee dei broker, la scala della correlazione, il peso ideale del PAC, `readableText`; e
  >   `drawnColors.ts`, 18 ruoli); la promessa del ponte, sempre sRGB; la regola del primo lettore, con le chiamate
  >   letterali e `PENDING_READERS`.
  > - **Fuori area, col sì del coordinatore:** la riga di `drawnColors.ts`, che diceva ancora «Legacy values, written
  >   by R». Ora: ogni colore è un ruolo letto con `chartRoles` al disegno (AF, 17/10); il foglio di calcolo in chiaro
  >   resta sul tema `MATERIAL_DESIGN` di cheetah-grid coi soli due bordi sui ruoli (AF-14); le scelte provvisorie
  >   stanno al punto 35 della raccolta; un ruolo traslucido si compone sul suo fondo (`over()`); il proprietario
  >   resta T.
  > - Verifiche: le due righe hanno le 5 colonne della tabella; nessun test o script legge `SKILL.md` (lo script del
  >   giro della designer legge solo `palette.md`); `git diff --check` pulito.
  > - **La terza riga, col sì del coordinatore** (03:38): in «Asking for a new role», passo 2, lo stand-in in
  >   `roleColors.ts` serve «if a chart or a drawn colour reads it» (era «if a chart reads it»); il punto è riavvolto a
  >   120 colonne.

### Giro 3 — La palette finale dei grafici ⏳ (17/10/2026 sera)

Il developer, 22:05: «leggilo e applicalo, modifica i temi colori esistenti, e se ne servono altri, creali»; la designer
ha scelto con lui le correzioni. Valgono D-T27/D-T28. Base `38b7e6313` (fast-forward del coordinatore), corsia 6156 e
`/tmp/librefolio-r2-dv`. La specifica, da una sola fonte:
`designer-feedback/2026-10-17-round3-grafici/decisioni.md` (accanto `palette-finale.json`, i due originali, il foglio
delle scelte). Il campo di DV è il §1; i file liberi secondo la 1.3 (ferma, STOP del developer alle 21:45), salvo
Z-29b su `LineChart.svelte`, che resta fuori.

- [x] ✅ (17/10/2026) G3-0, analisi (22:42–23:15, sola lettura; misure in `files/dv_r3_measure.py` e nei log
  `dv_r3_measure.log` e `dv_r3_badges.log` della sessione).
  > **I valori, verificati coi conti** (`palette-finale.json`, ΔE00 e contrasto come i gate):
  > - tutte le categorie ≥ 3:1 sulla card, nessuna nella banda verde (OKLCH 115–225, croma > 0,03), nessuna a meno di
  >   ΔE00 10 dal verde di successo;
  > - nessuna coppia sotto 5 nella stessa tavolozza; le coppie fra 5 e 8 sono quelle del §1.8, più **ETF/Liquidità 5,9
  >   in chiaro** fra i tipi, gli stessi colori di Tecnologia/Liquidità (il §1.8 la dà per implicita). ETF/Obbligazione
  >   in scuro mi viene 7,3 (il documento dice 7,4): arrotondamento;
  > - barre KPI, ETF contro Liquidità, ΔE00 5,9/10,2, tutte e due ≥ 3:1 sulla traccia;
  > - correlazione: il migliore fra nero e bianco ≥ 4,59:1 su tutta la scala, interpolata in sRGB come zrender.
  > - **⚠️ L'ideale del PAC contro «Non classificato»:** in scuro `#858E9B` contro `#83939D`, ΔE00 **4,1**; in chiaro
  >   7,6. L'8,6 del §1.8 è il tipo più vicino (Altro), non il secchio: nel PAC la riga «Non classificato» disegna il
  >   reale quasi uguale all'ideale. Domanda al coordinatore.
  > - **⚠️ Badge (§1.9, per T):** i fondi della designer sono esattamente `color-mix(in srgb, tipo 14%, card)` (ΔE00
  >   0,0; Fondo scuro 0,5, calcolato sul viola di prima). In `oklab`, la convenzione dei derivati (D-T5), Obbligazione
  >   e Altro in chiaro scendono a 4,46:1: va scritto `in srgb`.
  > - Da sapere: «senza dati» della mappa in chiaro a ΔE00 4,9 dal primo passo (più scuro, «neutro» per scelta); il
  >   centro della correlazione sulla card a 2,94/2,76:1, visibile (ΔE00 27,6/25,4) ma sotto 3:1.
  > **Già com'è oggi:** il reale del PAC nel colore della riga, coi sottotipi sfumati (TD-1); i KPI con segno su
  > `SIGN_TEXT`; oltre il 14° paese le sfumature (GR5); i primi otto tipi nell'ordine del §1.5 (`CATEGORY_SEQUENCE`); un
  > solo «Non classificato» per tutte le tavolozze; una riga per valore (C2).
  > **Lotti proposti:**
  > - R3-1, le tabelle di `chartCategories.ts`: tipi, settori, Liquidità in blu ardesia (non più il salvia di GR3),
  >   «Non classificato»; la sequenza dei paesi come elenco di riferimenti a tipi e settori (`{kind, key}`), perché il
  >   §1.4 vuole che ne segua le scelte; `sequenceColor` prende riferimenti. Il Lab (C1–C3) non legge le sequenze.
  > - R3-2, le scale: `GEO_CHOROPLETH_SCALE` e «senza dati» (`GEO_MAP_COLORS.land`); la correlazione su una scala sua
  >   (`CORRELATION_SCALE`) invece di danger/panel/info, col testo di cella `readableOn(cella, ['#000000',
  >   '#FFFFFF'])`. Nessun ruolo diventa morto: danger, info e panel li leggono altri.
  > - R3-3, PAC e KPI: l'ideale come coppia di valori, non più `--lf-text-secondary`; l'effetto tempi su
  >   `SIGN_TEXT.kpi` senza l'alfa variabile (sotto ±0,05 il testo neutro, come l'etichetta); `timingEffectColor`
  >   sparisce.
  > - R3-4, la semi-ciambella per chiave: la chiave di un proprietario è il suo `user_id`, il colore il tipo del suo
  >   rango fra i proprietari ordinati per `user_id`. Serve una riga in `features/brokers/BrokerSharingPanel.svelte`,
  >   fuori dai miei file: domanda.
  > - R3-5, le due barre della card del patrimonio (ETF e Liquidità): dipendono dal §1.9, perché sono HTML.
  > - Test con `test-author`: `chartCategories`, `CorrelationHeatmap`, `SemiDonutChart`, `AllocationHistoryChart`,
  >   `KpiSection`, `exposureBarColours` (eccezioni: Altro 8,6 e «Non classificato» 7,6 in chiaro, 4,1 in scuro).
  > - Fuori, salvo via del coordinatore: gli indicatori del §1.5 (S9; i colori salvati dagli utenti non cambiano).
  > **§1.9, la fonte unica, proposta (A) in due passi:**
  > - (A) ruoli `--lf-cat-*` in `tokens.css`: casa `tokens.css`; i grafici col ponte e gli stand-in del gate di parità;
  >   badge e barre utilità normali, contrasti nel gate C3 di T. Il layer `category` del Lab diventa una vista dei ruoli
  >   (un rifacimento per L). Prima i valori in `chartCategories.ts` e i ruoli di T coi valori uguali, bloccati da un
  >   test di parità; poi, con L, `chartCategories.ts` legge i ruoli.
  > - (B) i valori restano in `chartCategories.ts` e un modulo scrive a runtime le variabili in un `<style>`, di nuovo a
  >   ogni C4: una casa, Lab invariato; ma variabili fuori da `tokens.css`, classi arbitrarie, contrasti fuori dal gate
  >   di T, un installatore nel layout condiviso.
  > - (C) CSS generato in build da `chartCategories.ts`: una casa, niente runtime, ma le modifiche dal vivo del Lab non
  >   arrivano ai badge.
  > **Run:** leggere sotto 50 (Prettier, compilatore, ratchet, `front check`, circa 50 Vitest); slot al via del
  > coordinatore (`core-unit`, `component-unit`, E2E `dashboard`, `risk`, `risk-lab`, `asset-detail`, broker `detail`,
  > `broker-sharing`, `pac-allocator-real`, `allocation-negative-cash`); galleria di G.
- [x] ✅ (17/10/2026, 23:03) **Via del coordinatore a R3-1…R3-4**, sul via del developer delle 22:05.
  > **Decisioni:**
  > - **§1.9 = (A), in due passi.** Stanotte DV scrive i valori in `chartCategories.ts`; T crea i ruoli dei **tipi**
  >   (11 più la Liquidità) coi valori uguali, più `-soft` e `-on-soft` in `color-mix(in srgb, … 14%, card)`. Il test
  >   di parità di DV blocca le due copie. Il Lab passa ai ruoli in un lotto successivo (L è archiviato).
  > - **R3-5**, le due barre della card del patrimonio, dopo i ruoli di T: `--lf-cat-etf` e `--lf-cat-liquidity`.
  > - **L'ideale del PAC contro «Non classificato», 4,1 in scuro:** si applicano i valori del documento e il punto
  >   resta **aperto** nel test; il coordinatore lo porta alla designer con delle opzioni e manda il valore scelto.
  > - **`BrokerSharingPanel.svelte`:** una riga per R3-4, dichiarata fuori area (su 16 worktree il file non ha
  >   modifiche né commit).
  > - **ETF/Liquidità 5,9 in chiaro** fra le eccezioni nominate.
  > - **Fuori:** gli indicatori (S9: il giro 3 non parla dei segnali, i colori salvati non si toccano); Z-29b su
  >   `LineChart.svelte`.
  > - **Run:** leggere sotto 50; lo slot di circa 60 minuti al via del coordinatore, coordinato con la run di T.
  > **Domande aperte (23:20):** i nomi dei ruoli di T per la parità (`--lf-cat-real-estate`?); chi aggiorna le righe
  > «Charts» dello skill `design-system` che il giro 3 rende false.
- [x] ✅ (17/10/2026, 23:35) **Risposte del coordinatore.**
  > - Nomi confermati per DV e T: `--lf-cat-stock`, `-etf`, `-bond`, `-crypto`, `-fund`, `-hold`, `-crowdfund`,
  >   `-commodity`, `-real-estate`, `-index`, `-other`, `-liquidity`, più i derivati `-soft` e `-on-soft`; passaggio
  >   di consegne alla `PENDING_READERS`, girato a T.
  > - Lo skill: la sezione «Charts» è di DV, aggiornata in questo lotto e dichiarata; la tabella dei moduli e
  >   `palette.md` le fa T in R3-c, dopo l'ingresso di DV.
  > - **L'ideale del PAC, scelto dalla designer:** chiaro `#8C929E` (P1-a′), scuro `#868594` (P2-c). Misurato
  >   (`files/dv_r3_ideal.py`): in chiaro 3,01:1, sotto 10 solo «Non classificato» 8,0 e Altro 8,7, la sfumatura ETF
  >   più vicina a 14,0; in scuro 4,82:1, tutto ≥ 10 (minimo «Non classificato» 10,1, sfumatura ETF 14,4). Riferito al
  >   coordinatore: nessun conflitto, nessuna sfumatura sotto 8.
- [x] ✅ (17/10/2026) G3-1…G3-4, il codice (Prettier pulito; test con `test-author` in G3-5).
  > **Note implementazione:**
  > - **R3-1, `chartCategories.ts`:** tipi, settori, Liquidità (blu ardesia) e «Non classificato» del §1.2–1.3, una
  >   riga per valore (C2), commenti di tinta aggiornati, nessun esadecimale fuori dalle tabelle. Nuovo
  >   `CategoryRef {kind, key}`; `CATEGORY_SEQUENCE` diventa 8 riferimenti di tipo; `KEYLESS_SEQUENCE` sostituito da
  >   `COUNTRY_SEQUENCE`, i 14 riferimenti del §1.4 (a parità di colore il tipo: 1 ETF, 10 FUND, 11 HOLD, 14 OTHER);
  >   `sequenceColor(sequence, rank, dark, poles)`. Chiamanti: `growthBrokerColor`, `AllocationHistoryChart`,
  >   `SemiDonutChart`.
  > - **R3-2:** `GEO_CHOROPLETH_SCALE` sui sei blu, `GEO_MAP_COLORS.land` sul «senza dati» (ΔE00 4,9/6,1 dal primo
  >   passo); `CORRELATION_SCALE` e `CORRELATION_CELL_TEXT` in `chartPalettes.ts`; `CorrelationHeatmap` senza
  >   `chartRoles`, testo di cella `readableOn(cella, nero/bianco)`: minimo 4,59:1 (`files/dv_r3_scales.py`).
  >   Danger, info, panel e text-secondary restano letti (`drawnColors`, `chartTheme`): nessun ruolo morto.
  > - **R3-3:** `PAC_EXPOSURE_COLORS.ideal` in `chartTheme.ts`, `idealColour(dark)`; effetto tempi sulle classi di
  >   segno (`SIGN_TEXT.headline` il valore, `SIGN_TEXT.kpi` l'etichetta; neutro: testo primario e muted), con
  >   `data-direction` (`favorable`/`unfavorable`/`neutral`); `timingEffectColor` rimossa.
  > - **R3-4:** `OwnerSlice.key`; il colore per rango fra i proprietari ordinati per chiave (numeri per valore), non
  >   per ordine dei dati; `BrokerSharingPanel` passa `key: o.user_id` (fuori area, approvato).
  > **⚠️ Fuori pista:**
  > - `CorrelationPairsList.svelte`: solo il commento della polarità («gli estremi della scala» non sono più info e
  >   danger), fuori area, da dichiarare.
  > - Docs: due frasi diventano false (`user/dashboard/kpi-cards`: «più forte il colore, più grande l'effetto»;
  >   `user/assets/correlation`: «pallido» per lo zero). Correzione puntuale nelle 4 lingue e stamp, da dichiarare.
  > - Per T in R3-c: le righe della tabella dello skill per `chartColorScales.ts` (nomina `timingEffectColor`),
  >   `chartPalettes.ts` (manca `CORRELATION_SCALE`) e `chartTheme.ts` (manca `PAC_EXPOSURE_COLORS`).
  > - Per il coordinatore: `decisioni.md` §1.7 e `palette-finale.json` hanno ancora l'ideale di prima
  >   (`#8B929E`/`#858E9B`).
  > - Misure: con i due secchi in entrambe le tabelle e «Non classificato» accanto ai paesi, le coppie sotto 8 sono
  >   esattamente quelle del §1.8 più ETF/Liquidità 5,9 (`files/dv_r3_pairs.py`); al limite OTHER/«Non classificato»
  >   in chiaro, 8,004.
- [x] ✅ (17/10/2026) G3-6, skill e docs (dichiarati).
  > - **Skill `design-system`, sezione «Charts»** (di DV): niente verdi nelle categorie e Liquidità in blu ardesia; la
  >   semi-ciambella per chiave; le linee dei broker (la riga «il nono broker ripete il primo» era già falsa dopo DV-8);
  >   i paesi su `COUNTRY_SEQUENCE`; le scale con valori propri (mappa, «senza dati», correlazione e testo di cella);
  >   l'ideale del PAC; la riga «la lista è in revisione (domanda aperta 1)» chiusa. Non toccate: la tabella dei moduli
  >   e la sezione delle domande aperte (T, R3-c).
  > - **Docs, 4 lingue:** `user/dashboard/kpi-cards` («né verde né rosso» invece di «più forte il colore, più grande
  >   l'effetto») e `user/assets/correlation` («grigio» invece di «pallido»). Le due pagine erano pulite a HEAD (MD5
  >   registrato = HEAD), quindi `dev.py mkdocs translate-stamp` su entrambe: `.translate-hashes.json` cambia solo nelle
  >   loro due voci.
  > - `node scripts/theme/theme-roles.mjs`: «Colour gates: clean».
- [x] ✅ (17/10/2026) G3-5, i test (`test-author`, agente `93d14ac3`; 12 file di test, nessun file nuovo, nessun
  codice di produzione).
  > **Note implementazione:**
  > - `chartCategories.test.ts`: i valori del giro 3; gli export (`COUNTRY_SEQUENCE` al posto di `KEYLESS_SEQUENCE`);
  >   le sequenze a riferimenti, coi paesi del §1.4 nei due temi; «la regola dei verdi» del §1.1 (nessuna tinta OKLCH
  >   115–225 con croma > 0,03, ΔE00 ≥ 10 da `--lf-success`, ≥ 3:1 sulla card, letti da `tokens.css`); la
  >   distinguibilità con pavimento 5 senza eccezioni e soglia 8 con le 15 coppie nominate; il blocco di parità coi
  >   ruoli `--lf-cat-*` di T, flag `CATEGORY_ROLES_IN_TOKENS = false`, col controllo positivo su token sintetici.
  > - `exposureBarColours`/`ExposureBars`: l'ideale come valore; la regola dei 10 su tipi, settori, secchi e su tutte
  >   le sfumature dei sottotipi (le sei ETF e quella di Crowdfund), eccezioni solo in chiaro: «Non classificato» 8,05
  >   e Altro 8,70; in scuro nessuna (minimo «Non classificato» 10,07).
  > - `CorrelationHeatmap`: la scala del tema e il testo di cella nero o bianco, ≥ 4,5:1 su 401 passi; un test C4.
  > - `SemiDonutChart`, `BrokerSharingPanel`, `chartFont.load`: la chiave; `AllocationHistoryChart`, `GrowthChart`:
  >   i riferimenti; `KpiSection`: `data-direction` dell'effetto tempi, nessuno stile in linea.
  > - `src/__tests__/colorDistance.ts`: `oklabOfXyz` e `oklchOf`, provati sulle tabelle pubblicate (Ottosson, CSS
  >   Color 4).
  > - Misure col righello del repo (`files/dv_r3_tests_measure.log`): le tre coppie al limite valgono 8,0039, quindi
  >   non sono eccezioni; STOCK/FUND e Paesi 2/10 5,91.
  > **⚠️ Fuori pista:**
  > - **Il nuovo test C4 ha trovato un difetto mio:** tolti i ruoli dalla scala della correlazione, l'effetto di
  >   ridisegno non leggeva più `colorsVersion`, quindi una modifica del Lab non ridisegnava la matrice. Corretto con
  >   `void neutrals;` nell'effetto.
  > - **Una svista nella mia risposta al coordinatore delle 23:35:** non ha sottotipi solo l'ETF, anche Crowdfund
  >   (`CROWDFUND_REAL_ESTATE`). La sua sfumatura dista dall'ideale 21,5 in chiaro e 14,8 in scuro
  >   (`files/dv_r3_ideal_crowdfund.log`): nessun effetto, da correggere nell'handoff.
- [x] ✅ (18/10/2026, 00:14) G3-7, prove leggere sulla base `38b7e6313` col lotto (`files/dv_r3_light.sh`, log in
  `files/r3-light/`; carico sempre sotto 12).
  > - Prettier pulito sui file cambiati; compilatore Svelte su 8 file, 0 errori e 0 avvisi; ratchet dei colori pulito.
  > - `front check`: **0 errori e 0 avvisi**, dopo `dev.py api sync`.
  > - **31 file Vitest, 1451 test, tutti verdi:** i gate `themeRoles` (80) e `themeTokens` (21), i moduli di
  >   `lib/theme`, i grafici, il PAC, la correlazione, la semi-ciambella, `BrokerSharingPanel`, `GrowthChart`,
  >   `KpiSection` e i sei test del Lab che leggono il file delle categorie.
  > **⚠️ Fuori pista:** il primo `front check` aveva 37 errori in 18 file, nessuno del lotto (backup, legal, cambi,
  > lotti…): proprietà che il client generato non aveva ancora (`secrets_rekeyed`, `legal`, `whats_new`…), perché il
  > client, ignorato da git, era fermo a una base vecchia. `api sync` (schema esportato nel processo, nessun server,
  > nessun file tracciato cambiato), poi tutta la serie di nuovo sullo stesso stato: verde. Riepilogo del primo giro in
  > `files/r3-light/summary-1-stale-client.txt`.
- [x] ✅ (18/10/2026, 00:20) **T R3-b è entrato prima di DV** (`7845fc3d3`): i ruoli `--lf-cat-<tipo>`, `-soft` e
  `-on-soft`, le utility `bg-lf-cat-etf` e `bg-lf-cat-liquidity`. Il flag di parità lo gira DV, dopo il merge del target.
  > - Parità pre-verificata in sola lettura sul commit (`files/dv_r3_parity_precheck.mjs`, `.log`): i 12 ruoli nei due
  >   temi coincidono coi valori di `chartCategories.ts`, 24 controlli su 24.
  > - Sovrapposizione col target: solo `BACKLOG_POST_1.2.md` (TC-19 di T attorno alla riga 2835, le righe di DV dalla
  >   2949): disgiunte, ma un merge non si fa su un file modificato e non committato.
  > - Il target ha già corretto l'ideale del PAC in `decisioni.md` e `palette-finale.json` (`ba8e06763`): la nota per
  >   il coordinatore di G3-1…G3-4 è chiusa.
- [x] ✅ (18/10/2026, 00:23) G3-8, sul ramo unito: il flag di parità e R3-5.
  > **Base:** il coordinatore ha committato il checkpoint in `323ea518e` (genitore `38b7e6313`, i 37 file) e fatto la
  > base merge `3dba7f894` (genitori `323ea518e` + `7845fc3d3`), pulita; `BACKLOG_POST_1.2.md` si è unito da sé.
  > **Note implementazione:**
  > - **Flag di parità:** `CATEGORY_ROLES_IN_TOKENS = true` in `chartCategories.test.ts`, con la data e il commit di T
  >   nel commento, e l'avviso che un colore di tipo vive in due posti fino a DV-11. Il blocco gira nel ramo `true`:
  >   3 test su 3 (`files/r3-light-merged/parity-verbose.log`).
  > - **R3-5:** `KpiSection.svelte`, la barra del valore contabile su `bg-lf-cat-etf` e quella della liquidità su
  >   `bg-lf-cat-liquidity`, le utility di T. `theme-roles.mjs --update`: il baseline perde solo la riga di
  >   `KpiSection` (m1 594 → 590). Nessun test né pagina di docs nominava quei colori.
  > - **Skill «Charts»:** una riga sui colori dei tipi fuori dal canvas (i ruoli `--lf-cat-*` di T, le due barre) e
  >   sulle due copie da cambiare insieme. La regola 11 dice ancora «palette classes until the categorical roles come»:
  >   è di T (R3-c).
  > - **Backlog:** DV-7, le barre dei KPI fatte; DV-11, il primo passo chiuso.
  > **Prove** sul ramo unito (`files/r3-light-merged/`, carico sotto 5): `api sync` senza file tracciati cambiati;
  > Prettier, compilatore e ratchet puliti; `front check` 0 e 0; **32 file Vitest, 1500 test, tutti verdi**
  > (i 31 di prima più `assetTypeTables.test.ts` di T, 49).
- [x] ✅ (18/10/2026, 00:50) G3-9, lo slot di circa 55 minuti nella 6156, al via del coordinatore.
  > **Via alle 00:23** sul commit `08512c952` (genitore `3dba7f894`: il flag e R3-5), carico a 4, la 1.3 ferma.
  > Script `files/r3-slot/dv_r3_slot.sh 01:20` (nessun passo nuovo dopo le 01:20), log in `files/r3-slot/`: `api sync`,
  > `core-unit`, `component-unit`, poi gli E2E con `--workers 1`: `dashboard`, `asset-detail`, `risk-lab`, `risk`,
  > broker `detail`, `front-user broker-sharing`, `pac-allocator-real`, `allocation-negative-cash`,
  > `front-designer-lab live`.
  > **Esito** (00:24:24–00:44:46, carico 4–15; tutti i progetti E2E sono `[desktop]`):
  > - `api sync` verde, nessun file tracciato cambiato (il solo modificato è questo piano);
  > - `core-unit`: 217 file, 9280 test; `component-unit`: 187 file, 4978 test; tutti verdi;
  > - E2E **220 su 222**: `dashboard` 26/27, `asset-detail` 39, `risk-lab` 44, `risk` 38, broker `detail` 40,
  >   `broker-sharing` 17, `pac-allocator-real` 1, `allocation-negative-cash` 4, `front-designer-lab live` 11/12.
  > **I due rossi, col protocollo di `test-triage`** (rilanciati da soli alle 00:48, log `12_` e `13_`):
  > - **`dashboard`, «Positions panel publishes its loading state through data-busy»: assunzione.** Da solo passa
  >   (2,9 s). Il test trattiene la *prima* POST `/portfolio/report` dopo la rotta, ma `login()` (nel `beforeEach`)
  >   atterra su `/dashboard` e aspetta solo che l'app arrivi: una richiesta della pagina d'atterraggio partita dopo la
  >   rotta (lazy, o un ritentativo di Y-24) è «la prima», il `goto` la abbandona, il report della pagina nuova passa e
  >   il pannello (`summaryLoading = reportLoading && !summary`) non è mai occupato. Stesso ordine dei test di B4, dove
  >   passava: la finestra la apre il flusso del report del target, non il giro 3, che non tocca né il pannello né il
  >   caricamento. Rimedio nel test: `page.goto('about:blank')` prima della rotta, oppure trattenere la richiesta della
  >   pagina sotto prova e non la prima che passa.
  > - **`front-designer-lab live`, «export JSON, reset all, import back»: assunzione, deterministica** (rossa anche da
  >   sola). Il sottotitolo delle transazioni (`546204732`, 16/10, `text-lf-muted`) e l'intestazione di `DataTable`
  >   (`77bfa6a39`, 16/10, `th { color: var(--lf-text-muted) }`) leggono lo stesso ruolo: la modifica della variabile
  >   (rosa, su `<html>`) vince su quella del letterale della sua definizione (blu), e l'intestazione è rosa. Lo spec è
  >   fermo al 16/10 alle 02:29, prima dei due commit; la modifica dei grafici (verde) non c'entra. Rimedio nel test:
  >   due elementi con fonti di colore diverse, e la precondizione scritta.
  > - Porta 6156 libera alla fine; HEAD invariato. Nel backlog DV-12 e DV-13.

### DPR — I grafici nitidi dopo un cambio di schermo ✅ (19/10/2026; i due file di Y-N65 in DV-14)

Il developer, dall'anteprima 6160: correlazione, dettaglio dell'asset, broker, PAC, «tutto ECharts» ha testi e numeri
sfocati dopo aver spostato su uno schermo Retina il browser aperto su uno schermo a meno DPI. Lavoro tecnico, non di
colore. Base `cc3c3af15` (fast-forward del coordinatore, pulita; dentro H-57: una sola migrazione `005`, quindi la
corsia 6156 + `/tmp/librefolio-r2-dv`, cancellata per liberare disco, va ripopolata con `--force --clean`). File liberi
secondo la 1.3, tranne `PriceChartFull` e `CandlestickChart` (Y-N65, circa un giorno); `LineChart` libero.

- [x] ✅ (19/10/2026, 15:26–15:45) DPR-0, analisi (sola lettura; carico 72, nessuna run).
  > **La causa, verificata in `node_modules` (echarts 6.0.0, zrender 6.0.0):**
  > - `zrender/lib/config.js` calcola la densità una volta, al caricamento: `Math.max(window.devicePixelRatio || …,
  >   1)`;
  > - `CanvasPainter` la fissa all'init (`this.dpr = opts.devicePixelRatio || devicePixelRatio`), ogni `Layer` la
  >   copia, e `Layer.resize` dimensiona il canvas con `this.dpr`;
  > - `CanvasPainter.resize` ridimensiona gli strati solo se cambia la misura; `ECharts.resize(opts)` non accetta una
  >   densità. Nessuna API pubblica la cambia dopo l'init.
  > - Quindi una scheda caricata su uno schermo 1× disegna a 1× ogni grafico, anche quelli aperti dopo, fino al
  >   ricaricamento. Vale anche per lo zoom del browser (Ctrl +/−), che cambia `devicePixelRatio`.
  > **I siti:** i 22 risultati di `echarts.init` sono 18 chiamate vere in 17 file (`LotGanttChart` ne ha due: grafico e
  > asse) più 4 commenti (`GrowthChart.svelte:323`, `echartsTooltipHelpers.ts:269`, `echartsDataZoomTouchPan.ts:31`,
  > `chartFont.ts:29`).
  > - `echartsTooltipHelpers` e `echartsDataZoomTouchPan` non chiamano `init`: il primo fa `resize()` su un'istanza
  >   che riceve, il secondo ascolta i puntatori sull'elemento del grafico.
  > - Fuori: la sonda 1×1 del Lab (`dev/designer-lab/engine/charts.ts:253`, `ec.init(host, null, …)`), mai disegnata;
  >   il gate K-13 la esclude già.
  > - Tre siti non passano opzioni (`ExposureTreemap`, `CorrelationHeatmap`, `ScatterChart`): canvas per default.
  > **Già presente:** il gate K-13 `components/charts/chartFlagFont.test.ts` (`chart-safety-unit`) scandisce ogni
  > `echarts.init(` di produzione (solo i blocchi `<script>`, rispettando parentesi e letterali), vuole
  > `CHART_INIT_THEME` come secondo argomento, nessun accesso a `init` per altre vie, e almeno 18 chiamate in 17 file.
  > `src/__tests__/component.ts` stubba `matchMedia` in jsdom (tutto «no match», `addEventListener` no-op); i test dei
  > componenti sostituiscono ECharts con un registratore, e nessuno verifica gli argomenti di `init`.
  > **Disegno proposto:**
  > - Un modulo nuovo, `lib/components/charts/chartPixelRatio.ts`, accanto a `chartFont.ts`:
  >   - `chartPixelRatio()`: `Math.max(window.devicePixelRatio || 1, 1)`, la regola di zrender, letta ogni volta;
  >   - `chartInitOptions(element, extra?)`: `{renderer: 'canvas', …extra, devicePixelRatio: chartPixelRatio()}`, e
  >     registra l'elemento per l'ascolto, che arma al primo uso. Ogni sito diventa
  >     `echarts.init(el, CHART_INIT_THEME, chartInitOptions(el))`: una riga, nella forma che il gate K-13 legge.
  >   - All'avvio il risultato è identico a oggi (zrender leggeva lo stesso valore): nessuno scatto della galleria
  >     dovrebbe cambiare.
  > - **L'ascolto:** una sola `matchMedia('(resolution: <dpr>dppx)')` per l'app, riarmata a ogni `change` col valore
  >   nuovo, togliendo la precedente. A ogni cambio, per ogni elemento registrato, `echarts.getInstanceByDom(el)` (API
  >   pubblica): un'istanza viva si aggiorna; un elemento staccato dal documento esce dall'elenco. Senza `matchMedia`
  >   non fa niente.
  > - **Aggiornare sul posto, non ricreare** (`setChartPixelRatio(chart, ratio)`): `painter.dpr`; per ogni strato
  >   `layer.dpr`, `layer.ctx.dpr` e `layer.resize(w, h)` alla misura corrente; poi `painter.refresh(true)`. È il ramo
  >   che `CanvasPainter.resize` esegue quando la misura cambia; il pennello legge `ctx.dpr` a ogni disegno
  >   (`canvas/graphic.js:364–369`), quindi testi, linee e ombre tornano nitidi.
  >   - **Perché non ricreare:** dispose e init perdono la finestra di dataZoom, la selezione della legenda, lo zoom di
  >     mappe e treemap, la coppia selezionata della correlazione, il tooltip aperto; rigiocano l'animazione d'ingresso;
  >     e chiedono a ognuno dei 17 componenti di riagganciare i suoi gestori (`chart.on`, `getZr().on` in candele,
  >     prezzi e lotti, il touch pan, `attachChartReady`). Sul posto tutto lo stato resta, senza lavoro per componente.
  >   - **Il prezzo:** cinque punti interni di zrender 6 (`painter.dpr`, `getLayers()`, `layer.dpr`, `layer.ctx.dpr`,
  >     `layer.resize`, più `painter.refresh(true)`). Mitigazioni: si riconoscono prima di toccarli, e se non tornano il
  >     grafico resta com'è oggi, con un avviso di debug (mai peggio di oggi); un test col vero zrender morde al primo
  >     aggiornamento che li cambia; la versione è fissata dal lockfile.
  >   - Dettaglio accettato: i percorsi già costruiti tengono la tolleranza di semplificazione della densità vecchia
  >     (`PathProxy`, sotto un pixel CSS) fino al prossimo ridisegno dei dati.
  > **Test, con `test-author`:**
  > - `chartPixelRatio.test.ts`, nuovo, in `chart-safety-unit`: la regola della densità; `chartInitOptions` con la
  >   densità del momento della creazione (lo stub passa da 1 a 2: il secondo grafico nasce a 2); l'ascolto con un
  >   `matchMedia` finto (arma `1dppx`, al cambio toglie il vecchio e arma `2dppx`, aggiorna i grafici vivi, un secondo
  >   cambio riarma ancora, salta i disposti, toglie gli staccati, senza `matchMedia` non lancia);
  >   `setChartPixelRatio` sul **vero zrender** in jsdom col contesto 2D finto (ogni canvas a 2×, misura CSS invariata,
  >   `ctx.dpr` 2, la forma ridisegnata con `setTransform(2, 0, 0, 2, …)`; idempotente; un painter non canvas resta
  >   intatto).
  > - Il gate K-13: un controllo in più col suo scanner, cioè il terzo argomento di ogni chiamata è
  >   `chartInitOptions(<primo argomento>…)`; i due file di Y-N65 in una deroga nominata, che diventa rossa quando resta
  >   ferma.
  > - Un test di componente (`CorrelationHeatmap` o `SemiDonutChart`, col registratore): `init` riceve la densità
  >   corrente.
  > - Un E2E nuovo (Chromium, CDP `Emulation.setDeviceMetricsOverride`): il rapporto fra larghezza del canvas e
  >   larghezza CSS passa da 1 a 2 per ogni grafico della pagina, con la finestra di zoom o la selezione intatte; un
  >   grafico aperto dopo nasce a 2. Rischio: se Chromium headless non emette il `change` della risoluzione sotto
  >   l'override, l'E2E copre la nascita e il resto lo coprono i test unitari.
  > **File:** il modulo nuovo e il suo test; i 17 componenti, una riga e un import ciascuno (`PriceChartFull` e
  > `CandlestickChart` per ultimi, o la riga data alla 1.3 per il merge). Condivisi, da dichiarare: il gate K-13
  > (`chartFlagFont.test.ts`), `scripts/test_runner/_frontend_portfolio.py` (registrazione), lo spec E2E nuovo e la sua
  > registrazione.
  > **Run:** leggere sotto 50 (Prettier, compilatore sui 17 file, `front check`, Vitest: il nuovo, `chartFlagFont`,
  > `chartFont.load` e i test dei 17 componenti); slot di circa 50–60 minuti nella 6156: prima `test db populate --force
  > --clean` sulla corsia ricreata, poi `core-unit`, `component-unit`, `chart-safety-unit` e gli E2E (il nuovo,
  > `dashboard`, `asset-detail`, `risk-lab`, `risk`, broker `detail`, `broker-sharing`, `pac-allocator-real`,
  > `allocation-negative-cash`).
  > **Domande aperte:** l'aggiornamento sul posto (interni di zrender) invece della ricreazione; il controllo nel gate
  > K-13 invece di un gate nuovo; Y-N65, deroga o attesa; una riga nella pagina sviluppatori dei grafici, ora o a fine
  > programma.
- [x] ✅ (19/10/2026, 15:41) **OK del coordinatore all'implementazione**, con le risposte:
  > 1. **Aggiornamento sul posto: sì**, alle condizioni scritte: interni riconosciuti prima di toccarli; se non tornano,
  >    nessuna eccezione, il grafico resta com'è con l'avviso di debug; il test sul vero zrender morde al primo
  >    aggiornamento che li cambia.
  > 2. **Il controllo nel gate K-13**, dichiarato; la 1.3 è avvisata (`chart-safety-unit`).
  > 3. **Y-N65: deroga nel gate.** `PriceChartFull` e `CandlestickChart` restano fuori finché la 1.3 non li dà liberi;
  >    poi un lotto piccolo di DV: le due righe e la deroga tolta. Nessuna riga passata alla 1.3.
  > 4. **Docs ora:** la pagina sviluppatori dei grafici; lo stamp di Aphra se ha traduzioni.
  > **Run:** leggere sotto 50; lo slot è nostro senza via, appena il checkpoint è pronto, col carico sotto 50 (la 1.3
  > ha confermato la deroga). T ha portato nel target le colonne fisse (`1fa64ceae`, solo `<style>` di `DataTable` e
  > `AssetTable`): base merge del coordinatore prima del checkpoint.
- [x] ✅ (19/10/2026) DPR-1, il codice e la pagina.
  > **Note implementazione:**
  > - **`lib/components/charts/chartPixelRatio.ts`, nuovo:** `chartPixelRatio()` (`max(devicePixelRatio, 1)`);
  >   `chartInitOptions(element, extra?)` (canvas, `extra`, densità del momento; segue l'elemento e arma l'ascolto al
  >   primo uso); l'ascolto, una `matchMedia` con `resolution` e la grafia WebKit per Safari prima del 16, riarmata a
  >   ogni `change`, che porta alla densità nuova i grafici vivi (`getInstanceByDom`) e lascia andare gli elementi
  >   staccati o senza grafico; `setChartPixelRatio(chart, ratio)`, che riconosce gli interni, non lancia mai, salta
  >   un grafico disposto, uno SVG o uno già alla densità.
  > - **15 componenti, 16 chiamate:** `echarts.init(el, CHART_INIT_THEME, chartInitOptions(el))` e un import. Fuori
  >   `PriceChartFull` e `CandlestickChart` (deroga Y-N65).
  > - **Docs:** `developer/frontend/components/charts.md` (solo inglese, nessuna traduzione e nessuna voce nella cache
  >   di Aphra, quindi niente stamp): l'esempio di `init`, la sottosezione «Pixel density», la tabella delle guardie
  >   (il terzo argomento nel gate K-13, il test nuovo).
  > **Prove leggere** (carico 21): Prettier pulito sui 16 file; compilatore Svelte sui 15 componenti, 0 errori e 0
  > avvisi; ratchet dei colori pulito.
- [x] ✅ (19/10/2026, 16:45) DPR-2, i test (`test-author`, agente `56115849`; nessun codice di produzione, nessuna
  operazione Git).
  > **Note implementazione:**
  > - `components/charts/chartPixelRatio.test.ts`, **nuovo, 49 test**, su ECharts e zrender 6 veri in jsdom col
  >   contesto 2D finto che registra: la densità, `chartInitOptions`, l'ascolto (riarmo, un solo ascolto vivo, senza
  >   `matchMedia` o con uno stub incompleto non lancia), i grafici seguiti portati alla densità nuova (stessa
  >   istanza, stessi canvas; staccati, disposti e non seguiti lasciati stare), l'aggiornamento sul vero zrender (i
  >   membri usati nominati, strato del passaggio del mouse compreso, idempotente, avanti e indietro), il
  >   riconoscimento (SVG, membri mancanti con l'avviso, `refresh` che lancia).
  > - `chartFlagFont.test.ts`, il gate K-13, **+4 test**: il terzo argomento è `chartInitOptions(<il primo argomento
  >   della chiamata>…)`; la deroga `PIXEL_RATIO_PENDING` (`PriceChartFull`, `CandlestickChart`) diventa rossa se il
  >   file sparisce, non ha chiamate o passa già `chartInitOptions`; due controlli sintetici prima.
  > - `SemiDonutChart.test.ts`: il finto `init` registra tema e opzioni; un `describe` nuovo, densità 2 e 1,5.
  > - `e2e/portfolio/chart-pixel-ratio.spec.ts`, **nuovo, 2 test**, Chromium desktop: la densità cambiata via CDP
  >   (`Emulation.setDeviceMetricsOverride`); i grafici della Dashboard (crescita e torta) passano 1× → 2× → 1× con
  >   le stesse istanze e gli stessi canvas; la torta di un'altra dimensione aperta dopo nasce a 2×. Una sonda propria
  >   distingue il caso «Chromium non emette il `change`» (colpa del banco) da «i grafici restano a 1×» (prodotto).
  >   `data-chart-renders` registrato, non asserito: un `ResizeObserver` può chiamare `resize()` dopo il cambio.
  > - `scripts/test_runner/_frontend_portfolio.py`: il file nuovo in `chart-safety-unit`; l'azione nuova
  >   `front-portfolio chart-pixel-ratio`. Il gate `check-orphans` è soddisfatto.
  > - **Che mordono:** 13 mutanti del modulo costruiti in memoria, ciascuno preso dal suo test; il test di componente
  >   rosso con le opzioni di prima; i controlli sintetici del gate.
  > - Vitest di test-author: `chartPixelRatio` 49, `chartFlagFont` 20, `chartFont.load` 16, `SemiDonutChart` 14,
  >   `CorrelationHeatmap` 10, `AllocationPieChart` 23, `GrowthChart` 166, `AllocationHistoryChart` 38,
  >   `ExposureBars` 12: tutti verdi.
  > - La pagina dei grafici, tabella delle guardie: la deroga nel gate e un paragrafo per il test di componente e
  >   l'E2E, come suggerito.
- [ ] DPR-3, `front check` e i Vitest toccati; poi lo slot (`files/dpr-slot/dv_dpr_slot.sh`, con
  `DPR_E2E_ACTION=chart-pixel-ratio`): `test db populate --force --clean` sulla corsia ricreata, `api sync`,
  `core-unit`, `component-unit`, `chart-safety-unit`, l'E2E nuovo, `dashboard`, `asset-detail`, `risk-lab`, `risk`,
  broker `detail` (copre i tre grafici dei lotti), `broker-sharing`, `pac-allocator-real`, `allocation-negative-cash`.
  > **Prove leggere** (16:39–16:54, `files/dv_dpr_light.sh`, log in `files/dpr-light/`, carico 29–43 nei passi,
  > punte a 115 in attesa): `api sync` senza file tracciati cambiati; Prettier pulito anche sui tre file nuovi;
  > compilatore sui 15 componenti, 0 errori e 0 avvisi; ratchet pulito; `front check` **0 errori e 0 avvisi**; **21
  > file Vitest, 989 test, tutti verdi**: i 9 di test-author, poi `CorrelationHeatmap.tooltipEscape`,
  > `AllocationPieChart.tooltipEscape`, `LineChart`, `ScatterChart`, `ExposureTreemap`, `PerformanceChart`,
  > `AssetSetRiskReturnSection`, `L3RiskAdjusted`, `chartCoreHelpers`, i gate `htmlInterpolation` e
  > `themeModeReads`, `scanColors` del Lab.
  > - Nel backlog **DV-14**: `PriceChartFull` e `CandlestickChart` dopo Y-N65.
  > **Checkpoint e base:** il coordinatore ha committato il checkpoint in `741a2d5c3` (genitore `cc3c3af15`, i 24 file)
  > e fatto la base merge `be7033b1c` (genitori `741a2d5c3` e il target `ccc2a4141`, con T: colonne fisse e T2),
  > pulita. **Slot partito alle 16:59** su `be7033b1c`, carico 49,7, taglio 17:55, `DPR_E2E_ACTION=chart-pixel-ratio`,
  > log in `files/dpr-slot/`. Disco: 21 GiB liberi.
  > **La sonda dell'E2E nuovo (17:08–17:16, carico fino a 157):** «nasce a 2×» verde (3,2 s); «seguono» rosso sulla
  > sonda del test: sotto `Emulation.setDeviceMetricsOverride` `window.devicePixelRatio` arriva a 2, ma la query
  > `(resolution: 1dppx)` della sonda non riceve nessun `change` in 10 s. È il banco, non il prodotto: la pagina non può
  > sentire il cambio, e la sonda lo distingue apposta.
  > **⚠️ Fuori pista:** a test-author la revisione del solo test 1: prima un aggiornamento del rendering a ogni lettura
  > della sonda (gli eventi `change` delle media query partono in «update the rendering»); se Chromium non emette
  > ancora niente, un ponte esplicito: `addInitScript` registra le `MediaQueryList` di risoluzione dell'app e il test
  > le notifica dopo il cambio reale di densità, con un'annotazione che dice chi ha emesso l'evento. Tutto il resto
  > resta reale: il cambio via CDP, i grafici, zrender, il gestore del modulo e il riarmo.
- [x] ✅ (19/10/2026, 17:42) DPR-3, lo slot su `be7033b1c` (16:59–17:41, carico 18–157, log in `files/dpr-slot/`).
  > - `test db populate --force --clean`: corsia ricreata (tabelle pulite, broker e utenti creati); `api sync` senza
  >   file tracciati cambiati.
  > - Vitest: `core-unit` 220 file e 9383 test; `component-unit` 191 file e 5010 test; `chart-safety-unit` 9 file e
  >   144 test (col gate K-13 esteso e `chartPixelRatio.test.ts`); tutti verdi.
  > - E2E, tutti nel progetto `[desktop]`: `dashboard` 27, `asset-detail` 43, `risk-lab` 44, `risk` 38, broker
  >   `detail` 40 (i tre grafici dei lotti), `broker-sharing` 17, `pac-allocator-real` 1, `allocation-negative-cash` 4;
  >   tutti verdi.
  > - `chart-pixel-ratio`: alla prima esecuzione 1 su 2, rosso sulla sonda del banco; **rivisto e rilanciato da solo
  >   (17:41–17:42, log `11_rerun-pixel-ratio.log`): 2 su 2.** La sonda, anche con due frame di rendering a ogni
  >   lettura, non riceve il `change` né all'andata né al ritorno; l'annotazione dice «dispatched by the test», e da
  >   lì i grafici seguono: 1× → 2× → 1×, stesse istanze, stessi canvas, e `data-chart-renders` invariato (2 → 2,
  >   4 → 4): niente ridisegnato dalle opzioni.
  > - Porta 6156 libera alla fine; HEAD `be7033b1c`. Da committare: lo spec rivisto, una clausola della `desc` del
  >   runner e il piano.
- [x] ✅ (19/10/2026, 17:47) **DPR entrato:** `56666d2ce` (il commit `80636e16e`, base merge `be870c783` con
  `98bee0d2b`, che contiene Y-N65 `5cb47395f`). Sul ramo unito: ratchet pulito, gate dei colori 119/119,
  `chart-safety-unit` 144/144 con K-13 sulle versioni di Y dei due file, `api sync` senza cambi, `front check` 0 e 0.
  Il worktree è sulla punta, pulito. Via a DV-14.
- [x] ✅ (19/10/2026, 18:02) DPR-4 (DV-14), `PriceChartFull` e `CandlestickChart` su `chartInitOptions`.
  > **Note implementazione:**
  > - Le due chiamate (`PriceChartFull.svelte:540`, `CandlestickChart.svelte:304`) come le altre 16, con l'import.
  >   Le righe di Y-N65 restano com'erano: il tipo e il commento di `onMeasureHover`, `measureHover` col suo `$effect`,
  >   il `mousemove` di zr con `setCursorStyle`, `data-measure-hover`.
  > - Il gate K-13 (`test-author`): `PIXEL_RATIO_PENDING` vuoto. **Decisione:** il meccanismo resta, per un grafico che
  >   non possa migrare subito; il controllo di staleness resta coerente (vuoto passa sul codice, i controlli
  >   sintetici mordono ancora).
  > - La pagina sviluppatori (tabella delle guardie): nessuna deroga, il record resta vuoto per un caso futuro.
  > - Backlog: DV-14 chiusa, in attesa del commit.
  > - Nessuna migrazione dal mio ultimo slot (`be7033b1c..56666d2ce` non tocca `backend/alembic` né `backend/app/db`):
  >   la corsia non si ripopola.
  > - test-author: in `chartFlagFont.test.ts` il record vuoto, la sua doc e l'intestazione (Part B, «why it was
  >   red»); gli altri quattro test dei due grafici non cambiano (i registratori di ECharts ignorano le opzioni, e lo
  >   stub di `matchMedia` non emette mai il `change`).
  > **Prove:**
  > - leggere (carico 18–28): Prettier e compilatore puliti sui due componenti; Vitest di test-author: `chartFlagFont`
  >   20, `chartPixelRatio` 49, `PriceChartFull` 58, `PriceChartFull.tooltipEscape` 17,
  >   `CandlestickChart.tooltipEscape` 7, `candlestickChartHelpers` 44, `priceChartHelpers` 163; i 9 file di
  >   `chart-safety-unit` in un colpo, 144 test; `front check` 0 errori e 0 avvisi; tutti verdi;
  > - slot (17:52–18:02, `files/dv14-slot/`): E2E `asset-detail` 43 su 43, `fx-detail` 28 su 28, progetto
  >   `[desktop]`; porta 6156 libera, HEAD `56666d2ce`.

## Definizione di fatto

- **Un colore fisso per chiave:** ogni chiave ha un colore per tema, uguale in torta e storico, in dashboard, broker
  e dettaglio asset, qualunque siano classifica e periodo.
- **GR2:** nessun rosso o verde semantico nelle categorie.
- **GR4 e GR5:** GR4 esatto, GR5 applicato; nessuna ripetizione silenziosa nello storico geografico.
- **Emoji:** una sola fonte.
- **Test e gate:** verdi.
  - Gate: `themeRoles`, `themeTokens`, `themeModeReads`.
  - Vitest mirati e `front check`.
  - E2E: dashboard, rischio, condivisione del broker.
  - Backend: `api utilities`, `services financial-math`.
- **Gallery:** il diff dello stesso giorno mostra solo gli scatti attesi.
- **Chiusura:** piano aggiornato a ogni passo; nessun server acceso.
