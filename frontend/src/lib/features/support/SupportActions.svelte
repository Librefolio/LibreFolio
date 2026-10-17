<script lang="ts">
    import {_} from '$lib/i18n';
    import {Coffee} from 'lucide-svelte';
    import SocialIcon from './SocialIcon.svelte';
    import {donationsVisible} from './donations.svelte';
    import {BUY_ME_A_COFFEE_URL, SOCIAL_SHARE_CONFIG, SOCIAL_SHARE_ORDER, type SocialPlatform} from './supportLinks';

    interface Props {
        onCoffeeClick?: () => void;
        coffeeTestId?: string;
        onShare?: (platform: SocialPlatform) => void;
        class?: string;
    }

    let {onCoffeeClick, coffeeTestId = 'support-coffee', onShare = () => {}, class: className = ''}: Props = $props();

    const shareItems = SOCIAL_SHARE_ORDER.map((platform) => ({
        platform,
        label: SOCIAL_SHARE_CONFIG[platform].label,
        brandClass: SOCIAL_SHARE_CONFIG[platform].brandClass,
    }));
</script>

<div class={`space-y-4 text-lf-primary ${className}`.trim()} data-testid="support-actions">
    <!-- F05: the coffee only on a self-hosted instance; sharing stays everywhere (D-A8) -->
    {#if donationsVisible()}
        <a
            href={BUY_ME_A_COFFEE_URL}
            target="_blank"
            rel="noopener noreferrer"
            class="flex w-full items-center justify-center gap-2 rounded-lg bg-lf-donate px-4 py-3 text-sm font-medium text-lf-on-status transition-colors hover:bg-lf-donate-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-lf-donate focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
            onclick={() => onCoffeeClick?.()}
            data-testid={coffeeTestId}
        >
            <Coffee size={16} />
            <span>{$_('help.buyMeACoffee')}</span>
        </a>

        <div class="flex items-center gap-3 text-[0.7rem] font-semibold uppercase tracking-[0.28em] text-lf-muted">
            <span class="h-px flex-1 bg-lf-subtle"></span>
            <span>{$_('support.shareDivider')}</span>
            <span class="h-px flex-1 bg-lf-subtle"></span>
        </div>
    {/if}

    <div class="flex flex-wrap items-center justify-center gap-3">
        {#each shareItems as item}
            {@const label = `${$_('support.shareOn')} ${item.label}`}
            <button
                type="button"
                class={`inline-flex h-11 w-11 items-center justify-center rounded-full border border-transparent transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent ${item.brandClass}`}
                onclick={() => onShare(item.platform)}
                aria-label={label}
                data-testid={`support-share-${item.platform}`}
            >
                <SocialIcon platform={item.platform} size={22} />
            </button>
        {/each}
    </div>
</div>
