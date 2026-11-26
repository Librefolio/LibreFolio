<!--
  A group of buttons joined into segments (85 BTN-2·0, the consultant's C2): the view toggles, the period presets.
  Only a thin wrapper: `role="group"` with its name, the outer border, the dividers, the rounded clip. Its `Button`s draw
  as joined segments (`buttonClasses({segment: true, joined: true})`: no border or radius of their own, the focus inside,
  on the card: C18) and stay toggles with `aria-pressed` — not radios.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {provideButtonGroup} from './buttonGroup';

    interface Props {
        /** Mandatory: what the group chooses («View», «Period»), for the reader. */
        label: string;
        /** Size and position only. */
        class?: string;
        children: Snippet;
        [key: `data-${string}`]: string | number | boolean | undefined | null;
    }

    let {label, class: className = '', children, ...rest}: Props = $props();

    provideButtonGroup();
</script>

<div role="group" aria-label={label} class="inline-flex divide-x divide-lf-subtle overflow-hidden rounded-lg border border-lf-subtle {className}" {...rest}>
    {@render children()}
</div>
