<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from 'svelte-i18n';
	import AnimatedBackground from '$lib/components/AnimatedBackground.svelte';
</script>

<AnimatedBackground />

<div class="min-h-screen flex items-center justify-center p-4">
	<div class="w-full max-w-md bg-libre-beige rounded-2xl shadow-2xl overflow-hidden">
		<!-- Header verde -->
		<div class="bg-libre-green p-6 flex flex-col items-center justify-center">
			<div class="text-6xl text-white mb-2">
				{$page.status}
			</div>
			<div class="text-white text-lg font-semibold">
				{#if $page.status === 404}
					{$_('error.pageNotFound')}
				{:else}
					{$_('error.somethingWentWrong')}
				{/if}
			</div>
		</div>

		<!-- Body -->
		<div class="p-8 text-center">
			<p class="text-gray-600 mb-6">
				{#if $page.status === 404}
					{$_('error.pageNotFoundMessage')}
				{:else}
					{$page.error?.message || $_('error.unexpectedError')}
				{/if}
			</p>

			<div class="flex flex-col space-y-3">
				<a
					href="/dashboard"
					class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:opacity-90 transition-all text-center"
				>
					{$_('error.goToDashboard')}
				</a>
				<a
					href="/"
					class="w-full border border-libre-green text-libre-green font-bold py-3 rounded-lg hover:bg-libre-green hover:text-white transition-all text-center"
				>
					{$_('error.goToHome')}
				</a>
			</div>
		</div>
	</div>
</div>

<style>
	/* Inherits from app.css - no extra styles needed */
</style>

