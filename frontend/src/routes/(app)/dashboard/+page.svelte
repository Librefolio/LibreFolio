<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentUser} from '$lib/stores/auth';
    import {ArrowRightLeft, BarChart3, Briefcase, Coins, PieChart, TrendingUp, Wallet} from 'lucide-svelte';

    // Quick action cards for navigation
    const quickActions = [
        {
            href: '/brokers',
            icon: Briefcase,
            titleKey: 'nav.brokers',
            descKey: 'dashboard.manageBrokers',
            color: 'blue'
        },
        {
            href: '/assets',
            icon: BarChart3,
            titleKey: 'nav.assets',
            descKey: 'dashboard.manageAssets',
            color: 'green'
        },
        {
            href: '/transactions',
            icon: ArrowRightLeft,
            titleKey: 'nav.transactions',
            descKey: 'dashboard.manageTransactions',
            color: 'purple'
        },
        {
            href: '/fx',
            icon: Coins,
            titleKey: 'nav.fx',
            descKey: 'dashboard.manageFx',
            color: 'yellow'
        }
    ];

    // Color mappings for cards
    const colorClasses: Record<string, { bg: string; bgHover: string; text: string }> = {
        blue: {bg: 'bg-blue-100', bgHover: 'group-hover:bg-blue-200', text: 'text-blue-600'},
        green: {bg: 'bg-green-100', bgHover: 'group-hover:bg-green-200', text: 'text-green-600'},
        purple: {bg: 'bg-purple-100', bgHover: 'group-hover:bg-purple-200', text: 'text-purple-600'},
        yellow: {bg: 'bg-amber-100', bgHover: 'group-hover:bg-amber-200', text: 'text-amber-600'}
    };
</script>

<div class="space-y-6" data-testid="dashboard-page">
    <!-- Page Title (sr-only but present for tests) -->
    <h1 class="sr-only">{$_('nav.dashboard')}</h1>

    <!-- Welcome Banner with User Name -->
    {#if $currentUser}
        <div class="bg-gradient-to-r from-libre-green to-libre-green/80 rounded-xl shadow-sm p-6 text-white">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-2xl font-bold">
                        {$_('dashboard.welcomeBack')}, {$currentUser.username}!
                    </h1>
                    <p class="text-white/80 mt-1">{$_('dashboard.welcomeSubtitle')}</p>
                </div>
                <div class="hidden sm:flex items-center justify-center w-16 h-16 bg-white/20 rounded-full">
					<span class="text-3xl font-bold">
						{$currentUser.username.charAt(0).toUpperCase()}
					</span>
                </div>
            </div>
        </div>
    {/if}

    <!-- Quick Stats (placeholder for future) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-gray-500 text-sm">{$_('dashboard.totalValue')}</p>
                    <p class="text-2xl font-bold text-gray-800 mt-1">€ --,---.--</p>
                </div>
                <div class="p-3 bg-libre-green/10 rounded-lg">
                    <Wallet class="text-libre-green" size={24}/>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-gray-500 text-sm">{$_('dashboard.totalGain')}</p>
                    <p class="text-2xl font-bold text-green-600 mt-1">+€ ---.--</p>
                </div>
                <div class="p-3 bg-green-100 rounded-lg">
                    <TrendingUp class="text-green-600" size={24}/>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-gray-500 text-sm">{$_('dashboard.assetCount')}</p>
                    <p class="text-2xl font-bold text-gray-800 mt-1">--</p>
                </div>
                <div class="p-3 bg-purple-100 rounded-lg">
                    <PieChart class="text-purple-600" size={24}/>
                </div>
            </div>
        </div>
    </div>

    <!-- Quick Actions -->
    <div>
        <h2 class="text-lg font-semibold text-gray-700 mb-4">{$_('dashboard.quickActions')}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {#each quickActions as action}
                {@const colors = colorClasses[action.color]}
                <a
                        href={action.href}
                        class="bg-white rounded-xl shadow-sm p-6 border border-gray-100 hover:shadow-md transition-all group"
                >
                    <div class="flex items-center justify-between mb-4">
                        <div class="{colors.bg} {colors.bgHover} p-3 rounded-lg transition-all">
                            <svelte:component this={action.icon} class={colors.text} size={24}/>
                        </div>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-700">{$_(action.titleKey)}</h3>
                    <p class="text-gray-500 text-sm mt-1">{$_(action.descKey)}</p>
                </a>
            {/each}
        </div>
    </div>

    <!-- Welcome Section -->
    <div class="bg-white rounded-xl shadow-sm p-8 text-center border border-gray-100">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-libre-green/10 rounded-full mb-4">
            <BarChart3 class="text-libre-green" size={32}/>
        </div>
        <h2 class="text-xl font-semibold text-gray-700 mb-2">{$_('dashboard.welcomeTitle')}</h2>
        <p class="text-gray-500 max-w-md mx-auto">
            {$_('dashboard.welcomeMessage')}
        </p>
    </div>
</div>

