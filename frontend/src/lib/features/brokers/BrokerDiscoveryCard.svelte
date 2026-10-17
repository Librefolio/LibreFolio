<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {Share2} from 'lucide-svelte';
    import BrokerIcon from '$lib/components/ui/display/BrokerIcon.svelte';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';

    export let broker: {
        id: number;
        name: string;
        icon_url?: string | null;
    };

    const dispatch = createEventDispatcher<{share: {id: number}}>();

    function handleShare(event: MouseEvent) {
        event.stopPropagation();
        dispatch('share', {id: broker.id});
    }
</script>

<div class="w-full bg-lf-card text-lf-primary rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle overflow-hidden" data-testid="broker-discovery-card-{broker.id}">
    <div class="p-4 flex items-center justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
            <BrokerIcon brokerId={broker.id} altText={broker.name} iconUrl={broker.icon_url} size="md" />
            <h3 use:scrollOnOverflow class="{overflowScrollTextClass} text-lg font-semibold text-lf-primary" title={broker.name}>{broker.name}</h3>
        </div>

        <button class="p-2 text-lf-muted hover:text-lf-link hover:bg-lf-selected rounded-lg transition-colors shrink-0" data-testid="broker-share-{broker.id}" on:click={handleShare} title={$_('brokers.sharing.title')}>
            <Share2 size={18} />
        </button>
    </div>
</div>
