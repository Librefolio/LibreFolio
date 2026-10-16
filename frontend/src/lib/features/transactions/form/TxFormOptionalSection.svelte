<!--
  TxFormOptionalSection — the optional fields: linked asset event, tags, description, link id and pair partner.

  Cut from TransactionFormModal.svelte (FE8a): the modal owns the state and the handlers; this
  section reads them as props, writes the bound ones back, and calls the handlers.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import TagInput from '$lib/components/ui/input/TagInput.svelte';
    import AssetEventPicker from '../events/AssetEventPicker.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import type {FormDraft} from './txFormTypes';

    interface Props {
        availableTags: string[];
        createEventOpen: boolean;
        draft: FormDraft;
        optionalOpen: boolean;
        canShowAssetEvent: boolean;
        isReadonly: boolean;
        pairPartnerId: number | null;
        onDescriptionInput: (e: Event) => void;
    }

    let {availableTags, createEventOpen = $bindable(), draft = $bindable(), optionalOpen = $bindable(), canShowAssetEvent, isReadonly, pairPartnerId, onDescriptionInput}: Props = $props();
</script>

<details class="border border-lf-subtle rounded-lg" bind:open={optionalOpen}>
    <summary class="text-xs font-semibold uppercase tracking-wide text-lf-muted px-4 py-3 cursor-pointer select-none" data-testid="tx-form-optional-toggle" use:guideAnchor={'transaction.create.details'}>{$t('transactions.form.sectionOptional')}</summary>
    <div class="px-4 pb-4 space-y-3 text-sm">
        <!-- 1. Asset event link (before tags) -->
        {#if canShowAssetEvent}
            <AssetEventPicker
                assetId={draft.asset_id!}
                txDate={draft.date}
                value={draft.asset_event_id}
                disabled={isReadonly}
                txCash={draft.cash}
                onChange={(id) => {
                    draft = {...draft, asset_event_id: id};
                }}
                onCreateNew={isReadonly ? undefined : () => (createEventOpen = true)}
            />
        {/if}

        <!-- 2. Tags -->
        <div class="flex flex-col gap-1">
            <span class="text-xs text-lf-muted">{$t('common.tags')}</span>
            <TagInput
                value={draft.tags}
                {availableTags}
                placeholder={$t('transactions.form.tagsPlaceholder')}
                disabled={isReadonly}
                onchange={(v) => {
                    draft = {...draft, tags: v};
                }}
            />
        </div>

        <!-- 3. Description -->
        <label class="flex flex-col gap-1">
            <span class="text-xs text-lf-muted">{$t('common.description')}</span>
            <textarea
                autocomplete="off"
                class="px-3 py-2 bg-lf-field text-lf-primary border border-lf-input hover:border-lf-input-hover rounded-lg resize-y min-h-[60px] disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-lf-focus/30"
                rows="2"
                bind:value={draft.description}
                disabled={isReadonly}
                oninput={onDescriptionInput}
                data-testid="tx-form-description"
                maxlength="500"
            ></textarea>
        </label>

        <!-- 4. link_uuid (readonly) -->
        {#if draft.link_uuid}
            <div class="flex items-center gap-2">
                <span class="text-xs text-lf-muted w-32 shrink-0">{$t('transactions.form.linkUuid')}</span>
                <code class="text-[10px] font-mono text-lf-muted truncate" data-testid="tx-form-link-uuid">{draft.link_uuid}</code>
            </div>
        {/if}

        <!-- 5. Pair partner chip -->
        {#if pairPartnerId}
            <div class="flex items-center gap-2">
                <span class="text-xs text-lf-muted w-32 shrink-0">{$t('transactions.form.pairPartner')}</span>
                <button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/50" data-testid="tx-form-pair-partner">
                    #{pairPartnerId}
                </button>
            </div>
        {/if}
    </div>
</details>
