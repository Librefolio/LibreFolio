<!--
  What each Broker can buy: one zone per operative Broker, with one card per Asset in the user's
  order. Clicking an Asset allows or excludes it on that Broker (green = the plan may propose buying
  it there); an allowed Asset shows its limits, each explained by its own «?». A field shows only
  when it can change the plan: the priority chooses between Brokers, so it needs the Asset allowed
  on more than one (or a value already set, which would otherwise act unseen). The limits carry no
  currency of their own: the card and the row already name the order currency.
  An allowed Asset priced in a currency the Broker has no order mode in has no limits to set: its
  card says what is missing and offers the two ways out, adding that mode (the Broker editor opens
  with the block already in place, written only on «Apply») or excluding the Asset on that Broker.
-->
<script lang="ts">
    import {CheckCheck, Plus, Square} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {exposureCategoryLabel} from '../categoryLabels.svelte';
    import {canonicalInput, decimalSign} from '../decimal';
    import type {DraftAsset, DraftMode, DraftRoute, PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyStep} from '../format';
    import {modeFeeText, modeIncrementText, modeKindText, modeUnitText} from '../modeText';
    import {BUTTON_LINK, BUTTON_PILL, BUTTON_SECONDARY, CARD, HINT, INPUT, INPUT_ADORNMENT, LABEL_ROW, NOTICE, TOGGLE_CARD, TOGGLE_OFF, TOGGLE_ON} from '../ui';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import PlannerBrokerIcon from '../shared/PlannerBrokerIcon.svelte';
    import BrokerEditor from './BrokerEditor.svelte';

    interface Props {
        draft: PlannerDraft;
    }

    let {draft}: Props = $props();

    const ids = $props.id();

    /** The Broker editor opened from a route, with the block for the missing currency already added. */
    let editing = $state<{brokerKey: string; currency: string; asset: string} | null>(null);

    function title(asset: DraftAsset | undefined): string {
        if (!asset) return '';
        return [asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ');
    }

    function typeText(asset: DraftAsset | undefined): string {
        return asset ? exposureCategoryLabel($t, 'asset_type', asset.assetClass) : '';
    }

    /** The price currency a route needs an order mode in, when the Broker has none in it; '' otherwise. */
    function missingCurrency(asset: DraftAsset | undefined, mode: DraftMode | null): string {
        const currency = asset?.price?.currency ?? '';
        return !mode && /^[A-Z]{3}$/.test(currency) ? currency : '';
    }

    function unitStep(mode: DraftMode | null): string {
        if (!mode) return '1';
        return mode.kind === 'whole_quantity' ? '1' : cldrCurrencyStep(mode.currency);
    }

    /** The unit inside a limit field: «units» for a quantity mode; none for an amount, whose currency heads the row. */
    function limitUnit(mode: DraftMode | null): string {
        return mode?.kind === 'whole_quantity' ? modeUnitText($t, mode) : '';
    }

    /** The same three facts as the Broker card: order type, increment, purchase fee. */
    function modeLine(mode: DraftMode): string {
        return $t('tools.pacAllocator.planner.route.modeLine', {
            default: '{kind} · Increment: {step} · Purchase fee: {fee}',
            values: {kind: modeKindText($t, mode.kind), step: modeIncrementText($t, mode), fee: modeFeeText($t, mode)},
        });
    }

    function setAll(routes: readonly DraftRoute[], enabled: boolean): void {
        for (const route of routes) route.enabled = enabled;
    }

    /** How many operative Brokers may buy each Asset: the priority only chooses among them. */
    const allowedBrokers = $derived.by(() => {
        const counts = new Map<string, number>();
        for (const route of Object.values(draft.data.routes)) {
            if (route.enabled) counts.set(route.assetKey, (counts.get(route.assetKey) ?? 0) + 1);
        }
        return counts;
    });

    /** Shown with a choice between Brokers, or while it holds a value other than 0 (never an unseen preference). */
    function priorityShown(route: DraftRoute): boolean {
        if ((allowedBrokers.get(route.assetKey) ?? 0) > 1) return true;
        const canonical = canonicalInput(route.priority);
        return canonical === null || decimalSign(canonical) !== 0;
    }
</script>

<div class="space-y-4" data-testid="pac-planner-routing">
    {#if draft.orderedAssets.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-routing-empty">{$t('tools.pacAllocator.planner.problems.noAssets', {default: 'Add at least one Asset.'})}</p>
    {:else if draft.operativeBrokers.length === 0}
        <p class={NOTICE.info} data-testid="pac-planner-routing-no-broker">{$t('tools.pacAllocator.planner.problems.noOperativeBroker', {default: 'Add at least one Broker on which orders can be proposed.'})}</p>
    {:else}
        {#each draft.operativeBrokers as broker (broker.key)}
            {@const routes = draft.routesOfBroker(broker.key)}
            {@const allowed = routes.filter((route) => route.enabled).length}
            <section class="{CARD} space-y-3" data-testid="pac-planner-routing-broker" data-broker-key={broker.key}>
                <div class="flex min-w-0 items-start gap-2.5">
                    <PlannerBrokerIcon {broker} size={28} />
                    <div class="min-w-0 flex-1 space-y-0.5">
                        <h4 class="min-w-0 font-semibold text-gray-900 dark:text-gray-100" data-testid="pac-planner-routing-title">
                            <span use:scrollOnOverflow class={overflowScrollTextClass} title={broker.name}>{broker.name || '—'}</span>
                        </h4>
                        {#if broker.modes.length === 0}
                            <p class="text-xs text-red-700 dark:text-red-300" data-testid="pac-planner-routing-broker-no-mode">
                                {$t('tools.pacAllocator.planner.problems.brokerNoMode', {default: 'The Broker has no order mode.'})}
                            </p>
                        {:else}
                            {#each broker.modes as mode (mode.key)}
                                <p class="flex flex-wrap items-center gap-x-1.5 {HINT}" data-testid="pac-planner-routing-broker-mode" data-currency={mode.currency}>
                                    <CurrencyCode code={mode.currency} />
                                    <span>{modeLine(mode)}</span>
                                </p>
                            {/each}
                        {/if}
                    </div>
                </div>

                <div class="flex flex-wrap items-center gap-2" data-testid="pac-planner-routing-bulk">
                    <button type="button" class={BUTTON_PILL} disabled={allowed === routes.length} data-testid="pac-planner-routing-all" onclick={() => setAll(routes, true)}>
                        <CheckCheck size={13} aria-hidden="true" />{$t('tools.pacAllocator.planner.routing.allowAll', {default: 'Allow all'})}
                    </button>
                    <button type="button" class={BUTTON_PILL} disabled={allowed === 0} data-testid="pac-planner-routing-none" onclick={() => setAll(routes, false)}>
                        <Square size={13} aria-hidden="true" />{$t('tools.pacAllocator.planner.routing.excludeAll', {default: 'Exclude all'})}
                    </button>
                    <span class="ml-auto {HINT}" data-testid="pac-planner-routing-count" data-allowed={allowed} data-total={routes.length}>
                        {$t('tools.pacAllocator.planner.routing.allowedCount', {default: '{allowed} of {total} allowed', values: {allowed, total: routes.length}})}
                    </span>
                </div>

                <ul class="space-y-2">
                    {#each routes as route (route.wireId)}
                        {@const asset = draft.asset(route.assetKey)}
                        {@const mode = draft.modeFor(route.assetKey, route.brokerKey)}
                        {@const missing = missingCurrency(asset, mode)}
                        <li
                            class="{TOGGLE_CARD} {route.enabled ? TOGGLE_ON : TOGGLE_OFF}"
                            data-testid="pac-planner-route"
                            data-asset-key={route.assetKey}
                            data-broker-key={route.brokerKey}
                            data-enabled={route.enabled ? 'true' : 'false'}
                            data-ready={mode ? 'true' : 'false'}
                        >
                            <button type="button" class="flex w-full cursor-pointer items-center gap-2 p-2 text-left" aria-pressed={route.enabled} data-testid="pac-planner-route-enabled" onclick={() => (route.enabled = !route.enabled)}>
                                <AssetIcon iconUrl={asset?.iconUrl} assetType={asset?.assetClass.toUpperCase()} altText="" size="sm" />
                                <span class="min-w-0 flex-1">
                                    <span class="block min-w-0 font-medium text-gray-900 dark:text-gray-100" data-testid="pac-planner-route-title">
                                        <span use:scrollOnOverflow class={overflowScrollTextClass} title={title(asset)}>{title(asset) || '—'}</span>
                                    </span>
                                    {#if typeText(asset) !== ''}<span class="block {HINT}">{typeText(asset)}</span>{/if}
                                </span>
                                {#if mode}<span class="shrink-0 text-xs text-gray-600 dark:text-gray-300" data-testid="pac-planner-route-currency"><CurrencyCode code={mode.currency} /></span>{/if}
                            </button>

                            {#if route.enabled && !mode}
                                {#if missing !== ''}
                                    <div
                                        class="mx-2 mb-2 space-y-2 rounded-md border border-amber-200 bg-amber-50 p-2.5 text-sm text-amber-900 sm:ml-10 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100"
                                        data-testid="pac-planner-route-mode-missing"
                                        data-currency={missing}
                                    >
                                        <div class="flex flex-wrap items-center gap-x-1">
                                            <span>{$t('tools.pacAllocator.planner.route.modeMissing', {default: '{broker} has no order mode in {currency} yet', values: {broker: broker.name || '—', currency: missing}})}</span>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.route.modeMissing', {default: '{broker} has no order mode in {currency} yet', values: {broker: broker.name || '—', currency: missing}})}
                                                help={$t('tools.pacAllocator.planner.route.modeMissingHelp', {
                                                    default: 'The order mode says how {broker} takes an order in {currency}: by units or by amount, with which increment and which fees. The plan needs it to size the purchase of this Asset, which is priced in {currency}. It is not the conversion: if you pay with another currency, the plan adds the conversion as you set it on the Broker. Add the mode, or exclude the Asset on this Broker.',
                                                    values: {broker: broker.name || '—', currency: missing},
                                                })}
                                                testid="pac-planner-route-mode-missing-help"
                                            />
                                        </div>
                                        <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
                                            <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-route-add-mode" onclick={() => (editing = {brokerKey: broker.key, currency: missing, asset: title(asset)})}>
                                                <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.route.addMode', {default: 'Add {currency} mode', values: {currency: missing}})}
                                            </button>
                                            <button type="button" class={BUTTON_LINK} data-testid="pac-planner-route-exclude" onclick={() => (route.enabled = false)}>
                                                {$t('tools.pacAllocator.planner.route.excludeHere', {default: 'Exclude on {broker}', values: {broker: broker.name || '—'}})}
                                            </button>
                                        </div>
                                    </div>
                                {/if}
                            {:else if route.enabled}
                                {@const unit = limitUnit(mode)}
                                <div class="grid gap-3 px-2 pb-2 sm:grid-cols-2 sm:pl-10 lg:grid-cols-3" data-testid="pac-planner-route-fields">
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{route.wireId}-min-active">{$t('tools.pacAllocator.planner.route.minimumIfActive', {default: 'Minimum purchase'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.route.minimumIfActive', {default: 'Minimum purchase'})}
                                                help={$t('tools.pacAllocator.planner.route.minimumHelp', {
                                                    default: 'If the plan buys here, it buys at least this much. Empty = the Broker increment is enough. Useful when a small purchase would make the fee weigh too much.',
                                                })}
                                            />
                                        </div>
                                        <div class="relative">
                                            <ExactDecimalInput
                                                id="{ids}-{route.wireId}-min-active"
                                                bind:value={route.minimumIfActive}
                                                step={unitStep(mode)}
                                                placeholder={$t('tools.pacAllocator.planner.route.minimumNone', {default: 'no minimum'})}
                                                className="{INPUT} {unit === '' ? '' : 'pr-20'}"
                                                testid="pac-planner-route-minimum-if-active"
                                            />
                                            {#if unit !== ''}<span class={INPUT_ADORNMENT} aria-hidden="true">{unit}</span>{/if}
                                        </div>
                                    </div>
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{route.wireId}-min-required">{$t('tools.pacAllocator.planner.route.requiredMinimum', {default: 'Required purchase'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.route.requiredMinimum', {default: 'Required purchase'})}
                                                help={$t('tools.pacAllocator.planner.route.requiredHelp', {
                                                    default: 'The plan buys at least this much here, whatever happens. If the resources are not enough, the plan becomes impossible. Empty = no obligation.',
                                                })}
                                            />
                                        </div>
                                        <div class="relative">
                                            <ExactDecimalInput
                                                id="{ids}-{route.wireId}-min-required"
                                                bind:value={route.requiredMinimum}
                                                step={unitStep(mode)}
                                                placeholder={$t('tools.pacAllocator.planner.route.requiredNone', {default: 'no obligation'})}
                                                className="{INPUT} {unit === '' ? '' : 'pr-20'}"
                                                testid="pac-planner-route-required-minimum"
                                            />
                                            {#if unit !== ''}<span class={INPUT_ADORNMENT} aria-hidden="true">{unit}</span>{/if}
                                        </div>
                                    </div>
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{route.wireId}-cap">{$t('tools.pacAllocator.planner.route.cap', {default: 'Maximum purchase'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.route.cap', {default: 'Maximum purchase'})}
                                                help={$t('tools.pacAllocator.planner.route.capHelp', {
                                                    default: 'The most the plan may buy of this Asset on this Broker. Empty = no limit of its own: the plan never buys more than the liquidity that can reach this Broker. Fill it to stop purchases here beyond a given size.',
                                                })}
                                            />
                                        </div>
                                        <div class="relative">
                                            <ExactDecimalInput
                                                id="{ids}-{route.wireId}-cap"
                                                bind:value={route.cap}
                                                step={unitStep(mode)}
                                                maxIntegerDigits={15}
                                                placeholder={$t('tools.pacAllocator.planner.route.capNone', {default: 'no limit'})}
                                                className="{INPUT} {unit === '' ? '' : 'pr-20'}"
                                                testid="pac-planner-route-cap"
                                            />
                                            {#if unit !== ''}<span class={INPUT_ADORNMENT} aria-hidden="true">{unit}</span>{/if}
                                        </div>
                                    </div>
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{route.wireId}-margin">{$t('tools.pacAllocator.planner.route.margin', {default: 'Price margin'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.route.margin', {default: 'Price margin'})}
                                                help={$t('tools.pacAllocator.planner.route.marginHelp', {
                                                    default: 'Each purchase is counted at price × (1 + margin), to cover a price that rises before the order. Example: 0.5% on 100 → 100.50. The difference is a reserve for the rise: it does not count as invested.',
                                                })}
                                            />
                                        </div>
                                        <div class="relative">
                                            <ExactDecimalInput id="{ids}-{route.wireId}-margin" bind:value={route.marginPercent} step="0.01" max="100" className="{INPUT} pr-8" testid="pac-planner-route-margin" />
                                            <span class={INPUT_ADORNMENT} aria-hidden="true">%</span>
                                        </div>
                                    </div>
                                    {#if priorityShown(route)}
                                        <div data-testid="pac-planner-route-priority-field">
                                            <div class={LABEL_ROW}>
                                                <label for="{ids}-{route.wireId}-priority">{$t('tools.pacAllocator.planner.route.priority', {default: 'Priority'})}</label>
                                                <HelpTip
                                                    label={$t('tools.pacAllocator.planner.route.priority', {default: 'Priority'})}
                                                    help={$t('tools.pacAllocator.planner.route.priorityHelp', {
                                                        default: 'It counts only between plans that get equally close to the target: among them, buying on the Brokers with the lowest number is preferred. It weighs more than the fees: to let the cost decide, leave them all at 0. All at 0 = no preference.',
                                                    })}
                                                />
                                            </div>
                                            <ExactDecimalInput id="{ids}-{route.wireId}-priority" bind:value={route.priority} step="1" maxFractionDigits={0} className={INPUT} testid="pac-planner-route-priority" />
                                        </div>
                                    {/if}
                                </div>
                            {/if}
                        </li>
                    {/each}
                </ul>
            </section>
        {/each}
    {/if}

    {#each draft.fundingOnlyBrokers as broker (broker.key)}
        <p class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400" data-testid="pac-planner-routing-funding-only">
            <PlannerBrokerIcon {broker} size={20} />
            {$t('tools.pacAllocator.planner.routing.fundingOnly', {default: '{name}: nothing is bought from this account', values: {name: broker.name || '—'}})}
        </p>
    {/each}
</div>

{#if editing}
    <BrokerEditor {draft} brokerKey={editing.brokerKey} addCurrency={editing.currency} addFor={editing.asset} onclose={() => (editing = null)} />
{/if}
