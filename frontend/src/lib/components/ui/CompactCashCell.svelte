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

  Empty value semantics: when the amount input is blank OR the code is empty,
  the cell emits `null` (cleared). Otherwise it emits the latest combined value.
-->
<script lang="ts">
    import type {SignRule} from '$lib/stores/transactionTypeStore';
    import CurrencySearchSelect from './select/CurrencySearchSelect.svelte';
    import {formatDecimalForDisplay} from '$lib/utils/formatDecimal';
    import {computeSignHint} from '$lib/utils/signHintColor';

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
        /** Test id root — emits `${testid}-amount` and `${testid}-currency`. */
        testid?: string;
    }

    let {value, onChange, signHint = 'free', amountPlaceholder = '0.00', defaultCode = '', originalCurrency, disabled = false, testid = 'compact-cash'}: Props = $props();

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
    $effect(() => {
        const incomingAmountRaw = value?.amount ?? '';
        const incomingAmount = formatDecimalForDisplay(incomingAmountRaw);
        const incomingCode = value?.code ?? defaultCode;
        if (incomingAmount !== amountStr) amountStr = incomingAmount;
        if (incomingCode !== code) code = incomingCode;
    });

    function emit() {
        const trimmed = amountStr.trim();
        if (trimmed === '' && code === '') {
            onChange(null);
            return;
        }
        // W30: preserve currency selection even when amount is still empty —
        // the user may pick currency first, then type the number.
        onChange({amount: trimmed, code});
    }

    function handleAmountInput(e: Event) {
        amountStr = (e.currentTarget as HTMLInputElement).value;
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
    $effect(() => {
        const {ok, bad} = computeSignHint(parseFloat(amountStr), signHint);
        signOk = ok;
        signBad = bad;
    });
</script>

<div class="compact-cash" class:sign-ok={signOk} class:sign-bad={signBad} class:disabled data-testid={testid}>
    <input type="number" step="any" inputmode="decimal" autocomplete="off" class="amount-input" value={amountStr} placeholder={amountPlaceholder} oninput={handleAmountInput} onblur={emit} {disabled} data-testid={`${testid}-amount`} />
    <div class="currency-wrap">
        <CurrencySearchSelect bind:value={code} compact={true} {disabled} onchange={handleCurrencyChange} {originalCurrency} />
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
           Bugfix-5 walkthrough #6: switched to `type="number"` so we hide
           the browser spinner controls (they collapse the horizontal space
           and look unpolished against the currency picker on the right).
           Walkthrough #6 (mobile): wrapper is now `flex` and amount input
           uses `flex: 1` so the field stretches to fill the row when Cash
           is dropped below Qty on narrow screens. */
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
        font-variant-numeric: tabular-nums;
        background: white;
        border: 1px solid rgb(229 231 235); /* gray-200 */
        border-radius: 0.5rem;
        padding: 0.5rem 0.625rem;
        outline: none;
        color: inherit;
        transition:
            border-color 120ms ease,
            box-shadow 120ms ease;
        -moz-appearance: textfield;
        appearance: textfield;
    }
    .amount-input::-webkit-outer-spin-button,
    .amount-input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    :global(.dark) .amount-input {
        background: rgb(30 41 59); /* slate-800 */
        border-color: rgb(71 85 105); /* slate-600 */
        color: rgb(241 245 249); /* slate-100 */
    }
    .amount-input:hover {
        border-color: rgb(156 163 175); /* gray-400 */
    }
    :global(.dark) .amount-input:hover {
        border-color: rgb(100 116 139); /* slate-500 */
    }
    .amount-input:focus {
        border-color: rgb(16 185 129); /* libre-green */
        box-shadow: 0 0 0 2px rgb(16 185 129 / 0.25);
    }
    .compact-cash.sign-ok .amount-input {
        border-color: rgb(16 185 129 / 0.7); /* emerald-500 */
    }
    .compact-cash.sign-bad .amount-input {
        border-color: rgb(239 68 68 / 0.7); /* red-500 */
    }
    .amount-input:disabled {
        color: rgb(156 163 175); /* gray-400 */
        background: rgb(243 244 246); /* gray-100 */
    }
    :global(.dark) .amount-input:disabled {
        background: rgb(15 23 42); /* slate-900 */
    }
    .currency-wrap {
        min-width: 8rem;
    }
    .compact-cash.disabled {
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
