<!--
  DataTableColumnFilter - Excel-style filter popover for table columns
  
  Filter types based on column data type:
  - text: text input with match mode (contains, starts, ends, equals) - instant apply
  - number: min/max range
  - size: file size with logarithmic slider + input with unit dropdown
  - date: from/to date pickers
  - enum: checkbox list of available options
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import {t} from '$lib/i18n';
    import {formatBytes} from '$lib/utils/files/upload';
    import {Check, Filter as FilterIcon, RotateCcw, Search, Trash2, X} from 'lucide-svelte';
    import {fade} from 'svelte/transition';
    import type {ColumnType, EnumOption, FilterValue} from './types';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {formatCurrencyCodeHtml} from '$lib/utils/currency/currencyFormat';
    import {currencyStoreVersion} from '$lib/stores/reference/currencyStore';
    import {clamp, DROPDOWN_VIEWPORT_MARGIN} from '$lib/utils/layout/dropdownPosition';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';

    import {numericArrows} from '$lib/actions/numericArrows';
    type TextMatchMode = 'contains' | 'startsWith' | 'endsWith' | 'equals';
    type SizeUnit = 'B' | 'KB' | 'MB' | 'GB';

    interface Props {
        type: ColumnType;
        enumOptions?: EnumOption[];
        /** For `currency-stack`: list of currency codes available in the current dataset (seed for the CurrencySearchSelect). */
        currencyOptions?: string[];
        /** For `currency-stack`: per-currency min/max amount in the dataset.
         *  Drives a relevant range editor for each picked currency (instead
         *  of one meaningless global range across mixed currencies). */
        currencyMinMaxByCode?: Map<string, {min: number; max: number}>;
        numberMin?: number;
        numberMax?: number;
        onApply: (filter: FilterValue | null) => void;
        onClose: () => void;
        initialValue?: FilterValue | null;
        /** Anchor element (filter button) for fixed-position popover */
        anchorElement?: HTMLElement | null;
        /** Force integer-only input (step=1, round on change). Default: false (decimal). */
        integerOnly?: boolean;
    }

    let {type, enumOptions = [], currencyOptions = [], currencyMinMaxByCode = new Map(), numberMin = 0, numberMax = 100, onApply, onClose, initialValue = null, anchorElement = null, integerOnly = false}: Props = $props();

    // Sentinel: ensure formatCurrencyCodeHtml re-evaluates after currency data loads.
    void $currencyStoreVersion;

    let popoverElement: HTMLDivElement;

    // Fixed positioning state
    let popoverStyle = $state('');

    // Size units conversion (labels are translated via getter)
    const SIZE_UNITS_BASE: {unit: SizeUnit; bytes: number; labelKey: string}[] = [
        {unit: 'B', bytes: 1, labelKey: 'common.bytes'},
        {unit: 'KB', bytes: 1024, labelKey: 'common.kilobytes'},
        {unit: 'MB', bytes: 1024 * 1024, labelKey: 'common.megabytes'},
        {unit: 'GB', bytes: 1024 * 1024 * 1024, labelKey: 'common.gigabytes'},
    ];

    // Reactive translated size units
    let SIZE_UNITS = $derived(
        SIZE_UNITS_BASE.map((u) => ({
            unit: u.unit,
            bytes: u.bytes,
            label: $t(u.labelKey) || u.unit,
        })),
    );

    /** BUG-C11: integer columns use step=1 and round slider values. Driven by `integerOnly` prop. */
    let isIntegerRange = $derived(integerOnly && type === 'number');

    // Helper functions to get initial values
    function getInitialTextValue(): string {
        return initialValue?.type === 'text' ? initialValue.value : '';
    }

    function getInitialTextMatchMode(): TextMatchMode {
        return initialValue?.type === 'text' ? initialValue.matchMode : 'contains';
    }

    function getInitialNumMin(): number {
        return initialValue?.type === 'number' ? (initialValue.min ?? numberMin) : numberMin;
    }

    function getInitialNumMax(): number {
        return initialValue?.type === 'number' ? (initialValue.max ?? numberMax) : numberMax;
    }

    function getInitialDateFrom(): string {
        return initialValue?.type === 'date' ? (initialValue.from ?? '') : '';
    }

    function getInitialDateTo(): string {
        return initialValue?.type === 'date' ? (initialValue.to ?? '') : '';
    }

    function getInitialEnums(): Set<string> {
        return new Set(initialValue?.type === 'enum' ? initialValue.selected : []);
    }

    function getInitialSizeMin(): number {
        return initialValue?.type === 'size' ? (initialValue.minBytes ?? numberMin) : numberMin;
    }

    function getInitialSizeMax(): number {
        return initialValue?.type === 'size' ? (initialValue.maxBytes ?? numberMax) : numberMax;
    }

    function handleEnumIconError(event: Event) {
        const img = event.currentTarget as HTMLImageElement;
        try {
            const fallbacks = JSON.parse(img.dataset.fallbacks || '[]') as string[];
            const next = fallbacks.shift();
            if (next) {
                img.dataset.fallbacks = JSON.stringify(fallbacks);
                img.src = next;
                return;
            }
        } catch {
            // Ignore malformed fallback metadata and fall back to dot-only UI.
        }
        img.style.visibility = 'hidden';
    }

    // Text filter state
    let textValue = $state(getInitialTextValue());
    let textMatchMode: TextMatchMode = $state(getInitialTextMatchMode());

    // Number filter state
    let numMin = $state(getInitialNumMin());
    let numMax = $state(getInitialNumMax());

    // Number slider positions (0-100)
    // svelte-ignore state_referenced_locally
    let numSliderMinPos = $state(numToSliderPos(getInitialNumMin()));
    // svelte-ignore state_referenced_locally
    let numSliderMaxPos = $state(numToSliderPos(getInitialNumMax()));

    // Linear scale for number slider
    function numToSliderPos(value: number): number {
        if (numberMax <= numberMin) return 0;
        return Math.round(((value - numberMin) / (numberMax - numberMin)) * 100);
    }

    // LINEAR scale: number slider maps 0-100 position linearly to [numberMin, numberMax]
    function sliderPosToNum(pos: number): number {
        const raw = numberMin + (pos / 100) * (numberMax - numberMin);
        // Integer columns always round to int
        if (isIntegerRange) return Math.round(raw);
        // Round to reasonable precision based on range magnitude
        const range = numberMax - numberMin;
        if (range < 1) return Math.round(raw * 100000) / 100000;
        if (range < 10) return Math.round(raw * 1000) / 1000;
        if (range < 100) return Math.round(raw * 100) / 100;
        if (range < 1000) return Math.round(raw * 10) / 10;
        return Math.round(raw);
    }

    /** Format number for slider labels */
    function fmtNum(v: number): string {
        if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, {maximumFractionDigits: 0});
        if (Math.abs(v) >= 1) return v.toLocaleString(undefined, {maximumFractionDigits: 2});
        return v.toPrecision(3);
    }

    /** Snap threshold: if the slider position is within this many units (out of
     *  0–100) of an extreme, snap to the exact boundary. This avoids rounding
     *  artifacts at the edges where the user clearly intends "min" or "max". */
    const SNAP = 3;

    function updateNumMinFromSlider() {
        // Clamp: prevent crossing
        if (numSliderMinPos > numSliderMaxPos) numSliderMinPos = numSliderMaxPos;
        // Compute value with snap (value snaps to exact boundary, position follows mouse)
        if (numSliderMinPos <= SNAP) {
            numMin = numberMin;
        } else if (numSliderMinPos >= 100 - SNAP) {
            numMin = numberMax;
        } else {
            numMin = sliderPosToNum(numSliderMinPos);
        }
        applyFilter();
    }

    function updateNumMaxFromSlider() {
        if (numSliderMaxPos < numSliderMinPos) numSliderMaxPos = numSliderMinPos;
        if (numSliderMaxPos >= 100 - SNAP) {
            numMax = numberMax;
        } else if (numSliderMaxPos <= SNAP) {
            numMax = numberMin;
        } else {
            numMax = sliderPosToNum(numSliderMaxPos);
        }
        applyFilter();
    }

    /** On mouseup: snap slider position to boundary if within threshold. */
    function finalizeNumSliders() {
        if (numSliderMinPos <= SNAP) numSliderMinPos = 0;
        if (numSliderMinPos >= 100 - SNAP) numSliderMinPos = 100;
        if (numSliderMaxPos >= 100 - SNAP) numSliderMaxPos = 100;
        if (numSliderMaxPos <= SNAP) numSliderMaxPos = 0;
    }

    let numMinInputEl: HTMLInputElement | null = $state(null);
    let numMaxInputEl: HTMLInputElement | null = $state(null);
    let sizeMinInputEl: HTMLInputElement | null = $state(null);
    let sizeMaxInputEl: HTMLInputElement | null = $state(null);

    /**
     * Sends the caret after the value when a swap moved it to the other field, so the
     * number the user is working on stays under their cursor instead of being left
     * behind in the box it just vacated.
     */
    async function followSwap(el: HTMLInputElement | null) {
        await tick();
        el?.focus();
        el?.select();
    }

    function syncNumSlidersFromInput() {
        if (isIntegerRange) {
            numMin = Math.round(numMin);
            numMax = Math.round(numMax);
        }
        // A minimum above its maximum selects nothing, and a filter that quietly matches
        // nothing looks like broken data. The user typed two bounds; they meant a range,
        // so the pair is put back in order — text and slider handles together.
        if (numMin > numMax) [numMin, numMax] = [numMax, numMin];
        numSliderMinPos = numToSliderPos(numMin);
        numSliderMaxPos = numToSliderPos(numMax);
    }

    // Date filter state
    let dateFrom = $state(getInitialDateFrom());
    let dateTo = $state(getInitialDateTo());

    // Enum filter state
    let selectedEnums: Set<string> = $state(getInitialEnums());

    // Multi-enum filter state (tags-like) — start with empty selection (= no filter)
    function getInitialMultiEnums(): Set<string> {
        return new Set(initialValue?.type === 'multi-enum' ? initialValue.selected : []);
    }
    let multiEnums: Set<string> = $state(getInitialMultiEnums());
    let multiEnumSearch = $state('');
    let enumSearch = $state('');

    // Currency-stack filter state
    type CurrencyStackItem = {code: string; min?: number; max?: number};
    function getInitialCurrencyStack(): CurrencyStackItem[] {
        return initialValue?.type === 'currency-stack' ? initialValue.items.map((i) => ({...i})) : [];
    }
    let currencyStack: CurrencyStackItem[] = $state(getInitialCurrencyStack());
    let currencyToAdd = $state('');
    /** Index of the currency-stack row whose range editor is currently open. */
    let currencyOpenIdx: number | null = $state(null);
    /** Per-row slider position state for the currency-stack range editor.
     *  Mirrors the linear scale used by `type:'number'` so the UX is identical. */
    let currencyMinPos: Record<number, number> = $state({});
    let currencyMaxPos: Record<number, number> = $state({});

    /** Per-currency linear helpers — same math as the global num slider but
     *  scoped to the min/max of the specific currency code. Falls back to
     *  `numberMin`/`numberMax` when the code is not in the map (defensive). */
    function curRange(idx: number): {min: number; max: number} {
        const code = currencyStack[idx]?.code;
        if (code) {
            const r = currencyMinMaxByCode.get(code);
            if (r) return r;
        }
        return {min: numberMin, max: numberMax};
    }
    function curNumToSliderPos(idx: number, value: number): number {
        const r = curRange(idx);
        if (r.max <= r.min) return 0;
        return Math.round(((value - r.min) / (r.max - r.min)) * 100);
    }
    function curSliderPosToNum(idx: number, pos: number): number {
        const r = curRange(idx);
        const raw = r.min + (pos / 100) * (r.max - r.min);
        const range = r.max - r.min;
        if (range < 1) return Math.round(raw * 100000) / 100000;
        if (range < 10) return Math.round(raw * 1000) / 1000;
        if (range < 100) return Math.round(raw * 100) / 100;
        if (range < 1000) return Math.round(raw * 10) / 10;
        return Math.round(raw);
    }

    function curMinPos(idx: number): number {
        if (currencyMinPos[idx] != null) return currencyMinPos[idx];
        const v = currencyStack[idx]?.min;
        return v == null ? 0 : curNumToSliderPos(idx, v);
    }
    function curMaxPos(idx: number): number {
        if (currencyMaxPos[idx] != null) return currencyMaxPos[idx];
        const v = currencyStack[idx]?.max;
        return v == null ? 100 : curNumToSliderPos(idx, v);
    }

    // Size filter state (stored in bytes internally)
    let sizeMinBytes = $state(getInitialSizeMin());
    let sizeMaxBytes = $state(getInitialSizeMax());

    // Helper to convert bytes to display unit
    function bytesToUnit(bytes: number): {value: number; unit: SizeUnit} {
        if (bytes >= 1024 * 1024 * 1024) return {value: Math.round((bytes / (1024 * 1024 * 1024)) * 10) / 10, unit: 'GB'};
        if (bytes >= 1024 * 1024) return {value: Math.round((bytes / (1024 * 1024)) * 10) / 10, unit: 'MB'};
        if (bytes >= 1024) return {value: Math.round((bytes / 1024) * 10) / 10, unit: 'KB'};
        return {value: bytes, unit: 'B'};
    }

    // Helper to convert unit to bytes
    function unitToBytes(value: number, unit: SizeUnit): number {
        const unitInfo = SIZE_UNITS.find((u) => u.unit === unit);
        return Math.round(value * (unitInfo?.bytes || 1));
    }

    // Size input values (displayed with units) - initialize from bytes immediately
    function initializeMinFromBytes(): {value: number; unit: SizeUnit} {
        return bytesToUnit(getInitialSizeMin());
    }

    function initializeMaxFromBytes(): {value: number; unit: SizeUnit} {
        return bytesToUnit(getInitialSizeMax());
    }

    let sizeMinInputValue = $state(initializeMinFromBytes().value);
    let sizeMinUnit: SizeUnit = $state(initializeMinFromBytes().unit);
    let sizeMaxInputValue = $state(initializeMaxFromBytes().value);
    let sizeMaxUnit: SizeUnit = $state(initializeMaxFromBytes().unit);

    // Slider positions (0-100)
    // svelte-ignore state_referenced_locally
    let sliderMinPos = $state(bytesToSliderPos(getInitialSizeMin()));
    // svelte-ignore state_referenced_locally
    let sliderMaxPos = $state(bytesToSliderPos(getInitialSizeMax()));

    // Initialize size input values from bytes
    function initSizeInputs() {
        const minResult = bytesToUnit(sizeMinBytes);
        sizeMinInputValue = minResult.value;
        sizeMinUnit = minResult.unit;

        const maxResult = bytesToUnit(sizeMaxBytes);
        sizeMaxInputValue = maxResult.value;
        sizeMaxUnit = maxResult.unit; // Fixed: was minResult.unit

        sliderMinPos = bytesToSliderPos(sizeMinBytes);
        sliderMaxPos = bytesToSliderPos(sizeMaxBytes);
    }

    // LOGARITHMIC scale: size slider maps 0-100 position logarithmically to [numberMin, numberMax]
    function sliderPosToBytes(pos: number): number {
        if (pos <= 0) return numberMin;
        if (pos >= 100) return numberMax;
        const logMin = Math.log10(Math.max(numberMin, 1));
        const logMax = Math.log10(Math.max(numberMax, 1));
        const logVal = logMin + (pos / 100) * (logMax - logMin);
        return Math.round(Math.pow(10, logVal));
    }

    // Bytes to slider position (0-100)
    function bytesToSliderPos(bytes: number): number {
        if (bytes <= numberMin) return 0;
        if (bytes >= numberMax) return 100;
        const logMin = Math.log10(Math.max(numberMin, 1));
        const logMax = Math.log10(Math.max(numberMax, 1));
        const logVal = Math.log10(Math.max(bytes, 1));
        return Math.round(((logVal - logMin) / (logMax - logMin)) * 100);
    }

    /**
     * Puts the size bounds back in order and repaints both fields and both handles.
     *
     * Crossing the bounds used to be clamped away, which silently threw the number the
     * user had just typed on the floor. Swapping keeps it: they wrote a range, they
     * just wrote its two ends in the other order.
     */
    function normalizeSizeBounds() {
        if (sizeMinBytes > sizeMaxBytes) [sizeMinBytes, sizeMaxBytes] = [sizeMaxBytes, sizeMinBytes];
        sliderMinPos = bytesToSliderPos(sizeMinBytes);
        sliderMaxPos = bytesToSliderPos(sizeMaxBytes);
        const minResult = bytesToUnit(sizeMinBytes);
        sizeMinInputValue = minResult.value;
        sizeMinUnit = minResult.unit;
        const maxResult = bytesToUnit(sizeMaxBytes);
        sizeMaxInputValue = maxResult.value;
        sizeMaxUnit = maxResult.unit;
    }

    // Update bytes from input change
    function updateSizeMinFromInput() {
        sizeMinBytes = Math.max(numberMin, Math.min(numberMax, unitToBytes(sizeMinInputValue, sizeMinUnit)));
        const swapped = sizeMinBytes > sizeMaxBytes;
        normalizeSizeBounds();
        applyFilter();
        if (swapped) void followSwap(sizeMaxInputEl);
    }

    function updateSizeMaxFromInput() {
        sizeMaxBytes = Math.max(numberMin, Math.min(numberMax, unitToBytes(sizeMaxInputValue, sizeMaxUnit)));
        const swapped = sizeMinBytes > sizeMaxBytes;
        normalizeSizeBounds();
        applyFilter();
        if (swapped) void followSwap(sizeMinInputEl);
    }

    // Update bytes from slider change
    function updateSizeMinFromSlider() {
        if (sliderMinPos > sliderMaxPos) sliderMinPos = sliderMaxPos;
        if (sliderMinPos <= SNAP) {
            sizeMinBytes = numberMin;
        } else {
            sizeMinBytes = sliderPosToBytes(sliderMinPos);
        }
        const minResult = bytesToUnit(sizeMinBytes);
        sizeMinInputValue = minResult.value;
        sizeMinUnit = minResult.unit;
        applyFilter();
    }

    function updateSizeMaxFromSlider() {
        if (sliderMaxPos < sliderMinPos) sliderMaxPos = sliderMinPos;
        if (sliderMaxPos >= 100 - SNAP) {
            sizeMaxBytes = numberMax;
        } else {
            sizeMaxBytes = sliderPosToBytes(sliderMaxPos);
        }
        const maxResult = bytesToUnit(sizeMaxBytes);
        sizeMaxInputValue = maxResult.value;
        sizeMaxUnit = maxResult.unit;
        applyFilter();
    }

    /** On mouseup: snap slider position to boundary if within threshold. */
    function finalizeSizeSliders() {
        if (sliderMinPos <= SNAP) sliderMinPos = 0;
        if (sliderMinPos >= 100 - SNAP) sliderMinPos = 100;
        if (sliderMaxPos >= 100 - SNAP) sliderMaxPos = 100;
        if (sliderMaxPos <= SNAP) sliderMaxPos = 0;
    }

    // Auto-apply for text filter with debounce
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    function autoApplyTextFilter() {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            applyFilter();
        }, 300);
    }

    function applyFilter() {
        let filter: FilterValue | null = null;

        if (type === 'text' && textValue.trim()) {
            filter = {type: 'text', value: textValue.trim(), matchMode: textMatchMode};
        } else if (type === 'number' && (numMin > numberMin || numMax < numberMax)) {
            filter = {type: 'number', min: numMin > numberMin ? numMin : undefined, max: numMax < numberMax ? numMax : undefined};
        } else if (type === 'size' && (sizeMinBytes > numberMin || sizeMaxBytes < numberMax)) {
            filter = {type: 'size', minBytes: sizeMinBytes > numberMin ? sizeMinBytes : undefined, maxBytes: sizeMaxBytes < numberMax ? sizeMaxBytes : undefined};
        } else if (type === 'date' && (dateFrom || dateTo)) {
            filter = {type: 'date', from: dateFrom || undefined, to: dateTo || undefined};
        } else if (type === 'enum' && selectedEnums.size < enumOptions.length && selectedEnums.size > 0) {
            filter = {type: 'enum', selected: Array.from(selectedEnums)};
        } else if (type === 'multi-enum' && multiEnums.size > 0) {
            filter = {type: 'multi-enum', selected: Array.from(multiEnums)};
        } else if (type === 'currency-stack' && currencyStack.length > 0) {
            filter = {type: 'currency-stack', items: currencyStack.map((i) => ({...i}))};
        }

        onApply(filter);
    }

    function clearFilter() {
        textValue = '';
        textMatchMode = 'contains';
        numMin = numberMin;
        numMax = numberMax;
        numSliderMinPos = 0;
        numSliderMaxPos = 100;
        dateFrom = '';
        dateTo = '';
        selectedEnums = new Set();
        multiEnums = new Set();
        multiEnumSearch = '';
        enumSearch = '';
        currencyStack = [];
        currencyToAdd = '';
        currencyOpenIdx = null;
        currencyMinPos = {};
        currencyMaxPos = {};
        sizeMinBytes = numberMin;
        sizeMaxBytes = numberMax;
        initSizeInputs();
        onApply(null);
    }

    function toggleEnum(value: string) {
        if (selectedEnums.has(value)) {
            selectedEnums.delete(value);
        } else {
            selectedEnums.add(value);
        }
        selectedEnums = new Set(selectedEnums);
        applyFilter();
    }

    function selectAllEnums() {
        selectedEnums = new Set(filteredEnumOptions.map((o) => o.value));
        applyFilter();
    }

    function clearAllEnums() {
        selectedEnums = new Set();
        applyFilter();
    }

    // ---- Multi-enum (tags-like) helpers ----
    function toggleMultiEnum(value: string) {
        if (multiEnums.has(value)) multiEnums.delete(value);
        else multiEnums.add(value);
        multiEnums = new Set(multiEnums);
        applyFilter();
    }
    function selectAllMultiEnums() {
        // Scoped to what the search left on screen, like `selectAllEnums`: ticking rows the user
        // filtered away would select things they can no longer see. With no query active,
        // `filteredMultiEnumOptions` is the whole list, so the plain "select all" is unchanged.
        //
        // It *adds* to the selection rather than replacing it. Replacing looks identical with no
        // query, but with one active it silently unticks everything the search is hiding — so
        // searching, ticking, searching again and ticking again would keep only the last batch.
        // That is "select only these" wearing the label "select all".
        multiEnums = new Set([...multiEnums, ...filteredMultiEnumOptions.map((o) => o.value)]);
        applyFilter();
    }
    function clearAllMultiEnums() {
        multiEnums = new Set();
        applyFilter();
    }

    /**
     * One "contains, case-insensitive, label OR hidden searchText" rule, shared by both the enum
     * and multi-enum lists so their search can never drift apart again. The multi-enum branch used
     * to match on the label alone, which left every option whose query lived only in `searchText`
     * (an ISIN standing behind an asset name, say) unreachable — the box looked live but filtered
     * nothing the user typed.
     */
    function optionMatchesQuery(option: EnumOption, rawQuery: string): boolean {
        const q = rawQuery.trim().toLowerCase();
        if (q === '') return true;
        return option.label.toLowerCase().includes(q) || (option.searchText?.toLowerCase().includes(q) ?? false);
    }
    let filteredMultiEnumOptions = $derived(multiEnumSearch.trim() === '' ? enumOptions : enumOptions.filter((o) => optionMatchesQuery(o, multiEnumSearch)));
    let filteredEnumOptions = $derived(enumSearch.trim() === '' ? enumOptions : enumOptions.filter((o) => optionMatchesQuery(o, enumSearch)));

    // ---- Currency-stack helpers ----
    /** Set of currency codes already in the stack (to exclude from the picker). */
    let usedCurrencies = $derived(new Set(currencyStack.map((i) => i.code)));
    function addCurrencyToStack(code: string) {
        if (!code || usedCurrencies.has(code)) return;
        currencyStack = [...currencyStack, {code}];
        currencyToAdd = '';
        applyFilter();
    }
    /**
     * Drops a currency row and keeps the index-keyed editor state aligned with it.
     *
     * The stack renders keyed by currency code, but the three pieces of editor state
     * around it — which row is expanded, and both slider thumb positions — are keyed
     * by array index. Removing a row from the middle shifts every later row down one
     * slot, so without re-indexing the next currency silently inherits the removed
     * one's thumbs: a row showing "any amount" with an empty min field would display
     * its predecessor's handle at 80%, and dragging from there produced a value the
     * user never aimed at. The expanded editor jumped to a different currency for the
     * same reason.
     */
    function removeCurrencyFromStack(idx: number) {
        currencyStack = currencyStack.filter((_, i) => i !== idx);
        currencyOpenIdx = currencyOpenIdx === null || currencyOpenIdx === idx ? null : currencyOpenIdx > idx ? currencyOpenIdx - 1 : currencyOpenIdx;
        currencyMinPos = shiftPositionsAfterRemoval(currencyMinPos, idx);
        currencyMaxPos = shiftPositionsAfterRemoval(currencyMaxPos, idx);
        applyFilter();
    }
    /** Drops `removedIdx` and slides every higher index down by one. */
    function shiftPositionsAfterRemoval(positions: Record<number, number>, removedIdx: number): Record<number, number> {
        const next: Record<number, number> = {};
        for (const [key, pos] of Object.entries(positions)) {
            const i = Number(key);
            if (i === removedIdx) continue;
            next[i > removedIdx ? i - 1 : i] = pos;
        }
        return next;
    }
    /** Reorders one currency row's bounds and repaints both handles. See {@link normalizeSizeBounds}. */
    function normalizeCurrencyBounds(idx: number) {
        const item = currencyStack[idx];
        if (!item) return;
        if (item.min != null && item.max != null && item.min > item.max) {
            currencyStack = currencyStack.map((it, i) => (i === idx ? {...it, min: item.max, max: item.min} : it));
        }
        const fixed = currencyStack[idx];
        currencyMinPos = {...currencyMinPos, [idx]: curNumToSliderPos(idx, fixed?.min ?? curRange(idx).min)};
        currencyMaxPos = {...currencyMaxPos, [idx]: curNumToSliderPos(idx, fixed?.max ?? curRange(idx).max)};
    }

    function updateCurrencyMin(idx: number, value: string) {
        const v = value === '' ? undefined : Number(value);
        currencyStack = currencyStack.map((it, i) => (i === idx ? {...it, min: Number.isFinite(v as number) ? (v as number) : undefined} : it));
        normalizeCurrencyBounds(idx);
        applyFilter();
    }
    function updateCurrencyMax(idx: number, value: string) {
        const v = value === '' ? undefined : Number(value);
        currencyStack = currencyStack.map((it, i) => (i === idx ? {...it, max: Number.isFinite(v as number) ? (v as number) : undefined} : it));
        normalizeCurrencyBounds(idx);
        applyFilter();
    }
    function updateCurrencyMinSlider(idx: number, pos: number, el: HTMLInputElement) {
        const maxP = curMaxPos(idx);
        // Clamp: prevent crossing
        if (pos > maxP) pos = maxP;
        // Force DOM thumb position (one-way `value={}` doesn't sync during drag)
        el.value = String(pos);
        currencyMinPos = {...currencyMinPos, [idx]: pos};
        // Compute value with snap (snap value, not position — position snaps on release)
        const r = curRange(idx);
        let v: number;
        if (pos <= SNAP) {
            v = r.min;
        } else if (pos >= 100 - SNAP) {
            v = r.max;
        } else {
            v = curSliderPosToNum(idx, pos);
        }
        currencyStack = currencyStack.map((it, i) => (i === idx ? {...it, min: v} : it));
        applyFilter();
    }
    function updateCurrencyMaxSlider(idx: number, pos: number, el: HTMLInputElement) {
        const minP = curMinPos(idx);
        if (pos < minP) pos = minP;
        el.value = String(pos);
        currencyMaxPos = {...currencyMaxPos, [idx]: pos};
        const r = curRange(idx);
        let v: number;
        if (pos >= 100 - SNAP) {
            v = r.max;
        } else if (pos <= SNAP) {
            v = r.min;
        } else {
            v = curSliderPosToNum(idx, pos);
        }
        currencyStack = currencyStack.map((it, i) => (i === idx ? {...it, max: v} : it));
        applyFilter();
    }
    /** On mouseup: snap slider thumb position to boundary if within threshold. */
    function finalizeCurrencySlider(idx: number, el: HTMLInputElement, role: 'min' | 'max') {
        if (role === 'min') {
            let p = curMinPos(idx);
            if (p <= SNAP) p = 0;
            else if (p >= 100 - SNAP) p = 100;
            currencyMinPos = {...currencyMinPos, [idx]: p};
            el.value = String(p);
        } else {
            let p = curMaxPos(idx);
            if (p >= 100 - SNAP) p = 100;
            else if (p <= SNAP) p = 0;
            currencyMaxPos = {...currencyMaxPos, [idx]: p};
            el.value = String(p);
        }
    }

    // Click outside to close
    function handleClickOutside(event: MouseEvent) {
        const target = event.target as HTMLElement;
        if (target.closest('.filter-btn')) return;
        // Skip clicks inside any combobox/listbox option (e.g. the
        // CurrencySearchSelect dropdown used by the currency-stack filter
        // mounts options outside `popoverElement`). Without this guard the
        // popover closes on every option click (W27).
        if (target.closest('[role="listbox"], [role="option"], [role="combobox"]')) return;
        if (popoverElement && !popoverElement.contains(target)) {
            onClose();
        }
    }

    onMount(() => {
        if (type === 'size') {
            initSizeInputs();
        }

        // Calculate fixed position from anchor element
        if (anchorElement) {
            const updatePosition = () => {
                const rect = anchorElement!.getBoundingClientRect();
                // Never let the popover be wider than the viewport (minus a safety
                // margin on each side) — narrow/mobile screens otherwise get a
                // popover wider than the screen itself.
                const maxPopW = window.innerWidth - DROPDOWN_VIEWPORT_MARGIN * 2;
                const popW = Math.min(popoverElement?.offsetWidth ?? 240, maxPopW);
                const popH = popoverElement?.offsetHeight ?? 300;
                // Clamp horizontal position on BOTH edges — previously only the right
                // edge was guarded, so a popover wider than the viewport (or anchored
                // near the left edge) could still spill off-screen to the left.
                const minLeft = DROPDOWN_VIEWPORT_MARGIN;
                const maxLeft = Math.max(minLeft, window.innerWidth - popW - DROPDOWN_VIEWPORT_MARGIN);
                const left = clamp(rect.left, minLeft, maxLeft);
                // Smart top/bottom: open upward if not enough space below
                const spaceBelow = window.innerHeight - rect.bottom - 8;
                const openAbove = spaceBelow < popH && rect.top > popH;
                const top = openAbove ? rect.top - popH - 4 : rect.bottom + 4;
                popoverStyle = `position: fixed; top: ${top}px; left: ${left}px; max-width: ${maxPopW}px;`;
            };
            updatePosition();
            // Re-measure after first render to get actual popover height
            requestAnimationFrame(updatePosition);
            // Close on scroll (parent containers + window)
            const scrollParent = anchorElement!.closest('.table-wrapper');
            const handleScroll = () => {
                const rect = anchorElement!.getBoundingClientRect();
                if (rect.bottom < 0 || rect.top > window.innerHeight) {
                    onClose();
                } else {
                    updatePosition();
                }
            };
            scrollParent?.addEventListener('scroll', handleScroll);
            window.addEventListener('scroll', handleScroll, true);
            window.addEventListener('resize', updatePosition);

            const timer = setTimeout(() => {
                document.addEventListener('click', handleClickOutside, true);
            }, 100);

            return () => {
                clearTimeout(timer);
                document.removeEventListener('click', handleClickOutside, true);
                scrollParent?.removeEventListener('scroll', handleScroll);
                window.removeEventListener('scroll', handleScroll, true);
                window.removeEventListener('resize', updatePosition);
                if (debounceTimer) clearTimeout(debounceTimer);
            };
        }

        const timer = setTimeout(() => {
            document.addEventListener('click', handleClickOutside, true);
        }, 100);

        return () => {
            clearTimeout(timer);
            document.removeEventListener('click', handleClickOutside, true);
            if (debounceTimer) clearTimeout(debounceTimer);
        };
    });
