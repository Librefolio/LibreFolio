<script lang="ts">
	import { _ } from '$lib/i18n';
	import { User, Sliders, Info } from 'lucide-svelte';
	import ProfileTab from '$lib/components/settings/ProfileTab.svelte';
	import PreferencesTab from '$lib/components/settings/PreferencesTab.svelte';
	import AboutTab from '$lib/components/settings/AboutTab.svelte';

	type TabId = 'profile' | 'preferences' | 'about';

	let activeTab: TabId = 'profile';

	const tabs: { id: TabId; icon: typeof User; labelKey: string }[] = [
		{ id: 'profile', icon: User, labelKey: 'settings.profile' },
		{ id: 'preferences', icon: Sliders, labelKey: 'settings.preferences' },
		{ id: 'about', icon: Info, labelKey: 'settings.about' }
	];
</script>

<div class="space-y-6">
	<!-- Tabs Navigation -->
	<div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
		<div class="flex border-b border-gray-200">
			{#each tabs as tab}
				<button
					on:click={() => (activeTab = tab.id)}
					class="flex items-center space-x-2 px-6 py-4 text-sm font-medium transition-all
						{activeTab === tab.id
						? 'text-libre-green border-b-2 border-libre-green bg-libre-green/5'
						: 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
				>
					<svelte:component this={tab.icon} size={18} />
					<span>{$_(tab.labelKey)}</span>
				</button>
			{/each}
		</div>

		<!-- Tab Content -->
		<div class="p-6">
			{#if activeTab === 'profile'}
				<ProfileTab />
			{:else if activeTab === 'preferences'}
				<PreferencesTab />
			{:else if activeTab === 'about'}
				<AboutTab />
			{/if}
		</div>
	</div>
</div>

