<!--
  The broker's operating profile panel (P2 of project 67, M10, D17): one component for «Edit broker» and, from P3, the
  planner's «Configure …» window. It knows neither the broker nor the planner: it gets a draft (`brokerOperatingProfile.ts`)
  and reports every edit through `onchange`, with a fresh copy of the whole draft.

  In the mockup's order (screen 14): a block per currency (M21: currency, order type, increment, purchase fee, sale fee
  with «same as the purchase», remove), «Add currency» and «Copy the rules from another currency»; then the currency
  conversion and the tax regime as big choice cards (M6), «Declarative» badged as the default (M18), and «The Broker
  converts when you buy» too (TL-6 of project 67: the default of a Broker that said nothing). The order row has three
  columns: the order type, the increment aligned right, and beside it, for an order by amount, its currency in the
  project's form (`symbol flag code`).

  `groups` chooses what is shown (every group when absent: «Edit broker»); a hidden group is kept in the draft and handed
  back untouched (P2, fact 8). `stepFor` lets the caller reset the increment when the order type changes, `rootTestid`
  rename the root when its page already uses the prefix as an id (both P3, the planner). `requiredCurrencies` (the planner's) adds an empty block for each currency the plan
  trades in and the profile lacks. Project controls only (M5): `CurrencySearchSelect`, `SimpleSelect`, `ExactDecimalInput`;
  an empty field is as tall as a filled one (M8). It imports nothing from `features/tools/` (D17).
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {Copy, Info, Plus, Trash2} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_} from '$lib/i18n';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import ChoiceCards from './ChoiceCards.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {currencyStoreVersion, ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {formatCurrencyCodeHtml} from '$lib/utils/currency/currencyFormat';
    import {copyRules, DEFAULT_CONVERSION_MODE, newRule, PROFILE_GROUPS, profileProblems, type ConversionMode, type FeeDraft, type OrderKind, type ProfileDraft, type ProfileField, type ProfileGroup, type RuleDraft, type TaxRegime} from './brokerOperatingProfile';

    interface Props {
        draft: ProfileDraft;
        groups?: readonly ProfileGroup[];
        requiredCurrencies?: readonly string[];
        testIdPrefix?: string;
        /** The root's test id, `testIdPrefix` unless the caller's page already uses that id (P3: the planner's root). */
        rootTestid?: string;
        /**
         * The increment a rule takes when its order type, or the currency of a rule by amount, changes (P3: the planner's
         * rule, the currency's smallest unit by amount). Absent: the increment stays as typed.
         */
        stepFor?: (kind: OrderKind, currency: string) => string;
        disabled?: boolean;
        onchange: (draft: ProfileDraft) => void;
    }

    let {draft, groups = PROFILE_GROUPS, requiredCurrencies = [], testIdPrefix = 'broker-profile', rootTestid, stepFor, disabled = false, onchange}: Props = $props();

    const P = 'brokers.operatingProfile';

    function withRequired(source: ProfileDraft): ProfileDraft {
        const copy = structuredClone(source);
        for (const currency of requiredCurrencies) {
            if (!copy.rules.some((rule) => rule.currency === currency)) copy.rules.push(newRule(currency));
        }
        return copy;
    }

    /** The panel's own copy: a new `draft` from the parent (a new reading) starts it again. */
    let working = $state<ProfileDraft>(untrack(() => withRequired(draft)));
    let lastDraft = untrack(() => draft);
    $effect.pre(() => {
        if (draft !== lastDraft) {
            lastDraft = draft;
            working = withRequired(draft);
        }
    });

    const shows = (group: ProfileGroup) => groups.includes(group);
    const problems = $derived(profileProblems(working));
    const invalid = (rule: RuleDraft, field: ProfileField) => problems.some((problem) => problem.ruleKey === rule.key && problem.field === field);
    const id = (suffix: string) => `${testIdPrefix}-${suffix}`;
    /** One literal key per problem, so the i18n audit can prove each one is used. */
    function problemText(key: string): string {
        switch (key) {
            case 'currencyMissing':
                return $_('brokers.operatingProfile.problems.currencyMissing');
            case 'notANumber':
                return $_('brokers.operatingProfile.problems.notANumber');
            case 'stepNotPositive':
                return $_('brokers.operatingProfile.problems.stepNotPositive');
            case 'stepNotWhole':
                return $_('brokers.operatingProfile.problems.stepNotWhole');
            default:
                return $_('brokers.operatingProfile.problems.feeNegative');
        }
    }

    function changed(): void {
        onchange($state.snapshot(working) as ProfileDraft);
    }

    function setFee(rule: RuleDraft, side: 'buy' | 'sell', name: keyof FeeDraft, value: string): void {
        rule[side][name] = value;
        changed();
    }

    const orderKinds = $derived([
        {value: 'whole_quantity', label: $_(`${P}.orderKindQuantity`)},
        {value: 'monetary_amount', label: $_(`${P}.orderKindAmount`)},
    ]);
    /** The four fields of a fee, each with its literal label key (the i18n audit proves each one). */
    const FEE_FIELDS: {name: keyof FeeDraft; suffix: string; label: () => string}[] = [
        {name: 'minimum', suffix: 'floor', label: () => $_('brokers.operatingProfile.feeMinimum')},
        {name: 'ratePercent', suffix: 'rate', label: () => $_('brokers.operatingProfile.feeRate')},
        {name: 'maximum', suffix: 'cap', label: () => $_('brokers.operatingProfile.feeMaximum')},
        {name: 'fixed', suffix: 'fixed', label: () => $_('brokers.operatingProfile.feeFixed')},
    ];
    const sideLabel = (side: 'buy' | 'sell') => (side === 'buy' ? $_('brokers.operatingProfile.buyFee') : $_('brokers.operatingProfile.sellFee'));

    // The currency beside an amount's increment (TL-6): the catalogue gives its symbol and flag; until it arrives, the code.
    $effect(() => {
        ensureCurrenciesLoaded($currentLanguage).catch(() => undefined);
    });
    function currencyHtml(code: string): string {
        void $currencyStoreVersion;
        return formatCurrencyCodeHtml(code);
    }

    const conversionOptions = $derived([
        {value: 'manual' as ConversionMode, label: $_(`${P}.conversionManual`)},
        {value: 'automatic' as ConversionMode, label: $_(`${P}.conversionAutomatic`)},
    ]);
    const regimeOptions = $derived([
        {value: 'administered' as TaxRegime, label: $_(`${P}.taxAdministered`), description: $_(`${P}.taxAdministeredHelp`)},
        {value: 'declarative' as TaxRegime, label: $_(`${P}.taxDeclarative`), description: $_(`${P}.taxDeclarativeHelp`)},
    ]);

    // «Copy the rules from another currency» (M21).
    let copying = $state(false);
    let copyFrom = $state('');
    let copyTo = $state('');
    const usedCurrencies = $derived(new Set(working.rules.map((rule) => rule.currency).filter((code) => code !== '')));
    const sourceOptions = $derived(working.rules.filter((rule) => rule.currency !== '').map((rule) => ({value: rule.key, label: rule.currency})));

    function openCopy(): void {
        copyFrom = sourceOptions[0]?.value ?? '';
        copyTo = '';
        copying = true;
    }

    function confirmCopy(): void {
        if (copyRules(working, copyFrom, copyTo)) {
            copying = false;
            changed();
        }
    }
