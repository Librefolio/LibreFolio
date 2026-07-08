# Phase 9: Dashboard

**Status**: ✅ Completato (Milestone 1 & 2) · ⏳ In corso (Milestone 3 — Redesign UI Broker v2)
**Sub-plans archiviati (M1 & M2)**: [`./phase-09-subplan/README.md`](./phase-09-subplan/README.md)
**Sub-plans attivi (M3)**: [`../phase-09-subplan/README.md`](../phase-09-subplan/README.md)
**Durata**: ~5 giorni (aggiornata)  
**Priorità**: P1 (Important)  
**Dipendenze**: Phase 4.8 (share_percentage per aggregazione), Phase 5 (PriceChartShared), Phase 6, Phase 7 (tutti i dati)

> **📊 WAC Analytics (2026-05-28)**: Il calcolo WAC iterativo è già implementato e testato
> (28 backend tests, `compute_wac_iterative` in `transaction_service.py`, `compute_wac_from_txlist`
> in `financial_utils.py`). L'attuale `/transactions/wac-preview` verrà migrato verso un endpoint
> analytics dedicato (`POST /api/v1/analytics/wac`) per serie temporali WAC — utile per:
> - Overlay WAC su price chart (linea entry price)
> - P&L storico (realized gains = sell_price − WAC)
> - Portfolio KPI (average entry price per holding)
>
> Il flusso workspace editing (validate/commit) integra già il calcolo WAC inline (nessun endpoint
> separato necessario). Vedi [`plan-WacInlineValidateCommit.prompt.md`](../PlanD_SplitPromoteFullStack/R2-WalktestFeedback/SP-C-Bugfix/WacPreview/plan-WacInlineValidateCommit.prompt.md).

> **🧪 Coverage gap (2026-06-02)**: `analytics_wac` in `backend/app/api/v1/analytics.py` ha 0%
> coverage (25 statements). L'endpoint è una predisposizione: diventerà testabile quando il
> sistema analytics sarà sviluppato in questa fase. **TODO**: creare
> `backend/test_scripts/test_api/test_analytics_api.py` con test per `POST /api/v1/analytics/wac`
> (serie temporali WAC per asset, multi-currency, edge cases empty portfolio).

> **📌 Riferimento principale**: [`plan-phase05-to-08-upgrade.md` §8](../plan-phase05-to-08-upgrade.md)
> Questa sezione è stata **SUPERATA** dal piano aggiornato. Quando si arriva a implementare Phase 8,
> ripartire da §8 di `plan-phase05-to-08-upgrade.md` che contiene:
> - **Step 8.1**: `KPICard` — NAV/PnL/ROI calcolati con `share_percentage` pesato (formula: `NAV_utente = Σ(NAV_broker × share%)`)
> - **Step 8.2**: `PortfolioChart` — due serie ECharts (investito vs mercato), range selector
> - **Step 8.3**: `AssetDualAxisChart` — dual Y-axis: prezzo asset a sinistra, gain/loss per transazione a destra, linea cumulativa con area, sell events come markPoints (frecce ↓)
> - **Step 8.4**: `AllocationChart` — ECharts donut, raggruppamento per asset_type
> - **Step 8.5**: `RecentTransactions` + `QuickActions` — ultime 10 tx con DataTable compatto, bottoni azioni rapide
>
> **Componenti da riusare**:
> `PriceChartShared` (Phase 5), `FiscalRegimeSelect` (Phase 7), `DataTable`, `ModalBase`, `SearchSelect`, `SimpleSelect`
>
> **Novità cruciali rispetto a questo vecchio plan**:
> - **Aggregazione GDPR-pesata**: valori assoluti × share_percentage, MAI media di percentuali ROI
> - EDITOR con share 0% → il broker NON compare nel Net Worth
> - VIEWER con share 0% → vede tx ma non impatta patrimonio
> - Warning se Σ(share%) > 100% → "sovrastima patrimonio"
> - `AnalyticsMethodSelect` per FIFO/LIFO/PMC — solo vista analitica, disclaimer PMC sempre presente
> - `AssetDualAxisChart` con sell arrows come ECharts markPoints
> - **API NUOVO**: `GET /api/v1/portfolio/overview` per aggregazione pesata

