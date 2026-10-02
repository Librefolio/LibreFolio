<!--
  The scenario data of one Broker: how you buy there in each currency, what a purchase costs, and
  which liquidity may pay for it. It edits a copy, and «Apply» writes that copy back to the draft.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {PiggyBank, Plus, Trash2} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import OrderableList from '$lib/components/ui/OrderableList.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {DEFAULT_QUANTITY_STEP} from '../defaults';
    import {defaultMode, type DraftBroker, type DraftFunding, type DraftMode, type FundingSourceRef, type ModeKind, type PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyStep, formatPlannerMoneyPlain} from '../format';
    import {fundingSourceHelp, modeKindText, modeUnitText} from '../modeText';
    import {BADGE, BUTTON_DANGER_SMALL, BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, ICON_BUBBLE, INPUT, INPUT_SUFFIX, LABEL_ROW, SECTION_TITLE, TITLE_INPUT, TOGGLE_CARD, TOGGLE_OFF, TOGGLE_ON} from '../ui';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import PlannerBrokerIcon from '../shared/PlannerBrokerIcon.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';

    interface Props {
        draft: PlannerDraft;
        brokerKey: string;
        /** Opened from the Route step: a currency this Broker has no block for, added on open. */
        addCurrency?: string;
        /** The Asset that needs that block, named in the hint over it. */
        addFor?: string;
        onclose: () => void;
    }

    let {draft, brokerKey, addCurrency = '', addFor = '', onclose}: Props = $props();

    const ids = $props.id();
    // Mount = open: the editor works on a copy taken once, and writes it back only on apply.
    const original = untrack(() => draft.broker(brokerKey));
    let working = $state<DraftBroker | null>(original ? structuredClone($state.snapshot(original)) : null);
    // A source not yet paired with this Broker starts allowed, as `syncFunding` does in the draft.
    untrack(() => {
        if (!working) return;
        for (const source of draft.fundingCandidates(working.key)) {
            if (!draft.fundingFor(working, source)) working.funding.push({...draft.newFunding(source), enabled: true});
        }
    });
    // The missing block goes first, in view with its starting values; like any edit here, it reaches the
    // draft only on «Apply». A currency the Broker already has adds nothing.
    const addedKey = untrack(() => {
        if (!working || !/^[A-Z]{3}$/.test(addCurrency) || working.modes.some((mode) => mode.currency === addCurrency)) return null;
        const mode = defaultMode(draft.nextId('mode'), addCurrency);
        working.modes = [mode, ...working.modes];
        return mode.key;
    });

    let adding = $state(false);
    let pendingCurrency = $state('');

    const kindOptions = $derived((['whole_quantity', 'monetary_amount'] as const).map((kind) => ({value: kind, label: modeKindText($t, kind)})));
    /** R4.9: who makes a currency conversion; it changes how the plan presents it, not the calculation. */
    const conversionOptions = $derived([
        {mode: 'manual' as const, label: $t('tools.pacAllocator.planner.brokerEditor.conversionManual', {default: 'You convert before buying'})},
        {mode: 'automatic' as const, label: $t('tools.pacAllocator.planner.brokerEditor.conversionAutomatic', {default: 'The Broker converts when you buy'})},
    ]);
    const usedCurrencies = $derived(new Set(working?.modes.map((mode) => mode.currency) ?? []));

    function setKind(mode: DraftMode, kind: string): void {
        if (kind !== 'whole_quantity' && kind !== 'monetary_amount') return;
        if (mode.kind === kind) return;
        mode.kind = kind as ModeKind;
        mode.step = kind === 'whole_quantity' ? DEFAULT_QUANTITY_STEP : cldrCurrencyStep(mode.currency);
    }

    /** The currencies another block already uses: a block cannot take one of them. */
    function otherCurrencies(mode: DraftMode): Set<string> {
        return new Set([...usedCurrencies].filter((currency) => currency !== mode.currency));
    }

    /** A block changes currency in place; an amount increment follows the new currency's minor unit. */
    function setCurrency(mode: DraftMode, currency: string): void {
        if (!/^[A-Z]{3}$/.test(currency) || currency === mode.currency || otherCurrencies(mode).has(currency)) return;
        mode.currency = currency;
        if (mode.kind === 'monetary_amount') mode.step = cldrCurrencyStep(currency);
    }

    /** The new currency goes first, where the user is looking; the list can be reordered after. */
    function addMode(currency: string): void {
        if (!working || !/^[A-Z]{3}$/.test(currency) || usedCurrencies.has(currency)) return;
        working.modes = [defaultMode(draft.nextId('mode'), currency), ...working.modes];
        closeAdd();
    }

    function closeAdd(): void {
        pendingCurrency = '';
        adding = false;
    }

    function removeMode(key: string): void {
        if (working) working.modes = working.modes.filter((mode) => mode.key !== key);
    }

    function restoreProposed(): void {
        if (working) working.modes = draft.defaultModes(working.observedCurrencies);
    }

    /** Who a funding source belongs to: a Broker account (with its icon) or a contribution. */
    function sourceOf(source: FundingSourceRef): {broker: DraftBroker | undefined; label: string; currency: string | null; amount: string | null} {
        if (source.kind === 'contribution') {
            const item = draft.contribution(source.contributionKey);
            return {broker: undefined, label: item?.label.trim() ?? '', currency: item?.currency ?? null, amount: item?.amount ?? null};
        }
        const cash = draft.cashRow(source.cashKey);
        const broker = cash ? draft.broker(cash.brokerKey) : undefined;
        return {broker, label: broker?.name ?? cash?.brokerKey ?? source.cashKey, currency: cash?.currency ?? null, amount: cash?.selected ?? null};
    }

    function sourceKey(source: FundingSourceRef): string {
        return source.kind === 'cash' ? source.cashKey : source.contributionKey;
    }

    const candidates = $derived(working ? draft.fundingCandidates(working.key) : []);
    const localCash = $derived(working ? draft.data.cash.filter((cash) => cash.brokerKey === working!.key) : []);

    function fundingOf(source: FundingSourceRef): DraftFunding | undefined {
        return working ? draft.fundingFor(working, source) : undefined;
    }

    function toggleFunding(source: FundingSourceRef, enabled: boolean): void {
        if (!working) return;
        const existing = fundingOf(source);
        if (existing) existing.enabled = enabled;
        else working.funding.push({...draft.newFunding(source), enabled});
    }

    function apply(): void {
        if (!working) return;
        draft.replaceBroker($state.snapshot(working) as DraftBroker);
        onclose();
    }
