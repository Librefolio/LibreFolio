<!--
  SyncResultRowHarness — test-only host for SyncResultRow (Vitest + jsdom).

  The row takes two snippets from its caller — the identity block (an asset's
  icon and name, a currency pair's flags) and the provider badge — and a snippet
  cannot be written in a `.ts` spec without `createRawSnippet`, whose one-shot
  `render()` does not follow updates. So the snippets live here, in a Svelte
  file, as the three modals write them.

  What they render is deliberately not what the modals render: a marker with a
  `data-testid`, no icons and no translated text, because the subject of the
  spec next door is what the *row* does with a result, not what a caller draws
  inside it. Which identity a modal chooses stays that modal's own test.

  `provider` is passed or withheld (`withProvider`) because the row draws a badge
  only when it is given both a `provider_used` and a snippet to draw it with, and
  the FX and asset modals differ on exactly that.

  Lives under `src/__tests__/`, which `vitest.config.ts` excludes from coverage:
  the harness must never inflate the numbers it exists to improve.
-->
<script lang="ts">
    import type {Component} from 'svelte';
    import SyncResultRow from '$lib/components/ui/modals/SyncResultRow.svelte';
    import type {SyncResult} from '$lib/utils/sync/syncHelpers';

    interface Props {
        result: SyncResult;
        syncing?: boolean;
        onRetry?: (id: string) => void;
        statusTooltip?: string;
        /** `undefined` leaves the row's own default in place; `null` asks for no glyph. */
        countIcon?: Component | null;
        /** False withholds the snippet entirely, as a caller that shows no badge does. */
        withProvider?: boolean;
    }

    let {result, syncing = false, onRetry = () => {}, statusTooltip = undefined, countIcon = undefined, withProvider = true}: Props = $props();
</script>

<SyncResultRow {countIcon} identity={rowIdentity} {onRetry} provider={withProvider ? rowProvider : undefined} {result} {statusTooltip} {syncing} />

{#snippet rowIdentity(item: SyncResult)}
    <span data-identity-for={item.id} data-testid="row-identity">{item.id}</span>
{/snippet}

{#snippet rowProvider(code: string)}
    <span data-provider={code} data-testid="row-provider">{code}</span>
{/snippet}
