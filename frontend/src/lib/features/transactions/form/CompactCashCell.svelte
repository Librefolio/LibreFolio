<!--
  CompactCashCell.svelte — Generic compact editor for {amount, currency} cells.

  Single horizontal cell that combines a numeric input and a compact
  CurrencySearchSelect. Designed to be usable inside DataTable CustomCell
  wrappers for any currency-backed amount column (transactions cash, FX
  rates, asset prices). Emits a unified `{amount, code} | null` change.

  Sign hint (matches SignRule from transactionTypeStore):
  - 'positive' → green border tint when amount > 0, red when ≤ 0
  - 'negative' → green when < 0, red when ≥ 0
  - 'nonzero' / 'zero' / 'free' → neutral (no color)
  The hint is purely visual — backend remains source-of-truth for validation.

  `maxSignificantDigits` (B-48): an amount past it marks the field `aria-invalid`, with a danger border; the form says why.

  A blur emits only a value that differs, by exact value or by currency, from the one received (B-47): an amount read back
  padded (`0.010000`) and shown as `0.01` is not a change, and the row stays as it was.

  Empty value semantics: when the amount input is blank OR the code is empty,
  the cell emits `null` (cleared). Otherwise it emits the latest combined value.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import type {SignRule} from '$lib/features/transactions/transactionTypeStore';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {decimalArrowStep, exceedsSignificantDigits, filterDecimalInput, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import {exactDecimalEqual} from '$lib/features/transactions/txPayloadHelpers';
    import {computeSignHint} from '$lib/features/transactions/form/signHintColor';

    interface CashValue {
        amount: string;
        code: string;
    }

    interface Props {
        /** Current value or `null` when empty. */
        value: CashValue | null;
        /** Called with the latest combined value (or `null` if cleared). */
        onChange: (next: CashValue | null) => void;
        /** Visual-only sign hint (uses SignRule from transactionTypeStore). */
        signHint?: SignRule;
        /** Placeholder for the numeric input. */
        amountPlaceholder?: string;
        /** Default currency to seed the select when value is `null`. */
        defaultCode?: string;
        /** When set, shows a "reset to original" shortcut at the top of the
         *  currency dropdown (via CurrencySearchSelect.originalCurrency). */
        originalCurrency?: string;
        /** Disable both inputs. */
        disabled?: boolean;
        /** Disable only the amount input (currency remains interactive). */
        amountDisabled?: boolean;
        /** Disable only the currency selector. */
        currencyDisabled?: boolean;
        /** When set, restrict currency dropdown to these codes only. */
        allowedCurrencies?: string[];
        /** Test id root — emits `${testid}-amount` and `${testid}-currency`. */
        testid?: string;
        /** At most this many significant digits in the amount (B-48): past it the field is invalid. No cap when unset. */
        maxSignificantDigits?: number;
    }

    let {value, onChange, signHint = 'free', amountPlaceholder = '0.00', defaultCode = '', originalCurrency, disabled = false, amountDisabled = false, currencyDisabled = false, allowedCurrencies, testid = 'compact-cash', maxSignificantDigits}: Props = $props();

    // Local edit buffers so an empty `amount` doesn't immediately collapse the cell to `null`
    // while the user is mid-typing. We commit `null` only when both fields are empty AND blur fires.
    // svelte-ignore state_referenced_locally — the $effect below syncs whenever props change.
    let amountStr = $state('');
    // svelte-ignore state_referenced_locally — same as above.
    let code = $state('');

    // Sync down on external value change (avoid loops: only when truly different).
    // Bugfix-4 §C14: incoming values from the backend are zero-padded
    // ("6.000000") — strip the noise on display while preserving any
    // user-typed precision once the field is dirty (we re-format only when
    // the *external* prop changes, not on every keystroke).
    // T1-a: our own emission comes back formatted ("12," → emit "12." → prop
    // "12."). If the buffer already normalizes to the same number, the change
    // is ours — keep the user's raw text (separator, trailing zeros) intact.
    $effect(() => {
        const incomingAmountRaw = value?.amount ?? '';
        const incomingAmount = formatDecimalForDisplay(incomingAmountRaw);
        const incomingCode = value?.code ?? defaultCode;
        // untrack local state reads to avoid re-running on every keystroke
        const local = untrack(() => amountStr);
        if (incomingAmount !== local) {
            // B-47: by exact value, never through Number, which makes two amounts past 15 digits one.
            const sameNumber = local.trim() !== '' && incomingAmountRaw.trim() !== '' && exactDecimalEqual(normalizeDecimalInput(local), normalizeDecimalInput(incomingAmountRaw));
            if (!sameNumber) amountStr = incomingAmount;
        }
        if (incomingCode !== untrack(() => code)) code = incomingCode;
    });

    function emit() {
        const trimmed = normalizeDecimalInput(amountStr);
        if (trimmed === '' && code === '') {
            onChange(null);
            return;
        }
        // W30: preserve currency selection even when amount is still empty —
        // the user may pick currency first, then type the number.
        onChange({amount: trimmed, code});
    }

    /** Whether the cell shows what it received: the same amount by exact value and the same currency; for no value, a
     *  blank amount (a currency picked alone was emitted when it was picked). */
    function showsReceivedValue(): boolean {
        const amount = normalizeDecimalInput(amountStr);
        if (value == null) return amount === '';
        return code === value.code && exactDecimalEqual(amount, normalizeDecimalInput(value.amount ?? ''));
    }

    function handleBlur() {
        amountStr = formatDecimalForDisplay(normalizeDecimalInput(amountStr));
        // B-47: every keystroke has emitted already; the blur only tidies the display. Emitting the tidy form of a value
        // received padded would change the row's text, and the editor would ask to discard an untouched row.
        if (showsReceivedValue()) return;
        emit();
    }

    function handleAmountInput(e: Event) {
        const input = e.currentTarget as HTMLInputElement;
        amountStr = filterDecimalInput(input.value, true);
        if (input.value !== amountStr) input.value = amountStr;
        emit();
    }

    /** Arrow keys step the amount, as they did while this was a number input. */
    function handleAmountKeydown(e: KeyboardEvent) {
        const stepped = decimalArrowStep(e, amountStr);
        if (stepped === null) return;
        amountStr = stepped;
        emit();
    }

    function handleCurrencyChange(next: string) {
        code = next;
        emit();
    }

    // Sign-hint visual state — drives `sign-ok` / `sign-bad` class binding.
    // Colors reflect the VALUE AFTER AUTO-FLIP conformance to the backend rule.
    let signOk = $state(false);
    let signBad = $state(false);
    let digitsInvalid = $derived(maxSignificantDigits !== undefined && exceedsSignificantDigits(amountStr, maxSignificantDigits));
    $effect(() => {
        const {ok, bad} = computeSignHint(parseFloat(normalizeDecimalInput(amountStr)), signHint);
        signOk = ok;
        signBad = bad;
    });
</script>

<div class="compact-cash" class:sign-ok={signOk} class:sign-bad={signBad} class:digits-bad={digitsInvalid} data-testid={testid}>
    <input
        type="text"
        inputmode="decimal"
        autocomplete="off"
        class="amount-input"
        aria-invalid={digitsInvalid}
        value={amountStr}
        oninput={handleAmountInput}
        onkeydown={handleAmountKeydown}
        onblur={handleBlur}
        placeholder={amountPlaceholder}
        disabled={disabled || amountDisabled}
        data-testid={`${testid}-amount`}
    />
    <div class="currency-wrap">
        <CurrencySearchSelect bind:value={code} compact={true} disabled={disabled || currencyDisabled} onchange={handleCurrencyChange} {originalCurrency} {allowedCurrencies} />
        <span class="sr-only" data-testid={`${testid}-currency`}>{code}</span>
    </div>
</div>

<style>
    .compact-cash {
        display: flex;
        align-items: stretch;
        gap: 0.375rem;
        min-width: 0;
        width: 100%;
        padding: 0;
    }
    .amount-input {
        flex: 1 1 auto;
        min-width: 5rem;
        font-size: 0.875rem;
        line-height: 1.25rem;
        text-align: right;
        /* Bugfix-2 §U12 + Bugfix-3 §C12: monospace + tabular numerals AND a
           visible input-style border so the field reads as editable.
           Locale-safe text input keeps browser number controls from
           reinterpreting "." as a thousands separator.
           Walkthrough #6 (mobile): wrapper is now `flex` and amount input
           uses `flex: 1` so the field stretches to fill the row when Cash
           is dropped below Qty on narrow screens. */
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
        font-variant-numeric: tabular-nums;
        background: var(--lf-surface-field);
        border: 1px solid var(--lf-border-input);
        border-radius: 0.5rem;
        padding: 0.5rem 0.625rem;
        outline: none;
        color: var(--lf-text-primary);
        transition:
            border-color 120ms ease,
            box-shadow 120ms ease;
        -moz-appearance: textfield;
        appearance: textfield;
    }
    .amount-input::placeholder {
        color: var(--lf-text-placeholder);
    }
    .amount-input::-webkit-outer-spin-button,
    .amount-input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    .amount-input:hover {
        border-color: var(--lf-border-input-hover);
    }
    .amount-input:focus {
        border-color: var(--lf-focus);
        box-shadow: 0 0 0 2px color-mix(in oklab, var(--lf-focus) 25%, transparent);
    }
    .compact-cash.sign-ok .amount-input {
        border-color: color-mix(in oklab, var(--lf-gain) 70%, transparent);
    }
    .compact-cash.sign-bad .amount-input {
        border-color: color-mix(in oklab, var(--lf-loss) 70%, transparent);
    }
    /* B-48: an amount past the significant digits is refused, whatever its sign: after the sign rules, so it wins. */
    .compact-cash.digits-bad .amount-input {
        border-color: var(--lf-danger);
    }
    .amount-input:disabled {
        color: var(--lf-text-muted);
        background: var(--lf-surface-panel);
        border-color: var(--lf-border-subtle);
        opacity: 0.6;
    }
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
</style>