---

## Obiettivo

Riprogettazione completa della Dashboard Home e delle schermate di dettaglio del Broker, unificando le analisi matematiche e standardizzando le API sotto la famiglia `/portfolio`.

---

## 📂 Piano Implementativo e Sub-Plans

Lo sviluppo e l'architettura di questa fase sono stati dettagliati in una serie di documenti dedicati. Questi documenti sostituiscono completamente le indicazioni legacy presenti più in basso in questo file.

### Documenti Architetturali e di Processo — Milestone 1 & 2 ✅ (archiviati in [`phase-09-subplan/`](./phase-09-subplan/README.md))
* **`implementation_roadmap.md`**: Scompone il lavoro in Milestone Sequenziali e verificabili (1. Backend/API, 2. Dashboard Home).
* **`plan_financial_algorithms.md`**: Documento di dettaglio matematico/algoritmico per l'implementazione dei servizi finanziari (TWRR, MWRR e interazioni con WAC), con gestione edge-case.

### Documenti di Design dell'Interfaccia — Milestone 1 & 2 ✅ (archiviati in [`phase-09-subplan/`](./phase-09-subplan/README.md))
* **`plan_ui_dashboard.md`**: Design della Home principale. KPI Cards, filtro Multi-Broker, Grafico a torta/Mappa e Grafico storico della crescita (Investito, Liquidità, NAV).

### Documenti — Milestone 3 ⏳ in corso (attivi in [`../phase-09-subplan/`](../phase-09-subplan/README.md))
* **`implementation_plan.md`**: Analizza il gap architetturale tra l'attuale (FastAPI/SvelteKit) e il desiderato, chiarendo il passaggio all'uso unificato di `portfolio_service.py` per le metriche sia di portfolio globale che del singolo broker (copre sia M1/M2 sia M3 — riferimento condiviso, non archiviato).
* **`Milestone_3/plan_ui_broker_overview.md`** (v2, supersede il disegno originale): Design del Tab 1 "Panoramica" all'interno del singolo broker. Riutilizza gli stessi componenti della Dashboard filtrando per il `broker_id` corrente.
* **`Milestone_3/plan_ui_broker_holdings.md`** (v2, supersede il disegno originale): Design del Tab 2 "Posizioni". Tabella delle quote detenute e Modale "Slide-over" con lo spaccato dei lotti aperti/chiusi (logica FIFO) e la serie storica del WAC.
* **`Milestone_3/plan_ui_broker_transactions.md`** (v2, supersede il disegno originale): Design del Tab 3 "Transazioni e Storico File". Riuso della `TransactionsTable` unito allo storico dei report BRIM importati.

---

## 📈 Summary dello Sviluppo (Work in Progress)

- [x] **Milestone 1**: Fondamenta Backend e API di Portafoglio (TWRR, MWRR, endpoint unificati) — ✅ completata, archiviata
- [x] **Milestone 2**: Dashboard Home (Positions/Performance panel, Portfolio Engine, GrowthChart, Allocation history) — ✅ completata, archiviata
- [ ] **Milestone 3**: Redesign UI Broker v2 (Panoramica, Posizioni & Lotti FIFO, Transazioni & File) — ⏳ in corso, vedi [`../phase-09-subplan/Milestone_3/README.md`](../phase-09-subplan/Milestone_3/README.md)


---

## ⚠️ Nota: Plan Originale (Legacy)

Il contenuto sotto è il **plan originale** scritto prima delle fasi 4.5–4.8. I componenti UI suggeriti
andranno **riscritti** usando i componenti unificati (DataTable, ModalBase, etc.) e con la logica di
aggregazione pesata (share_percentage). Fare riferimento a §8 di `plan-phase05-to-08-upgrade.md` per
la versione aggiornata.

**Componenti previsti per questa fase (aggiornati)**:

