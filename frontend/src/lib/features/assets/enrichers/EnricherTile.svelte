<!--
  EnricherTile — an enricher's icon, or its initials when it has none or the icon does not load (plan 68, E7b2).
  `size="sm"` is the small one of a table cell (the profile's «Chi», 87).
-->
<script lang="ts">
    interface Props {
        code: string;
        name: string;
        /** One address, or a list of candidates (the first that is set is tried). */
        icon: string | (string | null)[] | null;
        /** Drawn off: the instance does not serve it, or it is not configured. */
        muted?: boolean;
        /** `sm`: beside a name in a table cell (the profile's «Chi», 87). */
        size?: 'md' | 'sm';
    }

    let {code, name, icon, muted = false, size = 'md'}: Props = $props();

    let failed = $state(false);
    let source = $derived(Array.isArray(icon) ? (icon.find((candidate) => !!candidate) ?? null) : icon);

    /** The first letters of the first two words («Borsa Italiana» → «BI»); a single word, its first letter and its first
     *  capital after it («justETF» → «JE»), else its first two letters («GLEIF» → «GL»). */
    let initials = $derived.by(() => {
        const words = name.split(/[\s_-]+/).filter(Boolean);
        if (words.length > 1) return (words[0][0] + words[1][0]).toUpperCase();
        const word = words[0] ?? code;
        const capital = word.slice(1).match(/[A-Z]/)?.[0];
        return (word[0] + (capital ?? word.slice(1, 2))).toUpperCase();
    });
</script>

<span class="shrink-0 inline-flex items-center justify-center border border-lf-subtle bg-lf-panel font-bold text-lf-secondary {size === 'sm' ? 'w-5 h-5 rounded text-[8px]' : 'w-8 h-8 rounded-md text-[10px]'} {muted ? 'opacity-50' : ''}" aria-hidden="true" data-testid="enricher-tile-{code}">
    {#if source && !failed}
        <img src={source} alt="" class={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} loading="lazy" onerror={() => (failed = true)} />
    {:else}
        {initials}
    {/if}
</span>
