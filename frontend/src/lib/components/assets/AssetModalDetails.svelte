<!--
  AssetModalDetails — the identity of the asset in AssetModal: icon, name, type, quote base quantity, currency, the
  user's URL and the short description. The fields are bound to the modal's state; edits are reported back so the
  modal can track what the user changed by hand.
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ExternalLink, Info, Loader2, RefreshCw, Upload} from 'lucide-svelte';
    import {AssetTypeSelect, CurrencySearchSelect} from '$lib/components/ui/select';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import AssetIcon from './AssetIcon.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {numericArrows} from '$lib/actions/numericArrows';

    interface Props {
        displayName: string;
        assetType: string;
        quoteBaseQuantity: number;
        /** Set once the user edits the quote base by hand, so the bond default never overrides it. */
        quoteBaseQuantityTouched: boolean;
        providerUserUrl: string;
        shortDescription: string;
        currency: string;
        iconUrl: string | null;
        hasProvider: boolean;
        askingProvider: boolean;
        duplicateAssetName: string | null;
        quoteBaseQuantityInvalid: boolean;
        /** i18n key of the quote base error. */
        quoteBaseQuantityError: string;
        /** A field the user edited by hand (`display_name`, `asset_type`). */
        onmanualedit: (field: string) => void;
        onaskprovider: () => void;
        onpickicon: () => void;
        oncurrencychange: (currency: string) => void;
        ondescriptionedit: () => void;
    }

    let {
        displayName = $bindable(),
        assetType = $bindable(),
        quoteBaseQuantity = $bindable(),
        quoteBaseQuantityTouched = $bindable(),
        providerUserUrl = $bindable(),
        shortDescription = $bindable(),
        currency,
        iconUrl,
        hasProvider,
        askingProvider,
        duplicateAssetName,
        quoteBaseQuantityInvalid,
        quoteBaseQuantityError,
        onmanualedit,
        onaskprovider,
        onpickicon,
        oncurrencychange,
        ondescriptionedit,
    }: Props = $props();

    /** Drops the decimals the user typed, once they have moved on. */
    function truncateQuoteBaseQuantity() {
        if (!Number.isFinite(quoteBaseQuantity)) return;
        const truncated = Math.trunc(quoteBaseQuantity);
        if (truncated !== quoteBaseQuantity) quoteBaseQuantity = truncated;
    }
</script>

