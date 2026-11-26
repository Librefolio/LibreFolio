<script lang="ts">
    /**
     * The «Limits» cell of the targets table (F2 of project 67, M1 and M8): minimum and maximum of the Asset's value at the
     * end of the plan, two text fields that read «500» as an amount and «35%» as a share of the plan's total (`limits.ts`).
     * A plain text field, not `ExactDecimalInput`: that one keeps only digits and separators, and the «%» is the form.
     * Both fields turn red (`aria-invalid`, the look of `ExactDecimalInput`) when the minimum is above the maximum in the same form;
     * a field that is not a limit turns red alone.
     * Side by side on a wide screen, one above the other on a phone.
     */
    import {t} from '$lib/i18n';
    import type {PlannerDraft} from '../draft.svelte';
    import {limitsConflict, parseLimit, shareAboveHundred, type LimitSide} from '../limits';
    import {minimumAboveTotal} from '../request';
    import type {PlannerExactMoney} from '../types';
    import {INPUT} from '../ui';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();
    const KEY = 'tools.pacAllocator.planner.targets';

    interface Props {
        draft: PlannerDraft;
        assetKey: string;
        label: string;
        /**
         * An Asset's row: the Tool's base of the last preview, read when drawn. A minimum, an amount, alone above it is drawn
         * red at once (TL-4 of project 67, `minimumAboveTotal`). A cash entry passes none: its trapped cash counts too.
         */
        total?: () => PlannerExactMoney | null;
    }

    let {draft, assetKey, label, total}: Props = $props();

    const limits = $derived(draft.data.limits[assetKey]);
    const conflict = $derived(limitsConflict(limits));
    const aboveTotal = $derived(total !== undefined && minimumAboveTotal(draft, assetKey, total()));

    function wrong(side: LimitSide): boolean {
        const limit = parseLimit(limits?.[side]);
        return conflict || limit === 'invalid' || shareAboveHundred(limit) || (side === 'minimum' && aboveTotal);
    }

    const SIDES = [
        {side: 'minimum', placeholder: 'limitMinimum', placeholderFallback: 'min', aria: 'limitMinimumLabel', ariaFallback: 'Minimum of {asset}'},
        {side: 'maximum', placeholder: 'limitMaximum', placeholderFallback: 'max', aria: 'limitMaximumLabel', ariaFallback: 'Maximum of {asset}'},
    ] as const;
</script>

<div class="flex flex-col items-end gap-1 md:flex-row md:items-center" data-testid={testId('limit', profile)} data-asset-key={assetKey} data-conflict={conflict ? 'true' : 'false'} data-above-total={aboveTotal ? 'true' : 'false'}>
    {#each SIDES as field (field.side)}
        {@const invalid = wrong(field.side)}
        <input
            type="text"
            inputmode="decimal"
            autocomplete="off"
            spellcheck="false"
            class="{INPUT} w-20 text-right aria-invalid:border-lf-danger"
            value={limits?.[field.side] ?? ''}
            placeholder={$t(`${KEY}.${field.placeholder}`, {default: field.placeholderFallback})}
            aria-label={$t(`${KEY}.${field.aria}`, {default: field.ariaFallback, values: {asset: label}})}
            aria-invalid={invalid ? 'true' : 'false'}
            data-testid={testId(`limit-${field.side}`, profile)}
            oninput={(event) => draft.setLimit(assetKey, field.side, event.currentTarget.value)}
        />
    {/each}
</div>
