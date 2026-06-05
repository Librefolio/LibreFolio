<!--
  CalendarMonth — Reusable single-month calendar grid with navigation.

  Pure rendering component: no selection logic, no swap logic.
  The parent controls everything via callbacks and highlights.

  Used by: DateRangePicker (×2), SingleDatePicker (×1).
-->
<script lang="ts">
    import {CalendarCheck, ChevronLeft, ChevronRight} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {SimpleSelect} from '$lib/components/ui/select';

    // =========================================================================
    // Types
    // =========================================================================

    export interface CalendarHighlights {
        /** Currently selected date (SingleDatePicker) */
        selected?: string;
        /** Range start date (DateRangePicker) */
        rangeStart?: string;
        /** Range end date (DateRangePicker) */
        rangeEnd?: string;
        /** Pending first-click date (DateRangePicker) */
        pending?: string;
        /** Currently hovered date for range preview (DateRangePicker) */
        hovered?: string;
    }

    interface Props {
        year: number;
        month: number;
        weekdayLabels: string[];
        monthLabels: string[];
        onDayClick: (iso: string) => void;
        onDayHover?: (iso: string) => void;
        onPrevMonth: () => void;
        onNextMonth: () => void;
        onSetMonth: (m: number) => void;
        onSetYear: (y: number) => void;
        onGoToToday?: () => void;
        highlights?: CalendarHighlights;
        disabledDates?: Set<string>;
        /** Allow selecting future dates (default: false — future dates are greyed out) */
        allowFuture?: boolean;
    }

    let {year, month, weekdayLabels, monthLabels, onDayClick, onDayHover, onPrevMonth, onNextMonth, onSetMonth, onSetYear, onGoToToday, highlights = {}, disabledDates, allowFuture = false}: Props = $props();

    // =========================================================================
    // Helpers
    // =========================================================================

    function todayISO(): string {
        return new Date().toISOString().slice(0, 10);
    }

    function formatISO(y: number, m: number, d: number): string {
        return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    }

    function isFuture(iso: string): boolean {
        if (allowFuture) return false;
        return iso > todayISO();
    }

    // SimpleSelect options (derived)
    let monthSelectOptions = $derived(monthLabels.map((label, i) => ({value: String(i), label})));

    function getMonthGrid(y: number, m: number): Array<Array<{day: number; iso: string; inMonth: boolean}>> {
        const firstDay = new Date(y, m, 1);
        let startDow = firstDay.getDay() - 1;
        if (startDow < 0) startDow = 6;
        const daysInMonth = new Date(y, m + 1, 0).getDate();
        const prevMonthDays = new Date(y, m, 0).getDate();
        const cells: Array<{day: number; iso: string; inMonth: boolean}> = [];
        for (let i = startDow - 1; i >= 0; i--) {
            const d = prevMonthDays - i;
            const prevM = m === 0 ? 11 : m - 1;
            const prevY = m === 0 ? y - 1 : y;
            cells.push({day: d, iso: formatISO(prevY, prevM, d), inMonth: false});
        }
        for (let d = 1; d <= daysInMonth; d++) {
            cells.push({day: d, iso: formatISO(y, m, d), inMonth: true});
        }
        const remaining = 42 - cells.length;
        for (let d = 1; d <= remaining; d++) {
            const nextM = m === 11 ? 0 : m + 1;
            const nextY = m === 11 ? y + 1 : y;
            cells.push({day: d, iso: formatISO(nextY, nextM, d), inMonth: false});
        }
        const weeks: (typeof cells)[] = [];
        for (let i = 0; i < cells.length; i += 7) {
            weeks.push(cells.slice(i, i + 7));
        }
        return weeks;
    }

    // =========================================================================
    // Day class logic
    // =========================================================================

    function isSelected(iso: string): boolean {
        return iso === highlights.selected;
    }

    function isRangeStart(iso: string): boolean {
        const {pending, hovered, rangeStart} = highlights;
        if (pending && hovered) return iso === (pending <= hovered ? pending : hovered);
        return iso === rangeStart;
    }

    function isRangeEnd(iso: string): boolean {
        const {pending, hovered, rangeEnd} = highlights;
        if (pending && hovered) return iso === (pending <= hovered ? hovered : pending);
        return iso === rangeEnd;
    }

    function isInRange(iso: string): boolean {
        const {pending, hovered, rangeStart, rangeEnd} = highlights;
        if (pending && hovered) {
            const lo = pending <= hovered ? pending : hovered;
            const hi = pending <= hovered ? hovered : pending;
            return iso >= lo && iso <= hi;
        }
        if (rangeStart && rangeEnd) return iso >= rangeStart && iso <= rangeEnd;
        return false;
    }

    function isToday(iso: string): boolean {
        return iso === todayISO();
    }

    function isDisabled(iso: string): boolean {
        return disabledDates?.has(iso) ?? false;
    }

    function getDayClasses(iso: string, inMonth: boolean): string {
        const future = isFuture(iso);
        const outOfMonth = !inMonth;
        const disabled = isDisabled(iso);
        const selected = isSelected(iso);
        const rangeStart = isRangeStart(iso);
        const rangeEnd = isRangeEnd(iso);
        const inRange = isInRange(iso);
        const pending = iso === highlights.pending;
        const today = isToday(iso);

        let cls = '';

        // Base color
        if (disabled) {
            cls += 'text-gray-300/40 dark:text-gray-700/40 cursor-not-allowed line-through';
        } else if (future && outOfMonth) {
            cls += 'text-gray-300/40 dark:text-gray-700/40 cursor-not-allowed';
        } else if (future) {
            cls += 'text-gray-400 dark:text-gray-500 opacity-40 cursor-not-allowed italic';
        } else if (outOfMonth) {
            cls += 'text-gray-300 dark:text-gray-600';
        } else {
            cls += 'text-gray-700 dark:text-gray-200';
        }

        // Highlight
        if (selected || rangeStart || rangeEnd) {
            cls += ' bg-libre-green !text-white font-bold !opacity-100 !not-italic';
        } else if (inRange) {
            cls += ' bg-libre-green/20 dark:bg-libre-green/25 !text-gray-800 dark:!text-gray-100 !opacity-100 !not-italic';
        } else if (pending) {
            cls += ' bg-libre-green/50 !text-white font-bold !not-italic';
        } else if (!future && !disabled) {
            cls += ' hover:bg-gray-100 dark:hover:bg-slate-700';
        }

        // Today ring
        if (today && !selected && !rangeStart && !rangeEnd && !pending) {
            cls += ' ring-1 ring-libre-green ring-inset font-bold !opacity-100 !not-italic';
        }

        return cls;
    }
