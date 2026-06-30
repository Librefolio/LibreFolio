<!--
  ContributionTreemap — Dual gain/loss ECharts treemaps for period P&L contribution.

  Two vertically stacked treemaps:
  - GAINS: assets with period_pnl > 0 (green)
  - LOSSES: assets with period_pnl < 0 (red)

  Shared scale: container heights proportional to gross_gains / gross_losses vs scale_max.
  Hierarchy: Broker → AssetType → Asset.

  Pattern: ECharts lifecycle, Svelte 5 Runes, dark mode, data-testid.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_} from '$lib/i18n';
    import {buildTooltipTheme, buildTooltipRow, buildTooltipHeader} from '$lib/components/charts/echartsTooltipHelpers';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    interface Position {
        asset_id: number;
        asset_name: string;
        asset_type: string;
        broker_id: number;
        broker_name: string;
        period_pnl?: string | (string | null)[] | null;
        period_pnl_percent?: string | (string | null)[] | null;
    }

    interface Props {
        positions: Position[];
        grossGains: number;
        grossLosses: number;
        displayCurrency?: string;
        totalHeight?: number;
    }

    let {positions = [], grossGains = 0, grossLosses = 0, displayCurrency = 'EUR', totalHeight = 360}: Props = $props();

    let gainsContainer: HTMLDivElement | undefined = $state(undefined);
    let lossesContainer: HTMLDivElement | undefined = $state(undefined);
    let gainsChart: echarts.ECharts | null = null;
    let lossesChart: echarts.ECharts | null = null;
    let gainsObserver: ResizeObserver | null = null;
    let lossesObserver: ResizeObserver | null = null;

    function safeNum(v: string | (string | null)[] | null | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return isNaN(n) ? null : n;
    }

    const scaleMax = $derived(Math.max(grossGains, grossLosses) || 1);
    const gainsPct = $derived(grossGains / scaleMax);
    const lossesPct = $derived(grossLosses / scaleMax);
    const gainsHeight = $derived(Math.max(gainsPct * totalHeight * 0.85, grossGains > 0 ? 60 : 0));
    const lossesHeight = $derived(Math.max(lossesPct * totalHeight * 0.85, grossLosses > 0 ? 60 : 0));
    const hasGains = $derived(grossGains > 0);
    const hasLosses = $derived(grossLosses > 0);

    onMount(() => {
        const observer = new MutationObserver(() => {
            renderGains();
            renderLosses();
        });
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    function cleanup() {
        gainsObserver?.disconnect();
        lossesObserver?.disconnect();
        gainsChart?.dispose();
        lossesChart?.dispose();
        gainsChart = null;
        lossesChart = null;
    }

    $effect(() => {
        void positions;
        void grossGains;
        void grossLosses;
        tick().then(() => {
            renderGains();
            renderLosses();
        });
    });

    function buildTreeData(filter: 'gains' | 'losses'): any[] {
        const brokerMap = new Map<string, Map<string, any[]>>();

        for (const p of positions) {
            const pnl = safeNum(p.period_pnl);
            if (pnl == null || pnl === 0) continue;
            if (filter === 'gains' && pnl < 0) continue;
            if (filter === 'losses' && pnl > 0) continue;

            const bName = p.broker_name || 'Unknown';
            const aType = p.asset_type || 'Unknown';

            if (!brokerMap.has(bName)) brokerMap.set(bName, new Map());
            const typeMap = brokerMap.get(bName)!;
            if (!typeMap.has(aType)) typeMap.set(aType, []);

            typeMap.get(aType)!.push({
                name: p.asset_name,
                value: Math.abs(pnl),
                _meta: {broker: bName, type: aType, pnl, pnlPct: safeNum(p.period_pnl_percent)},
            });
        }

        const tree: any[] = [];
        for (const [broker, typeMap] of brokerMap) {
            const children: any[] = [];
            for (const [type, assets] of typeMap) {
                children.push({name: type, children: assets});
            }
            tree.push({name: broker, children});
        }
        return tree;
    }

    function makeTooltip(isDark: boolean) {
        const theme = buildTooltipTheme(isDark);
        return {
            formatter: (params: any) => {
                const meta = params.data?._meta;
                if (!meta) return params.name;
                const pnlColor = meta.pnl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : (isDark ? '#f87171' : '#dc2626');
                let html = buildTooltipHeader(meta.broker, theme.textColor);
                html += buildTooltipRow(meta.type, params.name);
                html += buildTooltipRow($_('dashboard.periodPnl'), `<span style="color:${pnlColor}">${formatCurrencyAmountPlain(meta.pnl, displayCurrency, {showSign: true})}</span>`);
                if (meta.pnlPct != null) {
                    html += buildTooltipRow('', `${(meta.pnlPct * 100).toFixed(2)}%`);
                }
                return `<div style="font-size:11px;color:${theme.textColor}">${html}</div>`;
            },
            backgroundColor: theme.bg,
            borderColor: theme.border,
            textStyle: {color: theme.textColor},
        };
    }

    function makeOptions(data: any[], color: string, isDark: boolean): any {
        return {
            tooltip: makeTooltip(isDark),
            series: [{
                type: 'treemap',
                data,
                width: '100%',
                height: '100%',
                roam: false,
                nodeClick: false,
                breadcrumb: {show: false},
                upperLabel: {
                    show: true,
                    height: 18,
                    color: isDark ? '#e2e8f0' : '#334155',
                    fontSize: 10,
                    backgroundColor: isDark ? 'rgba(30,41,59,0.8)' : 'rgba(248,250,252,0.8)',
                },
                label: {
                    show: true,
                    formatter: (p: any) => {
                        const meta = p.data?._meta;
                        if (!meta) return p.name;
                        return `${p.name}\n${formatCurrencyAmountPlain(meta.pnl, displayCurrency, {showSign: true})}`;
                    },
                    fontSize: 10,
                    color: '#fff',
                    textShadowColor: 'rgba(0,0,0,0.5)',
                    textShadowBlur: 2,
                    lineHeight: 14,
                },
                itemStyle: {color, borderColor: isDark ? '#334155' : '#e2e8f0'},
                levels: [
                    {itemStyle: {borderWidth: 2, gapWidth: 2}},
                    {itemStyle: {borderWidth: 1, gapWidth: 1}},
                    {itemStyle: {borderWidth: 0, gapWidth: 1}},
                ],
            }],
        };
    }

    function renderGains() {
        if (!gainsContainer || !hasGains) return;
        const isDark = document.documentElement.classList.contains('dark');
        if (!gainsChart) {
            gainsChart = echarts.init(gainsContainer);
            gainsObserver = new ResizeObserver(() => gainsChart?.resize());
            gainsObserver.observe(gainsContainer);
        }
        const data = buildTreeData('gains');
        const color = isDark ? '#22c55e' : '#16a34a';
        gainsChart.setOption(makeOptions(data, color, isDark), true);
    }

    function renderLosses() {
        if (!lossesContainer || !hasLosses) return;
        const isDark = document.documentElement.classList.contains('dark');
        if (!lossesChart) {
            lossesChart = echarts.init(lossesContainer);
            lossesObserver = new ResizeObserver(() => lossesChart?.resize());
            lossesObserver.observe(lossesContainer);
        }
        const data = buildTreeData('losses');
        const color = isDark ? '#ef4444' : '#dc2626';
        lossesChart.setOption(makeOptions(data, color, isDark), true);
    }
</script>

<div class="space-y-2" data-testid="contribution-treemap">
    <!-- Scale label -->
    <p class="text-[10px] text-gray-400 dark:text-gray-500 text-center">
        {$_('dashboard.sharedScale')}
    </p>

    {#if hasGains}
        <div>
            <p class="text-xs font-medium text-green-600 dark:text-green-400 mb-1">
                {$_('dashboard.gains')} {formatCurrencyAmountPlain(grossGains, displayCurrency, {showSign: true})}
            </p>
            <div bind:this={gainsContainer} style="width:100%;height:{gainsHeight}px" data-testid="contribution-treemap-gains"></div>
        </div>
    {/if}

    {#if hasLosses}
        <div>
            <p class="text-xs font-medium text-red-500 dark:text-red-400 mb-1">
                {$_('dashboard.losses')} {formatCurrencyAmountPlain(grossLosses, displayCurrency, {showSign: false})}
            </p>
            <div bind:this={lossesContainer} style="width:100%;height:{lossesHeight}px" data-testid="contribution-treemap-losses"></div>
        </div>
    {/if}

    {#if !hasGains && !hasLosses}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-6 text-center">
            {$_('dashboard.noPeriodPnl')}
        </p>
    {/if}
</div>
