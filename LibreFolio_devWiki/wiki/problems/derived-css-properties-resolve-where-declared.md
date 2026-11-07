---
title: "A custom property that names another is resolved where it is declared: derived colours declared on :root kept their light values under a dark theme set on body"
category: problem
status: resolved
date: 2026-11-07
tags: [docs, mkdocs, css, custom-properties, dark-mode, theme]
related:
  - decisions/docs-home-badges-match-project-site
  - decisions/colour-factorisation-at-pixel-parity
  - problems/esbuild-colour-minify-skips-custom-properties
---

# Problem: derived colours did not follow the docs' dark scheme

## Symptom

In the documentation's dark scheme, links and the other derived colour roles kept their light-theme values (a light
green link on the dark page). The base roles switched correctly.

## Root cause

The docs read the app's colour roles from `frontend/src/lib/theme/tokens.css`, rewritten at build time by the hook
`lf_theme_tokens.py`: the app's dark block (`html.dark, .dark`) is re-keyed on Material's scheme,
`[data-md-color-scheme="slate"]`, which Material sets on **`body`**. Derived roles live in a separate block,
`:root, .light, .dark { --lf-link: var(--lf-focus); … }`.

A custom property whose value is `var(--other)` is **computed on the element where it is declared**, and the computed
value is what descendants inherit. On `:root` (`html`) the base roles are the light ones, so `--lf-link` is computed
light there; `body` inherits the computed value, and redefining `--lf-focus` on `body` does not recompute
`--lf-link`. In the app it works because the dark class is on `html` itself; in the docs the scheme sits one level
lower.

## Solution

The hook adds Material's scheme selector to the derived block too
(`:root, .light, .dark, [data-md-color-scheme="slate"] { … }`), so the derived roles are recomputed on `body` under the
dark scheme. It fails the build when it cannot find exactly one such block. A test pins the transform (`b131b0a6e`).
The badge workaround (`--lf-focus` instead of `--lf-link`) was removed afterwards.

## Prevention

- A block of derived custom properties must be declared on **every element that changes the base values**, not only on
  `:root`.
- When a theme switch is moved to another element (a framework's `body` attribute instead of `html.dark`), re-check
  the derived variables, not only the base ones.

## Impact

Wrong link colour in the dark documentation; one workaround in the home badges, later removed.

## Source files

| Role | Path |
|------|------|
| The hook (the fix) | `mkdocs_src/hooks/lf_theme_tokens.py` |
| Source of the roles | `frontend/src/lib/theme/tokens.css` |
| Test | `backend/test_scripts/test_utilities/test_docs_theme_tokens.py` |
| Badge that carried the workaround | `mkdocs_src/docs/stylesheets/home-custom.css` |
