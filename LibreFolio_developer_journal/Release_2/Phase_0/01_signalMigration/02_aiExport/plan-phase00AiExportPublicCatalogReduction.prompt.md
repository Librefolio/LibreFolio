# Piano Phase 0 — AI Export Public Catalog Reduction V3

**Stato**: in esecuzione  
**Obiettivo**: sostituire il catalogo pubblico 32 Dataset + 17 Analysis con
8 Export Data autonomi + 13 Analysis task-oriented, mantenendo i mattoncini
granulari backend-internal.

## Decisioni congelate

- `CATALOG_VERSION = 3`; selezioni pubbliche V3; snapshot wire schema V2.
- `CatalogVisibility.PUBLIC | INTERNAL`, default internal.
- Catalog API espone solo 8 Dataset + 13 Analysis.
- Snapshot API rifiuta selezioni interne dirette; Analysis può comporle.
- Mini-history uniforme: Portfolio/Broker 8/16/30, Asset interni 6/12/24,
  Asset/FX singoli 8/16/30.
- P/M/K Technical Export e policy eventi invariati.
- Memoria frontend V2→V3 tramite alias.
- Probe finale: 126 varianti, metriche complete, retention selettiva.
- Nessun commit, push, release, cleanup generale, wiki lint o full MkDocs prima review.

## Catalogo pubblico

### Export Data

1. `portfolio.overview_and_history`
2. `portfolio.asset_history`
3. `broker.overview_and_history`
4. `broker.asset_history`
5. `asset.position_and_history`
6. `asset.market_history`
7. `fx.market_and_exposure`
8. `fx.market_history`

### Analysis

1. `portfolio.pac_planning`
2. `portfolio.rebalancing`
3. `portfolio.performance_market_drivers`
4. `portfolio.fiscal_lots`
5. `broker.review`
6. `broker.performance_market_drivers`
7. `broker.cost_efficiency`
8. `broker.fiscal_lots`
9. `asset.position_review`
10. `asset.market_analysis`
11. `fx.pair_analysis`
12. `fx.conversion_planning`
13. `fx.exposure_impact`

## Step

### 1. Baseline e istruzioni — ✅ 2026-08-04

> **Note implementazione**: lette istruzioni AI/backend/frontend/testing e guide
> runtime/composition/sampling/probe; verificato `--help` corrente; congelato run
> baseline `20260801T035128.653789Z`; suite baseline verdi:
> servizi AI Export 1067/1067, probe utility 40/40.

### 2. Visibility, versioning e API boundary — ✅ 2026-08-04

Implementare visibility fail-closed, catalogo V3, filtro pubblico, rifiuto ID interni
diretti e relativi test.

> **Note implementazione**: aggiunto `CatalogVisibility` fail-closed; catalogo e
> selezioni pubbliche V3, wire schema V2; API espone solo 8+13 e rifiuta richieste
> dirette interne. Registry interno resta completo.

### 3. Componenti condivisi — ✅ 2026-08-04

Mini-history/performance path, sintesi economica Asset, concentrazione Portfolio,
FIFO economico Asset e prezzi tecnici Broker.

> **Note implementazione**: registry 67 componenti; mini-history observed-only
> uniforme 6/12/24 e 8/16/30; percorso Portfolio/Broker 8/16/30 con NAV esplicito
> flow-inclusive e rendimento/index TWRR; allocazione valuta/HHI Portfolio; FIFO
> economico sintetico Portfolio/Broker; prezzi grezzi Broker.

> **⚠️ Fuori pista**: review ha rilevato che un indice da NAV avrebbe confuso
> depositi/prelievi con rendimento. Corretto su `historical_twrr`, mantenendo NAV
> soltanto come valore del percorso.

### 4. Otto Export Data pubblici — ✅ 2026-08-04

Comporre dataset autonomi, senza duplicazioni sostanziali.

> **Note implementazione**: creati gli 8 ID V3. I general export hanno core
> finanziario required e contesti tecnico/FIFO/drawdown optional, così un guasto
> ausiliario non elimina la fotografia finanziaria; detailed export preservano
> serie tecniche complete.

### 5. Tredici Analysis pubbliche — ✅ 2026-08-04

