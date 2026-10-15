<!--
LinkShare — one link to share (invitation, password reset): the server address, editable, the link built on it, a copy
button and the registered extra actions (`linkShareActions.ts`).

The address starts from `LIBREFOLIO_PUBLIC_URL` when the backend used it for `url`, from the browser's origin otherwise
(decision D-A3). Once the administrator changes it, a check from the browser says whether this very instance answers
there (`addressProbe.ts`); whatever the answer, the link can be copied — only an address that is not one turns it off.
-->
<script lang="ts">
    import {Copy} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {formatDateTime} from '$lib/utils/core/formatDateTime';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import type {LinkPurpose} from '$lib/features/auth/linkToken';
    import {composeLink, initialBase} from './linkShare';
    import {checkAddress, normalizeBase, type ProbeVerdict} from './addressProbe';
    import {visibleLinkShareActions, type LinkShareContext} from './linkShareActions';

    interface Props {
        purpose: LinkPurpose;
        /** The path of the page that takes the token, the token in the fragment. */
        path: string;
        /** `LIBREFOLIO_PUBLIC_URL` followed by `path`, or null when the variable is not set. */
        url: string | null;
        expiresAt: string;
        context?: LinkShareContext;
    }

    let {purpose, path, url, expiresAt, context = {}}: Props = $props();

    type ProbeState = 'idle' | 'checking' | ProbeVerdict | 'invalid';

    const PROBE_DEBOUNCE_MS = 500;
    const PROBE_TONE: Record<ProbeState, string> = {
        idle: 'text-lf-muted',
        checking: 'text-lf-muted',
        match: 'text-lf-success',
        mismatch: 'text-lf-warning',
        unverifiable: 'text-lf-muted',
        invalid: 'text-lf-danger',
    };
    const PROBE_MESSAGE: Record<Exclude<ProbeState, 'idle'>, string> = {
        checking: 'settings.linkShare.probe.checking',
        match: 'settings.linkShare.probe.match',
        mismatch: 'settings.linkShare.probe.mismatch',
        unverifiable: 'settings.linkShare.probe.unverifiable',
        invalid: 'settings.linkShare.probe.invalid',
    };

    const uid = $props.id();
    const startBase = $derived(initialBase(url, path, window.location.origin));
    let edited = $state<string | null>(null);
    const address = $derived(edited ?? startBase);
    const normalized = $derived(normalizeBase(address));
    const normalizedStart = $derived(normalizeBase(startBase) ?? startBase);
    const link = $derived(composeLink(normalized ?? address.trim(), path));
    const actions = $derived(visibleLinkShareActions(purpose, context));

    let probeState = $state<ProbeState>('idle');
    let linkInput = $state<HTMLInputElement>();
    let generation = 0;

    async function issueNonce(): Promise<string> {
        const issued = await zodiosApi.issue_address_probe_api_v1_users_address_probe_post(undefined);
        return issued.nonce;
    }

    // A check only for an address the administrator changed, 500 ms after the last keystroke; a newer edit outruns
    // an older check, whose answer is then dropped
    $effect(() => {
        void address;
        const base = normalized;
        const start = normalizedStart;
        const mine = ++generation;
        if (base === null) {
            probeState = 'invalid';
            return;
        }
        probeState = 'idle';
        if (base === start) {
            return;
        }
        const timer = setTimeout(async () => {
            if (mine !== generation) {
                return;
            }
            probeState = 'checking';
            const verdict = await checkAddress(base, {issueNonce});
            if (mine !== generation) {
                return;
            }
            probeState = verdict;
            notify({name: 'accounts.address.checked', detail: {state: verdict, purpose}});
        }, PROBE_DEBOUNCE_MS);
        return () => clearTimeout(timer);
    });

    function onAddressInput(event: Event) {
        edited = (event.currentTarget as HTMLInputElement).value;
    }

    async function copyLink() {
        if (probeState === 'invalid') {
            return;
        }
        try {
            await writeTextToClipboard(link);
            notify({name: 'accounts.link.copied', detail: {purpose}, toast: {variant: 'success', message: $_('settings.linkShare.copied')}});
        } catch {
            // Neither the Clipboard API nor the legacy copy worked: the link is selected for a manual copy
            linkInput?.focus();
            linkInput?.select();
        }
    }
</script>

<div class="space-y-3 text-lf-primary" data-purpose={purpose} data-testid="link-share">
    <div>
        <label class="mb-1 block text-sm font-medium text-lf-secondary" for="{uid}-address">{$_('settings.linkShare.addressLabel')}</label>
        <input
            autocomplete="off"
            class="w-full rounded-md border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-2 focus:ring-lf-focus"
            data-testid="link-share-address"
            id="{uid}-address"
            oninput={onAddressInput}
            spellcheck="false"
            type="url"
            value={address}
        />
        <p class="mt-1 text-xs text-lf-muted">{$_('settings.linkShare.addressHint')}</p>
        <p aria-live="polite" class="mt-1 min-h-4 text-xs {PROBE_TONE[probeState]}" data-state={probeState} data-testid="link-share-probe">
            {probeState === 'idle' ? '' : $_(PROBE_MESSAGE[probeState])}
        </p>
    </div>

    <div>
        <label class="mb-1 block text-sm font-medium text-lf-secondary" for="{uid}-link">{$_('settings.linkShare.linkLabel')}</label>
        <div class="flex gap-2">
            <input bind:this={linkInput} class="w-full min-w-0 rounded-md border border-lf-input bg-lf-panel px-3 py-2 font-mono text-xs text-lf-primary focus:outline-none focus:ring-2 focus:ring-lf-focus" data-testid="link-share-link" id="{uid}-link" readonly type="text" value={link} />
            <button
                class="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-lf-action px-3 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50"
                data-testid="link-share-copy"
                disabled={probeState === 'invalid'}
                onclick={copyLink}
                type="button"
            >
                <Copy class="h-4 w-4" />
                {$_('settings.linkShare.copy')}
            </button>
        </div>
        <p class="mt-1 text-xs text-lf-muted" data-expires-at={expiresAt} data-testid="link-share-expires">
            {$_('settings.linkShare.expires', {values: {date: formatDateTime(expiresAt)}})}
        </p>
    </div>

    <div class="flex flex-wrap gap-2" data-testid="link-share-actions">
        {#each actions as action (action.id)}
            <action.component {context} {link} {purpose} />
        {/each}
    </div>
</div>
