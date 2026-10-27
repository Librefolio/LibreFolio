# LibreFolio palette: every colour role, in both themes

The companion of [`SKILL.md`](SKILL.md), the design system (the themes, the shared colour folder, the rules). This file
holds every role of [`tokens.css`](../../../../frontend/src/lib/theme/tokens.css): its utility, its value in the light
and in the dark theme, and when to use it. Rule numbers refer to `SKILL.md`.

- **The values** are copied from `tokens.css` by a script and checked against it: every role has exactly one row, with
  its own utilities. If they ever differ, `tokens.css` wins, and whoever changes a role (T) updates this file in the
  same commit.
- Every utility takes an opacity: `bg-lf-card/90`, `border-lf-on-brand/20`.
- Paths are under `frontend/`.

## Surfaces

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-app` | `bg-lf-app` | `#f3f5f3` | `#0d1110` | Behind the app shell: the background of every page inside the app. The same colour as `page` since round 2 |
| `--lf-surface-page` | `bg-lf-page` | `#f3f5f3` | `#0d1110` | A page outside the shell: login, sign-up, welcome, error, offline, splash, server unreachable |
| `--lf-surface-card` | `bg-lf-card` | `#fafbfa` | `#151b19` | Cards, modals, menus, dropdowns, popovers |
| `--lf-surface-panel` | `bg-lf-panel` | `#e8ece9` | `#1b2421` | The secondary surface: panels, table heads, boxes inside a card, the track of a segmented control, a secondary button, inline code |
| `--lf-surface-field` | `bg-lf-field` | `#ffffff` | `#0f1413` | The inside of an input, a select trigger, a textarea |
| `--lf-surface-hover` | `hover:bg-lf-hover` | `#e8ece9` | `#1b2421` | A row or an item under the pointer, on a card or a page. It equals `panel`: on a panel, hover with `hover:bg-lf-neutral` (SKILL.md, «Values the designer has not confirmed», rule 2) |
| `--lf-surface-neutral` | `bg-lf-neutral` | `#d8e0dc` | `#222c28` | Neutral fills: progress tracks, skeletons, neutral chips; the hover of a control that sits on a panel |
| `--lf-surface-logo` | `bg-lf-logo` | `#ffffff` | `#ffffff` | The tile behind the logo: white in both themes, on the green too (N1) |

## Text

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-text-primary` | `text-lf-primary` | `#1c2420` | `#edf2f0` | Body text, titles, values. Set it on the root of every component (rule 1) |
| `--lf-text-secondary` | `text-lf-secondary` | `#4a5550` | `#9ba8a2` | Labels, subtitles, the caption of a value, the text of a secondary button |
| `--lf-text-muted` | `text-lf-muted`; `bg-lf-muted` for the dot | `#616d67` | `#7f8c87` | Hints, timestamps, inactive icons, disabled text, the «inactive» status dot (Q5) |
| `--lf-text-placeholder` | `placeholder:text-lf-placeholder` | `#616d67` | `#7f8c87` | The placeholder of a field: the muted text |

## Borders

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-border-subtle` | `border-lf-subtle`, `divide-lf-subtle` | `#d8e0dc` | `#222c28` | Borders and dividers of cards, tables and sections; the edge of inline code |
| `--lf-border-raised` | `border-lf-raised` | `#d8e0dc` | `#2e3b36` | The border of a surface that floats: modal, dropdown, menu, popover, the login card (N3) |
| `--lf-border-input` | `border-lf-input` | `#7e8984` | `#606f6a` | The border of a field or a control at rest, 3:1 on every surface (D-T18); the edge of a switch knob turned off |
| `--lf-border-input-hover` | `hover:border-lf-input-hover` | `#616d67` | `#7f8c87` | The border of a field under the pointer: the muted text colour (D-T18). `focus:border-lf-focus` wins over it |

## Brand and action

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-brand` | `bg-lf-brand` | `#1b4334` | `#1b4334` | The brand green as a surface: the header of the login card. The sidebar has a family of its own (`bar`), on the same green |
| `--lf-on-brand` | `text-lf-on-brand` | `#fafbfa` | `#edf2f0` | Text and icons on the brand green; `/70` for its secondary text, `/20` for its borders, `/10` for a hover |
| `--lf-action` | `bg-lf-action` | `#1b4334` | `#215240` | The primary button: the action the view is for |
| `--lf-action-hover` | `hover:bg-lf-action-hover` | `color-mix(in oklab, #1b4334 70%, #236b4d)` | `#28634e` | The primary button under the pointer (provisional in light: toward the focus green) |
| `--lf-on-action` | `text-lf-on-action` | `#fafbfa` | `#edf2f0` | Text and icons on the primary button |

