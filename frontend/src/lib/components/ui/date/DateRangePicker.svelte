<!--
  DateRangePicker — Unified date range picker with custom dual-calendar popover.

  Features:
  - "Flight-style" From/To display fields in a single unified component
  - Click to open custom dual-calendar popover with SEMI-INDEPENDENT columns
    (each column has its own month/year selector, auto-swap if out of order)
  - Click any two dates → min is "from", max is "to"
  - Quick-select preset buttons: 1W, 1M, 1Y, Custom (inline editable badge)
  - Custom window: number + granularity (days/weeks/months/years) going backwards from today
  - All presets compute "from today backwards"
  - i18n for weekdays and month names
  - Dark mode support
  - Emits change event with {start, end} dates

  Used by: FX list page, FX detail page, transaction filters, etc.
-->
<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {Calendar} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import type {CalendarHighlights} from './CalendarMonth.svelte';
    import CalendarMonth from './CalendarMonth.svelte';
    import {SimpleSelect} from '$lib/components/ui/select';
    import {attachLayoutDebugExtra, type LayoutMode} from '$lib/utils/layout/responsiveLayout.svelte';

    // =========================================================================
    // Types
    // =========================================================================

    export type QuickPreset = '1W' | '1M' | '3M' | '6M' | 'WTD' | 'MTD' | 'QTD' | 'YTD' | '1Y' | '2Y' | '3Y' | '5Y' | '10Y' | 'MAX';
    export type Granularity = 'days' | 'weeks' | 'months' | 'years';

    interface Props {
        /** Start date (ISO YYYY-MM-DD) */
        start: string;
        /** End date (ISO YYYY-MM-DD) */
        end: string;
        /** Active preset (if any) */
        activePreset?: QuickPreset | 'custom' | null;
        /** Show quick presets */
        showPresets?: boolean;
        /** Show custom window input */
        showCustomWindow?: boolean;
        /** Show date input fields (From/To) — set false to show only presets */
        showDateFields?: boolean;
        /** Compact mode (smaller text, tighter spacing) */
        compact?: boolean;
        /** Show From/To stacked vertically instead of side by side */
        stacked?: boolean;
        /** Portal calendar popover to document.body (fixes z-index inside tables with overflow) */
        usePortal?: boolean;
        /** Allow selecting future dates (default: false) */
        allowFuture?: boolean;
        /** Root alignment: 'center' (default, unchanged) or 'start' (left-justified — for use inside a page toolbar where the whole block shouldn't float centered) */
        align?: 'center' | 'start';
        /** Max width in px for the align='start' toolbar layout WHEN the picker is in 1-row mode
         *  (default 740 — user-tuned value, was Tailwind's max-w-2xl/672 originally). Starting
         *  value only — becomes a live reactive knob internally (see debugName). Ignored when
         *  the picker is in 2-row mode (see `maxWidthTwoRow` below). */
        maxWidth?: number;
        /** Max width in px for the align='start' toolbar layout WHEN the picker is in 2-row mode
         *  (Round 10.1 — default 390, user-tuned). A single shared `maxWidth` looked fine for 1
         *  row but produced an ugly, overly-wide 2-row layout (each row much wider than its own
         *  content needs, huge `justify-between` gaps) — the 2 row-modes need their own,
         *  independently tunable cap. Only applies when `isSingleRow` is false (i.e. `layoutMode`
         *  is anything other than `'oneRow'`, or no `layoutMode` prop is used AND the internal
         *  content itself doesn't fit in `maxWidth`'s single-row budget).
         *  ⚠️ Round 13 invariant: MUST be >= the page's own `thresholds.oneColumn` value — the
         *  narrowest tier (`oneColumn`) can still present a container as wide as that threshold
         *  (it's the unconditional fallback below `stackFilters`, not its own banded tier — see
         *  responsiveLayout.svelte.ts), so a smaller `maxWidthTwoRow` artificially caps the picker
         *  (and the "Centro" content mirroring it via `effectiveMaxWidth`) narrower than the space
         *  actually available, wasting it. Pages with `oneColumn` > 390 (the default) MUST pass an
         *  explicit `maxWidthTwoRow` >= that threshold (see the 5 pages that do this today). */
        maxWidthTwoRow?: number;
        /** Current PageToolbar layoutMode (Round 10) — when provided, DIRECTLY controls whether
         *  the picker renders 1 row or 2 internal rows: 'oneRow' → 1 row, everything else → 2 rows.
         *  This is a deterministic, threshold-driven decision (via the page's `oneRow` threshold
         *  in PageToolbar), NOT autonomous content measurement — the whole point is giving the
         *  page/thresholds full control over the whole row, per explicit user request. Omit to
         *  default to 1-row (matches the pre-Round-10 default when no toolbar context exists). */
        layoutMode?: LayoutMode;
        /** Registers a live-tunable {maxWidth, maxWidthTwoRow} config on window.__lfLayouts.<debugName>.pickerConfig for console tuning (e.g. window.__lfLayouts.dashboard.pickerConfig.maxWidthTwoRow = 420) — no resize needed, recomputes immediately. Omit to skip registration. */
        debugName?: string;
        /** Optional read-out of the picker's OWN currently-applied max-width (740/maxWidth in
         *  1-row mode, 390/maxWidthTwoRow in 2-row mode) — lets a page mirror this exact value
         *  onto its own "Center" content (e.g. currency/broker row) so both stay pixel-aligned
         *  when `filtersStacked`, including while live-tuning `pickerConfig` from the console. */
        effectiveMaxWidth?: number;
        /** Called when dates change */
        onchange?: (start: string, end: string) => void;
    }

    let {
        start = $bindable(''),
        end = $bindable(''),
        activePreset = $bindable(null),
        showPresets = true,
        showCustomWindow = true,
        showDateFields = true,
        compact = false,
        stacked = false,
        usePortal = false,
        allowFuture = false,
        align = 'center',
        maxWidth: initialMaxWidth = 740,
        maxWidthTwoRow: initialMaxWidthTwoRow = 390,
        layoutMode,
        debugName,
        // Non-undefined fallback (390 = maxWidthTwoRow default) is REQUIRED: Svelte 5 forbids
        // `bind:key={undefined}` when `key` has ANY declared fallback (even `undefined` itself)
        // — the parent's bound variable must never START as undefined, or it crashes at mount
        // with props_invalid_value. Matches PageToolbar's layoutMode/isStacked/showActionLabels
        // pattern, which all use real (non-undefined) fallbacks for the same reason.
        effectiveMaxWidth: effectiveMaxWidthOut = $bindable(390),
        onchange,
    }: Props = $props();

    // Reactive config — mutating pickerConfig.maxWidth/maxWidthTwoRow (typically from the console
    // debug registry) resizes the picker immediately: the style binding below re-renders, the
    // browser reflows, and the existing ResizeObserver on presetRowRef picks up the new width on
    // its own. untrack(): both are prop-seeded initial values, not meant to track the prop
    // reactively afterward (same pattern used for thresholds/layoutDebugName in PageToolbar).
    let pickerConfig = $state({maxWidth: untrack(() => initialMaxWidth), maxWidthTwoRow: untrack(() => initialMaxWidthTwoRow)});
    const debugNameSnapshot = untrack(() => debugName);
    if (debugNameSnapshot) attachLayoutDebugExtra(debugNameSnapshot, {pickerConfig});

    // =========================================================================
    // State
    // =========================================================================

    let customAmount = $state(3);
    let customGranularity: Granularity = $state('years');
    let customEditing = $state(false);

    // Calendar popover state
    let calendarOpen = $state(false);
    let pendingDate: string | null = $state(null);
    let hoveredDate: string | null = $state(null);
    let triggerEl: HTMLButtonElement | null = $state(null);
    let popoverStyle = $state('');

    // Semi-independent left/right month+year
    let calLeftYear = $state(new Date().getFullYear());
    let calLeftMonth = $state(new Date().getMonth());
    let calRightYear = $state(new Date().getFullYear());
    let calRightMonth = $state(new Date().getMonth());

    // =========================================================================
    // i18n Weekdays and Months
    // =========================================================================

    const WEEKDAY_KEYS = ['datePicker.weekdays.mo', 'datePicker.weekdays.tu', 'datePicker.weekdays.we', 'datePicker.weekdays.th', 'datePicker.weekdays.fr', 'datePicker.weekdays.sa', 'datePicker.weekdays.su'];

    const MONTH_KEYS = [
        'datePicker.months.january',
        'datePicker.months.february',
        'datePicker.months.march',
        'datePicker.months.april',
        'datePicker.months.may',
        'datePicker.months.june',
        'datePicker.months.july',
        'datePicker.months.august',
        'datePicker.months.september',
        'datePicker.months.october',
        'datePicker.months.november',
        'datePicker.months.december',
    ];

    // Pre-compute translated strings at top-level (Svelte 5 doesn't allow $_ inside snippets)
    let weekdayLabels: string[] = $derived(WEEKDAY_KEYS.map((k) => $_(k)));
    let monthLabels: string[] = $derived(MONTH_KEYS.map((k) => $_(k)));

    // =========================================================================
    // Preset Definitions
    // =========================================================================

    const presets: {key: QuickPreset; label: string; months?: number; weeks?: number; years?: number}[] = [
        {key: '1W', label: '1W', weeks: 1},
        {key: '1M', label: '1M', months: 1},
        {key: '3M', label: '3M', months: 3},
        {key: '6M', label: '6M', months: 6},
        {key: '1Y', label: '1Y', years: 1},
        {key: '2Y', label: '2Y', years: 2},
        {key: 'YTD', label: $_('datePicker.presets.ytd')},
        {key: 'MAX', label: $_('datePicker.presets.max')},
    ];

    // "Jolly" fill badges — two independent pools, each belonging to one of the two visual
    // blocks (Block A = core presets, Block B = YTD/Tutti/Personalizzato). They are NEVER shown
    // via fixed CSS breakpoints — a real JS measurement (see "JS-measured jolly fill" below)
    // decides how many of each to render, only to fill leftover space that would otherwise stay
    // empty, never as the cause of an extra line wrap.
    // Duration pool — extends the core year progression (Block A).
    const durationFillPresets: {key: QuickPreset; label: string; years: number}[] = [
        {key: '3Y', label: '3Y', years: 3},
        {key: '5Y', label: '5Y', years: 5},
        {key: '10Y', label: '10Y', years: 10},
    ];
    // Period pool — extends the "start of period to today" family alongside YTD (Block B).
    const periodFillPresets: {key: QuickPreset; label: string}[] = [
        {key: 'MTD', label: $_('datePicker.presets.mtd')},
        {key: 'QTD', label: $_('datePicker.presets.qtd')},
        {key: 'WTD', label: $_('datePicker.presets.wtd')},
    ];

    const granularityOptions: {value: Granularity; labelKey: string; shortKey: string}[] = [
        {value: 'days', labelKey: 'datePicker.granularity.days', shortKey: 'datePicker.granularity.daysShort'},
        {value: 'weeks', labelKey: 'datePicker.granularity.weeks', shortKey: 'datePicker.granularity.weeksShort'},
        {value: 'months', labelKey: 'datePicker.granularity.months', shortKey: 'datePicker.granularity.monthsShort'},
        {value: 'years', labelKey: 'datePicker.granularity.years', shortKey: 'datePicker.granularity.yearsShort'},
    ];

    // Granularity short options for the compact native select (must be after granularityOptions)
    let granularitySelectOptions = $derived(granularityOptions.map((o) => ({value: o.value, label: $_(o.shortKey).toUpperCase()})));

    // Auto-detect which preset matches the current start/end dates (± 1 day tolerance).
    // This ensures badges highlight correctly even when dates come from URL params.
    let effectivePreset = $derived.by(() => {
        if (activePreset) return activePreset;
        // "min" is the MAX/"All" sentinel — may still be pending resolution to a
        // concrete date by the controller, but the badge should highlight regardless.
        if (start === 'min') return 'MAX';
        if (!start || !end) return null;
        const today = todayISO();
        // End must be today (presets always go "backwards from today")
        if (end !== today) return null;
        for (const p of [...presets, ...durationFillPresets, ...periodFillPresets]) {
            const expectedStart = computeStartDate(p.key);
            // Allow ±1 day tolerance (timezone edge cases)
            const diff = Math.abs(new Date(start).getTime() - new Date(expectedStart).getTime());
            if (diff <= 86400000) return p.key;
        }
        return null;
    });

    // =========================================================================
    // Helpers
    // =========================================================================

    function todayISO(): string {
        return new Date().toISOString().slice(0, 10);
    }

    // Shared by YTD/WTD/MTD/QTD: a "start of period" that's very recent (e.g. YTD on Jan 2nd,
    // WTD on a Monday) would otherwise produce a near-empty 1-2 day chart — enforce a minimum
    // window by falling back to "N days ago" whenever the period start is more recent than
    // that. Default 14 days for YTD/MTD/QTD; WTD uses its own smaller 6-day floor (see call
    // site below) since a week-to-date range is by definition never more than 6 days old — a
    // 14-day floor would ALWAYS override it, making WTD collapse into a fixed "last 14 days"
    // preset that can never show its real (shorter) range.
    function withMinWindow(periodStart: string, minDays = 14): string {
        const minDate = new Date();
        minDate.setDate(minDate.getDate() - minDays);
        const floor = minDate.toISOString().slice(0, 10);
        return periodStart < floor ? periodStart : floor;
    }

    function computeStartDate(preset: QuickPreset): string {
        const d = new Date();
        switch (preset) {
            case '1W':
                d.setDate(d.getDate() - 7);
                break;
            case '1M':
                d.setMonth(d.getMonth() - 1);
                break;
            case '3M':
                d.setMonth(d.getMonth() - 3);
                break;
            case '6M':
                d.setMonth(d.getMonth() - 6);
                break;
            case 'WTD': {
                const now = new Date();
                const day = now.getDay(); // 0=Sun..6=Sat
                const diffToMonday = day === 0 ? 6 : day - 1;
                const monday = new Date(now);
                monday.setDate(now.getDate() - diffToMonday);
                // 6-day floor (not the shared 14-day one) — WTD spans at most 6 days by
                // definition, so the default floor would always win and hide the real range.
                return withMinWindow(monday.toISOString().slice(0, 10), 6);
            }
            case 'MTD': {
                const now = new Date();
                const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
                return withMinWindow(monthStart);
            }
            case 'QTD': {
                const now = new Date();
                const quarterStartMonth = Math.floor(now.getMonth() / 3) * 3;
                const quarterStart = `${now.getFullYear()}-${String(quarterStartMonth + 1).padStart(2, '0')}-01`;
                return withMinWindow(quarterStart);
            }
            case 'YTD': {
                const jan1 = `${new Date().getFullYear()}-01-01`;
                return withMinWindow(jan1);
            }
            case '1Y':
                d.setFullYear(d.getFullYear() - 1);
                break;
            case '2Y':
                d.setFullYear(d.getFullYear() - 2);
                break;
            case '3Y':
                d.setFullYear(d.getFullYear() - 3);
                break;
            case '5Y':
                d.setFullYear(d.getFullYear() - 5);
                break;
            case '10Y':
                d.setFullYear(d.getFullYear() - 10);
                break;
            case 'MAX':
                return 'min';
        }
        return d.toISOString().slice(0, 10);
    }

    function computeCustomStart(amount: number, granularity: Granularity): string {
        const d = new Date();
        switch (granularity) {
            case 'days':
                d.setDate(d.getDate() - amount);
                break;
            case 'weeks':
                d.setDate(d.getDate() - amount * 7);
                break;
            case 'months':
                d.setMonth(d.getMonth() - amount);
                break;
            case 'years':
                d.setFullYear(d.getFullYear() - amount);
                break;
        }
        return d.toISOString().slice(0, 10);
    }

    function monthOrder(year: number, month: number): number {
        return year * 12 + month;
    }

    // =========================================================================
    // Calendar navigation — SEMI-INDEPENDENT columns
    // =========================================================================

    function leftPrevMonth() {
        if (calLeftMonth === 0) {
            calLeftMonth = 11;
            calLeftYear--;
        } else {
            calLeftMonth--;
        }
    }

    function leftNextMonth() {
        if (calLeftMonth === 11) {
            calLeftMonth = 0;
            calLeftYear++;
        } else {
            calLeftMonth++;
        }
        if (monthOrder(calLeftYear, calLeftMonth) > monthOrder(calRightYear, calRightMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    function rightPrevMonth() {
        if (calRightMonth === 0) {
            calRightMonth = 11;
            calRightYear--;
        } else {
            calRightMonth--;
        }
        if (monthOrder(calRightYear, calRightMonth) < monthOrder(calLeftYear, calLeftMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    function rightNextMonth() {
        if (calRightMonth === 11) {
            calRightMonth = 0;
            calRightYear++;
        } else {
            calRightMonth++;
        }
    }

    function setLeftMonth(m: number) {
        calLeftMonth = m;
        if (monthOrder(calLeftYear, calLeftMonth) > monthOrder(calRightYear, calRightMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    function setLeftYear(newYear: number) {
        calLeftYear = newYear;
        if (monthOrder(calLeftYear, calLeftMonth) > monthOrder(calRightYear, calRightMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    function setRightMonth(m: number) {
        calRightMonth = m;
        if (monthOrder(calRightYear, calRightMonth) < monthOrder(calLeftYear, calLeftMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    function setRightYear(newYear: number) {
        calRightYear = newYear;
        if (monthOrder(calRightYear, calRightMonth) < monthOrder(calLeftYear, calLeftMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    // =========================================================================
    // Calendar click logic
    // =========================================================================

    function handleDayClick(iso: string) {
        if (pendingDate === null) {
            pendingDate = iso;
        } else {
            const d1 = pendingDate;
            const d2 = iso;
            const newStart = d1 <= d2 ? d1 : d2;
            const newEnd = d1 <= d2 ? d2 : d1;
            start = newStart;
            end = newEnd;
            activePreset = null;
            pendingDate = null;
            hoveredDate = null;
            calendarOpen = false;
            onchange?.(newStart, newEnd);
        }
    }

    function goToTodayLeft() {
        const now = new Date();
        calLeftYear = now.getFullYear();
        calLeftMonth = now.getMonth();
    }

    function goToTodayRight() {
        const now = new Date();
        calRightYear = now.getFullYear();
        calRightMonth = now.getMonth();
    }

    /** Whether to use single-column layout (viewport too narrow for dual) */
    let singleColumn = $state(false);

    function updatePopoverPosition() {
        if (!triggerEl) return;
        const rect = triggerEl.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const DUAL_W = 560;
        const SINGLE_W = Math.min(280, vw - 16);
        const MARGIN = 8;

        // Determine if single-column layout is needed
        singleColumn = vw < DUAL_W + MARGIN * 2;
        const popW = singleColumn ? SINGLE_W : DUAL_W;
        const popH = singleColumn ? 420 : 380;

        // Vertical: prefer below, open above if not enough space
        const spaceBelow = vh - rect.bottom - MARGIN;
        const spaceAbove = rect.top - MARGIN;
        const openAbove = spaceBelow < popH && spaceAbove > spaceBelow;
        const top = openAbove ? rect.top - popH - MARGIN : rect.bottom + MARGIN;

        // Horizontal: align to trigger left, shift left if overflows right
        let left = Math.max(MARGIN, rect.left);
        if (left + popW > vw - MARGIN) {
            left = Math.max(MARGIN, vw - popW - MARGIN);
        }

        popoverStyle = `position: fixed; top: ${top}px; left: ${left}px; width: ${popW}px; z-index: 99999;`;
    }

    function openCalendar() {
        // ...existing code for setting calLeft/calRight from start/end...
        if (start) {
            const [sy, sm] = start.split('-').map(Number);
            calLeftYear = sy;
            calLeftMonth = sm - 1;
        } else {
            const now = new Date();
            calLeftYear = now.getFullYear();
            calLeftMonth = Math.max(0, now.getMonth() - 1);
        }
        if (end) {
            const [ey, em] = end.split('-').map(Number);
            calRightYear = ey;
            calRightMonth = em - 1;
        } else {
            calRightYear = calLeftYear;
            calRightMonth = calLeftMonth < 11 ? calLeftMonth + 1 : 0;
            if (calLeftMonth === 11) calRightYear++;
        }
        if (monthOrder(calLeftYear, calLeftMonth) > monthOrder(calRightYear, calRightMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
        pendingDate = null;
        hoveredDate = null;
        calendarOpen = true;
        requestAnimationFrame(updatePopoverPosition);
    }

    function closeCalendar() {
        calendarOpen = false;
        pendingDate = null;
        hoveredDate = null;
    }

    // Note: No scroll listener needed — popover uses position:fixed,
    // so page scroll doesn't cause misalignment.
    // However, when embedded inside another fixed popover that repositions
    // on scroll (e.g., DataTableColumnFilter), the trigger moves and we need
    // to follow it. Reposition on scroll, close if trigger exits viewport.
    $effect(() => {
        if (!calendarOpen || !triggerEl) return;
        const handleScroll = () => {
            const rect = triggerEl!.getBoundingClientRect();
            if (rect.bottom < 0 || rect.top > window.innerHeight) {
                closeCalendar();
            } else {
                updatePopoverPosition();
            }
        };
        window.addEventListener('scroll', handleScroll, true);
        return () => window.removeEventListener('scroll', handleScroll, true);
    });

    // Ref for the custom edit container to detect click-outside reliably
    let customEditRef: HTMLDivElement | null = $state(null);

    // =========================================================================
    // JS-measured "jolly" fill badges (align='start' toolbar mode only)
    // =========================================================================
    // Two independent pools of extra badges fill LEFTOVER horizontal space instead of ever
    // causing an extra line wrap — durationFillPresets (3Y/5Y/10Y) belong to Row 1 (core
    // presets), periodFillPresets (WTD/MTD/QTD) belong to Row 2 (YTD/Tutti/Personalizzato).
    // JS decides ONLY (a) how many jolly badges of each pool to show and (b) whether everything
    // fits on ONE row or needs to split into TWO — the template then renders either a single
    // flat flex-wrap row (all badges as direct siblings) or two separate full-width rows
    // (stacked), each with native CSS `justify-between` doing the actual spreading. This avoids
    // ever computing pixel-perfect spacing in JS: with badges always siblings in a real
    // flex-wrap context (never just 2 fixed blocks), `justify-between` naturally distributes
    // leftover space across every gap instead of dumping it all into one seam (Round 5b bug) or
    // leaving it as unfilled trailing margin (Round 5b's fixed-gap-1 regression).
    let presetRowRef: HTMLDivElement | null = $state(null);
    let coreBadgeRefs: (HTMLButtonElement | null)[] = $state([]);
    let trailingBadgeRefs: (HTMLButtonElement | null)[] = $state([]); // YTD, Tutti (2 items)
    let customPlainBtnRef: HTMLButtonElement | null = $state(null); // "Personalizzato" button (not editing)
    // Hidden (position:absolute; visibility:hidden — never in normal flow), always rendered
    // with all 6 possible jolly badges so their REAL widths can be measured — replaces an
    // earlier proxy-estimate approach ("reuse 2Y/YTD width + fudge factor") that Playwright
    // testing proved inaccurate enough to cause visible overflow/wrap once actually rendered.
    let durationMeasureRefs: (HTMLButtonElement | null)[] = $state([]);
    let periodMeasureRefs: (HTMLButtonElement | null)[] = $state([]);

    let isSingleRow = $derived(!layoutMode || layoutMode === 'oneRow');
    // Round 10.1: the picker's own max-width cap is different for 1-row vs 2-row — a single
    // shared cap looked fine on 1 row but made 2-row layouts look stretched/empty (each row much
    // wider than its own content, huge justify-between gaps). Switches automatically whenever
    // `isSingleRow` flips (e.g. crossing the `oneRow` PageToolbar threshold), no extra wiring
    // needed — the existing ResizeObserver on presetRowRef picks up the new width on its own.
    let effectiveMaxWidth = $derived(isSingleRow ? pickerConfig.maxWidth : pickerConfig.maxWidthTwoRow);
    // Mirror onto the optional bindable prop — same one-way-export pattern as PageToolbar's
    // layoutMode/isStacked/showActionLabels (see PageToolbar.svelte). Lets a page apply this
    // EXACT value to its own "Center" content so both stay pixel-aligned, including live.
    $effect(() => {
        effectiveMaxWidthOut = effectiveMaxWidth;
    });
    let extrasToShowDuration = $state(0);
    let extrasToShowPeriod = $state(0);

    const JOLLY_GAP_PX = 4; // matches gap-1 (0.25rem) used on every row

    function sumWidths(widths: number[]): number {
        return widths.reduce((sum, w) => sum + w, 0) + JOLLY_GAP_PX * Math.max(0, widths.length - 1);
    }

    // Greedy fill: every additional item (whichever pool) costs its own width + exactly one new
    // gap, uniformly — true regardless of how many are already shown, since each is just one
    // more direct sibling in a real flex row (unlike Round 5b's fixed-2-block structure, where
    // the very first jolly didn't need its own connecting gap).
    function greedyFillCount(budget: number, widths: number[]): number {
        let used = 0;
        let count = 0;
        for (const w of widths) {
            const cost = w + JOLLY_GAP_PX;
            if (used + cost > budget) break;
            used += cost;
            count++;
        }
        return count;
    }

    // Shared-budget variant for the single-row case: both pools contribute a candidate per round
    // while it still fits, naturally interleaving rather than exhausting one pool before the other.
    function greedyFillShared(budget: number, poolA: number[], poolB: number[]): {a: number; b: number} {
        let a = 0;
        let b = 0;
        let remaining = budget;
        let addedSomething = true;
        while (addedSomething && (a < poolA.length || b < poolB.length)) {
            addedSomething = false;
            if (a < poolA.length) {
                const cost = poolA[a] + JOLLY_GAP_PX;
                if (cost <= remaining) {
                    remaining -= cost;
                    a++;
                    addedSomething = true;
                }
            }
            if (b < poolB.length) {
                const cost = poolB[b] + JOLLY_GAP_PX;
                if (cost <= remaining) {
                    remaining -= cost;
                    b++;
                    addedSomething = true;
                }
            }
        }
        return {a, b};
    }

    // Single synchronous pass — no async/tick() needed for the jolly-fill count. A badge's width
    // is intrinsic (its own text + padding), unaffected by which row/block wraps it, so both
    // jolly counts can be decided correctly in one shot from the CURRENT measurements in the
    // vast majority of cases. A separate, narrowly-scoped verify+shed pass below (see
    // verifyNoWrap) catches the rare cases where a small measurement margin makes the COUNT
    // (not the row split — that's fixed by `isSingleRow`/`layoutMode`, see below) wrong.
    //
    // Round 10: `isSingleRow` is no longer decided here from a width-fit computation — it's a
    // direct, deterministic function of the externally-provided `layoutMode` prop (see its
    // $derived declaration above), driven by the page's own `oneRow` PageToolbar threshold. This
    // was a deliberate architecture change (explicit user request): thresholds should have full
    // control over the whole row, not an autonomous content-measurement decision. Only the JOLLY
    // COUNT within whichever row-count is already fixed still comes from real measurement.
    //
    // Bounded-retry note: `layoutMode` changing swaps the {#if}/{:else} DOM branch (Svelte
    // destroys the old row structure and creates the new one), which changes presetRowRef's
    // OWN height (1 line ↔ 2 lines) — that alone re-fires the ResizeObserver almost
    // immediately. If THAT follow-up run reads coreBadgeRefs/trailingBadgeRefs before Svelte
    // has finished re-assigning bind:this to the freshly-created elements, it sees stale
    // (detached, 0-width) refs. Silently giving up in that case froze the layout forever at a
    // stale decision (confirmed via Playwright: fx page got stuck in an incorrectly-narrow
    // 2-row split even at 1400px, because every recompute attempt kept hitting this exact
    // zero-width guard and bailing without ever retrying) — so a zero-width read now retries
    // via requestAnimationFrame (bounded attempts) instead of abandoning the update entirely.
    let measureRetryCount = 0;
    const MAX_MEASURE_RETRIES = 5;

    // Bumped every time measureAndFill reaches a tentative decision — lets a verifyNoWrap()
    // chain detect it's been superseded by a newer recompute (e.g. another resize came in while
    // it was still awaiting a tick()) and bail out instead of shedding against stale state.
    let measureGeneration = 0;

    function measureAndFill() {
        if (align !== 'start' || !presetRowRef) return;
        const availableWidth = presetRowRef.getBoundingClientRect().width;

        const coreWidths = coreBadgeRefs.map((el) => el?.getBoundingClientRect().width ?? 0);
        const trailingWidths = trailingBadgeRefs.map((el) => el?.getBoundingClientRect().width ?? 0);
        const customWidth = (customEditing ? customEditRef : customPlainBtnRef)?.getBoundingClientRect().width ?? 0;
        const durationWidths = durationMeasureRefs.map((el) => el?.getBoundingClientRect().width ?? 0);
        const periodWidths = periodMeasureRefs.map((el) => el?.getBoundingClientRect().width ?? 0);

        const notReady = !availableWidth || coreWidths.some((w) => w === 0) || trailingWidths.some((w) => w === 0) || customWidth === 0 || durationWidths.some((w) => w === 0) || periodWidths.some((w) => w === 0);
        if (notReady) {
            if (measureRetryCount < MAX_MEASURE_RETRIES) {
                measureRetryCount++;
                requestAnimationFrame(() => measureAndFill());
            }
            return;
        }
        measureRetryCount = 0;

        // Baseline: core + trailing + custom rendered flat, adjacent, zero jollies — gaps
        // between EVERY pair (not a single fixed gap at one seam).
        const coreBaseWidth = sumWidths(coreWidths);
        const trailingBaseWidth = sumWidths([...trailingWidths, customWidth]);

        if (isSingleRow) {
            const baseWidth = coreBaseWidth + JOLLY_GAP_PX + trailingBaseWidth;
            const {a, b} = greedyFillShared(availableWidth - baseWidth, durationWidths, periodWidths);
            extrasToShowDuration = a;
            extrasToShowPeriod = b;
        } else {
            extrasToShowDuration = greedyFillCount(availableWidth - coreBaseWidth, durationWidths);
            extrasToShowPeriod = greedyFillCount(availableWidth - trailingBaseWidth, periodWidths);
        }

        measureGeneration++;
        void verifyNoWrap(measureGeneration);
    }

    // =========================================================================
    // Verify + shed — catches the rare case where the jolly-count math above is wrong
    // =========================================================================
    // Reported bug (confirmed via user report, Round 8): the picker rendered correctly at
    // first, then broke after a window resize and STAYED broken (never self-corrected on
    // further resizes). Root cause at the time: the greedy-fill math used REAL measured widths
    // (not estimates), but a small margin — e.g. the hidden measurement clone's minimal classes
    // vs the real badge's full class list, or JOLLY_GAP_PX=4 not exactly matching gap-1's real
    // computed pixel value — could still make it overestimate by one badge at some widths.
    //
    // Since Round 10, `isSingleRow` itself can no longer be "wrong" (it's a direct function of
    // `layoutMode`, not a measurement) — but the JOLLY COUNT within a given, already-fixed row
    // can still be off by one from the same measurement-margin issue, which is what this verify
    // pass continues to guard against: after Svelte commits the tentative decision to the DOM
    // (tick()), verify it actually rendered without an unwanted wrap — group each row's badges
    // by their shared direct parent and check they all share the same rendered `top`. If not,
    // shed the most-recently-relevant jolly badge and re-verify, bounded to the max possible
    // extras (3 duration + 3 period = 6) so this can never loop forever. Runs on EVERY recompute
    // (not just the first), so it also self-heals rather than getting stuck.
    function anyRowWrapped(container: HTMLElement): boolean {
        const rows = new Map<Element, HTMLElement[]>();
        for (const btn of container.querySelectorAll('button')) {
            const parent = btn.parentElement;
            if (!parent) continue;
            const group = rows.get(parent) ?? [];
            group.push(btn as HTMLElement);
            rows.set(parent, group);
        }
        for (const group of rows.values()) {
            if (group.length < 2) continue; // a lone badge can't "wrap" against itself
            const firstTop = group[0].getBoundingClientRect().top;
            if (group.some((b) => Math.abs(b.getBoundingClientRect().top - firstTop) > 1)) return true;
        }
        return false;
    }

    // Sheds one jolly from whichever pool currently shows more (balances the 2 pools instead of
    // fully draining one before touching the other); ties prefer duration. Returns false once
    // both pools are already at 0 (nothing left to shed — accept the wrap as a last resort).
    function shedOneJolly(): boolean {
        if (extrasToShowDuration === 0 && extrasToShowPeriod === 0) return false;
        if (extrasToShowDuration >= extrasToShowPeriod) {
            extrasToShowDuration--;
        } else {
            extrasToShowPeriod--;
        }
        return true;
    }

    async function verifyNoWrap(generation: number, attemptsLeft = 6) {
        await tick();
        if (generation !== measureGeneration) return; // superseded by a newer measureAndFill() run
        if (align !== 'start' || !presetRowRef) return;
        if (!anyRowWrapped(presetRowRef)) return; // verified — genuinely fits on one line each
        if (attemptsLeft <= 0) return; // safety valve — never loop forever
        if (!shedOneJolly()) return; // nothing left to shed
        await verifyNoWrap(generation, attemptsLeft - 1);
    }

    // Debounced re-measure on container resize — a live window drag fires the native resize
    // event continuously (many times/second), and re-measuring on every single one caused a
    // visible slowdown. Only the LAST event in a burst (~100ms of quiet) actually triggers a
    // recompute; ResizeObserver's own guaranteed initial callback still covers first mount.
    let resizeDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    function scheduleMeasure() {
        if (resizeDebounceTimer) clearTimeout(resizeDebounceTimer);
        resizeDebounceTimer = setTimeout(() => {
            resizeDebounceTimer = null;
            measureRetryCount = 0; // fresh retry budget for this new trigger
            measureAndFill();
        }, 100);
    }

    $effect(() => {
        if (align !== 'start' || !presetRowRef) return;
        const ro = new ResizeObserver(() => scheduleMeasure());
        ro.observe(presetRowRef);
        return () => {
            ro.disconnect();
            if (resizeDebounceTimer) clearTimeout(resizeDebounceTimer);
        };
    });

    // Re-measure when Row 2's base content changes width for reasons the row's OWN size doesn't
    // reflect: toggling the custom-window editor, a locale switch resizing translated labels
    // (Tutti/Personalizzato), or the externally-provided `layoutMode` changing (Round 10 — e.g.
    // a live console threshold edit crossing the `oneRow` boundary, with no resize event at
    // all). Discrete, infrequent events — no debounce needed, immediate via rAF.
    $effect(() => {
        if (align !== 'start' || !presetRowRef) return;
        void customEditing;
        void $_('common.custom');
        void $_('datePicker.presets.max');
        void layoutMode;
        const raf = requestAnimationFrame(() => {
            measureRetryCount = 0; // fresh retry budget for this new trigger
            measureAndFill();
        });
        return () => cancelAnimationFrame(raf);
    });

    function handleClickOutside(e: MouseEvent) {
        const target = e.target as HTMLElement;
        // If the target was detached from DOM (e.g., SimpleSelect dropdown option removed
        // on mousedown before the click event), skip — don't close customEditing
        if (!target.isConnected) return;
        if (!target.closest('.drp-popover') && !target.closest('.drp-trigger')) {
            closeCalendar();
            customEditing = false;
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') {
            if (calendarOpen) closeCalendar();
            if (customEditing) customEditing = false;
        }
    }

    // =========================================================================
    // Handlers
    // =========================================================================

    function handlePresetClick(preset: QuickPreset) {
        activePreset = preset;
        customEditing = false;
        if (preset === 'MAX') {
            start = 'min';
            end = 'max';
            onchange?.('min', 'max');
        } else {
            const newStart = computeStartDate(preset);
            const newEnd = todayISO();
            start = newStart;
            end = newEnd;
            onchange?.(newStart, newEnd);
        }
    }

    function handleCustomApply() {
        activePreset = 'custom';
        const newStart = computeCustomStart(customAmount, customGranularity);
        const newEnd = todayISO();
        start = newStart;
        end = newEnd;
        onchange?.(newStart, newEnd);
    }

    function toggleCustomEdit(e?: MouseEvent) {
        e?.stopPropagation();
        customEditing = !customEditing;
        // Apply immediately when opening (so the initial values take effect)
        if (customEditing) {
            handleCustomApply();
        }
    }

    // Auto-apply custom window when amount or granularity ACTUALLY change (not on every render).
    // We use a plain object (not $state) to track previous values — avoids infinite loops.
    const _prev = {amt: 3, gran: 'years' as Granularity};
    $effect(() => {
        const amt = customAmount;
        const gran = customGranularity;
        if (customEditing && amt > 0 && (amt !== _prev.amt || gran !== _prev.gran)) {
            _prev.amt = amt;
            _prev.gran = gran;
            // Break synchronous effect chain to avoid re-entrance
            queueMicrotask(() => handleCustomApply());
        }
    });

    function handleGranularityChange(v: string) {
        customGranularity = v as Granularity;
    }

    function displayDate(iso: string): string {
        if (!iso) return '—';
        // "min" is the MAX/"All" sentinel, pending resolution to a concrete date
        // by the controller (once the real earliest date is known from backend data).
        if (iso === 'min') return $_('datePicker.resolvingStart');
        // "max" should never persist (controllers resolve it to today immediately),
        // kept only as a defensive fallback.
        if (iso === 'max') return displayDate(todayISO());
        if (compact) return iso; // YYYY-MM-DD — fits narrow cells
        const d = new Date(iso + 'T00:00:00');
        return d.toLocaleDateString('en', {day: '2-digit', month: 'short', year: 'numeric'});
    }

    /** Highlights object for CalendarMonth instances */
    let calHighlights: CalendarHighlights = $derived({
        rangeStart: start === 'min' ? undefined : start || undefined,
        rangeEnd: end === 'max' ? undefined : end || undefined,
        pending: pendingDate ?? undefined,
        hovered: hoveredDate ?? undefined,
    });

    /** Svelte action: portal — moves node to document.body (escapes stacking contexts) */
    function portalAction(node: HTMLElement) {
        document.body.appendChild(node);
        return {
            destroy() {
                if (node.parentElement === document.body) node.remove();
            },
        };
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown} />

{#snippet coreButtons()}
    {#each presets.slice(0, 6) as preset, i}
        <button
            type="button"
            bind:this={coreBadgeRefs[i]}
            class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                {effectivePreset === preset.key ? 'bg-libre-green text-white shadow-sm' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
            onclick={() => handlePresetClick(preset.key)}>{preset.label}</button
        >
    {/each}
{/snippet}

{#snippet durationJollyButtons()}
    <!-- Duration pool (3Y/5Y/10Y) — JS-measured, never a fixed CSS breakpoint set. Fills
         leftover space in Block A only up to how many actually fit (see measureAndFill). -->
    {#each durationFillPresets.slice(0, extrasToShowDuration) as preset}
        <button
            type="button"
            class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                {effectivePreset === preset.key ? 'bg-libre-green text-white shadow-sm' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
            onclick={() => handlePresetClick(preset.key)}>{preset.label}</button
        >
    {/each}
{/snippet}

{#snippet periodJollyButtons()}
    <!-- Period pool (WTD/MTD/QTD) — same idea as durationJollyButtons but for Block B. -->
    {#each periodFillPresets.slice(0, extrasToShowPeriod) as preset}
        <button
            type="button"
            class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                {effectivePreset === preset.key ? 'bg-libre-green text-white shadow-sm' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
            onclick={() => handlePresetClick(preset.key)}>{preset.label}</button
        >
    {/each}
{/snippet}

{#snippet trailingButtons()}
    {#each presets.slice(6) as preset, i}
        <button
            type="button"
            bind:this={trailingBadgeRefs[i]}
            class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                {effectivePreset === preset.key ? 'bg-libre-green text-white shadow-sm' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
            onclick={() => handlePresetClick(preset.key)}>{preset.label}</button
        >
    {/each}
{/snippet}

{#snippet customWindowArea()}
    {#if showCustomWindow}
        {#if customEditing}
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <div
                bind:this={customEditRef}
                class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-500/10 dark:bg-amber-500/20 rounded-lg border border-amber-400/40 drp-trigger"
                role="group"
                onclick={(e) => e.stopPropagation()}
                onkeydown={(e) => {
                    if (e.key === 'Escape') customEditing = false;
                }}
            >
                <input
                    type="number"
                    bind:value={customAmount}
                    min="1"
                    max="999"
                    class="w-8 px-0.5 py-0.5 text-xs text-center border-none bg-transparent text-amber-700 dark:text-amber-300 focus:ring-0 focus:outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                <SimpleSelect value={customGranularity} options={granularitySelectOptions} onchange={handleGranularityChange} class="inline-block w-auto" dropdownPosition="auto" compact showChevron={false} />
            </div>
        {:else}
            <button
                type="button"
                bind:this={customPlainBtnRef}
                class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                    {effectivePreset === 'custom' ? 'bg-amber-500 text-white shadow-sm' : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
                onclick={(e) => toggleCustomEdit(e)}>{effectivePreset === 'custom' ? `${customAmount}${$_(granularityOptions.find((o) => o.value === customGranularity)?.shortKey ?? 'common.custom').toUpperCase()}` : $_('common.custom')}</button
            >
        {/if}
    {/if}
{/snippet}

<div class="relative flex flex-col gap-1.5 {align === 'start' ? 'grow self-stretch items-stretch' : 'items-center'}" style={align === 'start' ? `max-width: ${effectiveMaxWidth}px` : ''}>
    {#if showPresets}
        <!-- align='start': JS decides ONLY isSingleRow + jolly counts (see measureAndFill) —
             the actual spreading/"giustificato" look is native CSS justify-between, applied to
             whichever real structure is rendered below. Never a fixed gap AND never a
             justify-between with just 2 fake "block" children (both tried and rejected in
             earlier rounds — see history above). -->
        <div bind:this={presetRowRef} class={align === 'start' ? 'w-full' : 'flex items-center gap-1 flex-wrap justify-center'}>
            {#if align === 'start'}
                {#if isSingleRow}
                    <!-- Single row: ALL badges are direct siblings in ONE flex-wrap row — CSS
                         justify-between distributes any leftover space across every gap between
                         them, never concentrated in one seam, and genuinely spans the full
                         available width. -->
                    <div class="flex items-center gap-1 flex-wrap w-full justify-between">
                        {@render coreButtons()}
                        {@render durationJollyButtons()}
                        {@render periodJollyButtons()}
                        {@render trailingButtons()}
                        {@render customWindowArea()}
                    </div>
                {:else}
                    <!-- Two rows: each is its OWN full-width flex-wrap row with its OWN
                         justify-between — row 1 (core+duration jolly) and row 2 (period
                         jolly+trailing+custom) each spread independently across the same full
                         width, filled only from their own pool (see measureAndFill). -->
                    <div class="flex flex-col gap-1.5">
                        <div class="flex items-center gap-1 flex-wrap w-full justify-between">
                            {@render coreButtons()}
                            {@render durationJollyButtons()}
                        </div>
                        <div class="flex items-center gap-1 flex-wrap w-full justify-between">
                            {@render periodJollyButtons()}
                            {@render trailingButtons()}
                            {@render customWindowArea()}
                        </div>
                    </div>
                {/if}
            {:else}
                {@render coreButtons()}
                <span class="inline-flex items-center gap-1">
                    {@render trailingButtons()}
                    {@render customWindowArea()}
                </span>
            {/if}
        </div>
    {/if}

    {#if align === 'start'}
        <!-- Hidden measurement-only clone of all 6 jolly badges — position:absolute +
             invisible keeps it OUT of normal flow/paint entirely, purely so measureAndFill()
             can read their REAL widths (not a guessed proxy). aria-hidden since it's never
             meant to be seen or interacted with. -->
        <div class="absolute invisible pointer-events-none" style="top: 0; left: 0;" aria-hidden="true">
            {#each durationFillPresets as preset, i}
                <button type="button" bind:this={durationMeasureRefs[i]} class="px-2.5 py-1 text-xs font-medium rounded-lg" tabindex="-1">{preset.label}</button>
            {/each}
            {#each periodFillPresets as preset, i}
                <button type="button" bind:this={periodMeasureRefs[i]} class="px-2.5 py-1 text-xs font-medium rounded-lg" tabindex="-1">{preset.label}</button>
            {/each}
        </div>
    {/if}

    {#if showDateFields}
        <div class="relative drp-trigger w-full">
            <button
                bind:this={triggerEl}
                type="button"
                class="w-full flex {stacked ? 'flex-col' : ''} items-center gap-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 overflow-hidden cursor-pointer hover:border-libre-green/50 transition-colors {compact ? '' : 'shadow-sm'} {calendarOpen
                    ? 'ring-1 ring-libre-green border-libre-green'
                    : ''}"
                onclick={openCalendar}
            >
                <span class="{stacked ? 'w-full' : 'flex-1'} flex items-center gap-1 whitespace-nowrap overflow-hidden {compact ? 'px-1.5 py-1' : 'px-3 py-2'}">
                    <Calendar size={compact ? 11 : 14} class="text-libre-green flex-shrink-0" />
                    <span class="text-[9px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">{$_('datePicker.from')}</span>
                    <span class="font-mono {compact ? 'text-[10px]' : 'text-xs'} text-gray-700 dark:text-gray-200 truncate">{displayDate(start)}</span>
                </span>
                {#if stacked}
                    <span class="block w-full h-px bg-gray-200 dark:bg-slate-600 flex-shrink-0"></span>
                {:else}
                    <span class="block w-px h-6 bg-gray-200 dark:bg-slate-600 flex-shrink-0"></span>
                {/if}
                <span class="{stacked ? 'w-full' : 'flex-1'} flex items-center gap-1 whitespace-nowrap overflow-hidden {compact ? 'px-1.5 py-1' : 'px-3 py-2'}">
                    <Calendar size={compact ? 11 : 14} class="text-libre-green flex-shrink-0" />
                    <span class="text-[9px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">{$_('datePicker.to')}</span>
                    <span class="font-mono {compact ? 'text-[10px]' : 'text-xs'} text-gray-700 dark:text-gray-200 truncate">{displayDate(end)}</span>
                </span>
            </button>

            {#if calendarOpen}
                {#if usePortal}
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div use:portalAction>
                        <div class="fixed inset-0" style="z-index:99998;" onclick={closeCalendar}></div>
                        <div class="drp-popover bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-600 p-4" style={popoverStyle}>
                            <div class="flex {singleColumn ? 'flex-col' : 'flex-row'} gap-4 justify-center">
                                <CalendarMonth
                                    year={calLeftYear}
                                    month={calLeftMonth}
                                    {weekdayLabels}
                                    {monthLabels}
                                    onDayClick={handleDayClick}
                                    onDayHover={(iso) => {
                                        if (pendingDate) hoveredDate = iso;
                                    }}
                                    onPrevMonth={leftPrevMonth}
                                    onNextMonth={leftNextMonth}
                                    onSetMonth={setLeftMonth}
                                    onSetYear={setLeftYear}
                                    onGoToToday={goToTodayLeft}
                                    highlights={calHighlights}
                                    {allowFuture}
                                />
                                <div class="{singleColumn ? 'hidden' : 'block'} w-px bg-gray-200 dark:bg-slate-600 self-stretch"></div>
                                <CalendarMonth
                                    year={calRightYear}
                                    month={calRightMonth}
                                    {weekdayLabels}
                                    {monthLabels}
                                    onDayClick={handleDayClick}
                                    onDayHover={(iso) => {
                                        if (pendingDate) hoveredDate = iso;
                                    }}
                                    onPrevMonth={rightPrevMonth}
                                    onNextMonth={rightNextMonth}
                                    onSetMonth={setRightMonth}
                                    onSetYear={setRightYear}
                                    onGoToToday={goToTodayRight}
                                    highlights={calHighlights}
                                    {allowFuture}
                                />
                            </div>
                            {#if pendingDate}
                                <div class="mt-3 text-xs text-center text-gray-400 dark:text-gray-500">
                                    {$_('datePicker.selectSecondDate')}
                                </div>
                            {/if}
                        </div>
                    </div>
                {:else}
                    <div class="drp-popover bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-600 p-4" style={popoverStyle}>
                        <div class="flex {singleColumn ? 'flex-col' : 'flex-row'} gap-4 justify-center">
                            <CalendarMonth
                                year={calLeftYear}
                                month={calLeftMonth}
                                {weekdayLabels}
                                {monthLabels}
                                onDayClick={handleDayClick}
                                onDayHover={(iso) => {
                                    if (pendingDate) hoveredDate = iso;
                                }}
                                onPrevMonth={leftPrevMonth}
                                onNextMonth={leftNextMonth}
                                onSetMonth={setLeftMonth}
                                onSetYear={setLeftYear}
                                onGoToToday={goToTodayLeft}
                                highlights={calHighlights}
                                {allowFuture}
                            />
                            <div class="{singleColumn ? 'hidden' : 'block'} w-px bg-gray-200 dark:bg-slate-600 self-stretch"></div>
                            <CalendarMonth
                                year={calRightYear}
                                month={calRightMonth}
                                {weekdayLabels}
                                {monthLabels}
                                onDayClick={handleDayClick}
                                onDayHover={(iso) => {
                                    if (pendingDate) hoveredDate = iso;
                                }}
                                onPrevMonth={rightPrevMonth}
                                onNextMonth={rightNextMonth}
                                onSetMonth={setRightMonth}
                                onSetYear={setRightYear}
                                onGoToToday={goToTodayRight}
                                highlights={calHighlights}
                                {allowFuture}
                            />
                        </div>
                        {#if pendingDate}
                            <div class="mt-3 text-xs text-center text-gray-400 dark:text-gray-500">
                                {$_('datePicker.selectSecondDate')}
                            </div>
                        {/if}
                    </div>
                {/if}
            {/if}
        </div>
    {/if}
</div>
