<!--
  ImportBrokerMismatchModal - a file its broker's default import plugin cannot read.

  Raised by the import wizard right after an upload, one file at a time: the file was probably
  assigned to the wrong broker. It shows where the file is (the broker, with the default plugin that
  cannot read it), the default plugin's notes (its refusal, translated by code), the brokers whose
  default plugin reads the file, and three answers: move the file there, keep it where it is (the
  plugin is then chosen as before), or remove it. Closing it keeps the file.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import {AlertTriangle, CheckCircle2, MessageSquareText, XCircle} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';

    /** A broker as the modal shows it: the icon fields follow BrokerIcon's chain. */
    export interface BrokerMismatchBroker {
        id: number;
        name: string;
        iconUrl?: string | null;
        portalUrl?: string | null;
        /** The broker's default import plugin, the last link of BrokerIcon's chain. */
        pluginCode?: string | null;
    }

    /** An import plugin as the modal shows it, its name in the UI language. */
    export interface BrokerMismatchPlugin {
        code: string;
        name: string;
        iconUrl?: string | null;
    }

    /** A broker that can take the file, with its default import plugin. */
    export interface BrokerMismatchTarget extends BrokerMismatchBroker {
        plugin: BrokerMismatchPlugin;
    }

    interface Props {
        open: boolean;
        /** Identifies the file on screen: a new file resets the chosen target. */
        fileKey: string;
        fileName: string;
        /** The broker the file was uploaded to. */
        broker: BrokerMismatchBroker;
        /** Its default import plugin, which cannot read the file. */
        defaultPlugin: BrokerMismatchPlugin;
        /** The default plugin's reason, already in the UI language; null when it gave none. */
        reason: string | null;
        /** Brokers whose default plugin reads the file. */
        targets: BrokerMismatchTarget[];
        /** Names of the plugins that read the file, shown when no broker uses one by default. */
        readerNames: string[];
        /** Position in the queue of files to review. */
        current: number;
        total: number;
        /** A move or a removal is running. */
        busy?: boolean;
        onMove: (brokerId: number) => void;
        onKeep: () => void;
        onRemove: () => void;
        zIndex?: number;
    }

    let {open, fileKey, fileName, broker, defaultPlugin, reason, targets, readerNames, current, total, busy = false, onMove, onKeep, onRemove, zIndex = 70}: Props = $props();

    let chosen = $state<{fileKey: string; brokerId: number} | null>(null);
    let selectedTarget = $derived((chosen?.fileKey === fileKey ? targets.find((target) => target.id === chosen?.brokerId) : undefined) ?? targets[0] ?? null);

    function requestClose() {
        if (!busy) onKeep();
    }
</script>

