<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { initI18n, i18nLoading } from '$lib/i18n';
	import { currentLanguage } from '$lib/stores/language';

	// Initialize i18n
	initI18n();

	onMount(() => {
		// Sync language store with i18n after mount
		currentLanguage.init();
	});
</script>

{#if $i18nLoading}
	<!-- Show loading while translations load -->
	<div class="min-h-screen flex items-center justify-center bg-libre-beige">
		<div class="text-libre-green text-xl">Loading...</div>
	</div>
{:else}
	<div class="min-h-screen">
		<slot />
	</div>
{/if}
