<!--
  AllocationPieChart — Pie chart for allocation distribution (sector or asset type).

  Supports two modes:
  - 'sector' (default): uses emoji from backend AllocationItem; shows emoji inside each slice
  - 'type': translates asset-type keys via assets.types.*; shows the PNG icon
    inside each slice (ECharts rich text), icon + label in legend and tooltip.

  Props:
  - data: AllocationEntry[] — name, value (0-100%), amount (abs), optional emoji
  - height: CSS height (default "280px")
  - mode: 'sector' | 'type' (default 'sector')
  - currency: currency code for absolute value formatting (default 'EUR')

  Used by:
  - Dashboard page (allocation panel, both type and sector tabs)
  - Asset Detail Page (metadata section, sector distribution)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_ANIMATION_CONFIG} from '$lib/components/charts/echartsAnimationConfig';
    import {scheduleFirstRenderStabilityFix, tooltipPositionAboveFinger} from '$lib/components/charts/echartsTooltipHelpers';
    import {_ as t} from '$lib/i18n';
    import {sectorI18nKey, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    // =========================================================================
    // Types & Props
    // =========================================================================

    export interface AllocationEntry {
        name: string;
        /** Percentage share 0-100 */
        value: number;
        /** Absolute amount in base currency */
        amount: number;
        /** Emoji from backend (sectors) */
        emoji?: string | null;
    }

    interface Props {
        /** Allocation data array from backend AllocationItem[] */
        data: AllocationEntry[];
        /** CSS height of the chart container */
        height?: string;
        /** Display mode: 'sector' uses backend emoji + i18n labels; 'type' uses asset type PNG icons */
        mode?: 'sector' | 'type';
        /**
         * Legend placement strategy.
         * - 'auto' (default): legend on the right when wide, below when narrow (<400px)
         * - 'bottom': legend always below the pie (better for constrained-height panels)
         */
        legendPosition?: 'auto' | 'bottom';
        /** Currency code for absolute amount formatting */
        currency?: string;
    }

    let {data = [], height = '280px', mode = 'sector', legendPosition = 'auto', currency = 'EUR'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let lastDark: boolean | null = null;
    let chartFullyInitialized = false;
    // Tracks the distinct set of raw type keys (mode='type') used to build richStyles
    // during the last FULL render — the fast-path data-only update below must NOT be
    // taken if the current data introduces a type not covered by that set, otherwise its
    // icon (and, previously, its translation via a since-removed name-based fallback)
    // would never be registered until some unrelated full rebuild (dark mode/resize).
    let lastRawTypeKeys = '';
    let needsInitialLayoutStabilityPass = false;

    // Diversified color palette — high chromatic distance
    const PALETTE_LIGHT = ['#1a4031', '#2563eb', '#7c3aed', '#dc2626', '#d97706', '#0d9488', '#be185d', '#4f46e5', '#059669', '#ea580c', '#6366f1', '#0891b2', '#ca8a04', '#9333ea'];
    const PALETTE_DARK = ['#4ade80', '#60a5fa', '#a78bfa', '#f87171', '#fbbf24', '#2dd4bf', '#f472b6', '#818cf8', '#34d399', '#fb923c', '#a5b4fc', '#22d3ee', '#facc15', '#c084fc'];

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        const observer = new MutationObserver(() => renderChart());
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    $effect(() => {
        if (chartContainer && data) {
            tick().then(() => {
                setupResizeObserver();
                renderChart();
            });
        }
    });

    function setupResizeObserver() {
        if (resizeObserver || !chartContainer) return;
        resizeObserver = new ResizeObserver(() => {
            // Container size affects layout (pieCenter/pieRadius/legend orientation) which
            // the fast-path below skips — force a full rebuild so resizing actually
            // repositions the chart. Skip the enter/update animation for this specific
            // call: a live window drag-resize can fire the observer many times in rapid
            // succession, and animating every intermediate frame (800ms update transition)
            // would queue up and look janky. Data/dark-mode driven rebuilds still animate
            // smoothly as before.
            chartFullyInitialized = false;
            renderChart({skipAnimation: true});
        });
        resizeObserver.observe(chartContainer);
    }

    function cleanup() {
        resizeObserver?.disconnect();
        resizeObserver = null;
        chartInstance?.dispose();
        chartInstance = null;
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart(opts: {skipAnimation?: boolean} = {}) {
        if (!chartContainer) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            needsInitialLayoutStabilityPass = true;
        }

        const isDark = document.documentElement.classList.contains('dark');
        const tr = $t;
        const palette = isDark ? PALETTE_DARK : PALETTE_LIGHT;

        const entries = data.filter((e) => e.value > 0);
        if (entries.length === 0) return; // Keep old chart visible, don't clear

        // Build chart data with name for ECharts diffing
        const chartData = entries
            .map((entry) => {
                let displayName: string;
                if (mode === 'sector') {
                    const i18nKey = `sectors.${sectorI18nKey(entry.name)}`;
                    const translated = tr(i18nKey) !== i18nKey ? tr(i18nKey) : entry.name.replace(/_/g, ' ');
                    const emoji = entry.emoji ?? '';
                    displayName = emoji ? `${emoji} ${translated}` : translated;
                } else {
                    // Bugfix: namespace is plural "assets.types.X" (matches en.json) — the
                    // singular "asset.types.X" key does not exist, so this translation was
                    // silently failing and falling back to the raw untranslated type string.
                    const typeKey = `assets.types.${entry.name.toUpperCase()}`;
                    const translated = tr(typeKey);
                    displayName = translated !== typeKey ? translated : entry.name;
                }
                return {name: displayName, value: entry.value, amount: entry.amount, rawName: entry.name, emoji: entry.emoji ?? ''};
            })
            .sort((a, b) => b.value - a.value);

        // Data-only update when chart is already initialized, dark mode hasn't changed,
        // AND (mode='type' only) no new asset type has appeared since the last full
        // build — a new type needs richStyles/legend/label formatters rebuilt so its
        // icon actually registers (see lastRawTypeKeys declaration above for why).
        const currentRawTypeKeys = mode === 'type' ? [...new Set(chartData.map((d) => d.rawName.toUpperCase()))].sort().join(',') : '';
        const sameTypeSet = mode !== 'type' || currentRawTypeKeys === lastRawTypeKeys;
        if (chartFullyInitialized && lastDark === isDark && sameTypeSet) {
            // Bugfix: preserve the FULL data item (not just {name, value}) — formatters
            // (tooltip especially) read params.data.rawName/amount, and stripping them
            // here silently broke the fallback path for any type whose translated name
            // does not equal its raw enum after uppercasing (e.g. IT/FR/ES "Crowdfunding" != "CROWDFUND").
            chartInstance.setOption({
                series: [{data: chartData}],
            });
            return;
        }
        lastRawTypeKeys = currentRawTypeKeys;

        // Build ECharts rich-text image styles for type mode (one key per asset type)
        const richStyles: Record<string, any> = {};
        // Bugfix: legend formatter only receives the (already-translated) display name
        // string from ECharts, not the full data item — build a lookup back to the raw
        // backend type key (e.g. "CROWDFUND") so it can re-translate/find the icon
        // correctly instead of re-deriving a key from the translated name itself (which
        // produced a mismatched key for languages whose translation differs from the
        // enum, e.g. IT/FR/ES "Crowdfunding" -> "CROWDFUNDING" != "CROWDFUND").
        const rawKeyByName: Record<string, string> = {};
        if (mode === 'type') {
            for (const {name, rawName} of chartData) {
                const safeKey = `img_${rawName.toUpperCase().replace(/[^A-Z_]/g, '')}`;
                richStyles[safeKey] = {
                    backgroundColor: {image: getAssetTypeIconUrl(rawName)},
                    width: 16,
                    height: 16,
                    align: 'center',
                };
                rawKeyByName[name] = rawName.toUpperCase().replace(/[^A-Z_]/g, '');
            }
        }

        // Responsive: narrow containers → legend below the pie
        const containerWidth = chartContainer.getBoundingClientRect().width;
        const isNarrow = containerWidth < 400;
        const legendBelow = legendPosition === 'bottom' || isNarrow;

        // Legend — always scrollable to avoid 4+ unwrapped rows
        const legendBaseTextStyle: any = {color: isDark ? '#94a3b8' : '#64748b', fontSize: 11};
        const legendTextStyle = mode === 'type' ? {...legendBaseTextStyle, rich: richStyles} : legendBaseTextStyle;

        const legendTypeExtras =
            mode === 'type'
                ? {
                      formatter: (name: string) => {
                          // Bugfix: look up the raw key from the translated name (see
                          // rawKeyByName above) instead of re-deriving it from `name`
                          // itself, which is already translated and would produce a
                          // mismatched key. Defensive fallback for safety.
                          const rawKey = rawKeyByName[name] ?? name.toUpperCase().replace(/[^A-Z_]/g, '');
                          const safeKey = `img_${rawKey}`;
                          const translated = tr(`assets.types.${rawKey}`) || name;
                          return `{${safeKey}|} ${translated}`;
                      },
                  }
                : {};

        const legendConfig: any = legendBelow
            ? {
                  ...legendTypeExtras,
                  type: 'scroll',
                  orient: 'horizontal',
                  bottom: 0,
                  left: 'center',
                  width: '95%',
                  textStyle: legendTextStyle,
                  pageTextStyle: {color: isDark ? '#94a3b8' : '#64748b', fontSize: 10},
                  pageIconColor: isDark ? '#94a3b8' : '#64748b',
                  pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
                  pageButtonGap: 4,
              }
            : {
                  ...legendTypeExtras,
                  type: 'scroll',
                  orient: 'vertical',
                  right: 10,
                  top: 20,
                  bottom: 20,
                  textStyle: legendTextStyle,
                  pageTextStyle: {color: isDark ? '#94a3b8' : '#64748b'},
                  pageIconColor: isDark ? '#94a3b8' : '#64748b',
                  pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
              };

        const pieCenter = legendBelow ? ['50%', '40%'] : ['35%', '50%'];
        const pieRadius = legendBelow ? ['25%', '55%'] : ['35%', '70%'];

        // Inner label — sector: emoji only (from data.emoji); type: PNG icon via rich text.
        const labelConfig: any =
            mode === 'sector'
                ? {
                      show: true,
                      position: 'inner',
                      // Show only the emoji (first token before the space in display name)
                      formatter: (params: any) => {
                          const first = (params.name as string).split(' ')[0];
                          // If it looks like an emoji (non-ASCII), use it; otherwise skip
                          return first && first.codePointAt(0)! > 127 ? first : '';
                      },
                      fontSize: 14,
                      backgroundColor: 'rgba(255, 255, 255, 0.75)',
                      borderRadius: 20,
                      padding: [4, 4],
                  }
                : {
                      show: true,
                      position: 'inner',
                      formatter: (params: any) => {
                          // Bugfix: use the raw backend type carried on the data item
                          // (params.data.rawName) instead of re-deriving a key from
                          // params.name (already translated — would produce a mismatched
                          // key for languages whose translation differs from the enum,
                          // e.g. IT/FR/ES "Crowdfunding" -> "CROWDFUNDING" != "CROWDFUND").
                          const rawSource = params.data?.rawName ?? params.name;
                          const rawKey = (rawSource as string).toUpperCase().replace(/[^A-Z_]/g, '');
                          return `{img_${rawKey}|}`;
                      },
                      rich: richStyles,
                      backgroundColor: 'rgba(255, 255, 255, 0.75)',
                      borderRadius: 20,
                      padding: [4, 4],
                  };

        // Build amount lookup by display name for tooltip
        const amountByName: Record<string, number> = {};
        for (const item of chartData) {
            amountByName[item.name] = item.amount;
        }

        // Tooltip — emoji + translated label + percentage + absolute amount (on new line)
        const tooltipFormatter = (params: any) => {
            const absAmount = amountByName[params.name];
            const amountLine = absAmount != null && absAmount > 0 ? `<br/><span style="font-size:11px;opacity:0.8">${formatCurrencyAmountPlain(absAmount, currency, {showSign: false})}</span>` : '';
            if (mode === 'type') {
                // Bugfix: same as above — use the raw backend type from the data item
                // rather than re-deriving from the already-translated params.name.
                const rawSource = params.data?.rawName ?? params.name;
                const rawKey = (rawSource as string).toUpperCase().replace(/[^A-Z_]/g, '');
                const translated = tr(`assets.types.${rawKey}`) || params.name;
                const iconUrl = getAssetTypeIconUrl(rawKey);
                return `<img src="${iconUrl}" style="width:14px;height:14px;vertical-align:middle;margin-right:5px;">${translated}: ${params.value}%${amountLine}`;
            }
            // Sector: display name already contains the emoji prefix
            return `${params.name}: ${params.value}%${amountLine}`;
        };

        const option: echarts.EChartsOption = {
            ...CHART_ANIMATION_CONFIG,
            ...(opts.skipAnimation ? {animation: false} : {}),
            color: palette,
            tooltip: {
                trigger: 'item',
                formatter: tooltipFormatter,
                position: tooltipPositionAboveFinger,
                backgroundColor: isDark ? '#1e293b' : '#fff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
            },
            legend: legendConfig,
            series: [
                {
                    type: 'pie',
                    radius: pieRadius,
                    center: pieCenter,
                    avoidLabelOverlap: true,
                    padAngle: 1,
                    itemStyle: {
                        borderRadius: 4,
                        borderColor: isDark ? '#293548' : '#ffffff',
                        borderWidth: 2,
                    },
                    label: labelConfig,
                    labelLayout: {hideOverlap: true},
                    emphasis: {
                        // Tooltip is sufficient on hover — hide inner label instead of replacing it with text
                        label: {show: false},
                        scaleSize: 5,
                    },
                    labelLine: {show: false},
                    data: chartData,
                },
            ],
        };

        chartInstance.setOption(option, {notMerge: false});
        chartFullyInitialized = true;
        lastDark = isDark;
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }
    }
</script>

<div bind:this={chartContainer} class="w-full" style="height: {height};"></div>