{#snippet targetBody(target: BrokerMismatchTarget)}
    <BrokerIcon brokerId={target.id} iconUrl={target.iconUrl} portalUrl={target.portalUrl} pluginCode={target.pluginCode} altText={target.name} size="md" />
    <span class="party-text">
        <span class="party-name">{target.name}</span>
        <span class="plugin-chip reads">
            <BrokerIcon iconUrl={target.plugin.iconUrl} altText={target.plugin.name} size={16} />
            <span class="plugin-name">{target.plugin.name}</span>
            <CheckCircle2 class="shrink-0" size={13} />
            <span class="verdict">{$t('importWizard.brokerMismatch.canRead')}</span>
        </span>
    </span>
{/snippet}

<ModalBase maxWidth="max-w-lg" onRequestClose={requestClose} {open} {zIndex} testId="import-broker-mismatch-modal">
    <div class="modal-header">
        <AlertTriangle class="text-amber-500 shrink-0" size={22} />
        <h2 class="modal-title">{$t('importWizard.brokerMismatch.title')}</h2>
        {#if total > 1}
            <span class="counter" data-testid="import-broker-mismatch-counter">{$t('importWizard.brokerMismatch.counter', {values: {current, total}})}</span>
        {/if}
    </div>

    <div class="modal-body">
        <p class="message" data-testid="import-broker-mismatch-intro">
            {$t('importWizard.brokerMismatch.intro', {values: {file: fileName, broker: broker.name, plugin: defaultPlugin.name}})}
        </p>

        <section class="section">
            <span class="section-label">{$t('importWizard.brokerMismatch.fromLabel')}</span>
            <div class="party from" data-testid="import-broker-mismatch-from">
                <BrokerIcon brokerId={broker.id} iconUrl={broker.iconUrl} portalUrl={broker.portalUrl} pluginCode={broker.pluginCode} altText={broker.name} size="md" />
                <span class="party-text">
                    <span class="party-name">{broker.name}</span>
                    <span class="plugin-chip refuses">
                        <BrokerIcon iconUrl={defaultPlugin.iconUrl} altText={defaultPlugin.name} size={16} />
                        <span class="plugin-name">{defaultPlugin.name}</span>
                        <XCircle class="shrink-0" size={13} />
                        <span class="verdict">{$t('importWizard.brokerMismatch.cannotRead')}</span>
                    </span>
                </span>
            </div>
        </section>

        {#if reason}
            <div class="reason" data-testid="import-broker-mismatch-reason">
                <span class="reason-label">
                    <MessageSquareText class="shrink-0" size={14} />
                    {$t('importWizard.brokerMismatch.reasonTitle')}
                </span>
                <p class="reason-text">{reason}</p>
            </div>
        {/if}

        {#if targets.length === 1}
            <section class="section">
                <span class="section-label">{$t('importWizard.brokerMismatch.toLabel')}</span>
                <div class="party target selected" data-testid="import-broker-mismatch-target">
                    {@render targetBody(targets[0])}
                </div>
            </section>
        {:else if targets.length > 1}
            <section class="section">
                <span class="section-label">{$t('importWizard.brokerMismatch.targetMany')}</span>
                <div class="targets" role="radiogroup" data-testid="import-broker-mismatch-targets">
                    {#each targets as target (target.id)}
                        <label class="party target {selectedTarget?.id === target.id ? 'selected' : ''}" data-testid="import-broker-mismatch-target-{target.id}">
                            <input type="radio" name="import-broker-mismatch-target" checked={selectedTarget?.id === target.id} onchange={() => (chosen = {fileKey, brokerId: target.id})} disabled={busy} />
                            {@render targetBody(target)}
                        </label>
                    {/each}
                </div>
            </section>
        {:else if readerNames.length > 0}
            <p class="message" data-testid="import-broker-mismatch-no-target">{$t('importWizard.brokerMismatch.noTarget', {values: {plugins: readerNames.join(', ')}})}</p>
        {:else}
            <p class="message" data-testid="import-broker-mismatch-no-reader">{$t('importWizard.brokerMismatch.noReader')}</p>
        {/if}
    </div>

    <div class="modal-footer">
        <button type="button" class="btn btn-danger-outline" onclick={onRemove} disabled={busy} data-testid="import-broker-mismatch-remove">
            {$t('importWizard.brokerMismatch.remove')}
        </button>
        <span class="spacer"></span>
        <button type="button" class="btn btn-secondary" onclick={onKeep} disabled={busy} data-testid="import-broker-mismatch-keep">
            {$t('importWizard.brokerMismatch.keep')}
        </button>
        {#if selectedTarget}
            <button type="button" class="btn btn-primary" onclick={() => selectedTarget && onMove(selectedTarget.id)} disabled={busy} data-testid="import-broker-mismatch-move">
                <BrokerIcon brokerId={selectedTarget.id} iconUrl={selectedTarget.iconUrl} portalUrl={selectedTarget.portalUrl} pluginCode={selectedTarget.pluginCode} altText="" size={18} />
                {$t('importWizard.brokerMismatch.move', {values: {broker: selectedTarget.name}})}
            </button>
        {/if}
    </div>
</ModalBase>

<style>
    .modal-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid #e2e8f0;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #334155;
    }

    .modal-title {
        flex: 1;
        font-size: 1.125rem;
        font-weight: 600;
        color: #0f172a;
        margin: 0;
    }

    :global(.dark) .modal-title {
        color: #f1f5f9;
    }

    .counter {
        font-size: 0.75rem;
        color: #64748b;
        white-space: nowrap;
    }

    :global(.dark) .counter {
        color: #94a3b8;
    }

    .modal-body {
        display: flex;
        flex-direction: column;
        gap: 0.875rem;
        padding: 1.25rem;
        overflow-y: auto;
    }

    .message {
        color: #475569;
        line-height: 1.6;
        margin: 0;
        overflow-wrap: anywhere;
    }

    :global(.dark) .message {
        color: #94a3b8;
    }

    .reason {
        border-left: 3px solid #f59e0b;
        background: #fffbeb;
        border-radius: 6px;
        padding: 0.625rem 0.875rem;
    }

    :global(.dark) .reason {
        background: rgba(245, 158, 11, 0.12);
    }

    .reason-label {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: #92400e;
        margin-bottom: 0.25rem;
    }

    :global(.dark) .reason-label {
        color: #fcd34d;
    }

    .reason-text {
        margin: 0;
        font-size: 0.875rem;
        color: #334155;
        line-height: 1.5;
    }

    :global(.dark) .reason-text {
        color: #e2e8f0;
    }

    .section {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .section-label {
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #64748b;
    }

    :global(.dark) .section-label {
        color: #94a3b8;
    }

    .targets {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .party {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.625rem 0.75rem;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        background: #f8fafc;
    }

    :global(.dark) .party {
        border-color: #334155;
        background: rgba(15, 23, 42, 0.4);
    }

    .party.from {
        border-color: #fecaca;
        background: #fef2f2;
    }

    :global(.dark) .party.from {
        border-color: #7f1d1d;
        background: rgba(127, 29, 29, 0.15);
    }

    label.target {
        cursor: pointer;
    }

    .target.selected {
        border-color: #1a4031;
        background: #f0fdf4;
        box-shadow: 0 0 0 1px #1a4031;
    }

    :global(.dark) .target.selected {
        border-color: #4ade80;
        background: rgba(22, 101, 52, 0.18);
        box-shadow: 0 0 0 1px #4ade80;
    }

    .party-text {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        min-width: 0;
    }

    .party-name {
        font-weight: 600;
        color: #0f172a;
        overflow-wrap: anywhere;
    }

    :global(.dark) .party-name {
        color: #f1f5f9;
    }

    .plugin-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        align-self: flex-start;
        max-width: 100%;
        padding: 0.125rem 0.5rem 0.125rem 0.25rem;
        border-radius: 999px;
        font-size: 0.75rem;
        line-height: 1.25rem;
    }

    .plugin-chip.refuses {
        background: #fee2e2;
        color: #991b1b;
    }

    :global(.dark) .plugin-chip.refuses {
        background: rgba(220, 38, 38, 0.2);
        color: #fca5a5;
    }

    .plugin-chip.reads {
        background: #dcfce7;
        color: #166534;
    }

    :global(.dark) .plugin-chip.reads {
        background: rgba(34, 197, 94, 0.18);
        color: #86efac;
    }

    .plugin-name {
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .verdict {
        white-space: nowrap;
    }

    .modal-footer {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem 1.25rem;
        border-top: 1px solid #e2e8f0;
    }

    :global(.dark) .modal-footer {
        border-top-color: #334155;
    }

    .spacer {
        flex: 1;
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-radius: 6px;
        border: 1px solid transparent;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .btn-secondary {
        background: #f1f5f9;
        color: #475569;
    }

    .btn-secondary:hover:not(:disabled) {
        background: #e2e8f0;
    }

    :global(.dark) .btn-secondary {
        background: #334155;
        color: #e2e8f0;
    }

    .btn-primary {
        background: #1a4031;
        color: white;
    }

    .btn-primary:hover:not(:disabled) {
        background: #153428;
    }

    .btn-danger-outline {
        background: transparent;
        border-color: #fca5a5;
        color: #dc2626;
    }

    .btn-danger-outline:hover:not(:disabled) {
        background: #fef2f2;
    }

    :global(.dark) .btn-danger-outline {
        border-color: #7f1d1d;
        color: #f87171;
    }

    :global(.dark) .btn-danger-outline:hover:not(:disabled) {
        background: rgba(220, 38, 38, 0.12);
    }
</style>
