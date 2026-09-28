<script lang="ts">
    /**
     * CorrelationHeatmap — the matrix, made readable.
     *
     * The chart this replaces drew a full N×N grid whose loudest diagonal said
     * that each asset correlates with itself, truncated every label twice (once
     * by a fixed 110px grid, once by an `overflow: 'truncate'` at 100px), and
     * opened a tooltip that reported a number without ever naming the two
     * assets it belonged to. The one question a correlation matrix exists to
     * answer — *which of these two things are the same bet?* — was the one it
     * refused to answer.
     *
     * Four changes, in the order they matter:
     *
     * 1. **Names in the tooltip.** Both of them, plus a plain-language reading
     *    of the coefficient. `labels` was already in scope; nobody had written
     *    it in.
     * 2. **Half the matrix.** The diagonal is a tautology and the upper
     *    triangle is a mirror; a 10-asset matrix drops from 100 cells to 45
     *    with no fact lost.
     * 3. **Labels that survive.** Truncated once, deliberately, by
     *    `truncateName`, with the grid margins *computed* from the truncation
     *    rather than fixed and hoped for.
     * 4. **Order by similarity.** Assets that move together become adjacent, so
     *    blocks of redundancy appear as squares instead of scattered dots.
     *
     * 5. **Sized from its content (F-3b, V5-A).** The developer's review found the
     *    names drawn over the cells and the chart running past the card. The only
     *    label placed right was the only one without emoji: the canvas
     *    mis-measures them, so the axis labels are now drawn without (the
     *    tooltip keeps them). Cells keep a minimum size and the card scrolls
     *    sideways instead of squeezing them. The margins come from the measured
     *    labels, and the empty first row and last column of the triangle are
     *    gone, so the full row sits on the column names.
     *
     * The arithmetic lives in `correlationHelpers.ts` and is unit-tested there;
     * this file is the drawing.
     */
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {createResizeWatcher} from '$lib/utils/core/resizeWatcher';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    import {_ as t} from '$lib/i18n';
    import type {RiskCorrelationOutput} from '$lib/risk/riskTypes';
    import {getCountryInfo} from '$lib/stores/reference/countryStore';
    import {getSectorEmoji} from '$lib/stores/reference/sectorStore';
    import {ASSET_TYPE_MENU_ORDER, sectorI18nKey} from '$lib/utils/assetTypes';
    import CorrelationPairsList from './CorrelationPairsList.svelte';
    import {
        buildLookup,
        clusterOrder,
        correlationBand,
        dominantExposure,
        exposureOrder,
        heatmapLayout,
        lowerTrianglePoints,
        nameOrder,
        NEAR_IDENTICAL,
        OTHER_EXPOSURE,
        PAIR_LIST_THRESHOLD,
        pairKey,
        plainName,
        typeOrder,
        type CorrelationPair,
        type ExposureGroup,
        type HeatmapPoint,
    } from './correlationHelpers';

    type Ordering = 'similarity' | 'name' | 'type' | 'sector' | 'region';
    type Distribution = Readonly<Record<string, number>>;

    interface Props {
        output: RiskCorrelationOutput;
        assetLabels?: ReadonlyMap<number, string>;
        /** Asset types by id. When given, a third ordering groups the matrix by type. */
        assetTypes?: ReadonlyMap<number, string | null | undefined>;
        /** Sector and country distributions by id. When given, two more orderings group the matrix by dominant exposure. */
        assetSectors?: ReadonlyMap<number, Distribution | null>;
        assetRegions?: ReadonlyMap<number, Distribution | null>;
        /** `similarity` groups assets that move together; `name` sorts by the label the reader sees. */
        initialOrdering?: 'similarity' | 'name';
    }

    let {output, assetLabels = new Map(), assetTypes = new Map(), assetSectors = new Map(), assetRegions = new Map(), initialOrdering = 'similarity'}: Props = $props();
    /** `null` means "the caller's choice still stands"; any click pins it locally. */
    let orderingOverride = $state<Ordering | null>(null);
    let ordering = $derived<Ordering>(orderingOverride ?? initialOrdering);
    let sectorGroups = $derived(exposureGroups(assetSectors));
    let regionGroups = $derived(exposureGroups(assetRegions));
    let modes = $derived<Ordering[]>([
        'similarity',
        ...(assetTypes.size > 0 ? (['type'] as const) : []),
        ...(hasGroups(sectorGroups) ? (['sector'] as const) : []),
        ...(hasGroups(regionGroups) ? (['region'] as const) : []),
        // Last, by the developer's choice: the one ordering that says nothing about the assets.
        'name',
    ]);
    let container: HTMLDivElement | undefined = $state(undefined);
    /** The scrolling box around the chart: its width, not the chart's, is the room available. */
    let wrapper: HTMLDivElement | undefined = $state(undefined);
    let wrapperWidth = $state(0);
    let dark = $state(false);
    let chart: echarts.ECharts | null = null;
    const resizeWatcher = createResizeWatcher((entry) => {
        wrapperWidth = Math.floor(entry?.contentRect.width ?? wrapper?.clientWidth ?? 0);
    });

    /** ECharts' own axis-label font, set explicitly so that what is measured here is what gets drawn. */
    const AXIS_FONT_SIZE = 12;
    const AXIS_FONT_FAMILY = 'sans-serif';
    const AXIS_LINE_HEIGHT = 14;
    /** Row names wrap onto a second line past this width; rotated column names are cut with an ellipsis past theirs. */
    const Y_LABEL_MAX = 200;
    const X_LABEL_MAX = 150;
    const X_LABEL_ROTATION = 45;
    /** Red for −1, neutral for 0, blue for +1. The neutral follows the card, so a zero reads as "nothing" in both themes. */
    const SCALE_LIGHT = ['#b91c1c', '#f8fafc', '#1d4ed8'];
    const SCALE_DARK = ['#b91c1c', '#334155', '#1d4ed8'];

    let lookup = $derived(buildLookup(output.cells));
    let order = $derived.by(() => {
        if (ordering === 'similarity') return clusterOrder(output.asset_ids, lookup);
        if (ordering === 'type') return typeOrder(output.asset_ids, (assetId) => assetTypes.get(assetId), nameOf, ASSET_TYPE_MENU_ORDER);
        if (ordering === 'sector') return exposureOrder(output.asset_ids, (assetId) => sectorGroups.get(assetId) ?? null, nameOf, sectorName);
        if (ordering === 'region') return exposureOrder(output.asset_ids, (assetId) => regionGroups.get(assetId) ?? null, nameOf, regionName);
        return nameOrder(output.asset_ids, nameOf);
    });
    /**
     * The selection's composition by sector and by area, always shown (the
     * developer: *«li metterei sempre, non solo in base al selettore»*): each group
     * once, with how many assets it holds, in the order the grouped matrix would
     * show it — computed by the same `exposureOrder`, so the two cannot disagree.
     */
    let sectorSummary = $derived(summarise(sectorGroups, 'sector'));
    let regionSummary = $derived(summarise(regionGroups, 'region'));
    let badgeRows = $derived([
        {dimension: 'sector' as const, label: $t('risk.assetSet.exposure.sector'), summary: sectorSummary},
        {dimension: 'region' as const, label: $t('risk.assetSet.exposure.region'), summary: regionSummary},
    ]);
    /** Per dimension: `true` when its row cannot show every name on one line, and folds to icon + count. */
    let compactRows = $state<Record<'sector' | 'region', boolean>>({sector: false, region: false});

    /**
     * The developer: badge rows never wrap — when the names do not fit, they fold
     * and the icon and the count stay. The row carries an invisible copy of itself
     * with every name shown (`w-max`, so its width is its content's); the row
     * folds exactly when that copy is wider than the row.
     */
    function foldWhenNarrow(node: HTMLElement, dimension: 'sector' | 'region') {
        const probe = node.querySelector<HTMLElement>('[data-badge-probe]');
        const measure = () => {
            if (probe) compactRows[dimension] = probe.offsetWidth > node.clientWidth;
        };
        const observer = new ResizeObserver(measure);
        observer.observe(node);
        if (probe) observer.observe(probe);
        measure();
        return {destroy: () => observer.disconnect()};
    }
    /** Strict lower triangle: the first asset has no row and the last has no column, so neither is drawn empty. */
    let rowIds = $derived(order.slice(1));
    let columnIds = $derived(order.slice(0, -1));
    let rowLabels = $derived(rowIds.map((assetId) => fitText(plainName(nameOf(assetId)), Y_LABEL_MAX * 1.75)));
    let columnLabels = $derived(columnIds.map((assetId) => plainName(nameOf(assetId))));
    let layout = $derived(
        heatmapLayout({
            columns: columnIds.length,
            rows: rowIds.length,
            availableWidth: wrapperWidth,
            yLabelWidth: Math.min(Y_LABEL_MAX, widest(rowLabels)),
            xLabelWidth: Math.min(X_LABEL_MAX, widest(columnLabels)),
            labelHeight: AXIS_LINE_HEIGHT,
        }),
    );
    let overflowing = $derived(wrapperWidth > 0 && layout.width > wrapperWidth);
    let scale = $derived(dark ? SCALE_DARK : SCALE_LIGHT);
    /** The legend spans the cells, not the card; it gets a floor so a two-asset matrix still has a readable scale. */
    let legendWidth = $derived(Math.max(280, layout.width - layout.grid.left - layout.grid.right));
    /** `pairKey` of the pair shown in the matrix and in the ranking: one selection for both views. */
    let selectedPairKey = $state<string | null>(null);
    /** The points last drawn, in data-index order: what `dispatchAction` addresses. */
    let drawn: HeatmapPoint[] = [];

    function nameOf(assetId: number): string {
        return assetLabels.get(assetId) ?? `#${assetId}`;
    }

    function exposureGroups(distributions: ReadonlyMap<number, Distribution | null>): Map<number, ExposureGroup | null> {
        return new Map([...distributions].map(([assetId, distribution]) => [assetId, dominantExposure(distribution)]));
    }

    function hasGroups(groups: ReadonlyMap<number, ExposureGroup | null>): boolean {
        return [...groups.values()].some((group) => group !== null);
    }

    function summarise(groups: ReadonlyMap<number, ExposureGroup | null>, dimension: 'sector' | 'region'): (BadgeParts & {count: number})[] {
        if (!hasGroups(groups)) return [];
        const sorted = exposureOrder(output.asset_ids, (assetId) => groups.get(assetId) ?? null, nameOf, dimension === 'sector' ? sectorName : regionName);
        const summary: (BadgeParts & {count: number})[] = [];
        for (const assetId of sorted) {
            const parts = groupParts(groups.get(assetId) ?? null, dimension);
            const last = summary.at(-1);
            if (last && last.icon === parts.icon && last.name === parts.name) last.count += 1;
            else summary.push({...parts, count: 1});
        }
        return summary;
    }

    /** A backend sector key in the reader's language; an unknown key is shown as it is, never as `sectors.…`. */
    function sectorName(key: string): string {
        return $t(`sectors.${sectorI18nKey(key)}`, {default: key});
    }

    function regionName(key: string): string {
        return key === OTHER_EXPOSURE ? $t('common.other') : getCountryInfo(key).name;
    }

    /** A badge's two parts: the icon survives when a badge row is too narrow for the names. */
    interface BadgeParts {
        icon: string;
        name: string;
    }

    /** Emoji for the groups that have no sector or country of their own (the developer's call). */
    const DIVERSIFIED_ICON = '🧩';
    const UNCLASSIFIED_ICON = '❔';
    const OTHER_REGION_ICON = '🌐';

    function entryParts(key: string, dimension: 'sector' | 'region'): BadgeParts {
        if (dimension === 'sector') return {icon: getSectorEmoji(key), name: sectorName(key)};
        if (key === OTHER_EXPOSURE) return {icon: OTHER_REGION_ICON, name: regionName(key)};
        return {icon: getCountryInfo(key).flag_emoji, name: regionName(key)};
    }

    function groupParts(group: ExposureGroup | null, dimension: 'sector' | 'region'): BadgeParts {
        if (group === null) return {icon: UNCLASSIFIED_ICON, name: $t('risk.assetSet.group.unclassified')};
        if (group.key === null) return {icon: DIVERSIFIED_ICON, name: $t('risk.assetSet.group.diversified')};
        return entryParts(group.key, dimension);
    }

    let measureContext: CanvasRenderingContext2D | null | undefined;

    function textWidth(text: string): number {
        if (measureContext === undefined) measureContext = document.createElement('canvas').getContext('2d');
        if (!measureContext) return text.length * 6.6;
        measureContext.font = `${AXIS_FONT_SIZE}px ${AXIS_FONT_FAMILY}`;
        return measureContext.measureText(text).width;
    }

    function widest(labels: readonly string[]): number {
        return labels.reduce((max, label) => Math.max(max, Math.ceil(textWidth(label))), 0);
    }

    /** Cut `text` with an ellipsis so it fits in `maxWidth` pixels, measured, not counted in characters. */
    function fitText(text: string, maxWidth: number): string {
        if (textWidth(text) <= maxWidth) return text;
        let low = 0;
        let high = text.length;
        while (low < high) {
            const middle = Math.ceil((low + high) / 2);
            if (textWidth(`${text.slice(0, middle).trimEnd()}…`) <= maxWidth) low = middle;
            else high = middle - 1;
        }
        return `${text.slice(0, low).trimEnd()}…`;
    }

    /** Dark text on pale cells, white on saturated ones: the value must stay legible across the whole scale. */
    function valueColor(value: number | null): string {
        if (dark) return '#f1f5f9';
        return value !== null && Math.abs(value) >= 0.6 ? '#ffffff' : '#0f172a';
    }

    /**
     * Past this size the matrix stops being the answer and becomes the
     * context: the in-cell numbers are already gone, and hunting for the
     * darkest of four hundred squares is not reading. The list goes first, the
     * picture stays underneath — demoted, not removed.
     */
    let pairsLead = $derived(order.length > PAIR_LIST_THRESHOLD);

    onMount(() => {
        const readTheme = () => {
            dark = document.documentElement.classList.contains('dark');
        };
        readTheme();
        const darkObserver = new MutationObserver(readTheme);
        darkObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            darkObserver.disconnect();
            resizeWatcher.disconnect();
            chart?.dispose();
        };
    });

    $effect(() => {
        if (!wrapper) return;
        resizeWatcher.observe(wrapper);
        wrapperWidth = Math.floor(wrapper.clientWidth);
    });

    $effect(() => {
        void output;
        void assetLabels;
        void ordering;
        void layout;
        void dark;
        if (container) void tick().then(render);
    });

    /** Asset names are user data and the tooltip is raw HTML. */
    function escapeHtml(value: string): string {
        return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }

    /**
     * One asset in the tooltip: its name, then one line for its sectors and one
     * for its countries, whatever the ordering. A full list made the tooltip tall
     * and hard to read (the developer), so each line shows the three largest named
     * entries and folds everything else into one «Altro», always last — even when
     * the data's own "Other" is the largest share.
     */
    function assetBlock(assetId: number): string {
        const lines = [`<div style="font-weight:600">${escapeHtml(nameOf(assetId))}</div>`];
        const sector = assetSectors.get(assetId);
        const region = assetRegions.get(assetId);
        if (sector) lines.push(exposureLine($t('risk.assetSet.exposure.sector'), sector, 'sector'));
        if (region) lines.push(exposureLine($t('risk.assetSet.exposure.region'), region, 'region'));
        return `<div style="margin-top:4px">${lines.join('')}</div>`;
    }

    /** Named entries shown per line; the rest becomes «Altro». */
    const EXPOSURE_TOP = 3;

    /**
     * One line of badges, like the rows above the matrix (the developer wanted the
     * same look here): the three largest named entries, then a single «Altro» with
     * everything else — the data's own "Other" included — always last. The line does
     * not wrap; if it is too long for the tooltip it is cut at its end.
     */
    function exposureLine(label: string, distribution: Distribution, dimension: 'sector' | 'region'): string {
        const entries = Object.entries(distribution).filter(([key, weight]) => key !== '' && Number.isFinite(weight) && weight > 0);
        const named = entries.filter(([key]) => key !== OTHER_EXPOSURE).sort(([leftKey, left], [rightKey, right]) => right - left || leftKey.localeCompare(rightKey));
        const shown = named.slice(0, EXPOSURE_TOP);
        const shownKeys = new Set(shown.map(([key]) => key));
        const rest = Math.round(entries.reduce((sum, [key, weight]) => (shownKeys.has(key) ? sum : sum + weight), 0) * 100);
        const badges = shown.map(([key, weight]) => badgeHtml(entryParts(key, dimension), `${Math.round(weight * 100)}%`));
        if (rest > 0) badges.push(badgeHtml(entryParts(OTHER_EXPOSURE, dimension), `${rest}%`));
        return `<div style="margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"><span style="font-size:11px;font-weight:600;opacity:0.8;margin-right:4px">${escapeHtml(label)}</span>${badges.join('')}</div>`;
    }

    function badgeHtml(parts: BadgeParts, value: string): string {
        return `<span style="display:inline-block;margin-right:4px;padding:0 6px;border-radius:9999px;background:#f1f5f9;color:#334155;font-size:11px;line-height:18px">${escapeHtml(`${parts.icon} ${parts.name}`)} <b>${escapeHtml(value)}</b></span>`;
    }

    /**
     * Beside the cell, never on it: above when the page has room, otherwise
     * below. The cell's box is computed from the layout rather than taken from
     * ECharts, so a tooltip opened from the ranking — no mouse, no hovered
     * element — lands in the same place as one opened by hovering. The tooltip
     * is appended to the body, so it may leave the scrolling box instead of
     * being cut by it or pushed onto the cell.
     */
    function tooltipBesideCell(point: number[], params: unknown, _dom: unknown, _rect: unknown, size: {contentSize: number[]}): number[] {
        const item = (params as {data?: HeatmapPoint} | null)?.data;
        const [width, height] = size.contentSize;
        const gap = 10;
        const cell = item ? {x: layout.grid.left + item.value[0] * layout.cellWidth, y: layout.grid.top + item.value[1] * layout.cellHeight, width: layout.cellWidth, height: layout.cellHeight} : {x: point[0], y: point[1], width: 0, height: 0};
        const box = container?.getBoundingClientRect();
        const pageLeft = box?.left ?? 0;
        const pageTop = box?.top ?? 0;
        const x = Math.min(Math.max(cell.x + cell.width / 2 - width / 2, 8 - pageLeft), window.innerWidth - pageLeft - width - 8);
        let y = cell.y - height - gap;
        if (pageTop + y < 8) y = cell.y + cell.height + gap;
        return [x, y];
    }

    function drawnIndex(key: string): number {
        return drawn.findIndex((point) => pairKey(point.rowAssetId, point.columnAssetId) === key);
    }

    /** A ranking entry was clicked: show its cell, or hide it again on a second click. */
    function selectPair(pair: CorrelationPair): void {
        if (!chart) return;
        const key = pairKey(pair.rowAssetId, pair.columnAssetId);
        chart.dispatchAction({type: 'downplay', seriesIndex: 0});
        if (selectedPairKey === key) {
            selectedPairKey = null;
            chart.dispatchAction({type: 'hideTip'});
            return;
        }
        const dataIndex = drawnIndex(key);
        if (dataIndex < 0) return;
        selectedPairKey = key;
        revealCell(drawn[dataIndex]);
        chart.dispatchAction({type: 'highlight', seriesIndex: 0, dataIndex});
        chart.dispatchAction({type: 'showTip', seriesIndex: 0, dataIndex});
    }

    /** Scroll the cell into view: sideways inside the card, then the chart into the page. */
    function revealCell(point: HeatmapPoint): void {
        if (wrapper) {
            const centre = layout.grid.left + (point.value[0] + 0.5) * layout.cellWidth;
            const {scrollLeft, clientWidth} = wrapper;
            if (centre < scrollLeft + layout.grid.left || centre > scrollLeft + clientWidth - layout.cellWidth) {
                wrapper.scrollTo({left: Math.max(0, centre - clientWidth / 2), behavior: 'smooth'});
            }
        }
        container?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
    }

    function render(): void {
        if (!container) return;
        if (order.length < 2) {
            chart?.clear();
            return;
        }
        if (!chart) {
            chart = echarts.init(container);
            attachChartReady(chart, container, 'correlation-heatmap');
            scheduleFirstRenderStabilityFix(chart, container);
            // The other direction of the link: a cell clicked in the matrix selects its ranking entry, if it has one.
            chart.on('click', (params) => {
                const point = params.data as HeatmapPoint | undefined;
                if (point) selectedPairKey = pairKey(point.rowAssetId, point.columnAssetId);
            });
        } else {
            chart.resize();
        }

        // Row `r` of the drawing is asset `order[r + 1]`: the triangle has no row for the first asset.
        const data = lowerTrianglePoints(order, lookup).map((point) => ({
            ...point,
            value: [point.value[0], point.value[1] - 1, point.value[2]] as HeatmapPoint['value'],
            label: {color: valueColor(point.value[2])},
        }));
        drawn = data;
        const axisColor = dark ? '#cbd5e1' : '#475569';
        const axisLabel = {color: axisColor, fontSize: AXIS_FONT_SIZE, fontFamily: AXIS_FONT_FAMILY, interval: 0};

        chart.setOption(
            {
                ...CHART_ANIMATION_CONFIG,
                // `none`: ECharts 6 would otherwise shrink the plot on its own when a label
                // overflows. The margins below are measured, and they are the only authority.
                grid: {...layout.grid, outerBoundsMode: 'none'},
                xAxis: {
                    type: 'category',
                    data: columnLabels,
                    axisTick: {show: false},
                    axisLine: {show: false},
                    axisLabel: {...axisLabel, rotate: X_LABEL_ROTATION, width: X_LABEL_MAX, overflow: 'truncate', ellipsis: '…'},
                },
                yAxis: {
                    type: 'category',
                    data: rowLabels,
                    // First row at the top: the triangle grows downwards and its full row sits on the column names.
                    inverse: true,
                    axisTick: {show: false},
                    axisLine: {show: false},
                    axisLabel: {...axisLabel, width: Y_LABEL_MAX, overflow: 'break', lineHeight: AXIS_LINE_HEIGHT},
                },
                // Drawn in HTML under the chart, so it stays in view when the card scrolls.
                visualMap: {min: -1, max: 1, show: false, inRange: {color: scale}},
                tooltip: {
                    position: tooltipBesideCell,
                    appendTo: 'body',
                    extraCssText: 'max-width: 440px; white-space: normal;',
                    formatter: (params: {data?: (typeof data)[number]}) => {
                        const item = params.data;
                        if (!item) return '';
                        const value = item.value[2];
                        const band = correlationBand(value);
                        // The reading first: it is what the cell means; the two assets follow, with their exposures.
                        const reading =
                            typeof value === 'number' && band
                                ? `<div style="font-weight:600">ρ = ${value.toFixed(3)} · ${$t(`risk.assetSet.band.${band}`)}${value >= NEAR_IDENTICAL ? ` · ${$t('risk.assetSet.nearIdentical')}` : ''}</div>`
                                : `<div style="font-weight:600">${$t(`risk.valueStatus.${item.status}`)}</div>`;
                        const metadata = `<div style="opacity:0.75;margin-top:2px">${$t('risk.metadata.observations')}: ${item.observations} · ${$t('risk.metadata.coverage')}: ${(item.coverage * 100).toFixed(1)}%</div>`;
                        const assets = `<div style="margin-top:6px;padding-top:4px;border-top:1px solid rgba(148,163,184,0.35)">${assetBlock(item.rowAssetId)}${assetBlock(item.columnAssetId)}</div>`;
                        return `${reading}${metadata}${assets}`;
                    },
                },
                series: [
                    {
                        name: $t('risk.analytics.correlation.name'),
                        type: 'heatmap',
                        data,
                        // A gap the colour of the card between cells: the triangle reads as tiles, not as a smear.
                        itemStyle: {borderColor: dark ? '#1e293b' : '#ffffff', borderWidth: 2, borderRadius: 3},
                        label: {
                            show: true,
                            fontSize: AXIS_FONT_SIZE,
                            formatter: (params: {data?: (typeof data)[number]}) => {
                                const value = params.data?.value?.[2];
                                return typeof value === 'number' ? value.toFixed(2) : '—';
                            },
                        },
                        // Hovered or picked from the ranking, the cell gets a bright border and a halo (the
                        // developer: otherwise the tooltip's cell is hard to find). No hue: every colour tried
                        // collided with the scale — amber vanished on the red cells, green read as blue. A
                        // neutral border, black on the light theme and white on the dark one, with a halo of
                        // the opposite shade, stands out on the pale cells and on the saturated ones alike.
                        // ECharts lifts an emphasised cell above its neighbours (`Z2_EMPHASIS_LIFT`), so the
                        // neighbours' tile gaps cannot cover its border.
                        emphasis: {itemStyle: dark ? {borderColor: '#ffffff', borderWidth: 3, shadowBlur: 10, shadowColor: 'rgba(2, 6, 23, 0.95)'} : {borderColor: '#0f172a', borderWidth: 3, shadowBlur: 10, shadowColor: 'rgba(255, 255, 255, 0.95)'}},
                    },
                ],
            },
            CHART_SET_OPTION_OPTS,
        );

        // A redraw (new ordering, new data) moves every data index: re-point the selection or drop it.
        if (selectedPairKey) {
            const dataIndex = drawnIndex(selectedPairKey);
            if (dataIndex < 0) selectedPairKey = null;
            else chart.dispatchAction({type: 'highlight', seriesIndex: 0, dataIndex});
        }
    }
