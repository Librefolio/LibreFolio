<script lang="ts">
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {exactDecimalArrowStep, filterDecimalInput, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';

    interface Props {
        value?: string;
        step?: string;
        maxIntegerDigits?: number;
        maxFractionDigits?: number;
        allowNegative?: boolean;
        disabled?: boolean;
        placeholder?: string;
        ariaLabel?: string;
        testid?: string;
        className?: string;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), step = '1', maxIntegerDigits = 12, maxFractionDigits = 12, allowNegative = false, disabled = false, placeholder = '', ariaLabel, testid, className = '', onchange}: Props = $props();
    let inputEl = $state<HTMLInputElement | null>(null);

    function normalizedParts(candidate: string): {normalized: string; valid: boolean} {
        const trimmed = candidate.trim();
        if (trimmed === '') return {normalized: '', valid: true};
        if (!/^-?[\d\s.,]*$/.test(trimmed)) return {normalized: candidate, valid: false};
        const normalized = normalizeDecimalInput(trimmed);
        if (!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) return {normalized, valid: false};
        if (!allowNegative && normalized.startsWith('-')) return {normalized, valid: false};
        const unsigned = normalized.startsWith('-') ? normalized.slice(1) : normalized;
        const [integer = '', fraction = ''] = unsigned.split('.');
        return {
            normalized,
            valid: (integer || '0').length <= maxIntegerDigits && fraction.length <= maxFractionDigits,
        };
    }

    let locallyInvalid = $derived(!normalizedParts(value).valid);

    function commit(): void {
        const parsed = normalizedParts(value);
        if (!parsed.valid || parsed.normalized === '') return;
        const next = formatDecimalForDisplay(parsed.normalized, {maxFrac: maxFractionDigits});
        if (next === value) return;
        value = next;
        if (inputEl) inputEl.value = next;
        onchange?.(next);
    }

    function handleInput(event: Event): void {
        const target = event.currentTarget;
        if (!(target instanceof HTMLInputElement)) return;
        const filtered = filterDecimalInput(target.value, allowNegative);
        if (filtered !== target.value) target.value = filtered;
        value = filtered;
        onchange?.(value);
    }

    function stepValue(event: KeyboardEvent): void {
        const next = exactDecimalArrowStep(event, value, step);
        if (next === null) {
            if (event.key === 'Enter') commit();
            return;
        }
        const constrained = !allowNegative && next.startsWith('-') ? '0' : next;
        value = constrained;
        onchange?.(constrained);
    }
</script>

<input
    bind:this={inputEl}
    type="text"
    inputmode="decimal"
    autocomplete="off"
    spellcheck="false"
    maxlength={maxIntegerDigits + maxFractionDigits + 3}
    bind:value
    {disabled}
    {placeholder}
    aria-label={ariaLabel}
    aria-invalid={locallyInvalid}
    data-testid={testid}
    oninput={handleInput}
    onblur={commit}
    onkeydown={stepValue}
    class={`w-full rounded-lg border bg-white px-3 py-2 font-mono text-gray-900 outline-none transition-colors focus:border-libre-green focus:ring-1 focus:ring-libre-green disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gray-900 dark:text-gray-100 ${
        locallyInvalid ? 'border-red-400 dark:border-red-500' : 'border-gray-300 dark:border-gray-600'
    } ${className}`}
/>
