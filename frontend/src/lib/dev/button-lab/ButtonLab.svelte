<!--
  The Button Lab (project 85, BTN-0): every case of the standard button, to try with a finger on a real phone (iPhone
  and Android) before the areas migrate. Debug builds only (`routes/button-lab`). What happened is written in the log at
  the top, so a long press that did nothing is told from a tap that acted.

  Texts in English on purpose: a developer's bench, never shown to a user.
-->
<script lang="ts">
    import {Download, Pencil, Plus, RefreshCw, Sparkles, Star, Trash2} from 'lucide-svelte';
    import Button from '$lib/components/ui/button/Button.svelte';
    import CloseButton from '$lib/components/ui/button/CloseButton.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';
    import {createResponsiveLayout} from '$lib/utils/layout/responsiveLayout.svelte';

    interface LogEntry {
        id: number;
        event: string;
        at: string;
    }

    let log = $state<LogEntry[]>([]);
    let nextId = 0;

    function note(event: string) {
        log = [{id: nextId++, event, at: new Date().toLocaleTimeString()}, ...log].slice(0, 8);
    }

    let width = $state(360);
    /** The page toolbar's own mechanism (PageToolbar): one ResizeObserver, the words hide under `labelHideActions`. The
     *  Button takes the decision through `compact`; it measures nothing itself. Only that threshold matters here. */
    const AUTO_LABEL_HIDE_PX = 360;
    const autoLayout = createResponsiveLayout({oneRow: 0, denseRow: 0, stackFilters: 0, oneColumn: 0, labelHideActions: AUTO_LABEL_HIDE_PX, labelHideTabs: 0});
    let autoBox = $state<HTMLDivElement | null>(null);
    $effect(() => {
        const el = autoBox;
        if (!el) return;
        autoLayout.attach(el);
        return () => autoLayout.detach();
    });
    let busy = $state(false);
    let starred = $state(false);
    let selection = $state<string[]>([]);

    function startBusy() {
        note('action: save (busy 2 s)');
        busy = true;
        setTimeout(() => {
            busy = false;
            note('save finished');
        }, 2000);
    }

    interface LabRow {
        id: string;
        name: string;
    }

    const rows: LabRow[] = [
        {id: 'r1', name: 'First row'},
        {id: 'r2', name: 'Second row'},
        {id: 'r3', name: 'Third row'},
    ];

    const columns: ColumnDef<LabRow>[] = [
        {id: 'name', header: 'Name', type: 'text', cell: (row) => row.name},
        {
            id: 'open',
            header: 'Open',
            type: 'custom',
            cell: (row) => ({
                type: 'custom',
                component: Button,
                props: {label: `Open ${row.name}`, icon: Download, display: 'icon', size: 'sm', variant: 'ghost', onclick: () => note(`action: open ${row.id}`), 'data-testid': `lab-row-open-${row.id}`},
            }),
        },
    ];

    const rowActions: RowAction<LabRow>[] = [{id: 'menu-edit', icon: Pencil, label: 'Edit', onClick: (row) => note(`row menu: edit ${row.id}`)}];
</script>

