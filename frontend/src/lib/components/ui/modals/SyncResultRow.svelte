<!--
  SyncResultRow — one line of a sync result, for every sync modal.

  There were four copies of this row: `AssetSyncModal`, `FxSyncModal` and the
  two snippets inside `PageSyncModal`. They started identical and drifted, and
  the drift was invisible because each one only ever gets read next to itself.
  Three of the four differences were defects rather than choices:

    · the *reason* a sync went wrong was shown for `failed || partial` in the
      asset row, for `failed` alone in the FX row, and — in `PageSyncModal` —
      inside an `{:else if}` chain that a `partial` row can never reach, since
      it has already matched the counters branch above. Same payload, three
      answers, and the two-of-three that stayed silent left the user with a
      retry button and no idea what to retry;
    · the FX row computed `pr.errors?.join('; ') ?? pr.message`. An empty
      `errors` array — which is what both the API mapper and the base modal's
      own failure path produce — joins to `''`, and `??` does not catch an
      empty string, so the tooltip came up blank exactly when there was a
      message to show;
    · the double-click / long-press to copy a long error existed only on the
      asset row.

  So the row keeps the widest behaviour of the four, and what genuinely varies
  is passed in: the identity block (an asset's icon and name, a pair's flags and
  codes) and the provider badge, whose lookup differs between asset and FX
  registries. Everything else — status icon, retry affordance, counters, the
  skipped note, the error and its tooltip, the elapsed time — is one
  implementation.
-->
<script lang="ts">
    import type {Component, Snippet} from 'svelte';
    import {CalendarClock, DollarSign, RotateCw} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {writeExportToClipboard} from '$lib/utils/clipboard';
    import {clearTimer} from '$lib/utils/core/clearTimer';
    import type {SyncResult} from '$lib/utils/sync/syncHelpers';
    import {formatElapsed, STATUS_COLORS, STATUS_ICONS} from '$lib/utils/sync/syncHelpers';

    interface Props {
        result: SyncResult;
        /** True while a sync is running: the retry affordance is hidden then. */
        syncing: boolean;
        onRetry: (id: string) => void;
        /** What this row is *about* — an asset with its icon, a currency pair. */
        identity: Snippet<[SyncResult]>;
        /** Badge for `provider_used`. Omitted when the caller shows none. */
        provider?: Snippet<[string]>;
        /** Widest label the identity block may take before truncating. */
        identityWidth?: string;
        /**
         * Hover text on the status icon / retry button.
         *
         * FX rows use it for the per-leg breakdown of a chain, which has no
         * equivalent on an asset. A parameter rather than a fork: the caller is
         * the only one that knows whether there is anything to say.
         */
        statusTooltip?: string;
        /**
         * Glyph in front of the fetched/changed counters, or `null` for none.
         *
         * Defaults to the prices icon, which is what the asset rows show and
         * what the data-editor tab uses. FX rows count rates, not prices, and
         * have always shown the bare numbers.
         */
        countIcon?: Component | null;
    }

    let {result, syncing, onRetry, identity, provider, identityWidth = 'max-w-[140px]', statusTooltip, countIcon = DollarSign as unknown as Component}: Props = $props();

    let longPressTimer: ReturnType<typeof setTimeout> | null = null;

    const StatusIcon = $derived(STATUS_ICONS[result.status] ?? STATUS_ICONS.failed);
    /** A retry is offered for anything that did not fully succeed. */
    const retryable = $derived(result.status === 'failed' || result.status === 'partial');
    const hasCounters = $derived(result.status === 'ok' || result.status === 'partial');

    /** Everything that went wrong, for the tooltip. */
    const fullError = $derived(result.errors && result.errors.length ? result.errors.join('; ') : (result.message ?? ''));
    /** The one line that fits on screen. */
    const shortError = $derived(result.errors?.[0] ?? result.message ?? $t('prices.sync.failedDefault') ?? 'Failed');

    async function copyError(): Promise<void> {
        await writeExportToClipboard(fullError, toasts, $t('common.copiedToClipboard'));
    }

    function handleTouchStart(): void {
        longPressTimer = setTimeout(copyError, 500);
    }

    function handleTouchEnd(): void {
        longPressTimer = clearTimer(longPressTimer);
    }
</script>

<div class="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 group" data-row-id={result.id} data-status={result.status} data-testid="sync-result-row">
    {#if retryable && !syncing}
        {#if statusTooltip}
            <Tooltip text={statusTooltip} position="top">
                <button
                    class="shrink-0 p-0.5 rounded transition-colors
                        {result.status === 'failed' ? 'hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500' : 'hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-500'}"
                    data-testid="sync-retry-row"
                    onclick={() => onRetry(result.id)}
                    type="button"
                >
                    <RotateCw size={13} />
                </button>
            </Tooltip>
        {:else}
            <button
                class="shrink-0 p-0.5 rounded transition-colors
                    {result.status === 'failed' ? 'hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500' : 'hover:bg-amber-100 dark:hover:bg-amber-900/30 text-amber-500'}"
                data-testid="sync-retry-row"
                onclick={() => onRetry(result.id)}
                type="button"
            >
                <RotateCw size={13} />
            </button>
        {/if}
    {:else if statusTooltip}
        <Tooltip text={statusTooltip} position="top">
            <StatusIcon size={14} class="{STATUS_COLORS[result.status] ?? 'text-gray-400'} shrink-0 cursor-help" />
        </Tooltip>
    {:else}
        <StatusIcon size={14} class="{STATUS_COLORS[result.status] ?? 'text-gray-400'} shrink-0" />
    {/if}

    <span class="flex items-center gap-2 min-w-0 font-medium truncate {identityWidth}">
        {@render identity(result)}
    </span>

    {#if hasCounters}
        <span class="text-gray-400">—</span>
        <span class="inline-flex items-center gap-0.5">
            {#if countIcon}
                {@const CountIcon = countIcon}
                <CountIcon size={13} class="text-gray-400 shrink-0" />
            {/if}
            {result.points_fetched ?? 0}↓ {result.points_changed ?? 0}Δ
        </span>
        {#if (result.events_fetched ?? 0) > 0}
            <span class="text-gray-400">·</span>
            <span class="inline-flex items-center gap-0.5"><CalendarClock size={13} class="text-gray-400 shrink-0" />{result.events_fetched}↓ {result.events_changed ?? 0}Δ</span>
        {/if}
        {#if result.provider_used && provider}
            {@render provider(result.provider_used)}
        {/if}
    {/if}

    {#if result.status === 'skipped' && result.message}
        <span class="text-gray-400 italic truncate" data-testid="sync-row-skipped">{result.message}</span>
    {/if}

    {#if retryable}
        <!-- The tooltip carries the full text because the visible span truncates
             inside a narrow flex row; double-click and long-press copy it, which
             is the only way to get a multi-error payload out of the modal. -->
        <Tooltip text={fullError} position="top" maxWidth="500px">
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span class="{result.status === 'partial' ? 'text-amber-500' : 'text-red-500'} truncate inline-block max-w-[240px] align-middle cursor-help" data-testid="sync-row-error" ondblclick={copyError} ontouchend={handleTouchEnd} ontouchstart={handleTouchStart}>{shortError}</span>
        </Tooltip>
    {/if}

    {#if result.elapsed_ms}
        <span class="ml-auto text-gray-400 font-mono tabular-nums text-[10px]">{formatElapsed(result.elapsed_ms)}</span>
    {/if}
</div>