- `KPICard.svelte` - Card KPI con NAV/PnL/ROI pesati + trend e breakdown
- `PortfolioChart.svelte` - Chart crescita portfolio (ECharts, investito vs mercato)
- `AssetDualAxisChart.svelte` - Dual Y-axis per-tx gain/loss (ECharts)
- `AllocationChart.svelte` - Donut chart allocazione (ECharts)
- `AnalyticsMethodSelect.svelte` - Selettore metodo analitico (FIFO/LIFO/PMC)
- `RangeSelector.svelte` - Selezione range temporale
- `RecentTransactions.svelte` - Ultime transazioni con DataTable compatto
- `QuickActions.svelte` - Bottoni azioni rapide

---

## 8.1 Dashboard Overview (3 giorni)

### Tasks

- [ ] Creare `src/routes/(app)/dashboard/+page.svelte`
- [ ] Creare `src/routes/(app)/dashboard/+page.ts`
- [ ] Creare KPI cards
- [ ] Creare Portfolio Growth chart (ECharts)
- [ ] Creare Asset Allocation chart (ECharts donut)
- [ ] Creare Recent Transactions widget
- [ ] Creare Quick Actions

### Load Function

```typescript
// src/routes/(app)/dashboard/+page.ts
export async function load() {
    // Per MVP: aggregare da endpoint esistenti
    // Future: dedicato /portfolio/overview endpoint

    const [brokers, transactions, assets] = await Promise.all([
        api.get('/brokers'),
        api.get('/transactions?limit=10'),
        api.get('/assets/query?active=true')
    ]);

    return {brokers, transactions, assets};
}
```

### Page Layout

```svelte
<!-- src/routes/(app)/dashboard/+page.svelte -->
<div class="dashboard">
  <h1>Dashboard</h1>
  
  <!-- KPI Cards Row -->
  <div class="kpi-row grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
    <KPICard 
      title="Total Net Worth"
      value={formatCurrency(totalNetWorth, baseCurrency)}
      change={dailyChange}
      trend="up"
    />
    <KPICard 
      title="Weighted ROI"
      value={formatPercent(weightedROI)}
      period={roiPeriod}
      on:periodChange={(e) => roiPeriod = e.detail}
    />
    <KPICard 
      title="Available Cash"
      value={formatCurrency(totalCash, baseCurrency)}
      breakdown={cashBreakdown}
    />
  </div>
  
  <!-- Charts Row -->
  <div class="charts-row grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
    <!-- Portfolio Growth (2 cols) -->
    <div class="lg:col-span-2 bg-white rounded-lg shadow p-4">
      <div class="flex justify-between items-center mb-4">
        <h3>Portfolio Growth</h3>
        <RangeSelector bind:value={portfolioRange} />
      </div>
      <PortfolioChart 
        investedData={investedSeries}
        marketData={marketSeries}
        currency={baseCurrency}
      />
    </div>
    
    <!-- Asset Allocation (1 col) -->
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="mb-4">Asset Allocation</h3>
      <AllocationChart data={allocationData} />
    </div>
  </div>
  
  <!-- Bottom Row -->
  <div class="bottom-row grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Recent Transactions (2 cols) -->
    <div class="lg:col-span-2 bg-white rounded-lg shadow p-4">
      <div class="flex justify-between items-center mb-4">
        <h3>Recent Transactions</h3>
        <a href="/transactions" class="text-libre-green hover:underline">View All →</a>
      </div>
      <RecentTransactions transactions={recentTransactions} />
    </div>
    
    <!-- Quick Actions (1 col) -->
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="mb-4">Quick Actions</h3>
      <QuickActions />
    </div>
  </div>
</div>
```

### KPI Card Component

