<!--
  The ✕ of a dialog, a panel or a banner (project 85, BTN-0): the standard button, icon only, ghost, named
  «Close» in the user's language unless the caller gives a more precise name («Close editor»). Fixes D7: a ✕ never
  comes without a name.
-->
<script lang="ts">
    import {X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import Button from './Button.svelte';
    import type {ButtonSize} from './buttonClasses';
    import type {TipPosition} from './pressable.svelte';

    interface Props {
        /** The name; defaults to `common.close`. */
        label?: string;
        size?: ButtonSize;
        disabled?: boolean;
        onclick?: (event: MouseEvent) => void;
        tipPosition?: TipPosition;
        /** Size and position only. */
        class?: string;
        [key: `data-${string}`]: string | number | boolean | undefined | null;
    }

    let {label, size = 'md', disabled = false, onclick, tipPosition = 'bottom', class: className = '', ...rest}: Props = $props();
</script>

<Button label={label ?? $t('common.close')} icon={X} display="icon" variant="ghost" {size} {disabled} {onclick} {tipPosition} class={className} {...rest} />
