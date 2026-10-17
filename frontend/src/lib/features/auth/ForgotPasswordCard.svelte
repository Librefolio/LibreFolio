<script lang="ts">
    import {createEventDispatcher, onMount} from 'svelte';
    import {AlertTriangle, ArrowLeft, ChevronDown, Terminal, UserCog} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import ForgotPasswordEmailForm from '$lib/features/email/ForgotPasswordEmailForm.svelte';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

    type _DispatchEvents = {
        gotoLogin: void;
    };
    const dispatch = createEventDispatcher();

    // Workstream E: with an email with a link able to go out, the reset link comes by email, and the commands, for
    // whoever runs the server, stay in a panel closed by default (developer's decision P1, 16/10). The sign-in page
    // loads the configuration already: this shares its request.
    onMount(() => {
        void instanceConfig.load();
    });

    let commandsOpen = false;
    // The server commands are for whoever runs the server: shown once the server said self-hosted. A managed instance's
    // users have no terminal: they ask their administrator for a reset link (F05). Before the answer, neither.
</script>

<div class="w-full max-w-lg bg-lf-card text-lf-primary border border-lf-raised rounded-2xl shadow-2xl shadow-lf-shadow overflow-hidden flex flex-col font-sans" data-testid="forgot-modal">
    <!-- Header Section (Dark Green) -->
    <div class="bg-lf-brand p-8 flex flex-col items-center justify-center space-y-2">
        <div class="flex items-center space-x-3 text-lf-on-brand">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center p-1 bg-lf-logo">
                <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
            </div>
            <span class="text-2xl font-bold tracking-wide">LibreFolio</span>
        </div>
    </div>

    <!-- Body Section -->
    <div class="p-8 pt-6 space-y-4">
        {#snippet commands()}
            <div class="bg-lf-terminal border border-lf-terminal-line text-lf-terminal-prompt font-mono text-sm p-3 rounded-lg overflow-x-auto" data-testid="forgot-reset-commands">
                <code class="block whitespace-pre text-lf-terminal-comment"># Docker</code>
                <code class="block whitespace-pre">docker compose exec librefolio python dev.py user reset &lt;username&gt; &lt;new_password&gt;</code>
                <code class="block whitespace-pre mt-2 text-lf-terminal-comment"># Manual install</code>
                <code class="block whitespace-pre">./dev.py user reset &lt;username&gt; &lt;new_password&gt;</code>
            </div>

            <p class="text-xs text-lf-muted">
                {$_('auth.contactAdministrator')}
            </p>
        {/snippet}

        {#snippet askAdmin()}
            <div class="bg-lf-panel rounded-lg p-4 flex items-start space-x-3 text-sm text-lf-secondary" data-testid="forgot-ask-admin">
                <UserCog class="text-lf-muted flex-shrink-0 mt-0.5" size={18} />
                <p>{$_('auth.askAdminToResetPassword')}</p>
            </div>
        {/snippet}

        {#if instanceConfig.config.email?.links}
            <!-- Reset link by email (workstream E) -->
            <ForgotPasswordEmailForm />

            {#if instanceConfig.loaded && instanceConfig.config.profile === 'managed'}
                {@render askAdmin()}
            {:else if instanceConfig.loaded}
                <!-- The server commands, in a panel closed by default (developer's decision P1) -->
                <details bind:open={commandsOpen} class="bg-lf-panel rounded-lg" data-testid="forgot-commands-panel">
                    <summary class="flex cursor-pointer list-none items-center justify-between gap-2 rounded-lg p-4 text-lf-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus" data-testid="forgot-commands-toggle">
                        <span class="flex items-center space-x-2">
                            <Terminal size={18} />
                            <span class="font-medium text-sm">{$_('auth.serverTerminalInstructions')}</span>
                        </span>
                        <ChevronDown aria-hidden="true" class="shrink-0 transition-transform {commandsOpen ? 'rotate-180' : ''}" size={16} />
                    </summary>
                    <div class="px-4 pb-4 space-y-3">
                        {@render commands()}
                    </div>
                </details>
            {/if}
        {:else if instanceConfig.loaded && instanceConfig.config.profile === 'managed'}
            {@render askAdmin()}
        {:else if instanceConfig.loaded}
            <!-- Warning Box -->
            <div class="bg-lf-warning-soft border border-lf-warning-line rounded-lg p-4 flex items-start space-x-3" data-testid="forgot-email-unavailable">
                <AlertTriangle class="text-lf-warning flex-shrink-0 mt-0.5" size={20} />
                <p class="text-sm text-lf-warning-on-soft">
                    {$_('auth.emailRecoveryNotAvailable')}
                </p>
            </div>

            <!-- Instructions Box -->
            <div class="bg-lf-panel rounded-lg p-4 space-y-3">
                <div class="flex items-center space-x-2 text-lf-secondary">
                    <Terminal size={18} />
                    <span class="font-medium text-sm">{$_('auth.serverTerminalInstructions')}</span>
                </div>

                {@render commands()}
            </div>
        {/if}

        <!-- Back to Login Button -->
        <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98] flex items-center justify-center space-x-2" data-testid="forgot-back-to-login" on:click={() => dispatch('gotoLogin')} type="button">
            <ArrowLeft size={18} />
            <span>{$_('auth.backToLogin')}</span>
        </button>
    </div>
</div>
