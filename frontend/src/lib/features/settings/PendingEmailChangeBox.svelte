<!--
  PendingEmailChangeBox — under the Email row of Profile while a change of address waits for its link (release 1.4,
  project 71, decision D5.3 P1): the waiting address written in full, so a typo shows; what happens next; until when the
  link works; «Send again» and «Cancel the request». A controlled component: the profile calls the server and passes
  `busy` while it does. An information box (blue), as wide as the row: the text on the left, the buttons on the right;
  on a phone the text wraps and the buttons go under it. Svelte 5 runes.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Clock, Send, X} from 'lucide-svelte';
    import {STATUS_TONES} from '$lib/theme/toneClasses';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';

    interface Props {
        /** The address the account will have once the link sent to it is clicked. */
        email: string;
        /** When the link stops working (ISO 8601, from the API). */
        expiresAt: string;
        /** A request of the profile is running: both buttons wait. */
        busy?: boolean;
        onResend: () => void;
        onCancel: () => void;
    }

    let {email, expiresAt, busy = false, onResend, onCancel}: Props = $props();

    const expiresLabel = $derived(formatDateTime(expiresAt));
    /** The buttons inside a banner stand on the card, edged in the banner's state (design system, rule 12). */
    const buttonTone = `${STATUS_TONES.bannerChip.info.base} ${STATUS_TONES.bannerChip.info.hover}`;
</script>

<div class="flex flex-col sm:flex-row sm:items-start gap-3 rounded-lg border border-lf-info-line bg-lf-info-soft text-lf-info-on-soft px-4 py-3 text-sm" data-testid="profile-email-pending" data-busy={busy ? 'true' : 'false'} data-expires-at={expiresAt} aria-busy={busy}>
    <div class="flex items-start gap-3 flex-1 min-w-0">
        <Clock size={18} class="shrink-0 mt-0.5 text-lf-info" aria-hidden="true" />
        <div class="min-w-0">
            <p class="font-semibold">
                {$_('settings.emailPending.title')}
                <span class="break-all" data-testid="profile-email-pending-address">{email}</span>
            </p>
            <p class="mt-1">{$_('settings.emailPending.body')}</p>
            <p class="mt-1">
                {$_('settings.emailPending.expires')}
                <time datetime={expiresAt} data-testid="profile-email-pending-expires">{expiresLabel}</time>.
            </p>
        </div>
    </div>
    <div class="flex flex-wrap gap-2 sm:shrink-0">
        <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors focus-visible:outline-lf-focus disabled:opacity-50 disabled:cursor-not-allowed {buttonTone}"
            data-testid="profile-email-pending-resend"
            disabled={busy}
            onclick={() => !busy && onResend()}
        >
            <Send size={14} aria-hidden="true" />
            {$_('settings.emailPending.resend')}
        </button>
        <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors focus-visible:outline-lf-focus disabled:opacity-50 disabled:cursor-not-allowed {buttonTone}"
            data-testid="profile-email-pending-cancel"
            disabled={busy}
            onclick={() => !busy && onCancel()}
        >
            <X size={14} aria-hidden="true" />
            {$_('settings.emailPending.cancel')}
        </button>
    </div>
</div>
