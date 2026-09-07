<!--
  UserSearchSelect.svelte - Svelte 5

  User picker built on SearchSelect with inline search: opening the dropdown
  shows the full user list immediately, and typing narrows it down client-side.
  Used by broker sharing to pick the user to grant access to.
-->
<script lang="ts">
    import {SearchSelect, type SelectOption} from '$lib/components/ui/select';
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';
    import {_} from '$lib/i18n';

    /** Minimal user info needed by the picker. */
    interface UserSelectItem {
        id: number;
        username: string;
        avatar_url: string | null;
    }

    interface Props {
        users: UserSelectItem[];
        value: number | null;
        placeholder?: string;
        disabled?: boolean;
        loading?: boolean;
        dropdownPosition?: 'top' | 'bottom' | 'auto';
        maxVisibleItems?: number;
        testId?: string;
        onchange?: (userId: number | null) => void;
    }

    let {users, value = $bindable(null), placeholder = '', disabled = false, loading = false, dropdownPosition = 'auto', maxVisibleItems = 6, testId, onchange}: Props = $props();

    let userOptions: SelectOption[] = $derived(
        users.map((u) => ({
            value: String(u.id),
            label: u.username,
            searchText: u.username,
            data: u,
        })),
    );

    let stringValue = $derived(value != null ? String(value) : '');

    function asUser(data: unknown): UserSelectItem {
        return data as UserSelectItem;
    }

    /** First character of the username, used when the user has no avatar. */
    function getAvatarInitial(username: string): string {
        return username.charAt(0).toUpperCase();
    }

    function handleChange(newValue: string) {
        const numericValue = newValue ? parseInt(newValue, 10) : null;
        value = numericValue;
        onchange?.(numericValue);
    }
</script>

<SearchSelect {disabled} {dropdownPosition} inlineSearch={true} {loading} {maxVisibleItems} onchange={handleChange} options={userOptions} placeholder={placeholder || $_('brokers.sharing.searchPlaceholder')} {testId} value={stringValue}>
    {#snippet item(option)}
        {@const user = asUser(option.data)}
        <div class="flex items-center gap-2 min-w-0">
            <span class="w-6 h-6 rounded-full overflow-hidden shrink-0">
                {#if user.avatar_url}
                    <LazyImage src="{user.avatar_url}?img_preview=48x48" alt={user.username} circle />
                {:else}
                    <span class="w-full h-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center rounded-full">
                        <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(user.username)}</span>
                    </span>
                {/if}
            </span>
            <span class="truncate">{user.username}</span>
        </div>
    {/snippet}
    {#snippet selectedItem(option)}
        {@const user = asUser(option.data)}
        <div class="flex items-center gap-2 min-w-0">
            <span class="w-6 h-6 rounded-full overflow-hidden shrink-0">
                {#if user.avatar_url}
                    <LazyImage src="{user.avatar_url}?img_preview=48x48" alt={user.username} circle />
                {:else}
                    <span class="w-full h-full bg-gray-200 dark:bg-slate-600 flex items-center justify-center rounded-full">
                        <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400">{getAvatarInitial(user.username)}</span>
                    </span>
                {/if}
            </span>
            <span class="truncate text-sm font-medium text-gray-700 dark:text-gray-200">{user.username}</span>
        </div>
    {/snippet}
</SearchSelect>
