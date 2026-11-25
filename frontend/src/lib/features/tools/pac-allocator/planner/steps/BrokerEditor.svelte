<!--
  The scenario data of one Broker: how you buy there in each currency, what a purchase costs, and
  which liquidity may pay for it. It edits a copy, and «Apply» writes that copy back to the draft.

  P3 of project 67: the order modes, the purchase fee and the currency conversion are edited with the broker's own
  operating profile panel (`BrokerOperatingProfileBox`, groups `orderMode`, `buyFee`, `conversion`), through
  `brokerProfileAdapter.ts`; the liquidity sources stay the planner's. «Restore» goes back to the modes copied from the
  account's profile (D12), or to the default modes when it has none.
-->
<script lang="ts">
    import {tick, untrack} from 'svelte';
    import {PiggyBank, Save} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import BrokerOperatingProfileBox from '$lib/features/brokers/profile/BrokerOperatingProfileBox.svelte';
    import {DEFAULT_CONVERSION_MODE, fromDraft, profileProblems, type OrderKind, type ProfileDraft, type ProfileGroup} from '$lib/features/brokers/profile/brokerOperatingProfile';
    import {modeKeys, modesFromProfile, modesOf, profileDraftOf} from '../brokerProfileAdapter';
    import {planProfileSave, readStoredProfile, writeStoredProfile, type ProfileSavePhase, type ProfileSavePlan, type ProfileWriteOutcome} from '../brokerProfileSave';
    import {DEFAULT_QUANTITY_STEP} from '../defaults';
    import {brokerModesModified, defaultMode, type DraftBroker, type DraftFunding, type FundingSourceRef, type PlannerDraft} from '../draft.svelte';
    import {cldrCurrencyStep, formatPlannerMoneyPlain} from '../format';
    import {fundingSourceHelp} from '../modeText';
    import {BADGE, BUTTON_LINK, BUTTON_PRIMARY, BUTTON_SECONDARY, HINT, ICON_BUBBLE, INPUT, INPUT_SUFFIX, LABEL_ROW, SECTION_TITLE, TITLE_INPUT, TOGGLE_CARD, TOGGLE_OFF, TOGGLE_ON} from '../ui';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import PlannerBrokerIcon from '../shared/PlannerBrokerIcon.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';
    import ProfileSaveConfirm from '../shared/ProfileSaveConfirm.svelte';
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

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

    /** The planner shows the purchase side only: the sale fee and the tax regime are not part of a plan yet. */
    const BOX_GROUPS: readonly ProfileGroup[] = ['orderMode', 'buyFee', 'conversion'];

    const ids = $props.id();
    // Mount = open: the editor works on a copy taken once, and writes it back only on apply.
    const original = untrack(() => draft.broker(brokerKey));
    let working = $state<DraftBroker | null>(original ? structuredClone($state.snapshot(original)) : null);
    // A source not yet paired with this Broker starts allowed, as `syncFunding` does in the draft. A Tool without funding
    // routes (the Rebalancer) has none to pair, and no liquidity section below.
    untrack(() => {
        if (!working || !profile.fundingRoutes) return;
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
    /** The box marks the block the Route step asked for, only when the Broker did not have it. */
    const requiredCurrencies = untrack(() => (addedKey ? [addCurrency] : []));

    /** The panel's starting draft: a new object only on «Restore», so the panel never restarts while the user types. */
    let boxDraft = $state.raw<ProfileDraft>(untrack(() => profileDraftOf(working?.modes ?? [], working?.conversionMode ?? DEFAULT_CONVERSION_MODE)));
    /** The panel's latest draft, for its local problems. */
    let latest = $state.raw<ProfileDraft>(untrack(() => boxDraft));
    const problems = $derived(profileProblems(latest));
    let keyFor = untrack(() => modeKeys(working?.modes.map((mode) => mode.key) ?? [], () => draft.nextId('mode')));

    /** The increment that follows a new order type, or a new currency by amount (as before the shared panel). */
    function stepFor(kind: OrderKind, currency: string): string {
        return kind === 'whole_quantity' ? DEFAULT_QUANTITY_STEP : cldrCurrencyStep(currency);
    }

    function profileChanged(next: ProfileDraft): void {
        latest = next;
        // A confirm list speaks of the values it was computed on: an edit closes it.
        closeProfileSave();
        if (!working) return;
        const back = modesOf(next, keyFor);
        working.modes = back.modes;
        working.conversionMode = back.conversionMode;
    }

    /** `profile`: as the account's profile gave them; `modified`: changed since; `none`: no profile was copied. */
    const modesOrigin = $derived(!working || (working.copiedModes === null && working.copiedConversionMode === null) ? 'none' : brokerModesModified(working) ? 'modified' : 'profile');

    function restoreProposed(): void {
        if (!working) return;
        working.modes = working.copiedModes ? structuredClone($state.snapshot(working.copiedModes)) : draft.defaultModes(working.observedCurrencies);
        working.conversionMode = working.copiedConversionMode ?? DEFAULT_CONVERSION_MODE;
        keyFor = modeKeys(
            working.modes.map((mode) => mode.key),
            () => draft.nextId('mode'),
        );
        boxDraft = profileDraftOf(working.modes, working.conversionMode);
        latest = boxDraft;
        closeProfileSave();
    }

    // -- «Save to the broker profile» (M10, D18, N4) ---------------------------------------------------------------

    /** Only a Broker copied from LibreFolio has a profile to write; a manual one never (W2). */
    const savable = $derived(working !== null && working.origin === 'copied' && working.sourceBrokerId !== null);
    /** The profile as the last copy (or save) knew it; `null` when it had none. */
    const knownProfile = $derived(working && (working.copiedModes !== null || working.copiedConversionMode !== null) ? fromDraft(profileDraftOf(working.copiedModes ?? [], working.copiedConversionMode ?? DEFAULT_CONVERSION_MODE)) : null);
    /** Off when the scenario says nothing the profile does not say already. */
    const saveHasChanges = $derived(working ? planProfileSave(knownProfile, working.modes, working.conversionMode).changes.length > 0 : false);
    let savePhase = $state<ProfileSavePhase | null>(null);
    let savePlan = $state.raw<ProfileSavePlan | null>(null);
    let saveRefusal = $state<string | null>(null);

    /** N4: re-read the broker, then show what the save would change; nothing is written yet. */
    async function startProfileSave(): Promise<void> {
        if (!working || working.sourceBrokerId === null) return;
        savePhase = 'reading';
        savePlan = null;
        saveRefusal = null;
        try {
            const stored = await readStoredProfile(working.sourceBrokerId);
            if (!working || savePhase !== 'reading') return;
            savePlan = planProfileSave(stored, working.modes, working.conversionMode);
            savePhase = 'confirm';
        } catch {
            if (savePhase === 'reading') savePhase = 'readFailed';
        }
    }

    /** D18: one write of the merged document; the copy then follows what the account now says. */
    async function confirmProfileSave(): Promise<void> {
        if (!working || working.sourceBrokerId === null || !savePlan || savePhase !== 'confirm') return;
        const plan = savePlan;
        savePhase = 'writing';
        let outcome: ProfileWriteOutcome;
        try {
            outcome = await writeStoredProfile(working.sourceBrokerId, plan.document);
        } catch {
            savePhase = 'writeFailed';
            return;
        }
        if (!outcome.ok) {
            saveRefusal = outcome.error;
            savePhase = 'refused';
            return;
        }
        const copiedModes = modesFromProfile(plan.document, () => draft.nextId('mode'));
        const copiedConversionMode = plan.document ? (plan.document.conversion_mode ?? DEFAULT_CONVERSION_MODE) : null;
        working.copiedModes = copiedModes;
        working.copiedConversionMode = copiedConversionMode;
        // The draft's Broker learns the new copy too: the account changed even if this window is cancelled.
        const target = draft.broker(working.key);
        if (target) {
            target.copiedModes = copiedModes ? structuredClone(copiedModes) : null;
            target.copiedConversionMode = copiedConversionMode;
        }
        savePhase = 'saved';
    }

    /** «Save to the broker»: the confirmation modal gives the focus back to it when it closes without writing (R1-C). */
    let saveButton = $state<HTMLButtonElement | undefined>(undefined);

    function closeProfileSave(): void {
        if (savePhase === 'writing') return;
        const asked = savePhase === 'confirm';
        savePhase = null;
        savePlan = null;
        saveRefusal = null;
        if (asked) void tick().then(() => saveButton?.focus({preventScroll: true}));
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

<PlannerDialog open title={$t('tools.pacAllocator.planner.brokerEditor.title', {default: 'Configure {name} · scenario data (the Broker is not changed)', values: {name: working?.name || '—'}})} testid={testId('broker-editor', profile)} {onclose} maxWidth="4xl">
    {#if working}
        <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
            <PlannerBrokerIcon broker={working} size={32} />
            {#if working.origin === 'copied'}
                <span class="min-w-0 truncate text-base font-semibold text-lf-primary">{working.name}</span>
            {:else}
                <div class="min-w-0 flex-1 sm:max-w-sm">
                    <input class={TITLE_INPUT} bind:value={working.name} maxlength="120" aria-label={$t('common.name', {default: 'Name'})} placeholder={$t('common.name', {default: 'Name'})} data-testid={testId('broker-editor-name', profile)} />
                </div>
            {/if}
            {#if working.origin === 'copied'}
                <button type="button" class="{BUTTON_LINK} sm:ml-auto" data-testid={testId('broker-editor-restore', profile)} onclick={restoreProposed}>
                    {$t('tools.pacAllocator.planner.brokerEditor.restore', {default: 'Restore the copied values'})}
                </button>
            {/if}
        </div>

        <section class="space-y-3" aria-labelledby="{ids}-modes" data-testid={testId('broker-editor-modes', profile)} data-origin={modesOrigin}>
            <div class="flex items-center gap-0.5">
                <h3 id="{ids}-modes" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokerEditor.modes', {default: 'How you buy, currency by currency'})}</h3>
                <HelpTip
                    label={$t('tools.pacAllocator.planner.brokerEditor.modes', {default: 'How you buy, currency by currency'})}
                    help={$t('tools.pacAllocator.planner.brokerEditor.modesHelp', {default: 'One block for each currency you buy in at this Broker: an Asset priced in that currency is bought with its rules. Drag the blocks into the order you prefer.'})}
                />
            </div>
            {#if addedKey}
                <p class="rounded-md border border-lf-warning-line bg-lf-warning-soft px-2.5 py-1.5 text-xs text-lf-warning-on-soft" data-testid={testId('mode-added-for', profile)}>
                    {$t('tools.pacAllocator.planner.brokerEditor.addedFor', {
                        default: '{currency} mode added to buy {asset}, with starting values: check order type, increment and fees, then apply.',
                        values: {currency: addCurrency, asset: addFor || '—'},
                    })}
                </p>
            {/if}
            {#if problems.length > 0}
                <p class="text-sm text-lf-danger" role="alert" data-testid={testId('broker-editor-profile-problems', profile)}>
                    {$t('tools.pacAllocator.planner.brokerEditor.fixBeforeApplying', {default: 'Some fields are not valid: fix the ones in red to apply.'})}
                </p>
            {/if}
            <BrokerOperatingProfileBox draft={boxDraft} groups={BOX_GROUPS} {requiredCurrencies} testIdPrefix={profile.testIdPrefix} rootTestid={testId('broker-editor-profile', profile)} {stepFor} onchange={profileChanged} />
        </section>

        {#if profile.fundingRoutes}
            <section class="space-y-3" aria-labelledby="{ids}-funding" data-testid={testId('broker-editor-funding', profile)}>
                <div class="flex items-center gap-0.5">
                    <h3 id="{ids}-funding" class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.brokerEditor.funding', {default: 'Liquidity {name} may use', values: {name: working.name || '—'}})}</h3>
                    <HelpTip
                        label={$t('tools.pacAllocator.planner.brokerEditor.funding', {default: 'Liquidity {name} may use', values: {name: working.name || '—'}})}
                        help={$t('tools.pacAllocator.planner.brokerEditor.fundingHelp', {default: 'Purchases on this Broker can be paid with its own cash and with every source in green here. Everything starts allowed: click a source to exclude it, click again to allow it.'})}
                    />
                </div>
                <ul class="space-y-2">
                    {#each localCash as cash (cash.key)}
                        <li class="flex flex-wrap items-center gap-2 p-2 {TOGGLE_CARD} {TOGGLE_ON}" data-testid={testId('funding-local', profile)} data-currency={cash.currency}>
                            <PlannerBrokerIcon broker={working} size={20} />
                            <span class="font-medium text-lf-primary">{working.name || '—'}</span>
                            <CurrencyCode code={cash.currency} />
                            <HelpTip label={working.name || '—'} help={fundingSourceHelp($t, 'local', working.name, cash.currency)} />
                        </li>
                    {/each}
                    {#each candidates as source (sourceKey(source))}
                        {@const funding = fundingOf(source)}
                        {@const info = sourceOf(source)}
                        {@const enabled = funding?.enabled === true}
                        <li class="{TOGGLE_CARD} {enabled ? TOGGLE_ON : TOGGLE_OFF}" data-testid={testId('funding', profile)} data-source={sourceKey(source)} data-enabled={enabled ? 'true' : 'false'}>
                            <button type="button" class="flex w-full cursor-pointer flex-wrap items-center gap-2 p-2 text-left" aria-pressed={enabled} data-testid={testId('funding-toggle', profile)} onclick={() => toggleFunding(source, !enabled)}>
                                {#if source.kind === 'contribution'}
                                    <span class={ICON_BUBBLE} style="width: 20px; height: 20px;"><PiggyBank size={12} aria-hidden="true" /></span>
                                {:else}
                                    <PlannerBrokerIcon broker={info.broker} size={20} />
                                {/if}
                                {#if info.label}<span class="font-medium text-lf-primary">{info.label}</span>{/if}
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
                                        <ExactDecimalInput id="{ids}-{funding.key}-priority" bind:value={funding.priority} step="1" maxFractionDigits={0} className={INPUT} testid={testId('funding-priority', profile)} />
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
                                                <ExactDecimalInput
                                                    id="{ids}-{funding.key}-cap"
                                                    bind:value={funding.cap}
                                                    step={info.currency ? cldrCurrencyStep(info.currency) : '0.01'}
                                                    placeholder={$t('tools.pacAllocator.planner.brokerEditor.fundingCapAll', {default: 'all'})}
                                                    className={INPUT}
                                                    testid={testId('funding-cap', profile)}
                                                />
                                            </div>
                                            <span class={INPUT_SUFFIX}
                                                >{#if info.currency}<CurrencyCode code={info.currency} />{/if}</span
                                            >
                                        </div>
                                    </div>
                                </div>
                            {/if}
                        </li>
                    {:else}
                        {#if localCash.length === 0}
                            <li class={HINT} data-testid={testId('funding-empty', profile)}>{$t('tools.pacAllocator.planner.brokerEditor.noFunding', {default: 'No liquidity can reach this Broker yet: add cash or a contribution in the Liquidity step.'})}</li>
                        {/if}
                    {/each}
                </ul>
            </section>
        {/if}

        {#if savePhase}
            <ProfileSaveConfirm phase={savePhase} brokerName={working.name} changes={savePlan?.changes ?? []} refusal={saveRefusal} onconfirm={confirmProfileSave} oncancel={closeProfileSave} />
        {/if}

        <p class={HINT}>{$t('tools.pacAllocator.planner.brokerEditor.notYetSupported', {default: 'Not supported yet: tax regime, losses, sell fees.'})}</p>
    {/if}

    {#snippet footer()}
        {#if savable}
            <button
                bind:this={saveButton}
                type="button"
                class="{BUTTON_SECONDARY} sm:mr-auto"
                disabled={!saveHasChanges || problems.length > 0 || savePhase === 'reading' || savePhase === 'confirm' || savePhase === 'writing'}
                data-testid={testId('broker-editor-profile-save', profile)}
                onclick={startProfileSave}><Save class="h-4 w-4" aria-hidden="true" />{$t('tools.pacAllocator.planner.brokerEditor.profileSave.button')}</button
            >
        {/if}
        <button type="button" class={BUTTON_SECONDARY} data-testid={testId('broker-editor-cancel', profile)} onclick={onclose}>{$t('common.cancel', {default: 'Cancel'})}</button>
        <button type="button" class={BUTTON_PRIMARY} disabled={!working || problems.length > 0} data-testid={testId('broker-editor-apply', profile)} onclick={apply}>{$t('tools.pacAllocator.planner.applyToDraft', {default: 'Apply to the draft'})}</button>
    {/snippet}
</PlannerDialog>