```svelte
<!-- KPICard.svelte -->
<div class="kpi-card bg-white rounded-lg shadow p-6">
  <div class="title text-gray-600 text-sm mb-1">{title}</div>
  <div class="value text-2xl font-bold">{value}</div>
  
  {#if change !== undefined}
    <div class="change flex items-center gap-1 mt-2" class:text-green-600={change >= 0} class:text-red-600={change < 0}>
      <span>{change >= 0 ? '↑' : '↓'}</span>
      <span>{formatPercent(Math.abs(change))}</span>
      <span class="text-gray-400 text-sm">today</span>
    </div>
  {/if}
  
  {#if breakdown}
    <details class="mt-2">
      <summary class="text-sm text-gray-500 cursor-pointer">Breakdown</summary>
      <ul class="mt-2 text-sm">
        {#each Object.entries(breakdown) as [currency, amount]}
          <li>{getFlag(currency)} {formatCurrency(amount, currency)}</li>
        {/each}
      </ul>
    </details>
  {/if}
  
  {#if period !== undefined}
    <div class="period-selector mt-2 flex gap-1">
      {#each ['1M', '3M', '6M', '1Y', 'ALL'] as p}
        <button 
          class="text-xs px-2 py-1 rounded"
          class:bg-libre-green={period === p}
          class:text-white={period === p}
          on:click={() => dispatch('periodChange', p)}
        >
          {p}
        </button>
      {/each}
    </div>
  {/if}
</div>
```

### Portfolio Chart (ECharts)

```svelte
<!-- PortfolioChart.svelte -->
<script>
  import * as echarts from 'echarts';
  import { onMount, onDestroy } from 'svelte';
  
  export let investedData: { date: string; value: number }[];
  export let marketData: { date: string; value: number }[];
  export let currency: string = 'EUR';
  
  let container: HTMLDivElement;
  let chart: echarts.ECharts;
  
  onMount(() => {
    chart = echarts.init(container);
    updateChart();
    
    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  });
  
  onDestroy(() => chart?.dispose());
  
  $: if (chart && investedData && marketData) updateChart();
  
  function updateChart() {
    const dates = marketData.map(d => d.date);
    
    chart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const date = params[0].axisValue;
          const invested = params[0].value;
          const market = params[1].value;
          const pnl = market - invested;
          const pnlPercent = (pnl / invested * 100).toFixed(2);
          return `
            <strong>${date}</strong><br/>
            Invested: ${formatCurrency(invested, currency)}<br/>
            Market: ${formatCurrency(market, currency)}<br/>
            P&L: ${formatCurrency(pnl, currency)} (${pnlPercent}%)
          `;
        }
      },
      legend: {
        data: ['Invested', 'Market Value'],
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { rotate: 45 }
      },
      yAxis: {
        type: 'value',
        name: currency,
        axisLabel: { formatter: (v) => formatCompact(v) }
      },
      series: [
        {
          name: 'Invested',
          type: 'line',
          data: investedData.map(d => d.value),
          smooth: true,
          itemStyle: { color: '#1A4D3E' },
          lineStyle: { width: 2 }
        },
        {
          name: 'Market Value',
          type: 'line',
          data: marketData.map(d => d.value),
          smooth: true,
          itemStyle: { color: '#A8D5BA' },
          lineStyle: { width: 2 },
          areaStyle: { 
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(168, 213, 186, 0.4)' },
              { offset: 1, color: 'rgba(168, 213, 186, 0.1)' }
            ])
          }
        }
      ]
    });
  }
</script>

<div class="chart-container h-80" bind:this={container}></div>
```

### Allocation Chart (ECharts Donut)

```svelte
<!-- AllocationChart.svelte -->
<script>
  import * as echarts from 'echarts';
  import { onMount, onDestroy } from 'svelte';
  
  export let data: { name: string; value: number; color?: string }[];
  
  let container: HTMLDivElement;
  let chart: echarts.ECharts;
  
  // Color palette
  const COLORS = ['#1A4D3E', '#A8D5BA', '#4A7C6F', '#7FB3A1', '#2E6B54', '#C5DED3'];
  
  onMount(() => {
    chart = echarts.init(container);
    updateChart();
    
    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  });
  
  onDestroy(() => chart?.dispose());
  
  $: if (chart && data) updateChart();
  
  function updateChart() {
    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center'
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold'
            }
          },
          labelLine: { show: false },
          data: data.map((d, i) => ({
            name: d.name,
            value: d.value,
            itemStyle: { color: d.color || COLORS[i % COLORS.length] }
          }))
        }
      ]
    });
  }
</script>

<div class="chart-container h-64" bind:this={container}></div>
```

### Recent Transactions Widget

