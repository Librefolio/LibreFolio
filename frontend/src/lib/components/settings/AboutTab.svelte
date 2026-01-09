<script lang="ts">
	import { _ } from '$lib/i18n';
	import { ShieldCheck, Github, Scale, Heart } from 'lucide-svelte';

	// Get version from package.json (injected at build time or hardcoded for now)
	const appVersion = '0.1.0';
</script>

<div class="space-y-8">
	<!-- App Info -->
	<div class="flex items-center space-x-4">
		<div class="p-4 bg-libre-green rounded-xl">
			<ShieldCheck class="text-white" size={40} />
		</div>
		<div>
			<h3 class="text-xl font-bold text-gray-800">LibreFolio</h3>
			<p class="text-gray-500">{$_('settings.version')} {appVersion}</p>
		</div>
	</div>

	<!-- Description -->
	<div class="space-y-2">
		<p class="text-gray-600">
			{$_('settings.aboutDescription')}
		</p>
	</div>

	<!-- Links -->
	<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
		<!-- GitHub -->
		<a
			href="https://github.com/your-username/LibreFolio"
			target="_blank"
			rel="noopener noreferrer"
			class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-all"
		>
			<Github size={24} class="text-gray-700" />
			<div>
				<p class="font-medium text-gray-700">GitHub</p>
				<p class="text-sm text-gray-500">{$_('settings.viewSource')}</p>
			</div>
		</a>

		<!-- License -->
		<div class="flex items-center space-x-3 p-4 bg-gray-50 rounded-lg">
			<Scale size={24} class="text-gray-700" />
			<div>
				<p class="font-medium text-gray-700">{$_('settings.license')}</p>
				<p class="text-sm text-gray-500">MIT License</p>
			</div>
		</div>
	</div>

	<!-- Credits -->
	<div class="pt-6 border-t border-gray-200">
		<h4 class="text-md font-medium text-gray-700 mb-4">{$_('settings.credits')}</h4>
		<div class="flex items-center space-x-2 text-gray-500">
			<span>{$_('settings.madeWith')}</span>
			<Heart size={16} class="text-red-500" />
			<span>{$_('settings.usingTech')}</span>
		</div>
		<div class="mt-4 flex flex-wrap gap-2">
			{#each ['Python', 'FastAPI', 'SvelteKit', 'Tailwind CSS', 'SQLite'] as tech}
				<span class="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
					{tech}
				</span>
			{/each}
		</div>
	</div>
</div>

