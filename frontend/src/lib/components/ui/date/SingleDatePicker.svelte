<!--
  SingleDatePicker — Single-date field: type it, or pick it from the calendar.

  The calendar icon opens a popover with one CalendarMonth (single click = select
  and close). The date itself is a text field, because reaching a date far from
  today through month arrows is slow and a user who already knows the date should
  simply be able to write it. Typed input accepts both orders and all three
  separators (see `parseTypedDate`); anything unreadable is refused and the field
  falls back to the current value rather than guessing.

  Used by: DataEditor (new row date editing), transaction form, broker form.
-->
<script lang="ts">
    import {todayIso} from '$lib/utils/dateOnly';
    import {Calendar} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import CalendarMonth from './CalendarMonth.svelte';
    import {parseTypedDate} from '$lib/utils/core/parseTypedDate';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';
    import {dateArrowStep, resetDateArrowHold} from '$lib/utils/core/dateArrowStep';

    // =========================================================================
    // i18n
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

    let weekdayLabels: string[] = $derived(WEEKDAY_KEYS.map((k) => $_(k)));
    let monthLabels: string[] = $derived(MONTH_KEYS.map((k) => $_(k)));

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
        /** Render the trigger as a full-width input-style control matching
         *  SearchSelect (`w-full px-3 py-2 text-sm`). Useful when used inside
         *  a DataTable cell or grid alongside other selectors (Bugfix-3 §U13). */
        inputStyle?: boolean;
        /** Called when user selects a date */
        onchange: (date: string) => void;
        /** Set of dates that cannot be selected */
        disabledDates?: Set<string>;
        /** Allow selecting future dates (default: false) */
        allowFuture?: boolean;
        /** Disable both the field and the calendar. */
        disabled?: boolean;
        /** Test id for E2E targeting. */
        testid?: string;
    }

    let {value = $bindable(''), label = 'Date', compact = false, inputStyle = false, onchange, disabledDates, allowFuture = false, disabled = false, testid}: Props = $props();

    /**
     * Prefix for the structural test ids. `testid` names the *input*, which is what a
     * caller cares about; the trigger and the popover derive from it so two pickers on
     * the same screen stay distinguishable. Without a caller-supplied id they fall back
     * to a shared default — fine for a screen that only has one.
     */
    let tid = $derived(testid ?? 'single-date-picker');

    // =========================================================================
    // State
    // =========================================================================

    let calendarOpen = $state(false);
    let calYear = $state(new Date().getFullYear());
    let calMonth = $state(new Date().getMonth());
    let triggerEl: HTMLElement | null = $state(null);
    let popoverStyle = $state('');
    /** What the user is typing. `null` means the field just shows `value`. */
    let typed = $state<string | null>(null);

    let shown = $derived(typed ?? value ?? '');
    let typedIso = $derived(typed === null ? null : parseTypedDate(typed));
    /** The raw fact: the text does not read as a date this picker would accept. */
    let typedUnparseable = $derived(typed !== null && typed.trim() !== '' && !isSelectable(typedIso));
    /**
     * A half-typed date is not a mistake, it is a date in progress: `2024-08-0` fails to
     * parse for exactly as long as it takes to press one more key. Complaining on every
     * keystroke painted the field red for the whole time the user was typing it
     * *correctly* — from `2` all the way to the last digit.
     *
     * So the complaint is armed only when the user leaves the value as it stands: blur,
     * or Enter. It is disarmed again the moment they resume editing, because at that
     * point the text is in progress once more.
     */
    let validationArmed = $state(false);
    let typedInvalid = $derived(validationArmed && typedUnparseable);
    /** What the calendar highlights: the date being typed as soon as it reads as one. */
    let previewIso = $derived(isSelectable(typedIso) ? typedIso : value);

    // =========================================================================
    // Helpers
    // =========================================================================

    /**
     * The same gates the calendar applies to a day cell, applied to a typed date:
     * a field that accepts what the calendar greys out would be a way around the rule.
     */
    function isSelectable(iso: string | null): iso is string {
        if (!iso) return false;
        if (disabledDates?.has(iso)) return false;
        if (!allowFuture && iso > todayIso()) return false;
        return true;
    }

    /**
     * Reads what the user typed.
     *
     * Text the picker will not accept is *kept on screen* instead of being discarded.
     * Throwing it away silently put the previous value back with no explanation, so
     * "I mistyped" and "I typed a date this field refuses" looked identical — nothing
     * on screen said which. Now the refused text stays, and the caller arms the
     * warning, so leaving the field is where the user finds out.
     *
     * Escape remains the way to abandon an edit, and an empty field is read as exactly
     * that: nothing was refused, so the stored value comes back.
     */
    function commitTyped() {
        if (typed === null) return;
        const parsed = parseTypedDate(typed);
        if (isSelectable(parsed)) {
            if (parsed !== value) {
                value = parsed;
                onchange(parsed);
            }
            typed = null;
            return;
        }
        if (typed.trim() === '') typed = null;
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
        if (disabled) return;
        const anchor = previewIso || value;
        if (anchor) {
            const [y, m] = anchor.split('-').map(Number);
            calYear = y;
            calMonth = m - 1;
        } else {
            const now = new Date();
            calYear = now.getFullYear();
            calMonth = now.getMonth();
        }
        // Positioned *before* it is shown: the popover is `position: fixed` only once
        // `popoverStyle` is set, so opening first would paint one frame in the document
        // flow, on top of the field. The frame after is for anything that moved since.
        updatePopoverPosition();
        calendarOpen = true;
        requestAnimationFrame(updatePopoverPosition);
    }

    function closeCalendar() {
        calendarOpen = false;
    }

    // Reposition on scroll (needed when embedded inside another fixed popover).
    // Close if trigger exits viewport.
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

    function handleDayClick(iso: string) {
        value = iso;
        typed = null;
        calendarOpen = false;
        onchange(iso);
    }

    /**
     * Typing is the fast path, but the calendar is what tells the user *which* date they
     * actually wrote — "07/08" reads differently to everyone. It follows along, so a
     * misread is visible before it is committed.
     */
    function syncCalendarToTyped() {
        if (!calendarOpen || !isSelectable(typedIso)) return;
        const [y, m] = typedIso.split('-').map(Number);
        calYear = y;
        calMonth = m - 1;
    }

    /**
     * Arrow keys step the date, accelerating while held: day, then month, then year,
     * then tens and hundreds of years. Reaching a birth date or a decade-old boundary
     * through the month arrows of the calendar is otherwise a long click session.
     */
    function stepDate(e: KeyboardEvent) {
        const next = dateArrowStep(e, isSelectable(typedIso) ? typedIso : value || null, todayIso());
        if (next === null) return false;
        // The same ceiling the calendar enforces: arrows are a stepper, and a stepper
        // stops at its bound instead of walking past it into an invalid state.
        typed = !allowFuture && next > todayIso() ? todayIso() : next;
        syncCalendarToTyped();
        if (!calendarOpen) openCalendar();
        return true;
    }

    function handleInputKeydown(e: KeyboardEvent) {
        if (stepDate(e)) return;
        if (e.key === 'Enter') {
            e.preventDefault();
            // Enter commits and puts the calendar away; pressing it again asks for it back,
            // which is the only way to reopen it without leaving and re-entering the field.
            if (calendarOpen) {
                // Enter says "this is my answer", so an answer that does not read as a
                // date is now worth complaining about — same moment as leaving the field.
                validationArmed = true;
                commitTyped();
                closeCalendar();
            } else {
                openCalendar();
            }
        } else if (e.key === 'Escape') {
            typed = null;
            validationArmed = false;
        }
    }

    function handleClickOutside(e: MouseEvent) {
        // The isConnected guard (target detached before the click — a nested
        // SimpleSelect option removed on mousedown) now lives in isOutsideClick.
        if (isOutsideClick(e.target, (el) => !!el.closest('.sdp-popover') || !!el.closest('.sdp-trigger'))) {
            closeCalendar();
        }
    }

    // Close on click outside — use mousedown in capture phase to avoid stopPropagation issues
    $effect(() => {
        if (!calendarOpen) return;
        const handler = (e: MouseEvent) => handleClickOutside(e);
        document.addEventListener('mousedown', handler, true);
        return () => document.removeEventListener('mousedown', handler, true);
    });

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
<svelte:window onkeydown={handleKeydown} />

