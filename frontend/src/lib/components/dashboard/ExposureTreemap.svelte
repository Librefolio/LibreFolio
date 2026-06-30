<!--
  ExposureTreemap — ECharts treemap for portfolio exposure.

  Hierarchy: Broker → Asset Type → Asset.
  Area = current_value, color = gain_loss_percent (red→green gradient).
  Tooltip: asset name, broker, type, value, NAV weight, unrealized P&L.

  Pattern: ECharts lifecycle (init, MutationObserver, ResizeObserver),
  Svelte 5 Runes, dark mode, data-testid.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_} from '$lib/i18n';
    import {buildTooltipTheme, buildTooltipRow, buildTooltipHeader, buildTooltipDivider} from '$lib/components/charts/echartsTooltipHelpers';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getBrokerInfo} from '$lib/stores/reference/brokerStore';

    interface Holding {
        asset_id: number;
        asset_name: string;
        asset_type: string;
        broker_id?: number | (number | null)[] | null;
        broker_name?: string | (string | null)[] | null;
        current_value?: string | (string | null)[] | null;
        nav_weight_percent?: string | (string | null)[] | null;
        gain_loss?: string | (string | null)[] | null;
        gain_loss_percent?: string | (string | null)[] | null;
    }

    interface Props {
        holdings: Holding[];
        displayCurrency?: string;
        height?: string;
    }

    let {holdings = [], displayCurrency = 'EUR', height = '320px'}: Props = $props();

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;

    function safeNum(v: string | (string | null)[] | null | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return isNaN(n) ? null : n;
    }

    function safeInt(v: number | (number | null)[] | null | undefined): number | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    function safeStr(v: string | (string | null)[] | null | undefined): string | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    onMount(() => {
        const observer = new MutationObserver(() => renderChart());
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    function cleanup() {
        resizeObserver?.disconnect();
        chartInstance?.dispose();
        chartInstance = null;
    }

    $effect(() => {
        void holdings;
        void displayCurrency;
        tick().then(() => renderChart());
    });

    function buildTreeData(): any[] {
        // Group: Broker → AssetType → Asset
        const brokerMap = new Map<string, Map<string, any[]>>();

        for (const h of holdings) {
            const val = safeNum(h.current_value);
            if (val == null || val <= 0) continue;

            const bid = safeInt(h.broker_id);
            const bName = safeStr(h.broker_name) || (bid ? getBrokerInfo(bid)?.name : null) || 'Unknown';
            const aType = h.asset_type || 'Unknown';

            if (!brokerMap.has(bName)) brokerMap.set(bName, new Map());
            const typeMap = brokerMap.get(bName)!;
            if (!typeMap.has(aType)) typeMap.set(aType, []);

            const glPct = safeNum(h.gain_loss_percent);
            const gl = safeNum(h.gain_loss);
            const weight = safeNum(h.nav_weight_percent);

            typeMap.get(aType)!.push({
                name: h.asset_name,
                value: val,
                itemStyle: {color: pnlColor(glPct)},
                _meta: {
                    assetId: h.asset_id,
                    broker: bName,
                    type: aType,
                    value: val,
                    weight,
                    gl,
                    glPct,
                },
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

    function pnlColor(pct: number | null): string {
        if (pct == null) return '#6b7280';
        const isDark = document.documentElement.classList.contains('dark');
        if (pct >= 0) {
            const intensity = Math.min(pct * 100, 50) / 50;
            return isDark
                ? `rgb(${34 + intensity * 40}, ${197 + intensity * 40}, ${94 + intensity * 40})`
                : `rgb(${22 - intensity * 10}, ${163 - intensity * 30}, ${74 + intensity * 20})`;
        }
        const intensity = Math.min(Math.abs(pct * 100), 50) / 50;
        return isDark
            ? `rgb(${248}, ${113 - intensity * 40}, ${113 - intensity * 40})`
            : `rgb(${220 + intensity * 20}, ${38 + intensity * 20}, ${38 + intensity * 20})`;
    }

    function renderChart() {
        if (!chartContainer) return;
        const isDark = document.documentElement.classList.contains('dark');

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer);
            resizeObserver = new ResizeObserver(() => chartInstance?.resize());
            resizeObserver.observe(chartContainer);
        }

        const theme = buildTooltipTheme(isDark);
        const data = buildTreeData();

        if (data.length === 0) {
            chartInstance.clear();
            return;
        }

        chartInstance.setOption({
            tooltip: {
                formatter: (params: any) => {
                    const meta = params.data?._meta;
                    if (!meta) return params.name;
                    let html = buildTooltipHeader(meta.broker, theme.textColor);
                    html += buildTooltipRow($_('common.asset'), meta.assetId ? meta.name ?? '' : params.name);
                    html += buildTooltipRow($_('common.type'), meta.type);
                    html += buildTooltipRow($_('common.value'), formatCurrencyAmountPlain(meta.value, displayCurrency));
                    if (meta.weight != null) html += buildTooltipRow($_('dashboard.navWeight'), `${meta.weight.toFixed(1)}%`);
                    html += buildTooltipDivider(theme.border);
                    if (meta.gl != null) {
                        const glColor = meta.gl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : (isDark ? '#f87171' : '#dc2626');
                        html += buildTooltipRow($_('dashboard.unrealizedPnl'), `<span style="color:${glColor}">${formatCurrencyAmountPlain(meta.gl, displayCurrency, {showSign: true})}</span>`);
                    }
                    if (meta.glPct != null) {
                        html += buildTooltipRow('', `${(meta.glPct * 100).toFixed(2)}%`);
                    }
                    return `<div style="font-size:11px;color:${theme.textColor}">${html}</div>`;
                },
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor},
            },
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
                    height: 20,
                    color: isDark ? '#e2e8f0' : '#334155',
                    fontSize: 10,
                    backgroundColor: isDark ? 'rgba(30,41,59,0.8)' : 'rgba(248,250,252,0.8)',
                },
                label: {
                    show: true,
                    formatter: '{b}',
                    fontSize: 10,
                    color: '#fff',
                    textShadowColor: 'rgba(0,0,0,0.5)',
                    textShadowBlur: 2,
                },
                levels: [
                    {itemStyle: {borderWidth: 2, borderColor: isDark ? '#334155' : '#e2e8f0', gapWidth: 2}},
                    {itemStyle: {borderWidth: 1, borderColor: isDark ? '#475569' : '#cbd5e1', gapWidth: 1}},
                    {itemStyle: {borderWidth: 0, gapWidth: 1}},
                ],
            }],
        }, true);
    }
</script>

<div bind:this={chartContainer} style="width:100%;height:{height}" data-testid="exposure-treemap"></div>
