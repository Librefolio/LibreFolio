<!--
  GeographyMap — Choropleth world map for geographic distribution visualization.

  Shows countries colored by weight using ECharts map series.
  Data keys are ISO 3166-1 Alpha-3 codes (USA, DEU, ITA, etc.)
  mapped to the GeoJSON country names via an internal lookup table.

  Props:
  - data: Record<string, number> — ISO A3 code → weight (0-1)
  - height: CSS height (default "320px")

  Requires:
  - /data/world.json (ECharts GeoJSON) in static folder

  Used by:
  - Asset Detail Page (metadata section)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';

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

    let {
        data = {},
        height = '320px',
        language = 'en',
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let mapRegistered = $state(false);
    let mapError = $state<string | null>(null);
    let localizedNames = $state<Record<string, string>>({});

    // =========================================================================
    // ISO A3 → ECharts GeoJSON name mapping
    // =========================================================================

    const ISO_A3_TO_NAME: Record<string, string> = {
        AFG: 'Afghanistan', ALB: 'Albania', DZA: 'Algeria', AGO: 'Angola',
        ARG: 'Argentina', ARM: 'Armenia', AUS: 'Australia', AUT: 'Austria',
        AZE: 'Azerbaijan', BHS: 'Bahamas', BGD: 'Bangladesh', BLR: 'Belarus',
        BEL: 'Belgium', BLZ: 'Belize', BEN: 'Benin', BTN: 'Bhutan',
        BOL: 'Bolivia', BIH: 'Bosnia and Herz.', BWA: 'Botswana', BRA: 'Brazil',
        BRN: 'Brunei', BGR: 'Bulgaria', BFA: 'Burkina Faso', BDI: 'Burundi',
        KHM: 'Cambodia', CMR: 'Cameroon', CAN: 'Canada', CAF: 'Central African Rep.',
        TCD: 'Chad', CHL: 'Chile', CHN: 'China', COL: 'Colombia',
        COG: 'Congo', COD: 'Dem. Rep. Congo', CRI: 'Costa Rica', CIV: "Côte d'Ivoire",
        HRV: 'Croatia', CUB: 'Cuba', CYP: 'Cyprus', CZE: 'Czech Rep.',
        DNK: 'Denmark', DJI: 'Djibouti', DOM: 'Dominican Rep.', ECU: 'Ecuador',
        EGY: 'Egypt', SLV: 'El Salvador', GNQ: 'Eq. Guinea', ERI: 'Eritrea',
        EST: 'Estonia', ETH: 'Ethiopia', FLK: 'Falkland Is.', FJI: 'Fiji',
        FIN: 'Finland', FRA: 'France', GAB: 'Gabon', GMB: 'Gambia',
        GEO: 'Georgia', DEU: 'Germany', GHA: 'Ghana', GRC: 'Greece',
        GRL: 'Greenland', GTM: 'Guatemala', GIN: 'Guinea', GNB: 'Guinea-Bissau',
        GUY: 'Guyana', HTI: 'Haiti', HND: 'Honduras', HUN: 'Hungary',
        ISL: 'Iceland', IND: 'India', IDN: 'Indonesia', IRN: 'Iran',
        IRQ: 'Iraq', IRL: 'Ireland', ISR: 'Israel', ITA: 'Italy',
        JAM: 'Jamaica', JPN: 'Japan', JOR: 'Jordan', KAZ: 'Kazakhstan',
        KEN: 'Kenya', PRK: 'North Korea', KOR: 'Korea', KWT: 'Kuwait',
        KGZ: 'Kyrgyzstan', LAO: 'Lao PDR', LVA: 'Latvia', LBN: 'Lebanon',
        LSO: 'Lesotho', LBR: 'Liberia', LBY: 'Libya', LTU: 'Lithuania',
        LUX: 'Luxembourg', MKD: 'Macedonia', MDG: 'Madagascar', MWI: 'Malawi',
        MYS: 'Malaysia', MLI: 'Mali', MRT: 'Mauritania', MEX: 'Mexico',
        MDA: 'Moldova', MNG: 'Mongolia', MNE: 'Montenegro', MAR: 'Morocco',
        MOZ: 'Mozambique', MMR: 'Myanmar', NAM: 'Namibia', NPL: 'Nepal',
        NLD: 'Netherlands', NZL: 'New Zealand', NIC: 'Nicaragua', NER: 'Niger',
        NGA: 'Nigeria', NOR: 'Norway', OMN: 'Oman', PAK: 'Pakistan',
        PAN: 'Panama', PNG: 'Papua New Guinea', PRY: 'Paraguay', PER: 'Peru',
        PHL: 'Philippines', POL: 'Poland', PRT: 'Portugal', QAT: 'Qatar',
        ROU: 'Romania', RUS: 'Russia', RWA: 'Rwanda', SAU: 'Saudi Arabia',
        SEN: 'Senegal', SRB: 'Serbia', SLE: 'Sierra Leone', SGP: 'Singapore',
        SVK: 'Slovakia', SVN: 'Slovenia', SLB: 'Solomon Is.', SOM: 'Somalia',
        ZAF: 'South Africa', SSD: 'S. Sudan', ESP: 'Spain', LKA: 'Sri Lanka',
        SDN: 'Sudan', SUR: 'Suriname', SWZ: 'Swaziland', SWE: 'Sweden',
        CHE: 'Switzerland', SYR: 'Syria', TWN: 'Taiwan', TJK: 'Tajikistan',
        TZA: 'Tanzania', THA: 'Thailand', TLS: 'Timor-Leste', TGO: 'Togo',
        TTO: 'Trinidad and Tobago', TUN: 'Tunisia', TUR: 'Turkey',
        TKM: 'Turkmenistan', UGA: 'Uganda', UKR: 'Ukraine',
        ARE: 'United Arab Emirates', GBR: 'United Kingdom', USA: 'United States',
        URY: 'Uruguay', UZB: 'Uzbekistan', VUT: 'Vanuatu', VEN: 'Venezuela',
        VNM: 'Vietnam', PSE: 'W. Sahara', YEM: 'Yemen', ZMB: 'Zambia',
        ZWE: 'Zimbabwe',
    };

    // Reverse lookup: English GeoJSON name → ISO A3
    const NAME_TO_ISO_A3: Record<string, string> = {};
    for (const [code, name] of Object.entries(ISO_A3_TO_NAME)) {
        NAME_TO_ISO_A3[name] = code;
    }

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

    // Load localized country names from backend
    $effect(() => {
        const lang = language;
        if (lang === 'en') {
            localizedNames = {};  // English names are already in ISO_A3_TO_NAME
            return;
        }
        fetch(`/api/v1/utilities/countries?language=${lang}`)
            .then(r => r.ok ? r.json() : {items: []})
            .then((response: {items: Array<{iso3: string; name: string}>}) => {
                const map: Record<string, string> = {};
                for (const item of (response.items || [])) {
                    map[item.iso3] = item.name;
                }
                localizedNames = map;
                // Re-render chart with new names
                renderChart();
            })
            .catch(() => { localizedNames = {}; });
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

        // Convert ISO A3 → country name + percentage
        const chartData: Array<{ name: string; value: number }> = [];
        for (const [code, weight] of Object.entries(data)) {
            if (weight <= 0) continue;
            const countryName = ISO_A3_TO_NAME[code] ?? code;
            chartData.push({name: countryName, value: +(weight * 100).toFixed(2)});
        }

        const maxValue = chartData.length > 0 ? Math.max(...chartData.map(d => d.value)) : 100;

        const option: echarts.EChartsOption = {
            tooltip: {
                trigger: 'item',
                formatter: (params: any) => {
                    // Reverse lookup: GeoJSON name → ISO A3 → localized name
                    const iso3 = NAME_TO_ISO_A3[params.name];
                    const displayName = (iso3 && localizedNames[iso3]) || params.name;
                    if (params.value != null && !isNaN(params.value)) {
                        return `${displayName}: ${params.value}%`;
                    }
                    return displayName;
                },
                backgroundColor: isDark ? '#1e293b' : '#fff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
            },
            visualMap: {
                min: 0,
                max: maxValue,
                text: [`${maxValue.toFixed(0)}%`, '0%'],
                realtime: false,
                calculable: false,
                inRange: {
                    color: isDark
                        ? ['#1e3a2f', '#22543d', '#276749', '#2f855a', '#38a169', '#48bb78']
                        : ['#f0fdf4', '#bbf7d0', '#86efac', '#4ade80', '#22c55e', '#16a34a'],
                },
                textStyle: {color: isDark ? '#94a3b8' : '#64748b', fontSize: 11},
                left: 'left',
                bottom: 10,
                orient: 'horizontal',
                itemWidth: 12,
                itemHeight: 80,
            },
            series: [{
                name: 'Distribution',
                type: 'map',
                map: 'world',
                roam: true,
                scaleLimit: {min: 1, max: 5},
                emphasis: {
                    label: {show: true, color: isDark ? '#e2e8f0' : '#1e293b'},
                    itemStyle: {areaColor: isDark ? '#fbbf24' : '#f59e0b'},
                },
                itemStyle: {
                    areaColor: isDark ? '#334155' : '#e2e8f0',
                    borderColor: isDark ? '#1e293b' : '#cbd5e1',
                    borderWidth: 0.5,
                },
                label: {show: false},
                data: chartData,
            }],
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
    <div
        bind:this={chartContainer}
        class="w-full"
        style="height: {height};"
    ></div>
{/if}



