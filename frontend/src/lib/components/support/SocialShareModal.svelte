<script lang="ts">
    import {_} from '$lib/i18n';
    import {locale} from 'svelte-i18n';
    import {Check, Copy, Loader2, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {SOCIAL_SHARE_CONFIG, buildSocialShareCopy, buildSocialShareUrl, type SocialPlatform} from './supportLinks';
    import {reserveShareTab, type ShareTab} from './shareNavigation';
    import SocialIcon from './SocialIcon.svelte';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import {onDestroy, onMount} from 'svelte';
    import {getClientSessionGeneration, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';

    interface Props {
        open?: boolean;
        platform: SocialPlatform;
        onClose?: () => void;
    }

    let {open = false, platform = 'x', onClose = () => {}}: Props = $props();

    let copyState = $state<'idle' | 'pending' | 'copied' | 'error'>('idle');
    let copyError = $state<string | null>(null);
    let copyErrorKind = $state<'copy' | 'navigation'>('copy');
    let resetTimer: ReturnType<typeof setTimeout> | null = null;
    let pendingTab: ShareTab | null = null;
    let copySequence = 0;
    let alive = true;
    const titleId = $props.id();

    let shareConfig = $derived(SOCIAL_SHARE_CONFIG[platform]);
    let shareMessage = $derived($_(shareConfig.messageKey));
    let shareHint = $derived($_(shareConfig.hintKey));
    let shareTitle = $derived(platform === 'reddit' ? $_('support.share.reddit.title') : undefined);

    function closePendingTab() {
        const tab = pendingTab;
        pendingTab = null;
        if (tab && !tab.closed) tab.close();
    }

    function resetCopyState() {
        copySequence++;
        closePendingTab();
        copyState = 'idle';
        copyError = null;
        if (resetTimer) {
            clearTimeout(resetTimer);
            resetTimer = null;
        }
    }

    function handleClose() {
        resetCopyState();
        onClose();
    }

    function selectAll(event: Event) {
        const target = event.currentTarget as HTMLInputElement | HTMLTextAreaElement | null;
        target?.select();
    }

    function reportNavigationFailure(requestedPlatform: SocialPlatform, reason: string) {
        copyState = 'error';
        copyErrorKind = 'navigation';
        copyError = $_('support.navigationFailed');
        notify({
            name: 'support.social.open.failed',
            detail: {platform: requestedPlatform, reason, copied: true},
            toast: {variant: 'warning', message: copyError},
        });
    }

    async function copyAndGo() {
        if (copyState === 'pending') return;
        resetCopyState();
        const sequence = ++copySequence;
        const generation = getClientSessionGeneration();
        const requestedPlatform = platform;
        const requestedLocale = $locale;
        const message = shareMessage;
        const title = shareTitle;
        const isCurrent = () => alive && open && sequence === copySequence && platform === requestedPlatform && $locale === requestedLocale && shareMessage === message && shareTitle === title && isClientSessionCurrent(generation);
        const payload = buildSocialShareCopy(message);
        const destination = buildSocialShareUrl(requestedPlatform, message, title);
        copyState = 'pending';
        copyError = null;
        let tab: ShareTab | null = null;
        let reservationFailed = false;

        try {
            // Start copying while this document still has focus; reserve the new
            // tab within the same user gesture, before awaiting clipboard access.
            const copying = writeTextToClipboard(payload);
            try {
                tab = reserveShareTab();
                pendingTab = tab;
            } catch {
                reservationFailed = true;
            }
            await copying;
        } catch (error) {
            if (pendingTab === tab) closePendingTab();
            if (!isCurrent()) return;
            copyState = 'error';
            copyErrorKind = 'copy';
            copyError = $_('support.clipboardUnavailable');
            notify({
                name: 'support.social.copy.failed',
                detail: {platform: requestedPlatform, reason: error instanceof Error ? error.message : 'clipboard unavailable'},
                toast: {variant: 'error', message: $_('support.clipboardUnavailable')},
            });
            return;
        }

        if (!isCurrent()) {
            if (pendingTab === tab) closePendingTab();
            return;
        }
        notify({name: 'support.social.copy.copied', detail: {platform: requestedPlatform}});
        if (!tab || tab.closed) {
            if (pendingTab === tab) closePendingTab();
            reportNavigationFailure(requestedPlatform, reservationFailed ? 'reservation-failed' : tab ? 'closed' : 'blocked');
            return;
        }
        try {
            tab.navigate(destination);
            pendingTab = null;
        } catch {
            closePendingTab();
            reportNavigationFailure(requestedPlatform, 'navigation-failed');
            return;
        }
        copyState = 'copied';
        notify({
            name: 'support.social.open.requested',
            detail: {platform: requestedPlatform},
            toast: {variant: 'success', message: $_(SOCIAL_SHARE_CONFIG[requestedPlatform].afterCopyKey ?? 'common.copiedToClipboard')},
        });
        resetTimer = setTimeout(() => {
            copyState = 'idle';
            resetTimer = null;
        }, 2000);
    }

    onMount(() => registerClientSessionReset(`support-share-${titleId}`, resetCopyState));

    onDestroy(() => {
        alive = false;
        resetCopyState();
    });

    $effect(() => {
        void platform;
        void open;
        void $locale;
        void shareMessage;
        void shareTitle;
        resetCopyState();
    });
</script>

<ModalBase {open} onRequestClose={handleClose} maxWidth="2xl" testId="support-social-share-modal" zIndex={60} trapFocus={true} restoreFocus={true} labelledBy={titleId}>
    <div class="flex min-h-0 flex-1 flex-col bg-libre-beige dark:bg-slate-800">
        <div class="flex items-start justify-between gap-4 border-b border-black/5 px-6 py-5 dark:border-white/10 shrink-0">
            <div class="flex min-w-0 flex-1 items-start gap-3">
                <div class={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${shareConfig.brandClass}`} data-testid="support-social-share-badge">
                    <SocialIcon {platform} size={24} />
                </div>
                <div class="min-w-0 flex-1 space-y-1 break-words">
                    <h2 class="text-lg font-semibold text-libre-dark dark:text-slate-100" id={titleId} data-testid="support-social-share-title">
                        {$_('support.shareOn')}
                        {shareConfig.label}
                    </h2>
                    <p class="text-sm leading-relaxed text-slate-600 dark:text-slate-300" data-testid="support-social-share-hint">
                        {shareHint}
                    </p>
                </div>
            </div>

            <button
                type="button"
                class="shrink-0 rounded-lg p-2 text-slate-500 transition-colors hover:bg-black/5 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-100"
                onclick={handleClose}
                data-testid="support-social-share-close-icon"
                aria-label={$_('common.close')}
            >
                <X size={18} />
            </button>
        </div>

        <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-5">
            {#if copyError}
                <div
                    class="rounded-lg border px-4 py-3 text-sm {copyErrorKind === 'navigation'
                        ? 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200'
                        : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-200'}"
                    role="alert"
                    data-testid="support-social-share-error"
                >
                    {copyError}
                </div>
            {/if}

            {#if shareTitle}
                <div class="space-y-2">
                    <label class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400" for="support-social-share-post-title" data-testid="support-social-share-title-label">
                        {$_('support.share.titleLabel')}
                    </label>
                    <input
                        id="support-social-share-post-title"
                        data-testid="support-social-share-post-title"
                        class="w-full rounded-lg border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-700 dark:border-slate-600 dark:bg-slate-900/70 dark:text-slate-100"
                        value={shareTitle}
                        readonly
                        onfocus={selectAll}
                        onclick={selectAll}
                    />
                </div>
            {/if}

            <div class="space-y-2">
                <label class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400" for={`support-social-share-message-${platform}`}>
                    {$_('support.shareMessageLabel')}
                </label>
                <textarea
                    id={`support-social-share-message-${platform}`}
                    class="min-h-32 w-full rounded-lg border border-slate-200 bg-white/90 px-4 py-3 text-sm leading-relaxed text-slate-700 shadow-sm outline-none transition focus:border-libre-green focus:ring-2 focus:ring-libre-green/20 dark:border-slate-600 dark:bg-slate-900/70 dark:text-slate-100"
                    readonly
                    rows="7"
                    spellcheck="false"
                    autocapitalize="off"
                    onfocus={selectAll}
                    onclick={selectAll}
                    value={shareMessage}
                    data-testid="support-social-share-message"
                ></textarea>
            </div>
        </div>

        <div class="border-t border-black/5 px-6 py-4 dark:border-white/10 shrink-0">
            <div class="grid grid-cols-2 gap-2" data-testid="support-social-share-actions">
                <button
                    type="button"
                    class="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white/80 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/20 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent dark:border-slate-600 dark:bg-slate-800/70 dark:text-slate-200 dark:hover:bg-slate-700 dark:focus-visible:ring-offset-slate-800"
                    onclick={handleClose}
                    data-testid="support-social-share-close"
                >
                    <X size={16} />
                    <span>{$_('common.close')}</span>
                </button>

                <button
                    type="button"
                    class={`flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent dark:focus-visible:ring-offset-slate-800 ${shareConfig.brandClass}`}
                    onclick={copyAndGo}
                    data-testid="support-social-share-copy"
                    data-copy-state={copyState}
                    data-social-platform={platform}
                    aria-busy={copyState === 'pending'}
                    disabled={copyState === 'pending'}
                >
                    {#if copyState === 'pending'}
                        <Loader2 size={16} class="animate-spin" />
                    {:else if copyState === 'copied'}
                        <Check size={16} />
                    {:else}
                        <Copy size={16} />
                    {/if}
                    <span>{$_('support.copyAndGo')}</span>
                </button>
            </div>
        </div>
    </div>
</ModalBase>
