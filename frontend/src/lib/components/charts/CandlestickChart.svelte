<!--
  CandlestickChart — ECharts candlestick chart with optional volume bars.

  Architecture: Two ECharts grids in a single instance.
  - grid[0]: Price — candlestick series + overlay signals (EMA, BB, RSI, MACD…)
  - grid[1]: Volume — bar series (hidden when showVolume=false)
  - dataZoom: 'inside' type, links both x-axes for synchronised zoom/pan

  Y-axes:
    yAxis[0] = price (scale:true, grid[0])
    yAxis[1] = RSI / secondary (right, grid[0]) — always declared to avoid coord crash
    yAxis[2] = MACD / tertiary (right+offset, grid[0]) — always declared
    yAxis[3] = volume (hidden, auto-scale, grid[1]) — only rendered when showVolume=true

  Overlay signals keep their original yAxisIndex (0 / 1 / 2) unchanged — same
  as LineChart. Volume is on yAxis[3] so no conflict.

  Used by: PriceChartFull (candlestick mode)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import type {RenderedSignal} from '$lib/charts/signals';
    import type {LineDataPoint} from './LineChart.svelte';
    import {COLORS, hexToRgba, updateArrowRotations} from './lineChartHelpers';
    import {signalLabelToHtml} from '$lib/charts/signalLabel';
    import {buildPriceYAxis, buildSecondaryYAxes, buildOverlaySignalSeries, buildDataZoom, computeRightMargin, getChartColors} from './chartCoreHelpers';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** OHLCV data aligned to dateAxis */
        data: LineDataPoint[];
        /** Whether dark mode is active (passed from parent to avoid flicker) */
        isDark?: boolean;
        /** Show volume bars in the lower grid (default: true) */
        showVolume?: boolean;
        /** CSS height for the price grid area */
        height?: string;
        /** Show grid split lines */
        showGridLines?: boolean;
        /** Signal overlays — same RenderedSignal used by LineChart */
        overlaySignals?: RenderedSignal[];
        /** Y-axis currency label */
        currency?: string;
        /** View mode — 'percentage' transforms OHLCV relative to first data point */
        viewMode?: 'absolute' | 'percentage';
        /** Measure mode: enables click-to-place measurement points */
        measureMode?: boolean;
        /** Called on click in measure mode (date, close value) */
        onMeasureClick?: (date: string, value: number) => void;
        /** Called on mousemove in measure mode (date, close value) */
        onMeasureHover?: (date: string, value: number) => void;
        /** Called on double-click on a data point (date, value) — for editor scroll */
        onDblClick?: (date: string, value: number) => void;
        /** Main series label for tooltip header (e.g. asset name) */
        mainSeriesLabel?: string;
        /** Main series icon URL (for tooltip rendering) */
        mainIconUrl?: string | null;
        /** Main series asset type (for tooltip icon fallback) */
        mainAssetType?: string | null;
        /** Display currency (when FX conversion active) */
        displayCurrency?: string;
        /** Display currency flag emoji */
        displayCurrencyFlag?: string;
        /** Main asset native currency code */
        mainCurrency?: string;
        /** Main asset native currency flag emoji */
        mainCurrencyFlag?: string;
        /** Y-axis mode: 'auto' (scale:true), 'include0', or 'custom' */
        yAxisMode?: 'auto' | 'include0' | 'custom';
        /** Y-axis minimum (when yAxisMode='custom') */
        yAxisMin?: number;
        /** Y-axis maximum (when yAxisMode='custom') */
        yAxisMax?: number;
    }

    let {
        data = [],
        isDark: isDarkProp,
        showVolume = true,
        height = '400px',
        showGridLines = true,
        overlaySignals = [],
        currency = '',
        viewMode = 'absolute',
        measureMode = false,
        onMeasureClick,
        onMeasureHover,
        onDblClick,
        mainSeriesLabel,
        mainIconUrl,
        mainAssetType,
        displayCurrency: displayCurrencyProp,
        displayCurrencyFlag,
        mainCurrency: mainCurrencyProp,
        mainCurrencyFlag: mainCurrencyFlagProp,
        yAxisMode = 'auto',
        yAxisMin,
        yAxisMax,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement;
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let chartOptionSet = false;

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        // Watch for dark-mode class changes on <html>
        const observer = new MutationObserver(() => {
            if (chartContainer && data.length > 0) renderChart();
        });
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['class'],
        });
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    $effect(() => {
        if (chartContainer && data) {
            void overlaySignals;
            void showVolume;
            void showGridLines;
            void height;
            void viewMode;
            void yAxisMode;
            void yAxisMin;
            void yAxisMax;
            tick().then(renderChart);
        }
    });

    function cleanup() {
        resizeObserver?.disconnect();
        resizeObserver = null;
        chartOptionSet = false;
        chartInstance?.dispose();
        chartInstance = null;
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart() {
        if (!chartContainer || data.length === 0) return;

        if (!resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                if (chartOptionSet) {
                    try {
                        chartInstance?.resize();
                        if (chartInstance) updateArrowRotations(chartInstance);
                    } catch (_) {
                        /* ignore coord errors during resize */
                    }
                } else if (chartContainer && data.length > 0) {
                    renderChart();
                }
            });
            resizeObserver.observe(chartContainer);
        }

        const rect = chartContainer.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            chartInstance.on('dataZoom', () => {
                if (chartInstance) updateArrowRotations(chartInstance);
            });

            // Measure mode: click handler
            chartInstance.getZr().on('click', (params: any) => {
                if (!measureMode || !onMeasureClick || !chartInstance) return;
                const pointInPixel = [params.offsetX, params.offsetY];
                if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                    const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                    if (pointInGrid) {
                        const dateIdx = Math.round(pointInGrid[0]);
                        if (dateIdx >= 0 && dateIdx < data.length) {
                            const d = data[dateIdx];
                            const closeVal = d.close ?? d.value;
                            onMeasureClick(d.date, closeVal);
                        }
                    }
                }
            });

            // Measure mode: hover handler
            let hoverRaf = false;
            chartInstance.getZr().on('mousemove', (params: any) => {
                if (!measureMode || !onMeasureHover || !chartInstance || hoverRaf) return;
                hoverRaf = true;
                requestAnimationFrame(() => {
                    hoverRaf = false;
                    if (!chartInstance) return;
                    const pointInPixel = [params.offsetX, params.offsetY];
                    if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                        const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                        if (pointInGrid) {
                            const dateIdx = Math.round(pointInGrid[0]);
                            if (dateIdx >= 0 && dateIdx < data.length) {
                                const d = data[dateIdx];
                                const closeVal = d.close ?? d.value;
                                onMeasureHover!(d.date, closeVal);
                            }
                        }
                    }
                });
            });

            // Double-click handler — scrolls editor to clicked date (works on both price and volume grids)
            chartInstance.getZr().on('dblclick', (params: any) => {
                if (!onDblClick || !chartInstance) return;
                const pointInPixel = [params.offsetX, params.offsetY];
                // Check price grid first, then volume grid
                for (const gi of [0, 1]) {
                    if (chartInstance.containPixel({gridIndex: gi}, pointInPixel)) {
                        const pointInGrid = chartInstance.convertFromPixel({gridIndex: gi}, pointInPixel);
                        if (pointInGrid) {
                            const dateIdx = Math.round(pointInGrid[0]);
                            if (dateIdx >= 0 && dateIdx < data.length) {
                                const d = data[dateIdx];
                                onDblClick(d.date, d.close ?? d.value);
                            }
                        }
                        break;
                    }
                }
            });
        }

        const dark = isDarkProp ?? document.documentElement.classList.contains('dark');

        const greenColor = dark ? COLORS.greenDark : COLORS.greenLight;
        const redColor = dark ? COLORS.redDark : COLORS.redLight;
        const axisColor = dark ? '#475569' : '#d1d5db';
        const labelColor = dark ? '#94a3b8' : '#6b7280';

        const dates = data.map((d) => d.date);

        // ── Percentage mode: transform prices relative to first data point ──
        const isPercentage = viewMode === 'percentage';
        const baseValue = isPercentage && data.length > 0 ? (data[0].open ?? data[0].value) : 1;
        const pct = (v: number) => (isPercentage && baseValue !== 0 ? ((v - baseValue) / baseValue) * 100 : v);

        // ── Candlestick series data: ECharts format = [open, close, low, high] ──
        // DB values have priority; synthesize only fields that are null/undefined.
        // Synthesis: open = prev close, high = max(open, close), low = min(open, close)
        const candleData: (number[] | null)[] = data.map((d, i) => {
            const c = d.close ?? d.value;
            if (c == null) return null;
            const prevClose = i > 0 ? (data[i - 1].close ?? data[i - 1].value) : c;
            const o = d.open ?? prevClose;
            const h = d.high ?? Math.max(o, c);
            const l = d.low ?? Math.min(o, c);
            return [pct(o), pct(c), pct(l), pct(h)];
        });

        // ── Volume series data ──
        const hasAnyVolume = data.some((d) => d.volume != null && d.volume > 0);
        const actualShowVolume = showVolume && hasAnyVolume;

        const volumeData: any[] = data.map((d) => {
            const vol = d.volume ?? 0;
            const c = d.close ?? d.value;
            const o = d.open ?? c;
            const bullish = c >= o;
            return {
                value: vol,
                itemStyle: {
                    color: bullish ? hexToRgba(greenColor, 0.55) : hexToRgba(redColor, 0.55),
                },
            };
        });

        // ── Overlay signals ──
        const {axes: secondaryAxes, extraAxesCount} = buildSecondaryYAxes(overlaySignals, dark, 0);

        const series: any[] = [];

        // Candlestick series
        series.push({
            type: 'candlestick',
            name: currency || 'Price',
            data: candleData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            barWidth: '80%',
            itemStyle: {
                color: greenColor,
                color0: redColor,
                borderColor: greenColor,
                borderColor0: redColor,
            },
        });

        // Volume bars (on separate grid)
        if (actualShowVolume) {
            series.push({
                type: 'bar',
                name: 'Volume',
                data: volumeData,
                xAxisIndex: 1,
                yAxisIndex: 3,
                barMaxWidth: 12,
            });
        }

        // Overlay signals — uses shared helper
        series.push(...buildOverlaySignalSeries(overlaySignals, dates, dark, 0));

        // ── Grid configuration ──
        // Price grid: leaves room for volume below (if active) and extra yAxes to the right
        const rightMargin = computeRightMargin(extraAxesCount);
        const priceGridBottom = actualShowVolume ? '27%' : '10%';

        const grids: any[] = [
            {
                top: 20,
                right: rightMargin,
                bottom: priceGridBottom,
                left: 10,
                containLabel: true,
            },
        ];

        if (actualShowVolume) {
            grids.push({
                top: '76%',
                right: rightMargin,
                bottom: 20,
                left: 10,
                containLabel: true,
            });
        }

        // ── X-axes ──
        const xAxisBase = {
            type: 'category' as const,
            data: dates,
            boundaryGap: true,
            axisLine: {lineStyle: {color: axisColor}},
            axisLabel: {color: labelColor, fontSize: 11},
            splitLine: {show: false},
        };

        const xAxes: any[] = [{...xAxisBase, gridIndex: 0}];

        if (actualShowVolume) {
            xAxes.push({
                ...xAxisBase,
                gridIndex: 1,
                show: false, // hide x-axis labels on volume grid
            });
        }

        // ── Y-axes ──
        const colors = getChartColors(dark);
        const priceYAxis = buildPriceYAxis({mode: yAxisMode, min: yAxisMin, max: yAxisMax, isPercentage}, colors, {gridIndex: 0, showGridLines});
        const yAxes: any[] = [priceYAxis, ...secondaryAxes];

        if (actualShowVolume) {
            // yAxis[3] — volume (grid[1], hidden)
            yAxes.push({
                type: 'value',
                gridIndex: 1,
                show: false,
                scale: false,
                splitLine: {show: false},
            });
        }

        // ── Tooltip ──
        const fmtPrice = (v: number) => {
            if (isPercentage) return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
            if (Math.abs(v) >= 100) return v.toFixed(2);
            if (Math.abs(v) >= 1) return v.toFixed(4);
            return v.toFixed(6).replace(/0+$/, '').replace(/\.$/, '.0');
        };

        // Build header label (asset name + icon + currency)
        const tooltipHeaderHtml = (() => {
            let label = mainSeriesLabel || currency || 'Price';
            let suffix = '';
            if (displayCurrencyProp && mainCurrencyProp && displayCurrencyProp !== mainCurrencyProp) {
                suffix = ` <span style="font-size:10px">(${displayCurrencyFlag || ''} ${displayCurrencyProp})</span>`;
            } else if (mainCurrencyProp) {
                suffix = ` <span style="font-size:10px">(${mainCurrencyFlagProp || ''} ${mainCurrencyProp})</span>`;
            }
            return signalLabelToHtml({label, iconUrl: mainIconUrl, assetType: mainAssetType, isCrown: true}, 15) + suffix;
        })();

        const tooltipFormatter = (params: any) => {
            const arr = Array.isArray(params) ? params : [params];
            if (!arr.length) return '';

            const date = arr[0].axisValue ?? arr[0].name ?? '';
            let html = `<div style="font-size:12px;font-weight:600;margin-bottom:2px;color:${dark ? '#e2e8f0' : '#1f2937'}">${date}</div>`;
            html += `<div style="font-size:11px;margin-bottom:3px">${tooltipHeaderHtml}</div>`;

            for (const p of arr) {
                if (p.seriesName === 'Volume') {
                    const vol: number = p.value ?? 0;
                    const volFmt = vol >= 1_000_000 ? `${(vol / 1_000_000).toFixed(2)}M` : vol >= 1_000 ? `${(vol / 1_000).toFixed(1)}K` : vol.toFixed(0);
                    html += `<div style="color:${dark ? '#94a3b8' : '#6b7280'};font-size:11px;margin-top:3px">Vol: ${volFmt}</div>`;
                    continue;
                }

                if (p.seriesType === 'candlestick' && Array.isArray(p.value)) {
                    const [open, close, low, high] = p.value as number[];
                    const bullish = close >= open;
                    const clr = bullish ? greenColor : redColor;
                    const dimClr = dark ? '#94a3b8' : '#6b7280';
                    html += `<div style="display:grid;grid-template-columns:auto 1fr;gap:0 6px;font-size:11px;margin-top:2px">`;
                    html += `<span style="color:${dimClr}">O</span><span style="color:${clr}">${fmtPrice(open)}</span>`;
                    html += `<span style="color:${dimClr}">H</span><span style="color:${clr}">${fmtPrice(high)}</span>`;
                    html += `<span style="color:${dimClr}">L</span><span style="color:${clr}">${fmtPrice(low)}</span>`;
                    html += `<span style="color:${dimClr}">C</span><span style="color:${clr};font-weight:600">${fmtPrice(close)}</span>`;
                    html += `</div>`;
                    continue;
                }

                // Overlay signal line
                if (p.value !== null && p.value !== undefined) {
                    html += `<div style="font-size:11px"><span style="color:${p.color ?? '#888'}">${p.seriesName}: ${typeof p.value === 'number' ? p.value.toFixed(4) : p.value}</span></div>`;
                }
            }
            return html;
        };

        const option: echarts.EChartsOption = {
            animation: false,
            grid: grids,
            dataZoom: buildDataZoom(actualShowVolume ? [0, 1] : [0]),
            xAxis: xAxes,
            yAxis: yAxes,
            tooltip: {
                trigger: 'axis' as const,
                axisPointer: {type: 'cross' as const, crossStyle: {color: dark ? '#475569' : '#9ca3af'}},
                backgroundColor: dark ? '#1e293b' : '#ffffff',
                borderColor: dark ? '#334155' : '#e5e7eb',
                textStyle: {color: dark ? '#e2e8f0' : '#111827', fontSize: 12},
                formatter: tooltipFormatter,
            },
            series,
        };

        chartInstance.setOption(option, true);
        chartOptionSet = true;
        updateArrowRotations(chartInstance);
    }
</script>

<div bind:this={chartContainer} class="w-full" class:cursor-crosshair={measureMode} data-testid="candlestick-chart" style="height: {height};"></div>