## Focus, links and selection

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-focus` | `focus-visible:outline-lf-focus`, `focus:ring-lf-focus`, `focus:border-lf-focus` | `#236b4d` | `#429e79` | Keyboard focus, and the border of a focused field, on every neutral surface (3:1). On the sidebar, `--lf-bar-focus` |
| `--lf-link` | `text-lf-link` | `#236b4d` | `#429e79` | Links, the active item inside a page, accent icons. The focus green: the designer's «Focus, link attivi» |
| `--lf-selected` | `bg-lf-selected` | `color-mix(in oklab, #236b4d 12%, transparent)` | `color-mix(in oklab, #429e79 12%, transparent)` | A selected or highlighted row, option, item or date range: a quiet tint of the focus green. Its text: `text-lf-primary`, `text-lf-secondary`, or `text-lf-link` except over a `panel`; never muted, a status or a sign (SKILL.md, rule 5) |
| `--lf-checked` | `bg-lf-checked` | `#236b4d` | `#429e79` | A selected control: checkbox, radio, switch turned on, selected day or preset, active segment (D-T16) |
| `--lf-on-checked` | `text-lf-on-checked` | `#fafbfa` | `#151b19` | The mark on a checked fill: the tick, the dot, the number of the selected day |
| `--lf-tour-glow` | `ring-lf-tour-glow`, or `var(--lf-tour-glow)` in a shadow | `color-mix(in oklab, #236b4d 40%, transparent)` | `color-mix(in oklab, #429e79 40%, transparent)` | The glow of the guided tour around the element it shows (Q9) |

## States

