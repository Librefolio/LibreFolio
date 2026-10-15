---
title: "Colours factored into lib/theme at pixel parity (workstream R)"
category: decision
status: resolved
date: 2026-10-15
tags: [frontend, theme, colour, css, charts, dark-mode, refactor, gates]
related: [problems/esbuild-colour-minify-skips-custom-properties, problems/colour-ratchet-resolve-drops-an-accept, decisions/heatmap-emphasis-is-hue-free, problems/front-check-does-not-check-what-you-think]
---

# Decision: Colours factored into lib/theme at pixel parity (workstream R)

## Context
The colour programme after 1.2 (folder `Phase_1/10_colorSystem`) waits for a designer's palette. Its analysis of
14/10 counted, in production code outside `app.css`, **1 554 hex literals and 198 colour functions**. They were
spread across chart scripts, sign and status ternaries, and the `<style>` blocks of tables, media and file modals. The
same meaning carried slightly different values in different places (the loss red is `#ef4444` on price charts,
`#dc2626` on portfolio charts).

The developer, 14/10: «già che ci siamo iniziamo anche a fattorizzare e correggere gli errori che avevi già
identificato a livello di progetto per i colori, e poi quando la designer arriva aggiorniamo i colori». In short:
factor the colours and fix the known errors now; change the colours when the designer arrives.

## Options Considered
1. **Factor and re-colour together**: rejected. Every visible change waits for the designer's report, and mixing the
   two would hide regressions inside intended changes.
2. **Factor straight onto role tokens (`--lf-*`)**: rejected. Roles are the designer's decision; they became phase B,
   workstream T.
3. **Factor at pixel parity, keeping today's divergences under a name**: chosen.

## Decision
Every colour moves to a few central modules in `frontend/src/lib/theme/`, and **no pixel changes**:

| Module | Holds |
|---|---|
| `colorAlpha.ts` | `toRgba`, `withAlpha`, `withHexAlpha`: the same strings as before on the real inputs, never `NaN` |
| `themePair.ts` | `ThemePair` and `themed(pair, dark)`, the one place where a value is picked by theme |
| `chartTheme.ts`, `chartPalettes.ts`, `chartColorScales.ts` | ECharts colours by meaning, the categorical palettes and scales, the two colour formulas |
| `toneClasses.ts` | complete literal Tailwind classes for sign, status and badges |
| `components/{table,media,files,dialogs}.css` | `--lf-cmp-<component>-<role>` tokens and their `-dark` twins on `:root`, imported by their components |
| `drawnColors.ts` | colours a `var()` cannot reach: the cheetah-grid theme, SVG data URLs |
| `themeMode.ts` | `isDarkTheme()` and `onThemeClassChange()`, the only reader of the theme class |

Rules:
- same values and the same strings; two different values are never merged; one name holds one value and one meaning;
- a divergence keeps its own name, so the designer sees it: `CHART_GAIN_LOSS.price` (loss `#ef4444`) against
  `CHART_GAIN_LOSS.portfolio` (loss `#dc2626`), the light-only semi-donut, the inverted treemap scale;
- Tailwind classes stay complete literals in `.ts` files under `src/lib`, which the scanner reads;
- a component's `.dark` rules stay where they are and read the `-dark` twin (D2);
- charts keep redrawing on any change of the class of `<html>`, not only `dark` (D4): the Designer Lab relies on it.

The developer's decisions D1–D7 (14/10) were all option (a). They come with the rule «conta lo stile»: code proofs
stay strict; in the gallery, differences of content are accepted and differences of style or colour are regressions.
R was allowed exactly two fixes:
- the dark `theme-color` meta, `#156534` → `#166534` in its three copies (D3);
- alpha helpers that only accepted `#rrggbb` (R-4).

### How parity was proved
Each wave, before any commit:
- **conservation**: in every file touched, the colour literals, light/dark pairs and Tailwind classes equal those of
  the new file once the `lib/theme` values are put back;
