<script lang="ts">
    /**
     * PrivacyToggle — hide or show every monetary amount in the app.
     *
     * Sits in the header rather than in Settings because the need is contextual:
     * someone walks up to the screen. A control reachable only after navigating
     * would arrive after the moment it exists for.
     */
    import {Eye, EyeOff} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {isPrivacyEnabled, togglePrivacy} from '$lib/stores/app/privacyStore.svelte';
    import Button from '$lib/components/ui/button/Button.svelte';

    const hidden = $derived(isPrivacyEnabled());
    const label = $derived(hidden ? $_('header.privacy.show') : $_('header.privacy.hide'));
</script>

<!-- The standard icon button (85 BTN-2a). The state stays in the icon and in `aria-pressed`, passed as an attribute: the
     `pressed` look (a filled control) would change the header. The name by long press, rest or Tab, no `title`. -->
<Button {label} icon={hidden ? EyeOff : Eye} display="icon" variant="ghost-strong" size="lg" aria-pressed={hidden ? 'true' : 'false'} onclick={togglePrivacy} data-testid="privacy-toggle" />
