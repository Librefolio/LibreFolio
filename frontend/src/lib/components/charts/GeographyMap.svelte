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
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {_ as t} from '$lib/i18n';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Geographic distribution: key = ISO A3 code, value = weight (0-1) */
        data: Record<string, number>;
        /** Absolute amounts per ISO A3 code in base currency (optional) */
        amounts?: Record<string, number>;
        /** CSS height of the chart container */
        height?: string;
        /** Language code for localized country names (e.g. 'it', 'en') */
        language?: string;
        /** Currency code for absolute amount formatting */
        currency?: string;
    }

    let {data = {}, amounts = {}, height = '320px', language = 'en', currency = 'EUR'}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let mapRegistered = $state(false);
    let mapError = $state<string | null>(null);
    let needsInitialLayoutStabilityPass = false;
    /** True once the user has zoomed in beyond the default "whole world" fit
     *  (scaleLimit.min is 1) — i.e. there is actually something to pan. Gates the
     *  two-finger pan handler below so it never bothers dispatching a guaranteed no-op
     *  at the default zoom. Two-finger touch never competes with native single-finger
     *  scroll, so — unlike an earlier single-finger attempt — this no longer needs to
     *  toggle `touch-action` on the container at all; a stray 1-finger swipe over the
     *  map always scrolls the page, zoomed or not. Kept in sync via the 'georoam' chart
     *  event (fired on every zoom/pan), reading back the true cumulative zoom from
     *  getOption() rather than the event payload's per-tick delta. */
    let isZoomedIn = $state(false);
    /** Tracks an in-progress manual two-finger pan drag (see the doc comment on
     *  `handleTouchPanStart` below for why two fingers, not one). Null when not dragging. */
    let touchPanState: {x: number; y: number} | null = null;

    /** Stable series id so manually-dispatched `geoRoam` actions (see handleTouchPanMove)
     *  target this exact series — matches what ECharts' own roam→action dispatch does
     *  internally (`api.dispatchAction({seriesId: seriesModel.id, type: 'geoRoam', dx, dy})`
     *  in zrender's roamHelper.js), just with an explicit id instead of an auto-assigned one. */
    const GEO_SERIES_ID = 'geo-distribution-map';

    /** Percentage of value with no geographic classification (key "Unknown" or "Other" in data).
     *  "Other" is a provider placeholder for "rest of world" — treated as unclassified. */
    const unknownPct = $derived(+(((data['Unknown'] ?? 0) + (data['Other'] ?? 0)) * 100).toFixed(1));

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
        if (chartContainer) {
            chartContainer.removeEventListener('touchstart', handleTouchPanStart);
            chartContainer.removeEventListener('touchmove', handleTouchPanMove);
            chartContainer.removeEventListener('touchend', handleTouchPanEnd);
            chartContainer.removeEventListener('touchcancel', handleTouchPanEnd);
        }
        chartInstance?.dispose();
        chartInstance = null;
    }

    /** Manual TWO-finger drag-to-pan bridge for touch devices.
     *
     *  WHY TWO FINGERS, NOT ONE (verified by reading zrender's source, not guessed): on any
     *  modern mobile browser (Pointer Events API support, `'onpointerdown' in window`),
     *  zrender's `HandlerProxy` translates `pointerdown`/`pointerup` into the internal
     *  mousedown/mouseup zrender relies on regardless of origin — but its `pointermove`
     *  handler does `if (!isPointerFromTouch(event)) { ...translate to mousemove... }`, i.e.
     *  touch-sourced pointer movement is explicitly EXCLUDED from ever reaching
     *  `RoamController`'s pan tracking. That alone was fixable by tracking touch drags
     *  ourselves — but a SECOND, unrelated and unfixable problem showed up with a
     *  single-finger implementation: a browser decides "this touch gesture is native scroll"
     *  vs "this touch gesture is handled by JS" once, at the START of the gesture, and will
     *  NOT hand it back to native scrolling mid-gesture — so once a single-finger drag starts
     *  panning a zoomed map, reaching the edge (nothing left to pan) could not seamlessly
     *  continue as page scroll within that same continuous drag; the user would have to lift
     *  and re-touch. Reserving ONE finger exclusively for scrolling (always, with zero
     *  exceptions) and using TWO fingers for pan sidesteps the conflict entirely — a
     *  single-finger drag is never intercepted at all, so it always scrolls the page
     *  normally, edge or no edge.
     *
     *  Dispatches the exact same `geoRoam` action ECharts' own desktop mouse-drag path would
     *  have dispatched (`api.dispatchAction({seriesId, type:'geoRoam', dx, dy})`, per
     *  zrender's roamHelper.js), computed from the CENTROID of the two touches — fully
     *  reusing ECharts' own transform/render logic. Runs independently of whatever already
     *  drives pinch-to-zoom (untouched by this fix, it was already working) — this only ever
     *  adjusts position, never scale, so the two naturally compose on a real 2-finger
     *  gesture that both translates and pinches at once. */
    function centroidOf(touches: TouchList): {x: number; y: number} {
        let x = 0;
        let y = 0;
        for (let i = 0; i < touches.length; i++) {
            x += touches[i].clientX;
            y += touches[i].clientY;
        }
        return {x: x / touches.length, y: y / touches.length};
    }

    function handleTouchPanStart(e: TouchEvent) {
        if (e.touches.length !== 2 || !isZoomedIn) {
            touchPanState = null;
            return;
        }
        touchPanState = centroidOf(e.touches);
    }

    function handleTouchPanMove(e: TouchEvent) {
        if (e.touches.length !== 2) {
            // Finger count changed mid-gesture (e.g. one lifted) — stop tracking rather than
            // computing a bogus delta against a stale reference point.
            touchPanState = null;
            return;
        }
        if (!touchPanState || !chartInstance) return;
        const centroid = centroidOf(e.touches);
        const dx = centroid.x - touchPanState.x;
        const dy = centroid.y - touchPanState.y;
        touchPanState = centroid;
        // Two-finger gestures never compete with native single-finger scroll, so this
        // preventDefault only ever suppresses the browser's own pinch-zoom-the-page
        // gesture — it can't block page scroll, which is exactly the point.
        e.preventDefault();
        chartInstance.dispatchAction({type: 'geoRoam', seriesId: GEO_SERIES_ID, dx, dy});
    }

    function handleTouchPanEnd(e: TouchEvent) {
        // Re-arm if exactly 2 touches remain (e.g. a 3rd finger lifted back to 2); otherwise
        // stop — a drop to 0 or 1 remaining touch ends the pan gesture.
        touchPanState = e.touches.length === 2 && isZoomedIn ? centroidOf(e.touches) : null;
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
            needsInitialLayoutStabilityPass = true;
            chartInstance.on('georoam', () => {
                const opt = chartInstance?.getOption() as {series?: Array<{zoom?: number}>} | undefined;
                const zoom = opt?.series?.[0]?.zoom ?? 1;
                isZoomedIn = zoom > 1.01;
            });
            // {passive: false} is required — we conditionally call preventDefault() in
            // handleTouchPanMove, which a passive listener would silently ignore.
            chartContainer.addEventListener('touchstart', handleTouchPanStart, {passive: true});
            chartContainer.addEventListener('touchmove', handleTouchPanMove, {passive: false});
            chartContainer.addEventListener('touchend', handleTouchPanEnd, {passive: true});
            chartContainer.addEventListener('touchcancel', handleTouchPanEnd, {passive: true});
        }

        const isDark = document.documentElement.classList.contains('dark');

        // Convert ISO A3 → GeoJSON country name + percentage (skip unclassified)
        const chartData: Array<{name: string; value: number}> = [];
        for (const [code, weight] of Object.entries(data)) {
            if (weight <= 0 || code === 'Unknown' || code === 'Other') continue;
            const countryName = iso3ToGeoName[code] ?? code;
            chartData.push({name: countryName, value: +(weight * 100).toFixed(2)});
        }

        const maxValue = chartData.length > 0 ? Math.max(...chartData.map((d) => d.value)) : 100;

        // Fixed label — show flag + translated country name + % + absolute amount on hover
        const labelFormatter = (params: any) => {
            const iso3 = geoNameToIso3[params.name] ?? '';
            const info = iso3 ? getCountryInfo(iso3) : null;
            const flag = info?.flag_emoji ?? '';
            const displayName = info?.name ?? params.name;
            const prefix = flag ? `${flag} ` : '';
            if (params.value != null && !isNaN(params.value) && params.value > 0) {
                const absAmt = iso3 ? amounts[iso3] : undefined;
                const amtLine = absAmt != null && absAmt > 0 ? `\n${formatCurrencyAmountPlain(absAmt, currency, {showSign: false})}` : '';
                return `${prefix}${displayName}: ${params.value}%${amtLine}`;
            }
            return `${prefix}${displayName}`;
        };

        const fixedLabelStyle = {
            show: true,
            formatter: labelFormatter,
            color: isDark ? '#e2e8f0' : '#1e293b',
            fontSize: 10,
            backgroundColor: isDark ? 'rgba(15, 23, 42, 0.55)' : 'rgba(255,255,255,0.72)',
            borderRadius: 4,
            padding: [1, 3],
        };

        const option: echarts.EChartsOption = {
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
                    id: GEO_SERIES_ID,
                    roam: true,
                    scaleLimit: {min: 1, max: 5},
                    emphasis: {
                        label: fixedLabelStyle,
                        itemStyle: {areaColor: isDark ? '#fbbf24' : '#f59e0b'},
                    },
                    select: {
                        label: fixedLabelStyle,
                        itemStyle: {areaColor: isDark ? '#fbbf24' : '#f59e0b'},
                    },
                    itemStyle: {
                        areaColor: isDark ? '#334155' : '#e2e8f0',
                        borderColor: isDark ? '#1e293b' : '#cbd5e1',
                        borderWidth: 0.5,
                    },
                    // Always show translated fixed labels for countries that have data.
                    label: {show: false},
                    labelLayout: {hideOverlap: true},
                    data: chartData,
                },
            ],
        };

        chartInstance.setOption(option, CHART_SET_OPTION_OPTS);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }
    }
</script>

{#if mapError}
    <div class="flex items-center justify-center text-sm text-gray-400 dark:text-gray-500 italic" style="height: {height};">
        {mapError}
    </div>
{:else}
    <!-- Outer wrapper takes the exact allocated height; chart fills flex-1 so the
         optional "unclassified" paragraph doesn't push the canvas outside bounds. -->
    <div class="flex flex-col" style="height: {height};">
        <div bind:this={chartContainer} class="w-full flex-1 min-h-0"></div>
        {#if unknownPct > 0}
            <p class="mt-1 text-[11px] text-gray-400 dark:text-gray-500 italic text-center leading-snug">
                {$t('dashboard.geoUnclassified', {values: {pct: unknownPct}})}
            </p>
        {/if}
    </div>
{/if}
