# Milestone 3 — UI Broker v2 (post Portfolio Engine unificato)

Questa cartella raccoglie il **redesign ad alto livello** delle pagine Broker (lista globale + dettaglio a
tab), aggiornato dopo il lavoro su Portfolio Engine e Dashboard Home documentato in
[`../plan_ui_dashboard.md`](../plan_ui_dashboard.md) e in
[`../Milestone_2/portfolio_engine/`](../Milestone_2/portfolio_engine/).

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
| 2 | [`plan_ui_broker_holdings.md`](./plan_ui_broker_holdings.md) | Tab Posizioni (riuso `PositionsPanel`) + Modale Lotti FIFO (bubble timeline + WAC/prezzo) | [`../plan_ui_broker_holdings.md`](../plan_ui_broker_holdings.md) | ✅ disegno · ⏳ piano implementativo |
| 3 | [`plan_ui_broker_transactions.md`](./plan_ui_broker_transactions.md) | Tab Transazioni (riuso `<TransactionsTable>`) + File Importati | [`../plan_ui_broker_transactions.md`](../plan_ui_broker_transactions.md) | ✅ disegno · ⏳ piano implementativo |

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

## Piano principale

→ [`../../phases/phase-09-dashboard.md`](../../phases/phase-09-dashboard.md) — Macro plan ufficiale di
Phase 9.
