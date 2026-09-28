<!--
  SignalTreeSelect — the signals panel's picker (indicators, comparisons, benchmarks).

  A thin adapter since decision D-K1 (workstream K, R15): the mechanics — dropdown, search across
  both levels, groups that open and close, keyboard, ARIA tree — live in the generic
  `ui/select/TreeSelect.svelte`, where they moved verbatim. This file supplies only what makes the
  generic select the signals picker: `SignalOptionContent` as row content, the `signal-tree` test-id
  prefix that the E2E suites and `gallery.spec.ts` rely on, and the `signals.selector.*` texts.

  It stays an *action* picker (the trigger never shows a value) whose first family opens by
  itself. Props and exported types are unchanged, so `ChartSignalsSection` did not change, and
  `SignalTreeSelect.test.ts` pins that the behaviour did not either.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import TreeSelect from '$lib/components/ui/select/TreeSelect.svelte';
    import SignalOptionContent from './SignalOptionContent.svelte';

    export interface SignalTreeItem {
        value: string;
        icon: string;
        name: string;
        subtitle: string;
        dataSubtitle?: string;
        searchText: string;
    }

    export interface SignalTreeGroup {
        key: string;
        label: string;
        subtitle: string;
        items: SignalTreeItem[];
    }

    interface Props {
        value?: string;
        groups: SignalTreeGroup[];
        placeholder?: string;
        testId?: string;
        flat?: boolean;
        onchange?: (value: string) => void;
    }

    let {value = $bindable(''), groups, placeholder = '', testId, flat = false, onchange}: Props = $props();
</script>

{#snippet option(item: SignalTreeItem)}
    <SignalOptionContent icon={item.icon} name={item.name} subtitle={item.subtitle} dataSubtitle={item.dataSubtitle} />
{/snippet}

<TreeSelect bind:value {groups} {placeholder} {testId} {flat} {onchange} item={option} testIdPrefix="signal-tree" searchPlaceholder={$t('signals.selector.searchPlaceholder')} noMatchesText={$t('signals.selector.noMatches')} />
