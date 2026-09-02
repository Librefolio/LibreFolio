<!--
  UpdateAvailableModal — F14: tells an admin that a newer stable LibreFolio
  release exists. Shown at most once per login (probe throttled to once/24h,
  see updateCheck.ts). Two ways out: "later" (prompts again next login) or
  "skip this version" (never prompts for that version again). Links point to
  the updating guide (locale-aware mkdocs) and to the GitHub release page.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {ArrowRight, ArrowUpCircle, BookOpen, ExternalLink} from 'lucide-svelte';
    import {getStringBadgeStyle} from '$lib/utils/colors';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';

    interface Props {
        /** Version currently running, e.g. "0.10.0". */
        currentVersion: string;
    }

    let {currentVersion}: Props = $props();

    let release = $derived(updateAvailable.release);

    /** Updating guide, locale-prefixed like HelpMenu.mkdocsUrl, deep-linked to the
     *  stable {#updating} anchor (added to all four locales' installation pages). */
    function updatingGuideUrl(): string {
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        return `/mkdocs/${prefix}user/installation/#updating`;
    }
</script>

<ModalBase open={release !== null} onRequestClose={() => updateAvailable.close()} maxWidth="md" testId="update-available-modal">
    {#if release}
        <div class="px-6 py-6 flex flex-col gap-3 bg-libre-beige dark:bg-slate-800">
            <div class="flex items-center gap-3">
                <ArrowUpCircle size={28} class="text-libre-green dark:text-green-400 shrink-0" />
                <h2 class="text-lg font-semibold text-libre-dark dark:text-slate-100">{$_('updateCheck.title')}</h2>
            </div>
            <p class="text-sm text-slate-600 dark:text-slate-300 leading-relaxed" data-testid="update-available-message">
                {$_('updateCheck.message', {values: {latest: release.version, current: currentVersion}})}
            </p>
            <!-- Version badges: current → latest (round 7); colors from the
                 shared golden-ratio palette so the two are always distinct
                 and readable in both themes (round 7 fix). Centered row. -->
            <div class="flex items-center justify-center gap-2" data-testid="update-available-versions">
                <span class="version-badge px-2.5 py-1 rounded-lg font-mono text-xs font-medium" style={getStringBadgeStyle('installed')} data-testid="update-available-current">{currentVersion.startsWith('v') ? currentVersion : `v${currentVersion}`}</span>
                <ArrowRight size={16} class="text-libre-green dark:text-green-400 shrink-0" />
                <span class="version-badge px-2.5 py-1 rounded-lg font-mono text-xs font-semibold" style={getStringBadgeStyle('latest-release')} data-testid="update-available-latest">v{release.version}</span>
            </div>
            <div class="flex flex-col gap-1.5 text-sm">
                <a href={updatingGuideUrl()} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 font-medium text-libre-green dark:text-green-400 hover:underline" data-testid="update-available-guide">
                    <BookOpen size={15} />
                    {$_('updateCheck.guideLink')}
                </a>
                <a href={release.url} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400 hover:underline" data-testid="update-available-release">
                    <ExternalLink size={14} />
                    {$_('updateCheck.releaseLink')}
                </a>
            </div>
        </div>

        <div class="flex flex-col sm:flex-row gap-2 px-6 py-4 bg-libre-beige dark:bg-slate-800 border-t border-black/5 dark:border-white/10">
            <button type="button" class="order-2 sm:order-1 flex-1 px-4 py-2.5 text-sm font-medium rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors" onclick={() => updateAvailable.skipVersion()} data-testid="update-available-skip">
                {$_('updateCheck.skipVersion')}
            </button>
            <button type="button" class="order-1 sm:order-2 flex-1 px-4 py-2.5 text-sm font-medium rounded-lg bg-libre-green text-white hover:bg-primary-600 transition-colors" onclick={() => updateAvailable.close()} data-testid="update-available-later">
                {$_('updateCheck.laterButton')}
            </button>
        </div>
    {/if}
</ModalBase>

<style>
    /* Version badges consume the shared golden-ratio palette's CSS custom
       properties (see $lib/utils/colors.getStringBadgeStyle). */
    .version-badge {
        background: var(--badge-bg, #e2e8f0);
        color: var(--badge-text, #334155);
    }

    :global(html.dark) .version-badge {
        background: var(--badge-dark-bg, #334155);
        color: var(--badge-dark-text, #e2e8f0);
    }
</style>
