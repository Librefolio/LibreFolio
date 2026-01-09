# Phase 8: Dashboard

**Status**: ⏳ TODO  
**Durata**: 3 giorni  
**Priorità**: P1 (Important)
**Dipendenze**: Phase 4, 6, 7 (tutti i dati)

---

## Obiettivo

Creare la dashboard principale con KPI, grafici di portfolio growth, e asset allocation usando Apache ECharts.

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

**Componenti previsti per questa fase**:

- `KPICard.svelte` - Card KPI riutilizzabile
- `PortfolioChart.svelte` - Chart crescita portfolio (ECharts)
- `AllocationChart.svelte` - Donut chart allocazione (ECharts)
- `RangeSelector.svelte` - Selezione range temporale

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

