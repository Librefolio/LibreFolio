<script lang="ts">
    import {untrack} from 'svelte';
    import {colorKey, formatOklch, inSrgbGamut, parseColor, rgbaToOklch, toHex} from './color.js';
    import {editTarget, isInlineAlias, sourceCategoryValue, sourceVarValue, varImpact} from './catalogView';
    import {baseVar, resolveValue, valueOpacity, withBase, withOpacity} from './colorValue';
    import {literalsOf} from './export';
    import {labT} from './i18n';
    import {changeId} from './store';
    import {isSafeCssValue} from './engine/targets';
    import type {ColorCatalog, LabChange, LabSelection, LabState, Scope} from './types';

    interface Props {
        catalog: ColorCatalog;
        lab: LabState;
        selection: LabSelection;
        scope: Scope;
        dark: boolean;
        /** Bumped whenever the page's colours change, to re-read computed values. */
        revision: number;
        onApply: (change: LabChange) => void;
        onRemove: (id: string) => void;
        onClose: () => void;
    }

    let {catalog, lab, selection, scope, dark, revision, onApply, onRemove, onClose}: Props = $props();

    const OCC_ROWS = 60;
    const isVar = $derived(selection.layer === 'css-var');
    const isElement = $derived(selection.layer === 'element');
    const isCategory = $derived(selection.layer === 'category');
    const isLiteral = $derived(!isVar && !isElement && !isCategory);

    function computed(name: string): string {
        void revision;
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    /** The occurrence this change is restricted to (`css-literal` only); undefined = every occurrence of the value. The picked element's rule is preselected. */
    let occurrence = $state<number | undefined>(untrack(() => (selection.layer === 'css-literal' ? selection.occurrence : undefined)));
    const existing = $derived(lab.changes.find((c) => c.id === changeId({layer: selection.layer, target: selection.target, scope, occurrence, property: selection.property, colorKey: selection.colorKey})));
    const original = $derived.by(() => {
        if (existing) return existing.from;
        if (isElement) return selection.from ?? '';
        if (isVar) return sourceVarValue(catalog, selection.target, scope === 'dark' || (scope === 'both' && dark), computed(selection.target));
        if (isCategory) return sourceCategoryValue(catalog, selection.target, scope === 'dark' || (scope === 'both' && dark));
        return selection.target;
    });
    const anchor = $derived(selection.anchor ?? existing?.anchor);

    let to = $state('');
    let note = $state('');
    let shots = $state('');
    let alphaVariants = $state(true);
    let snap = $state('');

    // Load the form whenever the edited item, theme or occurrence changes.
    $effect(() => {
        const c = existing;
        to = c?.to ?? original;
        note = c?.note ?? '';
        shots = c?.shots?.join(', ') ?? '';
        alphaVariants = c?.alphaVariants ?? true;
        snap = c ? (baseVar(c.to) ?? '') : '';
    });

    const varNames = $derived([...new Set([...catalog.palette.map((p) => editTarget(p)), ...catalog.css_vars.filter((v) => v.defs.length && !isInlineAlias(v)).map((v) => v.name)])].sort());
    // A literal, a `var()` read from the page, or the translucent mix of the role tokens (`color-mix(…, transparent)`).
    const resolved = $derived.by(() => {
        void revision;
        return resolveValue(to, computed);
    });
    const opacity = $derived(valueOpacity(to));
    const valid = $derived(isSafeCssValue(to.trim()) && !!resolved);
    const oklch = $derived(resolved ? rgbaToOklch(resolved) : null);
    const outOfGamut = $derived(!!resolved && !inSrgbGamut(resolved));
    const occurrences = $derived(isLiteral ? literalsOf(catalog, {id: '', layer: selection.layer, target: selection.target, scope, from: '', to: '', alphaVariants}) : []);
    const impact = $derived(isVar ? varImpact(catalog, selection.target) : null);
    const cssVar = $derived(impact?.variable);
    const sharedRule = $derived(selection.layer === 'css-literal' && scope !== 'both' && occurrences.some((l) => l.theme === 'both'));
    /** A chart value that is also the fixed colour of chart categories: editing the value reaches them all at once. */
    const valueCategories = $derived([...new Set(occurrences.map((l) => l.category).filter((c): c is string => !!c))]);
    /** `category`: the line of each theme in the tables of `chartCategories.ts`. */
    const categoryLines = $derived.by(() => {
        if (!isCategory) return [];
        const category = catalog.categories?.find((c) => c.target === selection.target);
        if (!category) return [];
        return (['light', 'dark'] as const).map((theme) => ({theme, lit: category[theme] === null ? undefined : catalog.literals[category[theme] as number]})).filter((x): x is {theme: 'light' | 'dark'; lit: (typeof catalog.literals)[number]} => !!x.lit);
    });
    const topClasses = $derived(
        impact
            ? Object.entries(impact.classes)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 12)
            : [],
    );

    // The colour controls change the colour and keep the opacity: a translucent value stays translucent, a mix stays a mix.
    function setFromOklch(part: 'l' | 'c' | 'h', value: number): void {
        if (!oklch) return;
        snap = '';
        to = withBase(to, formatOklch({...oklch, alpha: 1, [part]: value}));
    }

    function setOpacity(value: number): void {
        const next = withOpacity(to, value);
        if (next !== null) to = next;
    }

    function apply(): void {
        if (!valid) return;
        const lit = occurrence === undefined ? undefined : catalog.literals.find((l) => l.id === occurrence);
        const change: LabChange = {id: '', layer: selection.layer, target: selection.target, scope, from: original, to: to.trim()};
        if (isElement) {
            change.property = selection.property;
            if (selection.colorKey) change.colorKey = selection.colorKey;
        } else if (isLiteral) change.alphaVariants = alphaVariants;
        if (lit) {
            change.occurrence = lit.id;
            change.match = {selector: lit.selector ?? '', property: lit.property ?? null};
        }
        if (anchor) change.anchor = anchor;
        if (note.trim()) change.note = note.trim();
        const shotList = shots
            .split(/[,\s]+/)
            .map((s) => s.trim())
            .filter(Boolean);
        if (shotList.length) change.shots = shotList;
        change.id = changeId(change);
        onApply(change);
    }
