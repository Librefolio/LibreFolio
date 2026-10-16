---
name: design-system
description: "Use this skill whenever you create or change any frontend UI (a component, a page, a dialog, a form, a badge, a chart), choose a colour, or touch the light or dark theme. It is the LibreFolio design system: the two themes «Stone and Sage» (light) and «Slate and Sage» (dark), every colour role with its value in both themes and when to use it, the shared colour folder frontend/src/lib/theme/, and the rules (roles only, no dark:, WCAG contrast, focus, tooltips, gain and loss, charts, how to get a new role). To convert legacy palette classes or touch the colour ratchet baseline, use theme-roles."
---

# LibreFolio design system: two themes, one palette, the rules

## The one idea

**You never pick a colour: you pick a role.** A role says what the colour is for: the card, the muted text, the
border of a field, an error. Each role has one value in the light theme and one in the dark theme, and it lives in
one place, [`tokens.css`](../../../../frontend/src/lib/theme/tokens.css). A component that uses roles follows both
themes, and every later change of the designer, with no `dark:` at all.

- **This skill:** what to use when you build or change UI. The themes, the palette with its values, the shared colour
  folder, the rules, the decisions and what is still open.
- **The skill [`theme-roles`](../theme-roles/SKILL.md):** how to convert a component that still writes palette classes
  (the class → role table), and the colour ratchet's baseline (`--update`, `--split`, `--resolve`). Not repeated here.
- **Paths** are under `frontend/` (`src/…`, `static/…`, `e2e/…`); the files of the colour folder go by their name.

## The two themes

|  | Light | Dark |
|---|---|---|
| Name | **«Stone and Sage»** | **«Slate and Sage»** |
| The designer's name | «Pietra e Salvia» | «Ardesia e Salvia» |
| Surfaces | a pale stone page, near-white cards, a stone panel | a near-black slate page, slate cards one step lighter |
| Text | a green-black, with two quieter steps | a near-white grey-green, with two quieter steps |

- **Shared by both:** the brand green of the sidebar, the login card header and the installed app's title bar; the
  focus green, a step brighter in dark, for focus, links and selected controls; amber for warnings and the donation
  link; a violet for the AI functions; four state families with explicit tints.
- **Where they come from:** the designer's round 2, 15/10/2026
  ([`designer-feedback/2026-10-15-round2-palette/`](../../../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/designer-feedback/2026-10-15-round2-palette/README.md)),
  approved whole by the developer (D-T17), with his later corrections (D-T18, D-T23–D-T26). The English names are the
  ones of the `CHANGELOG.md`; `tokens.css` keeps the Italian ones in its comments.
- **How a theme is applied:** the `dark` class on `<html>`, written by the anti-FOUC script of `src/app.html` and by
  `applyTheme()` in `src/lib/stores/app/themeStore.ts`. A subtree can force a theme with `.light` or `.dark`, and the
  roles recompute inside it. Read and watch the theme only through `themeMode.ts`.

## The shared colour folder: `frontend/src/lib/theme/`

**Every colour of the app lives in this folder, and only there.**

- **Components take their colours from it:** the role utilities of `tokens.css`, the class tables of `toneClasses.ts`,
  the palettes and the categories of the charts.
- **At most, you add to it; never to a component.** A new colour is a new role in `tokens.css` with its contrast pair
  in the gate (only T creates roles, see «Asking for a new role»), or a new entry in the right table below.
- **The gate enforces it** (`src/themeRoles.gate.test.ts`):
  - colour literals (m2) are not counted under `lib/theme/**`, and are counted everywhere else: an existing file can
    only lose them (R2);
  - a new file starts with no legacy class and no colour literal, unless it lives under `lib/theme/**` (R3).
- **A table entry that needs a role which does not exist yet:** ask T for it, through the colour coordinator.

