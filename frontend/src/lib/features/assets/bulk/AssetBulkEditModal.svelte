<!--
  AssetBulkEditModal — «Modifica N asset», step 1 «Campi» (lane 65, mockup-AB-v5).

  The selected assets are changed together: each field starts as «Leave as is» and shows what the assets hold now, with
  counts; a touched field takes the «modified» chip and its own Undo, the header has an Undo-all. Three zones, in this
  order: Other details (icon on the left, the user's URL on the right), Classification (the type), Price and status
  (units per single price, Active, Benchmark). Only the fields that are touched are sent, and for each asset only the
  ones that change for it (`assetBulkEdit.ts`).

  «Verify now» (F4) sends the draft payload to `POST /assets/validate` and shows the answer on top: the blocks (red)
  before the warnings (amber), grouped by code (`assetBulkVerify.ts`). «Remove from the edit» takes the assets of a
  group out of this edit (the selection of the page is not touched); «That's fine» closes the warnings, which do not
  come back and never stop the save. A field a block points at takes the chip «blocked». Any change of the draft or of
  the selection discards the answer: it was about something else.

  The summary and the save (F5) come next: the modal already keeps `step` and publishes it as `data-step`, and
  «Continue to summary» hands the draft, the payload and whether the warnings were accepted to `oncontinue`.

  Published state for the tests: `data-step` on the root, `data-modified` (the count of touched fields),
  `data-verify` (`idle`, `running`, `done`, `failed`) and `data-blocked` (the count of blocking groups), `data-state`
  (`leave`, `yes`, `no`) on the three-state controls, `data-modified` and `data-blocked` on each field.
  Svelte 5 runes.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {_ as t} from '$lib/i18n';
    import {Loader2, Undo, Upload, X} from 'lucide-svelte';
    import {zodiosApi} from '$lib/api';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {AssetTypeSelect} from '$lib/components/ui/select';
    import ImagePickerWrapper from '$lib/components/ui/media/ImagePickerWrapper.svelte';
    import TransactionResultBanner from '$lib/features/transactions/bulk/TransactionResultBanner.svelte';
    import AssetIcon from '../AssetIcon.svelte';
    import {extractErrorMessage} from '$lib/utils/trySave';
    import {assetTypeBadgeClass, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {buildBulkPatch, hasChanges, summarizeChanges, summarizeCurrent, touchedFields, validateQuoteBase, type BulkAsset, type BulkDraft, type BulkFieldKey, type BulkPatchItem, type ValueCounts} from './assetBulkEdit';
    import {affectedIds, hasBlocks, organizeVerify, type VerifyGroup, type VerifyView} from './assetBulkVerify';
    import {patchIssueMessage, type AssetPatchAnswer} from '../assetPatchResult';

    type Tri = 'leave' | 'yes' | 'no';
    const TRI_OPTIONS: readonly Tri[] = ['leave', 'yes', 'no'];

    interface Props {
        open?: boolean;
        /** The selected assets, in the order of the selection. */
        assets: BulkAsset[];
        zIndex?: number;
        onclose?: () => void;
        /** «Continue to summary»: the draft and the items the save would send. */
        oncontinue?: (change: {draft: BulkDraft; items: BulkPatchItem[]; warningsAccepted: boolean}) => void;
    }

    let {open = false, assets, zIndex = 50, onclose, oncontinue}: Props = $props();

    /** Selected assets shown as chips before «Show all». */
    const CHIPS_SHOWN = 4;

    let step = $state<'fields' | 'summary'>('fields');
    // What the user chose; '' and 'leave' are «Leave as is».
    let iconUrl = $state('');
    let userUrl = $state('');
    let assetType = $state('');
    let quoteBaseInput = $state('');
    let active = $state<Tri>('leave');
    let benchmark = $state<Tri>('leave');
    let showAllSelected = $state(false);
    let showImagePicker = $state(false);
    // «Remove from the edit»: assets taken out of this edit (the page's selection stays as it is).
    let removedIds = $state<number[]>([]);
    // «Verify now»: the answer organised for the banners, or null (nothing checked, or the answer went stale).
    let verify = $state<VerifyView | null>(null);
    let verifyRun = $state<'idle' | 'running' | 'done' | 'failed'>('idle');
    let verifyError = $state('');
    let warningsAccepted = $state(false);
    let verifyToken = 0;

    function triValue(choice: Tri): boolean | null {
        return choice === 'leave' ? null : choice === 'yes';
    }

    let quoteCheck = $derived(validateQuoteBase(quoteBaseInput));
    let draft = $derived<BulkDraft>({
        icon_url: iconUrl || null,
        user_url: userUrl,
        asset_type: assetType || null,
        quote_base_quantity: quoteCheck === 'ok' ? Number(quoteBaseInput.trim()) : null,
        active: triValue(active),
        is_benchmark: triValue(benchmark),
    });
    let selection = $derived(assets.filter((asset) => !removedIds.includes(asset.id)));
    let current = $derived(summarizeCurrent(selection));
    let touched = $derived(touchedFields(draft));
    let summary = $derived(summarizeChanges(selection, draft));
    // A unit that is typed but not valid keeps «Continue» off: otherwise another touched field would turn it on and the
    // typed unit would be dropped without a word.
    let canContinue = $derived(hasChanges(selection, draft) && (quoteCheck === 'empty' || quoteCheck === 'ok'));
    let quoteBaseError = $derived(quoteCheck === 'notInteger' ? 'assets.modal.quoteBaseInteger' : quoteCheck === 'belowOne' ? 'assets.modal.quoteBaseMin' : '');
    // The unit shows its chip as soon as something is typed, valid or not.
    let modifiedCount = $derived(touched.length + (quoteCheck !== 'empty' && quoteCheck !== 'ok' ? 1 : 0));

    let shownSelected = $derived(showAllSelected ? selection : selection.slice(0, CHIPS_SHOWN));
    let iconFileName = $derived(iconUrl ? decodeURIComponent(iconUrl.split(/[?#]/)[0].split('/').pop() ?? '') : '');
    let urlPlaceholder = $derived(current.user_url.distinct + (current.user_url.empty > 0 ? 1 : 0) > 1 ? $t('assets.bulkEdit.leaveDifferent') : $t('assets.bulkEdit.leave'));
    let typePlaceholder = $derived(current.asset_type.distinct > 1 ? $t('assets.bulkEdit.leaveDifferent') : $t('assets.bulkEdit.leave'));

    // The answer of the check is about one draft of one selection: any change discards it.
    let verifyKey = $derived(JSON.stringify([draft, selection.map((asset) => asset.id)]));
    $effect(() => {
        verifyKey;
        untrack(() => discardVerify());
    });

    let blockedCount = $derived(verify ? verify.blocks.length : 0);
    let warningGroups = $derived(verify && !warningsAccepted ? verify.warnings : []);

    function discardVerify() {
        verifyToken++;
        verify = null;
        verifyRun = 'idle';
        verifyError = '';
        warningsAccepted = false;
    }

    // Every opening starts clean.
    let wasOpen = false;
    $effect(() => {
        if (open && !wasOpen) resetAll();
        wasOpen = open;
    });

    function resetAll() {
        step = 'fields';
        iconUrl = '';
        userUrl = '';
        assetType = '';
        quoteBaseInput = '';
        active = 'leave';
        benchmark = 'leave';
        showAllSelected = false;
        showImagePicker = false;
        removedIds = [];
        discardVerify();
    }

    function resetField(field: BulkFieldKey) {
        if (field === 'icon_url') iconUrl = '';
        else if (field === 'user_url') userUrl = '';
        else if (field === 'asset_type') assetType = '';
        else if (field === 'quote_base_quantity') quoteBaseInput = '';
        else if (field === 'active') active = 'leave';
        else benchmark = 'leave';
    }

    function isModified(field: BulkFieldKey): boolean {
        return field === 'quote_base_quantity' ? quoteBaseInput.trim() !== '' : touched.includes(field);
    }

    function impactOf(field: BulkFieldKey) {
        return summary.fields.find((entry) => entry.field === field) ?? null;
    }

    function handleClose() {
        onclose?.();
    }

    function handleContinue() {
        if (!canContinue) return;
        oncontinue?.({draft, items: buildBulkPatch(selection, draft), warningsAccepted});
    }

    /** «Verify now»: the payload of the draft goes to `POST /assets/validate`, which never writes. */
    async function handleVerify() {
        if (!canContinue || verifyRun === 'running') return;
        const token = ++verifyToken;
        verifyRun = 'running';
        verifyError = '';
        try {
            const answer = (await zodiosApi.validate_assets_patch_api_v1_assets_validate_post(buildBulkPatch(selection, draft) as never)) as AssetPatchAnswer;
            if (token !== verifyToken) return; // the draft changed while the check ran: that answer is about another one
            verify = organizeVerify(answer, selection);
            verifyRun = 'done';
        } catch (err: unknown) {
            if (token !== verifyToken) return;
            verify = null;
            verifyError = extractErrorMessage(err, 'unknown error');
            verifyRun = 'failed';
        }
    }

    function removeFromEdit(ids: number[]) {
        removedIds = [...removedIds, ...ids.filter((id) => !removedIds.includes(id))];
    }

    function blockedOf(field: BulkFieldKey): number {
        return verify?.blockedFields[field] ?? 0;
    }

    function paramText(group: VerifyGroup, entryIndex: number, key: string): string {
        const params = group.entries[entryIndex].issue.params;
        const value = params && typeof params === 'object' ? (params as Record<string, unknown>)[key] : undefined;
        return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
    }

    function typeLabel(type: unknown): string {
        const code = typeof type === 'string' ? type : '';
        return code ? $t(`assets.types.${code}`) : '';
    }

    function handleIconChange(url: string) {
        iconUrl = url || '';
        showImagePicker = false;
    }

    function triLabel(choice: Tri): string {
        return choice === 'leave' ? $t('assets.bulkEdit.leave') : choice === 'yes' ? $t('assets.bulkEdit.yes') : $t('assets.bulkEdit.no');
    }

    function flagLabel(value: boolean): string {
        return value ? $t('assets.bulkEdit.yes') : $t('assets.bulkEdit.no');
    }
</script>

{#snippet fieldHead(field: BulkFieldKey, label: string, forId?: string, labelId?: string)}
    <div class="mb-1 flex min-h-[26px] flex-wrap items-center gap-1.5">
        {#if forId}
            <label for={forId} class="text-sm font-medium text-lf-primary">{label}</label>
        {:else}
            <span id={labelId} class="text-sm font-medium text-lf-primary">{label}</span>
        {/if}
        {#if blockedOf(field) > 0}
            <span class="rounded px-1.5 py-0.5 text-[10px] font-medium bg-lf-danger-soft text-lf-danger-on-soft" data-testid="asset-bulk-{field}-blocked">{$t('assets.bulkEdit.blocked')}</span>
        {/if}
        {#if isModified(field)}
            <span class="rounded px-1.5 py-0.5 text-[10px] font-medium bg-lf-selected text-lf-link" data-testid="asset-bulk-{field}-chip">{$t('assets.bulkEdit.modified')}</span>
            <button type="button" class="ml-auto rounded-lg bg-lf-panel p-1.5 text-lf-secondary transition-colors hover:bg-lf-neutral" title={$t('common.undo')} aria-label={$t('common.undo')} data-testid="asset-bulk-reset-{field}" onclick={() => resetField(field)}>
                <Undo size={14} />
            </button>
        {/if}
    </div>
{/snippet}

{#snippet impactLine(field: BulkFieldKey)}
    {@const impact = impactOf(field)}
    {#if blockedOf(field) > 0}
        <p class="mt-1 text-[11px] text-lf-danger" data-testid="asset-bulk-{field}-blocked-line" data-blocked={blockedOf(field)}>
            {$t('assets.bulkEdit.blockedFor', {values: {count: blockedOf(field), total: selection.length}})}
        </p>
    {/if}
    {#if impact}
        <p class="mt-1 text-[11px] text-lf-muted" data-testid="asset-bulk-{field}-impact" data-changing={impact.changing} data-total={impact.total}>
            {$t('assets.bulkEdit.changesFor', {values: {changing: impact.changing, total: impact.total}})}{#if impact.alreadyIds.length > 0 && impact.changing > 0}
                · {$t('assets.bulkEdit.alreadyHave', {values: {already: impact.alreadyIds.length}})}{/if}
        </p>
    {/if}
{/snippet}

{#snippet moreCount(counts: ValueCounts<unknown>)}
    {#if counts.more > 0}
        <span class="text-lf-muted" data-testid="asset-bulk-now-more">{$t('assets.bulkEdit.more', {values: {count: counts.more}})}</span>
    {/if}
{/snippet}

{#snippet nowFlags(field: 'active' | 'is_benchmark', counts: ValueCounts<boolean>)}
    <p class="text-[11px] text-lf-muted" data-testid="asset-bulk-{field}-now">
        {$t('assets.bulkEdit.now')}
        {#each counts.shown as group (group.value)}
            <span class="text-lf-secondary">{flagLabel(group.value)} ×{group.count}</span>{' '}
        {/each}
        {@render moreCount(counts)}
    </p>
{/snippet}

{#snippet triState(field: 'active' | 'is_benchmark', labelId: string, value: Tri, set: (next: Tri) => void)}
    <div role="radiogroup" aria-labelledby={labelId} class="inline-flex w-full overflow-hidden rounded-lg border border-lf-input" data-testid="asset-bulk-{field}" data-state={value} data-modified={value !== 'leave' ? 'true' : 'false'}>
        {#each TRI_OPTIONS as option (option)}
            <button
                type="button"
                role="radio"
                aria-checked={value === option}
                data-testid="asset-bulk-{field}-{option}"
                class="min-w-0 flex-1 truncate px-2 py-1.5 text-xs font-medium transition-colors focus-visible:outline-lf-focus {value === option ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-field text-lf-secondary hover:bg-lf-hover'}"
                onclick={() => set(option)}
            >
                {triLabel(option)}
            </button>
        {/each}
    </div>
{/snippet}

{#snippet removeButton(label: string, tone: 'block' | 'warning', testId: string, ids: number[])}
    <button
        type="button"
        class="rounded-lg border bg-lf-card px-3 py-1 text-xs font-medium transition-colors hover:bg-lf-hover {tone === 'block' ? 'border-lf-danger-line text-lf-danger-on-soft' : 'border-lf-warning-line text-lf-warning-on-soft'}"
        data-testid={testId}
        onclick={() => removeFromEdit(ids)}
    >
        {label}
    </button>
{/snippet}

{#snippet verifyBanners()}
    {#if verifyRun === 'failed'}
        <TransactionResultBanner variant="error" title={$t('assets.bulkEdit.verifyFailed')} subtitle={verifyError} testId="asset-bulk-verify-failed" />
    {/if}
    {#if verify}
        {#each verify.blocks as group (group.code)}
            {@const ids = affectedIds(group)}
            <TransactionResultBanner
                variant="error"
                title={group.code === 'indexWithTransactions' ? $t('assets.bulkEdit.blockIndexTitle') : $t('assets.bulkEdit.blockOtherTitle')}
                subtitle={group.code === 'indexWithTransactions' ? $t('assets.bulkEdit.blockIndexBody', {values: {count: ids.length}}) : $t('assets.bulkEdit.blockOtherBody')}
                testId="asset-bulk-block-{group.code}"
            >
                <ul class="list-disc space-y-0.5 pl-4 text-sm" data-testid="asset-bulk-block-{group.code}-rows">
                    {#each group.entries as entry, at (entry.assetId + ':' + at)}
                        <li data-asset-id={entry.assetId}>
                            {#if group.code === 'indexWithTransactions'}
                                {$t('assets.bulkEdit.blockIndexRow', {values: {name: entry.name, count: Number(paramText(group, at, 'tx_count')) || 0}})}
                            {:else}
                                {entry.name}: {patchIssueMessage(entry.issue, $t)}
                            {/if}
                        </li>
                    {/each}
                </ul>
                <div class="mt-2">{@render removeButton($t('assets.bulkEdit.removeBlocked', {values: {count: ids.length}}), 'block', `asset-bulk-block-${group.code}-remove`, ids)}</div>
            </TransactionResultBanner>
        {/each}
        {#each warningGroups as group (group.code)}
            {@const ids = affectedIds(group)}
            <TransactionResultBanner
                variant="warning"
                title={group.code === 'assetFamilyChange' ? $t('assets.bulkEdit.warnFamilyTitle', {values: {count: ids.length}}) : $t('assets.bulkEdit.warnOtherTitle')}
                subtitle={group.code === 'assetFamilyChange' ? $t('assets.bulkEdit.warnFamilyNote') : ''}
                testId="asset-bulk-warning-{group.code}"
            >
                <ul class="list-disc space-y-0.5 pl-4 text-sm" data-testid="asset-bulk-warning-{group.code}-rows">
                    {#each group.entries as entry, at (entry.assetId + ':' + at)}
                        <li data-asset-id={entry.assetId}>
                            {#if group.code === 'assetFamilyChange'}
                                {$t('assets.bulkEdit.warnFamilyRow', {values: {name: entry.name, from: typeLabel(paramText(group, at, 'from')), to: typeLabel(paramText(group, at, 'to'))}})}
                            {:else}
                                {entry.name}: {patchIssueMessage(entry.issue, $t)}
                            {/if}
                        </li>
                    {/each}
                </ul>
                <div class="mt-2 flex flex-wrap gap-2">
                    {@render removeButton($t('assets.bulkEdit.removeFromEdit'), 'warning', `asset-bulk-warning-${group.code}-remove`, ids)}
                    <button type="button" class="rounded-lg border border-lf-warning-line bg-lf-card px-3 py-1 text-xs font-medium text-lf-warning-on-soft transition-colors hover:bg-lf-hover" data-testid="asset-bulk-warning-{group.code}-ok" onclick={() => (warningsAccepted = true)}>
                        {$t('assets.bulkEdit.warnOk')}
                    </button>
                </div>
            </TransactionResultBanner>
        {/each}
    {/if}
{/snippet}

<ModalBase {open} maxWidth="4xl" allowOverflow={true} onRequestClose={handleClose} {zIndex} testId="asset-bulk-edit-modal" labelledBy="asset-bulk-edit-title">
    <div data-testid="asset-bulk-edit" data-step={step} data-modified={modifiedCount} data-selected={selection.length} data-verify={verifyRun} data-blocked={blockedCount}>
        <!-- Header -->
        <div class="flex items-start justify-between gap-3 border-b border-lf-subtle px-6 py-4">
            <div class="min-w-0">
                <h2 id="asset-bulk-edit-title" class="text-lg font-semibold text-lf-primary" data-testid="asset-bulk-title">{$t('assets.bulkEdit.title', {values: {count: selection.length}})}</h2>
                <p class="mt-0.5 text-sm text-lf-muted" data-testid="asset-bulk-subtitle">
                    {#if modifiedCount > 0}
                        {$t('assets.bulkEdit.subtitleChanged', {values: {fields: modifiedCount, assets: summary.changing}})}
                    {:else}
                        {$t('assets.bulkEdit.subtitle')}
                    {/if}
                </p>
            </div>
            <div class="flex shrink-0 items-center gap-2">
                {#if modifiedCount > 0}
                    <button type="button" class="rounded-lg bg-lf-panel p-2 text-lf-secondary transition-all hover:bg-lf-neutral" title={$t('common.undoAll')} aria-label={$t('common.undoAll')} data-testid="asset-bulk-reset-all" onclick={resetAll}>
                        <Undo size={18} />
                    </button>
                {/if}
                <button type="button" class="text-lf-muted transition-colors hover:text-lf-secondary" aria-label={$t('common.close')} data-testid="asset-bulk-close" onclick={handleClose}>
                    <X size={20} />
                </button>
            </div>
        </div>

        <!-- Body -->
        <div class="max-h-[70vh] min-h-0 space-y-5 overflow-y-auto px-6 py-4">
            <!-- Steps -->
            <ol class="flex items-center gap-3 text-xs font-medium" data-testid="asset-bulk-steps">
                <li class="flex items-center gap-1.5 {step === 'fields' ? 'text-lf-primary' : 'text-lf-muted'}" data-testid="asset-bulk-step-fields" data-active={step === 'fields'}>
                    <span class="flex h-5 w-5 items-center justify-center rounded-full text-[11px] {step === 'fields' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-neutral text-lf-muted'}">1</span>
                    {$t('assets.bulkEdit.stepFields')}
                </li>
                <li class="flex items-center gap-1.5 {step === 'summary' ? 'text-lf-primary' : 'text-lf-muted'}" data-testid="asset-bulk-step-summary" data-active={step === 'summary'}>
                    <span class="flex h-5 w-5 items-center justify-center rounded-full text-[11px] {step === 'summary' ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-neutral text-lf-muted'}">2</span>
                    {$t('assets.bulkEdit.stepSummary')}
                </li>
            </ol>

            <!-- «Verify now»: the blocks first, the warnings after; nothing at all when the check finds nothing -->
            <div class="space-y-2" data-testid="asset-bulk-verify-banners">
                {@render verifyBanners()}
            </div>

            <!-- Selected assets -->
            <div data-testid="asset-bulk-selected">
                <div class="mb-1.5 flex items-center gap-2">
                    <span class="text-xs font-semibold uppercase tracking-wider text-lf-muted">{$t('assets.bulkEdit.selected', {values: {count: selection.length}})}</span>
                    {#if selection.length > CHIPS_SHOWN}
                        <button type="button" class="text-xs text-lf-link hover:underline" data-testid="asset-bulk-selected-toggle" onclick={() => (showAllSelected = !showAllSelected)}>
                            {showAllSelected ? $t('assets.bulkEdit.showLess') : $t('assets.bulkEdit.showAll')}
                        </button>
                    {/if}
                </div>
                <div class="flex flex-wrap gap-1.5">
                    {#each shownSelected as asset (asset.id)}
                        <span class="inline-flex max-w-[16rem] items-center rounded-full bg-lf-panel px-2.5 py-0.5 text-xs text-lf-secondary" data-testid="asset-bulk-selected-chip" data-asset-id={asset.id}>
                            <span class="truncate">{asset.display_name}</span>
                        </span>
                    {/each}
                    {#if !showAllSelected && selection.length > CHIPS_SHOWN}
                        <span class="inline-flex items-center rounded-full bg-lf-panel px-2.5 py-0.5 text-xs text-lf-muted" data-testid="asset-bulk-selected-more">{$t('assets.bulkEdit.more', {values: {count: selection.length - CHIPS_SHOWN}})}</span>
                    {/if}
                </div>
            </div>

            <!-- Zone: Other details -->
            <section class="rounded-xl border border-lf-subtle bg-lf-card p-4" data-testid="asset-bulk-zone-details">
                <h3 class="mb-3 text-xs font-semibold uppercase tracking-wider text-lf-muted">{$t('assets.bulkEdit.zoneDetails')}</h3>
                <div class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    <div data-testid="asset-bulk-field-icon_url" data-modified={isModified('icon_url') ? 'true' : 'false'}>
                        {@render fieldHead('icon_url', $t('common.icon'), undefined, 'asset-bulk-icon-label')}
                        <p class="text-[11px] text-lf-muted" data-testid="asset-bulk-icon_url-now">
                            {$t('assets.bulkEdit.now')}
                            {$t('assets.bulkEdit.nowIcon', {values: {withIcon: current.icon.with, without: current.icon.without}})}
                        </p>
                    </div>
                    <div data-testid="asset-bulk-field-user_url" data-modified={isModified('user_url') ? 'true' : 'false'}>
                        {@render fieldHead('user_url', $t('assets.provider.userUrl'), 'asset-bulk-user-url')}
                        <p class="text-[11px] text-lf-muted" data-testid="asset-bulk-user_url-now">
                            {$t('assets.bulkEdit.now')}
                            {$t('assets.bulkEdit.nowUrl', {values: {distinct: current.user_url.distinct, empty: current.user_url.empty}})}
                        </p>
                    </div>
                    <!-- The icon's circle and the URL field share one centre: the field sits at half the circle's height. -->
                    <div class="flex w-16 flex-col items-center gap-1">
                        <button
                            type="button"
                            class="group relative flex h-16 w-16 items-center justify-center rounded-full {iconUrl ? '' : 'border-2 border-dashed border-lf-input text-lf-muted hover:border-lf-input-hover'}"
                            aria-labelledby="asset-bulk-icon-label"
                            title={$t('assets.bulkEdit.iconPick')}
                            data-testid="asset-bulk-icon-pick"
                            onclick={() => (showImagePicker = true)}
                        >
                            {#if iconUrl}
                                <AssetIcon {iconUrl} size="lg" />
                                <span class="absolute inset-0 flex items-center justify-center rounded-full bg-lf-overlay opacity-0 transition-opacity group-hover:opacity-100">
                                    <Upload class="text-lf-on-overlay" size={16} />
                                </span>
                            {:else}
                                <Upload size={20} />
                            {/if}
                        </button>
                        {#if iconFileName}
                            <span class="max-w-[8rem] truncate text-[10px] text-lf-muted" data-testid="asset-bulk-icon-file">{iconFileName}</span>
                        {/if}
                    </div>
                    <div class="flex h-16 items-center">
                        <input
                            id="asset-bulk-user-url"
                            type="text"
                            bind:value={userUrl}
                            placeholder={urlPlaceholder}
                            data-testid="asset-bulk-user-url"
                            class="w-full rounded-lg border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:border-lf-focus focus:outline-none focus:ring-2 focus:ring-lf-focus/50"
                        />
                    </div>
                </div>
                {@render impactLine('icon_url')}
                {@render impactLine('user_url')}
            </section>

            <!-- Zone: Classification -->
            <section class="rounded-xl border border-lf-subtle bg-lf-card p-4" data-testid="asset-bulk-zone-classification">
                <h3 class="mb-3 text-xs font-semibold uppercase tracking-wider text-lf-muted">{$t('assets.bulkEdit.zoneClassification')}</h3>
                <div
                    class="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,18rem)] sm:items-start {blockedOf('asset_type') > 0 ? 'rounded-lg border border-lf-danger p-2' : ''}"
                    data-testid="asset-bulk-field-asset_type"
                    data-modified={isModified('asset_type') ? 'true' : 'false'}
                    data-blocked={blockedOf('asset_type')}
                >
                    <div>
                        {@render fieldHead('asset_type', $t('common.type'), undefined, 'asset-bulk-type-label')}
                        <p class="flex flex-wrap items-center gap-1 text-[11px] text-lf-muted" data-testid="asset-bulk-asset_type-now">
                            {$t('assets.bulkEdit.now')}
                            {#each current.asset_type.shown as group (group.value)}
                                <span class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium {assetTypeBadgeClass(group.value)}" data-testid="asset-bulk-now-type" data-asset-type={group.value}>
                                    <img src={getAssetTypeIconUrl(group.value)} alt="" class="h-3.5 w-3.5 object-contain" />
                                    {$t(`assets.types.${group.value}`)} ×{group.count}
                                </span>
                            {/each}
                            {@render moreCount(current.asset_type)}
                        </p>
                        {@render impactLine('asset_type')}
                    </div>
                    <div class="sm:pt-[26px]">
                        <AssetTypeSelect bind:value={assetType} testId="asset-bulk-type" placeholder={typePlaceholder} />
                    </div>
                </div>
            </section>

            <!-- Zone: Price and status -->
            <section class="rounded-xl border border-lf-subtle bg-lf-card p-4" data-testid="asset-bulk-zone-price">
                <h3 class="mb-3 text-xs font-semibold uppercase tracking-wider text-lf-muted">{$t('assets.bulkEdit.zonePrice')}</h3>
                <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
                    <div data-testid="asset-bulk-field-quote_base_quantity" data-modified={isModified('quote_base_quantity') ? 'true' : 'false'}>
                        {@render fieldHead('quote_base_quantity', $t('assets.modal.quoteBaseQuantity'), 'asset-bulk-quote-base')}
                        <p class="text-[11px] text-lf-muted" data-testid="asset-bulk-quote_base_quantity-now">
                            {$t('assets.bulkEdit.now')}
                            {#each current.quote_base_quantity.shown as group (group.value)}
                                <span class="text-lf-secondary">{group.value} ×{group.count}</span>{' '}
                            {/each}
                            {@render moreCount(current.quote_base_quantity)}
                        </p>
                        <input
                            id="asset-bulk-quote-base"
                            type="text"
                            inputmode="numeric"
                            bind:value={quoteBaseInput}
                            placeholder={$t('assets.bulkEdit.leave')}
                            aria-invalid={quoteBaseError !== ''}
                            data-testid="asset-bulk-quote-base"
                            class="mt-1 w-full rounded-lg border bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-2 {quoteBaseError
                                ? 'border-lf-danger focus:ring-lf-danger/50'
                                : 'border-lf-input hover:border-lf-input-hover focus:border-lf-focus focus:ring-lf-focus/50'}"
                        />
                        {#if quoteBaseError}
                            <p class="mt-1 text-[11px] text-lf-danger" data-testid="asset-bulk-quote-base-error">{$t(quoteBaseError)}</p>
                        {/if}
                        {@render impactLine('quote_base_quantity')}
                    </div>
                    <div data-testid="asset-bulk-field-active" data-modified={isModified('active') ? 'true' : 'false'}>
                        {@render fieldHead('active', $t('common.active'), undefined, 'asset-bulk-active-label')}
                        {@render nowFlags('active', current.active)}
                        <div class="mt-1">{@render triState('active', 'asset-bulk-active-label', active, (next) => (active = next))}</div>
                        {@render impactLine('active')}
                    </div>
                    <div data-testid="asset-bulk-field-is_benchmark" data-modified={isModified('is_benchmark') ? 'true' : 'false'}>
                        {@render fieldHead('is_benchmark', $t('assets.modal.benchmark'), undefined, 'asset-bulk-benchmark-label')}
                        {@render nowFlags('is_benchmark', current.is_benchmark)}
                        <div class="mt-1">{@render triState('is_benchmark', 'asset-bulk-benchmark-label', benchmark, (next) => (benchmark = next))}</div>
                        {@render impactLine('is_benchmark')}
                    </div>
                </div>
            </section>
        </div>

        <!-- Footer -->
        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-lf-subtle px-6 py-4">
            <div class="flex items-center gap-2">
                <button
                    type="button"
                    class="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm text-lf-secondary transition-colors hover:bg-lf-hover disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!canContinue || verifyRun === 'running'}
                    title={$t('transactions.validate.now')}
                    data-testid="asset-bulk-verify"
                    onclick={handleVerify}
                >
                    {#if verifyRun === 'running'}
                        <Loader2 size={14} class="animate-spin" />
                    {:else}
                        ⚡
                    {/if}
                    <span>{$t('transactions.validate.now')}</span>
                </button>
                {#if verifyRun === 'running'}
                    <span class="text-[11px] text-lf-muted" data-testid="asset-bulk-verifying">{$t('transactions.validate.validating')}</span>
                {/if}
            </div>
            <div class="flex flex-wrap items-center justify-end gap-3">
                <button type="button" class="rounded-lg bg-lf-panel px-4 py-2 text-sm font-medium text-lf-secondary transition-colors hover:bg-lf-neutral" data-testid="asset-bulk-cancel" onclick={handleClose}>
                    {$t('common.cancel')}
                </button>
                <button type="button" class="rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action transition-colors hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50" disabled={!canContinue} data-testid="asset-bulk-continue" onclick={handleContinue}>
                    {$t('assets.bulkEdit.continue')}
                </button>
            </div>
        </div>
    </div>
</ModalBase>

<ImagePickerWrapper open={showImagePicker} preset="asset-icon" title={$t('uploads.selectIcon')} initialUrl={iconUrl} circularPreview={false} filterImages={true} onchange={handleIconChange} oncancel={() => (showImagePicker = false)} zIndex={zIndex + 20} />