</script>

{#snippet feeFields(rule: RuleDraft, side: 'buy' | 'sell')}
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {#each FEE_FIELDS as field (field.name)}
            <label class="block space-y-1">
                <span class="block text-xs font-medium text-lf-secondary">{field.label()}</span>
                <ExactDecimalInput
                    value={rule[side][field.name]}
                    step={field.name === 'ratePercent' ? '0.01' : '1'}
                    ariaLabel={`${sideLabel(side)} · ${field.label()}`}
                    externalInvalid={invalid(rule, `${side}.${field.name}`)}
                    {disabled}
                    testid={side === 'buy' ? id(`mode-fee-${field.suffix}`) : id(`mode-sell-fee-${field.suffix}`)}
                    onchange={(value) => setFee(rule, side, field.name, value)}
                />
            </label>
        {/each}
    </div>
{/snippet}

<div class="space-y-4 text-lf-primary" data-testid={rootTestid ?? testIdPrefix}>
    <section class="space-y-3" data-testid={id('group')} data-group="orderMode">
        {#if working.rules.length === 0}
            <p class="text-sm text-lf-muted" data-testid={id('mode-empty')}>{$_(`${P}.empty`)}</p>
        {/if}
        {#each working.rules as rule (rule.key)}
            {@const required = requiredCurrencies.includes(rule.currency)}
            <div class="space-y-3 rounded-lg border border-lf-subtle bg-lf-card p-3" data-testid={id('mode')} data-currency={rule.currency} data-kind={rule.orderKind} data-rule-key={rule.key} data-required={required ? 'true' : 'false'}>
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="w-44 space-y-1">
                        <span class="block text-xs font-medium text-lf-secondary">{$_(`${P}.currency`)}</span>
                        <CurrencySearchSelect
                            value={rule.currency}
                            excludedCurrencies={new Set([...usedCurrencies].filter((code) => code !== rule.currency))}
                            {disabled}
                            compact
                            testId={id('mode-currency')}
                            onchange={(value) => {
                                rule.currency = value;
                                if (stepFor && rule.orderKind === 'monetary_amount') rule.step = stepFor(rule.orderKind, value);
                                changed();
                            }}
                        />
                    </div>
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm text-lf-danger hover:bg-lf-danger-soft focus-visible:outline-2 focus-visible:outline-lf-focus disabled:opacity-50"
                        aria-label={$_(`${P}.removeCurrency`, {values: {currency: rule.currency || '—'}})}
                        {disabled}
                        data-testid={id('mode-remove')}
                        onclick={() => {
                            working.rules = working.rules.filter((item) => item.key !== rule.key);
                            changed();
                        }}
                    >
                        <Trash2 class="h-4 w-4" aria-hidden="true" />
                    </button>
                </div>
                {#if required}
                    <p class="text-xs text-lf-warning" data-testid={id('mode-required')}>{$_(`${P}.requiredCurrency`)}</p>
                {/if}
                {#each [...new Set(problems.filter((problem) => problem.ruleKey === rule.key).map((problem) => problem.key))] as key (key)}
                    <p class="text-xs text-lf-danger" data-testid={id('mode-problem')} data-key={key}>{problemText(key)}</p>
                {/each}
                <!-- Three columns from `sm`; on a phone the order type takes its own line, so its select is not cut. -->
                <div class="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" data-testid={id('mode-row')}>
                    <div class="col-span-2 min-w-0 space-y-1 sm:col-span-1">
                        <span class="block text-xs font-medium text-lf-secondary">{$_(`${P}.orderKind`)}</span>
                        <SimpleSelect
                            value={rule.orderKind}
                            options={orderKinds}
                            {disabled}
                            testId={id('mode-kind')}
                            ariaLabel={$_(`${P}.orderKind`)}
                            optionTestId={(option) => id(`mode-kind-option-${option.value}`)}
                            onchange={(value) => {
                                if (value === rule.orderKind) return;
                                rule.orderKind = value as OrderKind;
                                if (stepFor) rule.step = stepFor(rule.orderKind, rule.currency);
                                changed();
                            }}
                        />
                    </div>
                    <label class="block min-w-0 space-y-1">
                        <span class="flex items-center gap-1 text-xs font-medium text-lf-secondary">
                            {$_(`${P}.step`)}
                            <Tooltip text={$_(`${P}.stepHelp`)} maxWidth="320px"><Info size={14} class="text-lf-muted" aria-hidden="true" /></Tooltip>
                        </span>
                        <ExactDecimalInput
                            value={rule.step}
                            step={rule.orderKind === 'whole_quantity' ? '1' : '0.01'}
                            ariaLabel={$_(`${P}.step`)}
                            externalInvalid={invalid(rule, 'step')}
                            {disabled}
                            testid={id('mode-step')}
                            className="text-right"
                            onchange={(value) => {
                                rule.step = value;
                                changed();
                            }}
                        />
                    </label>
                    <!-- The third column: the currency of an amount, beside its number; nothing for whole units, or while no currency is chosen. -->
                    <span class="flex min-h-10 items-center whitespace-nowrap text-sm text-lf-secondary" data-testid={id('mode-step-currency')} data-currency={rule.orderKind === 'monetary_amount' ? rule.currency : ''}>
                        {#if rule.orderKind === 'monetary_amount' && rule.currency !== ''}<span>{@html sanitizeHtml(currencyHtml(rule.currency))}</span>{/if}
                    </span>
                </div>
                {#if shows('buyFee')}
                    <div class="space-y-2 border-t border-lf-subtle pt-3" data-testid={id('group')} data-group="buyFee">
                        <p class="flex items-center gap-1 text-sm font-medium">
                            {$_(`${P}.buyFee`)}
                            <Tooltip text={$_(`${P}.feeHelp`)} maxWidth="320px"><Info size={14} class="text-lf-muted" aria-hidden="true" /></Tooltip>
                        </p>
                        {@render feeFields(rule, 'buy')}
                    </div>
                {/if}
                {#if shows('sellFee')}
                    <div class="space-y-2 border-t border-lf-subtle pt-3" data-testid={id('group')} data-group="sellFee">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <p class="text-sm font-medium">{$_(`${P}.sellFee`)}</p>
                            <label class="inline-flex items-center gap-2 text-sm text-lf-secondary">
                                <input
                                    type="checkbox"
                                    class="accent-lf-checked"
                                    checked={rule.sellSameAsBuy}
                                    {disabled}
                                    data-testid={id('mode-sell-same')}
                                    onchange={(event) => {
                                        rule.sellSameAsBuy = event.currentTarget.checked;
                                        changed();
                                    }}
                                />
                                {$_(`${P}.sameAsBuy`)}
                            </label>
                        </div>
                        {#if !rule.sellSameAsBuy}
                            {@render feeFields(rule, 'sell')}
                        {/if}
                    </div>
                {/if}
            </div>
        {/each}
        <div class="flex flex-wrap gap-2">
            <button
                type="button"
                class="inline-flex items-center gap-1.5 rounded-lg border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-primary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus disabled:opacity-50"
                {disabled}
                data-testid={id('mode-add')}
                onclick={() => {
                    working.rules.push(newRule());
                    changed();
                }}
            >
                <Plus class="h-4 w-4" aria-hidden="true" />
                {$_(`${P}.addCurrency`)}
            </button>
            {#if sourceOptions.length > 0}
                <button
                    type="button"
                    class="inline-flex items-center gap-1.5 rounded-lg border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-primary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus disabled:opacity-50"
                    {disabled}
                    data-testid={id('copy-open')}
                    onclick={openCopy}
                >
                    <Copy class="h-4 w-4" aria-hidden="true" />
                    {$_(`${P}.copyRules`)}
                </button>
            {/if}
        </div>
        {#if copying}
            <div class="grid gap-2 rounded-lg border border-lf-subtle bg-lf-card p-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end" data-testid={id('copy')}>
                <div class="space-y-1">
                    <span class="block text-xs font-medium text-lf-secondary">{$_(`${P}.copyFrom`)}</span>
                    <SimpleSelect value={copyFrom} options={sourceOptions} testId={id('copy-from')} ariaLabel={$_(`${P}.copyFrom`)} onchange={(value) => (copyFrom = value)} />
                </div>
                <div class="space-y-1">
                    <span class="block text-xs font-medium text-lf-secondary">{$_(`${P}.copyTo`)}</span>
                    <CurrencySearchSelect value={copyTo} excludedCurrencies={usedCurrencies} compact testId={id('copy-to')} onchange={(value) => (copyTo = value)} />
                </div>
                <div class="flex gap-2">
                    <button type="button" class="rounded-lg px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-lf-focus" data-testid={id('copy-cancel')} onclick={() => (copying = false)}>{$_(`${P}.cancel`)}</button>
                    <button
                        type="button"
                        class="rounded-lg bg-lf-action px-3 py-1.5 text-sm text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-lf-focus disabled:opacity-50"
                        disabled={!copyFrom || !/^[A-Z]{3}$/.test(copyTo) || usedCurrencies.has(copyTo)}
                        data-testid={id('copy-confirm')}
                        onclick={confirmCopy}>{$_(`${P}.copyConfirm`)}</button
                    >
                </div>
            </div>
        {/if}
    </section>

    {#if shows('conversion')}
        <section class="space-y-2" data-testid={id('group')} data-group="conversion">
            <p class="text-sm font-medium">{$_(`${P}.conversion`)}</p>
            <ChoiceCards
                name="{testIdPrefix}-conversion"
                legend={$_(`${P}.conversion`)}
                options={conversionOptions}
                value={working.conversionMode}
                defaultValue={DEFAULT_CONVERSION_MODE}
                defaultLabel={$_(`${P}.defaultBadge`)}
                {disabled}
                testid={id('conversion-modes')}
                cardTestid={id('conversion-mode')}
                radioTestid={id('conversion-mode-radio')}
                valueAttribute="mode"
                onchange={(value) => {
                    working.conversionMode = value;
                    changed();
                }}
            />
        </section>
    {/if}

    {#if shows('taxRegime')}
        <section class="space-y-2" data-testid={id('group')} data-group="taxRegime">
            <p class="text-sm font-medium">{$_(`${P}.taxRegime`)}</p>
            <ChoiceCards
                name="{testIdPrefix}-tax-regime"
                legend={$_(`${P}.taxRegime`)}
                options={regimeOptions}
                value={working.taxRegime}
                defaultValue="declarative"
                defaultLabel={$_(`${P}.defaultBadge`)}
                {disabled}
                testid={id('tax-regime')}
                onchange={(value) => {
                    working.taxRegime = value;
                    changed();
                }}
            />
        </section>
    {/if}
</div>
