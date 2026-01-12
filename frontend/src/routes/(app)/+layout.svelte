<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import {i18nLoading, initI18n} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {auth, isAuthenticated} from '$lib/stores/auth';
    import Sidebar from '$lib/components/layout/Sidebar.svelte';
    import Header from '$lib/components/layout/Header.svelte';

    // Sidebar state for mobile
    let sidebarOpen = false;

    // Sidebar collapsed state
    let sidebarCollapsed = false;

    // Initialize i18n
    initI18n();

    onMount(async () => {
        // Sync language store with i18n after mount
        currentLanguage.init();

        // Load sidebar collapsed state from localStorage
        if (browser) {
            const saved = localStorage.getItem('sidebar-collapsed');
            if (saved !== null) {
                sidebarCollapsed = saved === 'true';
            }
        }

        // Check authentication
        if (browser) {
            const isAuth = await auth.checkAuth();
            if (!isAuth) {
                goto('/');
            }
        }
    });

    function toggleSidebar() {
        sidebarOpen = !sidebarOpen;
    }
</script>

{#if $i18nLoading}
    <!-- Loading screen while translations load -->
    <div class="min-h-screen flex items-center justify-center bg-libre-beige">
        <div class="text-libre-green text-xl">Loading...</div>
    </div>
{:else if $isAuthenticated}
    <div class="min-h-screen bg-libre-beige">
        <!-- Sidebar -->
        <Sidebar bind:isOpen={sidebarOpen} bind:collapsed={sidebarCollapsed}/>

        <!-- Main Content Area -->
        <div class="min-h-screen flex flex-col transition-all duration-300 {sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}">
            <!-- Header -->
            <Header on:toggleSidebar={toggleSidebar}/>

            <!-- Page Content -->
            <main class="flex-1 p-4 lg:p-6">
                <slot/>
            </main>
        </div>
    </div>
{:else}
    <!-- Loading while checking auth -->
    <div class="min-h-screen flex items-center justify-center bg-libre-beige">
        <div class="text-libre-green text-xl">Checking authentication...</div>
    </div>
{/if}

