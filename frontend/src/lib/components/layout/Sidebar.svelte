<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import { auth, currentUser } from '$lib/stores/auth';
	import { currentLanguage } from '$lib/stores/language';
	import { LANGUAGE_OPTIONS, type SupportedLocale } from '$lib/i18n';
	import {
		ShieldCheck,
		LayoutDashboard,
		Briefcase,
		BarChart3,
		ArrowRightLeft,
		Coins,
		Settings,
		LogOut,
		Menu,
		X
	} from 'lucide-svelte';

	// Mobile sidebar state
	export let isOpen = false;


	// Navigation items
	const navItems = [
		{ href: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.dashboard' },
		{ href: '/brokers', icon: Briefcase, labelKey: 'nav.brokers' },
		{ href: '/assets', icon: BarChart3, labelKey: 'nav.assets' },
		{ href: '/transactions', icon: ArrowRightLeft, labelKey: 'nav.transactions' },
		{ href: '/fx', icon: Coins, labelKey: 'nav.fx' },
		{ href: '/settings', icon: Settings, labelKey: 'nav.settings' }
	];

	function isActive(href: string): boolean {
		return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
	}

	function handleLanguageChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		currentLanguage.set(target.value as SupportedLocale);
	}

	async function handleLogout() {
		await auth.logout();
	}

	function closeSidebar() {
		isOpen = false;
	}
</script>

<!-- Mobile Overlay -->
{#if isOpen}
	<div
		class="fixed inset-0 bg-black/50 z-40 lg:hidden"
		on:click={closeSidebar}
		on:keydown={(e) => e.key === 'Escape' && closeSidebar()}
		role="button"
		tabindex="-1"
	></div>
{/if}

<!-- Sidebar -->
<nav
	class="fixed left-0 top-0 h-screen w-64 bg-libre-green text-white flex flex-col z-50 transform transition-transform duration-300 ease-in-out
		{isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0"
>
	<!-- Logo -->
	<div class="p-6 flex items-center justify-between border-b border-white/10">
		<div class="flex items-center space-x-3">
			<ShieldCheck size={32} />
			<span class="text-xl font-bold tracking-wide">LibreFolio</span>
		</div>
		<!-- Mobile close button -->
		<button class="lg:hidden p-2 hover:bg-white/10 rounded-lg" on:click={closeSidebar}>
			<X size={20} />
		</button>
	</div>

	<!-- Navigation -->
	<ul class="flex-1 py-4 overflow-y-auto">
		{#each navItems as item}
			<li>
				<a
					href={item.href}
					on:click={closeSidebar}
					class="flex items-center space-x-3 px-6 py-3 transition-all
						{isActive(item.href)
						? 'bg-white/20 border-r-4 border-white'
						: 'hover:bg-white/10'}"
				>
					<svelte:component this={item.icon} size={20} />
					<span>{$_(item.labelKey)}</span>
				</a>
			</li>
		{/each}
	</ul>

	<!-- User Section (bottom) -->
	<div class="border-t border-white/10 p-4 space-y-3">
		<!-- Username -->
		{#if $currentUser}
			<div class="text-white/80 text-sm truncate">
				{$currentUser.username}
			</div>
		{/if}

		<!-- Language Selector -->
		<div class="relative">
			<select
				class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm
					appearance-none cursor-pointer hover:bg-white/20 transition-all"
				value={$currentLanguage}
				on:change={handleLanguageChange}
			>
				{#each LANGUAGE_OPTIONS as lang}
					<option value={lang.code} class="bg-libre-green text-white">
						{lang.flag} {lang.name}
					</option>
				{/each}
			</select>
		</div>

		<!-- Logout Button -->
		<button
			on:click={handleLogout}
			class="w-full flex items-center justify-center space-x-2 px-4 py-2
				bg-white/10 hover:bg-white/20 rounded-lg transition-all text-sm"
		>
			<LogOut size={16} />
			<span>{$_('auth.logout')}</span>
		</button>
	</div>
</nav>

