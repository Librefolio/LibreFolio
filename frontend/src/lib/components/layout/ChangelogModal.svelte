<!--
  ChangelogModal — F12: opens from the version label in the sidebar and shows
  the bundled CHANGELOG.md split into per-release chapters (rendered markdown),
  plus a link to the live file on GitHub.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {marked} from 'marked';
    import {ExternalLink} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {CHANGELOG_REMOTE_URL, changelogChapters} from '$lib/features/changelog/changelog';

    interface Props {
        open: boolean;
        onClose: () => void;
    }

    let {open, onClose}: Props = $props();

    function renderChapter(body: string): string {
        return marked.parse(body, {async: false}) as string;
    }
</script>

<ModalBase {open} onRequestClose={onClose} maxWidth="4xl" testId="changelog-modal">
    <div class="bg-white dark:bg-slate-800 rounded-xl flex flex-col max-h-[85vh]">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{$_('changelog.title')}</h2>
            <a href={CHANGELOG_REMOTE_URL} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 text-xs font-medium text-libre-green dark:text-green-400 hover:underline" data-testid="changelog-remote-link">
                <ExternalLink size={13} />
                {$_('changelog.viewRemote')}
            </a>
        </div>

        <!-- Chapters -->
        <div class="flex-1 overflow-y-auto p-4 space-y-6" data-testid="changelog-chapters">
            {#if changelogChapters.length === 0}
                <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="changelog-empty">{$_('changelog.empty')}</p>
            {:else}
                {#each changelogChapters as chapter (chapter.version + chapter.date)}
                    <section data-testid="changelog-chapter">
                        <header class="flex items-baseline gap-2 mb-2 sticky top-0 bg-white dark:bg-slate-800 py-1 border-b border-gray-100 dark:border-slate-700">
                            <h3 class="text-base font-semibold text-libre-green dark:text-green-400">v{chapter.version}</h3>
                            <span class="text-xs text-gray-400 dark:text-gray-500">{chapter.date}</span>
                        </header>
                        <div class="changelog-body text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                            {@html renderChapter(chapter.body)}
                        </div>
                    </section>
                {/each}
            {/if}
        </div>
    </div>
</ModalBase>

<style>
    /* Minimal markdown typography for the bundled changelog (trusted content —
       the file ships with the app build). */
    .changelog-body :global(h3) {
        font-size: 0.95rem;
        font-weight: 600;
        margin: 0.75rem 0 0.25rem;
        color: inherit;
    }

    .changelog-body :global(h4) {
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.6rem 0 0.2rem;
        color: inherit;
    }

    .changelog-body :global(ul) {
        list-style: disc;
        padding-left: 1.25rem;
        margin: 0.4rem 0;
    }

    .changelog-body :global(li) {
        margin: 0.2rem 0;
    }

    .changelog-body :global(p) {
        margin: 0.4rem 0;
    }

    .changelog-body :global(a) {
        color: #1a4031;
        text-decoration: underline;
    }

    :global(html.dark) .changelog-body :global(a) {
        color: #4ade80;
    }

    .changelog-body :global(code) {
        font-size: 0.8em;
        background: rgba(0, 0, 0, 0.05);
        padding: 0.1em 0.3em;
        border-radius: 0.25rem;
    }

    :global(html.dark) .changelog-body :global(code) {
        background: rgba(255, 255, 255, 0.08);
    }

    .changelog-body :global(blockquote) {
        border-left: 3px solid #d1d5db;
        padding-left: 0.75rem;
        margin: 0.5rem 0;
        color: #6b7280;
    }
</style>
