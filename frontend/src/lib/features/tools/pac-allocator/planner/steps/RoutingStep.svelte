<script lang="ts">
    import {ChevronLeft, ChevronRight} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {DraftMode, DraftRoute, PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyStep, formatPlannerPlainDecimal, formatPlannerPricePlain} from '../format';
    import {MODE_KIND_FALLBACKS} from '../labels';
    import {BADGE, BUTTON_SECONDARY, CARD, HINT, INPUT, LABEL, NOTICE} from '../ui';

    interface Props {
        draft: PlannerDraft;
    }

    let {draft}: Props = $props();

    const ids = $props.id();
    let index = $state(0);

    const assets = $derived(draft.data.assets);
    const current = $derived(assets.length === 0 ? null : assets[Math.min(index, assets.length - 1)]);
    const routes = $derived(current ? draft.routesOf(current.key) : []);
    const assetOptions = $derived(assets.map((asset, position) => ({value: String(position), label: [asset.ticker, asset.name].filter((part) => part.trim() !== '').join(' ')})));

    function unitLabel(mode: DraftMode): string {
        return mode.kind === 'whole_quantity' ? $t('tools.pacAllocator.planner.units.shares', {default: 'units'}) : mode.currency;
    }

    function unitStep(mode: DraftMode): string {
        return mode.kind === 'whole_quantity' ? '1' : cldrCurrencyStep(mode.currency);
    }

    function modeLine(mode: DraftMode): string {
        const step =
            mode.kind === 'whole_quantity'
                ? $t('tools.pacAllocator.planner.brokers.stepUnits', {default: 'step {step} units', values: {step: formatPlannerPlainDecimal(mode.step)}})
                : $t('tools.pacAllocator.planner.brokers.stepAmount', {default: 'step {step}', values: {step: formatPlannerPricePlain(mode.step, mode.currency)}});
        return [mode.currency, $t(`tools.pacAllocator.planner.modeKinds.${mode.kind}`, {default: MODE_KIND_FALLBACKS[mode.kind]}), step].join(' · ');
    }

    function feeLine(route: DraftRoute, mode: DraftMode): string {
        return $t('tools.pacAllocator.planner.route.fee', {
            default: 'BUY {currency} of {broker} · fixed {fixed} + {rate}%',
            values: {currency: mode.currency, broker: draft.broker(route.brokerKey)?.name ?? route.brokerKey, fixed: formatPlannerPricePlain(mode.fixedFee, mode.currency), rate: formatPlannerPlainDecimal(mode.ratePercent)},
        });
    }

    function move(delta: number): void {
        index = Math.max(0, Math.min(assets.length - 1, index + delta));
    }
</script>

