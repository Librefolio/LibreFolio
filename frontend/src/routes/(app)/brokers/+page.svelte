<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {fetchReport} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {Briefcase, Plus, RefreshCw} from 'lucide-svelte';
    import BrokerCard from '$lib/components/brokers/BrokerCard.svelte';
    import BrokerDiscoveryCard from '$lib/components/brokers/BrokerDiscoveryCard.svelte';
    import BrokerModal from '$lib/components/brokers/BrokerModal.svelte';
    import BrokerSharingModal from '$lib/components/brokers/BrokerSharingModal.svelte';
    import DeleteBrokerDialog from '$lib/components/brokers/DeleteBrokerDialog.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {refreshAllBrokers, getAllBrokers, getAccessibleBrokers, invalidateBroker} from '$lib/stores/reference/brokerStore';
    import type {Broker} from '$lib/types';

    type CurrencyLike = {code: string; amount: number | string};
    type PageBroker = {
        id: number;
        name: string;
        description?: string | null;
        portal_url?: string | null;
        icon_url?: string | null;
        default_import_plugin?: string | null;
        allow_cash_overdraft: boolean;
        allow_asset_shorting: boolean;
        is_active?: boolean;
        user_role?: string | null;
        user_share_percentage?: number | string | null;
        opened_at?: string | null;
    };
    type BrokerBreakdownView = {
        broker_id: number;
        broker_name: string;
        net_worth: CurrencyLike;
        gain_loss: CurrencyLike;
        gain_loss_percent: string;
        cash_total: CurrencyLike;
        cash_balances?: CurrencyLike[];
    };
    type PortfolioHoldingLike = {broker_id?: number | null};
    type DiscoveryBroker = {id: number; name: string; icon_url?: string | null};

    let brokers: PageBroker[] = [];
    let inaccessibleBrokers: DiscoveryBroker[] = [];
    let brokerBreakdownById: Record<number, BrokerBreakdownView> = {};
    let brokerAssetCountById: Record<number, number> = {};
    let loading = true;
    let error: string | null = null;

    let targetCurrency = 'EUR';
    let targetCurrencyManuallySet = false;
    let targetCurrencyInitialized = false;

    let modalOpen = false;
    let modalMode: 'create' | 'edit' = 'create';
    let editingBrokerId: number | null = null;
    let editingBrokerData: {
        name?: string;
        description?: string | null;
        portal_url?: string | null;
        icon_url?: string | null;
        default_import_plugin?: string | null;
        allow_cash_overdraft?: boolean;
        allow_asset_shorting?: boolean;
        is_active?: boolean;
        opened_at?: string | null;
    } = {};

    let deleteDialogOpen = false;
    let deletingBroker: {id: number; name: string} | null = null;
    let deletingTransactionCount = 0;
    let deleteLoading = false;

    let sharingModalOpen = false;
    let sharingBrokerId: number | null = null;
    let sharingBrokerName = '';
    let sharingReadOnly = false;

    $: baseCurrency = $globalSettings.default_currency || 'EUR';
    $: if (!targetCurrencyInitialized) {
        targetCurrency = baseCurrency;
        targetCurrencyInitialized = true;
    } else if (!targetCurrencyManuallySet && targetCurrency !== baseCurrency) {
        targetCurrency = baseCurrency;
        // Guard with !loading: globalSettings.load() (root layout) can resolve AFTER
        // onMount's own loadBrokers() already started with the hardcoded 'EUR' fallback —
        // without this guard, a second concurrent loadBrokers() could fire and race the
        // first one while reassigning brokers/brokerBreakdownById mid-flight.
        if (brokers.length > 0 && !loading) {
            void loadBrokers();
        }
    }

    onMount(async () => {
        await loadBrokers();
    });

    function asBrokerBreakdowns(value: unknown): BrokerBreakdownView[] {
        return Array.isArray(value) ? (value as BrokerBreakdownView[]) : [];
    }

    function asPortfolioHoldings(value: unknown): PortfolioHoldingLike[] {
        return Array.isArray(value) ? (value as PortfolioHoldingLike[]) : [];
    }

    function firstString(value: unknown): string | null {
        if (typeof value === 'string') return value;
        if (Array.isArray(value)) {
            const first = value.find((item) => typeof item === 'string');
            return typeof first === 'string' ? first : null;
        }
        return null;
    }

    function firstBoolean(value: unknown): boolean {
        if (typeof value === 'boolean') return value;
        if (Array.isArray(value)) {
            const first = value.find((item) => typeof item === 'boolean');
            return typeof first === 'boolean' ? first : false;
        }
        return false;
    }

    function normalizeBroker(raw: Broker): PageBroker {
        const rawShare = raw.user_share_percentage;
        return {
            id: raw.id,
            name: raw.name,
            description: firstString(raw.description),
            portal_url: firstString(raw.portal_url),
            icon_url: firstString(raw.icon_url),
            default_import_plugin: firstString(raw.default_import_plugin),
            allow_cash_overdraft: firstBoolean(raw.allow_cash_overdraft),
            allow_asset_shorting: firstBoolean(raw.allow_asset_shorting),
            is_active: firstBoolean(raw.is_active),
            user_role: firstString(raw.user_role),
            user_share_percentage: Array.isArray(rawShare) ? (typeof rawShare[0] === 'string' ? rawShare[0] : null) : (rawShare ?? null),
            opened_at: firstString(raw.opened_at),
        };
    }

    async function loadBrokers() {
        loading = true;
        error = null;
        try {
            // Single ensureBrokersLoaded-backed refresh: brokerStore's loader already
            // merges accessible + inaccessible brokers (see brokerStore.ts), so both
            // `brokers` and `inaccessibleBrokers` come from this ONE network call —
            // no separate `include_inaccessible` fetch needed here.
            await refreshAllBrokers();
            brokers = getAccessibleBrokers().map((broker) => normalizeBroker(broker as unknown as Broker));
            inaccessibleBrokers = getAllBrokers()
                .filter((broker) => broker.user_role == null)
                .map((broker) => ({id: broker.id, name: broker.name, icon_url: broker.icon_url ?? null}));

            const brokerIds = brokers.map((broker) => broker.id);
            // Reuse portfolioStore.fetchReport (cache + in-flight de-dup + shared
            // invalidation on transaction CRUD/price sync) instead of a raw direct
            // call — same principle already applied everywhere else in the app.
            // includeHistory/includeAllocationHistory=false: this page only reads
            // summary.by_broker/holdings below — the daily series can be several MB
            // for a long-lived portfolio and was previously fetched unconditionally,
            // its JSON.parse blocking the main thread long enough to make card clicks
            // feel unresponsive while it was in flight.
            const report = brokerIds.length > 0 ? await fetchReport(brokerIds, undefined, undefined, targetCurrency, false, false, true, false, false) : null;

            const breakdowns = asBrokerBreakdowns((report?.summary as {by_broker?: unknown} | null)?.by_broker);
            brokerBreakdownById = Object.fromEntries(breakdowns.map((item) => [item.broker_id, item]));

            const holdings = asPortfolioHoldings((report?.summary as {holdings?: unknown} | null)?.holdings);
            brokerAssetCountById = holdings.reduce<Record<number, number>>((acc, holding) => {
                if (holding.broker_id == null) return acc;
                acc[holding.broker_id] = (acc[holding.broker_id] ?? 0) + 1;
                return acc;
            }, {});
        } catch (e) {
            console.error('Failed to load brokers:', e);
            error = 'Failed to load brokers';
        } finally {
            loading = false;
        }
    }

    function openCreateModal() {
        modalMode = 'create';
        editingBrokerId = null;
        editingBrokerData = {};
        modalOpen = true;
    }

    function handleEdit(event: CustomEvent<{id: number}>) {
        const broker = brokers.find((item) => item.id === event.detail.id);
        if (!broker) return;

        modalMode = 'edit';
        editingBrokerId = broker.id;
        editingBrokerData = {
            name: broker.name,
            description: broker.description,
            portal_url: broker.portal_url,
            icon_url: broker.icon_url,
            default_import_plugin: broker.default_import_plugin,
            allow_cash_overdraft: broker.allow_cash_overdraft,
            allow_asset_shorting: broker.allow_asset_shorting,
            is_active: broker.is_active,
            opened_at: broker.opened_at,
        };
        modalOpen = true;
    }

    function handleDelete(event: CustomEvent<{id: number; name: string}>) {
        deletingBroker = event.detail;
        deletingTransactionCount = 0;
        deleteDialogOpen = true;
    }

    function openSharingModal(brokerId: number, brokerName: string, readOnly: boolean) {
        sharingBrokerId = brokerId;
        sharingBrokerName = brokerName;
        sharingReadOnly = readOnly;
        sharingModalOpen = true;
    }

    function handleShare(event: CustomEvent<{id: number}>) {
        const broker = brokers.find((item) => item.id === event.detail.id);
        if (!broker) return;
        openSharingModal(broker.id, broker.name, broker.user_role !== 'OWNER');
    }

    function handleDiscoveryShare(event: CustomEvent<{id: number}>) {
        const broker = inaccessibleBrokers.find((item) => item.id === event.detail.id);
        if (!broker) return;
        openSharingModal(broker.id, broker.name, true);
    }

    async function confirmDelete(event: CustomEvent<{force: boolean}>) {
        if (!deletingBroker) return;

        deleteLoading = true;
        try {
            await zodiosApi.delete_brokers_api_v1_brokers_delete(undefined, {queries: {ids: [deletingBroker.id], force: event.detail.force}});
            invalidateBroker(deletingBroker.id);
            deleteDialogOpen = false;
            deletingBroker = null;
            await loadBrokers();
        } catch (e) {
            console.error('Failed to delete broker:', e);
        } finally {
            deleteLoading = false;
        }
    }

    function handleModalClose() {
        modalOpen = false;
    }

    async function handleCreated() {
        await loadBrokers();
    }

    async function handleUpdated() {
        await loadBrokers();
    }
