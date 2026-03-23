<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import {i18nLoading, initI18n} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {auth, isAuthenticated, isAuthInitialized} from '$lib/stores/auth';
    import {userSettings} from '$lib/stores/settings';
    import {globalSettings} from '$lib/stores/globalSettings';
    import {debug} from '$lib/debug';
    import {getUserStorage} from '$lib/utils/storage';
    import Sidebar from '$lib/components/layout/Sidebar.svelte';
    import Header from '$lib/components/layout/Header.svelte';
    import ToastContainer from '$lib/components/ui/ToastContainer.svelte';

    // Sidebar state for mobile
    let sidebarOpen = false;

    // Sidebar collapsed state
    let sidebarCollapsed = false;

    // Initialize i18n
    initI18n();

    onMount(async () => {
        debug.log('AppLayout', 'onMount started');

        // Sync language store with i18n after mount
        currentLanguage.init();

        // Load sidebar collapsed state from user-scoped localStorage
        if (browser) {
            const saved = getUserStorage('sidebar-collapsed', 'false');
            sidebarCollapsed = saved === 'true';
        }

        // Check authentication with timeout
        if (browser) {
            debug.log('AppLayout', 'Starting auth check');

            // Create a timeout promise
            const timeoutPromise = new Promise<boolean>((_, reject) => {
                setTimeout(() => reject(new Error('Auth check timeout')), 5000);
            });

            try {
                // Race between auth check and timeout
                const isAuth = await Promise.race([
                    auth.checkAuth(),
                    timeoutPromise
                ]);

                debug.log('AppLayout', 'Auth check result:', isAuth);

                if (!isAuth) {
                    debug.log('AppLayout', 'Not authenticated, redirecting to /');
                    goto('/');
                } else {
                    // Load settings stores after successful auth
                    debug.log('AppLayout', 'Loading user and global settings');
                    await Promise.all([
                        userSettings.load(),
                        globalSettings.load()
                    ]);
                }
            } catch (error) {
                debug.error('AppLayout', 'Auth check failed:', error);
                goto('/');
            }
        }
    });

    // Reactive redirect when auth state changes after initialization
    $: if (browser && $isAuthInitialized && !$isAuthenticated) {
        debug.log('AppLayout', 'Reactive redirect triggered');
        goto('/');
    }

    function toggleSidebar() {
        sidebarOpen = !sidebarOpen;
    }
</script>

{#if $i18nLoading}
    <!-- Loading screen while translations load -->
    <div class="min-h-screen flex items-center justify-center bg-libre-beige dark:bg-slate-900">
        <div class="text-libre-green dark:text-green-400 text-xl">Loading...</div>
    </div>
{:else if $isAuthenticated}
    <div class="min-h-screen bg-libre-beige dark:bg-slate-900">
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
    <ToastContainer />
{:else}
    <!-- Loading while checking auth -->
    <div class="min-h-screen flex items-center justify-center bg-libre-beige dark:bg-slate-900">
        <div class="text-libre-green dark:text-green-400 text-xl">Checking authentication...</div>
    </div>
{/if}

