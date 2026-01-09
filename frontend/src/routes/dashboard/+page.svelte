<script lang="ts">
	import { onMount } from 'svelte';
	import { ShieldCheck, LogOut, LayoutDashboard, Briefcase, BarChart3, ArrowRightLeft, Settings } from 'lucide-svelte';
	import { _ } from '$lib/i18n';
	import { auth, currentUser, isAuthenticated } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';

	// Check auth on mount
	onMount(async () => {
		if (browser) {
			const isAuth = await auth.checkAuth();
			if (!isAuth) {
				goto('/');
			}
		}
	});

	async function handleLogout() {
		await auth.logout();
	}
</script>

<div class="min-h-screen bg-gray-100">
	<!-- Header -->
	<header class="bg-libre-green text-white shadow-lg">
		<div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
			<div class="flex items-center space-x-3">
				<ShieldCheck size={32} />
				<span class="text-2xl font-bold tracking-wide">LibreFolio</span>
			</div>

			<div class="flex items-center space-x-4">
				{#if $currentUser}
					<span class="text-white/80">
						{$_('common.welcome')}, <strong>{$currentUser.username}</strong>
					</span>
				{/if}
				<button
					on:click={handleLogout}
					class="flex items-center space-x-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-all"
				>
					<LogOut size={18} />
					<span>{$_('auth.logout')}</span>
				</button>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 py-8">
		<h1 class="text-3xl font-bold text-gray-800 mb-8">{$_('nav.dashboard')}</h1>

		<!-- Quick Stats Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
			<!-- Card: Brokers -->
			<a href="/brokers" class="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-all group">
				<div class="flex items-center justify-between mb-4">
					<div class="p-3 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-all">
						<Briefcase class="text-blue-600" size={24} />
					</div>
				</div>
				<h3 class="text-lg font-semibold text-gray-700">{$_('nav.brokers')}</h3>
				<p class="text-gray-500 text-sm mt-1">{$_('dashboard.manageBrokers')}</p>
			</a>

			<!-- Card: Assets -->
			<a href="/assets" class="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-all group">
				<div class="flex items-center justify-between mb-4">
					<div class="p-3 bg-green-100 rounded-lg group-hover:bg-green-200 transition-all">
						<BarChart3 class="text-green-600" size={24} />
					</div>
				</div>
				<h3 class="text-lg font-semibold text-gray-700">{$_('nav.assets')}</h3>
				<p class="text-gray-500 text-sm mt-1">{$_('dashboard.manageAssets')}</p>
			</a>

			<!-- Card: Transactions -->
			<a href="/transactions" class="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-all group">
				<div class="flex items-center justify-between mb-4">
					<div class="p-3 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-all">
						<ArrowRightLeft class="text-purple-600" size={24} />
					</div>
				</div>
				<h3 class="text-lg font-semibold text-gray-700">{$_('nav.transactions')}</h3>
				<p class="text-gray-500 text-sm mt-1">{$_('dashboard.manageTransactions')}</p>
			</a>

			<!-- Card: Settings -->
			<a href="/settings" class="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-all group">
				<div class="flex items-center justify-between mb-4">
					<div class="p-3 bg-gray-100 rounded-lg group-hover:bg-gray-200 transition-all">
						<Settings class="text-gray-600" size={24} />
					</div>
				</div>
				<h3 class="text-lg font-semibold text-gray-700">{$_('nav.settings')}</h3>
				<p class="text-gray-500 text-sm mt-1">{$_('dashboard.configureSettings')}</p>
			</a>
		</div>

		<!-- Placeholder Content -->
		<div class="bg-white rounded-xl shadow-md p-8 text-center">
			<LayoutDashboard class="mx-auto text-gray-400 mb-4" size={64} />
			<h2 class="text-xl font-semibold text-gray-600 mb-2">{$_('dashboard.welcomeTitle')}</h2>
			<p class="text-gray-500">
				{$_('dashboard.welcomeMessage')}
			</p>
		</div>
	</main>
</div>