</script>

<div class="space-y-6" data-testid="brokers-page">
    <!-- Header: Title left, controls right. Round 14.1 bugfix: `lg:` is a VIEWPORT breakpoint
         (1024px) — wraps unconditionally below that width regardless of whether the actual
         header row has room. Plain `flex-wrap` reacts to the row's OWN available width instead
         (see fx/+page.svelte's equivalent header for the full note). -->
    <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
            <h2 class="text-lg font-semibold text-gray-700">{$_('brokers.title')}</h2>
            <p class="text-gray-500 text-sm">{$_('brokers.subtitle')}</p>
        </div>

        <div class="flex flex-wrap items-center gap-2 justify-end">
            <div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                <span class="whitespace-nowrap">{$_('common.currency')}:</span>
                <div class="w-28">
                    <CurrencySearchSelect
                        bind:value={targetCurrency}
                        compact={true}
                        dropdownPosition="bottom"
                        placeholder={baseCurrency}
                        onchange={() => {
                            targetCurrencyManuallySet = true;
                            void loadBrokers();
                        }}
                    />
                </div>
            </div>

            <button class="p-2 text-gray-500 hover:text-libre-green hover:bg-libre-green/10 rounded-lg transition-colors disabled:opacity-50" data-testid="brokers-refresh" disabled={loading} on:click={loadBrokers} title="Refresh">
                <RefreshCw class={loading ? 'animate-spin' : ''} size={18} />
            </button>
            <button class="flex items-center justify-center gap-2 px-3 sm:px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all" data-testid="add-broker-button" on:click={openCreateModal}>
                <Plus size={18} />
                <span class="hidden sm:inline">{$_('brokers.addBroker')}</span>
            </button>
        </div>
    </div>

    {#if loading && brokers.length === 0 && inaccessibleBrokers.length === 0}
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-12 text-center border border-gray-100 dark:border-slate-700">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-libre-green/10 rounded-full mb-4">
                <RefreshCw class="text-libre-green animate-spin" size={32} />
            </div>
            <p class="text-gray-500 dark:text-gray-400">{$_('common.loading')}</p>
        </div>
    {:else if error}
        <div class="bg-white rounded-xl shadow-sm p-12 text-center border border-red-100">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                <Briefcase class="text-red-600" size={32} />
            </div>
            <h3 class="text-lg font-semibold text-gray-700 mb-2">{$_('common.error')}</h3>
            <p class="text-gray-500 mb-4">{error}</p>
            <button on:click={loadBrokers} class="px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors">
                {$_('common.retry')}
            </button>
        </div>
    {:else}
        {#if brokers.length === 0}
            <div class="bg-white rounded-xl shadow-sm p-12 text-center border border-gray-100">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                    <Briefcase class="text-blue-600" size={32} />
                </div>
                <h3 class="text-lg font-semibold text-gray-700 mb-2">{$_('brokers.noBrokers')}</h3>
                <p class="text-gray-500 mb-4">{$_('brokers.noBrokersMessage')}</p>
                <button on:click={openCreateModal} class="inline-flex items-center space-x-2 px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all">
                    <Plus size={18} />
                    <span>{$_('brokers.addBroker')}</span>
                </button>
            </div>
        {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {#each brokers as broker (broker.id)}
                    <BrokerCard {broker} assetCount={brokerAssetCountById[broker.id] ?? 0} summary={brokerBreakdownById[broker.id] ?? null} {targetCurrency} on:edit={handleEdit} on:delete={handleDelete} on:share={handleShare} />
                {/each}
            </div>
        {/if}

        {#if inaccessibleBrokers.length > 0}
            <section class="space-y-4" data-testid="brokers-other-existing">
                <div>
                    <h3 class="text-base font-semibold text-gray-700 dark:text-gray-200">{$_('brokers.otherExisting')}</h3>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {#each inaccessibleBrokers as broker (broker.id)}
                        <BrokerDiscoveryCard {broker} on:share={handleDiscoveryShare} />
                    {/each}
                </div>
            </section>
        {/if}
    {/if}
</div>

<BrokerModal brokerId={editingBrokerId} initialData={editingBrokerData} isOpen={modalOpen} mode={modalMode} onclose={handleModalClose} oncreated={handleCreated} onupdated={handleUpdated} />

<DeleteBrokerDialog
    brokerName={deletingBroker?.name ?? ''}
    isOpen={deleteDialogOpen}
    loading={deleteLoading}
    on:cancel={() => {
        deleteDialogOpen = false;
        deletingBroker = null;
    }}
    on:confirm={confirmDelete}
    transactionCount={deletingTransactionCount}
/>

{#if sharingBrokerId !== null}
    <BrokerSharingModal open={sharingModalOpen} brokerId={sharingBrokerId} brokerName={sharingBrokerName} readOnly={sharingReadOnly} onClose={() => (sharingModalOpen = false)} onChanged={handleUpdated} />
{/if}
