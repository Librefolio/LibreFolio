<!--
  SemiDonutChart — Half-donut (semi-circle) pie chart for ownership visualization.

  Extracted from BrokerSharingModal to be reusable across the application.
  Shows ownership distribution as a semi-circle with avatar labels.

  Features:
  - Semi-circle pie chart (180°-360°)
  - Circular avatar images pre-clipped via offscreen canvas
  - Initial letter fallback when no avatar available
  - "Available" slice for unallocated percentage
  - Dark mode support
  - ResizeObserver for responsive sizing
  - Diversified color palette with high chromatic distance

  Used by:
  - BrokerSharingModal (ownership distribution)
  - Dashboard (future - portfolio allocation)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';

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

    let {
        data = [],
        availableLabel = 'Available',
        height = '180px',
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;

    // Diversified color palette — high chromatic distance between adjacent slices
    const PALETTE = ['#1a4031', '#2563eb', '#7c3aed', '#dc2626', '#d97706', '#0d9488', '#be185d', '#4f46e5'];

    // Cache for circular avatar data URLs
    const circularAvatarCache = new Map<string, string>();

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        return () => cleanup();
    });

    $effect(() => {
        // Re-render when data changes or container appears
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
            chartInstance?.resize();
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

    async function renderChart() {
        if (!chartContainer) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
        }

        const isDark = document.documentElement.classList.contains('dark');
        const avatarSize = 44;
        const borderColor = isDark ? '#334155' : '#ffffff';
        const borderWidth = 2;

        // Pre-load circular avatars in parallel
        const avatarPromises: Array<{ index: number; promise: Promise<string> }> = [];
        data.forEach((slice, i) => {
            if (slice.avatarUrl && slice.percentage > 0) {
                const url = slice.avatarUrl.includes('?') ? slice.avatarUrl : `${slice.avatarUrl}?img_preview=64x64`;
                avatarPromises.push({index: i, promise: createCircularImage(url, avatarSize, borderColor, borderWidth)});
            }
        });

        const resolvedAvatars = await Promise.all(
            avatarPromises.map(async (p) => ({index: p.index, dataUrl: await p.promise}))
        );
        const avatarMap = new Map<number, string>();
        resolvedAvatars.forEach(r => {
            if (r.dataUrl) avatarMap.set(r.index, r.dataUrl);
        });

        // Build chart data
        const chartData: Array<{ value: number; name: string; itemStyle?: any; label?: any }> = [];
        const totalAllocated = data.reduce((sum, s) => sum + s.percentage, 0);

        data.forEach((slice, i) => {
            if (slice.percentage <= 0) return;

            const initial = slice.name.charAt(0).toUpperCase();
            const totalIconSize = avatarSize + borderWidth * 2;
            const rich: Record<string, any> = {
                pct: {
                    fontSize: 11,
                    fontWeight: 'bold',
                    color: isDark ? '#e2e8f0' : '#1e293b',
                    lineHeight: 18,
                    padding: [2, 0, 0, 0],
                    align: 'center',
                    textShadowColor: isDark ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.8)',
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
                formatter = `{avatar| }\n{pct|${slice.percentage.toFixed(1)}%}`;
            } else {
                rich['avatar'] = {
                    fontSize: 18,
                    fontWeight: 'bold',
                    color: '#fff',
                    backgroundColor: PALETTE[i % PALETTE.length],
                    borderRadius: avatarSize / 2,
                    width: avatarSize,
                    height: avatarSize,
                    align: 'center',
                    lineHeight: avatarSize,
                    borderColor: isDark ? '#334155' : '#ffffff',
                    borderWidth: 2,
                };
                formatter = `{avatar|${initial}}\n{pct|${slice.percentage.toFixed(1)}%}`;
            }

            chartData.push({
                value: slice.percentage,
                name: slice.name,
                label: {show: true, formatter, rich},
            });
        });

        // Available slice
        const avail = Math.max(0, 100 - totalAllocated);
        if (avail > 0.01) {
            chartData.push({
                value: avail,
                name: availableLabel,
                itemStyle: {color: isDark ? 'rgba(100,116,139,0.3)' : 'rgba(203,213,225,0.5)'},
                label: {show: false},
            });
        }

        // Edge case: no data
        if (chartData.length === 0) {
            chartData.push({
                value: 100,
                name: `${availableLabel} (100%)`,
                itemStyle: {color: isDark ? 'rgba(100,116,139,0.3)' : 'rgba(203,213,225,0.5)'},
                label: {show: false},
            });
        }

        const option: echarts.EChartsOption = {
            color: PALETTE,
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c}%',
                backgroundColor: isDark ? '#1e293b' : '#fff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b'},
            },
            series: [{
                type: 'pie',
                radius: ['55%', '95%'],
                center: ['50%', '85%'],
                startAngle: 180,
                endAngle: 360,
                padAngle: 2,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: isDark ? '#1e293b' : '#ffffff',
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
                    lineStyle: {color: isDark ? '#475569' : '#94a3b8'},
                },
                emphasis: {
                    label: {show: true},
                    scaleSize: 4,
                },
                data: chartData,
            }],
        };

        chartInstance.setOption(option, true);
        chartInstance.resize();
    }
</script>

<div
        bind:this={chartContainer}
        class="w-full"
        style="height: {height};"
></div>

