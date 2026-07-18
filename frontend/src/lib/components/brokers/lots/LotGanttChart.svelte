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
    import {buildGridColors, buildTooltipDivider, buildTooltipHeader, buildTooltipRow, buildTooltipTheme, setupTooltipAutoHide, tooltipPositionAboveFinger} from '$lib/components/charts/echartsTooltipHelpers';
    import BrokerBadge from '$lib/components/ui/display/BrokerBadge.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getBrokerColor, type BrokerLike} from '$lib/utils/broker/brokerColors';
    import {lotStateColor} from './lotStateVisual';

    type LotSummarySchema = z.infer<typeof schemas.LotSummarySchema>;
    type GanttSegmentSchema = z.infer<typeof schemas.GanttSegmentSchema>;
    type LotTimelineEventSchema = z.infer<typeof schemas.LotTimelineEventSchema>;
    type EventMarkerKind = 'BUY' | 'SELL' | 'TRANSFER' | 'ADJUSTMENT_IN' | 'ADJUSTMENT_OUT' | 'SPLIT';

    interface Props {
        lots: ReadonlyArray<LotSummarySchema>;
        segments: ReadonlyArray<GanttSegmentSchema>;
        events?: ReadonlyArray<LotTimelineEventSchema>;
        brokers: ReadonlyArray<BrokerLike>;
        currency: string;
        selectedLotIds?: number[];
        onSelectionChange?: (lotIds: number[]) => void;
        xAxisRange?: {min: string; max: string} | null;
        onZoomChange?: (start: number, end: number) => void;
        externalZoomStart?: number | null;
        externalZoomEnd?: number | null;
        onRowDoubleClick?: (lotId: number) => void;
        /** Shared "Aperti | Chiusi" filter (lifted to the orchestrator so UnifiedLotsTable and the
         * bubbles show the same lot set — see LotsAnalysisPanel.svelte). The two-button toggle renders
         * here; the incoming `lots` are already filtered, this component only reflects/drives the state. */
        openSelected?: boolean;
        closedSelected?: boolean;
        onToggleOpen?: () => void;
        onToggleClosed?: () => void;
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
        laneKey: string;
        laneIndex: number;
        parentLaneIndex: number | null;
        branchDepth: number;
        thickness: number;
        isOpen: boolean;
        isFirstInLane: boolean;
    }

    interface RenderedLane {
        laneKey: string;
        laneIndex: number;
        parentLaneIndex: number | null;
        branchDepth: number;
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
        value: [number, number, number, number];
        meta: {segment: RenderedSegment; lotId: number; pulse: boolean; selected: boolean};
    }

    interface EventMarkerDatum {
        name: string;
        value: [number, number];
        meta: {kind: EventMarkerKind; lotId: number; laneIndex: number; dateMs: number; date: string; quantity: number | null; label: string};
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
    const LANE_ROW_HEIGHT = 30;
    const STICKY_AXIS_HEIGHT = 52;
    const CHART_MIN_WIDTH = 720;
    const PULSE_DURATION_MS = 1800;
    const TOGGLE_DEBOUNCE_MS = 260;
    const THICKNESS_MIN = 10;
    const THICKNESS_MAX = 26;
    const BRANCH_THICKNESS_MAX = 22;
    const LANE_GAP_PX = 4;
    const LANE_CHART_MIN_HEIGHT = 160;
    const GRID_LEFT_PX = 56;
    const GRID_RIGHT_PX = 18;

    let {
        lots = [],
        segments = [],
        events = [],
        brokers = [],
        currency,
        selectedLotIds = [],
        onSelectionChange,
        xAxisRange = null,
        onZoomChange,
        externalZoomStart = null,
        externalZoomEnd = null,
        onRowDoubleClick,
        openSelected = true,
        closedSelected = true,
        onToggleOpen,
        onToggleClosed,
    }: Props = $props();

    let wrapperEl: HTMLDivElement | undefined = $state(undefined);
    let lanesScrollEl: HTMLDivElement | undefined = $state(undefined);
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let axisContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | undefined = undefined;
    let axisInstance: echarts.ECharts | undefined = undefined;
    let resizeObserver: ResizeObserver | null = null;
    let axisResizeObserver: ResizeObserver | null = null;
    let darkModeObserver: MutationObserver | null = null;
    let tooltipCleanup: (() => void) | null = null;
    let activeTooltipDataIndex: number | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let dataZoomSyncHandle: DataZoomSyncHandle | null = null;
    let axisDataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let axisDataZoomSyncHandle: DataZoomSyncHandle | null = null;
    let isDark = $state(false);
    let overlayRects = $state<OverlayRect[]>([]);
    let axisScrollLeft = $state(0);
    let axisContentWidthPx = $state(CHART_MIN_WIDTH);
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

    function safeUnknownString(value: unknown): string | null {
        if (Array.isArray(value)) return safeUnknownString(value[0]);
        if (typeof value === 'string') return value;
        if (typeof value === 'number' && Number.isFinite(value)) return String(value);
        return null;
    }

    function parseUnknownNumber(value: unknown): number | null {
        const raw = safeUnknownString(value);
        if (raw == null) return null;
        const parsed = Number.parseFloat(raw);
        return Number.isFinite(parsed) ? parsed : null;
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

    function translatedOr(key: string, fallback: string): string {
        const translated = $t(key);
        return !translated || translated === key ? fallback : translated;
    }

    function formatMoneyField(value: unknown): string {
        const parsed = parseUnknownNumber(value);
        return parsed == null ? '—' : formatCurrencyAmountPlain(parsed, currency);
    }

    function formatSignedMoneyField(value: unknown): string {
        const parsed = parseUnknownNumber(value);
        return parsed == null ? '—' : formatCurrencyAmountPlain(parsed, currency, {showSign: parsed !== 0});
    }

    function formatSignedPercentField(value: unknown): string {
        const parsed = parseUnknownNumber(value);
        if (parsed == null) return '—';
        const sign = parsed > 0 ? '+' : '';
        return `${sign}${(parsed * 100).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}%`;
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

    function thicknessForQuantity(quantity: number, qMax: number, isBranch: boolean): number {
        if (qMax <= 0) return THICKNESS_MIN;
        const maxThickness = isBranch ? BRANCH_THICKNESS_MAX : THICKNESS_MAX;
        return THICKNESS_MIN + (clamp(quantity, 0, qMax) / qMax) * (maxThickness - THICKNESS_MIN);
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

    function transferPairId(fragmentId: string): string | null {
        return fragmentId.match(/\/transfer:([^/]+)/)?.[1] ?? null;
    }

    function isTransferFragment(segment: SegmentModel): boolean {
        return segment.fragmentId.includes('/transfer:') || segment.custodyType === 'IN_TRANSIT';
    }

    function laneKeyForFragmentId(lotId: number, fragmentId: string): string {
        const pairId = transferPairId(fragmentId);
        if (pairId != null) return `lot:${lotId}/transfer:${pairId}`;
        return fragmentId;
    }

    function laneKeyForSegment(segment: SegmentModel): string {
        const pairId = transferPairId(segment.fragmentId);
        if (pairId != null) return `lot:${segment.lotId}/transfer:${pairId}`;
        return segment.fragmentId;
    }

    function branchDepthForLaneKey(laneKey: string): number {
        return laneKey.includes('/transfer:') ? 1 : 0;
    }

    function laneSortKey(segmentsForLane: SegmentModel[], laneKey: string): [number, number, string] {
        const firstStart = Math.min(...segmentsForLane.map((segment) => segment.startMs));
        return [branchDepthForLaneKey(laneKey), firstStart, laneKey];
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
        // The incoming `lots` are already filtered by the shared Aperti|Chiusi toggle (LotsAnalysisPanel),
        // so render every lot model as-is; only range-intersection filtering happens below.
        const sourceLots = lotModels;
        const minMs = axisRangeMs?.minMs ?? null;
        const maxMs = axisRangeMs?.maxMs ?? null;
        const candidateLots = sourceLots.filter((lot) => (segmentModelsByLot.get(lot.lotId) ?? []).some((segment) => segmentIntersectsRange(segment, minMs, maxMs)));
        const qMax = Math.max(1, ...candidateLots.map((lot) => lot.originalQuantity), ...candidateLots.flatMap((lot) => (segmentModelsByLot.get(lot.lotId) ?? []).map((segment) => segment.quantity)));

        const lanes: RenderedLane[] = [];
        for (const lot of candidateLots) {
            const lotSegments = (segmentModelsByLot.get(lot.lotId) ?? []).filter((segment) => segmentIntersectsRange(segment, minMs, maxMs));
            const grouped = new Map<string, SegmentModel[]>();
            for (const segment of lotSegments) {
                const laneKey = laneKeyForSegment(segment);
                const laneSegments = grouped.get(laneKey) ?? [];
                laneSegments.push(segment);
                grouped.set(laneKey, laneSegments);
            }

            const sortedGroups = [...grouped.entries()]
                .map(([laneKey, laneSegments]) => [laneKey, laneSegments.sort((a, b) => a.startMs - b.startMs || a.sortEndMs - b.sortEndMs || a.fragmentId.localeCompare(b.fragmentId))] as const)
                .sort((a, b) => {
                    const left = laneSortKey(a[1], a[0]);
                    const right = laneSortKey(b[1], b[0]);
                    return left[0] - right[0] || left[1] - right[1] || left[2].localeCompare(right[2]);
                });

            const originLaneIndex = sortedGroups.some(([laneKey]) => branchDepthForLaneKey(laneKey) === 0) ? lanes.length : null;
            for (const [laneKey, laneSegments] of sortedGroups) {
                const branchDepth = branchDepthForLaneKey(laneKey);
                const laneIndex = lanes.length;
                const segmentParentLaneIndex = branchDepth > 0 ? originLaneIndex : null;
                lanes.push({
                    laneKey,
                    laneIndex,
                    parentLaneIndex: segmentParentLaneIndex,
                    branchDepth,
                    lotId: lot.lotId,
                    lot,
                    isOpen: openLotIdSet.has(lot.lotId),
                    segments: laneSegments.map((segment, segmentIndex) => ({
                        ...segment,
                        laneKey,
                        laneIndex,
                        parentLaneIndex: segmentParentLaneIndex,
                        branchDepth,
                        thickness: thicknessForQuantity(segment.quantity, qMax, branchDepth > 0),
                        isOpen: segment.endDate == null,
                        isFirstInLane: segmentIndex === 0,
                    })),
                });
            }
        }

        return lanes;
    });

    const chartHasData = $derived(renderedLanes.length > 0);
    const chartHeightPx = $derived(Math.max(LANE_CHART_MIN_HEIGHT, renderedLanes.length * LANE_ROW_HEIGHT + 16));

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
            .flatMap((lane) =>
                lane.segments.map((segment) => ({
                    name: `highlight-${segment.key}`,
                    value: [segment.startMs, segment.laneIndex, segment.endMs, segment.thickness],
                    meta: {
                        segment,
                        lotId: lane.lotId,
                        pulse: pulseState?.lotId === lane.lotId,
                        selected: selectedLotIdSet.has(lane.lotId),
                    },
                })),
            ),
    );

    function eventMarkerKind(kind: string): EventMarkerKind {
        if (kind === 'TRANSFER_DEPART' || kind === 'TRANSFER_ARRIVE') return 'TRANSFER';
        if (kind === 'ADJUSTMENT_IN') return 'ADJUSTMENT_IN';
        if (kind === 'ADJUSTMENT_OUT') return 'ADJUSTMENT_OUT';
        if (kind === 'SPLIT') return 'SPLIT';
        if (kind === 'SELL') return 'SELL';
        return 'BUY';
    }

    function eventMarkerSymbol(kind: EventMarkerKind): string {
        if (kind === 'SELL') return '▼';
        if (kind === 'TRANSFER') return '◆';
        if (kind === 'ADJUSTMENT_IN') return '+';
        if (kind === 'ADJUSTMENT_OUT') return '×';
        if (kind === 'SPLIT') return '│';
        return '▲';
    }

    function eventMarkerLabel(kind: EventMarkerKind): string {
        const keyKind = kind === 'TRANSFER' ? 'TRANSFER_DEPART' : kind;
        const fallback = kind === 'ADJUSTMENT_IN' ? 'Adjustment In' : kind === 'ADJUSTMENT_OUT' ? 'Adjustment Out' : kind === 'TRANSFER' ? 'Transfer' : kind === 'SELL' ? 'Sale' : kind === 'SPLIT' ? 'Split' : 'Buy';
        return translatedOr(`brokers.lots.chartMarkers.eventType.${keyKind}`, fallback);
    }

    function isSplitTransition(prev: RenderedSegment, next: RenderedSegment): boolean {
        if (prev.quantity === next.quantity || prev.unitPrice <= 0 || next.unitPrice <= 0) return false;
        const prevNotional = prev.quantity * prev.unitPrice;
        const nextNotional = next.quantity * next.unitPrice;
        return Math.abs(prevNotional - nextNotional) <= Math.max(0.000001, Math.abs(prevNotional) * 0.0001);
    }

    function inferredTransitionKind(prev: RenderedSegment, next: RenderedSegment, transferDates: Set<number> | undefined): EventMarkerKind {
        if (transferDates?.has(next.startMs)) return 'TRANSFER';
        if (isSplitTransition(prev, next)) return 'SPLIT';
        if (next.quantity > prev.quantity) return 'ADJUSTMENT_IN';
        if (next.quantity < prev.quantity) return 'SELL';
        return 'TRANSFER';
    }

    function pushEventMarker(target: EventMarkerDatum[], seen: Set<string>, kind: EventMarkerKind, segment: RenderedSegment, dateMs: number, date: string, quantity: number | null = segment.quantity) {
        const key = `${kind}:${segment.lotId}:${segment.laneIndex}:${dateMs}`;
        if (seen.has(key)) return;
        seen.add(key);
        target.push({
            name: key,
            value: [dateMs, segment.laneIndex],
            meta: {
                kind,
                lotId: segment.lotId,
                laneIndex: segment.laneIndex,
                dateMs,
                date,
                quantity,
                label: eventMarkerLabel(kind),
            },
        });
    }

    function buildExplicitEventMarkers(): EventMarkerDatum[] {
        const byLaneKey = new Map(renderedLanes.map((lane) => [lane.laneKey, lane]));
        const firstByLot = new Map<number, RenderedLane>();
        for (const lane of renderedLanes) {
            if (!firstByLot.has(lane.lotId)) firstByLot.set(lane.lotId, lane);
        }

        const out: EventMarkerDatum[] = [];
        const seen = new Set<string>();
        for (const event of events) {
            const date = safeString(event.date) ?? '';
            const dateMs = date ? parseDateToUtcMs(date) : null;
            if (dateMs == null) continue;
            const fragmentId = safeString(event.fragment_id);
            const lane = (fragmentId != null ? byLaneKey.get(laneKeyForFragmentId(event.lot_id, fragmentId)) : null) ?? firstByLot.get(event.lot_id);
            const segment = lane?.segments.find((entry) => entry.startMs <= dateMs && entry.endMs >= dateMs) ?? lane?.segments[0];
            if (!segment) continue;
            pushEventMarker(out, seen, eventMarkerKind(event.kind), segment, dateMs, date, parseUnknownNumber(event.quantity));
        }
        return out.sort((a, b) => a.value[0] - b.value[0] || a.value[1] - b.value[1] || a.name.localeCompare(b.name));
    }

    function buildInferredEventMarkers(): EventMarkerDatum[] {
        const out: EventMarkerDatum[] = [];
        const seen = new Set<string>();
        const transferStartsByLot = new Map<number, Set<number>>();
        for (const lane of renderedLanes) {
            if (lane.branchDepth === 0) continue;
            const first = lane.segments[0];
            if (!first) continue;
            const starts = transferStartsByLot.get(lane.lotId) ?? new Set<number>();
            starts.add(first.startMs);
            transferStartsByLot.set(lane.lotId, starts);
        }

        for (const lane of renderedLanes) {
            const transferStarts = transferStartsByLot.get(lane.lotId);
            const sorted = [...lane.segments].sort((a, b) => a.startMs - b.startMs || a.sortEndMs - b.sortEndMs);
            const first = sorted[0];
            if (!first) continue;
            pushEventMarker(out, seen, lane.branchDepth > 0 || isTransferFragment(first) ? 'TRANSFER' : 'BUY', first, first.startMs, first.startDate, first.quantity);

            for (let index = 1; index < sorted.length; index += 1) {
                const prev = sorted[index - 1];
                const next = sorted[index];
                if (prev.endMs !== next.startMs) continue;
                pushEventMarker(out, seen, inferredTransitionKind(prev, next, transferStarts), next, next.startMs, next.startDate, Math.abs(prev.quantity - next.quantity) || next.quantity);
            }

            for (const segment of sorted) {
                if (segment.custodyType === 'IN_TRANSIT' && segment.endDate != null) {
                    pushEventMarker(out, seen, 'TRANSFER', segment, segment.endMs, segment.endDate, segment.quantity);
                }
            }

            const last = sorted.at(-1);
            if (last?.endDate != null && !transferStarts?.has(last.endMs)) {
                pushEventMarker(out, seen, 'SELL', last, last.endMs, last.endDate, last.quantity);
            }
        }
        return out.sort((a, b) => a.value[0] - b.value[0] || a.value[1] - b.value[1] || a.name.localeCompare(b.name));
    }

    const eventMarkerData = $derived.by((): EventMarkerDatum[] => (events.length > 0 ? buildExplicitEventMarkers() : buildInferredEventMarkers()));

    function firstPresentUnknown(...values: unknown[]): unknown {
        for (const value of values) {
            if (Array.isArray(value)) {
                const scalar = value[0];
                if (scalar != null) return scalar;
            } else if (value != null) {
                return value;
            }
        }
        return undefined;
    }

    function compactStateLabel(lot: LotModel | undefined, openQuantity: number, originalQuantity: number): string {
        if (openQuantity <= 0) return translatedOr('brokers.lots.modal.state.closed', 'Closed');
        if (lot?.states.includes('PARTIALLY_CLOSED') || openQuantity < originalQuantity) return translatedOr('brokers.lots.modal.state.partially_closed', 'Partially closed');
        return translatedOr('brokers.lots.modal.state.open', 'Open');
    }

    function latestLotEndDate(lotId: number): string | null {
        const latest = (segmentModelsByLot.get(lotId) ?? [])
            .filter((segment) => segment.endDate != null)
            .sort((a, b) => b.endMs - a.endMs)[0];
        return latest?.endDate ?? null;
    }

    function segmentBrokerLabel(meta: RenderedSegment, lot: LotModel | undefined): string {
        if (meta.custodyType === 'IN_TRANSIT') return `${brokerName(meta.sourceBrokerId)} → ${brokerName(meta.destinationBrokerId)}`;
        return brokerName(meta.brokerId ?? lot?.openingBrokerId ?? null);
    }

    function signedColorField(value: unknown, formatter: (v: unknown) => string, themeDark: boolean): string {
        const num = parseUnknownNumber(value);
        const text = escapeHtml(formatter(value));
        if (num == null || num === 0) return text;
        const color = num > 0 ? (themeDark ? '#4ade80' : '#16a34a') : themeDark ? '#f87171' : '#dc2626';
        return `<span style="color:${color}">${text}</span>`;
    }

    function buildTooltip(meta: RenderedSegment, themeDark: boolean): string {
        const theme = buildTooltipTheme(themeDark);
        const lot = renderedLanes.find((lane) => lane.lotId === meta.lotId)?.lot;
        const lotDto = lot?.lot;
        const openingDate = lot?.openingDate || meta.startDate;
        const openQuantity = lot?.openQuantity ?? Math.max(0, meta.isOpen ? meta.quantity : 0);
        const originalQuantity = lot?.originalQuantity ?? Math.max(openQuantity, meta.quantity);
        const isClosedLot = openQuantity <= 0;
        const stateLabel = compactStateLabel(lot, openQuantity, originalQuantity);
        const brokerLabel = segmentBrokerLabel(meta, lot);
        const valueSource = safeUnknownString(lotDto?.value_source);
        const isEstimatedAtCost = valueSource === 'ESTIMATED_AT_COST';
        const currentValue = firstPresentUnknown(lotDto?.open_value, lotDto?.total_value);
        const valueField = isClosedLot ? lotDto?.original_cost : currentValue;
        const valueLabel = isClosedLot ? translatedOr('brokers.lots.tooltip.initialValue', 'Initial value') : translatedOr('brokers.lots.currentValue', 'Current value');
        const assetIncome = parseUnknownNumber(lotDto?.asset_income);
        const quantityLine = isClosedLot
            ? `${formatQuantity(originalQuantity)} → 0 ${translatedOr('brokers.lots.tooltip.shares', 'shares')}`
            : `${formatQuantity(openQuantity)} ${translatedOr('brokers.lots.tooltip.sharesOpenOutOf', 'shares open out of')} ${formatQuantity(originalQuantity)}`;
        const closeDate = isClosedLot ? latestLotEndDate(meta.lotId) ?? meta.endDate : null;
        const footer = isClosedLot
            ? `${formatDateLong(openingDate)} → ${closeDate ? formatDateLong(closeDate) : '…'}`
            : `${translatedOr('brokers.lots.tooltip.since', 'Since')} ${formatDateLong(openingDate)}`;
        let html = buildTooltipHeader(escapeHtml(lotLabel(openingDate)), theme.textColor);
        html += `<div style="margin-top:6px;font-weight:700;color:${theme.textColor}">${escapeHtml(brokerLabel)} · ${escapeHtml(meta.direction)} · ${escapeHtml(stateLabel)}</div>`;
        html += `<div style="margin-top:2px;color:${theme.mutedColor}">${escapeHtml(quantityLine)}</div>`;
        html += buildTooltipDivider(theme.border);
        html += buildTooltipRow(escapeHtml(translatedOr('brokers.lots.openingPriceReference', 'Opening price')), escapeHtml(formatMoneyField(firstPresentUnknown(lotDto?.opening_unit_price, meta.unitPrice))));
        if (isEstimatedAtCost && !isClosedLot) {
            const estimatedColor = themeDark ? '#fbbf24' : '#d97706';
            const estLabel = `<span style="color:${estimatedColor};font-weight:600">⚠ ${escapeHtml(translatedOr('brokers.lots.estimatedCurrentValue', 'Estimated current value'))}</span>`;
            const estValue = `<span style="color:${estimatedColor}">${escapeHtml(formatMoneyField(valueField))}</span>`;
            html += buildTooltipRow(estLabel, estValue);
        } else {
            html += buildTooltipRow(escapeHtml(valueLabel), escapeHtml(formatMoneyField(valueField)));
        }
        if (assetIncome != null && assetIncome !== 0) {
            html += buildTooltipRow(escapeHtml(translatedOr('brokers.lots.assetIncome', 'Income')), signedColorField(assetIncome, formatSignedMoneyField, themeDark));
        }
        html += buildTooltipRow(escapeHtml(translatedOr('brokers.lots.tooltip.totalPnl', 'Total P&L')), signedColorField(firstPresentUnknown(lotDto?.total_pnl, lotDto?.pnl), formatSignedMoneyField, themeDark));
        html += buildTooltipRow(escapeHtml(translatedOr('brokers.lots.totalReturn', 'Total return')), signedColorField(lotDto?.total_return, formatSignedPercentField, themeDark));
        html += buildTooltipDivider(theme.border);
        html += `<div style="margin-top:4px;color:${theme.mutedColor}">${escapeHtml(footer)}</div>`;

        return `<div style="min-width:250px;font-size:11px;color:${theme.textColor}">${html}</div>`;
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
                const segment = meta.segment;
                const startCoord = api.coord([segment.startMs, segment.laneIndex]);
                const endCoord = api.coord([segment.endMs, segment.laneIndex]);
                const bandSize = (api.size?.([0, 1]) as number[] | undefined)?.[1] ?? LANE_ROW_HEIGHT;
                const barHeight = Math.min(segment.thickness + 6, Math.max(8, bandSize - 2));
                const coordSys = params.coordSys as {x: number; y: number; width: number; height: number};
                const rectShape = echarts.graphic.clipRectByRect(
                    {
                        x: Math.min(startCoord[0], endCoord[0]) - 2,
                        y: startCoord[1] - barHeight / 2,
                        width: Math.max(5, Math.abs(endCoord[0] - startCoord[0]) + 4),
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
                return {
                    type: 'rect',
                    silent: true,
                    shape: {...rectShape, r: 8},
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
                const barHeight = Math.min(meta.thickness, Math.max(8, laneBand - LANE_GAP_PX));
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

                if (meta.isFirstInLane && meta.parentLaneIndex != null && !isClippedLeft) {
                    const parentCoord = api.coord([meta.startMs, meta.parentLaneIndex]);
                    const elbowX = Math.max(coordSys.x + 4, startCoord[0] - 12 - meta.branchDepth * 8);
                    children.unshift({
                        type: 'polyline',
                        silent: true,
                        shape: {
                            points: [
                                [elbowX, parentCoord[1]],
                                [elbowX, startCoord[1]],
                                [Math.max(coordSys.x + 4, startCoord[0] - 2), startCoord[1]],
                            ],
                        },
                        style: {
                            stroke: themeDark ? 'rgba(226,232,240,0.48)' : 'rgba(71,85,105,0.45)',
                            lineWidth: 1.5,
                            fill: 'none',
                        },
                    });
                }

                if (isClippedLeft) {
                    // Segment starts before the visible range — a left-pointing chevron ("‹" arrow,
                    // stroked not filled) replaces the usual opening dot to signal "this lot's story
                    // continues off-screen" without reading as a heavy black triangle when selected.
                    children.push({
                        type: 'polyline',
                        silent: true,
                        shape: {
                            points: [
                                [edgeMarkerX + 6, startCoord[1] - Math.min(7, barHeight / 2)],
                                [edgeMarkerX - 4, startCoord[1]],
                                [edgeMarkerX + 6, startCoord[1] + Math.min(7, barHeight / 2)],
                            ],
                        },
                        style: {stroke: borderColor, lineWidth: 2, fill: 'none', opacity: 0.9},
                    });
                }

                if ((meta.isOpen || isClippedRight) && rectShape.width >= 24) {
                    children.push({
                        type: 'polyline',
                        silent: true,
                        shape: {
                            points: [
                                [rectShape.x + rectShape.width - 10, startCoord[1] - Math.min(7, barHeight / 2)],
                                [rectShape.x + rectShape.width, startCoord[1]],
                                [rectShape.x + rectShape.width - 10, startCoord[1] + Math.min(7, barHeight / 2)],
                            ],
                        },
                        style: {stroke: borderColor, lineWidth: 2, fill: 'none', opacity: 0.9},
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

        const eventMarkerSeries: any = {
            name: '__event-markers',
            type: 'custom',
            clip: false,
            z: 6,
            tooltip: {show: false},
            data: eventMarkerData,
            renderItem: (params: any, api: any) => {
                const meta = eventMarkerData[params.dataIndex]?.meta as EventMarkerDatum['meta'] | undefined;
                if (!meta) return null;
                const coord = api.coord([meta.dateMs, meta.laneIndex]);
                const coordSys = params.coordSys as {x: number; width: number};
                if (coord[0] < coordSys.x - 10 || coord[0] > coordSys.x + coordSys.width + 10) return null;
                const color = meta.kind === 'SELL' || meta.kind === 'ADJUSTMENT_OUT' ? (themeDark ? '#f87171' : '#dc2626') : meta.kind === 'TRANSFER' ? (themeDark ? '#c084fc' : '#7c3aed') : meta.kind === 'SPLIT' ? (themeDark ? '#facc15' : '#ca8a04') : themeDark ? '#34d399' : '#059669';
                return {
                    type: 'text',
                    info: {lotId: meta.lotId},
                    cursor: 'pointer',
                    x: coord[0],
                    y: coord[1],
                    silent: false,
                    style: {
                        text: eventMarkerSymbol(meta.kind),
                        fill: color,
                        stroke: themeDark ? '#0f172a' : '#ffffff',
                        lineWidth: 3,
                        fontSize: meta.kind === 'SPLIT' ? 18 : 15,
                        fontWeight: 800,
                        textAlign: 'center',
                        textVerticalAlign: 'middle',
                    },
                };
            },
        };

        return {
            ...CHART_ANIMATION_CONFIG,
            animationDurationUpdate: 450,
            grid: {
                top: 8,
                right: GRID_RIGHT_PX,
                bottom: 8,
                left: GRID_LEFT_PX,
                containLabel: false,
            },
            tooltip: {
                trigger: 'item',
                position: tooltipPositionAboveFinger,
                appendTo: 'body',
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
                    show: false,
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
            series: [laneHighlightSeries, segmentSeries, eventMarkerSeries],
            dataZoom: ganttDataZoom(),
        };
    }

    /** Preserve the shared zoom window across re-renders (both the lane instance and the sticky
     * axis instance), so a data/theme re-render does not silently reset dataZoom to 0-100 and
     * desync the Gantt from the WAC/price chart. setOption does not re-emit a 'dataZoom' event,
     * so this cannot cause a sync ping-pong. */
    function applySharedZoomWindow<T extends {start?: number; end?: number}>(zooms: T[]): T[] {
        if (externalZoomStart == null || externalZoomEnd == null) return zooms;
        return zooms.map((zoom) => ({...zoom, start: externalZoomStart as number, end: externalZoomEnd as number}));
    }

    /** Gantt bars are custom-series items whose x-value is the segment START. With the default
     * dataZoom `filterMode:'filter'` ECharts DROPS any data item whose start scrolls out of the
     * zoom window, so a bar that still overlaps the visible range vanishes entirely the moment its
     * opening event leaves the left edge. `filterMode:'none'` keeps every item and lets the
     * renderItem `clipRectByRect` trim the bar at the plot edges instead (see renderItem clip). */
    function ganttDataZoom(): any[] {
        return applySharedZoomWindow(buildDataZoom([0]).map((zoom) => ({...zoom, filterMode: 'none'})));
    }

    function buildAxisOption(themeDark: boolean): echarts.EChartsOption {
        const gridColors = buildGridColors(themeDark);
        const minMs = axisRangeMs?.minMs ?? Date.now() - DAY_MS;
        const maxMs = axisRangeMs?.maxMs ?? Date.now();
        return {
            ...CHART_ANIMATION_CONFIG,
            grid: {
                top: 4,
                right: GRID_RIGHT_PX,
                bottom: 22,
                left: GRID_LEFT_PX,
                containLabel: false,
            },
            xAxis: {
                type: 'time',
                min: xAxisRange?.min ?? minMs,
                max: xAxisRange?.max ?? maxMs,
                axisLine: {lineStyle: {color: gridColors.gridColor}},
                axisTick: {show: true, lineStyle: {color: gridColors.gridColor}},
                splitLine: {show: false},
                axisLabel: {
                    color: gridColors.textColor,
                    hideOverlap: true,
                    formatter: (value: number) => formatAxisDate(value),
                },
            },
            yAxis: {
                type: 'value',
                min: 0,
                max: 1,
                axisLine: {show: false},
                axisTick: {show: false},
                axisLabel: {show: false},
                splitLine: {show: false},
            },
            series: [],
            dataZoom: ganttDataZoom(),
        };
    }

    function setupResizeObserver() {
        if (chartContainer && !resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                syncAxisViewport();
                chartInstance?.resize();
            });
            resizeObserver.observe(chartContainer);
        }
        if (axisContainer && !axisResizeObserver) {
            axisResizeObserver = new ResizeObserver(() => axisInstance?.resize());
            axisResizeObserver.observe(axisContainer);
        }
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
                    top: left[1] - Math.min(LANE_ROW_HEIGHT, Math.max(24, meta.thickness + 8)) / 2,
                    width: Math.max(4, Math.abs(right[0] - left[0])),
                    height: Math.min(LANE_ROW_HEIGHT, Math.max(24, meta.thickness + 8)),
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

    function syncAxisViewport() {
        if (!lanesScrollEl) return;
        axisScrollLeft = lanesScrollEl.scrollLeft;
        axisContentWidthPx = Math.max(CHART_MIN_WIDTH, chartContainer?.clientWidth ?? lanesScrollEl.scrollWidth ?? CHART_MIN_WIDTH);
    }

    function handleLanesScroll() {
        syncAxisViewport();
        refreshOverlayRects();
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
        activeTooltipDataIndex = rect.dataIndex;
        chartInstance?.dispatchAction({type: 'showTip', seriesIndex, dataIndex: rect.dataIndex});
    }

    function hideSegmentTooltip() {
        activeTooltipDataIndex = null;
        chartInstance?.dispatchAction({type: 'hideTip'});
    }

    /** Re-assert the currently hovered/tapped segment's tooltip after a selection re-render.
     * On touch a tap both shows the tooltip (mouseenter) and toggles selection (click); the
     * selection setOption would otherwise drop the freshly shown tip — re-showing keeps it up
     * (the touch auto-hide timer still dismisses it a few seconds later). */
    function reassertActiveTooltip() {
        if (activeTooltipDataIndex == null) return;
        const seriesIndex = segmentsSeriesIndex();
        if (seriesIndex == null) return;
        chartInstance?.dispatchAction({type: 'showTip', seriesIndex, dataIndex: activeTooltipDataIndex});
    }

    function renderChart() {
        if (!chartContainer) {
            chartInstance?.clear();
            axisInstance?.clear();
            overlayRects = [];
            return;
        }

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
        if (axisInstance && (!axisContainer || axisInstance.getDom() !== axisContainer)) {
            axisResizeObserver?.disconnect();
            axisResizeObserver = null;
            axisDataZoomTouchPanHandle?.dispose();
            axisDataZoomTouchPanHandle = null;
            axisDataZoomSyncHandle?.dispose();
            axisDataZoomSyncHandle = null;
            axisInstance.dispose();
            axisInstance = undefined;
        }

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
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
        if (axisContainer && !axisInstance) {
            axisInstance = echarts.init(axisContainer, undefined, {renderer: 'canvas'});
            axisDataZoomTouchPanHandle = attachDataZoomTouchPan(axisInstance, axisContainer);
            axisDataZoomSyncHandle = attachDataZoomSync(axisInstance, (start, end) => onZoomChange?.(start, end));
        }
        setupResizeObserver();

        if (!chartHasData) {
            chartInstance.clear();
            axisInstance?.clear();
            overlayRects = [];
            return;
        }

        syncAxisViewport();
        chartInstance.setOption(buildOption(isDark), CHART_SET_OPTION_OPTS);
        axisInstance?.setOption(buildAxisOption(isDark), CHART_SET_OPTION_OPTS);
        chartInstance.resize();
        axisInstance?.resize();
        refreshOverlayRects();
    }

    function refreshSelectionRendering() {
        if (!chartInstance || !chartHasData) return;
        chartInstance.setOption(
            {
                // Selection only re-tints existing bars — skip the 450ms update morph so a mobile tap
                // (which both selects and shows a tooltip) doesn't animate every chart or drop the tip.
                animationDurationUpdate: 0,
                series: [
                    {name: '__lane-highlight', data: laneHighlightData},
                    {name: '__segments', data: segmentSeriesData},
                    {name: '__event-markers', data: eventMarkerData},
                ],
            },
            {notMerge: false},
        );
        refreshOverlayRects();
        reassertActiveTooltip();
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
            axisResizeObserver?.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            dataZoomSyncHandle?.dispose();
            dataZoomSyncHandle = null;
            axisDataZoomTouchPanHandle?.dispose();
            axisDataZoomTouchPanHandle = null;
            axisDataZoomSyncHandle?.dispose();
            axisDataZoomSyncHandle = null;
            chartInstance?.dispose();
            chartInstance = undefined;
            axisInstance?.dispose();
            axisInstance = undefined;
            if (pulseTimeoutId != null) clearTimeout(pulseTimeoutId);
        };
    });

    $effect(() => {
        const start = externalZoomStart;
        const end = externalZoomEnd;
        if (start == null || end == null) return;
        dataZoomSyncHandle?.applyExternal(start, end);
        axisDataZoomSyncHandle?.applyExternal(start, end);
    });

    $effect(() => {
        void selectedLotIds;
        void laneHighlightData;
        void segmentSeriesData;
        void eventMarkerData;
        void pulseState;
        if (!chartInstance || !chartHasData) return;
        tick().then(refreshSelectionRendering);
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
        void events;
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
        void openSelected;
        void closedSelected;
        void axisContainer;
        void axisContentWidthPx;
        void $currentLanguage;

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

        <div class="flex w-fit overflow-hidden rounded-lg border border-gray-200 text-xs font-medium dark:border-slate-600" data-testid="lot-gantt-state-filter">
            <button
                class="px-3 py-1 transition-colors {openSelected ? '' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                style={openSelected ? `background-color:${lotStateColor('OPEN', isDark)};color:${isDark ? '#0f172a' : '#ffffff'}` : ''}
                onclick={() => onToggleOpen?.()}
                data-testid="lot-gantt-filter-open"
                aria-pressed={openSelected}
                type="button"
            >
                {$t('brokers.lots.openOnly') || 'Open'}
            </button>
            <button
                class="border-l border-gray-200 px-3 py-1 transition-colors dark:border-slate-600 {closedSelected ? '' : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-400 dark:hover:bg-slate-700'}"
                style={closedSelected ? `background-color:${lotStateColor('CLOSED', isDark)};color:${isDark ? '#0f172a' : '#ffffff'}` : ''}
                onclick={() => onToggleClosed?.()}
                data-testid="lot-gantt-filter-closed"
                aria-pressed={closedSelected}
                type="button"
            >
                {$t('brokers.lots.closedOnly') || 'Closed'}
            </button>
        </div>
    </div>

    <div class="overflow-hidden rounded-lg border border-gray-100 dark:border-slate-700">
        <div bind:this={lanesScrollEl} class="max-h-[34rem] overflow-auto" data-testid="lot-gantt-scroll" onscroll={handleLanesScroll}>
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

        {#if chartHasData}
            <div class="overflow-hidden border-t border-gray-100 bg-white dark:border-slate-700 dark:bg-slate-800" data-testid="lot-gantt-sticky-axis">
                <div bind:this={axisContainer} class="will-change-transform" style={`height:${STICKY_AXIS_HEIGHT}px; width:${axisContentWidthPx}px; min-width:${CHART_MIN_WIDTH}px; transform:translateX(-${axisScrollLeft}px);`}></div>
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
