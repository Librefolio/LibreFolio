<!--
  ProfileDetails — the «Dettagli» of the «Profilo» tab (plan 68, E4): the groups of the catalogue (the fund, the company,
  the identity, the bond), each a list of label and value. On a wide screen the bond takes the right column, the other
  three the left one; on a phone they follow one another.

  The identity group adds the asset's ISIN and ticker: identifiers of the asset, not voices of the profile. A row
  publishes `data-state` (`value`, `emptied`, `unavailable`); a row with a value opens the voice's history (E6) when the
  page handles it.

  Pattern: Svelte 5 Runes, Tailwind CSS 4, colour roles only.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {DetailGroup} from './profileTabState';

    interface Props {
        groups: DetailGroup[];
        /** The text of each voice with a value, by key (`formatProfileValue`). */
        texts: Record<string, string>;
        isin: string | null;
        ticker: string | null;
        /** The asset's other identifiers (CUSIP, FIGI…), label and value, shown after the ISIN and the ticker when present. */
        otherIdentifiers?: [string, string][];
        /** Opens a voice's history (E6); without it the rows are plain text. */
        onhistory?: (key: string) => void;
    }

    let {groups, texts, isin, ticker, otherIdentifiers = [], onhistory}: Props = $props();

    const left = $derived(groups.filter((group) => group.group !== 'bond'));
    const right = $derived(groups.filter((group) => group.group === 'bond'));
    const identifiers = $derived([
        {id: 'isin', label: $t('assets.profile.tab.isin'), value: isin},
        {id: 'ticker', label: $t('assets.profile.tab.ticker'), value: ticker},
    ]);
</script>

{#snippet missing()}
    <span class="italic text-lf-muted">{$t('assets.profile.tab.notAvailable')}</span>
{/snippet}

{#snippet column(list: DetailGroup[])}
    <div class="flex min-w-0 flex-col gap-5">
        {#each list as group (group.group)}
            <section data-testid="profile-details-group-{group.group}">
                <h4 class="mb-1 text-xs font-bold uppercase tracking-wide text-lf-secondary">{$t(`assets.profile.groups.${group.group}`)}</h4>
                <dl class="divide-y divide-lf-subtle">
                    {#each group.cells as cell (cell.key)}
                        {@const text = cell.state === 'value' ? (texts[cell.key] ?? '') : ''}
                        <div class="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3 py-2 text-sm" data-testid="profile-detail-{cell.key}" data-state={cell.state}>
                            <!-- The company's sector is its one sector («Settore»), not the classification's map -->
                            <dt class="text-lf-secondary">{group.group === 'company' && cell.key === 'sector' ? $t('assets.profile.tab.companySector') : $t(`assets.profile.voices.${cell.key}`)}</dt>
                            <dd class="min-w-0 break-words text-lf-primary">
                                {#if text === ''}
                                    {@render missing()}
                                {:else if onhistory}
                                    <button type="button" class="text-left hover:underline focus-visible:outline-2 focus-visible:outline-lf-focus rounded" data-testid="profile-detail-{cell.key}-history" onclick={() => onhistory?.(cell.key)}>{text}</button>
                                {:else}
                                    {text}
                                {/if}
                            </dd>
                        </div>
                    {/each}
                    {#if group.group === 'identity'}
                        {#each identifiers as identifier (identifier.id)}
                            <div class="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3 py-2 text-sm" data-testid="profile-detail-{identifier.id}" data-state={identifier.value ? 'value' : 'unavailable'}>
                                <dt class="text-lf-secondary">{identifier.label}</dt>
                                <dd class="min-w-0 break-all text-lf-primary">
                                    {#if identifier.value}<span class="font-mono">{identifier.value}</span>{:else}{@render missing()}{/if}
                                </dd>
                            </div>
                        {/each}
                        {#each otherIdentifiers as [label, value], index (`${label}-${value}-${index}`)}
                            <div class="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3 py-2 text-sm" data-testid="profile-detail-identifier-{index}" data-state="value">
                                <dt class="text-lf-secondary">{label}</dt>
                                <dd class="min-w-0 break-all font-mono text-lf-primary">{value}</dd>
                            </div>
                        {/each}
                    {/if}
                </dl>
            </section>
        {/each}
    </div>
{/snippet}

<div class="grid grid-cols-1 gap-5 lg:grid-cols-2 lg:gap-8" data-testid="profile-details">
    {@render column(left)}
    {@render column(right)}
</div>
