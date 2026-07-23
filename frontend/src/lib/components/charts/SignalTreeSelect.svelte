<script lang="ts">
    import {ChevronDown, ChevronRight, Search, X} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import SignalOptionContent from './SignalOptionContent.svelte';

    export interface SignalTreeItem {
        value: string;
        icon: string;
        name: string;
        subtitle: string;
        searchText: string;
    }

    export interface SignalTreeGroup {
        key: string;
        label: string;
        subtitle: string;
        items: SignalTreeItem[];
    }

    interface Props {
        value?: string;
        groups: SignalTreeGroup[];
        placeholder?: string;
        testId?: string;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), groups, placeholder = '', testId, onchange}: Props = $props();
    let isOpen = $state(false);
    let query = $state('');
    let expanded = $state(new Set<string>());
    let containerRef = $state<HTMLDivElement | null>(null);
    let inputRef = $state<HTMLInputElement | null>(null);
    let dropdownStyle = $state('');
    const treeId = `signal-tree-${Math.random().toString(36).slice(2, 9)}`;

    let normalizedQuery = $derived(query.trim().toLocaleLowerCase());
    let visibleGroups = $derived(
        groups
            .map((group) => ({
                ...group,
                items: normalizedQuery ? group.items.filter((item) => item.searchText.includes(normalizedQuery)) : group.items,
            }))
            .filter((group) => group.items.length > 0),
    );

    function updatePosition() {
        if (!containerRef) return;
        const rect = containerRef.getBoundingClientRect();
        const width = Math.min(Math.max(rect.width, 390), window.innerWidth - 16);
        const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
        const spaceBelow = window.innerHeight - rect.bottom - 16;
        const openAbove = spaceBelow < 360 && rect.top > spaceBelow;
        dropdownStyle = openAbove ? `position:fixed; bottom:${window.innerHeight - rect.top + 4}px; left:${left}px; width:${width}px; z-index:9999;` : `position:fixed; top:${rect.bottom + 4}px; left:${left}px; width:${width}px; z-index:9999;`;
    }

    function open() {
        updatePosition();
        isOpen = true;
        query = '';
        if (expanded.size === 0 && groups[0]) expanded = new Set([groups[0].key]);
        setTimeout(() => inputRef?.focus(), 0);
    }

    function close() {
        isOpen = false;
        query = '';
    }

    function toggle() {
        if (isOpen) close();
        else open();
    }

    function toggleGroup(groupKey: string) {
        const next = new Set(expanded);
        if (next.has(groupKey)) next.delete(groupKey);
        else next.add(groupKey);
        expanded = next;
    }

    function select(item: SignalTreeItem) {
        value = item.value;
        onchange?.(item.value);
        close();
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            event.preventDefault();
            close();
        } else if (event.key === 'Enter' && visibleGroups.length === 1 && visibleGroups[0].items.length === 1) {
            event.preventDefault();
            select(visibleGroups[0].items[0]);
        }
    }

    $effect(() => {
        if (!isOpen) return;
        const handleOutside = (event: MouseEvent) => {
            if (!containerRef?.contains(event.target as Node)) close();
        };
        const reposition = () => updatePosition();
        document.addEventListener('mousedown', handleOutside, true);
        window.addEventListener('resize', reposition);
        window.addEventListener('scroll', reposition, true);
        return () => {
            document.removeEventListener('mousedown', handleOutside, true);
            window.removeEventListener('resize', reposition);
            window.removeEventListener('scroll', reposition, true);
        };
    });
</script>

<div bind:this={containerRef} class="relative" data-testid={testId}>
    <div
        aria-expanded={isOpen}
        aria-haspopup="tree"
        aria-controls={treeId}
        class="flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-all
            bg-white text-sm text-gray-900 hover:border-gray-400 dark:border-slate-600 dark:bg-slate-700 dark:text-gray-100 dark:hover:border-slate-500
            {isOpen ? 'border-libre-green ring-2 ring-libre-green' : 'border-gray-300'}"
        onclick={toggle}
        onkeydown={(event) => {
            if (!isOpen && (event.key === 'Enter' || event.key === ' ' || event.key.length === 1)) {
                event.preventDefault();
                open();
                if (event.key.length === 1) setTimeout(() => (query = event.key), 0);
            } else {
                handleKeydown(event);
            }
        }}
        role="combobox"
        tabindex="0"
        data-testid={testId ? `${testId}-button` : undefined}
    >
        {#if isOpen}
            <Search size={14} class="shrink-0 text-gray-400" />
            <input
                bind:this={inputRef}
                bind:value={query}
                class="min-w-0 flex-1 border-none bg-transparent text-sm outline-none placeholder:text-gray-400"
                placeholder={$t('signals.selector.searchPlaceholder')}
                onclick={(event) => event.stopPropagation()}
                onkeydown={(event) => {
                    event.stopPropagation();
                    handleKeydown(event);
                }}
            />
            {#if query}
                <button
                    type="button"
                    class="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                    aria-label={$t('common.clear')}
                    onclick={(event) => {
                        event.stopPropagation();
                        query = '';
                        inputRef?.focus();
                    }}
                >
                    <X size={14} />
                </button>
            {/if}
        {:else}
            <span class="text-gray-400">{placeholder || $t('common.select')}</span>
            <ChevronDown size={14} class="shrink-0 text-gray-400" />
        {/if}
    </div>

    {#if isOpen}
        <div class="max-h-[420px] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-800" id={treeId} style={dropdownStyle} role="tree">
            {#if visibleGroups.length === 0}
                <div class="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                    {$t('signals.selector.noMatches')}
                </div>
            {:else}
                {#each visibleGroups as group (group.key)}
                    {@const groupOpen = normalizedQuery !== '' || expanded.has(group.key)}
                    <div class="border-b border-gray-100 last:border-b-0 dark:border-slate-700">
                        <button type="button" class="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-slate-700" aria-expanded={groupOpen} onclick={() => toggleGroup(group.key)}>
                            {#if groupOpen}
                                <ChevronDown size={15} class="mt-0.5 shrink-0 text-gray-400" />
                            {:else}
                                <ChevronRight size={15} class="mt-0.5 shrink-0 text-gray-400" />
                            {/if}
                            <span class="min-w-0">
                                <span class="block text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200">{group.label}</span>
                                <span class="block text-[10px] leading-4 text-gray-400 dark:text-gray-500">{group.subtitle}</span>
                            </span>
                            <span class="ml-auto rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-slate-700 dark:text-gray-400">{group.items.length}</span>
                        </button>
                        {#if groupOpen}
                            <div class="pb-1" role="group">
                                {#each group.items as item (item.value)}
                                    <button type="button" class="w-full px-4 py-2 text-left hover:bg-libre-green/10 dark:hover:bg-libre-green/20" onclick={() => select(item)} data-testid="signal-tree-option-{item.value}">
                                        <SignalOptionContent icon={item.icon} name={item.name} subtitle={item.subtitle} />
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>
                {/each}
            {/if}
        </div>
    {/if}
</div>
