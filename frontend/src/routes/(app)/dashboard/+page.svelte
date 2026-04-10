<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentUser} from '$lib/stores/auth';
    import {userSettings} from '$lib/stores/settings';
    import {ArrowRightLeft, BarChart3, Briefcase, Coins, PieChart, TrendingUp, Wallet} from 'lucide-svelte';
    import LiveTicker from '$lib/components/layout/LiveTicker.svelte';

    // Get avatar URL from settings
    $: avatarUrl = $userSettings?.avatar_url as string | null | undefined;

    // Quick action cards for navigation
    const quickActions = [
        {
            href: '/brokers',
            icon: Briefcase,
            titleKey: 'brokers.title',
            descKey: 'dashboard.manageBrokers',
            bgClass: 'bg-blue-100 dark:bg-blue-900/30 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50',
            iconClass: 'text-blue-600 dark:text-blue-400'
        },
        {
            href: '/assets',
            icon: BarChart3,
            titleKey: 'assets.title',
            descKey: 'dashboard.manageAssets',
            bgClass: 'bg-green-100 dark:bg-green-900/30 group-hover:bg-green-200 dark:group-hover:bg-green-900/50',
            iconClass: 'text-green-600 dark:text-green-400'
        },
        {
            href: '/transactions',
            icon: ArrowRightLeft,
            titleKey: 'transactions.title',
            descKey: 'dashboard.manageTransactions',
            bgClass: 'bg-purple-100 dark:bg-purple-900/30 group-hover:bg-purple-200 dark:group-hover:bg-purple-900/50',
            iconClass: 'text-purple-600 dark:text-purple-400'
        },
        {
            href: '/fx',
            icon: Coins,
            titleKey: 'fx.title',
            descKey: 'dashboard.manageFx',
            bgClass: 'bg-amber-100 dark:bg-amber-900/30 group-hover:bg-amber-200 dark:group-hover:bg-amber-900/50',
            iconClass: 'text-amber-600 dark:text-amber-400'
        }
    ];
</script>

<div class="space-y-6" data-testid="dashboard-page">
    <!-- Page Title (sr-only but present for tests) -->
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <!-- Welcome Banner with User Name -->
    {#if $currentUser}
        <div class="bg-gradient-to-r from-libre-banner to-libre-banner/80 rounded-xl shadow-sm p-6 text-white">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-2xl font-bold">
                        {$_('dashboard.welcomeBack')}, {$currentUser.username}!
                    </h1>
                    <p class="text-white/80 mt-1">{$_('dashboard.welcomeSubtitle')}</p>
                </div>
                <div class="hidden sm:flex items-center justify-center w-16 h-16 bg-white/20 rounded-full overflow-hidden">
                    {#if avatarUrl}
                        <img src={avatarUrl} alt="Avatar" class="w-full h-full object-cover"/>
                    {:else}
                        <span class="text-3xl font-bold">
                            {$currentUser.username.charAt(0).toUpperCase()}
                        </span>
                    {/if}
                </div>
            </div>
        </div>
    {/if}

    <!-- Quick Stats (placeholder for future) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-slate-700">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('common.totalValue')}</p>
                    <p class="text-2xl font-bold text-gray-800 dark:text-gray-100 mt-1">€ --,---.--</p>
                </div>
                <div class="p-3 bg-libre-green/10 dark:bg-libre-green/20 rounded-lg">
                    <Wallet class="text-libre-green" size={24}/>
                </div>
            </div>
        </div>

        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-slate-700">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('dashboard.totalGain')}</p>
                    <p class="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">+€ ---.--</p>
                </div>
                <div class="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                    <TrendingUp class="text-green-600 dark:text-green-400" size={24}/>
                </div>
            </div>
        </div>

        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-slate-700">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-gray-500 dark:text-gray-400 text-sm">{$_('dashboard.assetCount')}</p>
                    <p class="text-2xl font-bold text-gray-800 dark:text-gray-100 mt-1">--</p>
                </div>
                <div class="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                    <PieChart class="text-purple-600 dark:text-purple-400" size={24}/>
                </div>
            </div>
        </div>
    </div>

    <!-- Live Asset Prices -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-slate-700">
        <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-4 flex items-center gap-2">
            <TrendingUp size={20} class="text-libre-green"/>
            {$_('assets.title')} — {$_('ticker.livePrices')}
        </h2>
        <LiveTicker />
    </div>

    <!-- Quick Actions -->
    <div>
        <h2 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-4">{$_('dashboard.quickActions')}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {#each quickActions as action}
                <a
                        href={action.href}
                        class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6 border border-gray-100 dark:border-slate-700 hover:shadow-md transition-all group"
                >
                    <div class="flex items-center justify-between mb-4">
                        <div class="{action.bgClass} p-3 rounded-lg transition-all">
                            <svelte:component this={action.icon} class={action.iconClass} size={24}/>
                        </div>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200">{$_(action.titleKey)}</h3>
                    <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">{$_(action.descKey)}</p>
                </a>
            {/each}
        </div>
    </div>

    <!-- Welcome Section -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-8 text-center border border-gray-100 dark:border-slate-700">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-libre-green/10 dark:bg-libre-green/20 rounded-full mb-4">
            <BarChart3 class="text-libre-green" size={32}/>
        </div>
        <h2 class="text-xl font-semibold text-gray-700 dark:text-gray-200 mb-2">{$_('dashboard.welcomeTitle')}</h2>
        <p class="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            {$_('dashboard.welcomeMessage')}
        </p>
    </div>
</div>
