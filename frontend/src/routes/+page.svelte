<script lang="ts">
	import AnimatedBackground from '$lib/components/AnimatedBackground.svelte';
	import LoginModal from '$lib/components/auth/LoginModal.svelte';
	import RegisterModal from '$lib/components/auth/RegisterModal.svelte';
	import ForgotPasswordModal from '$lib/components/auth/ForgotPasswordModal.svelte';
	import { currentLanguage, availableLanguages, currentLanguageFlag } from '$lib/stores/language';
	import { auth } from '$lib/stores/auth';
	import { page } from '$app/stores';

	// Auth view state (modals)
	type AuthView = 'login' | 'register' | 'forgot-password';
	let currentView: AuthView = 'login';

	// Success message (from registration)
	let successMessage = '';

	// Get redirect URL from query params (if coming from protected route)
	$: redirectTo = $page.url.searchParams.get('redirect') || '/dashboard';

	// Language selector toggle
	let showLangMenu = false;

	// Handle navigation between modals
	function handleGotoRegister() {
		auth.clearError();
		successMessage = '';
		currentView = 'register';
	}

	function handleGotoForgot() {
		auth.clearError();
		successMessage = '';
		currentView = 'forgot-password';
	}

	function handleGotoLogin(event: CustomEvent<{ message?: string }>) {
		auth.clearError();
		successMessage = event.detail?.message || '';
		currentView = 'login';
	}

	function handleGotoLoginSimple() {
		auth.clearError();
		successMessage = '';
		currentView = 'login';
	}
</script>

<AnimatedBackground />

<div class="min-h-screen flex items-center justify-center p-4">
	<!-- Language Selector (top right) -->
	<div class="fixed top-4 right-4 z-50">
		<button
			on:click={() => showLangMenu = !showLangMenu}
			class="flex items-center space-x-2 px-3 py-2 rounded-lg bg-white/80 hover:bg-white shadow-md transition-all"
		>
			<span class="text-xl">{$currentLanguageFlag}</span>
		</button>

		{#if showLangMenu}
			<div class="absolute right-0 mt-2 bg-white rounded-lg shadow-xl py-2 min-w-[150px]">
				{#each availableLanguages as lang}
					<button
						on:click={() => { currentLanguage.set(lang.code); showLangMenu = false; }}
						class="w-full px-4 py-2 text-left hover:bg-gray-100 flex items-center space-x-2"
						class:bg-gray-50={$currentLanguage === lang.code}
					>
						<span>{lang.flag}</span>
						<span>{lang.name}</span>
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Modal Container - Cambio istantaneo senza transizione -->
	{#if currentView === 'login'}
		<LoginModal
			{redirectTo}
			{successMessage}
			on:gotoRegister={handleGotoRegister}
			on:gotoForgot={handleGotoForgot}
		/>
	{:else if currentView === 'register'}
		<RegisterModal
			on:gotoLogin={handleGotoLogin}
		/>
	{:else if currentView === 'forgot-password'}
		<ForgotPasswordModal
			on:gotoLogin={handleGotoLoginSimple}
		/>
	{/if}
</div>

