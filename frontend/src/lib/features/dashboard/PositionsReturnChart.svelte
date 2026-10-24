<!--
  PositionsReturnChart — the return of the ticked positions, one line each, beside the portfolio's.

  The chart under the Dashboard's holdings table (Y5-2, #48). Two views of the same lines: the position's
  result in money (Abs, a dashed reference at 0) or its return in «base 100» (%, a dashed reference at 100).
  A custom HTML legend turns each line on and off and says which position closed and which line leaves values out.

  The component is CONTROLLED: it keeps no view and no hidden set. It draws the props it is given and calls
  `onviewchange(view)` / `ontoggle(id)`. The numbers are the backend's, shaped by `positionsSeries.ts`; a missing
  value stays `null` in the data, so the line breaks instead of dropping to zero.

  Props:
  - lines: the lines to draw, in legend order (positions, then the portfolio)
  - view / onviewchange: 'absolute' | 'percentage'
  - hiddenIds / ontoggle: the lines switched off
  - colorOf: the colour of a line id (the same one the table's tick uses)
  - currency: the display currency of the Abs view
  - loading / failed: the states of the request
  - portfolioLabel: overrides the portfolio line's label in the legend and the tooltip
  - note: the caption under the legend that says what the portfolio line is

  Pattern: Svelte 5 runes, ECharts, dark mode, privacy masking (see .claude/rules/frontend.md).
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {Flag, TriangleAlert} from 'lucide-svelte';
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {chartInitOptions} from '$lib/components/charts/chartPixelRatio';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {buildTooltipHeader, buildTooltipRow, buildTooltipTheme, scheduleFirstRenderStabilityFix, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import {axisLabelMeasure, buildResponsiveXAxisPolicy, timeAxisGridRight} from '$lib/components/charts/responsiveXAxis';
    import {formatAxisCurrency} from '$lib/features/brokers/lots/lotComparisonChartHelpers';
    import {_} from '$lib/i18n';
    import {isPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {chartNeutrals} from '$lib/theme/chartTheme';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import type {PositionLine, PositionsChartView} from './positionsSeries';

    interface Props {
        lines: ReadonlyArray<PositionLine>;
        view: PositionsChartView;
        onviewchange?: (view: PositionsChartView) => void;
        hiddenIds?: ReadonlySet<string>;
        ontoggle?: (id: string) => void;
        colorOf: (id: string) => string;
        currency: string;
        loading?: boolean;
        failed?: boolean;
        portfolioLabel?: string;
        note?: string;
        /** CSS height of the chart area. */
        height?: string;
    }

    /** The part of an axis-trigger tooltip item this chart reads. */
    interface TooltipItem {
        seriesId?: string;
        value?: unknown;
    }

    let {lines, view, onviewchange, hiddenIds = new Set<string>(), ontoggle, colorOf, currency, loading = false, failed = false, portfolioLabel, note, height = '18rem'}: Props = $props();

    const VIEWS: ReadonlyArray<PositionsChartView> = ['absolute', 'percentage'];

    /** Where each view draws its reference line: the start of the window (0 in money, base 100 in %). */
    const REFERENCE_LEVEL: Record<PositionsChartView, number> = {absolute: 0, percentage: 100};

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chart: echarts.ECharts | null = null;
    let lastWidth = 0;
    /** Bumped by a theme switch and by the Designer Lab's colour edits (C4): the whole option is built again. */
    let redrawRevision = $state(0);
    const resizeWatcher = createResizeWatcher(() => {
        if (!chart || !chartContainer) return;
        chart.resize();
        const width = chartContainer.clientWidth;
        // The x-axis labels and the right inset depend on the width: build them again, but only when it moved.
        if (width !== lastWidth) renderChart(true);
    });

    // =========================================================================
    // What is drawn
    // =========================================================================

    const hasValue = (line: PositionLine): boolean => line.points.some((point) => point.value !== null);

    /** The lines that reach the chart: switched on, and with at least one known point. */
    let drawn = $derived(lines.filter((line) => !hiddenIds.has(line.id) && hasValue(line)));

    let chartState = $derived<'loading' | 'failed' | 'empty' | 'ready'>(loading ? 'loading' : failed ? 'failed' : drawn.length === 0 ? 'empty' : 'ready');

    let hasPortfolioLine = $derived(lines.some((line) => line.kind === 'portfolio'));

    function labelOf(line: PositionLine): string {
        return line.kind === 'portfolio' && portfolioLabel ? portfolioLabel : line.label;
    }

    function closedText(line: PositionLine): string | undefined {
        return line.closedOn ? $_('dashboard.positionsChart.closedOn', {values: {date: formatDay(line.closedOn)}}) : undefined;
    }

    function legendTitle(line: PositionLine): string | undefined {
        return closedText(line) ?? (line.kind === 'portfolio' ? note : undefined);
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        const darkObserver = onThemeClassChange(() => {
            redrawRevision += 1;
        });
        const chartColors = onChartColorsChange(() => {
            redrawRevision += 1;
        });
        return () => {
            darkObserver.disconnect();
            chartColors.disconnect();
            resizeWatcher.disconnect();
            disposeChart();
        };
    });

    function disposeChart(): void {
        chart?.dispose();
        chart = null;
    }

    $effect(() => {
        void drawn;
        void view;
        void currency;
        void colorOf;
        void redrawRevision;
        // The axes and the tooltip are written in the interface locale, and ECharts runs its formatters outside
        // effect tracking: a language switch and the privacy toggle must redraw from here.
        void uiLocale();
        void isPrivacyEnabled();
        void portfolioLabel;
        const container = chartContainer;
        if (chartState !== 'ready' || !container) {
            // Leaving `ready` removes the canvas host: an instance left on the detached node would draw into nothing.
            disposeChart();
            return;
        }
        void tick().then(() => {
            if (chartContainer === container) renderChart();
        });
    });

    // =========================================================================
    // The option
    // =========================================================================

    /** The value of a tooltip item: ECharts hands `[date, value]`. */
    function itemValue(item: TooltipItem): number | null {
        const raw = Array.isArray(item.value) ? item.value[item.value.length - 1] : item.value;
        return typeof raw === 'number' && Number.isFinite(raw) ? raw : null;
    }

    function itemDate(item: TooltipItem): string {
        return Array.isArray(item.value) ? String(item.value[0]) : '';
    }

    /** One tooltip row's value: money in Abs; in %, the base-100 number with its signed percent (value − 100) beside it. */
    function tooltipValue(value: number, mutedColor: string): string {
        if (view === 'absolute') return escapeHtml(formatCurrencyAmountPlain(value, currency, {showSign: true}));
        const level = formatPercent(value, {suffix: '', signed: false, digits: 2});
        // `value − 100` is a change of unit (base 100 → percent), the one `positionsSeries.ts` declares.
        const change = formatPercent(value - REFERENCE_LEVEL.percentage, {digits: 2});
        return `${escapeHtml(level)} <span style="color:${mutedColor};font-weight:400">(${escapeHtml(change)})</span>`;
    }

    /** The points whose neighbours are both unknown: a line has nothing to join them to, so they get a symbol. */
    function isolatedPoints(line: PositionLine): boolean[] {
        const known = line.points.map((point) => point.value !== null);
        return known.map((here, i) => here && !known[i - 1] && !known[i + 1]);
    }

    function buildSeries(closedMarkerFill: string, referenceColor: string): echarts.SeriesOption[] {
        const level = REFERENCE_LEVEL[view];
        return drawn.map((line, index) => {
            const color = colorOf(line.id);
            const isolated = isolatedPoints(line);
            const series: echarts.SeriesOption & Record<string, unknown> = {
                id: line.id,
                name: labelOf(line),
                type: 'line',
                data: line.points.map((point) => namedPoint(point.date, point.value)),
                smooth: false,
                connectNulls: false,
                showSymbol: isolated.some(Boolean),
                symbol: (_value: unknown, params: {dataIndex: number}) => (isolated[params.dataIndex] ? 'circle' : 'none'),
                symbolSize: 6,
                lineStyle: {color, width: line.kind === 'portfolio' ? 2.5 : 1.75},
                itemStyle: {color},
                emphasis: {focus: 'series'},
            };
            // The window's start, drawn once: the first series carries it.
            if (index === 0) {
                series.markLine = {
                    silent: true,
                    symbol: 'none',
                    label: {show: false},
                    lineStyle: {type: 'dashed', color: referenceColor, width: 1},
                    data: [{yAxis: level}],
                };
            }
            // A closed position ends on its last known day: a ringed point says the line stops there for a reason.
            if (line.closedOn) {
                const last = [...line.points].reverse().find((point) => point.value !== null);
                if (last) {
                    series.markPoint = {
                        silent: true,
                        symbol: 'circle',
                        symbolSize: 9,
                        label: {show: false},
                        itemStyle: {color: closedMarkerFill, borderColor: color, borderWidth: 2},
                        data: [{name: line.id, coord: [last.date, last.value as number]}],
                    };
                }
            }
            return series;
        });
    }

    function buildOption(isDark: boolean, skipAnimation: boolean): echarts.EChartsOption {
        const neutrals = chartNeutrals(isDark, chartContainer);
        const box = buildTooltipTheme(isDark, chartContainer);
        const level = REFERENCE_LEVEL[view];
        const dates = [...new Set(drawn.flatMap((line) => line.points.map((point) => point.date)))].sort();
        const width = chartContainer?.clientWidth ?? 0;
        lastWidth = width;
        const xAxisPolicy = buildResponsiveXAxisPolicy({width, values: dates, locale: uiLocale(), axisType: 'time'});
        const gridRight = timeAxisGridRight({width, values: dates, locale: uiLocale(), base: '4%', measure: axisLabelMeasure(chart, 12)});
        const labelById = new Map(lines.map((line) => [line.id, labelOf(line)]));

        return {
            ...(skipAnimation ? {animation: false, animationDuration: 0, animationDurationUpdate: 0} : CHART_ANIMATION_CONFIG),
            backgroundColor: 'transparent',
            grid: {left: '3%', right: gridRight, bottom: '28px', top: '12px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                confine: true,
                position: tooltipPositionSide,
                axisPointer: {type: 'line', lineStyle: {color: neutrals.axisPointer.line}},
                backgroundColor: box.bg,
                borderColor: box.border,
                borderWidth: 1,
                textStyle: {color: box.textColor, fontSize: 12},
                formatter: (params: unknown) => {
                    const items = (Array.isArray(params) ? params : [params]) as TooltipItem[];
                    const rows = items
                        .map((item) => ({id: item.seriesId, value: itemValue(item), date: itemDate(item)}))
                        .filter((row): row is {id: string; value: number; date: string} => typeof row.id === 'string' && row.value !== null)
                        .sort((left, right) => right.value - left.value);
                    if (rows.length === 0) return '';
                    const header = buildTooltipHeader(escapeHtml(formatDay(rows[0].date)), box.mutedColor);
                    return header + rows.map((row) => buildTooltipRow(escapeHtml(labelById.get(row.id) ?? row.id), tooltipValue(row.value, box.mutedColor), colorOf(row.id))).join('');
                },
            },
            xAxis: {
                type: 'time',
                ...(xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber} : {}),
                axisLabel: {color: neutrals.dashboard.text, fontSize: 12, rotate: 0, formatter: xAxisPolicy.formatter, ...(xAxisPolicy.axisLabel ?? {})},
                axisLine: {lineStyle: {color: neutrals.dashboard.gridLine}},
                splitLine: {show: false},
            },
            yAxis: {
                type: 'value',
                scale: true,
                // The reference line must stay on the plot, whatever the lines do.
                min: (extent: {min: number}) => Math.min(extent.min, level),
                max: (extent: {max: number}) => Math.max(extent.max, level),
                axisLabel: {
                    color: neutrals.dashboard.text,
                    fontSize: 12,
                    // Abs: compact money, masked under privacy. %: the base-100 numbers as they are (112), public.
                    formatter: (value: number) => (view === 'absolute' ? formatAxisCurrency(value, currency) : formatPercent(value, {suffix: '', signed: false, digits: 1, trim: true})),
                },
                axisLine: {show: false},
                splitLine: {lineStyle: {color: neutrals.dashboard.gridLine, type: 'dashed'}},
            },
            series: buildSeries(neutrals.lots.markerRing, neutrals.growth.pnlReference),
        };
    }

    function renderChart(skipAnimation = false): void {
        const container = chartContainer;
        if (!container || chartState !== 'ready') return;

        if (chart && chart.getDom() !== container) disposeChart();
        if (!chart) {
            chart = echarts.init(container, CHART_INIT_THEME, chartInitOptions(container));
            attachChartReady(chart, container, 'positions-return');
            scheduleFirstRenderStabilityFix(chart, container);
        }
        resizeWatcher.observe(container);

        chart.setOption(buildOption(isDarkTheme(), skipAnimation), CHART_SET_OPTION_OPTS);
    }
</script>

<div class="flex flex-col gap-2 text-lf-primary" data-testid="positions-return-chart" data-state={chartState} data-view={view} data-line-count={drawn.length}>
    <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="text-sm font-semibold text-lf-primary">{$_('dashboard.positionsChart.title')}</h3>
        <div class="inline-flex overflow-hidden rounded-md border border-lf-input" role="group" aria-label={$_('dashboard.positionsChart.title')}>
            {#each VIEWS as option (option)}
                <button
                    type="button"
                    class="px-2.5 py-1 text-xs font-medium focus-visible:outline-2 focus-visible:outline-lf-focus {view === option ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-secondary hover:bg-lf-panel'}"
                    aria-pressed={view === option}
                    title={option === 'absolute' ? $_('dashboard.positionsChart.viewAbsoluteHint') : $_('dashboard.positionsChart.viewPercentageHint')}
                    data-testid="positions-chart-view-{option}"
                    onclick={() => onviewchange?.(option)}
                >
                    {option === 'absolute' ? $_('dashboard.positionsChart.viewAbsolute') : $_('dashboard.positionsChart.viewPercentage')}
                </button>
            {/each}
        </div>
    </div>

    {#if lines.length > 0}
        <div class="flex flex-wrap gap-1.5" role="group" aria-label={$_('dashboard.positionsChart.title')}>
            {#each lines as line (line.id)}
                {@const visible = !hiddenIds.has(line.id)}
                <button
                    type="button"
                    class="inline-flex max-w-full items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs focus-visible:outline-2 focus-visible:outline-lf-focus {visible ? 'border-lf-input bg-lf-card text-lf-primary' : 'border-lf-subtle bg-lf-panel text-lf-muted'}"
                    aria-pressed={visible}
                    title={legendTitle(line)}
                    data-testid="positions-chart-legend-{line.id}"
                    data-kind={line.kind}
                    data-closed={line.closedOn ? 'true' : 'false'}
                    onclick={() => ontoggle?.(line.id)}
                >
                    <span class="inline-block h-2.5 w-2.5 shrink-0 rounded-full {visible ? '' : 'opacity-40'}" style="background-color: {colorOf(line.id)}" data-testid="positions-chart-swatch-{line.id}"></span>
                    <span class="truncate {line.kind === 'portfolio' ? 'font-semibold' : ''}">{labelOf(line)}</span>
                    {#if line.closedOn}
                        <Flag size={12} class="shrink-0" aria-hidden="true" />
                    {/if}
                    {#if !line.complete}
                        <span class="inline-flex shrink-0 text-lf-warning" title={$_('dashboard.positionsChart.incomplete')} data-testid="positions-chart-incomplete-{line.id}">
                            <TriangleAlert size={12} aria-hidden="true" />
                        </span>
                    {/if}
                </button>
            {/each}
        </div>
        {#if hasPortfolioLine && note}
            <p class="text-xs text-lf-muted" data-testid="positions-chart-note">{note}</p>
        {/if}
    {/if}

    {#if chartState === 'loading'}
        <div class="animate-pulse rounded bg-lf-panel" style:height data-testid="positions-chart-skeleton" aria-busy="true" aria-label={$_('common.loading')}></div>
    {:else if chartState === 'failed'}
        <div class="flex items-center justify-center rounded border border-dashed border-lf-input px-4 text-center text-sm text-lf-danger" style:height data-testid="positions-chart-failed" role="alert">
            {$_('dashboard.positionsChart.failed')}
        </div>
    {:else if chartState === 'empty'}
        <div class="flex items-center justify-center rounded border border-dashed border-lf-input px-4 text-center text-sm text-lf-muted" style:height data-testid="positions-chart-hint">
            {$_('dashboard.positionsChart.hint')}
        </div>
    {:else}
        <div bind:this={chartContainer} class="w-full" style:height data-testid="positions-chart-canvas"></div>
    {/if}
</div>
