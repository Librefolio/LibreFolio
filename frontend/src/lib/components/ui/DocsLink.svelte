<script lang="ts">
    /**
     * DocsLink — the icon that opens a page of the guide, in a line of text or beside a title (46 places).
     *
     * The standard button (85 BTN-2a, the consultant's C12): `inline` (a hair of padding, the line's text size, a 24 px
     * target for the finger) and `link-muted` (grey at rest, the link's colour on hover: the sign that it opens the
     * guide). Its name is the guide's sentence (`label`, KaTeX with `math`): by long press, mouse rest or Tab, as for
     * every icon alone. It stays a `<button>` opening a new window, not an `<a>`: on a link the long press would be the
     * browser's, and the name would never reach the finger. The `Tooltip` around the old button is gone (D3).
     */
    import {BookOpen, HelpCircle} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import Button from './button/Button.svelte';
    import type {ButtonDisplay, ButtonSize} from './button/buttonClasses';

    interface Props {
        /** MkDocs path (relative to /mkdocs/) */
        path: string;
        /** Localized fallback used when the requested page exists only in English */
        localizedFallbackPath?: string;
        /** The name: the guide's sentence (may contain $...$ LaTeX). Defaults to «Documentation». */
        label?: string;
        /** Icon size in pixels, as the callers wrote it: 11–12 → xs, 14 → sm, 16 → md, 18–20 → lg. */
        size?: number;
        /** Enable KaTeX math rendering in the name */
        math?: boolean;
        /** Icon variant */
        icon?: 'help' | 'book';
        /** Stable E2E selector */
        testId?: string;
        /** The word beside the icon: never (`hidden`), from `sm` up (`responsive`), always (`visible`). */
        labelDisplay?: 'hidden' | 'responsive' | 'visible';
    }

    let {path, localizedFallbackPath, label, size = 12, math = false, icon = 'help', testId, labelDisplay = 'hidden'}: Props = $props();

    let name = $derived(label ?? $_('common.documentation'));
    let buttonSize = $derived<ButtonSize>(size < 14 ? 'xs' : size < 16 ? 'sm' : size < 18 ? 'md' : 'lg');
    let display = $derived<ButtonDisplay>(labelDisplay === 'hidden' ? 'icon' : labelDisplay === 'responsive' ? 'auto' : 'icon-text');

    function getDocsUrl(): string {
        const lang = $currentLanguage;
        const prefix = lang !== 'en' ? `${lang}/` : '';
        const resolvedPath = lang !== 'en' && localizedFallbackPath ? localizedFallbackPath : path;
        return `/mkdocs/${prefix}${resolvedPath}`;
    }
</script>

<Button label={name} {math} icon={icon === 'book' ? BookOpen : HelpCircle} {display} hideWordBelow={labelDisplay === 'responsive' ? 'sm' : undefined} variant="link-muted" size={buttonSize} inline onclick={() => window.open(getDocsUrl(), '_blank', 'noopener')} data-testid={testId} />
