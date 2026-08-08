<!--
  IdentifierPrimaryChooser.svelte — Pick which identifier is *primary* when several
  candidates for the same structured type are in play.

  ## Why this exists

  Before this component the only choices on an identifier conflict were "replace" or
  "just assign" — both destructive, because either way one of the two codes was lost.
  The missing third outcome is the one users actually want: **keep both, choose which
  one leads**.

  The motivating case is the Italian retail government bond. A BTP bought at issue
  carries a non-tradeable "CUM" ISIN that grants the loyalty premium; to be sold it must
  be converted into a different, quoted ISIN. In LibreFolio the two are one asset: the
  quoted code goes in `identifier_isin` (it is the only one a price provider can index,
  since a price *is* the last trade), the CUM code goes in `identifier_other` so every
  future import that quotes it still finds the asset.

  Nothing is lost on the pricing side: `AssetProviderAssignment` carries its own
  identifier, decoupled from `Asset.identifier_isin`. Choosing the primary is an
  *identity* decision, not a pricing one.

  ## Contract

  - N values, not just two — a unified group can carry several.
  - Every value shows **where it came from** (provider / report / already saved).
    Without the origin the user has no basis to decide.
  - The default preselects the provider's value when present: that is the quoted one.
    The typical case is therefore two clicks — open, confirm.
  - The BTP note appears only when it is pertinent (ISIN type, ≥ 2 values), so it is not
    a permanent wall of text.

  Callers: the import wizard (assign / create) and the provider-comparison modal.

  Svelte 5 runes, `data-testid` on every row for E2E.
-->
<script module lang="ts">
    /** Where a candidate value came from — shown as a badge next to it. */
    export type IdentifierOrigin = 'provider' | 'report' | 'stored';

    export interface IdentifierChoice {
        /** The identifier value itself (e.g. an ISIN). */
        value: string;
        /** Provenance, rendered as a badge. */
        origin: IdentifierOrigin;
        /** Optional extra context (e.g. the file name the value came from). */
        detail?: string;
    }
</script>

<script lang="ts">
    import {Info} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';

    interface Props {
        /** Candidate values. Duplicates (case-insensitive) are collapsed. */
        choices: IdentifierChoice[];
        /** Asset name, shown in the question. */
        assetName: string;
        /** Human label of the identifier type (e.g. "ISIN", "Ticker"). */
        typeLabel?: string;
        /** True when the values are ISINs — enables the BTP explanation. */
        isIsin?: boolean;
        /** Currently selected primary value (bindable). */
        primary?: string | null;
        /** Test id prefix. */
        testid?: string;
        /** Fired whenever the selection changes, with the primary and the leftovers. */
        onchange?: (primary: string, alternates: string[]) => void;
    }

    let {choices, assetName, typeLabel, isIsin = false, primary = $bindable(null), testid = 'identifier-primary-chooser', onchange}: Props = $props();

    /**
     * Collapse duplicates case-insensitively, keeping the strongest provenance.
     *
     * The same code legitimately arrives from two sources at once (the provider returns
     * what the report already said); showing it twice would be noise, and the provider
     * label is the more informative of the two.
     */
    const ORIGIN_RANK: Record<IdentifierOrigin, number> = {provider: 0, report: 1, stored: 2};

    let uniqueChoices = $derived.by<IdentifierChoice[]>(() => {
        const byValue = new Map<string, IdentifierChoice>();
        for (const c of choices) {
            const key = (c.value ?? '').trim().toUpperCase();
            if (key === '') continue;
            const existing = byValue.get(key);
            if (!existing) {
                byValue.set(key, {...c, value: c.value.trim()});
                continue;
            }
            if (ORIGIN_RANK[c.origin] < ORIGIN_RANK[existing.origin]) {
                byValue.set(key, {...c, value: existing.value});
            }
        }
        return [...byValue.values()];
    });

    /** The provider's value is the quoted one, so it is the safest default. */
    let defaultPrimary = $derived(uniqueChoices.find((c) => c.origin === 'provider')?.value ?? uniqueChoices.find((c) => c.origin === 'stored')?.value ?? uniqueChoices[0]?.value ?? null);

    $effect(() => {
        // Seed (or repair) the selection when the candidate list changes underneath us.
        const valid = uniqueChoices.some((c) => c.value === primary);
        if (!valid && defaultPrimary) {
            primary = defaultPrimary;
            onchange?.(defaultPrimary, alternatesFor(defaultPrimary));
        }
    });

    function alternatesFor(selected: string): string[] {
        return uniqueChoices.filter((c) => c.value !== selected).map((c) => c.value);
    }

    /** Everything that is not primary becomes an alternate — that is the whole point. */
    let alternates = $derived(primary ? alternatesFor(primary) : []);

    function select(value: string): void {
        primary = value;
        onchange?.(value, alternatesFor(value));
    }

    function originLabel(origin: IdentifierOrigin): string {
        if (origin === 'provider') return $t('assets.identifiers.primaryChooser.originProvider');
        if (origin === 'report') return $t('assets.identifiers.primaryChooser.originReport');
        return $t('assets.identifiers.primaryChooser.originStored');
    }

    function originClass(origin: IdentifierOrigin): string {
        if (origin === 'provider') return 'bg-libre-green/10 text-libre-green dark:bg-libre-green/20';
        if (origin === 'report') return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300';
        return 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-300';
    }

    let title = $derived(typeLabel ? $t('assets.identifiers.primaryChooser.title', {values: {type: typeLabel, asset: assetName}}) : $t('assets.identifiers.primaryChooser.titleGeneric', {values: {asset: assetName}}));

    /** Only worth explaining when there is an actual ISIN choice to make. */
    let showBtpNote = $derived(isIsin && uniqueChoices.length >= 2);

    /**
     * Render `**bold**` segments from the translated note without `{@html}`.
     * The note is the one place where emphasis carries the recommendation.
     */
    let btpNoteParts = $derived.by<Array<{text: string; bold: boolean}>>(() => {
        const raw = $t('assets.identifiers.primaryChooser.btpNote');
        return raw.split(/\*\*(.+?)\*\*/g).map((segment, i) => ({text: segment, bold: i % 2 === 1}));
    });
