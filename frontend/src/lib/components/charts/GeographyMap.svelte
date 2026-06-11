<!--
  GeographyMap — Choropleth world map for geographic distribution visualization.

  Shows countries colored by weight using ECharts map series.
  Data keys are ISO 3166-1 Alpha-3 codes (USA, DEU, ITA, etc.)
  mapped to the GeoJSON country names via the ISO_A3 property embedded in world.json.

  Country names, ISO-2 codes, and flag emoji are resolved via countryStore
  (backed by GET /api/v1/utilities/countries).

  Props:
  - data: Record<string, number> — ISO A3 code → weight (0-1)
  - height: CSS height (default "320px")
  - language: Language code for localized names (e.g. 'it', 'en')

  Requires:
  - /data/world.json (ECharts GeoJSON with ISO_A3 property) in static folder
  - countryStore loaded for the current language

  Used by:
  - Asset Detail Page (metadata section)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {_ as t} from '$lib/i18n';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Geographic distribution: key = ISO A3 code, value = weight (0-1) */
        data: Record<string, number>;
        /** CSS height of the chart container */
        height?: string;
        /** Language code for localized country names (e.g. 'it', 'en') */
        language?: string;
    }

    let {data = {}, height = '320px', language = 'en'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let mapRegistered = $state(false);
    let mapError = $state<string | null>(null);

    /** Percentage of value with no geographic classification (key "Unknown" in data) */
    const unknownPct = $derived(+((data['Unknown'] ?? 0) * 100).toFixed(1));

    /** ISO A3 → GeoJSON feature name (built dynamically from loaded world.json) */
    let iso3ToGeoName: Record<string, string> = {};
    /** GeoJSON feature name → ISO A3 (reverse of above) */
    let geoNameToIso3: Record<string, string> = {};

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        registerWorldMap();
        // Re-render on dark mode toggle
        const observer = new MutationObserver(() => renderChart());
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    // Load country data from backend via countryStore when language changes
    $effect(() => {
        ensureCountriesLoaded(language).then(() => {
            // Re-render chart with new localized names
            renderChart();
        });
    });

    $effect(() => {
        if (chartContainer && data && mapRegistered) {
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
    // Map Registration
    // =========================================================================

    async function registerWorldMap() {
        try {
            const response = await fetch('/data/world.json');
            if (!response.ok) {
                mapError = `Failed to load map data (HTTP ${response.status})`;
                return;
            }
            const geoJson = await response.json();

            // Build ISO A3 ↔ GeoJSON name mappings from the enriched GeoJSON
            iso3ToGeoName = {};
            geoNameToIso3 = {};
            for (const feature of geoJson.features ?? []) {
                const name: string = feature.properties?.name ?? '';
                const iso3: string = feature.properties?.ISO_A3 ?? '';
                if (name && iso3) {
                    iso3ToGeoName[iso3] = name;
                    geoNameToIso3[name] = iso3;
                }
            }

            echarts.registerMap('world', geoJson as any);
            mapRegistered = true;
        } catch (e: any) {
            console.error('Failed to load world map GeoJSON:', e);
            mapError = 'Failed to load map data';
        }
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart() {
        if (!chartContainer || !mapRegistered) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
        }

        const isDark = document.documentElement.classList.contains('dark');

        // Convert ISO A3 → GeoJSON country name + percentage (skip unclassified)
        const chartData: Array<{name: string; value: number}> = [];
        for (const [code, weight] of Object.entries(data)) {
            if (weight <= 0 || code === 'Unknown') continue;
            const countryName = iso3ToGeoName[code] ?? code;
            chartData.push({name: countryName, value: +(weight * 100).toFixed(2)});
        }

        const maxValue = chartData.length > 0 ? Math.max(...chartData.map((d) => d.value)) : 100;

        // Restore full roam on desktop; pinch-zoom only on touch to avoid blocking page scroll
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

        const labelFormatter = (params: any) => {
            if (params.value == null || isNaN(params.value) || params.value === 0) return '';
            const iso3 = geoNameToIso3[params.name] ?? '';
            const info = iso3 ? getCountryInfo(iso3) : null;
            const flag = info?.flag_emoji ?? '';
            const displayName = info?.name ?? params.name;
            const prefix = flag ? `${flag} ` : '';
            return `${prefix}${displayName}: ${params.value}%`;
        };

        const option: echarts.EChartsOption = {
            // tooltip: {
            //     trigger: 'item',
            //     formatter: tooltipFormatter,
            //     backgroundColor: isDark ? '#1e293b' : '#fff',
            //     borderColor: isDark ? '#334155' : '#e2e8f0',
            //     textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
            // },
            visualMap: {
                min: 0,
                max: maxValue,
                text: [`${maxValue.toFixed(0)}%`, '0%'],
                realtime: false,
                calculable: false,
                inRange: {
                    color: isDark ? ['#1e3a2f', '#22543d', '#276749', '#2f855a', '#38a169', '#48bb78'] : ['#f0fdf4', '#bbf7d0', '#86efac', '#4ade80', '#22c55e', '#16a34a'],
                },
                textStyle: {color: isDark ? '#94a3b8' : '#64748b', fontSize: 11},
                left: 'left',
                bottom: 10,
                orient: 'horizontal',
                itemWidth: 12,
                itemHeight: 80,
            },
            series: [
                {
                    name: 'Distribution',
                    type: 'map',
                    map: 'world',
                    roam: isTouchDevice ? 'scale' : true, // mobile: pinch-zoom only; desktop: full pan+zoom
                    scaleLimit: {min: 1, max: 5},
                    emphasis: {
                        label: {show: true, color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 10},
                        itemStyle: {areaColor: isDark ? '#fbbf24' : '#f59e0b'},
                    },
                    itemStyle: {
                        areaColor: isDark ? '#334155' : '#e2e8f0',
                        borderColor: isDark ? '#1e293b' : '#cbd5e1',
                        borderWidth: 0.5,
                    },
                    label: {
                        show: true,
                        formatter: labelFormatter,
                        fontSize: 9,
                        color: isDark ? '#e2e8f0' : '#1e293b',
                    },
                    labelLayout: {hideOverlap: true},
                    data: chartData,
                },
            ],
        };

        chartInstance.setOption(option, true);
        chartInstance.resize();
    }
</script>

{#if mapError}
    <div class="flex items-center justify-center text-sm text-gray-400 dark:text-gray-500 italic" style="height: {height};">
        {mapError}
    </div>
{:else}
    <div bind:this={chartContainer} class="w-full" style="height: {height};"></div>
    {#if unknownPct > 0}
        <p class="mt-1 text-[11px] text-gray-400 dark:text-gray-500 italic text-center leading-snug">
            {$t('dashboard.geoUnclassified', {values: {pct: unknownPct}})}
        </p>
    {/if}
{/if}
