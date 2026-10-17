---
name: design-system
description: "Use this skill whenever you create or change any frontend UI (a component, a page, a dialog, a form, a badge, a chart), choose a colour, or touch the light or dark theme. It is the LibreFolio design system: the two themes «Stone and Sage» (light) and «Slate and Sage» (dark), every colour role and when to use it (both themes' values in palette.md), the shared colour folder frontend/src/lib/theme/, and the rules (roles only, no dark:, WCAG contrast, focus, tooltips, gain and loss, charts, how to get a new role). To convert legacy palette classes or touch the colour ratchet baseline, use theme-roles."
---

# LibreFolio design system: two themes, one palette, the rules

## The one idea

**You never pick a colour: you pick a role.** A role says what the colour is for: the card, the muted text, the
border of a field, an error. Each role has one value in the light theme and one in the dark theme, and it lives in
one place, [`tokens.css`](../../../../frontend/src/lib/theme/tokens.css). A component that uses roles follows both
themes, and every later change of the designer, with no `dark:` at all.

- **This skill:** what to use when you build or change UI. The themes, the shared colour folder, the roles by family,
  the rules, the decisions and what is still open.
- **[`palette.md`](palette.md), beside it:** every role, with its value in both themes and when to use it.
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
| `tokens.css` | The 102 roles of the two themes (a light, a derived and a dark block) and the `@theme inline` table that turns 98 of them into utilities (`bg-lf-card`…) | it draws any colour: as a utility, or `var(--lf-…)` in a `<style>` | T | Only T: «Asking for a new role» below |
| `components/media.css`, `table.css` | The last component tokens `--lf-cmp-<component>-<role>` (with `-dark` twins) that workstream R moved out of the `<style>` blocks at pixel parity, all categorical and waiting for the categorical roles: the image icon of `FileUploader` (`media.css`, 2 tokens, one colour per file type, AF-11) and the portfolio and benchmark row tints of `RiskReturnLevel` (`table.css`, 4, the designer's point 2.5). The dialogs, the files, the rest of the media and the tables, `CompactCashCell` included, read the roles | it is `FileUploader` or `RiskReturnLevel`; it loads its file with a side-effect import (`import '$lib/theme/components/table.css'`) | T | **Never a new token**: a new colour is a role. Migrating such a component replaces its `var(--lf-cmp-…)` with roles, deletes the tokens nobody reads any more, and deletes the file once it holds none (`src/themeComponentTokens.gate.test.ts`: each token defined once, imported where read, read by someone; every area file defines tokens) |
| `toneClasses.ts` | Whole class strings on the roles: signed figures (`SIGN_TEXT`, `SIGN_BAR`, `SIGN_BADGE`), diverging measures (`POLARITY_TONES`), states (`STATUS_TONES`: sync, PAC, toasts, import report and file sets, risk chips, data quality, live updates). The kinds told apart by hue alone (`KIND_TONES`, `STATUS_TONES.fileSet.combined`) are categorical, still palette classes | it colours a sign, a polarity, a state or a kind: it takes the entry by name; the threshold (`>= 0`, `> 0`) stays with the caller | T | A new named entry, a whole literal string of role utilities (never assembled), in the table of its meaning. An entry keeps its own name even when its classes equal another's |
| `chartCategories.ts` | The fixed colour of every asset type and sector, of the cash and of «unclassified», in both themes (GR1–GR3); the key sequences (GR5); `categoryColor`, `sequenceColor`, `lookupKey`, `isUnclassifiedCountry` | it draws a category: a chart, its legend, its tooltip | DV | A new key (a new asset type or sector) takes the designer's pair, one literal per line (C2), in her table order. Until then it reads as unclassified |
| `chartShades.ts` | The colour arithmetic of the category charts: `mixOklab`, `familyShade` (subtypes, GR4; rounds past a sequence, GR5), `shadePoles`, `scaleColor` | it draws a subtype, a sequence past its end, a value on a continuous scale | DV | A new mixing rule here, with its test. Never mix colours in a component |
| `chartPalettes.ts` | Two lists read as they are: `SIGNAL_DEFAULT_PALETTE` (a new signal's line; still one list for both themes, a default per theme is S9, waiting for Y4, Y8 and FE5c) and `GEO_CHOROPLETH_SCALE` (the world maps, GR5.1); and `growthBrokerColor` (the broker lines of the Growth chart), which reads `categoryColor` of the first eight asset types at each draw (TD-1b), so it follows the Designer Lab | it is one of those charts | DV | Through DV. A palette that colours categories goes through `chartCategories.ts` instead |
| `chartColorScales.ts` | Colours computed from a value: `treemapPnlColor` (a treemap tile by its P&L; a legacy formula, for the designer), `timingEffectColor` (`color-mix` over `--lf-gain`/`--lf-loss`) | it is one of those | T and DV | A new value → colour formula here, on the roles: `color-mix(in oklab, var(--lf-…) …)` for CSS, `chartRoles` for a canvas |
| `chartTheme.ts` | The colours of the ECharts charts, by meaning. **The neutrals on roles** (B4): `chartNeutrals(dark, scope)` reads, at each draw and on the chart's own element, the roles of the axes, grids and rules, labels, tooltip boxes, pointers and the gaps and rings in the card's colour, under the names of the tables they left. **The rest as named pairs**, `{light, dark}` or one string for both themes, with legacy values for the designer: series (prices, signals, income events, growth, performance, risk overlays, lots), gain and loss, states, the points of the risk-return chart, the map's land and highlight, divergences kept under two names | a neutral: `chartNeutrals`; a series, a state or a sign: `themed(pair, dark)` | DV | Reuse a name. A new neutral is a role in `chartNeutrals`, never a hex; a new series name only through DV; never a category: categories go to `chartCategories.ts` |
| `roleColors.ts` | The bridge from roles to whatever draws outside CSS: `chartRoles(dark, scope)` reads `--lf-*` on the drawing's own element, once per draw. `color(role)` is always sRGB, `#rrggbb` or `rgba()` for a translucent role (`--lf-selected`), whatever the canvas reports (`oklab()`, `oklch()` and `color(srgb …)` are converted, anything else stands in); `readableText(background)` picks the primary or the inverse text. Stand-ins equal to `tokens.css` answer where no stylesheet is loaded. **22 roles (`ChartRole`):** the card, panel, neutral, field and hover surfaces; the primary, secondary, muted and inverse texts; the subtle, raised and input borders; focus, selected, checked; the primary button and its text; the text on a state fill; warning, danger, info; the mark. **Read by** the charts — the neutrals (`chartNeutrals`), the GR4 shades and the broker lines (the card), the correlation scale (danger, panel, info), the PAC's ideal weight (the secondary text), `readableText` — and by the colours drawn outside CSS (`drawnColors.ts`, 18 of them) | a canvas chart or a drawn colour needs a role: take `chartRoles(dark, element)` once per draw and read `roles.color('--lf-…')` | DV | A missing role is added to `ChartRole` with its stand-in (an `rgba()` if translucent), which the parity test `roleColors.test.ts` keeps equal to `tokens.css`, channels and alpha, and **with its first reader**: production code must read every role through a literal `.color('--lf-…')` or `readableText` — a read through a variable or a loop is invisible — or the test's dead-role check fails. A role declared ahead of its reader waits in the test's `PENDING_READERS`, named with the batch that will read it; the list only shrinks: once the role is read, the test goes red until that batch removes the line. Ask through the colour coordinator |
| `drawnColors.ts` | Colours drawn outside CSS — handed to a canvas library or baked into an SVG data URL, where a `var(--lf-…)` cannot reach: the spreadsheet preview (cheetah-grid, `FilePreviewModal`: the rows the caller points at, the light theme's borders, the whole dark theme), the `LazyImage` placeholders, the initial of an uploader's avatar (`FilesTable`); no chart. **Each colour is a role**, read when the caller draws, through the `chartRoles` it takes once per drawing: 18 of the 22 roles of `roleColors.ts`, and `readableText` for the initial (AF, 17/10). In the light theme the spreadsheet keeps cheetah-grid's `MATERIAL_DESIGN` theme, with only its two borders on roles (AF-14). Provisional choices, point 35 of the designer's collection: the pointed rows on the mark, the initial by `readableText`, the light spreadsheet | it draws one of those: it takes `chartRoles(dark, element)` and passes it in | T | Only for a colour that cannot be a `var()`, and then as a role read through the caller's `chartRoles`, never a hex. A translucent role is composited over its surface (`over()`) where the library does not clear what it fills, as cheetah-grid does. A role `roleColors.ts` lacks comes through DV, as its row says |
| `colorAlpha.ts` | Alpha for a computed colour: `parseRgb`, `parseRgba`, `toRgba`, `withAlpha`, `withHexAlpha` | a chart or canvas colour needs transparency. Never build an `rgba(…)` string by hand | T and DV | With its test, through the colour coordinator |
| `contrast.ts` | WCAG contrast at run time: `relativeLuminance`, `over`, `contrastRatio`, `readableOn` | a chart picks a readable text over a fill it computed | T and DV | With its test, through the colour coordinator |
| `themeMode.ts` | The one read and watch of the theme: `isDarkTheme`, `onThemeClassChange`; the Designer Lab's signal `onChartColorsChange`, `notifyChartColorsChange` (C4) | it draws by theme (charts, canvas) and redraws on a change | T and DV | Never read `document.documentElement.classList` yourself (`src/themeModeReads.gate.test.ts`) |
| `themePair.ts` | `ThemePair` (`{light, dark}`) and `themed(pair, dark)`, the one place that picks between them | it reads a pair of the chart tables | T and DV | — |

## The roles, by family

What to reach for, family by family. **Every role, with its value in both themes and when to use it, is in
[`palette.md`](palette.md)**, beside this file and checked against `tokens.css`. Every utility takes an opacity:
`bg-lf-card/90`.

| Family | Utilities | What for |
|---|---|---|
| Surfaces | `bg-lf-app`, `bg-lf-page`, `bg-lf-card`, `bg-lf-panel`, `bg-lf-field`, `hover:bg-lf-hover`, `bg-lf-neutral`, `bg-lf-logo` | behind the shell; standalone pages (login, error, offline); cards, modals, menus; panels, table heads, secondary buttons, inline code; inside a field; hover on a card or a page; tracks, skeletons, hover on a panel; the logo tile |
| Text | `text-lf-primary`, `text-lf-secondary`, `text-lf-muted`, `placeholder:text-lf-placeholder` | body, titles, values (on every component's root); labels, captions; hints, inactive and disabled; placeholders |
| Borders | `border-lf-subtle`, `border-lf-raised`, `border-lf-input`, `hover:border-lf-input-hover` | dividers; floating surfaces (N3); fields at rest, 3:1; fields under the pointer (D-T18) |
| Brand and action | `bg-lf-brand` with `text-lf-on-brand`; `bg-lf-action`, `hover:bg-lf-action-hover`, `text-lf-on-action` | the login card header; the primary button |
| Focus, links, selection | `focus-visible:outline-lf-focus`, `focus:ring-lf-focus`, `focus:border-lf-focus`; `text-lf-link`; `bg-lf-selected`; `bg-lf-checked` with `text-lf-on-checked`; `ring-lf-tour-glow` | keyboard focus (rule 8); links and accents; a selected row, item or range; a selected control (D-T16); the guided tour's glow (Q9) |
| States, X = `success`, `warning`, `danger`, `info` | `text-lf-X`; `bg-lf-X-soft`, `border-lf-X-line`, `text-lf-X-on-soft`; `bg-lf-X` with `text-lf-on-status`, hovered `hover:bg-lf-X-hover`; `bg-lf-danger-solid`, `hover:bg-lf-danger-hover`, `text-lf-on-danger-solid` | a state as text or icon; an alert, banner, badge or row; a solid fill (toasts) and a solid button hovered (warning Q3; success and info provisional); a solid destructive button (Q3) |
| Gain, loss, donation | `text-lf-gain`, `text-lf-loss`; `bg-lf-gain-soft` with `text-lf-gain-on-soft`, `bg-lf-loss-soft` with `text-lf-loss-on-soft` (`SIGN_BADGE`); `text-lf-donate`, `hover:text-lf-donate-hover` | signed figures, never states (rule 7); a sign on a tint, a badge or a chip; the donation link |
| The tooltip | `bg-lf-inverse` with `text-lf-on-inverse`; `text-lf-warning-on-inverse`, `text-lf-danger-on-inverse`, `text-lf-info-on-inverse`, `text-lf-muted-on-inverse` | the inverted surface; coloured text inside it (Q10, rule 6) |
| Backdrops and shadows | `bg-lf-overlay` with `text-lf-on-overlay`; `shadow-lf-shadow`; `shadow-lf-shadow-card` | modal and tour backdrops (Q13), and text or icons on them (provisional); floating surfaces (Q8, rule 9); the cards of a page |
| The shell | `bg-lf-header`; `bg-lf-bar`, `text-lf-bar-text`, `text-lf-bar-muted`, `border-lf-bar-line`, `hover:bg-lf-bar-hover`, `bg-lf-bar-active`, `text-lf-on-bar-active`, `border-lf-bar-indicator`, `bg-lf-bar-logout`, `hover:bg-lf-bar-logout-hover`, `focus-visible:outline-lf-bar-focus`, `text-lf-bar-success`, `text-lf-bar-warning`, `text-lf-bar-danger` | the neutral header (D-T23); the green sidebar, one family in both themes (D-T17) |
| Controls and special surfaces | `bg-lf-switch-off`, `bg-lf-switch-knob-off`, `bg-lf-switch-knob-on`; `bg-lf-terminal`, `border-lf-terminal-line`, `text-lf-on-terminal`, `text-lf-terminal-prompt`, `text-lf-terminal-comment`; `bg-lf-mark`, `text-lf-on-mark`, `border-lf-mark-line`; `text-lf-ai`, `bg-lf-ai`, `bg-lf-ai-soft`, `border-lf-ai-line`, `text-lf-on-ai`; `var(--lf-art-hill-1)` and its siblings | the switch (Q2); the terminal (Q6); a highlighted result (Q7); the AI accent (Q11); the login illustration (N6), read in its `<style>` |

The installed app's title bar (`<meta name="theme-color">`) continues the sidebar, `#1b4334` in both themes (N2,
D-T24): static copies of it, and of a few roles, live outside `tokens.css` (see `palette.md`, «The shell»).

## The rules

### 1. Roles only

- A component writes only role utilities. Never a palette class (`bg-white`, `text-gray-500`, `bg-libre-green`), never a
  hand-written colour (hex, `rgb()`, `hsl()`, `oklch()`, a colour name) in markup, script or `<style>`.
- In a `<style>` block or a `style` attribute: `var(--lf-…)`, or `color-mix(in oklab, var(--lf-…) 70%, transparent)` for
  a translucent role. An arbitrary utility only reads roles: `shadow-[0_0_0_5px_var(--lf-tour-glow)]`.
- **The text role on the component's root** (`text-lf-primary`): in dark, `body` still passes the legacy text colour
  down until the clean-up (B6).
- **Every `border` names its role** (`border border-lf-subtle`): Tailwind 4 draws an unnamed border in `currentColor`.
- **A native field names its text and its placeholder:** an `<input>` of a text kind, a `<textarea>` and a `<select>`
  write `text-lf-primary` themselves, and `placeholder:text-lf-placeholder` when they have a placeholder, even where
  the parent already gives the colour. `app.css` colours the text and the placeholder of native fields in dark only
  while they carry no `-lf-` class: a field on roles falls back to the Tailwind preflight, the inherited colour and a
  placeholder at 50 % of it. Checkboxes, radios, ranges, file and colour pickers and the button kinds are exempt. The
  gate checks it (G6), but it cannot tell a ternary that gives a text role in each branch from one that gives it in
  one branch only: `{err ? 'text-lf-danger' : 'text-lf-primary'}`, never `{err ? 'text-lf-danger' : ''}`.
- **Class names stay whole literals.** Never `'bg-lf-' + x`: Tailwind would not generate it, and the gate could not
  see it.
- **The gate:** `src/themeRoles.gate.test.ts`. The ratchet (R1–R5: a new file starts with no legacy class and no colour
  literal, an existing one only loses them) and the grammar (G1 no `dark:` on a role, G2 no unknown role, G3 no mixed
  element, G4 no arbitrary colour that is not a role, G5 one property, one ternary (rule 4), G6 a native field names its
  text and placeholder roles). Run it alone with `node frontend/scripts/theme/theme-roles.mjs --check`, together with
  the Vitest file of the gate: the file checks more than the command line.

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
- **The gate checks it (G5):** two role utilities on one colour utility with the same variants, in one element, one of
  them always on — the static classes, a `{…}` that does not branch, or an UPPER_CASE string constant, the file's own or
  imported. A `class:` directive and a branching `{…}` or `${…}` are the conditions. Two conditions are never
  compared: they may exclude each other. What it cannot see: a class prop, a variable that is no UPPER_CASE constant,
  an object of a table such as `toneClasses.ts`.
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
| `gain`, `loss` | `app`, `page`, `header`, `card`, `panel`, `field` | 4.5 |
| `X`, `X-on-soft`, `text-muted`, `text-primary` | the tint `X-soft` of each state X, and of `gain` and `loss` | 4.5 |
| `donate` | `app`, `page`, `header`, `hover` | 4.5 |
| `on-brand` | `brand`, the sidebar | 4.5 |
| `on-action` | `action`, `action-hover` | 4.5 |
| `on-status` | `success`, `warning`, `danger`, `info`, and the hovers `success-hover`, `warning-hover`, `info-hover` | 4.5 |
| `on-danger-solid` | `danger-solid`, `danger-hover` | 4.5 |
| `on-checked` | `checked` | 4.5 |
| `text-on-inverse` and the four `-on-inverse` | `inverse` | 4.5 |
| `on-overlay` | the backdrop `surface-overlay`, composited over each of `app`, `page`, `header`, `card`, `panel`, `field`; the backdrop is the same in both themes | 4.5 |
| `link` | the tint `selected`, composited over `app`, `page`, `header`, `card`, `field`: **never over a `panel`** | 4.5 |
| `text-primary`, `text-secondary` | the tint `selected`, composited over `app`, `page`, `header`, `card`, `panel`, `field` | 4.5 |
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

- **A pair not in the list is not promised:** a state on another state's tint, any text on `neutral`, a text on a
  translucent colour. If your design needs one, ask for the pair to be measured and added.
- **On a selected row, option or chip** (`bg-lf-selected`), the text is `text-lf-primary`, `text-lf-secondary` or
  `text-lf-link`, and `link` never on a `selected` that lies on a `panel` (4.09:1 in dark). **The muted text, the
  statuses and the signs fail there** (3.84–4.48:1 on most surfaces; a lighter tint would not cure it): a muted caption
  of a row becomes `text-lf-secondary` while the row is selected or highlighted (TC-15). The selects of `ui/select` do
  it for every option, a caller's snippet included, with one rule in their `<style>`:
  `[data-highlighted='true'] :global(.text-lf-muted) { color: var(--lf-text-secondary) }` (`TreeSelect`: its active and
  hovered options); so does `DataTable` for its selected, highlighted and analyzed rows, HtmlCell cells included. A new
  list that tints its rows does the same, and publishes the state it keys on. A selected chip
  under the pointer: `hover:bg-lf-checked/20 hover:text-lf-primary` — the link green on that deeper tint falls to
  3.99:1.
- **A translucent background** is measured composited over the opaque surfaces it lies on (the `over` field of a pair,
  as the backdrop is).
- **What no pair can hold:** the switch turned off is recognised by the edge of its knob, and a translucent colour that
  is no role (`bg-lf-bar-danger/20`) has no role to compose. Both are checked by hand.

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
  timing effect. Take them from `SIGN_TEXT` and `SIGN_BAR` of `toneClasses.ts`; a sign on a tint (a badge, a chip)
  from `SIGN_BADGE`, on `bg-lf-gain-soft` and `bg-lf-loss-soft`.
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
- **A modal about a destructive or irreversible change** takes `tone="danger"` on `ModalBase`: a 2 px
  `border-lf-danger-line` frame, in one ternary with the raised border, published as `data-tone`. Never a border colour
  in `contentClass`: a role sorting before `border-lf-raised` would lose (rule 4).

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
    toward white at 15, 30 and 45 %; dark theme: toward the card at 18, 32 and 45 %. From the fourth subtype (the ETF
    family has six) the same steps go toward the opposite pole: `#1C2420` in light, white in dark (DV decision 2). Past
    the sixth the cycle starts again.
- **No green among the categories (round 3, §1.1).** No green, teal, olive, lime or greenish cyan in a type, a sector,
  a country or the map: green and red belong to gain and loss, the brand green to the primary actions. The cash
  (`Liquidity`) is a slate blue, `#3F628C` in light and `#639BC0` in dark; «unclassified» a blue-grey. The list is
  the designer's final one (17/10/2026): the pairs she kept between ΔE00 5 and 8 are named exceptions of the
  distinguishability test (`chartCategories.test.ts`), told apart by the legend and the tooltip.
- **Categories without a key (GR5):**
  - the owners of the semi-donut: by their key (the user id), never by the order of the data. Sorted by key, they take
    `sequenceColor()` over `CATEGORY_SEQUENCE`, the first eight asset types, with the poles of `shadePoles()` (§1.5);
  - the broker lines of the Growth chart: `growthBrokerColor()`, the same eight by the broker's index;
  - the countries of the geography history: `sequenceColor()` over `COUNTRY_SEQUENCE`, fourteen references to types
    and sectors (§1.4), so a country follows the colour of the category it shares it with;
  - a sequence names categories (`CategoryRef`), never colours: the tables are the only colours of the file (C2);
  - past the end of a sequence, the same colours one shade further, never a silent repeat.
- **Scales, values of their own (round 3, §1.6):**
  - the world maps: `GEO_CHOROPLETH_SCALE` (`chartPalettes.ts`), six blues, the same on the Dashboard, the asset page
    and the PAC; the countries with no data: `GEO_MAP_COLORS.land` (`chartTheme.ts`);
  - the correlation matrix: `CORRELATION_SCALE`, red ↔ grey-blue ↔ cobalt, no longer on roles; the value in a cell is
    pure black or pure white, whichever reads best (`CORRELATION_CELL_TEXT` through `readableOn()`).
- **The PAC's bars, «ideal vs actual»:** the ideal in its own neutral grey, `PAC_EXPOSURE_COLORS.ideal` of
  `chartTheme.ts`; the actual weight in its row's category colour, a subtype in a shade of its family (§1.7).
- **The type colours outside the canvas** (§1.9, decision A): the HTML that draws a type reads T's roles
  `--lf-cat-<type>` (`bg-lf-cat-etf`; `-soft` and `-on-soft` for a badge), as the book-value and cash bars of the
  Dashboard's net-worth card do. Until the Designer Lab moves to the roles (DV-11) a type colour lives twice, in
  `chartCategories.ts` and in tokens.css: change both together; the parity test of `chartCategories.test.ts` holds them
  equal.
- **Roles in a chart:** `chartRoles(dark, scope)` of `roleColors.ts` reads `--lf-*` on the chart's own element at each
  draw: `color(role)`, and `readableText(background)` for a label over a fill.
- **Neutrals on roles (B4):** axes, grids and rules, labels, tooltip boxes, pointers, and the gaps and rings in the
  card's colour come from `chartNeutrals(dark, scope)` of `chartTheme.ts`, taken once per draw on the chart's own
  element:
  - text by its shade, as the interface's classes were migrated: `primary`, `secondary`, `muted`;
  - a tooltip box is a popover: the card, the raised border, the primary and the muted text;
  - the structure lines (axes, grids, separators, frames) `subtle`; reference lines, pointers and leader lines `input`;
  - always name a tooltip box and an axis pointer: ECharts' own are white and grey in both themes.
- **Series, states and signs not on roles yet:** the named pairs of `chartTheme.ts`, read with `themed(pair, dark)`,
  legacy values on purpose, for the designer; gain and loss wait for a batch with her. Computed scales are in
  `chartColorScales.ts`, alpha in `colorAlpha.ts`, contrast in `contrast.ts`.
- **Redraw** when the theme changes (`onThemeClassChange`) and when the Designer Lab edits a colour
  (`onChartColorsChange`, contract C4). A chart that otherwise updates its data only must rebuild its options at that
  signal, or its colours do not change (TD-1b: `GrowthChart` calls `renderChart(true)`).
- **Never a hex in a chart component, and never a category colour changed locally:** a change of the designer's
  list goes back to her, and lands in `chartCategories.ts`.
- **A colour the user picked stays his** (signals, DV decisions 6 and 7): only the proposed colours change, and a saved
  signal migrates only while it is still on the old default. This is S9, still to do.

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
   - its stand-in in `roleColors.ts`, if a chart or a drawn colour reads it, and the static copies, if the splash, the
     offline page or the title bar paint it;
   - its row in [`palette.md`](palette.md), and its family's line in this skill.
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
   - the centre of the correlation matrix, the panel, at 1.1:1 on the card;
   - 2.2: the cash (`Liquidity`) at ΔE00 7.8 from the success green in light, and equal to `--lf-focus` in dark;
   - 2.8: whether the rule of the greens concerns the categories only;
   - 2.9: «unclassified» at 2.6:1 on the card, under the 3:1 of WCAG 1.4.11;
   - the exception of TD-1: the dark «Other» at ΔE00 9.0 from `--lf-text-secondary` (`exposureBarColours.test.ts`).

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
   its own. A new switch follows the Q2 rows of [`palette.md`](palette.md) and is reported to the colour
   coordinator.
5. **Three provisional roles of 16/10**, asked by the migration and built by T from her values:
   - `--lf-success-hover` and `--lf-info-hover`, a solid success or info button hovered:
     `color-mix(in oklab, var(--lf-X) 80%, var(--lf-text-primary))`, 20 % toward the primary text. It darkens in light
     and lightens in dark, so the hover always moves away from its text `--lf-on-status`: 6.58:1 and 6.54:1 in light,
     10.63:1 and 6.47:1 in dark. Her own Q3 hovers go darker in both themes instead (in dark: warning `#d97706`, danger
     `#d51c42`); a darker info hover would fall under 4.5:1 in dark.
   - `--lf-on-overlay`, text and icons on the backdrop: `#ffffff` in both themes, 4.98:1 at worst (the backdrop over a
     white field).

   Until then: use them as they are.
6. **The selected tint.** `--lf-selected`, a selected or highlighted row, option or chip, is the focus green at 12 %
   over its surface (T, from her «Focus, link attivi»). On it the muted text, the statuses and the signs fall to
   3.84–4.48:1, and a lighter tint would not cure it (6 %: 4.17:1). Under review: the tint, and how a selected row keeps
   its muted captions.

   Until then: rule 5, «On a selected row» — the captions turn secondary while the row is selected (TC-15), `link`
   never over a `panel`, and a selected chip under the pointer takes `hover:bg-lf-checked/20 hover:text-lf-primary`.
7. **The accent of an empty page.** The empty states of the asset and the FX lists draw an icon in a tinted circle: the
   assets' now takes the app's accent (`bg-lf-selected`, `text-lf-link`), the FX's is still amber, a page colour no role
   covers (`warning` would read as a warning). Under review: one accent per page, or the app's green for every empty
   state.

   Until then: a new empty state takes the app's accent; the FX one stays as it is (`routes/(app)/fx/+page.svelte`).

**Values waiting for her confirmation** (backlog TC-8):
- the seven minimal contrast corrections of her round 2 (D-T6), each with her value in a comment of `tokens.css`: in
  light `--lf-warning`, `--lf-danger-soft`, `--lf-info-soft`, `--lf-bar-text-muted`; in dark
  `--lf-warning-on-inverse`, `--lf-danger-solid`, `--lf-danger-hover`;
- the roles marked «provisional»: `--lf-action-hover` in light, `--lf-on-ai`, `--lf-terminal-comment`,
  `--lf-shadow-card` in dark, and the three of question 5;
- the developer's dark red and green (D-T25, D-T26), extended to the states on the green sidebar;
- gain and loss kept apart from success and error; the switch turned off, recognised in light only by the edge of its
  knob.

The choices the night's migration made «da rivedere» are in the backlog, TC-10: the developer reviews them first.

## See also

- [`palette.md`](palette.md): every role, with its value in both themes and when to use it.
- [`tokens.css`](../../../../frontend/src/lib/theme/tokens.css): the roles, with the source of each value in a comment.
- The skill [`theme-roles`](../theme-roles/SKILL.md): migrating a component, the class → role table, the baseline.
- The skill [`designer-lab-apply`](../designer-lab-apply/SKILL.md): the Designer Lab (debug builds) tunes the roles
  live; an export of it is applied with that skill.
- `.github/instructions/frontend.instructions.md`, «Design System»; the gates `src/themeRoles.gate.test.ts`,
  `src/themeTokens.gate.test.ts`, `src/themeColorMeta.gate.test.ts`, `src/themeComponentTokens.gate.test.ts`,
  `src/themeModeReads.gate.test.ts`.
- devWiki: [`decisions/colour-factorisation-at-pixel-parity`](../../../../LibreFolio_devWiki/wiki/decisions/colour-factorisation-at-pixel-parity.md),
  the factorisation of every colour into `lib/theme/` (workstream R).
