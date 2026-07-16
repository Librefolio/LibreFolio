<script lang="ts">
    import {tick} from 'svelte';
    import * as echarts from 'echarts';
    import {z} from 'zod';
    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {CHART_ANIMATION_CONFIG, CHART_SET_OPTION_OPTS} from '$lib/components/charts/echartsAnimationConfig';
    import {buildDataZoom} from '$lib/components/charts/chartCoreHelpers';
    import {attachDataZoomSync, type DataZoomSyncHandle} from '$lib/components/charts/echartsDataZoomSync';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from '$lib/components/charts/echartsDataZoomTouchPan';
    import {buildGridColors, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, setupTooltipAutoHide, tooltipPositionSide} from '$lib/components/charts/echartsTooltipHelpers';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type GanttSegmentSchema = z.infer<typeof schemas.GanttSegmentSchema>;
    type FilterMode = 'open' | 'all';

    interface Props {
        lots: ReadonlyArray<LotSummarySchema>;
        segments: ReadonlyArray<GanttSegmentSchema>;
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        selectedLotIds?: number[];
        onSelectionChange?: (lotIds: number[]) => void;
        xAxisRange?: {min: string; max: string} | null;
        onZoomChange?: (start: number, end: number) => void;
        externalZoomStart?: number | null;
        externalZoomEnd?: number | null;
        onRowDoubleClick?: (lotId: number) => void;
        /** Shared Aperti/Tutti filter (lifted to the orchestrator so UnifiedLotsTable shows the
         * same lot set — see LotsAnalysisPanel.svelte). The toggle control still renders here. */
        filterMode?: FilterMode;
        onFilterModeChange?: (mode: FilterMode) => void;
    }

    interface LotModel {
        lotId: number;
        assetId: number;
        direction: 'LONG' | 'SHORT';
        openingBrokerId: number;
        openingDate: string;
        openingMs: number;
        originalQuantity: number;
        openQuantity: number;
        states: string[];
        lot: LotSummarySchema;
    }

    interface SegmentModel {
        key: string;
        lotId: number;
        fragmentId: string;
        direction: 'LONG' | 'SHORT';
        custodyType: 'BROKER' | 'IN_TRANSIT';
        brokerId: number | null;
        sourceBrokerId: number | null;
        destinationBrokerId: number | null;
        quantity: number;
        unitPrice: number;
        startDate: string;
        endDate: string | null;
        startMs: number;
        endMs: number;
        sortEndMs: number;
        segment: GanttSegmentSchema;
    }

    interface RenderedSegment extends SegmentModel {
        laneIndex: number;
        thickness: number;
        isOpen: boolean;
        isFirstInLane: boolean;
    }

    interface RenderedLane {
        laneIndex: number;
        lotId: number;
        lot: LotModel;
        segments: RenderedSegment[];
        isOpen: boolean;
    }

    interface SegmentDatum {
        name: string;
        value: [number, number, number, number];
        meta: RenderedSegment;
    }

    interface LaneHighlightDatum {
        name: string;
        value: [number];
        meta: {laneIndex: number; lotId: number; pulse: boolean; selected: boolean};
    }

    /** Invisible, focusable per-segment hit target absolutely positioned over the ECharts custom
     * series (recomputed on every 'rendered' event, so it stays in sync with pan/zoom/resize).
     * Gives keyboard/assistive-tech users and Playwright a real DOM element to interact with,
     * since canvas-rendered custom series have no native accessibility hooks. Sized per rendered
     * SEGMENT (not per lane) so hover can drive the native ECharts tooltip via dispatchAction
     * with a precise dataIndex — see showSegmentTooltip/hideSegmentTooltip. */
    interface OverlayRect {
        lotId: number;
        dataIndex: number;
        left: number;
        top: number;
        width: number;
        height: number;
    }

    const DAY_MS = 24 * 60 * 60 * 1000;
    const LANE_ROW_HEIGHT = 72;
    const ZOOM_AREA_HEIGHT = 64;
    const CHART_MIN_WIDTH = 720;
    const PULSE_DURATION_MS = 1800;
    const TOGGLE_DEBOUNCE_MS = 260;
    const THICKNESS_MIN = 12;
    const THICKNESS_MAX = 28;
    const GRID_LEFT_PX = 56;
    const GRID_RIGHT_PX = 18;

    let {lots = [], segments = [], brokers = [], currency, selectedLotIds = [], onSelectionChange, xAxisRange = null, onZoomChange, externalZoomStart = null, externalZoomEnd = null, onRowDoubleClick, filterMode = 'open', onFilterModeChange}: Props = $props();

    let wrapperEl: HTMLDivElement | undefined = $state(undefined);
    let lanesScrollEl: HTMLDivElement | undefined = $state(undefined);
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let dataZoomSyncHandle: DataZoomSyncHandle | null = null;
    let isDark = $state(false);
    let overlayRects = $state<OverlayRect[]>([]);
    let pulseState = $state<{lotId: number; nonce: number} | null>(null);
    let pulseTimeoutId: ReturnType<typeof setTimeout> | null = null;
    let pulseNonce = 0;
    let lastSelectionToggleAt = 0;
    let lastSelectionToggleLotId: number | null = null;

    function syncTheme() {
        if (typeof document === 'undefined') return;
        isDark = document.documentElement.classList.contains('dark');
    }

    function safeScalar<T>(value: T | Array<T | null> | null | undefined): T | null {
        if (Array.isArray(value)) return value[0] ?? null;
        return value ?? null;
    }

    function safeString(value: string | Array<string | null> | null | undefined): string | null {
        return safeScalar(value);
    }

    function safeInt(value: number | Array<number | null> | null | undefined): number | null {
        return safeScalar(value);
    }

    function parseNumber(value: string | Array<string | null> | null | undefined): number {
        const raw = safeString(value);
        if (raw == null) return 0;
        const parsed = Number.parseFloat(raw);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function parseDateToUtcMs(value: string): number | null {
        const dateOnlyMatch = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (dateOnlyMatch) {
            const [, year, month, day] = dateOnlyMatch;
            return Date.UTC(Number(year), Number(month) - 1, Number(day));
        }

        const parsed = Date.parse(value);
        if (!Number.isFinite(parsed)) return null;
        const date = new Date(parsed);
        return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
    }

    function formatDate(value: string, opts: Intl.DateTimeFormatOptions): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString($currentLanguage || undefined, opts);
    }

    function formatDateShort(value: string): string {
        return formatDate(value, {day: '2-digit', month: '2-digit'});
    }

    function formatDateLong(value: string): string {
        return formatDate(value, {year: 'numeric', month: 'short', day: 'numeric'});
    }

    function formatAxisDate(value: number): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleDateString($currentLanguage || undefined, {month: 'short', day: 'numeric'});
    }

    function formatQuantity(value: number): string {
        return value.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 6});
    }

    function clamp(value: number, min: number, max: number): number {
        return Math.min(max, Math.max(min, value));
    }

    function escapeHtml(value: string): string {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function withAlpha(color: string, alpha: number): string {
        const hslMatch = color.match(/^hsl\((.+)\)$/i);
        if (hslMatch) return `hsla(${hslMatch[1]}, ${alpha})`;
        const hexMatch = color.match(/^#([0-9a-f]{6})$/i);
        if (hexMatch)
            return `${color}${Math.round(clamp(alpha, 0, 1) * 255)
                .toString(16)
                .padStart(2, '0')}`;
        return color;
    }

    function lotLabel(openingDate: string): string {
        const translated = $t('brokers.lots.lotLabel', {values: {date: formatDateShort(openingDate)}});
        return !translated || translated === 'brokers.lots.lotLabel' ? `Lot ${formatDateShort(openingDate)}` : translated;
    }

    function brokerName(brokerId: number | null): string {
        if (brokerId == null) return '—';
        return brokers.find((broker) => broker.id === brokerId)?.name ?? `#${brokerId}`;
    }

    function brokerLike(brokerId: number | null): BrokerLike | null {
        if (brokerId == null) return null;
        return brokers.find((broker) => broker.id === brokerId) ?? {id: brokerId, name: brokerName(brokerId)};
    }

    function segmentBaseColor(segment: SegmentModel, themeDark: boolean): string {
        if (segment.custodyType === 'IN_TRANSIT') return themeDark ? '#c084fc' : '#7c3aed';
        if (segment.brokerId == null) return themeDark ? '#60a5fa' : '#2563eb';
        const brokerColor = getBrokerColor(segment.brokerId, brokers);
        return themeDark ? brokerColor.vivid : brokerColor.vividLight;
    }

    function segmentOpacity(segment: SegmentModel): number {
        if (segment.custodyType === 'IN_TRANSIT') return 0.65;
        return segment.endDate == null ? 0.9 : 0.45;
    }

    function thicknessForQuantity(quantity: number, qMax: number): number {
        if (qMax <= 0) return THICKNESS_MIN;
        return THICKNESS_MIN + (clamp(quantity, 0, qMax) / qMax) * (THICKNESS_MAX - THICKNESS_MIN);
    }

    function segmentIntersectsRange(segment: SegmentModel, minMs: number | null, maxMs: number | null): boolean {
        if (minMs == null || maxMs == null) return true;
        return segment.endMs > minMs && segment.startMs < maxMs;
    }

    function buildTransitLabel(segment: SegmentModel): string {
        const translated = $t('brokers.lots.inTransit');
        const from = brokerName(segment.sourceBrokerId);
        const to = brokerName(segment.destinationBrokerId);
        const prefix = !translated || translated === 'brokers.lots.inTransit' ? 'In transit' : translated;
        return `${prefix} · ${from} → ${to}`;
    }

    function lotWordText(): string {
        const translated = $t('brokers.lots.lotWord');
        return !translated || translated === 'brokers.lots.lotWord' ? 'Lot' : translated;
    }

    /** Rough Latin-glyph width estimate (no canvas measureText available inside renderItem) —
     * good enough to pick which label variant fits before ECharts' own char-level `overflow:
     * 'truncate'` kicks in as a final safety net. */
    function estimateTextWidthPx(text: string, fontSize = 11): number {
        return text.length * fontSize * 0.58;
    }

    /** Segment label with graceful degradation. Priority (kept longest first, per plan §3.4):
     * 1) date, 2) broker, 3) quantity, 4) the word "Lot" — so variants are built by dropping
     * from the END of that list first. */
    function buildSegmentLabel(meta: RenderedSegment, availableWidthPx: number): string {
        const dateText = formatDateLong(meta.startDate);

        if (meta.custodyType === 'IN_TRANSIT') {
            const transit = buildTransitLabel(meta);
            const withDate = `${dateText} · ${transit}`;
            if (estimateTextWidthPx(withDate) <= availableWidthPx) return withDate;
            if (estimateTextWidthPx(transit) <= availableWidthPx) return transit;
            return dateText;
        }

        const brokerText = brokerName(meta.brokerId);
        const qtyText = formatQuantity(meta.quantity);
        const variants = [`${lotWordText()} ${dateText} · ${brokerText} · ${qtyText}`, `${dateText} · ${brokerText} · ${qtyText}`, `${dateText} · ${brokerText}`, dateText];
        for (const variant of variants) {
            if (estimateTextWidthPx(variant) <= availableWidthPx) return variant;
        }
        return variants.at(-1) ?? dateText;
    }

    function triggerPulse(lotId: number) {
        pulseNonce += 1;
        const nonce = pulseNonce;
        pulseState = {lotId, nonce};
        if (pulseTimeoutId != null) clearTimeout(pulseTimeoutId);
        pulseTimeoutId = setTimeout(() => {
            if (pulseState?.nonce === nonce) pulseState = null;
            pulseTimeoutId = null;
        }, PULSE_DURATION_MS);
    }

    function scrollLaneIntoView(lotId: number) {
        const lane = renderedLanes.find((entry) => entry.lotId === lotId);
        if (!lane) return;
        lanesScrollEl?.scrollTo({
            top: Math.max(0, lane.laneIndex * LANE_ROW_HEIGHT - LANE_ROW_HEIGHT),
            behavior: 'smooth',
        });
    }

    function shouldSkipToggle(lotId: number): boolean {
        const now = Date.now();
        if (lastSelectionToggleLotId === lotId && now - lastSelectionToggleAt < TOGGLE_DEBOUNCE_MS) return true;
        lastSelectionToggleLotId = lotId;
        lastSelectionToggleAt = now;
        return false;
    }

    function toggleLotSelection(lotId: number) {
        if (shouldSkipToggle(lotId)) return;
        const next = new Set(selectedLotIds);
        if (next.has(lotId)) next.delete(lotId);
        else next.add(lotId);
        onSelectionChange?.([...next]);
    }

    function handleLaneDoubleClick(lotId: number) {
        triggerPulse(lotId);
        onRowDoubleClick?.(lotId);
    }

    export function pulseLot(lotId: number): void {
        if (filterMode === 'open' && !openLotIdSet.has(lotId)) onFilterModeChange?.('all');
        wrapperEl?.scrollIntoView({behavior: 'smooth', block: 'center'});
        triggerPulse(lotId);
    }

    const selectedLotIdSet = $derived.by(() => new Set(selectedLotIds));

    const lotModels = $derived.by((): LotModel[] =>
        lots
            .map((lot) => {
                const openingDate = safeString(lot.opening_date) ?? '';
                return {
                    lotId: lot.lot_id,
                    assetId: lot.asset_id,
                    direction: lot.direction,
                    openingBrokerId: lot.opening_broker_id,
                    openingDate,
                    openingMs: parseDateToUtcMs(openingDate) ?? 0,
                    originalQuantity: Math.max(0, parseNumber(lot.original_quantity)),
                    openQuantity: Math.max(0, parseNumber(lot.open_quantity)),
                    states: lot.states ?? [],
                    lot,
                };
            })
            .sort((a, b) => a.openingMs - b.openingMs || a.lotId - b.lotId),
    );

    const openLotIdSet = $derived.by(() => new Set(lotModels.filter((lot) => lot.openQuantity > 0 || lot.states.includes('OPEN')).map((lot) => lot.lotId)));

    const segmentModelsByLot = $derived.by(() => {
        const todayMs = Date.now();
        const grouped = new Map<number, SegmentModel[]>();

        for (const segment of segments) {
            const startDate = safeString(segment.start_date) ?? '';
            const endDate = safeString(segment.end_date);
            const startMs = parseDateToUtcMs(startDate);
            const endMs = endDate != null ? parseDateToUtcMs(endDate) : todayMs;
            if (startMs == null || endMs == null) continue;

            const lotSegments = grouped.get(segment.lot_id) ?? [];
            lotSegments.push({
                key: `${segment.fragment_id}:${startDate}:${endDate ?? 'open'}`,
                lotId: segment.lot_id,
                fragmentId: segment.fragment_id,
                direction: segment.direction,
                custodyType: segment.custody_type,
                brokerId: safeInt(segment.broker_id),
                sourceBrokerId: safeInt(segment.source_broker_id),
                destinationBrokerId: safeInt(segment.destination_broker_id),
                quantity: Math.max(0, parseNumber(segment.quantity)),
                unitPrice: parseNumber(segment.unit_price),
                startDate,
                endDate,
                startMs,
                endMs,
                sortEndMs: endDate != null ? endMs : Number.MAX_SAFE_INTEGER,
                segment,
            });
            grouped.set(segment.lot_id, lotSegments);
        }

        for (const lotSegments of grouped.values()) {
            lotSegments.sort((a, b) => a.startMs - b.startMs || a.sortEndMs - b.sortEndMs || a.fragmentId.localeCompare(b.fragmentId));
        }

        return grouped;
    });

    const axisRangeMs = $derived.by(() => {
        const fallbackMin =
            segmentModelsByLot.size > 0
                ? Math.min(
                      ...Array.from(segmentModelsByLot.values())
                          .flat()
                          .map((segment) => segment.startMs),
                  )
                : null;
        const fallbackMax =
            segmentModelsByLot.size > 0
                ? Math.max(
                      ...Array.from(segmentModelsByLot.values())
                          .flat()
                          .map((segment) => segment.endMs),
                  )
                : null;
        const minMs = xAxisRange?.min ? parseDateToUtcMs(xAxisRange.min) : fallbackMin;
        const maxMs = xAxisRange?.max ? parseDateToUtcMs(xAxisRange.max) : fallbackMax;

        if (minMs == null || maxMs == null) return null;
        if (maxMs > minMs) return {minMs, maxMs};
        return {minMs, maxMs: minMs + DAY_MS};
    });

    const renderedLanes = $derived.by((): RenderedLane[] => {
        const sourceLots = filterMode === 'open' ? lotModels.filter((lot) => openLotIdSet.has(lot.lotId)) : lotModels;
        const minMs = axisRangeMs?.minMs ?? null;
        const maxMs = axisRangeMs?.maxMs ?? null;
        const candidateLots = sourceLots.filter((lot) => (segmentModelsByLot.get(lot.lotId) ?? []).some((segment) => segmentIntersectsRange(segment, minMs, maxMs)));
        const qMax = Math.max(1, ...candidateLots.map((lot) => lot.originalQuantity));

        return candidateLots.map((lot, laneIndex) => {
            const lotSegments = (segmentModelsByLot.get(lot.lotId) ?? []).filter((segment) => segmentIntersectsRange(segment, minMs, maxMs));
            return {
                laneIndex,
                lotId: lot.lotId,
                lot,
                isOpen: openLotIdSet.has(lot.lotId),
                segments: lotSegments.map((segment, segmentIndex) => ({
                    ...segment,
                    laneIndex,
                    thickness: thicknessForQuantity(segment.quantity, qMax),
                    isOpen: segment.endDate == null,
                    isFirstInLane: segmentIndex === 0,
                })),
            };
        });
    });

    const chartHasData = $derived(renderedLanes.length > 0);
    const chartHeightPx = $derived(Math.max(220, renderedLanes.length * LANE_ROW_HEIGHT + ZOOM_AREA_HEIGHT));

    const visibleBrokers = $derived.by(() => {
        const ids = new Set<number>();
        for (const lane of renderedLanes) {
            ids.add(lane.lot.openingBrokerId);
            for (const segment of lane.segments) {
                if (segment.brokerId != null) ids.add(segment.brokerId);
                if (segment.sourceBrokerId != null) ids.add(segment.sourceBrokerId);
                if (segment.destinationBrokerId != null) ids.add(segment.destinationBrokerId);
            }
        }
        return [...ids]
            .sort((a, b) => a - b)
            .map((id) => brokerLike(id))
            .filter((broker): broker is BrokerLike => broker != null);
    });

    const segmentSeriesData = $derived.by((): SegmentDatum[] =>
        renderedLanes.flatMap((lane) =>
            lane.segments.map((segment) => ({
                name: segment.key,
                value: [segment.startMs, segment.laneIndex, segment.endMs, segment.thickness],
                meta: segment,
            })),
        ),
    );

    const laneHighlightData = $derived.by((): LaneHighlightDatum[] =>
        renderedLanes
            .filter((lane) => selectedLotIdSet.has(lane.lotId) || pulseState?.lotId === lane.lotId)
            .map((lane) => ({
                name: `highlight-${lane.lotId}`,
                value: [lane.laneIndex],
                meta: {
                    laneIndex: lane.laneIndex,
                    lotId: lane.lotId,
                    pulse: pulseState?.lotId === lane.lotId,
                    selected: selectedLotIdSet.has(lane.lotId),
                },
            })),
    );

    function buildTooltip(meta: RenderedSegment, themeDark: boolean): string {
        const theme = buildTooltipTheme(themeDark);
        const lot = renderedLanes.find((lane) => lane.lotId === meta.lotId)?.lot;
        const statusLabel = meta.custodyType === 'IN_TRANSIT' ? $t('brokers.lots.inTransit') || 'In transit' : meta.isOpen ? $t('dashboard.openPositions') || 'Open' : $t('dashboard.closedPositions') || 'Closed';
        let html = buildTooltipHeader(escapeHtml(lotLabel(lot?.openingDate ?? meta.startDate)), theme.textColor);
        html += buildTooltipRow(escapeHtml($t('brokers.lots.buyDate') || 'Opening date'), escapeHtml(formatDateLong(lot?.openingDate ?? meta.startDate)));
        html += buildTooltipRow(escapeHtml($t('brokers.lots.direction') || 'Direction'), escapeHtml(meta.direction));
        html += buildTooltipRow(escapeHtml($t('common.status') || 'Status'), escapeHtml(statusLabel));
        html += buildTooltipRow(escapeHtml($t('dashboard.quantity') || 'Qty'), escapeHtml(formatQuantity(meta.quantity)));
        html += buildTooltipRow(escapeHtml($t('dashboard.price') || 'Price'), escapeHtml(formatCurrencyAmountPlain(meta.unitPrice, currency)));
        html += buildTooltipRow(escapeHtml($t('brokers.lots.dateRange') || 'Range'), escapeHtml(`${formatDateLong(meta.startDate)} → ${meta.endDate ? formatDateLong(meta.endDate) : '…'}`));

        if (meta.custodyType === 'IN_TRANSIT') {
            html += buildTooltipRow(escapeHtml($t('brokers.lots.inTransit') || 'In transit'), escapeHtml(`${brokerName(meta.sourceBrokerId)} → ${brokerName(meta.destinationBrokerId)}`));
        } else {
            html += buildTooltipRow(escapeHtml($t('common.broker') || 'Broker'), escapeHtml(brokerName(meta.brokerId)));
        }

        return `<div style="font-size:11px;color:${theme.textColor}">${html}</div>`;
    }

    function buildOption(themeDark: boolean): echarts.EChartsOption {
        const theme = buildTooltipTheme(themeDark);
        const gridColors = buildGridColors(themeDark);
        const laneCount = Math.max(renderedLanes.length, 1);
        const minMs = axisRangeMs?.minMs ?? Date.now() - DAY_MS;
        const maxMs = axisRangeMs?.maxMs ?? Date.now();

        const laneHighlightSeries: any = {
            name: '__lane-highlight',
            type: 'custom',
            silent: true,
            clip: false,
            tooltip: {show: false},
            z: 1,
            data: laneHighlightData,
            encode: {y: 0},
            renderItem: (params: any, api: any) => {
                const meta = laneHighlightData[params.dataIndex]?.meta as LaneHighlightDatum['meta'] | undefined;
                if (!meta) return null;
                const [, centerY] = api.coord([minMs, meta.laneIndex]);
                const bandSize = (api.size?.([0, 1]) as number[] | undefined)?.[1] ?? LANE_ROW_HEIGHT;
                const coordSys = params.coordSys as {x: number; width: number};
                return {
                    type: 'rect',
                    silent: true,
                    shape: {
                        x: coordSys.x,
                        y: centerY - bandSize * 0.42,
                        width: coordSys.width,
                        height: bandSize * 0.84,
                        r: 10,
                    },
                    style: {
                        fill: meta.pulse ? (themeDark ? 'rgba(168, 85, 247, 0.16)' : 'rgba(147, 51, 234, 0.12)') : themeDark ? 'rgba(96, 165, 250, 0.10)' : 'rgba(59, 130, 246, 0.08)',
                        stroke: meta.pulse ? (themeDark ? '#c084fc' : '#7c3aed') : themeDark ? '#60a5fa' : '#2563eb',
                        lineWidth: meta.pulse ? 2 : 1,
                        shadowBlur: meta.pulse ? 18 : 0,
                        shadowColor: meta.pulse ? 'rgba(168, 85, 247, 0.35)' : 'transparent',
                    },
                };
            },
        };

        const segmentSeries: any = {
            name: '__segments',
            type: 'custom',
            clip: false,
            z: 3,
            data: segmentSeriesData,
            renderItem: (params: any, api: any) => {
                const meta = segmentSeriesData[params.dataIndex]?.meta as RenderedSegment | undefined;
                if (!meta) return null;

                const startCoord = api.coord([meta.startMs, meta.laneIndex]);
                const endCoord = api.coord([meta.endMs, meta.laneIndex]);
                const coordSys = params.coordSys as {x: number; y: number; width: number; height: number};
                const laneBand = (api.size?.([0, 1]) as number[] | undefined)?.[1] ?? LANE_ROW_HEIGHT;
                const barHeight = Math.min(meta.thickness, laneBand - 12);
                const rawX = Math.min(startCoord[0], endCoord[0]);
                const rawWidth = Math.max(3, Math.abs(endCoord[0] - startCoord[0]));

                // Keep partially out-of-range lots visible: ECharts still computes off-screen
                // coords (startCoord/endCoord are never clamped), then this clip trims the bar
                // to the plot rect instead of dropping it. Comparing the *unclamped* coords
                // against coordSys below is what lets us tell a truly clipped edge apart from
                // one that merely coincides with the plot boundary.
                const rectShape = echarts.graphic.clipRectByRect(
                    {
                        x: rawX,
                        y: startCoord[1] - barHeight / 2,
                        width: rawWidth,
                        height: barHeight,
                    },
                    {
                        x: coordSys.x,
                        y: coordSys.y,
                        width: coordSys.width,
                        height: coordSys.height,
                    },
                );
                if (!rectShape) return null;

                const isClippedLeft = rawX < coordSys.x - 0.5;
                const isClippedRight = rawX + rawWidth > coordSys.x + coordSys.width + 0.5;

                const baseColor = segmentBaseColor(meta, themeDark);
                const selected = selectedLotIdSet.has(meta.lotId);
                const pulsing = pulseState?.lotId === meta.lotId;
                const borderColor = pulsing ? (themeDark ? '#c084fc' : '#7c3aed') : selected ? (themeDark ? '#e0f2fe' : '#0f172a') : withAlpha(baseColor, themeDark ? 0.92 : 0.85);
                const label = buildSegmentLabel(meta, Math.max(0, rectShape.width - 24));
                const labelFits = rectShape.width >= 28;
                const edgeMarkerX = Math.max(coordSys.x + 4, Math.min(rectShape.x + 8, coordSys.x + coordSys.width - 6));
                const children: any[] = [
                    {
                        type: 'rect',
                        shape: rectShape,
                        silent: false,
                        // ECharts custom-series limitation (confirmed against echarts 6 source,
                        // node_modules/echarts/lib/chart/custom/CustomSeries.js
                        // CustomSeriesModel.prototype.getDataParams): a renderItem group's CHILD
                        // shapes don't reliably resolve `params.dataIndex` for chart.on('click'),
                        // but ECharts explicitly reads `info` off the exact clicked element via
                        // customInnerStore(el).info and exposes it as `params.info` — this is the
                        // documented mechanism for per-child event metadata.
                        info: {lotId: meta.lotId},
                        cursor: 'pointer',
                        style: {
                            fill: meta.custodyType === 'IN_TRANSIT' ? withAlpha(baseColor, 0.35) : withAlpha(baseColor, segmentOpacity(meta)),
                            stroke: borderColor,
                            lineWidth: pulsing ? 3 : selected ? 2 : 1,
                            lineDash: meta.custodyType === 'IN_TRANSIT' ? [7, 4] : undefined,
                            shadowBlur: pulsing ? 22 : selected ? 10 : 0,
                            shadowColor: pulsing ? withAlpha(borderColor, 0.45) : withAlpha(baseColor, 0.18),
                        },
                    },
                ];

                if (isClippedLeft) {
                    // Segment starts before the visible range — a left-pointing chevron replaces
                    // the usual opening dot to signal "this lot's story continues off-screen".
                    children.push({
                        type: 'polygon',
                        silent: true,
                        shape: {
                            points: [
                                [edgeMarkerX + 6, startCoord[1] - Math.min(7, barHeight / 2)],
                                [edgeMarkerX - 4, startCoord[1]],
                                [edgeMarkerX + 6, startCoord[1] + Math.min(7, barHeight / 2)],
                            ],
                        },
                        style: {fill: borderColor, opacity: 0.9},
                    });
                } else if (meta.isFirstInLane) {
                    children.push({
                        type: 'circle',
                        silent: true,
                        shape: {cx: edgeMarkerX, cy: startCoord[1], r: Math.min(6, barHeight / 2)},
                        style: {
                            fill: pulsing ? (themeDark ? '#c084fc' : '#7c3aed') : themeDark ? '#f8fafc' : '#0f172a',
                            stroke: borderColor,
                            lineWidth: pulsing ? 2 : 1,
                        },
                    });
                }

                if ((meta.isOpen || isClippedRight) && rectShape.width >= 24) {
                    children.push({
                        type: 'polygon',
                        silent: true,
                        shape: {
                            points: [
                                [rectShape.x + rectShape.width - 10, startCoord[1] - Math.min(7, barHeight / 2)],
                                [rectShape.x + rectShape.width, startCoord[1]],
                                [rectShape.x + rectShape.width - 10, startCoord[1] + Math.min(7, barHeight / 2)],
                            ],
                        },
                        style: {fill: borderColor, opacity: 0.9},
                    });
                }

                if (labelFits) {
                    children.push({
                        type: 'text',
                        silent: true,
                        x: rectShape.x + 14,
                        y: startCoord[1],
                        style: {
                            text: label,
                            fill: themeDark ? '#f8fafc' : '#0f172a',
                            fontSize: 11,
                            fontWeight: pulsing ? 700 : 600,
                            textAlign: 'left',
                            textVerticalAlign: 'middle',
                            overflow: 'truncate',
                            width: Math.max(0, rectShape.width - 24),
                        },
                    });
                }

                return {type: 'group', children};
            },
        };

        return {
            ...CHART_ANIMATION_CONFIG,
            animationDurationUpdate: 450,
            grid: {
                top: 8,
                right: GRID_RIGHT_PX,
                bottom: 54,
                left: GRID_LEFT_PX,
                containLabel: false,
            },
            tooltip: {
                trigger: 'item',
                position: tooltipPositionSide,
                backgroundColor: theme.bg,
                borderColor: theme.border,
                textStyle: {color: theme.textColor},
                formatter: (params: any) => {
                    const meta = segmentSeriesData[params.dataIndex]?.meta as RenderedSegment | undefined;
                    return meta ? buildTooltip(meta, themeDark) : '';
                },
            },
            xAxis: {
                type: 'time',
                min: xAxisRange?.min ?? minMs,
                max: xAxisRange?.max ?? maxMs,
                axisLine: {
                    lineStyle: {color: gridColors.gridColor},
                },
                axisTick: {show: false},
                splitLine: {
                    lineStyle: {
                        color: gridColors.gridColor,
                    },
                },
                axisLabel: {
                    color: gridColors.textColor,
                    hideOverlap: true,
                    formatter: (value: number) => formatAxisDate(value),
                },
            },
            yAxis: {
                type: 'value',
                min: -0.5,
                max: laneCount - 0.5,
                interval: 1,
                inverse: true,
                axisLine: {show: false},
                axisTick: {show: false},
                axisLabel: {show: false},
                splitLine: {
                    lineStyle: {
                        color: gridColors.gridColor,
                    },
                },
            },
            series: [laneHighlightSeries, segmentSeries],
            dataZoom: buildDataZoom([0]),
        };
    }

    function setupResizeObserver() {
        if (!chartContainer || resizeObserver) return;
        resizeObserver = new ResizeObserver(() => chartInstance?.resize());
        resizeObserver.observe(chartContainer);
    }

    /** Recomputes the invisible per-segment hit targets (see OverlayRect) from the chart's
     * current pixel mapping. `convertToPixel` coordinates are already relative to the chart DOM
     * node's own top-left, which is exactly the coordinate space our absolutely-positioned
     * overlay `<button>`s need — no extra offset math against ancestor elements required. */
    function computeOverlayRects(): OverlayRect[] {
        const chart = chartInstance;
        if (!chart) return [];
        const minMs = axisRangeMs?.minMs ?? null;
        const maxMs = axisRangeMs?.maxMs ?? null;
        if (minMs == null || maxMs == null) return [];

        const rects: OverlayRect[] = [];
        segmentSeriesData.forEach((datum, dataIndex) => {
            const meta = datum.meta;
            const clippedStartMs = Math.max(meta.startMs, minMs);
            const clippedEndMs = Math.min(meta.endMs, maxMs);
            if (clippedEndMs <= clippedStartMs) return; // outside visible range (defensive — should already be filtered)

            try {
                const left = chart.convertToPixel({xAxisIndex: 0, yAxisIndex: 0}, [clippedStartMs, meta.laneIndex]);
                const right = chart.convertToPixel({xAxisIndex: 0, yAxisIndex: 0}, [clippedEndMs, meta.laneIndex]);
                if (!left || !right) return;
                rects.push({
                    lotId: meta.lotId,
                    dataIndex,
                    left: Math.min(left[0], right[0]),
                    top: left[1] - LANE_ROW_HEIGHT / 2,
                    width: Math.max(4, Math.abs(right[0] - left[0])),
                    height: LANE_ROW_HEIGHT,
                });
            } catch {
                // Chart not fully laid out yet (e.g. mid-resize) — skip this segment for this
                // pass, the next 'rendered'/resize event will recompute it.
            }
        });
        return rects;
    }

    function refreshOverlayRects() {
        overlayRects = computeOverlayRects();
    }

    /** Index of the '__segments' custom series in the live ECharts option — looked up by name
     * (not hardcoded) so it stays correct if buildOption()'s series order ever changes. */
    function segmentsSeriesIndex(): number | null {
        const series = (chartInstance?.getOption() as {series?: Array<{name?: string}>} | undefined)?.series;
        if (!series) return null;
        const index = series.findIndex((entry) => entry?.name === '__segments');
        return index >= 0 ? index : null;
    }

    /** Overlay hover -> native ECharts tooltip. The overlay's own `pointer-events:auto` (needed
     * for click/dblclick/keyboard selection) sits on top of the canvas and blocks the browser's
     * hit-testing from ever reaching it, so `tooltip.trigger:'item'` never fires on a real mouse
     * hover. Driving the SAME tooltip via dispatchAction with the exact dataIndex this overlay
     * represents sidesteps that entirely — no coordinate-guessing needed. */
    function showSegmentTooltip(rect: OverlayRect) {
        const seriesIndex = segmentsSeriesIndex();
        if (seriesIndex == null) return;
        chartInstance?.dispatchAction({type: 'showTip', seriesIndex, dataIndex: rect.dataIndex});
    }

    function hideSegmentTooltip() {
        chartInstance?.dispatchAction({type: 'hideTip'});
    }

    function renderChart() {
        if (!chartContainer) return;

        syncTheme();

        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            tooltipCleanup?.();
            resizeObserver?.disconnect();
            resizeObserver = null;
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            dataZoomSyncHandle?.dispose();
            dataZoomSyncHandle = null;
            chartInstance.dispose();
            chartInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            setupResizeObserver();
            tooltipCleanup?.();
            tooltipCleanup = setupTooltipAutoHide(chartContainer, () => chartInstance);
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
            dataZoomSyncHandle = attachDataZoomSync(chartInstance, (start, end) => onZoomChange?.(start, end));
            chartInstance.on('click', (params: any) => {
                const lotId = params.info?.lotId;
                if (typeof lotId === 'number') toggleLotSelection(lotId);
            });
            chartInstance.on('dblclick', (params: any) => {
                const lotId = params.info?.lotId;
                if (typeof lotId === 'number') handleLaneDoubleClick(lotId);
            });
            chartInstance.on('rendered', refreshOverlayRects);
        }

        if (!chartHasData) {
            chartInstance.clear();
            overlayRects = [];
            return;
        }

        chartInstance.setOption(buildOption(isDark), CHART_SET_OPTION_OPTS);
        chartInstance.resize();
        refreshOverlayRects();
    }

    $effect(() => {
        if (typeof document === 'undefined') return;
        syncTheme();
        darkModeObserver = new MutationObserver(() => {
            syncTheme();
            renderChart();
        });
        darkModeObserver.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});

        return () => {
            tooltipCleanup?.();
            darkModeObserver?.disconnect();
            resizeObserver?.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            dataZoomSyncHandle?.dispose();
            dataZoomSyncHandle = null;
            chartInstance?.dispose();
            chartInstance = undefined;
            if (pulseTimeoutId != null) clearTimeout(pulseTimeoutId);
        };
    });

    $effect(() => {
        const start = externalZoomStart;
        const end = externalZoomEnd;
        if (start == null || end == null) return;
        dataZoomSyncHandle?.applyExternal(start, end);
    });

    $effect(() => {
        const pulseNonceValue = pulseState?.nonce;
        if (pulseNonceValue == null) return;
        void pulseNonceValue;
        tick().then(() => {
            if (pulseState == null) return;
            scrollLaneIntoView(pulseState.lotId);
        });
    });

    $effect(() => {
        void lots;
        void segments;
        void brokers;
        void currency;
        void xAxisRange;
        void onSelectionChange;
        void onZoomChange;
        void onRowDoubleClick;
        void renderedLanes;
        void chartHasData;
        void chartHeightPx;
        void pulseState;
        void filterMode;
        void $currentLanguage;

        if (!chartContainer) return;

        tick().then(() => {
            renderChart();
        });
    });
