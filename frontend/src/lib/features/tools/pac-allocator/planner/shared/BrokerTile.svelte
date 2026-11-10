<script lang="ts">
    /**
     * A Broker as a tile you press (P2): its icon above, its name below, lit while chosen. It replaces the tick box of the two Broker
     * choosers of the planner. A Broker the user cannot read from is dimmed and cannot be pressed, and says why under its name.
     * `detail` is an optional small block under the name (the cash a copy would bring, the currencies seen): one line, scrolled by itself when it does not fit.
     */
    import type {Snippet} from 'svelte';
    import {Check} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {compareDecimal} from '../decimal';
    import {formatPlannerPercent} from '../format';
    import type {ScopeBroker} from '../scope';
    import {BADGE, HINT} from '../ui';

    interface Props {
        broker: ScopeBroker;
        pressed: boolean;
        /** Prefix of the tile's test ids: the button is `{testid}-check`, the reason a Broker is out `{testid}-blocked`. */
        testid: string;
        /** Off for a reason of the caller's (a Broker with nothing to copy yet), over the role's own. */
        disabled?: boolean;
        ontoggle: (next: boolean) => void;
        detail?: Snippet;
    }

    let {broker, pressed, testid, disabled = false, ontoggle, detail}: Props = $props();

    const off = $derived(!broker.selectable || disabled);

    function partial(share: string | null): boolean {
        return share !== null && compareDecimal(share, '1') === -1;
    }
</script>

<button
    type="button"
    class="relative flex h-full w-full flex-col items-center gap-1.5 rounded-lg border p-3 text-center transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus
        {off ? 'cursor-not-allowed border-dashed border-lf-subtle text-lf-muted' : pressed ? 'border-lf-checked bg-lf-selected text-lf-primary' : 'border-lf-subtle text-lf-primary hover:border-lf-link'}"
    aria-pressed={pressed}
    disabled={off}
    data-testid="{testid}-check"
    data-pressed={pressed ? 'true' : 'false'}
    onclick={() => ontoggle(!pressed)}
>
    {#if pressed && !off}
        <span class="absolute right-1.5 top-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-lf-checked text-lf-on-checked" aria-hidden="true"><Check size={11} /></span>
    {/if}
    <span class="inline-flex {broker.selectable ? '' : 'opacity-60 grayscale'}"><BrokerIcon brokerId={broker.id} iconUrl={broker.iconUrl} portalUrl={broker.portalUrl} pluginCode={broker.pluginCode} altText="" size={32} /></span>
    <span class="min-w-0 max-w-full break-words text-sm font-medium">{broker.name}</span>
    {#if broker.selectable}
        {#if partial(broker.share)}
            <span class={HINT}>{$t('tools.pacAllocator.planner.scope.share', {default: 'share {share}', values: {share: formatPlannerPercent(broker.share)}})}</span>
        {/if}
        {#if !broker.active}
            <span class={BADGE.warning}>{$t('tools.pacAllocator.planner.scope.inactive', {default: 'Inactive'})}</span>
        {/if}
        {#if detail}
            <!-- One line that scrolls by itself when it does not fit, as the names and badges of the planner do. -->
            <span use:scrollOnOverflow class="{overflowScrollTextClass} w-full" data-testid="{testid}-detail">{@render detail()}</span>
        {/if}
    {:else}
        <span class={HINT} data-testid="{testid}-blocked">{$t('tools.pacAllocator.planner.scope.notSelectable', {default: 'Not selectable: {role} access, not read', values: {role: broker.role ?? '—'}})}</span>
    {/if}
</button>
