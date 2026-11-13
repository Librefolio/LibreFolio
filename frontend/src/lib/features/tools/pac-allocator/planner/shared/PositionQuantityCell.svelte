<!--
  The «Quantity» cell of a position (F3a of project 67, the Rebalancer): the planning quantity, the user's to change, and
  whether it is still the copied one (`OriginBadge`: copied, or modified once the user changed it). Writes the draft
  directly, as the targets table's cells do. A quantity held is personal: with privacy on the field gives way to the
  masked quantity (`formatPlannerQuantity`), and it is editable again once privacy is off.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {isPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {positionIsCopied, type PlannerDraft} from '../draft.svelte';
    import {formatPlannerQuantity} from '../format';
    import {INPUT} from '../ui';
    import OriginBadge from './OriginBadge.svelte';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile. */
    const profile = getPlannerProfile();

    interface Props {
        draft: PlannerDraft;
        positionKey: string;
        assetLabel: string;
    }

    let {draft, positionKey, assetLabel}: Props = $props();

    const position = $derived(draft.data.positions.find((item) => item.key === positionKey));
</script>

{#if position}
    <div class="flex flex-wrap items-center justify-end gap-1.5" data-testid={testId('position-quantity-cell', profile)} data-position-key={positionKey}>
        {#if isPrivacyEnabled()}
            <span class="font-mono text-lf-primary" data-testid={testId('position-quantity-masked', profile)}>{formatPlannerQuantity(position.quantity)}</span>
        {:else}
            <div class="w-28">
                <ExactDecimalInput
                    value={position.quantity}
                    step="1"
                    className="{INPUT} text-right"
                    ariaLabel={$t('tools.portfolioRebalancer.planner.positions.quantityLabel', {values: {asset: assetLabel, broker: position.brokerName}})}
                    testid={testId('position-quantity', profile)}
                    onchange={(value) => {
                        position.quantity = value;
                    }}
                />
            </div>
        {/if}
        <OriginBadge origin="copied" modified={!positionIsCopied(position)} testid={testId('position-origin', profile)} />
    </div>
{/if}