</script>

<PlannerDialog open title={$t('tools.pacAllocator.planner.brokerEditor.title', {default: 'Configure {name} · scenario data (the Broker is not changed)', values: {name: working?.name || '—'}})} testid="pac-planner-broker-editor" {onclose} maxWidth="4xl">
    {#if working}
        <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
            <PlannerBrokerIcon broker={working} size={32} />
            {#if working.origin === 'copied'}
                <span class="min-w-0 truncate text-base font-semibold text-gray-900 dark:text-gray-100">{working.name}</span>
            {:else}
                <div class="min-w-0 flex-1 sm:max-w-sm">
                    <input class={TITLE_INPUT} bind:value={working.name} maxlength="120" aria-label={$t('common.name', {default: 'Name'})} placeholder={$t('common.name', {default: 'Name'})} data-testid="pac-planner-broker-editor-name" />
                </div>
            {/if}
            {#if working.origin === 'copied'}
                <button type="button" class="{BUTTON_LINK} sm:ml-auto" data-testid="pac-planner-broker-editor-restore" onclick={restoreProposed}>
                    {$t('tools.pacAllocator.planner.brokerEditor.restore', {default: 'Restore the copied values'})}
                </button>
            {/if}
        </div>

        <section class="space-y-3" aria-labelledby="{ids}-modes">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-0.5">
                    <h3 id="{ids}-modes" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokerEditor.modes', {default: 'How you buy, currency by currency'})}</h3>
                    <HelpTip
                        label={$t('tools.pacAllocator.planner.brokerEditor.modes', {default: 'How you buy, currency by currency'})}
                        help={$t('tools.pacAllocator.planner.brokerEditor.modesHelp', {default: 'One block for each currency you buy in at this Broker: an Asset priced in that currency is bought with its rules. Drag the blocks into the order you prefer.'})}
                    />
                </div>
                <button type="button" class={BUTTON_SECONDARY} disabled={adding} data-testid="pac-planner-mode-add" onclick={() => (adding = true)}>
                    <Plus class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.brokerEditor.addCurrency', {default: 'Add currency'})}
                </button>
            </div>

            {#if adding}
                <div class="flex flex-wrap items-end gap-2 rounded-lg border border-dashed border-libre-green/60 bg-libre-green/5 p-3 dark:bg-libre-green/10" data-testid="pac-planner-mode-pending">
                    <div class="w-full sm:w-72">
                        <p class={LABEL_ROW}>{$t('tools.pacAllocator.planner.brokerEditor.pickCurrency', {default: 'Currency of the new block'})}</p>
                        <CurrencySearchSelect bind:value={pendingCurrency} excludedCurrencies={usedCurrencies} testId="pac-planner-mode-add-currency" onchange={(currency) => addMode(currency)} />
                    </div>
                    <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-mode-add-cancel" onclick={closeAdd}>{$t('common.cancel', {default: 'Cancel'})}</button>
                </div>
            {/if}

            {#if working.modes.length > 0}
                <OrderableList items={working.modes} keyFn={(mode) => mode.key} onReorder={(next) => working && (working.modes = next)}>
                    {#snippet children({item: mode})}
                        <div class="space-y-3 p-1 sm:p-2" data-testid="pac-planner-mode" data-currency={mode.currency} data-kind={mode.kind} data-added={mode.key === addedKey ? 'true' : undefined}>
                            {#if mode.key === addedKey && mode.currency === addCurrency}
                                <p class="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100" data-testid="pac-planner-mode-added-for">
                                    {$t('tools.pacAllocator.planner.brokerEditor.addedFor', {
                                        default: '{currency} mode added to buy {asset}, with starting values: check order type, increment and fees, then apply.',
                                        values: {currency: mode.currency, asset: addFor || '—'},
                                    })}
                                </p>
                            {/if}
                            <div class="flex items-center justify-between gap-2">
                                <div class="w-full max-w-64">
                                    <CurrencySearchSelect
                                        value={mode.currency}
                                        compact
                                        excludedCurrencies={otherCurrencies(mode)}
                                        testId="pac-planner-mode-currency"
                                        onchange={(currency) => setCurrency(mode, currency)}
                                    />
                                </div>
                                <button type="button" class={BUTTON_DANGER_SMALL} data-testid="pac-planner-mode-remove" onclick={() => removeMode(mode.key)}>
                                    <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />{$t('common.remove', {default: 'Remove'})}
                                </button>
                            </div>

                            <div class="grid gap-3 sm:grid-cols-2">
                                <div>
                                    <div class={LABEL_ROW}>
                                        <span>{$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'Order type'})}</span>
                                        <HelpTip
                                            label={$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'Order type'})}
                                            help={$t('tools.pacAllocator.planner.brokers.orderKindHelp', {default: 'How you enter an order at this Broker: by number of units (you buy 3 units) or by amount (you invest 150). It sets the unit of the increment and of the limits on each order.'})}
                                        />
                                    </div>
                                    <SimpleSelect value={mode.kind} options={kindOptions} testId="pac-planner-mode-kind" ariaLabel={$t('tools.pacAllocator.planner.brokerEditor.kind', {default: 'Order type'})} onchange={(value) => setKind(mode, value)} />
                                </div>
                                <div>
                                    <div class={LABEL_ROW}>
                                        <label for="{ids}-{mode.key}-step">{$t('tools.pacAllocator.planner.brokerEditor.step', {default: 'Increment'})} *</label>
                                        <HelpTip
                                            label={$t('tools.pacAllocator.planner.brokerEditor.step', {default: 'Increment'})}
                                            help={$t('tools.pacAllocator.planner.brokers.incrementHelp', {default: 'Every proposed order is a multiple of this value. By number of units: 1 = whole units only, 0.001 = fractions down to three decimals. By amount: the smallest amount you can enter, for example 0.01.'})}
                                        />
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <div class="min-w-0 flex-1">
                                            <ExactDecimalInput id="{ids}-{mode.key}-step" bind:value={mode.step} step={mode.kind === 'whole_quantity' ? '1' : cldrCurrencyStep(mode.currency)} className={INPUT} testid="pac-planner-mode-step" />
                                        </div>
                                        <span class={INPUT_SUFFIX}>
                                            {#if mode.kind === 'monetary_amount'}<CurrencyCode code={mode.currency} />{:else}{modeUnitText($t, mode)}{/if}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div role="group" aria-labelledby="{ids}-{mode.key}-fee" class="border-t border-gray-100 pt-3 dark:border-gray-700/60">
                                <div class={LABEL_ROW}>
                                    <span id="{ids}-{mode.key}-fee" class="font-semibold text-gray-700 dark:text-gray-200">{$t('tools.pacAllocator.planner.brokerEditor.fee', {default: 'Purchase fee'})}</span>
                                    <HelpTip
                                        label={$t('tools.pacAllocator.planner.brokerEditor.fee', {default: 'Purchase fee'})}
                                        help={$t('tools.pacAllocator.planner.brokers.feeHelp', {default: 'What the Broker charges on each purchase: the percentage of the amount, kept between minimum and maximum, plus the fixed part. No purchase, no fee. It is paid from your liquidity and is not invested.\n\nExamples, in the currency of the purchase:\n• 0.19%, minimum 1.50, maximum 18: on 500 you pay 1.50, on 2,000 you pay 3.80, on 20,000 you pay 18.\n• Only a fixed part of 2.95: 2.95 on any purchase.\n• Fixed part 1 plus 0.10%: on 1,000 you pay 2.\n• Everything at 0: no fee.'})}
                                    />
                                </div>
                                <div class="mt-1 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{mode.key}-floor">{$t('tools.pacAllocator.planner.brokerEditor.feeFloor', {default: 'Minimum'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.brokerEditor.feeFloor', {default: 'Minimum'})}
                                                help={$t('tools.pacAllocator.planner.brokerEditor.feeFloorHelp', {default: 'The percentage part is never below this amount. 0 = no minimum.'})}
                                            />
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <div class="min-w-0 flex-1">
                                                <ExactDecimalInput id="{ids}-{mode.key}-floor" bind:value={mode.floor} step={cldrCurrencyStep(mode.currency)} className={INPUT} testid="pac-planner-mode-fee-floor" />
                                            </div>
                                            <span class={INPUT_SUFFIX}><CurrencyCode code={mode.currency} /></span>
                                        </div>
                                    </div>
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{mode.key}-rate">{$t('tools.pacAllocator.planner.brokerEditor.feeRate', {default: 'Percentage'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.brokerEditor.feeRate', {default: 'Percentage'})}
                                                help={$t('tools.pacAllocator.planner.brokerEditor.feeRateHelp', {default: 'The share of the amount bought, in percent: 0.19 means 0.19%. Minimum and maximum limit this part only.'})}
                                            />
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <div class="min-w-0 flex-1">
                                                <ExactDecimalInput id="{ids}-{mode.key}-rate" bind:value={mode.ratePercent} step="0.01" className={INPUT} testid="pac-planner-mode-fee-rate" />
                                            </div>
                                            <span class={INPUT_SUFFIX}>%</span>
                                        </div>
                                    </div>
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{mode.key}-cap">{$t('tools.pacAllocator.planner.brokerEditor.feeCap', {default: 'Maximum'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.brokerEditor.feeCap', {default: 'Maximum'})}
                                                help={$t('tools.pacAllocator.planner.brokerEditor.feeCapHelp', {default: 'The percentage part is never above this amount. Empty = no maximum.'})}
                                            />
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <div class="min-w-0 flex-1">
                                                <ExactDecimalInput id="{ids}-{mode.key}-cap" bind:value={mode.cap} step={cldrCurrencyStep(mode.currency)} placeholder={$t('tools.pacAllocator.planner.brokerEditor.feeCapNone', {default: 'none'})} className={INPUT} testid="pac-planner-mode-fee-cap" />
                                            </div>
                                            <span class={INPUT_SUFFIX}><CurrencyCode code={mode.currency} /></span>
                                        </div>
                                    </div>
                                    <div>
                                        <div class={LABEL_ROW}>
                                            <label for="{ids}-{mode.key}-fixed">{$t('tools.pacAllocator.planner.brokerEditor.feeFixed', {default: 'Fixed part'})}</label>
                                            <HelpTip
                                                label={$t('tools.pacAllocator.planner.brokerEditor.feeFixed', {default: 'Fixed part'})}
                                                help={$t('tools.pacAllocator.planner.brokerEditor.feeFixedHelp', {default: 'Paid on every purchase, whatever the amount, on top of the percentage part. 0 = none.'})}
                                            />
                                        </div>
                                        <div class="flex items-center gap-2">
                                            <div class="min-w-0 flex-1">
                                                <ExactDecimalInput id="{ids}-{mode.key}-fixed" bind:value={mode.fixedFee} step={cldrCurrencyStep(mode.currency)} className={INPUT} testid="pac-planner-mode-fee-fixed" />
                                            </div>
                                            <span class={INPUT_SUFFIX}><CurrencyCode code={mode.currency} /></span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    {/snippet}
                </OrderableList>
            {:else}
                <p class="text-sm text-amber-700 dark:text-amber-300" data-testid="pac-planner-mode-empty">{$t('tools.pacAllocator.planner.problems.brokerNoMode', {default: 'The Broker has no order mode.'})}</p>
            {/if}
        </section>

        <section class="space-y-3" aria-labelledby="{ids}-conversion">
            <div class="flex items-center gap-0.5">
                <h3 id="{ids}-conversion" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokers.conversionLabel', {default: 'Currency conversion'})}</h3>
                <HelpTip label={$t('tools.pacAllocator.planner.brokers.conversionLabel', {default: 'Currency conversion'})} help={$t('tools.pacAllocator.planner.brokers.conversionHelp', {default: 'When a purchase needs a currency you do not hold here, money is converted at the rate and spread of the FX step. If you convert yourself, the plan gives the conversion as a numbered step before the orders; if the Broker converts when you buy, the plan shows it next to its orders. The calculation is the same either way.'})} />
            </div>
            <fieldset class="grid gap-2 sm:grid-cols-2" data-testid="pac-planner-conversion-modes">
                <legend class="sr-only">{$t('tools.pacAllocator.planner.brokers.conversionLabel', {default: 'Currency conversion'})}</legend>
                {#each conversionOptions as option (option.mode)}
                    {@const on = working.conversionMode === option.mode}
                    <label class="flex cursor-pointer items-center gap-2 p-3 {TOGGLE_CARD} {on ? TOGGLE_ON : TOGGLE_OFF}" data-testid="pac-planner-conversion-mode" data-mode={option.mode} data-selected={on ? 'true' : 'false'}>
                        <input type="radio" name="{ids}-conversion" value={option.mode} bind:group={working.conversionMode} class="shrink-0 accent-libre-green" data-testid="pac-planner-conversion-mode-radio" />
                        <span class="font-medium text-gray-900 dark:text-gray-100">{option.label}</span>
                    </label>
                {/each}
            </fieldset>
        </section>

        <section class="space-y-3" aria-labelledby="{ids}-funding">
            <div class="flex items-center gap-0.5">
                <h3 id="{ids}-funding" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokerEditor.funding', {default: 'Liquidity {name} may use', values: {name: working.name || '—'}})}</h3>
                <HelpTip
                    label={$t('tools.pacAllocator.planner.brokerEditor.funding', {default: 'Liquidity {name} may use', values: {name: working.name || '—'}})}
                    help={$t('tools.pacAllocator.planner.brokerEditor.fundingHelp', {default: 'Purchases on this Broker can be paid with its own cash and with every source in green here. Everything starts allowed: click a source to exclude it, click again to allow it.'})}
                />
            </div>
            <ul class="space-y-2">
                {#each localCash as cash (cash.key)}
                    <li class="flex flex-wrap items-center gap-2 p-2 {TOGGLE_CARD} {TOGGLE_ON}" data-testid="pac-planner-funding-local" data-currency={cash.currency}>
                        <PlannerBrokerIcon broker={working} size={20} />
                        <span class="font-medium text-gray-900 dark:text-gray-100">{working.name || '—'}</span>
                        <CurrencyCode code={cash.currency} />
                        <HelpTip label={working.name || '—'} help={fundingSourceHelp($t, 'local', working.name, cash.currency)} />
                    </li>
                {/each}
                {#each candidates as source (sourceKey(source))}
                    {@const funding = fundingOf(source)}
                    {@const info = sourceOf(source)}
                    {@const enabled = funding?.enabled === true}
                    <li class="{TOGGLE_CARD} {enabled ? TOGGLE_ON : TOGGLE_OFF}" data-testid="pac-planner-funding" data-source={sourceKey(source)} data-enabled={enabled ? 'true' : 'false'}>
                        <button type="button" class="flex w-full cursor-pointer flex-wrap items-center gap-2 p-2 text-left" aria-pressed={enabled} data-testid="pac-planner-funding-toggle" onclick={() => toggleFunding(source, !enabled)}>
                            {#if source.kind === 'contribution'}
                                <span class={ICON_BUBBLE} style="width: 20px; height: 20px;"><PiggyBank size={12} aria-hidden="true" /></span>
                            {:else}
                                <PlannerBrokerIcon broker={info.broker} size={20} />
                            {/if}
                            {#if info.label}<span class="font-medium text-gray-900 dark:text-gray-100">{info.label}</span>{/if}
                            {#if info.currency}<CurrencyCode code={info.currency} />{/if}
                            {#if source.kind === 'contribution'}<span class={BADGE.neutral}>{$t('tools.pacAllocator.planner.contribution.kind', {default: 'contribution'})}</span>{/if}
                            {#if info.currency && info.amount && info.amount.trim() !== ''}
                                <span class={HINT}>· {$t('tools.pacAllocator.planner.brokerEditor.sourceAmount', {default: 'source {amount}', values: {amount: formatPlannerMoneyPlain(info.amount, info.currency)}})}</span>
                            {/if}
                        </button>
                        {#if funding && enabled}
                            <div class="grid gap-3 px-2 pb-2 sm:grid-cols-2 sm:pl-9">
                                <div>
                                    <div class={LABEL_ROW}>
                                        <label for="{ids}-{funding.key}-priority">{$t('tools.pacAllocator.planner.route.priority', {default: 'Priority'})}</label>
                                        <HelpTip
                                            label={$t('tools.pacAllocator.planner.route.priority', {default: 'Priority'})}
                                            help={$t('tools.pacAllocator.planner.brokerEditor.priorityHelp', {default: 'It counts only between plans that get equally close to the target: then the plan uses first the sources with the lowest number. 0 = preferred.'})}
                                        />
                                    </div>
                                    <ExactDecimalInput id="{ids}-{funding.key}-priority" bind:value={funding.priority} step="1" maxFractionDigits={0} className={INPUT} testid="pac-planner-funding-priority" />
                                </div>
                                <div>
                                    <div class={LABEL_ROW}>
                                        <label for="{ids}-{funding.key}-cap">{$t('tools.pacAllocator.planner.brokerEditor.fundingCap', {default: 'Maximum usable here'})}</label>
                                        <HelpTip
                                            label={$t('tools.pacAllocator.planner.brokerEditor.fundingCap', {default: 'Maximum usable here'})}
                                            help={$t('tools.pacAllocator.planner.brokerEditor.fundingCapHint', {default: 'The most the plan may take from this source for purchases here. Empty = the whole amount of the source.'})}
                                        />
                                    </div>
                                    <div class="flex items-center gap-2">
                                        <div class="min-w-0 flex-1">
                                            <ExactDecimalInput id="{ids}-{funding.key}-cap" bind:value={funding.cap} step={info.currency ? cldrCurrencyStep(info.currency) : '0.01'} placeholder={$t('tools.pacAllocator.planner.brokerEditor.fundingCapAll', {default: 'all'})} className={INPUT} testid="pac-planner-funding-cap" />
                                        </div>
                                        <span class={INPUT_SUFFIX}>{#if info.currency}<CurrencyCode code={info.currency} />{/if}</span>
                                    </div>
                                </div>
                            </div>
                        {/if}
                    </li>
                {:else}
                    {#if localCash.length === 0}
                        <li class={HINT} data-testid="pac-planner-funding-empty">{$t('tools.pacAllocator.planner.brokerEditor.noFunding', {default: 'No liquidity can reach this Broker yet: add cash or a contribution in the Liquidity step.'})}</li>
                    {/if}
                {/each}
            </ul>
        </section>

        <p class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.notYetSupported', {default: 'Not supported yet: tax regime, losses, sell fees.'})}</p>
    {/if}

    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-broker-editor-cancel" onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} disabled={!working} data-testid="pac-planner-broker-editor-apply" onclick={apply}>{$t('tools.pacAllocator.planner.applyToDraft', {default: 'Apply to the draft'})}</button>
    {/snippet}
</PlannerDialog>
