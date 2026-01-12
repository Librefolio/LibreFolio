<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {Menu} from 'lucide-svelte';
    import LanguageSelector from '$lib/components/LanguageSelector.svelte';

    const dispatch = createEventDispatcher();

    function toggleSidebar() {
        dispatch('toggleSidebar');
    }
</script>

<header class="sticky top-0 z-30 bg-libre-beige border-b border-gray-200 px-4 py-3">
    <div class="flex items-center justify-between">
        <!-- Mobile menu button -->
        <button
                aria-label="Toggle menu"
                class="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
                on:click={toggleSidebar}
        >
            <Menu class="text-libre-dark" size={24}/>
        </button>

        <!-- Spacer for desktop (sidebar visible) -->
        <div class="hidden lg:block"></div>

        <!-- Right side - Language Selector -->
        <div class="flex items-center">
            <LanguageSelector variant="dropdown"/>
        </div>
    </div>
</header>