</script>

<div bind:this={wrapperEl} class="flex w-full flex-col gap-3 rounded-xl border border-gray-100 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800" data-testid="lot-gantt-chart">
    <div class="flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {$t('brokers.lots.ganttTitle') || 'Lot life & custody'}
        </h3>

        <div class="flex overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600">
            <button
                class="px-3 py-1 transition-colors {filterMode === 'open' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                onclick={() => onFilterModeChange?.('open')}
                data-testid="lot-gantt-filter-open"
                type="button"
            >
                {$t('brokers.lots.openOnly') || 'Open'}
            </button>
            <button
                class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {filterMode === 'all' ? 'bg-libre-green text-white' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                onclick={() => onFilterModeChange?.('all')}
                data-testid="lot-gantt-filter-all"
                type="button"
            >
                {$t('brokers.lots.allLots') || 'All'}
            </button>
        </div>
    </div>

    <div bind:this={lanesScrollEl} class="max-h-[34rem] overflow-auto rounded-lg border border-gray-100 dark:border-slate-700" data-testid="lot-gantt-scroll">
        {#if chartHasData}
            <div class="relative min-w-[720px]">
                <div bind:this={chartContainer} class="w-full" data-testid="lot-gantt-echart" style={`height:${chartHeightPx}px; min-width:${CHART_MIN_WIDTH}px;`}></div>

                <!-- Invisible per-segment hit targets kept in sync with the ECharts custom
                     series (see computeOverlayRects) — provide a real, focusable, testable DOM
                     element over each Gantt bar without reintroducing a fixed HTML column.
                     mouseenter/mousemove/mouseleave drive the native tooltip via dispatchAction
                     (see showSegmentTooltip) since this element's own pointer-events would
                     otherwise block the canvas from ever seeing the hover. -->
                {#each overlayRects as rect (rect.dataIndex)}
                    <button
                        type="button"
                        class="absolute cursor-pointer bg-transparent opacity-0"
                        style={`left:${rect.left}px; top:${rect.top}px; width:${rect.width}px; height:${rect.height}px;`}
                        data-testid={`lot-gantt-segment-${rect.lotId}`}
                        aria-label={lotLabel(lots.find((lot) => lot.lot_id === rect.lotId)?.opening_date ?? '')}
                        onclick={(event) => {
                            if (event.detail !== 1) return;
                            toggleLotSelection(rect.lotId);
                        }}
                        ondblclick={() => handleLaneDoubleClick(rect.lotId)}
                        onmouseenter={() => showSegmentTooltip(rect)}
                        onmousemove={() => showSegmentTooltip(rect)}
                        onmouseleave={hideSegmentTooltip}
                        onfocus={() => showSegmentTooltip(rect)}
                        onblur={hideSegmentTooltip}
                    ></button>
                {/each}
            </div>
        {:else}
            <div class="flex h-[220px] items-center justify-center px-4 text-center text-sm italic text-gray-400 dark:text-gray-500">
                {$t('brokers.lots.noGanttData') || 'No lot custody history in selected range'}
            </div>
        {/if}
    </div>

    {#if visibleBrokers.length > 0}
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-600 dark:text-gray-300" data-testid="lot-gantt-legend">
            {#each visibleBrokers as broker (broker.id)}
                <span data-testid={`lot-gantt-legend-broker-${broker.id}`}>
                    <BrokerBadge {broker} {brokers} size={14} showName={true} nameClass="text-xs" />
                </span>
            {/each}
            <span class="inline-flex items-center gap-2 rounded-full border border-dashed border-violet-400/70 px-2 py-1 text-xs text-violet-700 dark:border-violet-300/60 dark:text-violet-200" data-testid="lot-gantt-legend-transit">
                {$t('brokers.lots.inTransit') || 'In transit'}
            </span>
        </div>
    {/if}
</div>
