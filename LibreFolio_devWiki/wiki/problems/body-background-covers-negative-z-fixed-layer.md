---
title: "Once html has its own background, a body background stops propagating to the canvas and covers a fixed layer with negative z-index"
category: problem
status: resolved
date: 2026-11-07
tags: [frontend, css, dark-mode, theme, stacking-context, login]
related:
  - decisions/colour-factorisation-at-pixel-parity
  - problems/derived-css-properties-resolve-where-declared
---

# Problem: the login animation disappeared in the dark theme

## Symptom

1. On 06/11/2026 a strip of a legacy colour showed at the right edge of the app: the space reserved by
   `scrollbar-gutter: stable` on `html` showed the document's default background.
2. The fix gave `html` the app's background. The next day the animated background of the standalone pages (login and
   the others outside the app shell) was gone in the dark theme, while it still showed in the light one.

## Root cause

CSS background propagation: when `html` has no background, the `body` background is **propagated to the canvas** and
painted behind everything. Once `html` has its own background, the `body` background is painted on the body's own box.
The animated background is a fixed element with negative `z-index`: it is painted after the root's background but
before the in-flow blocks, so the body's box now covered it. Only the dark theme set a body background
(`html.dark body { background-color: … }`), so only the dark theme lost the animation.

## Solution

- `html { background-color: var(--lf-surface-app); }` — the gutter shows the app's colour (`7ef834b30`).
- No background on `body` in the dark theme: the document's is the page's (`5ce63979c`). The theme-token gate test pins
  both.

## Prevention

- Give the page background to **one** element. If `html` has it, `body` must not, or every negative-z-index layer
  disappears behind the body.
- A visual change to `html` or `body` needs a look at the standalone pages in both themes.

## Impact

A day without the login animation in the dark theme; caught on the developer's test list.

## Source files

| Role | Path |
|------|------|
| Document and body backgrounds | `frontend/src/app.css` |
| Gate test | `frontend/src/themeTokens.gate.test.ts` |
| The fixed layer (`position: fixed; z-index: -10`) | `frontend/src/lib/components/ui/AnimatedBackground.svelte` |