Four families: `success`, `warning`, `danger`, `info`. **Each one comes as a set**, never split:
- `text-lf-X` for a state as text or icon;
- `bg-lf-X-soft border-lf-X-line text-lf-X-on-soft` for an alert, a banner, a toast, a badge, a row in that state;
- `bg-lf-X text-lf-on-status` for a solid fill (a solid badge), and `hover:bg-lf-X-hover` for a solid button hovered;
- a chip or a button inside a banner: `STATUS_TONES.bannerChip` (SKILL.md, rule 12), the card with an edge in `X`.

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-success` | `text-lf-success`, `bg-lf-success` | `#18794e` | `#5ed69a` | A success as text or icon (✓, «Strong»), or its solid fill; the edge of a chip inside a banner (rule 12) |
| `--lf-success-soft` | `bg-lf-success-soft` | `#e6f4ed` | `#13261e` | The tint of a success alert, toast, badge or row |
| `--lf-success-line` | `border-lf-success-line` | `#b8dfca` | `#1f4435` | Its border; the hover of a dismiss button on the tint |
| `--lf-success-on-soft` | `text-lf-success-on-soft` | `#145937` | `#86efac` | Text on the success tint |
| `--lf-success-hover` | `hover:bg-lf-success-hover` | `color-mix(in oklab, #18794e 80%, #1c2420)` | `color-mix(in oklab, #5ed69a 80%, #edf2f0)` | A solid success button under the pointer, with `text-lf-on-status`. **Provisional**: 20 % toward the primary text (≈ `#1f6744` in light, `#81dcab` in dark), so it moves away from its text in both themes; 6.58:1 in light, 10.63:1 in dark |
| `--lf-warning` | `text-lf-warning`, `bg-lf-warning` | `#ae4e00` | `#f59e0b` | A warning as text or icon, or its solid fill; the «modified» state of a setting (Q4); the edge of a chip inside a banner (rule 12) |
| `--lf-warning-soft` | `bg-lf-warning-soft` | `#fef3c7` | `#291e0c` | The tint of a warning alert, toast, badge or row |
| `--lf-warning-line` | `border-lf-warning-line` | `#fde68a` | `#54380e` | Its border; the hover of a dismiss button on the tint |
| `--lf-warning-on-soft` | `text-lf-warning-on-soft` | `#92400e` | `#fcd34d` | Text on the warning tint |
| `--lf-warning-hover` | `hover:bg-lf-warning-hover` | `#92400e` | `#d97706` | A solid warning button under the pointer (Q3) |
| `--lf-danger` | `text-lf-danger`, `bg-lf-danger` | `#c82838` | `#ff7a86` | An error as text, icon or border (an invalid field), or its solid fill. A softer red in dark (D-T25); the edge of a chip inside a banner (rule 12) |
| `--lf-danger-soft` | `bg-lf-danger-soft` | `#ffe5e5` | `#2a1417` | The tint of an error alert, toast, badge or row |
| `--lf-danger-line` | `border-lf-danger-line` | `#fecaca` | `#581c24` | Its border; the hover of a dismiss button on the tint |
| `--lf-danger-on-soft` | `text-lf-danger-on-soft` | `#991b1b` | `#fca5a5` | Text on the error tint |
| `--lf-danger-solid` | `bg-lf-danger-solid` | `#c82838` | `#e1284f` | A solid destructive button, «Delete account» (Q3): it carries white text, which `danger` cannot in dark |
| `--lf-danger-hover` | `hover:bg-lf-danger-hover` | `#a81f2d` | `#d51c42` | That button under the pointer |
| `--lf-on-danger-solid` | `text-lf-on-danger-solid` | `#ffffff` | `#ffffff` | Its white text, at rest and hovered |
| `--lf-info` | `text-lf-info`, `bg-lf-info` | `#155eef` | `#3f86fa` | Information as text or icon, or its solid fill; the edge of a chip inside a banner (rule 12) |
| `--lf-info-soft` | `bg-lf-info-soft` | `#deedff` | `#131f33` | The tint of an info alert, toast, badge or row |
| `--lf-info-line` | `border-lf-info-line` | `#bfdbfe` | `#1e3a5f` | Its border; the hover of a dismiss button on the tint |
| `--lf-info-on-soft` | `text-lf-info-on-soft` | `#1e40af` | `#93c5fd` | Text on the info tint |
| `--lf-info-hover` | `hover:bg-lf-info-hover` | `color-mix(in oklab, #155eef 80%, #1c2420)` | `color-mix(in oklab, #3f86fa 80%, #edf2f0)` | A solid info button under the pointer, with `text-lf-on-status`. **Provisional**, as `success-hover` (≈ `#1854c2` in light, `#639efa` in dark): 6.54:1 in light, 6.47:1 in dark (a darker hover would fall under 4.5:1 in dark) |
| `--lf-on-status` | `text-lf-on-status` | `#fafbfa` | `#151b19` | Text on a solid state fill (solid badges) and on a solid warning or donation button hovered. Toasts are tints since round 3 |

## Gain, loss and donation

A sign, never a state (rule 7): as text `text-lf-gain`, `text-lf-loss`; on a tint, `SIGN_BADGE` of `toneClasses.ts`.

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-gain` | `text-lf-gain` | `#18794e` | `#5ed69a` | A positive signed figure: P&L, return, a price that went up (rule 7). Today the value of `success` |
| `--lf-loss` | `text-lf-loss` | `#c82838` | `#ff7a86` | A negative signed figure. Today the value of `danger` |
| `--lf-gain-soft` | `bg-lf-gain-soft` | `#e6f4ed` | `#13261e` | A gain on a tint: a badge or a chip that says gain or loss, not a state (`SIGN_BADGE` of `toneClasses.ts`). Today the success tint, kept a role of its own |
| `--lf-gain-on-soft` | `text-lf-gain-on-soft` | `#145937` | `#86efac` | Text on the gain tint |
| `--lf-loss-soft` | `bg-lf-loss-soft` | `#ffe5e5` | `#2a1417` | A loss on a tint. Today the danger tint, kept a role of its own |
| `--lf-loss-on-soft` | `text-lf-loss-on-soft` | `#991b1b` | `#fca5a5` | Text on the loss tint |
| `--lf-donate` | `text-lf-donate` | `#ae4e00` | `#f59e0b` | The donation link «Offrimi un caffè»: the warm amber of `warning` |
| `--lf-donate-hover` | `hover:text-lf-donate-hover` | `#92400e` | `#d97706` | The donation link under the pointer (Q3) |

