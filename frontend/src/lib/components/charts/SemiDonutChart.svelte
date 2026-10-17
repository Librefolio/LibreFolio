<!--
  SemiDonutChart — Half-donut (semi-circle) pie chart for ownership visualization.

  Extracted from BrokerSharingModal to be reusable across the application.
  Shows ownership distribution as a semi-circle with avatar labels.

  Features:
  - Semi-circle pie chart (180°-360°)
  - Circular avatar images pre-clipped via offscreen canvas
  - Initial letter fallback when no avatar available, in the text that reads best on its disc
  - "Available" slice for unallocated percentage
  - Dark mode support: redraws when the theme switches, or when the chart colours change (Designer Lab, C4)
  - ResizeObserver for responsive sizing
  - Owners coloured in order with the first eight asset types of the designer's palette, a version per
    theme (GR5.2), shaded past the eighth

  Used by:
  - BrokerSharingModal (ownership distribution)
  - Dashboard (future - portfolio allocation)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {scheduleFirstRenderStabilityFix, tooltipPositionAboveFinger} from '$lib/components/charts/echartsTooltipHelpers';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {chartNeutrals} from '$lib/theme/chartTheme';
    import {CATEGORY_SEQUENCE, sequenceColor} from '$lib/theme/chartCategories';
    import {shadePoles} from '$lib/theme/chartShades';
    import {chartRoles} from '$lib/theme/roleColors';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';

    // =========================================================================
    // Types
    // =========================================================================

    interface OwnerSlice {
        /** Display name */
        name: string;
        /** Percentage (0-100) */
        percentage: number;
        /** Optional avatar URL */
        avatarUrl?: string | null;
    }

    interface Props {
        /** Owner data slices */
        data: OwnerSlice[];
        /** Label for the "available" (unallocated) slice */
        availableLabel?: string;
        /** CSS height of the chart container */
        height?: string;
    }

    let {data = [], availableLabel = 'Available', height = '180px'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    const resizeWatcher = createResizeWatcher(() => {
        chartInstance?.resize();
    });
    let needsInitialLayoutStabilityPass = false;
    let renderGeneration = 0;

    // Cache for circular avatar data URLs
    const circularAvatarCache = new Map<string, string>();

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        // The colours are read when the chart draws: a theme switch, or a chart colour changed without one (a Designer
        // Lab edit, contract C4), draws it again (backlog R-7).
        const theme = onThemeClassChange(redraw);
        const colors = onChartColorsChange(redraw);
        return () => {
            theme.disconnect();
            colors.disconnect();
            cleanup();
        };
    });

    /** Draws the current data again, as the next generation. */
    function redraw() {
        if (!chartContainer) return;
        void renderChart(
            ++renderGeneration,
            data.map((slice) => ({...slice})),
            availableLabel,
        );
    }

    $effect(() => {
        const container = chartContainer;
        const slices = data.map((slice) => ({...slice}));
        const label = availableLabel;
        void height;
        // The labels are written in the interface locale: a language switch redraws them (M-18).
        void uiLocale();

        if (container) {
            const generation = ++renderGeneration;
            tick().then(async () => {
                if (generation !== renderGeneration || chartContainer !== container) return;
                setupResizeObserver();
                await renderChart(generation, slices, label);
            });
        }
    });

    function setupResizeObserver() {
        resizeWatcher.observe(chartContainer);
    }

    function cleanup() {
        renderGeneration++;
        resizeWatcher.disconnect();
        if (chartInstance && !chartInstance.isDisposed()) {
            chartInstance.dispose();
        }
        chartInstance = null;
    }

    // =========================================================================
    // Avatar Helper
    // =========================================================================

    function createCircularImage(url: string, size: number, borderColor: string, borderWidth: number): Promise<string> {
        const cacheKey = `${url}_${size}_${borderColor}_${borderWidth}`;
        const cached = circularAvatarCache.get(cacheKey);
        if (cached) return Promise.resolve(cached);

        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                const totalSize = size + borderWidth * 2;
                const canvas = document.createElement('canvas');
                canvas.width = totalSize * 2; // 2x for retina
                canvas.height = totalSize * 2;
                const ctx = canvas.getContext('2d')!;
                ctx.scale(2, 2);

                const cx = totalSize / 2;
                const cy = totalSize / 2;
                const outerR = totalSize / 2;
                const innerR = size / 2;

                // Draw border circle
                if (borderWidth > 0) {
                    ctx.beginPath();
                    ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
                    ctx.fillStyle = borderColor;
                    ctx.fill();
                }

                // Clip to inner circle and draw image
                ctx.save();
                ctx.beginPath();
                ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
                ctx.clip();
                const imgSize = innerR * 2;
                ctx.drawImage(img, cx - innerR, cy - innerR, imgSize, imgSize);
                ctx.restore();

                const dataUrl = canvas.toDataURL('image/png');
                circularAvatarCache.set(cacheKey, dataUrl);
                resolve(dataUrl);
            };
            img.onerror = () => resolve('');
            img.src = url;
        });
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    async function waitForRenderableContainer(container: HTMLDivElement, generation: number) {
        for (let attempt = 0; attempt < 4; attempt++) {
            if (generation !== renderGeneration || chartContainer !== container || !container.isConnected) return false;
            const rect = container.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) return true;
            await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
        }
        return generation === renderGeneration && chartContainer === container && container.isConnected;
    }

    async function renderChart(generation: number, slices: OwnerSlice[], label: string) {
        const container = chartContainer;
        if (!container) return;
        if (!(await waitForRenderableContainer(container, generation))) return;

        if (!chartInstance || chartInstance.isDisposed()) {
            chartInstance = echarts.init(container, CHART_INIT_THEME, {renderer: 'canvas'});
            attachChartReady(chartInstance, container, 'semi-donut');
            needsInitialLayoutStabilityPass = true;
        }
        const currentInstance = chartInstance;

        const isDark = isDarkTheme();
        const neutrals = chartNeutrals(isDark, container);
        const avatarSize = 44;
        const borderColor = neutrals.semiDonut.avatarBorder;
        const borderWidth = 2;
        // GR5.2: the owners take the first eight asset types in order, then a shade of them (GR4) past the eighth. The
        // roles are read once, from the chart's own element.
        const roles = chartRoles(isDark, container);
        const poles = shadePoles(isDark, roles.color('--lf-surface-card'));
        const ownerColor = (index: number) => sequenceColor('type', CATEGORY_SEQUENCE, index, isDark, poles);

        // Pre-load circular avatars in parallel
        const avatarPromises: Array<{index: number; promise: Promise<string>}> = [];
        slices.forEach((slice, i) => {
            if (slice.avatarUrl && slice.percentage > 0) {
                const url = slice.avatarUrl.includes('?') ? slice.avatarUrl : `${slice.avatarUrl}?img_preview=64x64`;
                avatarPromises.push({index: i, promise: createCircularImage(url, avatarSize, borderColor, borderWidth)});
            }
        });

        const resolvedAvatars = await Promise.all(avatarPromises.map(async (p) => ({index: p.index, dataUrl: await p.promise})));
        if (generation !== renderGeneration || chartInstance !== currentInstance || currentInstance.isDisposed()) return;

        const avatarMap = new Map<number, string>();
        resolvedAvatars.forEach((r) => {
            if (r.dataUrl) avatarMap.set(r.index, r.dataUrl);
        });

        // Build chart data
        const chartData: Array<{value: number; name: string; itemStyle?: any; label?: any}> = [];
        const totalAllocated = slices.reduce((sum, s) => sum + s.percentage, 0);

        slices.forEach((slice, i) => {
            if (slice.percentage <= 0) return;

            // The slice and its avatar's disc are one colour, the owner's: by its place among the owners.
            const color = ownerColor(i);
            const initial = slice.name.charAt(0).toUpperCase();
            const totalIconSize = avatarSize + borderWidth * 2;
            const rich: Record<string, any> = {
                pct: {
                    fontSize: 11,
                    fontWeight: 'bold',
                    color: neutrals.semiDonut.label,
                    lineHeight: 18,
                    padding: [2, 0, 0, 0],
                    align: 'center',
                    textShadowColor: neutrals.semiDonut.labelShadow,
                    textShadowBlur: 3,
                },
            };

            let formatter: string;
            const circularDataUrl = avatarMap.get(i);
            if (circularDataUrl) {
                rich['avatar'] = {
                    backgroundColor: {image: circularDataUrl},
                    width: totalIconSize,
                    height: totalIconSize,
                    align: 'center',
                };
                formatter = `{avatar| }\n{pct|${formatPercent(slice.percentage, {digits: 1, signed: false})}}`;
            } else {
                rich['avatar'] = {
                    fontSize: 18,
                    fontWeight: 'bold',
                    color: roles.readableText(color),
                    backgroundColor: color,
                    borderRadius: avatarSize / 2,
                    width: avatarSize,
                    height: avatarSize,
                    align: 'center',
                    lineHeight: avatarSize,
                    borderColor: neutrals.semiDonut.avatarBorder,
                    borderWidth: 2,
                };
                formatter = `{avatar|${initial}}\n{pct|${formatPercent(slice.percentage, {digits: 1, signed: false})}}`;
            }

            chartData.push({
                value: slice.percentage,
                name: slice.name,
                itemStyle: {color},
                label: {show: true, formatter, rich},
            });
        });

        // Available slice
        const avail = Math.max(0, 100 - totalAllocated);
        if (avail > 0.01) {
            chartData.push({
                value: avail,
                name: label,
                itemStyle: {color: neutrals.semiDonut.available},
                label: {show: false},
            });
        }

        // Edge case: no data
        if (chartData.length === 0) {
            chartData.push({
                value: 100,
                name: `${label} (100%)`,
                itemStyle: {color: neutrals.semiDonut.available},
                label: {show: false},
            });
        }

        const option: echarts.EChartsOption = {
            tooltip: {
                trigger: 'item',
                formatter: (params: unknown) => {
                    const item = params as {name?: string; value?: number};
                    return `${escapeHtml(String(item.name ?? ''))}: ${formatPercent(Number(item.value), {digits: 1, signed: false})}`;
                },
                position: tooltipPositionAboveFinger,
                backgroundColor: neutrals.tooltip.box.background,
                borderColor: neutrals.tooltip.box.border,
                textStyle: {color: neutrals.tooltip.box.text},
            },
            series: [
                {
                    type: 'pie',
                    radius: ['55%', '95%'],
                    center: ['50%', '85%'],
                    startAngle: 180,
                    endAngle: 360,
                    padAngle: 2,
                    itemStyle: {
                        borderRadius: 6,
                        borderColor: neutrals.semiDonut.sliceGap,
                        borderWidth: 2,
                    },
                    label: {
                        show: true,
                        position: 'outside',
                        distanceToLabelLine: 5,
                        alignTo: 'labelLine',
                    },
                    labelLine: {
                        show: true,
                        length: 10,
                        length2: 8,
                        lineStyle: {color: neutrals.semiDonut.labelLine},
                    },
                    emphasis: {
                        label: {show: true},
                        scaleSize: 4,
                    },
                    data: chartData,
                },
            ],
        };

        if (generation !== renderGeneration || chartInstance !== currentInstance || currentInstance.isDisposed()) return;

        currentInstance.setOption(option, CHART_SET_OPTION_OPTS);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(currentInstance, container);
        }
    }
</script>

<div bind:this={chartContainer} class="w-full" style="height: {height};"></div>
