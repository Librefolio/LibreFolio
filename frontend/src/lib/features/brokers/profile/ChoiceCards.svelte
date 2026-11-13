<!--
  A choice among a few options as big cards (P2 of project 67, M6, M18): a radio inside each card, never a menu. The
  broker's operating profile uses it for the currency conversion and the tax regime. The option a profile starts from
  (`defaultValue`) carries a «default» badge, and reads as chosen while nothing is chosen. It imports nothing from the
  planner (D17): its look follows the planner's conversion cards with the same colour roles.
-->
<script lang="ts" generics="V extends string">
    interface Option {
        value: V;
        label: string;
        description?: string;
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
        onchange: (value: V) => void;
    }

    let {name, legend, options, value, defaultValue = null, defaultLabel = '', testid, cardTestid, radioTestid, valueAttribute, disabled = false, onchange}: Props = $props();

    const shown = $derived(value ?? defaultValue);
</script>

<fieldset class="grid gap-2 sm:grid-cols-2" data-testid={testid} {disabled}>
    <legend class="sr-only">{legend}</legend>
    {#each options as option (option.value)}
        {@const on = shown === option.value}
        <label
            class="flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm transition-colors focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-lf-focus {on ? 'border-lf-checked bg-lf-selected' : 'border-lf-subtle hover:border-lf-input'}"
            data-testid={cardTestid ?? `${testid}-card`}
            data-value={option.value}
            {...valueAttribute ? {[`data-${valueAttribute}`]: option.value} : {}}
            data-selected={on ? 'true' : 'false'}
        >
            <input type="radio" {name} value={option.value} checked={on} {disabled} class="mt-0.5 shrink-0 accent-lf-checked" data-testid={radioTestid ?? `${testid}-radio`} onchange={() => onchange(option.value)} />
            <span class="min-w-0 space-y-0.5">
                <span class="flex flex-wrap items-center gap-1.5 font-medium text-lf-primary">
                    {option.label}
                    {#if defaultValue === option.value}
                        <span class="rounded-full border border-lf-subtle bg-lf-panel px-2 py-0.5 text-xs font-normal text-lf-secondary" data-testid="{testid}-default">{defaultLabel}</span>
                    {/if}
                </span>
                {#if option.description}
                    <span class="block text-xs text-lf-secondary">{option.description}</span>
                {/if}
            </span>
        </label>
    {/each}
</fieldset>