## The tooltip, an inverted surface

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-inverse` | `bg-lf-inverse` | `#1c2420` | `#edf2f0` | The tooltip: dark in the light theme, light in the dark theme (the primary text colour) |
| `--lf-text-on-inverse` | `text-lf-on-inverse` | `#fafbfa` | `#151b19` | The text of a tooltip (the card colour) |
| `--lf-warning-on-inverse` | `text-lf-warning-on-inverse` | `#f59e0b` | `#ae4e00` | A warning inside a tooltip: the other theme's warning (Q10, rule 6) |
| `--lf-danger-on-inverse` | `text-lf-danger-on-inverse` | `#ff7a86` | `#c82838` | An error inside a tooltip: the other theme's danger |
| `--lf-info-on-inverse` | `text-lf-info-on-inverse` | `#3f86fa` | `#155eef` | Information, links and formulas inside a tooltip: the other theme's info |
| `--lf-text-muted-on-inverse` | `text-lf-muted-on-inverse` | `#7f8c87` | `#616d67` | Muted text inside a tooltip: the other theme's muted text |

## Backdrops and shadows

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-surface-overlay` | `bg-lf-overlay` | `color-mix(in oklab, #0d1110 60%, transparent)` | `color-mix(in oklab, #0d1110 60%, transparent)` | The backdrop of a modal and of the guided tour: the dark page at 60 %, in both themes (Q13) |
| `--lf-on-overlay` | `text-lf-on-overlay` | `#ffffff` | `#ffffff` | Text and icons on the backdrop: a camera on an avatar, an icon on a scrim. **Provisional**: white in both themes, 4.98:1 at worst, the backdrop over a white field |
| `--lf-shadow-raised` | `shadow-lf-shadow` | `color-mix(in oklab, #0d1110 25%, transparent)` | `color-mix(in oklab, #0d1110 50%, transparent)` | The shadow colour of a floating surface, beside a size: `shadow-xl shadow-lf-shadow` (Q8) |
| `--lf-shadow-card` | `shadow-lf-shadow-card` | `color-mix(in oklab, #0d1110 7%, transparent)` | `color-mix(in oklab, #0d1110 40%, transparent)` | The shadow colour of a card on a page: `shadow-sm shadow-lf-shadow-card` (provisional in dark) |

## The shell: sidebar and header

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

## Controls and special surfaces

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

## Categories: the asset types (round 3)

The colour of each asset type, the one the charts draw it in (§1.2 of the designer's round 3: since DV-11
`chartCategories.ts` reads these roles, one copy), with its badge tint and text (§1.9): the eleven types
and the cash. **A badge is the pair** `bg-lf-cat-X-soft text-lf-cat-X-on-soft`, taken from
`assetTypeBadgeClass()` of `src/lib/utils/assetTypes.ts`, never written by hand; a subtype takes its family's colour and
says what it contains with a dot, `assetTypeBadgeDotClass()`, in the content's `-on-soft` (SKILL.md, rule 11).

- **`-soft`** is derived: `color-mix(in srgb, var(--lf-cat-X) 14%, var(--lf-surface-card))`, the type's colour at
  14 % on the card, mixed in sRGB as her values were.
- **`-on-soft`** is her badge text: the colour itself, or the colour moved in OKLCH lightness alone as far as 4.5:1 on
  its tint.
- **No green, teal or cyan among them** (§1.1): the cash is slate blue.

| Role | Utility | Light | Dark | When to use |
|---|---|---|---|---|
| `--lf-cat-stock` | `bg-lf-cat-stock` | `#7041c6` | `#b69af0` | `STOCK`: the colour of a stock in the charts, as a fill or a mark |
| `--lf-cat-stock-soft` | `bg-lf-cat-stock-soft` | `color-mix(in srgb, #7041c6 14%, #fafbfa)` | `color-mix(in srgb, #b69af0 14%, #151b19)` | The tint of a stock's badge (≈ `#e7e1f3` in light, `#2c2d37` in dark) |
| `--lf-cat-stock-on-soft` | `text-lf-cat-stock-on-soft`, `bg-lf-cat-stock-on-soft` | `#7041c6` | `#b69af0` | The text of a stock's badge, 5.04 and 5.79:1 on its tint; the dot of `ETF_STOCK` |
| `--lf-cat-etf` | `bg-lf-cat-etf` | `#2459b8` | `#82acf8` | `ETF`: the colour of an ETF in the charts, as a fill or a mark; the book-value bar of the net-worth card |
| `--lf-cat-etf-soft` | `bg-lf-cat-etf-soft` | `color-mix(in srgb, #2459b8 14%, #fafbfa)` | `color-mix(in srgb, #82acf8 14%, #151b19)` | The tint of an ETF's badge (≈ `#dce4f1` in light, `#242f38` in dark); every `ETF_*` subtype's badge |
| `--lf-cat-etf-on-soft` | `text-lf-cat-etf-on-soft` | `#2459b8` | `#82acf8` | The text of an ETF's badge, 5.15 and 5.96:1 on its tint |
| `--lf-cat-bond` | `bg-lf-cat-bond` | `#536a9e` | `#9baed8` | `BOND`: the colour of a bond in the charts, as a fill or a mark |
| `--lf-cat-bond-soft` | `bg-lf-cat-bond-soft` | `color-mix(in srgb, #536a9e 14%, #fafbfa)` | `color-mix(in srgb, #9baed8 14%, #151b19)` | The tint of a bond's badge (≈ `#e3e7ed` in light, `#283034` in dark) |
| `--lf-cat-bond-on-soft` | `text-lf-cat-bond-on-soft`, `bg-lf-cat-bond-on-soft` | `#4f669a` | `#9baed8` | The text of a bond's badge, 4.56 and 6.07:1 on its tint; the dot of `ETF_BOND`. In light a D-T6 correction of her `#50679b` (4.49:1 on the exact tint), accepted by the coordinator (17/10) |
| `--lf-cat-crypto` | `bg-lf-cat-crypto` | `#b87916` | `#e8bd69` | `CRYPTO`: the colour of a crypto-asset in the charts, as a fill or a mark |
| `--lf-cat-crypto-soft` | `bg-lf-cat-crypto-soft` | `color-mix(in srgb, #b87916 14%, #fafbfa)` | `color-mix(in srgb, #e8bd69 14%, #151b19)` | The tint of a crypto-asset's badge (≈ `#f1e9da` in light, `#333224` in dark) |
| `--lf-cat-crypto-on-soft` | `text-lf-cat-crypto-on-soft`, `bg-lf-cat-crypto-on-soft` | `#925e0c` | `#e8bd69` | The text of a crypto-asset's badge, 4.54 and 7.38:1 on its tint; the dot of `ETF_CRYPTO` |
| `--lf-cat-fund` | `bg-lf-cat-fund` | `#5147b8` | `#9280ff` | `FUND`: the colour of a fund in the charts, as a fill or a mark (dark: V1-dc) |
| `--lf-cat-fund-soft` | `bg-lf-cat-fund-soft` | `color-mix(in srgb, #5147b8 14%, #fafbfa)` | `color-mix(in srgb, #9280ff 14%, #151b19)` | The tint of a fund's badge (≈ `#e2e2f1` in light, `#272939` in dark) |
| `--lf-cat-fund-on-soft` | `text-lf-cat-fund-on-soft` | `#5147b8` | `#9280ff` | The text of a fund's badge, 5.56 and 4.62:1 on its tint |
| `--lf-cat-hold` | `bg-lf-cat-hold` | `#5d687b` | `#c6d0e0` | `HOLD`: the colour of a held asset in the charts, as a fill or a mark (G1-la and G1-db) |
| `--lf-cat-hold-soft` | `bg-lf-cat-hold-soft` | `color-mix(in srgb, #5d687b 14%, #fafbfa)` | `color-mix(in srgb, #c6d0e0 14%, #151b19)` | The tint of a held asset's badge (≈ `#e4e6e8` in light, `#2e3435` in dark) |
| `--lf-cat-hold-on-soft` | `text-lf-cat-hold-on-soft` | `#5c677a` | `#c6d0e0` | The text of a held asset's badge, 4.58 and 8.11:1 on its tint |
| `--lf-cat-crowdfund` | `bg-lf-cat-crowdfund` | `#8b547d` | `#d5a0c7` | `CROWDFUND`: the colour of a crowdfunding in the charts, as a fill or a mark |
| `--lf-cat-crowdfund-soft` | `bg-lf-cat-crowdfund-soft` | `color-mix(in srgb, #8b547d 14%, #fafbfa)` | `color-mix(in srgb, #d5a0c7 14%, #151b19)` | The tint of a crowdfunding's badge (≈ `#eae4e9` in light, `#302e31` in dark); `CROWDFUND_REAL_ESTATE`'s badge |
| `--lf-cat-crowdfund-on-soft` | `text-lf-cat-crowdfund-on-soft` | `#8b547d` | `#d5a0c7` | The text of a crowdfunding's badge, 4.57 and 6.23:1 on its tint |
| `--lf-cat-commodity` | `bg-lf-cat-commodity` | `#b85e45` | `#e99a82` | `COMMODITY`: the colour of a commodity in the charts, as a fill or a mark |
| `--lf-cat-commodity-soft` | `bg-lf-cat-commodity-soft` | `color-mix(in srgb, #b85e45 14%, #fafbfa)` | `color-mix(in srgb, #e99a82 14%, #151b19)` | The tint of a commodity's badge (≈ `#f1e5e1` in light, `#332d28` in dark) |
| `--lf-cat-commodity-on-soft` | `text-lf-cat-commodity-on-soft`, `bg-lf-cat-commodity-on-soft` | `#a64e35` | `#e99a82` | The text of a commodity's badge, 4.52 and 6.10:1 on its tint; the dot of `ETF_COMMODITY` |
| `--lf-cat-real-estate` | `bg-lf-cat-real-estate` | `#96602c` | `#d6a36c` | `REAL_ESTATE`: the colour of real estate in the charts, as a fill or a mark |
| `--lf-cat-real-estate-soft` | `bg-lf-cat-real-estate-soft` | `color-mix(in srgb, #96602c 14%, #fafbfa)` | `color-mix(in srgb, #d6a36c 14%, #151b19)` | The tint of real estate's badge (≈ `#ece5dd` in light, `#302e25` in dark) |
| `--lf-cat-real-estate-on-soft` | `text-lf-cat-real-estate-on-soft`, `bg-lf-cat-real-estate-on-soft` | `#905a26` | `#d6a36c` | The text of real estate's badge, 4.58 and 6.04:1 on its tint; the dot of `ETF_REAL_ESTATE`, `CROWDFUND_REAL_ESTATE` |
| `--lf-cat-index` | `bg-lf-cat-index` | `#a33d79` | `#e58bb9` | `INDEX`: the colour of an index in the charts, as a fill or a mark |
| `--lf-cat-index-soft` | `bg-lf-cat-index-soft` | `color-mix(in srgb, #a33d79 14%, #fafbfa)` | `color-mix(in srgb, #e58bb9 14%, #151b19)` | The tint of an index's badge (≈ `#eee0e8` in light, `#322b2f` in dark) |
| `--lf-cat-index-on-soft` | `text-lf-cat-index-on-soft` | `#a33d79` | `#e58bb9` | The text of an index's badge, 4.71 and 5.74:1 on its tint |
| `--lf-cat-other` | `bg-lf-cat-other` | `#727b87` | `#a9b0bb` | `OTHER`: the colour of another asset in the charts, as a fill or a mark |
| `--lf-cat-other-soft` | `bg-lf-cat-other-soft` | `color-mix(in srgb, #727b87 14%, #fafbfa)` | `color-mix(in srgb, #a9b0bb 14%, #151b19)` | The tint of another asset's badge (≈ `#e7e9ea` in light, `#2a3030` in dark) |
| `--lf-cat-other-on-soft` | `text-lf-cat-other-on-soft` | `#616a75` | `#a9b0bb` | The text of another asset's badge, 4.51 and 6.16:1 on its tint |
| `--lf-cat-liquidity` | `bg-lf-cat-liquidity` | `#3f628c` | `#639bc0` | `Liquidity`: the colour of the cash in the charts, as a fill or a mark (dark: B1-dc); the cash bar of the net-worth card |
| `--lf-cat-liquidity-soft` | `bg-lf-cat-liquidity-soft` | `color-mix(in srgb, #3f628c 14%, #fafbfa)` | `color-mix(in srgb, #639bc0 14%, #151b19)` | The tint of the cash's badge (≈ `#e0e6eb` in light, `#202d30` in dark) |
| `--lf-cat-liquidity-on-soft` | `text-lf-cat-liquidity-on-soft`, `bg-lf-cat-liquidity-on-soft` | `#3f628c` | `#639bc0` | The text of the cash's badge, 4.98 and 4.72:1 on its tint; the dot of `ETF_MONETARY` |
