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
    import {attachChartReady} from '$lib/utils/chartReady';
    import {CHART_ANIMATION_CONFIG, namedPoint} from '$lib/components/charts/echartsAnimationConfig';
    import {INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import ResolutionBadge from '$lib/components/charts/ResolutionBadge.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {aggregateLineSeries, cascadeResolution, chooseInitialResolution, mapDateToBucket, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
    import {_, t} from '$lib/i18n';
    import {buildTooltipTheme, buildTooltipHeader, buildTooltipByThreshold, buildTooltipRow, tooltipPositionSide, setupTooltipAutoHide, scheduleFirstRenderStabilityFix, type TooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {getCountryInfo, ensureCountriesLoaded} from '$lib/stores/reference/countryStore';
    import {getSectorEmoji, ensureSectorsLoaded} from '$lib/stores/reference/sectorStore';
    import {getAssetTypeEmoji} from '$lib/components/dashboard/allocationTypeEmoji';
    import {assetTypeFamily, sectorI18nKey} from '$lib/utils/assetTypes';
    import {buildAllocationHierarchy} from '$lib/components/charts/allocationHierarchy';
    import {currentLanguage} from '$lib/stores/app/language';
    import {debug} from '$lib/debug';
    import {buildResponsiveXAxisPolicy} from '$lib/components/charts/responsiveXAxis';

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

    interface LogicalRange {
        startDate: string;
        endDate: string;
    }

    interface TemporalBucketRow {
        date: string;
        bucketStart: string;
        bucketEnd: string;
        valuesByName: Record<string, number>;
    }

    interface AggregatedAllocationDataset {
        resolution: ChartResolution;
        categoryNames: string[];
        rows: TemporalBucketRow[];
        dates: string[];
        sortedNames: string[];
        avgWeights: Record<string, number>;
        rawDataByName: Record<string, number[]>;
        seriesDataByName: Record<string, ReturnType<typeof namedPoint>[]>;
        lineSeriesByName: Record<string, LineDataPoint[]>;
    }

    /** One drawn series: its id, its colour and the raw categories it sums — one, except a type family (D375). */
    interface SeriesStyle {
        id: string;
        color: string;
        members: string[];
    }

    // Resolution switches recompute dataZoom with absolute startValue/endValue (not
    // percentages). The shared CHART_SET_OPTION_OPTS only replaceMerges 'series', so a plain
    // merge would combine the new startValue/endValue with any stale percentage-based
    // start/end left over from the user's own interactive zoom — a documented ECharts
    // conflict that collapses the visible window to empty (blank chart). Replacing
    // 'dataZoom' wholesale avoids that merge conflict.
    // https://github.com/apache/echarts/issues/8230
    const CHART_SERIES_UPDATE_OPTS: {notMerge: boolean; replaceMerge: string[]} = {notMerge: false, replaceMerge: ['series', 'dataZoom', 'xAxis']};

    let {data = [], height = '100%', loading = false, dimension = 'type'}: Props = $props();

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let responsiveXAxisCompact = false;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let visibilityObservers: MutationObserver[] = [];
    let visibilityObserved = false;
    let lastKnownVisibility: boolean | null = null;
    let currentResolution: ChartResolution = $state('daily');
    let logicalRange: LogicalRange | null = $state(null);

    let refDataVersion = $state(0);

    const aggregatedDataCache = new Map<ChartResolution, AggregatedAllocationDataset>();
    let lastDataRef: AllocationHistoryPoint[] | null = null;
    let lastRenderedResolution: ChartResolution | null = null;
    let resolutionCheckTimer: ReturnType<typeof setTimeout> | null = null;
    let shouldPickInitialResolution = true;
    let suppressDataZoomHandling = false;
    let needsInitialLayoutStabilityPass = false;
    /** The series ids, in order, last applied to the current instance; null before its first option. */
    let lastSeriesOrder: string | null = null;

    // Distinct colors for allocation categories — 14 slots, which is enough for
    // the `type` dimension and NOT enough for `sector`. Read the next paragraph
    // before assuming the count closes.
    //
    // The two palettes are paired slot by slot — slot 0 is green in both themes,
    // slot 1 blue, slot 2 amber … — so a category keeps its identity when the
    // theme is toggled. Any addition must preserve that pairing.
    //
    // Grown from 12 to 14. That closes ONE of the two dimensions this palette
    // serves:
    //
    //   type   — 12 base colours: the 11 families of assetTypeFamily (I's D15:
    //            the chart groups by vehicle, like the pie), plus the synthetic
    //            "Liquidity" bucket that `DailyStateBuilder.build` injects at its
    //            step 4h, outside the enum. Each family is drawn as ONE area in its
    //            base colour, and its subtypes appear only in the tooltip (D375).
    //            12 <= 14, so no family is ever handed another's colour. (At
    //            12 slots, grouping by content, it was: 13 keys, and the 13th took
    //            the colour of the 1st — the largest slice on screen.)
    //
    //   sector — 15 keys: the 14 of SECTOR_KEYS_FALLBACK, plus the same
    //            "Liquidity", which that same backend step injects into
    //            `by_sector` as well. 15 > 14, so ONE collision SURVIVES here:
    //            `palette[i % 14]` hands the 15th category the colour of the 1st.
    //            The names are sorted by weight, so that is the smallest slice
    //            wearing the largest slice's colour.
    //
    // That surviving case is hard to notice by design: the i18n label still
    // resolves (the `.toUpperCase()` normalisation further down is independent of
    // the palette), so the slice reads with the right name and the wrong colour —
    // which looks like a design choice, not a bug. It needs a portfolio holding
    // >=15 distinct sector buckets at once, so no fixture has ever produced it.
    //
    // Growing the palette again would NOT close it. getSectorKeysList() returns
    // getSectorKeys() from the API store and falls back to the 14 above only when
    // that store is empty: the real cardinality is backend data, not a constant,
    // so no number is provably sufficient. The mechanism is the defect — the
    // index WRAPS instead of SIGNALLING. Until that is cured (by deriving a shade
    // for the wrapped slot, so a collision becomes visible instead of silent),
    // the wrap is at least announced: see the debug.warn where `styling` is built.
    //
    // The two new slots were measured, not chosen: fuchsia (~295°) is the widest
    // hue gap left in BOTH palettes, and purple-700/400 follows it while keeping
    // the cross-theme pairing. The first 12 entries are untouched, so every chart
    // with 12 categories or fewer renders exactly as before.
    const PALETTE_LIGHT = ['#1a4031', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#ec4899', '#f97316', '#14b8a6', '#6366f1', '#a3a3a3', '#a21caf', '#7e22ce'];
    const PALETTE_DARK = ['#4ade80', '#60a5fa', '#fbbf24', '#f87171', '#a78bfa', '#22d3ee', '#a3e635', '#f472b6', '#fb923c', '#2dd4bf', '#818cf8', '#d4d4d4', '#e879f9', '#c084fc'];

    /** Get an emoji/icon label for a category. */
    function getCategoryEmoji(rawName: string): string {
        if (dimension === 'sector') return getSectorEmoji(rawName);
        if (dimension === 'geo') {
            if (rawName === 'Other' || rawName === 'Unknown') return '🏳️';
            return getCountryInfo(rawName).flag_emoji || '🌍';
        }
        if (dimension === 'type') return getAssetTypeEmoji(rawName);
        return '';
    }

    onMount(() => {
        darkModeObserver = new MutationObserver(() => renderChart());
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        const loadRefs = async () => {
            await Promise.allSettled([ensureCountriesLoaded($currentLanguage), ensureSectorsLoaded()]);
            refDataVersion++;
        };
        loadRefs();

        return () => {
            if (resolutionCheckTimer) clearTimeout(resolutionCheckTimer);
            tooltipCleanup?.();
            disconnectVisibilityObservers();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance?.dispose();
        };
    });

    $effect(() => {
        void data;
        void dimension;
        void refDataVersion;
        void $currentLanguage;
        if (chartContainer) {
            tick().then(() => {
                setupVisibilityObservers();
                if (!resizeObserver && chartContainer) {
                    resizeObserver = new ResizeObserver(() => {
                        chartInstance?.resize();
                        if (chartInstance && chartContainer) {
                            const dataset = getResolutionDataset(currentResolution);
                            const policy = buildResponsiveXAxisPolicy({
                                width: chartContainer.clientWidth,
                                values: dataset.dates,
                                locale: $currentLanguage,
                                axisType: 'time',
                            });
                            const wasCompact = responsiveXAxisCompact;
                            responsiveXAxisCompact = policy.compact;
                            if (policy.axisLabel) {
                                chartInstance.setOption({xAxis: {splitNumber: policy.splitNumber, axisLabel: policy.axisLabel}}, {lazyUpdate: true});
                            } else if (wasCompact) {
                                renderChart();
                            }
                        }
                        scheduleResolutionCheck();
                    });
                    resizeObserver.observe(chartContainer);
                }
                syncVisibilityState();
                renderChart();
            });
        }
    });

    function disconnectVisibilityObservers() {
        for (const observer of visibilityObservers) observer.disconnect();
        visibilityObservers = [];
        visibilityObserved = false;
    }

    function isChartVisible(container: HTMLElement): boolean {
        if (!container.isConnected || container.getClientRects().length === 0) return false;
        const style = getComputedStyle(container);
        return style.display !== 'none' && style.visibility !== 'hidden';
    }

    function syncVisibilityState() {
        if (!chartContainer) return;
        const visible = isChartVisible(chartContainer);
        if (visible === lastKnownVisibility) return;
        lastKnownVisibility = visible;

        if (!visible) {
            chartInstance?.dispatchAction({type: 'hideTip'});
            return;
        }

        if (chartInstance) {
            chartInstance.resize();
        }
        renderChart({skipAnimation: true});
    }

    function setupVisibilityObservers() {
        if (!chartContainer || visibilityObserved) return;
        let ancestor = chartContainer.parentElement;
        while (ancestor) {
            const observer = new MutationObserver(() => syncVisibilityState());
            observer.observe(ancestor, {attributes: true, attributeFilter: ['class', 'style', 'hidden']});
            visibilityObservers.push(observer);
            ancestor = ancestor.parentElement;
        }
        visibilityObserved = true;
    }

    /** Localize category label. Temporal resolution pipeline stays fully separate. */
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
            // The engine injects the cash slice as "Liquidity" (capitalized) while every
            // other type is an uppercase enum — normalize so `assets.types.LIQUIDITY`
            // resolves instead of leaking the raw i18n path into the chart.
            const key = `assets.types.${rawName.toUpperCase()}`;
            const localized = $t(key);
            return localized !== key ? localized : rawName;
        }
        return rawName;
    }

    function toUtcDate(value: string): Date {
        return new Date(`${value}T00:00:00Z`);
    }

    function normalizeAxisDate(value: unknown): string | null {
        if (typeof value === 'string') return value.slice(0, 10);
        if (typeof value === 'number') return new Date(value).toISOString().slice(0, 10);
        if (value instanceof Date) return value.toISOString().slice(0, 10);
        return null;
    }

    function getFullLogicalRangeFromData(): LogicalRange | null {
        if (data.length === 0) return null;
        const sorted = [...data].sort((left, right) => left.date.localeCompare(right.date));
        return {
            startDate: sorted[0].date,
            endDate: sorted[sorted.length - 1].date,
        };
    }

    function invalidateTemporalCacheIfNeeded() {
        if (data === lastDataRef) return;
        aggregatedDataCache.clear();
        lastDataRef = data;
        currentResolution = 'daily';
        logicalRange = getFullLogicalRangeFromData();
        lastRenderedResolution = null;
        shouldPickInitialResolution = true;
        if (resolutionCheckTimer) {
            clearTimeout(resolutionCheckTimer);
            resolutionCheckTimer = null;
        }
    }

    function finalizeDataset(resolution: ChartResolution, rows: TemporalBucketRow[], categoryNames: string[]): AggregatedAllocationDataset {
        const avgWeights: Record<string, number> = {};
        const rawDataByName: Record<string, number[]> = {};
        const lineSeriesByName: Record<string, LineDataPoint[]> = {};

        for (const name of categoryNames) {
            const values = rows.map((row) => row.valuesByName[name] ?? 0);
            rawDataByName[name] = values;
            lineSeriesByName[name] = rows.map((row) => ({date: row.date, value: row.valuesByName[name] ?? 0}));
            avgWeights[name] = values.length > 0 ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
        }

        const sortedNames = [...categoryNames].sort((left, right) => (avgWeights[right] ?? 0) - (avgWeights[left] ?? 0));
        const seriesDataByName: Record<string, ReturnType<typeof namedPoint>[]> = {};

        for (const name of sortedNames) {
            seriesDataByName[name] = rows.map((row) => namedPoint(row.date, row.valuesByName[name] ?? 0));
        }

        return {
            resolution,
            categoryNames,
            rows,
            dates: rows.map((row) => row.date),
            sortedNames,
            avgWeights,
            rawDataByName,
            seriesDataByName,
            lineSeriesByName,
        };
    }

    function buildDailyDataset(): AggregatedAllocationDataset {
        const sortedPoints = [...data].sort((left, right) => left.date.localeCompare(right.date));
        const categoryNames = [...new Set(sortedPoints.flatMap((point) => point.components.map((component) => component.name)))];
        const rows = sortedPoints.map((point) => {
            const valueMap = new Map(point.components.map((component) => [component.name, Number(component.value)]));
            const valuesByName: Record<string, number> = {};

            for (const name of categoryNames) {
                valuesByName[name] = valueMap.get(name) ?? 0;
            }

            return {
                date: point.date,
                bucketStart: point.date,
                bucketEnd: point.date,
                valuesByName,
            };
        });

        return finalizeDataset('daily', rows, categoryNames);
    }

    function buildAggregatedDataset(resolution: Exclude<ChartResolution, 'daily'>): AggregatedAllocationDataset {
        const dailyDataset = getResolutionDataset('daily');
        const rowsByDate = new Map<string, TemporalBucketRow>();

        for (const name of dailyDataset.categoryNames) {
            const aggregatedPoints = aggregateLineSeries(dailyDataset.lineSeriesByName[name] ?? [], resolution);

            for (const point of aggregatedPoints) {
                const meta = point as LineDataPoint & {bucketStart?: string; bucketEnd?: string};
                const bucketStart = meta.bucketStart ?? point.date;
                const bucketEnd = meta.bucketEnd ?? point.date;
                const existing = rowsByDate.get(point.date);

                if (existing) {
                    existing.valuesByName[name] = point.value ?? 0;
                    if (bucketStart < existing.bucketStart) existing.bucketStart = bucketStart;
                    if (bucketEnd > existing.bucketEnd) existing.bucketEnd = bucketEnd;
                } else {
                    rowsByDate.set(point.date, {
                        date: point.date,
                        bucketStart,
                        bucketEnd,
                        valuesByName: {[name]: point.value ?? 0},
                    });
                }
            }
        }

        const rows = [...rowsByDate.values()]
            .sort((left, right) => left.date.localeCompare(right.date))
            .map((row) => {
                const valuesByName: Record<string, number> = {};
                for (const name of dailyDataset.categoryNames) {
                    valuesByName[name] = row.valuesByName[name] ?? 0;
                }
                return {...row, valuesByName};
            });

        return finalizeDataset(resolution, rows, dailyDataset.categoryNames);
    }

    function getResolutionDataset(resolution: ChartResolution): AggregatedAllocationDataset {
        const cached = aggregatedDataCache.get(resolution);
        if (cached) return cached;

        const dataset = resolution === 'daily' ? buildDailyDataset() : buildAggregatedDataset(resolution);
        aggregatedDataCache.set(resolution, dataset);
        return dataset;
    }

    function getBucketCountsForRange(range: LogicalRange | null): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        const dailyDataset = getResolutionDataset('daily');
        const visibleRows = range ? dailyDataset.rows.filter((row) => row.date >= range.startDate && row.date <= range.endDate) : dailyDataset.rows;

        const weeklyBuckets = new Set<string>();
        const monthlyBuckets = new Set<string>();

        for (const row of visibleRows) {
            const weekly = mapDateToBucket(row.date, 'weekly');
            weeklyBuckets.add(`${weekly.bucketStart}|${weekly.bucketEnd}`);

            const monthly = mapDateToBucket(row.date, 'monthly');
            monthlyBuckets.add(`${monthly.bucketStart}|${monthly.bucketEnd}`);
        }

        return {
            dailyCount: visibleRows.length,
            weeklyCount: weeklyBuckets.size,
            monthlyCount: monthlyBuckets.size,
        };
    }

    function getRowsIntersectingRange(rows: TemporalBucketRow[], range: LogicalRange | null): TemporalBucketRow[] {
        if (!range) return rows;
        return rows.filter((row) => row.bucketEnd >= range.startDate && row.bucketStart <= range.endDate);
    }

    function findRowIndexAtOrAfter(rows: TemporalBucketRow[], date: string): number {
        const index = rows.findIndex((row) => row.date >= date);
        return index === -1 ? Math.max(rows.length - 1, 0) : index;
    }

    function findRowIndexAtOrBefore(rows: TemporalBucketRow[], date: string): number {
        for (let index = rows.length - 1; index >= 0; index--) {
            if (rows[index].date <= date) return index;
        }
        return 0;
    }

    function getRangeFromPercentages(rows: TemporalBucketRow[], start: number, end: number): LogicalRange | null {
        if (rows.length === 0) return null;
        const lastIndex = rows.length - 1;
        const clampedStart = Math.min(Math.max(start, 0), 100);
        const clampedEnd = Math.min(Math.max(end, 0), 100);
        const startIndex = Math.min(Math.floor((clampedStart / 100) * lastIndex), lastIndex);
        const endIndex = Math.min(Math.ceil((clampedEnd / 100) * lastIndex), lastIndex);
        const firstRow = rows[Math.min(startIndex, endIndex)];
        const lastRow = rows[Math.max(startIndex, endIndex)];

        return {
            startDate: firstRow.bucketStart,
            endDate: lastRow.bucketEnd,
        };
    }

    function getCurrentVisibleLogicalRange(): LogicalRange | null {
        const dataset = aggregatedDataCache.get(currentResolution);
        if (!chartInstance || !dataset || dataset.rows.length === 0) return logicalRange;

        let rawStart: unknown;
        let rawEnd: unknown;

        try {
            const option = chartInstance.getOption() as any;
            const dataZoom = option?.dataZoom?.[0];
            rawStart = dataZoom?.startValue;
            rawEnd = dataZoom?.endValue;

            if (rawStart == null || rawEnd == null) {
                const start = typeof dataZoom?.start === 'number' ? dataZoom.start : 0;
                const end = typeof dataZoom?.end === 'number' ? dataZoom.end : 100;
                return getRangeFromPercentages(dataset.rows, start, end);
            }
        } catch (_) {
            return logicalRange;
        }

        const startDate = normalizeAxisDate(rawStart);
        const endDate = normalizeAxisDate(rawEnd);
        if (!startDate || !endDate) return logicalRange;

        const firstIndex = findRowIndexAtOrAfter(dataset.rows, startDate);
        const lastIndex = findRowIndexAtOrBefore(dataset.rows, endDate);
        const firstRow = dataset.rows[Math.min(firstIndex, lastIndex)];
        const lastRow = dataset.rows[Math.max(firstIndex, lastIndex)];

        return {
            startDate: firstRow.bucketStart,
            endDate: lastRow.bucketEnd,
        };
    }

    function buildDataZoomOption(dataset: AggregatedAllocationDataset, range: LogicalRange | null): Record<string, unknown>[] {
        const baseDataZoom = {type: 'inside', ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG};
        const visibleRows = getRowsIntersectingRange(dataset.rows, range);
        if (visibleRows.length === 0) return [{...baseDataZoom, start: 0, end: 100}];
        return [
            {
                ...baseDataZoom,
                startValue: visibleRows[0].date,
                endValue: visibleRows[visibleRows.length - 1].date,
            },
        ];
    }

    function formatMonthLabel(date: string): string {
        return new Intl.DateTimeFormat($currentLanguage, {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC',
        }).format(toUtcDate(date));
    }

    function buildAllocationTooltipHeader(row: TemporalBucketRow, mutedColor: string): string {
        if (currentResolution === 'weekly') {
            return buildTooltipHeader($t('chart.tooltip.weekRange', {values: {start: row.bucketStart, end: row.bucketEnd}}), mutedColor) + buildTooltipHeader($t('chart.tooltip.valueAt', {values: {date: row.date}}), mutedColor);
        }

        if (currentResolution === 'monthly') {
            return buildTooltipHeader($t('chart.tooltip.monthLabel', {values: {month: formatMonthLabel(row.bucketStart)}}), mutedColor) + buildTooltipHeader($t('chart.tooltip.valueAt', {values: {date: row.date}}), mutedColor);
        }

        return buildTooltipHeader(row.date, mutedColor);
    }

    function getDisplayName(rawName: string): string {
        const emoji = getCategoryEmoji(rawName);
        const localized = localizeName(rawName);
        return emoji ? `${emoji} ${localized}` : localized;
    }

    /** One entry per asset family, in the hierarchy's group order, with its base colour verbatim and its raw members. */
    function familyStyling(dataset: AggregatedAllocationDataset, palette: readonly string[]): SeriesStyle[] {
        const hierarchy = buildAllocationHierarchy(
            dataset.sortedNames.map((name) => ({key: name, weight: dataset.avgWeights[name] ?? 0, item: name})),
            {resolvePrimary: assetTypeFamily, palette},
        );
        const families: SeriesStyle[] = [];
        for (const entry of hierarchy) {
            const current = families[families.length - 1];
            // A group's first member has depth 0, so its colour is the palette entry itself.
            if (current && current.id === entry.primary) current.members.push(entry.item);
            else families.push({id: entry.primary, color: entry.color, members: [entry.item]});
        }
        return families;
    }

    /**
     * The type tooltip under D375: families ranked by the day's value, then, under a family,
     * the members present that day — the generic one first, captioned as the pie captions it,
     * then the subtypes by value. A family holding only its own key is a single row. More
     * than six families: the top five and the rest summed, as before.
     */
    function buildFamilyTooltipRows(styling: readonly SeriesStyle[], dataset: AggregatedAllocationDataset, idx: number, theme: TooltipTheme, remainingLabel: string): string {
        const valueAt = (key: string) => dataset.rawDataByName[key]?.[idx] ?? 0;
        const percent = (value: number) => `${value.toFixed(1)}%`;
        const families = styling
            .map((family) => {
                const members = family.members.map((key) => ({key, value: valueAt(key), pure: key.toUpperCase() === family.id})).filter((member) => member.value > 0.01);
                return {...family, members, value: members.reduce((sum, member) => sum + member.value, 0)};
            })
            .filter((family) => family.value > 0.01)
            .sort((left, right) => right.value - left.value);
        const shown = families.length <= 6 ? families : families.slice(0, 5);
        const rest = families.slice(shown.length);

        let html = '';
        for (const family of shown) {
            let rows = buildTooltipRow(escapeHtml(getDisplayName(family.id)), percent(family.value), family.color);
            if (!(family.members.length === 1 && family.members[0].pure)) {
                const ordered = [...family.members].sort((left, right) => (left.pure !== right.pure ? (left.pure ? -1 : 1) : right.value - left.value));
                for (const member of ordered) {
                    const label = member.pure ? $t('dashboard.allocationGeneric', {values: {type: localizeName(family.id)}}) : getDisplayName(member.key);
                    rows += `<div data-allocation-member="${escapeHtml(member.key)}" style="padding-left:16px">${buildTooltipRow(escapeHtml(label), percent(member.value))}</div>`;
                }
            }
            html += `<div data-allocation-family="${escapeHtml(family.id)}">${rows}</div>`;
        }
        if (rest.length > 0) {
            const sum = rest.reduce((total, family) => total + family.value, 0);
            html += buildTooltipRow(escapeHtml(`${remainingLabel} (${rest.length})`), percent(sum), theme.mutedColor);
        }
        return html;
    }

    function buildChartOption(dataset: AggregatedAllocationDataset, isDark: boolean, skipAnimation: boolean): echarts.EChartsOption {
        const palette = isDark ? PALETTE_DARK : PALETTE_LIGHT;
        const textColor = isDark ? '#94a3b8' : '#64748b';
        const gridColor = isDark ? '#1e293b' : '#f1f5f9';
        const tooltipBg = isDark ? '#1e293b' : '#ffffff';
        const tooltipBorder = isDark ? '#334155' : '#e2e8f0';
        const xAxisPolicy = buildResponsiveXAxisPolicy({
            width: chartContainer?.clientWidth ?? 0,
            values: dataset.dates,
            locale: $currentLanguage,
            axisType: 'time',
        });
        responsiveXAxisCompact = xAxisPolicy.compact;

        // Order and colour are decided together, once, and consumed by both the
        // series and the tooltip — they must not drift apart.
        //
        // By type, one area per family (D375, developer, 05/10/2026: «Una sola area per
        // famiglia (ETF = somma di tutti), con i sottotipi solo nel tooltip»). The family
        // order and base colour are the pie's, from buildAllocationHierarchy by vehicle;
        // the shades it gives the members are not drawn here, so the stack never shows two
        // near-identical bands that read as an overlap.
        //
        // Deliberately not cached on the dataset: the dataset survives theme
        // changes, the palette does not.
        // The index wraps silently when there are more categories than slots: the
        // wrapped one wears an earlier category's colour, with its own name still
        // correct. Live today for `sector` — announce it rather than let it pass.
        // (The `type` branch reports its own wrap from inside the helper.)
        if (dimension !== 'type' && dataset.sortedNames.length > palette.length) {
            debug.warn('AllocationHistoryChart', `palette exhausted: ${dataset.sortedNames.length} "${dimension}" categories for ${palette.length} colours — ` + `${dataset.sortedNames.length - palette.length} will repeat an earlier colour`);
        }

        const styling: SeriesStyle[] = dimension === 'type' ? familyStyling(dataset, palette) : dataset.sortedNames.map((name, index) => ({id: name, color: palette[index % palette.length], members: [name]}));

        const series: echarts.SeriesOption[] = styling.map(({id, color, members}) => {
            const emoji = getCategoryEmoji(id);
            const averageWeight = members.reduce((sum, member) => sum + (dataset.avgWeights[member] ?? 0), 0);
            const showLabel = averageWeight >= 3 && emoji;

            return {
                id,
                name: getDisplayName(id),
                type: 'line',
                stack: 'allocation',
                data:
                    members.length === 1
                        ? dataset.seriesDataByName[members[0]]
                        : dataset.rows.map((row) =>
                              namedPoint(
                                  row.date,
                                  members.reduce((sum, member) => sum + (row.valuesByName[member] ?? 0), 0),
                              ),
                          ),
                smooth: false,
                symbol: 'none',
                lineStyle: {color, width: 1, opacity: 0.7},
                areaStyle: {color: color + '88'},
                itemStyle: {color},
                emphasis: {focus: 'series'},
                label: showLabel
                    ? {
                          show: true,
                          position: 'inside',
                          formatter: () => emoji,
                          fontSize: 14,
                          color: isDark ? '#ffffff' : '#000000',
                          textShadowColor: isDark ? '#000' : '#fff',
                          textShadowBlur: 2,
                      }
                    : {show: false},
            };
        });

        return {
            ...(skipAnimation ? {animation: false, animationDuration: 0, animationDurationUpdate: 0} : CHART_ANIMATION_CONFIG),
            backgroundColor: 'transparent',
            grid: {left: '3%', right: '4%', bottom: '40px', top: '10px', containLabel: true},
            tooltip: {
                trigger: 'axis',
                // Bugfix: `appendToBody` moves the tooltip DOM to `document.body`, which
                // requires ECharts/zrender to convert our chart-local position into
                // document-absolute coordinates (accounting for scroll) — the exact same
                // class of bug already fixed once in PriceChartFull.svelte (see commit
                // fcdd89e8: "Fix mobile tooltip scroll offset ... instead of
                // cursor-relative positioning that shifted with vertical scroll") and again
                // in GrowthChart.svelte, by dropping `appendToBody` entirely. Without it,
                // the tooltip stays nested inside this chart's own container (forced to
                // `position:relative`), scrolling as ONE unit with the rest of the page —
                // no coordinate conversion needed at all, so it can't drift out of sync
                // with scroll. Not needed for clipping either: this card (AllocationPanel)
                // has no `overflow-hidden` ancestor around the chart itself.
                confine: true,
                position: tooltipPositionSide,
                axisPointer: {type: 'line'},
                backgroundColor: tooltipBg,
                borderColor: tooltipBorder,
                borderWidth: 1,
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: unknown) => {
                    const items = Array.isArray(params) ? params : [params];
                    const idx = (items[0] as {dataIndex?: number} | undefined)?.dataIndex ?? 0;
                    const row = dataset.rows[idx];
                    if (!row) return '';

                    const theme = buildTooltipTheme(isDark);
                    const header = buildAllocationTooltipHeader(row, theme.mutedColor);
                    const remainingLabel = $_('common.remaining') || 'Remaining';
                    if (dimension === 'type') return header + buildFamilyTooltipRows(styling, dataset, idx, theme, remainingLabel);

                    const allItems = styling
                        .map(({id, color}) => ({
                            name: getDisplayName(id),
                            value: dataset.rawDataByName[id]?.[idx] ?? 0,
                            color,
                        }))
                        .filter((item) => item.value > 0.01);

                    return header + buildTooltipByThreshold(allItems, 3, theme, remainingLabel);
                },
            },
            legend: {
                bottom: 0,
                left: 'center',
                textStyle: {color: textColor, fontSize: 14},
                itemWidth: 12,
                itemHeight: 8,
                type: 'scroll',
                width: '90%',
                pageTextStyle: {color: textColor},
                pageIconColor: textColor,
                pageIconInactiveColor: isDark ? '#334155' : '#cbd5e1',
            },
            dataZoom: buildDataZoomOption(dataset, logicalRange),
            xAxis: {
                type: 'time',
                ...(xAxisPolicy.compact ? {splitNumber: xAxisPolicy.splitNumber} : {}),
                axisLabel: {color: textColor, fontSize: 14, rotate: 0, ...(xAxisPolicy.axisLabel ?? {})},
                axisLine: {lineStyle: {color: gridColor}},
                splitLine: {show: false},
            },
            yAxis: {
                type: 'value',
                max: 100,
                axisLabel: {color: textColor, fontSize: 14, formatter: (value: number) => `${value}%`},
                axisLine: {show: false},
                splitLine: {lineStyle: {color: gridColor, type: 'dashed'}},
            },
            series,
        };
    }

    function attachDataZoomListener() {
        if (!chartInstance) return;

        chartInstance.off('dataZoom');
        chartInstance.on('dataZoom', () => {
            if (suppressDataZoomHandling) return;
            scheduleResolutionCheck();
        });
    }

    // NOTE: getCurrentVisibleLogicalRange() internally calls chartInstance.getOption(),
    // which deep-clones the entire chart option (documented ECharts behavior) — expensive
    // on charts with years of daily data. It must only run ONCE, inside the debounced
    // timeout body below (after the zoom/resize gesture settles for 200ms), never on every
    // raw dataZoom/resize tick — otherwise it runs at interaction frequency (~60/sec) and
    // causes visible stutter.
    function scheduleResolutionCheck() {
        if (resolutionCheckTimer) clearTimeout(resolutionCheckTimer);

        resolutionCheckTimer = setTimeout(() => {
            resolutionCheckTimer = null;
            if (!chartInstance) return;

            const range = getCurrentVisibleLogicalRange() ?? logicalRange ?? getFullLogicalRangeFromData();
            if (!range) return;

            logicalRange = range;

            const nextResolution = cascadeResolution(currentResolution, getBucketCountsForRange(range), Math.max(chartInstance.getWidth(), 1));
            if (nextResolution === currentResolution) return;

            currentResolution = nextResolution;
            renderChart({skipAnimation: true});
        }, 200);
    }

    function renderChart(options: {skipAnimation?: boolean} = {}) {
        if (!chartContainer || loading || data.length === 0) return;
        if (!isChartVisible(chartContainer)) return;

        invalidateTemporalCacheIfNeeded();

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            attachChartReady(chartInstance, chartContainer, 'allocation-history');
            // ECharts draws to a canvas, so a colour has no DOM an E2E could read.
            // Exposing the instance is the only way a test can assert that the
            // hierarchy actually reached the option — same hook, same name, as
            // PriceChartFull.svelte.
            (chartContainer as unknown as Record<string, unknown>).__lfChart = chartInstance;
            needsInitialLayoutStabilityPass = true;
            lastSeriesOrder = null;
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
        }

        const fullRange = logicalRange ?? getFullLogicalRangeFromData();
        if (!logicalRange) logicalRange = fullRange;

        if (shouldPickInitialResolution && fullRange) {
            currentResolution = chooseInitialResolution(getBucketCountsForRange(fullRange), Math.max(chartInstance.getWidth(), 1));
            shouldPickInitialResolution = false;
        }

        const activeDataset = getResolutionDataset(currentResolution);
        const isDark = document.documentElement.classList.contains('dark');
        const skipAnimation = options.skipAnimation ?? (lastRenderedResolution !== null && lastRenderedResolution !== currentResolution);
        const option = buildChartOption(activeDataset, isDark, skipAnimation);

        // skipAnimation is true exactly when the resolution changed (daily <-> weekly/monthly),
        // where the number of stacked series/points differs from the previous render. If a
        // tooltip is currently showing (user hovering while zooming — the exact gesture that
        // triggers a resolution switch), ECharts can crash inside its internal
        // _showAxisTooltip reading stale series/dataIndex references once the series are
        // replaced via replaceMerge. Hiding the tooltip first clears that internal state safely.
        if (skipAnimation) {
            chartInstance.dispatchAction({type: 'hideTip'});
        }

        // Under `replaceMerge`, ECharts keeps a series whose `id` comes back at the index it
        // had before, so a series that appears in a later render, or a re-ranked one, kept
        // its old place and the stack contradicted the order decided above (verified on
        // ECharts 6 while settling D375). When the order moved, the series are cleared first;
        // the tooltip goes too, for the same reason as above.
        const seriesOrder = ((option.series ?? []) as Array<{id?: string}>).map((entry) => entry.id ?? '').join('\u0000');
        if (lastSeriesOrder !== null && seriesOrder !== lastSeriesOrder) {
            chartInstance.dispatchAction({type: 'hideTip'});
            chartInstance.setOption({series: []}, {replaceMerge: ['series']});
        }
        lastSeriesOrder = seriesOrder;

        suppressDataZoomHandling = true;
        chartInstance.setOption(option, CHART_SERIES_UPDATE_OPTS);
        Promise.resolve().then(() => {
            suppressDataZoomHandling = false;
        });
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }

        attachDataZoomListener();
        lastRenderedResolution = currentResolution;
    }
</script>

<div class="relative" style="height: {height}">
    <div class="absolute top-2 left-2 z-10 pointer-events-none">
        <ResolutionBadge resolution={currentResolution} />
    </div>

    {#if loading}
        <div class="absolute inset-0 z-10 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
    {:else if data.length === 0}
        <div class="absolute inset-0 z-10 flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm">
            {$_('common.noData')}
        </div>
    {/if}

    <div bind:this={chartContainer} style="height: 100%; width: 100%;" class:invisible={loading || data.length === 0} data-testid="allocation-history-chart"></div>
</div>