<!-- Asset Details -->
<div class="space-y-3" use:guideAnchor={'asset.identity'} data-testid="asset-tour-identity">
    <div class="flex items-center justify-between">
        <div class="text-xs font-semibold text-lf-muted uppercase tracking-wider">
            {$t('assets.modal.assetDetails')}
        </div>
        <!-- Ask Provider global button -->
        <button
            type="button"
            onclick={onaskprovider}
            disabled={!hasProvider || askingProvider}
            data-testid="asset-modal-ask-provider"
            class="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md
                   bg-lf-card border border-lf-subtle
                   text-lf-secondary hover:bg-lf-hover
                   disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            title={!hasProvider ? $t('assets.identifiers.askProviderHint') : ''}
        >
            {#if askingProvider}
                <Loader2 size={12} class="animate-spin" />
            {:else}
                <RefreshCw size={12} />
            {/if}
            <span class="hidden sm:inline">{$t('assets.identifiers.askProvider')}</span>
        </button>
    </div>

    <!-- Grid: Icon on left, form fields on right -->
    <div class="grid grid-cols-[auto_1fr] gap-4 items-center">
        <!-- Left: Icon (clickable) -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="group relative cursor-pointer" onclick={onpickicon} title={$t('uploads.selectIcon')}>
            <AssetIcon {iconUrl} {assetType} size="lg" />
            <div
                class="absolute inset-0 rounded-full bg-lf-overlay opacity-0 group-hover:opacity-100
                    flex items-center justify-center transition-opacity"
            >
                <Upload class="text-lf-on-overlay" size={16} />
            </div>
        </div>

        <!-- Right: Name+URL row, Type+Currency row (2×2 on desktop, column on mobile) -->
        <div class="space-y-3">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <!-- Display Name -->
                <div>
                    <label for="asset-display-name" class="block text-xs font-medium text-lf-muted mb-1">
                        {$t('common.name')} *
                    </label>
                    <input
                        id="asset-display-name"
                        type="text"
                        bind:value={displayName}
                        oninput={() => onmanualedit('display_name')}
                        placeholder="Apple Inc."
                        data-testid="asset-modal-display-name"
                        aria-invalid={!displayName.trim()}
                        aria-describedby={!displayName.trim() ? 'asset-name-required' : undefined}
                        class="w-full px-3 py-2 text-sm border border-lf-input hover:border-lf-input-hover rounded-lg
                               bg-lf-field text-lf-primary
                               placeholder:text-lf-placeholder
                               focus:outline-none focus:ring-2 focus:ring-lf-focus/50 focus:border-lf-focus"
                    />
                    {#if !displayName.trim()}
                        <p id="asset-name-required" class="mt-1 text-xs text-lf-warning" data-testid="asset-modal-name-required">
                            {$t('assets.modal.nameRequired')}
                        </p>
                    {/if}
                    {#if duplicateAssetName}
                        <Tooltip text={$t('assets.modal.duplicateNameTooltip', {values: {name: duplicateAssetName}})} position="bottom" maxWidth="300px">
                            <span data-testid="asset-modal-duplicate-warning" data-duplicate-name={duplicateAssetName} class="inline-flex items-center gap-1 mt-1 text-xs text-lf-warning">
                                ⚠️ {$t('assets.modal.duplicateNameWarning', {values: {name: duplicateAssetName}})}
                            </span>
                        </Tooltip>
                    {/if}
                </div>

                <!-- Asset Type -->
                <div>
                    <span class="block text-xs font-medium text-lf-muted mb-1">
                        {$t('common.type')} *
                    </span>
                    <AssetTypeSelect bind:value={assetType} testId="asset-modal-type" onchange={() => onmanualedit('asset_type')} />
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <!-- Quote Base Quantity -->
                <div>
                    <div class="flex items-center gap-1 mb-1">
                        <label for="asset-quote-base-quantity" class="block text-xs font-medium text-lf-muted">
                            {$t('assets.modal.quoteBaseQuantity')} *
                        </label>
                        <Tooltip text={$t('assets.modal.quoteBaseTooltip')} position="bottom" maxWidth="280px">
                            <Info size={14} class="text-lf-muted cursor-help" />
                        </Tooltip>
                    </div>
                    <input
                        id="asset-quote-base-quantity"
                        type="number"
                        use:numericArrows
                        min="1"
                        step="1"
                        bind:value={quoteBaseQuantity}
                        oninput={() => (quoteBaseQuantityTouched = true)}
                        onblur={truncateQuoteBaseQuantity}
                        data-testid="asset-modal-quote-base-quantity"
                        class="w-full px-3 py-2 text-sm border rounded-lg
                               bg-lf-field text-lf-primary
                               focus:outline-none focus:ring-2 {quoteBaseQuantityInvalid ? 'border-lf-danger focus:ring-lf-danger/50' : 'border-lf-input hover:border-lf-input-hover focus:ring-lf-focus/50 focus:border-lf-focus'}"
                    />
                    {#if quoteBaseQuantityInvalid}
                        <p class="mt-1 text-[11px] text-lf-danger" data-testid="asset-modal-quote-base-quantity-error">{$t(quoteBaseQuantityError)}</p>
                    {/if}
                    {#if assetType === 'BOND'}
                        <p class="mt-1 flex items-start gap-1 text-[11px] text-lf-info" data-testid="asset-modal-bond-qbq-hint">
                            <Info size={12} class="mt-0.5 shrink-0" />
                            <span>{$t('assets.modal.bondQuoteBaseHint')}</span>
                        </p>
                    {/if}
                </div>

                <!-- Currency -->
                <div data-testid="asset-modal-currency-group">
                    <div class="flex items-center gap-1 mb-1">
                        <span class="text-xs font-medium text-lf-muted">{$t('common.currency')} *</span>
                        <Tooltip text={$t('assets.modal.currencyHelp')} interactiveChild maxWidth="360px">
                            <button type="button" class="text-lf-muted hover:text-lf-info" aria-label={$t('assets.modal.currencyHelpLabel')} data-testid="asset-modal-currency-help">
                                <Info size={13} />
                            </button>
                        </Tooltip>
                    </div>
                    <CurrencySearchSelect
                        value={currency}
                        onchange={(v) => {
                            if (v) oncurrencychange(v);
                        }}
                        maxVisibleItems={6}
                        compact={true}
                    />
                </div>
            </div>
        </div>
    </div>
</div>

<!-- User URL -->
<div>
    <label for="asset-user-url" class="block text-xs font-medium text-lf-muted mb-1">
        {$t('assets.provider.userUrl')}
    </label>
    <div class="flex gap-1.5">
        <input
            id="asset-user-url"
            type="text"
            bind:value={providerUserUrl}
            placeholder="https://..."
            class="flex-1 px-3 py-2 text-sm border border-lf-input hover:border-lf-input-hover rounded-lg
                   bg-lf-field text-lf-primary
                   placeholder:text-lf-placeholder
                   focus:outline-none focus:ring-2 focus:ring-lf-focus/50 focus:border-lf-focus"
        />
        {#if providerUserUrl}
            <a href={providerUserUrl} target="_blank" rel="noopener noreferrer" class="shrink-0 flex items-center px-2 py-2 text-lf-muted hover:text-lf-link transition-colors">
                <ExternalLink size={14} />
            </a>
        {/if}
    </div>
</div>

<!-- Description (short, always visible) -->
<div>
    <label for="asset-description" class="block text-xs font-medium text-lf-muted mb-1">
        {$t('common.description')}
    </label>
    <textarea
        id="asset-description"
        data-testid="asset-modal-description"
        bind:value={shortDescription}
        oninput={ondescriptionedit}
        rows={2}
        placeholder={$t('assets.modal.descriptionPlaceholder')}
        class="w-full px-3 py-2 text-sm border border-lf-input hover:border-lf-input-hover rounded-lg
               bg-lf-field text-lf-primary
               placeholder:text-lf-placeholder
               focus:outline-none focus:ring-2 focus:ring-lf-focus/50 focus:border-lf-focus resize-none"
    ></textarea>
</div>
