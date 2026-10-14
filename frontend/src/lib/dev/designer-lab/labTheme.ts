/**
 * Designer Lab — the Lab's own colours.
 *
 * They reach the page only as `--lab-*` custom properties in the inline `style` of the Lab's root element. The
 * engines rewrite stylesheet rules and `<html>` variables, never an element's inline style, so editing the app's
 * colours never repaints the Lab itself; the Lab's stylesheet holds no colour of its own, only `var(--lab-*)`.
 */

const LIGHT = {
    bg: '#f6f6f4',
    panel: '#ffffff',
    sunken: '#efefec',
    fg: '#1c1c1e',
    muted: '#5f5f66',
    border: '#d5d5d9',
    accent: '#2d5a4c',
    'accent-fg': '#ffffff',
    danger: '#b3261e',
    warn: '#8a5a00',
    ok: '#1f7a3a',
    focus: '#2b63d9',
    check: '#e4e4e7',
};

const DARK: typeof LIGHT = {
    bg: '#161618',
    panel: '#202024',
    sunken: '#2a2a2f',
    fg: '#ececef',
    muted: '#a2a2aa',
    border: '#3a3a40',
    accent: '#7fc4a9',
    'accent-fg': '#10201a',
    danger: '#ff8a80',
    warn: '#f2c14e',
    ok: '#7ad49a',
    focus: '#8ab4ff',
    check: '#3a3a40',
};

export function labStyle(dark: boolean): string {
    return Object.entries(dark ? DARK : LIGHT)
        .map(([k, v]) => `--lab-${k}: ${v}`)
        .join('; ');
}