</script>

<div class="space-y-3">
    <div class="flex items-center justify-end">
        <div class="inline-flex max-w-full overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-600" role="group" aria-label={$t('risk.assetSet.ordering.label')}>
            {#each modes as mode (mode)}
                <button
                    type="button"
                    class="shrink-0 px-2.5 py-1 text-xs font-medium whitespace-nowrap transition-colors {ordering === mode ? 'bg-libre-green text-white' : 'bg-white text-gray-600 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700'}"
                    aria-pressed={ordering === mode}
                    onclick={() => (orderingOverride = mode)}
                    data-testid="risk-correlation-ordering-{mode}"
                >
                    {$t(`risk.assetSet.ordering.${mode}`)}
                </button>
            {/each}
        </div>
    </div>

    {#if sectorSummary.length > 0 || regionSummary.length > 0}
        <!-- The selection's composition, whatever the ordering: one row per dimension, each
             group once with its size. The label of the dimension the matrix is grouped by
             is underlined, so the two readings line up. -->
        <div class="space-y-1 text-[11px]" data-testid="risk-correlation-groups">
            {#each badgeRows as row (row.dimension)}
                {#if row.summary.length > 0}
                    <div class="relative flex min-w-0 flex-nowrap items-center gap-1.5 overflow-hidden" data-testid="risk-correlation-groups-{row.dimension}" data-compact={compactRows[row.dimension]} use:foldWhenNarrow={row.dimension}>
                        <div data-badge-probe aria-hidden="true" class="pointer-events-none invisible absolute top-0 left-0 flex w-max items-center gap-1.5 whitespace-nowrap">
                            <span class="font-semibold">{row.label}</span>
                            {#each row.summary as group, index (index)}
                                <span class="rounded-full px-2 py-0.5">{group.icon} {group.name} <span class="font-semibold">· {group.count}</span></span>
                            {/each}
                        </div>
                        <span class="shrink-0 font-semibold text-slate-600 dark:text-slate-300 {ordering === row.dimension ? 'underline decoration-libre-green decoration-2 underline-offset-2' : ''}">{row.label}</span>
                        {#each row.summary as group, index (index)}
                            {#if compactRows[row.dimension]}
                                <Tooltip text={group.name} position="top">
                                    <span class="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 whitespace-nowrap text-slate-600 dark:bg-slate-700 dark:text-slate-300">{group.icon} <span class="font-semibold tabular-nums">{group.count}</span></span>
                                </Tooltip>
                            {:else}
                                <span class="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 whitespace-nowrap text-slate-600 dark:bg-slate-700 dark:text-slate-300">{group.icon} {group.name} <span class="font-semibold tabular-nums">· {group.count}</span></span>
                            {/if}
                        {/each}
                    </div>
                {/if}
            {/each}
        </div>
    {/if}

    <!-- `grid-cols-1` is `minmax(0, 1fr)`: without it the single column below `lg` is `auto`
         and may grow to the chart's width, pushing the matrix out of the card. -->
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]" data-testid="risk-correlation-layout" data-pairs-lead={pairsLead}>
        <div class="min-w-0 {pairsLead ? 'lg:order-2' : ''}">
            <!-- `data-asset-order` publishes the very array the chart is built from, so a
                 test can assert the reordering itself instead of the button's pressed state.
                 Without it the only observable effect of the toggle is inside a canvas. -->
            <div class="relative">
                <div bind:this={wrapper} class="overflow-x-auto" data-testid="risk-correlation-heatmap" data-asset-order={order.join(',')} data-overflowing={overflowing}>
                    <div bind:this={container} style:width="{layout.width}px" style:height="{layout.height}px"></div>
                    <!-- Inside the scrolling box and under the cells, not under the card: it starts
                         where the first column starts and moves with the matrix when the card scrolls. -->
                    <div class="pb-2 text-[11px] leading-tight text-slate-500 dark:text-slate-400" style:margin-left="{layout.grid.left}px" style:width="{legendWidth}px" data-testid="risk-correlation-legend">
                        <div class="h-2 rounded-full border border-slate-200 dark:border-slate-600" style:background="linear-gradient(to right, {scale[0]}, {scale[1]}, {scale[2]})"></div>
                        <div class="mt-1 grid grid-cols-3 gap-2">
                            <div>
                                <div class="font-semibold text-slate-700 dark:text-slate-200">−1 · {$t('risk.assetSet.legend.negative')}</div>
                                <div>{$t('risk.assetSet.band.inverse')}</div>
                            </div>
                            <div class="text-center">
                                <div class="font-semibold text-slate-700 dark:text-slate-200">0 · {$t('risk.assetSet.legend.none')}</div>
                                <div>{$t('risk.assetSet.band.low')}</div>
                            </div>
                            <div class="text-right">
                                <div class="font-semibold text-slate-700 dark:text-slate-200">+1 · {$t('risk.assetSet.legend.positive')}</div>
                                <div>{$t('risk.assetSet.band.high')}</div>
                            </div>
                        </div>
                    </div>
                </div>
                {#if overflowing}
                    <!-- A fade on the right edge: the matrix goes on, and it scrolls. -->
                    <div class="pointer-events-none absolute inset-y-0 right-0 w-8 bg-linear-to-l from-white dark:from-slate-800"></div>
                {/if}
            </div>
        </div>
        <div class={pairsLead ? 'lg:order-1' : ''}>
            <CorrelationPairsList {output} {assetLabels} limit={pairsLead ? 8 : 5} selectedKey={selectedPairKey} onselect={selectPair} />
        </div>
    </div>
</div>