Composizione, Scenario Thesis, PAC timing, market-driver research e confini fiscali.

> **Note implementazione**: creati 13 profili pubblici V3; vecchi profili assorbiti
> restano interni. Aggiunti Scenario Thesis, gate PAC timing, ricerca datata
> performance/market drivers e confine FIFO economico vs fiscalità legale.

### 6. Frontend, memoria, i18n e API sync — ✅ 2026-08-04

Catalogo esatto, alias V2→V3, EN/IT/FR/ES, Additional Data, test UI.

> **Note implementazione**: frontend V3 esatto 8+13, request/contract V3,
> migrazione one-shot memoria V2→V3, prompt contract canonical English, client
> OpenAPI/Zodios sincronizzato. UI EN/IT/FR/ES aggiornata atomicamente con
> `./dev.py i18n`; audit 2335/2335 completo, 0 chiavi backend mancanti.

> **⚠️ Fuori pista**: le 32 chiavi Dataset V2 non possono essere rimosse finché i
> relativi spec restano registry-internal: l'audit backend le richiede. Sono state
> ripristinate ma non compaiono nel catalogo/UI pubblico.

### 7. Test mirati — ✅ 2026-08-04

Backend, frontend unit/type-check, E2E AI Export, lint e format.

> **Note implementazione**: suite servizi AI Export completa verde; frontend
> 199 unit; Playwright AI Export 34 casi desktop/mobile; `svelte-check` 0/0;
> probe utility 55; Ruff/Black/Prettier verdi.

> **⚠️ Fuori pista**: Playwright interrotto inizialmente da DB test cancellato e
> lock residui; ricreato esclusivamente il DB test. Un test FX chiamava “storia
> completa” 516 giorni, insufficienti per warm-up EMA200=1200 punti: corretta la
> fixture, non il runtime.

### 8. Probe V3 — ✅ 2026-08-04

Profilo 126 varianti, metriche, percentili, retention manifest, SVG e comparison.

> **Note implementazione**: aggiunto profilo `public-catalog-v3`, matrice esatta
> 126, category/composition metrics, distribuzioni, retention nominata+percentili,
> manifest dedicato, placeholder review non-fabbricati, comparison manifest e SVG
> deterministici.

### 9. Run autorevole — ✅ 2026-08-04

Smoke, copied-DB run, integrità, secret scan, equivalenza renderer.

> **Note implementazione**: smoke `20260804T134643.050933Z` 1/1; run finale
> autorevole `20260804T155305.988711Z` 126/126, 0 failure/skip, 38 prompt
> retained, secret scan passato, DB production invariato, UI/probe equivalenti.
> Tutti i prompt/file/stable key usano `user_anon_01`.

> **⚠️ Fuori pista**: il primo full run `20260804T134815.017107Z` era
> semanticamente corretto ma usava l'alias login nel nome artefatti. Aggiunto
> anonymizer fail-closed e rerun completo; SHA dei 126 prompt identici.

### 10. Review e correzioni mirate — ✅ 2026-08-04

78 Analysis + 48 Export Data; nessun rerun corpus non necessario.

> **Note implementazione**: review per dominio dei 38 retained + 126 metriche.
> Corrette densità general, scope weights/esclusioni, denominator concentrazione,
> FIFO allocated/unallocated, zero Asset, lot economics, FX 30d/91d, input
> conversione, observed-close basis e status Signal locali. Rating finale:
> 126 OPTIMAL, 0 SUFFICIENT, 0 INSUFFICIENT.

### 11. Report e docs — ✅ 2026-08-04

`report-phase00AiExportPublicCatalogReductionV1.md`,
`report-phase00AiExportTaskAdequacyReviewV2.md`, docs AI Export correlate.

> **Note implementazione**: creati report, comparison logica, review JSON/tabelle,
> grafici e aggiornate le sorgenti inglesi user/developer AI Export.

> **⚠️ Fuori pista**: una pipeline traduzioni MkDocs parallela poteva
> sovrascrivere le sorgenti. Dopo lo stop della pipeline sono state ricontrollate
> tutte le pagine inglesi AI Export; nessuna traduzione docs è stata avviata.

### 12. Stop per review — ✅ 2026-08-04

Nessun commit o release.
