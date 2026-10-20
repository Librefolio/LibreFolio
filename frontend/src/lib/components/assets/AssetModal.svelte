<!--
  AssetModal — Create/Edit asset modal.

  Features:
  - Create mode: search + auto-fill + auto-test
  - Edit mode: pre-populated form
  - Identifiers section (collapsible) with Ask Provider
  - Provider Assignment section (collapsible) with test
  - Confirmation modals (save without test, change identifier)
  - ModalBase with allowOverflow
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {onDestroy, untrack} from 'svelte';
    import {zodiosApi} from '$lib/api';
    import {debug} from '$lib/debug';
    import {ChevronDown, ChevronRight, Search, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import AssetSearchAutocomplete from './AssetSearchAutocomplete.svelte';
    import AssetModalDetails from './AssetModalDetails.svelte';
    import AssetModalFooter from './AssetModalFooter.svelte';
    import AssetModalImportNotices from './AssetModalImportNotices.svelte';
    import AssetModalIdentifiers from './AssetModalIdentifiers.svelte';
    import AssetModalProvider from './AssetModalProvider.svelte';
    import AssetModalSelectionPrompts from './AssetModalSelectionPrompts.svelte';
    import ProviderAssignmentSection from './ProviderAssignmentSection.svelte';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import ProviderComparisonModal from './ProviderComparisonModal.svelte';
    import type {DiffItem} from './ProviderComparisonModal.svelte';
    import type {IdentifierChoice} from './IdentifierPrimaryChooser.svelte';
    import AssetCurrencyChangeModal from './AssetCurrencyChangeModal.svelte';
    import DistributionEditor from '$lib/components/ui/input/DistributionEditor.svelte';
    import {getIndexColor} from '$lib/utils/colors';
    import ImagePickerWrapper from '$lib/components/ui/media/ImagePickerWrapper.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {probeRateLimitMessage} from './resolveProviderError';
    import {userSettings} from '$lib/stores/app/settings';
    import {get} from 'svelte/store';
    import {trySave} from '$lib/utils/trySave';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {wipeRefusalMessage} from './currencyChangeErrors';
    import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
    import {columnsToIdentifierRows, fieldToIdType, identifierValue, withIdentifier, mergeOtherIdentifierValues, withElectedPrimary} from './assetIdentifiers';
    import {searchResultAssetType, searchResultIdentifier, searchResultProviderParams} from './assetSearchSelection';
    import {compareMetadata, type ComparisonAction, type ComparisonSnapshot} from './assetMetadataComparison';
    import {isCurrencyChangeBlockedMessage, parseCurrencyChangeBlocker} from './currencyBlocker';
    import {buildClassificationParams, buildCreateItem, buildPatchItem, buildProviderAssignItem, type AssetFormFields, type ClassificationParams, type ProviderAssignment} from './assetPayload';
    import {isQuoteBaseQuantityInvalid, quoteBaseQuantityErrorKey, defaultQuoteBaseQuantity, proposeQuoteBase, quoteBaseNote, computeHasProvider, computeProviderDirty, groupImportNotices, type QuoteBaseSource, type QuoteBaseSuggestion} from './assetFormState';
    import {ensureAssetProvidersCached, getAssetProviderName, isParametricProvider} from '$lib/utils/providerHelpers';
    import type {AssetCreateSyncResult} from '$lib/utils/sync/syncHelpers';
    import {mergeAssets, invalidateAfterMutation} from '$lib/stores/reference/assetStore';
    import {entityDetailLinkHtml} from '$lib/utils/core/entityLink';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {createProviderProbeState, providerConfigurationKey, type ProviderConfiguration, type ProviderRequestTicket} from './providerProbeState.svelte';
    import {decideComparison, identifierQuestion, type IdentifierQuestion} from './providerComparisonQueue';

    // =========================================================================
    // Types
    // =========================================================================

    interface AssetData {
        id?: number;
        display_name: string;
        currency: string;
        asset_type: string;
        icon_url?: string | null;
        quote_base_quantity?: number | null;
        active?: boolean;
        is_benchmark?: boolean;
        classification_params?: {
            short_description?: string | null;
            sector_area?: {distribution: Record<string, number>} | null;
            geographic_area?: {distribution: Record<string, number>} | null;
        } | null;
        // Identifiers
        identifier_isin?: string | null;
        identifier_ticker?: string | null;
        identifier_cusip?: string | null;
        identifier_sedol?: string | null;
        identifier_figi?: string | null;
        identifier_uuid?: string | null;
        identifier_other?: string | string[] | null;
        // Provider
        provider_code?: string | null;
        provider_identifier?: string;
        provider_identifier_type?: string;
        provider_params?: Record<string, any> | null;
        provider_user_url?: string;
        provider_url?: string | null;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open?: boolean;
        editMode?: boolean;
        editData?: AssetData | null;
        /**
         * Pre-fill data for create mode. When provided (and editMode=false),
         * the form opens with these fields populated instead of all-blank.
         * Useful for the BRIM import wizard: prefill identifier_ticker, identifier_isin, display_name.
         */
        prefillData?: Partial<AssetData> | null;
        /** Z-index override for stacked modal contexts. */
        zIndex?: number;
        /** Tour-only preview: no create/update action can be submitted. */
        tourPreview?: boolean;
        /**
         * Pre-fill the "Search Online" input with this query when the modal opens in create mode.
         * Useful for the BRIM import wizard: pass the extracted symbol/ISIN/name so the user
         * can immediately see provider search results without typing.
         */
        initialSearchQuery?: string;
        /**
         * Clickable badge suggestions shown above the search input (create mode only).
         * Each badge has a display label and a click value (e.g. label="Ticker: TSLA", value="TSLA").
         * Replaces concatenated initialSearchQuery for BRIM wizard.
         */
        initialSearchBadges?: Array<{label: string; value: string}>;
        /**
         * Extra search terms (ISIN + all candidate names extracted from the report),
         * forwarded to the provider search as `hints`. Used only by the link-finder
         * fallback to build a specific query when a provider's on-site search finds
         * nothing (e.g. a fund whose bare ISIN surfaces several sibling share classes).
         */
        searchHints?: string[];
        /**
         * When true, open the provider section with "No provider" pre-selected.
         * Used by the BRIM import wizard: assets created manually don't come
         * from an online search, so the UI should default to no-provider mode.
         */
        initialNoProvider?: boolean;
        /**
         * Wizard create context only: called when the user, after selecting a search result
         * whose provider name matches an existing asset, chooses to reuse that asset instead
         * of creating a duplicate. `addKeys` = also merge the import's search keys into the
         * existing asset's identifier_other. When undefined, the reuse prompt is disabled.
         */
        onReuseExisting?: (existingAssetId: number, addKeys: boolean) => void;
        /**
         * Whether reusing an existing asset may also merge the import's search keys into
         * its identifiers. False when the caller has no identifier to offer — the plugin
         * could not read one — so the prompt drops that option instead of proposing to
         * add nothing.
         */
        reuseAllowKeyMerge?: boolean;
        /**
         * Wizard create context only: advisory notices raised by the broker-import plugin for
         * this asset (e.g. a suspected maturity/redemption implying the security is delisted and
         * won't be found by the online search). Rendered as amber banners grouped by `kind`;
         * purely informational — never changes behaviour (the user decides via the active toggle).
         */
        importNotices?: Array<{kind: string; reason: string}>;
        /** Asset-global only; contextual creation keeps its existing plain success toast. */
        linkCreatedAsset?: boolean;
        /** The asset exists. `detail.syncing`: its one price sync started, and `onsynced` will tell how it ended. */
        oncreated?: (assetId: number, detail?: {syncing: boolean}) => void;
        /** The one price sync after a creation ended (O-20): its result for the asset, or null when the request failed.
         * Never called when no sync starts (no provider, or its assignment failed). */
        onsynced?: (assetId: number, result: AssetCreateSyncResult | null) => void;
        onupdated?: () => void;
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        editMode = false,
        editData = null,
        prefillData = null,
        zIndex = 50,
        tourPreview = false,
        initialSearchQuery = '',
        initialSearchBadges = [],
        searchHints = [],
        initialNoProvider = false,
        onReuseExisting,
        reuseAllowKeyMerge = true,
        importNotices = [],
        linkCreatedAsset = false,
        oncreated,
        onsynced,
        onupdated,
        onclose,
    }: Props = $props();

    // =========================================================================
    // Constants
    // =========================================================================

    // Asset types and icon mapping are imported from $lib/utils/assetTypes

    // =========================================================================
    // State — Form fields
    // =========================================================================

    let displayName = $state('');
    let currency = $state('USD');
    let assetType = $state('STOCK');
    let iconUrl: string | null = $state(null);
    let quoteBaseQuantity = $state(1);
    // Z-32 (d): the provider's suggestion behind the current quote base, shown under the field while it holds for the
    // provider line it came from (`key`, that line's `providerConfigKey`); null for a typed value or a type default.
    interface QuoteBaseHint {
        key: string;
        provider: string;
        quoteCurrency: string | null;
        quantity: number;
    }
    let quoteBaseHint = $state<QuoteBaseHint | null>(null);
    // R1: the latest explicit suggestion the provider gave for a line (search or probe), for a later probe whose own
    // suggestion failed (a timeout, a pause): it never proposes to undo it.
    let lineQuoteBaseSuggestion: {key: string; suggestion: QuoteBaseSuggestion} | null = null;
    let active = $state(true);
    let isBenchmark = $state(false);

    // Identifiers — dynamic rows instead of fixed fields
    interface IdentifierRow {
        id: string;
        type: string;
        value: string;
        autoFilled?: boolean;
    }
    let identifierRows: IdentifierRow[] = $state([]);
    /** Codes that arrived from `prefillData` (i.e. from the imported reports), upper-cased. */
    let prefilledIdentifiers = $state<Set<string>>(new Set());

    // Classification
    let shortDescription = $state('');
    // True while shortDescription holds a BRIM-import prefill (identified-names block) that
    // was auto-populated, not typed by the user. Lets provider enrichment merge over it
    // instead of routing to the diff modal. Cleared on manual edit or provider autofill.
    let descriptionFromPrefill = $state(false);
    let sectorDistribution: Record<string, number> = $state({});
    let geographicDistribution: Record<string, number> = $state({});

    // Provider
    let providerCode = $state('');
    let providerIdentifier = $state('');
    let providerIdentifierType = $state('TICKER');
    let providerParams: Record<string, any> | null = $state(null);
    let providerUserUrl = $state('');
    let providerNoProvider = $state(false);
    const providerProbe = createProviderProbeState(providerConfiguration);
    let providerUrl = $derived(providerProbe.url);
    let providerTestStatus = $derived(providerProbe.status);
    let providerConfigKey = $derived(providerConfigurationKey(providerConfiguration()));
    let visibleQuoteBaseHint = $derived(quoteBaseHint && quoteBaseHint.key === providerConfigKey ? {provider: quoteBaseHint.provider, currency: quoteBaseHint.quoteCurrency, quantity: quoteBaseHint.quantity} : null);

    function providerConfiguration(): ProviderConfiguration {
        return {providerCode, identifier: providerIdentifier, identifierType: providerIdentifierType, providerParams, noProvider: providerNoProvider};
    }

    onDestroy(() => providerProbe.dispose());

    // UI state
    let moreInfoExpanded = $state(false);
    let providerExpanded = $state(false);
    let saving = $state(false);
    let formError: string | null = $state(null);
    let askingProvider = $derived(providerProbe.metadataPending);
    let autoFilledFields: Set<string> = $state(new Set());
    let conflictFields: Map<string, string> = $state(new Map());

    // Confirmation modals
    let showSaveWithoutTestConfirm = $state(false);
    let saveConfirmContext: ProviderRequestTicket | null = null;
    let showIdentifierChangeConfirm = $state(false);
    let showDiscardConfirm = $state(false);

    // Badge-driven search query — updated by clicking initialSearchBadges chips.
    // Using a separate state allows {#key} remount of AssetSearchAutocomplete.
    let activeSearchQuery = $state(untrack(() => initialSearchQuery));

    // #R3-4 — scheduled_investment regenerate confirm. Shown when the user edits an
    // existing scheduled_investment asset and changes its provider_params (schedule /
    // maturation_frequency / …). Confirming wipes the old prices server-side and
    // triggers an immediate re-sync so the chart reflects the new schedule.
    let showScheduledRegenConfirm = $state(false);
    let pendingSaveAssetId: number | null = $state(null);
    let initialProviderParamsJson: string = $state('');

    // Leaving a parametric provider (scheduled_investment → Yahoo, …) wipes the
    // generated series server-side, for the same reason a params change does: the
    // prices were *invented* from the params, so under a market provider they are
    // not history. Unlike the params change the user has no reason to expect it,
    // so the warning states the actual counts before anything is destroyed.
    let showParametricSwitchConfirm = $state(false);
    let parametricSwitchInfo = $state<{prices: number; events: number; from: string; to: string} | null>(null);

    // I-bis #2 — snapshot of the provider config as loaded from the DB.
    // Used by the ``providerDirty`` derived below to gate the
    // "Save Without Testing?" modal: it must fire **only** when one of
    // these four fields changed vs what was loaded. Non-provider edits
    // (name, description, classification, etc.) skip the modal entirely.
    let initialProviderCode: string = $state('');
    let initialProviderIdentifier: string = $state('');
    let initialProviderIdentifierType: string = $state('TICKER');

    // I.6 — destructive currency-change modal state.
    let currencyChangeModalOpen = $state(false);
    let currencyChangeBlocker = $state<{
        assetId: number;
        prices: number;
        eventsManual: number;
        eventsProvider: number;
        linkedTx: number;
        oldest: string;
        newest: string;
        from: string;
        to: string;
    } | null>(null);
    let currencyChangePatchPayload: Record<string, unknown> | null = $state(null);
    let currencyChangeProviderAssigned = $state(false);
    let pendingSearchResult: any = $state(null);

    // ── Provider vs report: which code leads ────────────────────────────────────────────
    // A provider search is a *source of information*, not an authority. When it returns an
    // identifier of a type the form already holds with a different value, overwriting it
    // silently destroys a code the user got from a document he owns — which is exactly how
    // the CUM ISIN of an Italian retail BTP used to disappear. So the two values are put
    // side by side, with their provenance, and the user says which one leads.
    let identifierChoiceOpen = $state(false);
    let identifierChoiceType = $state<string | null>(null);
    let identifierChoiceOptions = $state<IdentifierChoice[]>([]);
    let identifierChoicePrimary = $state<string | null>(null);
    let identifierChoiceProvider = $state<string | null>(null);
    let identifierChoiceDiscardOpen = $state(false);

    // Provider comparison modal
    let showComparisonModal = $state(false);
    let comparisonDifferences: DiffItem[] = $state([]);
    let comparisonContext: ProviderRequestTicket | null = null;
    let comparisonIntent = new Map<string, number>();

    // ── A search selection asks each identifier question once (R18) ─────────────────────
    // Picking a search result can open the primary-identifier chooser at once *and* start the
    // metadata read whose comparison asks the same ISIN again. That comparison waits while any
    // prompt of the selection is open, and loses the rows the chooser already put to the user —
    // whether the answer came before or after the read. `providerComparisonQueue.ts` decides.
    let selectionQuestions: IdentifierQuestion[] = [];
    let heldComparison: {differences: DiffItem[]; context: ProviderRequestTicket; intent: Map<string, number>} | null = null;
    const manualFieldRevisions = new Map<string, number>();

    function markManualField(field: string) {
        manualFieldRevisions.set(field, (manualFieldRevisions.get(field) ?? 0) + 1);
        if (field === 'quote_base_quantity') quoteBaseHint = null;
    }

    function resetDraftReads(seedUrl: string | null = null) {
        providerProbe.reset(seedUrl);
        manualFieldRevisions.clear();
        lineQuoteBaseSuggestion = null;
        comparisonContext = null;
        comparisonIntent.clear();
        showComparisonModal = false;
        comparisonDifferences = [];
        heldComparison = null;
        selectionQuestions = [];
        showSaveWithoutTestConfirm = false;
        saveConfirmContext = null;
        reuseModalOpen = false;
        reuseExistingId = null;
    }

    function reconcileProviderContext() {
        if (providerProbe.configure()) autoFilledFields = new Set();
        if (comparisonContext && !providerProbe.isMetadataCurrent(comparisonContext)) {
            showComparisonModal = false;
            comparisonDifferences = [];
            comparisonContext = null;
        }
        if (heldComparison && !providerProbe.isMetadataCurrent(heldComparison.context)) heldComparison = null;
        if (saveConfirmContext && !providerProbe.isContextCurrent(saveConfirmContext)) {
            showSaveWithoutTestConfirm = false;
            saveConfirmContext = null;
        }
    }

    $effect(() => {
        void providerConfigKey;
        untrack(reconcileProviderContext);
    });

    // Image picker
    let showImagePicker = $state(false);

    // Identifier selection + bulk delete
    let identifierSelectedIds: string[] = $state([]);
    let showIdentifierDeleteConfirm = $state(false);
    let pendingIdentifierDeleteIds: string[] = $state([]);

    // Track if search result was selected (for auto-assign banner)
    let searchResultSelected = $state(false);
    /** True once the user explicitly picks a currency in the form (manual intent). */
    let currencyUserSet = $state(false);
    /** The currency and the type a blank create form starts with (resetForm): the report of a search names them only
     * once they say something about the asset (P20). */
    let blankCurrency = $state('');
    let blankAssetType = $state('');
    /** What the form holds, for the report of a search that found nothing useful (P20): its identifiers, and the
     * currency and the type once they say something about the asset — an edit, an import's prefill, the user's choice,
     * or not the blank form's default. No other data leaves. */
    let searchReportContext = $derived({
        currency: editMode || !!prefillData?.currency || currencyUserSet || currency !== blankCurrency ? currency : null,
        assetType: editMode || !!prefillData?.asset_type || assetType !== blankAssetType ? assetType : null,
        identifiers: identifierRows.filter((row) => row.value.trim() !== '').map((row) => ({type: row.type, value: row.value})),
    });

    // Dirty tracking — snapshot of initial form to detect unsaved changes
    let initialSnapshot = $state('');
    let initialClassification: ClassificationParams | undefined;

    // Duplicate name detection
    let duplicateAssetName: string | null = $state(null);

    // Reuse-existing prompt (wizard create context only): shown after a search selection
    // whose provider name matches an existing asset — offers to reuse it instead of creating a dup.
    let reuseModalOpen = $state(false);
    let reuseExistingId: number | null = $state(null);
    let reuseExistingName = $state('');

    /** A prompt of the current search selection is on screen: its comparison has to wait (R18). */
    let selectionPromptOpen = $derived(identifierChoiceOpen || identifierChoiceDiscardOpen || reuseModalOpen);

    // The last prompt of the selection just closed — confirmed, discarded or dismissed: a held
    // comparison may now open, with what is left once the answered rows are gone.
    $effect(() => {
        if (selectionPromptOpen) return;
        untrack(releaseHeldComparison);
    });

    // =========================================================================
    // Derived
    // =========================================================================

    /**
     * A quote base of zero or less is not a unit, it is a division by zero waiting to
     * happen in every price conversion. It used to be coerced to 1 on save, which hid
     * the mistake instead of reporting it.
     */
    let quoteBaseQuantityInvalid = $derived(isQuoteBaseQuantityInvalid(quoteBaseQuantity));
    /** A price is quoted per N units, and half a unit is not a quotation base. */
    let quoteBaseQuantityError = $derived(quoteBaseQuantityErrorKey(quoteBaseQuantity));

    let isValid = $derived(displayName.trim().length > 0 && !quoteBaseQuantityInvalid);
    let hasProvider = $derived(computeHasProvider(providerNoProvider, providerCode, providerIdentifier, providerIdentifierType));

    // Import advisory notices grouped by category (`kind`) — rendered as amber banners in the
    // wizard create context. Category label comes from app i18n; each reason bullet is authored
    // by the plugin in the report's language. Purely informational (never toggles `active`).
    let groupedNotices = $derived.by(() => groupImportNotices(importNotices));

    // I-bis #2 — dirty detection for the provider block.
    //
    // Previous behaviour: the "Save Without Testing?" modal fired on every
    // save whenever a provider was configured, even if the user only
    // touched a non-provider field (name, description, classification…).
    //
    // New behaviour: the modal fires only when any of the four provider
    // fields (code / identifier / identifier_type / params) changed
    // compared to the snapshot taken at load time. In **create mode**
    // (editMode === false) there is no snapshot, so any provider
    // configured means "dirty" by definition.
    let providerDirty = $derived(
        computeProviderDirty(editMode, hasProvider, {code: providerCode, identifier: providerIdentifier, identifierType: providerIdentifierType, params: providerParams}, initialProviderParamsJson, {
            code: initialProviderCode,
            identifier: initialProviderIdentifier,
            identifierType: initialProviderIdentifierType,
        }),
    );
    let title = $derived(editMode ? $t('assets.modal.titleEdit') : $t('assets.modal.title'));

    /** Build form snapshot for dirty tracking — single source of truth */
    function buildFormSnapshot(): string {
        return JSON.stringify([
            displayName,
            currency,
            assetType,
            iconUrl,
            quoteBaseQuantity,
            active,
            isBenchmark,
            providerUserUrl,
            JSON.stringify(identifierRows.map((r) => [r.type, r.value])),
            shortDescription,
            JSON.stringify(sectorDistribution),
            JSON.stringify(geographicDistribution),
            providerCode,
            providerIdentifier,
            providerIdentifierType,
            JSON.stringify(providerParams),
            providerNoProvider,
        ]);
    }

    /** Current form fingerprint for dirty detection */
    let currentSnapshot = $derived(buildFormSnapshot());
    let isDirty = $derived(initialSnapshot !== '' && currentSnapshot !== initialSnapshot);

    // =========================================================================
    // Helpers — Identifier rows ↔ DB columns conversion
    // (pure logic lives in ./assetIdentifiers.ts; the table and its row edits in ./AssetModalIdentifiers.svelte)
    // =========================================================================

    /** Handle image picker change — empty string means remove */
    function handleImagePickerChange(url: string) {
        iconUrl = url || null;
        showImagePicker = false;
    }

    /** Bulk delete identifiers with confirmation */
    function handleIdentifierBulkDelete() {
        pendingIdentifierDeleteIds = [...identifierSelectedIds];
        showIdentifierDeleteConfirm = true;
    }

    function confirmIdentifierBulkDelete() {
        const deleteSet = new Set(pendingIdentifierDeleteIds);
        for (const row of identifierRows) if (deleteSet.has(row.id)) markManualField(`identifier_${row.type.toLowerCase()}`);
        identifierRows = identifierRows.filter((r) => !deleteSet.has(r.id));
        identifierSelectedIds = [];
        pendingIdentifierDeleteIds = [];
        showIdentifierDeleteConfirm = false;
    }

    /** Get identifier value by type from rows */
    function getIdentifierByType(type: string): string {
        return identifierValue(identifierRows, type);
    }

    // =========================================================================
    // Lifecycle — Populate in edit mode
    // =========================================================================

    $effect(() => {
        void editMode;
        void editData?.id;
        if (open) {
            // Form edits must not retrigger population of the opening context.
            // populateFromEditData reads $state vars it just wrote (e.g. identifierRows.length)
            // which would create a dependency loop → effect_update_depth_exceeded.
            untrack(() => {
                closeIdentifierPrimary();
                activeSearchQuery = initialSearchQuery;
                if (editMode && editData) {
                    populateFromEditData(editData);
                } else if (!editMode && prefillData) {
                    populateFromPrefill(prefillData);
                } else {
                    resetForm();
                }
                if (!editMode && initialNoProvider) {
                    providerNoProvider = true;
                    providerProbe.configure();
                }
                if (!editMode && tourPreview) {
                    providerNoProvider = false;
                    providerExpanded = true;
                }
                initialSnapshot = buildFormSnapshot();
                initialClassification = $state.snapshot(buildClassificationParams(shortDescription, sectorDistribution, geographicDistribution));
            });
        } else {
            untrack(() => providerProbe.cancelPending());
        }
    });

    function populateFromEditData(data: AssetData) {
        displayName = data.display_name;
        currency = data.currency;
        assetType = data.asset_type ?? 'STOCK';
        iconUrl = data.icon_url ?? null;
        quoteBaseQuantity = data.quote_base_quantity && data.quote_base_quantity > 0 ? data.quote_base_quantity : 1;
        quoteBaseHint = null;
        active = data.active !== false;
        isBenchmark = data.is_benchmark === true;
        identifierRows = columnsToIdentifierRows(data);
        // Classification
        const cp = data.classification_params;
        shortDescription = cp?.short_description ?? '';
        descriptionFromPrefill = false;
        prefilledIdentifiers = new Set();
        sectorDistribution = cp?.sector_area?.distribution ?? {};
        geographicDistribution = cp?.geographic_area?.distribution ?? {};
        // Provider
        providerCode = data.provider_code ?? '';
        providerIdentifier = data.provider_identifier ?? '';
        providerIdentifierType = data.provider_identifier_type ?? 'TICKER';
        providerParams = data.provider_params ?? null;
        providerUserUrl = data.provider_user_url ?? '';
        providerNoProvider = !data.provider_code;
        resetDraftReads(data.provider_url ?? null);
        // #R3-4 — snapshot initial params to detect scheduled_investment changes at save.
        initialProviderParamsJson = providerParams ? JSON.stringify(providerParams) : '';
        // I-bis #2 — snapshot the other three provider fields too so
        // ``providerDirty`` can detect any user edit and gate the
        // "Save Without Testing?" modal accordingly.
        initialProviderCode = providerCode;
        initialProviderIdentifier = providerIdentifier;
        initialProviderIdentifierType = providerIdentifierType;
        moreInfoExpanded = identifierRows.length > 0;
        providerExpanded = !!data.provider_code;
        searchResultSelected = false;
        // Edit mode: the stored currency is a real prior value, not a blank default —
        // treat it as user-set so the provider probe flags a genuine mismatch.
        currencyUserSet = true;
        autoFilledFields = new Set();
        conflictFields = new Map();
        formError = null;
        showComparisonModal = false;
        comparisonDifferences = [];
        duplicateAssetName = null;
    }

    function resetForm() {
        displayName = '';
        currency = get(userSettings)?.base_currency ?? 'EUR';
        assetType = 'STOCK';
        blankCurrency = currency;
        blankAssetType = assetType;
        iconUrl = null;
        quoteBaseQuantity = 1;
        quoteBaseHint = null;
        active = true;
        isBenchmark = false;
        identifierRows = [];
        prefilledIdentifiers = new Set();
        shortDescription = '';
        descriptionFromPrefill = false;
        sectorDistribution = {};
        geographicDistribution = {};
        providerCode = '';
        providerIdentifier = '';
        providerIdentifierType = 'TICKER';
        providerParams = null;
        providerUserUrl = '';
        providerNoProvider = false;
        resetDraftReads();
        moreInfoExpanded = false;
        providerExpanded = false;
        searchResultSelected = false;
        currencyUserSet = false;
        autoFilledFields = new Set();
        conflictFields = new Map();
        formError = null;
        saving = false;
        showComparisonModal = false;
        comparisonDifferences = [];
        duplicateAssetName = null;
    }

    /** Pre-populate create form with partial data (e.g. from BRIM import wizard). */
    function populateFromPrefill(data: Partial<AssetData>) {
        resetForm();
        displayName = data.display_name?.trim() || data.identifier_isin?.trim() || data.identifier_ticker?.trim() || '';
        if (data.currency) currency = data.currency;
        if (data.asset_type) assetType = data.asset_type;
        // A base the import gives stays; else the type's default (Z-32 d: 100 for a bond)
        quoteBaseQuantity = data.quote_base_quantity && data.quote_base_quantity > 0 ? data.quote_base_quantity : defaultQuoteBaseQuantity(assetType);
        if (data.classification_params?.short_description) {
            shortDescription = data.classification_params.short_description;
            descriptionFromPrefill = true;
        }
        // Build identifier rows from prefilled columns (handles OTHER as a JSON list)
        const rows = columnsToIdentifierRows(data as AssetData);
        if (rows.length > 0) {
            identifierRows = rows;
            // Remember which codes came from the documents: it is the only way to tell the user
            // later *where* a value came from when a provider proposes a different one.
            prefilledIdentifiers = new Set(rows.map((r) => r.value.trim().toUpperCase()).filter((v) => v !== ''));
            moreInfoExpanded = true;
        }
        naLog(`prefill from import → name="${data.display_name ?? ''}" type=${data.asset_type ?? '—'} currency=${data.currency ?? '—'} qbq=${data.quote_base_quantity ?? '—'} · suggested identifiers: ${identifiersSummary()}`);
    }

    // =========================================================================
    // Duplicate name detection (debounced)
    // =========================================================================

    $effect(() => {
        if (!open) return;
        const name = displayName.trim();
        if (name.length < 2) {
            duplicateAssetName = null;
            return;
        }
        const context = untrack(() => providerProbe.captureContext());
        let current = true;
        const timer = setTimeout(async () => {
            try {
                const response = await zodiosApi.list_assets_api_v1_assets_query_get({
                    queries: {},
                });
                const items = response as any[];
                if (!current || !open || !providerProbe.isContextCurrent(context) || displayName.trim() !== name) return;
                const match = items.find((a: any) => {
                    if (editMode && editData?.id === a.id) return false;
                    return a.display_name.toLowerCase() === name.toLowerCase();
                });
                duplicateAssetName = match ? match.display_name : null;
            } catch {
                if (current && open && providerProbe.isContextCurrent(context)) duplicateAssetName = null;
            }
        }, 400);
        return () => {
            current = false;
            clearTimeout(timer);
        };
    });

    // =========================================================================
    // Search result selection — auto-fill + auto-test
    // =========================================================================

    function handleSearchSelect(result: any) {
        // If edit mode and identifier differs → show confirm
        if (editMode && providerIdentifier && providerIdentifier !== result.identifier) {
            pendingSearchResult = result;
            showIdentifierChangeConfirm = true;
            return;
        }
        applySearchResult(result);
    }

    function applySearchResult(result: any) {
        closeIdentifierPrimary();
        let question: IdentifierQuestion | null = null;
        // Auto-fill form
        displayName = result.display_name || displayName;
        if (result.asset_type) assetType = searchResultAssetType(result.asset_type);
        if (result.currency) currency = result.currency;
        // Z-32 (d): the quote base like the name — the provider's suggestion, else the type's default
        const quoteBase = proposeQuoteBase(result.quote_base_suggestion, assetType);
        quoteBaseQuantity = quoteBase.quantity;

        // Auto-fill identifier based on identifier_type
        const identifier = searchResultIdentifier(identifierRows, result.identifier_type, result.identifier);
        if (identifier.kind === 'conflict') {
            // Two codes of the same type, both legitimate: don't pick for the user.
            // The provider link below is established regardless — the search did its job;
            // only the *identity* question is deferred to the chooser.
            askIdentifierPrimary(identifier.type, identifier.incoming, identifier.current, result.provider_code);
            question = identifierQuestion(identifier.type, [identifier.incoming, identifier.current]);
        } else if (identifier.kind === 'rows') {
            identifierRows = identifier.rows;
        }

        // Auto-fill provider
        providerCode = result.provider_code;
        providerIdentifier = result.identifier;
        providerIdentifierType = result.identifier_type;
        providerNoProvider = false;
        // Carry over provider_params from search result (e.g. language, currency): the provider's own take priority,
        // the result's currency is the fallback.
        providerParams = searchResultProviderParams(result.provider_params, result.currency);
        resetDraftReads(result.provider_url ?? null);
        // After the reset, which clears the previous selection's questions: these are this one's.
        selectionQuestions = question ? [question] : [];
        // The new line's key: the hint and the remembered suggestion (R1) hold only for it.
        const lineKey = providerConfigurationKey(providerConfiguration());
        lineQuoteBaseSuggestion = quoteBase.kind === 'suggestion' ? {key: lineKey, suggestion: result.quote_base_suggestion} : null;
        quoteBaseHint = suggestionHint(quoteBase, result.provider_code, lineKey);

        // Expand sections
        moreInfoExpanded = true;
        providerExpanded = true;
        searchResultSelected = true;
        formError = null;

        // Auto-trigger test + metadata fetch (global ask provider). The read is the selection's:
        // its comparison waits for the chooser and never re-asks what the chooser asked.
        autoTriggerProbe();
        void fetchAndCompareMetadata('all', 'selection');

        // Wizard create context: if the selected result's provider name matches an existing
        // asset, offer to reuse it (and add the search keys) instead of creating a duplicate.
        void maybePromptReuse(result.display_name);

        naLog(`search result selected → name="${result.display_name ?? ''}" provider=${result.provider_code ?? '—'} ${(result.identifier_type ?? 'ID').toUpperCase()}=${result.identifier ?? '—'} type=${result.asset_type ?? '—'} currency=${result.currency ?? '—'}`);
        naLog(`identifiers now present: ${identifiersSummary()}`);
    }

    /**
     * Two codes of the same type are on the table — ask which one leads.
     *
     * The one the user does *not* elect is not discarded: it lands among the alternate
     * identifiers, where it no longer quotes but still *recognises*, so any future import
     * quoting it finds this asset. That is the whole CUM/quoted mechanism for a BTP.
     */
    function askIdentifierPrimary(idType: string, incoming: string, current: string, providerCodeForResult?: string | null) {
        identifierChoiceType = idType;
        identifierChoiceProvider = providerCodeForResult ? getAssetProviderName(providerCodeForResult) : null;
        identifierChoiceOptions = [
            {value: incoming, origin: 'provider'},
            {value: current, origin: prefilledIdentifiers.has(current.toUpperCase()) ? 'report' : editMode ? 'stored' : 'report'},
        ];
        // Default to the provider's value: it is the one a price provider can index.
        identifierChoicePrimary = incoming;
        identifierChoiceOpen = true;
    }

    /** Write the elected primary into its typed row and demote the rest to alternates. */
    function confirmIdentifierPrimary() {
        const idType = identifierChoiceType;
        const primary = identifierChoicePrimary;
        if (!idType || !primary) return;
        identifierRows = withElectedPrimary(
            identifierRows,
            idType,
            primary,
            identifierChoiceOptions.map((c) => c.value),
        );
        moreInfoExpanded = true;
        closeIdentifierPrimary();
    }

    /**
     * Leaving without choosing is a real outcome, not a non-event: the provider's code is
     * dropped and the asset stays on the identifier it started with. Cheap to undo now,
     * invisible later — so it is stated before it happens, never after.
     */
    function requestCloseIdentifierPrimary() {
        identifierChoiceDiscardOpen = true;
    }

    function closeIdentifierPrimary() {
        identifierChoiceDiscardOpen = false;
        identifierChoiceOpen = false;
        identifierChoiceType = null;
        identifierChoiceOptions = [];
        identifierChoicePrimary = null;
        identifierChoiceProvider = null;
    }

    /** A provider's display name, its code when unknown. */
    function providerDisplayName(code: string | null | undefined): string {
        return code ? getAssetProviderName(code) || code : '';
    }

    /** The hint under the quote base field for a proposal of a provider line (Z-32 d): only for its suggestion. */
    function suggestionHint(source: QuoteBaseSource, code: string | null | undefined, key: string): QuoteBaseHint | null {
        return source.kind === 'suggestion' ? {key, provider: providerDisplayName(code), quoteCurrency: source.quoteCurrency, quantity: source.quantity} : null;
    }

    /**
     * Lightweight, text-only console trace for the new-asset (create) flow. Makes the decision
     * history inspectable in the browser console: detected suggestions, identifiers already present,
     * duplicate hits (who + which asset), reuse choices and the final created asset. No side effects,
     * no network. Routed through the shared ``$lib/debug`` helper, so — exactly like the ``[API]`` and
     * ``[Toast]`` traces — it is active only in dev (``vite dev``) or a debug build (``VITE_DEBUG=true`` /
     * ``./dev.py server --debug``) and is tree-shaken away in a normal production build. Silent in edit
     * mode (this is a create-flow aid only).
     */
    function naLog(msg: string) {
        if (editMode) return;
        debug.info('new-asset', msg);
    }

    /** Compact "TYPE=value" list of the current identifier rows (for console traces). */
    function identifiersSummary(): string {
        return identifierRows.map((r) => `${r.type}=${r.value}`).join(', ') || 'none';
    }

    /**
     * After a search selection in the wizard create flow, check whether an existing asset
     * already has the same provider-supplied name. If so, prompt the user to reuse it
     * (optionally adding the import's search keys to its identifiers) instead of creating a
     * duplicate. No-op outside the wizard create context (onReuseExisting undefined) or edit mode.
     */
    async function maybePromptReuse(name: string) {
        if (!onReuseExisting || editMode) return;
        const trimmed = (name ?? '').trim();
        if (trimmed.length < 2) return;
        const context = providerProbe.captureContext();
        try {
            const response = await zodiosApi.list_assets_api_v1_assets_query_get({queries: {}});
            const items = response as any[];
            if (!open || saving || !providerProbe.isContextCurrent(context) || displayName.trim() !== trimmed) return;
            const match = items.find((a: any) => (a.display_name ?? '').toLowerCase() === trimmed.toLowerCase());
            if (match) {
                reuseExistingId = match.id;
                reuseExistingName = match.display_name;
                reuseModalOpen = true;
                naLog(`duplicate name detected → existing asset #${match.id} "${match.display_name}" matches provider name "${trimmed}". Prompting reuse (annulla / usa / usa+aggiungi identificatore).`);
            } else {
                naLog(`no duplicate for provider name "${trimmed}" → proceeding as a new asset`);
            }
        } catch {
            /* best-effort: if the lookup fails, just let the user create the asset normally */
        }
    }

    function reuseExisting(addKeys: boolean) {
        const id = reuseExistingId;
        reuseModalOpen = false;
        reuseExistingId = null;
        naLog(`reuse choice → asset #${id} ${addKeys ? 'REUSE + add provider search key to its identifiers' : 'REUSE only (no identifier change)'}`);
        if (id != null) onReuseExisting?.(id, addKeys);
    }

    function dismissReuse() {
        reuseModalOpen = false;
        reuseExistingId = null;
        naLog('reuse dismissed → keeping the new-asset form (will create a distinct asset)');
    }

    async function autoTriggerProbe() {
        await providerProbe.run('auto');
    }

    // =========================================================================
    // Ask Provider (metadata) — unified fetch + compare logic (C1+C2 refactoring)
    // =========================================================================

    /** Set or update an identifier row by type */
    function setIdentifierByType(type: string, val: string) {
        identifierRows = withIdentifier(identifierRows, type, val);
    }

    /**
     * Merge provider "soft" identifiers (identifier_other, a JSON list) as separate OTHER rows.
     * Additive + deduped: never route the array through the string-oriented compare path
     * (which would stuff the whole list into one row.value and throw `.trim` at save time).
     * Returns how many new rows were added.
     */
    function mergeOtherIdentifiers(raw: unknown): number {
        const merged = mergeOtherIdentifierValues(identifierRows, raw);
        if (merged.added > 0) identifierRows = merged.rows;
        return merged.added;
    }

    /**
     * Unified metadata fetch + comparison logic.
     * Used by: handleAskProvider() [global], handleAskProviderSection() [per-section],
     *          and applySearchResult() [auto after search].
     *
     * @param scope Which fields to compare. 'all' = everything, others = section-specific.
     */
    async function fetchAndCompareMetadata(scope: 'all' | 'identifiers' | 'sector' | 'geographic', origin: 'manual' | 'selection' = 'manual') {
        if (!hasProvider || saving) return;
        const request = providerProbe.beginMetadata();
        const requestIntent = new Map(manualFieldRevisions);
        const manuallyChanged = (field: string) => (manualFieldRevisions.get(field) ?? 0) !== (requestIntent.get(field) ?? 0);
        autoFilledFields = new Set();
        showComparisonModal = false;
        comparisonContext = null;
        heldComparison = null;

        try {
            const response = (await zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post(providerProbe.requestPayload(request, ['metadata']))) as any;
            if (!open || saving || !providerProbe.isMetadataCurrent(request)) return;

            const meta = response.metadata;
            // R1: the provider's explicit suggestion for this line is remembered, for a later probe without one
            const probeSuggestion: QuoteBaseSuggestion | null = meta?.quote_base_suggestion ?? null;
            if (probeSuggestion && proposeQuoteBase(probeSuggestion, assetType).kind === 'suggestion') lineQuoteBaseSuggestion = {key: request.key, suggestion: probeSuggestion};
            if (!meta?.success || !meta.patch_data) {
                toasts.info($t('assets.identifiers.askProviderHint') + ' — no data from provider');
                return;
            }
            // The decision is pure (./assetMetadataComparison.ts); the writes are applied here, in order.
            const lineSuggestion = lineQuoteBaseSuggestion?.key === request.key ? lineQuoteBaseSuggestion.suggestion : null;
            const providerName = providerDisplayName(request.configuration.providerCode);
            const {actions, differences, missingFields} = compareMetadata(
                meta.patch_data,
                comparisonSnapshot(),
                scope,
                manuallyChanged,
                {
                    name: $t('common.name'),
                    type: $t('common.type'),
                    currency: $t('common.currency'),
                    quoteBase: $t('assets.modal.quoteBaseQuantity'),
                    quoteBaseNote: (source) => {
                        const note = quoteBaseNote(source, providerName);
                        return note ? $t(note.key, {values: note.values}) : undefined;
                    },
                    description: $t('common.description'),
                    sector: $t('common.sectorDistribution'),
                    geographic: $t('common.geoDistribution'),
                },
                lineSuggestion,
            );
            for (const action of actions) applyComparisonAction(action);

            // --- RESULTS: consistent toast logic (Fix 3) ---
            if (missingFields.length > 0) {
                toasts.info($t('assets.comparison.noDistributionData', {values: {fields: missingFields.join(', ')}}));
            }

            if (differences.length > 0) {
                const intent = new Map(manualFieldRevisions);
                if (origin === 'manual') {
                    openComparison(differences, request, intent);
                } else {
                    // Every row answered by the chooser is a silent drop: no dialog, and no "all
                    // match" either — the differences existed, the user has already settled them.
                    const decision = decideComparison({differences, questions: selectionQuestions, promptOpen: selectionPromptOpen, current: true});
                    if (decision.kind === 'open') openComparison(decision.differences, request, intent);
                    else if (decision.kind === 'hold') heldComparison = {differences: decision.differences, context: request, intent};
                }
            } else if (missingFields.length === 0) {
                // Only show success if nothing was missing — never both info + success
                toasts.success($t('assets.comparison.allMatch'));
            }
        } catch (e: any) {
            if (!open || saving || !providerProbe.isMetadataCurrent(request)) return;
            console.error(`Ask Provider (${scope}) failed:`, e);
            // The probe's own limit (X-R66) says when to try again; any other failure stays generic
            toasts.error(probeRateLimitMessage(e, $t) ?? $t('common.errorOccurred'));
        } finally {
            providerProbe.finishMetadata(request);
        }
    }

    function openComparison(differences: DiffItem[], context: ProviderRequestTicket, intent: Map<string, number>) {
        comparisonDifferences = differences;
        comparisonContext = context;
        comparisonIntent = intent;
        showComparisonModal = true;
    }

    /** Open the comparison held behind the selection's prompts, if it is still current and still asks something. */
    function releaseHeldComparison() {
        const held = heldComparison;
        if (!held) return;
        heldComparison = null;
        const decision = decideComparison({differences: held.differences, questions: selectionQuestions, promptOpen: false, current: open && !saving && providerProbe.isMetadataCurrent(held.context)});
        if (decision.kind === 'open') openComparison(decision.differences, held.context, held.intent);
    }

    /** Global "Ask Provider" — compares all fields */
    function handleAskProvider() {
        fetchAndCompareMetadata('all');
    }

    /** Per-section "Ask Provider" — compares only the given section */
    function handleAskProviderSection(section: 'identifiers' | 'sector' | 'geographic') {
        fetchAndCompareMetadata(section);
    }

    /** The form values a metadata comparison reads (see ./assetMetadataComparison.ts). */
    function comparisonSnapshot(): ComparisonSnapshot {
        return {
            identifiers: Object.fromEntries(IDENTIFIER_TYPES.filter((type) => type !== 'OTHER').map((type) => [type, getIdentifierByType(type)])),
            displayName,
            assetType,
            currency,
            currencyUserSet,
            quoteBaseQuantity,
            shortDescription,
            descriptionFromPrefill,
            sectorDistribution,
            geographicDistribution,
        };
    }

    /** Apply one write of a metadata comparison and mark its field auto-filled. */
    function applyComparisonAction(action: ComparisonAction) {
        switch (action.kind) {
            case 'fill':
                setFieldValue(action.field, action.value);
                break;
            case 'fillDistribution':
                if (action.field === 'sector_area') sectorDistribution = action.value;
                else geographicDistribution = action.value;
                break;
            case 'mergeDescription':
                shortDescription = action.value;
                descriptionFromPrefill = false;
                break;
            case 'mergeOther':
                if (mergeOtherIdentifiers(action.values) === 0) return;
                break;
            case 'agree':
                break;
        }
        autoFilledFields = new Set([...autoFilledFields, action.field]);
    }

    /** Generic setter used by comparison logic */
    function setFieldValue(field: string, value: string) {
        if (field.startsWith('identifier_')) {
            const idType = fieldToIdType(field);
            setIdentifierByType(idType, value);
        } else {
            switch (field) {
                case 'display_name':
                    displayName = value;
                    break;
                case 'asset_type':
                    assetType = value;
                    break;
                case 'quote_base_quantity':
                    quoteBaseQuantity = Number(value);
                    break;
                case 'currency':
                    currency = value;
                    break;
                case 'short_description':
                    shortDescription = value;
                    descriptionFromPrefill = false;
                    break;
            }
        }
    }

    /**
     * Apply selected fields from ProviderComparisonModal.
     *
     * Identifier rows carry a `resolution` (P3/B-04): the chosen value lands in the
     * structured column and everything else is merged into `identifier_other` instead of
     * being discarded. Keeping the loser matters — for an Italian BTP the two ISINs are
     * two phases of one security, and losing either breaks a future reimport.
     */
    function handleComparisonApply(selectedFields: string[], resolutions: Record<string, {primary: string; alternates: string[]}> = {}) {
        if (!comparisonContext || !providerProbe.isMetadataCurrent(comparisonContext)) {
            showComparisonModal = false;
            return;
        }
        const changed = comparisonDifferences.some((diff) => selectedFields.includes(diff.field) && (manualFieldRevisions.get(diff.field) ?? 0) !== (comparisonIntent.get(diff.field) ?? 0));
        if (changed) {
            void fetchAndCompareMetadata('all');
            return;
        }
        for (const diff of comparisonDifferences) {
            if (selectedFields.includes(diff.field)) {
                if (diff.type === 'string') {
                    const resolution = resolutions[diff.field];
                    if (resolution) {
                        setFieldValue(diff.field, resolution.primary);
                        mergeOtherIdentifiers(resolution.alternates);
                    } else {
                        setFieldValue(diff.field, diff.providerValue);
                    }
                    if (diff.field === 'quote_base_quantity') quoteBaseHint = diff.quoteBaseSource ? suggestionHint(diff.quoteBaseSource, comparisonContext?.configuration.providerCode, comparisonContext?.key ?? providerConfigKey) : null;
                } else if (diff.type === 'distribution') {
                    if (diff.field === 'sector_area') {
                        sectorDistribution = diff.providerValue?.distribution ?? diff.providerValue;
                    } else if (diff.field === 'geographic_area') {
                        geographicDistribution = diff.providerValue?.distribution ?? diff.providerValue;
                    }
                }
                autoFilledFields = new Set([...autoFilledFields, diff.field]);
            }
        }
        showComparisonModal = false;
    }

    // =========================================================================
    // Save
    // =========================================================================

    function handleSave() {
        if (tourPreview || !isValid) return;
        // I-bis #2 — retest 1.3 follow-up: when the user changes the provider
        // dropdown, ``ProviderAssignmentSection.handleProviderChange`` clears
        // the identifier on purpose (different providers use different ID
        // formats). As a result ``hasProvider`` becomes ``false`` →
        // (a) the "Save Without Testing?" gate below would NOT fire, and
        // (b) ``saveEdit``'s provider step would silently skip both the
        //     remove and the assign branch, so the provider change would
        //     be thrown away without any feedback.
        // Surface an explicit form error so the user completes the provider
        // block (or ticks "No provider") before saving.
        if (editMode && providerDirty && !providerNoProvider && providerCode !== '' && !hasProvider) {
            formError = $t('assets.modal.providerIncomplete');
            setTimeout(() => {
                document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 50);
            return;
        }
        // I-bis #2 — only gate on the "Save Without Testing?" modal when
        // the provider block has actually been touched. Before, the modal
        // fired on every save with a configured provider, even if the
        // user only edited non-provider metadata (name, description,
        // classification…).
        if (hasProvider && providerDirty && providerTestStatus !== 'passed') {
            saveConfirmContext = providerProbe.captureContext();
            showSaveWithoutTestConfirm = true;
            return;
        }
        doSave();
    }

    function confirmSaveWithoutTest() {
        if (!saveConfirmContext || !providerProbe.isContextCurrent(saveConfirmContext)) {
            showSaveWithoutTestConfirm = false;
            handleSave();
            return;
        }
        void doSave();
    }

    async function doSave() {
        saving = true;
        providerProbe.cancelPending();
        formError = null;
        showSaveWithoutTestConfirm = false;
        saveConfirmContext = null;

        // I-bis #22 (Batch 4.d-part2) — route the orchestrator through
        // ``trySave`` for uniform error extraction. Two custom
        // semantics are preserved:
        //   (a) **409 currency-change** is NOT handled here: it's intercepted
        //       deeper in ``saveEdit`` (see the patch_assets_bulk try/catch
        //       around the PATCH call) which rewrites the ``patchResp`` from
        //       ``detail.results[]`` and opens the destructive
        //       ``AssetCurrencyChangeModal``. That path never throws to us.
        //   (b) **409 duplicate-name** (create path) still maps to the
        //       dedicated ``duplicateName`` i18n key via the ``onError``
        //       hook below.
        // ``toast: false`` because the error is rendered inline via the
        // ``data-form-error`` banner (the existing UX).
        const result = await trySave(() => (editMode && editData?.id ? saveEdit(editData.id) : saveCreate()), {
            toast: false,
            fallback: $t('assets.modal.saveFailed'),
            onError: (err: any) => {
                if (err?.response?.status === 409) {
                    formError = $t('assets.modal.duplicateName');
                    return true;
                }
                return false;
            },
        });

        if (result.status === 'error' && !formError) {
            formError = result.message;
        }
        if (result.status === 'error') {
            // Scroll error into view (same behavior as the previous try/catch)
            setTimeout(() => {
                document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 50);
        }
        saving = false;
    }

    /** The form's values, as the save requests are built from them (./assetPayload.ts). */
    function formFields(): AssetFormFields {
        return {displayName, currency, assetType, iconUrl, quoteBaseQuantity, active, isBenchmark, userUrl: providerUserUrl, shortDescription, sectorDistribution, geographicDistribution, identifierRows};
    }

    /** The provider the save assigns to the asset. */
    function providerAssignment(): ProviderAssignment {
        return {code: providerCode, identifier: providerIdentifier, identifierType: providerIdentifierType, params: providerParams};
    }

    async function saveCreate() {
        // Step 1: Create asset
        const createItem = buildCreateItem(formFields());
        const createPayload = [createItem];

        const createResp = (await zodiosApi.create_assets_bulk_api_v1_assets_post(createPayload as any)) as any;
        const result = createResp?.results?.[0];
        if (!result?.success) {
            throw new Error(result?.message || 'Failed to create asset');
        }
        const assetId = result.asset_id;
        naLog(`created asset #${assetId} "${displayName.trim()}" type=${assetType} currency=${currency} qbq=${createItem.quote_base_quantity} · identifiers: ${identifiersSummary()} · provider=${hasProvider ? providerCode : 'none'}`);

        // Upsert the new asset into the shared cache so other pages
        // (transactions cell, AssetCard, AssetTable, …) reflect the entry
        // immediately. The BE response only carries `asset_id`; we merge the
        // fields the FE just submitted (no extra round-trip).
        mergeAssets([{id: assetId, ...(createItem as Record<string, unknown>)}]);

        // Step 2: Assign provider (separate try/catch — asset already created)
        // Skip assignment for scheduled_investment if no schedule is configured yet
        const skipProviderAssignment = providerCode === 'scheduled_investment' && (!providerParams || !providerParams.schedule?.length);
        if (hasProvider && !skipProviderAssignment) {
            try {
                const assignPayload = [buildProviderAssignItem(assetId, providerAssignment())];
                await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload as any);
            } catch (assignErr: any) {
                console.error('Provider assignment failed after asset creation:', assignErr);
                toasts.warning($t('assets.modal.createSuccessProviderFailed', {values: {name: displayName}}));
                open = false;
                oncreated?.(assetId);
                return;
            }
        }

        // Success UX first — close the modal and notify immediately. The historical price
        // sync below is fired in the BACKGROUND so the ~2s network round-trip no longer
        // blocks the modal close (the user reported the save felt too slow on localhost).
        const createdLabel = linkCreatedAsset ? entityDetailLinkHtml({kind: 'asset', id: assetId}, displayName) : escapeHtml(displayName);
        toasts.success($t('assets.modal.createSuccess', {values: {name: createdLabel}}));
        open = false;
        const syncing = hasProvider && !skipProviderAssignment;
        oncreated?.(assetId, {syncing});

        // The one price sync of a new asset with a provider (O-20): fire-and-forget, so the modal
        // closes at once, and reported through `onsynced`, so the caller can show it and reload —
        // the Assets page used to start a second sync of its own. Parametric providers (e.g.
        // scheduled_investment) need it too: assigning one stores no price, the sync generates
        // the series. Errors are non-blocking (the chart stays empty until the next sync).
        //
        // `start: 'resume'` is the backend sentinel for "the day after the last price I already
        // have, or the provider's full history if I have none". A just-created asset has none,
        // so this is a full-history fetch — expressed as the same rule every other auto-sync
        // uses, instead of a hardcoded date that silently truncates whatever precedes it.
        if (syncing) {
            const end = new Date().toISOString().slice(0, 10);
            void zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([{asset_id: assetId, date_range: {start: 'resume', end}}]).then(
                (response) => onsynced?.(assetId, ((response as any)?.results?.[0] ?? null) as AssetCreateSyncResult | null),
                // Only the request's failure: an error of the caller's handler must not report the sync a second time.
                (syncErr) => {
                    console.warn('Post-create full-history sync failed (non-blocking):', syncErr);
                    onsynced?.(assetId, null);
                },
            );
        }
    }

    /** How much of the asset's series was generated, for the warning below.
     *
     * Uses the market-data summary — the same counters the currency-change flow
     * relies on — because it reports *stored rows*. The price query endpoint
     * cannot be used here: it backward-fills every calendar day in the requested
     * range, so it would answer with the width of the window instead of the size
     * of the series, and the warning would quote a plausible wrong number.
     *
     * Best effort on purpose: a failed count must never block a save, so a
     * failure degrades to zeroes and the warning stays generic rather than
     * lying with a number it does not have.
     */
    async function countGeneratedSeries(assetId: number): Promise<{prices: number; events: number}> {
        try {
            const summary: any = await zodiosApi.market_data_summary_api_v1_assets__asset_id__market_data_summary_get({params: {asset_id: assetId}});
            return {prices: summary?.prices ?? 0, events: summary?.events_provider ?? 0};
        } catch (err) {
            console.warn('Could not count the generated series before the provider switch:', err);
            return {prices: 0, events: 0};
        }
    }

    async function saveEdit(assetId: number) {
        // #R3-4 — for PARAMETRIC_GENERATION providers (e.g. scheduled_investment), if the
        // user changed `provider_params` intercept the save flow to show an explicit
        // regenerate confirmation. Confirming will: (1) PATCH/assign through the normal
        // path, (2) BE wipes old prices + invalidates caches atomically, (3) we trigger
        // an immediate re-sync so the chart reflects the new schedule without requiring
        // a manual click. Gating on `isParametricProvider()` (kind-based) instead of
        // hardcoding 'scheduled_investment' so future parametric providers inherit the
        // flow for free.
        await ensureAssetProvidersCached();
        if (isParametricProvider(providerCode) && !providerNoProvider && initialProviderParamsJson && JSON.stringify(providerParams ?? null) !== initialProviderParamsJson && !pendingSaveAssetId) {
            pendingSaveAssetId = assetId;
            showScheduledRegenConfirm = true;
            return; // wait for confirm; the modal will re-invoke saveEdit()
        }

        // Same interception for the *other* destructive parametric case: swapping the
        // provider away from a parametric one. The backend wipes the generated prices
        // and events (services/assets/provider_management.py, "provider changed"), and without that wipe the
        // next sync would resume from the day after the last invented price and never
        // backfill the real past. Counts come from the two existing query endpoints —
        // a warning that cannot say how much it is about to destroy is not a warning.
        if (!providerNoProvider && hasProvider && initialProviderCode && providerCode !== initialProviderCode && isParametricProvider(initialProviderCode) && !pendingSaveAssetId) {
            pendingSaveAssetId = assetId;
            parametricSwitchInfo = {
                ...(await countGeneratedSeries(assetId)),
                from: getAssetProviderName(initialProviderCode) || initialProviderCode,
                to: getAssetProviderName(providerCode) || providerCode,
            };
            showParametricSwitchConfirm = true;
            return; // wait for confirm; the modal will re-invoke saveEdit()
        }

        // Step 1: Patch asset (classification_params only when it changed since the modal opened)
        const patchItem = buildPatchItem(assetId, formFields(), initialClassification);
        const patchPayload = [patchItem];

        // I.3 + R3-3 Policy D — PATCH returns a per-item failure with the structured
        // blocker token when the user changed the currency on an asset that still has
        // *any* market data (prices, events or linked transactions). Token format:
        //   CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=N|events_manual=M|
        //     events_provider=K|linked_tx=L|oldest=...|newest=...|from=X|to=Y
        // The modal turns this into the destructive-confirm dialog.
        //
        // I-bis #7 — the backend now also returns HTTP 409 when *every* item in
        // the batch is blocked by market data (single-asset edits always fall in
        // this case). Axios throws on non-2xx; we catch below and re-extract the
        // ``results[]`` from the response body so the UX is identical.
        let patchResp: any;
        try {
            patchResp = await zodiosApi.patch_assets_bulk_api_v1_assets_patch(patchPayload as any);
        } catch (err: any) {
            const status = err?.response?.status;
            const detail = err?.response?.data?.detail;
            if (status === 409 && detail && typeof detail === 'object' && Array.isArray(detail.results)) {
                patchResp = {results: detail.results, success_count: 0};
            } else {
                throw err;
            }
        }
        const resultItem = patchResp?.results?.[0];
        if (resultItem && resultItem.success === false && isCurrencyChangeBlockedMessage(resultItem.message)) {
            currencyChangeBlocker = {
                assetId,
                ...parseCurrencyChangeBlocker(resultItem.message),
            };
            currencyChangePatchPayload = patchItem;
            currencyChangeProviderAssigned = hasProvider && !providerNoProvider;
            currencyChangeModalOpen = true;
            return; // abort save — the modal will either finish the flow or the user cancels
        }
        if (!resultItem?.success) throw new Error(resultItem?.message || $t('assets.modal.saveFailed'));

        // PATCH succeeded — sync the patched fields into the shared cache so
        // every consumer (transactions cell, AssetCard, AssetTable, …) sees
        // the new icon/name/etc. without a manual reload. The BE response
        // only carries `{success, asset_id, message}`; we merge the fields
        // the FE just submitted.
        mergeAssets([{id: assetId, ...(patchItem as unknown as Record<string, unknown>)}]);

        // Step 2: Handle provider change
        if (providerNoProvider) {
            // Remove provider
            try {
                await zodiosApi.remove_providers_bulk_api_v1_assets_provider_delete(undefined, {
                    queries: {asset_ids: [assetId]},
                });
            } catch (removeErr: unknown) {
                // X-R62: a removal refused because transactions are linked to the events the provider generated (or to
                // one linked meanwhile) is said here, inline and in the user's language, as X-R49's refusal below; the
                // modal stays open on the draft, whose 409 would otherwise read «duplicate name». Any other error goes on.
                const refusal = wipeRefusalMessage(removeErr, $t, (iso) => formatDay(iso));
                if (refusal === null) throw removeErr;
                formError = refusal;
                pendingSaveAssetId = null;
                setTimeout(() => {
                    document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
                }, 50);
                return;
            }
        } else if (hasProvider) {
            const assignPayload = [buildProviderAssignItem(assetId, providerAssignment())];
            try {
                await zodiosApi.assign_providers_bulk_api_v1_assets_provider_post(assignPayload as any);
            } catch (assignErr: unknown) {
                // X-R49: a change refused because a split the provider generated has adjustments without a purchase cost
                // is said here, inline and in the user's language, and the modal stays open (every way in: the regenerate
                // and switch-away confirms, and the plain save, whose 409 would read «duplicate name»). Any other error goes on.
                const refusal = wipeRefusalMessage(assignErr, $t, (iso) => formatDay(iso));
                if (refusal === null) throw assignErr;
                formError = refusal;
                pendingSaveAssetId = null;
                setTimeout(() => {
                    document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
                }, 50);
                return;
            }
        }

        // #R3-4 — after a confirmed scheduled_investment regenerate, trigger an
        // immediate sync so the prices are regenerated with the new params and
        // the chart refreshes on close.
        //
        // #R6-5 (2026-04-24, retest Batch 4) — extended to cover non-parametric
        // provider changes too. Scenario 1.3: user changes provider Yahoo →
        // JustETF with a valid identifier. Without this auto-sync, the page
        // reloads after save but the chart keeps showing the OLD prices (from
        // Yahoo) because nothing regenerated the series. The user perceived
        // this as "no reload happened" and had to F5 manually. Now, any
        // change to ``providerCode``, ``providerIdentifier`` or
        // ``providerIdentifierType`` triggers an opportunistic sync so the
        // new provider fetches fresh data on close. ``providerDirty`` already
        // covers all four fields including ``providerParams``.
        const didRegenerate = pendingSaveAssetId === assetId;
        pendingSaveAssetId = null;
        const providerChanged = providerDirty && !providerNoProvider && hasProvider;
        const shouldAutoSync = (didRegenerate && isParametricProvider(providerCode)) || providerChanged;
        if (shouldAutoSync && !providerNoProvider) {
            try {
                const end = new Date().toISOString().slice(0, 10);
                // One rule for both cases: resume from the day after the last price we already
                // have, and fall back to the provider's full history when there is none.
                //
                // It covers the parametric regenerate without a special case, because the backend
                // wipes every price row before this runs (services/assets/provider_management.py: "params changed … wiped
                // N price row(s)") — nothing left to resume from, so 'resume' resolves to 'min' by
                // itself. A provider change wipes nothing, so the old series stays and the new
                // provider only fills the gap.
                await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([{asset_id: assetId, date_range: {start: 'resume', end}}]);
            } catch (syncErr) {
                console.warn('Post-save auto-sync failed (non-blocking):', syncErr);
                // Non-blocking: the user can manually re-sync if needed.
            }
        }

        toasts.success($t('assets.modal.saveSuccess', {values: {name: displayName}}));
        open = false;
        onupdated?.();
    }

    /**
     * Currency-change wipe-confirm flow: triggered when the user accepts the
     * destructive currency change. Sync the patched fields into the shared
     * cache, then evict so any consumer refetches fresh data on next access.
     */
    function handleCurrencyChangeConfirmed(): void {
        const payload = currencyChangePatchPayload;
        if (payload && typeof payload.asset_id === 'number') {
            const id = payload.asset_id;
            mergeAssets([{id, ...payload}]);
            invalidateAfterMutation(id);
        }
        open = false;
        onupdated?.();
    }

    // =========================================================================
    // Close
    // =========================================================================

    function handleClose() {
        if (saving) return;
        if (tourPreview) {
            doClose();
            return;
        }
        if (isDirty) {
            showDiscardConfirm = true;
            return;
        }
        doClose();
    }

    function doClose() {
        showDiscardConfirm = false;
        providerProbe.cancelPending();
        open = false;
        onclose?.();
    }
</script>

<ModalBase {open} maxWidth="4xl" allowOverflow={true} onRequestClose={handleClose} {zIndex} testId="asset-modal">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-lf-subtle">
        <h2 class="text-lg font-semibold text-lf-primary">{title}</h2>
        <button type="button" onclick={handleClose} disabled={saving} class="text-lf-muted hover:text-lf-secondary transition-colors">
            <X size={20} />
        </button>
    </div>

    <!-- Body. The scroll box is this div, not the fieldset: when flex shrinks a fieldset that scrolls,
         Chromium keeps painting its content down to the max height — under the footer, which it shows
         through on a phone. -->
    <div class="min-h-0 max-h-[70vh] overflow-y-auto">
        <fieldset disabled={saving} class="min-w-0 px-6 py-4 space-y-5" data-testid="asset-modal-form" aria-busy={saving || askingProvider} data-busy={saving || askingProvider} data-snapshot-ready={initialSnapshot !== '' ? 'true' : 'false'} data-dirty={isDirty ? 'true' : 'false'}>
            <!-- Import advisory notices (wizard create context): amber banners grouped by kind. -->
            {#if !editMode && groupedNotices.length > 0}
                <AssetModalImportNotices groups={groupedNotices} />
            {/if}
            <!-- Search Online -->
            <div use:guideAnchor={'asset.search'} data-testid="asset-tour-search">
                {#if !editMode && initialSearchBadges.length > 0}
                    <!-- All three (title, badges, input) in one space-y-1.5 wrapper → uniform 6px gaps -->
                    <div class="space-y-1.5">
                        <div class="flex items-center gap-2 text-xs font-semibold text-lf-muted uppercase tracking-wider">
                            <Search size={12} />
                            <span>{$t('assets.modal.searchOnline')}</span>
                        </div>
                        <div class="flex flex-wrap items-center gap-1.5">
                            <span class="flex items-center gap-1 text-xs text-lf-muted shrink-0">
                                <Search size={11} class="opacity-60" />
                                {$t('assets.modal.searchSuggestions')}:
                            </span>
                            {#each initialSearchBadges as badge, i}
                                {@const color = getIndexColor(i, 200)}
                                <button type="button" style="background-color:{color.bg};color:{color.text}" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium transition-opacity hover:opacity-80" onclick={() => (activeSearchQuery = badge.value)}>
                                    {badge.label}
                                </button>
                            {/each}
                        </div>
                        {#key activeSearchQuery}
                            <AssetSearchAutocomplete onselect={handleSearchSelect} initialQuery={activeSearchQuery} hideTitle={true} hints={searchHints} reportContext={searchReportContext} />
                        {/key}
                    </div>
                {:else}
                    {#key activeSearchQuery}
                        <AssetSearchAutocomplete onselect={handleSearchSelect} initialQuery={editMode ? '' : activeSearchQuery} hints={searchHints} reportContext={searchReportContext} />
                    {/key}
                {/if}
            </div>

            <AssetModalDetails
                bind:displayName
                bind:assetType
                bind:quoteBaseQuantity
                quoteBaseSuggestion={visibleQuoteBaseHint}
                bind:providerUserUrl
                bind:shortDescription
                {currency}
                {iconUrl}
                {hasProvider}
                {askingProvider}
                {duplicateAssetName}
                {quoteBaseQuantityInvalid}
                {quoteBaseQuantityError}
                onmanualedit={markManualField}
                onaskprovider={handleAskProvider}
                onpickicon={() => (showImagePicker = true)}
                oncurrencychange={(v) => {
                    currency = v;
                    currencyUserSet = true;
                    markManualField('currency');
                }}
                ondescriptionedit={() => {
                    descriptionFromPrefill = false;
                    markManualField('short_description');
                }}
            />

            <!-- More Info (collapsible — Identifiers + Classification) -->
            <div class="border border-lf-subtle rounded-lg" use:guideAnchor={'asset.provider'} data-testid="asset-tour-provider">
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div
                    class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-lf-secondary bg-lf-panel hover:bg-lf-neutral transition-colors cursor-pointer select-none"
                    role="button"
                    tabindex="0"
                    data-testid="asset-modal-more-info"
                    data-expanded={moreInfoExpanded}
                    onclick={() => {
                        moreInfoExpanded = !moreInfoExpanded;
                    }}
                    onkeydown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            moreInfoExpanded = !moreInfoExpanded;
                        }
                    }}
                >
                    <div class="flex items-center gap-2">
                        {#if moreInfoExpanded}
                            <ChevronDown size={16} />
                        {:else}
                            <ChevronRight size={16} />
                        {/if}
                        <span>{$t('assets.modal.moreInfo')}</span>
                    </div>
                </div>

                {#if moreInfoExpanded}
                    <div class="px-4 py-3 space-y-4 border-t border-lf-subtle">
                        <AssetModalIdentifiers bind:rows={identifierRows} bind:selectedIds={identifierSelectedIds} {hasProvider} {askingProvider} onmanualedit={markManualField} onaskprovider={() => handleAskProviderSection('identifiers')} onbulkdelete={handleIdentifierBulkDelete} />

                        <!-- Sub-section: Classification -->
                        <div class="space-y-3">
                            <div class="text-[10px] font-semibold text-lf-muted uppercase tracking-wider">
                                {$t('common.classification')}
                            </div>

                            <!-- Sector Distribution -->
                            <DistributionEditor kind="sector" bind:value={sectorDistribution} {hasProvider} {askingProvider} onchange={() => markManualField('sector_area')} onAskProvider={() => handleAskProviderSection('sector')} zIndex={zIndex + 20} />

                            <!-- Geographic Distribution -->
                            <DistributionEditor kind="geographic" bind:value={geographicDistribution} {hasProvider} {askingProvider} onchange={() => markManualField('geographic_area')} onAskProvider={() => handleAskProviderSection('geographic')} zIndex={zIndex + 20} />
                        </div>
                    </div>
                {/if}
            </div>

            <AssetModalProvider
                bind:expanded={providerExpanded}
                bind:noProvider={providerNoProvider}
                bind:providerCode
                bind:identifier={providerIdentifier}
                bind:identifierType={providerIdentifierType}
                bind:providerParams
                {providerUrl}
                probeState={providerProbe}
                testStatus={providerTestStatus}
                {saving}
                onreconcile={reconcileProviderContext}
            />

            <!-- Auto-assign info banner -->
            {#if searchResultSelected && hasProvider && !editMode}
                <InfoBanner variant="info">
                    <span>{$t('assets.modal.autoAssignInfo', {values: {provider: providerCode}})}</span>
                </InfoBanner>
            {/if}

            <!-- Error -->
            {#if formError}
                <div data-form-error data-testid="asset-modal-form-error" class="text-sm text-lf-danger-on-soft bg-lf-danger-soft px-4 py-2 rounded-lg">
                    {formError}
                </div>
            {/if}
        </fieldset>
    </div>

    <AssetModalFooter bind:active bind:isBenchmark {saving} {isValid} {tourPreview} {editMode} oncancel={handleClose} onsave={handleSave} />
</ModalBase>

<!-- Confirmation: Save without test -->
<ConfirmModal
    open={showSaveWithoutTestConfirm}
    title={$t('assets.confirm.saveWithoutTest')}
    message={$t('assets.confirm.saveWithoutTestMessage')}
    confirmText={$t('assets.confirm.saveAnyway')}
    warning={true}
    onConfirm={confirmSaveWithoutTest}
    onCancel={() => {
        showSaveWithoutTestConfirm = false;
        saveConfirmContext = null;
    }}
    zIndex={zIndex + 20}
/>

<AssetModalSelectionPrompts
    {zIndex}
    assetName={displayName}
    choiceOpen={identifierChoiceOpen}
    choiceType={identifierChoiceType}
    choiceOptions={identifierChoiceOptions}
    bind:choicePrimary={identifierChoicePrimary}
    choiceProvider={identifierChoiceProvider}
    bind:choiceDiscardOpen={identifierChoiceDiscardOpen}
    onchoicerequestclose={requestCloseIdentifierPrimary}
    onchoiceconfirm={confirmIdentifierPrimary}
    onchoicediscard={closeIdentifierPrimary}
    identifierChangeOpen={showIdentifierChangeConfirm}
    onidentifierchangeconfirm={() => {
        showIdentifierChangeConfirm = false;
        if (pendingSearchResult) applySearchResult(pendingSearchResult);
        pendingSearchResult = null;
    }}
    onidentifierchangecancel={() => {
        showIdentifierChangeConfirm = false;
        pendingSearchResult = null;
    }}
    reuseOpen={reuseModalOpen}
    {reuseAllowKeyMerge}
    {reuseExistingName}
    onreuse={reuseExisting}
    onreusedismiss={dismissReuse}
/>

<!-- Confirmation: Discard unsaved changes -->
<ConfirmModal
    open={showDiscardConfirm}
    title={$t('common.discardChanges')}
    message={$t('common.discardChangesMessage')}
    confirmText={$t('common.discardAndClose')}
    cancelText={$t('common.continueEditing')}
    warning={true}
    testId="asset-modal-discard-confirm"
    onConfirm={() => doClose()}
    onCancel={() => {
        showDiscardConfirm = false;
    }}
    zIndex={zIndex + 20}
/>

<!-- #R3-4 — Confirmation: regenerate scheduled_investment prices on params change -->
<ConfirmModal
    open={showScheduledRegenConfirm}
    title={$t('assets.modal.scheduledRegenTitle')}
    message={$t('assets.modal.scheduledRegenMessage')}
    confirmText={$t('assets.modal.scheduledRegenConfirm')}
    cancelText={$t('common.cancel')}
    danger={true}
    testId="asset-scheduled-regen-confirm"
    onConfirm={() => {
        showScheduledRegenConfirm = false;
        const aid = pendingSaveAssetId;
        // pendingSaveAssetId is kept non-null so the guard in saveEdit() skips
        // re-showing this modal and proceeds to PATCH+assign+sync.
        if (aid !== null) {
            saveEdit(aid).catch((err) => {
                console.error('saveEdit after regenerate confirm failed:', err);
                toasts.error($t('common.errorOccurred'));
                pendingSaveAssetId = null;
            });
        }
    }}
    onCancel={() => {
        showScheduledRegenConfirm = false;
        pendingSaveAssetId = null;
    }}
    zIndex={zIndex + 20}
/>

<!-- Confirmation: swapping away from a parametric provider discards its generated series -->
<ConfirmModal
    open={showParametricSwitchConfirm}
    title={$t('assets.modal.parametricSwitchTitle')}
    message={$t('assets.modal.parametricSwitchMessage', {
        values: {
            from: parametricSwitchInfo?.from ?? '',
            to: parametricSwitchInfo?.to ?? '',
            prices: parametricSwitchInfo?.prices ?? 0,
            events: parametricSwitchInfo?.events ?? 0,
        },
    })}
    confirmText={$t('assets.modal.parametricSwitchConfirm')}
    cancelText={$t('common.cancel')}
    danger={true}
    testId="asset-parametric-switch-confirm"
    onConfirm={() => {
        showParametricSwitchConfirm = false;
        const aid = pendingSaveAssetId;
        // pendingSaveAssetId stays non-null so the guard in saveEdit() skips this
        // modal on the second pass and proceeds to PATCH+assign+sync.
        if (aid !== null) {
            saveEdit(aid).catch((err) => {
                console.error('saveEdit after parametric switch confirm failed:', err);
                toasts.error($t('common.errorOccurred'));
                pendingSaveAssetId = null;
            });
        }
    }}
    onCancel={() => {
        showParametricSwitchConfirm = false;
        parametricSwitchInfo = null;
        pendingSaveAssetId = null;
    }}
    zIndex={zIndex + 20}
/>

<!-- Provider Comparison Modal -->
<ProviderComparisonModal
    bind:open={showComparisonModal}
    differences={comparisonDifferences}
    assetName={displayName}
    zIndex={zIndex + 20}
    onapply={handleComparisonApply}
    oncancel={() => {
        showComparisonModal = false;
    }}
/>

<!-- I.6 + R3-3 Policy D — Destructive currency-change modal. Triggered by the CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA marker. -->
<AssetCurrencyChangeModal
    bind:open={currencyChangeModalOpen}
    blocker={currencyChangeBlocker}
    patchPayload={currencyChangePatchPayload}
    providerAssigned={currencyChangeProviderAssigned}
    zIndex={zIndex + 20}
    onconfirmed={() => {
        // The flow completed: the child modal already emitted the final
        // `currencyChange.done` toast. I-bis #12 — suppress the generic
        // "updated successfully" toast here to avoid duplicate notifications.
        // Cache eviction + merge handled by `handleCurrencyChangeConfirmed`.
        handleCurrencyChangeConfirmed();
    }}
    oncanceled={() => {
        currencyChangeBlocker = null;
        currencyChangePatchPayload = null;
    }}
/>

<!-- Image Picker for asset icon -->
<ImagePickerWrapper open={showImagePicker} preset="asset-icon" title={$t('uploads.selectIcon')} initialUrl={iconUrl ?? ''} circularPreview={false} filterImages={true} onchange={handleImagePickerChange} oncancel={() => (showImagePicker = false)} zIndex={zIndex + 20} />

<!-- Confirmation: Bulk delete identifiers -->
<ConfirmModal
    open={showIdentifierDeleteConfirm}
    title={$t('assets.identifiers.deleteSelected')}
    message={$t('assets.identifiers.deleteConfirmMessage', {values: {n: pendingIdentifierDeleteIds.length}})}
    confirmText={$t('common.delete')}
    warning={true}
    onConfirm={confirmIdentifierBulkDelete}
    onCancel={() => {
        showIdentifierDeleteConfirm = false;
        pendingIdentifierDeleteIds = [];
    }}
    zIndex={zIndex + 20}
/>
