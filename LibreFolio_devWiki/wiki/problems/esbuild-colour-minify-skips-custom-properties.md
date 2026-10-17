---
title: "Moving a colour into a CSS custom property changes what the build emits"
category: problem
status: resolved
date: 2026-10-14
tags: [frontend, css, vite, esbuild, build, colour, custom-properties]
related: [decisions/colour-factorisation-at-pixel-parity]
---

# Problem: Moving a colour into a CSS custom property changes what the build emits

## Symptom
In workstream R, step R-3 moved the colour literals of component `<style>` blocks into tokens. It was planned as a
pure move:

```css
/* before */
.context-menu { box-shadow: 0 10px 25px -5px rgb(0 0 0 / 0.1); }
/* after */
:root { --lf-cmp-context-menu-shadow-1: rgb(0 0 0 / 0.1); }
.context-menu { box-shadow: 0 10px 25px -5px var(--lf-cmp-context-menu-shadow-1); }
```

The production CSS would not have been the same. Before, the build shipped `#0000001a`; after, it would ship the
property as written, `rgb(0 0 0 / .1)`. The change was found on the pilot component (`ContextMenu`, 14/10), before any
commit, by minifying both versions with the build's own esbuild.

## Root Cause
Vite minifies CSS with esbuild (`build.minify: 'esbuild'`). At the time this was Vite 7.3.5 with its own esbuild
0.27.2, with the target `chrome107, edge107, firefox104, safari16`. esbuild does not treat a colour the same way
everywhere:
- **In many properties it rewrites the colour** (`color`, `background`, `border-color`, `outline-color`, `box-shadow`…).
  For example `rgb(0 0 0 / 0.1)` → `#0000001a` (alpha 26/255), `rgba(15, 23, 42, 0.5)` → `#0f172a80`, `white` →
  `#fff`, `hsl(210 40% 98%)` → `#f8fafc`.
- **In others it keeps the colour as written**, only dropping spaces and leading zeros: in the `border` and `outline`
  shorthands (`2px solid white`, `rgba(255,255,255,.6)`) and in the arguments of `color-mix()`.
- **In a custom property it rewrites no colour at all**: `--a: white` stays `white` and `--b: #FFFFFF` keeps its upper
  case; only the leading zeros go (`0.1` → `.1`).

So the same literal reaches the browser as different text depending on where it sits. An alpha of `0.1` against
`26/255` differs by less than one level of an 8-bit channel, but «probably the same pixels» is not a proof.

## Solution
Each custom property holds the exact text the build emitted for the literal it replaces, with the original spelling
in a comment when it differs:

```css
--lf-cmp-context-menu-shadow-1: #0000001a; /* rgb(0 0 0 / 0.1) */
```

Two proofs held it (session tools of workstream R):
1. every rewritten declaration, with each `var()` replaced by the token's value, minified with the same esbuild and
   target, gives the same text as the original declaration;
2. the whole build matches the baseline rule by rule once the tokens are substituted.

Where the build kept a function form (the shorthands), the token keeps the source text: the custom property carries
it unchanged, and Prettier keeps it stable.

Of the 728 tokens in the four area files, 131 hold a text different from their source spelling: the comment beside
each one shows the original.

## Prevention
- When a CSS value moves into a custom property, compare the **built** CSS, not the source.
- In a dev server (`vite dev`, no minification) the tokens now render the build's text (`#0000001a` instead of
  `rgb(0 0 0 / 0.1)`). This is invisible, and production is identical.
- Phase B (role tokens) changes the values on purpose, so the parity concern ends there.

## Impact
Nothing shipped wrong: the difference was caught on the pilot, before the first wave.

## Source files
| Role | Path |
|------|------|
| CSS minification settings | `frontend/vite.config.ts` |
| Tokens holding the emitted text | `frontend/src/lib/theme/components/table.css` |
| Tokens holding the emitted text | `frontend/src/lib/theme/components/media.css` |
| Tokens holding the emitted text | `frontend/src/lib/theme/components/files.css` |
| Tokens holding the emitted text | `frontend/src/lib/theme/components/dialogs.css` |
| Pilot component | `frontend/src/lib/components/ui/ContextMenu.svelte` |
| Gate on the tokens | `frontend/src/themeComponentTokens.gate.test.ts` |
