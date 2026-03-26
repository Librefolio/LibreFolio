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
    import {Calendar, Info} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import type {CalendarHighlights} from './CalendarMonth.svelte';
    import CalendarMonth from './CalendarMonth.svelte';
    import {SimpleSelect} from '$lib/components/ui/select';

    // =========================================================================
    // Types
    // =========================================================================

    export type QuickPreset = '1W' | '1M' | '3M' | '6M' | '1Y' | '2Y';
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
        onchange,
    }: Props = $props();

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
    let triggerEl = $state<HTMLButtonElement | null>(null);
    let popoverStyle = $state('');

    // Semi-independent left/right month+year
    let calLeftYear = $state(new Date().getFullYear());
    let calLeftMonth = $state(new Date().getMonth());
    let calRightYear = $state(new Date().getFullYear());
    let calRightMonth = $state(new Date().getMonth());

    // =========================================================================
    // i18n Weekdays and Months
    // =========================================================================

    const WEEKDAY_KEYS = [
        'datePicker.weekdays.mo',
        'datePicker.weekdays.tu',
        'datePicker.weekdays.we',
        'datePicker.weekdays.th',
        'datePicker.weekdays.fr',
        'datePicker.weekdays.sa',
        'datePicker.weekdays.su',
    ];

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
    let weekdayLabels: string[] = $derived(WEEKDAY_KEYS.map(k => $_(k)));
    let monthLabels: string[] = $derived(MONTH_KEYS.map(k => $_(k)));

    // =========================================================================
    // Preset Definitions
    // =========================================================================

    const presets: { key: QuickPreset; label: string; months?: number; weeks?: number; years?: number }[] = [
        {key: '1W', label: '1W', weeks: 1},
        {key: '1M', label: '1M', months: 1},
        {key: '3M', label: '3M', months: 3},
        {key: '6M', label: '6M', months: 6},
        {key: '1Y', label: '1Y', years: 1},
        {key: '2Y', label: '2Y', years: 2},
    ];

    const granularityOptions: { value: Granularity; labelKey: string; shortKey: string }[] = [
        {value: 'days', labelKey: 'datePicker.granularity.days', shortKey: 'datePicker.granularity.daysShort'},
        {value: 'weeks', labelKey: 'datePicker.granularity.weeks', shortKey: 'datePicker.granularity.weeksShort'},
        {value: 'months', labelKey: 'datePicker.granularity.months', shortKey: 'datePicker.granularity.monthsShort'},
        {value: 'years', labelKey: 'datePicker.granularity.years', shortKey: 'datePicker.granularity.yearsShort'},
    ];

    // Granularity short options for the compact native select (must be after granularityOptions)
    let granularitySelectOptions = $derived(
        granularityOptions.map(o => ({value: o.value, label: $_(o.shortKey).toUpperCase()}))
    );

    // =========================================================================
    // Helpers
    // =========================================================================

    function todayISO(): string {
        return new Date().toISOString().slice(0, 10);
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
            case '1Y':
                d.setFullYear(d.getFullYear() - 1);
                break;
            case '2Y':
                d.setFullYear(d.getFullYear() - 2);
                break;
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

    function setLeftYear(y: number) {
        calLeftYear = y;
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

    function setRightYear(y: number) {
        calRightYear = y;
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

        popoverStyle = `position: fixed; top: ${top}px; left: ${left}px; width: ${popW}px; z-index: 9999;`;
    }

    function openCalendar() {
        // ...existing code for setting calLeft/calRight from start/end...
        if (start) {
            const [y, m] = start.split('-').map(Number);
            calLeftYear = y;
            calLeftMonth = m - 1;
        } else {
            const now = new Date();
            calLeftYear = now.getFullYear();
            calLeftMonth = Math.max(0, now.getMonth() - 1);
        }
        if (end) {
            const [y, m] = end.split('-').map(Number);
            calRightYear = y;
            calRightMonth = m - 1;
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

    // Close popover on scroll (position: fixed doesn't follow the trigger)
    $effect(() => {
        if (!calendarOpen) return;
        const handleScroll = () => closeCalendar();
        window.addEventListener('scroll', handleScroll, true);
        return () => window.removeEventListener('scroll', handleScroll, true);
    });

    // Ref for the custom edit container to detect click-outside reliably
    let customEditRef = $state<HTMLDivElement | null>(null);

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
        const newStart = computeStartDate(preset);
        const newEnd = todayISO();
        start = newStart;
        end = newEnd;
        onchange?.(newStart, newEnd);
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

    function displayDate(iso: string): string {
        if (!iso) return '—';
        const d = new Date(iso + 'T00:00:00');
        return d.toLocaleDateString('en', {day: '2-digit', month: 'short', year: 'numeric'});
    }

    /** Highlights object for CalendarMonth instances */
    let calHighlights: CalendarHighlights = $derived({
        rangeStart: start || undefined,
        rangeEnd: end || undefined,
        pending: pendingDate ?? undefined,
        hovered: hoveredDate ?? undefined,
    });
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown}/>

<div class="flex flex-col gap-1.5 items-center">
    {#if showPresets}
        <div class="flex items-center gap-1 flex-wrap justify-center">
            {#each presets as preset}
                <button type="button"
                        class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                        {activePreset === preset.key
                            ? 'bg-libre-green text-white shadow-sm'
                            : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
                        onclick={() => handlePresetClick(preset.key)}
                >{preset.label}</button>
            {/each}
            {#if showCustomWindow}
                {#if customEditing}
                    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                    <div bind:this={customEditRef}
                         class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-amber-500/10 dark:bg-amber-500/20 rounded-lg border border-amber-400/40 drp-trigger"
                         role="group"
                         onclick={(e) => e.stopPropagation()}
                         onkeydown={(e) => { if (e.key === 'Escape') customEditing = false; }}>
                        <input type="number" bind:value={customAmount} min="1" max="999"
                               class="w-8 px-0.5 py-0.5 text-xs text-center border-none bg-transparent text-amber-700 dark:text-amber-300 focus:ring-0 focus:outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"/>
                        <SimpleSelect
                                value={customGranularity}
                                options={granularitySelectOptions}
                                onchange={(v) => { customGranularity = v as Granularity; }}
                                class="inline-block w-auto"
                                dropdownPosition="auto"
                                compact
                                showChevron={false}
                        />
                    </div>
                {:else}
                    <button type="button"
                            class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                            {activePreset === 'custom'
                                ? 'bg-amber-500 text-white shadow-sm'
                                : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
                            onclick={(e) => toggleCustomEdit(e)}
                    >{activePreset === 'custom' ? `${customAmount}${$_(granularityOptions.find(o => o.value === customGranularity)?.shortKey ?? 'common.custom').toUpperCase()}` : $_('common.custom')}</button>
                {/if}
            {/if}
            <!-- Info tooltip -->
            <Tooltip text={$_('datePicker.info')} position="bottom" maxWidth="280px">
                <Info size={14} class="text-gray-400 dark:text-gray-500 hover:text-libre-green transition-colors"/>
            </Tooltip>
        </div>
    {/if}

    {#if showDateFields}
        <div class="relative drp-trigger w-full">
            <button
                    bind:this={triggerEl}
                    type="button"
                    class="w-full flex {stacked ? 'flex-col' : ''} items-center gap-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 overflow-hidden cursor-pointer hover:border-libre-green/50 transition-colors {compact ? '' : 'shadow-sm'} {calendarOpen ? 'ring-1 ring-libre-green border-libre-green' : ''}"
                    onclick={openCalendar}
            >
                <div class="{stacked ? 'w-full' : 'flex-1'} flex items-center gap-1.5 whitespace-nowrap {compact ? 'px-2.5 py-1.5' : 'px-3 py-2'}">
                    <Calendar size={compact ? 12 : 14} class="text-libre-green flex-shrink-0"/>
                    <span class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">{$_('datePicker.from')}</span>
                    <span class="font-mono {compact ? 'text-[11px]' : 'text-xs'} text-gray-700 dark:text-gray-200 flex-shrink-0">{displayDate(start)}</span>
                </div>
                {#if stacked}
                    <div class="w-full h-px bg-gray-200 dark:bg-slate-600 flex-shrink-0"></div>
                {:else}
                    <div class="w-px h-6 bg-gray-200 dark:bg-slate-600 flex-shrink-0"></div>
                {/if}
                <div class="{stacked ? 'w-full' : 'flex-1'} flex items-center gap-1.5 whitespace-nowrap {compact ? 'px-2.5 py-1.5' : 'px-3 py-2'}">
                    <Calendar size={compact ? 12 : 14} class="text-libre-green flex-shrink-0"/>
                    <span class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">{$_('datePicker.to')}</span>
                    <span class="font-mono {compact ? 'text-[11px]' : 'text-xs'} text-gray-700 dark:text-gray-200 flex-shrink-0">{displayDate(end)}</span>
                </div>
            </button>

            {#if calendarOpen}
                <div class="drp-popover bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-600 p-4" style={popoverStyle}>
                    <div class="flex {singleColumn ? 'flex-col' : 'flex-row'} gap-4 justify-center">
                        <!-- Left month (semi-independent) -->
                        <CalendarMonth
                                year={calLeftYear}
                                month={calLeftMonth}
                                {weekdayLabels}
                                {monthLabels}
                                onDayClick={handleDayClick}
                                onDayHover={(iso) => { if (pendingDate) hoveredDate = iso; }}
                                onPrevMonth={leftPrevMonth}
                                onNextMonth={leftNextMonth}
                                onSetMonth={setLeftMonth}
                                onSetYear={setLeftYear}
                                onGoToToday={goToTodayLeft}
                                highlights={calHighlights}
                        />
                        <div class="{singleColumn ? 'hidden' : 'block'} w-px bg-gray-200 dark:bg-slate-600 self-stretch"></div>
                        <!-- Right month (semi-independent) -->
                        <CalendarMonth
                                year={calRightYear}
                                month={calRightMonth}
                                {weekdayLabels}
                                {monthLabels}
                                onDayClick={handleDayClick}
                                onDayHover={(iso) => { if (pendingDate) hoveredDate = iso; }}
                                onPrevMonth={rightPrevMonth}
                                onNextMonth={rightNextMonth}
                                onSetMonth={setRightMonth}
                                onSetYear={setRightYear}
                                onGoToToday={goToTodayRight}
                                highlights={calHighlights}
                        />
                    </div>
                    {#if pendingDate}
                        <div class="mt-3 text-xs text-center text-gray-400 dark:text-gray-500">
                            {$_('datePicker.selectSecondDate')}
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    {/if}
</div>

