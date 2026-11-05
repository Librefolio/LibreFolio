<!--
  The clean-up of the backups the instance keeps (lot FB-24): how much space they may take, and how long they stay.

  Two global settings, saved together: `backup_cleanup_max_mb` and `backup_cleanup_max_days`; 0 switches a rule off.
  The latest backup is always kept. On a hosted (managed) instance the size limit cannot be switched off: its field
  starts at 1 and the server refuses a 0.

  A panel that starts closed (K-3). Published state: `data-state` (`loading`, `idle`, `saving`, `saved`, `error`) and `data-error-code` (empty unless
  `error`). Event: `backup.cleanup.saved`.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {CircleCheck, Eraser, LoaderCircle, TriangleAlert} from 'lucide-svelte';
    import {managedConfirmed} from '$lib/features/instance/profile';
    import FoldPanel from '$lib/components/ui/display/FoldPanel.svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {cleanupSaveCode, getCleanupSettings, saveCleanupSettings} from './backupApi';

    type PanelState = 'loading' | 'idle' | 'saving' | 'saved' | 'error';

    let panelState = $state<PanelState>('loading');
    let errorCode = $state('');
    // What the server holds, and what is typed (text: an empty or half-typed field is not a number yet).
    let saved = $state({maxMb: 0, maxDays: 0});
    let maxMb = $state('0');
    let maxDays = $state('0');

    // The profile the server confirmed: before its answer the field takes the self-hosted rule, and the server refuses a 0 on a managed one anyway.
    const managed = $derived(managedConfirmed());

    function wholeNumber(text: string): number | null {
        return /^\d+$/.test(text.trim()) ? Number.parseInt(text.trim(), 10) : null;
    }

    const typedMb = $derived(wholeNumber(maxMb));
    const typedDays = $derived(wholeNumber(maxDays));
    const valid = $derived(typedMb !== null && typedDays !== null);
    const changed = $derived(typedMb !== saved.maxMb || typedDays !== saved.maxDays);
    const canSave = $derived(panelState !== 'loading' && panelState !== 'saving' && valid && changed);

    onMount(() => {
        void getCleanupSettings().then(
            (settings) => {
                saved = settings;
                maxMb = String(settings.maxMb);
                maxDays = String(settings.maxDays);
                panelState = 'idle';
            },
            () => {
                // The settings cannot be read: the fields stay at 0 and saving is the only way forward.
                panelState = 'idle';
            },
        );
    });

    function edited() {
        // A new edit takes the «saved» tick away; a refusal stays on screen until the next save.
        if (panelState === 'saved') panelState = 'idle';
    }

    async function save() {
        if (!canSave || typedMb === null || typedDays === null) return;
        const settings = {maxMb: typedMb, maxDays: typedDays};
        panelState = 'saving';
        errorCode = '';
        try {
            await saveCleanupSettings(settings);
        } catch (error) {
            errorCode = cleanupSaveCode(error);
            panelState = 'error';
            return;
        }
        saved = settings;
        panelState = 'saved';
        notify({name: 'backup.cleanup.saved', detail: {max_mb: settings.maxMb, max_days: settings.maxDays}});
    }

    const fieldClass = 'w-full rounded-lg border border-lf-input bg-lf-field px-3 py-2 text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:outline-none focus:ring-1 focus:ring-lf-focus disabled:opacity-50';
</script>

<div data-testid="backup-cleanup" data-state={panelState} data-error-code={panelState === 'error' ? errorCode : ''} aria-busy={panelState === 'loading' || panelState === 'saving'}>
    <!-- K-3: the clean-up is an advanced setting: a panel that starts closed, under the list of the backups. -->
    <FoldPanel title={$_('backup.cleanup.title')} testId="backup-cleanup-fold">
        <p class="flex items-start gap-2 text-sm text-lf-secondary">
            <Eraser class="mt-0.5 shrink-0 text-lf-secondary" size={16} aria-hidden="true" />
            <span>{$_('backup.cleanup.description')}</span>
        </p>

        <div class="grid gap-4 sm:grid-cols-2">
            <div class="space-y-1">
                <label class="block text-sm font-medium text-lf-secondary" for="backup-cleanup-max-mb">{$_('backup.cleanup.maxMb')}</label>
                <input class={fieldClass} id="backup-cleanup-max-mb" data-testid="backup-cleanup-max-mb" type="number" inputmode="numeric" step="1" min={managed ? 1 : 0} value={maxMb} disabled={panelState === 'loading'} oninput={(event) => ((maxMb = event.currentTarget.value), edited())} />
                <p class="text-xs text-lf-muted">{managed ? $_('backup.cleanup.hintManaged') : $_('backup.cleanup.hintSelfhosted')}</p>
            </div>
            <div class="space-y-1">
                <label class="block text-sm font-medium text-lf-secondary" for="backup-cleanup-max-days">{$_('backup.cleanup.maxDays')}</label>
                <input class={fieldClass} id="backup-cleanup-max-days" data-testid="backup-cleanup-max-days" type="number" inputmode="numeric" step="1" min="0" value={maxDays} disabled={panelState === 'loading'} oninput={(event) => ((maxDays = event.currentTarget.value), edited())} />
                <p class="text-xs text-lf-muted">{$_('backup.cleanup.hintDays')}</p>
            </div>
        </div>

        <p class="text-xs text-lf-muted" data-testid="backup-cleanup-latest-kept">{$_('backup.cleanup.latestKept')}</p>

        {#if panelState === 'error'}
            <div class="flex items-start gap-2 rounded-lg border border-lf-danger-line bg-lf-danger-soft p-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="backup-cleanup-error" data-error-code={errorCode}>
                <TriangleAlert class="mt-0.5 shrink-0" size={16} aria-hidden="true" />
                <span>{$_(`backup.cleanup.errors.${errorCode}`)}</span>
            </div>
        {/if}

        <div class="flex flex-wrap items-center gap-3">
            <button
                class="inline-flex items-center gap-2 rounded-lg bg-lf-action px-4 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                data-testid="backup-cleanup-save"
                disabled={!canSave}
                onclick={() => void save()}
            >
                {#if panelState === 'saving'}
                    <LoaderCircle class="animate-spin" size={16} aria-hidden="true" />
                {/if}
                {$_('backup.cleanup.save')}
            </button>
            {#if panelState === 'saved'}
                <span class="inline-flex items-center gap-1.5 text-sm text-lf-success" data-testid="backup-cleanup-saved">
                    <CircleCheck size={16} aria-hidden="true" />
                    {$_('backup.cleanup.saved')}
                </span>
            {/if}
        </div>
    </FoldPanel>
</div>