<main class="min-h-screen bg-lf-page p-4 text-lf-primary" data-testid="button-lab">
    <h1 class="mb-2 text-lg font-semibold">Button Lab</h1>
    <p class="mb-3 text-sm text-lf-secondary">Tap = action. Long press (½ s) = the name, no action. Mouse rest = the name. Tab = the name.</p>

    <section class="sticky top-0 z-10 mb-4 rounded-lg border border-lf-subtle bg-lf-card p-2 text-xs" aria-live="polite">
        <div class="mb-1 flex items-center justify-between">
            <strong>Log</strong>
            <Button label="Clear the log" size="sm" variant="link" onclick={() => (log = [])} data-testid="lab-log-clear" />
        </div>
        <ol data-testid="lab-log">
            {#each log as entry (entry.id)}
                <li data-testid="lab-log-entry" data-event={entry.event}><span class="text-lf-muted">{entry.at}</span> {entry.event}</li>
            {:else}
                <li class="text-lf-muted">nothing yet</li>
            {/each}
        </ol>
    </section>

    <section class="mb-6">
        <h2 class="mb-2 font-medium">Icons only: the name by long press</h2>
        <div class="flex flex-wrap gap-2">
            <Button label="Edit" icon={Pencil} display="icon" onclick={() => note('action: edit')} data-testid="lab-icon-edit" />
            <Button label="Sync prices" icon={RefreshCw} display="icon" onclick={() => note('action: sync')} data-testid="lab-icon-sync" />
            <Button label="Delete" icon={Trash2} display="icon" variant="danger" onclick={() => note('action: delete')} data-testid="lab-icon-delete" />
            <CloseButton onclick={() => note('action: close')} data-testid="lab-close" />
        </div>
    </section>

    <section class="mb-6">
        <h2 class="mb-2 font-medium">Words that hide (the toolbar's showActionLabels, under {AUTO_LABEL_HIDE_PX}px)</h2>
        <label class="mb-2 flex items-center gap-2 text-sm">
            width <input type="range" min="240" max="900" bind:value={width} data-testid="lab-width" />
            {width}px
        </label>
        <div bind:this={autoBox} class="rounded-lg border border-lf-subtle p-2" style="width: {width}px; max-width: 100%" data-testid="lab-auto-box" data-labels={autoLayout.showActionLabels ? 'shown' : 'hidden'}>
            <div class="flex gap-2">
                <Button label="Add goal" icon={Plus} display="auto" compact={!autoLayout.showActionLabels} variant="primary" onclick={() => note('action: add goal')} data-testid="lab-auto-add" />
                <Button label="Suggest" icon={Sparkles} display="auto" compact={!autoLayout.showActionLabels} onclick={() => note('action: suggest')} data-testid="lab-auto-suggest" />
                <Button label="Reset all" icon={RefreshCw} display="auto" compact={!autoLayout.showActionLabels} variant="danger" onclick={() => note('action: reset')} data-testid="lab-auto-reset" />
            </div>
        </div>
        <p class="mt-3 mb-2 text-sm text-lf-muted">The other rule of today, a word hidden on a narrow screen (<code>hidden sm:inline</code>), is the same class: <code>hideWordBelow="sm"</code>.</p>
        <Button label="Import" icon={Download} display="auto" hideWordBelow="sm" onclick={() => note('action: import')} data-testid="lab-auto-sm" />
    </section>

    <section class="mb-6">
        <h2 class="mb-2 font-medium">States</h2>
        <div class="flex flex-wrap gap-2">
            <Button label="Delete selected" icon={Trash2} variant="danger" reason="Select at least one row first." reasonCode="no_selection" onclick={() => note('ERROR: a disabled action ran')} data-testid="lab-reason" />
            <Button label="Disabled, no reason" disabled onclick={() => note('ERROR: a disabled action ran')} data-testid="lab-disabled" />
            <Button label="Save" icon={Download} variant="primary" {busy} busyLabel="Saving…" onclick={startBusy} data-testid="lab-busy" />
            <Button label="Favourite" icon={Star} pressed={starred} onclick={() => ((starred = !starred), note(`action: favourite ${starred ? 'on' : 'off'}`))} data-testid="lab-toggle" />
            <Button label="Compare" help="Shows the two providers' prices side by side." onclick={() => note('action: compare')} data-testid="lab-help" />
            <Button label="A link" href="#lab-anchor" variant="link" data-testid="lab-link" />
        </div>
    </section>

    <section class="mb-6">
        <h2 class="mb-2 font-medium">Inside a table row (long press on the row selects it; on the button, only the name)</h2>
        <DataTable
            data={rows}
            {columns}
            getRowId={(row) => row.id}
            storageKey="button-lab"
            enableSelection
            enableTouchSelection
            enableContextMenu
            enableActions
            {rowActions}
            onSelectionChange={(ids) => {
                selection = ids;
                note(`selection: ${ids.join(', ') || 'none'}`);
            }}
        />
        <p class="mt-1 text-xs text-lf-muted" data-testid="lab-selection">selected: {selection.join(', ') || 'none'}</p>
    </section>

    <p id="lab-anchor" class="text-xs text-lf-muted">The end.</p>
</main>
