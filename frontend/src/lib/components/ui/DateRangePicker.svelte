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
    import {Calendar, CalendarCheck, ChevronLeft, ChevronRight, Info} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/Tooltip.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';

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
        onchange,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let customAmount = $state(3);
    let customGranularity: Granularity = $state('months');
    let customEditing = $state(false);

    // Calendar popover state
    let calendarOpen = $state(false);
    let pendingDate: string | null = $state(null);
    let hoveredDate: string | null = $state(null);

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

    const presets: {key: QuickPreset; label: string; months?: number; weeks?: number; years?: number}[] = [
        {key: '1W', label: '1W', weeks: 1},
        {key: '1M', label: '1M', months: 1},
        {key: '3M', label: '3M', months: 3},
        {key: '6M', label: '6M', months: 6},
        {key: '1Y', label: '1Y', years: 1},
        {key: '2Y', label: '2Y', years: 2},
    ];

    const granularityOptions: {value: Granularity; labelKey: string}[] = [
        {value: 'days', labelKey: 'datePicker.granularity.days'},
        {value: 'weeks', labelKey: 'datePicker.granularity.weeks'},
        {value: 'months', labelKey: 'datePicker.granularity.months'},
        {value: 'years', labelKey: 'datePicker.granularity.years'},
    ];

    // Granularity options as SelectOption[] for SimpleSelect (must be after granularityOptions)
    let granularitySelectOptions = $derived(
        granularityOptions.map(o => ({ value: o.value, label: $_(o.labelKey) }))
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
            case '1W': d.setDate(d.getDate() - 7); break;
            case '1M': d.setMonth(d.getMonth() - 1); break;
            case '3M': d.setMonth(d.getMonth() - 3); break;
            case '6M': d.setMonth(d.getMonth() - 6); break;
            case '1Y': d.setFullYear(d.getFullYear() - 1); break;
            case '2Y': d.setFullYear(d.getFullYear() - 2); break;
        }
        return d.toISOString().slice(0, 10);
    }

    function computeCustomStart(amount: number, granularity: Granularity): string {
        const d = new Date();
        switch (granularity) {
            case 'days': d.setDate(d.getDate() - amount); break;
            case 'weeks': d.setDate(d.getDate() - amount * 7); break;
            case 'months': d.setMonth(d.getMonth() - amount); break;
            case 'years': d.setFullYear(d.getFullYear() - amount); break;
        }
        return d.toISOString().slice(0, 10);
    }

    function formatISO(year: number, month: number, day: number): string {
        return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }

    function monthOrder(year: number, month: number): number {
        return year * 12 + month;
    }

    function getMonthGrid(year: number, month: number): Array<Array<{day: number; iso: string; inMonth: boolean}>> {
        const firstDay = new Date(year, month, 1);
        let startDow = firstDay.getDay() - 1;
        if (startDow < 0) startDow = 6;
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const prevMonthDays = new Date(year, month, 0).getDate();
        const cells: Array<{day: number; iso: string; inMonth: boolean}> = [];
        for (let i = startDow - 1; i >= 0; i--) {
            const d = prevMonthDays - i;
            const prevM = month === 0 ? 11 : month - 1;
            const prevY = month === 0 ? year - 1 : year;
            cells.push({day: d, iso: formatISO(prevY, prevM, d), inMonth: false});
        }
        for (let d = 1; d <= daysInMonth; d++) {
            cells.push({day: d, iso: formatISO(year, month, d), inMonth: true});
        }
        const remaining = 42 - cells.length;
        for (let d = 1; d <= remaining; d++) {
            const nextM = month === 11 ? 0 : month + 1;
            const nextY = month === 11 ? year + 1 : year;
            cells.push({day: d, iso: formatISO(nextY, nextM, d), inMonth: false});
        }
        const weeks: typeof cells[] = [];
        for (let i = 0; i < cells.length; i += 7) {
            weeks.push(cells.slice(i, i + 7));
        }
        return weeks;
    }

    // =========================================================================
    // Calendar navigation — SEMI-INDEPENDENT columns
    // =========================================================================

    function leftPrevMonth() {
        if (calLeftMonth === 0) { calLeftMonth = 11; calLeftYear--; }
        else { calLeftMonth--; }
    }

    function leftNextMonth() {
        if (calLeftMonth === 11) { calLeftMonth = 0; calLeftYear++; }
        else { calLeftMonth++; }
        if (monthOrder(calLeftYear, calLeftMonth) > monthOrder(calRightYear, calRightMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    function rightPrevMonth() {
        if (calRightMonth === 0) { calRightMonth = 11; calRightYear--; }
        else { calRightMonth--; }
        if (monthOrder(calRightYear, calRightMonth) < monthOrder(calLeftYear, calLeftMonth)) {
            [calLeftYear, calRightYear] = [calRightYear, calLeftYear];
            [calLeftMonth, calRightMonth] = [calRightMonth, calLeftMonth];
        }
    }

    function rightNextMonth() {
        if (calRightMonth === 11) { calRightMonth = 0; calRightYear++; }
        else { calRightMonth++; }
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

    function isInRange(iso: string): boolean {
        if (pendingDate && hoveredDate) {
            const lo = pendingDate <= hoveredDate ? pendingDate : hoveredDate;
            const hi = pendingDate <= hoveredDate ? hoveredDate : pendingDate;
            return iso >= lo && iso <= hi;
        }
        if (start && end) return iso >= start && iso <= end;
        return false;
    }

    function isRangeStart(iso: string): boolean {
        if (pendingDate && hoveredDate) return iso === (pendingDate <= hoveredDate ? pendingDate : hoveredDate);
        return iso === start;
    }

    function isRangeEnd(iso: string): boolean {
        if (pendingDate && hoveredDate) return iso === (pendingDate <= hoveredDate ? hoveredDate : pendingDate);
        return iso === end;
    }

    function isToday(iso: string): boolean { return iso === todayISO(); }

    function isFuture(iso: string): boolean { return iso > todayISO(); }

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

    function openCalendar() {
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
    }

    function closeCalendar() {
        calendarOpen = false;
        pendingDate = null;
        hoveredDate = null;
    }

    function handleClickOutside(e: MouseEvent) {
        const target = e.target as HTMLElement;
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
    const _prev = {amt: 3, gran: 'months' as Granularity};
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

    function yearOptions(): number[] {
        const currentYear = new Date().getFullYear();
        const years: number[] = [];
        for (let y = currentYear - 10; y <= currentYear + 2; y++) years.push(y);
        return years;
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown} />

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
                    <div class="flex items-center gap-1 px-2 py-0.5 bg-amber-500/10 dark:bg-amber-500/20 rounded-lg border border-amber-400/40 drp-trigger">
                        <input type="number" bind:value={customAmount} min="1" max="999"
                            class="w-10 px-1 py-0.5 text-xs text-center border-none bg-transparent text-amber-700 dark:text-amber-300 focus:ring-0 focus:outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
                        <div class="w-24">
                            <SimpleSelect
                                bind:value={customGranularity}
                                options={granularitySelectOptions}
                                class="[&_button]:!px-1.5 [&_button]:!py-0.5 [&_button]:!text-xs [&_button]:!border-none [&_button]:!bg-transparent [&_button]:!text-amber-700 dark:[&_button]:!text-amber-300 [&_button]:!rounded [&_button]:!min-h-0"
                            />
                        </div>
                    </div>
                {:else}
                    <button type="button"
                        class="px-2.5 py-1 text-xs font-medium rounded-lg transition-all duration-150
                            {activePreset === 'custom'
                                ? 'bg-amber-500 text-white shadow-sm'
                                : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'}"
                        onclick={(e) => toggleCustomEdit(e)}
                    >{activePreset === 'custom' ? `${customAmount} ${$_(granularityOptions.find(o => o.value === customGranularity)?.labelKey ?? 'datePicker.custom')}` : $_('datePicker.custom')}</button>
                {/if}
            {/if}
            <!-- Info tooltip -->
            <Tooltip text={$_('datePicker.info')} position="bottom" maxWidth="280px">
                <Info size={14} class="text-gray-400 dark:text-gray-500 hover:text-libre-green transition-colors" />
            </Tooltip>
        </div>
    {/if}

    {#if showDateFields}
    <div class="relative drp-trigger w-full">
        <button
            type="button"
            class="w-full flex items-center gap-0 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 overflow-hidden cursor-pointer hover:border-libre-green/50 transition-colors {compact ? '' : 'shadow-sm'} {calendarOpen ? 'ring-1 ring-libre-green border-libre-green' : ''}"
            onclick={openCalendar}
        >
            <div class="flex-1 flex items-center gap-1.5 whitespace-nowrap {compact ? 'px-2.5 py-1.5' : 'px-3 py-2'}">
                <Calendar size={compact ? 12 : 14} class="text-libre-green flex-shrink-0" />
                <span class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">{$_('datePicker.from')}</span>
                <span class="font-mono {compact ? 'text-[11px]' : 'text-xs'} text-gray-700 dark:text-gray-200 flex-shrink-0">{displayDate(start)}</span>
            </div>
            <div class="w-px h-6 bg-gray-200 dark:bg-slate-600 flex-shrink-0"></div>
            <div class="flex-1 flex items-center gap-1.5 whitespace-nowrap {compact ? 'px-2.5 py-1.5' : 'px-3 py-2'}">
                <Calendar size={compact ? 12 : 14} class="text-libre-green flex-shrink-0" />
                <span class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">{$_('datePicker.to')}</span>
                <span class="font-mono {compact ? 'text-[11px]' : 'text-xs'} text-gray-700 dark:text-gray-200 flex-shrink-0">{displayDate(end)}</span>
            </div>
        </button>

        {#if calendarOpen}
            <div class="drp-popover absolute z-50 top-full mt-2 left-0 bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-600 p-4">
                <div class="flex flex-wrap gap-4 justify-center">
                    <!-- Left month (semi-independent) -->
                    <div class="min-w-[240px] flex-1">
                        <div class="flex items-center justify-between mb-2">
                            <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400" onclick={leftPrevMonth}>
                                <ChevronLeft size={16} />
                            </button>
                            <div class="flex items-center gap-1">
                                <select
                                    class="text-sm font-semibold text-gray-700 dark:text-gray-200 bg-transparent border-none focus:ring-0 focus:outline-none cursor-pointer px-0 py-0"
                                    value={calLeftMonth}
                                    onchange={(e) => setLeftMonth(parseInt((e.target as HTMLSelectElement).value))}
                                >
                                    {#each Array(12) as _, i}
                                        <option value={i}>{monthLabels[i]}</option>
                                    {/each}
                                </select>
                                <select
                                    class="text-sm font-semibold text-gray-700 dark:text-gray-200 bg-transparent border-none focus:ring-0 focus:outline-none cursor-pointer px-0 py-0"
                                    value={calLeftYear}
                                    onchange={(e) => setLeftYear(parseInt((e.target as HTMLSelectElement).value))}
                                >
                                    {#each yearOptions() as y}
                                        <option value={y}>{y}</option>
                                    {/each}
                                </select>
                            </div>
                            <div class="flex items-center gap-0.5">
                                <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 dark:text-gray-500" title={$_('datePicker.today')} onclick={goToTodayLeft}>
                                    <CalendarCheck size={14} />
                                </button>
                                <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400" onclick={leftNextMonth}>
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        </div>
                        {@render monthGridSnippet(calLeftYear, calLeftMonth)}
                    </div>
                    <div class="hidden sm:block w-px bg-gray-200 dark:bg-slate-600 self-stretch"></div>
                    <!-- Right month (semi-independent) -->
                    <div class="min-w-[240px] flex-1">
                        <div class="flex items-center justify-between mb-2">
                            <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400" onclick={rightPrevMonth}>
                                <ChevronLeft size={16} />
                            </button>
                            <div class="flex items-center gap-1">
                                <select
                                    class="text-sm font-semibold text-gray-700 dark:text-gray-200 bg-transparent border-none focus:ring-0 focus:outline-none cursor-pointer px-0 py-0"
                                    value={calRightMonth}
                                    onchange={(e) => setRightMonth(parseInt((e.target as HTMLSelectElement).value))}
                                >
                                    {#each Array(12) as _, i}
                                        <option value={i}>{monthLabels[i]}</option>
                                    {/each}
                                </select>
                                <select
                                    class="text-sm font-semibold text-gray-700 dark:text-gray-200 bg-transparent border-none focus:ring-0 focus:outline-none cursor-pointer px-0 py-0"
                                    value={calRightYear}
                                    onchange={(e) => setRightYear(parseInt((e.target as HTMLSelectElement).value))}
                                >
                                    {#each yearOptions() as y}
                                        <option value={y}>{y}</option>
                                    {/each}
                                </select>
                            </div>
                            <div class="flex items-center gap-0.5">
                                <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 dark:text-gray-500" title={$_('datePicker.today')} onclick={goToTodayRight}>
                                    <CalendarCheck size={14} />
                                </button>
                                <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400" onclick={rightNextMonth}>
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        </div>
                        {@render monthGridSnippet(calRightYear, calRightMonth)}
                    </div>
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

{#snippet monthGridSnippet(year: number, month: number)}
    <table class="w-full table-fixed">
        <thead>
            <tr>
                {#each weekdayLabels as wdLabel}<th class="text-center text-[10px] font-semibold text-gray-500 dark:text-gray-400 pb-1 w-[14.28%]">{wdLabel}</th>{/each}
            </tr>
        </thead>
        <tbody>
            {#each getMonthGrid(year, month) as week}
                <tr>
                    {#each week as cell}
                        {@const future = isFuture(cell.iso)}
                        {@const outOfMonth = !cell.inMonth}
                        <td class="text-center p-0"
                            onmouseenter={() => { if (pendingDate) hoveredDate = cell.iso; }}>
                            <button type="button"
                                class="w-full aspect-square text-xs leading-none rounded-md transition-colors
                                    {future && outOfMonth
                                        ? 'text-gray-300/40 dark:text-gray-700/40 cursor-not-allowed'
                                        : future
                                            ? 'text-gray-400 dark:text-gray-500 opacity-40 cursor-not-allowed italic'
                                            : outOfMonth
                                                ? 'text-gray-300 dark:text-gray-600'
                                                : 'text-gray-700 dark:text-gray-200'}
                                    {isRangeStart(cell.iso) || isRangeEnd(cell.iso)
                                        ? 'bg-libre-green !text-white font-bold !opacity-100 !not-italic'
                                        : isInRange(cell.iso)
                                            ? 'bg-libre-green/20 dark:bg-libre-green/25 !text-gray-800 dark:!text-gray-100 !opacity-100 !not-italic'
                                            : cell.iso === pendingDate
                                                ? 'bg-libre-green/50 !text-white font-bold !not-italic'
                                                : future
                                                    ? ''
                                                    : 'hover:bg-gray-100 dark:hover:bg-slate-700'}
                                    {isToday(cell.iso) && !isRangeStart(cell.iso) && !isRangeEnd(cell.iso) && cell.iso !== pendingDate
                                        ? 'ring-1 ring-libre-green ring-inset font-bold !opacity-100 !not-italic' : ''}"
                                onclick={() => handleDayClick(cell.iso)}
                            >{cell.day}</button>
                        </td>
                    {/each}
                </tr>
            {/each}
        </tbody>
    </table>
{/snippet}
