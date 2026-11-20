<!--
  F2 of project 67 (developer's answer of 13/11, point 1): a Broker in automatic conversion converts currency at each
  purchase, while the plan counts one conversion per currency pair; the Broker's own rounding may differ by a few cents per
  order. An info note at the top of the operational plan, naming those Brokers once each. Read-only: nothing is computed.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import type {PlannerConversion} from '../types';
    import {NOTICE} from '../ui';
    import type {ResultNames} from './model';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        conversions: readonly PlannerConversion[];
        names: ResultNames;
    }

    let {conversions, names}: Props = $props();

    const brokerIds = $derived([...new Set(conversions.filter((action) => action.mode === 'automatic').map((action) => action.broker_id))]);
</script>

{#if brokerIds.length > 0}
    <p class={NOTICE.info} role="status" data-testid={testId('plan-auto-conversion-note', profile)} data-brokers={brokerIds.join(' ')}>
        {$t('tools.pacAllocator.planner.result.plan.automaticConversionNote', {
            default: '{brokers} convert currency at each purchase. The plan counts one conversion per currency pair; the broker may round each order separately, so a few cents per order may differ.',
            values: {brokers: brokerIds.map((id) => names.broker(id)).join(', ')},
        })}
    </p>
{/if}
