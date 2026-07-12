# Milestone 3 — UI Broker v2 (post Portfolio Engine unificato)

Questa cartella raccoglie il **redesign ad alto livello** delle pagine Broker (lista globale + dettaglio a
tab), aggiornato dopo il lavoro su Portfolio Engine e Dashboard Home documentato in
[`../../phases/phase-09-subplan/plan_ui_dashboard.md`](../../phases/phase-09-subplan/plan_ui_dashboard.md) e in
[`../../phases/phase-09-subplan/Milestone_2/portfolio_engine/`](../../phases/phase-09-subplan/Milestone_2/portfolio_engine/).

I 3 piani originali (`../plan_ui_broker_overview.md`, `../plan_ui_broker_holdings.md`,
`../plan_ui_broker_transactions.md`) erano stati scritti **prima** che esistesse l'endpoint unificato
`POST /portfolio/report` e i widget generici della Dashboard Home (KPI cards, GrowthChart, Allocation panel,
PositionsPanel, RecentTransactionsPanel). Questa milestone li ridisegna riusando quei widget dove possibile
e segnalando esplicitamente i gap ancora presenti nel backend.

Solo disegno UI e requisiti dati (riusa/manca) — **nessun piano implementativo di dettaglio**.

## Fasi

| # | File | Descrizione | Supersede | Stato |
|---|------|-------------|-----------|:-----:|
| 1 | [`plan_ui_broker_overview.md`](./plan_ui_broker_overview.md) | Lista Globale Brokers (+ Broker Discovery) e shell a tab del Broker Detail + Tab Panoramica | [`../plan_ui_broker_overview.md`](../plan_ui_broker_overview.md) | ✅ disegno · ✅ [piano implementativo](./impl_plan_broker_overview.md) |
| 2 | [`plan_ui_broker_holdings.md`](./plan_ui_broker_holdings.md) | Tab Posizioni (riuso `PositionsPanel`) + Pannello Inline Lotti FIFO multi-broker (bubble timeline + WAC/prezzo per-broker+combinato) | [`../plan_ui_broker_holdings.md`](../plan_ui_broker_holdings.md) | ✅ disegno raffinato · ✅ [piano implementativo](./impl_plan_broker_holdings.md) · ✅ implementato (2026-07-10) · ✅ evoluto multi-broker (2026-07-11, fleet — codice in working tree non ancora committato) |
| 3 | [`plan_ui_broker_transactions.md`](./plan_ui_broker_transactions.md) | Tab Transazioni (riuso `<TransactionsTable>`) + File Importati | [`../plan_ui_broker_transactions.md`](../plan_ui_broker_transactions.md) | ✅ disegno · ✅ implementato (recap in-doc, nessun `impl_plan_*.md` separato — chiuso 2026-07-08, codice in working tree non ancora committato) |

L'ordine riflette anche l'ordine di realizzazione consigliato: la Fase 1 introduce la shell a tab del
Broker Detail (prerequisito condiviso), le Fasi 2 e 3 riempiono gli altri due tab.

Il piano implementativo di Fase 1 ([`impl_plan_broker_overview.md`](./impl_plan_broker_overview.md)) traduce
il disegno in step concreti (file, schemi, componenti da riusare/creare/ritirare), massimizzando il riuso di
componenti custom esistenti. Le Fasi 2/3 avranno un proprio `impl_plan_*.md` con lo stesso pattern, dopo che
la Fase 1 sarà implementata.

## Gap principali emersi (riepilogo trasversale)

- **`GET /portfolio/asset-history` — regressione da ripristinare, non gap da progettare.** Verificato con
  `git log`: la route esisteva ed era funzionante (test inclusi), è stata rimossa per errore nel commit
  `3184a969` insieme a un cleanup di endpoint legacy realmente superseduti — ma questo endpoint non lo era
  (il servizio `get_asset_history()` è rimasto orfano e il docstring del file la elenca ancora come
  disponibile). Dettagli in Fase 2.
- **Broker Discovery — confermato in scope, semplificato.** `GET /brokers` guadagna un parametro opt-in
  `include_inaccessible` (default `False`, sia per performance sia per correttezza: non deve inquinare i
  selettori broker esistenti) che aggiunge solo `{id, name, icon_url}` dei broker non posseduti. Nessun
  flusso "Richiedi Accesso"/notifica in questa fase (confermato). L'informazione "chi ha accesso" passa
  dalla stessa icona Condividi presente su ogni card, in sola lettura — vedi punto successivo. Dettagli in
  Fase 1.
- **Icona Condividi ovunque (nuova) + sola-lettura per non-membri (nuova capability backend).** Ogni card
  broker (proprio o altrui) guadagna un'icona Condividi che apre `BrokerSharingModal`: editabile per OWNER
  (nessun cambiamento, già così), sola-lettura per EDITOR/VIEWER (oggi impossibile: il bottone è visibile
  solo all'OWNER) e per non-membri (oggi impossibile: `GET /brokers/{id}/access` risponde 404 a chi non ha
  accesso). Va aperto l'endpoint ai non-membri restituendo un payload ridotto (solo `username`+`role`,
  senza `email`/`share_percentage`). Dettagli in Fase 1.
