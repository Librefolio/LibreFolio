<!--
  The user's share of a Broker and their role on it, as one badge: the percentage, then the role's icon (a crown for the
  owner, a pencil for an editor, an eye for a viewer), on the role's tint. The Broker page's header draws it, and the
  Rebalancer's positions too (R1-D of project 67: «la quota del conto come badge con la corona e la percentuale,
  similmente a come avviene in broker detail»). Each caller formats the share its own way and passes the text. With no
  role there is no icon and a neutral tint: a crown is never drawn by default.
-->
<script lang="ts">
    import {Crown, Eye, Pencil} from 'lucide-svelte';
    import {_} from '$lib/i18n';

    interface Props {
        /** OWNER, EDITOR or VIEWER; null when not known. */
        role?: string | null;
        /** The share, already formatted by the caller; null for none. */
        share?: string | null;
        size?: number;
        /** The hover text; the role's name when absent. */
        title?: string;
        testid?: string;
        /** Extra attributes for the caller's selectors (`data-position-key`). */
        [attribute: `data-${string}`]: string | undefined;
    }

    let {role = null, share = null, size = 13, title, testid, ...rest}: Props = $props();

    // colour: closest role, to review: broker role badge (owner amber, editor blue, viewer grey) on warning, info and neutral tints
    const tone = $derived(role === 'OWNER' ? 'bg-lf-warning-soft text-lf-warning-on-soft' : role === 'EDITOR' ? 'bg-lf-info-soft text-lf-info-on-soft' : 'bg-lf-neutral text-lf-secondary');
    const roleName = $derived(role === 'OWNER' ? $_('brokers.sharing.roleOwnerShort') : role === 'EDITOR' ? $_('brokers.sharing.roleEditorShort') : role === 'VIEWER' ? $_('brokers.sharing.roleViewerShort') : undefined);
</script>

<span class="inline-flex flex-shrink-0 items-center gap-1 rounded-full px-2 py-1 {tone}" title={title ?? roleName} data-testid={testid} data-role={role ?? undefined} {...rest}>
    {#if share !== null}
        <span class="text-xs font-medium">{share}</span>
    {/if}
    {#if role === 'OWNER'}<Crown {size} aria-hidden="true" />{:else if role === 'EDITOR'}<Pencil {size} aria-hidden="true" />{:else if role === 'VIEWER'}<Eye {size} aria-hidden="true" />{/if}
</span>