</script>

<div data-testid={testid} class="space-y-3">
    <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{title}</p>

    <div class="space-y-1.5" role="radiogroup" aria-label={title}>
        {#each uniqueChoices as choice (choice.value)}
            <button
                type="button"
                role="radio"
                aria-checked={primary === choice.value}
                data-testid="{testid}-option-{choice.value}"
                class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg border text-left transition-colors {primary === choice.value ? 'border-libre-green bg-libre-green/5 dark:bg-libre-green/10' : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500'}"
                onclick={() => select(choice.value)}
            >
                <span class="shrink-0 w-4 h-4 rounded-full border-2 flex items-center justify-center {primary === choice.value ? 'border-libre-green' : 'border-gray-300 dark:border-slate-500'}">
                    {#if primary === choice.value}
                        <span class="w-2 h-2 rounded-full bg-libre-green"></span>
                    {/if}
                </span>
                <span class="font-mono text-sm text-gray-900 dark:text-gray-100 truncate">{choice.value}</span>
                <span class="shrink-0 ml-auto text-[10px] px-1.5 py-0.5 rounded font-medium {originClass(choice.origin)}">
                    {originLabel(choice.origin)}
                </span>
            </button>
            {#if choice.detail}
                <p class="pl-9 -mt-0.5 text-[11px] text-gray-500 dark:text-gray-400 truncate">{choice.detail}</p>
            {/if}
        {/each}
    </div>

    <p class="text-xs text-gray-600 dark:text-gray-400">{$t('assets.identifiers.primaryChooser.hint')}</p>

    {#if alternates.length > 0}
        <p data-testid="{testid}-alternates" class="text-xs text-gray-500 dark:text-gray-400">
            <span class="font-medium">{$t('assets.identifiers.primaryChooser.keepAlternates')}</span>
            <span class="font-mono">{alternates.join(', ')}</span>
        </p>
    {/if}

    {#if showBtpNote}
        <div data-testid="{testid}-btp-note" class="flex gap-2 p-2.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-[11px] leading-relaxed text-blue-800 dark:text-blue-200">
            <Info class="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <p>
                {#each btpNoteParts as part, i (i)}{#if part.bold}<strong>{part.text}</strong>{:else}{part.text}{/if}{/each}
            </p>
        </div>
    {/if}
</div>
