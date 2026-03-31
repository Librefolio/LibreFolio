<!--
  SingleDatePicker — Single-date picker with calendar popover.

  Renders a trigger button (Calendar icon + label + date) that opens
  a popover with one CalendarMonth. Single click = select + close.

  Used by: DataEditor (new row date editing).
-->
<script lang="ts">
    import {Calendar} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import CalendarMonth from './CalendarMonth.svelte';

    // =========================================================================
    // i18n
    // =========================================================================

    const WEEKDAY_KEYS = [
        'datePicker.weekdays.mo', 'datePicker.weekdays.tu', 'datePicker.weekdays.we',
        'datePicker.weekdays.th', 'datePicker.weekdays.fr', 'datePicker.weekdays.sa',
        'datePicker.weekdays.su',
    ];

    const MONTH_KEYS = [
        'datePicker.months.january', 'datePicker.months.february', 'datePicker.months.march',
        'datePicker.months.april', 'datePicker.months.may', 'datePicker.months.june',
        'datePicker.months.july', 'datePicker.months.august', 'datePicker.months.september',
        'datePicker.months.october', 'datePicker.months.november', 'datePicker.months.december',
    ];

    let weekdayLabels: string[] = $derived(WEEKDAY_KEYS.map(k => $_(k)));
    let monthLabels: string[] = $derived(MONTH_KEYS.map(k => $_(k)));

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Selected date (ISO YYYY-MM-DD) */
        value: string;
        /** Label displayed next to the icon */
        label?: string;
        /** Compact mode (smaller text) */
        compact?: boolean;
        /** Called when user selects a date */
        onchange: (date: string) => void;
        /** Set of dates that cannot be selected */
        disabledDates?: Set<string>;
        /** Allow selecting future dates (default: false) */
        allowFuture?: boolean;
    }

    let {
        value = $bindable(''),
        label = 'Date',
        compact = false,
        onchange,
        disabledDates,
        allowFuture = false,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let calendarOpen = $state(false);
    let calYear = $state(new Date().getFullYear());
    let calMonth = $state(new Date().getMonth());
    let triggerEl = $state<HTMLButtonElement | null>(null);
    let popoverStyle = $state('');

    // =========================================================================
    // Helpers
    // =========================================================================

    function displayDate(iso: string): string {
        if (!iso) return '—';
        // Use YYYY-MM-DD format (ISO, non-ambiguous)
        return iso;
    }

    function updatePopoverPosition() {
        if (!triggerEl) return;
        const rect = triggerEl.getBoundingClientRect();
        const popoverHeight = 330; // estimated height of calendar popover
        const spaceBelow = window.innerHeight - rect.bottom - 8;
        const spaceAbove = rect.top - 8;
        // Open above if not enough space below and more space above
        const openAbove = spaceBelow < popoverHeight && spaceAbove > spaceBelow;
        const top = openAbove ? rect.top - popoverHeight - 4 : rect.bottom + 4;
        const left = Math.max(4, Math.min(rect.left, window.innerWidth - 280));
        popoverStyle = `position: fixed; top: ${top}px; left: ${left}px; z-index: 9999;`;
    }

    function openCalendar() {
        if (value) {
            const [y, m] = value.split('-').map(Number);
            calYear = y;
            calMonth = m - 1;
        } else {
            const now = new Date();
            calYear = now.getFullYear();
            calMonth = now.getMonth();
        }
        calendarOpen = true;
        requestAnimationFrame(updatePopoverPosition);
    }

    function closeCalendar() {
        calendarOpen = false;
    }

    // Close popover on scroll (position: fixed doesn't follow the trigger)
    $effect(() => {
        if (!calendarOpen) return;
        const handleScroll = () => closeCalendar();
        window.addEventListener('scroll', handleScroll, true);
        return () => window.removeEventListener('scroll', handleScroll, true);
    });

    function handleDayClick(iso: string) {
        value = iso;
        calendarOpen = false;
        onchange(iso);
    }

    function handleClickOutside(e: MouseEvent) {
        const target = e.target as HTMLElement;
        if (!target.isConnected) return;
        if (!target.closest('.sdp-popover') && !target.closest('.sdp-trigger')) {
            closeCalendar();
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape' && calendarOpen) closeCalendar();
    }

    // Navigation
    function prevMonth() {
        if (calMonth === 0) {
            calMonth = 11;
            calYear--;
        } else {
            calMonth--;
        }
    }

    function nextMonth() {
        if (calMonth === 11) {
            calMonth = 0;
            calYear++;
        } else {
            calMonth++;
        }
    }

    function setMonth(m: number) {
        calMonth = m;
    }

    function setYear(y: number) {
        calYear = y;
    }

    function goToToday() {
        const now = new Date();
        calYear = now.getFullYear();
        calMonth = now.getMonth();
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown}/>

<div class="relative sdp-trigger inline-block">
    <button
            bind:this={triggerEl}
            class="flex items-center gap-1.5 bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-600 cursor-pointer hover:border-libre-green/50 transition-colors {compact ? 'px-2 py-1' : 'px-2.5 py-1.5'} {calendarOpen ? 'ring-1 ring-libre-green border-libre-green' : ''}"
            onclick={(e) => { e.stopPropagation(); openCalendar(); }}
            type="button"
    >
        <Calendar class="text-libre-green flex-shrink-0" size={compact ? 12 : 14}/>
        {#if label}<span class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide flex-shrink-0">{label}</span>{/if}
        <span class="font-mono {compact ? 'text-[11px]' : 'text-xs'} text-gray-700 dark:text-gray-200 flex-shrink-0">{displayDate(value)}</span>
    </button>

    {#if calendarOpen}
        <div class="sdp-popover bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-600 p-4 w-[280px]" style={popoverStyle}>
            <CalendarMonth
                    year={calYear}
                    month={calMonth}
                    {weekdayLabels}
                    {monthLabels}
                    onDayClick={handleDayClick}
                    onPrevMonth={prevMonth}
                    onNextMonth={nextMonth}
                    onSetMonth={setMonth}
                    onSetYear={setYear}
                    onGoToToday={goToToday}
                    highlights={{ selected: value }}
                    {disabledDates}
                    {allowFuture}
            />
        </div>
    {/if}
</div>

