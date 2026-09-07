<!--
  SyncModalBaseHarness — test-only host for SyncModalBase (Vitest + jsdom).

  SyncModalBase takes `sections: SyncSection[]`, and a section carries a
  `resultRow: Snippet<[SyncResult, boolean]>`. A snippet cannot be written in a
  `.ts` spec without `createRawSnippet`, whose `render()` returns a one-shot HTML
  string and needs a manual `setup()` effect to track updates — precisely the
  state changes (a row going failed → ok on retry) these tests exist to observe.
  A real `{#snippet}` is reactive by construction, so the harness is a Svelte
  file rather than a helper in the spec.

  It publishes the same handles as the three production specializations
  (`sync-result-row` + `data-row-id`/`data-status`, `sync-retry-row`), so a spec
  reads the base and its wrappers the same way. The extra `data-syncing` mirrors
  the second snippet argument, which is otherwise invisible from outside.

  Lives under `src/__tests__/`, which `vitest.config.ts` excludes from coverage:
  the harness must never inflate the numbers it exists to improve.
-->
<script lang="ts">
    import SyncModalBase from '$lib/components/ui/modals/SyncModalBase.svelte';
    import type {SyncResult, SyncSection} from '$lib/utils/sync/syncHelpers';

    /** A section without its snippet — the harness supplies the only one it has. */
    interface HarnessSection {
        id: string;
        targetIds: string[];
        doSyncFn: (targetIds: string[]) => Promise<SyncResult[]>;
        /** Defaults to a non-translated marker so a spec never reads a catalogue. */
        title?: string;
        countLabel?: string;
    }

    interface Props {
        open?: boolean;
        specs: HarnessSection[];
        onsynced?: () => void;
        onclose?: () => void;
        dateStart?: string;
        dateEnd?: string;
    }

    let {open = $bindable(true), specs, onsynced = () => {}, onclose = () => {}, dateStart = '2024-01-01', dateEnd = '2024-01-31'}: Props = $props();

    let base: SyncModalBase | undefined = $state(undefined);

    let sections: SyncSection[] = $derived(
        specs.map((s) => ({
            id: s.id,
            title: s.title ?? `title:${s.id}`,
            countLabel: s.countLabel ?? `unit:${s.id}`,
            targetIds: s.targetIds,
            doSyncFn: s.doSyncFn,
            resultRow: row,
        })),
    );
</script>

<SyncModalBase bind:open bind:this={base} {dateEnd} {dateStart} description="harness description" {onclose} {onsynced} {sections} testId="harness-sync-modal" title="harness title"></SyncModalBase>

{#snippet row(item: SyncResult, syncing: boolean)}
    <div data-changed={item.points_changed} data-fetched={item.points_fetched} data-row-id={item.id} data-status={item.status} data-syncing={syncing ? 'true' : 'false'} data-testid="sync-result-row">
        <button data-testid="sync-retry-row" onclick={() => base?.handleRetrySingle(item.id)} type="button">retry</button>
    </div>
{/snippet}
