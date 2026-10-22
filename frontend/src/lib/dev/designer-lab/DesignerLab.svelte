<script lang="ts">
    import {onMount} from 'svelte';
    import catalog from 'virtual:lf-color-catalog';
    import {APP_VERSION} from '$lib/version';
    import {writeTextToClipboard} from '$lib/utils/clipboard';
    import ColorEditor from './ColorEditor.svelte';
    import ContrastPanel from './ContrastPanel.svelte';
    import PickedElementPanel from './PickedElement.svelte';
    import {appVars, categoryRows, editTarget, matchesSearch, paletteFamilies, valueGroups, type ValueGroup} from './catalogView';
    import {applyNow} from './client';
    import {contrastRows} from './contrast';
    import {buildExport, downloadText, parseImport, renderMarkdown, renderSummary, type LabExport} from './export';
    import {labLang, labT} from './i18n';
    import {labStyle} from './labTheme';
    import {markSeen, newPickId, PICK_KEY, readPick, writePick} from './pick';
    import {pickView} from './pickView';
    import {emptyState, readState, removeChange, STORAGE_KEY, upsertChange, writeState} from './store';
    import type {ChangeLayer, CvdMode, LabChange, LabSelection, LabState, Layer, PickedElement, Scope} from './types';

    type Tab = 'overview' | 'element' | 'palette' | 'vars' | 'sheets' | 'charts' | 'categories' | 'proposals' | 'changes' | 'contrast' | 'notes';
    type ValueTab = 'sheets' | 'charts' | 'proposals';
    const TABS: Tab[] = ['overview', 'element', 'palette', 'vars', 'sheets', 'charts', 'categories', 'proposals', 'changes', 'contrast', 'notes'];
    const SEARCHABLE: Tab[] = ['palette', 'vars', 'sheets', 'charts', 'categories', 'proposals'];
    /** The groups of the Categories tab, in the order of the tables of `chartCategories.ts`. */
    const CATEGORY_GROUPS = ['type', 'sector', 'bucket'] as const;
    const SCOPES: Scope[] = ['light', 'dark', 'both'];
    const CVD: CvdMode[] = ['none', 'protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia'];
    const LAYERS: Layer[] = ['css-literal', 'chart-color', 'script', 'markup', 'static'];
    const VALUE_LAYER: Record<ValueTab, ChangeLayer> = {sheets: 'css-literal', charts: 'chart-color', proposals: 'proposal'};

    let tab = $state<Tab>('overview');
    let lab = $state<LabState>(readState() ?? emptyState());
    let dark = $state(document.documentElement.classList.contains('dark'));
    let scope = $state<Scope>(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    let query = $state('');
    let selection = $state<LabSelection | null>(null);
    let status = $state<{kind: 'ok' | 'warn' | 'error'; text: string} | null>(null);
    let stale = $state(false);
    let revision = $state(0);
    let variantName = $state('');
    let importInput = $state<HTMLInputElement>();
    /** The pick request this Lab is waiting for; null when not picking. */
    let picking = $state<string | null>(null);
    let picked = $state<PickedElement | null>(null);
    let onlyPicked = $state(false);
    const view = $derived(picked ? pickView(catalog, picked) : null);
    /** The lists keep only the picked element's colours when the filter is on. */
    const pickFilter = $derived(onlyPicked && view ? view.filter : null);

    const families = paletteFamilies(catalog);
    const vars = appVars(catalog);
    const categories = categoryRows(catalog);
    const withSearch = (list: ValueGroup[]) => list.map((g) => ({...g, search: [g.key, ...g.literals.map((l) => `${catalog.files[l.file]} ${l.selector ?? ''} ${l.raw}`)].join(' ')}));
    const groups: Record<ValueTab, (ValueGroup & {search: string})[]> = {
        sheets: withSearch(valueGroups(catalog, ['css-literal'])),
        charts: withSearch(valueGroups(catalog, ['chart-color'])),
        proposals: withSearch(valueGroups(catalog, ['script', 'markup', 'static'])),
    };
    const live = (catalog.meta.layers['css-literal'] ?? 0) + (catalog.meta.layers['chart-color'] ?? 0);
    const total = Object.values(catalog.meta.layers).reduce((a, b) => a + b, 0);

    const changed = $derived(new Set(lab.changes.map((c) => `${c.layer}:${c.target}`)));
    const variantNames = $derived(Object.keys(lab.variants).sort());

    function cssVarValue(name: string): string {
        void revision;
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    function commit(next: LabState): void {
        try {
            lab = writeState(next);
        } catch {
            // Storage refused the write (full, or disabled): the other tabs would never see this state, so keep the last saved one.
            status = {kind: 'error', text: $labT('storageFailed')};
            return;
        }
        void applyNow().then(() => revision++);
    }

    function select(layer: ChangeLayer, target: string): void {
        selection = {layer, target};
    }

    /** Open the editor on a change: its own selection, so a specialisation keeps its property and anchor. */
    function selectChange(c: LabChange): void {
        selection = {layer: c.layer, target: c.target, ...(c.occurrence !== undefined ? {occurrence: c.occurrence} : {}), ...(c.property ? {property: c.property, from: c.from} : {}), ...(c.colorKey ? {colorKey: c.colorKey} : {}), ...(c.anchor ? {anchor: c.anchor} : {})};
    }

    function startPick(): void {
        const id = newPickId();
        writePick({op: 'start', id, at: Date.now()});
        picking = id;
        status = {kind: 'ok', text: $labT('pickWaiting')};
    }

    function cancelPick(): void {
        if (picking) writePick({op: 'cancel', id: picking, at: Date.now()});
        picking = null;
        status = null;
    }

    /** A pick message from an app tab: a result (from this Lab's request or the Alt+Shift+D shortcut), or a cancel. */
    function onPickMessage(): void {
        const message = readPick();
        if (message?.op === 'result') {
            picked = message.element;
            picking = null;
            tab = 'element';
            status = null;
            // An editor left on the previous pick's specialisation would edit the wrong element.
            if (selection?.layer === 'element') selection = null;
            // Edit the theme the element was picked in (a dark override shows only there), unless both are edited.
            if (scope !== 'both') scope = message.element.theme;
        } else if (message?.op === 'cancel' && picking && message.id === picking) {
            picking = null;
            status = {kind: 'warn', text: $labT('pickCancelled')};
        }
    }

    function onApply(change: LabChange): void {
        commit(upsertChange(lab, change));
    }

    function onRemove(id: string): void {
        commit(removeChange(lab, id));
    }

    function makeExport(): LabExport {
        const contrast = contrastRows(catalog, lab.changes, cssVarValue)
            .filter((r) => r.before !== r.after)
            .map((r) => ({fg: r.fg, bg: r.bg, scope: r.scope, before: r.before ?? 0, after: r.after ?? 0}));
        return buildExport(lab, catalog, APP_VERSION, contrast);
    }

    function exportFiles(which: 'json' | 'md' | 'both'): void {
        const doc = makeExport();
        if (which !== 'md') downloadText('designer-lab-changes.json', JSON.stringify(doc, null, 2) + '\n', 'application/json');
        if (which !== 'json') downloadText('designer-lab-changes.md', renderMarkdown(doc, $labLang), 'text/markdown');
        status = {kind: 'ok', text: $labT('exported')};
    }

    async function copySummary(): Promise<void> {
        await writeTextToClipboard(renderSummary(makeExport()));
        status = {kind: 'ok', text: $labT('copied')};
    }

    async function importFile(file: File | undefined): Promise<void> {
        if (!file) return;
        const result = parseImport(await file.text(), lab, catalog);
        if (importInput) importInput.value = '';
        if (!result.state) {
            status = {kind: 'error', text: [$labT('importFailed'), ...result.errors].join(' · ')};
            return;
        }
        commit(result.state);
        status = {kind: result.errors.length || result.warnings.length ? 'warn' : 'ok', text: [$labT('imported'), ...result.errors, ...result.warnings].join(' · ')};
    }

    function saveVariant(): void {
        const name = variantName.trim();
        if (!name) return;
        commit({...lab, variants: {...lab.variants, [name]: lab.changes}, activeVariant: name});
        variantName = '';
    }

    function useVariant(name: string): void {
        // The changes on screen are kept in the variant they came from before switching away.
        const variants = lab.activeVariant ? {...lab.variants, [lab.activeVariant]: lab.changes} : lab.changes.length ? {...lab.variants, current: lab.changes} : lab.variants;
        if (!name) {
            commit({...lab, variants, activeVariant: null});
            return;
        }
        commit({...lab, variants, changes: variants[name] ?? [], activeVariant: name});
    }

    function resetAll(): void {
        if (confirm($labT('resetAllConfirm'))) commit({...lab, changes: []});
    }

    onMount(() => {
        // Only a browser where the Lab has been opened gets the Alt+Shift+D shortcut in its app tabs.
        markSeen();
        const last = readPick();
        if (last?.op === 'result') picked = last.element;
        const observer = new MutationObserver(() => {
            const d = document.documentElement.classList.contains('dark');
            if (d !== dark) {
                dark = d;
                revision++;
            }
        });
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        const onStorage = (e: StorageEvent) => {
            if (e.key === PICK_KEY || e.key === null) onPickMessage();
            if (e.key !== STORAGE_KEY && e.key !== null) return;
            lab = readState() ?? emptyState();
            revision++;
        };
        window.addEventListener('storage', onStorage);
        // Closing the Lab's tab while it waits: the app tabs leave picking mode, and no new tab joins a stale request.
        const onPageHide = () => {
            if (picking) writePick({op: 'cancel', id: picking, at: Date.now()});
        };
        window.addEventListener('pagehide', onPageHide);
        if (import.meta.hot) import.meta.hot.on('lf-designer-lab:catalog-stale', () => (stale = true));
        return () => {
            observer.disconnect();
            window.removeEventListener('storage', onStorage);
            window.removeEventListener('pagehide', onPageHide);
            // Leaving the Lab while it waits: the app tabs leave picking mode too.
            if (picking) writePick({op: 'cancel', id: picking, at: Date.now()});
        };
    });
</script>

<div class="lab" style={labStyle(dark)} data-testid="designer-lab" data-catalog-hash={catalog.meta.hash} data-changes={lab.changes.length}>
    <header class="top">
        <div class="brand">
            <h1>{$labT('title')}</h1>
            <span class="muted">{$labT('subtitle')}</span>
            <span class="muted" data-testid="lab-version"><code>{APP_VERSION}</code> · {$labT('catalog')} <code>{catalog.meta.hash.slice(7, 19)}</code></span>
        </div>
        <div class="controls">
            {#if picking}
                <button type="button" class="on" onclick={cancelPick} data-testid="lab-pick-cancel">{$labT('pickCancel')}</button>
            {:else}
                <button type="button" class="primary" onclick={startPick} data-testid="lab-pick">{$labT('pick')}</button>
            {/if}
            <span class="muted">{$labT('pickHint')}</span>
            <label class="inline">
                {$labT('editing')}
                <select bind:value={scope} data-testid="lab-scope">
                    {#each SCOPES as s (s)}<option value={s}>{$labT(`scope.${s}`)}</option>{/each}
                </select>
            </label>
            <button type="button" class:on={lab.suspended} onclick={() => commit({...lab, suspended: !lab.suspended})} data-testid="lab-suspend" aria-pressed={lab.suspended}>{lab.suspended ? $labT('resume') : $labT('suspend')}</button>
            <span class="count" data-testid="lab-change-count">{$labT('tab.changes')}: {lab.changes.length}</span>
            <label class="inline">
                {$labT('variant')}
                <select value={lab.activeVariant ?? ''} onchange={(e) => useVariant(e.currentTarget.value)} data-testid="lab-variant-select">
                    <option value="">{$labT('variantNone')}</option>
                    {#each variantNames as v (v)}<option value={v}>{v}</option>{/each}
                </select>
            </label>
            <input type="text" class="short" placeholder={$labT('variantName')} bind:value={variantName} data-testid="lab-variant-name" />
            <button type="button" onclick={saveVariant} disabled={!variantName.trim()} data-testid="lab-variant-save">{$labT('variantSave')}</button>
            <label class="inline">
                {$labT('cvd')}
                <select value={lab.cvd} onchange={(e) => commit({...lab, cvd: e.currentTarget.value as CvdMode})} data-testid="lab-cvd">
                    {#each CVD as m (m)}<option value={m}>{$labT(`cvd.${m}`)}</option>{/each}
                </select>
            </label>
            <button type="button" class="primary" onclick={() => exportFiles('both')} data-testid="lab-export">{$labT('exportBoth')}</button>
            <button type="button" onclick={() => exportFiles('json')} data-testid="lab-export-json">JSON</button>
            <button type="button" onclick={() => exportFiles('md')} data-testid="lab-export-md">MD</button>
            <button type="button" onclick={copySummary} data-testid="lab-copy-summary">{$labT('copySummary')}</button>
            <button type="button" onclick={() => importInput?.click()} data-testid="lab-import">{$labT('import')}</button>
            <input bind:this={importInput} type="file" accept="application/json,.json" hidden onchange={(e) => importFile(e.currentTarget.files?.[0])} data-testid="lab-import-input" />
            <button type="button" class="danger" onclick={resetAll} disabled={!lab.changes.length} data-testid="lab-reset-all">{$labT('resetAll')}</button>
        </div>
        {#if status}<p class="status" data-kind={status.kind} data-testid="lab-status">{status.text}</p>{/if}
        {#if stale}<p class="status" data-kind="warn" data-testid="lab-stale">{$labT('staleCatalog')}</p>{/if}
    </header>

    <nav class="tabs" aria-label={$labT('title')}>
        {#each TABS as t (t)}
            <button type="button" class:active={tab === t} onclick={() => (tab = t)} data-testid="lab-tab-{t}" aria-current={tab === t}>
                {$labT(`tab.${t}`)}{#if t === 'changes'}&nbsp;({lab.changes.length}){/if}
            </button>
        {/each}
    </nav>

    <div class="body" class:with-editor={!!selection}>
        <main>
            {#if SEARCHABLE.includes(tab)}
                <div class="filters">
                    <input type="search" class="search" placeholder={$labT('search')} bind:value={query} data-testid="lab-search" />
                    {#if view && tab !== 'categories'}<label class="inline"><input type="checkbox" bind:checked={onlyPicked} data-testid="lab-filter-picked" /> {$labT('element.filter')}</label>{/if}
                </div>
            {/if}

            {#if tab === 'element'}
                {#if view}
                    <PickedElementPanel {catalog} {view} onEdit={(s) => (selection = s)} />
                {:else}
                    <p class="hint" data-testid="lab-picked-none">{$labT('element.none')}</p>
                {/if}
            {:else if tab === 'overview'}
                <section data-testid="lab-overview">
                    <p class="hint">{$labT('overview.hint')}</p>
                    <h2>{$labT('overview.layers')}</h2>
                    <ul class="stats">
                        {#each LAYERS as layer (layer)}
                            <li data-testid="lab-overview-layer-{layer}"><strong>{catalog.meta.layers[layer] ?? 0}</strong> {$labT(`layer.${layer}`)}</li>
                        {/each}
                        <li><strong>{live} / {total}</strong> {$labT('overview.live')}</li>
                        <li><strong>{catalog.palette.length}</strong> {$labT('overview.palette')}</li>
                        <li><strong>{vars.length}</strong> {$labT('overview.vars')}</li>
                    </ul>
                    <p class="muted">
                        <code>{catalog.meta.schema}</code> · {catalog.meta.parity.files}
                        {$labT('files')} · {catalog.meta.scan_ms} ms · {catalog.meta.generated_at}
                    </p>
                </section>
            {:else if tab === 'palette'}
                <section class="families">
                    {#each families as f (f.family)}
                        {@const entries = f.entries.filter((e) => (!pickFilter || pickFilter.vars.has(e.var)) && matchesSearch(query, [e.var, e.role ?? '', ...Object.keys(e.classes)]))}
                        {#if entries.length}
                            <div class="family">
                                <h3>{f.family}</h3>
                                <div class="chips">
                                    {#each entries as e (e.var)}
                                        {@const target = editTarget(e)}
                                        <button type="button" class="chip" class:modified={changed.has(`css-var:${target}`)} onclick={() => select('css-var', target)} data-testid="lab-item-var-{e.var}" data-target={target} title={e.role ? `${e.var} → ${e.role}` : e.var}>
                                            <span class="swatch" style:background={`var(${target})`}></span>
                                            <span>{e.shade}</span>
                                            <span class="muted">{e.uses}</span>
                                        </button>
                                    {/each}
                                </div>
                            </div>
                        {/if}
                    {/each}
                </section>
            {:else if tab === 'vars'}
                <section class="list">
                    {#each vars.filter((v) => (!pickFilter || pickFilter.vars.has(v.name)) && matchesSearch(query, [v.name, ...v.defs.map((d) => `${catalog.files[d.file]} ${d.value}`)])) as v (v.name)}
                        {@const scoped = v.defs.every((d) => d.scope === 'scoped')}
                        <button type="button" class="row" class:modified={changed.has(`css-var:${v.name}`)} onclick={() => select('css-var', v.name)} data-testid="lab-item-var-{v.name}">
                            <span class="swatch" style:background={scoped ? v.defs[0].value : `var(${v.name})`}></span>
                            <code>{v.name}</code>
                            <span class="muted">{v.defs.map((d) => `${d.theme ?? ''}: ${d.value}`).join(' · ')}</span>
                            <span class="muted">{v.uses} {$labT('uses')}</span>
                        </button>
                    {/each}
                </section>
            {:else if tab === 'sheets' || tab === 'charts' || tab === 'proposals'}
                {@const valueTab = tab}
                <section class="list">
                    {#each groups[valueTab].filter((g) => (!pickFilter || pickFilter.keys.has(g.key)) && matchesSearch(query, [g.search])) as g (g.key)}
                        <button type="button" class="row" class:modified={changed.has(`${VALUE_LAYER[valueTab]}:${g.key}`)} onclick={() => select(VALUE_LAYER[valueTab], g.key)} data-testid="lab-item-value-{VALUE_LAYER[valueTab]}-{g.key}">
                            <span class="swatch" style:background={g.key}></span>
                            <code>{g.key}</code>
                            <span class="muted">{g.literals.length} {$labT('occurrences')} · {g.files} {$labT('files')}</span>
                            {#if g.alphas.length > 1 || g.alphas[0] !== 1}<span class="muted">α {g.alphas.join(' ')}</span>{/if}
                            <span class="muted">{g.themes.join(' ')}</span>
                        </button>
                    {/each}
                </section>
            {:else if tab === 'categories'}
                <section class="list" data-testid="lab-categories">
                    {#if !categories.length}<p class="muted">{$labT('categories.none')}</p>{/if}
                    {#each CATEGORY_GROUPS as group (group)}
                        {@const rows = categories.filter((r) => r.kind === group && matchesSearch(query, [r.target, r.key, r.lightValue ?? '', r.darkValue ?? '']))}
                        {#if rows.length}
                            <h3>{$labT(`categories.${group}`)}</h3>
                            {#each rows as r (r.target)}
                                <button type="button" class="row" class:modified={changed.has(r.role ? `css-var:${r.role}` : `category:${r.target}`)} onclick={() => (r.role ? select('css-var', r.role) : select('category', r.target))} data-testid="lab-item-category-{r.target}" data-role={r.role}>
                                    <span class="swatch" style:background={r.lightValue ?? 'transparent'} title={$labT('scope.light')}></span>
                                    <span class="swatch" style:background={r.darkValue ?? 'transparent'} title={$labT('scope.dark')}></span>
                                    <code>{r.key}</code>
                                    {#if r.role}<code class="muted">{r.role}</code>{/if}
                                    <span class="muted">{r.lightValue ?? '—'} · {r.darkValue ?? '—'}</span>
                                </button>
                            {/each}
                        {/if}
                    {/each}
                </section>
            {:else if tab === 'changes'}
                <section class="list" data-testid="lab-changes">
                    {#if !lab.changes.length}<p class="muted">{$labT('changes.empty')}</p>{/if}
                    {#each lab.changes as c (c.id)}
                        <div class="row change" data-testid="lab-change" data-change-id={c.id}>
                            <span class="swatch" style:background={c.from || 'transparent'}></span>
                            <span>→</span>
                            <span class="swatch" style:background={c.to}></span>
                            <button type="button" class="link" onclick={() => selectChange(c)}
                                ><code>{c.target}</code>{#if c.property}&nbsp;<code>{c.property}{c.colorKey ? ` ${c.colorKey}` : ''}</code>{/if}</button
                            >
                            <span class="badge">{$labT(`layer.${c.layer}`)}</span>
                            <span class="badge">{$labT(`scope.${c.scope}`)}</span>
                            <code class="muted">{c.to}</code>
                            {#if c.note}<span class="muted">{c.note}</span>{/if}
                            <button type="button" class="danger" onclick={() => onRemove(c.id)} data-testid="lab-change-remove" aria-label={$labT('editor.remove')}>✕</button>
                        </div>
                    {/each}
                </section>
            {:else if tab === 'contrast'}
                <ContrastPanel {catalog} {lab} {dark} {revision} />
            {:else if tab === 'notes'}
                <section class="notes">
                    <label class="field">
                        {$labT('notes.author')}
                        <input type="text" value={lab.author} onchange={(e) => commit({...lab, author: e.currentTarget.value})} data-testid="lab-author" />
                    </label>
                    <label class="field">
                        {$labT('notes.general')}
                        <textarea rows="12" value={lab.notes} onchange={(e) => commit({...lab, notes: e.currentTarget.value})} data-testid="lab-notes"></textarea>
                    </label>
                </section>
            {/if}
        </main>

        {#if selection}
            <aside>
                {#key `${selection.layer}:${selection.target}:${selection.property ?? ''}:${selection.colorKey ?? ''}:${selection.occurrence ?? ''}`}
                    <ColorEditor {catalog} {lab} {selection} {scope} {dark} {revision} {onApply} {onRemove} onClose={() => (selection = null)} />
                {/key}
            </aside>
        {/if}
    </div>
</div>

<style>
    .lab {
        min-height: 100vh;
        background: var(--lab-bg);
        color: var(--lab-fg);
        font-size: 0.9rem;
        display: flex;
        flex-direction: column;
    }
    .top {
        position: sticky;
        top: 0;
        z-index: 2;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        background: var(--lab-panel);
        border-bottom: 1px solid var(--lab-border);
    }
    .brand {
        display: flex;
        gap: 1rem;
        align-items: baseline;
        flex-wrap: wrap;
    }
    h1 {
        font-size: 1.2rem;
        font-weight: 700;
        margin: 0;
    }
    h2 {
        font-size: 1rem;
        margin: 1rem 0 0.5rem;
    }
    h3 {
        font-size: 0.85rem;
        margin: 0 0 0.3rem;
        text-transform: capitalize;
    }
    .controls {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .inline {
        display: flex;
        gap: 0.35rem;
        align-items: center;
    }
    .count {
        font-weight: 600;
    }
    .status {
        margin: 0;
        font-size: 0.82rem;
    }
    .status[data-kind='ok'] {
        color: var(--lab-ok);
    }
    .status[data-kind='warn'] {
        color: var(--lab-warn);
    }
    .status[data-kind='error'] {
        color: var(--lab-danger);
    }
    .tabs {
        display: flex;
        gap: 0.25rem;
        padding: 0.5rem 1rem 0;
        flex-wrap: wrap;
        border-bottom: 1px solid var(--lab-border);
        background: var(--lab-bg);
    }
    .tabs button {
        border: 1px solid transparent;
        border-bottom: none;
        border-radius: 8px 8px 0 0;
        background: transparent;
        color: var(--lab-muted);
        padding: 0.4rem 0.8rem;
    }
    .tabs button.active {
        background: var(--lab-panel);
        color: var(--lab-fg);
        border-color: var(--lab-border);
        font-weight: 600;
    }
    .body {
        display: grid;
        grid-template-columns: minmax(0, 1fr);
        gap: 1rem;
        padding: 1rem;
        align-items: start;
    }
    .body.with-editor {
        grid-template-columns: minmax(0, 1fr) minmax(22rem, 34rem);
    }
    aside {
        position: sticky;
        top: 8.5rem;
        max-height: calc(100vh - 9.5rem);
        overflow: auto;
    }
    .search {
        width: 100%;
        max-width: 28rem;
    }
    .filters {
        display: flex;
        gap: 1rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.75rem;
    }
    .hint {
        max-width: 60rem;
        color: var(--lab-muted);
    }
    .stats {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
        gap: 0.5rem;
    }
    .stats li {
        padding: 0.6rem 0.8rem;
        border: 1px solid var(--lab-border);
        border-radius: 8px;
        background: var(--lab-panel);
    }
    .families {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
    }
    .chip {
        display: inline-flex;
        gap: 0.35rem;
        align-items: center;
        padding: 0.25rem 0.5rem;
    }
    .list {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    .row {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        text-align: left;
        padding: 0.35rem 0.6rem;
        flex-wrap: wrap;
    }
    .modified {
        border-color: var(--lab-accent);
        box-shadow: inset 3px 0 0 var(--lab-accent);
    }
    .swatch {
        display: inline-block;
        width: 1.1rem;
        height: 1.1rem;
        border-radius: 4px;
        border: 1px solid var(--lab-border);
        flex: none;
    }
    .badge {
        font-size: 0.72rem;
        padding: 0.05rem 0.4rem;
        border-radius: 999px;
        border: 1px solid var(--lab-border);
        color: var(--lab-muted);
    }
    .muted {
        color: var(--lab-muted);
        font-size: 0.8rem;
    }
    .notes {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        max-width: 50rem;
    }
    .field {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }
    button,
    input,
    select,
    textarea {
        font: inherit;
        color: var(--lab-fg);
        background: var(--lab-sunken);
        border: 1px solid var(--lab-border);
        border-radius: 6px;
        padding: 0.3rem 0.6rem;
    }
    button {
        cursor: pointer;
    }
    button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    button.primary {
        background: var(--lab-accent);
        color: var(--lab-accent-fg);
        border-color: var(--lab-accent);
    }
    button.danger {
        color: var(--lab-danger);
    }
    button.on {
        border-color: var(--lab-warn);
        color: var(--lab-warn);
    }
    button.link {
        background: none;
        border: none;
        padding: 0;
        color: var(--lab-fg);
        text-decoration: underline;
    }
    input.short {
        width: 9rem;
    }
    button:focus-visible,
    input:focus-visible,
    select:focus-visible,
    textarea:focus-visible {
        outline: 2px solid var(--lab-focus);
        outline-offset: 1px;
    }
    code {
        font-family: var(--font-mono);
        font-size: 0.8rem;
    }
</style>