```svelte
<!-- RecentTransactions.svelte -->
<table class="w-full text-sm">
  <tbody>
    {#each transactions as tx}
      <tr class="border-b last:border-0">
        <td class="py-2">
          <Badge variant={getTypeVariant(tx.type)} size="sm">
            {tx.type}
          </Badge>
        </td>
        <td class="py-2 text-gray-600">{formatDate(tx.date)}</td>
        <td class="py-2">{tx.asset?.display_name || '-'}</td>
        <td class="py-2 text-right" class:text-green-600={tx.cash?.amount > 0} class:text-red-600={tx.cash?.amount < 0}>
          {tx.cash ? formatCurrency(tx.cash.amount, tx.cash.code) : '-'}
        </td>
      </tr>
    {/each}
  </tbody>
</table>
```

### Quick Actions Widget

```svelte
<!-- QuickActions.svelte -->
<div class="quick-actions flex flex-col gap-3">
  <button 
    class="action-btn flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 text-left"
    on:click={() => showAddTransactionModal = true}
  >
    <span class="icon text-2xl">➕</span>
    <div>
      <div class="font-medium">Add Transaction</div>
      <div class="text-sm text-gray-500">Record buy, sell, dividend...</div>
    </div>
  </button>
  
  <button 
    class="action-btn flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 text-left"
    on:click={() => goto('/transactions/import')}
  >
    <span class="icon text-2xl">📄</span>
    <div>
      <div class="font-medium">Import Broker Report</div>
      <div class="text-sm text-gray-500">Upload CSV from your broker</div>
    </div>
  </button>
  
  <button 
    class="action-btn flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 text-left"
    on:click={() => showAddAssetModal = true}
  >
    <span class="icon text-2xl">📊</span>
    <div>
      <div class="font-medium">Add Asset</div>
      <div class="text-sm text-gray-500">Search and add new asset</div>
    </div>
  </button>
</div>
```

### File da Creare

| File                                                     | Descrizione    |
|----------------------------------------------------------|----------------|
| `src/routes/(app)/dashboard/+page.svelte`                | Dashboard page |
| `src/routes/(app)/dashboard/+page.ts`                    | Load function  |
| `src/lib/components/dashboard/KPICard.svelte`            | KPI card       |
| `src/lib/components/dashboard/PortfolioChart.svelte`     | Growth chart   |
| `src/lib/components/dashboard/AllocationChart.svelte`    | Donut chart    |
| `src/lib/components/dashboard/RecentTransactions.svelte` | Lista tx       |
| `src/lib/components/dashboard/QuickActions.svelte`       | Azioni rapide  |
| `src/lib/components/dashboard/RangeSelector.svelte`      | Time range     |

---

## Data Aggregation (MVP)

Per MVP, i dati sono calcolati client-side:

```typescript
// src/lib/utils/portfolio.ts
export function calculateTotalCash(brokers: Broker[]) {
    return brokers.reduce((total, broker) => {
        return total + Object.values(broker.cash_balances || {}).reduce((sum, amt) => sum + amt, 0);
    }, 0);
}

export function calculateAllocation(assets: Asset[], transactions: Transaction[]) {
    // Raggruppa per asset_type
    const byType: Record<string, number> = {};
    // ... logica di aggregazione
    return Object.entries(byType).map(([name, value]) => ({name, value}));
}
```

**Nota**: In futuro, questi calcoli dovranno essere fatti backend per performance e precisione. Sarà necessario un nuovo endpoint `/api/v1/portfolio/overview`.

---

## Verifica Completamento

### Test Manuali

- [ ] Dashboard carica senza errori
- [ ] KPI cards mostrano valori corretti
- [ ] Portfolio chart renderizza (anche con dati vuoti)
- [ ] Allocation chart renderizza
- [ ] Recent transactions mostra ultime 10
- [ ] Quick actions aprono modali/pagine corrette
- [ ] Range selector cambia dati chart
- [ ] Responsive su mobile

---

## Dipendenze

- **Richiede**: Phase 4, 6, 7 (dati da visualizzare)
- **Sblocca**: Nessuna (feature finale)

