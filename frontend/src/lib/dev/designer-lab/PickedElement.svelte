<script lang="ts">
    import {labT} from './i18n';
    import type {PickView, PropertyView} from './pickView';
    import type {ColorCatalog, LabSelection} from './types';

    interface Props {
        catalog: ColorCatalog;
        view: PickView;
        onEdit: (selection: LabSelection) => void;
    }

    let {catalog, view, onEdit}: Props = $props();

    const el = $derived(view.element);

    const matchesText = (n: number) => (n === 1 ? $labT('element.matchesOne') : $labT('element.matches', {n}));

    /** A variable of the chain, edited with the property's anchor as context. */
    const editVar = (p: PropertyView, name: string): LabSelection => ({layer: 'css-var', target: name, ...(p.edit?.anchor ? {anchor: p.edit.anchor} : {})});
</script>

<section class="picked" data-testid="lab-picked" data-route={el.route} data-theme={el.theme}>
    <p class="meta">
        <code data-testid="lab-picked-route">{el.route}</code> · {$labT(`scope.${el.theme}`)} · <code>&lt;{el.element.tag}&gt;</code>
        {#each el.element.classes.slice(0, 12) as c (c)}<code class="cls">.{c}</code>{/each}
    </p>
    <dl>
        <dt>{$labT('element.testids')}</dt>
        <dd data-testid="lab-picked-testids">
            {#each el.testids as id, i (i)}{#if i}<span class="muted"> ‹ </span>{/if}<code>{id}</code>{:else}<span class="muted">—</span>{/each}
        </dd>
        <dt>{$labT('element.selector')}</dt>
        <dd>
            <code data-testid="lab-picked-selector">{el.selector}</code>
            <span class="badge">{$labT(`element.breadth.${el.breadth}`)}</span>
            <span class="muted" data-testid="lab-picked-matches" data-matches={el.matches}>{matchesText(el.matches)}</span>
        </dd>
        <dt>{$labT('element.path')}</dt>
        <dd><code>{el.css_path}</code></dd>
    </dl>

    <ul class="props">
        {#each view.properties as p (p.property)}
            <li data-testid="lab-picked-property" data-property={p.property} data-kind={p.kind}>
                <div class="head">
                    <span class="swatch" style:background={p.computed}></span>
                    <strong>{p.property}</strong>
                    <code>{p.computed}</code>
                    <span class="badge kind">{$labT(`source.${p.kind}`)}</span>
                    {#if p.darkOverride}<span class="badge warn" data-testid="lab-picked-dark-override">{$labT('element.darkOverride')}</span>{/if}
                    {#if p.overriddenClass}<span class="muted">{$labT('element.overrides', {cls: p.overriddenClass})}</span>{/if}
                    {#if p.labOverride}<span class="badge accent">{$labT('element.labOverride')}</span>{/if}
                    {#if p.depth > 0 && !p.property.startsWith('background')}<span class="muted">{$labT('element.inherited', {tag: p.ancestorTag ?? '?', id: p.ancestorTestid ?? '—'})}</span>{/if}
                    {#if p.depth > 0 && p.property.startsWith('background')}<span class="muted">{$labT('element.behind', {tag: p.ancestorTag ?? '?', id: p.ancestorTestid ?? '—'})}</span>{/if}
                    {#if p.followsColor}<span class="muted">{$labT('element.followsColor')}</span>{/if}
                </div>
                <div class="source">
                    {#if p.className}<code data-testid="lab-picked-class">{p.className}</code>{/if}
                    {#if p.varChain.length}
                        {#each p.varChain as name, i (name)}{#if i}<span class="muted"> → </span>{/if}<button type="button" class="link" onclick={() => onEdit(editVar(p, name))} data-testid="lab-picked-var"><code>{name}</code></button>{/each}
                    {/if}
                    {#if p.winner && p.kind !== 'tailwind-class'}<code class="rule">{p.winner.selector ?? p.winner.origin} {'{'} {p.winner.declared_as}: {p.winner.value}{p.winner.important ? ' !important' : ''} {'}'}</code>{/if}
                    {#each p.literals.slice(0, 3) as l (l.id)}<code class="where">{catalog.files[l.file]}:{l.line}</code>{/each}
                </div>
                <div class="actions">
                    {#if p.edit}<button type="button" onclick={() => p.edit && onEdit(p.edit)} data-testid="lab-picked-edit">{$labT('element.editSource')}</button>{/if}
                    {#if p.specialise}
                        <button type="button" class="primary" onclick={() => p.specialise && onEdit(p.specialise)} data-testid="lab-picked-specialise">{$labT('element.specialise')}</button>
                        <code class="where" data-testid="lab-picked-specialise-selector">{p.specialise.target}</code>
                        <span class="muted" data-testid="lab-picked-specialise-matches" data-matches={p.specialise.anchor?.matches ?? 0}>{matchesText(p.specialise.anchor?.matches ?? 0)}</span>
                    {/if}
                </div>
                {#if p.candidates.length}
                    <details>
                        <summary>{$labT('element.candidates')} ({p.candidates.length})</summary>
                        <ul class="sub" data-testid="lab-picked-candidates">
                            {#each p.candidates as c (`${c.file}:${c.line}:${c.why}`)}<li><code>{c.file}:{c.line}</code> <span class="badge">{c.why}</span> <code class="muted">{c.needle}</code></li>{/each}
                        </ul>
                    </details>
                {/if}
                {#if p.winner || p.literals.length}
                    <details>
                        <summary>{$labT('element.declarations')}</summary>
                        <ul class="sub">
                            {#each view.element.properties.find((x) => x.property === p.property)?.declarations ?? [] as d, i (i)}
                                <li class:won={d.wins} class:muted={d.state}>
                                    <code>{d.selector ?? d.origin}</code>
                                    <code>{d.declared_as}: {d.value}{d.important ? ' !important' : ''}</code>
                                    {#if d.layer !== null}<span class="badge">@layer {d.layer || '—'}</span>{/if}
                                    {#each d.conditions as cond, ci (ci)}<span class="badge">{cond}</span>{/each}
                                    {#if d.sheet}<span class="muted">{d.sheet}</span>{/if}
                                </li>
                            {/each}
                        </ul>
                    </details>
                {/if}
            </li>
        {/each}
    </ul>

    {#if view.chart}
        <h3>{$labT('element.chart')} <code>{view.chart.hostTestid ?? view.chart.selector}</code> <span class="muted">{matchesText(view.chart.matches)}</span></h3>
        <ul class="props" data-testid="lab-picked-chart">
            {#each view.chart.colors as c (c.key)}
                <li class="chart-color" class:pointed={c.pointed} data-testid="lab-picked-chart-color" data-key={c.key}>
                    <span class="swatch" style:background={c.color}></span>
                    <code>{c.key}</code>
                    {#if c.pointed}<span class="badge accent">{$labT('element.pointed')}</span>{/if}
                    <span class="actions">
                        <button type="button" onclick={() => onEdit(c.edit)} data-testid="lab-picked-chart-edit">{$labT('element.editSource')}</button>
                        <button type="button" class="primary" onclick={() => onEdit(c.specialise)} data-testid="lab-picked-chart-specialise">{$labT('element.specialise')}</button>
                    </span>
                </li>
            {/each}
        </ul>
    {/if}
</section>

<style>
    .picked {
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
    }
    .meta {
        margin: 0;
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem;
        align-items: center;
    }
    .cls {
        color: var(--lab-muted);
    }
    dl {
        display: grid;
        grid-template-columns: max-content minmax(0, 1fr);
        gap: 0.3rem 0.8rem;
        margin: 0;
    }
    dt {
        color: var(--lab-muted);
        font-size: 0.8rem;
    }
    dd {
        margin: 0;
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        align-items: center;
        word-break: break-all;
    }
    h3 {
        font-size: 0.9rem;
        margin: 0.6rem 0 0;
    }
    .props {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .props > li {
        border: 1px solid var(--lab-border);
        border-radius: 8px;
        background: var(--lab-panel);
        padding: 0.5rem 0.7rem;
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }
    .props > li.chart-color {
        flex-direction: row;
        flex-wrap: wrap;
        align-items: center;
    }
    .props > li.pointed {
        border-color: var(--lab-accent);
    }
    .head,
    .source,
    .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        align-items: center;
    }
    .rule,
    .where {
        word-break: break-all;
    }
    .sub {
        list-style: none;
        margin: 0.3rem 0 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        font-size: 0.78rem;
    }
    .sub li {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        align-items: center;
    }
    .sub li.won {
        font-weight: 600;
    }
    summary {
        cursor: pointer;
        color: var(--lab-muted);
        font-size: 0.8rem;
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
    .badge.kind {
        color: var(--lab-fg);
    }
    .badge.warn {
        color: var(--lab-warn);
        border-color: var(--lab-warn);
    }
    .badge.accent {
        color: var(--lab-accent);
        border-color: var(--lab-accent);
    }
    .muted {
        color: var(--lab-muted);
        font-size: 0.8rem;
    }
    button {
        font: inherit;
        color: var(--lab-fg);
        background: var(--lab-sunken);
        border: 1px solid var(--lab-border);
        border-radius: 6px;
        padding: 0.25rem 0.6rem;
        cursor: pointer;
    }
    button.primary {
        background: var(--lab-accent);
        color: var(--lab-accent-fg);
        border-color: var(--lab-accent);
    }
    button.link {
        background: none;
        border: none;
        padding: 0;
        text-decoration: underline;
    }
    button:focus-visible,
    summary:focus-visible {
        outline: 2px solid var(--lab-focus);
        outline-offset: 1px;
    }
    code {
        font-family: var(--font-mono);
        font-size: 0.8rem;
    }
</style>
