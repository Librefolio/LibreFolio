<script lang="ts">
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {filterDecimalInput, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import {ArrowHold} from '$lib/utils/core/arrowHold';

    interface ExactDecimalValidity {
        normalized: string;
        empty: boolean;
        syntaxValid: boolean;
        requiredValid: boolean;
        digitsValid: boolean;
        rangeValid: boolean;
        valid: boolean;
    }

    interface Props {
        value?: string;
        step?: string;
        maxIntegerDigits?: number;
        maxFractionDigits?: number;
        allowNegative?: boolean;
        accelerateOnHold?: boolean;
        min?: string;
        max?: string;
        disabled?: boolean;
        readonly?: boolean;
        required?: boolean;
        id?: string;
        name?: string;
        placeholder?: string;
        ariaLabel?: string;
        ariaDescribedby?: string;
        ariaErrormessage?: string;
        externalInvalid?: boolean;
        testid?: string;
        className?: string;
        style?: string;
        onchange?: (value: string) => void;
        oncommit?: (value: string) => void;
        onvaliditychange?: (state: ExactDecimalValidity) => void;
        onfocus?: (event: FocusEvent) => void;
        onblur?: (event: FocusEvent) => void;
    }

    let {
        value = $bindable(''),
        step = '1',
        maxIntegerDigits = 12,
        maxFractionDigits = 12,
        allowNegative = false,
        accelerateOnHold = false,
        min,
        max,
        disabled = false,
        readonly: readOnly = false,
        required = false,
        id,
        name,
        placeholder = '',
        ariaLabel,
        ariaDescribedby,
        ariaErrormessage,
        externalInvalid = false,
        testid,
        className = '',
        style: inlineStyle = '',
        onchange,
        oncommit,
        onvaliditychange,
        onfocus,
        onblur,
    }: Props = $props();
    let inputEl = $state<HTMLInputElement | null>(null);
    const arrowHold = new ArrowHold();

    interface ScaledDecimal {
        coefficient: bigint;
        places: number;
    }

    function exactDecimal(candidate: string): ScaledDecimal | null {
        const normalized = normalizeDecimalInput(candidate);
        if (!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) return null;
        const negative = normalized.startsWith('-');
        const unsigned = negative ? normalized.slice(1) : normalized;
        const [integer = '', fraction = ''] = unsigned.split('.');
        const digits = `${integer || '0'}${fraction}`.replace(/^0+(?=\d)/, '');
        const magnitude = BigInt(digits || '0');
        return {
            coefficient: negative && magnitude !== 0n ? -magnitude : magnitude,
            places: fraction.length,
        };
    }

    function powerOfTen(exponent: number): bigint {
        return 10n ** BigInt(exponent);
    }

    function rescale(value: ScaledDecimal, places: number): bigint {
        return value.coefficient * powerOfTen(places - value.places);
    }

    function compareExact(left: string, right: string): -1 | 0 | 1 | null {
        const parsedLeft = exactDecimal(left);
        const parsedRight = exactDecimal(right);
        if (!parsedLeft || !parsedRight) return null;
        const places = Math.max(parsedLeft.places, parsedRight.places);
        const leftScaled = rescale(parsedLeft, places);
        const rightScaled = rescale(parsedRight, places);
        return leftScaled < rightScaled ? -1 : leftScaled > rightScaled ? 1 : 0;
    }

    function normalizedParts(candidate: string): ExactDecimalValidity {
        const trimmed = candidate.trim();
        if (trimmed === '') {
            return {
                normalized: '',
                empty: true,
                syntaxValid: true,
                requiredValid: !required,
                digitsValid: true,
                rangeValid: true,
                valid: !required,
            };
        }
        if (!/^-?[\d\s.,]*$/.test(trimmed)) {
            return {
                normalized: candidate,
                empty: false,
                syntaxValid: false,
                requiredValid: true,
                digitsValid: true,
                rangeValid: true,
                valid: false,
            };
        }
        const normalized = normalizeDecimalInput(trimmed);
        const syntaxValid = /^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized) && (allowNegative || !normalized.startsWith('-'));
        if (!syntaxValid) {
            return {
                normalized,
                empty: false,
                syntaxValid: false,
                requiredValid: true,
                digitsValid: true,
                rangeValid: true,
                valid: false,
            };
        }
        const unsigned = normalized.startsWith('-') ? normalized.slice(1) : normalized;
        const [integer = '', fraction = ''] = unsigned.split('.');
        const digitsValid = (integer || '0').length <= maxIntegerDigits && fraction.length <= maxFractionDigits;
        const belowMin = min !== undefined && compareExact(normalized, min) === -1;
        const aboveMax = max !== undefined && compareExact(normalized, max) === 1;
        const rangeValid = !belowMin && !aboveMax;
        return {
            normalized,
            empty: false,
            syntaxValid: true,
            requiredValid: true,
            digitsValid,
            rangeValid,
            valid: digitsValid && rangeValid,
        };
    }

    let parsedValue = $derived(normalizedParts(value));
    let locallyInvalid = $derived(!parsedValue.valid || externalInvalid);
    let maxLength = $derived(maxIntegerDigits + maxFractionDigits + Math.max(0, Math.floor((maxIntegerDigits - 1) / 3)) + (maxFractionDigits > 0 ? 1 : 0) + (allowNegative ? 1 : 0));
    let lastValidityKey = '';

    $effect(() => {
        const state: ExactDecimalValidity = {
            ...parsedValue,
            valid: parsedValue.valid && !externalInvalid,
        };
        const key = `${state.normalized}\0${state.empty}\0${state.syntaxValid}\0${state.requiredValid}\0${state.digitsValid}\0${state.rangeValid}\0${state.valid}`;
        if (key === lastValidityKey) return;
        lastValidityKey = key;
        onvaliditychange?.(state);
    });

    function restoreDomValue(): void {
        if (inputEl && inputEl.value !== value) inputEl.value = value;
    }

    function commit(): void {
        arrowHold.reset();
        if (readOnly || disabled) {
            restoreDomValue();
            return;
        }
        const parsed = normalizedParts(value);
        if (!parsed.valid || parsed.normalized === '') return;
        const next = formatDecimalForDisplay(parsed.normalized, {maxFrac: maxFractionDigits});
        if (next !== value) {
            value = next;
            if (inputEl) inputEl.value = next;
            onchange?.(next);
        }
        oncommit?.(next);
    }

    function handleInput(event: Event): void {
        const target = event.currentTarget;
        if (!(target instanceof HTMLInputElement)) return;
        if (readOnly || disabled) {
            target.value = value;
            return;
        }
        const filtered = filterDecimalInput(target.value, allowNegative);
        if (filtered !== target.value) target.value = filtered;
        value = filtered;
        onchange?.(value);
    }

    function floorDiv(value: bigint, divisor: bigint): bigint {
        const quotient = value / divisor;
        const remainder = value % divisor;
        return remainder !== 0n && value < 0n ? quotient - 1n : quotient;
    }

    function ceilDiv(value: bigint, divisor: bigint): bigint {
        const quotient = value / divisor;
        const remainder = value % divisor;
        return remainder !== 0n && value > 0n ? quotient + 1n : quotient;
    }

    function formatScaledInteger(value: bigint, places: number): string {
        const negative = value < 0n;
        const magnitude = negative ? -value : value;
        const digits = magnitude.toString().padStart(places + 1, '0');
        const integer = places === 0 ? digits : digits.slice(0, -places);
        const fraction = places === 0 ? '' : digits.slice(-places);
        const rendered = places === 0 ? integer : `${integer}.${fraction}`;
        return negative && magnitude !== 0n ? `-${rendered}` : rendered;
    }

    /**
     * Exact counterpart of the legacy Number-based hold accelerator. Cadence is
     * counted as small integers; every quantity/step/boundary operation is BigInt
     * fixed-point arithmetic and each rung is an exact power-of-ten multiplier.
     */
    function acceleratedArrowStep(event: KeyboardEvent, candidate: string): string | null {
        if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return null;
        if (event.ctrlKey || event.metaKey || event.altKey) return null;
        event.preventDefault();

        const direction = event.key === 'ArrowUp' ? 1 : -1;
        const parsedCandidate = exactDecimal(candidate);
        const parsedStep = exactDecimal(step);
        if (!parsedStep || parsedStep.coefficient <= 0n) return candidate;

        const places = Math.max(parsedCandidate?.places ?? 0, parsedStep.places);
        const current = parsedCandidate ? rescale(parsedCandidate, places) : 0n;
        const baseStep = rescale(parsedStep, places);
        if (!accelerateOnHold) {
            return formatScaledInteger(current + BigInt(direction) * baseStep, places);
        }
        const newRun = arrowHold.begin(event, direction);
        if (newRun) arrowHold.level = 0;

        let magnitude = baseStep * powerOfTen(arrowHold.level);
        if (!newRun && arrowHold.ready) {
            const nextMagnitude = magnitude * 10n;
            if (current % nextMagnitude === 0n) {
                arrowHold.escalated();
                arrowHold.level += 1;
                magnitude = nextMagnitude;
            } else {
                const next = current + BigInt(direction) * magnitude;
                if (floorDiv(next, nextMagnitude) !== floorDiv(current, nextMagnitude)) {
                    arrowHold.escalated();
                    arrowHold.level += 1;
                    const boundary = (direction > 0 ? ceilDiv(current, nextMagnitude) : floorDiv(current, nextMagnitude)) * nextMagnitude;
                    return formatScaledInteger(boundary, places);
                }
            }
        }

        return formatScaledInteger(current + BigInt(direction) * magnitude, places);
    }

    function clampToBounds(candidate: string): string {
        const implicitMin = allowNegative ? undefined : '0';
        const lowerBound = min ?? implicitMin;
        if (lowerBound !== undefined && compareExact(candidate, lowerBound) === -1) {
            return normalizeDecimalInput(lowerBound);
        }
        if (max !== undefined && compareExact(candidate, max) === 1) {
            return normalizeDecimalInput(max);
        }
        return candidate;
    }

    function stepValue(event: KeyboardEvent): void {
        if (readOnly || disabled) {
            restoreDomValue();
            return;
        }
        const next = acceleratedArrowStep(event, value);
        if (next === null) {
            if (event.key === 'Enter') commit();
            return;
        }
        const constrained = clampToBounds(next);
        value = constrained;
        if (inputEl) inputEl.value = constrained;
        onchange?.(constrained);
    }

    function handleKeyup(event: KeyboardEvent): void {
        if (readOnly || disabled) {
            restoreDomValue();
            return;
        }
        if (event.key === 'ArrowUp' || event.key === 'ArrowDown') arrowHold.reset();
    }

    function handleFocus(event: FocusEvent): void {
        onfocus?.(event);
    }

    function handleBlur(event: FocusEvent): void {
        if (readOnly || disabled) {
            arrowHold.reset();
            restoreDomValue();
            onblur?.(event);
            return;
        }
        commit();
        onblur?.(event);
    }
</script>

<input
    bind:this={inputEl}
    {id}
    {name}
    type="text"
    inputmode="decimal"
    autocomplete="off"
    spellcheck="false"
    maxlength={maxLength}
    {value}
    {disabled}
    readonly={readOnly}
    {required}
    {placeholder}
    aria-label={ariaLabel}
    aria-describedby={ariaDescribedby}
    aria-errormessage={ariaErrormessage}
    aria-invalid={locallyInvalid}
    data-testid={testid}
    oninput={handleInput}
    onfocus={handleFocus}
    onblur={handleBlur}
    onkeydown={stepValue}
    onkeyup={handleKeyup}
    style={inlineStyle || undefined}
    class={`w-full rounded-lg border bg-white px-3 py-2 font-mono text-gray-900 outline-none transition-colors focus:border-libre-green focus:ring-1 focus:ring-libre-green read-only:cursor-default disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gray-900 dark:text-gray-100 ${
        locallyInvalid ? 'border-red-400 dark:border-red-500' : 'border-gray-300 dark:border-gray-600'
    } ${className}`}
/>
