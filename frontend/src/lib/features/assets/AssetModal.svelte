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
    import AssetEnrichersModal from './enrichers/AssetEnrichersModal.svelte';
    import {createEnricherRecognitionState} from './enrichers/enricherRecognition.svelte';
    import {entersAlone, recognitionLine, type EnricherBinding, type EnricherInfo, type EnricherReadState, type EnrichersBanner} from './enrichers/enrichersEditState';
    import {invalidateAssetProfile, loadProfileCatalogue, readAssetProfile, type ProfileVoice} from './profile/profileStore';
    import AssetModalProfileRow from './profile/AssetModalProfileRow.svelte';
    import ProfileEditModal from './profile/ProfileEditModal.svelte';
    import {createProfileAutoAsk} from './profile/profileAutoAsk.svelte';
    import {autoAskRequest, currentFromRead, descriptionShown, mergeAutoFills, profileBlocksSave, profileRowSummary, userChanges, withDescription, withoutFillsOutside} from './profile/assetProfileDraft';
    import {profilePatch, type AskAnswer, type CurrentVoice, type PendingChanges, type PendingVoice} from './profile/profileEditState';
    import {todayIso} from '$lib/utils/dateOnly';
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
    import {getIndexColor} from '$lib/utils/colors';
    import ImagePickerWrapper from '$lib/components/ui/media/ImagePickerWrapper.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {probeRateLimitMessage} from './resolveProviderError';
    import {userSettings} from '$lib/stores/app/settings';
    import {get} from 'svelte/store';
    import {trySave} from '$lib/utils/trySave';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {wipeRefusalMessage} from './currencyChangeErrors';
    import {assertPatchCommitted} from './assetPatchResult';
    import {IMPACT_DIALOG, impactValues, loadProviderImpact, type ProviderImpact} from './providerImpact';
    import {currentLanguage} from '$lib/stores/app/language';
    import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
    import {columnsToIdentifierRows, fieldToIdType, identifierValue, withIdentifier, mergeOtherIdentifierValues, withElectedPrimary} from './assetIdentifiers';
    import {searchResultAssetType, searchResultAssignmentType, searchResultIdentifier, searchResultProviderParams} from './assetSearchSelection';
    import {compareMetadata, type ComparisonAction, type ComparisonScope, type ComparisonSnapshot} from './assetMetadataComparison';
    import {hasSomethingToLose, loadCurrencyChangeImpact, type CurrencyChangeImpact} from './currencyImpact';
    import {buildCreateItem, buildPatchItem, buildProviderAssignItem, type AssetFormFields, type ProviderAssignment} from './assetPayload';
    import {isQuoteBaseQuantityInvalid, quoteBaseQuantityErrorKey, defaultQuoteBaseQuantity, proposeQuoteBase, quoteBaseNote, computeHasProvider, computeProviderDirty, groupImportNotices, type QuoteBaseSource, type QuoteBaseSuggestion} from './assetFormState';
    import {ensureAssetProvidersCached, getAssetProviderAcceptedTypes, getAssetProviderName, getAssetProviderParamKeys, isParametricProvider} from '$lib/utils/providerHelpers';
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
        /** The asset's enrichers (plan 68, B3): bindings in their order, and the last read of each. Edit mode only. */
        enrichers?: {config: Record<string, EnricherBinding>; state?: Record<string, EnricherReadState>} | null;
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
        /**
         * Edit mode: open with the enrichers' window already on top (plan 68 E6c, the «Configura» of the «Profilo» tab).
         * Read when the window opens; the caller sets it for that opening only.
         */
        enrichersOnOpen?: boolean;
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
        enrichersOnOpen = false,
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

    /** The pending scroll to the form's error: one at a time, and none outlives the modal (SEL-FIX1). */
    let formErrorScroll: ReturnType<typeof setTimeout> | null = null;
    /** A save that fails after the modal is gone arms nothing. */
    let destroyed = false;

    /** Brings the inline form error into view once it is drawn (a moment after the error is set). */
    function scrollToFormError(): void {
        if (destroyed) return;
        if (formErrorScroll !== null) clearTimeout(formErrorScroll);
        formErrorScroll = setTimeout(() => {
            formErrorScroll = null;
            document.querySelector('[data-form-error]')?.scrollIntoView({behavior: 'smooth', block: 'center'});
        }, 50);
    }

    onDestroy(() => {
        destroyed = true;
        if (formErrorScroll !== null) clearTimeout(formErrorScroll);
        formErrorScroll = null;
    });

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

    // X5-1 — one confirmation for every provider change that deletes something: new parameters of a parametric provider
    // (its series is invented from them), leaving it, and removing any provider (the events it generated go). The dialog
    // states the server's own count (the dry run `POST /assets/provider/impact`): prices, provider events, transactions that
    // lose the link to a deleted event. Confirming re-enters `saveEdit`, which skips the question while `pendingSaveAssetId`
    // is set, then triggers the re-sync of the regenerated series.
    let providerImpactDialog = $state<{impact: ProviderImpact; from: string; to: string} | null>(null);
    let pendingSaveAssetId: number | null = $state(null);
    let initialProviderParamsJson: string = $state('');

    // I-bis #2 — snapshot of the provider config as loaded from the DB.
    // Used by the ``providerDirty`` derived below to gate the
    // "Save Without Testing?" modal: it must fire **only** when one of
    // these four fields changed vs what was loaded. Non-provider edits
    // (name, description, classification, etc.) skip the modal entirely.
    let initialProviderCode: string = $state('');
    let initialProviderIdentifier: string = $state('');
    let initialProviderIdentifierType: string = $state('TICKER');

    // I.6 + N68 — the confirm modal of a currency change that would delete something.
    let currencyChangeModalOpen = $state(false);
    let currencyChangeImpact = $state<CurrencyChangeImpact | null>(null);
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

    // =========================================================================
    // Enrichers (plan 68, E8a)
    // =========================================================================

    /** The asset's enrichers: code → binding, the order is the priority. */
    let enrichersConfig = $state<Record<string, EnricherBinding>>({});
    /** The list the window opened with: an edit sends `enrichers` only when it differs. */
    let initialEnrichers: Record<string, EnricherBinding> = {};
    let enrichersReadState = $state<Record<string, EnricherReadState>>({});
    /** The user applied a list of their own: «Riconosci» no longer changes it. Always true in edit mode. */
    let enrichersChosen = $state(false);
    let enrichersModalOpen = $state(false);
    let enricherCatalogue = $state<EnricherInfo[]>([]);
    let profileTopics = $state<ProfileVoice[]>([]);
    const recognition = createEnricherRecognitionState();

    function resetEnrichers(data: AssetData['enrichers'] | null, edit: boolean) {
        recognition.cancel();
        enrichersConfig = {...(data?.config ?? {})};
        initialEnrichers = {...enrichersConfig};
        enrichersReadState = {...(data?.state ?? {})};
        enrichersChosen = edit;
        enrichersModalOpen = false;
    }

    /** The identifiers of the form, type → value, as «Riconosci» and the enrichers' window read them. */
    let formIdentifiers = $derived(Object.fromEntries(identifierRows.filter((row) => row.type !== 'OTHER' && row.value.trim() !== '').map((row) => [row.type, row.value.trim()])));

    /** The enrichers that cover the asset's type, and the identifier types they accept between them. */
    let coveringEnrichers = $derived(enricherCatalogue.filter((info) => info.default_priority?.[assetType as keyof typeof info.default_priority] != null));
    let coveringTypes = $derived([...new Set(coveringEnrichers.flatMap((info) => info.accepted_identifier_types))]);

    /** The price assignment as «Riconosci»'s seed (ENR-2): the enricher of the same code is asked first with it, its
     *  parameters too (Borsa Italiana's `codice_fondo`), and its symbol is the ticker a found one may enter by. */
    let priceSeed = $derived(hasProvider && providerCode && providerIdentifier.trim() ? {code: providerCode, identifier_type: providerIdentifierType, identifier: providerIdentifier.trim(), params: {...(providerParams ?? {})}} : null);

    /** What «Riconosci» asks with: at creation a whole ISIN is needed; for an asset that exists any identifier a covering
     *  enricher accepts, the price assignment's too (ENR-1, R1; ENR-2). */
    let recognitionInput = $derived({assetType, identifiers: formIdentifiers, priceProviderCode: hasProvider ? providerCode : null, seed: priceSeed, ...(editMode ? {acceptedTypes: coveringTypes} : {})});

    // At creation «Riconosci» starts by itself with a whole ISIN (PROF, rounds 18 and 21); never in the tour's preview.
    // A question already asked is not asked again (enricherRecognition).
    $effect(() => {
        if (!open || editMode || tourPreview) return;
        const input = recognitionInput;
        untrack(() => {
            if (recognition.start(input)) loadEnricherCatalogues();
        });
    });

    // For an asset that exists it starts when its enrichers' window opens, once the catalogue says what the enrichers
    // accept (ENR-1, R1): the same question once per opening of the asset window, not at every opening of the window.
    // At creation the window's first opening asks too, when nothing was asked yet (ENR-2, E2-1: a symbol picked from
    // Yahoo's search, no ISIN): opening it is a deliberate gesture, a key typed is not
    $effect(() => {
        if (!open || tourPreview || !enrichersModalOpen || !coveringEnrichers.length) return;
        const input = {...recognitionInput, acceptedTypes: coveringTypes};
        const edit = editMode;
        untrack(() => {
            if (edit || recognition.status === 'idle') recognition.start(input);
        });
    });

    // What «Riconosci» proposes is the list until the user applies one of their own
    $effect(() => {
        const proposal = recognition.proposal;
        if (editMode || untrack(() => enrichersChosen)) return;
        untrack(() => (enrichersConfig = proposal));
    });

    /**
     * The catalogues the enrichers' window and the line under the header need: read once, when «Riconosci» starts or the
     * window opens, never just because the asset window opened.
     */
    let enricherCataloguesAsked = false;
    function loadEnricherCatalogues() {
        if (enricherCataloguesAsked) return;
        enricherCataloguesAsked = true;
        void zodiosApi.list_enrichers_api_v1_assets_enrichers_get().then(
            (catalogue) => (enricherCatalogue = ((catalogue as {enrichers?: EnricherInfo[]} | undefined)?.enrichers ?? []) as EnricherInfo[]),
            () => (enricherCataloguesAsked = false),
        );
        void loadProfileCatalogue().then(
            (voices) => (profileTopics = voices ?? []),
            () => (profileTopics = []),
        );
    }

    function openEnrichers() {
        loadEnricherCatalogues();
        enrichersModalOpen = true;
    }

    /** The covering enrichers «Riconosci» asks: configured, accepting an identifier the form holds (the cascade never
     *  answers for the others). */
    let askableEnrichers = $derived(coveringEnrichers.filter((info) => info.configured !== false && info.accepted_identifier_types.some((type) => type in formIdentifiers || type === priceSeed?.identifier_type)).map((info) => info.code));

    /** The codes «Riconosci» is still asking: the askable ones not answered yet. */
    let enrichersSearching = $derived(recognition.status === 'running' ? askableEnrichers.filter((code) => !recognition.recognitions[code]) : []);

    /** The line of «Riconosci» on top of the enrichers' window (ENR-1), once the catalogue is known: in edit mode always
     *  (it says when there is nothing to recognise with), at creation once «Riconosci» has started (the asset window's
     *  own line says the rest). */
    let enrichersLine = $derived(
        coveringEnrichers.length && (editMode || recognition.status !== 'idle')
            ? recognitionLine(
                  recognition.status,
                  recognition.recognitions,
                  coveringEnrichers.map((info) => info.code),
                  recognition.canRecognize(recognitionInput),
                  askableEnrichers,
              )
            : null,
    );

    /** The line under the header: what «Riconosci» found. Only at creation, once it has run. */
    let enrichersBanner = $derived.by((): EnrichersBanner | null => {
        if (editMode) return null;
        if (recognition.status === 'running') return {state: 'running', text: $t('assets.modal.enrichersSearching'), reading: 'none', readingText: null};
        if (recognition.status === 'refused') return {state: 'refused', text: $t('assets.modal.enrichersRefused'), reading: 'none', readingText: null};
        if (recognition.status === 'error') return {state: 'error', text: $t('assets.modal.enrichersError'), reading: 'none', readingText: null};
        if (recognition.status !== 'done') return null;
        const codes = Object.keys(enrichersConfig);
        // Found by a ticker alone: not in the list by itself (ENR-1, R2), named so the user checks and adds them
        const byTicker = Object.values(recognition.recognitions)
            .filter((answer) => answer.status === 'found' && !(answer.code in enrichersConfig) && !entersAlone(answer, recognition.trustedTickers))
            .map((answer) => enricherCatalogue.find((info) => info.code === answer.code)?.name ?? answer.name ?? answer.code);
        const tickerText = byTicker.length ? ` ${$t('assets.modal.enrichersTickerOnly', {values: {names: byTicker.join(', ')}})}` : '';
        if (!codes.length) return {state: 'none', text: $t('assets.modal.enrichersNone') + tickerText, reading: 'none', readingText: null};
        const names = codes.map((code) => enricherCatalogue.find((info) => info.code === code)?.name ?? recognition.recognitions[code]?.name ?? code).join(', ');
        // What the automatic «Chiedi» is doing with them (E9b2, the mock's «I loro dati si stanno leggendo adesso»)
        const reading = autoAsk.status === 'running' ? 'running' : autoAsk.status === 'refused' ? 'waiting' : 'none';
        const readingText = reading === 'running' ? $t('assets.modal.enrichersReading') : reading === 'waiting' ? $t('assets.modal.enrichersReadingWaiting') : null;
        return {state: 'found', text: $t('assets.modal.enrichersFound', {values: {count: codes.length, names}}) + tickerText, reading, readingText};
    });

    // =========================================================================
    // Profile (plan 68, E8b2): the «Dati del profilo» row and window, the automatic «Chiedi»
    // =========================================================================

    /** The changes the profile window kept, and the automatic fills: they leave with the save (`profilePatch`). */
    let profilePending = $state<PendingChanges>({});
    /** The automatic fills now in place: a later answer replaces those the user did not touch. */
    let profileAuto = $state<Record<string, PendingVoice>>({});
    /** «Adesso» of an asset that exists: its profile of today, read when the asset window opens in edit mode. */
    let profileCurrent = $state<Record<string, CurrentVoice>>({});
    let profileVoices = $state<ProfileVoice[]>([]);
    let profileModalOpen = $state(false);
    let profileCurrentAsked = false;
    const autoAsk = createProfileAutoAsk(
        (request) => zodiosApi.ask_profile_api_v1_assets_profile_ask_post(request as never) as Promise<AskAnswer>,
        (answer) => {
            const merged = mergeAutoFills(profilePending, profileAuto, answer, profileCurrent);
            profilePending = merged.pending;
            profileAuto = merged.auto;
            loadProfileVoices();
        },
    );

    /** The profile's catalogue: read when something of the profile is shown, never just because the window opened. */
    function loadProfileVoices() {
        void loadProfileCatalogue().then(
            (voices) => (profileVoices = voices ?? []),
            () => undefined,
        );
    }

    function resetProfile() {
        autoAsk.cancel();
        profilePending = {};
        profileAuto = {};
        profileCurrent = {};
        profileModalOpen = false;
        profileCurrentAsked = false;
    }

    /** «Adesso» of the asset being edited: its profile of today, once per opening (the description field shows it). */
    function loadProfileCurrent() {
        const id = editMode ? editData?.id : undefined;
        if (!id || profileCurrentAsked) return;
        profileCurrentAsked = true;
        void readAssetProfile(id, {start: todayIso()}).then(
            (read) => {
                if (read.kind === 'found' && editData?.id === id) profileCurrent = currentFromRead(read.voices);
            },
            () => (profileCurrentAsked = false),
        );
    }

    function openProfile() {
        loadProfileVoices();
        loadProfileCurrent();
        profileModalOpen = true;
    }

    // At creation, once the enrichers are settled («Riconosci» done, or a list the user applied), the automatic «Chiedi»
    // fills the empty voices (PROF §14.8); never on the proposal still growing, never in edit mode or in the preview
    $effect(() => {
        if (!open) return;
        const request = autoAskRequest({editMode, tourPreview, assetType, enrichers: enrichersConfig, settled: recognition.status === 'done' || enrichersChosen});
        if (request) untrack(() => autoAsk.start($state.snapshot(request) as typeof request));
    });

    // A fill whose source left the list goes: the creation would refuse the whole asset
    $effect(() => {
        const config = enrichersConfig;
        untrack(() => {
            const kept = withoutFillsOutside(profilePending, config);
            if (Object.keys(kept).length === Object.keys(profilePending).length) return;
            profilePending = kept;
            profileAuto = Object.fromEntries(Object.entries(profileAuto).filter(([key]) => key in kept));
        });
    });

    let profileSummary = $derived(profileRowSummary(profilePending, profileVoices));
    /** The description field: a view of the profile's description, the one waiting else «Adesso»'s (E9). */
    let descriptionValue = $derived(descriptionShown(profilePending, profileCurrent));
    /** A value the profile window would refuse blocks the save. */
    let profileBlocked = $derived(profileBlocksSave(profilePending, profileVoices));
    let enricherNames = $derived(Object.fromEntries(enricherCatalogue.map((info) => [info.code, info.name])));

    /** Build form snapshot for dirty tracking — single source of truth */
    function buildFormSnapshot(): string {
        return JSON.stringify([
            // The profile's changes count once they are the user's: the automatic fills alone change nothing to discard
            JSON.stringify(userChanges(profilePending, profileAuto)),
            // The enrichers count only once the user chose them: «Riconosci»'s proposal alone changes nothing to discard
            enrichersChosen ? JSON.stringify(Object.entries(enrichersConfig)) : null,
            displayName,
            currency,
            assetType,
            iconUrl,
            quoteBaseQuantity,
            active,
            isBenchmark,
            providerUserUrl,
            JSON.stringify(identifierRows.map((r) => [r.type, r.value])),
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
    function handleIdentifierBulkDelete(ids: string[]) {
        pendingIdentifierDeleteIds = [...ids];
        showIdentifierDeleteConfirm = true;
    }

    function confirmIdentifierBulkDelete() {
        const deleteSet = new Set(pendingIdentifierDeleteIds);
        for (const row of identifierRows) if (deleteSet.has(row.id)) markManualField(`identifier_${row.type.toLowerCase()}`);
        identifierRows = identifierRows.filter((r) => !deleteSet.has(r.id));
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
                resetEnrichers(editMode && editData ? (editData.enrichers ?? null) : null, editMode);
                if (editMode && enrichersOnOpen && !tourPreview) openEnrichers();
                resetProfile();
                initialSnapshot = buildFormSnapshot();
                // The description field shows «Adesso»'s description: the profile of today is read at once in edit mode
                if (editMode && editData) loadProfileCurrent();
            });
        } else {
            untrack(() => {
                providerProbe.cancelPending();
                // No work in the background (round 28): the answers in flight are dropped with the window
                recognition.cancel();
                autoAsk.cancel();
            });
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
        prefilledIdentifiers = new Set();
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
        const identifier = searchResultIdentifier(identifierRows, result.identifier_type, result.identifier, result.provider_code ? {code: result.provider_code, acceptedTypes: getAssetProviderAcceptedTypes(result.provider_code)} : null);
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
        // OTHER is an asset column, not an assignment type: the provider's own (CoinGecko's COINGECKO_ID, P3). The search
        // loaded the provider list when it opened; were it still empty, ProviderAssignmentSection sets the only type a
        // provider accepts
        providerIdentifierType = searchResultAssignmentType(result.identifier_type, getAssetProviderAcceptedTypes(result.provider_code));
        providerNoProvider = false;
        // Carry over provider_params from search result (e.g. language, currency): the provider's own take priority,
        // the result's currency is the fallback.
        providerParams = searchResultProviderParams(result.provider_params, result.currency, getAssetProviderParamKeys(result.provider_code));
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
    async function fetchAndCompareMetadata(scope: ComparisonScope, origin: 'manual' | 'selection' = 'manual') {
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
            const {actions, differences} = compareMetadata(
                meta.patch_data,
                comparisonSnapshot(),
                scope,
                manuallyChanged,
                {
                    name: $t('common.name'),
                    type: $t('common.type'),
                    currency: $t('common.currency'),
                    icon: $t('common.icon'),
                    quoteBase: $t('assets.modal.quoteBaseQuantity'),
                    quoteBaseNote: (source) => {
                        const note = quoteBaseNote(source, providerName);
                        return note ? $t(note.key, {values: note.values}) : undefined;
                    },
                },
                lineSuggestion,
            );
            for (const action of actions) applyComparisonAction(action);

            // --- RESULTS ---
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
            } else {
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

    /** Per-section "Ask Provider" — compares only the given section (the identifiers: plan 68 E9 left them alone) */
    function handleAskProviderSection(section: Exclude<ComparisonScope, 'all'>) {
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
            iconUrl: iconUrl ?? '',
            quoteBaseQuantity,
        };
    }

    /** Apply one write of a metadata comparison and mark its field auto-filled. */
    function applyComparisonAction(action: ComparisonAction) {
        switch (action.kind) {
            case 'fill':
                setFieldValue(action.field, action.value);
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
                case 'icon_url':
                    // The provider's logo (project 76, P3)
                    iconUrl = value || null;
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
        if (tourPreview || !isValid || profileBlocked) return;
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
            scrollToFormError();
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
        //   (a) **currency change** (N68): never refused. ``saveEdit`` asks the server's dry run first and,
        //       when the change would delete something, opens ``AssetCurrencyChangeModal`` and returns without
        //       throwing; if the dry run itself fails, the error lands in the inline banner like any other.
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
            scrollToFormError();
        }
        saving = false;
    }

    /** The form's values, as the save requests are built from them (./assetPayload.ts). */
    function formFields(): AssetFormFields {
        return {
            displayName,
            currency,
            assetType,
            iconUrl,
            quoteBaseQuantity,
            active,
            isBenchmark,
            userUrl: providerUserUrl,
            identifierRows,
            enrichers: $state.snapshot(enrichersConfig),
            profile: profilePatch(withoutFillsOutside($state.snapshot(profilePending) as PendingChanges, enrichersConfig)),
        };
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
        // Created: what «Riconosci» and the automatic «Chiedi» still have in flight is dropped (round 28)
        recognition.cancel();
        autoAsk.cancel();
        invalidateAssetProfile(assetId);
        naLog(`created asset #${assetId} "${displayName.trim()}" type=${assetType} currency=${currency} qbq=${createItem.quote_base_quantity} · identifiers: ${identifiersSummary()} · provider=${hasProvider ? providerCode : 'none'}`);

        // Upsert the new asset into the shared cache so other pages
        // (transactions cell, AssetCard, AssetTable, …) reflect the entry
        // immediately. The BE response only carries `asset_id`; we merge the
        // fields the FE just submitted (no extra round-trip).
        // The asset's own fields only: its enrichers and its profile are not the shared asset cache's
        const {enrichers: _enrichers, profile: _profile, ...cachedCreate} = createItem as Record<string, unknown>;
        mergeAssets([{id: assetId, ...cachedCreate}]);

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

    async function saveEdit(assetId: number) {
        // X5-1 — a change of provider, of its parameters, or its removal is first measured by the server (a dry run that
        // writes nothing): when it would delete something, the user is told how much and confirms; when it would delete
        // nothing, or the measure fails, the save goes on and the server judges the real call. Confirming re-enters here
        // with `pendingSaveAssetId` set, which skips the question.
        await ensureAssetProvidersCached();
        if (!pendingSaveAssetId) {
            const paramsChanged = !!initialProviderParamsJson && JSON.stringify(providerParams ?? null) !== initialProviderParamsJson;
            let impact: ProviderImpact | null = null;
            if (providerNoProvider && initialProviderCode) {
                impact = await loadProviderImpact(assetId, {action: 'remove'});
            } else if (!providerNoProvider && hasProvider && initialProviderCode && (providerCode !== initialProviderCode || paramsChanged)) {
                impact = await loadProviderImpact(assetId, {action: 'assign', item: buildProviderAssignItem(assetId, providerAssignment())});
            }
            if (impact) {
                pendingSaveAssetId = assetId;
                providerImpactDialog = {
                    impact,
                    from: getAssetProviderName(initialProviderCode) || initialProviderCode,
                    to: getAssetProviderName(providerCode) || providerCode,
                };
                return; // wait for the confirmation; the dialog re-invokes saveEdit()
            }
        }

        // Step 1: Patch asset (the profile's changes ride along as `profile`)
        const patchItem = buildPatchItem(assetId, formFields(), initialEnrichers);
        const patchPayload = [patchItem];

        // N68 — a currency change is never refused, but the PATCH that makes it deletes, in the same call, the asset's prices and
        // its events that are not SPLITs, and disconnects the transactions linked to them (the SPLITs stay). So the server's
        // dry run comes first: when something would go, the user is told how much and confirms (the modal sends the PATCH);
        // when nothing would, the PATCH goes on its own. The dry run is a gate: when it fails the save fails, nothing is sent.
        const storedCurrency = editData?.currency;
        if (storedCurrency && currency !== storedCurrency) {
            const impact = await loadCurrencyChangeImpact(assetId, storedCurrency, currency);
            if (hasSomethingToLose(impact)) {
                currencyChangeImpact = impact;
                currencyChangePatchPayload = patchItem;
                currencyChangeProviderAssigned = hasProvider && !providerNoProvider;
                currencyChangeModalOpen = true;
                return; // abort save — the modal sends the PATCH on confirm, or the user cancels
            }
        }

        // Lane 65: the PATCH is all or nothing and answers 200 either way. Not `committed` → nothing was saved: the sentence of
        // the first issue (the INDEX block, a name another asset has, …) lands in the inline banner, in the interface language.
        assertPatchCommitted(await zodiosApi.patch_assets_bulk_api_v1_assets_patch(patchPayload as any), $t, $t('assets.modal.saveFailed'));

        // PATCH succeeded — sync the patched fields into the shared cache so
        // every consumer (transactions cell, AssetCard, AssetTable, …) sees
        // the new icon/name/etc. without a manual reload. The BE response
        // only carries the per-item results; we merge the fields
        // the FE just submitted.
        const {enrichers: _enrichers, profile: _profile, ...cachedPatch} = patchItem as unknown as Record<string, unknown>;
        mergeAssets([{id: assetId, ...cachedPatch}]);
        // The profile may have changed (its row, the enrichers' read): the pages read it again
        invalidateAssetProfile(assetId);

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
                scrollToFormError();
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
                scrollToFormError();
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
                description={descriptionValue}
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
                ondescriptioninput={(text) => (profilePending = withDescription(profilePending, profileCurrent, text))}
                enricherCount={Object.keys(enrichersConfig).length}
                {enrichersBanner}
                onenrichers={tourPreview ? undefined : openEnrichers}
            />

            <!-- More Info (collapsible — Identifiers) -->
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
                        <AssetModalIdentifiers bind:rows={identifierRows} {hasProvider} {askingProvider} onmanualedit={markManualField} onaskprovider={() => handleAskProviderSection('identifiers')} onbulkdelete={handleIdentifierBulkDelete} />
                    </div>
                {/if}
            </div>

            <AssetModalProvider
                bind:expanded={providerExpanded}
                bind:noProvider={providerNoProvider}
                bind:providerCode
                savedProviderCode={editMode ? initialProviderCode : ''}
                bind:identifier={providerIdentifier}
                bind:identifierType={providerIdentifierType}
                bind:providerParams
                {providerUrl}
                probeState={providerProbe}
                testStatus={providerTestStatus}
                {saving}
                onreconcile={reconcileProviderContext}
            />

            <!-- The profile's data (plan 68, E8b2): a window over this one; what it keeps leaves with the save -->
            <AssetModalProfileRow summary={profileSummary} onopen={openProfile} disabled={tourPreview} />

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

    <AssetModalFooter bind:active bind:isBenchmark {saving} isValid={isValid && !profileBlocked} {tourPreview} {editMode} oncancel={handleClose} onsave={handleSave} />
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

<!-- X5-1 — Confirmation: a provider change that deletes prices or provider events, with the server's own count -->
<ConfirmModal
    open={providerImpactDialog !== null}
    title={providerImpactDialog ? $t(IMPACT_DIALOG[providerImpactDialog.impact.kind].title) : ''}
    message={providerImpactDialog
        ? $t(IMPACT_DIALOG[providerImpactDialog.impact.kind].message, {
              values: {...impactValues(providerImpactDialog.impact, $t, $currentLanguage), from: providerImpactDialog.from, to: providerImpactDialog.to},
          })
        : ''}
    confirmText={providerImpactDialog ? $t(IMPACT_DIALOG[providerImpactDialog.impact.kind].confirm) : ''}
    cancelText={$t('common.cancel')}
    danger={true}
    testId={providerImpactDialog ? IMPACT_DIALOG[providerImpactDialog.impact.kind].testId : 'asset-provider-impact-confirm'}
    onConfirm={() => {
        providerImpactDialog = null;
        const aid = pendingSaveAssetId;
        // pendingSaveAssetId stays non-null so the guard in saveEdit() skips the question on the second pass and
        // proceeds to PATCH + assign/remove + sync.
        if (aid !== null) {
            saveEdit(aid).catch((err) => {
                console.error('saveEdit after the provider-impact confirmation failed:', err);
                toasts.error($t('common.errorOccurred'));
                pendingSaveAssetId = null;
            });
        }
    }}
    onCancel={() => {
        providerImpactDialog = null;
        pendingSaveAssetId = null;
    }}
    zIndex={zIndex + 20}
/>

<!-- Provider Comparison Modal -->
<!-- The enrichers' window over the asset window (plan 68, E8a): it hands the list back, saved with the asset -->
<!-- The profile window over the asset window (plan 68, E8b2): «Tieni le modifiche» hands the changes back here -->
{#if profileModalOpen}
    <ProfileEditModal
        bind:open={profileModalOpen}
        assetName={displayName}
        mode="keep"
        assetId={editMode ? (editData?.id ?? null) : null}
        askTarget={editMode ? null : {asset_type: assetType, enrichers: enrichersConfig}}
        catalogue={profileVoices}
        current={profileCurrent}
        pending={profilePending}
        sourceNames={enricherNames}
        zIndex={zIndex + 30}
        onkeep={(pending) => {
            profilePending = pending;
            profileModalOpen = false;
        }}
        oncancel={() => (profileModalOpen = false)}
    />
{/if}

{#if enrichersModalOpen}
    <AssetEnrichersModal
        bind:open={enrichersModalOpen}
        asset={{name: displayName, assetType, identifiers: formIdentifiers}}
        config={enrichersConfig}
        readState={enrichersReadState}
        catalogue={enricherCatalogue}
        profileCatalogue={profileTopics}
        recognitions={recognition.recognitions}
        searching={enrichersSearching}
        proposal={recognition.proposal}
        adopt={editMode ? Object.keys(enrichersConfig).length === 0 : !enrichersChosen}
        line={enrichersLine}
        price={priceSeed ? {name: getAssetProviderName(priceSeed.code), identifier: priceSeed.identifier} : null}
        trustedTickers={recognition.trustedTickers}
        zIndex={zIndex + 30}
        onapply={(config) => {
            enrichersConfig = config;
            enrichersChosen = true;
            enrichersModalOpen = false;
        }}
        oncancel={() => (enrichersModalOpen = false)}
    />
{/if}

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

<!-- I.6 + R3-3 Policy D + N68 — confirm modal of a currency change that deletes market data. Opened by the dry run of saveEdit. -->
<AssetCurrencyChangeModal
    bind:open={currencyChangeModalOpen}
    impact={currencyChangeImpact}
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
        currencyChangeImpact = null;
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
