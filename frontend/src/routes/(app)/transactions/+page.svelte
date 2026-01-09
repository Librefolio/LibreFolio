<script lang="ts">
	import { _ } from '$lib/i18n';
	import { ArrowRightLeft, Plus, Upload } from 'lucide-svelte';
</script>

<div class="space-y-6">
	<!-- Header with actions -->
	<div class="flex items-center justify-between flex-wrap gap-4">
		<div>
			<h2 class="text-lg font-semibold text-gray-700">{$_('transactions.title')}</h2>
			<p class="text-gray-500 text-sm">{$_('transactions.subtitle')}</p>
		</div>
		<div class="flex items-center space-x-2">
			<button class="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all">
				<Upload size={18} />
				<span>{$_('transactions.import')}</span>
			</button>
			<button class="flex items-center space-x-2 px-4 py-2 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-all">
				<Plus size={18} />
				<span>{$_('transactions.addTransaction')}</span>
			</button>
		</div>
	</div>

	<!-- Placeholder -->
	<div class="bg-white rounded-xl shadow-sm p-12 text-center border border-gray-100">
		<div class="inline-flex items-center justify-center w-16 h-16 bg-purple-100 rounded-full mb-4">
			<ArrowRightLeft class="text-purple-600" size={32} />
		</div>
		<h3 class="text-lg font-semibold text-gray-700 mb-2">{$_('common.comingSoon')}</h3>
		<p class="text-gray-500">{$_('transactions.placeholderMessage')}</p>
	</div>
</div>

