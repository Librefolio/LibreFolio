<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { initI18n, i18nLoading } from '$lib/i18n';
	import { currentLanguage } from '$lib/stores/language';
	import { auth, isAuthenticated } from '$lib/stores/auth';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import Header from '$lib/components/layout/Header.svelte';

	// Sidebar state for mobile
	let sidebarOpen = false;

	// Initialize i18n
	initI18n();

	onMount(async () => {
		// Sync language store with i18n after mount
		currentLanguage.init();

		// Check authentication
		if (browser) {
			const isAuth = await auth.checkAuth();
			if (!isAuth) {
				goto('/');
			}
		}
	});

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

{#if $i18nLoading}
	<!-- Loading screen while translations load -->
	<div class="min-h-screen flex items-center justify-center bg-libre-beige">
		<div class="text-libre-green text-xl">Loading...</div>
	</div>
{:else if $isAuthenticated}
	<div class="min-h-screen bg-libre-beige">
		<!-- Sidebar -->
		<Sidebar bind:isOpen={sidebarOpen} />

		<!-- Main Content Area -->
		<div class="lg:ml-64 min-h-screen flex flex-col">
			<!-- Header -->
			<Header on:toggleSidebar={toggleSidebar} />

			<!-- Page Content -->
			<main class="flex-1 p-4 lg:p-6">
				<slot />
			</main>
		</div>
	</div>
{:else}
	<!-- Loading while checking auth -->
	<div class="min-h-screen flex items-center justify-center bg-libre-beige">
		<div class="text-libre-green text-xl">Checking authentication...</div>
	</div>
{/if}

