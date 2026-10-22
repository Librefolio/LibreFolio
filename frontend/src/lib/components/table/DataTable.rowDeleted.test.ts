/**
 * DataTable — a deleted row fades its content, never its background (TC-21).
 *
 * The defect. `tr.row-deleted td` had `opacity: 0.55`: every cell went translucent, the fixed ones too (the selection
 * column, the actions of `DataEditor`), and a fixed cell let the content that scrolls under it show through at 45 %.
 * A fixed cell hides what passes under it only with an opaque background (the rule of the row tints, `--dt-row-tint`).
 *
 * The contract, read from the component's `<style>` (jsdom lays nothing out, so the rule is checked where it is
 * written; the effect itself is seen in a browser):
 *   - no `opacity` on the cell of a deleted row: its background is opaque, the danger tint at the strength it had
 *     (55 % over the card);
 *   - the content fades under a veil of that same background at 45 %, drawn over it (`::after`), which lets the
 *     pointer through: the same look as before, the cell opaque;
 *   - the veil is placed on the cell itself: a cell that is not fixed is positioned, a fixed one already is (sticky),
 *     and on phones, where the fixed cells are unpinned, positioned again.
 *
 * Node env: the source is read as text.
 *
 * @module lib/components/table/DataTable.rowDeleted.test
 */
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

const SOURCE = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'DataTable.svelte'), 'utf-8');

/** The rules of the `<style>` block whose selector names `tr.row-deleted`: selector → declarations. */
function deletedRowRules(source: string): Map<string, string> {
    const style = /<style[^>]*>([\s\S]*?)<\/style>/.exec(source)?.[1] ?? '';
    const css = style.replace(/\/\*[\s\S]*?\*\//g, '');
    const rules = new Map<string, string>();
    for (const match of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
        const selector = match[1].trim().replace(/\s+/g, ' ');
        if (selector.includes('tr.row-deleted')) rules.set(selector, match[2].trim().replace(/\s+/g, ' '));
    }
    return rules;
}

describe('a deleted row (TC-21)', () => {
    const rules = deletedRowRules(SOURCE);

    it('barrier: the style block has rules for the deleted row', () => {
        expect(rules.size).toBeGreaterThan(0);
    });

    it('sets no opacity on its cells: a fixed cell stays opaque and hides what scrolls under it', () => {
        expect([...rules].filter(([, body]) => /(^|;)\s*opacity\s*:/.test(body)).map(([selector]) => selector)).toEqual([]);
    });

    it('paints the cell opaque, the danger tint at 55 % over the card, and veils the content with that background at 45 %, letting the pointer through', () => {
        const cell = rules.get(':global(tr.row-deleted) td') ?? '';
        expect(cell).toContain('--dt-deleted-bg: color-mix(in srgb, var(--lf-danger-soft) 55%, var(--lf-surface-card))');
        expect(cell).toContain('background: var(--dt-deleted-bg) !important');
        const veil = rules.get(':global(tr.row-deleted) td::after') ?? '';
        expect(veil).toContain("content: ''");
        expect(veil).toContain('position: absolute');
        expect(veil).toContain('inset: 0');
        expect(veil).toContain('background: color-mix(in srgb, var(--dt-deleted-bg) 45%, transparent)');
        expect(veil).toContain('pointer-events: none');
        expect(rules.get(':global(tr.row-deleted) td:not(.td-fixed)'), 'a cell that is not fixed holds its veil').toContain('position: relative');
        expect(rules.get(':global(tr.row-deleted) td.td-fixed'), 'on phones a fixed cell is unpinned (`position: static`): it is positioned again to hold its veil').toContain('position: relative');
    });
});
