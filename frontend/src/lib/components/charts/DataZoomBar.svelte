<!--
  DataZoomBar — ECharts dataZoom slider for time range navigation.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    interface DataPoint { date: string; value: number; }
    interface Props {
        data: DataPoint[];
        zoomRange?: [number, number];
        onZoomChange?: (start: number, end: number) => void;
        height?: string;
        lineColor?: string;
    }
    let {
        data = [], zoomRange = [0, 100], onZoomChange,
        height = '60px', lineColor = '#1a4031',
    }: Props = $props();
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    onMount(() => () => { resizeObserver?.disconnect(); chartInstance?.dispose(); });
    $effect(() => { if (chartContainer && data.length > 0) tick().then(renderChart); });
    function renderChart() {
        if (!chartContainer) return;
        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            chartInstance.on('datazoom', (params: any) => {
                if (onZoomChange && params.start !== undefined) onZoomChange(params.start, params.end);
            });
            if (!resizeObserver) {
                resizeObserver = new ResizeObserver(() => chartInstance?.resize());
                resizeObserver.observe(chartContainer);
            }
        }
        const isDark = document.documentElement.classList.contains('dark');
        const color = isDark ? '#4ade80' : lineColor;
        chartInstance.setOption({
            animation: false,
            grid: {top: 0, right: 0, bottom: 0, left: 0},
            xAxis: {type: 'category', data: data.map(d => d.date), show: false},
            yAxis: {type: 'value', show: false, scale: true},
            series: [{
                type: 'line', data: data.map(d => d.value), smooth: true, symbol: 'none',
                lineStyle: {width: 1, color, opacity: 0.5},
                areaStyle: {color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    {offset: 0, color: isDark ? 'rgba(74,222,128,0.15)' : 'rgba(26,64,49,0.1)'},
                    {offset: 1, color: 'transparent'},
                ])},
            }],
            dataZoom: [{
                type: 'slider', xAxisIndex: 0, start: zoomRange[0], end: zoomRange[1],
                height: '100%', top: 0,
                borderColor: isDark ? '#475569' : '#d1d5db',
                backgroundColor: isDark ? 'rgba(30,41,59,0.5)' : 'rgba(243,244,246,0.5)',
                fillerColor: isDark ? 'rgba(74,222,128,0.1)' : 'rgba(26,64,49,0.08)',
                handleStyle: {color: isDark ? '#4ade80' : '#1a4031'},
                textStyle: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 10},
                brushSelect: false,
            }],
        } as echarts.EChartsOption, true);
    }
</script>
<div bind:this={chartContainer} class="w-full" style="height: {height};"></div>
