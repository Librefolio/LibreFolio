<!--
  AssetModalSelectionPrompts — the questions AssetModal asks after a search result is chosen: which code leads when the
  provider and the report disagree (with its discard confirmation), whether to replace the identifier of an asset being
  edited, and whether to reuse an existing asset with the same name. The modal owns the open flags and the answers.
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Info, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import IdentifierPrimaryChooser from './IdentifierPrimaryChooser.svelte';
    import type {IdentifierChoice} from './IdentifierPrimaryChooser.svelte';

    interface Props {
        zIndex: number;
        /** The asset being created or edited (for the chooser's text). */
        assetName: string;
        /** Provider vs report: which code leads. */
        choiceOpen: boolean;
        choiceType: string | null;
        choiceOptions: IdentifierChoice[];
        choicePrimary: string | null;
        choiceProvider: string | null;
        choiceDiscardOpen: boolean;
        onchoicerequestclose: () => void;
        onchoiceconfirm: () => void;
        onchoicediscard: () => void;
        /** Edit mode: replace the identifier with the chosen result's one. */
        identifierChangeOpen: boolean;
        onidentifierchangeconfirm: () => void;
        onidentifierchangecancel: () => void;
        /** Wizard create: an existing asset has the result's name. */
        reuseOpen: boolean;
        reuseAllowKeyMerge: boolean;
        reuseExistingName: string;
        onreuse: (addKeys: boolean) => void;
        onreusedismiss: () => void;
    }

    let {
        zIndex,
        assetName,
        choiceOpen,
        choiceType,
        choiceOptions,
        choicePrimary = $bindable(),
        choiceProvider,
        choiceDiscardOpen = $bindable(),
        onchoicerequestclose,
        onchoiceconfirm,
        onchoicediscard,
        identifierChangeOpen,
        onidentifierchangeconfirm,
        onidentifierchangecancel,
        reuseOpen,
        reuseAllowKeyMerge,
        reuseExistingName,
        onreuse,
        onreusedismiss,
    }: Props = $props();
</script>

<!--
  Provider vs report: which code leads.

  Raised when a provider search returns an identifier of a type the form already holds with a
  different value. Both are shown with their provenance; the loser becomes an alternate, so
  nothing is destroyed — which is what keeps a dual-ISIN bond resolvable from either code.
-->
{#if choiceOpen}
    <ModalBase open={true} maxWidth="lg" onRequestClose={onchoicerequestclose} zIndex={zIndex + 20}>
        <div class="p-5 space-y-4" data-testid="asset-modal-identifier-primary">
            <IdentifierPrimaryChooser choices={choiceOptions} {assetName} typeLabel={choiceType ?? undefined} isIsin={choiceType === 'ISIN'} providerName={choiceProvider ?? undefined} bind:primary={choicePrimary} testid="asset-modal-primary-chooser" />
            <div class="flex justify-end gap-2 pt-1">
                <button type="button" class="rounded border border-lf-subtle px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" onclick={onchoicerequestclose} data-testid="asset-modal-primary-cancel">
                    {$t('assets.identifiers.primaryChooser.cancel')}
                </button>
                <button type="button" class="rounded bg-lf-action px-3 py-1.5 text-sm font-medium text-lf-on-action hover:opacity-90" onclick={onchoiceconfirm} data-testid="asset-modal-primary-confirm">
                    {$t('assets.identifiers.primaryChooser.confirm')}
                </button>
            </div>
        </div>
    </ModalBase>
{/if}

<ConfirmModal
    open={choiceDiscardOpen}
    title={$t('assets.identifiers.primaryChooser.discardTitle')}
    message={$t('assets.identifiers.primaryChooser.discardMessage')}
    confirmText={$t('assets.identifiers.primaryChooser.discardConfirm')}
    warning={true}
    onConfirm={onchoicediscard}
    onCancel={() => (choiceDiscardOpen = false)}
    zIndex={zIndex + 40}
/>

<!-- Confirmation: Identifier change in edit mode -->
<ConfirmModal
    open={identifierChangeOpen}
    title={$t('assets.confirm.identifierChanged')}
    message={$t('assets.confirm.identifierChangedMessage')}
    confirmText={$t('assets.confirm.confirmChange')}
    warning={true}
    onConfirm={onidentifierchangeconfirm}
    onCancel={onidentifierchangecancel}
    zIndex={zIndex + 20}
/>

<!-- Reuse existing asset (wizard create): a search result's provider name matches an existing asset -->
{#if reuseOpen}
    <ModalBase maxWidth="max-w-md" onRequestClose={onreusedismiss} open={reuseOpen} zIndex={zIndex + 20}>
        <div class="flex items-center gap-3 px-5 py-4 border-b border-lf-subtle">
            <Info class="text-lf-warning shrink-0" size={22} />
            <h2 class="flex-1 text-lg font-semibold text-lf-primary" data-testid="reuse-existing-title">
                {$t('assets.modal.reuseExisting.title')}
            </h2>
            <button type="button" aria-label={$t('common.close')} class="text-lf-muted hover:text-lf-secondary transition-colors" onclick={onreusedismiss}>
                <X size={20} />
            </button>
        </div>
        <div class="px-5 py-4 text-sm text-lf-secondary" data-testid="reuse-existing-message">
            <!-- Without the key merge there is no identifier to speak of: mentioning one
                 would send the user looking for a choice this dialog does not offer. -->
            {#if reuseAllowKeyMerge}
                {$t('assets.modal.reuseExisting.message', {values: {name: reuseExistingName}})}
            {:else}
                {$t('assets.modal.reuseExisting.messagePlain', {values: {name: reuseExistingName}})}
            {/if}
        </div>
        <div class="flex flex-col gap-2 px-5 py-4 border-t border-lf-subtle">
            {#if reuseAllowKeyMerge}
                <button type="button" data-testid="reuse-existing-add" class="w-full px-4 py-2 text-sm font-medium text-lf-on-action bg-lf-action rounded-lg hover:bg-lf-action-hover transition-colors" onclick={() => onreuse(true)}>
                    {$t('assets.modal.reuseExisting.useAndAdd')}
                </button>
            {/if}
            <button
                type="button"
                data-testid="reuse-existing-use"
                class="w-full px-4 py-2 text-sm font-medium transition-colors {reuseAllowKeyMerge ? 'rounded-lg border border-lf-subtle bg-lf-card text-lf-secondary hover:bg-lf-hover' : 'rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover'}"
                onclick={() => onreuse(false)}
            >
                {#if reuseAllowKeyMerge}
                    {$t('assets.modal.reuseExisting.useOnly')}
                {:else}
                    {$t('assets.modal.reuseExisting.use')}
                {/if}
            </button>
            <button type="button" data-testid="reuse-existing-cancel" class="w-full px-4 py-2 text-sm font-medium text-lf-muted hover:text-lf-secondary transition-colors" onclick={onreusedismiss}>
                {$t('assets.modal.reuseExisting.changeName')}
            </button>
        </div>
    </ModalBase>
{/if}
