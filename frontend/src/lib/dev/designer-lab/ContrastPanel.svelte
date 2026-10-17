<script lang="ts">
    import {contrastRatio} from './color.js';
    import {contrastRows, resolveColor, wcagLevel} from './contrast';
    import {labT} from './i18n';
    import type {ColorCatalog, LabState} from './types';

    interface Props {
        catalog: ColorCatalog;
        lab: LabState;
        dark: boolean;
        revision: number;
    }

    let {catalog, lab, dark, revision}: Props = $props();

    function computed(name: string): string {
        void revision;
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    const rows = $derived(contrastRows(catalog, lab.changes, computed));
    const pairs = $derived.by(() => {
        const byPair = new Map<string, typeof rows>();
        for (const r of rows) {
            const key = `${r.fg}|${r.bg}`;
            byPair.set(key, [...(byPair.get(key) ?? []), r]);
        }
        return [...byPair.values()];
    });

    let fg = $state('var(--theme-text-muted)');
    let bg = $state('var(--theme-bg-card)');
    const custom = $derived.by(() => {
        const lookup = (name: string) => computed(name);
        const f = resolveColor(fg, dark, lookup);
        const b = resolveColor(bg, dark, lookup);
        return f && b ? Math.round(contrastRatio(f, b) * 100) / 100 : null;
    });
</script>

<section class="contrast" data-testid="lab-contrast">
    <h2>{$labT('contrast.title')}</h2>
    <div class="custom">
        <h3>{$labT('contrast.custom')}</h3>
        <label>{$labT('contrast.fg')} <input type="text" bind:value={fg} data-testid="lab-contrast-fg" /></label>
        <label>{$labT('contrast.bg')} <input type="text" bind:value={bg} data-testid="lab-contrast-bg" /></label>
        <span class="sample" style:color={fg} style:background={bg}>Aa 1 234,56 €</span>
        <strong data-testid="lab-contrast-custom">{custom ?? '—'}</strong>
        <span class="level" data-level={wcagLevel(custom, 'text')}>{wcagLevel(custom, 'text')}</span>
    </div>

    <h3>{$labT('contrast.declared')}</h3>
    <table>
        <thead>
            <tr>
                <th>{$labT('contrast.fg')}</th>
                <th>{$labT('contrast.bg')}</th>
                <th>{$labT('scope.light')} · {$labT('contrast.before')}</th>
                <th>{$labT('contrast.after')}</th>
                <th>{$labT('scope.dark')} · {$labT('contrast.before')}</th>
                <th>{$labT('contrast.after')}</th>
            </tr>
        </thead>
        <tbody>
            {#each pairs as pair (pair[0].fg + pair[0].bg)}
                <tr data-testid="lab-contrast-row">
                    <td><code>{pair[0].fg}</code></td>
                    <td><code>{pair[0].bg}</code></td>
                    {#each pair as r (r.scope)}
                        <td>{r.before ?? '—'} <span class="level" data-level={wcagLevel(r.before, r.kind)}>{wcagLevel(r.before, r.kind)}</span></td>
                        <td class:changed={r.after !== r.before}>{r.after ?? '—'} <span class="level" data-level={wcagLevel(r.after, r.kind)}>{wcagLevel(r.after, r.kind)}</span></td>
                    {/each}
                </tr>
            {/each}
        </tbody>
    </table>
</section>

<style>
    .contrast {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    h2 {
        font-size: 1.05rem;
        margin: 0;
    }
    h3 {
        font-size: 0.9rem;
        margin: 0;
    }
    .custom {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: center;
        padding: 0.75rem;
        border: 1px solid var(--lab-border);
        border-radius: 8px;
        background: var(--lab-panel);
    }
    .custom label {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        font-size: 0.85rem;
    }
    input {
        background: var(--lab-sunken);
        color: var(--lab-fg);
        border: 1px solid var(--lab-border);
        border-radius: 6px;
        padding: 0.3rem 0.5rem;
        font: inherit;
        width: 14rem;
    }
    .sample {
        padding: 0.3rem 0.7rem;
        border-radius: 6px;
        border: 1px solid var(--lab-border);
        font-weight: 600;
    }
    table {
        border-collapse: collapse;
        font-size: 0.8rem;
        width: 100%;
    }
    th,
    td {
        border-bottom: 1px solid var(--lab-border);
        padding: 0.3rem 0.5rem;
        text-align: left;
        color: var(--lab-fg);
        background: var(--lab-panel);
    }
    th {
        color: var(--lab-muted);
        font-weight: 600;
    }
    td.changed {
        font-weight: 700;
    }
    .level {
        font-size: 0.7rem;
        padding: 0 0.3rem;
        border-radius: 4px;
        border: 1px solid var(--lab-border);
    }
    .level[data-level='fail'] {
        color: var(--lab-danger);
    }
    .level[data-level='AA'],
    .level[data-level='AAA'] {
        color: var(--lab-ok);
    }
    code {
        font-family: var(--font-mono);
    }
</style>
