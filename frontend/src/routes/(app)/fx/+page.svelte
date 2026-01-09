<script lang="ts">
	import { _ } from '$lib/i18n';
	import { Coins, RefreshCw } from 'lucide-svelte';
</script>

<div class="space-y-6">
	<!-- Header with action -->
	<div class="flex items-center justify-between">
		<div>
			<h2 class="text-lg font-semibold text-gray-700">{$_('fx.title')}</h2>
			<p class="text-gray-500 text-sm">{$_('fx.subtitle')}</p>
		</div>
		<button class="flex items-center space-x-2 px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all">
			<RefreshCw size={18} />
			<span>{$_('fx.syncRates')}</span>
		</button>
	</div>

	<!-- Placeholder -->
	<div class="bg-white rounded-xl shadow-sm p-12 text-center border border-gray-100">
		<div class="inline-flex items-center justify-center w-16 h-16 bg-amber-100 rounded-full mb-4">
			<Coins class="text-amber-600" size={32} />
		</div>
		<h3 class="text-lg font-semibold text-gray-700 mb-2">{$_('common.comingSoon')}</h3>
		<p class="text-gray-500">{$_('fx.placeholderMessage')}</p>
	</div>
</div>

