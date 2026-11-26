<!--
  ProfileVoiceSelect — the «Dato» cell of a row of the profile window (87, A4): the voices by group, with a search box,
  as wide as its cell. A row without a voice, or with one the list already holds, shows the danger border instead of a
  written error: the border marks where to click. The reason stays for a screen reader, on the cell's hidden text.
-->
<script lang="ts">
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';

    interface Props {
        rowId: string;
        value: string;
        /** The voices offered: the groups' titles, then their voices. */
        options: SelectOption[];
        placeholder: string;
        ariaLabel: string;
        /** Why the choice is missing or refused; null when it is fine. */
        issue?: string | null;
        onchange: (key: string) => void;
    }

    let {rowId, value, options, placeholder, ariaLabel, issue = null, onchange}: Props = $props();

    const issueId = $derived(`profile-row-voice-issue-${rowId}`);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="w-full" data-testid="profile-row-voice-cell-{rowId}" data-value={value} onclick={(event) => event.stopPropagation()}>
    <SearchSelect {value} {options} {placeholder} {ariaLabel} compact class="w-full" dropdownPosition="auto" dropdownMinWidth={280} invalid={issue !== null} describedBy={issue !== null ? issueId : undefined} testId={`profile-row-voice-${rowId}`} {onchange}>
        {#snippet selectedItem(option)}
            <span class="block truncate">{option.label}</span>
        {/snippet}
        {#snippet item(option)}
            <span class="block truncate text-sm">{option.label}</span>
        {/snippet}
    </SearchSelect>
    {#if issue !== null}<span id={issueId} class="sr-only">{issue}</span>{/if}
</div>
