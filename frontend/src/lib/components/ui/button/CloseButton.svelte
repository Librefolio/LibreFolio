<!--
  The ✕ of a dialog, a panel or a banner (project 85, BTN-0): the standard button, icon only, ghost, named
  «Close» in the user's language unless the caller gives a more precise name («Close editor»). Fixes D7: a ✕ never
  comes without a name. `variant="bar-ghost"` on the green sidebar; `tint` on a fill of a state (a toast, a banner: the
  fill's text, the hover a step down the family). A position goes on a wrapper, never in `class` (BTN-2·0).
-->
<script lang="ts">
    import {X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import Button from './Button.svelte';
    import type {ButtonSize, ButtonTone} from './buttonClasses';
    import type {TipPosition} from './pressable.svelte';

    interface Props {
        /** The name; defaults to `common.close`. */
        label?: string;
        size?: ButtonSize;
        /** `ghost` on a page or a dialog, `bar-ghost` on the green sidebar. */
        variant?: 'ghost' | 'bar-ghost';
        /** The ✕ stands on a fill of this state (a toast, a banner). */
        tint?: ButtonTone;
        disabled?: boolean;
        onclick?: (event: MouseEvent) => void;
        tipPosition?: TipPosition;
        /** Size and position only. */
        class?: string;
        [key: `data-${string}`]: string | number | boolean | undefined | null;
    }

    let {label, size = 'md', variant = 'ghost', tint, disabled = false, onclick, tipPosition = 'bottom', class: className = '', ...rest}: Props = $props();
</script>

<Button label={label ?? $t('common.close')} icon={X} display="icon" {variant} {tint} {size} {disabled} {onclick} {tipPosition} class={className} {...rest} />