</script>

<div bind:this={popoverElement} class="filter-popover" style={popoverStyle} transition:fade={{duration: 100}} data-testid="column-filter" data-filter-type={type}>
    <div class="filter-header">
        <span class="filter-title">{$t('table.filterLabel')}</span>
        <button class="reset-btn" onclick={clearFilter} title={$t('common.clear')} type="button" data-testid="column-filter-reset">
            <RotateCcw size={14} />
        </button>
    </div>

    <div class="filter-body">
        {#if type === 'text'}
            <div class="text-filter">
                <div class="search-input-wrapper">
                    <Search size={14} class="search-icon" />
                    <input type="text" class="filter-input" placeholder={$t('common.search')} bind:value={textValue} oninput={autoApplyTextFilter} id="text-filter-input" data-testid="filter-text-input" />
                    {#if textValue}
                        <button
                            type="button"
                            class="clear-input-btn"
                            data-testid="filter-text-clear"
                            onclick={() => {
                                textValue = '';
                                applyFilter();
                            }}
                        >
                            <X size={12} />
                        </button>
                    {/if}
                </div>
                <select class="match-mode-select" bind:value={textMatchMode} onchange={applyFilter} id="text-match-mode-select" data-testid="filter-text-match-mode">
                    <option value="contains">{$t('filter.contains')}</option>
                    <option value="startsWith">{$t('filter.startsWith')}</option>
                    <option value="endsWith">{$t('filter.endsWith')}</option>
                    <option value="equals">{$t('filter.equals')}</option>
                </select>
            </div>
        {:else if type === 'number'}
            <div class="number-filter">
                <div class="range-row">
                    <label class="range-label" for="number-min-input">{$t('common.min')}</label>
                    <input
                        type="number"
                        use:numericArrows
                        step={isIntegerRange ? '1' : 'any'}
                        class="range-input"
                        bind:this={numMinInputEl}
                        bind:value={numMin}
                        min={numberMin}
                        max={numberMax}
                        onchange={() => {
                            const swapped = numMin > numMax;
                            syncNumSlidersFromInput();
                            applyFilter();
                            if (swapped) void followSwap(numMaxInputEl);
                        }}
                        id="number-min-input"
                        data-testid="filter-number-min"
                    />
                </div>
                <div class="range-row">
                    <label class="range-label" for="number-max-input">{$t('common.max')}</label>
                    <input
                        type="number"
                        use:numericArrows
                        step={isIntegerRange ? '1' : 'any'}
                        class="range-input"
                        bind:this={numMaxInputEl}
                        bind:value={numMax}
                        min={numberMin}
                        max={numberMax}
                        onchange={() => {
                            const swapped = numMin > numMax;
                            syncNumSlidersFromInput();
                            applyFilter();
                            if (swapped) void followSwap(numMinInputEl);
                        }}
                        id="number-max-input"
                        data-testid="filter-number-max"
                    />
                </div>
                <!-- Dual range slider -->
                <div class="size-slider-container">
                    <div class="size-slider-track">
                        <div class="size-slider-range" style="left: {numSliderMinPos}%; right: {100 - numSliderMaxPos}%"></div>
                        <div class="slider-tick" style="left: 25%"></div>
                        <div class="slider-tick" style="left: 50%"></div>
                        <div class="slider-tick" style="left: 75%"></div>
                    </div>
                    <input type="range" class="size-slider size-slider-min" min="0" max="100" bind:value={numSliderMinPos} oninput={updateNumMinFromSlider} onchange={finalizeNumSliders} data-testid="filter-number-slider-min" />
                    <input type="range" class="size-slider size-slider-max" min="0" max="100" bind:value={numSliderMaxPos} oninput={updateNumMaxFromSlider} onchange={finalizeNumSliders} data-testid="filter-number-slider-max" />
                </div>

                <!-- Slider labels with intermediate values -->
                <div class="size-slider-labels">
                    <span>{fmtNum(numberMin)}</span>
                    <span class="slider-label-mid">{fmtNum(sliderPosToNum(25))}</span>
                    <span class="slider-label-mid">{fmtNum(sliderPosToNum(50))}</span>
                    <span class="slider-label-mid">{fmtNum(sliderPosToNum(75))}</span>
                    <span>{fmtNum(numberMax)}</span>
                </div>
            </div>
        {:else if type === 'size'}
            <div class="size-filter">
                <!-- Min size input -->
                <div class="size-row">
                    <label class="size-label" for="size-min-input">{$t('common.min')}</label>
                    <div class="size-input-group">
                        <input type="number" use:numericArrows class="size-input" id="size-min-input" bind:this={sizeMinInputEl} bind:value={sizeMinInputValue} min="0" onchange={updateSizeMinFromInput} data-testid="filter-size-min" />
                        <select class="size-unit-select" bind:value={sizeMinUnit} onchange={updateSizeMinFromInput} data-testid="filter-size-min-unit">
                            {#each SIZE_UNITS as u}
                                <option value={u.unit}>{u.label}</option>
                            {/each}
                        </select>
                    </div>
                </div>

                <!-- Max size input -->
                <div class="size-row">
                    <label class="size-label" for="size-max-input">{$t('common.max')}</label>
                    <div class="size-input-group">
                        <input type="number" use:numericArrows class="size-input" id="size-max-input" bind:this={sizeMaxInputEl} bind:value={sizeMaxInputValue} min="0" onchange={updateSizeMaxFromInput} data-testid="filter-size-max" />
                        <select class="size-unit-select" bind:value={sizeMaxUnit} onchange={updateSizeMaxFromInput} data-testid="filter-size-max-unit">
                            {#each SIZE_UNITS as u}
                                <option value={u.unit}>{u.label}</option>
                            {/each}
                        </select>
                    </div>
                </div>

                <!-- Dual range slider -->
                <div class="size-slider-container">
                    <div class="size-slider-track">
                        <div class="size-slider-range" style="left: {sliderMinPos}%; right: {100 - sliderMaxPos}%"></div>
                        <!-- Tick marks at 25%, 50%, 75% -->
                        <div class="slider-tick" style="left: 25%"></div>
                        <div class="slider-tick" style="left: 50%"></div>
                        <div class="slider-tick" style="left: 75%"></div>
                    </div>
                    <input type="range" class="size-slider size-slider-min" min="0" max="100" bind:value={sliderMinPos} oninput={updateSizeMinFromSlider} onchange={finalizeSizeSliders} data-testid="filter-size-slider-min" />
                    <input type="range" class="size-slider size-slider-max" min="0" max="100" bind:value={sliderMaxPos} oninput={updateSizeMaxFromSlider} onchange={finalizeSizeSliders} data-testid="filter-size-slider-max" />
                </div>

                <!-- Slider labels with intermediate values -->
                <div class="size-slider-labels">
                    <span>{formatBytes(numberMin)}</span>
                    <span class="slider-label-mid">{formatBytes(sliderPosToBytes(25))}</span>
                    <span class="slider-label-mid">{formatBytes(sliderPosToBytes(50))}</span>
                    <span class="slider-label-mid">{formatBytes(sliderPosToBytes(75))}</span>
                    <span>{formatBytes(numberMax)}</span>
                </div>
            </div>
        {:else if type === 'date'}
            <div class="date-filter">
                <DateRangePicker
                    start={dateFrom}
                    end={dateTo}
                    showPresets={false}
                    showCustomWindow={false}
                    compact={true}
                    stacked={true}
                    onchange={(s, e) => {
                        dateFrom = s;
                        dateTo = e;
                        applyFilter();
                    }}
                />
            </div>
        {:else if type === 'enum'}
            <div class="enum-filter">
                <div class="enum-actions">
                    <button type="button" class="enum-action-btn" onclick={selectAllEnums} data-testid="filter-enum-select-all">{$t('common.selectAll')}</button>
                    <button type="button" class="enum-action-btn" onclick={clearAllEnums} data-testid="filter-enum-clear-all">{$t('common.clearAll')}</button>
                </div>
                <div class="search-input-wrapper">
                    <Search size={14} class="search-icon" />
                    <input type="text" class="filter-input" placeholder={$t('common.search')} bind:value={enumSearch} data-testid="filter-enum-search" />
                    {#if enumSearch}
                        <button type="button" class="clear-input-btn" onclick={() => (enumSearch = '')} data-testid="filter-enum-search-clear">
                            <X size={12} />
                        </button>
                    {/if}
                </div>
                <div class="enum-list">
                    {#if filteredEnumOptions.length === 0}
                        <div class="enum-empty" data-testid="filter-enum-empty">{$t('table.filter.empty') || 'No options'}</div>
                    {:else}
                        {#each filteredEnumOptions as option}
                            {@const iconCandidates = option.iconCandidates?.length ? option.iconCandidates : option.iconUrl ? [option.iconUrl] : []}
                            <button type="button" class="enum-option" onclick={() => toggleEnum(option.value)} data-testid={`filter-enum-option-${option.value}`} data-checked={selectedEnums.has(option.value)}>
                                <span class="enum-checkbox" class:checked={selectedEnums.has(option.value)}>
                                    {#if selectedEnums.has(option.value)}
                                        <Check size={12} />
                                    {/if}
                                </span>
                                <span class="enum-icon-wrapper">
                                    {#if option.dotColor}
                                        <span class="enum-option-dot" style="background:{option.dotColor}"></span>
                                    {/if}
                                    {#if iconCandidates.length > 0}
                                        <img src={iconCandidates[0]} alt="" class="enum-option-icon enum-icon-overlay" data-fallbacks={JSON.stringify(iconCandidates.slice(1))} onerror={handleEnumIconError} referrerpolicy="no-referrer" />
                                    {/if}
                                </span>
                                <span use:scrollOnOverflow class="enum-label {overflowScrollTextClass}" title={option.label}>{option.label}</span>
                                {#if option.count != null}
                                    <span class="enum-count">{option.count}</span>
                                {/if}
                            </button>
                        {/each}
                    {/if}
                </div>
            </div>
        {:else if type === 'multi-enum'}
            <div class="enum-filter">
                <div class="enum-actions">
                    <button type="button" class="enum-action-btn" onclick={selectAllMultiEnums} data-testid="filter-multi-enum-select-all">{$t('common.selectAll')}</button>
                    <button type="button" class="enum-action-btn" onclick={clearAllMultiEnums} data-testid="filter-multi-enum-clear-all">{$t('common.clearAll')}</button>
                </div>
                <div class="search-input-wrapper">
                    <Search size={14} class="search-icon" />
                    <input type="text" class="filter-input" placeholder={$t('common.search')} bind:value={multiEnumSearch} data-testid="filter-multi-enum-search" />
                    {#if multiEnumSearch}
                        <button type="button" class="clear-input-btn" onclick={() => (multiEnumSearch = '')} data-testid="filter-multi-enum-search-clear">
                            <X size={12} />
                        </button>
                    {/if}
                </div>
                <div class="enum-list">
                    {#if filteredMultiEnumOptions.length === 0}
                        <div class="enum-empty" data-testid="filter-multi-enum-empty">{$t('table.filter.empty') || 'No options'}</div>
                    {:else}
                        {#each filteredMultiEnumOptions as option}
                            {@const iconCandidates = option.iconCandidates?.length ? option.iconCandidates : option.iconUrl ? [option.iconUrl] : []}
                            <button type="button" class="enum-option" onclick={() => toggleMultiEnum(option.value)} data-testid={`filter-multi-enum-option-${option.value}`} data-checked={multiEnums.has(option.value)}>
                                <span class="enum-checkbox" class:checked={multiEnums.has(option.value)}>
                                    {#if multiEnums.has(option.value)}
                                        <Check size={12} />
                                    {/if}
                                </span>
                                <span class="enum-icon-wrapper">
                                    {#if option.dotColor}
                                        <span class="enum-option-dot" style="background:{option.dotColor}"></span>
                                    {/if}
                                    {#if iconCandidates.length > 0}
                                        <img src={iconCandidates[0]} alt="" class="enum-option-icon enum-icon-overlay" data-fallbacks={JSON.stringify(iconCandidates.slice(1))} onerror={handleEnumIconError} referrerpolicy="no-referrer" />
                                    {/if}
                                </span>
                                <span use:scrollOnOverflow class="enum-label {overflowScrollTextClass}" title={option.label}>{option.label}</span>
                                {#if option.count != null}
                                    <span class="enum-count">{option.count}</span>
                                {/if}
                            </button>
                        {/each}
                    {/if}
                </div>
            </div>
        {:else if type === 'currency-stack'}
            <div class="currency-stack-filter">
                <div class="currency-add-row">
                    <CurrencySearchSelect
                        bind:value={currencyToAdd}
                        compact={true}
                        excludedCurrencies={usedCurrencies}
                        allowedCurrencies={currencyOptions.length > 0 ? currencyOptions : undefined}
                        placeholder={$t('table.filter.currencyStack.addCurrency') || 'Add currency…'}
                        onchange={(v) => addCurrencyToStack(v)}
                    />
                </div>
                {#if currencyStack.length === 0}
                    <div class="currency-stack-empty" data-testid="filter-currency-empty">{$t('table.filter.currencyStack.empty') || 'Pick a currency to add a numeric range filter.'}</div>
                {:else}
                    <ul class="currency-stack-list">
                        {#each currencyStack as item, idx (item.code)}
                            <li class="currency-stack-row" data-testid={`filter-currency-row-${item.code}`}>
                                <span class="currency-stack-code">{@html formatCurrencyCodeHtml(item.code)}</span>
                                <span class="currency-stack-range">
                                    {#if item.min != null || item.max != null}
                                        {item.min != null ? fmtNum(item.min) : '−∞'} … {item.max != null ? fmtNum(item.max) : '+∞'}
                                    {:else}
                                        <span class="currency-stack-any">{$t('table.filter.currencyStack.any') || 'any amount'}</span>
                                    {/if}
                                </span>
                                <button type="button" class="currency-stack-btn" title={$t('table.filterLabel') || 'Filter'} onclick={() => (currencyOpenIdx = currencyOpenIdx === idx ? null : idx)} data-testid={`filter-currency-funnel-${item.code}`}>
                                    <FilterIcon size={12} />
                                </button>
                                <button type="button" class="currency-stack-btn danger" title={$t('common.delete') || 'Delete'} onclick={() => removeCurrencyFromStack(idx)} data-testid={`filter-currency-trash-${item.code}`}>
                                    <Trash2 size={12} />
                                </button>
                                {#if currencyOpenIdx === idx}
                                    {@const r = curRange(idx)}
                                    <div class="currency-stack-range-editor number-filter" data-testid={`filter-currency-editor-${item.code}`}>
                                        <div class="range-row">
                                            <label class="range-label" for={`cur-min-${idx}`}>{$t('common.min')}</label>
                                            <input type="number" use:numericArrows class="range-input" id={`cur-min-${idx}`} value={item.min ?? ''} onchange={(e) => updateCurrencyMin(idx, e.currentTarget.value)} data-testid={`filter-currency-min-${item.code}`} />
                                        </div>
                                        <div class="range-row">
                                            <label class="range-label" for={`cur-max-${idx}`}>{$t('common.max')}</label>
                                            <input type="number" use:numericArrows class="range-input" id={`cur-max-${idx}`} value={item.max ?? ''} onchange={(e) => updateCurrencyMax(idx, e.currentTarget.value)} data-testid={`filter-currency-max-${item.code}`} />
                                        </div>
                                        <!-- Linear dual range slider — same UX as `type:'number'`, scoped to per-currency min/max. -->
                                        <div class="size-slider-container">
                                            <div class="size-slider-track">
                                                <div class="size-slider-range" style="left: {curMinPos(idx)}%; right: {100 - curMaxPos(idx)}%"></div>
                                                <div class="slider-tick" style="left: 25%"></div>
                                                <div class="slider-tick" style="left: 50%"></div>
                                                <div class="slider-tick" style="left: 75%"></div>
                                            </div>
                                            <input
                                                type="range"
                                                class="size-slider size-slider-min"
                                                min="0"
                                                max="100"
                                                value={curMinPos(idx)}
                                                oninput={(e) => updateCurrencyMinSlider(idx, Number(e.currentTarget.value), e.currentTarget)}
                                                onchange={(e) => finalizeCurrencySlider(idx, e.currentTarget, 'min')}
                                                data-testid="filter-currency-slider-min-{item.code}"
                                            />
                                            <input
                                                type="range"
                                                class="size-slider size-slider-max"
                                                min="0"
                                                max="100"
                                                value={curMaxPos(idx)}
                                                oninput={(e) => updateCurrencyMaxSlider(idx, Number(e.currentTarget.value), e.currentTarget)}
                                                onchange={(e) => finalizeCurrencySlider(idx, e.currentTarget, 'max')}
                                                data-testid="filter-currency-slider-max-{item.code}"
                                            />
                                        </div>
                                        <div class="size-slider-labels">
                                            <span>{fmtNum(r.min)}</span>
                                            <span class="slider-label-mid">{fmtNum(curSliderPosToNum(idx, 25))}</span>
                                            <span class="slider-label-mid">{fmtNum(curSliderPosToNum(idx, 50))}</span>
                                            <span class="slider-label-mid">{fmtNum(curSliderPosToNum(idx, 75))}</span>
                                            <span>{fmtNum(r.max)}</span>
                                        </div>
                                    </div>
                                {/if}
                            </li>
                        {/each}
                    </ul>
                {/if}
            </div>
        {/if}
    </div>
</div>

<style>
    .filter-popover {
        position: absolute;
        top: 100%;
        left: 0;
        margin-top: 0.25rem;
        min-width: 240px;
        box-sizing: border-box;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        box-shadow:
            0 10px 15px -3px rgba(0, 0, 0, 0.1),
            0 4px 6px -4px rgba(0, 0, 0, 0.1);
        z-index: 9999;
    }

    :global(.dark) .filter-popover {
        background: #1e293b;
        border-color: #334155;
    }

    .filter-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #e2e8f0;
    }

    :global(.dark) .filter-header {
        border-bottom-color: #334155;
    }

    .filter-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
    }

    :global(.dark) .filter-title {
        color: #94a3b8;
    }

    .reset-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border: none;
        border-radius: 4px;
        background: transparent;
        color: #64748b;
        cursor: pointer;
        transition: all 0.15s;
    }

    .reset-btn:hover {
        background: #f1f5f9;
        color: #0f172a;
    }

    :global(.dark) .reset-btn:hover {
        background: #334155;
        color: #f1f5f9;
    }

    .filter-body {
        padding: 0.75rem;
    }

    /* Text filter */
    .search-input-wrapper {
        position: relative;
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .search-input-wrapper :global(.search-icon) {
        position: absolute;
        left: 0.5rem;
        color: #94a3b8;
        pointer-events: none;
    }

    .filter-input {
        width: 100%;
        padding: 0.375rem 1.75rem;
        font-size: 0.8125rem;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        background: white;
        color: #0f172a;
    }

    :global(.dark) .filter-input {
        background: #0f172a;
        border-color: #334155;
        color: #f1f5f9;
    }

    .filter-input:focus {
        outline: none;
        border-color: #1a4031;
    }

    :global(.dark) .filter-input:focus {
        border-color: #4ade80;
    }

    .clear-input-btn {
        position: absolute;
        right: 0.375rem;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        border: none;
        border-radius: 50%;
        background: #e2e8f0;
        color: #64748b;
        cursor: pointer;
    }

    .clear-input-btn:hover {
        background: #cbd5e1;
        color: #0f172a;
    }

    :global(.dark) .clear-input-btn {
        background: #475569;
        color: #94a3b8;
    }

    :global(.dark) .clear-input-btn:hover {
        background: #64748b;
        color: #f1f5f9;
    }

    .match-mode-select {
        width: 100%;
        padding: 0.375rem 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        background: white;
        color: #0f172a;
        cursor: pointer;
    }

    :global(.dark) .match-mode-select {
        background: #0f172a;
        border-color: #334155;
        color: #f1f5f9;
    }

    /* Number/Date filter */
    .number-filter,
    .date-filter {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .range-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .range-label {
        min-width: 35px;
        font-size: 0.75rem;
        color: #64748b;
    }

    :global(.dark) .range-label {
        color: #94a3b8;
    }

    .range-input {
        flex: 1;
        padding: 0.375rem 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        background: white;
        color: #0f172a;
    }

    :global(.dark) .range-input {
        background: #0f172a;
        border-color: #334155;
        color: #f1f5f9;
    }

    .range-input:focus {
        outline: none;
        border-color: #1a4031;
    }

    :global(.dark) .range-input:focus {
        border-color: #4ade80;
    }

    /* Size filter */
    .size-filter {
        display: flex;
        flex-direction: column;
        gap: 0.625rem;
    }

    .size-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .size-label {
        min-width: 30px;
        font-size: 0.75rem;
        color: #64748b;
    }

    :global(.dark) .size-label {
        color: #94a3b8;
    }

    .size-input-group {
        display: flex;
        flex: 1;
        gap: 0.25rem;
    }

    .size-input {
        flex: 1;
        min-width: 60px;
        padding: 0.375rem 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid #e2e8f0;
        border-radius: 6px 0 0 6px;
        background: white;
        color: #0f172a;
    }

    :global(.dark) .size-input {
        background: #0f172a;
        border-color: #334155;
        color: #f1f5f9;
    }

    .size-input:focus {
        outline: none;
        border-color: #1a4031;
    }

    :global(.dark) .size-input:focus {
        border-color: #4ade80;
    }

    .size-unit-select {
        width: 55px;
        padding: 0.375rem 0.25rem;
        font-size: 0.75rem;
        border: 1px solid #e2e8f0;
        border-left: none;
        border-radius: 0 6px 6px 0;
        background: #f8fafc;
        color: #0f172a;
        cursor: pointer;
    }

    :global(.dark) .size-unit-select {
        background: #1e293b;
        border-color: #334155;
        color: #f1f5f9;
    }

    /* Dual range slider */
    .size-slider-container {
        position: relative;
        height: 24px;
        margin-top: 0.5rem;
    }

    .size-slider-track {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 4px;
        background: #e2e8f0;
        border-radius: 2px;
        transform: translateY(-50%);
        overflow: visible;
    }

    :global(.dark) .size-slider-track {
        background: #475569;
    }

    .size-slider-range {
        position: absolute;
        top: 0;
        bottom: 0;
        background: #1a4031;
        border-radius: 2px;
    }

    :global(.dark) .size-slider-range {
        background: #4ade80;
    }

    .slider-tick {
        position: absolute;
        top: -4px;
        width: 2px;
        height: 12px;
        background: #94a3b8;
        transform: translateX(-50%);
        z-index: 1;
        border-radius: 1px;
    }

    :global(.dark) .slider-tick {
        background: #64748b;
    }

    .size-slider {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        -webkit-appearance: none;
        appearance: none;
        background: transparent;
        pointer-events: none;
    }

    .size-slider::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 16px;
        height: 16px;
        background: #1a4031;
        border: 2px solid white;
        border-radius: 50%;
        cursor: pointer;
        pointer-events: auto;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }

    :global(.dark) .size-slider::-webkit-slider-thumb {
        background: #4ade80;
        border-color: #0f172a;
    }

    .size-slider::-moz-range-thumb {
        width: 16px;
        height: 16px;
        background: #1a4031;
        border: 2px solid white;
        border-radius: 50%;
        cursor: pointer;
        pointer-events: auto;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }

    :global(.dark) .size-slider::-moz-range-thumb {
        background: #4ade80;
        border-color: #0f172a;
    }

    .size-slider-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.5625rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }

    .slider-label-mid {
        opacity: 0.7;
    }

    /* Enum filter */
    .enum-actions {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .enum-action-btn {
        flex: 1;
        padding: 0.25rem 0.5rem;
        font-size: 0.6875rem;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        background: #f8fafc;
        color: #64748b;
        cursor: pointer;
        transition: all 0.15s;
    }

    .enum-action-btn:hover {
        background: #f1f5f9;
        color: #0f172a;
    }

    :global(.dark) .enum-action-btn {
        background: #0f172a;
        border-color: #334155;
        color: #94a3b8;
    }

    :global(.dark) .enum-action-btn:hover {
        background: #1e293b;
        color: #f1f5f9;
    }

    .enum-list {
        max-height: 180px;
        overflow-y: auto;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
    }

    :global(.dark) .enum-list {
        border-color: #334155;
    }

    .enum-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        width: 100%;
        padding: 0.375rem 0.5rem;
        border: none;
        background: transparent;
        color: #475569;
        font-size: 0.8125rem;
        text-align: left;
        cursor: pointer;
        transition: background 0.15s;
    }

    .enum-option:hover {
        background: #f8fafc;
    }

    :global(.dark) .enum-option {
        color: #e2e8f0;
    }

    :global(.dark) .enum-option:hover {
        background: #334155;
    }

    .enum-checkbox {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 16px;
        height: 16px;
        border: 1px solid #cbd5e1;
        border-radius: 3px;
        background: white;
        transition: all 0.15s;
    }

    .enum-checkbox.checked {
        background: #1a4031;
        border-color: #1a4031;
        color: white;
    }

    :global(.dark) .enum-checkbox {
        background: #0f172a;
        border-color: #475569;
    }

    :global(.dark) .enum-checkbox.checked {
        background: #4ade80;
        border-color: #4ade80;
        color: #0f172a;
    }

    .enum-empty {
        padding: 0.5rem;
        font-size: 0.75rem;
        color: #94a3b8;
        text-align: center;
        max-width: 200px;
        margin: 0 auto;
        /* .filter-popover is rendered inside the column <th> in the DOM (only escaped
         * visually via position:fixed) and th { white-space: nowrap } in DataTable.svelte
         * is inherited straight through — max-width alone can't wrap text while nowrap
         * is still inherited, so it must be reset explicitly here. */
        white-space: normal;
    }

    /* flex/min-width let this shrink inside .enum-option instead of forcing the row (and
     * the whole popover) wider than intended; overflow-x-hidden/whitespace-nowrap/block come
     * from overflowScrollTextClass (applied in the markup) for the auto-scroll marquee —
     * same pattern as AssetCard/BrokerCard/KpiCard for long names. */
    .enum-label {
        flex: 1 1 auto;
        min-width: 0;
    }

    .enum-option-icon {
        width: 1rem;
        height: 1rem;
        object-fit: contain;
        flex-shrink: 0;
        border-radius: 2px;
    }

    /* Overlay wrapper: dot as background, img absolutely positioned on top */
    .enum-icon-wrapper {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1rem;
        height: 1rem;
        flex-shrink: 0;
    }

    .enum-icon-wrapper .enum-option-dot {
        position: absolute;
    }

    .enum-icon-wrapper .enum-option-icon {
        position: absolute;
        width: 1rem;
        height: 1rem;
    }

    .enum-option-dot {
        display: inline-block;
        width: 0.625rem;
        height: 0.625rem;
        border-radius: 9999px;
        flex-shrink: 0;
        box-shadow: 0 0 0 1px rgb(0 0 0 / 0.06);
    }

    :global(.dark) .enum-option-dot {
        box-shadow: 0 0 0 1px rgb(255 255 255 / 0.08);
    }

    .enum-count {
        margin-left: auto;
        font-size: 0.6875rem;
        font-variant-numeric: tabular-nums;
        color: #94a3b8;
        background: #f1f5f9;
        padding: 0 0.35rem;
        border-radius: 9999px;
        min-width: 1.25rem;
        text-align: center;
        line-height: 1.4;
    }

    :global(.dark) .enum-count {
        color: #64748b;
        background: #334155;
    }

    /* Currency-stack filter */
    .currency-stack-filter {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        min-width: min(280px, 100%);
    }
    .currency-add-row {
        display: flex;
        align-items: center;
    }
    .currency-stack-empty {
        font-size: 0.75rem;
        color: #94a3b8;
        text-align: center;
        padding: 0.5rem;
        max-width: 200px;
        margin: 0 auto;
        /* Same inherited-nowrap issue as .enum-empty above — reset explicitly. */
        white-space: normal;
    }
    .currency-stack-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    .currency-stack-row {
        position: relative;
        display: grid;
        grid-template-columns: auto 1fr auto auto;
        align-items: center;
        gap: 0.4rem;
        padding: 0.3rem 0.5rem;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        background: #f8fafc;
    }
    :global(.dark) .currency-stack-row {
        background: #0f172a;
        border-color: #334155;
    }
    .currency-stack-code {
        font-weight: 600;
        font-size: 0.75rem;
        color: #1a4031;
    }
    :global(.dark) .currency-stack-code {
        color: #4ade80;
    }
    .currency-stack-range {
        font-size: 0.75rem;
        color: #475569;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 120px;
    }
    :global(.dark) .currency-stack-range {
        color: #cbd5e1;
    }
    .currency-stack-any {
        color: #94a3b8;
        font-style: italic;
    }
    .currency-stack-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border: 1px solid transparent;
        border-radius: 4px;
        background: transparent;
        color: #64748b;
        cursor: pointer;
        transition: all 0.15s;
    }
    .currency-stack-btn:hover {
        background: #e2e8f0;
        color: #0f172a;
    }
    :global(.dark) .currency-stack-btn:hover {
        background: #334155;
        color: #f1f5f9;
    }
    .currency-stack-btn.danger:hover {
        background: #fee2e2;
        color: #b91c1c;
    }
    :global(.dark) .currency-stack-btn.danger:hover {
        background: #7f1d1d;
        color: #fecaca;
    }
    .currency-stack-range-editor {
        grid-column: 1 / -1;
        margin-top: 0.4rem;
        padding-top: 0.4rem;
        border-top: 1px dashed #e2e8f0;
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }
    :global(.dark) .currency-stack-range-editor {
        border-top-color: #334155;
    }
</style>
