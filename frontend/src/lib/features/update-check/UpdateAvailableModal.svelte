<!--
  UpdateAvailableModal — F14: tells an admin that a newer stable LibreFolio
  release exists. Shown at most once per login (probe throttled to once/hour,
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

<!-- A requested prompt opens from inside the changelog modal, which lives in the sidebar's
     stacking context at the default modal z-index: above it, not beside it. -->
<ModalBase open={release !== null} onRequestClose={() => updateAvailable.close()} maxWidth="md" testId="update-available-modal" zIndex={updateAvailable.requested ? 60 : 50}>
    {#if release}
        <div class="px-6 py-6 flex flex-col gap-3 bg-lf-card">
            <div class="flex items-center gap-3">
                <ArrowUpCircle size={28} class="text-lf-link shrink-0" />
                <h2 class="text-lg font-semibold text-lf-primary">{$_('updateCheck.title')}</h2>
            </div>
            <p class="text-sm text-lf-secondary leading-relaxed" data-testid="update-available-message">
                {$_('updateCheck.message', {values: {latest: release.version, current: currentVersion}})}
            </p>
            <!-- Version badges: current → latest (round 7); colors from the
                 shared golden-ratio palette so the two are always distinct
                 and readable in both themes (round 7 fix). Centered row. -->
            <div class="flex items-center justify-center gap-2" data-testid="update-available-versions">
                <span class="version-badge px-2.5 py-1 rounded-lg font-mono text-xs font-medium" style={getStringBadgeStyle('installed')} data-testid="update-available-current">{currentVersion.startsWith('v') ? currentVersion : `v${currentVersion}`}</span>
                <ArrowRight size={16} class="text-lf-link shrink-0" />
                <span class="version-badge px-2.5 py-1 rounded-lg font-mono text-xs font-semibold" style={getStringBadgeStyle('latest-release')} data-testid="update-available-latest" data-version={release.version} data-tag={release.tag ?? ''}>{release.tag ?? `v${release.version}`}</span>
            </div>
            <div class="flex flex-col gap-1.5 text-sm">
                <a href={updatingGuideUrl()} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 font-medium text-lf-link hover:underline" data-testid="update-available-guide">
                    <BookOpen size={15} />
                    {$_('updateCheck.guideLink')}
                </a>
                <a href={release.url} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-lf-muted hover:underline" data-testid="update-available-release">
                    <ExternalLink size={14} />
                    {$_('updateCheck.releaseLink')}
                </a>
            </div>
        </div>

        <div class="flex flex-col sm:flex-row gap-2 px-6 py-4 bg-lf-card border-t border-lf-subtle">
            <button type="button" class="order-2 sm:order-1 flex-1 px-4 py-2.5 text-sm font-medium rounded-lg text-lf-muted hover:bg-lf-hover transition-colors" onclick={() => updateAvailable.skipVersion()} data-testid="update-available-skip">
                {$_('updateCheck.skipVersion')}
            </button>
            <button type="button" class="order-1 sm:order-2 flex-1 px-4 py-2.5 text-sm font-medium rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-colors" onclick={() => updateAvailable.close()} data-testid="update-available-later">
                {$_('updateCheck.laterButton')}
            </button>
        </div>
    {/if}
</ModalBase>

<style>
    /* Version badges consume the shared golden-ratio palette's CSS custom
       properties (see $lib/utils/colors.getStringBadgeStyle). */
    .version-badge {
        background: var(--badge-bg, var(--lf-surface-neutral));
        color: var(--badge-text, var(--lf-text-secondary));
    }

    :global(html.dark) .version-badge {
        background: var(--badge-dark-bg, var(--lf-surface-neutral));
        color: var(--badge-dark-text, var(--lf-text-secondary));
    }
</style>
