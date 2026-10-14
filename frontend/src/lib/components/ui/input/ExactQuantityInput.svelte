<script lang="ts">
    import ExactDecimalInput from './ExactDecimalInput.svelte';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';

    type QuantitySignRule = 'positive' | 'negative' | 'nonzero' | 'zero' | 'any';
    type SignState = 'ok' | 'bad' | 'neutral';

    interface DecimalValidity {
        normalized: string;
        empty: boolean;
        syntaxValid: boolean;
        requiredValid: boolean;
        digitsValid: boolean;
        rangeValid: boolean;
        valid: boolean;
    }

    interface QuantityValidity extends DecimalValidity {
        signState: SignState;
        signValid: boolean;
    }

    interface Props {
        /** Authoritative normalized draft. The locale-specific edit buffer stays private. */
        value?: string;
        step?: string;
        maxIntegerDigits?: number;
        maxFractionDigits?: number;
        allowNegative?: boolean;
        accelerateOnHold?: boolean;
        min?: string;
        max?: string;
        signRule?: QuantitySignRule;
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
        /** Forces the private edit buffer to reseed even when `value` is unchanged. */
        resetKey?: string | number;
        testid?: string;
        className?: string;
        style?: string;
        onchange?: (value: string) => void;
        oncommit?: (value: string) => void;
        onvaliditychange?: (state: QuantityValidity) => void;
        onfocus?: (event: FocusEvent) => void;
        onblur?: (event: FocusEvent) => void;
    }

    let {
        value = $bindable(''),
        step = '1',
        maxIntegerDigits = 12,
        maxFractionDigits = 12,
        allowNegative = false,
        accelerateOnHold = true,
        min,
        max,
        signRule = 'any',
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
        resetKey,
        testid,
        className = '',
        style: inlineStyle = '',
        onchange,
        oncommit,
        onvaliditychange,
        onfocus,
        onblur,
    }: Props = $props();

    function normalizedSign(candidate: string): -1 | 0 | 1 | null {
        const normalized = normalizeDecimalInput(candidate);
        if (!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) return null;
        const digits = normalized.replace(/[^\d]/g, '');
        if (!/[1-9]/.test(digits)) return 0;
        return normalized.startsWith('-') ? -1 : 1;
    }

    function signStateFor(candidate: string): SignState {
        const sign = normalizedSign(candidate);
        if (sign === null || signRule === 'any') return 'neutral';
        if (signRule === 'positive') return sign > 0 ? 'ok' : sign < 0 ? 'bad' : 'neutral';
        if (signRule === 'negative') return sign < 0 ? 'ok' : sign > 0 ? 'bad' : 'neutral';
        if (signRule === 'nonzero') return sign === 0 ? 'bad' : 'ok';
        return sign === 0 ? 'ok' : 'bad';
    }

    function withinDigitBudget(candidate: string): boolean {
        const normalized = normalizeDecimalInput(candidate);
        if (!/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) return false;
        const unsigned = normalized.startsWith('-') ? normalized.slice(1) : normalized;
        const [integer = '', fraction = ''] = unsigned.split('.');
        return (integer || '0').length <= maxIntegerDigits && fraction.length <= maxFractionDigits;
    }

    function displayValue(candidate: string): string {
        if (candidate.trim() === '') return '';
        const normalized = normalizeDecimalInput(candidate);
        if (!withinDigitBudget(normalized)) return candidate;
        return formatDecimalForDisplay(normalized, {maxFrac: maxFractionDigits});
    }

    let rawValue = $state('');
    let decimalValidity = $state<DecimalValidity>({
        normalized: '',
        empty: true,
        syntaxValid: true,
        requiredValid: true,
        digitsValid: true,
        rangeValid: true,
        valid: true,
    });
    let lastPublishedValue = $state<string | null>(null);
    let syncInitialized = $state(false);
    let lastIncomingValue = $state('');
    let lastFormatKey = $state('');
    let lastResetKey = $state<string | number | undefined>(undefined);
    let lastValidityKey = '';

    /*
     * A parent normally echoes each normalized onchange value. That echo must
     * not replace `1,20` with `1.20` while the user is still typing. A genuinely
     * new parent value (open/reset/type change) does reseed the display buffer.
     */
    $effect(() => {
        const incoming = value;
        const formatKey = `${maxIntegerDigits}\0${maxFractionDigits}`;
        const firstSync = !syncInitialized;
        const modelChanged = firstSync || incoming !== lastIncomingValue;
        const formatChanged = firstSync || formatKey !== lastFormatKey;
        const resetChanged = !firstSync && resetKey !== lastResetKey;
        if (!modelChanged && !formatChanged && !resetChanged) return;
        syncInitialized = true;
        lastIncomingValue = incoming;
        lastFormatKey = formatKey;
        lastResetKey = resetKey;
        if (!firstSync && !resetChanged && modelChanged && incoming === lastPublishedValue && normalizeDecimalInput(rawValue) === incoming) return;
        rawValue = displayValue(incoming);
        lastPublishedValue = null;
    });

    let signState = $derived(signStateFor(rawValue));
    let signInvalid = $derived(signState === 'bad');
    let canShowSignColor = $derived(!externalInvalid && !decimalValidity.empty && decimalValidity.syntaxValid && decimalValidity.digitsValid && decimalValidity.rangeValid);
    let signBorderColor = $derived(canShowSignColor && signState === 'bad' ? 'oklch(0.637 0.237 25.331 / 0.7)' : canShowSignColor && signState === 'ok' ? 'oklch(0.765 0.177 163.223 / 0.7)' : '');
    let mergedStyle = $derived(`${inlineStyle.trim().replace(/;$/, '')}${inlineStyle.trim() && signBorderColor ? '; ' : ''}${signBorderColor ? `border-color: ${signBorderColor}` : ''}`);

    $effect(() => {
        const state: QuantityValidity = {
            ...decimalValidity,
            normalized: normalizeDecimalInput(rawValue),
            signState,
            signValid: !signInvalid,
            valid: decimalValidity.valid && !externalInvalid && !signInvalid,
        };
        const key = `${state.normalized}\0${state.empty}\0${state.syntaxValid}\0${state.requiredValid}\0${state.digitsValid}\0${state.rangeValid}\0${state.signState}\0${state.valid}`;
        if (key === lastValidityKey) return;
        lastValidityKey = key;
        onvaliditychange?.(state);
    });

    function handleDecimalChange(nextRaw: string): void {
        if (readOnly || disabled) return;
        rawValue = nextRaw;
        const normalized = normalizeDecimalInput(nextRaw);
        lastPublishedValue = normalized;
        value = normalized;
        onchange?.(normalized);
    }

    function handleCommit(nextDisplay: string): void {
        if (readOnly || disabled) return;
        const normalized = normalizeDecimalInput(nextDisplay);
        oncommit?.(normalized);
    }

    function handleFocus(event: FocusEvent): void {
        onfocus?.(event);
    }

    function handleBlur(event: FocusEvent): void {
        if (!readOnly && !disabled) lastPublishedValue = null;
        onblur?.(event);
    }
</script>

<ExactDecimalInput
    value={rawValue}
    {step}
    {maxIntegerDigits}
    {maxFractionDigits}
    {allowNegative}
    {accelerateOnHold}
    {min}
    {max}
    {disabled}
    readonly={readOnly}
    {required}
    {id}
    {name}
    {placeholder}
    {ariaLabel}
    {ariaDescribedby}
    {ariaErrormessage}
    externalInvalid={externalInvalid || signInvalid}
    {testid}
    {className}
    style={mergedStyle}
    onchange={handleDecimalChange}
    oncommit={handleCommit}
    onvaliditychange={(state) => (decimalValidity = state)}
    onfocus={handleFocus}
    onblur={handleBlur}
/>
