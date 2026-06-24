<!--
  AllocationHistoryChart — 100% stacked area chart for allocation history.

  Shows how portfolio allocation by type, sector, or geography evolved over time.
  Each category is a stacked area layer whose height = percentage weight.

  Props:
  - data: AllocationHistoryPoint[] from POST /allocation-history
  - height: CSS height (default "100%")
  - loading: Show skeleton

  Pattern: Svelte 5 Runes, ECharts, dark mode support.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_, t} from '$lib/i18n';
    import {buildTooltipTheme, buildTooltipHeader, buildTooltipByThreshold, buildTooltipTopN, tooltipPositionSide, setupTooltipAutoHide} from '$lib/components/charts/echartsTooltipHelpers';
    import {getCountryInfo, isCountriesLoaded, ensureCountriesLoaded} from '$lib/stores/reference/countryStore';
    import {getSectorEmoji, isSectorsLoaded, ensureSectorsLoaded} from '$lib/stores/reference/sectorStore';
    import {sectorI18nKey, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {currentLanguage} from '$lib/stores/app/language';

    interface AllocationComponent {
        name: string;
        value: string;
        amount: string;
    }

    interface AllocationHistoryPoint {
        date: string;
        components: AllocationComponent[];
    }

    interface Props {
        data: AllocationHistoryPoint[];
        height?: string;
        loading?: boolean;
        /** Which allocation dimension is being displayed — affects label localization. */
        dimension?: 'type' | 'sector' | 'geo';
    }

    let {data = [], height = '100%', loading = false, dimension = 'type'}: Props = $props();

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;

    // Distinct colors for allocation categories (up to 12)
    const PALETTE_LIGHT = ['#1a4031', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#ec4899', '#f97316', '#14b8a6', '#6366f1', '#a3a3a3'];
    const PALETTE_DARK = ['#4ade80', '#60a5fa', '#fbbf24', '#f87171', '#a78bfa', '#22d3ee', '#a3e635', '#f472b6', '#fb923c', '#2dd4bf', '#818cf8', '#d4d4d4'];

    /** Get an emoji/icon label for a category. */
    function getCategoryEmoji(rawName: string): string {
        if (dimension === 'sector') return getSectorEmoji(rawName);
        if (dimension === 'geo') {
            if (rawName === 'Other' || rawName === 'Unknown') return '🏳️';
            return getCountryInfo(rawName).flag_emoji || '🌍';
        }
        if (dimension === 'type') {
            const typeEmojis: Record<string, string> = {
                STOCK: '📈', ETF: '📊', BOND: '🏛️', CRYPTO: '₿',
                FUND: '💼', HOLD: '⏸️', CROWDFUND_LOAN: '🤝',
                INDEX: '📉', OTHER: '📦', Liquidity: '💰',
            };
            return typeEmojis[rawName] ?? '📊';
        }
        return '';
    }

    // ── Derived: extract unique category names ──
    const categoryNames = $derived.by(() => {
        const names = new Set<string>();
        for (const pt of data) {
            for (const c of pt.components) names.add(c.name);
        }
        return [...names];
    });

    const dates = $derived(data.map((pt) => pt.date));

    // Track when reference data loads — triggers chart re-render for emoji/flags
    let refDataVersion = $state(0);

    onMount(() => {
        darkModeObserver = new MutationObserver(() => renderChart());
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        // Trigger load of countries/sectors, then re-render when done
        const loadRefs = async () => {
            await Promise.allSettled([
                ensureCountriesLoaded($currentLanguage),
                ensureSectorsLoaded(),
            ]);
            refDataVersion++;
        };
        loadRefs();

        return () => {
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        void data;
        void dimension;
        void refDataVersion;
        if (chartContainer) {
            tick().then(() => {
                if (!resizeObserver && chartContainer) {
                    resizeObserver = new ResizeObserver(() => chartInstance?.resize());
                    resizeObserver.observe(chartContainer);
                }
                renderChart();
            });
        }
    });

    /** Localize a category name (text only, no emoji). */
    function localizeName(rawName: string): string {
        if (dimension === 'geo') {
            if (rawName === 'Other' || rawName === 'Unknown') return $_('common.other') || 'Other';
            const info = getCountryInfo(rawName);
            return info.name || rawName;
        }
        if (dimension === 'sector') {
            const key = `sectors.${sectorI18nKey(rawName)}`;
            const localized = $t(key);
            return localized !== key ? localized : rawName;
        }
        if (dimension === 'type') {
            return $t(`assets.types.${rawName}`) || rawName;
        }
        return rawName;
    }

    function renderChart() {
        if (!chartContainer || loading || data.length === 0) return;

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            chartInstance.dispose();
            chartInstance = undefined;
        }
        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
        }

        const isDark = document.documentElement.classList.contains('dark');
        const palette = isDark ? PALETTE_DARK : PALETTE_LIGHT;
        const textColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        const tooltipBg = isDark ? '#1e293b' : '#ffffff';
        const tooltipBorder = isDark ? '#334155' : '#e2e8f0';

        // Build one series per category, stacked to 100%
        // Compute average weight per category for label visibility threshold
        const avgWeights: Record<string, number> = {};
        for (const name of categoryNames) {
            const values = data.map((pt) => {
                const comp = pt.components.find((c) => c.name === name);
                return comp ? Number(comp.value) : 0;
            });
            avgWeights[name] = values.length > 0 ? values.reduce((s, v) => s + v, 0) / values.length : 0;
        }

        // Sort categories by average weight (largest first) for legend and series order
        const sortedNames = [...categoryNames].sort((a, b) => (avgWeights[b] ?? 0) - (avgWeights[a] ?? 0));

        const series: echarts.SeriesOption[] = sortedNames.map((name, i) => {
            const emoji = getCategoryEmoji(name);
            const showLabel = avgWeights[name] >= 3 && emoji;
            const legendName = emoji ? `${emoji} ${localizeName(name)}` : localizeName(name);
            return {
                name: legendName,
                type: 'line',
                stack: 'allocation',
                data: data.map((pt) => {
                    const comp = pt.components.find((c) => c.name === name);
                    return comp ? Number(comp.value) : 0;
                }),
                smooth: false,
                symbol: 'none',
                lineStyle: {color: palette[i % palette.length], width: 1, opacity: 0.7},
                areaStyle: {color: palette[i % palette.length] + '88'},
                itemStyle: {color: palette[i % palette.length]},
                emphasis: {focus: 'series'},
                label: showLabel
                    ? {
                          show: true,
                          position: 'inside' as const,
                          formatter: () => emoji,
                          fontSize: 14,
                          color: isDark ? '#ffffff' : '#000000',
                          textShadowColor: isDark ? '#000' : '#fff',
                          textShadowBlur: 2,
                      }
                    : {show: false},
            };
        });

        // Pre-build per-category data index for accurate tooltip values
        const seriesDataByName: Record<string, number[]> = {};
        for (const name of sortedNames) {
            seriesDataByName[name] = data.map((pt) => {
                const comp = pt.components.find((c) => c.name === name);
                return comp ? Number(comp.value) : 0;
            });
        }

        const option: echarts.EChartsOption = {
            animation: false,
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '40px', top: '10px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                appendToBody: true,
                confine: true,
                position: tooltipPositionSide,
                axisPointer: {type: 'line'},
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    const date = items[0]?.axisValue ?? '';
                    const idx = items[0]?.dataIndex ?? 0;

                    const theme = buildTooltipTheme(isDark);

                    // Use raw (non-cumulative) data for correct percentages
                    const allItems = sortedNames
                        .map((name, i) => {
                            const emoji = getCategoryEmoji(name);
                            const displayName = emoji ? `${emoji} ${localizeName(name)}` : localizeName(name);
                            return {
                                name: displayName,
                                value: seriesDataByName[name]?.[idx] ?? 0,
                                color: palette[i % palette.length],
                            };
                        })
                        .filter((x) => x.value > 0.01);

                    const header = buildTooltipHeader(date, theme.mutedColor);
                    let rows: string;
                    if (dimension === 'type') {
                        // Type: show up to 5 directly, group 6th+ only if ≥2 items remain
                        if (allItems.length <= 6) {
                            rows = buildTooltipTopN(allItems, allItems.length, theme, $_('common.remaining') || 'Remaining');
                        } else {
                            rows = buildTooltipTopN(allItems, 5, theme, $_('common.remaining') || 'Remaining');
                        }
                    } else {
                        // Sector/Geo: threshold-based (≥3% shown, rest grouped)
                        rows = buildTooltipByThreshold(allItems, 3, theme, $_('common.remaining') || 'Remaining');
                    }
                    return header + rows;
                },
            },
            legend: {
                bottom: 0,
                left: 'center',
                textStyle: {color: textColor, fontSize: 10},
                itemWidth: 12,
                itemHeight: 8,
                type: 'scroll',
                width: '90%',
                pageTextStyle: {color: textColor},
                pageIconColor: textColor,
                pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
            },
            dataZoom: [{type: 'inside', start: 0, end: 100}],
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: {color: textColor, fontSize: 10, rotate: 0},
                axisLine: {lineStyle: {color: gridColor}},
                splitLine: {show: false},
                boundaryGap: false,
            },
            yAxis: {
                type: 'value',
                max: 100,
                axisLabel: {color: textColor, fontSize: 10, formatter: (v: number) => `${v}%`},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };

        chartInstance.setOption(option, {notMerge: true});
    }
</script>

{#if loading}
    <div class="w-full h-full bg-gray-100 dark:bg-slate-700 rounded animate-pulse" style="height: {height}"></div>
{:else if data.length === 0}
    <div class="flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm" style="height: {height}">
        {$_('dashboard.noData')}
    </div>
{:else}
    <div bind:this={chartContainer} style="height: {height}; width: 100%;"></div>
{/if}
