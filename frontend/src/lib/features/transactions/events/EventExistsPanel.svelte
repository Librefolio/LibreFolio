<!--
  EventExistsPanel.svelte — Svelte 5

  «+ New event» never overwrites (decision 20 of release 1.3): when the asset already has an event of the
  same type on that date, the create is refused (409 EVENT_EXISTS) and this panel shows what is there.
  Per event: «Use this» links it; «Edit this» opens it in the form (manual events only: a provider's event
  is rewritten by every refresh, so it is not edited here). «Cancel» goes back to the form.
  Colours: roles only (lib/theme/tokens.css).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {getEventTypeOptions, EVENT_TYPES_ALL} from '$lib/features/transactions/events/eventTypes';
    import {existingAmountText, type ExistingEvent} from './eventSaveError';

    interface Props {
        events: ExistingEvent[];
        onuse: (event: ExistingEvent) => void;
        onedit: (event: ExistingEvent) => void;
        oncancel: () => void;
    }

    let {events, onuse, onedit, oncancel}: Props = $props();

    const typeOptions = $derived(getEventTypeOptions($t, EVENT_TYPES_ALL));

    function typeName(type: string): string {
        const option = typeOptions.find((o) => o.value === type);
        return option ? `${option.emoji} ${option.label}` : type;
    }

    function dateName(iso: string): string {
        return new Date(`${iso}T00:00:00`).toLocaleDateString(uiLocale(), {day: 'numeric', month: 'short', year: 'numeric'});
    }
</script>

<div class="space-y-3 rounded-lg border border-lf-warning-line bg-lf-warning-soft p-3 text-lf-warning-on-soft" data-testid="event-exists-panel">
    <div class="space-y-1">
        <p class="text-sm font-semibold">{$t('events.exists.title')}</p>
        <p class="text-xs">{$t('events.exists.hint')}</p>
    </div>

    <ul class="space-y-2">
        {#each events as event (event.id)}
            <li class="space-y-2 rounded-md border border-lf-subtle bg-lf-card p-3 text-lf-primary" data-testid="event-exists-item" data-event-id={event.id}>
                <div class="flex items-center justify-between gap-2 text-sm">
                    <span class="font-medium">{typeName(event.type)} · {dateName(event.date)}</span>
                    <span class="whitespace-nowrap font-mono">
                        <span>{existingAmountText(event.value.amount)}</span>
                        <span class="text-lf-muted">{event.value.code}</span>
                    </span>
                </div>
                {#if event.notes}
                    <p class="text-xs text-lf-secondary">📝 {event.notes}</p>
                {/if}
                <p class="text-xs text-lf-muted">
                    {event.is_auto ? $t('events.exists.fromProvider') : $t('events.exists.manual')} · {$t('events.exists.linked', {values: {n: event.linked_transactions}})}
                </p>
                {#if event.is_auto}
                    <p class="text-xs text-lf-muted" data-testid="event-exists-provider-note">{$t('events.exists.providerNotEditable')}</p>
                {/if}
                <div class="flex justify-end gap-2">
                    {#if !event.is_auto}
                        <button type="button" class="rounded-lg border border-lf-input px-3 py-1.5 text-sm text-lf-secondary transition-colors hover:bg-lf-hover" data-testid="event-exists-edit" onclick={() => onedit(event)}>
                            {$t('events.exists.edit')}
                        </button>
                    {/if}
                    <button type="button" class="rounded-lg bg-lf-action px-3 py-1.5 text-sm text-lf-on-action transition-colors hover:bg-lf-action-hover" data-testid="event-exists-use" onclick={() => onuse(event)}>
                        {$t('events.exists.use')}
                    </button>
                </div>
            </li>
        {/each}
    </ul>

    <div class="flex justify-end">
        <button type="button" class="rounded-lg px-3 py-1.5 text-sm text-lf-secondary transition-colors hover:bg-lf-hover" data-testid="event-exists-cancel" onclick={oncancel}>
            {$t('common.cancel')}
        </button>
    </div>
</div>
