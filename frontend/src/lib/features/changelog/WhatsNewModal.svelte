<!--
  WhatsNewModal — «What's new since your last version» (C-54): the released changelog chapters the user has not seen,
  once, after an update. DeferredAppPopups opens it, first among the automatic popups; every close (button, Esc,
  backdrop) marks the running release seen. Each chapter in the interface language where the bundle translates it, in
  English otherwise with the pill of ChangelogModal; the bodies through the same Markdown, always sanitised.
-->
<script lang="ts">
    import {_, locale} from '$lib/i18n';
    import {marked} from 'marked';
    import {ExternalLink, Sparkles} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {CHANGELOG_REMOTE_URL, baseLanguage, localizedChangelog, type DisplayedChapter} from './changelog';
    import {whatsNew} from './whatsNewStore.svelte';

    /** The interface language: a chapter shown in another language carries the pill. */
    const uiLanguage = $derived(baseLanguage($locale));
    /** The last translation loaded, for the language it was for. */
    let loaded = $state<{language: string; chapters: DisplayedChapter[]} | null>(null);
    const localized = $derived(localizedChangelog.peek(uiLanguage) ?? (loaded?.language === uiLanguage ? loaded.chapters : undefined));

    // While the modal is open, fetch the interface language's translation once (a lazy chunk), as ChangelogModal does.
    $effect(() => {
        if (!whatsNew.shouldShow) return;
        const language = uiLanguage;
        if (localizedChangelog.peek(language)) return;
        let live = true;
        localizedChangelog.load(language).then((result) => {
            if (live) loaded = {language, chapters: result};
        });
        return () => {
            live = false;
        };
    });

    /** The pending chapters, each in the interface language where the bundle has it, English until then. */
    const chapters: DisplayedChapter[] = $derived(whatsNew.chapters.map((chapter) => localized?.find((item) => item.version === chapter.version) ?? {...chapter, lang: 'en'}));
    const since = $derived(whatsNew.pending?.since ?? null);
    const release = $derived(whatsNew.pending?.release ?? '');

    /** marked's HTML of a chapter body: the template sanitises it at the sink, as the gate wants. */
    function renderMarkdown(body: string): string {
        return marked.parse(body, {async: false}) as string;
    }
</script>

<ModalBase open={whatsNew.shouldShow} onRequestClose={() => whatsNew.dismiss()} maxWidth="2xl" testId="whats-new-modal" labelledBy="whats-new-title">
    <div class="flex max-h-[85vh] flex-col">
        <header class="shrink-0 border-b border-lf-subtle px-6 pb-3 pt-5">
            <h2 class="flex items-center gap-2 text-lg font-semibold text-lf-primary" id="whats-new-title">
                <Sparkles class="h-5 w-5 text-lf-link" />{$_('changelog.whatsNew.title')}
            </h2>
            <p class="mt-1 text-sm text-lf-muted">{since ? $_('changelog.whatsNew.intro') : $_('changelog.whatsNew.introRelease', {values: {version: release}})}</p>
        </header>
        <div class="flex-1 space-y-6 overflow-y-auto px-6 py-4">
            {#each chapters as chapter (chapter.version)}
                <section data-testid="whats-new-chapter" data-version={chapter.version}>
                    <h3 class="flex flex-wrap items-baseline gap-2 text-base font-semibold text-lf-primary">
                        <span>{chapter.version}</span>
                        {#if chapter.date}<span class="text-sm font-normal text-lf-muted">{chapter.date}</span>{/if}
                        {#if chapter.lang !== uiLanguage}
                            <span class="rounded-full border border-lf-subtle px-2 py-0.5 text-xs font-normal text-lf-muted" data-testid="whats-new-not-translated">{$_('changelog.notTranslated')}</span>
                        {/if}
                    </h3>
                    <div class="whats-new-body mt-2 text-sm leading-relaxed text-lf-secondary">
                        {@html sanitizeHtml(renderMarkdown(chapter.body))}
                    </div>
                </section>
            {/each}
        </div>
        <footer class="flex shrink-0 items-center justify-between gap-3 border-t border-lf-subtle px-6 py-3">
            <a class="inline-flex items-center gap-1 text-sm text-lf-link hover:underline" data-testid="whats-new-full-changelog" href={CHANGELOG_REMOTE_URL} rel="noopener noreferrer" target="_blank">
                <ExternalLink class="h-3.5 w-3.5" />{$_('changelog.whatsNew.fullChangelog')}
            </a>
            <button class="rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action transition-colors hover:bg-lf-action-hover" data-testid="whats-new-close" onclick={() => whatsNew.dismiss()} type="button">
                {$_('changelog.whatsNew.close')}
            </button>
        </footer>
    </div>
</ModalBase>

<style>
    /* The Markdown of the chapters, on the colour roles: the typography of ChangelogModal's bodies. */
    .whats-new-body :global(h3),
    .whats-new-body :global(h4) {
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.75rem 0 0.25rem;
        color: var(--lf-text-primary);
    }

    .whats-new-body :global(ul) {
        list-style: disc;
        padding-left: 1.25rem;
        margin: 0.4rem 0;
    }

    .whats-new-body :global(li) {
        margin: 0.2rem 0;
    }

    .whats-new-body :global(p) {
        margin: 0.4rem 0;
    }

    .whats-new-body :global(a) {
        color: var(--lf-link);
        text-decoration: underline;
    }

    .whats-new-body :global(code) {
        font-size: 0.8em;
        background: var(--lf-surface-panel);
        border: 1px solid var(--lf-border-subtle);
        color: var(--lf-text-primary);
        padding: 0.1em 0.3em;
        border-radius: 0.25rem;
    }

    .whats-new-body :global(blockquote) {
        border-left: 3px solid var(--lf-border-subtle);
        padding-left: 0.75rem;
        margin: 0.5rem 0;
        color: var(--lf-text-muted);
    }
</style>