| File | What it holds | A component uses it when… | Owner | To add an entry |
|---|---|---|---|---|
| `tokens.css` | The 95 roles of the two themes (a light, a derived and a dark block) and the `@theme inline` table that turns 91 of them into utilities (`bg-lf-card`…) | it draws any colour: as a utility, or `var(--lf-…)` in a `<style>` | T | Only T: «Asking for a new role» below |
| `components/dialogs.css`, `files.css`, `media.css`, `table.css` | The component tokens `--lf-cmp-<component>-<role>` (with `-dark` twins) that workstream R moved out of the `<style>` blocks of the dialogs, files, media and tables, at pixel parity: legacy values | it is one of those components; it loads its file with a side-effect import (`import '$lib/theme/components/table.css'`) | T | **Never a new token**: a new colour is a role. Migrating such a component replaces its `var(--lf-cmp-…)` with roles and deletes the tokens nobody reads any more (`src/themeComponentTokens.gate.test.ts`: each token defined once, imported where read, read by someone) |
| `toneClasses.ts` | Whole class strings on the roles: signed figures (`SIGN_TEXT`, `SIGN_BAR`), diverging measures (`POLARITY_TONES`), states (`STATUS_TONES`: sync, PAC, toasts, import report and file sets, risk chips, data quality, live updates). The kinds told apart by hue alone (`KIND_TONES`, `STATUS_TONES.fileSet.combined`) are categorical, still palette classes | it colours a sign, a polarity, a state or a kind: it takes the entry by name; the threshold (`>= 0`, `> 0`) stays with the caller | T | A new named entry, a whole literal string of role utilities (never assembled), in the table of its meaning. An entry keeps its own name even when its classes equal another's |
| `chartCategories.ts` | The fixed colour of every asset type and sector, of the cash and of «unclassified», in both themes (GR1–GR3); the key sequences (GR5); `categoryColor`, `sequenceColor`, `lookupKey`, `isUnclassifiedCountry` | it draws a category: a chart, its legend, its tooltip | DV | A new key (a new asset type or sector) takes the designer's pair, one literal per line (C2), in her table order. Until then it reads as unclassified |
| `chartShades.ts` | The colour arithmetic of the category charts: `mixOklab`, `familyShade` (subtypes, GR4; rounds past a sequence, GR5), `shadePoles`, `scaleColor` | it draws a subtype, a sequence past its end, a value on a continuous scale | DV | A new mixing rule here, with its test. Never mix colours in a component |
| `chartPalettes.ts` | The lists still read as they are: `SIGNAL_DEFAULT_PALETTE` (a new signal's line), `GEO_CHOROPLETH_SCALE` (the world maps, GR5.1), `growthBrokerColor` (the broker lines of the Growth chart) | it is one of those charts | DV | Through DV. A palette that colours categories goes through `chartCategories.ts` instead |
| `chartColorScales.ts` | Colours computed from a value: `treemapPnlColor` (a treemap tile by its P&L; a legacy formula, for the designer), `timingEffectColor` (`color-mix` over `--lf-gain`/`--lf-loss`) | it is one of those | DV | A new value → colour formula here, on the roles: `color-mix(in oklab, var(--lf-…) …)` for CSS, `chartRoles` for a canvas |
| `chartTheme.ts` | The named colours of the ECharts charts, by meaning, as `{light, dark}` pairs or one string for both themes (prices, gain and loss, neutrals, tooltips, risk, allocation, semi-donut, maps, correlation, signals, income events, growth, performance, treemap, risk overlays, lots), moved verbatim: legacy values, divergences kept under two names | it draws one of those meanings, read with `themed(pair, dark)` | DV | Reuse a name; a new one only through DV. B4 moves these onto roles |
| `roleColors.ts` | The bridge from roles to a canvas: `chartRoles(dark, scope)` reads `--lf-*` on the chart's own element at each draw (`color(role)`, `readableText(background)`), with stand-ins equal to `tokens.css` where no stylesheet is loaded | a canvas chart needs a role: card, panel, primary, secondary or inverse text, danger, info | DV | A role missing from `ChartRole` is added with its stand-in, which the parity test `roleColors.test.ts` keeps equal to `tokens.css`. Ask through the colour coordinator |
| `drawnColors.ts` | Colours handed to a canvas library or baked into an SVG data URL, where `var()` cannot reach: the spreadsheet preview, the `LazyImage` placeholders, the uploader avatar's initial. Legacy values | it is one of those | DV | Only for a colour that cannot be a `var()`; the value is the designer's |
| `colorAlpha.ts` | Alpha for a computed colour: `parseRgb`, `parseRgba`, `toRgba`, `withAlpha`, `withHexAlpha` | a chart or canvas colour needs transparency. Never build an `rgba(…)` string by hand | T and DV | With its test, through the colour coordinator |
| `contrast.ts` | WCAG contrast at run time: `relativeLuminance`, `over`, `contrastRatio`, `readableOn` | a chart picks a readable text over a fill it computed | T and DV | With its test, through the colour coordinator |
| `themeMode.ts` | The one read and watch of the theme: `isDarkTheme`, `onThemeClassChange`; the Designer Lab's signal `onChartColorsChange`, `notifyChartColorsChange` (C4) | it draws by theme (charts, canvas) and redraws on a change | T and DV | Never read `document.documentElement.classList` yourself (`src/themeModeReads.gate.test.ts`) |
| `themePair.ts` | `ThemePair` (`{light, dark}`) and `themed(pair, dark)`, the one place that picks between them | it reads a pair of the chart tables | T and DV | — |

## The palette

The values below come from `tokens.css` (16/10/2026), copied by a script and checked against it. **If they ever
differ, `tokens.css` wins**, and whoever changes a role (T) updates this table in the same commit. Every utility takes
an opacity: `bg-lf-card/90`, `border-lf-on-brand/20`.

### Surfaces

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-app` | `bg-lf-app` | `#f3f5f3` | `#0d1110` | Behind the app shell: the background of every page inside the app. The same colour as `page` since round 2 |
| `--lf-surface-page` | `bg-lf-page` | `#f3f5f3` | `#0d1110` | A page outside the shell: login, sign-up, welcome, error, offline, splash, server unreachable |
| `--lf-surface-card` | `bg-lf-card` | `#fafbfa` | `#151b19` | Cards, modals, menus, dropdowns, popovers |
| `--lf-surface-panel` | `bg-lf-panel` | `#e8ece9` | `#1b2421` | The secondary surface: panels, table heads, boxes inside a card, the track of a segmented control, a secondary button, inline code |
| `--lf-surface-field` | `bg-lf-field` | `#ffffff` | `#0f1413` | The inside of an input, a select trigger, a textarea |
| `--lf-surface-hover` | `hover:bg-lf-hover` | `#e8ece9` | `#1b2421` | A row or an item under the pointer, on a card or a page. It equals `panel`: on a panel, hover with `hover:bg-lf-neutral` (open question 3) |
| `--lf-surface-neutral` | `bg-lf-neutral` | `#d8e0dc` | `#222c28` | Neutral fills: progress tracks, skeletons, neutral chips; the hover of a control that sits on a panel |
| `--lf-surface-logo` | `bg-lf-logo` | `#ffffff` | `#ffffff` | The tile behind the logo: white in both themes, on the green too (N1) |

### Text

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-text-primary` | `text-lf-primary` | `#1c2420` | `#edf2f0` | Body text, titles, values. Set it on the root of every component (rule 1) |
| `--lf-text-secondary` | `text-lf-secondary` | `#4a5550` | `#9ba8a2` | Labels, subtitles, the caption of a value, the text of a secondary button |
| `--lf-text-muted` | `text-lf-muted`; `bg-lf-muted` for the dot | `#616d67` | `#7f8c87` | Hints, timestamps, inactive icons, disabled text, the «inactive» status dot (Q5) |
| `--lf-text-placeholder` | `placeholder:text-lf-placeholder` | `#616d67` | `#7f8c87` | The placeholder of a field: the muted text |

### Borders

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-border-subtle` | `border-lf-subtle`, `divide-lf-subtle` | `#d8e0dc` | `#222c28` | Borders and dividers of cards, tables and sections; the edge of inline code |
| `--lf-border-raised` | `border-lf-raised` | `#d8e0dc` | `#2e3b36` | The border of a surface that floats: modal, dropdown, menu, popover, the login card (N3) |
| `--lf-border-input` | `border-lf-input` | `#7e8984` | `#606f6a` | The border of a field or a control at rest, 3:1 on every surface (D-T18); the edge of a switch knob turned off |
| `--lf-border-input-hover` | `hover:border-lf-input-hover` | `#616d67` | `#7f8c87` | The border of a field under the pointer: the muted text colour (D-T18). `focus:border-lf-focus` wins over it |

### Brand and action

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-brand` | `bg-lf-brand` | `#1b4334` | `#1b4334` | The brand green as a surface: the header of the login card. The sidebar has a family of its own (`bar`), on the same green |
| `--lf-on-brand` | `text-lf-on-brand` | `#fafbfa` | `#edf2f0` | Text and icons on the brand green; `/70` for its secondary text, `/20` for its borders, `/10` for a hover |
| `--lf-action` | `bg-lf-action` | `#1b4334` | `#215240` | The primary button: the action the view is for |
| `--lf-action-hover` | `hover:bg-lf-action-hover` | `color-mix(in oklab, #1b4334 70%, #236b4d)` | `#28634e` | The primary button under the pointer (provisional in light: toward the focus green) |
| `--lf-on-action` | `text-lf-on-action` | `#fafbfa` | `#edf2f0` | Text and icons on the primary button |

### Focus, links and selection

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-focus` | `focus-visible:outline-lf-focus`, `focus:ring-lf-focus`, `focus:border-lf-focus` | `#236b4d` | `#429e79` | Keyboard focus, and the border of a focused field, on every neutral surface (3:1). On the sidebar, `--lf-bar-focus` |
| `--lf-link` | `text-lf-link` | `#236b4d` | `#429e79` | Links, the active item inside a page, accent icons. The focus green: the designer's «Focus, link attivi» |
| `--lf-selected` | `bg-lf-selected` | `color-mix(in oklab, #236b4d 12%, transparent)` | `color-mix(in oklab, #429e79 12%, transparent)` | A selected or highlighted row, option, item or date range: a quiet tint of the focus green |
| `--lf-checked` | `bg-lf-checked` | `#236b4d` | `#429e79` | A selected control: checkbox, radio, switch turned on, selected day or preset, active segment (D-T16) |
| `--lf-on-checked` | `text-lf-on-checked` | `#fafbfa` | `#151b19` | The mark on a checked fill: the tick, the dot, the number of the selected day |
| `--lf-tour-glow` | `ring-lf-tour-glow`, or `var(--lf-tour-glow)` in a shadow | `color-mix(in oklab, #236b4d 40%, transparent)` | `color-mix(in oklab, #429e79 40%, transparent)` | The glow of the guided tour around the element it shows (Q9) |

### States

Four families: `success`, `warning`, `danger`, `info`. **Each one comes as a set**, never split:
- `text-lf-X` for a state as text or icon;
- `bg-lf-X-soft border-lf-X-line text-lf-X-on-soft` for an alert, a banner, a badge, a row in that state;
- `bg-lf-X text-lf-on-status` for a solid fill (a toast, a solid badge).

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-success` | `text-lf-success`, `bg-lf-success` | `#18794e` | `#5ed69a` | A success as text or icon (✓, «Strong»), or its solid fill |
| `--lf-success-soft` | `bg-lf-success-soft` | `#e6f4ed` | `#13261e` | The tint of a success alert, badge or row |
| `--lf-success-line` | `border-lf-success-line` | `#b8dfca` | `#1f4435` | Its border |
| `--lf-success-on-soft` | `text-lf-success-on-soft` | `#145937` | `#86efac` | Text on the success tint |
| `--lf-warning` | `text-lf-warning`, `bg-lf-warning` | `#ae4e00` | `#f59e0b` | A warning as text or icon, or its solid fill; the «modified» state of a setting (Q4) |
| `--lf-warning-soft` | `bg-lf-warning-soft` | `#fef3c7` | `#291e0c` | The tint of a warning alert, badge or row |
| `--lf-warning-line` | `border-lf-warning-line` | `#fde68a` | `#54380e` | Its border |
| `--lf-warning-on-soft` | `text-lf-warning-on-soft` | `#92400e` | `#fcd34d` | Text on the warning tint |
| `--lf-warning-hover` | `hover:bg-lf-warning-hover` | `#92400e` | `#d97706` | A solid warning button under the pointer (Q3) |
| `--lf-danger` | `text-lf-danger`, `bg-lf-danger` | `#c82838` | `#ff7a86` | An error as text, icon or border (an invalid field), or its solid fill. A softer red in dark (D-T25) |
| `--lf-danger-soft` | `bg-lf-danger-soft` | `#ffe5e5` | `#2a1417` | The tint of an error alert, badge or row |
| `--lf-danger-line` | `border-lf-danger-line` | `#fecaca` | `#581c24` | Its border |
| `--lf-danger-on-soft` | `text-lf-danger-on-soft` | `#991b1b` | `#fca5a5` | Text on the error tint |
| `--lf-danger-solid` | `bg-lf-danger-solid` | `#c82838` | `#e1284f` | A solid destructive button, «Delete account» (Q3): it carries white text, which `danger` cannot in dark |
| `--lf-danger-hover` | `hover:bg-lf-danger-hover` | `#a81f2d` | `#d51c42` | That button under the pointer |
| `--lf-on-danger-solid` | `text-lf-on-danger-solid` | `#ffffff` | `#ffffff` | Its white text, at rest and hovered |
| `--lf-info` | `text-lf-info`, `bg-lf-info` | `#155eef` | `#3f86fa` | Information as text or icon, or its solid fill |
| `--lf-info-soft` | `bg-lf-info-soft` | `#deedff` | `#131f33` | The tint of an info alert, badge or row |
| `--lf-info-line` | `border-lf-info-line` | `#bfdbfe` | `#1e3a5f` | Its border |
| `--lf-info-on-soft` | `text-lf-info-on-soft` | `#1e40af` | `#93c5fd` | Text on the info tint |
| `--lf-on-status` | `text-lf-on-status` | `#fafbfa` | `#151b19` | Text on a solid state fill (toasts, solid badges) and on a solid warning or donation button hovered |

### Gain, loss and donation

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-gain` | `text-lf-gain` | `#18794e` | `#5ed69a` | A positive signed figure: P&L, return, a price that went up (rule 7). Today the value of `success` |
| `--lf-loss` | `text-lf-loss` | `#c82838` | `#ff7a86` | A negative signed figure. Today the value of `danger` |
| `--lf-donate` | `text-lf-donate` | `#ae4e00` | `#f59e0b` | The donation link «Offrimi un caffè»: the warm amber of `warning` |
| `--lf-donate-hover` | `hover:text-lf-donate-hover` | `#92400e` | `#d97706` | The donation link under the pointer (Q3) |

### The tooltip, an inverted surface

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-inverse` | `bg-lf-inverse` | `#1c2420` | `#edf2f0` | The tooltip: dark in the light theme, light in the dark theme (the primary text colour) |
| `--lf-text-on-inverse` | `text-lf-on-inverse` | `#fafbfa` | `#151b19` | The text of a tooltip (the card colour) |
| `--lf-warning-on-inverse` | `text-lf-warning-on-inverse` | `#f59e0b` | `#ae4e00` | A warning inside a tooltip: the other theme's warning (Q10, rule 6) |
| `--lf-danger-on-inverse` | `text-lf-danger-on-inverse` | `#ff7a86` | `#c82838` | An error inside a tooltip: the other theme's danger |
| `--lf-info-on-inverse` | `text-lf-info-on-inverse` | `#3f86fa` | `#155eef` | Information, links and formulas inside a tooltip: the other theme's info |
| `--lf-text-muted-on-inverse` | `text-lf-muted-on-inverse` | `#7f8c87` | `#616d67` | Muted text inside a tooltip: the other theme's muted text |

### Backdrops and shadows

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-overlay` | `bg-lf-overlay` | `color-mix(in oklab, #0d1110 60%, transparent)` | `color-mix(in oklab, #0d1110 60%, transparent)` | The backdrop of a modal and of the guided tour: the dark page at 60 %, in both themes (Q13) |
| `--lf-shadow-raised` | `shadow-lf-shadow` | `color-mix(in oklab, #0d1110 25%, transparent)` | `color-mix(in oklab, #0d1110 50%, transparent)` | The shadow colour of a floating surface, beside a size: `shadow-xl shadow-lf-shadow` (Q8) |
| `--lf-shadow-card` | `shadow-lf-shadow-card` | `color-mix(in oklab, #0d1110 7%, transparent)` | `color-mix(in oklab, #0d1110 40%, transparent)` | The shadow colour of a card on a page: `shadow-sm shadow-lf-shadow-card` (provisional in dark) |

### The shell: sidebar and header

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-header` | `bg-lf-header` | `#edf0ee` | `#111615` | The app header, desktop and mobile: a step darker than the page in light, lighter in dark (D-T23). Bottom border `border-lf-subtle`; its controls keep their page look |
| `--lf-surface-bar` | `bg-lf-bar` | `#1b4334` | `#1b4334` | The sidebar, green in both themes, desktop and mobile (D-T17), with no right edge (D-T23) |
| `--lf-bar-border` | `border-lf-bar-line` | `#265946` | `#265946` | Dividers inside the sidebar |
| `--lf-bar-text` | `text-lf-bar-text` | `#cfe0d8` | `#cfe0d8` | Inactive items, their icons, secondary information |
| `--lf-bar-text-muted` | `text-lf-bar-muted` | `#a0bcaf` | `#a0bcaf` | The version, the e-mail under the name |
| `--lf-bar-hover` | `hover:bg-lf-bar-hover` | `#21503e` | `#21503e` | An inactive item under the pointer |
| `--lf-bar-active-bg` | `bg-lf-bar-active` | `#285e49` | `#285e49` | The active item |
| `--lf-bar-active-text` | `text-lf-on-bar-active` | `#ffffff` | `#ffffff` | The text and icon of the active item; the username |
| `--lf-bar-indicator` | `border-lf-bar-indicator` | `#52c493` | `#52c493` | The mark on the left of the active item (`border-l-4`) |
| `--lf-bar-logout-bg` | `bg-lf-bar-logout` | `#153529` | `#153529` | The logout button |
| `--lf-bar-logout-hover` | `hover:bg-lf-bar-logout-hover` | `#21503e` | `#21503e` | The logout button under the pointer |
| `--lf-bar-focus` | `focus-visible:outline-lf-bar-focus` | `#52c493` | `#52c493` | Keyboard focus on the green, where the page's `--lf-focus` would reach 1.73:1 |
| `--lf-bar-success` | `text-lf-bar-success` | `#5ed69a` | `#5ed69a` | A success on the green (the connection security): the dark theme's bright state, in both themes (D-T26) |
| `--lf-bar-warning` | `text-lf-bar-warning` | `#fbbf24` | `#fbbf24` | A warning on the green |
| `--lf-bar-danger` | `text-lf-bar-danger` | `#ff7a86` | `#ff7a86` | A danger on the green (D-T25) |

The installed app's title bar (`<meta name="theme-color">`) continues the sidebar: `#1b4334` in both themes (N2,
D-T24). Three static copies write it (`src/app.html`, `src/lib/stores/app/themeStore.ts`, `static/offline.html`), and
the splash and the offline page copy a few roles too: `src/themeColorMeta.gate.test.ts` keeps them equal to
`tokens.css`. Change a role they copy, and change the copy in the same commit.

### Controls and special surfaces

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-switch-off` | `bg-lf-switch-off` | `#cbd4d0` | `#2c3834` | The track of a switch turned off: never green (Q2). Turned on, the track is `bg-lf-checked` |
| `--lf-switch-knob-off` | `bg-lf-switch-knob-off` | `#ffffff` | `#9ba8a2` | The knob of a switch turned off, with `border border-lf-input`: in light the edge is what makes the switch readable |
| `--lf-switch-knob-on` | `bg-lf-switch-knob-on` | `#ffffff` | `#ffffff` | The knob of a switch turned on, over `bg-lf-checked` |
| `--lf-terminal-bg` | `bg-lf-terminal` | `#0d1110` | `#0d1110` | A terminal block, dark in both themes (Q6). Inline code is not a terminal: `bg-lf-panel border-lf-subtle text-lf-primary` |
| `--lf-terminal-border` | `border-lf-terminal-line` | `#222c28` | `#222c28` | The terminal's border |
| `--lf-terminal-text` | `text-lf-on-terminal` | `#edf2f0` | `#edf2f0` | The terminal's text |
| `--lf-terminal-prompt` | `text-lf-terminal-prompt` | `#36d399` | `#36d399` | The prompt and the commands |
| `--lf-terminal-comment` | `text-lf-terminal-comment` | `color-mix(in oklab, #edf2f0 60%, #0d1110)` | `color-mix(in oklab, #edf2f0 60%, #0d1110)` | Comments (`# Docker`); provisional |
| `--lf-mark-bg` | `bg-lf-mark` | `#fde68a` | `#78350f` | A highlighted search result, `<mark>` (Q7) |
| `--lf-mark-text` | `text-lf-on-mark` | `#1c2420` | `#fef3c7` | The text of a highlighted result |
| `--lf-mark-line` | `border-lf-mark-line`, `inset-ring-lf-mark-line` | `transparent` | `#b45309` | Its edge: none in light, amber in dark. An inset ring does not move the text around it |
| `--lf-ai` | `text-lf-ai`, `bg-lf-ai` | `#6d28d9` | `#a78bfa` | The AI accent (Q11): the AI Export's icons and choices; `bg-lf-ai` is a solid AI button, with `text-lf-on-ai` |
| `--lf-ai-soft` | `bg-lf-ai-soft` | `#f3e8ff` | `#1e1b2e` | The AI tint |
| `--lf-ai-line` | `border-lf-ai-line` | `#ddd6fe` | `#3b3054` | The border of the AI tint |
| `--lf-on-ai` | `text-lf-on-ai` | `#ffffff` | `#151b19` | Text on a solid AI fill; provisional |
| `--lf-art-hill-1` | — | `color-mix(in oklab, #9caf9c 25%, transparent)` | `#16221d` | The login illustration (`src/lib/components/ui/AnimatedBackground.svelte`), first hill. No utility: its `<style>` reads it with `var()`, and the alpha is the strength of the layer (N6) |
| `--lf-art-hill-2` | — | `color-mix(in oklab, #9caf9c 18%, transparent)` | `#121c18` | The login illustration, second hill |
| `--lf-art-hill-3` | — | `color-mix(in oklab, #9caf9c 12%, transparent)` | `#0f1714` | The login illustration, third hill |
| `--lf-art-line` | — | `color-mix(in oklab, #1b4334 30%, transparent)` | `#3b5249` | The lines of the login illustration (no dots on them, N6) |

## The rules

### 1. Roles only

- A component writes only role utilities. Never a palette class (`bg-white`, `text-gray-500`, `bg-libre-green`), never a
  hand-written colour (hex, `rgb()`, `hsl()`, `oklch()`, a colour name) in markup, script or `<style>`.
- In a `<style>` block or a `style` attribute: `var(--lf-…)`, or `color-mix(in oklab, var(--lf-…) 70%, transparent)` for
  a translucent role. An arbitrary utility only reads roles: `shadow-[0_0_0_5px_var(--lf-tour-glow)]`.
- **The text role on the component's root** (`text-lf-primary`): in dark, `body` still passes the legacy text colour
  down until the clean-up (B6).
- **Every `border` names its role** (`border border-lf-subtle`): Tailwind 4 draws an unnamed border in `currentColor`.
- **Class names stay whole literals.** Never `'bg-lf-' + x`: Tailwind would not generate it, and the gate could not
  see it.
- **The gate:** `src/themeRoles.gate.test.ts`. The ratchet (R1–R5: a new file starts with no legacy class and no colour
  literal, an existing one only loses them) and the grammar (G1 no `dark:` on a role, G2 no unknown role, G3 no mixed
  element, G4 no arbitrary colour that is not a role). Run it alone with `node frontend/scripts/theme/theme-roles.mjs
  --check`, together with the Vitest file of the gate: the file checks more than the command line.

### 2. No `dark:` on a role

- A role already changes value with the theme: a `dark:` half is wrong (G1). If something must look different in dark,
  that is a role's value: ask for it («Asking for a new role»).
- Never read or watch the theme yourself: `isDarkTheme()` and `onThemeClassChange()` of `themeMode.ts`.

### 3. One element, one colour language (G3), and so is a chain of classes

- An element is all roles or all legacy: never a role utility and a palette class on the same element, or in the same
  class string. `app.css` exempts every element carrying a `-lf-` class from its legacy dark remap, so a mixed element
  keeps half of its old colours in dark.
- **A class prop** (`class`, `className`, `contentClass`, `triggerClass`, `fieldClass`, `tab.className`) puts the
  caller's classes on the component's element, beside its own. The caller passes layout (`mb-4`, `shrink-0`), not
  colours. A caller that needs another colour gets a variant prop (`variant="danger"`), not a colour through the chain.
- **A colour in a component's `<style>` beats every utility**, a caller's included: `<style>` sits outside Tailwind's
  layers. Keep in the markup the colours a caller may override.

### 4. One property, one ternary (the Tailwind 4 order)

- Two base utilities that set the same property on one element come out **sorted by name**, and the later one wins:
  their order in the `class` string does not count. `border-lf-input`, always on, beat `border-lf-focus`, set only while
  open, and an open select lost its focus border.
- So the idle and the state colour of one property are the two branches of **one** ternary, and the idle `hover:` sits
  in the idle branch: `{open ? 'border-lf-focus' : 'border-lf-input hover:border-lf-input-hover'}`.
- Variants (`hover:`, `focus:`, `aria-*:`) come after the base utilities and add specificity. A state that must beat a
  colour the caller passes is a variant: `aria-invalid:border-lf-danger`.
- Details: devWiki
  [`problems/tailwind4-same-property-utilities-sorted-by-name`](../../../../LibreFolio_devWiki/wiki/problems/tailwind4-same-property-utilities-sorted-by-name.md).

### 5. Contrast: the WCAG minimums, in both themes

- **Text 4.5:1** (WCAG 1.4.3). **3:1 for what is not text** (WCAG 1.4.11): the boundary of a field, a focus ring, a
  selected fill, a mark.
- The roles keep these minimums by construction, **on the pairs the gate measures**: `CONTRAST_PAIRS` in
  `src/themeTokens.gate.test.ts`, in both themes. `KNOWN_EXCEPTIONS` is empty, and an entry needs the designer's
  reason and its date.

| Foreground | On | Minimum |
|---|---|---|
| `text-primary`, `text-secondary`, `text-muted`, `text-placeholder` | `app`, `page`, `header`, `card`, `panel`, `field` | 4.5 |
| `link` | `app`, `page`, `card`, `panel` | 4.5 |
| `success`, `warning`, `danger`, `info` | `app`, `page`, `header`, `card`, `panel`, `field` | 4.5 |
| `X`, `X-on-soft`, `text-muted`, `text-primary` | the tint `X-soft` of each state X | 4.5 |
| `donate` | `app`, `page`, `header`, `hover` | 4.5 |
| `on-brand` | `brand`, the sidebar | 4.5 |
| `on-action` | `action`, `action-hover` | 4.5 |
| `on-status` | `success`, `warning`, `danger`, `info`, `warning-hover` | 4.5 |
| `on-danger-solid` | `danger-solid`, `danger-hover` | 4.5 |
| `on-checked` | `checked` | 4.5 |
| `text-on-inverse` and the four `-on-inverse` | `inverse` | 4.5 |
| `mark-text` | `mark-bg` | 4.5 |
| `terminal-text`, `terminal-prompt`, `terminal-comment` | `terminal-bg` | 4.5 |
| `ai` | `ai-soft`, `card`, `panel` | 4.5 |
| `on-ai` | `ai` | 4.5 |
| `border-input`, `border-input-hover` | `app`, `page`, `header`, `card`, `panel`, `field` | 3 |
| `focus` | `app`, `header`, `card`, `panel`, `field` | 3 |
| `checked` | `card`, `panel`, `field` | 3 |
| `switch-knob-on` | `checked` | 3 |
| `bar-text` | the sidebar, its hover, the active item, the logout button and its hover | 4.5 |
| `bar-text-muted`, `bar-warning` | the sidebar and its hover | 4.5 |
| `bar-active-text` | the active item, the sidebar, its hover | 4.5 |
| `bar-indicator` | the sidebar, the active item | 3 |
| `bar-focus` | the sidebar, its hover, the active item, the logout button | 3 |
| `bar-success`, `bar-danger` | the sidebar and its hover | 3 |

- **A pair not in the list is not promised:** a state on another state's tint, any text on `selected` or on
  `neutral`, a text on a translucent colour. If your design needs one, ask for the pair to be measured and added.
- **What no pair can hold:** the switch turned off is recognised by the edge of its knob, and a translucent tint has no
  background to measure on. Both are checked by hand.

### 6. Inside a tooltip, the other theme's colour (Q10)

- The tooltip inverts its surface (`bg-lf-inverse text-lf-on-inverse`), so a coloured text inside it takes the colour
  of the other theme: `text-lf-warning-on-inverse`, `text-lf-danger-on-inverse`, `text-lf-info-on-inverse`,
  `text-lf-muted-on-inverse`. **Never `text-lf-danger` inside a tooltip:** on the inverted surface it fails.
- The gate keeps each `--lf-X-on-inverse` equal to the other theme's `--lf-X`.
- `src/lib/components/ui/feedback/Tooltip.svelte` draws the surface, the text and the raised shadow. HTML built for a
  tooltip (`src/lib/utils/currency/fxConversionHelper.ts`, `src/lib/components/assets/providerProbe.ts`) uses the same
  roles in its `style`, as `var(--lf-…-on-inverse)`.

### 7. Gain and loss are not success and error

- `text-lf-gain` and `text-lf-loss`: the sign of a financial figure, such as a P&L, a return, a price change or the
  timing effect. Take them from `SIGN_TEXT` and `SIGN_BAR` of `toneClasses.ts`.
- `success` and `danger`: the outcome of an operation or a check, such as saved, failed or invalid.
- Today they share their values. They stay separate roles so that the designer can change one without the other:
  never use one for the other.
- Neither colours a category of a chart (GR2).

### 8. Focus is always visible

- Every interactive element shows the keyboard focus:
  - buttons, links, items: `focus-visible:outline-lf-focus`;
  - fields: `focus:border-lf-focus` with `focus:ring-lf-focus`;
  - on the green sidebar: `focus-visible:outline-lf-bar-focus`.
- Never `outline-none` without one of them. The focus colour reaches 3:1 on every neutral surface (rule 5).
- Focus wins over hover: write it as a `focus:` variant, which comes after `hover:` (rule 4).

### 9. Floating surfaces: the raised border and the shadow (N3, Q8)

- A modal, a dropdown, a menu, a popover: `bg-lf-card border border-lf-raised`, a shadow size and `shadow-lf-shadow`.
  A card on a page: `shadow-lf-shadow-card`.
- **A modal uses `src/lib/components/ui/modals/ModalBase.svelte`**: the backdrop `bg-lf-overlay`, the card, the 1 px
  raised border, the raised shadow. It frames every modal the same way; do not draw a second frame inside it.
- **A modal that needs another border colour** (the red one of `AssetCurrencyChangeModal`) needs a variant of
  `ModalBase`, not a colour in `contentClass`: a role sorting before `border-lf-raised` would lose (rule 4).

### 10. State for tests, not colours

- Publish the state as `data-state` or `aria-*` (`aria-invalid`, `aria-selected`, `aria-checked`, `data-active`) and
  let tests read it. Never select or assert by a colour class: the classes change whenever the colours do.
- A colour an E2E test must measure is compared with the role resolved in the page, never with a hex: see
  `expectComputedBorderColor` in `e2e/transactions/transactions-modals.spec.ts`.

### 11. Categories outside the charts

- Asset types and sectors in a badge, a chip or an icon take their colour from the shared helpers: the badges of
  `src/lib/utils/assetTypes.ts` and `KIND_TONES` of `toneClasses.ts`. They are categorical, still palette classes until the
  categorical roles come: reuse them, never copy their classes.
- Violet, indigo, teal, cyan, pink, fuchsia and lime are categories, never states. The AI violet is not a category: it
  has the `ai` roles (Q11).

## Charts

A chart draws on a canvas from options built in TypeScript, so its colours are values, taken from `lib/theme/` at each
draw. Owner: DV.

- **Categories, one colour per key (GR1):** `categoryColor(kind, key, dark)` of `chartCategories.ts`, never by rank.
  - An asset type or a sector keeps its colour in the pie and the history, in the legend and the tooltip, in every
    portfolio, broker and period.
  - A subtype resolves to its family with `assetTypeFamily()` (`src/lib/utils/assetTypes.ts`), then takes a shade of the
    family's colour: `familyShade()` of `chartShades.ts`, with the poles of `shadePoles(dark, card)` (GR4). Light theme:
    toward white at 15, 30 and 45 %; dark theme: toward the card at 18, 32 and 45 %.
- **No semantic red or green among the categories (GR2).** The brand sage colours the cash alone (`Liquidity`, GR3):
  `#2D6A54` in light and `#429E79` in dark. «Unclassified» is a fog grey.
- **Categories without a key (GR5):**
  - the owners of the semi-donut and the broker lines of the Growth chart: `sequenceColor()` over `CATEGORY_SEQUENCE`,
    the first eight asset types; or `growthBrokerColor()`;
  - the countries of the geography history: `KEYLESS_SEQUENCE`, the fourteen sectors;
  - past the end of a sequence, the same colours one shade further, never a silent repeat;
  - the world maps: `GEO_CHOROPLETH_SCALE` (`chartPalettes.ts`);
  - the correlation matrix: `danger` ↔ `panel` ↔ `info`.
- **Roles in a chart:** `chartRoles(dark, scope)` of `roleColors.ts` reads `--lf-*` on the chart's own element at each
  draw: `color(role)`, and `readableText(background)` for a label over a fill.
- **Neutrals and series not on roles yet:** the named pairs of `chartTheme.ts`, read with `themed(pair, dark)`. Their
  values are legacy on purpose, until B4 moves them onto roles. Computed scales are in `chartColorScales.ts`, alpha in
  `colorAlpha.ts`, contrast in `contrast.ts`.
- **Redraw** when the theme changes (`onThemeClassChange`) and when the Designer Lab edits a colour
  (`onChartColorsChange`, contract C4).
- **Never a hex in a chart component, and never a category colour changed locally:** the designer's list is under
  review (open question 1).
- **A colour the user picked stays his:** only the proposed defaults follow the palette (signals, DV decision 6).

## Asking for a new role

**Only T creates roles** (D-T28). Most needs already have one: check the palette and `toneClasses.ts` first.

1. **If none fits, do not write a colour.** Ask T through the colour coordinator, with:
   - the element and what it means;
   - where it is (file, screen), in both themes;
   - why no role fits;
   - a value built from the designer's values, or the question for her.
2. **T adds it, in one commit:**
   - the variable in the light and the dark blocks of `tokens.css`, or in the derived block as a `var()` or a
     `color-mix()` of other roles, with a comment naming its source (the designer's value, a decision, or
     «provisional»);
   - its utility in `@theme inline`, if components use it as a class;
   - its contrast pairs in `CONTRAST_PAIRS`, at 4.5:1 for text and 3:1 for the rest;
   - its stand-in in `roleColors.ts`, if a chart reads it, and the static copies, if the splash, the offline page or
     the title bar paint it;
   - its row in this skill's palette.
3. **Until it exists,** the element stays as it is, legacy and whole. A migration batch may take the nearest role,
   noted «da rivedere» in its plan (D-T27). Never a hand-written colour.
4. **The value of an existing role** changes only through T, on a decision of the developer or the designer, with the
   gates green. A pair left under its minimum needs the designer's reason and its date in `KNOWN_EXCEPTIONS`.

## Decisions

The sources:
- **T:** the decisions table of the plan
  [`T-tokensTheme/plan-phase01TokensTheme.prompt.md`](../../../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/T-tokensTheme/plan-phase01TokensTheme.prompt.md);
- **the designer's round 2:**
  [`designer-feedback/2026-10-15-round2-palette/README.md`](../../../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/designer-feedback/2026-10-15-round2-palette/README.md),
  with its analysis `analisi.md`;
- **the programme:**
  [`plan-phase00ColorSystemThemeLab.prompt.md`](../../../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/plan-phase00ColorSystemThemeLab.prompt.md);
- **DV:** [`DV-chartColors/plan-phase00ChartColors.prompt.md`](../../../../LibreFolio_developer_journal/Release_2/Phase_1/10_colorSystem/DV-chartColors/plan-phase00ChartColors.prompt.md).

| Code | Decision | Source |
|---|---|---|
| D-T3 | One final solution: roles and semantic utilities, migrated in waves. Tailwind's scales and white are not repainted: what is not migrated stays visibly old (ratchet, gallery) | T |
| D-T4 | Names `--lf-<group>-<name>`, utilities `*-lf-<name>` through `@theme inline` | T |
| D-T5 | The designer's values in sRGB hex; derived roles with `color-mix(in oklab, …)`; a bridge to the charts (`roleColors.ts`) | T |
| D-T6 | Minimal contrast corrections (OKLCH lightness only), her value in a comment, for her to confirm | T |
| D-T7 | The splash, the offline page and the manifest's background take `page` | T |
| D-T8 | The gates: ratchet R1–R5, grammar G1–G4, contract C1–C4 | T |
| D-T16 | A selected control: fill `--lf-checked` (the focus green), mark `--lf-on-checked` (the card colour) | T |
| D-T17 | The designer's round 2 approved whole: green sidebar in both themes, explicit state tints, N1–N6, Q2–Q13, GR1–GR5 | T, round 2 |
| D-T18 | The field border stays at 3:1; under the pointer, the muted text colour | T |
| D-T23 | A neutral header (`--lf-surface-header`); the sidebar stays green, with no right edge | T |
| D-T24 | The title bar of the installed app stays `#1b4334` in both themes | T |
| D-T25, D-T26 | Dark theme: a softer red (`#ff7a86`) and green (`#5ed69a`); the solid red button unchanged; the sidebar's states aligned | T |
| D-T27 | Migration nights: a case no role covers takes the nearest role, noted «da rivedere» | T |
| D-T28 | Migrate first, refine later, one workstream per area; T is the only one who creates roles | programme |
| D-T29 | This skill, cited by the frontend instructions | programme |
| N2 | The title bar of the installed app: `#1b4334` in both themes | round 2 |
| N3 | A card that floats (login, modal, dropdown) has its own border: `--lf-border-raised` | round 2 |
| N5 | The corrected muted text, dark danger and dark info approved; the field border stays at 3:1 (D-T18) | round 2 |
| N6 | The login illustration: unchanged in light, a darker forest in dark, no dots on the lines | round 2 |
| Q2 | The switch turned off is never green: a track and a knob for each theme | round 2 |
| Q3 | Hover of the solid buttons: destructive, warning, donation | round 2 |
| Q4 | The «modified» state of the settings takes the warning roles | round 2 |
| Q5 | The «inactive» dot takes the muted text | round 2 |
| Q6 | Inline code on the panel; the terminal dark in both themes | round 2 |
| Q7 | `<mark>`: an amber tint, with an edge in dark | round 2 |
| Q8 | Shadows: modals and dropdowns at 25 % in light and 50 % in dark; the cards of a page at 6–8 % | round 2 |
| Q9 | The guided tour: a glow of the focus green at 40 %; its backdrop is the overlay | round 2 |
| Q10 | Inside a tooltip, the other theme's warning; extended to danger, info and the muted text (D-T27) | round 2 |
| Q11 | The AI violet: an accent of its own for the AI functions | round 2 |
| Q12 | The icons of the «About» tab: no rainbow, a `bg-lf-panel` badge, the icon in the focus green | round 2 |
| Q13 | The backdrop: `#0d1110` at 60 % in both themes | round 2 |
| GR1–GR5 | Charts: one colour per key; no semantic red or green; the cash in sage; the shades of a subtype; the other palettes follow | round 2, DV |

## Open questions for the designer (round 3): not decided

Until she answers, follow what is written here and do not decide them in a component.

1. **The chart colours.** Package `grafici-giro3-2026-10-15.zip` (in `LibreFolio_visual_review/package/`, outside the
   repository), points 2.1–2.9. Under review:
   - a definitive list of the category colours, and the pairs too close to tell apart (under ΔE00 10, listed by the
     distinguishability test of `chartCategories.test.ts`);
   - the category greens near the gain green: ΔE00 11.4 between the dark `#5ed69a` and `#2dd4bf`;
   - the shades of a full family, down to ΔE00 3.2–6.0;
   - the centre of the correlation matrix, the panel, at 1.1:1 on the card.

   Until then: `chartCategories.ts` as it is.
2. **Toasts and banners.** Package `toast-e-banner-2026-10-15.zip`: the toasts solid or soft, the 11 families of
   banners.
   - Today a toast is solid (`bg-lf-X text-lf-on-status`) and a banner sits on the tints (`-soft`, `-line`,
     `-on-soft`). In dark the banners are louder than the old ones, which had their text at 60 %.
   - No role covers the hover of a tint: the migration took `hover:bg-lf-X-line`.

   Until then: `STATUS_TONES` and `src/lib/components/ui/feedback/InfoBanner.svelte` as they are.
3. **`panel` equals `hover`.** `--lf-surface-hover` is `--lf-surface-panel` in both themes, so `hover:bg-lf-hover`
   shows nothing on a panel. Until then, on a panel, hover with `hover:bg-lf-neutral`: a secondary button is
   `bg-lf-panel hover:bg-lf-neutral`.
4. **The switch turned on.** 13 switches in 9 files, «on» today in the Libre green, emerald or amber; the palette says
   `bg-lf-checked` (D-T16). The switch lot of T waits for her answer. Until then, do not migrate an existing switch on
   its own. A new switch follows the Q2 rows of the palette and is reported to the colour coordinator.

**Values waiting for her confirmation** (backlog TC-8):
- the seven minimal contrast corrections of her round 2 (D-T6), each with her value in a comment of `tokens.css`: in
  light `--lf-warning`, `--lf-danger-soft`, `--lf-info-soft`, `--lf-bar-text-muted`; in dark
  `--lf-warning-on-inverse`, `--lf-danger-solid`, `--lf-danger-hover`;
- the roles marked «provisional»: `--lf-action-hover` in light, `--lf-on-ai`, `--lf-terminal-comment`,
  `--lf-shadow-card` in dark;
- the developer's dark red and green (D-T25, D-T26), extended to the states on the green sidebar;
- gain and loss kept apart from success and error; the switch turned off, recognised in light only by the edge of its
  knob.

The choices the night's migration made «da rivedere» are in the backlog, TC-10: the developer reviews them first.

## See also

- [`tokens.css`](../../../../frontend/src/lib/theme/tokens.css): the roles, with the source of each value in a comment.
- The skill [`theme-roles`](../theme-roles/SKILL.md): migrating a component, the class → role table, the baseline.
- The skill [`designer-lab-apply`](../designer-lab-apply/SKILL.md): the Designer Lab (debug builds) tunes the roles
  live; an export of it is applied with that skill.
- `.github/instructions/frontend.instructions.md`, «Design System»; the gates `src/themeRoles.gate.test.ts`,
  `src/themeTokens.gate.test.ts`, `src/themeColorMeta.gate.test.ts`, `src/themeComponentTokens.gate.test.ts`,
  `src/themeModeReads.gate.test.ts`.
- devWiki: [`decisions/colour-factorisation-at-pixel-parity`](../../../../LibreFolio_devWiki/wiki/decisions/colour-factorisation-at-pixel-parity.md),
  the factorisation of every colour into `lib/theme/` (workstream R).