<div class="space-y-4" data-testid="pac-planner-routing">
    {#if current}
        <div class="flex flex-wrap items-center justify-between gap-2">
            <button type="button" class={BUTTON_SECONDARY} disabled={index <= 0} data-testid="pac-planner-routing-prev" onclick={() => move(-1)}>
                <ChevronLeft class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.routing.previous', {default: 'Previous Asset'})}
            </button>
            <div class="min-w-48">
                <SimpleSelect value={String(Math.min(index, assets.length - 1))} options={assetOptions} compact ariaLabel={$t('tools.pacAllocator.planner.routing.asset', {default: 'Asset'})} testId="pac-planner-routing-asset" onchange={(value) => (index = Number(value))} />
            </div>
            <button type="button" class={BUTTON_SECONDARY} disabled={index >= assets.length - 1} data-testid="pac-planner-routing-next" onclick={() => move(1)}>
                {$t('tools.pacAllocator.planner.routing.next', {default: 'Next Asset'})}<ChevronRight class="h-4 w-4" aria-hidden="true" />
            </button>
        </div>

        <h3 class="font-semibold text-gray-900 dark:text-gray-100" data-testid="pac-planner-routing-title">{[current.ticker, current.name].filter((part) => part.trim() !== '').join(' ')}</h3>

        {#each routes as route (route.wireId)}
            {@const mode = draft.modeFor(route.assetKey, route.brokerKey)}
            {@const broker = draft.broker(route.brokerKey)}
            <section class="{CARD} space-y-3" data-testid="pac-planner-route" data-broker-key={route.brokerKey} data-enabled={route.enabled ? 'true' : 'false'} data-ready={mode ? 'true' : 'false'}>
                <label class="flex flex-wrap items-center gap-2">
                    <input type="checkbox" class="rounded border-gray-300 text-libre-green focus:ring-libre-green" bind:checked={route.enabled} data-testid="pac-planner-route-enabled" />
                    <span class="font-medium">{broker?.name ?? route.brokerKey}</span>
                    {#if mode}
                        <span class={HINT}>· {modeLine(mode)}</span>
                        <span class={BADGE.success}>{$t('tools.pacAllocator.planner.route.ready', {default: 'ready'})}</span>
                    {:else}
                        <span class={BADGE.danger} data-testid="pac-planner-route-no-mode">
                            {current.price ? $t('tools.pacAllocator.planner.problems.routeNoMode', {default: 'The Broker has no order mode in the price currency of this Asset.'}) : $t('tools.pacAllocator.planner.route.noPrice', {default: 'No price yet: the mode follows the price currency.'})}
                        </span>
                    {/if}
                </label>
                {#if route.enabled}
                    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        <label for="{ids}-{route.wireId}-priority">
                            <span class={LABEL}>{$t('tools.pacAllocator.planner.route.priority', {default: 'Priority'})}</span>
                            <ExactDecimalInput id="{ids}-{route.wireId}-priority" bind:value={route.priority} step="1" maxFractionDigits={0} className={INPUT} testid="pac-planner-route-priority" />
                            <span class={HINT}>{$t('tools.pacAllocator.planner.route.priorityHint', {default: '0 = preferred'})}</span>
                        </label>
                        <label for="{ids}-{route.wireId}-min-active">
                            <span class={LABEL}>{$t('tools.pacAllocator.planner.route.minimumIfActive', {default: 'Minimum if you operate'})} <span class={HINT}>{mode ? unitLabel(mode) : ''}</span></span>
                            <ExactDecimalInput id="{ids}-{route.wireId}-min-active" bind:value={route.minimumIfActive} step={mode ? unitStep(mode) : '1'} placeholder={$t('tools.pacAllocator.planner.route.none', {default: 'None'})} className={INPUT} testid="pac-planner-route-minimum-if-active" />
                        </label>
                        <label for="{ids}-{route.wireId}-min-required">
                            <span class={LABEL}>{$t('tools.pacAllocator.planner.route.requiredMinimum', {default: 'Required minimum'})} <span class={HINT}>{mode ? unitLabel(mode) : ''}</span></span>
                            <ExactDecimalInput id="{ids}-{route.wireId}-min-required" bind:value={route.requiredMinimum} step={mode ? unitStep(mode) : '1'} placeholder={$t('tools.pacAllocator.planner.route.none', {default: 'None'})} className={INPUT} testid="pac-planner-route-required-minimum" />
                        </label>
                        <label for="{ids}-{route.wireId}-cap">
                            <span class={LABEL}>{$t('tools.pacAllocator.planner.route.cap', {default: 'Cap'})} * <span class={HINT}>{mode ? unitLabel(mode) : ''}</span></span>
                            <ExactDecimalInput id="{ids}-{route.wireId}-cap" bind:value={route.cap} step={mode ? unitStep(mode) : '1'} maxIntegerDigits={15} className={INPUT} testid="pac-planner-route-cap" />
                            <span class={HINT}>{$t('tools.pacAllocator.planner.route.capHint', {default: 'High default, editable'})}</span>
                        </label>
                        <label for="{ids}-{route.wireId}-margin">
                            <span class={LABEL}>{$t('tools.pacAllocator.planner.route.margin', {default: 'Execution margin'})} <span class={HINT}>%</span></span>
                            <ExactDecimalInput id="{ids}-{route.wireId}-margin" bind:value={route.marginPercent} step="0.01" max="100" className={INPUT} testid="pac-planner-route-margin" />
                        </label>
                        {#if mode}
                            <p class="text-sm sm:self-end" data-testid="pac-planner-route-fee">{feeLine(route, mode)}</p>
                        {/if}
                    </div>
                {/if}
            </section>
        {:else}
            <p class={NOTICE.info} data-testid="pac-planner-routing-no-broker">{$t('tools.pacAllocator.planner.problems.noOperativeBroker', {default: 'Add at least one Broker on which orders can be proposed.'})}</p>
        {/each}

        <p class={HINT}>{$t('tools.pacAllocator.planner.routing.unitRule', {default: "Minimum and cap follow the mode: units for 'number of units', an amount for 'amount'. No free choice."})}</p>
        <p class={HINT}>{$t('tools.pacAllocator.planner.routing.capRule', {default: 'The high cap does not widen the search: the real limit of every order is the lowest of cap and resources.'})}</p>
        {#each draft.fundingOnlyBrokers as broker (broker.key)}
            <p class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400" data-testid="pac-planner-routing-funding-only">
                <input type="checkbox" disabled class="rounded border-gray-300" aria-hidden="true" tabindex="-1" />
                {$t('tools.pacAllocator.planner.routing.fundingOnly', {default: '{name} · funding only, not selectable', values: {name: broker.name}})}
            </p>
        {/each}
    {:else}
        <p class={NOTICE.info} data-testid="pac-planner-routing-empty">{$t('tools.pacAllocator.planner.problems.noAssets', {default: 'Add at least one Asset.'})}</p>
    {/if}
</div>