</script>

<div class="min-w-[240px]">
    <!-- Month/Year navigation header -->
    <div class="flex items-center justify-between mb-2">
        <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400" onclick={onPrevMonth} type="button">
            <ChevronLeft size={16} />
        </button>
        <div class="flex items-center gap-1">
            <SimpleSelect class="inline-block w-auto" compact dropdownPosition="auto" onchange={(v) => onSetMonth(parseInt(v))} options={monthSelectOptions} showChevron={false} value={String(month)} />
            <input
                type="number"
                value={year}
                min="1900"
                max="2200"
                onchange={(e) => onSetYear(parseInt(e.currentTarget.value) || new Date().getFullYear())}
                class="w-14 px-1 py-0.5 text-xs font-semibold text-center bg-transparent border-none outline-none
                           text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-700 rounded
                           focus:ring-1 focus:ring-libre-green/50
                           [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
        </div>
        <div class="flex items-center gap-0.5">
            {#if onGoToToday}
                <button type="button" class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 dark:text-gray-500" title={$_('datePicker.today')} onclick={onGoToToday}>
                    <CalendarCheck size={14} />
                </button>
            {/if}
            <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400" onclick={onNextMonth} type="button">
                <ChevronRight size={16} />
            </button>
        </div>
    </div>

    <!-- Day grid -->
    <table class="w-full table-fixed">
        <thead>
            <tr>
                {#each weekdayLabels as wdLabel}
                    <th class="text-center text-[10px] font-semibold text-gray-500 dark:text-gray-400 pb-1 w-[14.28%]">{wdLabel}</th>
                {/each}
            </tr>
        </thead>
        <tbody>
            {#each getMonthGrid(year, month) as week}
                <tr>
                    {#each week as cell}
                        {@const future = isFuture(cell.iso)}
                        {@const disabled = isDisabled(cell.iso)}
                        <td
                            class="text-center p-0"
                            onmouseenter={() => {
                                if (onDayHover) onDayHover(cell.iso);
                            }}
                        >
                            <button
                                type="button"
                                class="w-full aspect-square text-xs leading-none rounded-md transition-colors {getDayClasses(cell.iso, cell.inMonth)}"
                                disabled={future || disabled}
                                onclick={() => {
                                    if (!disabled) onDayClick(cell.iso);
                                }}>{cell.day}</button
                            >
                        </td>
                    {/each}
                </tr>
            {/each}
        </tbody>
    </table>
</div>
