<script lang="ts">
    /**
     * RiskFreeRateField — the reader's risk-free rate, one value for every risk page (RN-21).
     *
     * Under the period line (`RiskPeriodLine`), the line that says on what the figures below are measured: the rate is
     * one more condition of that kind (the consultant, 17/11/2026), and it moves L1's «How does it move?» as well as
     * L3, so a field inside L3 would change figures above itself. The text is the reader's while they type; the shared
     * value (`riskFreeRate`) changes only on Enter or on leaving the field, and only with a value the engine accepts —
     * otherwise the field says so and keeps it. 0 % until the reader sets one; the hint (Q9 bis) lives in the ⓘ only.
     */
    import {CircleHelp} from 'lucide-svelte';

    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {formatExactDecimal} from '$lib/utils/core/formatFixed';
    import {normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';

    import {parseRiskFreePercent} from './riskFreeRate';
    import {riskFreeRate} from './riskFreeRateStore.svelte';

    interface Props {
        testId?: string;
    }

    let {testId = 'risk-free-rate'}: Props = $props();

    /** The shared value as the reader's language writes it. */
    function shown(percent: number): string {
        return formatExactDecimal(percent, {maxFrac: 4});
    }

    let draft = $state(shown(riskFreeRate.percent));
    let editing = $state(false);
    let invalid = $state(false);

    // Another field (another page, or a second panel on this one) set the value: show it, unless the reader is typing here.
    $effect(() => {
        const current = riskFreeRate.percent;
        if (!editing) {
            draft = shown(current);
            invalid = false;
        }
    });

    function commit(): void {
        const value = parseRiskFreePercent(normalizeDecimalInput(draft));
        if (value === null || !riskFreeRate.set(value)) {
            invalid = true;
            return;
        }
        invalid = false;
        editing = false;
        draft = shown(riskFreeRate.percent);
    }

    function handleKeydown(event: KeyboardEvent): void {
        if (event.key === 'Enter') {
            event.preventDefault();
            commit();
        } else if (event.key === 'Escape') {
            editing = false;
            invalid = false;
            draft = shown(riskFreeRate.percent);
        }
    }
</script>

<label class="mt-1 flex items-center gap-1 text-xs text-lf-muted" data-testid="{testId}-field" data-percent={riskFreeRate.percent}>
    <span>{$t('risk.params.riskFreeRate')}</span>
    <Tooltip text={$t('risk.params.riskFreeRateHint')} position="bottom" maxWidth="300px" testId="{testId}-hint">
        <CircleHelp size={13} class="text-lf-muted" aria-label={$t('risk.params.riskFreeRateHint')} />
    </Tooltip>
    <input
        type="text"
        inputmode="decimal"
        autocomplete="off"
        spellcheck="false"
        value={draft}
        oninput={(event) => {
            editing = true;
            draft = event.currentTarget.value;
        }}
        onkeydown={handleKeydown}
        onblur={() => {
            if (editing || invalid) commit();
        }}
        aria-invalid={invalid}
        class="w-16 rounded border border-lf-input bg-lf-field px-2 py-1 text-sm text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus aria-invalid:border-lf-danger"
        data-testid={testId}
    />
    <span>%</span>
</label>
