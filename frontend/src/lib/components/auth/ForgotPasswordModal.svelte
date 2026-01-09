<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { ShieldCheck, ArrowLeft, Terminal, AlertTriangle } from 'lucide-svelte';
	import { _ } from '$lib/i18n';

	const dispatch = createEventDispatcher<{
		gotoLogin: void;
	}>();
</script>

<div class="w-full max-w-lg bg-libre-beige rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans">

	<!-- Header Section (Dark Green) -->
	<div class="bg-libre-green p-8 flex flex-col items-center justify-center space-y-2">
		<div class="flex items-center space-x-2 text-white">
			<ShieldCheck size={32} />
			<span class="text-2xl font-bold tracking-wide">LibreFolio</span>
		</div>
		<span class="text-white/80 text-sm">{$_('auth.passwordRecovery')}</span>
	</div>

	<!-- Body Section -->
	<div class="p-8 pt-6 space-y-4">

		<!-- Warning Box -->
		<div class="bg-yellow-50 border border-yellow-300 rounded-lg p-4 flex items-start space-x-3">
			<AlertTriangle class="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
			<p class="text-sm text-yellow-800">
				{$_('auth.emailRecoveryNotAvailable')}
			</p>
		</div>

		<!-- Instructions Box -->
		<div class="bg-gray-100 rounded-lg p-4 space-y-3">
			<div class="flex items-center space-x-2 text-gray-700">
				<Terminal size={18} />
				<span class="font-medium text-sm">{$_('auth.serverTerminalInstructions')}</span>
			</div>

			<div class="bg-gray-800 text-green-400 font-mono text-sm p-3 rounded-lg overflow-x-auto">
				<code>./dev.sh user:reset &lt;username&gt; &lt;new_password&gt;</code>
			</div>

			<p class="text-xs text-gray-500">
				{$_('auth.contactAdministrator')}
			</p>
		</div>

		<!-- Back to Login Button -->
		<button
			type="button"
			on:click={() => dispatch('gotoLogin')}
			class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:bg-opacity-90 transition-all active:scale-[0.98] flex items-center justify-center space-x-2"
		>
			<ArrowLeft size={18} />
			<span>{$_('auth.backToLogin')}</span>
		</button>

	</div>
</div>

