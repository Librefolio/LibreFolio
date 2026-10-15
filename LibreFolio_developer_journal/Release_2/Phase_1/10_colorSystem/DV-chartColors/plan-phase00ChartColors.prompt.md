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
- **Gli altri passi aspettano le decisioni qui sotto** e l'ordine della 1.3 (Y9, Y10; FE2 per S9).

| # | Decisione richiesta | Proposta di DV | Stato |
|---|---|---|---|
| 1 | Dove vivono i colori di categoria | **A**: tabella TS in `lib/theme/chartCategories.ts` più ponte per i ruoli. **B**: variabili `--lf-cat-*` (file di DV, import di T) | aperta |
| 2 | GR4, ranghi 4–6 (l'ETF ha fino a 6 sottotipi) | stessi passi verso il polo opposto. ΔE00 minimo 3,2–6,0: va al giro 3 | aperta |
| 3 | Sequenza senza chiave (storico geografico) | settori 1–14 più «Non classificato» fisso. L'originale dice «primi 14 … 16 tinte» | aperta |
| 4 | Colore di un tipo `Unknown` (asset senza tipo) | quello di «Non classificato»: stessa ❓ dei settori | aperta |
| 5 | Linee dei broker («devono tutte seguire la famiglia nuova») | i primi 8 tipi, cambiando solo i valori di `GROWTH_BROKER_PALETTE` | aperta |
| 6 | Indicatori con colori per tema | S9 a parte, dopo Y4, Y8 e il taglio di X della pagina asset; fino ad allora restano i colori di oggi | aperta |
| 7 | Segnali già salvati (hex nel localStorage) | migrare i default alla tinta nuova più vicina (store v3) | aperta |
| 8 | Emoji dei settori nel frontend | un solo accessor, `getSectorEmoji`, anche nella torta della dashboard; ripiego come specchio fissato da gate | aperta |
| 9 | Badge dei tipi (`BADGE_CLASS_MAP`, per contenuto) | fuori dalla prima consegna: regola contenuto/famiglia al developer; ruoli con T | aperta |
| 10 | `POLARITY_TONES` della lista delle coppie | sui ruoli danger/info insieme alla matrice | aperta |
| 11 | R-7, semi-ciambella senza osservatore del tema | DV la chiude con GR5.2 | aperta |
| 12 | Chi costruisce il ponte `roleColors.ts` | DV, con l'API concordata con T (B4 lo estende) | aperta |

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

### S1 — Una mappa sola per le emoji dei settori, nel backend ✅ codice e test (15/10/2026); manca `api utilities`

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

### S2–S8 — In attesa delle decisioni 1–12 e dell'ordine della 1.3

| Passo | Contenuto | File | Conflitti |
|---|---|---|---|
| S2 | Fondamenta in `lib/theme` e gate: copertura, GR2, distinguibilità con le coppie §4 elencate, specchio delle emoji | `lib/theme/chartCategories.ts`, `chartShades.ts`, `roleColors.ts` (nuovi) | nessuno |
| S3 | Torta, anelli, gerarchia; emoji dei settori con un accessor | `allocationHierarchy.ts`, `allocationRings.ts`, `AllocationPieChart.svelte`, `chartPalettes.ts` | Y9 (K-13) |
| S4 | Storico per tipo, settore e paese | `AllocationHistoryChart.svelte` | Y10 (627/707/779/806), Y9 |
| S5 | Scale delle mappe | `chartPalettes.ts`, solo valori | nessuno |
| S6 | Semi-ciambella (GR5.2, R-7) | `SemiDonutChart.svelte`, `chartPalettes.ts`, `chartTheme.ts` | Y9 |
| S7 | Correlazione sui ruoli | `CorrelationHeatmap.svelte`, `toneClasses.ts`, `chartTheme.ts` | Y9 (C-34 riga 330), T (W3) |
| S8 | Linee dei broker, se la decisione 5 è sì | `chartPalettes.ts`, solo valori | nessuno |
| S9 | Indicatori per tema (via a parte) | `lib/charts/signals/*`, UI dei segnali, `chartSettingsStore`, pagina asset riga 916 | Y4, Y8, X |
| S10 | Verifiche e gallery (strumenti di G, slot pesante), checkpoint | — | — |

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
