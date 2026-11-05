<!--
  PortfolioToolbar — the controls of the portfolio view: period, currency, broker filter, AI Export, Refresh (which becomes
  «Updates paused» while the live prices wait for the user, F-4), and the tabs below them (Y6-7, delivery 2, checkpoint 9e; moved out of `PortfolioView.svelte`, markup and `data-testid`s
  kept).

  It wraps `PageToolbar`, so the layout state (`layoutMode`, `filtersStacked`, the labels that hide first) and the picker's
  measured width stay inside. The view keeps what the controls change — the date range controller, the currency, the broker
  selection and what a refresh does — and is told through callbacks.

  AI Export: the menu, its catalogue and its toasts are plumbing every page shares, so they live here; what differs is only
  which export it is (`aiExport.domain`, its memory key, its default choice) and the request's context, which the view gives.
-->
<script lang="ts">
    import {onMount, type ComponentProps, type Snippet} from 'svelte';
    import {_} from '$lib/i18n';
    import {Pause, RefreshCw} from 'lucide-svelte';
    import AiExportMenu from '$lib/features/ai-export/AiExportMenu.svelte';
    import {prepareAiExport, type AiExportRequestContext, type PreparedAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import type {AiExportOptionsSelection} from '$lib/features/ai-export/aiExportOptions';
    import {aiExportCatalogLoader, emptyAiExportCompatibility, type AiExportCatalogCompatibilityResult} from '$lib/features/ai-export/catalog/compatibility';
    import {buildAiExportMenuLabels, getAiExportErrorMessage, getAiExportSuccessMessages} from '$lib/features/ai-export/ui';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {STATUS_TONES} from '$lib/theme/toneClasses';
    import type {ActivePollingState} from '$lib/features/live-updates/activePolling';
    import type {DateRangeController} from '$lib/features/dashboard/dateRangeController.svelte';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import BrokerFilterSelect from './BrokerFilterSelect.svelte';
    import type {PortfolioScopeProfile} from './portfolioScopeProfile';

    type TabItems = ComponentProps<typeof PageToolbar>['tabs'];

    /** Which AI export the menu offers, and the context of its request. `context` throws when the page cannot ask yet. */
    interface AiExportConfig {
        domain: ComponentProps<typeof AiExportMenu>['domain'];
        memoryKey: ComponentProps<typeof AiExportMenu>['memoryKey'];
        defaultSelectionId: ComponentProps<typeof AiExportMenu>['defaultSelectionId'];
        /** The page cannot ask yet (its brokers are not known). */
        disabled: boolean;
        context: () => AiExportRequestContext;
    }

    interface Props {
        /** What the two pages do not share: test ids, thresholds, the order of the buttons, the broker filter. */
        profile: PortfolioScopeProfile;
        tabs: TabItems;
        activeTab: string;
        ontabchange: (tabId: string) => void;
        dateRangeCtl: DateRangeController;
        /** The currency of the figures the user asks. */
        targetCurrency: string;
        /** The user's default currency: the selector's placeholder and what «create forex» starts from. */
        baseCurrency: string;
        /** The user picked a currency. */
        oncurrencychange: () => void;
        /** «Create forex» was pressed in the selector, with the pair to start from (`EUR-`). */
        oncreateforex: (slug: string) => void;
        brokers: BrokerLike[];
        selectedBrokerIds: number[];
        /** Some but not all brokers are selected. */
        brokerFilterActive: boolean;
        onselectbrokers: (ids: number[]) => void;
        /** The prices stopped following because nobody used the page for two minutes (FB-28). */
        liveState: ActivePollingState;
        aiExport: AiExportConfig;
        onrefresh: () => void;
        /** The page's own buttons, first among the actions (the broker's Edit and Share). */
        actionsBefore?: Snippet<[{showActionLabels: boolean}]>;
    }

    let {profile, tabs, activeTab, ontabchange, dateRangeCtl, targetCurrency = $bindable(), baseCurrency, oncurrencychange, oncreateforex, brokers, selectedBrokerIds, brokerFilterActive, onselectbrokers, liveState, aiExport, onrefresh, actionsBefore}: Props = $props();

    /** Mirrors the DateRangePicker's own effective 2-row max-width, so the Currency+Broker row
     *  below it can be capped to the SAME pixel value when filtersStacked — otherwise it
     *  stretches to the full (wider) filters column instead of matching the picker's box.
     *  MUST start non-undefined (matches DateRangePicker's own maxWidthTwoRow default, 390) —
     *  Svelte forbids bind:key={undefined} when the child prop has a declared fallback. */
    let pickerMaxWidth = $state<number>(390);

    /** AI export state — dropdown open/position handled internally by AiExportMenu. */
    let aiExportCompatibility = $state<AiExportCatalogCompatibilityResult>(emptyAiExportCompatibility());
    let aiExportCatalogLoading = $state(true);
    let aiExportCatalogFailed = $state(false);
    const aiExportLabels = $derived(buildAiExportMenuLabels($_, aiExportCompatibility, $_('dashboard.aiExport')));

    async function loadAiExportCompatibility() {
        aiExportCatalogLoading = true;
        try {
            aiExportCompatibility = await aiExportCatalogLoader.load();
            aiExportCatalogFailed = false;
        } catch {
            aiExportCatalogFailed = true;
            toasts.error($_('aiExport.catalogUnavailable'));
        } finally {
            aiExportCatalogLoading = false;
        }
    }

    function handleAiExport(options: AiExportOptionsSelection): Promise<PreparedAiExport> {
        return prepareAiExport({context: aiExport.context(), options, compatibility: aiExportCompatibility, translate: (key) => $_(key)});
    }

    function handleAiExportCopied(result: PreparedAiExport) {
        const messages = getAiExportSuccessMessages($_, result);
        toasts.success(messages.copied);
        toasts.info(messages.privacyNotice);
    }

    onMount(() => {
        void loadAiExportCompatibility();
    });
</script>

<PageToolbar thresholds={profile.toolbar.thresholds} {tabs} {activeTab} {ontabchange} testId={profile.testIds.controls} filterRowTestId={profile.testIds.filterRow} layoutDebugName={profile.toolbar.debugName}>
    {#snippet filters({layoutMode, filtersStacked, showExtraLabels})}
        <!-- Date range picker (wired to global store via the shared dateRangeController) -->
        <DateRangePicker
            bind:activePreset={dateRangeCtl.activePreset}
            bind:start={dateRangeCtl.displayStart}
            bind:end={dateRangeCtl.end}
            compact={true}
            align="start"
            maxWidthTwoRow={profile.toolbar.pickerMaxWidthTwoRow}
            {layoutMode}
            debugName={profile.toolbar.debugName}
            onchange={dateRangeCtl.onDateRangeChange}
            bind:effectiveMaxWidth={pickerMaxWidth}
        />

        <!-- Currency override + Broker multi-select — share one justified row when the
             filters+summary zone stacks (stackFilters/oneColumn — see filtersStacked
             in PageToolbar), not each its own stacked full-width row; inline naturally
             otherwise, same as before (unconditional w-full here would fight
             DateRangePicker for row space in oneRow/denseRow mode). Capped to
             pickerMaxWidth (mirrors the picker's own 2-row max-width) so this row's right
             edge lines up with the picker's instead of stretching to the wider column. -->
        <div class="flex items-center gap-3 {filtersStacked ? 'w-full justify-around' : ''}" style={filtersStacked && pickerMaxWidth ? `max-width: ${pickerMaxWidth}px` : ''}>
            <!-- Currency override selector -->
            <div class="flex items-center gap-1.5 text-xs text-lf-muted">
                <!-- Round 13: "Valuta:" is an extra/decorative label — the select itself
                     (flag + code) already conveys enough at very narrow widths, so it hides
                     first via the independent noExtraLabel threshold, well before labelHide*
                     would ever strip anything else on this row. -->
                {#if showExtraLabels}<span class="whitespace-nowrap">{$_('common.currency')}:</span>{/if}
                <div class="w-28">
                    <CurrencySearchSelect
                        bind:value={targetCurrency}
                        compact={true}
                        configuredOnly={true}
                        testId={profile.testIds.currency}
                        defaultCurrency={baseCurrency}
                        createForexLabel={$_('common.createForex')}
                        dropdownPosition="bottom"
                        placeholder={baseCurrency}
                        onCreateForex={() => {
                            // Prefill base = user default currency, quote left for the user to pick
                            oncreateforex(baseCurrency ? `${baseCurrency}-` : '');
                        }}
                        onchange={oncurrencychange}
                    />
                </div>
            </div>

            {#if profile.hasBrokerFilter}
                <BrokerFilterSelect {brokers} selectedIds={selectedBrokerIds} active={brokerFilterActive} onselect={onselectbrokers} />
            {/if}
        </div>
    {/snippet}

    {#snippet actions({showActionLabels})}
        {@render actionsBefore?.({showActionLabels})}

        {#if profile.refreshBeforeAiExport}
            {@render refreshButton(showActionLabels)}
            {@render aiExportMenu(showActionLabels)}
        {:else}
            {@render aiExportMenu(showActionLabels)}
            {@render refreshButton(showActionLabels)}
        {/if}
    {/snippet}
</PageToolbar>

{#snippet aiExportMenu(showActionLabels: boolean)}
    <AiExportMenu
        domain={aiExport.domain}
        compatibility={aiExportCompatibility}
        memoryKey={aiExport.memoryKey}
        defaultSelectionId={aiExport.defaultSelectionId}
        disabled={aiExportCatalogLoading || aiExportCatalogFailed || aiExport.disabled}
        labels={aiExportLabels}
        showLabel={showActionLabels}
        onprepare={handleAiExport}
        oncopied={handleAiExportCopied}
        onerror={(error) => toasts.error(getAiExportErrorMessage($_, error))}
    />
{/snippet}

{#snippet refreshButton(showActionLabels: boolean)}
    <!-- One button for both: while the prices are paused for inactivity (FB-28: nobody used the page for two minutes) it takes the look of the
         «Updates paused» pill in the same place, so nothing shifts (F-4). The prices resume by themselves as soon as the user is active; the
         click is there to restart them by hand, and does what Refresh does. -->
    {@const paused = liveState === 'paused-idle'}
    <button
        class={paused
            ? `inline-flex items-center justify-center gap-1 px-2 py-0.5 whitespace-nowrap rounded-full text-xs font-medium transition-colors disabled:opacity-50 ${STATUS_TONES.liveUpdates.paused}`
            : 'flex items-center justify-center gap-1.5 px-2.5 py-1.5 whitespace-nowrap bg-lf-card border border-lf-subtle rounded-lg text-xs font-medium text-lf-secondary hover:bg-lf-hover transition-colors disabled:opacity-50'}
        onclick={onrefresh}
        disabled={pageBusy.busy}
        data-busy={pageBusy.busy ? 'true' : 'false'}
        data-live-state={liveState}
        data-testid={profile.testIds.refresh}
        title={paused ? $_('liveUpdates.resumeHint') : $_('dashboard.syncData')}
        aria-label={paused ? $_('liveUpdates.paused') : undefined}
    >
        {#if paused}
            <Pause size={12} aria-hidden="true" />
            {#if showActionLabels}
                <span>{$_('liveUpdates.paused')}</span>
            {/if}
        {:else}
            <RefreshCw size={14} class={pageBusy.busy ? 'animate-spin' : ''} />
            {#if showActionLabels}
                <span>{$_('dashboard.syncData')}</span>
            {/if}
        {/if}
    </button>
{/snippet}