- **Quota %, NAV/Gain/Cash-multivaluta per-card nella lista globale senza N+1 chiamate** — piccola
  estensione di `GET /brokers` (`user_share_percentage`, sempre inclusa, nessun costo) **+** uso di
  `PortfolioReportQuery(include_breakdown=true)` / `by_broker` (richiede l'aggiunta di
  `cash_balances: List[Currency]` nativo a `BrokerBreakdown` per non perdere il dettaglio multi-valuta) al
  posto delle chiamate `/summary` per-broker. Quest'ultima parte **usa il Portfolio Engine** e va tenuta
  come chiamata separata da `GET /brokers` (che alimenta selettori broker leggeri in tutta l'app), cachata a
  livello di sessione come già fa `portfolioStore`. Dettagli in Fase 1.
- **Selettore Valuta** — sia in Lista Globale sia in Tab Panoramica (istanze indipendenti dello stesso
  `CurrencySearchSelect` della Dashboard), pre-popolato da `globalSettings.default_currency`, usato come
  `target_currency` per NAV/Gain. Dettagli in Fase 1.

Tutti gli altri componenti necessari (KPI cards, GrowthChart, Allocation panel, PositionsPanel,
RecentTransactionsPanel, `GET /portfolio/lots`, `<TransactionsTable>`, storico/wizard import BRIM) esistono
già e vengono solo riposizionati/riparametrizzati per lo scope di un singolo broker.

## Studi trasversali

- [`study_chart_dynamic_resolution.md`](./chart_resolution/study_chart_dynamic_resolution.md) — studio di fattibilità (righe
  1-250) + raffinamento architetturale definitivo (righe 256+, semantic zoom daily→weekly→monthly) per i
  grafici a 2 assi (crescita portafoglio, storico allocazione, prezzi asset) in base al periodo visibile
  allo zoom corrente. Tradotto in 7 piani implementativi (gap-analysis + risoluzione), un file per
  componente/workstream, in [`chart_resolution/`](./chart_resolution/), scritti in parallelo da una flotta
  di agenti:
  1. [`impl_plan_chart_resolution_00_foundation.md`](./chart_resolution/impl_plan_chart_resolution_00_foundation.md)
     — nuova utility condivisa `timeSeriesAggregation.ts` (bucketing, regole di aggregazione, densità/isteresi,
     debounce) — documento fondativo, prerequisito concettuale degli altri 6.
  2. [`impl_plan_chart_resolution_01_price_candlestick.md`](./chart_resolution/impl_plan_chart_resolution_01_price_candlestick.md)
     — `PriceChartFull` + `CandlestickChart` (risoluzione condivisa linea↔candela, event marker, measure
     mode, tooltip bucket-aware).
  3. [`impl_plan_chart_resolution_02_growth_chart.md`](./chart_resolution/impl_plan_chart_resolution_02_growth_chart.md) —
     `GrowthChart` (5 serie EUR-mode + 3 serie %-mode).
  4. [`impl_plan_chart_resolution_03_allocation_history.md`](./chart_resolution/impl_plan_chart_resolution_03_allocation_history.md)
     — `AllocationHistoryChart` (serie stacked dinamiche per categoria).
  5. [`impl_plan_chart_resolution_04_signals_overlay.md`](./chart_resolution/impl_plan_chart_resolution_04_signals_overlay.md)
     — dispatch downsample per i 9 tipi di segnale overlay (Bollinger = envelope, MACD = 3 serie).
  6. [`impl_plan_chart_resolution_05_badge_i18n.md`](./chart_resolution/impl_plan_chart_resolution_05_badge_i18n.md) —
     componente condiviso `ResolutionBadge` + nuove chiavi i18n (4 lingue) sotto il namespace `chart.*`.
  7. [`impl_plan_chart_resolution_06_compact_cards.md`](./chart_resolution/impl_plan_chart_resolution_06_compact_cards.md)
     — `PriceChartCompact`/`LineChart` (ramo compact) nelle card `AssetCard`/`FxCard` di `/assets` e `/fx`;
     caso **statico** (nessun `dataZoom`, ricalcolo su cambio dati/larghezza, niente isteresi/badge pill).

  Stato: ✅ disegno · ✅ studio raffinato · ✅ 7 piani implementativi · ⏳ implementazione (non ancora
  iniziata — solo documentazione fin qui, nessun file sorgente toccato).

## Guide rapide

| File | Descrizione |
|------|-------------|
| [`GUIDA-TOOLBAR-RESPONSIVE.md`](./GUIDA-TOOLBAR-RESPONSIVE.md) | ✅ Come tarare le soglie responsive (`PageToolbar`/`DateRangePicker`) — soglie per pagina, badge "jolly" auto-fit, tuning live da console browser (`window.__lfLayouts`), checklist per estendere il sistema a una nuova pagina |

## Piano principale

→ [`../../phases/phase-09-dashboard.md`](../../phases/phase-09-dashboard.md) — Macro plan ufficiale di
Phase 9.
