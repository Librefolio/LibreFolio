<script lang="ts">
	import { _ } from '$lib/i18n';
	import { currentUser } from '$lib/stores/auth';
	import { User, Mail, Calendar } from 'lucide-svelte';

	// Format date for display
	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '-';
		const date = new Date(dateStr);
		return date.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}
</script>

<div class="space-y-6">
	<h3 class="text-lg font-semibold text-gray-700">{$_('settings.profileInfo')}</h3>

	<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
		<!-- Username -->
		<div class="space-y-2">
			<label class="flex items-center text-sm font-medium text-gray-600">
				<User size={16} class="mr-2" />
				{$_('auth.username')}
			</label>
			<div class="px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
				{$currentUser?.username || '-'}
			</div>
		</div>

		<!-- Email -->
		<div class="space-y-2">
			<label class="flex items-center text-sm font-medium text-gray-600">
				<Mail size={16} class="mr-2" />
				{$_('auth.email')}
			</label>
			<div class="px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
				{$currentUser?.email || '-'}
			</div>
		</div>

		<!-- Account Created -->
		<div class="space-y-2">
			<label class="flex items-center text-sm font-medium text-gray-600">
				<Calendar size={16} class="mr-2" />
				{$_('settings.accountCreated')}
			</label>
			<div class="px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
				{formatDate($currentUser?.created_at)}
			</div>
		</div>
	</div>

	<!-- Future: Change Password Section -->
	<div class="mt-8 pt-6 border-t border-gray-200">
		<h4 class="text-md font-medium text-gray-600 mb-4">{$_('settings.security')}</h4>
		<p class="text-gray-500 text-sm">
			{$_('settings.changePasswordInfo')}
		</p>
		<button
			disabled
			class="mt-4 px-4 py-2 bg-gray-100 text-gray-400 rounded-lg cursor-not-allowed"
		>
			{$_('settings.changePassword')} ({$_('common.comingSoon')})
		</button>
	</div>
</div>

