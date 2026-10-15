<!--
  Instance notices: what features register in `instanceNotices`, shown above every page of the (app) layout.

  Renders nothing while there is no notice. Colours are roles only (theme-roles skill): each severity has its state
  role, written whole in `NOTICE_CLASSES` and `ICON_CLASSES`, so the colour gates see every class.
-->
<script lang="ts">
    import {AlertCircle, AlertTriangle, Info, X} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {instanceNotices, type InstanceNoticeSeverity} from '../instanceNotices.svelte';

    const NOTICE_CLASSES: Record<InstanceNoticeSeverity, string> = {
        info: 'flex items-start gap-3 rounded-lg border border-lf-info-line bg-lf-info-soft px-4 py-3 text-sm text-lf-info-on-soft',
        warning: 'flex items-start gap-3 rounded-lg border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft',
        danger: 'flex items-start gap-3 rounded-lg border border-lf-danger-line bg-lf-danger-soft px-4 py-3 text-sm text-lf-danger-on-soft',
    };

    const ICON_CLASSES: Record<InstanceNoticeSeverity, string> = {
        info: 'mt-0.5 h-4 w-4 shrink-0 text-lf-info',
        warning: 'mt-0.5 h-4 w-4 shrink-0 text-lf-warning',
        danger: 'mt-0.5 h-4 w-4 shrink-0 text-lf-danger',
    };

    const ICONS = {info: Info, warning: AlertTriangle, danger: AlertCircle};
</script>

{#if instanceNotices.list.length > 0}
    <section class="mb-4 space-y-2" aria-label={$_('instance.notices.label')} data-testid="instance-notices">
        {#each instanceNotices.list as notice (notice.id)}
            {@const Icon = ICONS[notice.severity]}
            <div class={NOTICE_CLASSES[notice.severity]} role={notice.severity === 'danger' ? 'alert' : 'status'} data-testid="instance-notice" data-notice-id={notice.id} data-severity={notice.severity}>
                <Icon class={ICON_CLASSES[notice.severity]} aria-hidden="true" />
                <p class="flex-1">
                    {$_(notice.messageKey, {values: notice.params})}
                    {#if notice.action}
                        <a href={notice.action.href} class="ml-1 font-medium underline" data-testid="instance-notice-action">{$_(notice.action.labelKey)}</a>
                    {/if}
                </p>
                {#if notice.dismissible}
                    <button type="button" class="shrink-0 rounded p-0.5 hover:opacity-70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-lf-focus" aria-label={$_('common.close')} data-testid="instance-notice-dismiss" onclick={() => instanceNotices.dismiss(notice.id)}>
                        <X class="h-4 w-4" aria-hidden="true" />
                    </button>
                {/if}
            </div>
        {/each}
    </section>
{/if}
