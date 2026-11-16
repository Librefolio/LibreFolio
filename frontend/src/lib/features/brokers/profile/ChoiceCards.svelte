<!--
  A choice among a few options as big cards (P2 of project 67, M6, M18): a radio inside each card, never a menu. The
  broker's operating profile uses it for the currency conversion and the tax regime. The option a profile starts from
  (`defaultValue`) carries a «default» badge, and reads as chosen while nothing is chosen. It imports nothing from the
  planner (D17): its look follows the planner's conversion cards with the same colour roles.

  G6-3 of project 67 (the Rebalancer's strategy and target fidelity) adds, each optional and inert when absent: an option
  off with its own badge («coming soon»), a description in the warning colour, a card on the whole row, a content in the
  chosen card (`extra`, e.g. «Custom»'s field), and four columns on a wide screen.
-->
<script lang="ts" generics="V extends string">
    import type {Snippet} from 'svelte';

    interface Option {
        value: V;
        label: string;
        description?: string;
        /** The description in the warning colour. */
        tone?: 'warning';
        /** Shown, never chosen: its radio is off. */
        disabled?: boolean;
        /** A badge beside the label (translated by the caller), e.g. «coming soon». */
        badge?: string;
        /** The card takes the whole row. */
        wide?: boolean;
    }

    interface Props {
        /** The radio group's name: unique on the page. */
        name: string;
        legend: string;
        options: readonly Option[];
        value: V | null;
        defaultValue?: V | null;
        /** The badge's text on the default option (translated by the caller). */
        defaultLabel?: string;
        testid: string;
        /** The id of each card and of its radio: `{testid}-card` and `{testid}-radio` unless the caller keeps its own (P3: the planner's). */
        cardTestid?: string;
        radioTestid?: string;
        /** The data attribute that carries a card's value, besides `data-value`: `mode` gives `data-mode`. */
        valueAttribute?: string;
        disabled?: boolean;
        /** Four columns on a wide screen instead of two. */
        wideGrid?: boolean;
        /**
         * A content inside each card, after its label, given its value and whether it is chosen: the caller shows it where it
         * wants, with its own padding (`px-3 pb-3` lines it up with the label).
         */
        extra?: Snippet<[V, boolean]>;
        onchange: (value: V) => void;
    }

    let {name, legend, options, value, defaultValue = null, defaultLabel = '', testid, cardTestid, radioTestid, valueAttribute, disabled = false, wideGrid = false, extra, onchange}: Props = $props();

    const shown = $derived(value ?? defaultValue);
</script>

{#snippet choice(option: Option, on: boolean, off: boolean)}
    <input
        type="radio"
        {name}
        value={option.value}
        checked={on}
        disabled={off}
        class="mt-0.5 shrink-0 accent-lf-checked"
        data-testid={radioTestid ?? `${testid}-radio`}
        onchange={() => {
            // A browser fires nothing on a disabled radio; jsdom and some assistive paths still can.
            if (!off) onchange(option.value);
        }}
    />
    <span class="min-w-0 space-y-0.5">
        <span class="flex flex-wrap items-center gap-1.5 font-medium text-lf-primary">
            {option.label}
            {#if defaultValue === option.value}
                <span class="rounded-full border border-lf-subtle bg-lf-panel px-2 py-0.5 text-xs font-normal text-lf-secondary" data-testid="{testid}-default">{defaultLabel}</span>
            {/if}
            {#if option.badge}
                <span class="rounded-full border border-lf-subtle bg-lf-panel px-2 py-0.5 text-xs font-normal text-lf-secondary" data-testid="{testid}-badge">{option.badge}</span>
            {/if}
        </span>
        {#if option.description}
            <span class="block text-xs {option.tone === 'warning' ? 'text-lf-warning' : 'text-lf-secondary'}" data-tone={option.tone ?? 'default'}>{option.description}</span>
        {/if}
    </span>
{/snippet}

<fieldset class="grid gap-2 sm:grid-cols-2 {wideGrid ? 'lg:grid-cols-4' : ''}" data-testid={testid} {disabled}>
    <legend class="sr-only">{legend}</legend>
    {#each options as option (option.value)}
        {@const on = shown === option.value}
        {@const off = disabled || option.disabled === true}
        {@const look = `rounded-lg border text-sm transition-colors focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-lf-focus ${option.wide ? 'sm:col-span-full' : ''} ${on ? 'border-lf-checked bg-lf-selected' : option.disabled ? 'border-lf-subtle' : 'border-lf-subtle hover:border-lf-input'}`}
        {@const pointer = option.disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}
        {@const data = {
            'data-testid': cardTestid ?? `${testid}-card`,
            'data-value': option.value,
            ...(valueAttribute ? {[`data-${valueAttribute}`]: option.value} : {}),
            'data-selected': on ? 'true' : 'false',
            'data-disabled': option.disabled ? 'true' : 'false',
            'data-wide': option.wide ? 'true' : 'false',
        }}
        {#if extra}
            <!-- The card holds the radio's label, then the content: a field inside the label would be a second labelable element. -->
            <div class={look} {...data}>
                <label class="flex items-start gap-2 p-3 {pointer}">{@render choice(option, on, off)}</label>
                {@render extra(option.value, on)}
            </div>
        {:else}
            <label class="flex items-start gap-2 p-3 {look} {pointer}" {...data}>{@render choice(option, on, off)}</label>
        {/if}
    {/each}
</fieldset>
