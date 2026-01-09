<script lang="ts">
	import { _ } from '$lib/i18n';
	import { currentLanguage } from '$lib/stores/language';
	import { LANGUAGE_OPTIONS, type SupportedLocale } from '$lib/i18n';
	import { Globe, Palette, Coins } from 'lucide-svelte';

	// Theme options (future)
	type Theme = 'light' | 'dark' | 'auto';
	let selectedTheme: Theme = 'light';

	// Base currency (future)
	let baseCurrency = 'EUR';

	function handleLanguageChange(event: Event) {
		const target = event.target as HTMLSelectElement;
		currentLanguage.set(target.value as SupportedLocale);
	}
</script>

<div class="space-y-8">
	<!-- Language -->
	<div class="space-y-3">
		<label class="flex items-center text-sm font-medium text-gray-700">
			<Globe size={18} class="mr-2 text-libre-green" />
			{$_('settings.language')}
		</label>
		<select
			class="w-full max-w-xs px-4 py-3 border border-gray-300 rounded-lg bg-white
				focus:ring-2 focus:ring-libre-green focus:border-libre-green transition-all"
			value={$currentLanguage}
			on:change={handleLanguageChange}
		>
			{#each LANGUAGE_OPTIONS as lang}
				<option value={lang.code}>
					{lang.flag} {lang.name}
				</option>
			{/each}
		</select>
		<p class="text-gray-500 text-sm">{$_('settings.languageHint')}</p>
	</div>

	<!-- Base Currency (future) -->
	<div class="space-y-3">
		<label class="flex items-center text-sm font-medium text-gray-700">
			<Coins size={18} class="mr-2 text-libre-green" />
			{$_('settings.baseCurrency')}
		</label>
		<select
			disabled
			class="w-full max-w-xs px-4 py-3 border border-gray-200 rounded-lg bg-gray-50
				text-gray-400 cursor-not-allowed"
			bind:value={baseCurrency}
		>
			<option value="EUR">🇪🇺 EUR - Euro</option>
			<option value="USD">🇺🇸 USD - US Dollar</option>
			<option value="GBP">🇬🇧 GBP - British Pound</option>
			<option value="CHF">🇨🇭 CHF - Swiss Franc</option>
		</select>
		<p class="text-gray-400 text-sm">{$_('common.comingSoon')}</p>
	</div>

	<!-- Theme (future) -->
	<div class="space-y-3">
		<label class="flex items-center text-sm font-medium text-gray-700">
			<Palette size={18} class="mr-2 text-libre-green" />
			{$_('settings.theme')}
		</label>
		<div class="flex items-center space-x-4">
			{#each [
				{ value: 'light', label: 'settings.themeLight' },
				{ value: 'dark', label: 'settings.themeDark' },
				{ value: 'auto', label: 'settings.themeAuto' }
			] as option}
				<label
					class="flex items-center space-x-2 cursor-not-allowed opacity-50"
				>
					<input
						type="radio"
						name="theme"
						value={option.value}
						bind:group={selectedTheme}
						disabled
						class="w-4 h-4 text-libre-green focus:ring-libre-green"
					/>
					<span class="text-gray-500">{$_(option.label)}</span>
				</label>
			{/each}
		</div>
		<p class="text-gray-400 text-sm">{$_('common.comingSoon')}</p>
	</div>
</div>

