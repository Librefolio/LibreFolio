<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { ShieldCheck } from 'lucide-svelte';
	import { _ } from '$lib/i18n';
	import { auth, authError, isAuthLoading } from '$lib/stores/auth';
	import { goto } from '$app/navigation';

	const dispatch = createEventDispatcher<{
		gotoRegister: void;
		gotoForgot: void;
	}>();

	export let redirectTo = '/dashboard';
	export let successMessage = '';

	let username = '';
	let password = '';

	async function handleSubmit() {
		const success = await auth.login(username, password);
		if (success) {
			goto(redirectTo);
		}
	}
</script>

<div class="w-full max-w-lg bg-libre-beige rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans">

	<!-- Header Section (Dark Green) -->
	<div class="bg-libre-green p-8 flex flex-col items-center justify-center space-y-3">
		<div class="flex items-center space-x-2 text-white">
			<ShieldCheck size={32} />
			<span class="text-2xl font-bold tracking-wide">LibreFolio</span>
		</div>
	</div>

	<!-- Body Section (Beige) -->
	<div class="p-8 pt-10">
		<form on:submit|preventDefault={handleSubmit} class="space-y-5">

			<!-- Success Message (from registration) -->
			{#if successMessage}
				<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-2 rounded-lg text-sm">
					{successMessage}
				</div>
			{/if}

			<!-- Error Message -->
			{#if $authError}
				<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded-lg text-sm">
					{$authError}
				</div>
			{/if}

			<!-- Username Input -->
			<div class="relative">
				<input
					type="text"
					placeholder={$_('auth.usernameOrEmail')}
					bind:value={username}
					disabled={$isAuthLoading}
					autocomplete="username"
					class="w-full px-4 py-3 rounded-lg border border-gray-400 bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green transition-all disabled:opacity-50"
				/>
			</div>

			<!-- Password Input -->
			<div class="relative">
				<input
					type="password"
					placeholder={$_('auth.password')}
					bind:value={password}
					disabled={$isAuthLoading}
					autocomplete="current-password"
					class="w-full px-4 py-3 rounded-lg border border-gray-400 bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green transition-all disabled:opacity-50"
				/>
			</div>

			<!-- Forgot Password Link -->
			<div class="flex justify-end">
				<button
					type="button"
					on:click={() => dispatch('gotoForgot')}
					class="text-xs font-semibold text-libre-dark hover:text-libre-green underline decoration-1 underline-offset-2"
				>
					{$_('auth.forgotPassword')}
				</button>
			</div>

			<!-- Login Button -->
			<button
				type="submit"
				disabled={$isAuthLoading}
				class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:bg-opacity-90 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{#if $isAuthLoading}
					{$_('common.loading')}
				{:else}
					{$_('auth.login')}
				{/if}
			</button>

			<!-- Register Link -->
			<div class="text-center pt-2 text-xs text-gray-600">
				<span>{$_('auth.noAccount')} </span>
				<button
					type="button"
					on:click={() => dispatch('gotoRegister')}
					class="font-bold text-libre-dark hover:underline"
				>
					{$_('auth.registerHere')}
				</button>
			</div>

		</form>
	</div>
</div>

