<script lang="ts">
	import AnimatedBackground from '$lib/components/AnimatedBackground.svelte';
	import { ShieldCheck } from 'lucide-svelte';
	import { _ } from '$lib/i18n';
	import { currentLanguage, availableLanguages, currentLanguageFlag } from '$lib/stores/language';

	// Form state
	let username = '';
	let password = '';
	let isLoading = false;
	let error = '';

	async function handleLogin() {
		isLoading = true;
		error = '';

		try {
			console.log('Login attempt:', username);
			// TODO: Integrate with backend /auth/login
			// For now, just simulate a delay
			await new Promise(resolve => setTimeout(resolve, 500));

			// Placeholder - will redirect to dashboard after auth is implemented
		} catch (e) {
			error = $_('auth.invalidCredentials');
		} finally {
			isLoading = false;
		}
	}

	// Language selector toggle
	let showLangMenu = false;
</script>

<AnimatedBackground />

<div class="min-h-screen flex items-center justify-center p-4">
	<!-- Language Selector (top right) -->
	<div class="fixed top-4 right-4">
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

	<!-- Card Container -->
	<div class="w-full max-w-[400px] bg-libre-beige rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans">
		
		<!-- Header Section (Dark Green) -->
		<div class="bg-libre-green p-8 flex flex-col items-center justify-center space-y-3">
			<!-- Logo Area -->
			<div class="flex items-center space-x-2 text-white">
				<ShieldCheck size={32} />
				<span class="text-2xl font-bold tracking-wide">LibreFolio</span>
			</div>
		</div>

		<!-- Body Section (Beige) -->
		<div class="p-8 pt-10">
			<form on:submit|preventDefault={handleLogin} class="space-y-5">
				
				<!-- Error Message -->
				{#if error}
					<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded-lg text-sm">
						{error}
					</div>
				{/if}

				<!-- Username Input -->
				<div class="relative">
					<input 
						type="text" 
						placeholder={$_('auth.usernameOrEmail')}
						bind:value={username}
						disabled={isLoading}
						class="w-full px-4 py-3 rounded-lg border border-gray-400 bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green transition-all disabled:opacity-50"
					/>
				</div>

				<!-- Password Input -->
				<div class="relative">
					<input 
						type="password" 
						placeholder={$_('auth.password')}
						bind:value={password}
						disabled={isLoading}
						class="w-full px-4 py-3 rounded-lg border border-gray-400 bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green transition-all disabled:opacity-50"
					/>
				</div>

				<!-- Forgot Password Link -->
				<div class="flex justify-end">
					<a href="/forgot-password" class="text-xs font-semibold text-libre-dark hover:text-libre-green underline decoration-1 underline-offset-2">
						{$_('auth.forgotPassword')}
					</a>
				</div>

				<!-- Login Button -->
				<button 
					type="submit" 
					disabled={isLoading}
					class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:bg-opacity-90 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if isLoading}
						{$_('common.loading')}
					{:else}
						{$_('auth.login')}
					{/if}
				</button>

				<!-- Register Link -->
				<div class="text-center pt-2 text-xs text-gray-600">
					<span>{$_('auth.noAccount')} </span>
					<a href="/register" class="font-bold text-libre-dark hover:underline">{$_('auth.registerHere')}</a>
				</div>

			</form>
		</div>
	</div>
</div>
