<script lang="ts">
    /**
     * AssetSetRiskPanel — the laboratory.
     *
     * This panel used to open on `assets.slice(0, 100)`: a hundred instruments,
     * a ten-thousand-cell matrix with its numbers already suppressed, and no
     * way back except ninety-odd clicks on an X. The system made a bad choice
     * on the user's behalf and then hid the undo.
     *
     * What changed:
     *
     * - the opening set is **remembered**, then **owned**, then **small** — see
     *   `resolveInitialSelectionWithSource`; the hundred survives only as the API's
     *   ceiling;
     * - three quick actions and a holdings command make a large set reachable
     *   *and* escapable, and a "+" — with its own search and type and currency
     *   filters — adds any number of assets in one go;
     * - Risk's eligibility engine decides which selected assets the analysis can
     *   use in the period; the others stay in the selection as greyed chips, with
     *   the engine's reason, and are left out of the requests (`analysedIds`);
     * - the broker control stopped pretending to be a filter. It was never one:
     *   it replaced the selection wholesale. It is now a command beside the quick
     *   actions — "All mine", or one broker — that loads what is held and then
     *   leaves the selection to the user (see `runHoldingsPreset`).
     *
     * **No amount of money appears anywhere on this page.** Not in this panel,
     * not in the levels mounted below it. An asset set has no weights, so any
     * euro figure would be an arithmetic claim about a portfolio the user never
     * described. Percentages and coefficients only.
     *
     * WHY THE LEGACY PANEL IS NO LONGER MOUNTED HERE, and the one thing its
     * removal did take away. `RiskAnalysisPanel` gates each of its eight sections on a
     * capability the backend advertises for the scope (its `supports*`
     * derivations, each a `hasRiskCapability(catalog, code, scope.kind, mode)`), and on
     * `asset_set` the backend advertises **two** analytics: `correlation` and
     * `stress`. So on this page the legacy contributed exactly two analytics, and
     * both were defects:
     *
     *   - a **second** correlation matrix, identical to the one above it, which
     *     put two `risk-correlation-heatmap` nodes in one document and made
     *     every selector inside it ambiguous under Playwright strict mode;
     *   - the **hypothetical shock**, which `03-mappa-livelli-pagine` §3.3
     *     forbids here: without weights it rewrites its own input in a different
     *     shape and calls the result a scenario.
     *
     * Its historical replay — the one rung this page *is* allowed to show — was
     * unreachable from here anyway: the block holding `risk-replay-controls`
     * sits behind `{#if scope.kind === 'asset'}`, inside `{#if supportsStress}`.
     * It is named by the testid it contains, not by its guard, because the same
     * guard text also wraps the stress controls just above it. The page showed
     * the forbidden rung and hid the permitted one, which is what
     * `AssetSetReplaySection` now corrects.
     *
     * 🔴 The component itself is **not** deleted: `AssetRiskScenariosView`
     * still mounts it for Asset Detail, which `03` parks in beta and keeps out
     * of this redesign. What left is one mount, not the code.
     *
     * 🔴 **What the removal did take away (R2-128)**: the legacy also carried this
     * page's only *price and exchange-rate* sync (`risk-sync-button` opening a
     * `PageSyncModal`). The page's own sync refreshes prices only, so for two
     * rounds nothing here could refresh the rates a converted series stands on.
     * It was not a defect, it was a loss — the first reading of this docstring
     * checked whether the removed code left anything *orphaned* and missed that a
     * *capability* had become unreachable. The sync is back, scoped to the
     * selection: after an accepted run every section re-reads its base, and the
     * replay forgets an answer computed on the prices just replaced. Since F-3b its
     * button is the page toolbar's — one sync per page, where the grid tab keeps its
     * own — and it reaches this panel's modal through `openSync`, with `canSync`
     * telling the page when there is nothing to sync.
     */
    import {untrack} from 'svelte';
    import {AlertTriangle, Briefcase, CheckCheck, ChevronDown, FlipHorizontal, Info, RefreshCw, Square, Wallet, X} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import {singleValue} from '$lib/risk/riskTypes';
    import {currentLanguage} from '$lib/stores/app/language';
    import {fetchReport} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {assetStoreVersion, ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {brokerStoreVersion, ensureBrokersLoaded, getAccessibleBrokers} from '$lib/stores/reference/brokerStore';
    import {ensureFxRoutesLoaded, fxRoutesVersion, getConfiguredPairSlugs} from '$lib/stores/reference/fxRoutesStore';
    import {invalidateRisk} from '$lib/stores/risk/riskStore.svelte';
    import AssetSetCorrelationSection from './AssetSetCorrelationSection.svelte';
    import AssetSetComparisonLevels from './AssetSetComparisonLevels.svelte';
    import AssetSetReplaySection from './AssetSetReplaySection.svelte';
    import AssetChip from './AssetChip.svelte';
    import BenchmarkSelect from './BenchmarkSelect.svelte';
    import LabAssetPicker from './LabAssetPicker.svelte';
    import LabPopover from './LabPopover.svelte';
    import type {RiskBenchmarkState} from '$lib/stores/risk/riskBenchmarkStore.svelte';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {applyBulkAction, labBenchmarkId, MAX_SELECTED_ASSETS, readPersistedSelection, resolveInitialSelectionWithSource, writePersistedSelection, type BulkAction, type SelectionSource} from './assetSetSelection';
    import {dayFormatter, describeEligibility, eligibilityBatches, EMPTY_VERDICTS, fitPeriodOffer, isSelectable, mergeEligibilityAnswers, type DayRange, type EligibilityView, type EligibilityVerdicts} from './eligibility';
    import {buildSyncTargets} from './syncTargets';

    interface AssetOption {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        provider_code?: string | null;
        active?: boolean;
        /** Transactions across every broker the user can see: the fallback's ranking. */
        tx_count?: number;
    }

    interface Props {
        assets: AssetOption[];
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        /**
         * Called after an **accepted** sync, so the page can refresh what it holds
         * outside this panel (the grid's price series). An omission is never read as
         * acceptance: a run the user did not start refreshes nothing.
         */
        onsynced?: () => void | Promise<void>;
        /**
         * Whether the selection has anything to sync, mirrored for the page: the sync
         * button lives in the page's toolbar (one sync per page, V1) and must not offer
         * a run over an empty selection.
         */
        canSync?: boolean;
        /**
         * Move the page's period — the toolbar's — to the one the engine suggests for the
         * selection. The period belongs to the page, so the panel can only ask for it.
         */
        onfitperiod?: (range: DayRange) => void;
    }

    let {assets, dateStart, dateEnd, targetCurrency, onsynced, canSync = $bindable(false), onfitperiod}: Props = $props();

    let selectedAssetIds = $state<number[]>([]);
    let brokerAssetsLoading = $state(false);
    let brokerLoadFailed = $state(false);
    /** The last holdings command found nothing held, and left the selection alone. */
    let brokerLoadEmpty = $state(false);
    let presetOpen = $state(false);
    let seedInitialized = false;
    /** The opening selection is waiting for the holdings report (rung 2 of the ladder). */
    let seeding = $state(false);
    /** The user changed the selection by hand: a late opening seed must not overwrite that. */
    let selectionTouched = false;
    let selectionSource = $state<SelectionSource | null>(null);
    let brokerRequestGeneration = 0;

    /**
     * R2-128 — the price and exchange-rate sync, scoped to the selection.
     *
     * The same rule `RiskPanelHeader` applies on the single-scope pages, through
     * the shared `buildSyncTargets`: the selection's prices, plus every configured
     * pair that converts one of them into the target currency.
     */
    let syncOpen = $state(false);
    let syncGeneration = $state(0);
    let syncTargets = $derived.by(() => {
        void $assetStoreVersion;
        void $fxRoutesVersion;
        return buildSyncTargets(selectedAssetIds, targetCurrency, getAssetInfo, getConfiguredPairSlugs());
    });

    /**
     * This page has three controllers, one per section, so there is no single
     * `handleSynced` to call. What they need is the generation, handed to every
     * section as its `refreshVersion`: each re-reads its base, and the replay also
     * forgets its answer (see `AssetSetReplaySection`). No controller listens to
     * the risk cache itself, so dropping the cache alone would leave every section
     * on its pre-sync answer.
     *
     * The cache is already gone by the time this runs: the sync requests are
     * portfolio mutations (`isPortfolioAffectingMutation`), and `riskStore`
     * registers `invalidateRisk` as their listener. The explicit call mirrors the
     * controller's own `handleSynced`, so this refresh does not depend on how those
     * URLs happen to be classified.
     *
     * 🔴 **The page refreshes first, the sections after.** The page's `onsynced`
     * re-reads its price series, which reassigns its `assets` list several times.
     * Its live-price poll used to re-run on every one of those reassignments — each
     * run a write (`POST /assets/prices/current`) and so a portfolio mutation that
     * drops every risk answer in flight — until it was keyed on the set of ids
     * (`liveAssetIdsKey` in `assets/+page.svelte`). The order outlived the reason it
     * was introduced for, and is kept on purpose: it costs nothing, and it keeps the
     * sections clear of whatever that refresh sets off if the poll ever regresses,
     * since `loadBase` asks again only once. `finally`, so a page refresh that fails
     * still leaves the sections re-asked on the new data.
     *
     * A run that was not accepted changed nothing, so it refreshes nothing.
     */
    async function handleSynced(detail: {accepted: boolean}): Promise<void> {
        if (detail?.accepted !== true) return;
        try {
            await onsynced?.();
        } finally {
            invalidateRisk();
            syncGeneration += 1;
        }
    }

    $effect(() => {
        canSync = syncTargets.assets.length > 0 || syncTargets.fxPairs.length > 0;
    });

    /** The page toolbar's sync, on this tab: the selection's prices and rates, through this panel's modal. */
    export function openSync(): void {
        if (canSync) syncOpen = true;
    }

    /**
     * The page toolbar's reload, on this tab: every section asks its base again.
     * Nothing was synced, so the page's own series are left alone — this is the
     * refresh half of `handleSynced`, without the sync it follows.
     */
    export function reload(): void {
        invalidateRisk();
        syncGeneration += 1;
    }

    let brokers = $derived.by(() => {
        void $brokerStoreVersion;
        return getAccessibleBrokers();
    });
    let selectedAssets = $derived(selectedAssetIds.map((assetId) => assets.find((asset) => asset.id === assetId)).filter((asset): asset is AssetOption => Boolean(asset)));

    /**
     * Risk's verdict on every asset of the catalogue for the period
     * (`POST /api/v1/risk/eligibility`, see `eligibility.ts`). Asked once for the
     * whole list, again when the list, the period or the currency changes — after a
     * short pause, so a date being typed asks once — and a superseded answer is
     * dropped. A failed call leaves no verdict, and no verdict means selectable:
     * the engine can make the lab stricter, never emptier.
     */
    let verdicts = $state<EligibilityVerdicts>(EMPTY_VERDICTS);
    let eligibilityFailed = $state(false);
    let eligibilityGeneration = 0;
    const ELIGIBILITY_DEBOUNCE_MS = 300;
    let catalogueKey = $derived(
        assets
            .map((asset) => asset.id)
            .sort((left, right) => left - right)
            .join(','),
    );

    $effect(() => {
        const ids = catalogueKey ? catalogueKey.split(',').map(Number) : [];
        const period = {start: dateStart, end: dateEnd};
        const currency = targetCurrency;
        const generation = ++eligibilityGeneration;
        if (ids.length === 0 || !period.start) {
            verdicts = EMPTY_VERDICTS;
            return;
        }
        const timer = setTimeout(() => void loadEligibility(generation, ids, period, currency), ELIGIBILITY_DEBOUNCE_MS);
        return () => clearTimeout(timer);
    });

    /** One question to the engine for a set of ids, split in the batches it accepts. */
    async function requestEligibility(ids: number[], period: {start: string; end: string}, currency: string): Promise<EligibilityVerdicts> {
        const answers = await Promise.all(eligibilityBatches(ids).map((batch) => zodiosApi.asset_eligibility_api_v1_risk_eligibility_post({asset_ids: batch, date_range: {start: period.start, end: period.end || null}, target_currency: currency})));
        return mergeEligibilityAnswers(answers);
    }

    async function loadEligibility(generation: number, ids: number[], period: {start: string; end: string}, currency: string): Promise<void> {
        try {
            const next = await requestEligibility(ids, period, currency);
            if (generation !== eligibilityGeneration) return;
            verdicts = next;
            eligibilityFailed = false;
        } catch (error) {
            if (generation !== eligibilityGeneration) return;
            console.error('[Risk] Eligibility engine unavailable:', error);
            verdicts = EMPTY_VERDICTS;
            eligibilityFailed = true;
        }
    }

    /** The verdicts in the reader's language, for the "+" and the chips. */
    let eligibilityView = $derived.by(() => {
        const formatDay = dayFormatter($currentLanguage);
        const view = new Map<number, EligibilityView>();
        for (const [assetId, item] of verdicts.items) view.set(assetId, describeEligibility(item, verdicts, targetCurrency, $t, formatDay));
        return view;
    });

    /**
     * The same question for the **selection** alone, parked assets included, for the
     * "use the period in which all have prices" offer. The catalogue's answer cannot
     * serve: its common span is the catalogue's, and an unselected asset with a short
     * history would narrow the period offered to everyone (D1, agreed with Risk). The
     * selection holds at most a hundred ids, so this is one request. A failure only
     * withholds the offer; the verdicts on the chips come from the catalogue's answer.
     */
    let selectionVerdicts = $state<EligibilityVerdicts>(EMPTY_VERDICTS);
    let selectionEligibilityGeneration = 0;
    let selectionKey = $derived([...new Set(selectedAssetIds)].sort((left, right) => left - right).join(','));

    $effect(() => {
        const ids = selectionKey ? selectionKey.split(',').map(Number) : [];
        const period = {start: dateStart, end: dateEnd};
        const currency = targetCurrency;
        const generation = ++selectionEligibilityGeneration;
        if (ids.length === 0 || !period.start) {
            selectionVerdicts = EMPTY_VERDICTS;
            return;
        }
        const timer = setTimeout(async () => {
            try {
                const next = await requestEligibility(ids, period, currency);
                if (generation === selectionEligibilityGeneration) selectionVerdicts = next;
            } catch (error) {
                if (generation !== selectionEligibilityGeneration) return;
                console.error('[Risk] Eligibility of the selection unavailable:', error);
                selectionVerdicts = EMPTY_VERDICTS;
            }
        }, ELIGIBILITY_DEBOUNCE_MS);
        return () => clearTimeout(timer);
    });

    let fitOffer = $derived(fitPeriodOffer(selectionVerdicts, selectedAssetIds));
    let fitDay = $derived(dayFormatter($currentLanguage));
    let fitNames = $derived.by(() => (fitOffer ? fitOffer.recoverable.map((assetId) => selectionLabels.get(assetId) ?? `#${assetId}`).join(', ') : ''));

    /** What the quick actions may bring in: the catalogue without what the engine rules out. */
    let candidates = $derived(assets.filter((asset) => isSelectable(verdicts, asset.id)));

    /**
     * What the sections analyse: the selection without the assets ruled out for the
     * period. Those stay **in the selection**, as greyed chips with the reason, and
     * are only left out of the requests: changing the period — by hand, or through
     * Risk's coming "fit to the common period" — brings them back without anyone
     * having to find them again. The sync still covers them, because an asset with no
     * prices is sometimes an asset that was never synced.
     */
    let analysedIds = $derived(selectedAssetIds.filter((assetId) => isSelectable(verdicts, assetId)));
    let parkedCount = $derived(selectedAssetIds.length - analysedIds.length);
    let atCapacity = $derived(selectedAssetIds.length >= MAX_SELECTED_ASSETS);

    /**
     * The "+" lists the page's own list and never the global asset cache. That is
     * what keeps the two in step: the old picker was backed by the cache and had to
     * be restricted by hand, because an asset chosen from the wider cache entered
     * `selectedAssetIds`, reached the API, and then failed to resolve into a chip
     * here — present in the analysis, invisible in the controls.
     */
    let room = $derived(Math.max(0, MAX_SELECTED_ASSETS - selectedAssetIds.length));

    /**
     * Names for the matrix's axes.
     *
     * Built from the page's own list first, because this panel already holds
     * every display name it put in the selection: no store round-trip, no
     * version token, and no `#id` for anything the reader picked themselves.
     * The store is consulted only for the case the comment above describes —
     * an id remembered from a previous visit that is no longer on the page,
     * present in the analysis and invisible in the controls. Dropping that
     * lookup would have been a quiet regression: the legacy resolved those ids
     * through the store, so they show a name today.
     */
    let selectionLabels = $derived.by(() => {
        void $assetStoreVersion;
        const labels = new Map<number, string>();
        for (const asset of selectedAssets) labels.set(asset.id, asset.display_name);
        for (const assetId of selectedAssetIds) {
            if (labels.has(assetId)) continue;
            const name = getAssetInfo(assetId)?.display_name;
            if (name) labels.set(assetId, name);
        }
        return labels;
    });

    /** Same sources, same order of preference as the labels: the matrix's "by type" ordering reads it. */
    let selectionTypes = $derived.by(() => {
        void $assetStoreVersion;
        const types = new Map<number, string | null | undefined>();
        for (const asset of selectedAssets) types.set(asset.id, asset.asset_type);
        for (const assetId of selectedAssetIds) {
            if (!types.has(assetId)) types.set(assetId, getAssetInfo(assetId)?.asset_type);
        }
        return types;
    });

    /**
     * Same sources again, resolved the way the selection's chips resolve an icon
     * (`AssetChip`): the asset's own, else its type's. The loss table's asset cells read
     * it; an id known to neither source gets no icon and shows its name alone.
     */
    let selectionIcons = $derived.by(() => {
        void $assetStoreVersion;
        const icons = new Map<number, string>();
        for (const asset of selectedAssets) icons.set(asset.id, asset.icon_url || getAssetTypeIconUrl(asset.asset_type));
        for (const assetId of selectedAssetIds) {
            if (icons.has(assetId)) continue;
            const info = getAssetInfo(assetId);
            if (info) icons.set(assetId, info.icon_url || getAssetTypeIconUrl(info.asset_type));
        }
        return icons;
    });

    $effect(() => {
        untrack(() => void ensureBrokersLoaded());
    });

    /**
     * The sync reads two caches it must load itself: the asset cache (for the
     * modal's rows) and the configured FX routes (for the pairs). Neither may be
     * borrowed from a neighbour. On `/assets` nothing else loads the routes — the
     * page fetches the same list into a variable of its own — so without this call
     * the pair set stays empty and the sync silently shrinks back to prices only,
     * which is the loss R2-128 recorded. The asset cache used to be warmed by the
     * old add-asset select, and that is exactly the kind of accident this call
     * stops relying on. Both loaders are idempotent; `RiskAnalysisPanel` does the
     * same.
     */
    $effect(() => {
        untrack(() => void Promise.all([ensureAssetsLoaded(), ensureFxRoutesLoaded()]));
    });

    /**
     * The opening selection — the D19 ladder, `resolveInitialSelectionWithSource`.
     *
     * Rung 1, the last selection, is known at once. Rung 2, what is held on the
     * period's last day, is a portfolio report and arrives later: until it does the
     * card says it is loading rather than "no assets". Anything the user does in
     * the meantime wins, and the late seed is dropped.
     */
    $effect(() => {
        if (seedInitialized || assets.length === 0) return;
        seedInitialized = true;
        const first = resolveInitialSelectionWithSource(assets, readPersistedSelection());
        if (first.source === 'persisted') {
            selectedAssetIds = first.ids;
            selectionSource = first.source;
            return;
        }
        untrack(() => void seedFromHoldings());
    });

    async function seedFromHoldings(): Promise<void> {
        seeding = true;
        const generation = ++brokerRequestGeneration;
        try {
            const held = await heldAssetIds(null, generation);
            if (generation !== brokerRequestGeneration || selectionTouched) return;
            const seed = resolveInitialSelectionWithSource(assets, null, held ?? []);
            selectedAssetIds = seed.ids;
            selectionSource = seed.source;
        } finally {
            seeding = false;
        }
    }

    /** Remember the set, so the next visit starts where this one ended. */
    $effect(() => {
        const ids = selectedAssetIds;
        if (!seedInitialized || seeding) return;
        untrack(() => writePersistedSelection(ids));
    });

    /**
     * The ids held on the period's last day — in one broker, or in every broker the
     * user can see when `brokerId` is `null` — restricted to the page's own list.
     * `null` when the report could not be read; `undefined` when a newer request
     * superseded this one.
     *
     * "Held" is what the report's holdings mean: an open position, quantity above
     * the dust threshold, on `dateEnd`. It is **not** the asset list's `held_by_me`,
     * which means "held today": the two agree only when the period ends today, and
     * the labels keep them apart. `fetchReport` is a portfolio route, but only the
     * holdings' `asset_id`s are read from it — no amount, no weight, no valuation
     * crosses into this page.
     */
    async function heldAssetIds(brokerId: number | null, generation: number): Promise<number[] | null | undefined> {
        const brokerIds = brokerId === null ? undefined : [brokerId];
        // `fetchReport` answers with a report or with `null`, and `null` covers two
        // different facts: a *discard* (the client session or the report cache moved
        // while the request was in flight) and a *failure* (it turns every error into
        // `null` — nothing is ever thrown at this caller). On this page the cache moves
        // on its own: the live-price poll writes today's prices
        // (`POST /assets/prices/current`), that is a portfolio mutation, and
        // `portfolioStore`'s mutation listener drops every report in flight. Read as
        // "no holdings", a null used to wipe the selection in silence. It is asked once
        // more — the policy `loadBase` adopted for the same guard, and the right answer
        // to a transient failure too — and a second null is reported as a failure.
        // Only the holdings are read, so the report is asked without its daily history and
        // allocation history: those two series are what made "All mine" wait, and nothing here
        // reads them. The lighter report is cached under its own key (`|nohist|noalloc`).
        const light = () => fetchReport(brokerIds, dateStart, dateEnd, targetCurrency, false, false, false, false, false);
        let report = await light();
        if (generation !== brokerRequestGeneration) return undefined;
        if (report == null) {
            report = await light();
            if (generation !== brokerRequestGeneration) return undefined;
        }
        if (report == null) return null;
        const onPage = new Set(assets.map((asset) => asset.id));
        const summary = singleValue(report.summary);
        return [...new Set((summary?.holdings ?? []).map((holding) => holding.asset_id))].filter((assetId) => onPage.has(assetId)).sort((left, right) => left - right);
    }

    /**
     * Replace the selection with what is held on the period's last day: in one
     * broker, or — `null` — in every broker the user can see ("All mine").
     *
     * A **command**, like the three quick actions beside it, and no longer a
     * select with a standing value. The select re-applied itself whenever the
     * period or the currency changed, so an asset added by hand after choosing a
     * broker vanished at the next change of dates, with nothing on screen saying
     * why. A command runs once, when it is pressed, and then the selection is
     * the user's again. Nothing held is an answer, not an instruction to empty the
     * table: the command says so and the selection stays as it was.
     *
     * Held assets the engine rules out for the period enter the selection too, as
     * greyed chips (see `analysedIds`): "all mine" means all of them.
     */
    async function runHoldingsPreset(brokerId: number | null): Promise<void> {
        selectionTouched = true;
        const generation = ++brokerRequestGeneration;
        brokerLoadFailed = false;
        brokerLoadEmpty = false;
        brokerAssetsLoading = true;
        try {
            const held = await heldAssetIds(brokerId, generation);
            if (held === undefined) return;
            if (held === null) {
                brokerLoadFailed = true;
                return;
            }
            if (held.length === 0) {
                brokerLoadEmpty = true;
                return;
            }
            selectedAssetIds = held.slice(0, MAX_SELECTED_ASSETS);
        } catch (error) {
            console.error('[Risk] Failed to resolve broker asset set:', error);
            if (generation === brokerRequestGeneration) brokerLoadFailed = true;
        } finally {
            if (generation === brokerRequestGeneration) brokerAssetsLoading = false;
        }
    }

    /**
     * The benchmark the comparison levels measure against, when one applies.
     *
     * Chosen in the shared picker (`BenchmarkSelect`), mounted above the two comparison
     * levels: the developer's rule is that wherever a page measures against a benchmark it
     * can be chosen there, and that the picker opens on the current one. The choice itself
     * still lives in the shared `riskBenchmark` store, so choosing it here chooses it on every
     * risk page — `03-mappa-livelli-pagine` §3.1: two pages comparing against different
     * references stop being comparable.
     *
     * The picker confirms a stored choice against the asset list before it says `set`
     * (`pending` until then), and only a confirmed choice reaches a request
     * (`labBenchmarkId`). A choice that is also one of the analysed assets stays shown, with
     * its ⚠, but is withheld: `RiskAssetSetComparisonOutput` rejects a yardstick that is also
     * one of the measured.
     *
     * 🔴 **The levels mount only once the picker has stopped saying `pending`.** Their
     * controller asks for its base wave the moment it mounts. Mounted earlier, every load
     * with a stored benchmark would ask twice — first without the benchmark, over another
     * window, then with it — and L1° and L3° would show figures that are replaced a moment
     * later. Starting at `pending` keeps them out until the picker reports; with nothing
     * stored it reports `none` while it mounts.
     */
    let benchmarkValue = $state<number | null>(null);
    let benchmarkState = $state<RiskBenchmarkState>('pending');
    let benchmarkId = $derived(labBenchmarkId(benchmarkState, benchmarkValue, analysedIds));

    function runBulkAction(action: BulkAction): void {
        selectionTouched = true;
        selectedAssetIds = applyBulkAction(action, selectedAssetIds, candidates).sort((left, right) => left - right);
    }

    function addAssets(assetIds: readonly number[]): void {
        selectionTouched = true;
        const current = new Set(selectedAssetIds);
        const added = assetIds.filter((id) => !current.has(id)).slice(0, room);
        if (added.length === 0) return;
        selectedAssetIds = [...selectedAssetIds, ...added].sort((left, right) => left - right);
    }

    function removeAsset(assetId: number): void {
        selectionTouched = true;
        selectedAssetIds = selectedAssetIds.filter((id) => id !== assetId);
    }

    function choosePreset(brokerId: number | null): void {
        presetOpen = false;
        void runHoldingsPreset(brokerId);
    }

    /**
     * "My assets" left this row: it read `tx_count_own`, any transaction ever made
     * in the user's brokers, so it also brought back positions sold years ago. Its
     * place is the holdings command beside these three, which reads what is held.
     */
    const BULK_ACTIONS: {action: BulkAction; icon: typeof CheckCheck; key: string}[] = [
        {action: 'all', icon: CheckCheck, key: 'selectAll'},
        {action: 'none', icon: Square, key: 'selectNone'},
        {action: 'invert', icon: FlipHorizontal, key: 'invert'},
    ];

    const QUICK_BUTTON = 'inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-700';
</script>

{#snippet chip(asset: AssetOption, verdict: EligibilityView | undefined)}
    <!-- The shared `AssetChip` (owned here, mounted by the Dashboard's banner too). The help
         cursor goes with the tooltip the caller wraps around a chip that has a verdict. -->
    <AssetChip
        {asset}
        variant={verdict?.level === 'ineligible' ? 'excluded' : verdict?.level === 'warning' ? 'warning' : 'default'}
        help={verdict !== undefined && verdict.level !== 'eligible'}
        testId="risk-selected-asset-{asset.id}"
        data-level={verdict?.level ?? 'unknown'}
        data-reasons={verdict?.codes.join(' ') ?? ''}
    >
        {#snippet trailing()}
            <button
                class="rounded-full p-0.5 hover:bg-gray-200 dark:hover:bg-slate-600"
                onclick={(event) => {
                    // Removing is not asking why: the click must not also pin the chip's tooltip.
                    event.stopPropagation();
                    removeAsset(asset.id);
                }}
                aria-label={$t('common.remove')}
                data-testid="risk-remove-asset-{asset.id}"
            >
                <X size={11} />
            </button>
        {/snippet}
    </AssetChip>
{/snippet}

<div class="space-y-4" data-testid="asset-global-risk-panel">
    <section class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid="risk-asset-set-controls" data-selection-source={selectionSource}>
        {#if fitOffer}
            <!-- The developer's choice: a strip at the top of the card that says the chosen period
                 leaves some selected assets without prices, with the button that fixes it. The
                 period itself belongs to the page's toolbar, so the button asks the page. -->
            <div
                class="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200"
                data-testid="risk-fit-period-banner"
                data-recoverable={fitOffer.recoverable.length}
            >
                <AlertTriangle size={14} class="shrink-0" />
                <span class="min-w-0 flex-1">{$t('risk.assetSet.fitPeriod.banner', {values: {count: fitOffer.recoverable.length}})}</span>
                <Tooltip text={$t('risk.assetSet.fitPeriod.hint', {values: {names: fitNames}})} position="bottom" maxWidth="360px" interactiveChild>
                    <button
                        type="button"
                        class="rounded-md border border-amber-300 bg-white px-2.5 py-1 font-medium text-amber-800 hover:bg-amber-100 dark:border-amber-600 dark:bg-slate-800 dark:text-amber-200 dark:hover:bg-amber-900/40"
                        onclick={(event) => {
                            // Not up to the Tooltip wrapper: its click would pin the hint over the page.
                            event.stopPropagation();
                            if (fitOffer) onfitperiod?.(fitOffer.range);
                        }}
                        data-testid="risk-fit-period-button"
                        data-start={fitOffer.range.start}
                        data-end={fitOffer.range.end}
                    >
                        {$t('risk.assetSet.fitPeriod.button', {values: {start: fitDay(fitOffer.range.start), end: fitDay(fitOffer.range.end)}})}
                    </button>
                </Tooltip>
            </div>
        {/if}
        <!-- Row 1 — what goes on the table: three quick actions and the holdings command, then
             how many assets are in the analysis. The type and currency filters live in the "+":
             beside these buttons they also narrowed them, so "select all" meant "select what the
             filter you forgot about lets through". -->
        <div class="flex flex-wrap items-center gap-2">
            <div class="flex flex-wrap items-center gap-2" data-testid="risk-asset-set-bulk-actions">
                {#each BULK_ACTIONS as { action, icon: Icon, key } (action)}
                    <button type="button" class={QUICK_BUTTON} onclick={() => runBulkAction(action)} disabled={assets.length === 0 || (action === 'all' && atCapacity) || (action === 'none' && selectedAssetIds.length === 0)} data-testid="risk-bulk-{action}">
                        <Icon size={13} />
                        {$t(`risk.assetSet.bulk.${key}`)}
                    </button>
                {/each}

                <LabPopover bind:open={presetOpen} testId="risk-broker-filter-dropdown" panelClass="w-64">
                    {#snippet trigger({open, toggle})}
                        <button type="button" class={QUICK_BUTTON} aria-expanded={open} onclick={toggle} disabled={brokerAssetsLoading} data-testid="risk-broker-filter-button">
                            {#if brokerAssetsLoading}
                                <RefreshCw size={13} class="animate-spin text-libre-green" data-testid="risk-broker-filter-loading" />
                            {:else}
                                <Briefcase size={13} />
                            {/if}
                            {$t('risk.assetSet.bulk.mine')}
                            <ChevronDown size={12} class="transition-transform {open ? 'rotate-180' : ''}" />
                        </button>
                    {/snippet}
                    {#snippet children()}
                        <p class="border-b border-gray-100 px-3 py-2 text-[11px] leading-snug text-gray-500 dark:border-slate-700 dark:text-gray-400">{$t('risk.assetSet.preset.hint')}</p>
                        <div class="p-1">
                            <button type="button" class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] font-medium text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-slate-700" onclick={() => choosePreset(null)} data-testid="risk-broker-option-mine">
                                <span class="flex h-6 w-6 shrink-0 items-center justify-center"><Wallet size={15} class="text-libre-green" /></span>
                                {$t('risk.assetSet.preset.allMine')}
                            </button>
                        </div>
                        {#if brokers.length > 0}
                            <p class="border-t border-gray-100 px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:border-slate-700 dark:text-gray-500">{$t('risk.assetSet.preset.byBroker')}</p>
                            <div class="max-h-60 overflow-y-auto p-1 pt-0">
                                {#each brokers as broker (broker.id)}
                                    <button
                                        type="button"
                                        class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-slate-700"
                                        onclick={() => choosePreset(broker.id)}
                                        data-testid="risk-broker-option-{broker.id}"
                                    >
                                        <BrokerIcon brokerId={broker.id} iconUrl={broker.icon_url ?? null} portalUrl={broker.portal_url ?? null} pluginCode={broker.default_import_plugin ?? null} altText={broker.name} size="sm" />
                                        <span class="min-w-0 flex-1 truncate">{broker.name}</span>
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    {/snippet}
                </LabPopover>
            </div>

            <Tooltip text={$t('risk.assetSet.selectedCountHint')} position="bottom" maxWidth="360px" wrapperClass="ml-auto">
                <span class="cursor-help text-xs text-gray-500 underline decoration-dotted underline-offset-2 dark:text-gray-400" data-testid="risk-selected-count" data-selected={analysedIds.length} data-total={candidates.length} data-parked={parkedCount}>
                    {$t('risk.assetSet.selectedCount', {values: {selected: analysedIds.length, total: candidates.length}})}
                </span>
            </Tooltip>
        </div>

        {#if brokerLoadFailed}
            <p class="mt-2 text-xs text-red-600 dark:text-red-400" data-testid="risk-broker-filter-error">{$t('risk.states.loadFailed')}</p>
        {:else if brokerLoadEmpty}
            <p class="mt-2 text-xs text-amber-600 dark:text-amber-400" data-testid="risk-broker-filter-empty">{$t('risk.assetSet.preset.noneHeld')}</p>
        {/if}
        {#if eligibilityFailed}
            <p class="mt-2 text-xs text-amber-600 dark:text-amber-400" data-testid="risk-eligibility-failed">{$t('risk.assetSet.eligibilityFailed')}</p>
        {/if}

        <!-- Row 2 — what is on the table, and the "+" that adds to it. An asset the engine rules
             out for the period stays here, greyed, with the reason: it is left out of the
             analysis, not out of the selection. -->
        <div class="mt-3 flex flex-wrap items-center gap-2" data-testid="risk-selected-assets">
            {#each selectedAssets as asset (asset.id)}
                {@const verdict = eligibilityView.get(asset.id)}
                {#if verdict && verdict.level !== 'eligible'}
                    <!-- The engine's reason on the whole chip, on hover or on a click anywhere on it
                         (the developer: a small triangle was too small a target). -->
                    <Tooltip text={verdict.texts.join(' · ')} position="top" maxWidth="320px" interactiveChild>
                        {@render chip(asset, verdict)}
                    </Tooltip>
                {:else}
                    {@render chip(asset, verdict)}
                {/if}
            {/each}
            <LabAssetPicker {assets} selected={selectedAssetIds} {room} eligibility={eligibilityView} onadd={addAssets} />
        </div>
        {#if parkedCount > 0}
            <p class="mt-2 text-xs text-gray-500 dark:text-gray-400" data-testid="risk-parked-note">{$t('risk.assetSet.parkedNote', {values: {count: parkedCount}})}</p>
        {/if}
        {#if atCapacity}
            <p class="mt-2 text-xs text-amber-600 dark:text-amber-400">{$t('risk.assetSet.maxAssets')}</p>
        {/if}
        <!-- The benchmark is a parameter of the whole lab, chosen beside the assets it is set
             against (the developer's review, 02/10): today only «What did each of these pay?»
             uses it, for beta, correlation and its dot. Mounted with the card, so a stored
             choice is confirmed before the levels below ask for their data. -->
        <div class="mt-3 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3 dark:border-slate-700" data-testid="risk-asset-set-benchmark-row">
            <span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">{$t('risk.levels.l3.benchmark')}</span>
            <Tooltip text={$t('risk.assetSet.benchmark.help')} position="bottom" maxWidth="320px">
                <span class="inline-flex text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-benchmark-help"><Info size={14} aria-hidden="true" /></span>
            </Tooltip>
            <BenchmarkSelect bind:value={benchmarkValue} bind:state={benchmarkState} measuredAssetIds={analysedIds} measuredHint={$t('risk.assetSet.benchmark.measuredHint')} testid="risk-asset-set-benchmark" />
        </div>
    </section>

    {#if analysedIds.length > 0}
        <AssetSetCorrelationSection assetIds={analysedIds} assetLabels={selectionLabels} assetTypes={selectionTypes} {dateStart} {dateEnd} {targetCurrency} refreshVersion={syncGeneration} />
        {#if benchmarkState !== 'pending'}
            <AssetSetComparisonLevels assetIds={analysedIds} assetLabels={selectionLabels} assetIcons={selectionIcons} {dateStart} {dateEnd} {targetCurrency} {benchmarkId} refreshVersion={syncGeneration} />
        {/if}
        <AssetSetReplaySection assetIds={analysedIds} assetLabels={selectionLabels} {dateStart} {dateEnd} {targetCurrency} refreshVersion={syncGeneration} />
    {:else if seeding}
        <div class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-8 text-center" data-testid="risk-asset-set-seeding">
            <RefreshCw size={20} class="mx-auto animate-spin text-libre-green" />
        </div>
    {:else}
        <div class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-8 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-empty">
            {$t('risk.states.noAssets')}
        </div>
    {/if}
</div>

<PageSyncModal bind:open={syncOpen} {dateStart} {dateEnd} assets={syncTargets.assets} fxPairs={syncTargets.fxPairs} onsynced={handleSynced} onclose={() => (syncOpen = false)} />