<div class="relative sdp-trigger {inputStyle ? 'block w-full' : 'inline-block'}" data-testid="{tid}-root" data-open={calendarOpen ? 'true' : 'false'} data-invalid={typedInvalid ? 'true' : 'false'}>
    <!-- The date is typed, not only picked: the calendar is one click away but is
         the slow path for anything more than a few months from today. -->
    <div
        bind:this={triggerEl}
        class="flex items-center gap-1.5 rounded-lg border bg-white transition-colors dark:bg-slate-800 {inputStyle ? 'w-full px-3 py-2 text-sm' : compact ? 'px-2 py-1' : 'px-2.5 py-1.5'} {typedInvalid
            ? 'border-red-400 dark:border-red-500'
            : calendarOpen
              ? 'border-libre-green ring-1 ring-libre-green'
              : 'border-gray-200 hover:border-libre-green/50 dark:border-slate-600'} {disabled ? 'opacity-60' : ''}"
    >
        <button
            type="button"
            class="flex-shrink-0 text-libre-green disabled:cursor-not-allowed"
            data-testid="{tid}-calendar-button"
            {disabled}
            aria-label={$_('datePicker.openCalendar')}
            title={$_('datePicker.openCalendar')}
            onclick={(e) => {
                e.stopPropagation();
                if (calendarOpen) closeCalendar();
                else openCalendar();
            }}
        >
            <Calendar size={inputStyle ? 14 : compact ? 12 : 14} />
        </button>
        {#if label}<span class="flex-shrink-0 text-[10px] font-medium tracking-wide text-gray-400 uppercase dark:text-gray-500">{label}</span>{/if}
        <input
            type="text"
            inputmode="numeric"
            autocomplete="off"
            spellcheck="false"
            {disabled}
            class="min-w-0 flex-1 border-none bg-transparent font-mono text-gray-700 outline-none dark:text-gray-200 {inputStyle ? 'text-sm' : compact ? 'text-[11px]' : 'text-xs'} {typedInvalid ? 'text-red-600 dark:text-red-400' : ''}"
            style={inputStyle ? undefined : 'width: 6.5rem'}
            value={shown}
            placeholder="YYYY-MM-DD"
            title={$_('datePicker.formatHint')}
            data-testid={testid}
            oninput={(e) => {
                typed = e.currentTarget.value;
                // Editing resumed: whatever is on screen is in progress again.
                validationArmed = false;
                syncCalendarToTyped();
            }}
            onblur={() => {
                resetDateArrowHold();
                validationArmed = true;
                commitTyped();
            }}
            onkeyup={resetDateArrowHold}
            onkeydown={handleInputKeydown}
            onfocus={openCalendar}
            onclick={(e) => {
                e.stopPropagation();
                // Clicking the field still opens the calendar: the input is an addition to
                // the picker, not a replacement, and the click means "I want to set a date".
                if (!calendarOpen) openCalendar();
            }}
        />
    </div>

    {#if calendarOpen}
        <div class="sdp-popover bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-gray-200 dark:border-slate-600 p-4 w-[280px]" style={popoverStyle} data-testid="{tid}-popover">
            <CalendarMonth year={calYear} month={calMonth} {weekdayLabels} {monthLabels} onDayClick={handleDayClick} onPrevMonth={prevMonth} onNextMonth={nextMonth} onSetMonth={setMonth} onSetYear={setYear} onGoToToday={goToToday} highlights={{selected: previewIso}} {disabledDates} {allowFuture} />
        </div>
    {/if}
</div>
