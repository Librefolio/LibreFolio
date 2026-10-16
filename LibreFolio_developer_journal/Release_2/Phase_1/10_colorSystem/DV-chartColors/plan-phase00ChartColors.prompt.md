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