</script>

<section class="editor" data-testid="lab-editor" data-layer={selection.layer} data-target={selection.target} data-property={selection.property ?? null}>
    <header>
        <h2>{$labT('editor.title')}</h2>
        <button type="button" class="ghost" data-testid="lab-editor-close" onclick={onClose}>{$labT('editor.close')}</button>
    </header>
    <p class="target">
        <span class="badge">{$labT(`layer.${selection.layer}`)}</span> <code>{selection.target}</code>
        {#if isElement}· <code>{selection.property}</code>{#if selection.colorKey}&nbsp;<code>{selection.colorKey}</code>{/if}{/if} · {$labT(`scope.${scope}`)}
    </p>
    {#if isElement}
        <p class="msg" data-testid="lab-editor-specialise-hint">{$labT('editor.specialiseHint')}</p>
        {#if anchor}<p class="muted" data-testid="lab-editor-matches" data-matches={anchor.matches}>{anchor.matches === 1 ? $labT('editor.matchesOne') : $labT('editor.matches', {n: anchor.matches})}</p>{/if}
    {/if}

    <div class="swatches">
        <div>
            <span class="label">{$labT('editor.from')}</span>
            <span class="swatch big checker"><span class="fill" style:background={original}></span></span>
            <code data-testid="lab-editor-from">{original || '—'}</code>
        </div>
        <div>
            <span class="label">→</span>
            <span class="swatch big checker"><span class="fill" style:background={valid ? to : 'transparent'}></span></span>
        </div>
    </div>

    <label class="field">
        <span>{$labT('editor.to')}</span>
        <input type="text" spellcheck="false" bind:value={to} data-testid="lab-editor-to" />
    </label>
    {#if !valid}<p class="msg danger" data-testid="lab-editor-invalid">{$labT('editor.invalid')}</p>{/if}
    {#if outOfGamut}<p class="msg warn" data-testid="lab-editor-gamut-warning">{$labT('editor.gamut')}</p>{/if}

    {#if oklch}
        <div class="sliders">
            <label>L <input type="range" min="0" max="1" step="0.001" value={oklch.l} oninput={(e) => setFromOklch('l', +e.currentTarget.value)} data-testid="lab-editor-l" /> <code>{(oklch.l * 100).toFixed(1)}%</code></label>
            <label>C <input type="range" min="0" max="0.4" step="0.001" value={oklch.c} oninput={(e) => setFromOklch('c', +e.currentTarget.value)} data-testid="lab-editor-c" /> <code>{oklch.c.toFixed(3)}</code></label>
            <label>H <input type="range" min="0" max="360" step="0.5" value={oklch.h} oninput={(e) => setFromOklch('h', +e.currentTarget.value)} data-testid="lab-editor-h" /> <code>{oklch.h.toFixed(1)}</code></label>
            {#if opacity !== null}
                <label title={$labT('editor.opacity')}>A <input type="range" min="0" max="1" step="0.01" value={opacity} oninput={(e) => setOpacity(+e.currentTarget.value)} data-testid="lab-editor-a" /> <code>{Math.round(opacity * 100)}%</code></label>
            {/if}
        </div>
    {/if}

    <div class="row">
        <label class="inline">
            sRGB
            <input
                type="color"
                value={resolved ? toHex(resolved, false) : '#000000'}
                oninput={(e) => {
                    snap = '';
                    to = withBase(to, e.currentTarget.value);
                }}
                data-testid="lab-editor-color"
            />
        </label>
        <label class="inline grow">
            {$labT('editor.snap')}
            <select
                bind:value={snap}
                onchange={() => {
                    if (snap) to = withBase(to, `var(${snap})`);
                }}
                data-testid="lab-editor-snap"
            >
                <option value="">{$labT('editor.snapNone')}</option>
                {#each varNames as name (name)}<option value={name}>{name}</option>{/each}
            </select>
        </label>
    </div>

    {#if isLiteral}
        <label class="inline"><input type="checkbox" bind:checked={alphaVariants} data-testid="lab-editor-alpha" /> {$labT('editor.alpha')}</label>
    {/if}
    {#if selection.layer === 'css-literal'}
        <label class="field">
            <span>{$labT('editor.granularity')}</span>
            <select bind:value={occurrence} data-testid="lab-editor-occurrence">
                <option value={undefined}>{$labT('editor.allOccurrences')}</option>
                {#each occurrences.filter((l) => l.selector) as l (l.id)}<option value={l.id}>{$labT('editor.oneOccurrence')}: {catalog.files[l.file]}:{l.line} · {l.selector} {l.property}</option>{/each}
            </select>
        </label>
    {/if}
    {#if sharedRule}<p class="msg warn">{$labT('editor.sharedRule')}</p>{/if}
    {#if valueCategories.length}<p class="msg warn" data-testid="lab-editor-category-warning">{$labT('editor.categoryValue', {list: valueCategories.join(', ')})}</p>{/if}
    {#if isCategory}<p class="msg" data-testid="lab-editor-category-reach">{$labT('editor.categoryReach')}</p>{/if}
    {#if selection.layer === 'proposal'}<p class="msg warn">{$labT('editor.noPreview')}</p>{/if}

    <label class="field">
        <span>{$labT('editor.note')}</span>
        <textarea rows="2" bind:value={note} data-testid="lab-editor-note"></textarea>
    </label>
    <label class="field">
        <span>{$labT('editor.shots')}</span>
        <input type="text" bind:value={shots} data-testid="lab-editor-shots" />
    </label>

    <div class="actions">
        <button type="button" class="primary" disabled={!valid} onclick={apply} data-testid="lab-editor-apply">{$labT('editor.apply')}</button>
        {#if existing}<button type="button" class="danger" onclick={() => onRemove(existing.id)} data-testid="lab-editor-remove">{$labT('editor.remove')}</button>{/if}
    </div>

    {#if isVar}
        <h3>{$labT('editor.impact')}</h3>
        <p>{impact?.uses ?? 0} {$labT('uses')} · {impact?.files ?? 0} {$labT('files')}</p>
        {#if topClasses.length}<p class="classes">
                {#each topClasses as [cls, n] (cls)}<code>{cls}</code>×{n}
                {/each}
            </p>{/if}
        {#if cssVar?.defs.length}
            <h3>{$labT('editor.definedAt')}</h3>
            <ul class="occ">
                {#each cssVar.defs as d (d.file + ':' + d.line)}<li><code>{catalog.files[d.file]}:{d.line}</code> <code>{d.selector}</code> = <code>{d.value}</code></li>{/each}
            </ul>
        {/if}
    {:else if isLiteral}
        <h3>{occurrences.length} {$labT('occurrences')}</h3>
        <ul class="occ" data-testid="lab-editor-occurrences">
            {#each occurrences.slice(0, OCC_ROWS) as l (l.id)}
                <li>
                    <span class="swatch" style:background={l.raw}></span>
                    <code>{catalog.files[l.file]}:{l.line}</code>
                    {#if l.selector}<code>{l.selector}</code> {l.property}{/if}
                    {#if l.theme}<span class="badge">{l.theme}</span>{/if}
                    <span class="snippet">{l.snippet}</span>
                </li>
            {/each}
        </ul>
        {#if occurrences.length > OCC_ROWS}<p class="muted">{$labT('moreRows', {n: occurrences.length - OCC_ROWS})}</p>{/if}
        <p class="muted"><code>{colorKey(parseColor(selection.target) ?? {r: 0, g: 0, b: 0, alpha: 1})}</code></p>
    {:else if isCategory}
        <h3>{$labT('editor.categoryLines')}</h3>
        <ul class="occ" data-testid="lab-editor-category-lines">
            {#each categoryLines as x (x.theme)}
                <li>
                    <span class="swatch" style:background={x.lit.raw}></span>
                    <code>{catalog.files[x.lit.file]}:{x.lit.line}</code>
                    <span class="badge">{$labT(`scope.${x.theme}`)}</span>
                    <code>{x.lit.raw}</code>
                </li>
            {/each}
        </ul>
    {:else if anchor}
        <h3>{$labT('element.candidates')}</h3>
        <ul class="occ" data-testid="lab-editor-candidates">
            {#each anchor.candidates as c, ci (ci)}<li><code>{c.file}:{c.line}</code> <span class="badge">{c.why}</span> <code class="snippet">{c.needle}</code></li>{/each}
        </ul>
        <p class="muted"><code>{anchor.route}</code> · {anchor.testids.join(' ‹ ')}</p>
    {/if}
</section>

<style>
    .editor {
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        padding: 1rem;
        background: var(--lab-panel);
        border: 1px solid var(--lab-border);
        border-radius: 10px;
        min-width: 0;
    }
    header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    h2 {
        font-size: 1.05rem;
        font-weight: 600;
        margin: 0;
    }
    h3 {
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0.6rem 0 0;
    }
    .target {
        margin: 0;
        word-break: break-all;
    }
    .swatches {
        display: flex;
        gap: 1.5rem;
        align-items: center;
    }
    .swatches > div {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .label,
    .muted {
        color: var(--lab-muted);
        font-size: 0.8rem;
    }
    .swatch {
        display: inline-block;
        width: 1rem;
        height: 1rem;
        border-radius: 4px;
        border: 1px solid var(--lab-border);
        vertical-align: middle;
        flex: none;
    }
    .swatch.big {
        width: 2.5rem;
        height: 2.5rem;
    }
    /* A checkerboard under the colour, so that its opacity shows. */
    .checker {
        position: relative;
        overflow: hidden;
        background: conic-gradient(var(--lab-check) 25%, var(--lab-panel) 0 50%, var(--lab-check) 0 75%, var(--lab-panel) 0) 0 0 / 0.625rem 0.625rem;
    }
    .checker > .fill {
        position: absolute;
        inset: 0;
    }
    .field {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        font-size: 0.85rem;
    }
    .inline {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.85rem;
    }
    .grow {
        flex: 1;
    }
    .row {
        display: flex;
        gap: 1rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .sliders {
        display: grid;
        gap: 0.3rem;
        font-size: 0.85rem;
    }
    .sliders label {
        display: grid;
        grid-template-columns: 1.2rem 1fr 4.5rem;
        align-items: center;
        gap: 0.5rem;
    }
    input[type='range'],
    input[type='checkbox'] {
        accent-color: var(--lab-accent);
    }
    input[type='text'],
    textarea,
    select {
        background: var(--lab-sunken);
        color: var(--lab-fg);
        border: 1px solid var(--lab-border);
        border-radius: 6px;
        padding: 0.35rem 0.5rem;
        font: inherit;
        min-width: 0;
    }
    input:focus-visible,
    textarea:focus-visible,
    select:focus-visible,
    button:focus-visible {
        outline: 2px solid var(--lab-focus);
        outline-offset: 1px;
    }
    .actions {
        display: flex;
        gap: 0.5rem;
    }
    button {
        border-radius: 6px;
        padding: 0.35rem 0.8rem;
        border: 1px solid var(--lab-border);
        background: var(--lab-sunken);
        color: var(--lab-fg);
        font: inherit;
        cursor: pointer;
    }
    button.primary {
        background: var(--lab-accent);
        color: var(--lab-accent-fg);
        border-color: var(--lab-accent);
    }
    button.danger {
        color: var(--lab-danger);
    }
    button.ghost {
        background: transparent;
    }
    button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    .msg {
        margin: 0;
        font-size: 0.82rem;
    }
    .msg.danger {
        color: var(--lab-danger);
    }
    .msg.warn {
        color: var(--lab-warn);
    }
    .badge {
        font-size: 0.72rem;
        padding: 0.05rem 0.4rem;
        border-radius: 999px;
        background: var(--lab-sunken);
        border: 1px solid var(--lab-border);
        color: var(--lab-muted);
    }
    .occ {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        font-size: 0.78rem;
        max-height: 22rem;
        overflow: auto;
    }
    .occ li {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .snippet {
        color: var(--lab-muted);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 100%;
    }
    .classes {
        font-size: 0.78rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem;
    }
    code {
        font-family: var(--font-mono);
        font-size: 0.78rem;
    }
</style>