- **compiled CSS** identical for the Tailwind classes;
- **`<style>` → tokens**:
  - every rewritten declaration, with each `var()` replaced by the token's value, is minified with the esbuild and
    target that Vite uses, and gives the same text as before (see
    [[problems/esbuild-colour-minify-skips-custom-properties]]);
  - the whole build is then compared with the baseline rule by rule;
  - the Vite manifest shows that every entry reading a token also loads its definition;
- **undo self-checks** for the scripted rewrites: undoing every replacement gives back the input, byte for byte;
- **gates**, all in `core-unit`: `themeColorMeta` (D3), `themeComponentTokens` (R-3), `themeModeReads` (D4);
- **one gallery gate for the four lots** (15/10): 2 370 identical images and 454 changed, all content (upload times,
  the lane's files) or the shot's own noise.

## Consequences
- Literals outside `lib/theme/**` and `app.css` (production code, `scripts/visual_review/color_inventory.py`): hex
  1 554 → 85, colour functions 198 → 50. What is left is outside R's scope or a declared exception, and the colour
  ratchet M2 of workstream T (`frontend/scripts/theme/theme-roles.mjs`) watches it.
- Declared exceptions, in T's `LITERAL_EXCEPTIONS`:
  - the `lotColor` generator and the `hsl()` generators of `lib/utils/colors.ts`;
  - the `#000` of a demo signal that is never drawn;
  - the `#a855f7` preview line of the data editors (backlog R-6).
- Phase B (T) moves these names onto roles: `toneClasses` in B2, `themed()` in B4, `--lf-cmp-*` in B5. ECharts,
  cheetah-grid and SVG data URLs cannot read `var()`: roles must be resolved to values when drawing, with
  `onThemeClassChange()` as the single trigger.
- Left open in the backlog:
  - R-5: `withAlpha` on an `hsl()` with spaces;
  - R-6: the preview line;
  - R-7: two views that do not follow a live theme switch;
  - R-8: [[problems/colour-ratchet-resolve-drops-an-accept]].
- Lesson from the D3 fix: changing `static/offline.html` requires restamping `static/sw.js` ([[features/F-098]]).

## Links
- [[features/F-007]]
- Source: `LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/R-colorRefactor/plan-phase00ColorRefactor.prompt.md`
- Entered `dev_release2` on 15/10 with `8fd8e494b`, the four lots being `d80b9e0cd`, `75c45d923`, `0b660632f` and
  `98731240d`.

## Source files
| Role | Path |
|------|------|
| Alpha helpers | `frontend/src/lib/theme/colorAlpha.ts` |
| Pick by theme | `frontend/src/lib/theme/themePair.ts` |
| Chart colours by meaning | `frontend/src/lib/theme/chartTheme.ts` |
| Chart palettes | `frontend/src/lib/theme/chartPalettes.ts` |
| Chart colour formulas | `frontend/src/lib/theme/chartColorScales.ts` |
| Tone classes | `frontend/src/lib/theme/toneClasses.ts` |
| Component tokens | `frontend/src/lib/theme/components/table.css` |
| Component tokens | `frontend/src/lib/theme/components/media.css` |
| Component tokens | `frontend/src/lib/theme/components/files.css` |
| Component tokens | `frontend/src/lib/theme/components/dialogs.css` |
| Colours drawn outside CSS | `frontend/src/lib/theme/drawnColors.ts` |
| Theme reads | `frontend/src/lib/theme/themeMode.ts` |
| Gate D3 | `frontend/src/themeColorMeta.gate.test.ts` |
| Gate R-3 | `frontend/src/themeComponentTokens.gate.test.ts` |
| Gate D4 | `frontend/src/themeModeReads.gate.test.ts` |
| Colour ratchet and exceptions (T) | `frontend/scripts/theme/theme-roles.mjs` |
| Colour inventory | `scripts/visual_review/color_inventory.py` |
